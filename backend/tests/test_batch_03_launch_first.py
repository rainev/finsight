from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.us_valuation.batch_03_launch_first import (
    LAUNCH_FIRST_BATCH_03_VERSION,
    LAUNCH_FIRST_CONDITIONAL_TICKERS,
    build_batch_03_launch_first_hard_failure,
    build_batch_03_launch_first_result,
)


SOURCE_ROOT = Path("output/batch-03-sec-source-packets-20260824")
STRUCTURAL_ROOT = Path("output/batch-03-structural-sources-20260824")


def _rejection(ticker: str) -> tuple[str, ...]:
    private = json.loads(
        Path(
            f"output/batch-03-controlled/candidate-g/generated/{ticker}/valuation-private.json"
        ).read_text()
    )
    controlled = private["controlled_outcome"]
    return tuple(
        str(value)
        for value in (
            *controlled.get("blockers", []),
            controlled.get("model_selection_reason"),
        )
        if value
    )


def test_launch_first_exact_disposition_keeps_two_hard_failures() -> None:
    assert LAUNCH_FIRST_CONDITIONAL_TICKERS == (
        "LYV",
        "GOOGL",
        "APP",
        "FOXA",
        "TKO",
    )
    for ticker in ("ECHO", "PSKY"):
        result = build_batch_03_launch_first_hard_failure(
            ticker,
            source_root=SOURCE_ROOT,
            structural_root=STRUCTURAL_ROOT,
        )
        assert result["availability_type"] == "not_available"
        assert result["baseline"]["base"] is None
        assert len(result["hard_failures"]) == 2
        if ticker == "PSKY":
            replay = result["rejected_conditional_replay"]
            assert replay["raw_range"]["base"] < 0
            assert replay["raw_range"]["high"] > 0
            assert replay["decision"].startswith("rejected_nonpositive_base")


@pytest.mark.parametrize("ticker", LAUNCH_FIRST_CONDITIONAL_TICKERS)
def test_real_launch_first_result_is_source_linked_conditional_low(ticker: str) -> None:
    result = build_batch_03_launch_first_result(
        ticker=ticker,
        source_root=SOURCE_ROOT,
        structural_root=STRUCTURAL_ROOT,
        primary_rejection_reasons=_rejection(ticker),
    )

    assert result["model_version"] == LAUNCH_FIRST_BATCH_03_VERSION
    assert result["availability_type"] == "conditional_estimate"
    assert set(result["reported_inputs"]) == {
        "ttm_revenue",
        "ttm_operating_cash_flow",
        "ttm_capex",
    }
    assert result["scenario_range"]["low"] <= result["scenario_range"]["base"] <= result["scenario_range"]["high"]
    assert result["scenario_range"]["high"] > 0
    assert result["baseline"]["confidence"] == "Low"
    assert [row["outcome"] for row in result["baseline"]["fallback_attempts"]] == [
        "rejected",
        "selected",
    ]
    assert all(
        row["reported_vs_estimated"] in {"reported", "absence_proven_zero"}
        for row in result["source_ledger"]["bridge"]["sources"]
        if "reported_vs_estimated" in row
    )


def test_tko_has_an_explicit_bear_only_limited_liability_floor() -> None:
    result = build_batch_03_launch_first_result(
        ticker="TKO",
        source_root=SOURCE_ROOT,
        structural_root=STRUCTURAL_ROOT,
        primary_rejection_reasons=_rejection("TKO"),
    )

    assert result["scenario_range"]["low"] == 0
    assert result["scenario_range"]["base"] > 0
    assert result["scenario_range"]["high"] > 0
    assert result["scenario_rows"][0]["limited_liability_floor_applied"] is True
    assert all(
        row["limited_liability_floor_applied"] is False
        for row in result["scenario_rows"][1:]
    )


def test_higher_wacc_and_lower_cash_margin_reduce_value() -> None:
    result = build_batch_03_launch_first_result(
        ticker="GOOGL",
        source_root=SOURCE_ROOT,
        structural_root=STRUCTURAL_ROOT,
        primary_rejection_reasons=_rejection("GOOGL"),
    )
    rows = result["scenario_rows"]

    assert [row["wacc"] for row in rows] == sorted(
        [row["wacc"] for row in rows], reverse=True
    )
    assert [row["cash_conversion_margin"] for row in rows] == sorted(
        row["cash_conversion_margin"] for row in rows
    )
    assert [row["conditional_value_per_share"] for row in rows] == sorted(
        row["conditional_value_per_share"] for row in rows
    )
    derivation = result["source_ledger"]["margin_derivation"]
    assert derivation["effective_reinvestment"][0] > result["reported_inputs"]["ttm_capex"]
    assert derivation["commitment_horizons_years"] == (5.0, 8.0, 12.0)


def test_foxa_reserve_includes_separate_program_rights() -> None:
    result = build_batch_03_launch_first_result(
        ticker="FOXA",
        source_root=SOURCE_ROOT,
        structural_root=STRUCTURAL_ROOT,
        primary_rejection_reasons=_rejection("FOXA"),
    )
    derivation = result["source_ledger"]["margin_derivation"]
    assert derivation["incremental_reserve_amounts"] == pytest.approx(
        [797_700_000.0, 398_850_000.0, 0.0]
    )


def test_tko_nci_and_class_b_units_reconcile_to_diluted_shares() -> None:
    result = build_batch_03_launch_first_result(
        ticker="TKO",
        source_root=SOURCE_ROOT,
        structural_root=STRUCTURAL_ROOT,
        primary_rejection_reasons=_rejection("TKO"),
    )
    reconciliation = result["source_ledger"]["bridge"]["nci_share_reconciliation"]
    assert reconciliation["difference"] == 0
    assert reconciliation["conversion_ratio"] == 1
    assert reconciliation["nci_deducted_separately"] is False
