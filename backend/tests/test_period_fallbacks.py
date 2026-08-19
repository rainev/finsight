from __future__ import annotations

import pytest

from app.us_valuation.period_fallbacks import (
    annual_carried_forward_decision,
    company_history_decision,
    sector_estimate_decision,
)


def test_annual_range_uses_ten_percent_floor() -> None:
    result = annual_carried_forward_decision(
        field="noncurrent_debt",
        base=100.0,
        annual_values=[98.0, 100.0],
        source_age_days=365,
        source_accessions=["A", "B"],
    )
    assert (result.low, result.base, result.high) == pytest.approx((90, 100, 110))
    assert result.fallback_level == "annual_carried_forward"


def test_annual_range_uses_largest_recent_change() -> None:
    result = annual_carried_forward_decision(
        field="cash",
        base=150.0,
        annual_values=[100.0, 120.0, 150.0],
        source_age_days=180,
        source_accessions=["A", "B", "C"],
    )
    assert (result.low, result.high) == pytest.approx((112.5, 187.5))


def test_unquantified_major_change_cannot_use_annual_range() -> None:
    with pytest.raises(ValueError, match="unquantified"):
        annual_carried_forward_decision(
            field="noncurrent_debt",
            base=100.0,
            annual_values=[90.0, 100.0],
            source_age_days=100,
            source_accessions=["A", "B"],
            major_change_flags=["debt_refinancing"],
        )


def test_quantified_major_change_updates_base_and_widens_range() -> None:
    result = annual_carried_forward_decision(
        field="noncurrent_debt",
        base=100.0,
        annual_values=[90.0, 100.0],
        source_age_days=100,
        source_accessions=["A", "B"],
        major_change_flags=["debt_issuance"],
        quantified_change=50.0,
    )
    assert result.base == 150.0
    assert result.low <= 90.0
    assert result.high >= 150.0


def test_company_history_requires_two_observations_and_scales_by_assets() -> None:
    with pytest.raises(ValueError, match="at least two"):
        company_history_decision(
            field="preferred_equity",
            observations=[(10.0, 100.0, "A")],
            current_total_assets=200.0,
            source_age_days=400,
        )
    result = company_history_decision(
        field="preferred_equity",
        observations=[(10.0, 100.0, "A"), (30.0, 200.0, "B")],
        current_total_assets=400.0,
        source_age_days=400,
    )
    assert result.low == pytest.approx(40.0)
    assert result.base == pytest.approx(50.0)
    assert result.high == pytest.approx(60.0)
    assert result.reliability_cap == "Medium"


def test_sector_estimate_requires_five_peers_and_is_low_reliability() -> None:
    with pytest.raises(ValueError, match="five"):
        sector_estimate_decision(
            field="noncontrolling_interests",
            peer_ratios=[(0.01, "A")] * 4,
            current_total_assets=1_000.0,
        )
    result = sector_estimate_decision(
        field="noncontrolling_interests",
        peer_ratios=[
            (0.01, "A"),
            (0.02, "B"),
            (0.03, "C"),
            (0.04, "D"),
            (0.05, "E"),
        ],
        current_total_assets=1_000.0,
    )
    assert (result.low, result.base, result.high) == pytest.approx((20, 30, 40))
    assert result.reliability_cap == "Low"
