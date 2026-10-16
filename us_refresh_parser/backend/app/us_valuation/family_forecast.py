"""Reusable private equity forecasts and source bindings; no ticker branches."""
from copy import deepcopy
from datetime import date
from math import isfinite, isclose
from statistics import median
import re

from .calculation_recipe import evaluate_recipe
from .catalog import canonical_json_bytes, sha256_bytes
from .table_first import inspect_tables, project_table_facts
from .xbrl import CompanyFactsNormalizer, load_concept_config

SCHEMA = 'US-FAMILY-FORECAST-1'
CONTINUING_DIMENSIONS = [['us-gaap:StatementOperatingActivitiesSegmentAxis', 'us-gaap:SegmentContinuingOperationsMember']]
DEFAULTS = {
    'years': 5, 'cost_of_equity': [.14, .12, .10],
    'terminal_growth': [0., .01, .02], 'roe_multiplier': [.65, 1., 1.25],
    'payout_ratio': .30, 'terminal_roe_cap': .20,
    'dilution_multiplier': [1.05, 1.02, 1.],
    'extra_contingency_equity_fraction': [.10, .025, 0.],
}


def fact(packet, concepts, *, flow=False, end=None, optional=False, shortest=False, dimensions=None):
    filing=packet['controlling_filing'];end=end or filing['reportDate']
    cik=str(packet['submissions']['cik']).zfill(10)
    structure=packet.get('structural_packets',{}).get(filing['accessionNumber']) or packet['structural_filing']
    for name in concepts:
        rows=[r for r in structure['facts'] if r.get('local_name')==name and (r.get('dimensions') or [])==(dimensions or [])
              and re.fullmatch(r'https?://fasb.org/us-gaap/20\d{2}',str(r.get('namespace','')))
              and r.get('period_end')==end and bool(r.get('period_start'))==flow
              and r.get('source_accession')==filing['accessionNumber']
              and str(r.get('entity_identifier','')).zfill(10)==cik
              and r.get('entity_scheme')=='http://www.sec.gov/CIK']
        if not rows:continue
        if flow:
            start=(max if shortest else min)(r['period_start'] for r in rows);rows=[r for r in rows if r['period_start']==start]
        unit='shares' if 'Shares' in name else 'USD'
        if any(str(r.get('unit','')).removeprefix('xbrli:')!=unit or not isinstance(r['value'],(int,float))
               or isinstance(r['value'],bool) or not isfinite(r['value']) for r in rows):
            raise ValueError('invalid source unit/value: '+name)
        def radius(r):
            return 0. if str(r.get('decimals','INF'))=='INF' else .5*10**-int(r['decimals'])
        if max(r['value']-radius(r) for r in rows)>min(r['value']+radius(r) for r in rows):
            raise ValueError('conflicting source facts: '+name)
        r=min(rows,key=radius)
        return {k:r.get(k) for k in ('value','qname','period_start','period_end','unit','source_accession','context_id','dimensions')}
    if optional:return None
    raise ValueError('missing essential input: '+' / '.join(concepts))


def annualize(row):
    start=date.fromisoformat(row['period_start']);end=date.fromisoformat(row['period_end'])
    days=(end-start).days+1
    if not 75<=days<=385:raise ValueError('unsupported earnings duration')
    months=(end.year-start.year)*12+end.month-start.month+1
    factor=12/months if start.day==1 and months in (3,6,9,12) else 365.25/days
    return row['value']*factor, factor


