"""Mechanical and directional tests for practical valuation models."""

import pytest

from app.us_valuation.practical_models import (
    BankPracticalInputs,
    EquityCashFlowState,
    CyclicalOperatingState,
    captive_finance_owner_cash_flow,
    fcff_value_with_capital_efficiency,
    practical_bank_residual_income_range,
    practical_equity_cash_flow_range,
    practical_cyclical_fcff_range,
    mixed_utility_fcfe,
    practical_fcff_one_way_sensitivities,
    practical_fcff_scenarios,
    practical_reit_range,
    research_profitability_sensitivity,
    two_stage_cash_flow_value,
)
from app.us_valuation.practical_policy import ValueRange


def test_rd_life_changes_profitability_but_not_current_cash_fcff() -> None:
    result = research_profitability_sensitivity(
        rd_history_newest_first=(70.0, 60.0, 50.0, 40.0, 30.0, 20.0, 10.0, 5.0),
        reported_ebit=100.0,
        reported_operating_capital=500.0,
        reported_fcff=80.0,
    )
    assert len({row["adjusted_ebit"] for row in result["rows"]}) == 3
    assert {row["current_cash_fcff"] for row in result["rows"]} == {80.0}
    assert result["cash_flow_adjustment"] == 0.0


def test_higher_discount_rate_lowers_cash_flow_value() -> None:
    low_discount = two_stage_cash_flow_value(
        cash_flow_per_share=5.0,
        growth_rate=0.04,
        growth_years=8,
        terminal_growth=0.02,
        discount_rate=0.08,
    )
    high_discount = two_stage_cash_flow_value(
        cash_flow_per_share=5.0,
        growth_rate=0.04,
        growth_years=8,
        terminal_growth=0.02,
        discount_rate=0.11,
    )
    assert high_discount < low_discount


def test_equity_cash_flow_range_is_ordered_and_has_bounded_terminal_share() -> None:
    values, traces = practical_equity_cash_flow_range(
        states={
            "bear": EquityCashFlowState(80.0, 0.01, 0.01, 0.11),
            "base": EquityCashFlowState(100.0, 0.03, 0.02, 0.10),
            "bull": EquityCashFlowState(120.0, 0.04, 0.025, 0.09),
        },
        diluted_shares=10.0,
    )
    assert 0 < values.low < values.base < values.high
    assert all(row["terminal_share"] <= 0.85 for row in traces.values())


def test_equity_cash_flow_value_falls_with_cost_of_equity() -> None:
    low_cost, _ = practical_equity_cash_flow_range(
        states={
            name: EquityCashFlowState(100.0, 0.02, 0.01, 0.09)
            for name in ("bear", "base", "bull")
        },
        diluted_shares=10.0,
    )
    high_cost, _ = practical_equity_cash_flow_range(
        states={
            name: EquityCashFlowState(100.0, 0.02, 0.01, 0.11)
            for name in ("bear", "base", "bull")
        },
        diluted_shares=10.0,
    )
    assert high_cost.base < low_cost.base


def test_cyclical_states_are_issuer_balanced_and_claims_lower_value() -> None:
    current = CyclicalOperatingState("WDC", "2026", 120.0, 0.30, 0.03, 0.035)
    states = [
        CyclicalOperatingState("WDC", str(year), revenue, margin, 0.04, 0.04)
        for year, revenue, margin in ((2024, 70.0, -0.05), (2025, 95.0, 0.20), (2026, 120.0, 0.30))
    ] + [
        CyclicalOperatingState("STX", str(year), 90.0 + year, 0.08 + year / 100.0, 0.04, 0.045)
        for year in range(10)
    ]
    base, trace = practical_cyclical_fcff_range(
        current_state=current,
        observed_states=states,
        operating_nwc_ratio=0.01,
        normalized_tax_rate=0.21,
        wacc=0.10,
        cash=10.0,
        debt=5.0,
        other_claims=ValueRange(1.0, 2.0, 3.0),
        diluted_shares=10.0,
    )
    more_claims, _ = practical_cyclical_fcff_range(
        current_state=current,
        observed_states=states,
        operating_nwc_ratio=0.01,
        normalized_tax_rate=0.21,
        wacc=0.10,
        cash=10.0,
        debt=5.0,
        other_claims=ValueRange(2.0, 3.0, 4.0),
        diluted_shares=10.0,
    )
    assert trace["issuer_weights"] == {"STX": 0.5, "WDC": 0.5}
    assert 0 < base.low <= base.base <= base.high
    assert more_claims.base < base.base


