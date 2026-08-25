from pathlib import Path

from app.us_valuation.batch_04 import BATCH_04_TICKERS
from app.us_valuation.batch_04_launch_first import build_batch_04_launch_first_result

SOURCE=Path('output/batch-04-sec-source-packets-20260825')
STRUCTURAL=Path('output/batch-04-structural-sources-20260825')


def test_all_ten_batch_04_baselines_are_conditional_low_and_ordered() -> None:
    for ticker in BATCH_04_TICKERS:
        result=build_batch_04_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)
        values=result['scenario_range']
        assert 0 <= values['low'] <= values['base'] <= values['high']
        assert values['base'] > 0
        assert result['baseline']['availability_type']=='conditional_estimate'
        assert result['baseline']['confidence']=='Low'
        assert [row['outcome'] for row in result['baseline']['fallback_attempts']]==['rejected','selected']


def test_ford_credit_debt_is_not_subtracted_as_industrial_debt() -> None:
    result=build_batch_04_launch_first_result(ticker='F',source_root=SOURCE,structural_root=STRUCTURAL)
    assert result['method']=='ford_normalized_equity_earnings_baseline'
    assert result['governed_assumptions']['route_is_captive_finance_sotp'] is False
    assert result['governed_assumptions']['ev_debt_bridge_applied'] is False
    assert 'not a Ford Credit SOTP' in result['source_ledger']['ford_credit_treatment']


def test_higher_risk_states_have_lower_values_for_standard_models() -> None:
    for ticker in BATCH_04_TICKERS[1:]:
        rows=build_batch_04_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)['scenario_rows']
        assert rows[0]['wacc'] > rows[1]['wacc'] > rows[2]['wacc']
        assert rows[0]['conditional_value_per_share'] <= rows[1]['conditional_value_per_share'] <= rows[2]['conditional_value_per_share']


def test_standard_bridge_constants_are_source_traced_and_mcd_scale_is_explicit() -> None:
    for ticker in BATCH_04_TICKERS[1:]:
        result=build_batch_04_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)
        sources=result['source_ledger']['bridge_sources']
        assert len(sources)>=3
        assert any(row.get('unit')=='shares' for row in sources)
        assert result['source_ledger']['bridge_reconciliation']['cash_and_investments']>=0
    mcd=build_batch_04_launch_first_result(ticker='MCD',source_root=SOURCE,structural_root=STRUCTURAL)
    scaled=[row for row in mcd['source_ledger']['bridge_sources'] if row.get('source_kind')=='companyfacts_scaled_disclosure']
    assert scaled[0]['reported_value_millions']==712.3
    assert scaled[0]['value']==712_300_000


def test_mgm_and_mcd_operating_leases_stay_inside_operating_cash() -> None:
    for ticker in ('MCD','MGM'):
        result=build_batch_04_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)
        assert 'not subtracted again as debt' in result['source_ledger']['operating_lease_treatment']


def test_missing_nci_is_not_labeled_reported_zero() -> None:
    for ticker in ('LOW','MCD','TJX','NKE','HD','ROST'):
        result=build_batch_04_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)
        bridge=result['source_ledger']['bridge_reconciliation']
        assert bridge['reported_nci'] is None
        assert bridge['nci_status']=='unresolved_covered_by_asset_reserve'
        ranges=[row for row in result['source_ledger']['bridge_sources'] if row.get('field')=='unresolved_nci_and_other_claims']
        assert ranges[0]['reported_vs_estimated']=='estimated_range'
