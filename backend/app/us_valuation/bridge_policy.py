"""Pure evidence-aware policy for the enterprise-to-equity bridge."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Any, Mapping

from .field_availability import FieldAvailability


POLICY_VERSION = "US-BRIDGE-POLICY-1.0"

_POINT_STATES = frozenset(
    {
        "reported",
        "explicit_zero",
        "evidence_backed_zero",
        "not_applicable",
        "proxy",
    }
)
_OPTIONAL_ABSENT_STATES = frozenset({"not_disclosed", "unresolved"})
_LEASE_COMPONENTS = frozenset(
    {"finance_lease_current", "finance_lease_noncurrent"}
)
_DEBT_COMPONENTS = frozenset(
    {
        "commercial_paper",
        "current_debt",
        "noncurrent_debt",
        "finance_lease_current",
        "finance_lease_noncurrent",
    }
)


def _require_finite_number(value: object, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field} must be a finite number")
    try:
        finite = isfinite(value)
    except (OverflowError, TypeError) as error:
        raise ValueError(f"{field} must be a finite number") from error
    if not finite:
        raise ValueError(f"{field} must be a finite number")


def _require_string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError(f"{field} must be a tuple of nonempty strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} must be a tuple of nonempty strings")
    return tuple(sorted(set(value)))


def _restore_string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be an array of nonempty strings")
    return _require_string_tuple(tuple(value), field)


@dataclass(frozen=True)
class BridgeRange:
    low: float
    midpoint: float
    high: float

    def __post_init__(self) -> None:
        _require_finite_number(self.low, "low")
        _require_finite_number(self.midpoint, "midpoint")
        _require_finite_number(self.high, "high")
        if not self.low <= self.midpoint <= self.high:
            raise ValueError("bridge range must satisfy low <= midpoint <= high")

    def as_dict(self) -> dict[str, float]:
        return {
            "low": self.low,
            "midpoint": self.midpoint,
            "high": self.high,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> BridgeRange:
        if not isinstance(value, Mapping):
            raise ValueError("bridge range must be a mapping")
        return cls(
            low=value["low"],
            midpoint=value["midpoint"],
            high=value["high"],
        )


@dataclass(frozen=True)
class BridgeResolution:
    complete: bool
    can_value: bool
    missing_fields: tuple[str, ...]
    blocking_fields: tuple[str, ...]
    bounded_fields: tuple[str, ...]
    cash_and_investments: BridgeRange
    total_debt: BridgeRange
    preferred_equity: BridgeRange
    noncontrolling_interests: BridgeRange
    bridge_adjustment: BridgeRange
    fully_diluted_shares: float
    reason_codes: tuple[str, ...]
    policy_version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.complete, bool) or not isinstance(self.can_value, bool):
            raise ValueError("complete and can_value must be booleans")

        missing_fields = _require_string_tuple(
            self.missing_fields, "missing_fields"
        )
        blocking_fields = _require_string_tuple(
            self.blocking_fields, "blocking_fields"
        )
        bounded_fields = _require_string_tuple(
            self.bounded_fields, "bounded_fields"
        )
        reason_codes = _require_string_tuple(self.reason_codes, "reason_codes")
        object.__setattr__(self, "missing_fields", missing_fields)
        object.__setattr__(self, "blocking_fields", blocking_fields)
        object.__setattr__(self, "bounded_fields", bounded_fields)
        object.__setattr__(self, "reason_codes", reason_codes)

        expected_missing = tuple(sorted(set(blocking_fields) | set(bounded_fields)))
        if missing_fields != expected_missing:
            raise ValueError(
                "missing_fields must equal the union of blocking_fields "
                "and bounded_fields"
            )
        if self.complete != (not blocking_fields and not bounded_fields):
            raise ValueError("complete must be true only when no fields are unresolved")
        if self.can_value != (not blocking_fields):
            raise ValueError("can_value must be true exactly when no blockers remain")

        for field in (
            "cash_and_investments",
            "total_debt",
            "preferred_equity",
            "noncontrolling_interests",
            "bridge_adjustment",
        ):
            if not isinstance(getattr(self, field), BridgeRange):
                raise ValueError(f"{field} must be a BridgeRange")

        _require_finite_number(self.fully_diluted_shares, "fully_diluted_shares")
        if self.fully_diluted_shares <= 0:
            raise ValueError("fully_diluted_shares must be positive")
        if not isinstance(self.policy_version, str) or not self.policy_version.strip():
            raise ValueError("policy_version must be nonempty")

    def as_dict(self) -> dict[str, Any]:
        return {
            "complete": self.complete,
            "can_value": self.can_value,
            "missing_fields": list(self.missing_fields),
            "blocking_fields": list(self.blocking_fields),
            "bounded_fields": list(self.bounded_fields),
            "cash_and_investments": self.cash_and_investments.as_dict(),
            "total_debt": self.total_debt.as_dict(),
            "preferred_equity": self.preferred_equity.as_dict(),
            "noncontrolling_interests": self.noncontrolling_interests.as_dict(),
            "bridge_adjustment": self.bridge_adjustment.as_dict(),
            "fully_diluted_shares": self.fully_diluted_shares,
            "reason_codes": list(self.reason_codes),
            "policy_version": self.policy_version,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> BridgeResolution:
        if not isinstance(value, Mapping):
            raise ValueError("bridge resolution must be a mapping")
        return cls(
            complete=value["complete"],
            can_value=value["can_value"],
            missing_fields=_restore_string_tuple(
                value["missing_fields"], "missing_fields"
            ),
            blocking_fields=_restore_string_tuple(
                value["blocking_fields"], "blocking_fields"
            ),
            bounded_fields=_restore_string_tuple(
                value["bounded_fields"], "bounded_fields"
            ),
            cash_and_investments=BridgeRange.from_dict(
                value["cash_and_investments"]
            ),
            total_debt=BridgeRange.from_dict(value["total_debt"]),
            preferred_equity=BridgeRange.from_dict(value["preferred_equity"]),
            noncontrolling_interests=BridgeRange.from_dict(
                value["noncontrolling_interests"]
            ),
            bridge_adjustment=BridgeRange.from_dict(value["bridge_adjustment"]),
            fully_diluted_shares=value["fully_diluted_shares"],
            reason_codes=_restore_string_tuple(
                value["reason_codes"], "reason_codes"
            ),
            policy_version=value.get("policy_version", POLICY_VERSION),
        )

    def as_balance_sheet_fields(self) -> dict[str, Any]:
        return {
            "bridge_complete": self.complete,
            "bridge_can_value": self.can_value,
            "bridge_usable": self.complete,
            "bridge_decision": "complete" if self.complete else "withheld",
            "bridge_missing_fields": list(self.missing_fields),
            "bridge_blocking_fields": list(self.blocking_fields),
            "bridge_bounded_fields": list(self.bounded_fields),
            "bridge_precheck": self.as_dict(),
            "cash_and_nonoperating_investments": (
                self.cash_and_investments.midpoint
            ),
            "total_interest_bearing_debt": self.total_debt.midpoint,
            "preferred_equity": self.preferred_equity.midpoint,
            "noncontrolling_interests": self.noncontrolling_interests.midpoint,
        }


@dataclass(frozen=True)
class _ResolvedValue:
    value_range: BridgeRange
    bounded: bool = False


@dataclass(frozen=True)
class _AggregateCandidate:
    record: FieldAvailability
    value_range: BridgeRange
    bounded: bool


class _ResolutionContext:
    def __init__(self) -> None:
        self.blocking_fields: set[str] = set()
        self.bounded_fields: set[str] = set()
        self.reason_codes: set[str] = set()

    def block(self, field: str, reason_code: str) -> None:
        self.blocking_fields.add(field)
        if reason_code:
            self.reason_codes.add(reason_code)

    def bound(self, field: str, reason_code: str) -> None:
        self.bounded_fields.add(field)
        if reason_code:
            self.reason_codes.add(reason_code)


_ZERO_RANGE = BridgeRange(low=0.0, midpoint=0.0, high=0.0)


def _source_metadata_is_complete(record: FieldAvailability) -> bool:
    return all(
        isinstance(value, str) and bool(value.strip())
        for value in (
            record.source_accession,
            record.source_kind,
            record.evidence_class,
        )
    )


def _record_range(record: FieldAvailability) -> BridgeRange:
    if record.state in _POINT_STATES:
        assert record.value is not None
        return BridgeRange(
            low=record.value,
            midpoint=record.value,
            high=record.value,
        )
    assert record.uncertainty is not None
    return BridgeRange(
        low=record.uncertainty.low,
        midpoint=(record.uncertainty.low + record.uncertainty.high) / 2,
        high=record.uncertainty.high,
    )


def _resolve_record(
    record: object,
    *,
    field: str,
    allow_bounded: bool,
    context: _ResolutionContext,
    mark_bounded: bool = True,
) -> _ResolvedValue | None:
    if not isinstance(record, FieldAvailability):
        context.block(field, "BRIDGE_FIELD_MISSING_OR_INVALID")
        return None
    if record.field != field:
        context.block(field, "BRIDGE_FIELD_IDENTITY_MISMATCH")
        return None
    if record.state not in _POINT_STATES and not (
        allow_bounded and record.state == "bounded_unresolved"
    ):
        context.block(field, record.reason_code or "BRIDGE_EVIDENCE_UNUSABLE")
        return None
    if record.authority != "production":
        context.block(field, "BRIDGE_EVIDENCE_NOT_PRODUCTION")
        return None
    if record.freshness != "current":
        context.block(field, "BRIDGE_EVIDENCE_NOT_CURRENT")
        return None
    if not _source_metadata_is_complete(record):
        context.block(field, "BRIDGE_EVIDENCE_SOURCE_INCOMPLETE")
        return None

    is_bounded = record.state == "bounded_unresolved"
    if is_bounded and mark_bounded:
        context.bound(field, record.reason_code)
    return _ResolvedValue(value_range=_record_range(record), bounded=is_bounded)


def _resolve_required(
    availability: Mapping[str, FieldAvailability],
    field: str,
    *,
    allow_bounded: bool,
    context: _ResolutionContext,
) -> BridgeRange:
    resolved = _resolve_record(
        availability.get(field),
        field=field,
        allow_bounded=allow_bounded,
        context=context,
    )
    return resolved.value_range if resolved is not None else _ZERO_RANGE


def _aggregate_candidate(
    availability: Mapping[str, FieldAvailability],
    field: str,
    *,
    required_coverage: frozenset[str],
    incomplete_coverage_reason: str,
    context: _ResolutionContext,
) -> _AggregateCandidate | None:
    raw_record = availability.get(field)
    if raw_record is None:
        return None
    if not isinstance(raw_record, FieldAvailability):
        context.block(field, "BRIDGE_FIELD_MISSING_OR_INVALID")
        return None
    if raw_record.field != field:
        context.block(field, "BRIDGE_FIELD_IDENTITY_MISMATCH")
        return None
    if raw_record.state in _OPTIONAL_ABSENT_STATES:
        return None

    resolved = _resolve_record(
        raw_record,
        field=field,
        allow_bounded=True,
        context=context,
        mark_bounded=False,
    )
    if resolved is None:
        return None
    if frozenset(raw_record.covered_fields) != required_coverage:
        context.block(field, incomplete_coverage_reason)
        return None
    return _AggregateCandidate(
        record=raw_record,
        value_range=resolved.value_range,
        bounded=resolved.bounded,
    )


def _point_value_if_usable(
    availability: Mapping[str, FieldAvailability],
    field: str,
) -> float | None:
    record = availability.get(field)
    if (
        not isinstance(record, FieldAvailability)
        or record.field != field
        or record.state not in _POINT_STATES
        or record.authority != "production"
        or record.freshness != "current"
        or not _source_metadata_is_complete(record)
    ):
        return None
    return record.value


def _tolerance(first: float, second: float) -> float:
    return max(1.0, 1e-9 * max(abs(first), abs(second)))


def _point_matches_range(point: float, value_range: BridgeRange) -> bool:
    return (
        point >= value_range.low - _tolerance(point, value_range.low)
        and point <= value_range.high + _tolerance(point, value_range.high)
    )


def _corroborate_lease_candidate(
    availability: Mapping[str, FieldAvailability],
    candidate: _AggregateCandidate,
    context: _ResolutionContext,
) -> None:
    split_values = tuple(
        value
        for field in ("finance_lease_current", "finance_lease_noncurrent")
        if (value := _point_value_if_usable(availability, field)) is not None
    )
    if len(split_values) == 2:
        if not _point_matches_range(sum(split_values), candidate.value_range):
            context.block(
                "finance_lease_total", "FINANCE_LEASE_AGGREGATE_CONFLICT"
            )
    elif len(split_values) == 1:
        known_split = split_values[0]
        if known_split > candidate.value_range.high + _tolerance(
            known_split, candidate.value_range.high
        ):
            context.block(
                "finance_lease_total", "FINANCE_LEASE_AGGREGATE_CONFLICT"
            )


def _complete_debt_detail_point(
    availability: Mapping[str, FieldAvailability],
    lease_candidate: _AggregateCandidate | None,
) -> float | None:
    ordinary_values = tuple(
        _point_value_if_usable(availability, field)
        for field in ("commercial_paper", "current_debt", "noncurrent_debt")
    )
    if any(value is None for value in ordinary_values):
        return None

    if lease_candidate is not None:
        if lease_candidate.bounded:
            return None
        lease_value = lease_candidate.value_range.midpoint
    else:
        lease_values = tuple(
            _point_value_if_usable(availability, field)
            for field in ("finance_lease_current", "finance_lease_noncurrent")
        )
        if any(value is None for value in lease_values):
            return None
        lease_value = sum(value for value in lease_values if value is not None)

    return sum(value for value in ordinary_values if value is not None) + lease_value


def _add_ranges(*ranges: BridgeRange) -> BridgeRange:
    return BridgeRange(
        low=sum(value.low for value in ranges),
        midpoint=sum(value.midpoint for value in ranges),
        high=sum(value.high for value in ranges),
    )


def _resolve_total_debt(
    availability: Mapping[str, FieldAvailability],
    context: _ResolutionContext,
) -> BridgeRange:
    lease_candidate = _aggregate_candidate(
        availability,
        "finance_lease_total",
        required_coverage=_LEASE_COMPONENTS,
        incomplete_coverage_reason="FINANCE_LEASE_AGGREGATE_INCOMPLETE_COVERAGE",
        context=context,
    )
    if lease_candidate is not None:
        _corroborate_lease_candidate(availability, lease_candidate, context)

    debt_candidate = _aggregate_candidate(
        availability,
        "total_interest_bearing_debt",
        required_coverage=_DEBT_COMPONENTS,
        incomplete_coverage_reason="TOTAL_DEBT_AGGREGATE_INCOMPLETE_COVERAGE",
        context=context,
    )
    if debt_candidate is not None:
        complete_detail = _complete_debt_detail_point(
            availability, lease_candidate
        )
        if complete_detail is not None and not _point_matches_range(
            complete_detail, debt_candidate.value_range
        ):
            context.block(
                "total_interest_bearing_debt", "TOTAL_DEBT_AGGREGATE_CONFLICT"
            )
        if debt_candidate.bounded:
            context.bound(
                "total_interest_bearing_debt", debt_candidate.record.reason_code
            )
        return debt_candidate.value_range

    ordinary_debt = tuple(
        _resolve_required(
            availability,
            field,
            allow_bounded=True,
            context=context,
        )
        for field in ("commercial_paper", "current_debt", "noncurrent_debt")
    )
    if lease_candidate is not None:
        if lease_candidate.bounded:
            context.bound("finance_lease_total", lease_candidate.record.reason_code)
        lease_range = lease_candidate.value_range
    else:
        lease_range = _add_ranges(
            _resolve_required(
                availability,
                "finance_lease_current",
                allow_bounded=True,
                context=context,
            ),
            _resolve_required(
                availability,
                "finance_lease_noncurrent",
                allow_bounded=True,
                context=context,
            ),
        )
    return _add_ranges(*ordinary_debt, lease_range)


def reconcile_bridge(
    availability: Mapping[str, FieldAvailability],
    fully_diluted_shares: float,
) -> BridgeResolution:
    """Reconcile non-overlapping bridge groups from source-linked evidence."""

    _require_finite_number(fully_diluted_shares, "fully_diluted_shares")
    if fully_diluted_shares <= 0:
        raise ValueError("fully_diluted_shares must be positive")
    if not isinstance(availability, Mapping):
        raise ValueError("availability must be a mapping")

    context = _ResolutionContext()
    cash_and_investments = _add_ranges(
        _resolve_required(
            availability,
            "cash",
            allow_bounded=False,
            context=context,
        ),
        _resolve_required(
            availability,
            "marketable_securities_current",
            allow_bounded=True,
            context=context,
        ),
        _resolve_required(
            availability,
            "marketable_securities_noncurrent",
            allow_bounded=True,
            context=context,
        ),
    )
    total_debt = _resolve_total_debt(availability, context)
    preferred_equity = _resolve_required(
        availability,
        "preferred_equity",
        allow_bounded=True,
        context=context,
    )
    noncontrolling_interests = _resolve_required(
        availability,
        "noncontrolling_interests",
        allow_bounded=True,
        context=context,
    )

    bridge_adjustment = BridgeRange(
        low=(
            cash_and_investments.low
            - total_debt.high
            - preferred_equity.high
            - noncontrolling_interests.high
        ),
        midpoint=(
            cash_and_investments.midpoint
            - total_debt.midpoint
            - preferred_equity.midpoint
            - noncontrolling_interests.midpoint
        ),
        high=(
            cash_and_investments.high
            - total_debt.low
            - preferred_equity.low
            - noncontrolling_interests.low
        ),
    )

    blocking_fields = tuple(sorted(context.blocking_fields))
    bounded_fields = tuple(sorted(context.bounded_fields))
    missing_fields = tuple(sorted(set(blocking_fields) | set(bounded_fields)))
    return BridgeResolution(
        complete=not blocking_fields and not bounded_fields,
        can_value=not blocking_fields,
        missing_fields=missing_fields,
        blocking_fields=blocking_fields,
        bounded_fields=bounded_fields,
        cash_and_investments=cash_and_investments,
        total_debt=total_debt,
        preferred_equity=preferred_equity,
        noncontrolling_interests=noncontrolling_interests,
        bridge_adjustment=bridge_adjustment,
        fully_diluted_shares=fully_diluted_shares,
        reason_codes=tuple(sorted(context.reason_codes)),
    )
