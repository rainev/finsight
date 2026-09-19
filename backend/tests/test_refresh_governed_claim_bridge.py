from copy import deepcopy
import json
from pathlib import Path
import subprocess,sys,pytest
from app.us_valuation.refresh_governed_claim_bridge import governed_claim_bridge_policy,bind_governed_claim_bridge

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'output/us-refresh-group-verification/6d20e3a144bb41dccec7d5e59b5a241b3f140bda0abb3fd132c5f63f77010ccc/report.json'
def inputs():
 report=json.loads(REPORT.read_bytes());row=next(r for r in report['rows'] if r['ticker']=='MCK')
 recipe=json.loads((ROOT/'output/us-refresh-runtime/recipes/MCK.json').read_bytes())
 return recipe,row['partial_subsidiary_ownership_scope'],row['partial_settlement_payment_bridge'],row['partial_public_contract_evidence']
def bind(recipe=None,ownership=None,settlement=None,public=None):
 r,o,s,p=inputs();return bind_governed_claim_bridge(governed_claim_bridge_policy('MCK'),recipe or r,ownership or o,settlement or s,public or p)

def test_real_claim_semantics_are_source_classified_once_and_value_neutral():
 r=bind();assert r['ordinary_nci_claim']==376_000_000 and r['redeemable_nci_claim']==2_563_000_000
 assert r['approved_ownership_claim']==2_939_000_000 and r['legal_conditional_claim']==5_164_000_000
 assert r['legacy_mixed_claim']==8_103_000_000 and r['parent_conversion_shares'] is None
 assert r['claim_adjustment'] is None and not r['numeric_successor_issued']
 assert all(v['value_change']==0 and v['proposed_preferred_equity']==0 for v in r['scenario_checks'].values())
 assert all(v['proposed_noncontrolling_interests']==2_939_000_000 for v in r['scenario_checks'].values())
def test_floor_event_movements_and_proceeds_stay_nonadditive_diagnostics():
 r=bind();d=r['nonadditive_diagnostics']
 assert d['core_floor']==525_000_000 and d['apollo_transaction_descriptor']['transaction_enterprise_valuation']==13_000_000_000
 assert d['annual_fair_value_adjustment']==87_000_000 and d['annual_core_redemption_adjustment']==122_000_000
 assert sum(d['current_redemption_movements'].values())==374_000_000 and d['net_financing_proceeds']==1_238_000_000
 assert r['legacy_mixed_claim']==r['approved_ownership_claim']+r['legal_conditional_claim']
@pytest.mark.parametrize('mutation',['source_total','floor','public_claim','public_numeric','economic_claim','parent_shares','actual_liability','actual_cash','legal_claim','legacy','ownership_numeric','settlement_numeric','offset_components'])
def test_unknowns_promotions_conflicts_and_legacy_drift_fail_closed(mutation):
 recipe,o,s,p=inputs()
 if mutation=='source_total':o['ownership_carrying_proof']['source_total']+=1
 elif mutation=='floor':p['core_put']['source_arithmetic_floor']=o['reported_redeemable_carrying']+1
 elif mutation=='public_claim':p['claim_adjustment']=1
 elif mutation=='public_numeric':p['numeric_successor_issued']=True
 elif mutation=='economic_claim':o['instrument_economic_basis']['economic_claim']=1
 elif mutation=='parent_shares':o['instrument_economic_basis']['parent_conversion_shares']=1
 elif mutation=='actual_liability':s['payment_only_bridge']['actual_post_period_liability']=1
 elif mutation=='actual_cash':s['payment_only_bridge']['actual_post_period_cash']=1
 elif mutation=='legal_claim':s['payment_only_bridge']['claim_adjustment']=1
 elif mutation=='ownership_numeric':o['numeric_successor_issued']=True
 elif mutation=='settlement_numeric':s['numeric_successor_issued']=True
 elif mutation=='offset_components':o['reported_ordinary_carrying']+=1;o['reported_redeemable_carrying']-=1
 else:recipe['scenarios']['base']['inputs']['preferred_equity']+=1
 with pytest.raises(ValueError):bind(recipe,o,s,p)
def test_policy_contains_no_filing_amounts_dates_or_alternative_quantity():
 policy=governed_claim_bridge_policy('MCK');assert set(policy)=={'version','ticker','cik','ownership_basis','legal_basis'}
 assert '2939' not in json.dumps(policy) and '5164' not in json.dumps(policy)
def test_real_frozen_workers_execute_governed_bridge_preserve_lhx_and_full_gaps():
 p=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),'--ticker','MCK','--ticker','LHX','--max-workers','2',
  '--source-index',str(ROOT/'output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json')],cwd=ROOT,check=True,capture_output=True,text=True)
 summary=json.loads(p.stdout.strip().splitlines()[-1]);report=json.loads(Path(summary['report_path']).read_bytes())
 mck=next(r for r in report['rows'] if r['ticker']=='MCK');assert mck['status']=='implementation_gap'
 assert mck['partial_governed_claim_bridge']['status']=='ownership_carrying_treatment_approved_legal_bridge_review'
 assert all(v['value_change']==0 for v in mck['partial_governed_claim_bridge']['scenario_checks'].values())
 lhx=next(r for r in report['rows'] if r['ticker']=='LHX');assert lhx['status']=='implementation_gap' and 'partial_governed_claim_bridge' not in lhx
