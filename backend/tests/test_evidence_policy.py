"""FOD4 contracts for source exhaustion and valuation-policy projection."""

from __future__ import annotations

from app.us_valuation.evidence_policy import (
    EvidenceExhaustionReceipt,
    SourceAttempt,
    project_decision_to_availability,
    resolve_evidence_order,
)
import pytest


def _attempt(source: str, *, value: float | None = None, status: str = "reported", eligible: bool = True, low: float | None = None, high: float | None = None) -> SourceAttempt:
    return SourceAttempt(
        source=source, status=status, value=value, low=low, high=high,
        eligible=eligible, accession="0000123456-26-000001", period_end="2026-06-30",
        reason_codes=(f"{source.upper()}_CHECKED",),
    )


def test_resolver_uses_the_declared_official_evidence_order() -> None:
    decision = resolve_evidence_order(
        {"required_field": "noncurrent_debt", "model": "fcff_dcf", "valuation_date": "2026-08-14"},
        (
            _attempt("sector_range", low=80.0, high=120.0, status="bounded_estimate"),
            _attempt("company_history", low=90.0, high=110.0, status="bounded_estimate"),
            _attempt("annual_carry_forward", value=100.0),
            _attempt("current_aggregate", value=101.0),
            _attempt("regulator_or_sec_supplement", value=102.0),
            _attempt("exact_sec_filing", value=103.0),
        ),
    )

    assert decision.status == "reported"
    assert decision.selected.value == 103.0
    assert decision.selected.source == "exact_sec_filing"
    assert isinstance(decision.exhaustion_receipt, EvidenceExhaustionReceipt)


def test_resolver_carries_annual_only_through_day_365_then_uses_history() -> None:
    decision = resolve_evidence_order(
        {"required_field": "cash", "model": "fcff_dcf", "valuation_date": "2026-08-14"},
        (
            _attempt("annual_carry_forward", value=100.0, status="stale"),
            _attempt("company_history", low=90.0, high=110.0, status="bounded_estimate"),
        ),
    )

    assert decision.status == "bounded_estimate"
    assert decision.selected_range == (90.0, 110.0)
    assert "ANNUAL_CARRY_FORWARD_EXPIRED" in decision.reason_codes


def test_conflicting_current_official_facts_fail_closed_after_exhaustion() -> None:
    decision = resolve_evidence_order(
        {"required_field": "noncurrent_debt", "model": "fcff_dcf", "valuation_date": "2026-08-14"},
        (_attempt("exact_sec_filing", value=100.0), _attempt("exact_sec_filing", value=120.0)),
    )

    assert decision.status == "conflicting"
    assert decision.selected is None
    assert decision.exhaustion_receipt.exhausted is True


def test_nonpromotable_specialist_attempt_is_recorded_but_cannot_supply_a_value() -> None:
    decision = resolve_evidence_order(
        {"required_field": "cet1_capital", "model": "residual_income", "valuation_date": "2026-08-14"},
        (_attempt("regulator_or_sec_supplement", value=120.0, eligible=False, status="reported"),),
    )

    assert decision.status == "unresolved"
    assert decision.selected is None
    assert decision.exhaustion_receipt.exhausted is True
    assert "SPECIALIST_IDENTITY_OR_CONSOLIDATION_UNPROVEN" in decision.reason_codes


def test_finite_source_backed_range_projects_to_bounded_availability_and_reliability_cap() -> None:
    decision = resolve_evidence_order(
        {"required_field": "capex", "model": "fcff_dcf", "valuation_date": "2026-08-14"},
        (_attempt("company_history", low=90.0, high=110.0, status="bounded_estimate"),),
    )
    availability = project_decision_to_availability(decision, fallback_level="company_history", source_attempt=decision.selected)

    assert availability.state == "bounded_unresolved"
    assert availability.uncertainty.low == 90.0
    assert availability.uncertainty.high == 110.0
    assert availability.reliability_cap == "Low"


def test_specialist_evidence_never_authorizes_an_unsuitable_model() -> None:
    decision = resolve_evidence_order(
        {"required_field": "rate_base", "model": "fcff_dcf", "model_suitable": False, "valuation_date": "2026-08-14"},
        (_attempt("regulator_or_sec_supplement", value=500.0),),
    )

    assert decision.status == "unresolved"
    assert decision.selected is None
    assert "UNSUITABLE_MODEL" in decision.reason_codes


def test_annual_point_projection_preserves_carried_freshness_and_age() -> None:
    annual = SourceAttempt(
        source="annual_carry_forward", status="reported", value=100.0,
        low=None, high=None, eligible=True,
        accession="0000123456-26-000001", period_end="2025-12-31",
        reason_codes=("ANNUAL_REPORTED",), source_kind="companyfacts",
        source_age_days=226,
    )
    decision = resolve_evidence_order(
        {"required_field": "cash", "model": "fcff_dcf", "valuation_date": "2026-08-14"},
        (annual,),
    )
    projected = project_decision_to_availability(
        decision, fallback_level="annual_carried_forward", source_attempt=annual
    )

    assert projected.availability.freshness == "carried_forward"
    assert projected.availability.source_age_days == 226


def test_only_source_verified_sector_range_projects_as_bounded_low() -> None:
    sector = SourceAttempt(
        source="sector_range", status="bounded_estimate", value=None,
        low=80.0, high=120.0, eligible=True,
        accession="sector-verified-2026", period_end="2026-08-14",
        reason_codes=("SOURCE_VERIFIED_SECTOR_RANGE",), source_kind="sector_range",
    )
    decision = resolve_evidence_order(
        {"required_field": "capex", "model": "fcff_dcf", "valuation_date": "2026-08-14"},
        (sector,),
    )
    projected = project_decision_to_availability(
        decision, fallback_level="sector_estimate", source_attempt=sector
    )

    assert projected.state == "bounded_unresolved"
    assert projected.reliability_cap == "Low"
    assert projected.availability.source_kind == "sector_range"


def test_filing_table_requires_cutoff_and_immutable_package_lineage() -> None:
    with pytest.raises(ValueError, match="cutoff"):
        SourceAttempt(
            source="filing_table", status="reported", value=10.0,
            low=None, high=None, eligible=True,
            accession="0000123456-26-000001", period_end="2026-06-30",
            reason_codes=("TABLE",), source_kind="filing_table",
            source_url="https://www.sec.gov/example", unit="USD",
            entity_identifier="0000123456", consolidation_scope="consolidated_parent",
            candidate_id="table:1", package_sha256="a" * 64,
        )

    with pytest.raises(ValueError, match="package hash"):
        SourceAttempt(
            source="filing_table", status="reported", value=10.0,
            low=None, high=None, eligible=True,
            accession="0000123456-26-000001", period_end="2026-06-30",
            reason_codes=("TABLE",), source_kind="filing_table", filed_date="2026-08-01",
            source_url="https://www.sec.gov/example", unit="USD",
            entity_identifier="0000123456", consolidation_scope="consolidated_parent",
            candidate_id="table:1",
        )