def common_class_par(packet):
    """Aggregate disjoint standard common classes; reconciliation proves scope."""
    filing=packet['controlling_filing'];cik=str(packet['submissions']['cik']).zfill(10)
    structure=packet.get('structural_packets',{}).get(filing['accessionNumber']) or packet['structural_filing']
    grouped={}
    for r in structure['facts']:
        dims=r.get('dimensions',[])
        if (r.get('qname')!='us-gaap:CommonStockValue' or len(dims)!=1
            or not re.fullmatch(r'https?://fasb.org/us-gaap/20\d{2}',str(r.get('namespace','')))
            or r.get('entity_scheme')!='http://www.sec.gov/CIK'
            or dims[0][0]!='us-gaap:StatementClassOfStockAxis'
            or not re.fullmatch(r'us-gaap:CommonClass[A-Z]Member',dims[0][1])
            or r.get('period_end')!=filing['reportDate'] or r.get('period_start')
            or r.get('source_accession')!=filing['accessionNumber']
            or str(r.get('entity_identifier','')).zfill(10)!=cik):continue
        if r.get('unit')!='USD' or not isfinite(r['value']):raise ValueError('invalid common-class par fact')
        grouped.setdefault(dims[0][1],[]).append(r)
    if not grouped:return None
    selected=[]
    for rows in grouped.values():
        def radius(r):return 0 if str(r.get('decimals','INF'))=='INF' else .5*10**-int(r['decimals'])
        if max(r['value']-radius(r) for r in rows)>min(r['value']+radius(r) for r in rows):raise ValueError('conflicting common-class par facts')
        r=min(rows,key=radius)
        selected.append({k:r.get(k) for k in ('value','qname','unit','dimensions','context_id','source_accession','period_end')})
    return {'value':sum(r['value'] for r in selected),'qname':'derived:common_class_par','operands':selected}


def continuing_income(packet, *, shortest=False, end=None):
    continuing_parent=fact(packet,['IncomeLossFromContinuingOperationsAttributableToParent'],flow=True,
                           optional=True,shortest=shortest,end=end)
    if continuing_parent is not None:
        return continuing_parent
    parent=fact(packet,['NetIncomeLoss'],flow=True,optional=True,shortest=shortest,end=end)
    disposed=fact(packet,['IncomeLossFromDiscontinuedOperationsNetOfTaxAttributableToReportingEntity',
                         'IncomeLossFromDiscontinuedOperationsNetOfTaxAttributableToParent'],flow=True,optional=True,shortest=shortest,end=end)
    if parent is not None and disposed is not None:
        operands=[parent,disposed]
    else:
        group=fact(packet,['IncomeLossFromContinuingOperationsIncludingPortionAttributableToNoncontrollingInterest'],flow=True,shortest=shortest,end=end,optional=True)
        minority=fact(packet,['IncomeLossFromContinuingOperationsAttributableToNoncontrollingEntity'],flow=True,shortest=shortest,end=end,optional=True)
        if group is None or minority is None:
            common=fact(packet,['NetIncomeLossAvailableToCommonStockholdersBasic'],flow=True,
                        shortest=shortest,end=end,dimensions=CONTINUING_DIMENSIONS)
            return {**common,'attributable_to_common':True}
        operands=[group,minority]
    if operands[0]['period_start']!=operands[1]['period_start']:raise ValueError('continuing earnings periods differ')
    return {**operands[0],'value':operands[0]['value']-operands[1]['value'],
            'qname':'derived:continuing_parent_earnings','operands':operands}


