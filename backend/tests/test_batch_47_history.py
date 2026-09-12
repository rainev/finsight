import json
import math
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_47 import BATCH_47_MANIFEST, BATCH_47_TICKERS
from app.us_valuation.batch_47_history import WITHHELD_TICKERS, build_batch_47_history_result

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
KW = {
    "source_root": ROOT / "output/batch-47-sec-source-packets-20260908",
    "structural_root": ROOT / "output/batch-47-structural-sources-run-b-20260908",
    "event_root": ROOT / "output/batch-47-event-review-20260908",
    "structural_cache_root": ROOT / "output/batch-47-structural-cache-20260908",
}
EXPECTED = {
    "NRG": (None, None, None),
    "ED": (58.832227693802324, 68.05309800574659, 80.63433804341568),
    "EXC": (28.82961692878333, 33.36808288265989, 39.56134613318843),
    "NI": (20.10930686219995, 23.275385540394836, 27.595883749876123),
    "CNP": (17.922463850306404, 20.744246618184327, 24.594911658975356),
    "DUK": (69.98048796684587, 80.99559144091435, 96.02691566821457),
    "AWK": (64.10099900239177, 74.21274092153007, 88.01225211129905),
    "VST": (None, None, None),
    "EVRG": (39.970496400337105, 46.245895872378874, 54.80869811509221),
    "CEG": (None, None, None),
}


@lru_cache(None)
def result(ticker: str):
    return build_batch_47_history_result(ticker=ticker, **KW)


def test_exact_outcomes_ranges_and_reliability() -> None:
    rows = [result(ticker) for ticker in BATCH_47_TICKERS]
    assert [row["ticker"] for row in rows if row["availability_type"] == "not_available"] == ["NRG", "VST", "CEG"]
    assert len([row for row in rows if row["availability_type"] == "conditional_estimate"]) == 7
    for row in rows:
        observed = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        if row["ticker"] in WITHHELD_TICKERS:
            assert observed == EXPECTED[row["ticker"]] and row["history_reliability"] is None
        else:
            assert observed == pytest.approx(EXPECTED[row["ticker"]])
            assert 0 < observed[0] <= observed[1] <= observed[2]
            assert all(math.isfinite(value) for value in observed)
            assert row["history_reliability"]["label"] == "Low"


def test_controlling_sources_periods_and_histories_are_exact() -> None:
    for issuer in BATCH_47_MANIFEST:
        row = result(issuer.ticker)
        verified = row["source_ledger"]["runtime_source_verification"]
        assert verified["verified"] and verified["ticker"] == issuer.ticker and verified["cik"] == issuer.cik
        assert verified["period_end"] == "2026-06-30" and verified["filed"] <= "2026-08-14"
        history = row["source_ledger"]["annual_common_equity_history"]
        assert [item["period_end"] for item in history] == ["2024-12-31", "2025-12-31"]
        assert 0 < row["source_ledger"]["equity_allocation"]["parent_equity_share"] <= 1
        assert row["source_ledger"]["ttm_common_equity_state"]["period_end"] == "2026-06-30"
        assert row["source_ledger"]["structural_top_level_period_diagnostic"]["used_for_selection"] is False


def test_parent_equity_claims_and_ttm_income_are_not_double_counted() -> None:
    ni = result("NI")["source_ledger"]["equity_allocation"]
    assert ni["parent_common_equity"]["value"] == 9_574_600_000
    assert ni["noncontrolling_interest"]["value"] == 2_319_800_000
    duk = result("DUK")["source_ledger"]["equity_allocation"]
    assert duk["parent_common_equity"]["value"] == 54_751_000_000
    assert duk["noncontrolling_interest"]["value"] == 2_112_000_000
    awk = result("AWK")["source_ledger"]["equity_allocation"]
    assert awk["temporary_or_redeemable_equity"]["value"] == 3_000_000
    assert result("EXC")["reported_inputs"]["ending_common_equity"] == 29_698_000_000


def test_regulated_ranges_vary_only_cost_of_equity_and_use_no_ev_bridge() -> None:
    for ticker in set(BATCH_47_TICKERS) - WITHHELD_TICKERS:
        row = result(ticker)
        scenarios = row["scenario_rows"]
        assert len({item["current_roe"] for item in scenarios}) == 1
        assert len({item["current_payout_ratio"] for item in scenarios}) == 1
        assert len({item["terminal_roe"] for item in scenarios}) == 1
        assert len({item["terminal_growth"] for item in scenarios}) == 1
        assert len({item["shares"] for item in scenarios}) == 1
        assert tuple(item["cost_of_equity"] for item in scenarios) == (0.095, 0.085, 0.075)
        assert row["governed_assumptions"]["ev_debt_bridge_applied"] is False
        assert row["source_ledger"]["fcfe_route_not_selected"]["missing_values_zero_imputed"] is False


def test_merchant_generators_are_not_mislabeled_as_regulated_values() -> None:
    for ticker in WITHHELD_TICKERS:
        row = result(ticker)
        assert "merchant" in row["method"]
        assert row["source_ledger"]["specialist_gate"]["passed"] is False
        assert row["scenario_rows"] == [] and row["scenario_range"]["base"] is None
    vst = result("VST")["source_ledger"]["equity_allocation"]
    assert vst["preferred_equity"]["value"] == 2_476_000_000
    assert vst["noncontrolling_interest"]["value"] == 12_000_000


def test_public_identity_calculator_and_private_boundary() -> None:
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_47_history import _public

    for issuer in BATCH_47_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        assert public["model_policy"]["primary"] == "residual_income"
        encoded = json.dumps(public)
        for key in ("source_ledger", "reported_inputs", "governed_assumptions", "annual_common_equity_history"):
            assert key not in encoded
        view = calculator_view(public)
        if issuer.ticker in WITHHELD_TICKERS:
            assert public["availability_type"] == "not_available" and not view["can_calculate"]
        else:
            assert public["availability_type"] == "conditional_estimate" and view["can_calculate"]
            calculated = calculate(public, overrides={}, manual_price=None)["result"]
            assert tuple(calculated[key] for key in ("low", "base", "high")) == pytest.approx(tuple(public["scenario_range"][key] for key in ("low", "base", "high")))


def test_source_tampering_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "sources"
    shutil.copytree(KW["source_root"] / "ED", source / "ED")
    (source / "ED/companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_batch_47_history_result(ticker="ED", **{**KW, "source_root": source})


def test_runner_preserves_serving_and_bookkeeping(tmp_path: Path) -> None:
    from run_batch_47_history import run

    report = run(output_root=tmp_path / "candidate", **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 0, 7, 3, 7)
    assert report["denominator_tickers"] == list(BATCH_47_TICKERS)
    assert report["batch_46_dependency_status"] == "confirmed_batch_46_recovery_catalog_and_bookkeeping_bound"
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
