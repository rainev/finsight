"""Private contracts for bounded-uncertainty practical valuation policy.

This module deliberately does not select a valuation model or manufacture an
input.  It decides only whether caller-supplied, source-linked ranges are safe
to publish as a conservatively Low result, or must be withheld.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from numbers import Real
from typing import Literal, Sequence


Reliability = Literal["High", "Medium", "Low"]
PublicationState = Literal["pass", "review_required", "withheld"]
ReportedStatus = Literal["reported", "estimated"]
SourceKind = Literal["filing_evidence", "governed_policy"]

PRACTICAL_REASON_CODES = frozenset(
    {
        "CONSOLIDATED_MODEL_FALLBACK",
        "RD_LIFE_SENSITIVITY",
        "CAPEX_CASH_CONVERSION_SENSITIVITY",
        "NORMALIZED_CYCLICAL_RANGE",
        "PROVISIONAL_BANK_CAPITAL_RANGE",
        "CONSOLIDATED_MIXED_UTILITY_FALLBACK",
        "REPORTED_AFFO_FALLBACK",
        "SPECIALIST_MODEL_UNCERTAINTY",
    }
)

HARD_SAFETY_REASONS = frozenset(
    {
        "WRONG_IDENTITY",
        "SOURCE_UNRELIABLE",
        "PERIOD_INVALID",
        "UNIT_INVALID",
        "CURRENCY_INVALID",
        "SHARES_UNRELIABLE",
        "CONTRADICTORY_EVIDENCE",
        "MODEL_UNSUPPORTED",
        "CLAIMS_UNBOUNDED",
        "MAJOR_EVENT_UNBOUNDED",
        "PUBLIC_SAFETY_FAILURE",
        "NONFINITE_OR_NONPOSITIVE_VALUE",
    }
)
_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")


def _finite_positive(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite positive number")
    result = float(value)
    if result <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return result


def _finite_nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite nonnegative number")
    result = float(value)
    if result < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return result


@dataclass(frozen=True)
class ValueRange:
    """A strictly positive, ordered range; zero is never a missing-value proxy."""

    low: float
    base: float
    high: float

    def __post_init__(self) -> None:
        low = _finite_positive(self.low, "low")
        base = _finite_positive(self.base, "base")
        high = _finite_positive(self.high, "high")
        if not low <= base <= high:
            raise ValueError("range must satisfy low <= base <= high")
        object.__setattr__(self, "low", low)
        object.__setattr__(self, "base", base)
        object.__setattr__(self, "high", high)

    def as_dict(self) -> dict[str, float]:
        return {"low": self.low, "base": self.base, "high": self.high}


@dataclass(frozen=True)
class InputRange:
    """A nonnegative input range; an estimated base may never be silent zero."""

    low: float
    base: float
    high: float

    def __post_init__(self) -> None:
        low = _finite_nonnegative(self.low, "low")
        base = _finite_nonnegative(self.base, "base")
        high = _finite_nonnegative(self.high, "high")
        if not low <= base <= high:
            raise ValueError("input range must satisfy low <= base <= high")
        object.__setattr__(self, "low", low)
        object.__setattr__(self, "base", base)
        object.__setattr__(self, "high", high)

    def as_dict(self) -> dict[str, float]:
        return {"low": self.low, "base": self.base, "high": self.high}


@dataclass(frozen=True)
class SourceTrace:
    """Private filed-source lineage for a reported or estimated policy input."""

    source_kind: SourceKind
    accession: str | None
    policy_reference: str | None
    period_end: str
    unit: str
    reported_vs_estimated: ReportedStatus

    def __post_init__(self) -> None:
        if self.source_kind not in {"filing_evidence", "governed_policy"}:
            raise ValueError("source_kind is invalid")
        if self.source_kind == "filing_evidence":
            if not isinstance(self.accession, str) or not _ACCESSION.fullmatch(
                self.accession
            ):
                raise ValueError("filing evidence requires an SEC accession")
            if self.policy_reference is not None:
                raise ValueError("filing evidence cannot carry a policy reference")
        else:
            if self.accession is not None:
                raise ValueError("governed policy cannot claim a filing accession")
            if (
                not isinstance(self.policy_reference, str)
                or not self.policy_reference.strip()
            ):
                raise ValueError("governed policy requires a policy reference")
        if not isinstance(self.period_end, str) or not self.period_end.strip():
            raise ValueError("period_end must be nonempty")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValueError("unit must be nonempty")
        if self.reported_vs_estimated not in {"reported", "estimated"}:
            raise ValueError("reported_vs_estimated is invalid")


@dataclass(frozen=True)
class BoundedAssumption:
    """An explicit low/base/high assumption and its valuation impact."""

    name: str
    value_range: InputRange
    sources: tuple[SourceTrace, ...]
    fallback_level: str
    basis: str
    accounting_impact_ratio: float
    scenario_impact_ratio: float
    material_provisional: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("assumption name must be nonempty")
        if not self.sources:
            raise ValueError("assumption sources must not be empty")
        if not isinstance(self.value_range, InputRange):
            raise ValueError("assumption value_range must be an InputRange")
        if (
            self.value_range.base == 0
            and any(
                source.reported_vs_estimated == "estimated"
                for source in self.sources
            )
        ):
            raise ValueError("estimated assumption base cannot be zero")
        if not isinstance(self.fallback_level, str) or not self.fallback_level.strip():
            raise ValueError("fallback_level must be nonempty")
        if not isinstance(self.basis, str) or not self.basis.strip():
            raise ValueError("basis must be nonempty")
        _finite_nonnegative(self.accounting_impact_ratio, "accounting_impact_ratio")
        _finite_nonnegative(self.scenario_impact_ratio, "scenario_impact_ratio")
        if not isinstance(self.material_provisional, bool):
            raise ValueError("material_provisional must be boolean")


@dataclass(frozen=True)
class HardSafetyInput:
    """Facts which are never softened into an estimated valuation."""

    identity_valid: bool = True
    source_valid: bool = True
    period_valid: bool = True
    unit_valid: bool = True
    currency_valid: bool = True
    shares_reliable: bool = True
    evidence_consistent: bool = True
    model_supported: bool = True
    claims_bounded: bool = True
    major_event_bounded: bool = True
    public_safe: bool = True

    def reasons(self) -> tuple[str, ...]:
        checks = (
            (self.identity_valid, "WRONG_IDENTITY"),
            (self.source_valid, "SOURCE_UNRELIABLE"),
            (self.period_valid, "PERIOD_INVALID"),
            (self.unit_valid, "UNIT_INVALID"),
            (self.currency_valid, "CURRENCY_INVALID"),
            (self.shares_reliable, "SHARES_UNRELIABLE"),
            (self.evidence_consistent, "CONTRADICTORY_EVIDENCE"),
            (self.model_supported, "MODEL_UNSUPPORTED"),
            (self.claims_bounded, "CLAIMS_UNBOUNDED"),
            (self.major_event_bounded, "MAJOR_EVENT_UNBOUNDED"),
            (self.public_safe, "PUBLIC_SAFETY_FAILURE"),
        )
        if not all(isinstance(value, bool) for value, _ in checks):
            raise ValueError("hard safety flags must be boolean")
        return tuple(reason for valid, reason in checks if not valid)


@dataclass(frozen=True)
class PracticalOutcome:
    """Private outcome, including the information required for later audit."""

    publication_state: PublicationState
    value_range: ValueRange | None
    reliability: Reliability | None
    model_version: str
    model_selection_reason: str
    assumptions: tuple[BoundedAssumption, ...]
    reason_codes: tuple[str, ...]
    hard_block_reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.publication_state not in {"pass", "review_required", "withheld"}:
            raise ValueError("publication_state is invalid")
        if not isinstance(self.model_version, str) or not self.model_version.strip():
            raise ValueError("model_version must be nonempty")
        if not isinstance(self.model_selection_reason, str) or not self.model_selection_reason.strip():
            raise ValueError("model_selection_reason must be nonempty")
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not contain duplicates")
        if any(reason not in PRACTICAL_REASON_CODES for reason in self.reason_codes):
            raise ValueError("reason_codes contains an unsupported practical reason")
        if any(reason not in HARD_SAFETY_REASONS for reason in self.hard_block_reasons):
            raise ValueError("hard_block_reasons contains an unsupported safety reason")
        if self.hard_block_reasons:
            if self.publication_state != "withheld" or self.value_range is not None or self.reliability is not None:
                raise ValueError("hard safety failure must be withheld without a value")
        elif self.value_range is None or self.reliability is None:
            raise ValueError("non-withheld outcome requires a value range and reliability")
        elif self.publication_state == "withheld":
            raise ValueError("withheld outcome cannot expose a value range")
        elif self.reliability not in {"High", "Medium", "Low"}:
            raise ValueError("reliability is invalid")
        elif any(item.material_provisional for item in self.assumptions) and self.reliability != "Low":
            raise ValueError("material provisional assumptions require Low reliability")

    @property
    def is_numeric(self) -> bool:
        return self.value_range is not None


def decide_practical_outcome(
    *,
    value_range: ValueRange | Sequence[object] | None,
    model_version: str,
    model_selection_reason: str,
    assumptions: Sequence[BoundedAssumption],
    reason_codes: Sequence[str],
    safety: HardSafetyInput,
    reliability: Reliability = "Low",
) -> PracticalOutcome:
    """Return Low bounded result or a hard-withheld private outcome.

    Callers must pass ``None`` for unavailable values.  This function never
    changes that absence to zero and treats a missing/nonpositive range as a
    safety failure.
    """

    hard_reasons = safety.reasons()
    assumptions_tuple = tuple(assumptions)
    reason_codes_tuple = tuple(reason_codes)
    normalized_range: ValueRange | None
    if isinstance(value_range, ValueRange):
        normalized_range = value_range
    elif value_range is None:
        normalized_range = None
    else:
        try:
            low, base, high = value_range
            normalized_range = ValueRange(low, base, high)
        except (TypeError, ValueError):
            normalized_range = None
    if normalized_range is None:
        hard_reasons = (*hard_reasons, "NONFINITE_OR_NONPOSITIVE_VALUE")
    if hard_reasons:
        return PracticalOutcome(
            publication_state="withheld",
            value_range=None,
            reliability=None,
            model_version=model_version,
            model_selection_reason=model_selection_reason,
            assumptions=assumptions_tuple,
            reason_codes=reason_codes_tuple,
            hard_block_reasons=tuple(dict.fromkeys(hard_reasons)),
        )
    return PracticalOutcome(
        publication_state="review_required",
        value_range=normalized_range,
        reliability=reliability,
        model_version=model_version,
        model_selection_reason=model_selection_reason,
        assumptions=assumptions_tuple,
        reason_codes=reason_codes_tuple,
        hard_block_reasons=(),
    )
