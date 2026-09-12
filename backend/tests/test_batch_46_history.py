import json
import math
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_46 import BATCH_46_MANIFEST, BATCH_46_TICKERS
from app.us_valuation.batch_46_history import WITHHELD_TICKERS, build_batch_46_history_result
from app.us_valuation.practical_models import EquityCashFlowState, mixed_utility_fcfe, practical_equity_cash_flow_range

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
KW = {
    "source_root": ROOT / "output/batch-46-sec-source-packets-20260908",
    "structural_root": ROOT / "output/batch-46-structural-sources-20260908",
    "event_root": ROOT / "output/batch-46-event-review-20260908",
    "structural_cache_root": ROOT / "output/batch-46-structural-cache-20260908",
}
EXPECTED = {
    "ATO": (82.1650828593106, 95.06825811826447, 112.67481543417924),
    "CMS": (35.395745954518816, 40.91572854476697, 48.446023581762844),
    "EIX": (None, None, None),
    "AES": (None, None, None),
    "PPL": (15.703157070933019, 19.02003459891617, 22.68868509599735),
    "DTE": (67.81800404119343, 78.39756549826275, 92.83022710911898),
    "AEE": (56.545133199195774, 65.44409460920984, 77.58757578981091),
    "PCG": (None, None, None),
    "FE": (15.941474199183208, 18.46731997725126, 21.91487432949548),
    "SRE": (None, None, None),
}


@lru_cache(None)
def result(ticker: str):
    return build_batch_46_history_result(ticker=ticker, **KW)


def test_exact_outcomes_ranges_and_reliability() -> None:
    rows = [result(ticker) for ticker in BATCH_46_TICKERS]
    assert [row["ticker"] for row in rows if row["availability_type"] == "not_available"] == ["EIX", "AES", "PCG", "SRE"]
    assert len([row for row in rows if row["availability_type"] == "conditional_estimate"]) == 6
    for row in rows:
        observed = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        if row["ticker"] in WITHHELD_TICKERS:
            assert observed == EXPECTED[row["ticker"]] and row["history_reliability"] is None
        else:
            assert observed == pytest.approx(EXPECTED[row["ticker"]])
            assert 0 < observed[0] <= observed[1] <= observed[2]
            assert all(math.isfinite(value) for value in observed)
            assert row["history_reliability"]["label"] == "Low"


def test_exact_controls_and_fiscal_year_history() -> None:
    for issuer in BATCH_46_MANIFEST:
        row = result(issuer.ticker)
        verified = row["source_ledger"]["runtime_source_verification"]
        assert verified["verified"] and verified["ticker"] == issuer.ticker and verified["cik"] == issuer.cik
        assert verified["period_end"] == "2026-06-30" and verified["filed"] <= "2026-08-14"
        assert row["source_ledger"]["structural_top_level_period_diagnostic"]["used_for_selection"] is False
    ato = result("ATO")["source_ledger"]
    assert [row["period_end"] for row in ato["annual_common_equity_history"]] == ["2024-09-30", "2025-09-30"]
    assert ato["ttm_common_equity_state"]["common_net_income"]["method"] == "latest_fy_plus_current_ytd_minus_prior_comparable_ytd"


def test_parent_common_equity_and_fe_nci_are_reconciled_once() -> None:
    cms = result("CMS")["source_ledger"]["equity_allocation"]
    assert cms["parent_common_equity"]["value"] == 9_550_000_000
    assert cms["preferred_equity"]["value"] == 224_000_000
    assert cms["noncontrolling_interest"]["value"] == 625_000_000
    fe = result("FE")
    assert fe["reported_inputs"]["ttm_common_earnings"] == 813_000_000
    components = fe["source_ledger"]["ttm_common_equity_state"]["common_net_income"]["components"]
    assert sum(row["value"] * row["sign"] for row in components) == 813_000_000
    assert result("PPL")["source_ledger"]["equity_allocation"]["parent_common_equity"]["claim_absence_check"]["reported_vs_estimated"] == "source_bounded_absence"


def test_ppl_fcfe_replays_and_residuals_use_no_ev_bridge() -> None:
    ppl = result("PPL")
    reported, rows = ppl["reported_inputs"], ppl["scenario_rows"]
    for row in rows:
        assert row["cash_flow"] == pytest.approx(mixed_utility_fcfe(operating_cash_flow=reported["ttm_operating_cash_flow"], capital_expenditures=reported["ttm_capital_expenditures"], net_income=reported["model_income_before_parent_allocation"], debt_funding_share=row["debt_funding_share"], parent_cash_flow_share=reported["parent_cash_flow_share"]))
    states = {row["name"]: EquityCashFlowState(row["cash_flow"], row["growth_rate"], row["terminal_growth"], row["cost_of_equity"]) for row in rows}
    replay, _ = practical_equity_cash_flow_range(states=states, diluted_shares=rows[0]["shares"], forecast_years=10, maximum_terminal_share=0.90)
    assert replay.as_dict() == pytest.approx(ppl["scenario_range"])
    for ticker in {"ATO", "CMS", "DTE", "AEE", "FE"}:
        row = result(ticker)
        assert row["method"] == "regulated_utility_residual_income"
        assert row["governed_assumptions"]["ev_debt_bridge_applied"] is False
        assert len(set(item["current_roe"] for item in row["scenario_rows"])) == 1


def test_withheld_specialist_gates_keep_model_identity_and_no_values() -> None:
    from app.us_valuation.calculator import calculator_view
    from run_batch_46_history import _public

    for issuer in BATCH_46_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        expected_model = "residual_income" if issuer.ticker in {"EIX", "PCG"} or private["method"] == "regulated_utility_residual_income" else "fcfe_dcf"
        assert public["model_policy"]["primary"] == expected_model
        encoded = json.dumps(public)
        for key in ("source_ledger", "reported_inputs", "governed_assumptions", "annual_common_equity_history"):
            assert key not in encoded
        view = calculator_view(public)
        if issuer.ticker in WITHHELD_TICKERS:
            assert public["availability_type"] == "not_available" and public["scenario_range"]["base"] is None
            assert not view["can_calculate"]
            if issuer.ticker in {"AES", "SRE"}:
                assert public["primary_valuation_method"] == "regulated_utility_fcfe"
                assert public["methodology"]["sector_framework"] == "regulated_utility_fcfe"
        else:
            assert public["availability_type"] == "conditional_estimate" and view["can_calculate"]


def test_source_tampering_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "sources"
    shutil.copytree(KW["source_root"] / "ATO", source / "ATO")
    (source / "ATO/companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_batch_46_history_result(ticker="ATO", **{**KW, "source_root": source})


def test_runner_preserves_serving_and_bookkeeping(tmp_path: Path) -> None:
    from run_batch_46_history import run

    report = run(output_root=tmp_path / "candidate", **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 0, 6, 4, 6)
    assert report["denominator_tickers"] == list(BATCH_46_TICKERS)
    assert report["batch_45_dependency_status"] == "confirmed_batch_45_catalog_and_bookkeeping_bound"
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
