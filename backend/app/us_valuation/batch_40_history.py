"""History-backed practical baselines for controlled Universe Reset Batch 40."""
from __future__ import annotations
from copy import deepcopy
from datetime import date
import hashlib,json
from pathlib import Path
from typing import Any,Iterable
from app.valuation.bank import residual_income_valuation
from .baseline import AvailabilityType,BaselineValuation
from .batch_02_practical_inputs import _normalizer,_normalized_tax_rate,cash_fcff_from_reported
from .batch_04_launch_first import _controlling
from .batch_08_history import _annual_cash_with_losses
from .batch_35_history import _instant,_period_flow,_rows,_source
from .batch_40 import BATCH_40_MANIFEST,BATCH_40_TICKERS,BATCH_40_VALUATION_DATE
from .batch_40_sources import _verify_source_bundle
from .history import HISTORY_POLICY_VERSION,CompanyHistoryProfile,HistoryObservation,build_cash_fcff_history_profile,summarize_history_metric
from .practical_models import EnterpriseCashFlowState,enterprise_cash_flow_dcf
from .reliability import assess_reliability
from .xbrl import load_concept_config

BATCH_40_HISTORY_VERSION='BATCH-40-HISTORY-1.0';PERIOD='2026-06-30'
FINANCIAL=frozenset({'XYZ','SYF','PYPL','HOOD','APO','BLK'});OPERATING=frozenset({'MSCI','ICE','TPL'});WITHHELD=frozenset({'COIN'})
PASS_TICKERS=frozenset();CONDITIONAL_TICKERS=frozenset(set(BATCH_40_TICKERS)-WITHHELD);WITHHELD_TICKERS=WITHHELD
EARNINGS={'XYZ':('NetIncomeLossAvailableToCommonStockholdersBasic','NetIncomeLoss'),'SYF':('NetIncomeLossAvailableToCommonStockholdersBasic',),'PYPL':('NetIncomeLossAvailableToCommonStockholdersBasic',),'HOOD':('NetIncomeLossAvailableToCommonStockholdersBasic',),'APO':('NetIncomeLossAvailableToCommonStockholdersBasic',),'BLK':('NetIncomeLossAvailableToCommonStockholdersDiluted',)}
POLICY={
'XYZ':{'method':'fintech_parent_equity_residual_income_equity_earnings','roe':(.03,.06,.09),'payout':(.10,.20,.30),'coe':(.12,.105,.095),'warning':'Conditional Low fintech parent-equity baseline. Customer funds, settlements, consumer receivables, loans, warehouse funding and bitcoin remain inside equity economics; raw OCF is not treated as unrestricted cash.'},
'SYF':{'method':'consumer_finance_residual_income_equity_earnings','roe':(.08,.12,.16),'payout':(.25,.35,.45),'coe':(.115,.10,.09),'warning':'Conditional Low consumer-finance residual-income baseline. Deposits, receivables, securitization funding, credit losses, preferred claims and regulatory capital remain inside equity economics.'},
'PYPL':{'method':'payments_parent_equity_residual_income_equity_earnings','roe':(.08,.12,.16),'payout':(.25,.35,.45),'coe':(.11,.095,.085),'warning':'Conditional Low payments parent-equity baseline. Customer-float assets and liabilities, loans, credit losses and PYUSD/customer balances are not issuer cash; the controlling June filing replaces stale Companyfacts TTM inputs.'},
'HOOD':{'method':'broker_crypto_residual_income_equity_earnings','roe':(.06,.10,.14),'payout':(.20,.30,.40),'coe':(.11,.095,.085),'warning':'Conditional Low brokerage/crypto parent-equity baseline. Customer deposits, crypto, securities borrowing/lending and clearing collateral are not issuer cash; negative early history and current trading strength keep the range broad.'},
'APO':{'method':'alternative_manager_insurance_residual_income_equity_earnings','roe':(.04,.08,.12),'payout':(.20,.30,.40),'coe':(.11,.095,.085),'warning':'Conditional Low alternative-manager/insurance residual-income baseline. AUM, Athene assets, policyholder funds and consolidated VIEs are not parent cash; preferred claims, FRE/SRE, performance fees and insurance marks remain material.'},
'BLK':{'method':'asset_manager_residual_income_equity_earnings','roe':(.08,.12,.16),'payout':(.30,.40,.50),'coe':(.105,.09,.08),'warning':'Conditional Low asset-manager residual-income baseline. AUM, sponsored products and securities collateral are not parent cash; fully diluted earnings, shares and Subco unit equity are aligned once. HPS, performance fees, securities lending and legal matters remain material.'},}
EVENT_TREATMENTS={t:'Cutoff filings and exhibits were hash-verified; completed balance-sheet events are consumed once, pending events remain warnings, and client/fund/customer assets are not issuer cash.' for t in BATCH_40_TICKERS}
TPL_FIXED_ASSET_HISTORY={
 '2021-12-31':{'value':15_548_000.,'accession':'0001811074-24-000015','filed':'2024-02-21','primary_document':'tpl-20231231.htm','table_locator':'Consolidated cash flows: Purchase of fixed assets, 2021 comparative'},
 '2022-12-31':{'value':19_212_000.,'accession':'0001811074-24-000015','filed':'2024-02-21','primary_document':'tpl-20231231.htm','table_locator':'Consolidated cash flows: Purchase of fixed assets, 2022 comparative'},
 '2023-12-31':{'value':15_028_000.,'accession':'0001811074-24-000015','filed':'2024-02-21','primary_document':'tpl-20231231.htm','table_locator':'Consolidated cash flows: Purchase of fixed assets, 2023'},
 '2024-12-31':{'value':29_696_000.,'accession':'0001811074-26-000018','filed':'2026-02-18','primary_document':'tpl-20251231.htm','table_locator':'Consolidated cash flows: Purchase of fixed assets, 2024 comparative'},
 '2025-12-31':{'value':59_531_000.,'accession':'0001811074-26-000018','filed':'2026-02-18','primary_document':'tpl-20251231.htm','table_locator':'Consolidated cash flows: Purchase of fixed assets, 2025'},
}

