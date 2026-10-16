"""Bound current NCI from a consolidated-versus-parent equity difference.

This module is intentionally not wired into refresh bindings yet.  It proves
only the outside-equity difference and preserves reporting precision as an
uncertainty range; it does not prove preferred equity or classify investments.
"""

from __future__ import annotations

from math import isfinite
from numbers import Real
from typing import Any, Mapping

from .field_availability import FieldAvailability, UncertaintyRange


SCHEMA_VERSION = "FINSIGHT-PARENT-NCI-EQUITY-DIFFERENCE-1"
_COMBINED_QNAME = "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
_PARENT_QNAME = "us-gaap:StockholdersEquity"
_CLAIM_MARKERS = (
    "noncontrollinginterest",
    "minorityinterest",
    "temporaryequity",
    "redeemable",
    "outsideequity",
    "claim",
)


class ParentNciDifferenceReviewRequired(ValueError):
    """Raised when the current package cannot support the bounded proof."""


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value)):
        raise ParentNciDifferenceReviewRequired(f"{label} is not finite")
    return float(value)


def _metadata(packet: Mapping[str, Any]) -> dict[str, Any]:
    raw = packet.get("filing_metadata", ())
    metadata = dict(raw) if isinstance(raw, (dict, list, tuple)) else {}
    if metadata.get("manifest_version") != "FINSIGHT-XBRL-PACKAGE-1" or not metadata.get("package_generation"):
        raise ParentNciDifferenceReviewRequired("complete structural filing package receipt is required")
    return metadata


def _current_rows(packet: Mapping[str, Any], *, cik: str, accession: str, period_end: str) -> list[Mapping[str, Any]]:
    expected_cik = str(cik).zfill(10)
    facts = packet.get("facts")
    if not isinstance(facts, list):
        raise ParentNciDifferenceReviewRequired("structural equity facts are missing")
    rows = []
    for row in facts:
        if not isinstance(row, Mapping):
            continue
        if (
            row.get("period_end") == period_end
            and row.get("period_start") is None
            and row.get("unit") == "USD"
            and row.get("source_accession") == accession
            and row.get("entity_scheme") == "http://www.sec.gov/CIK"
            and str(row.get("entity_identifier", "")).zfill(10) == expected_cik
        ):
            rows.append(row)
    if not rows:
        raise ParentNciDifferenceReviewRequired("current structural equity facts are missing")
    return rows


def _unique_fact(rows: list[Mapping[str, Any]], qname: str) -> Mapping[str, Any]:
    typed = [row for row in rows if row.get("qname") == qname and row.get("dimensions")]
    if typed and not any(not row.get("dimensions") for row in rows if row.get("qname") == qname):
        raise ParentNciDifferenceReviewRequired(f"typed-dimension equity fact is not an undimensioned total: {qname}")
    matches = [row for row in rows if row.get("qname") == qname and not row.get("dimensions")]
    if not matches:
        raise ParentNciDifferenceReviewRequired(f"required equity fact is missing: {qname}")
    identities = {
        (
            _number(row.get("value"), qname),
            str(row.get("decimals")),
            row.get("context_id"),
            row.get("source_accession"),
        )
        for row in matches
    }
    if len(identities) != 1:
        raise ParentNciDifferenceReviewRequired(f"conflicting equity facts: {qname}")
    return matches[0]


def _precision_bound(row: Mapping[str, Any]) -> float:
    decimals = row.get("decimals")
    if decimals == "INF":
        return 0.0
    try:
        exponent = int(str(decimals))
    except (TypeError, ValueError) as exc:
        raise ParentNciDifferenceReviewRequired("equity fact precision is missing") from exc
    if exponent < -300 or exponent > 300:
        raise ParentNciDifferenceReviewRequired("equity fact precision exponent is not bounded")
    bound = 0.5 * (10.0 ** (-exponent))
    if not isfinite(bound):
        raise ParentNciDifferenceReviewRequired("equity fact precision interval is not finite")
    return bound


def _claim_conflicts(
    rows: list[Mapping[str, Any]],
    *,
    combined_qname: str,
    parent_qname: str,
) -> list[dict[str, Any]]:
    conflicts = []
    for row in rows:
        qname = str(row.get("qname", ""))
        local = str(row.get("local_name", qname.rsplit(":", 1)[-1])).casefold()
        dimensions = row.get("dimensions") or []
        dimension_text = " ".join(str(item) for pair in dimensions for item in (pair if isinstance(pair, (list, tuple)) else (pair,))).casefold()
        # The consolidated and parent totals are exempt from qname matching,
        # but their typed/explicit members still must be scanned.
        qname_matches = qname not in {combined_qname, parent_qname} and any(marker in local for marker in _CLAIM_MARKERS)
        dimension_matches = any(marker in dimension_text for marker in _CLAIM_MARKERS)
        if not qname_matches and not dimension_matches:
            continue
        value = _number(row.get("value"), "outside-equity claim")
        if value != 0.0:
            conflicts.append({
                "qname": qname,
                "value": value,
                "context_id": row.get("context_id"),
                "dimensions": dimensions,
            })
    return conflicts


