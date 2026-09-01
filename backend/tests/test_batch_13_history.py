from __future__ import annotations
import json,sys
from pathlib import Path
from app.us_valuation.batch_13 import BATCH_13_TICKERS,BATCH_13_MANIFEST
from app.us_valuation.batch_13_history import build_batch_13_history_result
from app.us_valuation.calculator import calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output'/'batch-13-sec-source-packets-20260829';STRUCT=ROOT/'output'/'batch-13-structural-sources-20260829'
def _result(t):return build_batch_13_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCT)
def test_batch_13_exact_outcomes_and_ordered_ranges():
 rows={t:_result(t) for t in BATCH_13_TICKERS};assert all(r['availability_type']=='conditional_estimate' for r in rows.values());assert all(0<=r['scenario_range']['low']<=r['scenario_range']['base']<=r['scenario_range']['high'] and r['scenario_range']['base']>0 for r in rows.values());assert all(r['history_reliability']['label']=='Low' for r in rows.values())
def test_batch_13_directions_and_claims():
 for t in BATCH_13_TICKERS:
  r=_result(t);rows=r['scenario_rows'];assert rows[0]['conditional_value_per_share']<=rows[1]['conditional_value_per_share']<=rows[2]['conditional_value_per_share']
  if t!='UNH':assert rows[0]['wacc']>rows[1]['wacc']>rows[2]['wacc'];assert rows[0]['growth']<=rows[1]['growth']<=rows[2]['growth']
 assert _result('JNJ')['source_ledger']['bridge_reconciliation']['other_equity_claims']==(4_523_000_000.,)*3;assert _result('MRK')['source_ledger']['bridge_reconciliation']['other_equity_claims']==(1_126_000_000.,)*3;assert _result('AMGN')['source_ledger']['bridge_reconciliation']['other_equity_claims']==(7_771_000_000.,3_971_000_000.,171_000_000.);assert _result('COO')['source_ledger']['bridge_reconciliation']['other_equity_claims']==(272_500_000.,)*3;assert _result('CAH')['source_ledger']['bridge_reconciliation']['other_equity_claims']==(4_488_000_000.,)*3;unh=_result('UNH');assert unh['source_ledger']['bridge_treatment'].startswith('Equity-level residual-income');assert all(unh['scenario_rows'][i]['cost_of_equity']>unh['scenario_rows'][i+1]['cost_of_equity'] for i in range(2));assert all(abs(row['raw_value_per_share']-unh['source_ledger']['residual_income_trace']['states'][row['name']]['intrinsic_value'])<1e-12 for row in unh['scenario_rows'])
 assert _result('PFE')['reported_inputs']['valuation_cash_fcff']==_result('PFE')['reported_inputs']['ttm_cash_fcff']-180_000_000.;assert _result('MRK')['governed_assumptions']['normalization_exclusions'];assert _result('DHR')['source_ledger']['bridge_reconciliation']['valuation_revenue_formula']
def test_batch_13_public_contract_is_safe():
 from run_batch_13_history import _public
 for issuer in BATCH_13_MANIFEST:
  r=_result(issuer.ticker);public=_public(issuer,r);raw=json.dumps(public);assert public['availability_type']=='conditional_estimate';assert public['scenario_range']['base']==r['scenario_range']['base'];assert 'source_ledger' not in raw and 'model_trace' not in raw
  if issuer.ticker=='UNH':assert calculator_view(public)['model_family']=='equity_earnings'
