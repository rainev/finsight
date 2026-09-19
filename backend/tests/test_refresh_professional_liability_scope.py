from copy import deepcopy
import json
from pathlib import Path
import subprocess,sys,pytest
from app.us_valuation.refresh_professional_liability_scope import professional_liability_policy,bind_professional_liability_scope
ROOT=Path(__file__).resolve().parents[2]
def inputs():
 st=json.loads((ROOT/'output/batch-14-structural-sources-20260829/HCA/structural-filing.json').read_bytes());n=json.loads((ROOT/'output/us-refresh-runtime/narrative-evidence/HCA.json').read_bytes());packet=ROOT/'output/batch-14-sec-source-packets-20260829/HCA'
 return st,n,json.loads((packet/'companyfacts.json').read_bytes()),json.loads((packet/'submissions.json').read_bytes()),json.loads((ROOT/'output/us-refresh-runtime/recipes/HCA.json').read_bytes())
def bind(st=None,n=None,cf=None,recipe=None):
 s,nn,c,sub,r=inputs();return bind_professional_liability_scope(professional_liability_policy('HCA'),st or s,n or nn,cf or c,sub,recipe or r,cutoff='2026-08-14',source_root=ROOT/'output')
def test_real_reserve_assets_schedule_and_ownership_stay_separate():
 r=bind();assert r['reported_balance_sheet_professional_liability']['value']==1_464_000_000
 assert r['comparative_balance_sheet_professional_liability']['value']==1_466_000_000
 assert r['total_narrative_professional_reserves']==1_996_000_000
 assert r['insurance_investments']['total']['value']==519_000_000
 assert r['insurance_investments']['current']['value']==117_000_000 and r['insurance_investments']['noncurrent']['value']==402_000_000
 assert r['ownership_carrying_proof']['source_total']==3_433_000_000
 assert r['claim_payment_schedule']=={'next_12_month_aggregate':573_000_000,'retained_portion_aggregate':532_000_000,'exact_timing':None}
 assert r['recognized_reinsurance_receivable'] is None and r['reported_claim_cash_payments'] is None
 assert r['claim_adjustment'] is None and not r['numeric_successor_issued']
 assert r['arithmetic_current_portion_diagnostic_not_reported']=={'total_reserves_less_balance_sheet_line':532_000_000,'equals_expected_retained_payments':True,'treatment':'arithmetic coincidence only; not a tagged current reserve'}
def test_coverage_reinsurance_and_dedicated_assets_are_not_claims_or_surplus_cash():
 r=bind();t=r['narrative_terms']
 assert t['coverage_limit_per_occurrence']==120_000_000 and t['self_insured_retention_per_occurrence']==15_000_000
 assert t['reinsurance_scope']=='contract_exists_recovery_amount_not_disclosed'
 assert 'not surplus cash' in r['insurance_investments']['treatment']
 assert t['funding_scope']=='operating_cash_credit_and_debt_not_allocated'
 assert len(r['annual_reported_operating_cash_flow_inventory'])==5
def test_legacy_noncurrent_stress_is_preserved_value_neutrally_not_full_reserve():
 r=bind();d=r['scenario_diagnostics_not_candidate']
 assert d['bear']['legacy_claim']==4_897_000_000 and d['bear']['noncurrent_reserve_sensitivity']==1_464_000_000
 assert d['base']['legacy_claim']==4_165_000_000 and d['base']['noncurrent_reserve_sensitivity']==732_000_000
 assert d['bull']['legacy_claim']==3_433_000_000 and d['bull']['noncurrent_reserve_sensitivity']==0
 assert all(row['value_change']==0 and row['old_value']==row['reclassified_value'] for row in d.values())
@pytest.mark.parametrize('mutation',['missing','namespace','parent','role','negative','conflict','current_investment','noncurrent_investment','canonical_qname'])
def test_source_scope_and_investment_reconciliation_fail_closed(mutation):
 st,_,_,_,_=inputs();liab=next(r for r in st['facts'] if r['local_name']=='ProfessionalLiabilityRisks' and r['period_end']=='2026-06-30')
 if mutation=='missing':st['facts'].remove(liab)
 elif mutation=='namespace':liab['namespace']='http://wrong.example/20260630'
 elif mutation=='parent':liab['presentation_parents']=[]
 elif mutation=='role':liab['statement_roles']=[]
 elif mutation=='negative':liab['value']=-1
 elif mutation=='conflict':
  row=deepcopy(liab);row['value']+=1;st['facts'].append(row)
 elif mutation=='canonical_qname':liab['qname']='wrong:ProfessionalLiabilityRisks'
 else:
  local='InvestmentsFairValueDisclosure' if mutation=='current_investment' else 'AvailableForSaleSecuritiesDebtSecuritiesNoncurrent'
  next(r for r in st['facts'] if r['local_name']==local and r['period_end']=='2026-06-30')['value']+=1
 with pytest.raises(ValueError):bind(st=st)
def test_tampered_narrative_and_insufficient_annual_cash_fail_closed():
 _,n,cf,_,_=inputs();next(t for t in n['terms'] if t['name']=='next_12_month_payments')['value']=0
 with pytest.raises(ValueError):bind(n=n)
 cf=deepcopy(cf)
 for concept in ('NetCashProvidedByUsedInOperatingActivities','NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'):
  cf['facts']['us-gaap'][concept]['units']['USD']=[]
 with pytest.raises(ValueError,match='cash history'):bind(cf=cf)
 cf=deepcopy(inputs()[2])
 keep={'2022-12-31','2023-12-31','2024-12-31','2025-12-31'}
 for concept in ('NetCashProvidedByUsedInOperatingActivities','NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'):
  rows=cf['facts']['us-gaap'][concept]['units']['USD'];cf['facts']['us-gaap'][concept]['units']['USD']=[r for r in rows if r.get('end') in keep]
 with pytest.raises(ValueError,match='cash history'):bind(cf=cf)
def test_legacy_stress_policy_is_deepcopied_and_drift_rejected():
 p=professional_liability_policy('HCA');p['legacy_reserve_stress']['bear']=0
 assert professional_liability_policy('HCA')['legacy_reserve_stress']['bear']==1
 st,n,cf,sub,recipe=inputs()
 with pytest.raises(ValueError,match='policy identity'):bind_professional_liability_scope(p,st,n,cf,sub,recipe,cutoff='2026-08-14',source_root=ROOT/'output')
 recipe['scenarios']['base']['inputs']['preferred_equity']+=1
 with pytest.raises(ValueError,match='legacy professional reserve stress'):bind(recipe=recipe)
def test_real_frozen_workers_process_hca_scope_and_preserve_mck_gap():
 p=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),'--ticker','HCA','--ticker','MCK','--max-workers','2','--source-index',str(ROOT/'output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json')],cwd=ROOT,check=True,capture_output=True,text=True)
 summary=json.loads(p.stdout.strip().splitlines()[-1]);report=json.loads(Path(summary['report_path']).read_bytes());hca=next(r for r in report['rows'] if r['ticker']=='HCA')
 assert hca['status']=='implementation_gap' and hca['partial_professional_liability_scope']['status']=='noncurrent_reserve_sensitivity_reconciled_forward_cash_review'
 assert next(r for r in report['rows'] if r['ticker']=='MCK')['status']=='implementation_gap'
