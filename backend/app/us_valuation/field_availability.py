"""Immutable field-availability and uncertainty records for valuation bridges."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from numbers import Real
from typing import TYPE_CHECKING, Any, Literal, Mapping, get_args

if TYPE_CHECKING:
    from .structural_xbrl import ResolutionDecision


AvailabilityState = Literal[
    "reported",
    "explicit_zero",
    "evidence_backed_zero",
    "not_applicable",
    "proxy",
    "bounded_unresolved",
    "not_disclosed",
    "unresolved",
    "stale",
    "conflict",
]
AvailabilityAuthority = Literal["production", "shadow"]
FallbackLevel = Literal[
    "current_reported",
    "current_structural",
    "reported_aggregate",
    "annual_carried_forward",
    "company_history",
    "sector_estimate",
]
CoverageBasis = Literal[
    "direct_issuer_total",
    "calculation_relationship",
    "reconciled_disjoint_components",
]
Freshness = Literal["current", "carried_forward", "stale", "unknown"]
PeriodRole = Literal["operating_ttm", "balance_sheet_snapshot"]


_AVAILABILITY_STATES = frozenset(get_args(AvailabilityState))
_AVAILABILITY_AUTHORITIES = frozenset(get_args(AvailabilityAuthority))
_FALLBACK_LEVELS = frozenset(get_args(FallbackLevel))
_COVERAGE_BASES = frozenset(get_args(CoverageBasis))
_FRESHNESS_STATES = frozenset(get_args(Freshness))
_PERIOD_ROLES = frozenset(get_args(PeriodRole))
_POINT_STATES = frozenset({"reported", "proxy"})
_ZERO_STATES = frozenset(
    {"explicit_zero", "evidence_backed_zero", "not_applicable"}
)
_BOUNDED_STATES = frozenset({"bounded_unresolved"})
_NONPOINT_STATES = frozenset({"not_disclosed", "unresolved", "stale", "conflict"})
_PRODUCTION_SOURCE_STATES = _POINT_STATES | _ZERO_STATES | _BOUNDED_STATES


LEGACY_STATE_MAP: dict[str, AvailabilityState] = {
    "reported": "reported",
    "governed_filing_fact": "reported",
    "policy_verified_zero": "evidence_backed_zero",
    "weighted_average_diluted_proxy": "proxy",
    "verification_stale": "stale",
    "missing": "unresolved",
}


def _require_finite_number(value: object, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field} must be a finite number")
    try:
        finite = isfinite(value)
    except (OverflowError, TypeError) as error:
        raise ValueError(f"{field} must be a finite number") from error
    if not finite:
        raise ValueError(f"{field} must be a finite number")


def _require_nonempty_text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty")


def _require_string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError(f"{field} must be a tuple of nonempty strings")
    for item in value:
        _require_nonempty_text(item, field)
    return value


def _restore_string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be an array of nonempty strings")
    restored = tuple(value)
    _require_string_tuple(restored, field)
    return restored


def _coverage_source_fact_parts(value: str) -> tuple[str, str, str, str]:
    parts = tuple(value.split("|"))
    if (
        len(parts) != 4
        or any(not part.strip() for part in parts)
        or ":" not in parts[2]
    ):
        raise ValueError(
            "coverage_source_facts must use accession|period|concept|context"
        )
    return parts  # type: ignore[return-value]


@dataclass(frozen=True)
class UncertaintyRange:
    low: float
    high: float
    basis: str
    source_accessions: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_finite_number(self.low, "low")
        _require_finite_number(self.high, "high")
        if self.low < 0 or self.low > self.high:
            raise ValueError("uncertainty range must satisfy 0 <= low <= high")
        _require_nonempty_text(self.basis, "basis")
        source_accessions = _require_string_tuple(
            self.source_accessions, "source_accessions"
        )
        if not source_accessions:
            raise ValueError("source_accessions must contain at least one accession")


@dataclass(frozen=True)
class FieldAvailability:
    field: str
    value: float | None
    state: AvailabilityState
    reason_code: str
    period_end: str
    source_accession: str | None
    source_kind: str | None
    evidence_class: str | None
    freshness: Freshness
    fallback_level: FallbackLevel = "current_reported"
    period_role: PeriodRole = "balance_sheet_snapshot"
    source_age_days: int | None = None
    uncertainty: UncertaintyRange | None = None
    covered_fields: tuple[str, ...] = ()
    coverage_basis: CoverageBasis | None = None
    coverage_source_facts: tuple[str, ...] = ()
    economic_scope: str | None = None
    extraction_complete: bool = False
    searched_concepts: tuple[str, ...] = ()
    authority: AvailabilityAuthority = "production"
    mapping_version: str = "US-FIELD-AVAILABILITY-1.0"

    def __post_init__(self) -> None:
        if self.state not in _AVAILABILITY_STATES:
            raise ValueError("state must be a recognized availability state")
        if self.authority not in _AVAILABILITY_AUTHORITIES:
            raise ValueError("authority must be production or shadow")
        if self.fallback_level not in _FALLBACK_LEVELS:
            raise ValueError("fallback_level must be a recognized fallback level")
        if self.freshness not in _FRESHNESS_STATES:
            raise ValueError(
                "freshness must be current, carried_forward, stale, or unknown"
            )
        if self.period_role not in _PERIOD_ROLES:
            raise ValueError(
                "period_role must be operating_ttm or balance_sheet_snapshot"
            )
        if self.fallback_level == "annual_carried_forward" and self.period_role != (
            "balance_sheet_snapshot"
        ):
            raise ValueError(
                "annual_carried_forward is only valid for balance-sheet snapshots"
            )
        if (self.fallback_level == "annual_carried_forward") != (
            self.freshness == "carried_forward"
        ):
            raise ValueError(
                "annual_carried_forward and carried_forward must be used together"
            )
        if (
            self.source_age_days is not None
            and (
                isinstance(self.source_age_days, bool)
                or not isinstance(self.source_age_days, int)
                or self.source_age_days < 0
            )
        ):
            raise ValueError("source_age_days must be a nonnegative integer or None")

        if self.value is not None:
            _require_finite_number(self.value, "value")
        if self.uncertainty is not None and not isinstance(
            self.uncertainty, UncertaintyRange
        ):
            raise ValueError("uncertainty must be an UncertaintyRange or None")
        if (
            self.uncertainty is not None
            and self.value is not None
            and not self.uncertainty.low <= self.value <= self.uncertainty.high
        ):
            raise ValueError("point value must lie inside its uncertainty range")
        if self.source_accession is not None:
            _require_nonempty_text(self.source_accession, "source_accession")
        if not isinstance(self.extraction_complete, bool):
            raise ValueError("extraction_complete must be a boolean")

        covered_fields = _require_string_tuple(self.covered_fields, "covered_fields")
        object.__setattr__(self, "covered_fields", tuple(sorted(set(covered_fields))))
        coverage_source_facts = _require_string_tuple(
            self.coverage_source_facts, "coverage_source_facts"
        )
        object.__setattr__(
            self,
            "coverage_source_facts",
            tuple(sorted(set(coverage_source_facts))),
        )
        has_coverage_proof = any(
            (
                self.coverage_basis is not None,
                bool(coverage_source_facts),
                self.economic_scope is not None,
            )
        )
        if has_coverage_proof or self.fallback_level == "reported_aggregate":
            if not covered_fields:
                raise ValueError("aggregate coverage proof requires covered_fields")
            if self.coverage_basis not in _COVERAGE_BASES:
                raise ValueError("aggregate coverage proof requires coverage_basis")
            if not coverage_source_facts:
                raise ValueError(
                    "aggregate coverage proof requires coverage_source_facts"
                )
            _require_nonempty_text(self.economic_scope, "economic_scope")
            parsed_coverage_facts = tuple(
                _coverage_source_fact_parts(item)
                for item in coverage_source_facts
            )
            if self.fallback_level == "reported_aggregate" and any(
                accession != self.source_accession or period != self.period_end
                for accession, period, _, _ in parsed_coverage_facts
            ):
                raise ValueError(
                    "current aggregate coverage facts must match source accession and period"
                )
            if (
                self.fallback_level in {"annual_carried_forward", "company_history"}
                and self.uncertainty is not None
                and any(
                    accession not in self.uncertainty.source_accessions
                    for accession, _, _, _ in parsed_coverage_facts
                )
            ):
                raise ValueError(
                    "historical aggregate coverage facts must match uncertainty sources"
                )
        searched_concepts = _require_string_tuple(
            self.searched_concepts, "searched_concepts"
        )
        object.__setattr__(
            self, "searched_concepts", tuple(sorted(set(searched_concepts)))
        )
        if self.extraction_complete and not searched_concepts:
            raise ValueError(
                "complete extraction requires searched_concepts"
            )

        if self.state in _POINT_STATES:
            if self.value is None:
                raise ValueError(f"{self.state} requires a finite point value")
        elif self.state in _ZERO_STATES:
            if self.value != 0:
                raise ValueError(f"{self.state} requires value == 0")
            if self.freshness != "current":
                raise ValueError(f"{self.state} requires current freshness")
        elif self.state in _BOUNDED_STATES:
            if self.value is not None:
                raise ValueError("bounded_unresolved requires value is None")
            if self.freshness not in (
                {"carried_forward"}
                if self.fallback_level == "annual_carried_forward"
                else {"current"}
            ):
                raise ValueError("bounded_unresolved freshness does not match its fallback")
            if self.uncertainty is None:
                raise ValueError("bounded_unresolved requires uncertainty")
        elif self.state in _NONPOINT_STATES:
            if self.value is not None:
                raise ValueError(f"{self.state} requires value is None")
            if self.uncertainty is not None:
                raise ValueError(f"{self.state} requires uncertainty is None")

        if self.state == "stale" and self.freshness != "stale":
            raise ValueError("stale requires stale freshness")
        if self.state == "not_disclosed":
            if not self.extraction_complete:
                raise ValueError(
                    "not_disclosed requires complete extraction"
                )
            if self.freshness != "current":
                raise ValueError("not_disclosed requires current freshness")
            if (
                self.source_accession is None
                or self.source_kind is None
                or self.evidence_class is None
            ):
                raise ValueError(
                    "not_disclosed requires current source metadata"
                )

        if (
            self.authority == "production"
            and self.state in _PRODUCTION_SOURCE_STATES
            and self.source_accession is None
        ):
            raise ValueError(
                f"production {self.state} requires source_accession"
            )

        if self.fallback_level == "annual_carried_forward":
            if self.authority != "production":
                raise ValueError(
                    "annual_carried_forward requires production authority"
                )
            if self.state not in {"reported", "bounded_unresolved"}:
                raise ValueError("annual_carried_forward requires reported or bounded state")
            if self.state == "reported" and (self.value is None or self.value < 0):
                raise ValueError("reported annual carry-forward requires a finite nonnegative value")
            if self.state == "bounded_unresolved" and self.uncertainty is None:
                raise ValueError("bounded annual carry-forward requires uncertainty")
            if self.source_kind != "companyfacts":
                raise ValueError(
                    "annual_carried_forward requires source_kind companyfacts"
                )
            if self.evidence_class not in {"reported", "bounded_estimate"}:
                raise ValueError("annual_carried_forward requires reported or bounded evidence class")
            if self.freshness != "carried_forward":
                raise ValueError(
                    "annual_carried_forward requires carried_forward freshness"
                )
            if self.source_accession is None:
                raise ValueError(
                    "annual_carried_forward requires source_accession"
                )
            if self.source_age_days is None or self.source_age_days > 365:
                raise ValueError(
                    "annual_carried_forward requires source_age_days between 0 and 365"
                )

    def as_dict(self) -> dict[str, Any]:
        uncertainty = None
        if self.uncertainty is not None:
            uncertainty = {
                "low": self.uncertainty.low,
                "high": self.uncertainty.high,
                "basis": self.uncertainty.basis,
                "source_accessions": list(self.uncertainty.source_accessions),
            }
        return {
            "field": self.field,
            "value": self.value,
            "state": self.state,
            "reason_code": self.reason_code,
            "period_end": self.period_end,
            "source_accession": self.source_accession,
            "source_kind": self.source_kind,
            "evidence_class": self.evidence_class,
            "freshness": self.freshness,
            "fallback_level": self.fallback_level,
            "period_role": self.period_role,
            "source_age_days": self.source_age_days,
            "uncertainty": uncertainty,
            "covered_fields": list(self.covered_fields),
            "coverage_basis": self.coverage_basis,
            "coverage_source_facts": list(self.coverage_source_facts),
            "economic_scope": self.economic_scope,
            "extraction_complete": self.extraction_complete,
            "searched_concepts": list(self.searched_concepts),
            "authority": self.authority,
            "mapping_version": self.mapping_version,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> FieldAvailability:
        if not isinstance(value, Mapping):
            raise ValueError("field availability must be a mapping")

        raw_uncertainty = value.get("uncertainty")
        uncertainty = None
        if raw_uncertainty is not None:
            if not isinstance(raw_uncertainty, Mapping):
                raise ValueError("uncertainty must be a mapping or None")
            uncertainty = UncertaintyRange(
                low=raw_uncertainty["low"],
                high=raw_uncertainty["high"],
                basis=raw_uncertainty["basis"],
                source_accessions=_restore_string_tuple(
                    raw_uncertainty["source_accessions"],
                    "uncertainty.source_accessions",
                ),
            )

        fallback_level = value.get("fallback_level", "current_reported")
        if (
            fallback_level == "annual_carried_forward"
            and "authority" not in value
        ):
            raise ValueError(
                "annual_carried_forward requires explicit authority metadata"
            )

        return cls(
            field=value["field"],
            value=value["value"],
            state=value["state"],
            reason_code=value["reason_code"],
            period_end=value["period_end"],
            source_accession=value["source_accession"],
            source_kind=value.get("source_kind"),
            evidence_class=value.get("evidence_class"),
            freshness=value["freshness"],
            fallback_level=fallback_level,
            period_role=value.get("period_role", "balance_sheet_snapshot"),
            source_age_days=value.get("source_age_days"),
            uncertainty=uncertainty,
            covered_fields=_restore_string_tuple(
                value.get("covered_fields", []), "covered_fields"
            ),
            coverage_basis=value.get("coverage_basis"),
            coverage_source_facts=_restore_string_tuple(
                value.get("coverage_source_facts", []),
                "coverage_source_facts",
            ),
            economic_scope=value.get("economic_scope"),
            extraction_complete=value.get("extraction_complete", False),
            searched_concepts=_restore_string_tuple(
                value.get("searched_concepts", []), "searched_concepts"
            ),
            authority=value.get("authority", "production"),
            mapping_version=value.get(
                "mapping_version", "US-FIELD-AVAILABILITY-1.0"
            ),
        )


def _reason_token(value: str) -> str:
    normalized = "".join(
        character if character.isalnum() else "_" for character in value.upper()
    )
    return "_".join(part for part in normalized.split("_") if part)


def _nonempty_text_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _finite_float_or_none(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        normalized = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return normalized if isfinite(normalized) else None


def _structural_reason_code(
    decision: ResolutionDecision, *, accepted_is_valid: bool
) -> str:
    if decision.status == "accepted" and not accepted_is_valid:
        return "STRUCTURAL_SHADOW_INVALID_ACCEPTED_DECISION"

    status = (
        _reason_token(decision.status)
        if isinstance(decision.status, str)
        else "INVALID_STATUS"
    )
    reasons = decision.reason_codes
    reason_tokens = (
        tuple(_reason_token(reason) for reason in reasons)
        if isinstance(reasons, tuple)
        and all(isinstance(reason, str) and reason.strip() for reason in reasons)
        else ()
    )
    return "_".join(("STRUCTURAL", "SHADOW", status, *reason_tokens))


def _accepted_structural_value(decision: ResolutionDecision) -> float | None:
    if decision.status != "accepted":
        return None

    value = _finite_float_or_none(decision.value)
    required_text = (
        decision.normalized_concept,
        decision.period,
        decision.source_accession,
        decision.source_concept,
        decision.unit,
        decision.mapping_method,
        decision.form,
        decision.mapping_version,
    )
    if value is None or any(
        _nonempty_text_or_none(item) is None for item in required_text
    ):
        return None
    if not isinstance(decision.reason_codes, tuple) or not decision.reason_codes:
        return None
    if any(
        _nonempty_text_or_none(reason) is None for reason in decision.reason_codes
    ):
        return None

    confidence = _finite_float_or_none(decision.confidence)
    if confidence is None or not 0 <= confidence <= 1:
        return None
    evidence = decision.evidence
    if evidence is None:
        return None
    try:
        evidence.validate_complete()
        fact = evidence.fact
        evidence_value = _finite_float_or_none(fact.value)
    except (AttributeError, TypeError, ValueError):
        return None
    if evidence_value is None:
        return None
    if (
        fact.qname != decision.source_concept
        or evidence_value != value
        or fact.unit != decision.unit
        or fact.period_end != decision.period
        or fact.source_accession != decision.source_accession
        or fact.filing_form != decision.form
        or evidence.mapping_version != decision.mapping_version
        or evidence.confidence != decision.confidence
        or evidence.reason_codes != decision.reason_codes
    ):
        return None
    return value


def availability_from_resolution_decision(
    decision: ResolutionDecision,
) -> FieldAvailability:
    """Project a structural resolution into a non-authoritative diagnostic."""

    accepted_value = _accepted_structural_value(decision)
    accepted_is_valid = decision.status == "accepted" and accepted_value is not None
    source_accession = _nonempty_text_or_none(decision.source_accession)
    return FieldAvailability(
        field=(
            decision.normalized_concept
            if _nonempty_text_or_none(decision.normalized_concept) is not None
            else "unknown_structural_field"
        ),
        value=accepted_value if accepted_is_valid else None,
        state="reported" if accepted_is_valid else "unresolved",
        reason_code=_structural_reason_code(
            decision, accepted_is_valid=accepted_is_valid
        ),
        period_end=(
            decision.period
            if _nonempty_text_or_none(decision.period) is not None
            else ""
        ),
        source_accession=source_accession,
        source_kind="structural_xbrl",
        evidence_class=_nonempty_text_or_none(decision.mapping_method),
        freshness="current" if accepted_is_valid else "unknown",
        authority="shadow",
    )


def availability_from_normalized_field(
    *,
    field: str,
    value: float | None,
    source: Mapping[str, Any] | None,
    legacy_state: str,
    period_end: str,
    reference_date: str,
    covered_fields: tuple[str, ...] = (),
    period_role: PeriodRole = "balance_sheet_snapshot",
) -> FieldAvailability:
    """Project a legacy normalized field into its compatibility availability."""

    try:
        state = LEGACY_STATE_MAP[legacy_state]
    except KeyError as error:
        raise ValueError(f"unrecognized legacy field state: {legacy_state}") from error

    source_record = source or {}
    if state == "unresolved" and source_record.get("extraction_complete") is True:
        state = "not_disclosed"
    raw_evidence_class = source_record.get("evidence_class") or source_record.get(
        "value_status"
    )
    evidence_class = (
        str(raw_evidence_class) if raw_evidence_class is not None else None
    )
    if legacy_state == "governed_filing_fact" and value == 0:
        state = (
            "explicit_zero"
            if evidence_class == "reported_zero"
            else "evidence_backed_zero"
        )

    raw_accession = source_record.get("source_accession") or source_record.get(
        "accession"
    )
    source_accession = str(raw_accession) if raw_accession is not None else None
    raw_source_kind = source_record.get("source_kind")
    source_kind = str(raw_source_kind) if raw_source_kind is not None else None
    raw_fallback_level = source_record.get("fallback_level", "current_reported")
    if raw_fallback_level not in _FALLBACK_LEVELS:
        raise ValueError("source fallback_level is not recognized")
    fallback_level = raw_fallback_level
    source_covered_fields = source_record.get("covered_fields", ())
    normalized_covered_fields = (
        covered_fields
        if covered_fields
        else _restore_string_tuple(source_covered_fields, "covered_fields")
    )
    coverage_basis = source_record.get("coverage_basis")
    coverage_source_facts = _restore_string_tuple(
        source_record.get("coverage_source_facts", ()),
        "coverage_source_facts",
    )
    economic_scope = source_record.get("economic_scope")
    extraction_complete = source_record.get("extraction_complete", False)
    searched_concepts = _restore_string_tuple(
        source_record.get("searched_concepts", ()), "searched_concepts"
    )

    if legacy_state == "verification_stale":
        raw_value = _finite_float_or_none(source_record.get("value"))
        raw_end = source_record.get("end")
        raw_form = source_record.get("form")
        raw_authority = source_record.get("authority")
        raw_evidence_class = source_record.get("evidence_class")
        if (
            raw_value is not None
            and raw_value >= 0
            and isinstance(raw_end, str)
            and raw_form in {"10-K", "10-K/A"}
            and raw_source_kind == "companyfacts"
            and raw_authority == "production"
            and raw_evidence_class == "reported"
            and source_accession is not None
        ):
            try:
                source_age_days = (
                    date.fromisoformat(reference_date)
                    - date.fromisoformat(raw_end)
                ).days
            except (TypeError, ValueError):
                source_age_days = None
            if source_age_days is not None and 0 <= source_age_days <= 365:
                return FieldAvailability(
                    field=field,
                    value=raw_value,
                    state="reported",
                    reason_code="ANNUAL_COMPANY_FACT_CARRIED_FORWARD",
                    period_end=period_end,
                    source_accession=source_accession,
                    source_kind=source_kind,
                    evidence_class=evidence_class,
                    freshness="carried_forward",
                    fallback_level="annual_carried_forward",
                    period_role=period_role,
                    source_age_days=source_age_days,
                    covered_fields=normalized_covered_fields,
                    coverage_basis=coverage_basis,
                    coverage_source_facts=coverage_source_facts,
                    economic_scope=economic_scope,
                    extraction_complete=extraction_complete,
                    searched_concepts=searched_concepts,
                )

    freshness: Freshness = (
        "stale"
        if state == "stale"
        else "unknown"
        if state == "unresolved"
        else "current"
    )
    reason_code = (
        "NOT_DISCLOSED_COMPLETE_EXTRACTION"
        if state == "not_disclosed"
        else "_".join(
            (
                _reason_token(state),
                _reason_token(evidence_class or "unspecified"),
            )
        )
    )

    return FieldAvailability(
        field=field,
        value=value,
        state=state,
        reason_code=reason_code,
        period_end=period_end,
        source_accession=source_accession,
        source_kind=source_kind,
        evidence_class=evidence_class,
        freshness=freshness,
        fallback_level=fallback_level,
        period_role=period_role,
        covered_fields=normalized_covered_fields,
        coverage_basis=coverage_basis,
        coverage_source_facts=coverage_source_facts,
        economic_scope=economic_scope,
        extraction_complete=extraction_complete,
        searched_concepts=searched_concepts,
    )
