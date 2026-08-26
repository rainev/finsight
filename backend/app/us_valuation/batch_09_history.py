"""History-backed launch-first baselines for controlled Batch 09."""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from .baseline import AssumptionClassification,AvailabilityType,BaselineAssumption,BaselineValuation
from .batch_02_conditional_estimates import five_year_fcff_dcf
from .batch_02_practical_inputs import _annual_cash_fcff,_normalizer,_normalized_tax_rate,cash_fcff_from_reported
from .batch_04_launch_first import _controlling,_duration,_point,_source_proven_no_other_equity_claims
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_09 import BATCH_09_TICKERS,BATCH_09_VALUATION_DATE
from .history import HISTORY_POLICY_VERSION,build_cash_fcff_history_profile
from .reliability import assess_reliability

BATCH_09_HISTORY_VERSION='BATCH-09-HISTORY-LAUNCH-FIRST-1.0'
PASS_TICKERS=frozenset({'BF.B','CL'})

def _shares(base):return (base*1.025,base,base*.975)
@dataclass(frozen=True)
class Policy:
 method:str;period:str;cash:float;debt:float;nci:tuple[float,float,float];shares:tuple[float,float,float];wacc:tuple[float,float,float];terminal:tuple[float,float,float];warning:str;invalidation:str
P={
'ADM':Policy('commodity_cycle_normalized_cash_fcff','2026-06-30',1_093_000_000.,8_011_000_000.,(299_000_000.,299_000_000.,299_000_000.),_shares(485_000_000.),(.115,.10,.09),(0,.01,.02),'Conditional Low estimate. Commodity margins, working capital, derivative collateral, supplier finance, and temporary equity remain material.','Invalidate if commodity cash conversion, restricted/margin cash, debt, temporary equity, NCI, or shares changes.'),
'BF.B':Policy('dual_class_brand_portfolio_cash_fcff','2026-04-30',308_000_000.,2_502_000_000.,(0.,0.,0.),_shares(466_733_000.),(.105,.09,.08),(0,.015,.02),'History-backed brand-portfolio cash-FCFF. BF.B class identity and the total Class A plus nonvoting economic denominator are preserved.','Invalidate if class rights/shares, cash, debt, inventory, brand cash conversion, or capex changes.'),
'STZ':Policy('alcohol_brand_portfolio_cash_fcff','2026-05-31',96_600_000.,10_533_800_000.,(294_200_000.,294_200_000.,294_200_000.),_shares(172_407_000.),(.11,.095,.085),(0,.01,.02),'Conditional Low estimate. Beer/wine/spirits scope, Canopy and equity-method interests, impairments, leverage, and NCI remain material.','Invalidate if portfolio scope, investment/impairment treatment, debt, NCI, cash conversion, or shares changes.'),
'KO':Policy('bottling_affiliate_normalized_cash_fcff','2026-07-03',16_371_000_000.,43_543_000_000.,(2_165_000_000.,2_165_000_000.,2_165_000_000.),_shares(4_313_000_000.),(.10,.085,.075),(0,.015,.025),'Conditional Low estimate. Bottling/equity affiliates, current structural replacement facts, debt, NCI, investments, and working-capital reversal remain material.','Invalidate if current filing facts, bottling/affiliate scope, debt, NCI, investment coverage, or cash conversion changes.'),
'CL':Policy('personal_care_pet_cash_fcff','2026-06-30',1_453_000_000.,7_857_000_000.,(330_000_000.,330_000_000.,330_000_000.),_shares(803_400_000.),(.10,.085,.075),(0,.015,.025),'History-backed global personal-care and pet-products cash-FCFF with debt, investments, NCI, and supplier finance reconciled.','Invalidate if Hill’s/pet scope, debt, NCI, investments, supplier finance, or diluted shares changes.'),
'TAP':Policy('brewer_cycle_normalized_cash_fcff','2026-06-30',2_128_100_000.,7_709_600_000.,(289_200_000.,289_200_000.,289_200_000.),_shares(188_600_000.),(.115,.10,.09),(0,.01,.02),'Conditional Low estimate. Beer volume/pricing, brand impairment, restructuring, brewery capex, leverage, leases, and NCI remain material.','Invalidate if brewer-cycle cash, impairment/restructuring, debt/leases, NCI, or shares changes.'),
'TGT':Policy('retail_supplier_finance_cash_fcff','2026-05-02',3_534_000_000.,15_415_000_000.,(0.,0.,0.),_shares(455_800_000.),(.11,.095,.085),(0,.01,.02),'Conditional Low estimate. Inventory/shrink, supplier finance, store reinvestment, leases, debt, and retail working capital remain material.','Invalidate if inventory/shrink, supplier finance, store capex, debt/leases, or shares changes.'),
'DG':Policy('discount_retail_reinvestment_cash_fcff','2026-05-01',1_353_113_000.,4_576_408_000.,(0.,0.,0.),_shares(221_559_000.),(.115,.10,.09),(0,.01,.02),'Conditional Low estimate. Store closures/remodels, shrink, inventory, supplier finance, leases, and refinancing remain material.','Invalidate if store program cash, inventory/shrink, debt/leases, supplier finance, or shares changes.'),
'GIS':Policy('packaged_food_portfolio_cash_fcff','2026-05-31',418_200_000.,13_538_400_000.,(12_200_000.,12_200_000.,12_200_000.),_shares(537_700_000.),(.11,.095,.085),(0,.01,.02),'Conditional Low estimate. Divestiture scope, impairment/restructuring, supplier finance, inventory, debt, and leases remain material.','Invalidate if continuing portfolio scope, debt/leases, supplier finance, NCI, cash, or shares changes.'),
}
POINTS={
'ADM':(('CashAndCashEquivalentsAtCarryingValue',1_060_000_000.),('DebtSecuritiesCurrent',33_000_000.),('ShortTermBorrowings',407_000_000.),('LongTermDebtCurrent',1_153_000_000.),('LongTermDebtNoncurrent',6_451_000_000.),('MinorityInterest',7_000_000.),('TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests',292_000_000.),('SupplierFinanceProgramObligation',427_000_000.)),
'BF.B':(('CashAndCashEquivalentsAtCarryingValue',308_000_000.),('ShortTermBorrowings',68_000_000.),('LongTermDebt',2_434_000_000.)),
'STZ':(('CashAndCashEquivalentsAtCarryingValue',96_600_000.),('LongTermDebt',10_197_500_000.),('ShortTermBorrowings',336_300_000.),('NoncontrollingInterestInVariableInterestEntity',294_200_000.)),
'KO':(('CashCashEquivalentsAndShortTermInvestments',13_529_000_000.),('MarketableSecurities',2_842_000_000.),('LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities',43_495_000_000.),('NotesAndLoansPayable',48_000_000.),('MinorityInterest',2_165_000_000.),('SupplierFinanceProgramObligation',1_431_000_000.)),
'CL':(('CashAndCashEquivalentsAtCarryingValue',1_370_000_000.),('MinorityInterest',330_000_000.),('SupplierFinanceProgramObligation',209_000_000.)),
'TAP':(('CashAndCashEquivalentsAtCarryingValue',2_128_100_000.),('DebtCurrent',2_037_100_000.),('LongTermDebtNoncurrent',5_672_500_000.),('MinorityInterest',187_200_000.),('RedeemableNoncontrollingInterestEquityCarryingAmount',102_000_000.),('SupplierFinanceProgramObligation',186_900_000.),('PreferredStockValue',0.)),
'TGT':(('CashCashEquivalentsAndShortTermInvestments',3_534_000_000.),('LongTermDebtAndCapitalLeaseObligations',14_282_000_000.),('LongTermDebtAndCapitalLeaseObligationsCurrent',1_133_000_000.),('SupplierFinanceProgramObligation',2_800_000_000.)),
'DG':(('CashAndCashEquivalentsAtCarryingValue',1_353_113_000.),('DebtCurrentAndNoncurrent',4_576_408_000.)),
'GIS':(('CashAndCashEquivalentsAtCarryingValue',453_800_000.),('DisposalGroupIncludingDiscontinuedOperationCashAndCashEquivalents',37_900_000.),('AvailableForSaleSecuritiesDebtSecurities',2_300_000.),('LongTermDebt',13_469_600_000.),('ShortTermBorrowings',68_400_000.),('FinanceLeaseLiability',400_000.),('MinorityInterest',12_200_000.),('SupplierFinanceProgramObligation',1_399_600_000.)),
}
STARTS={'ADM':'2026-01-01','BF.B':'2025-05-01','KO':'2026-01-01','CL':'2026-01-01','TAP':'2026-01-01','TGT':'2026-02-01','DG':'2026-01-31','GIS':'2025-05-26'}