def common_state(packet, *, requires_continuing=False):
    sources={}
    def get(key,names,**kwargs):
        row=fact(packet,names,**({**kwargs,'optional':True} if names==['CommonStockValue'] else kwargs))
        if row is None and names==['CommonStockValue']:row=common_class_par(packet)
        if row is None and not kwargs.get('optional'):raise ValueError('missing essential input: '+' / '.join(names))
        if row is not None:sources[key]=row
        return row['value'] if row is not None else None
    parent=get('parent_equity',['StockholdersEquity'],optional=True)
    if parent is None:
        group=get('group_equity',['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'])
        nci=get('nci',['MinorityInterest'],optional=True)
        if nci is not None:parent=group-nci
    preferred=get('preferred_book',['PreferredStockValue'],optional=True)
    preferred_shares=get('preferred_shares',['PreferredStockSharesOutstanding','PreferredStockSharesIssued'],optional=True)
    if preferred_shares is not None and preferred_shares>0 and (preferred is None or preferred<=0):
        raise ValueError('positive preferred shares have an unresolved economic claim')
    if preferred is None and preferred_shares==0:preferred=0.
    if parent is None:
        par=get('common_par',['CommonStockValue'])
        apic=get('common_apic',['AdditionalPaidInCapitalCommonStock','AdditionalPaidInCapital'])
        retained=get('retained_earnings',['RetainedEarningsAccumulatedDeficit'])
        aoci=get('aoci',['AccumulatedOtherComprehensiveIncomeLossNetOfTax'],optional=True)
        treasury=get('treasury',['TreasuryStockValue','TreasuryStockCommonValue'],optional=True)
        if preferred is None or not isclose(par+apic+retained+(aoci or 0)-(treasury or 0)+preferred,group,rel_tol=1e-5,abs_tol=1):
            raise ValueError('parent/minority equity allocation does not reconcile')
        parent=group
    if preferred is None:
        combined=get('common_paid_capital',['CommonStocksIncludingAdditionalPaidInCapital'],optional=True)
        if combined is None:
            par=get('common_par',['CommonStockValue'],optional=True)
            apic=get('common_apic',['AdditionalPaidInCapitalCommonStock','AdditionalPaidInCapital'],optional=True)
            if par is not None:combined=par+(apic or 0)
        retained=get('retained_earnings',['RetainedEarningsAccumulatedDeficit'],optional=True)
        aoci=get('aoci',['AccumulatedOtherComprehensiveIncomeLossNetOfTax'],optional=True)
        treasury=get('treasury',['TreasuryStockValue','TreasuryStockCommonValue'],optional=True)
        if combined is not None and retained is not None:
            subtotal=combined+retained+(aoci or 0)-(treasury or 0)
            if isclose(subtotal,parent,rel_tol=1e-5,abs_tol=1):preferred=0.
        if preferred is None:raise ValueError('common-equity/preferred scope does not reconcile')
    equity=parent-preferred
    if equity<=0:raise ValueError('nonpositive reported common equity')
    if preferred>0:
        capital=get('common_paid_capital',['CommonStocksIncludingAdditionalPaidInCapital'],optional=True)
        if capital is None:
            capital=get('common_par',['CommonStockValue'])+get('common_apic',['AdditionalPaidInCapitalCommonStock','AdditionalPaidInCapital'])
        retained=get('retained_earnings',['RetainedEarningsAccumulatedDeficit'])
        aoci=get('aoci',['AccumulatedOtherComprehensiveIncomeLossNetOfTax'],optional=True)
        treasury=get('treasury',['TreasuryStockValue','TreasuryStockCommonValue'],optional=True)
        if not isclose(capital+retained+(aoci or 0)-(treasury or 0),equity,rel_tol=1e-5,abs_tol=1):
            raise ValueError('preferred book allocation does not reconcile to common-equity components')
    disposed=fact(packet,['IncomeLossFromDiscontinuedOperationsNetOfTaxAttributableToReportingEntity',
                          'IncomeLossFromDiscontinuedOperationsNetOfTaxAttributableToParent'],flow=True,optional=True)
    continuing=requires_continuing or (disposed is not None and disposed['value']!=0)
    earnings_row=continuing_income(packet) if continuing else fact(packet,['NetIncomeLossAvailableToCommonStockholdersBasic'],flow=True,optional=True)
    if earnings_row is None:
        earnings_row=fact(packet,['NetIncomeLoss'],flow=True)
        if preferred>0:
            prefdiv=fact(packet,['PreferredStockDividendsIncomeStatementImpact'],flow=True)
            if prefdiv['period_start']!=earnings_row['period_start']:raise ValueError('preferred earnings periods differ')
            sources['preferred_income_charge']=prefdiv
            earnings_row={**earnings_row,'value':earnings_row['value']-prefdiv['value']}
    elif continuing and preferred>0 and not earnings_row.get('attributable_to_common'):
        prefdiv=fact(packet,['PreferredStockDividendsIncomeStatementImpact'],flow=True)
        if prefdiv['period_start']!=earnings_row['period_start']:raise ValueError('preferred earnings periods differ')
        sources['preferred_income_charge']=prefdiv
        earnings_row={**earnings_row,'value':earnings_row['value']-prefdiv['value']}
    sources['common_earnings']=earnings_row
    earnings,factor=annualize(earnings_row)
    shares=get('shares',['WeightedAverageNumberOfDilutedSharesOutstanding'],flow=True,optional=True)
    if shares is None and continuing:
        shares=get('shares',['WeightedAverageNumberOfDilutedSharesOutstanding'],flow=True,dimensions=CONTINUING_DIMENSIONS)
    if shares is None:raise ValueError('missing essential input: diluted common share denominator')
    if shares<=0:raise ValueError('invalid share denominator')
    share_source=sources['shares']
    if (share_source['period_start'],share_source['period_end']) != (earnings_row['period_start'],earnings_row['period_end']):
        raise ValueError('common earnings and diluted share periods differ')
    return {'equity':equity,'parent_equity':parent,'preferred':preferred,'earnings':earnings,
            'shares':shares,'annualization_factor':factor,'sources':sources,'continuing_scope':continuing}


