from __future__ import annotations

import json
from pathlib import Path
import sys

from app.us_valuation.batch_11 import BATCH_11_MANIFEST, BATCH_11_TICKERS
from app.us_valuation.batch_11_history import (
    PASS_TICKERS,
    build_batch_11_history_result,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "output/batch-11-sec-source-packets-20260828"
STRUCTURAL = ROOT / "output/batch-11-structural-sources-final-a"
sys.path.insert(0, str(ROOT / "scripts"))


def _result(ticker: str):
    return build_batch_11_history_result(
        ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL
    )


def test_batch_11_exact_initial_outcomes_and_ranges():
    rows = {ticker: _result(ticker) for ticker in BATCH_11_TICKERS}
    assert {
        ticker for ticker, row in rows.items() if row["availability_type"] == "available"
    } == set(PASS_TICKERS)
    assert {
        ticker
        for ticker, row in rows.items()
        if row["availability_type"] == "conditional_estimate"
    } == {"CHD", "COST", "DLTR", "MDLZ", "PM", "KHC"}
    assert {
        ticker
        for ticker, row in rows.items()
        if row["availability_type"] == "not_available"
    } == {"SYY", "BG"}
    for ticker, row in rows.items():
        if ticker in {"SYY", "BG"}:
            assert row["scenario_range"] == {"low": None, "base": None, "high": None}
            continue
        scenario = row["scenario_range"]
        assert 0 <= scenario["low"] <= scenario["base"] <= scenario["high"]
        assert scenario["base"] > 0
        assert row["governed_assumptions"]["history_years_used"] >= 3


def test_batch_11_sources_periods_units_shares_and_bridges_are_bound():
    expected = {
        "SYY": ("2026-03-28", 1_900_000_000., 14_008_000_000., 0., 480_738_926.),
        "CHD": ("2026-06-30", 254_800_000., 2_256_200_000., 14_600_000., 238_200_000.),
        "MO": ("2026-06-30", 2_367_000_000., 24_577_000_000., 50_000_000., 1_672_000_000.),
        "MNST": ("2026-06-30", 4_200_570_000., 0., 0., 988_456_000.),
        "COST": ("2026-05-10", 19_996_000_000., 5_670_000_000., 0., 444_455_000.),
        "DLTR": ("2026-05-02", 1_007_300_000., 2_932_600_000., 0., 197_400_000.),
        "MDLZ": ("2026-06-30", 1_716_000_000., 21_450_000_000., 53_000_000., 1_286_000_000.),
        "PM": ("2026-06-30", 5_999_000_000., 49_113_000_000., 1_926_000_000., 1_560_000_000.),
        "KHC": ("2026-06-27", 2_681_000_000., 19_001_000_000., 124_000_000., 1_186_000_000.),
        "BG": ("2026-06-30", 788_000_000., 15_214_000_000., 1_457_000_000., 195_536_176.),
    }
    for ticker, (period, cash, debt, claims, shares) in expected.items():
        row = _result(ticker)
        assert row["source_ledger"]["controlling_filing"]["period_end"] == period
        bridge = row["source_ledger"]["bridge_reconciliation"]
        assert bridge["cash_and_investments"] == cash
        assert bridge["debt_and_finance_leases"] == debt
        assert bridge["preferred_nci_and_redeemable_claims"] == claims
        assert bridge["shares"][1] == shares
        assert all(
            source.get("unit") in {None, "USD", "shares", "xbrli:shares"}
            for source in row["source_ledger"]["bridge_sources"]
        )


def test_batch_11_arithmetic_and_sensitivity_directions():
    for ticker in BATCH_11_TICKERS:
        if ticker in {"SYY", "BG"}:
            continue
        row = _result(ticker)
        scenarios = row["scenario_rows"]
        assert scenarios[0]["wacc"] > scenarios[1]["wacc"] > scenarios[2]["wacc"]
        assert (
            scenarios[0]["cash_conversion_margin"]
            <= scenarios[1]["cash_conversion_margin"]
            <= scenarios[2]["cash_conversion_margin"]
        )
        assert (
            scenarios[0]["conditional_value_per_share"]
            <= scenarios[1]["conditional_value_per_share"]
            <= scenarios[2]["conditional_value_per_share"]
        )
        assert scenarios[0]["shares"] > scenarios[1]["shares"] > scenarios[2]["shares"]


def test_batch_11_special_paths_fail_closed_or_use_current_period():
    monster = _result("MNST")
    assert monster["reported_inputs"]["ttm_interest"] == 0
    assert (
        monster["source_ledger"]["flow_sources"]["interest_expense"]["method"]
        == "not_applicable_source_proven_no_debt"
    )
    assert _result("MO")["reported_inputs"]["ttm_interest"] == 1_193_000_000.
    assert _result("PM")["reported_inputs"]["ttm_interest"] == 1_549_000_000.
    assert (
        _result("MO")["source_ledger"]["flow_sources"]["interest_expense"]["method"]
        == "latest_fy_expense_magnitude_plus_current_h1_magnitude_minus_prior_h1_magnitude"
    )
    assert "$1.169B accrued settlement" in _result("MO")["source_ledger"][
        "bridge_reconciliation"
    ]["settlement_liability_treatment"]
    assert "$2.900B supplier-finance" in _result("MDLZ")["source_ledger"][
        "bridge_reconciliation"
    ]["supplier_finance_and_operating_leases"]
    assert "$3.6555B noncurrent operating leases" in _result("DLTR")[
        "source_ledger"
    ]["bridge_reconciliation"]["supplier_finance_and_operating_leases"]
    assert _result("COST")["source_ledger"]["bridge_reconciliation"][
        "finance_lease_liability_reserve"
    ] == {"bear": 57_000_000., "base": 28_500_000., "bull": 0.}
    mondelez = _result("MDLZ")
    assert mondelez["reported_inputs"]["ttm_revenue"] == 39_675_000_000.
    assert all(
        flow["period_end"] == "2026-06-30"
        for flow in mondelez["source_ledger"]["flow_sources"].values()
    )
    bunge = _result("BG")
    assert bunge["scenario_range"]["base"] is None
    assert "comparable combined" in bunge["source_ledger"]["release_condition"]
    sysco = _result("SYY")
    assert sysco["scenario_range"]["base"] is None
    assert "Jetro" in sysco["source_ledger"]["release_condition"]


def test_batch_11_cutoff_excludes_later_filings_from_flows():
    for ticker in BATCH_11_TICKERS:
        result = _result(ticker)
        filing = result["source_ledger"]["controlling_filing"]
        assert filing["filed"] <= "2026-08-14"
        for flow in result["source_ledger"].get("flow_sources", {}).values():
            for source in flow.get("sources", []):
                filed = source.get("filed") or source.get("filed_date")
                if filed:
                    assert filed <= "2026-08-14"


def test_batch_11_public_contract_has_no_private_sources():
    from run_batch_11_history import _public

    for issuer in BATCH_11_MANIFEST:
        result = _result(issuer.ticker)
        public = _public(issuer, result)
        raw = json.dumps(public)
        assert public["availability_type"] == result["availability_type"]
        assert public["scenario_range"]["base"] == result["scenario_range"]["base"]
        assert "source_ledger" not in raw
        assert "company_history_profile" not in raw


def test_batch_11_structural_replay_embeds_filed_and_report_dates():
    summary = json.loads((STRUCTURAL / "summary.json").read_text())
    assert summary["attempted"] == summary["parsed"] == 10
    assert summary["failed"] == 0
    assert summary["reused_tickers"] == ["MO", "COST", "MDLZ", "PM"]
    assert summary["captured_tickers"] == ["SYY", "CHD", "MNST", "DLTR", "KHC", "BG"]
    for ticker in BATCH_11_TICKERS:
        package = json.loads((STRUCTURAL / ticker / "package-manifest.json").read_text())
        receipt = json.loads((STRUCTURAL / ticker / "source-receipt.json").read_text())
        assert package["filed_date"] == receipt["filing"]["filed"]
        assert package["report_date"] == receipt["filing"]["report_date"]
