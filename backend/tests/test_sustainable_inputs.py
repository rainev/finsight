import json

import pytest

from app.us_valuation.sustainable_inputs import (
    BoundedAdjustment,
    SourceEvidence,
    TimedCommitment,
    TimedPayment,
    assert_non_overlapping_commitments,
    check_timed_commitment_overlap,
    evaluate_timed_payment_pv,
    normalize_reported_value,
    resolve_total_capex,
)


def _source(value: float, field: str = "cash_flow") -> SourceEvidence:
    return SourceEvidence(
        source_id="sec:0000000001-26-000001",
        cik="0000000001",
        field=field,
        unit="USD",
        reported_value=value,
        period_end="2025-12-31",
        filing_date="2026-02-15",
    )


def test_normalization_preserves_reported_value_and_reconciles_bounded_adjustment() -> None:
    adjustment = BoundedAdjustment(
        name="one_time_settlement",
        amount=20.0,
        lower_bound=0.0,
        upper_bound=25.0,
        source=_source(20.0, "settlement_cash_paid"),
        rationale="Remove a source-reported non-recurring cash payment.",
    )

    result = normalize_reported_value(100.0, (adjustment,), field="cash_flow", frozen_cutoff="2026-08-14")

    assert result.reported_value == 100.0
    assert result.adjustment_total == 20.0
    assert result.normalized_value == 120.0
    assert result.reported_preserved is True
    assert result.as_dict()["adjustments"][0]["source"]["source_id"].startswith("sec:")


def test_adjustment_outside_bound_fails_closed() -> None:
    with pytest.raises(ValueError, match="above its upper bound"):
        BoundedAdjustment(
            name="unsupported_adjustment",
            amount=26.0,
            upper_bound=25.0,
            source=_source(26.0),
        )


def test_total_capex_is_default_and_components_are_diagnostic_not_added_again() -> None:
    result = resolve_total_capex(
        100.0,
        maintenance_capex=70.0,
        growth_capex=50.0,
        total_source=_source(100.0, "total_capex"),
        maintenance_source=_source(70.0, "maintenance_capex"),
        growth_source=_source(50.0, "growth_capex"),
        frozen_cutoff="2026-08-14",
    )

    assert result.effective_total_capex == 100.0
    assert result.basis == "reported_total_capex"
    assert result.component_difference == 20.0
    assert result.components_reconciled is False

    with pytest.raises(ValueError, match="reported total capex does not reconcile"):
        resolve_total_capex(
            100.0,
            total_source=_source(99.0, "total_capex"),
            frozen_cutoff="2026-08-14",
        )


def test_missing_total_capex_never_turns_one_missing_component_into_zero() -> None:
    with pytest.raises(ValueError, match="both maintenance and growth capex"):
        resolve_total_capex(
            None,
            maintenance_capex=70.0,
            maintenance_source=_source(70.0, "maintenance_capex"),
            frozen_cutoff="2026-08-14",
        )

    fallback = resolve_total_capex(
        None,
        maintenance_capex=70.0,
        growth_capex=30.0,
        maintenance_source=_source(70.0, "maintenance_capex"),
        growth_source=_source(30.0, "growth_capex"),
        frozen_cutoff="2026-08-14",
    )
    assert fallback.effective_total_capex == 100.0
    assert fallback.basis == "reported_components"


def test_timed_commitments_only_overlap_when_coverage_scope_overlaps() -> None:
    rows = (
        TimedCommitment("power", 100.0, 2027, _source(100.0), 2028, coverage_key="power"),
        TimedCommitment("cloud", 200.0, 2028, _source(200.0), 2029, coverage_key="cloud"),
        TimedCommitment("power_renewal", 50.0, 2028, _source(50.0), 2030, coverage_key="power"),
    )
    result = check_timed_commitment_overlap(rows, frozen_cutoff="2026-08-14")

    assert result.status == "overlap_found"
    assert result.overlaps[0].left_id == "power"
    assert result.overlaps[0].overlap_start_year == 2028
    assert result.total_by_year[2028] == pytest.approx(100.0 / 2 + 200.0 / 2 + 50.0 / 3)


def test_non_overlapping_schedule_is_serializable_and_assertion_returns_it() -> None:
    rows = (
        TimedCommitment("power", 100.0, 2027, _source(100.0), 2027, coverage_key="power"),
        TimedCommitment("power_renewal", 50.0, 2028, _source(50.0), 2028, coverage_key="power"),
    )
    result = assert_non_overlapping_commitments(rows, frozen_cutoff="2026-08-14")

    assert result.is_non_overlapping
    json.dumps(result.as_dict())


def test_source_amount_and_frozen_cutoff_are_load_bearing() -> None:
    with pytest.raises(ValueError, match="reconcile"):
        BoundedAdjustment("bad_source", 20.0, _source(21.0))
    with pytest.raises(ValueError, match="after the frozen cutoff"):
        normalize_reported_value(
            100.0,
            (BoundedAdjustment("late", 20.0, _source(20.0)),),
            frozen_cutoff="2026-01-01",
        )


def test_timed_payment_pv_is_finite_dated_and_rejects_overlap() -> None:
    payments = (
        TimedPayment("p1", 2027, 100.0, "lease", _source(100.0, "lease_payment")),
        TimedPayment("p2", 2028, 100.0, "lease", _source(100.0, "lease_payment")),
    )
    result = evaluate_timed_payment_pv(
        payments,
        valuation_year=2026,
        discount_rate=0.10,
        frozen_cutoff="2026-08-14",
    )
    assert result.present_value == pytest.approx(100.0 / 1.1 + 100.0 / 1.1**2)
    assert result.overlap_check.status == "pass"
    json.dumps(result.as_dict())

    with pytest.raises(ValueError, match="overlapping coverage"):
        evaluate_timed_payment_pv(
            (
                TimedPayment("p1", 2027, 100.0, "lease", _source(100.0, "lease_payment")),
                TimedPayment("p1b", 2027, 25.0, "lease", _source(25.0, "lease_payment")),
            ),
            valuation_year=2026,
            discount_rate=0.10,
            frozen_cutoff="2026-08-14",
        )