def mandatory_conversion_state(packet,state,terms):
    """Conservative maximum-dilution treatment of a source-defined instrument."""
    if terms.get('kind')!='mandatory_common_conversion':raise ValueError('unsupported capital transformation')
    cik=str(packet['submissions']['cik']).zfill(10)
    if str(terms['cik']).zfill(10)!=cik:raise ValueError('conversion terms issuer mismatch')
    maximum=terms['maximum_common_per_preferred'];minimum=terms['minimum_common_per_preferred']
    coupon=terms['quarterly_cash_dividend_per_preferred']
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) for v in (minimum,maximum,coupon)):
        raise ValueError('nonfinite or invalid conversion terms')
    if not 0<minimum<=maximum or coupon<0:raise ValueError('invalid conversion terms')
    months=terms['payment_months']
    if len(months)!=4 or months!=sorted(set(months)) or any(not 1<=m<=12 for m in months):
        raise ValueError('invalid quarterly dividend calendar')
    filing=packet['controlling_filing'];period=date.fromisoformat(filing['reportDate'])
    conversion=date.fromisoformat(terms['mandatory_date'])
    preferred=fact(packet,['PreferredStockSharesOutstanding','PreferredStockSharesIssued'])
    if preferred['value']==0 and state['preferred']==0:return state
    if preferred['value']<=0:raise ValueError('invalid outstanding preferred share count')
    if period>=conversion:raise ValueError('scheduled conversion status needs current confirmation')
    structure=packet.get('structural_packets',{}).get(filing['accessionNumber']) or packet['structural_filing']
    covers=[r for r in structure['facts'] if r.get('local_name')=='EntityCommonStockSharesOutstanding'
            and re.fullmatch(r'https?://xbrl.sec.gov/dei/20\d{2}(q[1-4])?',str(r.get('namespace','')))
            and not r.get('dimensions') and r.get('source_accession')==filing['accessionNumber']
            and str(r.get('entity_identifier','')).zfill(10)==cik
            and r.get('entity_scheme')=='http://www.sec.gov/CIK'
            and filing['reportDate']<=r.get('period_end','')<=filing['filingDate']]
    if not covers:raise ValueError('current common shares for conversion are missing')
    latest=max(r['period_end'] for r in covers);covers=[r for r in covers if r['period_end']==latest]
    if len({r['value'] for r in covers})!=1 or any(str(r['unit']).removeprefix('xbrli:')!='shares'
            or isinstance(r['value'],bool) or not isinstance(r['value'],(int,float))
            or not isfinite(r['value']) or r['value']<=0 for r in covers):
        raise ValueError('common cover-share evidence conflicts')
    cover=covers[0]
    compensation=fact(packet,['IncrementalCommonSharesAttributableToShareBasedPaymentArrangements'],flow=True)
    observed=fact(packet,['IncrementalCommonSharesAttributableToConversionOfPreferredStock'],flow=True)
    if compensation['value']<0 or observed['value']<0:raise ValueError('invalid incremental dilution facts')
    maximum_shares=preferred['value']*maximum
    if observed['value']>maximum_shares*1.001:raise ValueError('reported conversion shares exceed reviewed conversion terms')
    payments=[]
    for year in range(period.year,conversion.year+1):
        for month in terms['payment_months']:
            payment=date(year,month,terms['payment_day'])
            if period<payment<=conversion:payments.append({'date':payment.isoformat(),'amount':preferred['value']*coupon})
    reserve=sum(r['amount'] for r in payments)
    parent_income=fact(packet,['NetIncomeLoss'],flow=True)
    earnings,factor=annualize(parent_income)
    result=deepcopy(state)
    result.update(equity=state['parent_equity']-reserve,preferred=0.,earnings=earnings,
                  shares=cover['value']+maximum_shares+compensation['value'],annualization_factor=factor,
                  capital_treatment='as_if_mandatory_converted',conversion={
                      'terms':terms,'preferred_shares':preferred,'common_cover_shares':{k:cover.get(k) for k in ('value','qname','period_end','unit','source_accession','context_id')},
                      'incremental_compensation':compensation,'reported_conversion_proxy':observed,
                      'maximum_conversion_shares':maximum_shares,'remaining_dividends':payments,
                      'undiscounted_dividend_reserve':reserve,'preferred_principal_deducted':False})
    result['sources']['common_earnings']=parent_income
    if result['equity']<=0:raise ValueError('converted common capital is exhausted')
    return result


