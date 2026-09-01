from pathlib import Path
import json,sys,pytest
from app.us_valuation.batch_23 import BATCH_23_MANIFEST,BATCH_23_TICKERS
from app.us_valuation.batch_23_repair import ATTEMPTED_TICKERS,REPAIRED_PASS_TICKERS,REPAIRED_CONDITIONAL_TICKERS,build_batch_23_repair_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-23-sec-source-packets-20260831';STRUCT=ROOT/'output/batch-23-structural-sources-20260831';REPAIR=ROOT/'output/batch-23-repair-sources-20260831';INITIAL=ROOT/'output/batch-23-history-run-c-20260831'
def R(t):return build_batch_23_repair_result(ticker=t,initial_source_root=SOURCE,structural_root=STRUCT,repair_source_root=REPAIR)
EXPECTED={'AME':(48.45014916948007,104.52681204113686,173.27654805084276),'CHRW':(14.798420399149066,47.48124838589168,113.03694451238101),'FDX':(77.03464011602604,129.24145610107348,216.2202882010991),'PWR':(64.78810145210886,163.70936634287673,289.3670372535367),'RSG':(37.797779924407266,82.80880861875114,158.6435316486605),'URI':(0.,12.33671212702337,165.6850811981083),'AXON':(14.565501601258148,48.3228234917257,140.53384274513604),'LII':(95.15791967587914,209.6046488513602,379.7750837685485),'UPS':(30.350610895864627,61.37112889336235,124.61938641091136),'LDOS':(49.28415144084905,116.72141537538658,236.15171584384663)}
def test_repair_outcomes_ranges():
 rows={t:R(t) for t in BATCH_23_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(REPAIRED_PASS_TICKERS)=={'RSG','URI','LII'};assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(REPAIRED_CONDITIONAL_TICKERS);assert ATTEMPTED_TICKERS=={'AME','CHRW','FDX','PWR','URI','AXON','UPS','LDOS'}
 for t,r in rows.items():assert tuple(r['scenario_range'][k] for k in ('low','base','high'))==pytest.approx(EXPECTED[t]);assert 0<=r['scenario_range']['low']<=r['scenario_range']['base']<=r['scenario_range']['high'] and r['scenario_range']['base']>0
def test_uri_exact_capex_repair_and_no_zero_substitution():
 r=R('URI');assert r['reported_inputs']['ttm_reinvestment']==5.110e9;assert r['source_ledger']['uri_exact_capex_repair']=={'annual_accession':'0001067701-26-000007','fy2025_fleet_capex':4.149e9,'fy2025_other_capex':379e6,'ttm_capex':5.110e9,'zero_substitution_used':False};assert r['availability_type']=='available';assert r['scenario_rows'][0]['raw_value_per_share']<0 and r['scenario_range']['low']==0
def test_other_attempts_preserve_values_and_release_conditions():
 for t in ATTEMPTED_TICKERS-{'URI'}:
  r=R(t);assert r['availability_type']=='conditional_estimate';x=r['source_ledger']['whole_conditional_repair'];assert x['repair_attempted'] is True and x['release_condition']
 for t in {'RSG','LII'}:assert R(t)['source_ledger']['whole_conditional_repair']['repair_attempted'] is False
def test_public_safe_and_calculable():
 from run_batch_23_repair import _public
 for i in BATCH_23_MANIFEST:
  r=R(i.ticker);p=_public(i,r);raw=json.dumps(p);assert p['availability_type']==r['availability_type'] and all(p['scenario_range'][k]==r['scenario_range'][k] for k in ('low','base','high'));assert all(k not in raw for k in ('source_ledger','reported_inputs','uri_exact_capex_repair'));assert calculator_view(p)['model_family']=='operating';assert calculate(p,overrides={},manual_price=None)['result']==r['scenario_range']
def test_runner_attempts_exact_eight_and_preserves(tmp_path):
 from run_batch_23_repair import run
 r=run(initial_root=INITIAL,source_root=SOURCE,structural_root=STRUCT,repair_source_root=REPAIR,output_root=tmp_path/'x');assert r['attempted_count']==8;assert (r['pass_count'],r['conditional_count'],r['withheld_count'],r['numeric_count'])==(3,7,0,10);assert r['upgraded_to_pass_tickers']==['URI'];assert r['still_conditional_tickers']==['AME','CHRW','FDX','PWR','AXON','UPS','LDOS'];assert not r['serving_artifacts_changed'] and not r['watchlist_changed_during_staging'] and not r['withheld_register_changed_during_staging']
def test_arelle_outside_serving():
 for p in [ROOT/'backend/app/main.py',ROOT/'backend/app/deps.py',*sorted((ROOT/'backend/app/routers').glob('*.py'))]:assert 'arelle' not in p.read_text().lower()
