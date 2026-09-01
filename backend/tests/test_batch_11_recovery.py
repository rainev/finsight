from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.batch_11 import BATCH_11_MANIFEST
from app.us_valuation.batch_11_history import build_batch_11_history_result
from app.us_valuation.batch_11_recovery import (
    BATCH_11_RECOVERY_VERSION,
    build_bg_recovery_result,
    build_syy_recovery_result,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "output/batch-11-sec-source-packets-20260828"
STRUCTURAL = ROOT / "output/batch-11-structural-sources-final-a"
INITIAL = ROOT / "output/batch-11-history/candidate-o"
WATCHLIST = (
    ROOT
    / "backend/app/us_valuation/config/universe_reset_recovery_learning_watchlist.json"
)
WITHHELD = ROOT / "backend/app/us_valuation/config/universe_reset_withheld.json"
sys.path.insert(0, str(ROOT / "scripts"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_batch_11_initial_default_stays_withheld() -> None:
    result = build_batch_11_history_result(
        ticker="SYY", source_root=SOURCE, structural_root=STRUCTURAL
    )
    assert result["availability_type"] == "not_available"
    assert result["scenario_range"] == {"low": None, "base": None, "high": None}


def test_syy_recovery_is_pre_jetro_conditional_only() -> None:
    result = build_syy_recovery_result(
        source_root=SOURCE, structural_root=STRUCTURAL
    )
    assert result["model_version"] == BATCH_11_RECOVERY_VERSION
    assert result["availability_type"] == "conditional_estimate"
    assert result["method"] == "pre_jetro_current_state_cash_fcff"
    assert result["scenario_range"] == pytest.approx(
        {
            "low": 25.591781009209107,
            "base": 51.64451138890655,
            "high": 79.09343441308374,
        }
    )
    assumptions = result["governed_assumptions"]
    assert assumptions["economic_state"] == "pre_jetro_current_state"
    assert result["source_ledger"]["bridge_reconciliation"] == {
        **result["source_ledger"]["bridge_reconciliation"],
        "cash_and_investments": 1_900_000_000.,
        "debt_and_finance_leases": 14_008_000_000.,
    }
    receipt = result["source_ledger"]["recovery_attempt"]
    assert receipt["attempt_number"] == 1
    assert receipt["transaction_value_included"] is False
    assert receipt["transaction_terms_retained_as_invalidation_only"] is True
    assert set(receipt["source_hashes"]) == {
        "package_manifest_sha256",
        "structural_filing_sha256",
        "source_receipt_sha256",
        "source_packet_manifest_sha256",
    }
    event_values = {
        row.get("value") for row in result["source_ledger"]["bridge_sources"]
    }
    assert {
        29_100_000_000.,
        21_600_000_000.,
        91_500_000.,
        22_000_000_000.,
        1_164_000_000.,
        6_300_000_000.,
        3_000_000_000.,
        19_000_000_000.,
        88_000_000.,
    }.issubset(event_values)
    assert all(
        row.get("valuation_treatment")
        == "separate_transaction_surface_not_in_intrinsic_value"
        for row in result["source_ledger"]["bridge_sources"]
        if any(
            "JetroRestaurantDepotMember" in str(value)
            for _, value in (row.get("dimensions") or [])
        )
    )
    afs = next(
        row
        for row in result["source_ledger"]["bridge_sources"]
        if row.get("concept") == "us-gaap:AvailableForSaleSecuritiesDebtSecurities"
    )
    assert afs["included_in_excess_cash"] is False
    scenarios = result["scenario_rows"]
    assert scenarios[0]["wacc"] > scenarios[1]["wacc"] > scenarios[2]["wacc"]
    assert scenarios[0]["shares"] > scenarios[1]["shares"] > scenarios[2]["shares"]
    assert scenarios[0]["conditional_value_per_share"] < scenarios[1]["conditional_value_per_share"] < scenarios[2]["conditional_value_per_share"]


def test_bg_recovery_exhausts_sources_and_remains_withheld() -> None:
    result = build_bg_recovery_result(
        source_root=SOURCE, structural_root=STRUCTURAL
    )
    assert result["model_version"] == BATCH_11_RECOVERY_VERSION
    assert result["availability_type"] == "not_available"
    assert result["scenario_range"] == {"low": None, "base": None, "high": None}
    assert result["governed_assumptions"]["recovery_attempts"] == 1
    assert result["governed_assumptions"]["current_combined_h1_cash_fcff"] < 0
    receipt = result["source_ledger"]["recovery_attempt"]
    assert receipt["attempt_number"] == 1
    assert receipt["release_condition_cleared"] is False
    assert [row["outcome"] for row in receipt["official_source_tiers"]] == [
        "accepted_current_combined_h1",
        "not_disclosed",
        "unavailable",
    ]
    assert receipt["official_source_tiers"][1]["matched_structural_concepts"] == []
    assert receipt["hard_blockers"] == [
        "PREDECESSOR_HISTORY_NOT_COMPARABLE",
        "PRO_FORMA_CASH_FLOW_NOT_DISCLOSED",
        "NONFINITE_OR_NONPOSITIVE_VALUE",
    ]


def test_batch_11_recovery_public_contract_and_runner(tmp_path: Path) -> None:
    from run_batch_11_history import _public
    from run_batch_11_recovery import run

    syy = next(row for row in BATCH_11_MANIFEST if row.ticker == "SYY")
    bg = next(row for row in BATCH_11_MANIFEST if row.ticker == "BG")
    syy_result = build_syy_recovery_result(
        source_root=SOURCE, structural_root=STRUCTURAL
    )
    bg_result = build_bg_recovery_result(
        source_root=SOURCE, structural_root=STRUCTURAL
    )
    syy_public = _public(syy, syy_result)
    bg_public = _public(bg, bg_result)
    assert syy_public["availability_type"] == "conditional_estimate"
    assert syy_public["public_assumptions"]["forecast_mode"] == "current_state_pre_jetro"
    assert (
        syy_public["public_assumptions"]["forecast_policy_version"]
        == BATCH_11_RECOVERY_VERSION
    )
    assert syy_public["scenario_range"]["base"] == syy_result["scenario_range"]["base"]
    assert bg_public["availability_type"] == "not_available"
    assert bg_public["scenario_range"]["base"] is None
    assert "source_ledger" not in json.dumps(syy_public)

    watchlist_before = _sha(WATCHLIST)
    withheld_before = _sha(WITHHELD)
    report = run(
        initial_root=INITIAL,
        source_root=SOURCE,
        structural_root=STRUCTURAL,
        output_root=tmp_path / "recovery",
    )
    assert report["recovery_attempted_tickers"] == ["SYY", "BG"]
    assert report["recovered_tickers"] == ["SYY"]
    assert report["remaining_withheld_tickers"] == ["BG"]
    assert (
        report["pass_count"],
        report["conditional_count"],
        report["withheld_count"],
        report["numeric_count"],
    ) == (2, 7, 1, 9)
    assert report["serving_artifacts_changed"] is False
    assert report["watchlist_changed"] is False
    assert report["withheld_register_changed"] is False
    assert _sha(WATCHLIST) == watchlist_before
    assert _sha(WITHHELD) == withheld_before
