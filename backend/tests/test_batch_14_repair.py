from __future__ import annotations
import json,sys
from pathlib import Path
from app.us_valuation.batch_14 import BATCH_14_MANIFEST,BATCH_14_TICKERS
from app.us_valuation.batch_14_history import build_batch_14_history_result
from app.us_valuation.batch_14_repair import FINAL_PASS_TICKERS,REPAIRED_PASS_TICKERS,build_batch_14_repair_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-14-sec-source-packets-20260829';STRUCT=ROOT/'output/batch-14-structural-sources-resume-20260829';EVENT=ROOT/'output/batch-14-event-sources-20260829'
def _initial(t):return build_batch_14_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCT,event_root=EVENT)
def _repair(t):return build_batch_14_repair_result(ticker=t,source_root=SOURCE,structural_root=STRUCT,event_root=EVENT)
def test_batch_14_repair_changes_only_hca_regn_classification():
 rows={t:_repair(t) for t in BATCH_14_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(FINAL_PASS_TICKERS);assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(BATCH_14_TICKERS)-set(FINAL_PASS_TICKERS)
 for ticker in BATCH_14_TICKERS:
  before,after=_initial(ticker),rows[ticker];assert before['scenario_range']==after['scenario_range'];assert before['scenario_rows']==after['scenario_rows']
  if ticker not in REPAIRED_PASS_TICKERS:assert before==after
def test_hca_regn_repairs_are_below_materiality_threshold_and_source_bound():
 hca,regn=_repair('HCA'),_repair('REGN');assert hca['governed_assumptions']['materiality_assessment']['impact_ratio']<.05;assert hca['source_ledger']['pass_repair']['sources'][1]['reported_terms']['expected_next_twelve_month_claim_payments']==573_000_000.;assessment=regn['governed_assumptions']['materiality_assessment'];assert assessment['acquired_iprd_impact_ratio']<.01 and assessment['intangible_acquisition_cash_impact_ratio']<.01 and assessment['contingent_consideration_impact_ratio']<.01;assert assessment['collaboration_revenue_current_h1']>assessment['collaboration_revenue_prior_h1']
def test_batch_14_repair_public_contract_and_calculator():
 from run_batch_14_repair import _public
 for issuer in BATCH_14_MANIFEST:
  result=_repair(issuer.ticker);public=_public(issuer,result);raw=json.dumps(public);assert public['availability_type']==result['availability_type'];assert public['scenario_range']['base']==result['scenario_range']['base'];assert calculator_view(public)['model_family']=='operating';assert calculate(public,overrides={},manual_price=None)['result']==result['scenario_range'];assert 'source_ledger' not in raw and 'pass_repair' not in raw and 'RELIABILITY_PAYLOAD_INVALID' not in raw
  if issuer.ticker in REPAIRED_PASS_TICKERS:assert public['reliability']['model_cap']=='High' and public['reliability']['source_cap']=='High' and public['reliability']['accounting_impact_ratio']==0