def test_recovery_fcfe_directions_and_no_finance_double_count() -> None:
    utility = mixed_utility_fcfe(
        operating_cash_flow=100.0,
        capital_expenditures=120.0,
        net_income=50.0,
        debt_funding_share=0.75,
        parent_cash_flow_share=0.80,
    )
    more_capex = mixed_utility_fcfe(
        operating_cash_flow=100.0,
        capital_expenditures=130.0,
        net_income=50.0,
        debt_funding_share=0.75,
        parent_cash_flow_share=0.80,
    )
    assert more_capex < utility

    dell = captive_finance_owner_cash_flow(
        adjusted_free_cash_flow=100.0,
        finance_asset_growth=16.0,
        debt_to_equity=7.0,
    )
    assert dell == pytest.approx(98.0)
    assert captive_finance_owner_cash_flow(
        adjusted_free_cash_flow=100.0,
        finance_asset_growth=24.0,
        debt_to_equity=7.0,
    ) < dell


def test_higher_ai_capital_spending_lowers_value_without_more_cash_flow() -> None:
    assumptions = {
        "forecast_years": 5,
        "normalized_tax_rate": 0.20,
        "initial_revenue_growth": 0.10,
        "target_operating_margin": 0.25,
        "sales_to_capital": 2.0,
        "starting_revenue": 100.0,
        "starting_operating_margin": 0.25,
        "terminal_growth": 0.02,
        "initial_marginal_roic": 0.40,
        "terminal_marginal_roic": 0.10,
        "growth_persistence": 0.78,
        "margin_persistence": 0.78,
        "segment_forecast": None,
        "terminal_roic_basis": "competitive_fade_to_wacc",
    }
    financials = {
        "balance_sheet": {
            "cash_and_nonoperating_investments": 0.0,
            "total_interest_bearing_debt": 0.0,
            "preferred_equity": 0.0,
            "noncontrolling_interests": 0.0,
            "fully_diluted_shares_proxy": 1.0,
        }
    }
    lower_spending = fcff_value_with_capital_efficiency(
        assumptions=assumptions,
        discount_rate={"wacc": 0.10},
        financials=financials,
        capital_efficiency_multiplier=1.0,
    )
    higher_spending = fcff_value_with_capital_efficiency(
        assumptions=assumptions,
        discount_rate={"wacc": 0.10},
        financials=financials,
        capital_efficiency_multiplier=0.65,
    )
    assert higher_spending < lower_spending

    sensitivities = practical_fcff_one_way_sensitivities(
        assumptions=assumptions,
        discount_rate={"wacc": 0.10},
        financials=financials,
        base_capital_efficiency_multiplier=0.75,
        share_range=(1.0, 1.1, 1.2),
    )
    wacc = [row for row in sensitivities if row["field"] == "wacc"]
    capital = [
        row for row in sensitivities if row["field"] == "sales_to_capital"
    ]
    shares = [row for row in sensitivities if row["field"] == "diluted_shares"]
    assert wacc[0]["intrinsic_value_per_share"] > wacc[1]["intrinsic_value_per_share"] > wacc[2]["intrinsic_value_per_share"]
    assert capital[0]["intrinsic_value_per_share"] < capital[1]["intrinsic_value_per_share"] < capital[2]["intrinsic_value_per_share"]
    assert shares[0]["intrinsic_value_per_share"] > shares[1]["intrinsic_value_per_share"] > shares[2]["intrinsic_value_per_share"]

    scenarios = practical_fcff_scenarios(
        assumptions=assumptions,
        discount_rate={"wacc": 0.10},
        financials=financials,
        capital_efficiency_multipliers={
            "bear": 0.60,
            "base": 0.75,
            "bull": 0.90,
        },
    )
    assert scenarios["base"]["assumptions"]["sales_to_capital"] == pytest.approx(
        assumptions["sales_to_capital"] * 0.75
    )
    base_capital_row = next(
        row
        for row in sensitivities
        if row["field"] == "sales_to_capital" and row["delta"] == 0
    )
    assert base_capital_row["intrinsic_value_per_share"] == pytest.approx(
        scenarios["base"]["fcff_dcf"]["equity_value"] / 1.1
    )


