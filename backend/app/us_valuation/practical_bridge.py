"""Source-derived bridge ranges for the practical bounded-uncertainty policy."""

from __future__ import annotations

from typing import Sequence

from .field_availability import FieldAvailability, UncertaintyRange


def bounded_claim(
    *,
    field: str,
    upper_bound: float,
    source_accession: str,
    period_end: str,
    source_concept: str,
    context_id: str,
    basis: str,
) -> FieldAvailability:
    """Bound one unresolved claim from zero to a same-filing reported maximum."""

    if upper_bound <= 0:
        raise ValueError("claim upper bound must be positive")
    return FieldAvailability(
        field=field,
        value=None,
        state="bounded_unresolved",
        reason_code="REPORTED_AGGREGATE_REPLACEMENT",
        period_end=period_end,
        source_accession=source_accession,
        source_kind="practical_policy",
        evidence_class="same_filing_claim_upper_bound",
        freshness="current",
        fallback_level="company_history",
        uncertainty=UncertaintyRange(
            low=0.0,
            high=float(upper_bound),
            basis=basis,
            source_accessions=(source_accession,),
        ),
        authority="production",
    )


def reported_aggregate(
    *,
    field: str,
    low: float,
    high: float,
    source_accession: str,
    period_end: str,
    source_concept: str,
    context_id: str,
    covered_fields: Sequence[str],
    economic_scope: str,
    basis: str,
) -> FieldAvailability:
    """Create an exact or bounded current aggregate with explicit coverage proof."""

    if low < 0 or high < low:
        raise ValueError("aggregate range must satisfy 0 <= low <= high")
    coverage = tuple(covered_fields)
    if not coverage:
        raise ValueError("aggregate covered_fields must not be empty")
    common = {
        "field": field,
        "reason_code": "REPORTED_AGGREGATE_REPLACEMENT",
        "period_end": period_end,
        "source_accession": source_accession,
        "source_kind": "practical_policy",
        "evidence_class": "same_filing_reported_aggregate",
        "freshness": "current",
        "fallback_level": "reported_aggregate",
        "covered_fields": coverage,
        "coverage_basis": "direct_issuer_total",
        "coverage_source_facts": (
            f"{source_accession}|{period_end}|{source_concept}|{context_id}",
        ),
        "economic_scope": economic_scope,
        "authority": "production",
    }
    if low == high:
        return FieldAvailability(
            value=float(low),
            state="reported" if low else "explicit_zero",
            **common,
        )
    return FieldAvailability(
        value=None,
        state="bounded_unresolved",
        uncertainty=UncertaintyRange(
            low=float(low),
            high=float(high),
            basis=basis,
            source_accessions=(source_accession,),
        ),
        **common,
    )
