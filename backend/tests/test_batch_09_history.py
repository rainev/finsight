import json
from pathlib import Path
import pytest
from app.us_valuation.batch_09 import BATCH_09_MANIFEST,BATCH_09_TICKERS
from app.us_valuation.batch_09_history import PASS_TICKERS,build_batch_09_history_result
from app.us_valuation.calculator import calculate,calculator_view
from run_batch_09_history import _public
SOURCE=Path('output/batch-09-sec-source-packets-20260826');STRUCTURAL=Path('output/batch-09-structural-sources-20260826')
def _result(t):return build_batch_09_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCTURAL)
def test_batch_09_is_two_pass_seven_conditional_one_withheld():
 assert PASS_TICKERS=={'BF.B','CL'}
 expected={'ADM':'conditional_estimate','BF.B':'available','STZ':'conditional_estimate','CLX':'not_available','KO':'conditional_estimate','CL':'available','TAP':'conditional_estimate','TGT':'conditional_estimate','DG':'conditional_estimate','GIS':'conditional_estimate'}
 assert tuple(expected)==BATCH_09_TICKERS
 for t,state in expected.items():
  r=_result(t);assert r['availability_type']==state
  if state=='not_available':assert r['scenario_range']=={'low':None,'base':None,'high':None}
  else:assert 0<=r['scenario_range']['low']<=r['scenario_range']['base']<=r['scenario_range']['high'] and r['scenario_range']['base']>0
def test_numeric_history_is_three_to_five_unique_periods_and_clx_fails_closed():
 for t in BATCH_09_TICKERS:
  r=_result(t)
  if t=='CLX':
   assert r['source_ledger']['structural_fact_count']==2
   assert r['source_ledger']['current_financial_bridge_fact_count']==0
   continue
  h=r['source_ledger']['company_history_profile'];assert 3<=len(h['annual_periods'])<=5;assert len(h['annual_periods'])==len(set(h['annual_periods']));assert h['full_history'] is True
def test_brown_forman_preserves_class_identity_and_total_economic_denominator():
 manifest=json.loads((SOURCE/'BF.B'/'source-manifest.json').read_text());assert manifest['ticker_alias_evidence']=={'frozen_ticker':'BF.B','sec_ticker':'BF-B','cik':'0000014693','basis':'SEC submissions uses dash notation for the same Brown-Forman Class B security; no issuer or share class substitution.'}
 r=_result('BF.B');bridge=r['source_ledger']['bridge_sources'];assert r['governed_assumptions']['shares'][1]==466_733_000
 assert any(row.get('member')=='CommonClassAAndNonvotingCommonStockMember' and row['value']==458_703_000 and row['unit']=='xbrli:shares' for row in bridge)
def test_ko_uses_current_q2_structural_reconstruction_not_stale_companyfacts():
 r=_result('KO');flows=r['source_ledger']['flow_sources']
 assert {k:flows[k]['value'] for k in flows}=={'revenue':50_129_000_000,'operating_cash_flow':16_342_000_000,'capital_expenditures':2_045_000_000,'interest_expense':1_566_000_000}
 assert all(row['period_end']=='2026-07-03' for row in flows.values())
 assert r['source_ledger']['controlling_filing']['accession']=='0001628280-26-050503'
def test_current_claim_bridges_and_operating_supplier_finance_are_explicit():
 assert _result('ADM')['source_ledger']['bridge_reconciliation']['debt_and_finance_leases']==8_011_000_000
 assert _result('TAP')['source_ledger']['bridge_reconciliation']['nci_or_temporary_equity']==(289_200_000,)*3
 assert _result('TGT')['source_ledger']['bridge_reconciliation']['debt_and_finance_leases']==15_415_000_000
 assert _result('DG')['source_ledger']['bridge_reconciliation']['debt_and_finance_leases']==4_576_408_000
 assert any(row.get('field')=='debt_includes_lease_obligation' for row in _result('DG')['source_ledger']['bridge_sources'])
 gis=_result('GIS');assert gis['source_ledger']['bridge_reconciliation']['cash_and_investments']==418_200_000
 assert any(row.get('field')=='continuing_cash_and_securities' for row in gis['source_ledger']['bridge_sources'])
 for t in ('ADM','KO','CL','TAP','TGT','DG','GIS'):assert 'not subtracted again' in _result(t)['source_ledger']['bridge_reconciliation']['supplier_finance_and_operating_leases']
def test_public_artifacts_match_and_calculators_fail_closed_or_replay():
 for issuer in BATCH_09_MANIFEST:
  r=_result(issuer.ticker);p=_public(issuer,r);assert p['availability_type']==r['availability_type'];assert p['scenario_range']['base']==r['scenario_range']['base'];assert 'source_ledger' not in p
  if r['availability_type']=='not_available':assert calculator_view(p)['can_calculate'] is False
  else:assert calculate(p,overrides={},manual_price=None)['result']['base']==pytest.approx(r['scenario_range']['base'])
