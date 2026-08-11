"""Non-publishing evaluation of structural XBRL bridge candidates."""

from __future__ import annotations

from typing import Any, Mapping

from .concept_resolver import resolve_concept
from .structural_xbrl import ResolutionRequest, StructuralFiling


_MARKETABLE_SECURITIES_FIELDS = frozenset(
    {
        "marketable_securities_current",
        "marketable_securities_noncurrent",
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
    """Build marketable-securities resolution requests from explicit bridge gaps only."""

    missing = _bridge_missing_fields(artifact)
    requested_fields = tuple(
        field for field in missing if field in _MARKETABLE_SECURITIES_FIELDS
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
            field for field in missing if field not in _MARKETABLE_SECURITIES_FIELDS
        ],
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
    report.update(
        {
            "parser_diagnostics": _diagnostics_as_dict(filing),
            "decisions": [
                resolve_concept(request, filing.facts).as_dict() for request in requests
            ],
            "publication_effect": "none_shadow_only",
        }
    )
    return report
