"""Non-publishing evaluation of structural XBRL bridge candidates."""

from __future__ import annotations

import math
from typing import Any, Mapping

from .concept_resolver import resolve_concept
from .structural_xbrl import ResolutionRequest, StructuralFiling


SUPPORTED_STRUCTURAL_FIELDS = frozenset(
    {
        "marketable_securities_current",
        "marketable_securities_noncurrent",
        "commercial_paper",
        "current_debt",
        "noncurrent_debt",
        "finance_lease_current",
        "finance_lease_noncurrent",
        "finance_lease_total",
        "preferred_equity",
        "noncontrolling_interests",
    }
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    return value


def _bridge_missing_fields(artifact: Mapping[str, Any]) -> tuple[str, ...]:
    financials = _mapping(artifact.get("financials"))
    balance_sheet = _mapping(financials.get("balance_sheet"))
    missing = balance_sheet.get("bridge_missing_fields")
    if not isinstance(missing, (list, tuple)):
        return ()
    return tuple(field for field in missing if isinstance(field, str) and field)


def _artifact_context(artifact: Mapping[str, Any]) -> tuple[str, str, str]:
    financials = _mapping(artifact.get("financials"))
    ttm = _mapping(financials.get("ttm"))
    controlling_filing = _mapping(ttm.get("controlling_filing"))
    accession = _nonempty_text(
        controlling_filing.get("accession"), "controlling accession"
    )
    period_end = _nonempty_text(ttm.get("period_end"), "controlling period")
    form = _nonempty_text(controlling_filing.get("form"), "controlling form")
    return accession, period_end, form


def shadow_requests_from_artifact(
    artifact: Mapping[str, Any],
) -> tuple[ResolutionRequest, ...]:
    """Build structural bridge resolution requests from explicit bridge gaps only."""

    missing = _bridge_missing_fields(artifact)
    requested_fields = tuple(
        field for field in missing if field in SUPPORTED_STRUCTURAL_FIELDS
    )
    if not requested_fields:
        return ()
    accession, period_end, form = _artifact_context(artifact)
    return tuple(
        ResolutionRequest(
            normalized_concept=field,
            period_end=period_end,
            source_accession=accession,
            unit="USD",
            statement_role="balance_sheet",
            form=form,
        )
        for field in requested_fields
    )


def _ticker(artifact: Mapping[str, Any]) -> str | None:
    value = artifact.get("ticker")
    if isinstance(value, str) and value:
        return value
    issuer_ticker = _mapping(artifact.get("issuer")).get("ticker")
    return issuer_ticker if isinstance(issuer_ticker, str) and issuer_ticker else None


def _artifact_metadata(artifact: Mapping[str, Any]) -> dict[str, Any]:
    financials = _mapping(artifact.get("financials"))
    balance_sheet = _mapping(financials.get("balance_sheet"))
    ttm = _mapping(financials.get("ttm"))
    controlling_filing = _mapping(ttm.get("controlling_filing"))
    field_states = _mapping(balance_sheet.get("field_states"))
    missing = _bridge_missing_fields(artifact)
    return {
        "ticker": _ticker(artifact),
        "cik": _mapping(artifact.get("issuer")).get("cik"),
        "valuation_date": artifact.get("valuation_date"),
        "controlling_filing": dict(controlling_filing),
        "existing_field_state": {
            field: field_states.get(field) for field in missing
        },
        "skipped_fields": [
            field for field in missing if field not in SUPPORTED_STRUCTURAL_FIELDS
        ],
    }


def _decision_field(decision: Mapping[str, Any]) -> str | None:
    value = decision.get("normalized_concept")
    return value if isinstance(value, str) and value else None


def _blocking_field_names(
    artifact: Mapping[str, Any], decisions: list[Mapping[str, Any]]
) -> list[str]:
    fields: list[str] = []
    for decision in decisions:
        if decision.get("status") == "accepted":
            continue
        field = _decision_field(decision)
        if field is not None and field not in fields:
            fields.append(field)
    if fields:
        return fields
    if decisions:
        return []
    missing = [
        field
        for field in _bridge_missing_fields(artifact)
        if field in SUPPORTED_STRUCTURAL_FIELDS
    ]
    return missing or ["no_decisions"]


def shadow_case_eligibility(
    artifact: Mapping[str, Any],
    decisions: list[Mapping[str, Any]],
    *,
    parser_failed: bool = False,
) -> dict[str, Any]:
    """Classify a structural shadow case without affecting publication."""

    issuer = _mapping(artifact.get("issuer"))
    model_route_eligible = issuer.get("model_route_eligible") is True
    classification_confidence = issuer.get("classification_confidence")
    decision_list = [decision for decision in decisions if isinstance(decision, Mapping)]

    # Status is the first gate. In particular, never treat a non-accepted
    # decision's zero confidence as evidence that can lower the case score.
    nonaccepted = [
        decision
        for decision in decision_list
        if decision.get("status") != "accepted"
    ]
    blocking_fields = _blocking_field_names(artifact, decision_list)
    unsupported_fields = [
        field
        for field in _bridge_missing_fields(artifact)
        if field not in SUPPORTED_STRUCTURAL_FIELDS
    ]
    blocking_fields.extend(unsupported_fields)
    if parser_failed:
        blocking_fields = ["parser", *blocking_fields]
    if not decision_list:
        data_quality_status = "fail"
        data_quality_score = None
    elif nonaccepted or unsupported_fields or parser_failed:
        data_quality_status = "fail"
        data_quality_score = None
    else:
        confidences = [decision.get("confidence") for decision in decision_list]
        if any(
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(float(confidence))
            for confidence in confidences
        ):
            invalid_fields = [
                _decision_field(decision) or "unknown_field"
                for decision in decision_list
                if (
                    isinstance(decision.get("confidence"), bool)
                    or not isinstance(decision.get("confidence"), (int, float))
                    or not math.isfinite(float(decision.get("confidence")))
                )
            ]
            blocking_fields = list(dict.fromkeys(invalid_fields))
            data_quality_status = "fail"
            data_quality_score = None
        else:
            data_quality_status = "pass"
            data_quality_score = min(float(confidence) for confidence in confidences)

    if not model_route_eligible and "model_route" not in blocking_fields:
        blocking_fields.append("model_route")

    if data_quality_status != "pass":
        shadow_disposition = "withhold"
    elif not model_route_eligible:
        shadow_disposition = "withhold"
    elif data_quality_score is not None and data_quality_score >= 0.98:
        shadow_disposition = "publish_candidate"
    else:
        shadow_disposition = "lower_confidence_candidate"

    return {
        "model_route_eligible": model_route_eligible,
        "classification_confidence": classification_confidence,
        "data_quality_status": data_quality_status,
        "data_quality_score": data_quality_score,
        "shadow_disposition": shadow_disposition,
        "blocking_fields": list(dict.fromkeys(blocking_fields)),
        "publication_effect": "none_shadow_only",
    }


def _diagnostics_as_dict(filing: StructuralFiling) -> list[dict[str, Any]]:
    return [
        {
            "code": diagnostic.code,
            "message": diagnostic.message,
            "severity": diagnostic.severity,
            "context": [list(item) for item in diagnostic.context],
        }
        for diagnostic in filing.diagnostics
    ]


def evaluate_shadow_case(
    artifact: Mapping[str, Any], filing: StructuralFiling
) -> dict[str, Any]:
    """Evaluate structural candidates without changing the input or publication state."""

    requests = shadow_requests_from_artifact(artifact)
    report = _artifact_metadata(artifact)
    decisions = [
        resolve_concept(request, filing.facts).as_dict() for request in requests
    ]
    report.update(
        {
            "parser_diagnostics": _diagnostics_as_dict(filing),
            "decisions": decisions,
            **shadow_case_eligibility(artifact, decisions),
        }
    )
    return report