def matched_earnings_anchor(packet, state, policy):
    """Match historical common earnings to average common capital, never today's book.

    Changed scopes and preferred transformations use current scoped earnings;
    historical parent equity cannot silently stand in for historical common equity.
    No unsupported expense addbacks or analyst-price targets enter this rule.
    """
    config=load_concept_config()
    config['fields']['anchor_income']={'kind':'flow','unit':'USD','concepts':['NetIncomeLossAvailableToCommonStockholdersBasic','NetIncomeLoss']}
    config['fields']['anchor_book']={'kind':'instant','unit':'USD','concepts':['StockholdersEquity']}
    config['fields']['anchor_preferred']={'kind':'instant','unit':'USD','concepts':['PreferredStockValue']}
    n=CompanyFactsNormalizer(packet['companyfacts'],concept_config=config,as_of_date=policy['evidence_cutoff'])
    current=state['earnings']/state['equity']; history=[]; ratios=[]
    # Explicit common numerator + source-proven zero preferred at both endpoints
    # keeps book and profit attributable to the same owners.
    scoped=state['continuing_scope'] or policy.get('current_scope_only') or state.get('conversion') or state['preferred']>0
    if not scoped:
        books={r.end:r for r in n.annual_instant_series('anchor_book',7)}
        prefs={r.end:r for r in n.annual_instant_series('anchor_preferred',7)}
        for income in n.annual_series('anchor_income',3):
            from datetime import timedelta
            start=(date.fromisoformat(income.start)-timedelta(days=1)).isoformat()
            endpoints=[start,income.end]
            if not all(d in books and d in prefs and prefs[d].value==0 and books[d].value>0 for d in endpoints):continue
            average=sum(books[d].value for d in endpoints)/2
            ratio=income.value/average;ratios.append(ratio)
            history.append({'method':'matched_average_common_equity','income':income.as_dict(),
                            'equity':[books[d].as_dict() for d in endpoints],
                            'preferred':[prefs[d].as_dict() for d in endpoints],
                            'average_common_equity':average,'roe':ratio})
    target=median([*ratios,current]) if ratios else current
    history.append({'method':'current_scoped_earnings_anchor','annualization_factor':state['annualization_factor'],
                    'source':state['sources']['common_earnings'],'roe':current,
                    'historical_pairs':len(ratios),'historical_scope_excluded':bool(scoped)})
    if target<=0 and current>0:
        history.append({'method':'current_profit_recovery_anchor','historical_median_roe':target})
        target=current
    if target<=0 and state['continuing_scope'] and state['preferred']==0:
        quarter=continuing_income(packet,shortest=True)
        amount,factor=annualize(quarter)
        target=amount/state['equity']
        history.append({'method':'latest_quarter_recovery_anchor','source':quarter,'annualization_factor':factor})
    if target<=0:raise ValueError('positive scope-matched earnings anchor unavailable; operating normalization required')
    # Preserve observed historical loss stress even when capital history is
    # insufficient for estimating historical ROE. This is a downside assumption,
    # explicitly not a period-matched profitability observation.
    if not scoped and current>0 and not any(r.get('method')=='current_profit_recovery_anchor' for r in history):
        loss_rows=n.annual_series('anchor_income',5)
        if loss_rows and median(r.value for r in loss_rows)<0:
            history.append({'method':'current_profit_recovery_anchor',
                            'historical_median_roe':median(r.value for r in loss_rows)/state['equity'],
                            'interpretation':'historical absolute loss repeated against current capital; downside stress, not historical ROE',
                            'sources':[r.as_dict() for r in loss_rows]})
    return min(target,policy['assumptions']['terminal_roe_cap']),history


