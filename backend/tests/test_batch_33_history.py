from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_33 import BATCH_33_MANIFEST, BATCH_33_TICKERS
from app.us_valuation.batch_33_history import PASS_TICKERS, CONDITIONAL_TICKERS, WITHHELD_TICKERS, build_batch_33_history_result
from app.us_valuation.calculator import calculate, calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-33-sec-source-packets-20260903"
STRUCTURAL = ROOT / "output/batch-33-structural-sources-20260903"
EVENTS = ROOT / "output/batch-33-event-sources-20260903"


def result(ticker):
    return build_batch_33_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS)


def test_outcomes_ranges_and_denominator():
    rows = {ticker: result(ticker) for ticker in BATCH_33_TICKERS}
    assert set(PASS_TICKERS) == {"MRSH"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(CONDITIONAL_TICKERS) == set(BATCH_33_TICKERS) - {"MRSH"}
    assert not WITHHELD_TICKERS and len(rows) == 10
    for row in rows.values():
        values = row["scenario_range"]
        assert 0 < values["low"] <= values["base"] <= values["high"]
        assert row["history_reliability"]["label"] == "Low"


def test_exact_controlled_ranges_do_not_drift():
    expected = {
        "AXP": (45.78965102098829, 75.72258209404568, 105.8981422755196),
        "AFL": (47.022567382482706, 75.29040795589268, 110.35439142978144),
        "AIG": (36.98540422941858, 63.88295757209449, 103.28947736843519),
        "WRB": (20.713664867684567, 31.402261882466927, 44.785761508562764),
        "CINF": (78.25068949301883, 125.54448557709331, 180.36792368726464),
        "FITB": (21.617080195420307, 34.829033947926355, 47.744684954202874),
        "MTB": (124.43931439821407, 186.13172009729294, 253.6301076090076),
        "BEN": (9.465164771017143, 14.480240306402653, 21.485243852923485),
        "HBAN": (9.53105550644541, 15.208392056711958, 20.6496201815694),
        "MRSH": (76.31675154758247, 135.24506972155066, 208.30694759526924),
    }
    for ticker, values in expected.items():
        scenario = result(ticker)["scenario_range"]
        assert (scenario["low"], scenario["base"], scenario["high"]) == pytest.approx(values)


def test_financial_equity_routes_do_not_ev_bridge_operating_funding():
    for ticker in set(BATCH_33_TICKERS) - {"MRSH"}:
        row = result(ticker)
        assert row["governed_assumptions"]["route_is_equity_level"] is True
        assert row["governed_assumptions"]["ev_debt_bridge_applied"] is False
        assert "never EV-bridged" in row["source_ledger"]["bridge_treatment"]
        assert row["governed_assumptions"]["regulatory_capital_treatment"].endswith("rather than substituting zero.")


def test_common_equity_preferred_and_current_period_repairs():
    axp = result("AXP")
    assert axp["reported_inputs"]["ending_common_equity"] == 32_680_000_000.
    assert axp["governed_assumptions"]["preferred_event_treatment"]["series_e_cutoff_issuance"] == 1_600_000_000.
    assert axp["governed_assumptions"]["preferred_event_treatment"]["series_d_redemption_completed_at_cutoff"] is False
    fitb = result("FITB")
    assert fitb["reported_inputs"]["ending_common_equity"] == 32_300_000_000.
    assert fitb["governed_assumptions"]["note_exchange_treatment"]["new_principal_created"] is False
    mtb = result("MTB")
    assert mtb["reported_inputs"]["ending_common_equity"] == 25_512_000_000.
    assert mtb["governed_assumptions"]["preferred_event_treatment"]["series_l_cutoff_issuance"] == 600_000_000.
    hban = result("HBAN")
    assert hban["source_ledger"]["controlling_filing"]["period_end"] == "2026-06-30"
    assert hban["reported_inputs"]["ending_total_equity"] == 32_624_000_000.
    assert hban["source_ledger"]["common_earnings_reconstruction"]["current_ytd"]["value"] == 1_168_000_000.


def test_history_uses_exact_annual_periods_and_retains_loss_years():
    for ticker in set(BATCH_33_TICKERS) - {"MRSH"}:
        profile = result(ticker)["source_ledger"]["company_history_profile"]
        assert profile["full_history"] and len(profile["annual_periods"]) == 5
        assert len(set(profile["annual_periods"])) == 5
    aig_values = [row["value"] for row in result("AIG")["source_ledger"]["company_history_profile"]["metrics"][0]["observations"] if row["period_role"] == "annual"]
    cinf_values = [row["value"] for row in result("CINF")["source_ledger"]["company_history_profile"]["metrics"][0]["observations"] if row["period_role"] == "annual"]
    assert -1_426_000_000. in aig_values
    assert -487_000_000. in cinf_values
    assert result("WRB")["source_ledger"]["company_history_profile"]["annual_periods"] == ("2021-12-31", "2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31")


def test_roe_scenarios_and_partial_combinations_are_explicit():
    for ticker in set(BATCH_33_TICKERS) - {"MRSH"}:
        row = result(ticker)
        bridge = row["governed_assumptions"]["roe_scenario_bridge"]
        assert bridge["classification"] == "finsight_assumption_bounded_by_reported_history_and_current_equity"
        assert bridge["modeled_roe"] == tuple(item["current_roe"] for item in row["scenario_rows"])
        assert row["source_ledger"]["common_earnings_reconstruction"]["current_ytd"]["filed"]
        assert row["source_ledger"]["common_earnings_reconstruction"]["prior_ytd"]["filed"]
    assert "negative 2024" in result("AIG")["governed_assumptions"]["roe_scenario_bridge"]["normalization_reason"]
    assert "negative 2022" in result("CINF")["governed_assumptions"]["roe_scenario_bridge"]["normalization_reason"]
    for ticker in {"FITB", "HBAN"}:
        row = result(ticker)
        assert row["governed_assumptions"]["equity_anchor_method"] == "current_post_close_common_equity"
        assert row["governed_assumptions"]["combination_treatment"]["history_scope"] == "partial_combination"
        transaction = next(item for item in row["source_ledger"]["event_sources"] if item.get("source_kind") == "controlling_filing_reported_terms")
        assert transaction["document_sha256"] and transaction["package_manifest_sha256"]


def test_residual_income_and_fcff_replay_and_directions():
    from app.valuation.bank import residual_income_valuation
    from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
    for ticker in set(BATCH_33_TICKERS) - {"MRSH"}:
        row = result(ticker)
        for scenario in row["scenario_rows"]:
            replay = residual_income_valuation(book_value_per_share=scenario["book_value_per_share"], current_roe=scenario["current_roe"], cost_of_equity=scenario["cost_of_equity"], current_payout_ratio=scenario["current_payout_ratio"], terminal_roe=scenario["terminal_roe"], terminal_growth=scenario["terminal_growth"], years=5)
            assert replay["intrinsic_value"] == pytest.approx(scenario["raw_value_per_share"])
        assert row["scenario_rows"][0]["cost_of_equity"] > row["scenario_rows"][2]["cost_of_equity"]
        assert row["scenario_rows"][0]["current_roe"] <= row["scenario_rows"][2]["current_roe"]
    mrsh = result("MRSH")
    for scenario in mrsh["scenario_rows"]:
        state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"], scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"], 0., scenario["other_equity_claims"], scenario["shares"])
        replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
        assert replay["intrinsic_value_per_share"] == pytest.approx(scenario["raw_value_per_share"])


