"""Pure evidence-aware policy for the enterprise-to-equity bridge."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from numbers import Real
from typing import Any, Literal, Mapping

from .field_availability import FieldAvailability
from .reliability import ReliabilityLabel, accounting_label


POLICY_VERSION = "US-BRIDGE-POLICY-1.0"
_MAX_SPREAD_LIMIT = 0.01
_SPREAD_BOUNDARY_RELATIVE_TOLERANCE = 1e-14
_BASE_ENTERPRISE_VALUE_UNAVAILABLE = "BASE_ENTERPRISE_VALUE_UNAVAILABLE"
_NONFINITE_INTRINSIC_VALUE_RESULT = "NONFINITE_INTRINSIC_VALUE_RESULT"
_NONPOSITIVE_INTRINSIC_VALUE_MIDPOINT = (
    "NONPOSITIVE_INTRINSIC_VALUE_MIDPOINT"
)

_ACCOUNT_POINT_STATES = frozenset(
    {"reported", "explicit_zero", "evidence_backed_zero"}
)
_CLAIM_POINT_STATES = _ACCOUNT_POINT_STATES | {"not_applicable"}
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


def _bridge_adjustment_range(
    cash_and_investments: BridgeRange,
    total_debt: BridgeRange,
    preferred_equity: BridgeRange,
    noncontrolling_interests: BridgeRange,
) -> BridgeRange:
    return BridgeRange(
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

        expected_adjustment = _bridge_adjustment_range(
            self.cash_and_investments,
            self.total_debt,
            self.preferred_equity,
            self.noncontrolling_interests,
        )
        if self.bridge_adjustment != expected_adjustment:
            raise ValueError(
                "bridge_adjustment must equal cash_and_investments minus "
                "total_debt, preferred_equity, and noncontrolling_interests"
            )

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


def _bounded_review_warning(spread_ratio: float) -> str:
    return (
        "Enterprise-to-equity bridge uses source-bounded uncertainty; "
        f"the joint intrinsic-value spread is {spread_ratio * 100:.2f}% "
        "and requires review."
    )


def _require_spread_limit(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError("spread_limit must be a finite float or int")
    try:
        normalized = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError("spread_limit must be a finite float or int") from error
    if not isfinite(normalized):
        raise ValueError("spread_limit must be a finite float or int")
    if normalized <= 0 or normalized > _MAX_SPREAD_LIMIT:
        raise ValueError(
            "spread_limit must be positive and no greater than 0.01"
        )
    return normalized


def _spread_is_within_limit(spread_ratio: float, spread_limit: float) -> bool:
    return spread_ratio <= spread_limit or isclose(
        spread_ratio,
        spread_limit,
        rel_tol=_SPREAD_BOUNDARY_RELATIVE_TOLERANCE,
        abs_tol=0.0,
    )


@dataclass(frozen=True)
class BridgeAssessment:
    decision: Literal["complete", "bounded_review", "withheld"]
    usable: bool
    intrinsic_value_range: BridgeRange | None
    spread_ratio: float | None
    spread_limit: float
    accounting_impact_ratio: float | None
    reliability_cap: ReliabilityLabel
    blocking_fields: tuple[str, ...]
    bounded_fields: tuple[str, ...]
    reason_codes: tuple[str, ...]
    warning: str | None
    policy_version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        if self.decision not in {"complete", "bounded_review", "withheld"}:
            raise ValueError("decision must be complete, bounded_review, or withheld")
        if not isinstance(self.usable, bool):
            raise ValueError("usable must be a boolean")

        blocking_fields = _require_string_tuple(
            self.blocking_fields, "blocking_fields"
        )
        bounded_fields = _require_string_tuple(
            self.bounded_fields, "bounded_fields"
        )
        reason_codes = _require_string_tuple(self.reason_codes, "reason_codes")
        object.__setattr__(self, "blocking_fields", blocking_fields)
        object.__setattr__(self, "bounded_fields", bounded_fields)
        object.__setattr__(self, "reason_codes", reason_codes)

        if self.intrinsic_value_range is not None and not isinstance(
            self.intrinsic_value_range, BridgeRange
        ):
            raise ValueError(
                "intrinsic_value_range must be a BridgeRange or None"
            )
        if self.spread_ratio is not None:
            _require_finite_number(self.spread_ratio, "spread_ratio")
            if self.spread_ratio < 0:
                raise ValueError("spread_ratio must be nonnegative")
        if self.accounting_impact_ratio is not None:
            _require_finite_number(
                self.accounting_impact_ratio,
                "accounting_impact_ratio",
            )
            if self.accounting_impact_ratio < 0:
                raise ValueError("accounting_impact_ratio must be nonnegative")
        if self.reliability_cap not in {"High", "Medium", "Low"}:
            raise ValueError("reliability_cap must be High, Medium, or Low")
        spread_limit = _require_spread_limit(self.spread_limit)
        object.__setattr__(self, "spread_limit", spread_limit)
        if self.warning is not None and (
            not isinstance(self.warning, str) or not self.warning.strip()
        ):
            raise ValueError("warning must be nonempty or None")
        if not isinstance(self.policy_version, str) or not self.policy_version.strip():
            raise ValueError("policy_version must be nonempty")

        value_range = self.intrinsic_value_range
        expected_spread: float | None = None
        expected_accounting_impact: float | None = None
        if value_range is not None:
            expected_midpoint = (value_range.low + value_range.high) / 2
            if (
                not isfinite(expected_midpoint)
                or value_range.midpoint != expected_midpoint
            ):
                raise ValueError(
                    "intrinsic_value_range midpoint must equal (low + high) / 2"
                )
            if value_range.low == value_range.high and (
                value_range.midpoint > 0 or self.decision == "complete"
            ):
                expected_spread = 0.0
            elif value_range.midpoint > 0:
                candidate_spread = (
                    value_range.high - value_range.low
                ) / value_range.midpoint
                if isfinite(candidate_spread):
                    expected_spread = candidate_spread
            if value_range.midpoint > 0:
                candidate_impact = max(
                    abs(value_range.low - value_range.midpoint),
                    abs(value_range.high - value_range.midpoint),
                ) / abs(value_range.midpoint)
                if isfinite(candidate_impact):
                    expected_accounting_impact = candidate_impact

        complete_without_value = (
            self.decision == "complete"
            and value_range is None
            and self.spread_ratio == 0.0
        )
        if (
            self.spread_ratio is not None
            and self.spread_ratio != expected_spread
            and not complete_without_value
        ):
            raise ValueError(
                "spread_ratio must match the intrinsic_value_range arithmetic"
            )
        if expected_spread is not None and self.spread_ratio is None:
            raise ValueError(
                "spread_ratio is required when intrinsic_value_range has a "
                "finite positive computable spread"
            )
        if self.accounting_impact_ratio != expected_accounting_impact and not (
            self.decision == "complete"
            and self.accounting_impact_ratio == 0.0
        ):
            raise ValueError(
                "accounting_impact_ratio must match the "
                "intrinsic_value_range arithmetic"
            )

        if self.decision == "complete":
            if not self.usable or blocking_fields or bounded_fields:
                raise ValueError(
                    "complete must be usable with no blocking or bounded fields"
                )
            if self.spread_ratio != 0.0:
                raise ValueError("complete must have a zero spread_ratio")
            if self.accounting_impact_ratio != 0.0:
                raise ValueError(
                    "complete must have a zero accounting_impact_ratio"
                )
            if self.reliability_cap != "High":
                raise ValueError("complete must have High reliability_cap")
            if value_range is not None and value_range.low != value_range.high:
                raise ValueError("complete must have a point intrinsic-value range")
            if self.warning is not None:
                raise ValueError("complete must not have a warning")
            return

        if self.decision == "bounded_review":
            if (
                not self.usable
                or blocking_fields
                or not bounded_fields
                or value_range is None
                or self.spread_ratio is None
                or self.accounting_impact_ratio is None
                or value_range.midpoint <= 0
            ):
                raise ValueError(
                    "bounded_review requires a usable, finite positive "
                    "bounded range with no blockers"
                )
            if self.reliability_cap != accounting_label(
                self.accounting_impact_ratio
            ):
                raise ValueError(
                    "reliability_cap must match accounting_impact_ratio"
                )
            if self.warning != _bounded_review_warning(self.spread_ratio):
                raise ValueError("bounded_review warning does not match spread_ratio")
            return

        if self.usable:
            raise ValueError("withheld must not be usable")
        if not blocking_fields and not bounded_fields:
            raise ValueError("withheld requires blocking or bounded fields")
        if self.warning is not None:
            raise ValueError("withheld must not have a warning")
        if value_range is not None:
            if (
                blocking_fields
                or value_range.midpoint <= 0
                or self.spread_ratio is None
                or self.accounting_impact_ratio is None
                or _spread_is_within_limit(
                    self.spread_ratio,
                    self.spread_limit,
                )
                or self.reliability_cap
                != accounting_label(self.accounting_impact_ratio)
            ):
                raise ValueError(
                    "legacy withheld ranges require a finite positive "
                    "over-limit bounded assessment"
                )
            return
        if (
            self.spread_ratio is not None
            or self.accounting_impact_ratio is not None
        ):
            raise ValueError("withheld assessments without ranges need null metrics")
        if self.reliability_cap != "Low":
            raise ValueError(
                "withheld assessments without ranges need Low reliability_cap"
            )
        if not blocking_fields and not (
            {
                _BASE_ENTERPRISE_VALUE_UNAVAILABLE,
                _NONFINITE_INTRINSIC_VALUE_RESULT,
                _NONPOSITIVE_INTRINSIC_VALUE_MIDPOINT,
            }
            & set(reason_codes)
        ):
            raise ValueError(
                "withheld bounded assessments require a source or value blocker"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "usable": self.usable,
            "intrinsic_value_range": (
                self.intrinsic_value_range.as_dict()
                if self.intrinsic_value_range is not None
                else None
            ),
            "spread_ratio": self.spread_ratio,
            "spread_limit": self.spread_limit,
            "accounting_impact_ratio": self.accounting_impact_ratio,
            "reliability_cap": self.reliability_cap,
            "blocking_fields": list(self.blocking_fields),
            "bounded_fields": list(self.bounded_fields),
            "reason_codes": list(self.reason_codes),
            "warning": self.warning,
            "policy_version": self.policy_version,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> BridgeAssessment:
        if not isinstance(value, Mapping):
            raise ValueError("bridge assessment must be a mapping")
        raw_range = value["intrinsic_value_range"]
        intrinsic_value_range = (
            None if raw_range is None else BridgeRange.from_dict(raw_range)
        )
        accounting_impact_ratio = value.get("accounting_impact_ratio")
        reliability_cap = value.get("reliability_cap")
        if "accounting_impact_ratio" not in value:
            if (
                intrinsic_value_range is not None
                and intrinsic_value_range.midpoint != 0
            ):
                accounting_impact_ratio = max(
                    abs(
                        intrinsic_value_range.low
                        - intrinsic_value_range.midpoint
                    ),
                    abs(
                        intrinsic_value_range.high
                        - intrinsic_value_range.midpoint
                    ),
                ) / abs(intrinsic_value_range.midpoint)
            elif value["decision"] == "complete":
                accounting_impact_ratio = 0.0
        if "reliability_cap" not in value:
            reliability_cap = (
                accounting_label(accounting_impact_ratio)
                if accounting_impact_ratio is not None
                else "Low"
            )
        return cls(
            decision=value["decision"],
            usable=value["usable"],
            intrinsic_value_range=intrinsic_value_range,
            spread_ratio=value["spread_ratio"],
            spread_limit=value["spread_limit"],
            accounting_impact_ratio=accounting_impact_ratio,
            reliability_cap=reliability_cap,
            blocking_fields=_restore_string_tuple(
                value["blocking_fields"], "blocking_fields"
            ),
            bounded_fields=_restore_string_tuple(
                value["bounded_fields"], "bounded_fields"
            ),
            reason_codes=_restore_string_tuple(
                value["reason_codes"], "reason_codes"
            ),
            warning=value["warning"],
            policy_version=value.get("policy_version", POLICY_VERSION),
        )


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


def _is_nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _source_metadata_is_complete(
    record: FieldAvailability,
    *,
    require_extended_source: bool,
) -> bool:
    if not _is_nonempty_text(record.source_accession):
        return False
    if not require_extended_source:
        return True
    return _is_nonempty_text(record.source_kind) and _is_nonempty_text(
        record.evidence_class
    )


def _record_range(record: FieldAvailability) -> BridgeRange:
    if record.state == "bounded_unresolved":
        assert record.uncertainty is not None
        return BridgeRange(
            low=record.uncertainty.low,
            midpoint=(record.uncertainty.low + record.uncertainty.high) / 2,
            high=record.uncertainty.high,
        )
    assert record.value is not None
    return BridgeRange(
        low=record.value,
        midpoint=record.value,
        high=record.value,
    )


def _record_unusable_reason(
    record: object,
    *,
    field: str,
    allowed_point_states: frozenset[str],
    allow_bounded: bool,
    require_extended_source: bool,
) -> str | None:
    if not isinstance(record, FieldAvailability):
        return "BRIDGE_FIELD_MISSING_OR_INVALID"
    if record.field != field:
        return "BRIDGE_FIELD_IDENTITY_MISMATCH"
    if record.freshness == "carried_forward" or record.fallback_level == (
        "annual_carried_forward"
    ):
        try:
            FieldAvailability.from_dict(record.as_dict())
        except (AttributeError, KeyError, TypeError, ValueError):
            return "BRIDGE_EVIDENCE_INVALID_CONTRACT"
    if record.state not in allowed_point_states and not (
        allow_bounded and record.state == "bounded_unresolved"
    ):
        return record.reason_code or "BRIDGE_EVIDENCE_UNUSABLE"
    if record.authority != "production":
        return "BRIDGE_EVIDENCE_NOT_PRODUCTION"
    if record.freshness not in {"current", "carried_forward"}:
        return "BRIDGE_EVIDENCE_NOT_CURRENT"
    if not _source_metadata_is_complete(
        record,
        require_extended_source=require_extended_source,
    ):
        return "BRIDGE_EVIDENCE_SOURCE_INCOMPLETE"
    return None


def _resolve_record(
    record: object,
    *,
    field: str,
    allowed_point_states: frozenset[str],
    allow_bounded: bool,
    context: _ResolutionContext,
    mark_bounded: bool = True,
    require_extended_source: bool = False,
) -> _ResolvedValue | None:
    unusable_reason = _record_unusable_reason(
        record,
        field=field,
        allowed_point_states=allowed_point_states,
        allow_bounded=allow_bounded,
        require_extended_source=require_extended_source,
    )
    if unusable_reason is not None:
        context.block(field, unusable_reason)
        return None

    assert isinstance(record, FieldAvailability)
    is_bounded = record.state == "bounded_unresolved"
    if is_bounded and mark_bounded:
        context.bound(field, record.reason_code)
    return _ResolvedValue(value_range=_record_range(record), bounded=is_bounded)


def _resolve_required(
    availability: Mapping[str, FieldAvailability],
    field: str,
    *,
    allowed_point_states: frozenset[str],
    allow_bounded: bool,
    context: _ResolutionContext,
) -> BridgeRange:
    resolved = _resolve_record(
        availability.get(field),
        field=field,
        allowed_point_states=allowed_point_states,
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
    require_extended_source: bool = False,
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
        allowed_point_states=_ACCOUNT_POINT_STATES,
        allow_bounded=True,
        context=context,
        mark_bounded=False,
        require_extended_source=require_extended_source,
    )
    if resolved is None:
        return None
    if frozenset(raw_record.covered_fields) != required_coverage:
        context.block(field, incomplete_coverage_reason)
        return None
    for covered_field in required_coverage:
        covered_record = availability.get(covered_field)
        if (
            isinstance(covered_record, FieldAvailability)
            and covered_record.state == "conflict"
        ):
            context.block(
                covered_field,
                covered_record.reason_code or "BRIDGE_EVIDENCE_CONFLICT",
            )
    return _AggregateCandidate(
        record=raw_record,
        value_range=resolved.value_range,
        bounded=resolved.bounded,
    )


def _record_range_if_usable(
    availability: Mapping[str, FieldAvailability],
    field: str,
    *,
    allowed_point_states: frozenset[str],
    allow_bounded: bool,
) -> BridgeRange | None:
    record = availability.get(field)
    if _record_unusable_reason(
        record,
        field=field,
        allowed_point_states=allowed_point_states,
        allow_bounded=allow_bounded,
        require_extended_source=False,
    ) is not None:
        return None
    assert isinstance(record, FieldAvailability)
    return _record_range(record)


def _point_value_if_usable(
    availability: Mapping[str, FieldAvailability],
    field: str,
) -> float | None:
    value_range = _record_range_if_usable(
        availability,
        field,
        allowed_point_states=_ACCOUNT_POINT_STATES,
        allow_bounded=False,
    )
    return value_range.midpoint if value_range is not None else None


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
    split_values: list[float] = []
    for field in ("finance_lease_current", "finance_lease_noncurrent"):
        split_range = _record_range_if_usable(
            availability,
            field,
            allowed_point_states=_ACCOUNT_POINT_STATES,
            allow_bounded=True,
        )
        if split_range is None:
            continue
        if split_range.low > candidate.value_range.high + _tolerance(
            split_range.low, candidate.value_range.high
        ):
            context.block(
                "finance_lease_total", "FINANCE_LEASE_AGGREGATE_CONFLICT"
            )
        split_record = availability[field]
        if split_record.state in _ACCOUNT_POINT_STATES:
            split_values.append(split_range.midpoint)

    if len(split_values) == 2:
        if not _point_matches_range(sum(split_values), candidate.value_range):
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
        require_extended_source=True,
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
            allowed_point_states=_ACCOUNT_POINT_STATES,
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
                allowed_point_states=_ACCOUNT_POINT_STATES,
                allow_bounded=True,
                context=context,
            ),
            _resolve_required(
                availability,
                "finance_lease_noncurrent",
                allowed_point_states=_ACCOUNT_POINT_STATES,
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
            allowed_point_states=_ACCOUNT_POINT_STATES,
            allow_bounded=False,
            context=context,
        ),
        _resolve_required(
            availability,
            "marketable_securities_current",
            allowed_point_states=_ACCOUNT_POINT_STATES,
            allow_bounded=True,
            context=context,
        ),
        _resolve_required(
            availability,
            "marketable_securities_noncurrent",
            allowed_point_states=_ACCOUNT_POINT_STATES,
            allow_bounded=True,
            context=context,
        ),
    )
    total_debt = _resolve_total_debt(availability, context)
    preferred_equity = _resolve_required(
        availability,
        "preferred_equity",
        allowed_point_states=_CLAIM_POINT_STATES,
        allow_bounded=True,
        context=context,
    )
    noncontrolling_interests = _resolve_required(
        availability,
        "noncontrolling_interests",
        allowed_point_states=_CLAIM_POINT_STATES,
        allow_bounded=True,
        context=context,
    )

    bridge_adjustment = _bridge_adjustment_range(
        cash_and_investments,
        total_debt,
        preferred_equity,
        noncontrolling_interests,
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


def assess_bridge_materiality(
    resolution: BridgeResolution,
    enterprise_value: float | None,
    spread_limit: float = _MAX_SPREAD_LIMIT,
) -> BridgeAssessment:
    """Assess joint per-share bridge uncertainty against the global ceiling."""

    if not isinstance(resolution, BridgeResolution):
        raise ValueError("resolution must be a BridgeResolution")
    spread_limit = _require_spread_limit(spread_limit)

    common = {
        "spread_limit": spread_limit,
        "blocking_fields": resolution.blocking_fields,
        "bounded_fields": resolution.bounded_fields,
        "policy_version": resolution.policy_version,
    }
    if resolution.blocking_fields:
        return BridgeAssessment(
            decision="withheld",
            usable=False,
            intrinsic_value_range=None,
            spread_ratio=None,
            accounting_impact_ratio=None,
            reliability_cap="Low",
            reason_codes=resolution.reason_codes,
            warning=None,
            **common,
        )

    try:
        _require_finite_number(enterprise_value, "enterprise_value")
        finite_enterprise_value = True
    except ValueError:
        finite_enterprise_value = False

    if not resolution.bounded_fields:
        intrinsic_value_range = None
        if finite_enterprise_value:
            shares = resolution.fully_diluted_shares
            low = (enterprise_value + resolution.bridge_adjustment.low) / shares
            high = (enterprise_value + resolution.bridge_adjustment.high) / shares
            midpoint = (low + high) / 2
            if all(isfinite(value) for value in (low, high, midpoint)):
                intrinsic_value_range = BridgeRange(
                    low=low,
                    midpoint=midpoint,
                    high=high,
                )
        return BridgeAssessment(
            decision="complete",
            usable=True,
            intrinsic_value_range=intrinsic_value_range,
            spread_ratio=0.0,
            accounting_impact_ratio=0.0,
            reliability_cap="High",
            reason_codes=resolution.reason_codes,
            warning=None,
            **common,
        )

    if not finite_enterprise_value:
        return BridgeAssessment(
            decision="withheld",
            usable=False,
            intrinsic_value_range=None,
            spread_ratio=None,
            accounting_impact_ratio=None,
            reliability_cap="Low",
            reason_codes=tuple(
                sorted(
                    {*resolution.reason_codes, _BASE_ENTERPRISE_VALUE_UNAVAILABLE}
                )
            ),
            warning=None,
            **common,
        )

    shares = resolution.fully_diluted_shares
    low = (enterprise_value + resolution.bridge_adjustment.low) / shares
    high = (enterprise_value + resolution.bridge_adjustment.high) / shares
    midpoint = (low + high) / 2
    if not all(isfinite(value) for value in (low, high, midpoint)):
        return BridgeAssessment(
            decision="withheld",
            usable=False,
            intrinsic_value_range=None,
            spread_ratio=None,
            accounting_impact_ratio=None,
            reliability_cap="Low",
            reason_codes=tuple(
                sorted(
                    {*resolution.reason_codes, _NONFINITE_INTRINSIC_VALUE_RESULT}
                )
            ),
            warning=None,
            **common,
        )

    intrinsic_value_range = BridgeRange(
        low=low,
        midpoint=midpoint,
        high=high,
    )
    if midpoint <= 0:
        return BridgeAssessment(
            decision="withheld",
            usable=False,
            intrinsic_value_range=None,
            spread_ratio=None,
            accounting_impact_ratio=None,
            reliability_cap="Low",
            reason_codes=tuple(
                sorted(
                    {
                        *resolution.reason_codes,
                        _NONPOSITIVE_INTRINSIC_VALUE_MIDPOINT,
                    }
                )
            ),
            warning=None,
            **common,
        )

    spread_ratio = (high - low) / midpoint
    if not isfinite(spread_ratio):
        return BridgeAssessment(
            decision="withheld",
            usable=False,
            intrinsic_value_range=None,
            spread_ratio=None,
            accounting_impact_ratio=None,
            reliability_cap="Low",
            reason_codes=tuple(
                sorted(
                    {*resolution.reason_codes, _NONFINITE_INTRINSIC_VALUE_RESULT}
                )
            ),
            warning=None,
            **common,
        )

    accounting_impact_ratio = max(
        abs(intrinsic_value_range.low - intrinsic_value_range.midpoint),
        abs(intrinsic_value_range.high - intrinsic_value_range.midpoint),
    ) / abs(intrinsic_value_range.midpoint)
    return BridgeAssessment(
        decision="bounded_review",
        usable=True,
        intrinsic_value_range=intrinsic_value_range,
        spread_ratio=spread_ratio,
        accounting_impact_ratio=accounting_impact_ratio,
        reliability_cap=accounting_label(accounting_impact_ratio),
        reason_codes=resolution.reason_codes,
        warning=_bounded_review_warning(spread_ratio),
        **common,
    )