def earnings_anchor(packet,state,policy):
    if state.get('earnings_normalization'):
        target=state['earnings']/state['equity']
        if target<=0:raise ValueError('normalized earnings still require an operating recovery forecast')
        return min(target,policy['assumptions']['terminal_roe_cap']),[{'method':'source_reconciled_current_earnings',
            'normalization':state['earnings_normalization']}]
    anchor=policy.get('earnings_anchor_version','legacy')
    if anchor=='matched_common_roe_v2':return matched_earnings_anchor(packet,state,policy)
    if anchor!='legacy':raise ValueError('unsupported earnings anchor version')
    """Use retained same-business history where applicable; no three-year gate."""
    config=deepcopy(load_concept_config())
    concepts=['NetIncomeLossAvailableToCommonStockholdersBasic']
    if state['preferred']==0:concepts.append('NetIncomeLoss')
    if state.get('capital_treatment')=='as_if_mandatory_converted':concepts=['NetIncomeLoss']
    config['fields']['common_income']={'kind':'flow','unit':'USD','concepts':concepts}
    normalizer=CompanyFactsNormalizer(packet['companyfacts'],concept_config=config,as_of_date=policy['evidence_cutoff'])
    rows=[] if policy.get('current_scope_only') or state['continuing_scope'] else normalizer.annual_series('common_income',5)
    observations=[r.value for r in rows]
    target=median(observations) if observations else state['earnings']
    if target<=0 and observations and state['earnings']>0:
        return min(state['earnings']/state['equity'],policy['assumptions']['terminal_roe_cap']),[
            *[r.as_dict() for r in rows],
            {'method':'current_profit_recovery_anchor','historical_median_roe':target/state['equity']}]
    if state['continuing_scope'] and not policy.get('current_scope_only') and state['preferred']==0:
        from calendar import monthrange
        current=date.fromisoformat(packet['controlling_filing']['reportDate'])
        previous=current.replace(year=current.year-1,day=min(current.day,monthrange(current.year-1,current.month)[1]))
        try:
            comparable=continuing_income(packet,end=previous.isoformat())
            amount,factor=annualize(comparable)
            if isclose(factor,state['annualization_factor'],rel_tol=.03):
                target=median([amount,state['earnings']])
                if target>0:
                    return min(target/state['equity'],policy['assumptions']['terminal_roe_cap']),[
                        {'method':'same_filing_continuing_comparison','source':comparable,'annualization_factor':factor}]
        except ValueError:
            pass  # Optional comparison; current continuing earnings remain the anchor.
    if target<=0 and not observations and state['continuing_scope'] and state['preferred']==0:
        quarter=continuing_income(packet,shortest=True)
        target,factor=annualize(quarter)
        if target>0:
            return min(target/state['equity'],policy['assumptions']['terminal_roe_cap']),[
                {'method':'latest_quarter_recovery_anchor','source':quarter,'annualization_factor':factor}]
    # A recovery path needs an observed positive earnings anchor, not a floor.
    if target<=0:raise ValueError('positive sustainable-earnings anchor unavailable; explicit operating/funding forecast needed')
    return min(target/state['equity'],policy['assumptions']['terminal_roe_cap']),[r.as_dict() for r in rows]


