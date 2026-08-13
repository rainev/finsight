"""Immutable field-availability and uncertainty records for valuation bridges."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Any, Literal, Mapping, get_args


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
Freshness = Literal["current", "stale", "unknown"]


_AVAILABILITY_STATES = frozenset(get_args(AvailabilityState))
_AVAILABILITY_AUTHORITIES = frozenset(get_args(AvailabilityAuthority))
_FRESHNESS_STATES = frozenset(get_args(Freshness))
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
    uncertainty: UncertaintyRange | None = None
    covered_fields: tuple[str, ...] = ()
    authority: AvailabilityAuthority = "production"
    mapping_version: str = "US-FIELD-AVAILABILITY-1.0"

    def __post_init__(self) -> None:
        if self.state not in _AVAILABILITY_STATES:
            raise ValueError("state must be a recognized availability state")
        if self.authority not in _AVAILABILITY_AUTHORITIES:
            raise ValueError("authority must be production or shadow")
        if self.freshness not in _FRESHNESS_STATES:
            raise ValueError("freshness must be current, stale, or unknown")

        if self.value is not None:
            _require_finite_number(self.value, "value")
        if self.uncertainty is not None and not isinstance(
            self.uncertainty, UncertaintyRange
        ):
            raise ValueError("uncertainty must be an UncertaintyRange or None")
        if self.source_accession is not None:
            _require_nonempty_text(self.source_accession, "source_accession")

        covered_fields = _require_string_tuple(self.covered_fields, "covered_fields")
        object.__setattr__(self, "covered_fields", tuple(sorted(set(covered_fields))))

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
            if self.freshness != "current":
                raise ValueError("bounded_unresolved requires current freshness")
            if self.uncertainty is None:
                raise ValueError("bounded_unresolved requires uncertainty")
        elif self.state in _NONPOINT_STATES:
            if self.value is not None:
                raise ValueError(f"{self.state} requires value is None")
            if self.uncertainty is not None:
                raise ValueError(f"{self.state} requires uncertainty is None")

        if self.state == "stale" and self.freshness != "stale":
            raise ValueError("stale requires stale freshness")

        if (
            self.authority == "production"
            and self.state in _PRODUCTION_SOURCE_STATES
            and self.source_accession is None
        ):
            raise ValueError(
                f"production {self.state} requires source_accession"
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
            "uncertainty": uncertainty,
            "covered_fields": list(self.covered_fields),
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

        return cls(
            field=value["field"],
            value=value["value"],
            state=value["state"],
            reason_code=value["reason_code"],
            period_end=value["period_end"],
            source_accession=value["source_accession"],
            source_kind=value["source_kind"],
            evidence_class=value["evidence_class"],
            freshness=value["freshness"],
            uncertainty=uncertainty,
            covered_fields=_restore_string_tuple(
                value.get("covered_fields", []), "covered_fields"
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


def availability_from_normalized_field(
    *,
    field: str,
    value: float | None,
    source: Mapping[str, Any] | None,
    legacy_state: str,
    period_end: str,
    covered_fields: tuple[str, ...] = (),
) -> FieldAvailability:
    """Project a legacy normalized field into its compatibility availability."""

    try:
        state = LEGACY_STATE_MAP[legacy_state]
    except KeyError as error:
        raise ValueError(f"unrecognized legacy field state: {legacy_state}") from error

    source_record = source or {}
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
    freshness: Freshness = (
        "stale"
        if state == "stale"
        else "unknown"
        if state == "unresolved"
        else "current"
    )
    reason_code = "_".join(
        (
            _reason_token(state),
            _reason_token(evidence_class or "unspecified"),
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
        covered_fields=covered_fields,
    )
