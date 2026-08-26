from pathlib import Path
import pytest
from app.us_valuation.batch_08 import BATCH_08_MANIFEST
from app.us_valuation.batch_08_recovery import evaluate_nclh,recover_aptv
from app.us_valuation.calculator import calculate
from run_batch_08_history import _public

SOURCE=Path('output/batch-08-sec-source-packets-20260826');STRUCTURAL=Path('output/batch-08-structural-sources-20260826')

def test_aptv_recovers_conditionally_from_only_comparable_continuing_h1():
 result=recover_aptv(source_root=SOURCE,structural_root=STRUCTURAL)
 assert result['availability_type']=='conditional_estimate'
 assert result['reported_inputs']=={'current_h1_parent_continuing_earnings':427_000_000,'prior_h1_parent_continuing_earnings':125_000_000}
 assert result['governed_assumptions']['history_years_used']==2
 assert result['governed_assumptions']['ev_debt_bridge_applied'] is False
 assert result['scenario_range']==pytest.approx({'low':17.19001610305958,'base':32.14604996941608,'high':53.10945273631841})
 assert result['source_ledger']['continuing_earnings']['nci_subtracted_again'] is False
 assert 'pre-spin annual' in result['warning']

def test_aptv_public_calculator_matches_recovery_base():
 issuer=next(row for row in BATCH_08_MANIFEST if row.ticker=='APTV');result=recover_aptv(source_root=SOURCE,structural_root=STRUCTURAL);public=_public(issuer,result)
 assert public['availability_type']=='conditional_estimate'
 assert public['public_assumptions']['forecast_mode']=='normalized_equity_earnings'
 assert calculate(public,overrides={},manual_price=None)['result']['base']==pytest.approx(result['scenario_range']['base'])
 assert 'source_ledger' not in public

def test_nclh_recovery_attempt_rejects_unfunded_equity_earnings_shortcut():
 result=evaluate_nclh(source_root=SOURCE,structural_root=STRUCTURAL)
 assert result['availability_type']=='not_available'
 attempt=result['recovery_attempt']
 assert attempt['attempt_number']==1
 assert attempt['outcome']=='withheld'
 assert attempt['hard_stop']=='newbuild_funding_and_dilution_unbounded'
 assert attempt['diagnostic']['ttm_parent_earnings']==762_344_000
 assert attempt['diagnostic']['post_shutdown_annual_earnings']==(166_178_000,910_257_000,423_246_000)