def _dimension_duration(st,name,expected,start,end,member):
 rows=[r for r in st['facts'] if r.get('local_name')==name and r.get('period_start')==start and r.get('period_end')==end and isinstance(r.get('value'),(int,float)) and float(r['value'])==expected and any(member in str(v) for _,v in (r.get('dimensions') or []))]
 if not rows:raise ValueError(f'{name}/{member} absent')
 r=rows[0];return {'source_kind':'structural_xbrl','accession':st['source_accession'],'period_start':start,'period_end':end,'concept':r.get('qname'),'member':member,'unit':r.get('unit'),'value':expected,'reported_vs_estimated':'reported'}
def _dimension_point(st,name,expected,end,member):
 rows=[r for r in st['facts'] if r.get('local_name')==name and r.get('period_start') is None and r.get('period_end')==end and isinstance(r.get('value'),(int,float)) and float(r['value'])==expected and any(member in str(v) for _,v in (r.get('dimensions') or []))]
 if not rows:raise ValueError(f'{name}/{member} absent')
 r=rows[0];return {'source_kind':'structural_xbrl','accession':st['source_accession'],'period_end':end,'concept':r.get('qname'),'member':member,'unit':r.get('unit'),'value':expected,'reported_vs_estimated':'reported'}

def _bridge(t,st,p):
 rows=[_point(st,name=n,expected=v,period_end=p.period) for n,v in POINTS[t]]
 if t=='STZ':rows.append(_dimension_duration(st,'WeightedAverageNumberOfDilutedSharesOutstanding',172_407_000.,'2026-03-01','2026-05-31','CommonClassAMember'))
 else:rows.append(_duration(st,name='WeightedAverageNumberOfDilutedSharesOutstanding',expected=p.shares[1],period_start=STARTS[t],period_end=p.period))
 if t=='BF.B':rows.extend((_dimension_point(st,'CommonStockSharesOutstanding',168_441_000.,p.period,'CommonClassAMember'),_dimension_point(st,'CommonStockSharesOutstanding',290_262_000.,p.period,'NonvotingCommonStockMember'),_dimension_point(st,'CommonStockSharesOutstanding',458_703_000.,p.period,'CommonClassAAndNonvotingCommonStockMember')))
 if t=='CL':rows.extend((_dimension_point(st,'MarketableSecurities',83_000_000.,p.period,'typed'),_dimension_point(st,'LongTermDebt',7_857_000_000.,p.period,'CarryingReportedAmountFairValueDisclosureMember')))
 if t=='DG':rows.extend((_dimension_point(st,'SupplierFinanceProgramObligationCurrent',406_100_000.,p.period,'SupplyChainFinanceProgramMember'),{'source_kind':'structural_xbrl_scope_note','accession':st['source_accession'],'period_end':p.period,'field':'debt_includes_lease_obligation','value':4_576_408_000.,'unit':'USD','reported_vs_estimated':'reported_scope','basis':'DebtCurrentAndNoncurrent explicitly includes lease obligation; finance lease is not added again.'}))
 if t in {'BF.B','TGT','DG'}:rows.append(_source_proven_no_other_equity_claims(st,period_end=p.period))
 if t=='GIS':rows.append({'source_kind':'reported_cash_reconciliation','accession':st['source_accession'],'period_end':p.period,'field':'continuing_cash_and_securities','value':418_200_000.,'unit':'USD','reported_vs_estimated':'reported_reconciliation','basis':'$453.8M consolidated cash less $37.9M disposal-group cash plus $2.3M AFS securities.'})
 return rows

