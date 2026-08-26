from pathlib import Path

import pytest

from app.us_valuation.batch_08 import BATCH_08_MANIFEST, BATCH_08_TICKERS
from app.us_valuation.batch_08_history import PASS_TICKERS, build_batch_08_history_result
from app.us_valuation.calculator import calculate, calculator_view
from run_batch_08_history import _public


SOURCE = Path("output/batch-08-sec-source-packets-20260826")
STRUCTURAL = Path("output/batch-08-structural-sources-20260826")


def _result(ticker: str) -> dict:
    return build_batch_08_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL)


def test_batch_08_is_two_pass_six_conditional_two_withheld() -> None:
    assert PASS_TICKERS == {"ULTA", "HLT"}
    expected = {"LULU": "conditional_estimate", "ULTA": "available", "KDP": "conditional_estimate", "GM": "conditional_estimate", "NCLH": "not_available", "APTV": "not_available", "ABNB": "conditional_estimate", "HLT": "available", "CVNA": "conditional_estimate", "DASH": "conditional_estimate"}
    assert tuple(expected) == BATCH_08_TICKERS
    for ticker, availability in expected.items():
        result = _result(ticker)
        assert result["availability_type"] == availability
        if availability == "not_available":
            assert result["scenario_range"] == {"low": None, "base": None, "high": None}
        else:
            values = result["scenario_range"]
            assert 0 <= values["low"] <= values["base"] <= values["high"]
            assert values["base"] > 0


def test_numeric_history_is_source_linked_and_aptiv_fails_closed() -> None:
    for ticker in BATCH_08_TICKERS:
        result = _result(ticker)
        if ticker == "APTV":
            assert result["governed_assumptions"]["normalization_basis"] == "post_spin_comparable_history_unavailable"
            assert len(result["source_ledger"]["post_spin_context"]) == 3
            continue
        history = result["source_ledger"]["company_history_profile"]
        assert 3 <= len(history["annual_periods"]) <= 5
        assert len(history["annual_periods"]) == len(set(history["annual_periods"]))
        assert history["full_history"] is True


def test_current_specialist_bridges_and_events_are_bound() -> None:
    lulu = _result("LULU")
    assert any(row.get("concept") == "us-gaap:SupplierFinanceProgramObligationCurrent" and row["value"] == 39_900_000 for row in lulu["source_ledger"]["bridge_sources"])
    assert any(row.get("field") == "tariff_margin_stress" for row in lulu["source_ledger"]["bridge_sources"])
    ulta = _result("ULTA")
    assert ulta["source_ledger"]["bridge_reconciliation"]["debt_and_finance_leases"] == 144_899_000
    kdp = _result("KDP")
    bridge = kdp["source_ledger"]["bridge_reconciliation"]
    assert bridge["debt_and_finance_leases"] == 31_006_000_000
    assert bridge["nci_or_event_claim_range"] == (9_096_000_000, 8_939_000_000, 8_614_000_000)
    assert kdp["reported_inputs"]["revenue_anchor"] == 28_258_000_000
    nclh = _result("NCLH")
    assert nclh["availability_type"] == "not_available"
    assert nclh["source_ledger"]["bridge_reconciliation"]["carrying_debt"] == 15_034_785_000
    assert any(row.get("field") == "newbuild_commitments" and row["reported_commitment"] == 18_648_000_000 for row in nclh["source_ledger"]["bridge_sources"])


def test_customer_funds_capex_software_and_convertibles_are_not_silent() -> None:
    airbnb = _result("ABNB")
    assert airbnb["governed_assumptions"]["capex_range"] == (84_000_000, 42_000_000, 21_000_000)
    assert any(str(row.get("concept")).endswith(":CashAndCashEquivalentsIncludedInFundsReceivableAndAmountsHeldOnBehalfOfCustomers") and row["value"] == 12_161_000_000 for row in airbnb["source_ledger"]["bridge_sources"])
    dash = _result("DASH")
    assert dash["reported_inputs"]["ttm_capex"] == 691_000_000
    capex = dash["source_ledger"]["flow_sources"]["capital_expenditures"]
    assert capex["components"]["software"]["value"] == 456_000_000
    assert any(row.get("concept") == "us-gaap:ConvertibleLongTermNotesPayable" and row["value"] == 2_727_000_000 for row in dash["source_ledger"]["bridge_sources"])


def test_gm_and_carvana_use_equity_level_models_without_debt_bridge() -> None:
    for ticker in ("GM", "CVNA"):
        result = _result(ticker)
        assert result["governed_assumptions"]["ev_debt_bridge_applied"] is False
        assert "equity_earnings" in result["method"]
        components = result["source_ledger"]["current_earnings_reconstruction"]
        assert components["fy"] + components["current_h1"]["value"] - components["prior_h1"]["value"] == components["ttm"]
        assert "No EV debt bridge" in result["source_ledger"]["bridge_treatment"]


def test_public_artifacts_match_private_outcomes_and_calculator() -> None:
    for issuer in BATCH_08_MANIFEST:
        result = _result(issuer.ticker)
        public = _public(issuer, result)
        assert public["availability_type"] == result["availability_type"]
        assert public["scenario_range"]["base"] == result["scenario_range"]["base"]
        assert "source_ledger" not in public
        assert "company_history_profile" not in public
        view = calculator_view(public)
        if result["availability_type"] == "not_available":
            assert view["can_calculate"] is False
        else:
            assert calculate(public, overrides={}, manual_price=None)["result"]["base"] == pytest.approx(result["scenario_range"]["base"])
