import json
import math
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_48 import BATCH_48_MANIFEST, BATCH_48_TICKERS
from app.us_valuation.batch_48_history import REIT_INPUTS, WITHHELD_TICKERS, build_batch_48_history_result
from app.us_valuation.calculator import calculate, calculator_view
from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf, two_stage_cash_flow_value

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
KW = {"source_root": ROOT / "output/batch-48-sec-source-packets-20260911", "structural_root": ROOT / "output/batch-48-structural-sources-final-20260911", "event_root": ROOT / "output/batch-48-event-review-20260911", "structural_cache_root": ROOT / "output/batch-48-structural-cache-20260911"}
EXPECTED = {
    "FRT": (78.77441927557902, 84.20713784630857, 90.44470361270186),
    "UDR": (29.5686812903226, 31.607900689655175, 33.949226666666696),
    "WY": (None, None, None),
    "VTR": (45.39000000000003, 48.5203448275862, 52.11444444444449),
    "DOC": (20.630016759519624, 22.052776536038206, 23.686315538707717),
    "WELL": (75.97419354838715, 81.2137931034483, 87.22962962962971),
    "KIM": (21.494361290322594, 22.97673103448276, 24.678711111111134),
    "EQR": (None, None, None),
    "CPT": (76.80430560148505, 82.135893304636, 88.25734585269831),
    "IRM": (77.65161290322585, 83.00689655172414, 89.15555555555562),
}


@lru_cache(None)
def result(ticker: str):
    return build_batch_48_history_result(ticker=ticker, **KW)


def test_exact_outcomes_ranges_and_reliability() -> None:
    rows = [result(ticker) for ticker in BATCH_48_TICKERS]
    assert [row["ticker"] for row in rows if row["availability_type"] == "not_available"] == ["WY", "EQR"]
    assert len([row for row in rows if row["availability_type"] == "conditional_estimate"]) == 8
    for row in rows:
        observed = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        if row["ticker"] in WITHHELD_TICKERS:
            assert observed == EXPECTED[row["ticker"]] and row["history_reliability"] is None
        else:
            assert observed == pytest.approx(EXPECTED[row["ticker"]])
            assert 0 <= observed[0] <= observed[1] <= observed[2] and observed[1] > 0
            assert all(math.isfinite(value) for value in observed)
            assert row["history_reliability"]["label"] == "Low"


def test_source_controls_specialist_exhibits_and_no_zero_imputation() -> None:
    for issuer in BATCH_48_MANIFEST:
        row = result(issuer.ticker)
        verified = row["source_ledger"]["runtime_source_verification"]
        assert verified["verified"] and verified["ticker"] == issuer.ticker and verified["cik"] == issuer.cik
        assert verified["period_end"] == "2026-06-30" and verified["filed"] <= "2026-08-14"
        assert row["source_ledger"]["structural_top_level_period_diagnostic"]["used_for_selection"] is False
        if issuer.ticker in REIT_INPUTS:
            source = row["source_ledger"]["specialist_metric_source"]
            assert source["accession"] == REIT_INPUTS[issuer.ticker]["accession"] and source["unit"] == "USD/share"
            assert row["source_ledger"]["recurring_capital_basis"]["missing_values_zero_imputed"] is False


def test_reit_affo_ranges_replay_and_cost_direction() -> None:
    for ticker in REIT_INPUTS:
        row = result(ticker)
        for scenario in row["scenario_rows"]:
            replay = two_stage_cash_flow_value(cash_flow_per_share=scenario["normalized_affo_per_share"], growth_rate=scenario["growth_rate"], growth_years=scenario["forecast_years"], terminal_growth=scenario["terminal_growth"], discount_rate=scenario["discount_rate"])
            assert replay + scenario["nonrecurring_value_adjustment_per_share"] == pytest.approx(scenario["conditional_value_per_share"])
        assert len({scenario["normalized_affo_per_share"] for scenario in row["scenario_rows"]}) == 1
        assert len({scenario["recurring_cost_ratio"] for scenario in row["scenario_rows"]}) == 1
        assert row["scenario_rows"][0]["discount_rate"] >= row["scenario_rows"][1]["discount_rate"] >= row["scenario_rows"][2]["discount_rate"]
    frt = result("FRT")
    assert frt["source_ledger"]["cutoff_event_burden"]["principal"] == 460_000_000
    assert frt["source_ledger"]["cutoff_event_burden"]["initial_maximum_exchange_shares"] == 3_901_260
    assert frt["governed_assumptions"]["event_interest_burden_per_share"][0] > frt["governed_assumptions"]["event_interest_burden_per_share"][1] > frt["governed_assumptions"]["event_interest_burden_per_share"][2]
    assert frt["governed_assumptions"]["event_dilution_factor"][0] > frt["governed_assumptions"]["event_dilution_factor"][1] > frt["governed_assumptions"]["event_dilution_factor"][2]
    reconciliation = frt["source_ledger"]["event_adjustment_reconciliation"]
    assert reconciliation["arithmetic_bound_to_public_base"]
    assert reconciliation["event_adjusted_base_affo_per_share"] == pytest.approx(frt["scenario_rows"][1]["normalized_affo_per_share"])
    assert reconciliation["event_adjusted_base_affo_per_share"] < reconciliation["unadjusted_base_affo_per_share"]


