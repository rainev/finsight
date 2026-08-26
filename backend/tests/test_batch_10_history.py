from __future__ import annotations
import json,sys
from pathlib import Path
from app.us_valuation.batch_10 import BATCH_10_TICKERS
from app.us_valuation.batch_10_history import PASS_TICKERS,build_batch_10_history_result
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output'/'batch-10-sec-source-packets-20260826';STRUCT=ROOT/'output'/'batch-10-structural-sources-20260826'
def _result(t):return build_batch_10_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCT)
def test_batch_10_exact_outcomes_and_ranges():
 rows={t:_result(t) for t in BATCH_10_TICKERS}
 assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(PASS_TICKERS)
 assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}=={'MKC','SJM','TSN'}
 assert {t for t,r in rows.items() if r['availability_type']=='not_available'}=={'KMB'}
 assert all(0<=r['scenario_range']['low']<=r['scenario_range']['base']<=r['scenario_range']['high'] and r['scenario_range']['base']>0 for t,r in rows.items() if t!='KMB')
 assert all(r['governed_assumptions']['history_years_used']>=3 for t,r in rows.items() if t!='KMB')
def test_batch_10_sensitivity_and_bridge_directions():
 for t in BATCH_10_TICKERS:
  if t=='KMB':continue
  r=_result(t);rows=r['scenario_rows'];assert rows[0]['wacc']>rows[1]['wacc']>rows[2]['wacc'];assert rows[0]['cash_conversion_margin']<=rows[1]['cash_conversion_margin']<=rows[2]['cash_conversion_margin'];assert rows[0]['conditional_value_per_share']<=rows[1]['conditional_value_per_share']<=rows[2]['conditional_value_per_share']
 assert _result('PG')['source_ledger']['bridge_reconciliation']['preferred_nci_and_redeemable_claims']==230_000_000
 assert _result('WMT')['source_ledger']['bridge_reconciliation']['debt_and_finance_leases']==58_129_000_000
 assert _result('HSY')['source_ledger']['bridge_reconciliation']['debt_and_finance_leases']==5_610_680_000
 assert _result('MKC')['source_ledger']['bridge_reconciliation']['debt_and_finance_leases']==5_028_500_000
 assert _result('KMB')['scenario_range']=={'low':None,'base':None,'high':None}
def test_batch_10_public_contract_has_no_private_sources():
 from app.us_valuation.batch_10 import BATCH_10_MANIFEST
 from run_batch_10_history import _public
 for issuer in BATCH_10_MANIFEST:
  r=_result(issuer.ticker);public=_public(issuer,r);raw=json.dumps(public);assert public['availability_type']==r['availability_type'];assert public['scenario_range']['base']==r['scenario_range']['base'];assert 'source_ledger' not in raw and 'company_history_profile' not in raw
