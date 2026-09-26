from __future__ import annotations

import pytest

from app.pse_valuation.models.comparables import comparable_cross_check, market_relative_range
from app.pse_valuation.models.distributions import distribution_valuation
from app.pse_valuation.models.fcff import fcff_valuation
from app.pse_valuation.models.residual_income import residual_income_valuation
from app.pse_valuation.models.sotp import sotp_valuation


def test_fcff_zero_growth_perpetuity_reconciles() -> None:
    result = fcff_valuation(
        starting_nopat=100,
        growth_rate=0,
        roic=0.10,
        wacc=0.10,
        terminal_growth=0,
        terminal_roic=0.10,
        shares_outstanding=10,
        forecast_years=1,
    )
    assert result["enterprise_value"] == pytest.approx(1000)
    assert result["common_equity_value"] == pytest.approx(1000)
    assert result["value_per_share"] == pytest.approx(100)


def test_fcff_finite_life_has_no_perpetuity() -> None:
    result = fcff_valuation(
        starting_nopat=100,
        growth_rate=0,
        roic=0.10,
        wacc=0.10,
        shares_outstanding=10,
        forecast_years=2,
        finite_life_years=2,
        residual_value=0,
    )
    assert result["finite_life"] is True
    assert result["terminal_value"] == 0
    assert result["enterprise_value"] == pytest.approx(100 / 1.1 + 100 / 1.1**2)


def test_fcff_terminal_reinvestment_is_economically_funded() -> None:
    result = fcff_valuation(
        starting_nopat=100,
        growth_rate=0.05,
        roic=0.20,
        wacc=0.12,
        terminal_growth=0.03,
        terminal_roic=0.10,
        shares_outstanding=10,
    )
    assert result["schedule"][0]["reinvestment"] == pytest.approx(105 * 0.25)
    assert result["present_value_terminal"] > 0


def test_residual_income_returns_book_value_when_roe_equals_cost_of_equity() -> None:
    result = residual_income_valuation(
        opening_common_equity=100,
        shares_outstanding=10,
        current_roe=0.10,
        terminal_roe=0.10,
        cost_of_equity=0.10,
        payout_ratio=1.0,
        terminal_growth=0,
    )
    assert result["common_equity_value"] == pytest.approx(100)
    assert result["value_per_share"] == pytest.approx(10)
    assert result["justified_pb"] == pytest.approx(1)


def test_distribution_zero_growth_reconciles_to_perpetuity() -> None:
    result = distribution_valuation(
        current_distribution_per_share=1,
        explicit_growth=0,
        cost_of_equity=0.10,
        terminal_growth=0,
    )
    assert result["value_per_share"] == pytest.approx(10)


def test_distribution_finite_life_has_no_perpetuity() -> None:
    result = distribution_valuation(
        current_distribution_per_share=1,
        explicit_growth=0,
        cost_of_equity=0.10,
        forecast_years=2,
        finite_life_years=2,
    )
    assert result["finite_life"] is True
    assert result["terminal_value"] == 0
    assert result["value_per_share"] == pytest.approx(1 / 1.1 + 1 / 1.1**2)


def test_distribution_finite_life_rejects_horizon_mismatch() -> None:
    with pytest.raises(ValueError, match="finite_life_years"):
        distribution_valuation(
            current_distribution_per_share=1,
            explicit_growth=0,
            cost_of_equity=0.10,
            forecast_years=5,
            finite_life_years=4,
        )


def test_sotp_applies_ownership_before_parent_claims() -> None:
    result = sotp_valuation(
        components=[
            {"name": "Listed bank", "equity_value": 1000, "ownership": 0.50},
            {"name": "Industrial", "equity_value": 500, "ownership": 0.80},
        ],
        parent_cash=50,
        parent_debt=100,
        present_value_parent_costs=25,
        shares_outstanding=10,
    )
    assert result["attributable_component_value"] == pytest.approx(900)
    assert result["common_equity_value"] == pytest.approx(825)
    assert result["value_per_share"] == pytest.approx(82.5)


def test_comparables_are_separately_labeled_market_relative() -> None:
    result = comparable_cross_check(
        metric="price_to_book",
        peer_multiples=[1.0, 1.5, 2.0],
        target_metric_per_share=20,
    )
    assert result["output_type"] == "market_relative_only"
    assert result["estimate_per_share"] == pytest.approx(30)


def test_market_relative_ranges_support_multiple_and_yield_screens() -> None:
    pe = market_relative_range(
        metric="price_to_earnings",
        metric_value_per_share=10,
        assumptions={"low": 8, "base": 10, "high": 12},
    )
    distribution = market_relative_range(
        metric="distribution_yield",
        metric_value_per_share=2.4,
        assumptions={"low": 0.08, "base": 0.06, "high": 0.04},
        relation="yield",
    )
    assert pe["estimates"] == {"low": 80, "base": 100, "high": 120}
    assert distribution["estimates"] == pytest.approx({"low": 30, "base": 40, "high": 60})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"wacc": 0.03, "terminal_growth": 0.03, "terminal_roic": 0.10},
        {"wacc": 0.10, "terminal_growth": 0.03, "terminal_roic": 0.02},
    ],
)
def test_fcff_rejects_unsupported_terminal_economics(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        fcff_valuation(
            starting_nopat=100,
            growth_rate=0.02,
            roic=0.10,
            shares_outstanding=10,
            **kwargs,
        )