def reconcile_parent_nci_difference(
    structural_packet: Mapping[str, Any],
    *,
    cik: str,
    accession: str,
    period_end: str,
    combined_qname: str = _COMBINED_QNAME,
    parent_qname: str = _PARENT_QNAME,
    approved_basepoint: float = 0.0,
) -> tuple[FieldAvailability, dict[str, Any]]:
    """Return a precision-bounded current NCI difference.

    Equal consolidated and parent equity facts produce a zero reported
    difference, but finite XBRL rounding is retained as uncertainty.  The
    helper never classifies preferred equity and rejects nonzero ordinary,
    redeemable, temporary, or unknown claim markers in the same package.
    """
    _metadata(structural_packet)
    rows = _current_rows(structural_packet, cik=cik, accession=accession, period_end=period_end)
    combined = _unique_fact(rows, combined_qname)
    parent = _unique_fact(rows, parent_qname)
    for field in ("unit", "entity_identifier", "entity_scheme", "period_end", "source_accession"):
        if combined.get(field) != parent.get(field):
            raise ParentNciDifferenceReviewRequired(f"equity fact {field} mismatch")
    conflicts = _claim_conflicts(rows, combined_qname=combined_qname, parent_qname=parent_qname)
    if conflicts:
        raise ParentNciDifferenceReviewRequired("nonzero NCI or temporary-equity claim conflicts with parent-only equity")
    combined_value = _number(combined.get("value"), "consolidated equity")
    parent_value = _number(parent.get("value"), "parent equity")
    if combined.get("context_id") != parent.get("context_id"):
        raise ParentNciDifferenceReviewRequired("parent and consolidated equity facts use different contexts")
    reported_difference = combined_value - parent_value
    precision_bound = _precision_bound(combined) + _precision_bound(parent)
    if reported_difference < -precision_bound:
        raise ParentNciDifferenceReviewRequired("consolidated equity is materially below parent equity")
    low = max(0.0, reported_difference - precision_bound)
    high = max(0.0, reported_difference + precision_bound)
    approved_basepoint = _number(approved_basepoint, "approved NCI basepoint")
    if approved_basepoint < low or approved_basepoint > high:
        raise ParentNciDifferenceReviewRequired("approved NCI basepoint lies outside source precision bound")
    exact = precision_bound == 0.0 and reported_difference >= 0.0
    refs = (
        f"{accession}|{period_end}|{combined_qname}|{combined.get('context_id')}",
        f"{accession}|{period_end}|{parent_qname}|{parent.get('context_id')}",
    )
    if exact:
        availability = FieldAvailability(
            field="noncontrolling_interests", value=reported_difference,
            state="evidence_backed_zero" if reported_difference == 0.0 else "reported",
            reason_code="PARENT_CONSOLIDATED_EQUITY_DIFFERENCE",
            period_end=period_end, source_accession=accession,
            source_kind="structural_xbrl", evidence_class="reported_component_reconciliation",
            freshness="current", fallback_level="reported_aggregate",
            covered_fields=("noncontrolling_interests",), coverage_basis="reconciled_disjoint_components",
            coverage_source_facts=refs,
            economic_scope="consolidated equity less parent equity; preferred equity remains separately scoped",
            extraction_complete=True, searched_concepts=(combined_qname, parent_qname, "NCI and temporary-equity claims"),
            authority="production", mapping_version=SCHEMA_VERSION,
        )
    else:
        availability = FieldAvailability(
            field="noncontrolling_interests", value=None, state="bounded_unresolved",
            reason_code="PARENT_CONSOLIDATED_EQUITY_DIFFERENCE_WITH_REPORTING_PRECISION",
            period_end=period_end, source_accession=accession,
            source_kind="practical_policy", evidence_class="reported_component_reconciliation",
            freshness="current", fallback_level="reported_aggregate",
            uncertainty=UncertaintyRange(
                low=low, high=high,
                basis="Consolidated-parent equity difference bounded by both source facts' reported precision.",
                source_accessions=(accession,),
            ),
            covered_fields=("noncontrolling_interests",), coverage_basis="reconciled_disjoint_components",
            coverage_source_facts=refs,
            economic_scope="consolidated equity less parent equity; preferred equity remains separately scoped",
            extraction_complete=True, searched_concepts=(combined_qname, parent_qname, "NCI and temporary-equity claims"),
            authority="production", mapping_version=SCHEMA_VERSION,
        )
    proof = {
        "schema_version": SCHEMA_VERSION,
        "status": "source_bound",
        "cik": str(cik).zfill(10), "accession": accession, "period_end": period_end,
        "reported_difference": reported_difference,
        "precision_bound": precision_bound,
        "uncertainty": {"low": low, "high": high},
        "approved_basepoint": approved_basepoint,
        "approved_basepoint_within_bound": True,
        "approved_basepoint_projection_required": not exact,
        "exact_zero_proven": exact and reported_difference == 0.0,
        "combined_equity": combined_value, "parent_equity": parent_value,
        "conflicting_claims": conflicts,
        "preferred_equity": "not assessed by this helper",
        "source_facts": refs,
    }
    return availability, proof


__all__ = ["SCHEMA_VERSION", "ParentNciDifferenceReviewRequired", "reconcile_parent_nci_difference"]
