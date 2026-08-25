"""Batch 03 source-bounded model and stop-gate contracts."""

from app.us_valuation.batch_03_practical_models import (
    BATCH_03_NUMERIC_TICKERS,
    WITHHELD_DECISIONS,
    build_batch_03_practical_result,
)


SOURCE_ROOT = "output/batch-03-sec-source-packets-20260824"
STRUCTURAL_ROOT = "output/batch-03-structural-sources-20260824"


def test_batch_03_exact_initial_numeric_and_withheld_sets() -> None:
    assert BATCH_03_NUMERIC_TICKERS == (
        "NWSA", "TTD", "DIS"
    )
    assert tuple(WITHHELD_DECISIONS) == (
        "LYV", "ECHO", "TKO", "GOOGL", "APP", "FOXA", "PSKY"
    )
    assert all(row["hard_blockers"] for row in WITHHELD_DECISIONS.values())


def test_all_six_numeric_ranges_replay_from_real_packets() -> None:
    for ticker in BATCH_03_NUMERIC_TICKERS:
        result = build_batch_03_practical_result(
            ticker=ticker,
            source_root=SOURCE_ROOT,
            structural_root=STRUCTURAL_ROOT,
        )
        values = result["scenario_range"]
        assert 0 < values["low"] <= values["base"] <= values["high"]
        assert result["reliability"]["label"] == "Low"
        assert result["private_inputs"]["bridge"]["sources"]
        assert result["source_financial_statement"]["filed_date"] <= "2026-08-14"


def test_higher_wacc_lowers_every_numeric_base_value() -> None:
    for ticker in BATCH_03_NUMERIC_TICKERS:
        result = build_batch_03_practical_result(
            ticker=ticker,
            source_root=SOURCE_ROOT,
            structural_root=STRUCTURAL_ROOT,
        )
        rows = [row for row in result["sensitivities"] if row["field"] == "wacc"]
        assert rows[0]["intrinsic_value_per_share"] > rows[1]["intrinsic_value_per_share"] > rows[2]["intrinsic_value_per_share"]


def test_forward_commitments_and_disney_investment_are_handled_explicitly() -> None:
    nwsa = build_batch_03_practical_result(
        ticker="NWSA", source_root=SOURCE_ROOT, structural_root=STRUCTURAL_ROOT
    )["private_inputs"]["forward_commitment_evidence"]
    assert nwsa["next_twelve_months"]["value"] == 573_000_000.0
    assert nwsa["bear_covers_next_twelve_months"] is True
    assert nwsa["excluded_nonliquid_long_term_investment"]["value"] == 1_002_000_000.0

    disney = build_batch_03_practical_result(
        ticker="DIS", source_root=SOURCE_ROOT, structural_root=STRUCTURAL_ROOT
    )["private_inputs"]
    assert disney["bridge"]["cash_and_investments"] == (
        5_185_000_000.0,
        5_185_000_000.0,
        5_185_000_000.0,
    )
    commitments = disney["forward_commitment_evidence"]
    assert commitments["content_balance_change"] < 0
    assert commitments["excluded_nonliquid_or_unclassified_investments"] == 7_627_000_000.0

    ttd = build_batch_03_practical_result(
        ticker="TTD", source_root=SOURCE_ROOT, structural_root=STRUCTURAL_ROOT
    )["private_inputs"]["forward_commitment_evidence"]
    assert ttd["total_commitments"] == 939_124_000.0
    assert ttd["remainder_2026"] == 97_937_000.0
    assert ttd["bear_covers_governed_first_year_stress"] is True
    assert ttd["commitments_are_operating_cash_items_not_bridge_debt"] is True
