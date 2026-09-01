from __future__ import annotations
import json,sys
from pathlib import Path
from app.us_valuation.batch_14 import BATCH_14_MANIFEST,BATCH_14_TICKERS
from app.us_valuation.batch_14_history import PASS_TICKERS,build_batch_14_history_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-14-sec-source-packets-20260829';STRUCT=ROOT/'output/batch-14-structural-sources-resume-20260829';EVENT=ROOT/'output/batch-14-event-sources-20260829'
def _result(t):return build_batch_14_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCT,event_root=EVENT)
def test_batch_14_exact_outcomes_and_ordered_ranges():
 rows={t:_result(t) for t in BATCH_14_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(PASS_TICKERS)=={'IDXX'};assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(BATCH_14_TICKERS)-set(PASS_TICKERS);assert all(0<=r['scenario_range']['low']<=r['scenario_range']['base']<=r['scenario_range']['high'] and r['scenario_range']['base']>0 for r in rows.values());assert all(r['history_reliability']['label'] in {'High','Medium','Low'} for r in rows.values())
def test_batch_14_directions_claims_and_event_states():
 for t in BATCH_14_TICKERS:
  r=_result(t);rows=r['scenario_rows'];assert rows[0]['wacc']>rows[1]['wacc']>rows[2]['wacc'];assert rows[0]['growth']<=rows[1]['growth']<=rows[2]['growth'];assert rows[0]['other_equity_claims']>=rows[1]['other_equity_claims']>=rows[2]['other_equity_claims'];assert rows[0]['shares']>=rows[1]['shares']>=rows[2]['shares'];assert rows[0]['conditional_value_per_share']<=rows[1]['conditional_value_per_share']<=rows[2]['conditional_value_per_share'];assert all(abs(row['raw_value_per_share']-r['source_ledger']['model_trace']['states'][row['name']]['intrinsic_value_per_share'])<1e-12 for row in rows)
 assert _result('TECH')['source_ledger']['bridge_sources'][-2]['reported_terms']['cash_consideration_per_share']==73.;assert _result('VRTX')['source_ledger']['bridge_sources'][-1]['reported_vs_estimated']=='source_proven_absent';assert _result('GILD')['governed_assumptions']['normalization_exclusions'];assert _result('MCK')['source_ledger']['bridge_reconciliation']['other_equity_claims']==(8_103_000_000.,)*3
def test_batch_14_public_contract_is_safe_and_calculable():
 from run_batch_14_history import _public
 for issuer in BATCH_14_MANIFEST:
  r=_result(issuer.ticker);public=_public(issuer,r);raw=json.dumps(public);assert public['availability_type']==r['availability_type'];assert public['scenario_range']['base']==r['scenario_range']['base'];assert calculator_view(public)['model_family']=='operating';assert calculate(public,overrides={},manual_price=None)['result']==r['scenario_range'];assert 'source_ledger' not in raw and 'model_trace' not in raw and 'reported_inputs' not in raw
