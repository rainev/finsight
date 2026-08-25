"""Fail-closed precedence for externally prepared bridge evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .field_availability import FieldAvailability


_CURRENT_POINT_STATES = frozenset(
    {"reported", "explicit_zero", "evidence_backed_zero", "not_applicable"}
)
_OFFICIAL_CURRENT_SOURCE_KINDS = frozenset(
    {
        "companyfacts",
        "structural_xbrl",
        "filing_table",
        "filing_balance_sheet",
        "filing_debt_note",
        "filing_equity_note",
        "filing_note_explicit_classification",
        "fr_y9c",
        "ferc_form_1",
        "ferc_form_3q",
        "sec_filed_exhibit_99_2",
    }
)


@dataclass(frozen=True)
class BridgeEvidenceMerge:
    availability: dict[str, FieldAvailability]
    diagnostics: tuple[dict[str, object], ...]


def _validated(record: FieldAvailability) -> FieldAvailability:
    if not isinstance(record, FieldAvailability):
        raise ValueError("bridge evidence must contain FieldAvailability records")
    return FieldAvailability.from_dict(record.as_dict())


def _conflict(
    field: str,
    existing: FieldAvailability,
    candidate: FieldAvailability,
) -> FieldAvailability:
    return FieldAvailability(
        field=field,
        value=None,
        state="conflict",
        reason_code="BRIDGE_EVIDENCE_CONFLICT",
        period_end=max(existing.period_end, candidate.period_end),
        source_accession=None,
        source_kind="evidence_conflict",
        evidence_class="conflicting_current_points",
        freshness="unknown",
        authority="production",
    )


def _usable_current_point(record: FieldAvailability) -> bool:
    if (
        record.authority != "production"
        or record.freshness != "current"
        or record.state not in _CURRENT_POINT_STATES
        or record.source_accession is None
        or record.source_kind is None
        or record.evidence_class is None
    ):
        return False
    if record.covered_fields and (
        record.coverage_basis is None
        or not record.coverage_source_facts
        or record.economic_scope is None
    ):
        return False
    return True


def _external_candidate_is_usable(candidate: FieldAvailability) -> bool:
    if candidate.authority != "production":
        return False
    if candidate.fallback_level == "annual_carried_forward":
        return (
            candidate.source_kind == "companyfacts"
            and candidate.freshness == "carried_forward"
            and candidate.source_age_days is not None
            and candidate.source_age_days <= 365
            and candidate.state in {"reported", "bounded_unresolved"}
        )
    if candidate.freshness != "current":
        return False
    if candidate.source_kind in _OFFICIAL_CURRENT_SOURCE_KINDS and (
        candidate.state in _CURRENT_POINT_STATES
        and candidate.fallback_level in {
            "current_reported", "current_structural", "reported_aggregate"
        }
    ):
        return True
    if candidate.state == "bounded_unresolved":
        return (
            candidate.uncertainty is not None
            and (
                (
                    candidate.source_kind == "practical_policy"
                    and candidate.fallback_level in {"reported_aggregate", "company_history"}
                )
                or (
                    candidate.source_kind in {"companyfacts", "company_history"}
                    and candidate.fallback_level == "company_history"
                )
                or (
                    candidate.source_kind == "sector_range"
                    and candidate.fallback_level == "sector_estimate"
                )
            )
        )
    return (
        candidate.source_kind == "practical_policy"
        and candidate.state in _CURRENT_POINT_STATES
        and candidate.fallback_level == "reported_aggregate"
    )


def merge_bridge_evidence(
    primary: Mapping[str, FieldAvailability],
    candidates: Iterable[FieldAvailability],
) -> BridgeEvidenceMerge:
    """Merge current structural candidates without weakening stronger issuer facts."""

    if not isinstance(primary, Mapping):
        raise ValueError("primary availability must be a mapping")
    merged = {field: _validated(record) for field, record in primary.items()}
    primary_periods = {record.period_end for record in merged.values()}
    diagnostics: list[dict[str, object]] = []
    for raw_candidate in candidates:
        candidate = _validated(raw_candidate)
        if primary_periods and candidate.period_end not in primary_periods:
            if candidate.fallback_level in {
                "annual_carried_forward", "company_history", "sector_estimate"
            }:
                pass
            elif candidate.period_end < max(primary_periods):
                raise ValueError("external bridge evidence period predates normalization")
        if not _external_candidate_is_usable(candidate):
            raise ValueError(
                "external bridge evidence must be current governed production evidence"
            )
        field = candidate.field
        existing = merged.get(field)
        if existing is None:
            merged[field] = candidate
            diagnostics.append(
                {
                    "field": field,
                    "decision": "structural_added",
                    "reason": candidate.reason_code,
                }
            )
            continue
        if _usable_current_point(existing):
            if candidate.period_end > existing.period_end:
                merged[field] = candidate
                diagnostics.append(
                    {
                        "field": field,
                        "decision": "newer_official_period_replaced_stale_current",
                        "existing_period_end": existing.period_end,
                        "candidate_period_end": candidate.period_end,
                        "candidate_accession": candidate.source_accession,
                    }
                )
                continue
            candidate_low = (
                candidate.uncertainty.low
                if candidate.uncertainty is not None
                else candidate.value
            )
            candidate_high = (
                candidate.uncertainty.high
                if candidate.uncertainty is not None
                else candidate.value
            )
            if (
                candidate_low is not None
                and candidate_high is not None
                and existing.value is not None
                and candidate_low <= existing.value <= candidate_high
            ):
                diagnostics.append(
                    {
                        "field": field,
                        "decision": "companyfacts_retained_external_corroboration",
                        "existing_accession": existing.source_accession,
                        "candidate_accession": candidate.source_accession,
                    }
                )
            else:
                merged[field] = _conflict(field, existing, candidate)
                diagnostics.append(
                    {
                        "field": field,
                        "decision": "conflict",
                        "existing_value": existing.value,
                        "candidate_value": candidate.value,
                        "existing_accession": existing.source_accession,
                        "candidate_accession": candidate.source_accession,
                    }
                )
            continue
        merged[field] = candidate
        diagnostics.append(
            {
                "field": field,
                "decision": "structural_replaced_unusable_detail",
                "displaced_state": existing.state,
                "displaced_reason": existing.reason_code,
                "candidate_accession": candidate.source_accession,
            }
        )
    return BridgeEvidenceMerge(availability=merged, diagnostics=tuple(diagnostics))
