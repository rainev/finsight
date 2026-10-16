"""Reusable after-interest equity cash forecasts from aligned statement tables."""
from copy import deepcopy
from datetime import date
from math import isclose,isfinite

from .family_forecast import fact, annualize, common_state
from .table_first import inspect_tables
from .calculation_recipe import evaluate_recipe
from .catalog import canonical_json_bytes, sha256_bytes

SCHEMA='US-OPERATING-CASH-FORECAST-1'
LEGACY_GROWTH_RULE='incremental_revenue_times_current_common_equity_to_revenue'
REVISED_GROWTH_RULE='reported_total_capex_plus_reviewed_incremental_plan_only'
REINVESTMENT_VERSION='US-CASH-REINVESTMENT-2'
DEFAULTS={'years':5,'cost_of_equity':[.14,.12,.10],'terminal_growth':[0.,.01,.02],
          'cash_margin_multiplier':[.8,1.,1.2],'capex_multiplier':[1.1,1.,1.],
          'growth_delta':[-.02,0.,.02],'growth_limits':[-.10,.15],
          'funding':'zero_net_borrowing_existing_maturities_refinanced',
          'growth_investment':REVISED_GROWTH_RULE,
          'sbc':'deduct_reported_expense_no_additional_generic_dilution'}


def incremental_reinvestment(a, *, current_revenue, next_revenue, common_equity,
                             initial_revenue, scenario, year=None,terminal_growth=None):
    """Full forecast capex is deducted elsewhere. Only add demonstrated extras.

    Explicit legacy policies keep their recorded arithmetic for replay. New
    policies require a reviewed plan incremental to the existing capex forecast.
    """
    rule=a['growth_investment']
    if rule==LEGACY_GROWTH_RULE:
        if a.get('incremental_capital_plan') is not None:raise ValueError('legacy reserve and incremental capital plan cannot be combined')
        increment=current_revenue*terminal_growth if year is None and terminal_growth is not None else next_revenue-current_revenue
        return max(increment,0)*(common_equity/initial_revenue)
    if rule!=REVISED_GROWTH_RULE:raise ValueError('unsupported cash reinvestment rule')
    plan=a.get('incremental_capital_plan')
    if plan is None:return 0.
    if (plan.get('basis')!='incremental_to_forecast_total_capex'
        or not all(plan.get(k) for k in ('source_reference','reviewer','review_date','reason'))):
        raise ValueError('incremental capital plan lacks supported scope/review evidence')
    date.fromisoformat(plan['review_date'])
    amounts=plan.get('cash_by_scenario',{});terminal=plan.get('terminal_cash_by_scenario',{})
    if set(amounts)!={'bear','base','bull'} or set(terminal)!={'bear','base','bull'}:
        raise ValueError('incremental capital plan scenario coverage incomplete')
    for name in amounts:
        values=amounts[name]
        if not isinstance(values,list) or len(values)!=a['years']:
            raise ValueError('incremental capital plan horizon incomplete')
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) or v<0 for v in [*values,terminal[name]]):
            raise ValueError('incremental capital plan cash amounts invalid')
    return terminal[scenario] if year is None else amounts[scenario][year-1]


