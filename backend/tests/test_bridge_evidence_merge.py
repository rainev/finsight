"""Precedence and conflict tests for production bridge evidence."""

from dataclasses import replace

import pytest

from app.us_valuation.bridge_evidence_merge import merge_bridge_evidence
from app.us_valuation.field_availability import FieldAvailability


def _record(
    *,
    value=None,
    state="unresolved",
    source_kind=None,
    freshness="unknown",
    fallback_level="current_reported",
    authority="production",
    accession=None,
):
    return FieldAvailability(
        field="finance_lease_total",
        value=value,
        state=state,
        reason_code="TEST",
        period_end="2026-04-30",
        source_accession=accession,
        source_kind=source_kind,
        evidence_class="reported" if source_kind else None,
        freshness=freshness,
        fallback_level=fallback_level,
        authority=authority,
    )


def _structural(value=664_000_000.0):
    return _record(
        value=value,
        state="reported",
        source_kind="structural_xbrl",
        freshness="current",
        fallback_level="current_structural",
        accession="0001108524-26-000127",
    )


def test_structural_replaces_unresolved_but_not_equal_companyfact() -> None:
    replaced = merge_bridge_evidence(
        {"finance_lease_total": _record()},
        (_structural(),),
    )
    assert replaced.availability["finance_lease_total"] == _structural()
    assert (
        replaced.diagnostics[0]["decision"]
        == "structural_replaced_unusable_detail"
    )

    companyfact = _record(
        value=664_000_000.0,
        state="reported",
        source_kind="companyfacts",
        freshness="current",
        accession="0001108524-26-000127",
    )
    corroborated = merge_bridge_evidence(
        {"finance_lease_total": companyfact},
        (_structural(),),
    )
    assert corroborated.availability["finance_lease_total"] == companyfact
    assert "corroboration" in corroborated.diagnostics[0]["decision"]


def test_unequal_current_points_fail_closed_as_conflict() -> None:
    companyfact = _record(
        value=600_000_000.0,
        state="reported",
        source_kind="companyfacts",
        freshness="current",
        accession="0001108524-26-000127",
    )
    result = merge_bridge_evidence(
        {"finance_lease_total": companyfact},
        (_structural(),),
    )

    conflict = result.availability["finance_lease_total"]
    assert conflict.state == "conflict"
    assert conflict.value is None
    assert result.diagnostics[0]["decision"] == "conflict"


def test_shadow_or_ungoverned_candidate_cannot_enter_production() -> None:
    with pytest.raises(ValueError, match="governed production"):
        merge_bridge_evidence(
            {"finance_lease_total": _record()},
            (replace(_structural(), authority="shadow"),),
        )


def test_external_candidate_must_match_normalized_period() -> None:
    with pytest.raises(ValueError, match="period"):
        merge_bridge_evidence(
            {"finance_lease_total": _record()},
            (replace(_structural(), period_end="2026-03-31"),),
        )


def test_governed_companyfacts_and_filing_table_candidates_are_consumable() -> None:
    unresolved = {"finance_lease_total": _record()}
    companyfacts = _record(
        value=664_000_000.0,
        state="reported",
        source_kind="companyfacts",
        freshness="current",
        accession="0001108524-26-000127",
    )
    assert merge_bridge_evidence(
        unresolved, (companyfacts,)
    ).availability["finance_lease_total"] == companyfacts

    filing_table = replace(companyfacts, source_kind="filing_table")
    assert merge_bridge_evidence(
        unresolved, (filing_table,)
    ).availability["finance_lease_total"] == filing_table


def test_cutoff_limited_annual_carry_forward_can_replace_unresolved_current_field() -> None:
    annual = FieldAvailability(
        field="finance_lease_total",
        value=664_000_000.0,
        state="reported",
        reason_code="ANNUAL_COMPANY_FACT_CARRIED_FORWARD",
        period_end="2025-12-31",
        source_accession="0001108524-26-000040",
        source_kind="companyfacts",
        evidence_class="reported",
        freshness="carried_forward",
        fallback_level="annual_carried_forward",
        source_age_days=226,
        authority="production",
    )
    result = merge_bridge_evidence(
        {"finance_lease_total": _record()},
        (annual,),
    )
    assert result.availability["finance_lease_total"] == annual


def test_newer_controlling_filing_table_replaces_older_companyfacts_period() -> None:
    older = _record(
        value=600_000_000.0,
        state="reported",
        source_kind="companyfacts",
        freshness="current",
        accession="0001108524-26-000090",
    )
    newer = replace(
        older,
        value=664_000_000.0,
        source_kind="filing_table",
        source_accession="0001108524-26-000127",
        period_end="2026-06-30",
    )
    result = merge_bridge_evidence(
        {"finance_lease_total": older},
        (newer,),
    )
    assert result.availability["finance_lease_total"] == newer
    assert result.diagnostics[0]["decision"] == (
        "newer_official_period_replaced_stale_current"
    )