def test_insurance_reserves_and_client_funds_are_context_not_ev_claims():
    for ticker in {"AFL", "AIG", "WRB", "CINF"}:
        assert any("Claim" in item.get("concept", "") for item in result(ticker)["source_ledger"]["equity_model_context"])
    mrsh = result("MRSH")
    restricted = next(row for row in mrsh["source_ledger"]["bridge_sources"] if row.get("concept", "").endswith(":RestrictedCashAndCashEquivalentsAtCarryingValue"))
    assert restricted["value"] == 12_203_000_000. and restricted["used_in_arithmetic"] is False
    assert mrsh["source_ledger"]["bridge_reconciliation"]["cash_and_investments"] == (1_700_000_000.,) * 3
    assert mrsh["source_ledger"]["bridge_reconciliation"]["debt_and_finance_leases"] == 20_561_000_000.


def test_public_and_calculator_safety():
    from run_batch_33_history import _public
    for issuer in BATCH_33_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        raw = json.dumps(public)
        for private_key in ("source_ledger", "reported_inputs", "residual_income_trace", "equity_model_context", "ttm_"):
            assert private_key not in raw
        view = calculator_view(public)
        assert view["can_calculate"]
        assert view["model_family"] == ("operating" if issuer.ticker == "MRSH" else "equity_earnings")
        assert calculate(public, overrides={}, manual_price=None)["result"] == private["scenario_range"]


def test_runner_preserves_protected_and_bookkeeping(tmp_path):
    from run_batch_33_history import run
    report = run(source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS, output_root=tmp_path / "candidate")
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (1, 9, 0, 10)
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]


def test_arelle_outside_serving_process():
    for path in [ROOT / "backend/app/main.py", ROOT / "backend/app/deps.py", *sorted((ROOT / "backend/app/routers").glob("*.py"))]:
        assert "arelle" not in path.read_text().lower()
