"""Exact, accession-bound promotion of reviewed Batch 01 structural evidence."""

from __future__ import annotations

from datetime import date
from importlib.resources import files
import json
import math
from typing import Any, Mapping

from .field_availability import FieldAvailability
from .sec_client import normalize_cik
from .structural_xbrl import (
    ResolutionDecision,
    ResolutionEvidence,
    StructuralFact,
)


POLICY_VERSION = "BATCH-01-STRUCTURAL-PROMOTION-2.0"


class StructuralPromotionError(ValueError):
    """The structural decision does not match an exact reviewed fingerprint."""


def _load_policy() -> dict[str, Any]:
    path = files(__package__).joinpath(
        "config/batch_01_structural_promotions.json"
    )
    policy = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or policy.get("schema_version") != POLICY_VERSION:
        raise StructuralPromotionError("structural promotion policy version is invalid")
    promotions = policy.get("promotions")
    if not isinstance(promotions, list):
        raise StructuralPromotionError("structural promotion fingerprints are invalid")
    return policy


def resolution_decision_from_dict(value: Mapping[str, Any]) -> ResolutionDecision:
    """Restore one validated decision from a private structural report."""

    if not isinstance(value, Mapping):
        raise StructuralPromotionError("structural decision must be an object")
    raw_evidence = value.get("evidence")
    evidence = None
    if raw_evidence is not None:
        if not isinstance(raw_evidence, Mapping):
            raise StructuralPromotionError("structural evidence must be an object")
        fact = StructuralFact.from_dict(raw_evidence)
        evidence = ResolutionEvidence.from_fact(
            fact,
            mapping_version=raw_evidence["mapping_version"],
            confidence=raw_evidence["confidence"],
            reason_codes=tuple(raw_evidence["reason_codes"]),
        )
    try:
        return ResolutionDecision(
            status=value["status"],
            normalized_concept=value["normalized_concept"],
            source_concept=value.get("source_concept"),
            value=value.get("value"),
            unit=value.get("unit"),
            period=value["period"],
            source_accession=value["source_accession"],
            confidence=value["confidence"],
            mapping_method=value["mapping_method"],
            reason_codes=tuple(value.get("reason_codes", ())),
            form=value["form"],
            evidence=evidence,
            mapping_version=value["mapping_version"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StructuralPromotionError(
            f"structural decision is invalid: {error}"
        ) from error


def _fingerprint(
    decision: ResolutionDecision,
    *,
    ticker: str,
    cik: str,
    filing_date: str,
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "cik": normalize_cik(cik),
        "field": decision.normalized_concept,
        "value": decision.value,
        "unit": decision.unit,
        "period": decision.period,
        "accession": decision.source_accession,
        "form": decision.form,
        "filing_date": filing_date,
        "source_concept": decision.source_concept,
        "mapping_method": decision.mapping_method,
        "confidence": decision.confidence,
        "reason_codes": list(decision.reason_codes),
    }


def promote_structural_decision(
    decision: ResolutionDecision,
    *,
    ticker: str,
    cik: str,
    filing_date: str,
    valuation_date: str,
) -> FieldAvailability:
    """Promote only an exact reviewed accepted decision to production authority."""

    if not isinstance(decision, ResolutionDecision):
        raise StructuralPromotionError("decision must be a ResolutionDecision")
    if decision.status != "accepted" or decision.evidence is None:
        raise StructuralPromotionError("only accepted decisions can be promoted")
    try:
        decision.evidence.validate_complete()
        filed = date.fromisoformat(filing_date)
        cutoff = date.fromisoformat(valuation_date)
    except (TypeError, ValueError) as error:
        raise StructuralPromotionError(f"promotion provenance is invalid: {error}") from error
    if filed > cutoff:
        raise StructuralPromotionError("future-filed structural evidence cannot be promoted")
    if (
        isinstance(decision.value, bool)
        or not isinstance(decision.value, (int, float))
        or not math.isfinite(float(decision.value))
        or decision.value < 0
        or decision.unit != "USD"
    ):
        raise StructuralPromotionError(
            "promoted structural evidence must be a nonnegative finite USD value"
        )
    policy = _load_policy()
    if decision.mapping_version != policy.get("mapping_version"):
        raise StructuralPromotionError("structural mapping version is not approved")
    fingerprint = _fingerprint(
        decision,
        ticker=ticker,
        cik=cik,
        filing_date=filing_date,
    )
    if fingerprint not in policy["promotions"]:
        raise StructuralPromotionError(
            "structural decision does not match an exact reviewed fingerprint"
        )
    aggregate_fields: tuple[str, ...] = ()
    coverage_basis = None
    coverage_source_facts: tuple[str, ...] = ()
    economic_scope = None
    if decision.normalized_concept == "finance_lease_total":
        aggregate_fields = ("finance_lease_current", "finance_lease_noncurrent")
        coverage_basis = "direct_issuer_total"
        coverage_source_facts = (
            "|".join(
                (
                    decision.source_accession,
                    decision.period,
                    decision.source_concept,
                    decision.evidence.fact.context_id,
                )
            ),
        )
        economic_scope = "finance_lease_current_and_noncurrent"
    return FieldAvailability(
        field=decision.normalized_concept,
        value=float(decision.value),
        state="reported",
        reason_code="BATCH_01_EXACT_STRUCTURAL_PROMOTION",
        period_end=decision.period,
        source_accession=decision.source_accession,
        source_kind="structural_xbrl",
        evidence_class=decision.mapping_method,
        freshness="current",
        fallback_level="current_structural",
        covered_fields=aggregate_fields,
        coverage_basis=coverage_basis,
        coverage_source_facts=coverage_source_facts,
        economic_scope=economic_scope,
        authority="production",
    )
