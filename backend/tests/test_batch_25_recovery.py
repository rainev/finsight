from pathlib import Path
import json,sys,pytest
from app.us_valuation.batch_25 import BATCH_25_MANIFEST
from app.us_valuation.batch_25_recovery import build_batch_25_recovery_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));S=ROOT/'output/batch-25-sec-source-packets-20260831';X=ROOT/'output/batch-25-structural-sources-20260831';I=ROOT/'output/batch-25-history-run-c-20260831'
def R(t):return build_batch_25_recovery_result(ticker=t,source_root=S,structural_root=X)
def test_hona_recovered_equity_level():
 r=R('HONA');assert r['availability_type']=='conditional_estimate';assert tuple(r['scenario_range'][k] for k in ('low','base','high'))==pytest.approx((32.66396941464682,62.50110065334783,102.28654762315105));assert r['governed_assumptions']['ev_debt_bridge_applied'] is False;assert r['source_ledger']['equity_earnings_recovery']['debt_bridge_applied'] is False;assert r['reported_inputs']['current_h1_parent_earnings']==880e6;assert r['source_ledger']['equity_earnings_recovery']['current_h1_nci_earnings']==18e6
def test_public_and_runner(tmp_path):
 from run_batch_25_recovery import _public,run
 i=next(x for x in BATCH_25_MANIFEST if x.ticker=='HONA');r=R('HONA');p=_public(i,r);assert calculator_view(p)['model_family']=='equity_earnings';assert calculate(p,overrides={},manual_price=None)['result']==r['scenario_range'];assert 'source_ledger' not in json.dumps(p)
 q=run(initial_root=I,source_root=S,structural_root=X,output_root=tmp_path/'x');assert (q['attempted_count'],q['pass_count'],q['conditional_count'],q['withheld_count'],q['numeric_count'])==(1,2,8,0,10);assert not q['serving_artifacts_changed']
