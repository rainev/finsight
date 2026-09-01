from pathlib import Path
import json,sys,pytest
from app.us_valuation.batch_21 import BATCH_21_MANIFEST,BATCH_21_TICKERS
from app.us_valuation.batch_21_history import PASS_TICKERS,CONDITIONAL_TICKERS,EQUITY_EARNINGS_TICKERS,build_batch_21_history_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-21-sec-source-packets-20260831';STRUCT=ROOT/'output/batch-21-structural-sources-20260831'
def R(t):return build_batch_21_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCT)
EXPECTED={'RTX':(35.743855000836255,72.84565061777607,124.6239831081647),'EME':(217.12233784703986,435.859561905361,668.04289938177),'LHX':(69.08352051394239,152.4724672181145,263.63410016487416),'TXT':(36.58384850268102,71.32119440032285,149.02401864015843),'GWW':(286.9257018285964,484.20241160143104,723.87035943146),'CSX':(7.3448471629945775,14.856494079583952,31.268090058908186),'NSC':(26.508129394331853,80.69054422197621,180.46194243979474),'JBHT':(6.26851628770566,41.16947199779903,154.91625175509716),'EXPD':(52.560785911623014,90.52900016305611,207.19664504751066),'FAST':(9.020782791663601,14.873674387657928,22.707351851282105)}
def test_outcomes_ranges():
 rows={t:R(t) for t in BATCH_21_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(PASS_TICKERS);assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(CONDITIONAL_TICKERS)
 for t,r in rows.items():v=tuple(r['scenario_range'][k] for k in ('low','base','high'));assert v==pytest.approx(EXPECTED[t]);assert 0<=v[0]<=v[1]<=v[2] and v[1]>0;assert r['history_reliability']['label']=='Low'
def test_special_routes_and_claims():
 assert R('TXT')['governed_assumptions']['ev_debt_bridge_applied'] is False;assert R('RTX')['scenario_rows'][1]['other_equity_claims']==2.757e9;assert R('LHX')['scenario_rows'][1]['other_equity_claims']==1.628e9;assert R('NSC')['source_ledger']['event_sources'][0]['reported_terms']['cash_per_share_usd']==88.82
def test_public_and_calculator():
 from run_batch_21_history import _public
 for i in BATCH_21_MANIFEST:
  r=R(i.ticker);p=_public(i,r);raw=json.dumps(p);assert all(k not in raw for k in ('source_ledger','reported_inputs','model_trace'));assert calculator_view(p)['model_family']==('equity_earnings' if i.ticker in EQUITY_EARNINGS_TICKERS else 'operating');assert calculate(p,overrides={},manual_price=None)['result']==r['scenario_range']
def test_runner_preserves(tmp_path):
 from run_batch_21_history import run
 r=run(source_root=SOURCE,structural_root=STRUCT,output_root=tmp_path/'x');assert (r['pass_count'],r['conditional_count'],r['withheld_count'],r['numeric_count'])==(5,5,0,10);assert not r['serving_artifacts_changed'] and not r['watchlist_changed']
def test_arelle_outside_serving():
 for p in [ROOT/'backend/app/main.py',ROOT/'backend/app/deps.py',*sorted((ROOT/'backend/app/routers').glob('*.py'))]:assert 'arelle' not in p.read_text().lower()
