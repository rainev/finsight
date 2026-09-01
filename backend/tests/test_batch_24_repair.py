from pathlib import Path
import json,sys,pytest
from app.us_valuation.batch_24 import BATCH_24_MANIFEST,BATCH_24_TICKERS
from app.us_valuation.batch_24_repair import ATTEMPTED_TICKERS,REPAIRED_PASS_TICKERS,REPAIRED_CONDITIONAL_TICKERS,build_batch_24_repair_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-24-sec-source-packets-20260831';STRUCT=ROOT/'output/batch-24-structural-sources-20260831';INITIAL=ROOT/'output/batch-24-history-run-e-20260831'
def R(t):return build_batch_24_repair_result(ticker=t,source_root=SOURCE,structural_root=STRUCT)
EXPECTED={'NOC':(88.04214304931043,212.12894583631672,410.16789264750224),'TDG':(0.,285.06252027804044,729.4960847584991),'BLDR':(21.781785084149906,72.40667125273195,181.61927313845578),'TT':(98.97947940007514,200.69091592978498,347.78655928213783),'GNRC':(25.427398964060263,63.45759813781495,127.38502328926283),'HII':(0.,137.6861080081588,270.41902173472135),'XYL':(21.792671758837933,46.83099701332002,85.60971873338417),'UBER':(4.703856116276312,48.21775204041888,108.24779554442452),'ETN':(42.44055247200447,104.59308008804425,193.4932476286916),'ALLE':(62.13155416689109,113.44553498770335,182.5436709024724)}
def test_repair_outcomes_ranges():
 rows={t:R(t) for t in BATCH_24_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(REPAIRED_PASS_TICKERS)=={'BLDR','TT','XYL','ALLE'};assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(REPAIRED_CONDITIONAL_TICKERS);assert ATTEMPTED_TICKERS=={'NOC','TDG','GNRC','HII','UBER','ETN'}
 for t,r in rows.items():assert tuple(r['scenario_range'][k] for k in ('low','base','high'))==pytest.approx(EXPECTED[t]);assert 0<=r['scenario_range']['low']<=r['scenario_range']['base']<=r['scenario_range']['high'] and r['scenario_range']['base']>0
def test_all_attempts_retain_conditions():
 for t in ATTEMPTED_TICKERS:
  r=R(t);assert r['availability_type']=='conditional_estimate';x=r['source_ledger']['whole_conditional_repair'];assert x['repair_attempted'] is True and x['release_condition']
 for t in {'BLDR','TT','XYL','ALLE'}:assert R(t)['source_ledger']['whole_conditional_repair']['repair_attempted'] is False
def test_public_safe_and_calculable():
 from run_batch_24_repair import _public
 for i in BATCH_24_MANIFEST:
  r=R(i.ticker);p=_public(i,r);raw=json.dumps(p);assert p['availability_type']==r['availability_type'] and all(p['scenario_range'][k]==r['scenario_range'][k] for k in ('low','base','high'));assert all(k not in raw for k in ('source_ledger','reported_inputs','whole_conditional_repair'));assert calculator_view(p)['model_family']=='operating';assert calculate(p,overrides={},manual_price=None)['result']==r['scenario_range']
def test_runner_attempts_exact_six(tmp_path):
 from run_batch_24_repair import run
 r=run(initial_root=INITIAL,source_root=SOURCE,structural_root=STRUCT,output_root=tmp_path/'x');assert r['attempted_count']==6;assert (r['pass_count'],r['conditional_count'],r['withheld_count'],r['numeric_count'])==(4,6,0,10);assert r['upgraded_to_pass_tickers']==[];assert r['still_conditional_tickers']==['NOC','TDG','GNRC','HII','UBER','ETN'];assert not r['serving_artifacts_changed'] and not r['watchlist_changed_during_staging'] and not r['withheld_register_changed_during_staging']
def test_arelle_outside_serving():
 for p in [ROOT/'backend/app/main.py',ROOT/'backend/app/deps.py',*sorted((ROOT/'backend/app/routers').glob('*.py'))]:assert 'arelle' not in p.read_text().lower()
