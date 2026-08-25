"""Immutable, auditable structural XBRL parsing and resolution records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from numbers import Real
import sys
from typing import Any, Literal, Mapping


ResolutionStatus = Literal["accepted", "review", "rejected", "unresolved"]
MAX_SUPPORTED_INTEGER = int(sys.float_info.max)
ELIGIBLE_FILING_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"})


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
        if isinstance(value, int):
            if abs(value) > MAX_SUPPORTED_INTEGER:
                raise ValueError(f"{field} must be finite")
            return
        try:
            finite = isfinite(value)
        except OverflowError as error:
            raise ValueError(f"{field} must be finite") from error
        if not finite:
            raise ValueError(f"{field} must be finite")


def normalize_filing_form(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("form must be a string")
    return value.strip().upper()


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
class StructuralRelationship:
    arcrole: str
    linkrole: str
    from_concept: str
    to_concept: str
    order: float | None
    preferred_label: str | None
    calculation_weight: float | None
    statement_role: str | None = None

    def __post_init__(self) -> None:
        for value, field in (
            (self.arcrole, "arcrole"),
            (self.linkrole, "linkrole"),
            (self.from_concept, "from_concept"),
            (self.to_concept, "to_concept"),
        ):
            _require_text(value, field)
        if self.preferred_label is not None:
            _require_text(self.preferred_label, "preferred_label")
        if self.statement_role not in {
            None,
            "balance_sheet",
            "income_statement",
            "cash_flow",
        }:
            raise ValueError("statement_role must be a recognized statement role")
        _validate_number(self.order, "order")
        _validate_number(self.calculation_weight, "calculation_weight")

    def as_dict(self) -> dict[str, Any]:
        return {
            "arcrole": self.arcrole,
            "linkrole": self.linkrole,
            "from_concept": self.from_concept,
            "to_concept": self.to_concept,
            "order": self.order,
            "preferred_label": self.preferred_label,
            "calculation_weight": self.calculation_weight,
            "statement_role": self.statement_role,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> StructuralRelationship:
        return cls(
            arcrole=value["arcrole"],
            linkrole=value["linkrole"],
            from_concept=value["from_concept"],
            to_concept=value["to_concept"],
            order=value.get("order"),
            preferred_label=value.get("preferred_label"),
            calculation_weight=value.get("calculation_weight"),
            statement_role=value.get("statement_role"),
        )


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
    decimals: str | None = None
    scale: str | None = None
    sign: str | None = None
    filing_form: str | None = None
    filed_date: str | None = None
    report_date: str | None = None
    entity_identifier: str | None = None
    entity_scheme: str | None = None
    filing_metadata: tuple[tuple[str, str], ...] = ()
    presentation_ancestry: tuple[str, ...] = ()
    relationships: tuple[StructuralRelationship, ...] = ()

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
            (self.decimals, "decimals"),
            (self.scale, "scale"),
            (self.sign, "sign"),
        ):
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{field} must be a string or None")
        if self.filing_form is not None:
            normalized_form = normalize_filing_form(self.filing_form)
            object.__setattr__(self, "filing_form", normalized_form)
        _validate_optional_date(self.filed_date, "filed_date")
        _validate_optional_date(self.report_date, "report_date")
        for value, field in (
            (self.entity_identifier, "entity_identifier"),
            (self.entity_scheme, "entity_scheme"),
        ):
            if value is not None:
                _require_text(value, field)
        for value, field in (
            (self.labels, "labels"),
            (self.dimensions, "dimensions"),
            (self.filing_metadata, "filing_metadata"),
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
            (self.presentation_ancestry, "presentation_ancestry"),
        ):
            if not isinstance(value, tuple) or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                raise ValueError(f"{field} must be a tuple of nonempty strings")
        _tuple_pairs(self.labels, "labels")
        _tuple_pairs(self.dimensions, "dimensions")
        _tuple_pairs(self.filing_metadata, "filing_metadata")
        if not isinstance(self.relationships, tuple) or not all(
            isinstance(item, StructuralRelationship) for item in self.relationships
        ):
            raise ValueError("relationships must be a tuple of StructuralRelationship values")

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
                "decimals": self.decimals,
                "scale": self.scale,
                "sign": self.sign,
                "filing_form": self.filing_form,
                "filed_date": self.filed_date,
                "report_date": self.report_date,
                "entity_identifier": self.entity_identifier,
                "entity_scheme": self.entity_scheme,
                "filing_metadata": self.filing_metadata,
                "presentation_ancestry": self.presentation_ancestry,
                "relationships": tuple(item.as_dict() for item in self.relationships),
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
            decimals=value.get("decimals"),
            scale=value.get("scale"),
            sign=value.get("sign"),
            filing_form=value.get("filing_form"),
            filed_date=value.get("filed_date"),
            report_date=value.get("report_date"),
            entity_identifier=value.get("entity_identifier"),
            entity_scheme=value.get("entity_scheme"),
            filing_metadata=_tuple_pairs(
                value.get("filing_metadata", ()),
                "filing_metadata",
                allow_lists=True,
            ),
            presentation_ancestry=tuple(value.get("presentation_ancestry", ())),
            relationships=tuple(
                StructuralRelationship.from_dict(item)
                for item in value.get("relationships", ())
            ),
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

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ParseDiagnostic:
        if not isinstance(value, Mapping):
            raise ValueError("diagnostic must be an object")
        return cls(
            code=value["code"],
            message=value["message"],
            severity=value["severity"],
            context=_tuple_pairs(
                value.get("context", ()), "context", allow_lists=True
            ),
        )


@dataclass(frozen=True)
class StructuralFiling:
    source_accession: str
    period_end: str
    facts: tuple[StructuralFact, ...]
    diagnostics: tuple[ParseDiagnostic, ...]
    form: str | None = None
    filed_date: str | None = None
    report_date: str | None = None
    filing_metadata: tuple[tuple[str, str], ...] = ()

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
            normalized_form = normalize_filing_form(self.form)
            _require_text(normalized_form, "form")
            object.__setattr__(self, "form", normalized_form)
        _validate_optional_date(self.filed_date, "filed_date")
        _validate_optional_date(self.report_date, "report_date")
        if not isinstance(self.filing_metadata, tuple):
            raise ValueError("filing_metadata must be a tuple")
        _tuple_pairs(self.filing_metadata, "filing_metadata")

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
                "filed_date": self.filed_date,
                "report_date": self.report_date,
                "filing_metadata": self.filing_metadata,
            }
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> StructuralFiling:
        if not isinstance(value, Mapping):
            raise ValueError("structural filing must be an object")
        raw_facts = value.get("facts")
        raw_diagnostics = value.get("diagnostics")
        if not isinstance(raw_facts, (list, tuple)):
            raise ValueError("facts must be a list")
        if not isinstance(raw_diagnostics, (list, tuple)):
            raise ValueError("diagnostics must be a list")
        return cls(
            source_accession=value["source_accession"],
            period_end=value["period_end"],
            facts=tuple(StructuralFact.from_dict(item) for item in raw_facts),
            diagnostics=tuple(
                ParseDiagnostic.from_dict(item) for item in raw_diagnostics
            ),
            form=value.get("form"),
            filed_date=value.get("filed_date"),
            report_date=value.get("report_date"),
            filing_metadata=_tuple_pairs(
                value.get("filing_metadata", ()),
                "filing_metadata",
                allow_lists=True,
            ),
        )


@dataclass(frozen=True)
class ResolutionRequest:
    normalized_concept: str
    period_end: str
    source_accession: str
    unit: str
    statement_role: str
    form: str
    valuation_date: str | None = None

    def __post_init__(self) -> None:
        for value, field in (
            (self.normalized_concept, "normalized_concept"),
            (self.source_accession, "source_accession"),
            (self.unit, "unit"),
            (self.statement_role, "statement_role"),
        ):
            _require_text(value, field)
        _validate_date(self.period_end, "period_end")
        _validate_optional_date(self.valuation_date, "valuation_date")
        object.__setattr__(self, "form", normalize_filing_form(self.form))


@dataclass(frozen=True)
class ResolutionEvidence:
    fact: StructuralFact
    mapping_version: str
    confidence: float
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.fact, StructuralFact):
            raise ValueError("fact must be StructuralFact")
        _require_text(self.mapping_version, "mapping_version")
        _validate_number(self.confidence, "confidence")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not isinstance(self.reason_codes, tuple) or any(
            not isinstance(code, str) or not code.strip() for code in self.reason_codes
        ):
            raise ValueError("reason_codes must be a tuple of nonempty strings")

    @classmethod
    def from_fact(
        cls,
        fact: StructuralFact,
        *,
        mapping_version: str,
        confidence: float,
        reason_codes: tuple[str, ...],
    ) -> ResolutionEvidence:
        return cls(
            fact=fact,
            mapping_version=mapping_version,
            confidence=confidence,
            reason_codes=reason_codes,
        )

    def validate_complete(self) -> None:
        fact = self.fact
        has_statement_evidence = bool(
            fact.statement_roles
            or fact.presentation_parents
            or fact.calculation_parents
            or fact.presentation_ancestry
        )
        if (
            not fact.namespace
            or not fact.context_id
            or not has_statement_evidence
            or not fact.relationships
            or not (fact.labels or fact.documentation)
            or fact.decimals is None
            or not fact.filing_form
            or not fact.filing_metadata
        ):
            raise ValueError("accepted/review decisions require complete evidence")

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.fact.as_dict(),
            "mapping_version": self.mapping_version,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
        }


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
    form: str
    evidence: ResolutionEvidence | None
    mapping_version: str = "US-XBRL-RESOLVER-1.1"

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
        object.__setattr__(self, "form", normalize_filing_form(self.form))
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
        if self.status in {"accepted", "review"}:
            if self.evidence is None:
                raise ValueError("accepted/review decisions require evidence")
            self.evidence.validate_complete()
            if (
                self.evidence.fact.qname != self.source_concept
                or self.evidence.fact.value != self.value
                or self.evidence.fact.unit != self.unit
                or self.evidence.fact.period_end != self.period
                or self.evidence.fact.source_accession != self.source_accession
                or self.evidence.fact.filing_form != self.form
                or self.evidence.mapping_version != self.mapping_version
                or self.evidence.confidence != self.confidence
                or self.evidence.reason_codes != self.reason_codes
            ):
                raise ValueError("decision evidence does not match the selected fact")
        elif self.evidence is not None:
            raise ValueError("rejected/unresolved decisions cannot carry evidence")

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
                "form": self.form,
                "evidence": self.evidence.as_dict() if self.evidence is not None else None,
                "mapping_version": self.mapping_version,
            }
        )
