from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.batch_12 import BATCH_12_MANIFEST, BATCH_12_TICKERS
from app.us_valuation.batch_12_recovery import (
    BATCH_12_RECOVERY_VERSION,
    EQUITY_TICKERS,
    OPERATING_TICKERS,
    build_batch_12_recovery_result,
)
from app.us_valuation.calculator import calculate, calculator_view


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "output/batch-12-sec-source-packets-20260828"
STRUCTURAL = ROOT / "output/batch-12-structural-sources-20260828"
INITIAL = ROOT / "output/batch-12-history/candidate-i"
RECOVERY = ROOT / "output/batch-12-recovery/candidate-g"
sys.path.insert(0, str(ROOT / "scripts"))


def _result(ticker: str):
    return build_batch_12_recovery_result(
        ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL
    )


def test_batch_12_whole_recovery_exact_outcomes_and_values() -> None:
    expected = {
        "ABT": (29.689388909506913, 58.20809920073297, 89.65169838253692),
        "BAX": (0.0, 8.54935871774756, 27.122993321184648),
        "BDX": (38.32957575926068, 97.89744003146913, 170.62957095012766),
        "BMY": (39.97686970283852, 69.48694725602633, 108.19648925209388),
        "RVTY": (23.949331350831944, 47.46376938872663, 79.26693214147497),
        "HUM": (79.52285539825377, 159.4513697759513, 278.2255775282374),
        "LLY": (68.59986530767371, 288.68431693323413, 609.3265013738472),
        "CVS": (26.702245525339734, 41.33517799231275, 74.09609675030782),
        "WST": (56.57048303339984, 87.67279615257375, 127.71801118264509),
    }
    for ticker in BATCH_12_TICKERS:
        result = _result(ticker)
        if ticker == "UHS":
            assert result["availability_type"] == "not_available"
            assert result["scenario_range"] == {"low": None, "base": None, "high": None}
            continue
        assert result["availability_type"] == "conditional_estimate"
        assert tuple(result["scenario_range"][key] for key in ("low", "base", "high")) == pytest.approx(expected[ticker])


def test_batch_12_recovery_binds_scale_claims_and_post_period_events() -> None:
    abt = _result("ABT")
    assert abt["reported_inputs"]["recovery_starting_revenue"] == 49_000_000_000.0
    assert abt["source_ledger"]["bridge_reconciliation"]["recovery_other_equity_claims"] == (1_425_000_000.0,) * 3
    assert {row.get("value") for row in abt["source_ledger"]["recovery_event_sources"] if row.get("value")} >= {24_500_000_000.0, 2_900_000_000.0, 510_000_000.0}

    bax = _result("BAX")
    assert bax["source_ledger"]["bridge_reconciliation"]["recovery_other_equity_claims"] == (105_000_000.0,) * 3
    assert {row.get("value") for row in bax["source_ledger"]["recovery_event_sources"]} == {43_000_000.0, 52_000_000.0}
    assert bax["scenario_rows"][0]["raw_value_per_share"] < 0
    assert bax["scenario_rows"][0]["limited_liability_floor_applied"] is True

    bdx = _result("BDX")
    assert bdx["source_ledger"]["bridge_reconciliation"]["recovery_other_equity_claims"] == (1_600_000_000.0,) * 3

    bmy = _result("BMY")
    assert bmy["source_ledger"]["bridge_reconciliation"]["recovery_other_equity_claims"] == (1_557_000_000.0,) * 3
    assert any(row.get("contingent_maximum_not_probability_weighted") == 14_300_000_000.0 for row in bmy["source_ledger"]["recovery_event_sources"])

    lly = _result("LLY")
    assert lly["source_ledger"]["bridge_reconciliation"]["recovery_other_equity_claims"] == (4_518_000_000.0,) * 3
    assert any(row.get("reported_cash_paid") == 2_000_000_000.0 for row in lly["source_ledger"]["recovery_event_sources"])
    assert any(row.get("reported_value") == 2_800_000_000.0 for row in lly["source_ledger"]["recovery_event_sources"])


def test_batch_12_recovery_uses_faded_cash_and_residual_income_lanes() -> None:
    for ticker in OPERATING_TICKERS:
        result = _result(ticker)
        assumptions = result["governed_assumptions"]
        assert assumptions["forecast_years"] == 8
        assert assumptions["terminal_growth"][-1] <= 0.025
        scenarios = result["scenario_rows"]
        assert scenarios[0]["growth"] <= scenarios[1]["growth"] <= scenarios[2]["growth"]
        assert scenarios[0]["wacc"] > scenarios[1]["wacc"] > scenarios[2]["wacc"]
        assert scenarios[0]["conditional_value_per_share"] <= scenarios[1]["conditional_value_per_share"] <= scenarios[2]["conditional_value_per_share"]
    assert _result("LLY")["governed_assumptions"]["growth"] == (0.10, 0.18, 0.25)

    for ticker in EQUITY_TICKERS:
        result = _result(ticker)
        assumptions = result["governed_assumptions"]
        assert assumptions["ev_debt_bridge_applied"] is False
        assert assumptions["book_equity"] > 0
        for trace in result["source_ledger"]["recovery_model_trace"]["states"].values():
            assert trace["validation"]["clean_surplus_reconciliation_difference"] == pytest.approx(0.0, abs=1e-10)