def _events(ticker,root,manifest_sha):
 p=Path(root)/ticker/'inventory.json';rows=json.loads(p.read_text())
 if not rows or any(r.get('filed','')>BATCH_40_VALUATION_DATE for r in rows):raise ValueError(f'{ticker}: invalid event inventory')
 docs=[]
 for row in rows:
  for d in row.get('documents',[]):
   q=Path(d['path']);q=q if q.is_absolute() else Path(root).parent.parent/q
   if not q.exists() or hashlib.sha256(q.read_bytes()).hexdigest()!=d.get('sha256'):raise ValueError(f'{ticker}: event hash mismatch')
   docs.append(d)
 return {'source_kind':'sec_event_screening','decision':'accepted_context','screened_filings':rows,'documents':docs,'inventory_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_manifest_sha256':manifest_sha,'treatment':EVENT_TREATMENTS[ticker],'reported_vs_estimated':'reported_and_screened'}

def _dim_source(st,row):return {'source_kind':'structural_xbrl','accession':st.get('source_accession'),'filed':st.get('filed_date'),'form':st.get('form'),'period_start':row.get('period_start'),'period_end':row.get('period_end'),'concept':row.get('qname'),'unit':row.get('unit'),'value':float(row['value']),'dimensions':row.get('dimensions'),'reported_vs_estimated':'reported'}

def _member_instant(st,name,period,member):
 rows=[r for r in st.get('facts',[]) if r.get('local_name')==name and r.get('period_start') is None and r.get('period_end')==period and r.get('unit')=='USD' and isinstance(r.get('value'),(int,float)) and any(member in dimension_member for _,dimension_member in r.get('dimensions',[]))]
 if len(rows)!=1:raise ValueError(f'{name} {member} {period}: exact dimensional fact unresolved')
 return _dim_source(st,rows[0])

def _latest_shares(ticker,st):
 rows=[r for r in st.get('facts',[]) if r.get('local_name')=='EntityCommonStockSharesOutstanding' and r.get('period_start') is None and r.get('unit')=='xbrli:shares' and PERIOD<=str(r.get('period_end',''))<=BATCH_40_VALUATION_DATE and isinstance(r.get('value'),(int,float))]
 if not rows:raise ValueError(f'{ticker}: current shares absent')
 latest=max(r['period_end'] for r in rows);cur=[r for r in rows if r['period_end']==latest]
 if ticker=='BLK':
  fd=[r for r in cur if any('FullyDilutedSharesMember' in member for _,member in r.get('dimensions',[]))]
  if len(fd)!=1:raise ValueError('BLK: fully diluted share scope unresolved')
  return {**_dim_source(st,fd[0]),'source_kind':'structural_fully_diluted_share_count'}
 plain=[r for r in cur if not r.get('dimensions')]
 if plain:return {**_dim_source(st,plain[-1]),'source_kind':'structural_dei_current_share_count'}
 class_rows=[r for r in cur if any('StatementClassOfStockAxis' in axis for axis,_ in r.get('dimensions',[])) and not any('Preferred' in member for _,member in r.get('dimensions',[]))]
 if not class_rows:raise ValueError(f'{ticker}: class shares unresolved')
 return {'source_kind':'derived_current_class_share_count','accession':st.get('source_accession'),'period_end':latest,'unit':'xbrli:shares','value':sum(float(r['value']) for r in class_rows),'formula':'sum current economic common classes','sources':[_dim_source(st,r) for r in class_rows],'reported_vs_estimated':'reported_components'}