def _ko_ttm(st,n):
 specs={'revenue':('Revenues',25_852_000_000.,23_664_000_000.),'operating_cash_flow':('NetCashProvidedByUsedInOperatingActivities',7_543_000_000.,-1_391_000_000.),'capital_expenditures':('PaymentsToAcquirePropertyPlantAndEquipment',684_000_000.,751_000_000.),'interest_expense':('InterestExpenseNonoperating',744_000_000.,832_000_000.)};out={}
 for field,(name,current,prior) in specs.items():
  annual=n.annual_series(field,1)[0];cs=_structural_flow(st,name=name,start='2026-01-01',end='2026-07-03',expected=current);ps=_structural_flow(st,name=name,start='2025-01-01',end='2025-06-27',expected=prior);out[field]={'field':field,'value':annual.value+current-prior,'period_end':'2026-07-03','method':'latest_fy_plus_current_h1_minus_prior_h1','sources':[annual.as_dict(),cs,ps]}
 return out

def _withheld_clx(filing,st):
 reason='The controlling 2026-06-30 10-K structural package contains only two DEI facts and no current financial bridge facts. Older Q3 values cannot substitute for the year-end company.';baseline=BaselineValuation(ticker='CLX',method='unavailable_current_structural_bridge',method_version=BATCH_09_HISTORY_VERSION,low=None,base=None,high=None,confidence=None,availability_type=AvailabilityType.NOT_AVAILABLE,warnings=(reason,))
 return {'ticker':'CLX','method':'unavailable_current_structural_bridge','model_version':BATCH_09_HISTORY_VERSION,'availability_type':'not_available','scenario_rows':[],'scenario_range':{'low':None,'base':None,'high':None},'reported_inputs':{},'governed_assumptions':{'history_policy_version':HISTORY_POLICY_VERSION,'history_years_used':5,'normalization_basis':'current_structural_bridge_unavailable','assumption_source_mix':'reported_history_but_current_bridge_missing','invalidation':'Revalue after the controlling 10-K financial statements are structurally extracted.'},'history_reliability':None,'source_ledger':{'controlling_filing':filing,'structural_fact_count':len(st.get('facts',[])),'current_financial_bridge_fact_count':0,'structural_top_level_period_diagnostic':{'value':st.get('period_end'),'used_for_selection':False}},'warning':reason,'baseline':baseline.as_private_dict()}