def funding_check(packet,state,years):
    cfo=fact(packet,['NetCashProvidedByUsedInOperatingActivitiesContinuingOperations','NetCashProvidedByUsedInOperatingActivities'],flow=True,optional=True)
    capex=fact(packet,['PaymentsToAcquirePropertyPlantAndEquipment','PaymentsToAcquireProductiveAssets'],flow=True,optional=True)
    cash=fact(packet,['CashAndCashEquivalentsAtCarryingValue'],optional=True)
    if cfo is None or capex is None or cash is None:
        return {'status':'not_quantified','reason':'one or more cash-flow diagnostics missing'}
    if state['continuing_scope'] and cfo['qname'].split(':')[-1]!='NetCashProvidedByUsedInOperatingActivitiesContinuingOperations':
        return {'status':'not_quantified','reason':'continuing cash flow is not separately reported; model uses continuing parent earnings'}
    if cfo['period_start']!=capex['period_start']:raise ValueError('funding flow periods differ')
    annual_cfo,_=annualize(cfo);annual_capex,_=annualize(capex)
    # Cash is not assumed freely available; it may include operating/customer funds.
    gap=max(annual_capex-annual_cfo,0)*years
    if gap>.5*state['equity']:raise ValueError('observed investment cash deficit needs an explicit financing plan')
    return {'status':'screen_passed','flat_spending_stress_gap':gap,'sources':[cfo,capex,cash]}


