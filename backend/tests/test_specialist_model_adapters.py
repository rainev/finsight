"""Hand-calculation and fail-closed tests for specialist model adapters."""

import pytest

from app.us_valuation.specialist_model_adapters import (
    capitalize_research_and_development,
    capital_constrained_payout_ratio,
    derive_bank_common_equity,
    normalize_complete_cycle,
    normalized_affo,
    property_nav_per_share,
    sum_of_parts_equity_per_share,
)


def test_research_capitalization_matches_straight_line_hand_calculation() -> None:
    result = capitalize_research_and_development(
        rd_history_newest_first=(30.0, 24.0, 18.0, 12.0),
        amortization_life_years=3,
        reported_ebit=100.0,
        reported_operating_capital=200.0,
    )

    assert result.research_asset == pytest.approx(52.0)
    assert result.research_amortization == pytest.approx(18.0)
    assert result.adjusted_ebit == pytest.approx(112.0)
    assert result.adjusted_operating_capital == pytest.approx(252.0)


def test_research_adapter_has_no_default_asset_life_or_missing_history() -> None:
    with pytest.raises(ValueError, match="positive"):
        capitalize_research_and_development(
            rd_history_newest_first=(30.0,),
            amortization_life_years=0,
            reported_ebit=100.0,
            reported_operating_capital=200.0,
        )
    with pytest.raises(ValueError, match="R&D history"):
        capitalize_research_and_development(
            rd_history_newest_first=(30.0, 24.0),
            amortization_life_years=3,
            reported_ebit=100.0,
            reported_operating_capital=200.0,
        )


def test_wdc_three_year_trace_cannot_claim_a_complete_cycle() -> None:
    with pytest.raises(ValueError, match="complete-cycle"):
        normalize_complete_cycle(
            revenue_history=(6.317, 9.520, 12.919),
            operating_income_history=(-0.403, 2.334, 4.453),
            complete_cycle_evidence=False,
        )

    result = normalize_complete_cycle(
        revenue_history=(6.317, 9.520, 12.919),
        operating_income_history=(-0.403, 2.334, 4.453),
        complete_cycle_evidence=True,
    )
    assert result.normalized_revenue == pytest.approx(9.520)
    assert result.normalized_margin == pytest.approx(2.334 / 9.520)
    assert result.observed_margin_low == pytest.approx(-0.403 / 6.317)
    assert result.observed_margin_high == pytest.approx(4.453 / 12.919)


def test_bank_common_equity_and_capital_payout_match_hand_calculation() -> None:
    result = derive_bank_common_equity(
        beginning_total_equity=360.0,
        beginning_preferred_equity=20.0,
        ending_total_equity=374.598,
        ending_preferred_equity=21.040,
        prior_fiscal_common_net_income=55.681,
        current_ytd_common_net_income=36.901,
        prior_ytd_common_net_income=28.948,
    )

    assert result.ending_common_equity == pytest.approx(353.558)
    assert result.ttm_common_net_income == pytest.approx(63.634)
    assert result.average_common_equity == pytest.approx((340.0 + 353.558) / 2)
    assert result.current_roe == pytest.approx(63.634 / ((340.0 + 353.558) / 2))
    assert capital_constrained_payout_ratio(
        ttm_common_net_income=63.634,
        beginning_required_cet1=200.0,
        ending_required_cet1=210.0,
    ) == pytest.approx(53.634 / 63.634)


def test_sotp_counts_components_and_claims_once() -> None:
    value = sum_of_parts_equity_per_share(
        component_values={"industrial": 1_000.0, "finance": 300.0},
        excess_cash=100.0,
        debt=400.0,
        preferred_equity=50.0,
        noncontrolling_interests=25.0,
        corporate_claims=25.0,
        diluted_shares=100.0,
    )

    assert value == pytest.approx(9.0)
    with pytest.raises(ValueError, match="positive"):
        sum_of_parts_equity_per_share(
            component_values={"industrial": 100.0},
            excess_cash=0.0,
            debt=100.0,
            preferred_equity=0.0,
            noncontrolling_interests=0.0,
            corporate_claims=0.0,
            diluted_shares=100.0,
        )


def test_reit_affo_and_nav_require_explicit_adjustments_and_cap_rate() -> None:
    ffo = 655.721 + 1_274.952 - 73.902
    assert ffo == pytest.approx(1_856.771)
    affo = normalized_affo(
        ffo=ffo,
        straight_line_rent_adjustment=82.172,
        recurring_capital_expenditures=100.0,
        other_recurring_adjustments=0.0,
    )
    assert affo == pytest.approx(1_674.599)
    assert property_nav_per_share(
        normalized_noi=1_000.0,
        cap_rate=0.05,
        other_assets=500.0,
        net_debt=5_000.0,
        preferred_equity=0.0,
        noncontrolling_interests=0.0,
        diluted_shares=500.0,
    ) == pytest.approx(31.0)
    with pytest.raises(ValueError, match="positive NOI"):
        property_nav_per_share(
            normalized_noi=1_000.0,
            cap_rate=0.0,
            other_assets=500.0,
            net_debt=5_000.0,
            preferred_equity=0.0,
            noncontrolling_interests=0.0,
            diluted_shares=500.0,
        )
