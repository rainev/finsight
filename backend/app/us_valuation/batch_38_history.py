"""Batch 38: source-bound operating cash and insurer equity baselines."""
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path
from .batch_38 import BATCH_38_TICKERS
from .batch_38_sources import _verify_source_bundle
from .batch_04_launch_first import _controlling
from .batch_35_history import _instant, _period_flow, _share, _source
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_08_history import _annual_cash_with_losses
from .history import HISTORY_POLICY_VERSION, build_cash_fcff_history_profile
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .baseline import BaselineValuation, AvailabilityType
from .reliability import assess_reliability
from .xbrl import load_concept_config

BATCH_38_HISTORY_VERSION='BATCH-38-HISTORY-1.0'
INSURERS={'EG','PFG','PRU','AIZ'}
DATE='2026-08-14'
PERIOD='2026-06-30'
EVENT_TREATMENTS={
 'EG':'Quarterly earnings corroborate catastrophe/reserve history; controlling 10-Q remains the financial anchor.',
 'GPN':'First full Worldpay combined quarter; Jan9 acquisition and Issuer Solutions disposal are in current statements. No second consideration overlay.',
 'PFG':'July20 AUM is client fee-scale context; July27 results corroborate 10-Q. Client AUM is not issuer equity.',
 'FIS':'Issuer Solutions acquired and Worldpay interest disposed Jan9; July9 securities settlement substantially insurer funded. Current H1 is the operating anchor.',
 'PRU':'July24 Japan customer reimbursement update and Aug4 results retained. Japan suspension and Deerpath pending acquisition are model uncertainties; no unclosed cash proceeds assumed.',
 'WTW':'July28 Propel cash costs625M are discounted as three equal payments; projected savings and authorized buybacks are not assumed executed.',
 'MA':'Quarterly results corroborate operating facts; recorded litigation296M charged and unresolved legal tail remains outside operating range.',
 'CME':'August11 pricing-change announcement accepted as qualitative forward uncertainty; no quantified revenue uplift is assumed.',
 'CPAY':'July22 performance share grants and FTC preliminary settlement plus Maintenance disposal reviewed. Customer funding attribution remains unresolved; no numeric publication.',
 'AIZ':'Quarterly results corroborate reserve development and catastrophe facts; no further post-quarter financing overlay identified.',
}

def events(ticker,root,verification):
    path=Path(root)/ticker/'inventory.json'
    entries=json.loads(path.read_text())
    for entry in entries:
        if entry['filed']>DATE:raise ValueError('event after cutoff')
        for doc in entry['documents']:
            p=Path(doc['path'])
            if not p.is_absolute():p=Path(root).parent.parent/p
            if hashlib.sha256(p.read_bytes()).hexdigest()!=doc['sha256']:raise ValueError('event hash mismatch')
        entry['decision']='accepted_context' if ticker in {'PRU','WTW','CME','CPAY'} else 'rejected_as_separate_overlay'
        entry['treatment']=EVENT_TREATMENTS[ticker]
    return {'screened_filings':entries,'inventory_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_manifest_sha256':verification['source_manifest_sha256'],'treatment':EVENT_TREATMENTS[ticker]}

def point(st,name):return _instant(st,(name,),PERIOD)

def withheld(ticker,filing,reason,ledger):
    invalid='Revalue when source-supported operating cash, financing and share economics support a positive common-equity base.'
    baseline=BaselineValuation(ticker=ticker,method='payments_operating_fcff',method_version=BATCH_38_HISTORY_VERSION,low=None,base=None,high=None,confidence=None,availability_type=AvailabilityType.NOT_AVAILABLE,warnings=(reason,invalid))
    return {'ticker':ticker,'method':baseline.method,'model_version':BATCH_38_HISTORY_VERSION,'availability_type':'not_available','scenario_rows':[],'scenario_range':{'low':None,'base':None,'high':None},'reported_inputs':{},'history_reliability':None,'governed_assumptions':{'history_policy_version':HISTORY_POLICY_VERSION,'history_years_used':0,'forecast_years':8,'normalization_basis':'no_positive_current_state_equity_base','assumption_source_mix':'reported_current_filing','invalidation':invalid},'source_ledger':{'controlling_filing':filing,**ledger},'warning':reason,'baseline':baseline.as_private_dict()}

