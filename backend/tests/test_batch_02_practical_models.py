from dataclasses import replace

import pytest

from app.us_valuation.practical_models import (
    EnterpriseCashFlowState,
    enterprise_cash_flow_dcf,
    practical_cash_fcff_range,
)


BASE = EnterpriseCashFlowState(
    cash_fcff=10_000.0,
    initial_growth=0.04,
    terminal_growth=0.02,
    wacc=0.09,
    cash_and_investments=2_000.0,
    interest_bearing_debt=3_000.0,
    preferred_equity=100.0,
    noncontrolling_interests=200.0,
    diluted_shares=1_000.0,
)


def test_cash_fcff_range_is_ordered_and_directionally_economic() -> None:
    bear = replace(
        BASE,
        cash_fcff=8_000.0,
        initial_growth=0.02,
        terminal_growth=0.015,
        wacc=0.10,
        interest_bearing_debt=3_500.0,
        diluted_shares=1_050.0,
    )
    bull = replace(
        BASE,
        cash_fcff=12_000.0,
        initial_growth=0.06,
        terminal_growth=0.025,
        wacc=0.08,
        interest_bearing_debt=2_500.0,
        diluted_shares=980.0,
    )

    value_range, results = practical_cash_fcff_range(
        {"bear": bear, "base": BASE, "bull": bull}
    )

    assert value_range.low < value_range.base < value_range.high
    assert results["base"]["detail"]["interest_bearing_debt"] == 3_000.0
    assert results["base"]["detail"]["terminal_value_share"] < 1


def test_cash_fcff_value_falls_with_capex_proxy_wacc_claims_and_shares() -> None:
    base = enterprise_cash_flow_dcf(BASE)["intrinsic_value_per_share"]

    assert (
        enterprise_cash_flow_dcf(replace(BASE, cash_fcff=9_000.0))[
            "intrinsic_value_per_share"
        ]
        < base
    )
    assert (
        enterprise_cash_flow_dcf(replace(BASE, wacc=0.10))[
            "intrinsic_value_per_share"
        ]
        < base
    )
    assert (
        enterprise_cash_flow_dcf(replace(BASE, interest_bearing_debt=4_000.0))[
            "intrinsic_value_per_share"
        ]
        < base
    )
    assert (
        enterprise_cash_flow_dcf(replace(BASE, diluted_shares=1_100.0))[
            "intrinsic_value_per_share"
        ]
        < base
    )


def test_cash_fcff_rejects_missing_or_nonpositive_value_instead_of_using_zero() -> None:
    with pytest.raises(ValueError, match="cash_fcff"):
        enterprise_cash_flow_dcf(replace(BASE, cash_fcff=0.0))
    with pytest.raises(ValueError, match="nonpositive equity"):
        enterprise_cash_flow_dcf(
            replace(BASE, interest_bearing_debt=1_000_000.0)
        )


def test_cash_fcff_can_retain_an_explicit_private_nonpositive_trace() -> None:
    result = enterprise_cash_flow_dcf(
        replace(BASE, interest_bearing_debt=1_000_000.0),
        allow_nonpositive_equity_trace=True,
    )
    assert result["intrinsic_value_per_share"] < 0
    assert result["publication_state"] == "withheld"
    assert "limited-liability-floor trace" in result["warnings"][-1]