def build_cash_recipe(packet,policy):
    if policy.get('schema_version')!=SCHEMA:raise ValueError('unsupported operating cash policy')
    for source in ('submissions','companyfacts'):
        if str(packet[source]['cik']).zfill(10)!=str(policy['cik']).zfill(10):raise ValueError('cash source issuer mismatch')
    needs_bridge=bool(policy.get('current_scope_only') or policy.get('requires_continuing_income'))
    cash_bridge=None
    if needs_bridge:
        from .continuing_cash import reconcile_continuing_cash
        cash_bridge=reconcile_continuing_cash(packet,removal_scopes=policy.get('discontinued_removal_scopes'))
        if not cash_bridge['complete'] and policy.get('allocation_policy'):
            from .continuing_cash import apply_reviewed_allocation
            cash_bridge=apply_reviewed_allocation(packet,cash_bridge,policy['allocation_policy'])
        if not cash_bridge['complete']:
            raise ValueError('continuing-operation cash bridge unresolved: '+', '.join(cash_bridge['missing_fields']))
    if policy.get('business_family')!='general_operating':
        raise ValueError('cyclical, project or customer-funds cash flow needs its own shared forecast template')
    if policy.get('comparative_scope_review',{}).get('status')=='predecessor_comparison_unreconciled':
        raise ValueError('successor/predecessor comparative revenue needs an operating-scope reconciliation')
    filing=packet['controlling_filing'];cutoff=policy['evidence_cutoff']
    if filing['filingDate']>cutoff or filing['reportDate']>cutoff:raise ValueError('filing after cash cutoff')
    audit=inspect_tables(packet,cik=policy['cik'],cutoff=cutoff)
    if audit['exceptions']:raise ValueError('cash statement exception: '+str(audit['exceptions'][0]))
    state=common_state(packet,requires_continuing=needs_bridge)
    if state['preferred']>0 or policy.get('mandatory_conversion'):raise ValueError('preferred cash claims/conversion require an equity cash allocation')
    sources={}
    def flow(key,names,optional=False):
        value=fact(packet,names,flow=True,optional=optional)
        if value is not None:sources[key]=value
        return value
    revenue=flow('revenue',['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'])
    if cash_bridge is not None:
        from .continuing_cash import resolved_flow
        cfo=resolved_flow(cash_bridge,'cfo',revenue['period_start'])
        capex=resolved_flow(cash_bridge,'capex',revenue['period_start'])
        sbc=resolved_flow(cash_bridge,'sbc',revenue['period_start'])
        sources.update(cfo=cfo,capex=capex,sbc=sbc)
    else:
        cfo=flow('cfo',['NetCashProvidedByUsedInOperatingActivities'])
        capex=flow('capex',['PaymentsToAcquireProductiveAssets','PaymentsToAcquirePropertyPlantAndEquipment'])
        sbc=flow('sbc',['ShareBasedCompensation'])
    if any(r['period_start']!=revenue['period_start'] for r in (cfo,capex,sbc)):
        raise ValueError('cash/reinvestment periods differ')
    if revenue['value']<=0 or min(capex['value'],sbc['value'])<0:raise ValueError('invalid cash spending or revenue')
    # Separately tagged intangible cash investment supplements PP&E, never an
    # acquisition-price or marketable-security purchase. Productive-assets total
    # with another investment tag needs a scope review rather than double count.
    intangible=flow('intangible_capex',['PaymentsToAcquireIntangibleAssets','PaymentsToDevelopSoftware'],True)
    if intangible is not None and intangible['value']:
        if cash_bridge is not None and not cash_bridge.get('allocation_policy'):
            raise ValueError('separate intangible cash spending requires a continuing-operation scope allocation')
        if capex['qname'].endswith('PaymentsToAcquireProductiveAssets'):
            raise ValueError('capital-spending aggregate and intangible investment overlap unresolved')
        if intangible['period_start']!=revenue['period_start']:raise ValueError('intangible spending period differs')
    lease=flow('finance_lease_principal',['FinanceLeasePrincipalPayments','RepaymentsOfCapitalLeaseObligations'],True)
    liabilities=[fact(packet,[name],optional=True) for name in ('FinanceLeaseLiabilityCurrent','FinanceLeaseLiabilityNoncurrent',
                    'CapitalLeaseObligationsCurrent','CapitalLeaseObligationsNoncurrent')]
    if any(r is not None and r['value']>0 for r in liabilities) and lease is None:
        raise ValueError('reported finance leases require a principal-payment cash allocation')
    minority=flow('minority_income',['NetIncomeLossAttributableToNoncontrollingInterest'],True)
    if minority is None and cash_bridge and cash_bridge.get('allocation_policy'):
        group=flow('group_net_income',['ProfitLoss'],True)
        parent=flow('parent_net_income',['NetIncomeLoss'],True)
        if group is not None and parent is not None:
            if group['period_start']!=parent['period_start']:raise ValueError('group/parent minority earnings periods differ')
            minority={**group,'value':group['value']-parent['value'],
                'qname':'derived:group_minus_parent_minority_earnings','operands':[group,parent]}
            sources['minority_income']=minority
    distributions=flow('minority_distributions',['MinorityInterestDecreaseFromDistributionsToNoncontrollingInterestHolders',
                                               'PaymentsOfDividendsToNoncontrollingInterest'],True)
    if any(r is not None and r['period_start']!=revenue['period_start'] for r in (lease,minority,distributions)):
        raise ValueError('outside-owner cash allocation period differs')
    minority_book=fact(packet,['MinorityInterest'],optional=True)
    if minority is None and (minority_book is not None and minority_book['value']>0):
        raise ValueError('minority cash allocation lacks a current earnings/distribution basis')
    if minority is None:
        assets=fact(packet,['Assets']);liabilities_total=fact(packet,['Liabilities'])
        if not isclose(assets['value']-liabilities_total['value'],state['parent_equity'],rel_tol=1e-5,abs_tol=1000):
            raise ValueError('outside-owner balance allocation unresolved')
        sources['outside_equity_proof']={'assets':assets,'liabilities':liabilities_total,'parent':state['sources']['parent_equity']}
    reserve=max(minority['value'] if minority else 0.,distributions['value'] if distributions else 0.,0.)
    rev,factor=annualize(revenue);cash=cfo['value']*factor
    spending=(capex['value']+(intangible['value'] if intangible else 0.))*factor
    owners=(sbc['value']+reserve+(lease['value'] if lease else 0.))*factor
    if cash-spending-owners<=0:raise ValueError('nonpositive current owner cash requires an operating/funding recovery forecast')
    previous=date.fromisoformat(filing['reportDate'])
    try:prior_end=previous.replace(year=previous.year-1).isoformat()
    except ValueError:raise ValueError('nonstandard comparative cash calendar')
    prior=fact(packet,[revenue['qname'].split(':')[-1]],flow=True,end=prior_end)
    if prior['value']<=0 or date.fromisoformat(prior['period_start']).replace(year=date.fromisoformat(prior['period_start']).year+1).isoformat()!=revenue['period_start']:
        raise ValueError('aligned positive comparative revenue unavailable')
    sources['prior_revenue']=prior
    a=policy['assumptions']
    if a['funding']!=DEFAULTS['funding'] or a['growth_investment'] not in {LEGACY_GROWTH_RULE,REVISED_GROWTH_RULE} or a['sbc']!=DEFAULTS['sbc']:
        raise ValueError('unsupported cash funding/reinvestment policy')
    growth=max(a['growth_limits'][0],min(a['growth_limits'][1],revenue['value']/prior['value']-1))
    schedules={};specs={}
    for i,name in enumerate(('bear','base','bull')):
        rate=a['cost_of_equity'][i];g=a['terminal_growth'][i]
        if rate<=g or not 0<=g<.05:raise ValueError('invalid cash discount/terminal relationship')
        current=rev;schedule=[];flows=[];initial_growth=max(a['growth_limits'][0],min(a['growth_limits'][1],growth+a['growth_delta'][i]))
        cash_margin=(cash-owners)/rev*a['cash_margin_multiplier'][i]
        capex_margin=spending/rev*a['capex_multiplier'][i]
        # Recorded legacy recipes retain their reserve. Revised recipes deduct
        # total capex and add only a separately reviewed incremental cash plan.
        for year in range(1,a['years']+1):
            forecast_growth=initial_growth+(g-initial_growth)*(year-1)/max(1,a['years']-1)
            following=current*(1+forecast_growth)
            investment=incremental_reinvestment(a,current_revenue=current,next_revenue=following,
                common_equity=state['equity'],initial_revenue=rev,scenario=name,year=year)
            available=following*(cash_margin-capex_margin)-investment
            schedule.append({'year':year,'revenue':following,'cash_after_interest_and_owner_costs':following*cash_margin,
                'total_capex':following*capex_margin,'additional_growth_investment':investment,'cash_to_common':available})
            flows.append(available);current=following
        terminal_extra=incremental_reinvestment(a,current_revenue=current,next_revenue=current*(1+g),
            common_equity=state['equity'],initial_revenue=rev,scenario=name,terminal_growth=g)
        terminal=current*(1+g)*(cash_margin-capex_margin)-terminal_extra
        if terminal<=0:raise ValueError('nonpositive terminal common cash needs a funding forecast')
        contingency=state['equity']*policy.get('contingency_fraction',[0.,0.,0.])[i]
        specs[name]={'engine':'cash_schedule','inputs':{'cash_flows':flows,'terminal_cash_flow':terminal,
            'discount_rate':rate,'terminal_growth':g,'net_bridge':-contingency,'shares':state['shares']}}
        schedules[name]={'schedule':schedule,'terminal_cash_flow':terminal,'contingency_reserve':contingency,
                         'initial_growth':initial_growth,'cash_margin_multiplier':a['cash_margin_multiplier'][i],
                         'capex_multiplier':a['capex_multiplier'][i]}
    version=SCHEMA if a['growth_investment']==LEGACY_GROWTH_RULE else REINVESTMENT_VERSION
    recipe={'schema_version':'FINSIGHT-CALCULATION-RECIPE-1','ticker':policy['ticker'],'recipe_version':version,
        'model_version':version,'evidence_cutoff':cutoff,'source_accession':filing['accessionNumber'],
        'editable':{},'scenarios':specs,'cash_policy':deepcopy(policy)}
    valued=evaluate_recipe(recipe)
    ledger={'controlling_filing':filing,'policy_version':version,'recipe_engine':'operating_equity_cash',
        'sources':sources,'forecast':schedules,'state':state,'table_audit':audit,'continuing_cash_bridge':cash_bridge,
        'normalization':{'method':('reported after-interest cash margins, total capital spending and equity-funded incremental growth' if a['growth_investment']==LEGACY_GROWTH_RULE else 'reported after-interest cash margins and total capex; only reviewed additional reinvestment'),
        'limitations':['Provisional cash forecast; current cash margins and bounded revenue growth are assumptions, not analyst forecasts.',
            'Bear/base/bull cash-margin multipliers are '+str(a['cash_margin_multiplier'])+'; total-capex multipliers are '+str(a['capex_multiplier'])+'.',
            'Initial revenue growth uses the reported comparable period, bounded by '+str(a['growth_limits'])+' with scenario changes '+str(a['growth_delta'])+'; it fades to scenario terminal growth '+str(a['terminal_growth'])+'.',
            'Existing debt maturities are assumed refinanced with no net new borrowing; interest costs remain inside reported operating cash.',
            'Current SBC expense is deducted as an economic cash-cost proxy; no additional generic dilution multiplier is applied.',
            'Minority allocation uses the higher of reported earnings and distributions as a provisional cash-cost proxy; actual future distributions may differ.',
            ('Reported total capital spending remains in the forecast; incremental growth receives an additional conservative common-book capital allowance.' if a['growth_investment']==LEGACY_GROWTH_RULE else 'Forecast total capital spending is retained. Additional investment is charged only through a reviewed plan incremental to that spending. Future capex adequacy remains a forecast assumption.'),
            'No separate excess-cash addition or gross-debt deduction is applied to this after-interest equity model.',
            'Finance lease principal is deducted when reported; unquantified positive finance-lease exposure prevents migration.']}}
    if cash_bridge and cash_bridge.get('allocation_policy'):
        ledger['normalization']['limitations'].append(
            'Continuing operating cash is estimated by continuing revenue share with equal cash conversion. Exact reconciled inputs are retained; other reported group costs are retained as conservative budgets. Tax, working-capital and disposal effects can make this allocation inaccurate; reliability is Low.')
    return recipe,valued,ledger


def bind_cash_recipe(entry,recipe,packet,cutoff):
    policy=deepcopy(entry['refresh_policy'])
    if recipe['ticker']!=entry['ticker'] or policy['ticker']!=entry['ticker'] or str(policy['cik']).zfill(10)!=str(entry['cik']).zfill(10):
        raise ValueError('cash refresh identity mismatch')
    policy['evidence_cutoff']=cutoff
    updated,_,ledger=build_cash_recipe(packet,policy)
    updated['recipe_version']=updated['model_version']+'-'+sha256_bytes(canonical_json_bytes(updated))[:16]
    return updated,ledger