def operating(ticker,sub,facts,st,filing):
    config=copy.deepcopy(load_concept_config())
    if ticker=='CME':config['fields']['interest_expense']['concepts']=['InterestAndDebtExpense']
    if ticker=='MA':config['fields']['software_development']['concepts']=['PaymentsToAcquireSoftware']
    if ticker=='FIS':config['fields']['software_development']['concepts']=['PaymentsForSoftware']
    norm=_normalizer(sub,facts,concept_config=config)
    flows={k:norm.ttm_flow(k) for k in ('revenue','operating_cash_flow','capital_expenditures','interest_expense')}
    if any(v['period_end']!=PERIOD for v in flows.values()):raise ValueError(ticker+': stale TTM')
    tax,tax_sources=_normalized_tax_rate(norm)
    extra=norm.ttm_flow('software_development') if ticker in {'MA','FIS'} else None
    capex=flows['capital_expenditures']['value']+(extra['value'] if extra else 0.)
    fcff=cash_fcff_from_reported(operating_cash_flow=flows['operating_cash_flow']['value'],capital_expenditures=capex,spectrum_investment=0.,interest_expense=abs(flows['interest_expense']['value']),tax_rate=tax)
    annual=list(_annual_cash_with_losses(norm)[2])
    if extra:
        for row in annual:
            software=norm.annual_at_end('software_development',row['period_end'])
            if software is None:raise ValueError(ticker+': annual software cash absent')
            row['software_capex']=software.as_dict();row['cash_fcff']-=software.value
            row['formula']='OCF - PP&E - capitalized software + after-tax interest'
    profile=build_cash_fcff_history_profile(annual_cash_states=annual,ttm_revenue=flows['revenue']['value'],ttm_cash_fcff=fcff,ttm_period_end=PERIOD,ttm_sources=[s for f in flows.values() for s in f['sources']],valuation_date=DATE)
    metric=profile.metric('cash_conversion_margin')
    if metric is None:raise ValueError(ticker+': no cash history')
    revenue=flows['revenue']['value'];starting=[revenue*x for x in (metric.low,metric.base,metric.high)]
    scope=f'{len(annual)} annual periods plus reported TTM cash conversion.'
    if ticker in {'GPN','FIS'}:
        h1={k:_period_flow(st,(v['current_ytd']['concept'],),PERIOD,target_days=180) for k,v in flows.items()}
        h1_software=_period_flow(st,('PaymentsForSoftware',),PERIOD,target_days=180) if ticker=='FIS' else None
        current=2*(h1['operating_cash_flow']['value']-h1['capital_expenditures']['value']-(h1_software['value'] if h1_software else 0.)+h1['interest_expense']['value']*(1-tax))
        starting=[current*x for x in (.7,1.,1.25)]
        scope='Post-January-9 combined H1 annualization; pre-swap annual/TTM history is diagnostic only. Annualization and 70%/100%/125% cash factors are governed assumptions, not a full comparable year.'
        flows['combined_h1']={'flows':h1,'software':h1_software,'annualized_cash_fcff':current}
    bridge=[]
    def add(name):
        r=point(st,name);bridge.append(r);return r['value']
    cash=add('CashAndCashEquivalentsAtCarryingValue')
    if ticker!='MA':
        preferred_issued=_instant(st,('PreferredStockSharesIssued',),PERIOD,unit='xbrli:shares')
        bridge.append(preferred_issued)
        if preferred_issued['value']!=0:raise ValueError(ticker+': preferred claim unresolved')
    else:
        bridge.append({'source_kind':'controlling_balance_sheet_scope','accession':filing['accession'],'locator':'Stockholders equity presents Class A and Class B common stock only; no preferred class','period_end':PERIOD,'reported_vs_estimated':'reported_statement_scope'})
    if ticker=='GPN':
        cash=1_697_900_000.
        bridge.append({'source_kind':'controlling_filing_narrative','accession':filing['accession'],'period_end':PERIOD,'unit':'USD','value':cash,'locator':'MD&A Liquidity: available cash excludes settlement cash, merchant reserves and customer funds','reported_vs_estimated':'reported_rounded'})
        debt=add('LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities');claims=add('MinorityInterest')+add('RedeemableNoncontrollingInterestEquityCarryingAmount')
    elif ticker=='FIS':
        debt=add('LongTermDebtNoncurrent')+add('LongTermDebtCurrent')+add('ShortTermBorrowings');claims=add('MinorityInterest')
        reserve=max(0.,add('SettlementLiabilitiesCurrent')-add('SettlementAssetsCurrent'));cash-=reserve
    elif ticker=='WTW':
        debt=add('LongTermDebtNoncurrent')+add('LongTermDebtCurrent');claims=add('MinorityInterest')
        add('FundsHeldForClients')
        pension=add('PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent')+add('PensionAndOtherPostretirementAndPostemploymentBenefitPlansLiabilitiesCurrent')
        # Full deficit is a conservative additional claim; normal pension contributions remain in cash history.
        claims+=pension
    elif ticker=='MA':
        debt=add('LongTermDebtNoncurrent')+add('LongTermDebtCurrent');claims=max(0.,add('MinorityInterest'))
        cash+=add('AvailableForSaleSecuritiesDebtSecurities')
        reserve=max(0.,add('SettlementDueToCustomers')-add('SettlementDueFromCustomers'));cash-=reserve
        claims+=296_000_000.
        bridge.append({'source_kind':'controlling_balance_sheet','accession':filing['accession'],'period_end':PERIOD,'unit':'USD','value':296_000_000.,'locator':'Accrued litigation','reported_vs_estimated':'reported'})
    elif ticker=='CME':
        debt=add('UnsecuredLongTermDebt')+add('FinanceLeaseLiability');claims=0.
        cash+=add('MarketableSecuritiesCurrent')
        assets=add('GoodFaithAndMarginDepositsWithBrokerDealers');liabs=add('MarginDepositsAndGuarantyFundsLiabilitiesCurrent')
        if assets!=liabs:raise ValueError('CME clearing collateral mismatch')
    else:raise ValueError(ticker)
    weighted=_period_flow_shares(st)
    try:current_shares=_share(st,facts,PERIOD)['value']
    except ValueError:current_shares=weighted['value']
    if ticker=='MA':
        class_rows=[r for r in st['facts'] if r.get('local_name')=='EntityCommonStockSharesOutstanding' and r.get('unit')=='xbrli:shares' and PERIOD<=r.get('period_end','')<=DATE]
        current_shares=sum(r['value'] for r in class_rows)
    shares=(max(current_shares,weighted['value'])*1.01,max(current_shares,weighted['value']),current_shares)
    bridge.append(weighted)
    growth=(-.02,.02,.05);wacc=(.115,.10,.09);tg=(0.,.015,.02)
    traces={};rows=[]
    for i,name in enumerate(('bear','base','bull')):
        transformation_pv=sum((625_000_000./3)/(1+wacc[i])**y for y in (1,2,3)) if ticker=='WTW' else 0.
        state=EnterpriseCashFlowState(starting[i],growth[i],tg[i],wacc[i],cash,debt,0.,claims+transformation_pv,shares[i])
        tr=enterprise_cash_flow_dcf(state,forecast_years=8,allow_nonpositive_equity_trace=True);raw=tr['intrinsic_value_per_share']
        rows.append({'name':name,'raw_value_per_share':raw,'conditional_value_per_share':max(0.,raw),'starting_cash_fcff':starting[i],'growth':growth[i],'wacc':wacc[i],'terminal_growth':tg[i],'cash_and_investments':cash,'debt_and_finance_leases':debt,'other_equity_claims':claims+transformation_pv,'transformation_cost_pv':transformation_pv,'shares':shares[i],'limited_liability_floor_applied':raw<0});traces[name]=tr
    ledger={'controlling_filing':filing,'flow_sources':flows,'software_sources':extra,'annual_cash_sources':annual,'tax_rate_sources':tax_sources,'bridge_sources':bridge,'model_trace':{'states':traces},'history_scope':scope,'unknown_legal_tail':None,'raw_scenario_rows':rows,'structural_top_level_period_diagnostic':{'value':st.get('period_end'),'used_for_selection':False}}
    if rows[1]['raw_value_per_share']<=0:
        return withheld(ticker,filing,'Withheld: the reported post-transaction cash run rate does not support a positive base after debt and common-equity claims. A stronger normalized base needs source-backed integration cash economics.',ledger)
    sc=dict(zip(('low','base','high'),[r['conditional_value_per_share'] for r in rows]))
    if not 0<=sc['low']<=sc['base']<=sc['high']:raise ValueError(ticker+': unordered range')
    warning='Conditional Low reported-operations FCFF baseline. '+scope+' Customer/clearing cash is excluded from available cash. Transaction, working-capital, reinvestment and legal outcomes may move value outside this range.'
    if ticker=='MA':warning+=' Capitalized software is deducted; recorded $296M litigation is charged once. Unquantified legal outcomes remain outside this operating baseline.'
    if ticker=='WTW':
        warning+=' The full $642M pension liability is conservatively reserved in addition to ordinary operating cash contributions; possible overlap lowers value. The July Propel plan adds $625M cash costs, discounted over three years, without assuming its forecast savings.'
        ledger['transformation_event']={'accession':filing['accession'],'locator':'Note 20 subsequent events: July 28 Propel plan','reported_cash_cost':625_000_000.,'reported_non_cash_cost_excluded':25_000_000.,'reported_annual_net_savings_excluded':350_000_000.,'payment_schedule':[625_000_000./3]*3,'reported_vs_estimated':'reported cost with governed equal 3-year timing','pv_by_scenario':[row['transformation_cost_pv'] for row in rows]}
    rel=assess_reliability(accounting_low=sc['base'],accounting_base=sc['base'],accounting_high=sc['base'],scenario_low=sc['low'],scenario_base=sc['base'],scenario_high=sc['high'],model_cap='Low',source_cap='High',reasons=('SPECIALIST_MODEL_UNCERTAINTY',))
    assumptions={**profile.public_metadata(),'forecast_years':8,'normalization_basis':scope,'assumption_source_mix':'reported_history_and_governed_scenarios','cash_conversion_margin':tuple(x/revenue for x in starting),'growth':growth,'wacc':wacc,'terminal_growth':tg,'shares':shares,'equity_floor_basis':'limited liability floor; raw residual retained','calculator_calibration':'Exact FCFF default replay.','invalidation':'Revalue after material changes in continuing scope, claims, settlement funding, shares or recurring cash conversion.'}
    if ticker=='FIS':
        assumptions['history_years_used']=0
        assumptions['historical_years_examined']=len(annual)
        assumptions['comparable_current_months']=6
    baseline=BaselineValuation(ticker=ticker,method='payments_operating_fcff' if ticker in {'GPN','FIS','MA'} else 'broker_operating_fcff' if ticker=='WTW' else 'exchange_operating_fcff',method_version=BATCH_38_HISTORY_VERSION,low=sc['low'],base=sc['base'],high=sc['high'],confidence='Low',availability_type=AvailabilityType.CONDITIONAL,warnings=(warning,))
    return {'ticker':ticker,'method':baseline.method,'model_version':BATCH_38_HISTORY_VERSION,'availability_type':'conditional_estimate','scenario_rows':rows,'scenario_range':sc,'reported_inputs':{'ttm_cash_fcff':fcff,'ttm_reinvestment_including_software':capex},'governed_assumptions':assumptions,'history_reliability':rel.as_dict(),'source_ledger':ledger,'warning':warning,'baseline':baseline.as_private_dict()}

