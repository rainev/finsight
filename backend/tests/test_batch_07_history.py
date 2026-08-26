from pathlib import Path

import pytest

from app.us_valuation.batch_02_conditional_estimates import five_year_fcff_dcf
from app.us_valuation.batch_07 import BATCH_07_MANIFEST, BATCH_07_TICKERS
from app.us_valuation.batch_07_history import PASS_TICKERS, P, build_batch_07_history_result
from app.us_valuation.calculator import calculate
from run_batch_07_history import _public


SOURCE = Path("output/batch-07-sec-source-packets-20260826")
STRUCTURAL = Path("output/batch-07-structural-sources-20260826")


def _result(ticker: str) -> dict:
    return build_batch_07_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL)


def test_batch_07_is_exactly_six_pass_four_conditional_zero_withheld() -> None:
    assert PASS_TICKERS == {"EBAY", "TPR", "GRMN", "DPZ"}
    assert len(BATCH_07_TICKERS) == 10
    for ticker in BATCH_07_TICKERS:
        result = _result(ticker)
        expected = "available" if ticker in PASS_TICKERS else "conditional_estimate"
        assert result["availability_type"] == expected
        assert 0 <= result["scenario_range"]["low"] <= result["scenario_range"]["base"] <= result["scenario_range"]["high"]
        assert result["scenario_range"]["base"] > 0


def test_every_company_uses_three_to_five_unique_historical_periods() -> None:
    for ticker in BATCH_07_TICKERS:
        result = _result(ticker)
        history = result["source_ledger"]["company_history_profile"]
        periods = history["annual_periods"]
        assert 3 <= len(periods) <= 5
        assert len(periods) == len(set(periods))
        assert history["full_history"] is True
        assert result["governed_assumptions"]["assumption_source_mix"] == "reported_and_company_history"


def test_wynn_uses_current_revenue_concept_not_stale_2018_value() -> None:
    result = _result("WYNN")
    revenue = result["source_ledger"]["flow_sources"]["revenue"]
    assert revenue["value"] == 7_413_425_000
    assert revenue["period_end"] == "2026-06-30"
    assert {row["concept"] for row in revenue["sources"]} == {"RevenueFromContractWithCustomerIncludingAssessedTax"}


def test_garmin_latest_h1_is_reconstructed_and_debt_is_proven_absent() -> None:
    result = _result("GRMN")
    inputs = result["reported_inputs"]
    assert inputs["ttm_revenue"] == 7_671_438_000
    assert inputs["ttm_operating_cash_flow"] == 1_978_944_000
    assert inputs["ttm_capex"] == 379_103_000
    assert result["source_ledger"]["flow_sources"]["revenue"]["period_end"] == "2026-06-27"
    debt = [row for row in result["source_ledger"]["bridge_sources"] if row.get("field") == "interest_bearing_debt"]
    assert debt and debt[0]["reported_vs_estimated"] == "source_proven_absent"


def test_customer_funds_are_not_counted_as_excess_cash_or_bridge_debt() -> None:
    expected_cash = {"EBAY": 3_620_000_000, "BKNG": 12_006_500_000, "EXPE": 4_725_000_000}
    for ticker, cash in expected_cash.items():
        bridge = _result(ticker)["source_ledger"]["bridge_reconciliation"]
        assert bridge["cash_and_investments"] == cash
        assert "not subtracted again" in bridge["merchant_or_customer_funds_treatment"]


def test_challenge_repairs_cover_debt_nci_and_casino_reinvestment() -> None:
    assert P["EL"].debt == 7_312_000_000
    assert P["DPZ"].debt == 4_883_644_000
    assert P["TSLA"].debt == 9_342_000_000
    expedia = _result("EXPE")
    assert expedia["source_ledger"]["bridge_reconciliation"]["nci_range"] == (1_262_000_000,) * 3
    assert any(row.get("concept") == "us-gaap:NonredeemableNoncontrollingInterest" for row in expedia["source_ledger"]["bridge_sources"])
    for ticker in ("WYNN", "LVS"):
        result = _result(ticker)
        assert result["governed_assumptions"]["pandemic_downturn_stress"] is True
        assert result["scenario_range"]["low"] == 0
    las_vegas_sands = _result("LVS")
    commitment = [row for row in las_vegas_sands["source_ledger"]["bridge_sources"] if row.get("field") == "macao_concession_forward_reinvestment"]
    assert commitment[0]["reported_commitment"] == 4_440_000_000
    assert las_vegas_sands["governed_assumptions"]["forward_development_cash_reserve"] == (888_000_000, 444_000_000, 222_000_000)
    singapore = [row for row in las_vegas_sands["source_ledger"]["bridge_sources"] if row.get("field") == "singapore_expansion_nonoverlap"]
    assert singapore[0]["current_ttm_capex"] == 1_029_000_000
    tesla = _result("TSLA")
    share_source = [row for row in tesla["source_ledger"]["bridge_sources"] if row.get("concept") == "us-gaap:CommonStockSharesOutstanding"]
    assert share_source[0]["unit"] == "xbrli:shares"
    credit = [row for row in tesla["source_ledger"]["bridge_sources"] if row.get("field") == "automotive_regulatory_credit_cash_dependency"]
    assert credit[0]["current_h1"] == 526_000_000
    assert tesla["governed_assumptions"]["cash_dependency_reserve"] == (1_052_000_000, 526_000_000, 0)
    assert _result("BKNG")["source_ledger"]["bridge_reconciliation"]["cash_and_investments_range"] == (7_093_000_000, 12_006_500_000, 16_920_000_000)
    assert _result("EXPE")["source_ledger"]["bridge_reconciliation"]["cash_and_investments_range"] == (445_000_000, 4_725_000_000, 7_127_000_000)


def test_higher_wacc_lowers_value_holding_other_base_inputs_constant() -> None:
    for ticker in BATCH_07_TICKERS:
        result = _result(ticker)
        policy = P[ticker]
        base = result["scenario_rows"][1]
        common = dict(revenue=result["reported_inputs"]["ttm_revenue"], fcff_margin=base["cash_conversion_margin"], growth=base["growth"], terminal_growth=base["terminal_growth"], cash_and_investments=policy.cash, debt=policy.debt, noncontrolling_interests=policy.nci[1], shares=policy.shares[1])
        lower = five_year_fcff_dcf(wacc=base["wacc"] - .01, **common)["value_per_share"]
        higher = five_year_fcff_dcf(wacc=base["wacc"] + .01, **common)["value_per_share"]
        assert lower > base["conditional_value_per_share"] > higher


def test_public_artifacts_match_and_do_not_leak_private_history() -> None:
    for issuer in BATCH_07_MANIFEST:
        result = _result(issuer.ticker)
        public = _public(issuer, result)
        assert public["scenario_range"] == {**result["scenario_range"], "label": "assumption range, not a statistical confidence interval or recommendation"}
        assert public["availability_type"] == ("available" if issuer.ticker in PASS_TICKERS else "conditional_estimate")
        assert public["public_assumptions"]["history_years_used"] >= 3
        assert "company_history_profile" not in public
        assert "source_ledger" not in public
        assert calculate(public, overrides={}, manual_price=None)["result"]["base"] == pytest.approx(result["scenario_range"]["base"])