def build_batch_09_history_result(*,ticker,source_root:Path,structural_root:Path):
 packet=Path(source_root)/ticker;sub=json.loads((packet/'submissions.json').read_text());facts=json.loads((packet/'companyfacts.json').read_text());manifest=json.loads((packet/'source-manifest.json').read_text());st=json.loads((Path(structural_root)/ticker/'structural-filing.json').read_text());filing=_controlling(manifest,sub)
 if st['source_accession']!=filing['accession']:raise ValueError(f'{ticker}: source mismatch')
 if ticker=='CLX':return _withheld_clx(filing,st)
 p=P[ticker]
 if filing['period_end']!=p.period:raise ValueError(f'{ticker}: period mismatch')
 n=_normalizer(sub,facts);flows=_ko_ttm(st,n) if ticker=='KO' else {f:n.ttm_flow(f) for f in ('revenue','operating_cash_flow','capital_expenditures','interest_expense')};tax=_normalized_tax_rate(n)[0];current=cash_fcff_from_reported(operating_cash_flow=float(flows['operating_cash_flow']['value']),capital_expenditures=float(flows['capital_expenditures']['value']),spectrum_investment=0.,interest_expense=abs(float(flows['interest_expense']['value'])),tax_rate=tax);ac,ar,annual_sources=_annual_cash_with_losses(n) if ticker=='TGT' else _annual_cash_fcff(n,spectrum_required=False,spectrum_floor=0,spectrum_source={},scope_adjustment=0.);sources=[]
 for flow in flows.values():sources.extend(dict(row) for row in flow.get('sources',[]) if isinstance(row,dict))
 profile=build_cash_fcff_history_profile(annual_cash_states=annual_sources,ttm_revenue=float(flows['revenue']['value']),ttm_cash_fcff=current,ttm_period_end=p.period,ttm_sources=sources,valuation_date=BATCH_09_VALUATION_DATE);cash=profile.metric('cash_conversion_margin');growth_metric=profile.metric('revenue_growth')
 if not profile.full_history or cash is None or growth_metric is None:raise ValueError(f'{ticker}: history insufficient')
 margins=(cash.low,cash.base,cash.high);growth=tuple(max(-.10,min(.15,v)) for v in (growth_metric.low,growth_metric.base,growth_metric.high));rows=[]
 for i,name in enumerate(('bear','base','bull')):
  raw=five_year_fcff_dcf(revenue=float(flows['revenue']['value']),fcff_margin=max(.001,margins[i]),growth=growth[i],wacc=p.wacc[i],terminal_growth=p.terminal[i],cash_and_investments=p.cash,debt=p.debt,noncontrolling_interests=p.nci[i],shares=p.shares[i]);value=max(0.,float(raw['value_per_share']));rows.append({'name':name,'conditional_value_per_share':value,'raw_value_per_share':float(raw['value_per_share']),'cash_conversion_margin':max(.001,margins[i]),'growth':growth[i],'wacc':p.wacc[i],'terminal_growth':p.terminal[i],'shares':p.shares[i],'limited_liability_floor_applied':value==0 and float(raw['value_per_share'])<0})
 scenario={'low':rows[0]['conditional_value_per_share'],'base':rows[1]['conditional_value_per_share'],'high':rows[2]['conditional_value_per_share']};is_pass=ticker in PASS_TICKERS
 if not(0<=scenario['low']<=scenario['base']<=scenario['high']) or scenario['base']<=0:raise ValueError(f'{ticker}: invalid range')
 reasons=() if is_pass else ('CONDITIONAL_EVENT_MODEL','SPECIALIST_MODEL_UNCERTAINTY');reliability=assess_reliability(accounting_low=scenario['base'],accounting_base=scenario['base'],accounting_high=scenario['base'],scenario_low=scenario['low'],scenario_base=scenario['base'],scenario_high=scenario['high'],model_cap='High' if is_pass else 'Low',source_cap='High',reasons=reasons);pub=profile.public_metadata()
 if not is_pass:pub.update({'normalization_basis':'company_history_with_material_event_override','assumption_source_mix':'reported_history_and_finsight_policy'})
 assumptions={**pub,'cash_conversion_margin':tuple(row['cash_conversion_margin'] for row in rows),'growth':growth,'wacc':p.wacc,'terminal_growth':p.terminal,'shares':p.shares,'equity_floor_basis':'limited-liability floor after negative residual' if scenario['low']==0 else 'not applied','calculator_calibration':'Calculator is calibrated to the published base; private history and bridge remain fixed.','invalidation':p.invalidation}
 key=(BaselineAssumption('company history',str(profile.history_years_used),AssumptionClassification.HISTORICALLY_DERIVED,'Source-linked annual history supplies cash-conversion and growth states.'),BaselineAssumption('reported anchors',str({k:v['value'] for k,v in flows.items()}),AssumptionClassification.REPORTED,'Cutoff-safe filing facts anchor current cash generation.'),BaselineAssumption('scenario policy',str(assumptions),AssumptionClassification.FINSIGHT_ASSUMPTION,'Discount rates, terminal growth, shares, and named dependencies remain transparent assumptions.'))
 baseline=BaselineValuation(ticker=ticker,method=p.method,method_version=BATCH_09_HISTORY_VERSION,low=scenario['low'],base=scenario['base'],high=scenario['high'],confidence=reliability.label,availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL,key_assumptions=key,warnings=(p.warning,p.invalidation),confidence_reasons=tuple(reliability.reasons),calculator_link=f'/api/us-valuations/{ticker}/calculator')
 return {'ticker':ticker,'method':p.method,'model_version':BATCH_09_HISTORY_VERSION,'availability_type':baseline.availability_type.value,'scenario_rows':rows,'scenario_range':scenario,'reported_inputs':{'ttm_revenue':flows['revenue']['value'],'ttm_operating_cash_flow':flows['operating_cash_flow']['value'],'ttm_capex':flows['capital_expenditures']['value'],'ttm_interest':flows['interest_expense']['value']},'governed_assumptions':assumptions,'history_reliability':reliability.as_dict(),'source_ledger':{'controlling_filing':filing,'flow_sources':flows,'company_history_profile':profile.as_private_dict(),'bridge_sources':_bridge(ticker,st,p),'bridge_reconciliation':{'cash_and_investments':p.cash,'debt_and_finance_leases':p.debt,'nci_or_temporary_equity':p.nci,'supplier_finance_and_operating_leases':'Remain operating in cash conversion and are not subtracted again.'},'structural_top_level_period_diagnostic':{'value':st.get('period_end'),'used_for_selection':False}},'warning':p.warning,'baseline':baseline.as_private_dict()}
if set(P)|{'CLX'}!=set(BATCH_09_TICKERS):raise RuntimeError('Batch 09 policy denominator mismatch')