def _preferred(ticker,st,period):
 for name in ('PreferredStockLiquidationPreferenceValue','PreferredStockValueOutstanding','PreferredStockCarryingValue','PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount','PreferredStockValue'):
  try:r=_instant(st,(name,),period)
  except ValueError:continue
  return float(r['value']),'reported_preferred_claim' if r['value']>0 else 'reported_preferred_absence',[r]
 return 0.,'statement_proven_preferred_absence',[{'source_kind':'statement_scope_check','accession':st.get('source_accession'),'period_end':period,'treatment':'No economic preferred claim or preferred dividend is reported; blank facts are not silently converted to zero.','reported_vs_estimated':'source_bounded_absence_check'}]

def _annual(facts,ticker):
 required=3 if ticker=='BLK' else 5;selected={}
 for concept in EARNINGS[ticker]:
  for r in _rows(facts,concept):
   if r.get('form') not in {'10-K','10-K/A'} or r.get('filed','')>BATCH_40_VALUATION_DATE or not r.get('start') or not r.get('end') or not isinstance(r.get('val'),(int,float)):continue
   try:span=(date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days
   except (ValueError,TypeError):continue
   if not 300<=span<=380:continue
   old=selected.get(r['end'])
   if old is None or (r.get('filed',''),r.get('accn',''))>(old[0].get('filed',''),old[0].get('accn','')):selected[r['end']]=(r,concept)
 ends=[e for e in sorted(selected) if e>='2020-01-01'][-required:]
 if len(ends)!=required:raise ValueError(f'{ticker}: insufficient annual common history')
 return tuple({'period_end':e,'value':float(selected[e][0]['val']),'source':_source(selected[e][0],selected[e][1])} for e in ends)

def _financial(ticker,facts,st,filing,event):
 annual=_annual(facts,ticker);current=_period_flow(st,EARNINGS[ticker],PERIOD,target_days=180);prior=_period_flow(st,EARNINGS[ticker],'2025-06-30',target_days=180);ttm=annual[-1]['value']+current['value']-prior['value']
 if ticker=='HOOD':
  total=_instant(st,('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',),PERIOD);nci=_instant(st,('MinorityInterest',),PERIOD);equity={**total,'value':total['value']-nci['value'],'formula':'consolidated equity less NCI = parent equity','components':[total,nci]};ptotal=_instant(st,('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',),'2025-12-31');pnci=_instant(st,('MinorityInterest',),'2025-12-31');opening={**ptotal,'value':ptotal['value']-pnci['value'],'formula':'consolidated equity less NCI = parent equity','components':[ptotal,pnci]}
 elif ticker=='BLK':
  parent=_instant(st,('StockholdersEquity',),PERIOD);subco=_member_instant(st,'TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests',PERIOD,'SubCoMember');equity={**parent,'value':parent['value']+subco['value'],'formula':'parent stockholders equity plus exchangeable Subco unit temporary equity = fully diluted common-equivalent equity','components':[parent,subco]}
  pparent=_instant(st,('StockholdersEquity',),'2025-12-31');psubco=_member_instant(st,'TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests','2025-12-31','SubCoMember');opening={**pparent,'value':pparent['value']+psubco['value'],'formula':'parent stockholders equity plus exchangeable Subco unit temporary equity = fully diluted common-equivalent equity','components':[pparent,psubco]}
 else:equity=_instant(st,('StockholdersEquity',),PERIOD);opening=_instant(st,('StockholdersEquity',),'2025-12-31')
 pref,status,prefsrc=_preferred(ticker,st,PERIOD);ppref,pstatus,pprefsrc=_preferred(ticker,st,'2025-12-31');common=equity['value']-pref;ocommon=opening['value']-ppref;share=_latest_shares(ticker,st)
 if min(ttm,common,ocommon,share['value'])<=0:raise ValueError(f'{ticker}: nonpositive common input')
 obs=[HistoryObservation('annual',r['period_end'],int(r['period_end'][:4]),r['value'],'USD','reported annual parent/common earnings',(r['source'],)) for r in annual];obs.append(HistoryObservation('operating_ttm',PERIOD,None,ttm,'USD','latest FY plus current H1 less prior H1',(annual[-1]['source'],current,prior)));metric=summarize_history_metric('normalized_common_earnings',obs)
 if metric is None:raise ValueError(f'{ticker}: history absent')
 profile=CompanyHistoryProfile(HISTORY_POLICY_VERSION,'financial_equity_residual_income',BATCH_40_VALUATION_DATE,tuple(r['period_end'] for r in annual),(metric,),True,'reported_and_company_history');policy=POLICY[ticker];history_high=max(metric.high,ttm)/common;roes=tuple(min(x,history_high) for x in policy['roe'])
 if not 0<roes[0]<=roes[1]<=roes[2] or roes[0]==roes[2]:roes=(max(.02,history_high*.5),max(.025,history_high*.75),history_high)
 sv=float(share['value']);shares=(sv*1.015,sv,sv*.985);rows=[];traces={}
 for i,name in enumerate(('bear','base','bull')):
  tr=residual_income_valuation(book_value_per_share=common/shares[i],current_roe=roes[i],cost_of_equity=policy['coe'][i],current_payout_ratio=policy['payout'][i],terminal_roe=(.085,.105,.115)[i],terminal_growth=(.01,.02,.025)[i],years=5);raw=float(tr['intrinsic_value']);rows.append({'name':name,'raw_value_per_share':raw,'conditional_value_per_share':raw,'book_value_per_share':common/shares[i],'current_roe':roes[i],'current_payout_ratio':policy['payout'][i],'cost_of_equity':policy['coe'][i],'terminal_roe':(.085,.105,.115)[i],'terminal_growth':(.01,.02,.025)[i],'shares':shares[i],'preferred_claim':pref,'ending_common_equity':common,'limited_liability_floor_applied':False});traces[name]=tr
 sc=dict(zip(('low','base','high'),[r['raw_value_per_share'] for r in rows]));
 if not 0<sc['low']<=sc['base']<=sc['high']:raise ValueError(f'{ticker}: invalid residual range')
 rel=assess_reliability(accounting_low=sc['base'],accounting_base=sc['base'],accounting_high=sc['base'],scenario_low=sc['low'],scenario_base=sc['base'],scenario_high=sc['high'],model_cap='Low',source_cap='High',reasons=('SPECIALIST_MODEL_UNCERTAINTY',));invalid='Revalue if parent/common earnings, equity, preferred/NCI, shares, customer/client/fund boundaries, credit/capital, performance cycles or events leave the bounded range.';a={**profile.public_metadata(),'forecast_years':5,'normalization_basis':'reported_parent_common_equity_with_history_bounded_roe','assumption_source_mix':'reported_equity_earnings_history_and_governed_scenarios','equity_floor_basis':'not applied','earnings_multiples':tuple(r['raw_value_per_share']*r['shares']/ttm for r in rows),'current_roe':roes,'current_payout_ratio':policy['payout'],'cost_of_equity':policy['coe'],'terminal_roe':(.085,.105,.115),'terminal_growth':(.01,.02,.025),'shares':shares,'route_is_equity_level':True,'ev_debt_bridge_applied':False,'preferred_claim_status':status,'calculator_calibration':'Exact residual-income default replay.','invalidation':invalid};base=BaselineValuation(ticker=ticker,method=policy['method'],method_version=BATCH_40_HISTORY_VERSION,low=sc['low'],base=sc['base'],high=sc['high'],confidence='Low',availability_type=AvailabilityType.CONDITIONAL,warnings=(policy['warning'],invalid))
 return {'ticker':ticker,'method':policy['method'],'model_version':BATCH_40_HISTORY_VERSION,'availability_type':'conditional_estimate','scenario_rows':rows,'scenario_range':sc,'reported_inputs':{'ttm_common_earnings':ttm,'beginning_total_equity':opening['value'],'ending_total_equity':equity['value'],'beginning_preferred_claim':ppref,'preferred_claim':pref,'beginning_common_equity':ocommon,'ending_common_equity':common,'share_count':sv},'governed_assumptions':a,'history_reliability':rel.as_dict(),'source_ledger':{'controlling_filing':filing,'common_earnings_reconstruction':{'annual_history':list(annual),'latest_fy':annual[-1],'current_ytd':current,'prior_ytd':prior,'ttm':ttm,'formula':'latest FY + current H1 - prior H1'},'company_history_profile':profile.as_private_dict(),'equity_model_context':{'ending_parent_equity':equity,'opening_parent_equity':opening,'preferred_status':status,'prior_preferred_status':pstatus,'preferred_sources':prefsrc,'prior_preferred_sources':pprefsrc,'current_share_count':share},'event_sources':event,'bridge_treatment':'Equity-level model: customer, client, fund, insurance, deposit, crypto and securities-financing balances remain inside parent common earnings/equity; no EV debt bridge.','residual_income_trace':{'states':traces},'structural_top_level_period_diagnostic':{'value':st.get('period_end'),'used_for_selection':False}},'warning':policy['warning'],'baseline':base.as_private_dict()}

def _manual_pypl(sub,facts,st):
 n=_normalizer(sub,facts);tax,taxsrc=_normalized_tax_rate(n);fields={'revenue':'Revenues','operating_cash_flow':'NetCashProvidedByUsedInOperatingActivities','capital_expenditures':'PaymentsToAcquirePropertyPlantAndEquipment','interest_expense':'InterestExpenseNonoperating'};latest={k:n.annual_at_end(k,'2025-12-31') for k in fields}
 if any(v is None for v in latest.values()):raise ValueError('PYPL FY absent')
 cur={k:_period_flow(st,(c,),PERIOD,target_days=180) for k,c in fields.items()};prev={k:_period_flow(st,(c,),'2025-06-30',target_days=180) for k,c in fields.items()};vals={k:latest[k].value+cur[k]['value']-prev[k]['value'] for k in fields};fcff=cash_fcff_from_reported(operating_cash_flow=vals['operating_cash_flow'],capital_expenditures=vals['capital_expenditures'],spectrum_investment=0,interest_expense=vals['interest_expense'],tax_rate=tax);return {'latest_fy':{k:v.as_dict() for k,v in latest.items()},'current_h1':cur,'prior_h1':prev,'values':vals,'cash_fcff':fcff,'period_end':PERIOD,'generic_companyfacts_ttm_rejected':True},tax,list(taxsrc)

def _annual_operating(n,software_field=None):
 rows=list(_annual_cash_with_losses(n)[2])
 if software_field:
  for r in rows:
   s=n.annual_at_end(software_field,r['period_end'])
   if s is None:raise ValueError('annual software absent')
   r['software_capex']=s.as_dict();r['cash_fcff']-=s.value;r['formula']='OCF - PP&E - capitalized software + after-tax interest'
 return tuple(rows)

def _tpl_flows(sub,facts,st):
 n=_normalizer(sub,facts);tax,taxsrc=_normalized_tax_rate(n);rev=n.ttm_flow('revenue');ocf=n.ttm_flow('operating_cash_flow');interest=n.ttm_flow('interest_expense')
 concepts=('PaymentsToAcquireRealEstate','PaymentsToAcquireRoyaltyInterestsInMiningProperties')
 annual=[]
 def exact(concept,start,end,form):
  rs=[r for r in _rows(facts,concept) if r.get('start')==start and r.get('end')==end and r.get('form') in form and r.get('filed','')<=BATCH_40_VALUATION_DATE]
  if not rs:return {'source_kind':'cash_flow_statement_scope_absence','concept':'us-gaap:'+concept,'value':0.,'unit':'USD','period_start':start,'period_end':end,'treatment':'The complete filed cash-flow statement has no separate line for this reinvestment category in this period.','reported_vs_estimated':'source_bounded_absence_check'}
  r=max(rs,key=lambda x:(x.get('filed',''),x.get('accn','')));return _source(r,concept)
 for y in range(2021,2026):
  end=f'{y}-12-31';revenue=n.annual_at_end('revenue',end);cash=n.annual_at_end('operating_cash_flow',end);intr=n.annual_at_end('interest_expense',end)
  if revenue is None or cash is None:raise ValueError(f'TPL annual {y} absent')
  if intr is None:
   class ZeroInterest:
    value=0.
    def as_dict(self):return {'source_kind':'reported_no_debt_history','concept':'InterestExpenseNonoperating','value':0.,'unit':'USD','period_end':end,'reported_vs_estimated':'source_bounded_absence_check'}
   intr=ZeroInterest()
  fixed={**TPL_FIXED_ASSET_HISTORY[end],'source_kind':'sec_filing_cash_flow_table','concept':'tpl:PaymentsToAcquireEquipmentAndOtherAcquisitionOfRealEstate','unit':'USD','period_start':f'{y}-01-01','period_end':end,'reported_vs_estimated':'reported'};fixed['source_url']=f"https://www.sec.gov/Archives/edgar/data/1811074/{fixed['accession'].replace('-','')}/{fixed['primary_document']}";cap=[fixed,*[exact(c,f'{y}-01-01',end,{'10-K','10-K/A'}) for c in concepts]];total=sum(x['value'] for x in cap);fcff=cash_fcff_from_reported(operating_cash_flow=cash.value,capital_expenditures=total,spectrum_investment=0,interest_expense=abs(intr.value),tax_rate=tax);annual.append({'period_end':end,'revenue':revenue.as_dict(),'operating_cash_flow':cash.as_dict(),'capital_expenditures':{'value':total,'components':cap},'interest_expense':intr.as_dict(),'cash_fcff':fcff,'formula':'OCF - fixed assets - real estate - royalty interests + after-tax interest'})
 latest=annual[-1]['capital_expenditures'];current=[_period_flow(st,('PaymentsToAcquireEquipmentAndOtherAcquisitionOfRealEstate',),PERIOD,target_days=180),*[exact(c,'2026-01-01',PERIOD,{'10-Q','10-Q/A'}) for c in concepts]];prior=[_period_flow(st,('PaymentsToAcquireEquipmentAndOtherAcquisitionOfRealEstate',),'2025-06-30',target_days=180),*[exact(c,'2025-01-01','2025-06-30',{'10-Q','10-Q/A'}) for c in concepts]];ttmcap=latest['value']+sum(x['value'] for x in current)-sum(x['value'] for x in prior);fcff=cash_fcff_from_reported(operating_cash_flow=ocf['value'],capital_expenditures=ttmcap,spectrum_investment=0,interest_expense=abs(interest['value']),tax_rate=tax);return {'revenue':rev,'operating_cash_flow':ocf,'interest_expense':interest,'capital_expenditures':{'value':ttmcap,'latest_fy':latest,'current_h1':current,'prior_h1':prior},'cash_fcff':fcff,'period_end':PERIOD},tuple(annual),tax,list(taxsrc)

def _operating(ticker,sub,facts,st,filing,event):
 config=deepcopy(load_concept_config());software_field=None
 if ticker=='MSCI':config['fields']['software_development']['concepts']=['PaymentsForSoftware'];software_field='software_development'
 if ticker=='ICE':config['fields']['software_development']['concepts']=['PaymentsToDevelopSoftware'];software_field='software_development'
 n=_normalizer(sub,facts,concept_config=config)
 if ticker=='TPL':flows,annual,tax,taxsrc=_tpl_flows(sub,facts,st);revenue=flows['revenue']['value'];fcff=flows['cash_fcff'];ttmsrc=[x for k in ('revenue','operating_cash_flow','interest_expense') for x in flows[k]['sources']]
 else:
  raw={k:n.ttm_flow(k) for k in ('revenue','operating_cash_flow','capital_expenditures','interest_expense')};tax,taxsrc=_normalized_tax_rate(n);extra=n.ttm_flow(software_field) if software_field else None;cap=raw['capital_expenditures']['value']+(extra['value'] if extra else 0.);fcff=cash_fcff_from_reported(operating_cash_flow=raw['operating_cash_flow']['value'],capital_expenditures=cap,spectrum_investment=0,interest_expense=abs(raw['interest_expense']['value']),tax_rate=tax);flows={**raw,'software_development':extra,'total_reinvestment':cap};annual=_annual_operating(n,software_field);revenue=raw['revenue']['value'];ttmsrc=[x for v in raw.values() for x in v['sources']]
 if any((flows[k]['period_end'] if isinstance(flows[k],dict) else PERIOD)!=PERIOD for k in ('revenue','operating_cash_flow','interest_expense')):raise ValueError(f'{ticker}: stale TTM')
 profile=build_cash_fcff_history_profile(annual_cash_states=annual,ttm_revenue=revenue,ttm_cash_fcff=fcff,ttm_period_end=PERIOD,ttm_sources=ttmsrc,valuation_date=BATCH_40_VALUATION_DATE);metric=profile.metric('cash_conversion_margin');starting=[revenue*x for x in (metric.low,metric.base,metric.high)]
 if ticker=='MSCI':cash=_instant(st,('CashAndCashEquivalentsAtCarryingValue',),PERIOD)['value']-3_700_000.;debt=_instant(st,('LongTermDebtNoncurrent',),PERIOD)['value'];claims=(120e6,60e6,0.);share=_latest_shares(ticker,st);growth=(-.01,.04,.07);wacc=(.105,.09,.08);tg=(0,.015,.02);bridge={'restricted_cash_excluded':3.7e6,'first_street_fixed_cash_sensitivity':claims,'contingent_earnout':None}
 elif ticker=='ICE':cash=_instant(st,('CashAndCashEquivalentsAtCarryingValue',),PERIOD)['value'];debt=_instant(st,('LongTermDebtCurrent',),PERIOD)['value']+_instant(st,('LongTermDebtNoncurrent',),PERIOD)['value'];claims=_instant(st,('MinorityInterest',),PERIOD)['value']+_instant(st,('RedeemableNoncontrollingInterestEquityCarryingAmount',),PERIOD)['value'];share=_latest_shares(ticker,st);growth=(-.02,.03,.06);wacc=(.11,.095,.085);tg=(0,.015,.02);assets=_instant(st,('MarginDepositsAndGuarantyFundsCurrent',),PERIOD)['value'];liabs=_instant(st,('MarginDepositsAndGuarantyFundsLiabilityCurrent',),PERIOD)['value'];
 elif ticker=='TPL':cash=_instant(st,('CashAndCashEquivalentsAtCarryingValue',),PERIOD)['value'];debt=0.;claims=0.;share=_latest_shares(ticker,st);growth=(-.05,.01,.05);wacc=(.115,.095,.08);tg=(-.01,.01,.02);bridge={'drawn_debt':0.,'royalty_and_land_reinvestment_included':True,'future_project_value_included':False}
 else:raise ValueError(ticker)
 if ticker=='ICE':
  if assets!=liabs:raise ValueError('ICE clearing mismatch')
  bridge={'matched_margin_and_guaranty_funds':assets,'marketaxess_pending_consideration':6e9,'marketaxess_pending_financing':6.25e9,'notes_settlement_after_cutoff':'2026-08-20','transaction_overlay_included':False}
 sv=float(share['value']);shares=(sv*1.015,sv,sv*.985);rows=[];traces={}
 for i,name in enumerate(('bear','base','bull')):
  other=claims[i] if isinstance(claims,tuple) else claims;state=EnterpriseCashFlowState(starting[i],growth[i],tg[i],wacc[i],cash,debt,0,other,shares[i]);tr=enterprise_cash_flow_dcf(state,forecast_years=8,allow_nonpositive_equity_trace=True);raw=float(tr['intrinsic_value_per_share']);rows.append({'name':name,'raw_value_per_share':raw,'conditional_value_per_share':max(0.,raw),'starting_cash_fcff':starting[i],'growth':growth[i],'wacc':wacc[i],'terminal_growth':tg[i],'cash_and_investments':cash,'debt_and_finance_leases':debt,'other_equity_claims':other,'shares':shares[i],'limited_liability_floor_applied':raw<0});traces[name]=tr
 sc=dict(zip(('low','base','high'),[r['conditional_value_per_share'] for r in rows]));
 if not 0<=sc['low']<=sc['base']<=sc['high'] or sc['base']<=0:raise ValueError(f'{ticker}: invalid FCFF range')
 warnings={'MSCI':'Conditional Low data/subscription FCFF baseline. Capitalized software is deducted. The pending First Street $120M cash price is sensitivity-charged; contingent payments remain unbounded outside the range.','ICE':'Conditional Low exchange/data FCFF baseline. Capitalized software is deducted and matched clearing/guaranty funds are excluded. The pending ~$6B MarketAxess deal and financing remain outside the current-company range.','TPL':'Conditional Low land/royalty/water resource-cycle FCFF baseline. Fixed assets, real estate and royalty acquisitions are deducted; commodity, volume, water and land-sale cycles remain material, and no unreported project value is added.'};rel=assess_reliability(accounting_low=sc['base'],accounting_base=sc['base'],accounting_high=sc['base'],scenario_low=sc['low'],scenario_base=sc['base'],scenario_high=sc['high'],model_cap='Low',source_cap='High',reasons=('SPECIALIST_MODEL_UNCERTAINTY',));invalid='Revalue if cash conversion, software/reinvestment, debt/NCI, shares, commodity/volume, clearing funds, acquisitions or legal/event claims leave the bounded range.';a={**profile.public_metadata(),'forecast_years':8,'history_years_used':len(annual),'normalization_basis':'reported_cash_fcff_history','assumption_source_mix':'reported_history_and_governed_scenarios','cash_conversion_margin':tuple(x/revenue for x in starting),'growth':growth,'wacc':wacc,'terminal_growth':tg,'shares':shares,'equity_floor_basis':'bear-only limited liability floor; raw residual retained privately','calculator_calibration':'Exact enterprise cash-FCFF default replay.','invalidation':invalid};method='data_subscription_operating_fcff' if ticker=='MSCI' else 'financial_exchange_operating_fcff' if ticker=='ICE' else 'land_royalty_resource_cycle_fcff';base=BaselineValuation(ticker=ticker,method=method,method_version=BATCH_40_HISTORY_VERSION,low=sc['low'],base=sc['base'],high=sc['high'],confidence='Low',availability_type=AvailabilityType.CONDITIONAL,warnings=(warnings[ticker],invalid));return {'ticker':ticker,'method':method,'model_version':BATCH_40_HISTORY_VERSION,'availability_type':'conditional_estimate','scenario_rows':rows,'scenario_range':sc,'reported_inputs':{'ttm_revenue':revenue,'ttm_cash_fcff':fcff,'share_count':sv},'governed_assumptions':a,'history_reliability':rel.as_dict(),'source_ledger':{'controlling_filing':filing,'flow_sources':flows,'annual_cash_sources':list(annual),'tax_rate':tax,'tax_rate_sources':taxsrc,'company_history_profile':profile.as_private_dict(),'bridge_context':bridge,'event_sources':event,'model_trace':{'states':traces},'raw_scenario_rows':rows,'structural_top_level_period_diagnostic':{'value':st.get('period_end'),'used_for_selection':False}},'warning':warnings[ticker],'baseline':base.as_private_dict()}

def _coin_withheld(facts,st,filing,event):
 annual=[]
 for c in ('NetIncomeLossAvailableToCommonStockholdersBasic',):
  sel={}
  for r in _rows(facts,c):
   if r.get('form') in {'10-K','10-K/A'} and r.get('filed','')<=BATCH_40_VALUATION_DATE and r.get('start') and r.get('end'):
    try:span=(date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days
    except:continue
    if 300<=span<=380:sel[r['end']]=r
  annual=[{'period_end':e,'value':float(sel[e]['val']),'source':_source(sel[e],c)} for e in sorted(sel)[-5:]]
 cur=_period_flow(st,('NetIncomeLossAvailableToCommonStockholdersBasic',),PERIOD,target_days=180);prev=_period_flow(st,('NetIncomeLossAvailableToCommonStockholdersBasic',),'2025-06-30',target_days=180);ttm=annual[-1]['value']+cur['value']-prev['value'];equity=_instant(st,('StockholdersEquity',),PERIOD);share=_latest_shares('COIN',st);client=_instant(st,('ClientCustodialCashExcludingInTransitFundsReclassedCurrent',),PERIOD);funds=_instant(st,('ClientCustodialFundsCurrent',),PERIOD);liab=_instant(st,('CustodialCashLiabilitiesCurrent',),PERIOD)
 if ttm>=0 or funds['value']!=liab['value']:raise ValueError('COIN withholding gate changed')
 reason='Withheld: Coinbase has negative TTM common earnings and a highly discontinuous crypto cycle. Customer custodial cash/funds and matched liabilities cannot become issuer cash; no positive through-cycle base is supported without a specialist crypto/customer-funding model.';invalid='Revalue after positive source-backed through-cycle earnings or cash history and a matched custodial, stablecoin, collateral and crypto-financing schedule.';base=BaselineValuation(ticker='COIN',method='crypto_platform_parent_equity_residual_income',method_version=BATCH_40_HISTORY_VERSION,low=None,base=None,high=None,confidence=None,availability_type=AvailabilityType.NOT_AVAILABLE,warnings=(reason,invalid));return {'ticker':'COIN','method':base.method,'model_version':BATCH_40_HISTORY_VERSION,'availability_type':'not_available','scenario_rows':[],'scenario_range':{'low':None,'base':None,'high':None},'reported_inputs':{},'governed_assumptions':{'history_policy_version':HISTORY_POLICY_VERSION,'history_years_used':5,'forecast_years':5,'normalization_basis':'negative_ttm_and_unresolved_crypto_customer_funding','assumption_source_mix':'reported_current_and_history','invalidation':invalid},'history_reliability':None,'source_ledger':{'controlling_filing':filing,'common_earnings_reconstruction':{'annual_history':annual,'current_h1':cur,'prior_h1':prev,'ttm':ttm},'equity':equity,'share_count':share,'customer_boundary':{'client_custodial_cash':client,'client_custodial_funds':funds,'custodial_cash_liability':liab,'used_as_issuer_cash':False},'event_sources':event,'specialist_model_gap':'Stablecoin, custody, crypto-collateral and financing cash flows are not separated into a source-bounded recurring issuer cash series.'},'warning':reason,'baseline':base.as_private_dict()}

def build_batch_40_history_result(*,ticker,source_root,structural_root,event_root,structural_cache_root=None):
 if ticker not in BATCH_40_TICKERS:raise ValueError(ticker)
 packet=Path(source_root)/ticker;sp=Path(structural_root)/ticker;sub=json.loads((packet/'submissions.json').read_text());facts=json.loads((packet/'companyfacts.json').read_text());manifest=json.loads((packet/'source-manifest.json').read_text());st=json.loads((sp/'structural-filing.json').read_text());filing=_controlling(manifest,sub)
 if st.get('source_accession')!=filing['accession'] or st.get('report_date')!=PERIOD:raise ValueError(f'{ticker}: controlling mismatch')
 verify=_verify_source_bundle(ticker=ticker,packet=packet,structural_packet=sp,structural_cache_root=Path(structural_cache_root),filing=filing);event=_events(ticker,Path(event_root),verify['source_manifest_sha256'])
 if ticker=='PYPL':
  flow,tax,taxsrc=_manual_pypl(sub,facts,st);result=_financial(ticker,facts,st,filing,event);result['source_ledger']['controlling_ttm_cash_diagnostic']=flow;result['source_ledger']['controlling_ttm_cash_diagnostic']['tax_rate']=tax;result['source_ledger']['controlling_ttm_cash_diagnostic']['tax_sources']=taxsrc
 elif ticker in FINANCIAL:result=_financial(ticker,facts,st,filing,event)
 elif ticker in OPERATING:result=_operating(ticker,sub,facts,st,filing,event)
 else:result=_coin_withheld(facts,st,filing,event)
 result['source_ledger']['runtime_source_verification']=verify;return result

if FINANCIAL|OPERATING|WITHHELD!=set(BATCH_40_TICKERS) or PASS_TICKERS|CONDITIONAL_TICKERS|WITHHELD_TICKERS!=set(BATCH_40_TICKERS):raise RuntimeError('Batch 40 policy mismatch')