def test_wy_history_bridge_and_canonical_replay() -> None:
    row = result("WY")
    reported = row["reported_inputs"]
    assert reported["ttm_operating_cash_flow"] == 547_000_000
    assert reported["ttm_capital_expenditures"] == 525_000_000
    assert reported["ttm_interest_paid"] == 273_000_000
    assert reported["ttm_cash_fcff_diagnostic"] == pytest.approx(237_670_000)
    assert row["governed_assumptions"]["starting_cash_fcff_diagnostic"] == pytest.approx((237_670_000, 796_610_000, 1_209_570_000))
    diagnostic = row["source_ledger"]["private_pre_publication_diagnostic"]
    assert not diagnostic["published"]
    assert diagnostic["scenario_range"] == pytest.approx({"low": 0.0, "base": 5.195260828327604, "high": 16.55861668550236})
    for scenario in diagnostic["scenario_rows"]:
        state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth_rate"], scenario["terminal_growth"], scenario["wacc"], scenario["cash"], scenario["debt"], 0.0, scenario["preferred_and_nci"], scenario["shares"])
        trace = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
        assert trace["intrinsic_value_per_share"] == pytest.approx(scenario["raw_value_per_share"])
        assert max(0.0, trace["intrinsic_value_per_share"]) == pytest.approx(scenario["conditional_value_per_share"])


def test_eqr_pending_merger_is_withheld_without_successor_substitution() -> None:
    row = result("EQR")
    assert row["availability_type"] == "not_available" and row["scenario_range"] == {"low": None, "base": None, "high": None}
    assert row["source_ledger"]["cutoff_identity"] == {"ticker": "EQR", "cik": "0000906107", "name": "Equity Residential", "status": "standalone legal issuer at 2026-08-14"}
    merger = row["source_ledger"]["merger_event"]
    assert merger["accession"] == "0001140361-26-032504" and merger["filed"] == "2026-08-12"
    assert "2.793" in row["governed_assumptions"]["invalidation"]


def test_public_artifacts_keep_formula_identity_calculator_parity_and_no_leaks() -> None:
    from run_batch_48_history import _public

    forbidden = ("source_ledger", "reported_inputs", "governed_assumptions", "specialist_metric_source", "annual_cash_history")
    for issuer in BATCH_48_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        expected_model = "fcff_dcf" if issuer.ticker == "WY" else "affo_dcf"
        assert public["model_policy"]["primary"] == expected_model
        encoded = json.dumps(public)
        assert not any(key in encoded for key in forbidden)
        view = calculator_view(public)
        if issuer.ticker in {"WY", "EQR"}:
            assert public["availability_type"] == "not_available" and not view["can_calculate"]
            assert public["reliability"]["label"] == "Low"
            assert public["review"]["publication_state"] == "withheld"
        else:
            assert public["availability_type"] == "conditional_estimate" and view["can_calculate"]
            calculated = calculate(public, overrides={}, manual_price=None)
            assert calculated["result"] == pytest.approx({key: public["scenario_range"][key] for key in ("low", "base", "high")})
            if issuer.ticker != "WY":
                defaults = view["defaults"]
                assert two_stage_cash_flow_value(cash_flow_per_share=defaults["normalized_affo_per_share"], growth_rate=defaults["affo_growth"], growth_years=defaults["forecast_years"], terminal_growth=defaults["terminal_growth"], discount_rate=defaults["discount_rate"]) + defaults["nonrecurring_value_adjustment_per_share"] == pytest.approx(public["scenario_range"]["base"])
                assert "recurring_cost_ratio" not in {field["key"] for field in view["editable_assumptions"]}
                with pytest.raises(ValueError, match="locked source-derived input"):
                    calculate(public, overrides={"recurring_cost_ratio": 0.10}, manual_price=None)
        if issuer.ticker == "WY":
            assert set(public["models"]) == {"fcff_dcf"}
            assert all("conditional_estimate" not in reason for reason in public["automated_review"]["blocking_reasons"])


def test_source_tampering_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "sources"
    shutil.copytree(KW["source_root"] / "FRT", source / "FRT")
    (source / "FRT" / "companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_batch_48_history_result(ticker="FRT", **{**KW, "source_root": source})


def test_runner_preserves_serving_and_bookkeeping(tmp_path: Path) -> None:
    from run_batch_48_history import run

    report = run(output_root=tmp_path / "candidate", **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 0, 8, 2, 8)
    assert report["denominator_tickers"] == list(BATCH_48_TICKERS)
    assert report["batch_47_dependency_status"] == "confirmed_batch_47_recovery_catalog_and_bookkeeping_bound"
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