def test_batch_12_recovery_consumes_one_attempt_with_exact_source_hashes() -> None:
    for ticker in BATCH_12_TICKERS:
        result = _result(ticker)
        attempt = result["source_ledger"]["recovery_attempt"]
        assert attempt["attempt_number"] == 1
        assert attempt["attempt_scope"] == "whole_batch_value_recovery"
        assert attempt["market_price_used"] is False
        assert attempt["analyst_target_used"] is False
        packet = SOURCE / ticker
        structural = STRUCTURAL / ticker
        assert attempt["source_packet_manifest_sha256"] == hashlib.sha256((packet / "source-manifest.json").read_bytes()).hexdigest()
        assert attempt["package_manifest_sha256"] == hashlib.sha256((structural / "package-manifest.json").read_bytes()).hexdigest()
        assert attempt["source_receipt_sha256"] == hashlib.sha256((structural / "source-receipt.json").read_bytes()).hexdigest()
        assert attempt["structural_filing_sha256"] == hashlib.sha256((structural / "structural-filing.json").read_bytes()).hexdigest()


def test_batch_12_uhs_recovery_exhaustion_retains_withheld_state() -> None:
    result = _result("UHS")
    attempt = result["source_ledger"]["recovery_attempt"]
    assert attempt["outcome"] == "withheld"
    assert set(attempt["hard_blockers"]) == {
        "POST_PERIOD_CASH_DEBT_STATE_UNAVAILABLE",
        "POST_PERIOD_OPERATING_STATE_CHANGED",
        "PENDING_TRANSACTION_FINANCING_UNRESOLVED",
    }
    fields = {row.get("field") for row in result["source_ledger"]["recovery_event_sources"]}
    assert {"provo_canyon_license_revocations", "capital_medical_group_operating_responsibility", "ireland_financing_reserve_test"} <= fields


def test_batch_12_recovery_public_artifacts_and_calculators_are_safe() -> None:
    from run_batch_12_recovery import _public

    for issuer in BATCH_12_MANIFEST:
        result = _result(issuer.ticker)
        public = _public(issuer, result)
        raw = json.dumps(public)
        assert "source_ledger" not in raw
        assert "recovery_model_trace" not in raw
        view = calculator_view(public)
        if issuer.ticker == "UHS":
            assert view["can_calculate"] is False
        else:
            assert view["can_calculate"] is True
            assert view["model_family"] == ("equity_earnings" if issuer.ticker in EQUITY_TICKERS else "operating")
            calculated = calculate(public, overrides={}, manual_price=None)
            assert calculated["result"] == pytest.approx(result["scenario_range"])


def test_batch_12_recovery_report_is_exact_and_preserves_initial_evidence() -> None:
    report = json.loads((RECOVERY / "batch-12-recovery-report.json").read_text())
    assert report["policy_version"] == BATCH_12_RECOVERY_VERSION
    assert report["recovery_attempted_count"] == 10
    assert report["recovery_attempted_tickers"] == list(BATCH_12_TICKERS)
    assert set(report["recovery_attempts_per_ticker"].values()) == {1}
    assert (report["final_pass_count"], report["final_conditional_count"], report["final_withheld_count"], report["final_numeric_count"]) == (0, 9, 1, 9)
    assert report["final_withheld_tickers"] == ["UHS"]
    assert report["serving_artifacts_changed"] is False
    assert report["watchlist_changed_during_staging"] is False
    assert report["withheld_register_changed_during_staging"] is False
    assert report["initial_report_sha256"] == hashlib.sha256((INITIAL / "batch-12-report.json").read_bytes()).hexdigest()
    assert len(report["recovery_attempt_receipts"]) == 10


def test_batch_12_final_recovery_candidates_are_byte_identical() -> None:
    from run_batch_07_history import _tree

    twin = ROOT / "output/batch-12-recovery/candidate-h"
    assert _tree(RECOVERY) == _tree(twin)


def test_batch_12_recovery_bookkeeping_plan_adds_all_ten_and_only_withholds_uhs() -> None:
    from record_batch_12_recovery_bookkeeping import build_updates

    report = json.loads((RECOVERY / "batch-12-recovery-report.json").read_text())
    watchlist_path = ROOT / "backend/app/us_valuation/config/universe_reset_recovery_learning_watchlist.json"
    withheld_path = ROOT / "backend/app/us_valuation/config/universe_reset_withheld.json"
    watchlist = json.loads(watchlist_path.read_text())
    withheld = json.loads(withheld_path.read_text())
    watchlist["entries"] = [row for row in watchlist["entries"] if row["batch"] != 12]
    withheld["entries"] = [row for row in withheld["entries"] if row["batch"] != 12]
    updated_watchlist, updated_withheld, receipt = build_updates(report, watchlist, withheld)
    batch_12 = [row for row in updated_watchlist["entries"] if row["batch"] == 12]
    assert [row["ticker"] for row in batch_12] == list(BATCH_12_TICKERS)
    assert sum(row["current_status"] == "conditional_numeric_low" for row in batch_12) == 9
    assert sum(row["current_status"] == "withheld_after_recovery" for row in batch_12) == 1
    assert [row["ticker"] for row in updated_withheld["entries"] if row["batch"] == 12] == ["UHS"]
    assert receipt["watchlist_after_count"] == receipt["watchlist_before_count"] + 10
    assert receipt["withheld_after_count"] == receipt["withheld_before_count"] + 1