def test_bank_capital_uncertainty_produces_finite_ordered_range() -> None:
    value_range, trace = practical_bank_residual_income_range(
        BankPracticalInputs(
            beginning_total_equity=362.438,
            ending_total_equity=374.598,
            beginning_preferred_low=20.045,
            beginning_preferred_high=20.045,
            ending_preferred_low=21.040,
            ending_preferred_high=21.040,
            ttm_common_net_income=63.634,
            ending_common_shares=2.658186195,
            cost_of_equity=0.095,
            terminal_growth=0.03,
            forecast_years=5,
            terminal_roe=0.12,
        )
    )
    assert 0 < value_range.low <= value_range.base <= value_range.high
    assert trace["bear"]["ending_common_equity"] == pytest.approx(353.558)
    assert trace["base"]["ttm_common_net_income"] == pytest.approx(63.634)
    assert trace["bear"]["terminal_roe"] < trace["base"]["terminal_roe"]
    assert trace["bear"]["terminal_roe"] < trace["bear"]["cost_of_equity"]


def test_reit_maintenance_capex_and_cap_rate_both_lower_value() -> None:
    base_range, base_trace = practical_reit_range(
        ffo=3_405.15,
        straight_line_rent=164.344,
        maintenance_capex_range=ValueRange(130.102, 523.956, 531.159),
        diluted_shares=908.334,
        annualized_lease_income=5_437.332,
        cap_rate_range=ValueRange(0.0798, 0.0865, 0.0875),
        cash=434.842,
        debt=25_031.947,
        preferred_equity=167.394,
        noncontrolling_interests=2_384.520,
    )
    more_capex, _ = practical_reit_range(
        ffo=3_405.15,
        straight_line_rent=164.344,
        maintenance_capex_range=ValueRange(230.102, 623.956, 631.159),
        diluted_shares=908.334,
        annualized_lease_income=5_437.332,
        cap_rate_range=ValueRange(0.0798, 0.0865, 0.0875),
        cash=434.842,
        debt=25_031.947,
        preferred_equity=167.394,
        noncontrolling_interests=2_384.520,
    )
    higher_cap_rate, higher_cap_trace = practical_reit_range(
        ffo=3_405.15,
        straight_line_rent=164.344,
        maintenance_capex_range=ValueRange(130.102, 523.956, 531.159),
        diluted_shares=908.334,
        annualized_lease_income=5_437.332,
        cap_rate_range=ValueRange(0.0898, 0.0965, 0.0975),
        cash=434.842,
        debt=25_031.947,
        preferred_equity=167.394,
        noncontrolling_interests=2_384.520,
    )
    assert more_capex.base < base_range.base
    assert higher_cap_rate.base == pytest.approx(base_range.base)
    assert (
        higher_cap_trace["gross_lease_capitalization_support_per_share"]["base"]
        < base_trace["gross_lease_capitalization_support_per_share"]["base"]
    )
