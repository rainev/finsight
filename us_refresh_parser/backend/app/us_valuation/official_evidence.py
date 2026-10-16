"""Private, point-in-time evidence contracts for U.S. valuation inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from numbers import Real
import re
from typing import Any, Literal, Mapping, Sequence, get_args


EvidenceStatus = Literal[
    "reported", "reported_aggregate", "explicit_zero", "not_disclosed",
    "stale", "conflicting", "bounded_estimate", "unresolved",
]
Materiality = Literal["material", "supporting"]
PeriodRole = Literal[
    "operating_ttm", "balance_sheet_snapshot", "annual_history", "regulatory_snapshot",
]

_STATUSES = frozenset(get_args(EvidenceStatus))
_MATERIALITIES = frozenset(get_args(Materiality))
_PERIOD_ROLES = frozenset(get_args(PeriodRole))
_POINT_STATUSES = frozenset({"reported", "reported_aggregate", "explicit_zero"})
_NONPOINT_STATUSES = frozenset({"not_disclosed", "stale", "conflicting", "unresolved"})
_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty text")
    return value.strip()


def _optional_text(value: object, field: str) -> str | None:
    return None if value is None else _text(value, field)


def _iso(value: object, field: str) -> str:
    text = _text(value, field)
    try:
        date.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO date") from error
    return text


def _optional_iso(value: object, field: str) -> str | None:
    return None if value is None else _iso(value, field)


def _finite(value: object, field: str, *, optional: bool = False) -> float | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value)):
        raise ValueError(f"{field} must be a finite number")
    return float(value)


def _strings(value: Sequence[object], field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{field} must be a sequence")
    result = tuple(_text(item, field) for item in value)
    if not allow_empty and not result:
        raise ValueError(f"{field} must not be empty")
    return result


def _dimensions(value: Sequence[Sequence[object]]) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for item in value:
        if isinstance(item, (str, bytes)) or len(item) != 2:
            raise ValueError("dimensions must contain axis/member pairs")
        result.append((_text(item[0], "dimension axis"), _text(item[1], "dimension member")))
    normalized = tuple(sorted(result))
    if len(normalized) != len(set(normalized)):
        raise ValueError("dimensions must not contain duplicates")
    return normalized


@dataclass(frozen=True)
class EvidenceRequest:
    required_field: str
    model: str
    period_role: PeriodRole
    materiality: Materiality
    valuation_date: str | None = None
    expected_unit: str | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_field", _text(self.required_field, "required_field"))
        object.__setattr__(self, "model", _text(self.model, "model"))
        if self.period_role not in _PERIOD_ROLES:
            raise ValueError("period_role is unsupported")
        if self.materiality not in _MATERIALITIES:
            raise ValueError("materiality is unsupported")
        object.__setattr__(self, "valuation_date", _optional_iso(self.valuation_date, "valuation_date"))
        object.__setattr__(self, "expected_unit", _optional_text(self.expected_unit, "expected_unit"))
        identifier = self.request_id or ":".join(
            (self.model, self.required_field, self.period_role, self.valuation_date or "unspecified")
        )
        object.__setattr__(self, "request_id", _text(identifier, "request_id"))

    @property
    def field(self) -> str:
        return self.required_field

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "required_field": self.required_field,
            "model": self.model,
            "period_role": self.period_role,
            "materiality": self.materiality,
            "valuation_date": self.valuation_date,
            "expected_unit": self.expected_unit,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> EvidenceRequest:
        return cls(
            request_id=value.get("request_id"),
            required_field=value.get("required_field", value.get("field")),
            model=value["model"],
            period_role=value["period_role"],
            materiality=value["materiality"],
            valuation_date=value.get("valuation_date"),
            expected_unit=value.get("expected_unit"),
        )


@dataclass(frozen=True)
class EvidenceCandidate:
    value: float | None
    tag: str
    dimensions: tuple[tuple[str, str], ...]
    unit: str
    period_end: str
    accession: str
    filed_date: str
    source_url: str
    extraction_method: str
    field: str | None = None
    period_start: str | None = None
    report_date: str | None = None
    form: str | None = None
    source_kind: str = "sec_filing"
    cik: str | None = None
    entity_identifier: str | None = None
    entity_scheme: str | None = None
    consolidation_scope: str = "unknown"
    covered_fields: tuple[str, ...] = ()
    coverage_basis: str | None = None
    double_count_exclusions: tuple[str, ...] = ()
    candidate_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _finite(self.value, "value", optional=True))
        object.__setattr__(self, "tag", _text(self.tag, "tag"))
        object.__setattr__(self, "dimensions", _dimensions(self.dimensions))
        object.__setattr__(self, "unit", _text(self.unit, "unit"))
        object.__setattr__(self, "period_start", _optional_iso(self.period_start, "period_start"))
        object.__setattr__(self, "period_end", _iso(self.period_end, "period_end"))
        if self.period_start and self.period_start > self.period_end:
            raise ValueError("period_start must not follow period_end")
        accession = _text(self.accession, "accession")
        if not _ACCESSION.fullmatch(accession):
            raise ValueError("accession must use the SEC 10-2-6 format")
        object.__setattr__(self, "accession", accession)
        object.__setattr__(self, "filed_date", _iso(self.filed_date, "filed_date"))
        object.__setattr__(self, "report_date", _optional_iso(self.report_date, "report_date"))
        object.__setattr__(self, "source_url", _text(self.source_url, "source_url"))
        object.__setattr__(self, "extraction_method", _text(self.extraction_method, "extraction_method"))
        for field in ("field", "form", "cik", "entity_identifier", "entity_scheme"):
            object.__setattr__(self, field, _optional_text(getattr(self, field), field))
        object.__setattr__(self, "source_kind", _text(self.source_kind, "source_kind"))
        object.__setattr__(self, "consolidation_scope", _text(self.consolidation_scope, "consolidation_scope"))
        object.__setattr__(self, "covered_fields", _strings(self.covered_fields, "covered_fields"))
        object.__setattr__(self, "coverage_basis", _optional_text(self.coverage_basis, "coverage_basis"))
        object.__setattr__(self, "double_count_exclusions", _strings(self.double_count_exclusions, "double_count_exclusions"))
        identifier = self.candidate_id or ":".join(
            (self.accession, self.field or "unspecified", self.tag, self.period_end, self.unit)
        )
        object.__setattr__(self, "candidate_id", _text(identifier, "candidate_id"))

    @property
    def source_accession(self) -> str:
        return self.accession

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "field": self.field,
            "value": self.value,
            "tag": self.tag,
            "dimensions": [list(item) for item in self.dimensions],
            "unit": self.unit,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "accession": self.accession,
            "filed_date": self.filed_date,
            "report_date": self.report_date,
            "source_url": self.source_url,
            "extraction_method": self.extraction_method,
            "form": self.form,
            "source_kind": self.source_kind,
            "cik": self.cik,
            "entity_identifier": self.entity_identifier,
            "entity_scheme": self.entity_scheme,
            "consolidation_scope": self.consolidation_scope,
            "covered_fields": list(self.covered_fields),
            "coverage_basis": self.coverage_basis,
            "double_count_exclusions": list(self.double_count_exclusions),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> EvidenceCandidate:
        return cls(
            candidate_id=value.get("candidate_id"), field=value.get("field"),
            value=value.get("value"), tag=value["tag"],
            dimensions=tuple(tuple(item) for item in value.get("dimensions", ())),
            unit=value["unit"], period_start=value.get("period_start"),
            period_end=value["period_end"],
            accession=value.get("accession", value.get("source_accession")),
            filed_date=value["filed_date"], report_date=value.get("report_date"),
            source_url=value["source_url"], extraction_method=value["extraction_method"],
            form=value.get("form"), source_kind=value.get("source_kind", "sec_filing"),
            cik=value.get("cik"), entity_identifier=value.get("entity_identifier"),
            entity_scheme=value.get("entity_scheme"),
            consolidation_scope=value.get("consolidation_scope", "unknown"),
            covered_fields=tuple(value.get("covered_fields", ())),
            coverage_basis=value.get("coverage_basis"),
            double_count_exclusions=tuple(value.get("double_count_exclusions", ())),
        )


def _normalize_rejections(value: Sequence[object]) -> tuple[dict[str, Any], ...]:
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("rejected_candidates entries must be mappings")
        raw_candidate = item.get("candidate")
        candidate = raw_candidate if isinstance(raw_candidate, EvidenceCandidate) else (
            EvidenceCandidate.from_dict(raw_candidate) if isinstance(raw_candidate, Mapping) else None
        )
        if candidate is None:
            raise ValueError("rejected candidate record needs a candidate")
        reasons = _strings(item.get("reason_codes", ()), "rejection reason_codes", allow_empty=False)
        normalized.append({"candidate": candidate.as_dict(), "reason_codes": reasons})
    return tuple(normalized)


@dataclass(frozen=True)
class EvidenceDecision:
    request: EvidenceRequest
    selected: EvidenceCandidate | None
    selected_range: tuple[float, float] | None
    rejected_candidates: tuple[dict[str, Any], ...]
    status: EvidenceStatus
    completeness_proof: tuple[str, ...]
    reason_codes: tuple[str, ...]
    valuation_date: str | None = None
    package_failure: dict[str, Any] | None = None
    range_provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.request, EvidenceRequest):
            raise ValueError("request must be EvidenceRequest")
        if self.selected is not None and not isinstance(self.selected, EvidenceCandidate):
            raise ValueError("selected must be EvidenceCandidate or None")
        if self.status not in _STATUSES:
            raise ValueError("unsupported evidence status")
        object.__setattr__(self, "completeness_proof", _strings(self.completeness_proof, "completeness_proof", allow_empty=False))
        object.__setattr__(self, "reason_codes", _strings(self.reason_codes, "reason_codes", allow_empty=False))
        object.__setattr__(self, "rejected_candidates", _normalize_rejections(self.rejected_candidates))
        object.__setattr__(self, "range_provenance", _strings(self.range_provenance, "range_provenance"))
        cutoff = self.valuation_date or self.request.valuation_date
        object.__setattr__(self, "valuation_date", _optional_iso(cutoff, "valuation_date"))
        if self.selected is not None:
            if self.selected.field is not None and self.selected.field != self.request.required_field:
                raise ValueError("selected candidate field does not match the request")
            if cutoff is not None and self.selected.filed_date > cutoff:
                raise ValueError("selected candidate was filed after the valuation cutoff")
            if self.request.expected_unit and self.selected.unit != self.request.expected_unit:
                raise ValueError("selected candidate unit does not match the request")
        if self.status in _POINT_STATUSES:
            if self.selected is None or self.selected.value is None:
                raise ValueError(f"{self.status} requires a selected numeric candidate")
            if self.selected_range is not None:
                raise ValueError(f"{self.status} cannot carry a selected range")
            if self.status == "explicit_zero" and self.selected.value != 0:
                raise ValueError("explicit_zero requires a reported zero candidate")
            if (
                self.selected.field != self.request.required_field
                or not self.selected.cik
                or not self.selected.entity_identifier
                or not self.selected.entity_scheme
                or self.selected.consolidation_scope not in {"consolidated_parent", "public_parent"}
            ):
                raise ValueError("selected production evidence requires exact parent identity and consolidation scope")
            if self.status == "reported_aggregate" and (
                not self.selected.covered_fields
                or not self.selected.coverage_basis
                or self.request.required_field not in self.selected.covered_fields
            ):
                raise ValueError("reported_aggregate requires explicit aggregate coverage proof")
        elif self.status == "bounded_estimate":
            if self.selected is not None or self.selected_range is None:
                raise ValueError("bounded_estimate requires only a selected range")
            if not self.range_provenance:
                raise ValueError("bounded_estimate requires range provenance")
        elif self.status in _NONPOINT_STATUSES and (self.selected is not None or self.selected_range is not None):
            raise ValueError(f"{self.status} cannot carry selected evidence")
        if self.selected_range is not None:
            if len(self.selected_range) != 2:
                raise ValueError("selected_range must have low and high")
            low = _finite(self.selected_range[0], "selected_range low")
            high = _finite(self.selected_range[1], "selected_range high")
            assert low is not None and high is not None
            if low > high:
                raise ValueError("selected_range must be ordered")
            object.__setattr__(self, "selected_range", (low, high))
        if self.status == "not_disclosed" and "search_complete" not in self.completeness_proof:
            raise ValueError("not_disclosed requires search_complete proof")
        if self.package_failure is not None:
            if not isinstance(self.package_failure, Mapping):
                raise ValueError("package_failure must be a mapping")
            failure = dict(self.package_failure)
            _text(failure.get("code"), "package_failure code")
            _text(failure.get("detail"), "package_failure detail")
            object.__setattr__(self, "package_failure", failure)
            if self.status != "unresolved" or self.selected is not None:
                raise ValueError("package failure requires an unresolved decision")

    @property
    def selected_candidate(self) -> EvidenceCandidate | None:
        return self.selected

    @property
    def selected_value(self) -> float | None:
        return self.selected.value if self.selected is not None else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.as_dict(),
            "selected": self.selected.as_dict() if self.selected is not None else None,
            "selected_value": self.selected_value,
            "selected_range": list(self.selected_range) if self.selected_range is not None else None,
            "rejected_candidates": [dict(item) for item in self.rejected_candidates],
            "status": self.status,
            "completeness_proof": list(self.completeness_proof),
            "reason_codes": list(self.reason_codes),
            "valuation_date": self.valuation_date,
            "package_failure": self.package_failure,
            "range_provenance": list(self.range_provenance),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> EvidenceDecision:
        selected = value.get("selected", value.get("selected_candidate"))
        selected_range = value.get("selected_range")
        return cls(
            request=EvidenceRequest.from_dict(value["request"]),
            selected=EvidenceCandidate.from_dict(selected) if isinstance(selected, Mapping) else None,
            selected_range=tuple(selected_range) if selected_range is not None else None,
            rejected_candidates=tuple(value.get("rejected_candidates", ())),
            status=value["status"], completeness_proof=tuple(value.get("completeness_proof", ())),
            reason_codes=tuple(value.get("reason_codes", ())),
            valuation_date=value.get("valuation_date"),
            package_failure=dict(value["package_failure"]) if isinstance(value.get("package_failure"), Mapping) else None,
            range_provenance=tuple(value.get("range_provenance", ())),
        )


def unresolved_package_failure(
    request: EvidenceRequest, *, valuation_date: str, code: str, accession: str, detail: str,
) -> EvidenceDecision:
    return EvidenceDecision(
        request=request, selected=None, selected_range=None, rejected_candidates=(),
        status="unresolved", completeness_proof=("companyfacts_checked", "package_capture_failed"),
        reason_codes=("OFFICIAL_FILING_PACKAGE_FAILURE", _text(code, "code")),
        valuation_date=valuation_date,
        package_failure={"code": code, "accession": accession, "detail": detail},
    )
