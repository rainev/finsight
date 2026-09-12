from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_32 import BATCH_32_MANIFEST, BATCH_32_TICKERS
from app.us_valuation.batch_32_history import PASS_TICKERS, CONDITIONAL_TICKERS, WITHHELD_TICKERS, build_batch_32_history_result
from app.us_valuation.calculator import calculate, calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-32-sec-source-packets-20260903"
STRUCTURAL = ROOT / "output/batch-32-structural-sources-20260903"
EVENTS = ROOT / "output/batch-32-event-sources-b-20260903"


def result(ticker):
    return build_batch_32_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS)


def test_outcomes_ranges_and_denominator():
    rows = {ticker: result(ticker) for ticker in BATCH_32_TICKERS}
    assert set(PASS_TICKERS) == {"GDDY"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(CONDITIONAL_TICKERS) == set(BATCH_32_TICKERS) - {"GDDY"}
    assert not WITHHELD_TICKERS and len(rows) == 10
    for row in rows.values():
        values = row["scenario_range"]
        assert 0 <= values["low"] <= values["base"] <= values["high"] and values["base"] > 0
        assert row["history_reliability"]["label"] == "Low"


def test_exact_controlled_ranges_do_not_drift():
    expected = {
        "DDOG": (46.186456912436576, 71.67131147207404, 106.55939606567277),
        "KEYS": (66.00561618369719, 122.79757936851213, 182.1326305897931),
        "GDDY": (93.7959958846141, 166.32037911685867, 255.58237090584507),
        "LITE": (11.874045435982683, 26.704663131255703, 77.08109673376075),
        "HPE": (4.330120208040657, 12.393012022735743, 37.825097927260146),
        "VRT": (22.52775016549566, 89.3468249295978, 167.22306274092608),
        "AVGO": (73.33993519849935, 149.77664162796276, 259.60201820207277),
        "MRVL": (14.48662929892247, 30.348168621453485, 53.68957711281735),
        "SNDK": (46.26324917610671, 168.21285905631555, 429.94252789472625),
        "Q": (0.35821841813282007, 26.016577061628503, 71.42143088828675),
    }
    for ticker, values in expected.items():
        scenario = result(ticker)["scenario_range"]
        assert (scenario["low"], scenario["base"], scenario["high"]) == pytest.approx(values)


def test_difficult_event_and_claim_treatments_are_explicit():
    lite = result("LITE")
    assert lite["governed_assumptions"]["latest_release_treatment"]["revenue"] == 3_014_000_000.
    assert lite["source_ledger"]["bridge_reconciliation"]["debt_and_finance_leases"] == 1_637_400_000.
    cash_metric = next(metric for metric in lite["source_ledger"]["company_history_profile"]["metrics"] if metric["name"] == "cash_conversion_margin")
    operating_ttm = next(item for item in cash_metric["observations"] if item["period_role"] == "operating_ttm")
    assert operating_ttm["period_end"] == "2026-03-28"
    assert operating_ttm["value"] == pytest.approx(132_644_000. / 2_488_400_000.)
    hpe = result("HPE")
    assert hpe["source_ledger"]["bridge_reconciliation"]["other_equity_claims"] == pytest.approx((195_760_161.03343195, 196_744_325.67042312, 197_413_737.82283366))
    assert hpe["source_ledger"]["bridge_reconciliation"]["shares"][0] == 1_447_371_521.
    assert hpe["governed_assumptions"]["mandatory_convertible_treatment"]["minimum_common_conversion_shares"] == 76_056_000.
    assert hpe["reported_inputs"]["ttm_interest_basis"] == "current_h1_financing_cost_annualized_mixed_finance_proxy"
    mrvl = result("MRVL")
    treatment = mrvl["governed_assumptions"]["conversion_and_contingent_share_treatment"]
    assert treatment["preferred_as_converted_shares"] == 21_800_000.
    assert treatment["contingent_consideration_fair_value"] == 647_600_000.
    assert "not added again" in treatment["treatment"]
    assert mrvl["source_ledger"]["bridge_reconciliation"]["other_equity_claims"] == (647_600_000.,) * 3
    avgo = result("AVGO")
    assert avgo["source_ledger"]["bridge_reconciliation"]["other_equity_claims"] == (29_000_000_000., 0., 0.)
    backstop = next(row for row in avgo["source_ledger"]["event_sources"] if row.get("concept", "").endswith(":GuaranteeObligationsMaximumExposure"))
    assert backstop["value"] == 29_000_000_000.


def test_history_and_current_concept_lineage_controls():
    sndk = result("SNDK")
    assert sndk["governed_assumptions"]["history_years_used"] == 3
    assert sndk["governed_assumptions"]["cycle_normalization"]["annual_cash_observations"] == pytest.approx([-907_510_000., -443_400_000., -70_230_000.])
    assert sndk["governed_assumptions"]["cash_conversion_margin"] == (.01, .08, .16)
    assert sndk["reported_inputs"]["ttm_revenue"] == 20_248_000_000.
    assert sndk["source_ledger"]["bridge_reconciliation"]["cash_and_investments"] == (6_183_600_000., 6_539_000_000., 6_539_000_000.)
    q = result("Q")
    assert q["reported_inputs"]["ttm_interest"] == 187_000_000.
    assert all(source["concept"] == "InterestAndDebtExpense" for source in q["source_ledger"]["flow_sources"]["interest_expense"]["sources"])
    assert q["governed_assumptions"]["post_separation_history_treatment"]["current_h1_interest"] == 122_000_000.
    gddy = result("GDDY")
    assert gddy["source_ledger"]["bridge_reconciliation"]["cash_and_investments"] == (1_155_500_000.,) * 3
    event = next(row for row in gddy["source_ledger"]["event_sources"] if row.get("source_kind") == "sec_current_report")
    assert event["reported_terms"]["new_revolver_commitment"] == 1_200_000_000
    assert event["reported_terms"]["new_borrowing_reported"] is False
    assert not gddy["warning"].startswith("Conditional")


def test_share_units_dcf_replay_and_sensitivity_direction():
    from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
    for ticker in BATCH_32_TICKERS:
        row = result(ticker)
        assert any(item.get("unit") in {"shares", "xbrli:shares"} for item in row["source_ledger"]["bridge_sources"])
        for scenario in row["scenario_rows"]:
            state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"], scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"], 0., scenario["other_equity_claims"], scenario["shares"])
            replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
            assert float(replay["intrinsic_value_per_share"]) == pytest.approx(scenario["raw_value_per_share"])
        assert row["scenario_rows"][0]["wacc"] > row["scenario_rows"][2]["wacc"]
        assert row["scenario_rows"][0]["growth"] <= row["scenario_rows"][2]["growth"]


def test_public_and_calculator_safety():
    from run_batch_32_history import _public
    for issuer in BATCH_32_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        raw = json.dumps(public)
        for private_key in ("source_ledger", "reported_inputs", "model_trace", "bridge_sources", "event_sources", "ttm_"):
            assert private_key not in raw
        view = calculator_view(public)
        assert view["can_calculate"] and view["model_family"] == "operating"
        assert calculate(public, overrides={}, manual_price=None)["result"] == private["scenario_range"]


def test_runner_preserves_protected_and_bookkeeping(tmp_path):
    from run_batch_32_history import run
    report = run(source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS, output_root=tmp_path / "candidate")
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (1, 9, 0, 10)
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]


def test_arelle_outside_serving_process():
    for path in [ROOT / "backend/app/main.py", ROOT / "backend/app/deps.py", *sorted((ROOT / "backend/app/routers").glob("*.py"))]:
        assert "arelle" not in path.read_text().lower()