def _period_flow_shares(st):
    rs=[r for r in st['facts'] if r.get('local_name')=='WeightedAverageNumberOfDilutedSharesOutstanding' and r.get('period_start')=='2026-01-01' and r.get('period_end')==PERIOD and r.get('unit')=='xbrli:shares' and not r.get('dimensions')]
    if not rs:raise ValueError('diluted shares missing')
    r=rs[0]
    return {'source_kind':'structural_xbrl','accession':st['source_accession'],'concept':r['qname'],'period_start':'2026-01-01','period_end':PERIOD,'unit':'xbrli:shares','value':r['value'],'reported_vs_estimated':'reported'}

def build_batch_38_history_result(*,ticker,source_root,structural_root,event_root,structural_cache_root=None):
    if ticker not in BATCH_38_TICKERS:raise ValueError(ticker)
    packet=Path(source_root)/ticker;sp=Path(structural_root)/ticker
    sub=json.loads((packet/'submissions.json').read_text());facts=json.loads((packet/'companyfacts.json').read_text());manifest=json.loads((packet/'source-manifest.json').read_text());st=json.loads((sp/'structural-filing.json').read_text());filing=_controlling(manifest,sub)
    if st['source_accession']!=filing['accession'] or st['report_date']!=PERIOD:raise ValueError('controlling identity mismatch')
    verify=_verify_source_bundle(ticker=ticker,packet=packet,structural_packet=sp,structural_cache_root=Path(structural_cache_root),filing=filing)
    if ticker in INSURERS:
        from .batch_38_insurers import build_insurer
        result=build_insurer(ticker,facts,st,filing)
    elif ticker=='CPAY':
        result=withheld(ticker,filing,'Withheld: customer deposits and operating liabilities share one cash-flow line; the current source packet does not separate recurring issuer cash from customer funding. A financing-aware earnings or cash model must be reconciled before publication.',{'pooled_operating_inflow':_period_flow(st,('IncreaseDecreaseInAccountsPayableAndAccruedLiabilities',),PERIOD,target_days=180) if any(r.get('local_name')=='IncreaseDecreaseInAccountsPayableAndAccruedLiabilities' for r in st['facts']) else {'value':1570343000.,'unit':'USD','accession':filing['accession'],'locator':'Cash flow: accounts payable, accrued expenses and customer deposits'},'unknown_customer_funding_component':None})
        result['source_ledger']['funding_boundary']={'customer_deposits':point(st,'ContractWithCustomerLiabilityCurrent'),'restricted_cash':point(st,'RestrictedCashAndCashEquivalents'),'corporate_cash_candidate':point(st,'CashAndCashEquivalentsAtCarryingValue'),'used_as_free_cash':False,'reason':'The pooled OCF line does not identify the cash contribution attributable to customer funding. All model outputs remain null pending reconciliation.'}
    else:result=operating(ticker,sub,facts,st,filing)
    result['source_ledger']['runtime_source_verification']=verify
    result['source_ledger']['event_sources']=events(ticker,event_root,verify)
    return result
