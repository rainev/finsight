from __future__ import annotations
import json,sys
from pathlib import Path
from app.us_valuation.batch_09_recovery import build_clx_recovery_result

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
SOURCE=ROOT/'output'/'batch-09-sec-source-packets-20260826'
STRUCTURAL=ROOT/'output'/'batch-09-clx-recovery-sources-local-a'/'structural-filing.json'

def test_clx_split_filing_recovery_is_source_backed_and_conditional():
 result=build_clx_recovery_result(source_root=SOURCE,recovered_structural=STRUCTURAL)
 assert result['availability_type']=='conditional_estimate'
 assert result['history_reliability']['label']=='Low'
 assert result['scenario_range']['low']<=result['scenario_range']['base']<=result['scenario_range']['high']
 assert result['scenario_range']['base']>0
 assert result['reported_inputs']['GOJO_pro_forma_revenue_diagnostic']==7_331_000_000
 assert result['reported_inputs']['venture_termination_payment_disclosed_not_added_back']==476_000_000
 assert result['source_ledger']['structural_fact_count']==1675
 assert result['source_ledger']['bridge_reconciliation']['commercial_paper_long_term_debt_and_finance_leases']==5_146_000_000

def test_clx_recovery_has_expected_sensitivity_directions():
 result=build_clx_recovery_result(source_root=SOURCE,recovered_structural=STRUCTURAL)
 rows=result['scenario_rows']
 assert rows[0]['growth']<rows[1]['growth']<rows[2]['growth']
 assert rows[0]['wacc']>rows[1]['wacc']>rows[2]['wacc']
 assert rows[0]['cash_conversion_margin']<rows[1]['cash_conversion_margin']<rows[2]['cash_conversion_margin']
 assert rows[0]['limited_liability_floor_applied']
 assert not rows[1]['limited_liability_floor_applied']

def test_clx_recovery_public_result_contains_no_private_sources(tmp_path):
 from app.us_valuation.batch_09 import BATCH_09_MANIFEST
 from run_batch_09_history import _public
 result=build_clx_recovery_result(source_root=SOURCE,recovered_structural=STRUCTURAL)
 public=_public(next(row for row in BATCH_09_MANIFEST if row.ticker=='CLX'),result)
 raw=json.dumps(public)
 assert public['availability_type']=='conditional_estimate'
 assert {key:public['scenario_range'][key] for key in ('low','base','high')}==result['scenario_range']
 assert 'source_ledger' not in raw and 'company_history_profile' not in raw
