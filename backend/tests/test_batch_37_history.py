from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_37 import BATCH_37_MANIFEST, BATCH_37_TICKERS
from app.us_valuation.batch_37_history import CONDITIONAL_TICKERS, PASS_TICKERS, WITHHELD_TICKERS, build_batch_37_history_result


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-37-sec-source-packets-20260906"
STRUCTURAL = ROOT / "output/batch-37-structural-sources-20260906"
EVENTS = ROOT / "output/batch-37-event-sources-v2-20260906"
CACHE = ROOT / "output/batch-37-structural-cache-20260906"


def result(ticker):
    return build_batch_37_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS, structural_cache_root=CACHE)


def test_initial_partition_is_all_conditional():
    assert tuple(row.ticker for row in BATCH_37_MANIFEST) == BATCH_37_TICKERS
    assert not PASS_TICKERS and not WITHHELD_TICKERS
    assert CONDITIONAL_TICKERS == set(BATCH_37_TICKERS)


def test_all_ranges_are_finite_ordered_and_low_reliability():
    for ticker in BATCH_37_TICKERS:
        row = result(ticker)
        low, base, high = (row["scenario_range"][key] for key in ("low", "base", "high"))
        assert 0 <= low <= base <= high and base > 0
        assert row["availability_type"] == "conditional_estimate"
        assert row["history_reliability"]["label"] == "Low"
        assert row["governed_assumptions"]["history_years_used"] >= 3


def test_residual_income_and_fcff_scenarios_replay_exactly():
    from app.valuation.bank import residual_income_valuation
    from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
    for ticker in BATCH_37_TICKERS:
        row = result(ticker)
        for scenario in row["scenario_rows"]:
            if "book_value_per_share" in scenario:
                replay = residual_income_valuation(book_value_per_share=scenario["book_value_per_share"], current_roe=scenario["current_roe"], cost_of_equity=scenario["cost_of_equity"], current_payout_ratio=scenario["current_payout_ratio"], terminal_roe=scenario["terminal_roe"], terminal_growth=scenario["terminal_growth"], years=5)["intrinsic_value"]
            else:
                state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"], scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"], 0. if ticker != "OKE" else row["source_ledger"]["bridge_reconciliation"]["preferred"], scenario["other_equity_claims"] if ticker != "OKE" else row["source_ledger"]["bridge_reconciliation"]["nci"] + row["source_ledger"]["bridge_reconciliation"]["redeemable_nci"], scenario["shares"])
                replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"]
            assert max(0., replay) == pytest.approx(scenario["conditional_value_per_share"])


def test_ivz_impairment_and_aum_are_transparent_not_cash():
    row = result("IVZ")
    assert row["reported_inputs"]["raw_ttm_common_earnings"] == -309_200_000
    assert row["reported_inputs"]["normalization_adjustment"] == pytest.approx(1_417_971_000)
    assert row["reported_inputs"]["normalized_ttm_common_earnings"] == pytest.approx(1_108_771_000)
    assert row["reported_inputs"]["preferred_claim"] == 2_510_500_000
    event = row["source_ledger"]["event_sources"][0]
    assert event["reported_terms"]["july_aum"] == 2_447_100_000_000
    assert "never treated as cash" in row["warning"]


def test_erie_and_berkshire_class_economics_are_exact():
    erie = result("ERIE")
    assert erie["governed_assumptions"]["shares"][1] == 52_299_440
    context = erie["source_ledger"]["specialist_context"][0]
    assert context["management_fee_rate"]["value"] == .25
    assert context["management_fee_proceeds"]["value"] == 1_656_098_000
    berkshire = result("BRK.B")
    share = berkshire["source_ledger"]["equity_model_context"][-1]
    assert share["conversion_ratio"] == 1500
    assert share["value"] == 2_140_710_161
    assert berkshire["governed_assumptions"]["ev_debt_bridge_applied"] is False
    attribution = berkshire["source_ledger"]["earnings_attribution_context"]
    assert len(attribution) == 2
    assert attribution[0]["consolidated"]["value"] - attribution[0]["nci"]["value"] == attribution[0]["parent_attributable"]["value"]


def test_met_preferred_claim_rejects_zero_par_trap():
    row = result("MET")
    assert row["reported_inputs"]["preferred_claim"] == 2_905_000_000
    assert row["governed_assumptions"]["preferred_claim_status"] == "derived_current_preferred_claim"
    preferred_source = next(source for source in row["source_ledger"]["equity_model_context"] if source.get("source_kind") == "derived_period_specific_preferred_claim")
    assert any(source.get("value") == 76_000_000 for source in preferred_source["sources"])
    assert "zero par-value tag is rejected" in row["warning"]


def test_operating_data_debt_and_oke_claims_do_not_overlap():
    for ticker, debt in (("FDS", 1_389_701_000), ("MCO", 6_946_000_000)):
        bridge = result(ticker)["source_ledger"]["bridge_reconciliation"]
        assert bridge["debt_total"] == debt
        assert bridge["debt_components_sum"] == debt
    assert result("MCO")["reported_inputs"]["ttm_interest"] == 206_000_000
    assert all(source["concept"] == "InterestPaidNet" for source in result("MCO")["source_ledger"]["flow_sources"]["interest_expense"]["sources"])
    assert result("MCO")["governed_assumptions"]["cash_and_investments"][1] == 1_496_000_000
    oke = result("OKE")
    bridge = oke["source_ledger"]["bridge_reconciliation"]
    assert bridge["debt_and_finance_leases"] == 33_022_000_000
    assert bridge["other_equity_claims"] == 144_000_000
    event = oke["source_ledger"]["event_sources"][0]
    assert event["reported_terms"]["atm_common_stock_capacity"] == 1_000_000_000
    assert event["reported_terms"]["sales_completed_by_cutoff_documented"] is False
    assert oke["governed_assumptions"]["acquisition_reinvestment_burden"] == (353_000_000, 176_500_000, 0)
    assert oke["source_ledger"]["specialist_reinvestment"]["equity_method_impairment"]["value"] == 60_000_000
    assert oke["source_ledger"]["bridge_reconciliation"]["lease_scope"]["reported_vs_estimated"] == "source_bounded_absence_check"


def test_ndaq_nonrecurring_adjustments_and_revolver_are_separate():
    row = result("NDAQ")
    assert row["reported_inputs"]["normalization_adjustment"] == pytest.approx(-158_310_000)
    event = row["source_ledger"]["event_sources"][0]
    assert event["reported_terms"]["revolving_credit_capacity"] == 1_500_000_000
    assert row["governed_assumptions"]["ev_debt_bridge_applied"] is False


def test_public_model_identity_safety_and_calculator_parity():
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_37_history import _public
    for issuer in BATCH_37_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        expected = "fcff_dcf" if issuer.ticker in {"FDS", "MCO", "OKE"} else "residual_income"
        assert public["model_policy"]["primary"] == expected
        assert set(public["models"]) == {expected}
        assert public["availability_type"] == "conditional_estimate"
        for key in ("source_ledger", "reported_inputs", "runtime_source_verification", "event_sources", "model_trace", "residual_income_trace"):
            assert key not in encoded
        view = calculator_view(public)
        assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx(private["scenario_range"])
        assert calculate(public, overrides=view["defaults"], manual_price=None)["result"] == pytest.approx(private["scenario_range"])
