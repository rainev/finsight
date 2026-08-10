"""Immutable, auditable structural XBRL parsing and resolution records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from numbers import Real
from typing import Any, Literal, Mapping


ResolutionStatus = Literal["accepted", "review", "rejected", "unresolved"]


def _require_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty")


def _validate_date(value: str, field: str) -> None:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be an ISO date") from error


def _validate_optional_date(value: str | None, field: str) -> None:
    if value is not None:
        _validate_date(value, field)


def _validate_number(value: float | None, field: str) -> None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, Real)):
        raise ValueError(f"{field} must be numeric")
    if value is not None:
        try:
            finite = isfinite(value)
        except OverflowError as error:
            raise ValueError(f"{field} must be finite") from error
        if not finite:
            raise ValueError(f"{field} must be finite")


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _tuple_pairs(
    value: Any, field: str, *, allow_lists: bool = False
) -> tuple[tuple[str, str], ...]:
    sequence_type = (list, tuple) if allow_lists else tuple
    if not isinstance(value, sequence_type):
        raise ValueError(f"{field} must be a sequence of pairs")
    pairs: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, sequence_type) or len(item) != 2:
            raise ValueError(f"{field} must be a sequence of pairs")
        key, mapped_value = item
        _require_text(key, field)
        _require_text(mapped_value, field)
        pairs.append((key, mapped_value))
    return tuple(pairs)


@dataclass(frozen=True)
class StructuralFact:
    qname: str
    namespace: str
    local_name: str
    labels: tuple[tuple[str, str], ...]
    documentation: str | None
    value: float | None
    unit: str
    period_start: str | None
    period_end: str
    context_id: str
    dimensions: tuple[tuple[str, str], ...]
    statement_roles: tuple[str, ...]
    presentation_parents: tuple[str, ...]
    calculation_parents: tuple[str, ...]
    calculation_children: tuple[str, ...]
    definition_parents: tuple[str, ...]
    definition_children: tuple[str, ...]
    source_accession: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.qname, "qname"),
            (self.namespace, "namespace"),
            (self.local_name, "local_name"),
            (self.unit, "unit"),
            (self.context_id, "context_id"),
            (self.source_accession, "source_accession"),
        ):
            _require_text(value, field)
        _validate_optional_date(self.period_start, "period_start")
        _validate_date(self.period_end, "period_end")
        _validate_number(self.value, "value")
        if self.documentation is not None and not isinstance(self.documentation, str):
            raise ValueError("documentation must be a string or None")
        for value, field in (
            (self.labels, "labels"),
            (self.dimensions, "dimensions"),
        ):
            if not isinstance(value, tuple):
                raise ValueError(f"{field} must be a tuple")
        for value, field in (
            (self.statement_roles, "statement_roles"),
            (self.presentation_parents, "presentation_parents"),
            (self.calculation_parents, "calculation_parents"),
            (self.calculation_children, "calculation_children"),
            (self.definition_parents, "definition_parents"),
            (self.definition_children, "definition_children"),
        ):
            if not isinstance(value, tuple) or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                raise ValueError(f"{field} must be a tuple of nonempty strings")
        _tuple_pairs(self.labels, "labels")
        _tuple_pairs(self.dimensions, "dimensions")

    def as_dict(self) -> dict[str, Any]:
        return _json_value(
            {
                "qname": self.qname,
                "namespace": self.namespace,
                "local_name": self.local_name,
                "labels": self.labels,
                "documentation": self.documentation,
                "value": self.value,
                "unit": self.unit,
                "period_start": self.period_start,
                "period_end": self.period_end,
                "context_id": self.context_id,
                "dimensions": self.dimensions,
                "statement_roles": self.statement_roles,
                "presentation_parents": self.presentation_parents,
                "calculation_parents": self.calculation_parents,
                "calculation_children": self.calculation_children,
                "definition_parents": self.definition_parents,
                "definition_children": self.definition_children,
                "source_accession": self.source_accession,
            }
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> StructuralFact:
        return cls(
            qname=value["qname"],
            namespace=value["namespace"],
            local_name=value["local_name"],
            labels=_tuple_pairs(value["labels"], "labels", allow_lists=True),
            documentation=value.get("documentation"),
            value=value.get("value"),
            unit=value["unit"],
            period_start=value.get("period_start"),
            period_end=value["period_end"],
            context_id=value["context_id"],
            dimensions=_tuple_pairs(
                value.get("dimensions", ()), "dimensions", allow_lists=True
            ),
            statement_roles=tuple(value.get("statement_roles", ())),
            presentation_parents=tuple(value.get("presentation_parents", ())),
            calculation_parents=tuple(value.get("calculation_parents", ())),
            calculation_children=tuple(value.get("calculation_children", ())),
            definition_parents=tuple(value.get("definition_parents", ())),
            definition_children=tuple(value.get("definition_children", ())),
            source_accession=value["source_accession"],
        )


@dataclass(frozen=True)
class ParseDiagnostic:
    code: str
    message: str
    severity: Literal["info", "warning", "error"]
    context: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.code, "code")
        _require_text(self.message, "message")
        if self.severity not in {"info", "warning", "error"}:
            raise ValueError("severity must be info, warning, or error")
        if not isinstance(self.context, tuple):
            raise ValueError("context must be a tuple")
        _tuple_pairs(self.context, "context")


@dataclass(frozen=True)
class StructuralFiling:
    source_accession: str
    period_end: str
    facts: tuple[StructuralFact, ...]
    diagnostics: tuple[ParseDiagnostic, ...]
    form: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.source_accession, "source_accession")
        _validate_date(self.period_end, "period_end")
        if not isinstance(self.facts, tuple) or not all(
            isinstance(fact, StructuralFact) for fact in self.facts
        ):
            raise ValueError("facts must be a tuple of StructuralFact values")
        if not isinstance(self.diagnostics, tuple) or not all(
            isinstance(diagnostic, ParseDiagnostic) for diagnostic in self.diagnostics
        ):
            raise ValueError("diagnostics must be a tuple of ParseDiagnostic values")
        if self.form is not None:
            _require_text(self.form, "form")

    def as_dict(self) -> dict[str, Any]:
        return _json_value(
            {
                "source_accession": self.source_accession,
                "period_end": self.period_end,
                "facts": tuple(fact.as_dict() for fact in self.facts),
                "diagnostics": tuple(
                    {
                        "code": diagnostic.code,
                        "message": diagnostic.message,
                        "severity": diagnostic.severity,
                        "context": diagnostic.context,
                    }
                    for diagnostic in self.diagnostics
                ),
                "form": self.form,
            }
        )


@dataclass(frozen=True)
class ResolutionRequest:
    normalized_concept: str
    period_end: str
    source_accession: str
    unit: str
    statement_role: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.normalized_concept, "normalized_concept"),
            (self.source_accession, "source_accession"),
            (self.unit, "unit"),
            (self.statement_role, "statement_role"),
        ):
            _require_text(value, field)
        _validate_date(self.period_end, "period_end")


@dataclass(frozen=True)
class ResolutionDecision:
    status: ResolutionStatus
    normalized_concept: str
    source_concept: str | None
    value: float | None
    unit: str | None
    period: str
    source_accession: str
    confidence: float
    mapping_method: str
    reason_codes: tuple[str, ...]
    mapping_version: str = "US-XBRL-RESOLVER-1.0"

    def __post_init__(self) -> None:
        if self.status not in {"accepted", "review", "rejected", "unresolved"}:
            raise ValueError("status must be accepted, review, rejected, or unresolved")
        for value, field in (
            (self.normalized_concept, "normalized_concept"),
            (self.period, "period"),
            (self.source_accession, "source_accession"),
            (self.mapping_method, "mapping_method"),
            (self.mapping_version, "mapping_version"),
        ):
            _require_text(value, field)
        if self.source_concept is not None:
            _require_text(self.source_concept, "source_concept")
        if self.unit is not None:
            _require_text(self.unit, "unit")
        _validate_date(self.period, "period")
        _validate_number(self.value, "value")
        _validate_number(self.confidence, "confidence")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not isinstance(self.reason_codes, tuple) or any(
            not isinstance(code, str) or not code.strip() for code in self.reason_codes
        ):
            raise ValueError("reason_codes must be a tuple of nonempty strings")
        if self.status in {"rejected", "unresolved"} and self.value is not None:
            raise ValueError(f"{self.status} decisions cannot carry a value")
        if self.status == "accepted" and (
            self.value is None or self.source_concept is None or self.unit is None
        ):
            raise ValueError("accepted decisions require source_concept, value, and unit")

    def as_dict(self) -> dict[str, Any]:
        return _json_value(
            {
                "status": self.status,
                "normalized_concept": self.normalized_concept,
                "source_concept": self.source_concept,
                "value": self.value,
                "unit": self.unit,
                "period": self.period,
                "source_accession": self.source_accession,
                "confidence": self.confidence,
                "mapping_method": self.mapping_method,
                "reason_codes": self.reason_codes,
                "mapping_version": self.mapping_version,
            }
        )