def build_family_recipe(packet,policy):
    """Forecast common earnings, book retention, and residual income together."""
    if policy.get('schema_version')!=SCHEMA:raise ValueError('unsupported family policy')
    if str(packet.get('companyfacts',{}).get('cik','')).zfill(10)!=str(policy['cik']).zfill(10):
        raise ValueError('historical financial-data issuer identity mismatch')
    if policy.get('hard_gaps'):raise ValueError('; '.join(policy['hard_gaps']))
    filing=packet['controlling_filing'];cutoff=policy['evidence_cutoff']
    if filing['filingDate']>cutoff:raise ValueError('filing after cutoff')
    audit=inspect_tables(packet,cik=policy['cik'],cutoff=cutoff)
    fatal=[r for r in audit['exceptions'] if r['code'] not in {'material_business_change','continuing_scope_required'}]
    if fatal:raise ValueError('; '.join(r['detail'] for r in fatal))
    state=common_state(packet,requires_continuing=policy.get('requires_continuing_income',False));a=policy['assumptions'];years=a['years']
    if policy.get('mandatory_conversion'):
        state=mandatory_conversion_state(packet,state,policy['mandatory_conversion'])
    if policy.get('earnings_normalization'):
        from .earnings_normalization import normalize_earnings
        state=normalize_earnings(state,packet,policy['earnings_normalization'])
    if not state['continuing_scope']:
        for concept in ('DeconsolidationGainOrLossAmount','GainLossOnSaleOfBusiness',
                        'GainLossOnDispositionOfAssetsAndSaleOfBusiness','BusinessCombinationBargainPurchaseGainRecognizedAmount'):
            oneoff=fact(packet,[concept],flow=True,optional=True)
            if oneoff is not None and oneoff['period_start']==state['sources']['common_earnings']['period_start']:
                if abs(oneoff['value'])>.2*abs(state['sources']['common_earnings']['value']):
                    raise ValueError('material disposal/deconsolidation earnings need recurring-income normalization: '+concept)
    funding=funding_check(packet,state,years)
    target,history=earnings_anchor(packet,state,policy)
    specs={};schedules={}
    for index,name in enumerate(('bear','base','bull')):
        rate=a['cost_of_equity'][index];terminal_roe=target*a['roe_multiplier'][index]
        recovery=[r for r in history if r.get('method')=='current_profit_recovery_anchor']
        if index==0 and recovery:terminal_roe=recovery[0]['historical_median_roe']
        growth=terminal_roe if terminal_roe<=0 else min(a['terminal_growth'][index],terminal_roe*.5)
        reserve=state['equity']*a['extra_contingency_equity_fraction'][index] if policy['unquantified_contingency'] else 0.
        opening=state['equity']-reserve;initial_book=opening
        starting_roe=state['earnings']/state['equity']
        # Absolute losses are not improved in the bear case by a multiplier <1.
        starting_roe=starting_roe*a['roe_multiplier'][index] if starting_roe>=0 else starting_roe/a['roe_multiplier'][index]
        flows=[];schedule=[]
        for year in range(1,years+1):
            roe=starting_roe+(terminal_roe-starting_roe)*year/years
            terminal_payout=0 if terminal_roe<=0 else 1-growth/terminal_roe
            payout=a['payout_ratio']+(terminal_payout-a['payout_ratio'])*year/years
            income=opening*roe;dividends=max(income,0)*payout
            residual=income-rate*opening
            closing=opening+income-dividends
            if closing<=0:raise ValueError('forecast exhausts common capital; financing/dilution plan required')
            flows.append(residual);schedule.append({'year':year,'opening_equity':opening,'earnings':income,'dividends':dividends,'closing_equity':closing})
            opening=closing
        specs[name]={'engine':'cash_schedule','inputs':{'cash_flows':flows,
            'terminal_cash_flow':(terminal_roe-rate)*opening,'discount_rate':rate,
            'terminal_growth':growth,'net_bridge':initial_book,'shares':state['shares']*a['dilution_multiplier'][index]}}
        if index==0 and recovery:specs[name]['equity_floor']='limited_liability'
        schedules[name]={'schedule':schedule,'extra_contingency_stress':reserve,'terminal_roe':terminal_roe}
    recipe={'schema_version':'FINSIGHT-CALCULATION-RECIPE-1','recipe_version':SCHEMA,
            'ticker':policy['ticker'],'source_accession':filing['accessionNumber'],'evidence_cutoff':cutoff,
            'model_version':SCHEMA,'editable':{},'scenarios':specs,'family_policy':deepcopy(policy)}
    valued=evaluate_recipe(recipe)
    ledger={'controlling_filing':filing,'policy_version':SCHEMA,'recipe_engine':'residual_income',
            'state':state,'history':history,'forecast':schedules,'funding':funding,'table_audit':audit,
            'normalization':{'method':'parent-common equity forecast with explicit earnings recovery and clean-surplus retention',
                'limitations':['Low-reliability equity-model fallback; annualized current earnings and weighted-average diluted shares are proxies.',
                              'Terminal ROE is capped at 20%; future net OCI is assumed zero. These are explicit forecast assumptions.',
                              'Discount rates and payout/terminal rules are provisional policy assumptions, not newly observed market data.',
                              ('Scenario dilution adds 5%/2%/0% to the as-if-converted share base; it does not assume new funding proceeds.' if state.get('conversion') else 'Scenario dilution adds 5%/2%/0% to reported weighted-average diluted shares; it does not assume new funding proceeds.'),
                              *(['Mandatory preferred conversion uses current common shares plus maximum contractual conversion shares and reported incremental compensation. All dividends after the balance-sheet date through mandatory conversion are reserved without discounting; preferred principal is not deducted again. This is a conservative as-if-converted assumption.'] if state.get('conversion') else []),
                              *(['Investment cash screening is not quantified. This equity model assumes funding costs remain reflected in earnings and does not add reported cash as free cash.'] if funding['status']=='not_quantified' else []),
                              *(['Changed-business forecasts use current continuing earnings. A positive latest quarter may anchor recovery from year-to-date losses; repetition is a forecast assumption.'] if state['continuing_scope'] else []),
                              *(['Current profit anchors the recovery assumption despite negative historical median earnings; the bear case reverts to the historical loss rate and may be worth zero.'] if any(r.get('method')=='current_profit_recovery_anchor' for r in history) else []),
                              *(['Extra legal-loss stresses are 10%/2.5%/0% of common equity. They are not expected losses or exposure limits; losses and business restrictions can exceed them.'] if policy['unquantified_contingency'] else [])]}}
    return recipe,valued,ledger


def bind_family_recipe(entry,recipe,packet,cutoff):
    policy=deepcopy(entry['refresh_policy'])
    if recipe.get('ticker')!=entry['ticker'] or policy['ticker']!=entry['ticker'] or str(policy['cik']).zfill(10)!=str(entry['cik']).zfill(10):
        raise ValueError('family policy identity mismatch')
    policy['evidence_cutoff']=cutoff
    updated,_,ledger=build_family_recipe(packet,policy)
    updated['recipe_version']=SCHEMA+'-'+sha256_bytes(canonical_json_bytes(updated))[:16]
    return updated,ledger
