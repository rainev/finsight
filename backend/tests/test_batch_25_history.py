from pathlib import Path
import json,sys,pytest
from app.us_valuation.batch_25 import BATCH_25_MANIFEST,BATCH_25_TICKERS
from app.us_valuation.batch_25_history import PASS_TICKERS,CONDITIONAL_TICKERS,WITHHELD_TICKERS,build_batch_25_history_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-25-sec-source-packets-20260831';STRUCT=ROOT/'output/batch-25-structural-sources-20260831'
def R(t):return build_batch_25_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCT)
EXPECTED={'FTV':(12.587779487454403,33.326465670256106,57.15449473134972),'DD':(17.087958708278855,64.14495831691409,96.69836355689624),'IR':(21.267046428267115,47.041204909563284,79.49325688539665),'OTIS':(20.976367353265154,37.198108346885824,62.58178819933995),'CARR':(1.9637814895145458,16.251376910684073,35.96658553120981),'VLTO':(32.290878163020025,51.29770613927709,75.96467540738753),'GEV':(48.63496471613976,125.09539756421697,307.1382957394543),'FERG':(27.28291180858203,70.42904557537767,145.48560886947817),'FDXF':(0.,33.22895668870226,63.27727796011994)}
def test_outcomes_ranges():
 rows={t:R(t) for t in BATCH_25_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(PASS_TICKERS)=={'IR','OTIS'};assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(CONDITIONAL_TICKERS);assert {t for t,r in rows.items() if r['availability_type']=='not_available'}==set(WITHHELD_TICKERS)=={'HONA'}
 for t,v in EXPECTED.items():assert tuple(rows[t]['scenario_range'][k] for k in ('low','base','high'))==pytest.approx(v)
 assert rows['HONA']['scenario_range']=={'low':None,'base':None,'high':None}
def test_successors_and_public_safety():
 assert R('FDXF')['reported_inputs']['ttm_cash_fcff']<0 and R('FDXF')['scenario_range']['low']==0;assert R('HONA')['reported_inputs']['annualized_h1_cash_fcff']>0 and R('HONA')['availability_type']=='not_available'
 assert R('GEV')['scenario_rows'][1]['cash_and_investments']==12.720e9;assert R('FERG')['source_ledger']['event_sources'][1]['value']==1.6e9
 from run_batch_25_history import _public
 for i in BATCH_25_MANIFEST:
  r=R(i.ticker);p=_public(i,r);raw=json.dumps(p);assert 'source_ledger' not in raw and p['availability_type']==r['availability_type'];view=calculator_view(p);assert view['can_calculate']==(r['availability_type']!='not_available')
  if view['can_calculate']:assert calculate(p,overrides={},manual_price=None)['result']==r['scenario_range']
def test_runner_preserves(tmp_path):
 from run_batch_25_history import run
 r=run(source_root=SOURCE,structural_root=STRUCT,output_root=tmp_path/'x');assert (r['pass_count'],r['conditional_count'],r['withheld_count'],r['numeric_count'])==(2,7,1,9);assert r['withheld_tickers']==['HONA'];assert not r['serving_artifacts_changed'] and not r['watchlist_changed']
def test_arelle_outside_serving():
 for p in [ROOT/'backend/app/main.py',ROOT/'backend/app/deps.py',*sorted((ROOT/'backend/app/routers').glob('*.py'))]:assert 'arelle' not in p.read_text().lower()
