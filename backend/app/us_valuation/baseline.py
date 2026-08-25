"""Shared launch-first valuation result and ordered fallback policy.

The contract is deliberately model-agnostic. Existing engines build the numbers; this
module records which route produced them, why earlier routes were rejected, and which
retail availability label is honest.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from math import isfinite
from numbers import Real
import re
from typing import Any, Callable, Mapping, Sequence


class AvailabilityType(str, Enum):
    AVAILABLE = "available"
    CONDITIONAL = "conditional_estimate"
    RELATIVE = "relative_baseline"
    NOT_AVAILABLE = "not_available"


class FallbackStage(str, Enum):
    PRIMARY_INTRINSIC = "primary_intrinsic"
    CONSOLIDATED = "consolidated_fallback"
    NORMALIZED = "normalized_cash_flow_or_earnings"
    CONDITIONAL = "conditional_or_standalone"
    RELATIVE = "relative_value"


class AssumptionClassification(str, Enum):
    REPORTED = "reported"
    HISTORICALLY_DERIVED = "historically_derived"
    FINSIGHT_ASSUMPTION = "finsight_assumption"
    USER_OVERRIDE = "user_override"


class AttemptOutcome(str, Enum):
    SELECTED = "selected"
    REJECTED = "rejected"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class BaselineAssumption:
    name: str
    value: str | int | float | bool | None
    classification: AssumptionClassification
    basis: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.basis.strip():
            raise ValueError("baseline assumptions require a name and basis")
        if isinstance(self.value, float) and not isfinite(self.value):
            raise ValueError("baseline assumption values must be finite")


@dataclass(frozen=True)
class FallbackAttempt:
    stage: FallbackStage
    method: str
    outcome: AttemptOutcome
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.method.strip():
            raise ValueError("fallback attempt method is required")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("fallback attempt reasons must be nonempty")


@dataclass(frozen=True)
class BaselineValuation:
    ticker: str
    method: str
    method_version: str
    low: float | None
    base: float | None
    high: float | None
    confidence: str | None
    availability_type: AvailabilityType
    key_assumptions: tuple[BaselineAssumption, ...] = ()
    warnings: tuple[str, ...] = ()
    confidence_reasons: tuple[str, ...] = ()
    fallback_attempts: tuple[FallbackAttempt, ...] = ()
    calculator_link: str | None = None

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", self.ticker):
            raise ValueError("baseline ticker is invalid")
        if not self.method.strip() or not self.method_version.strip():
            raise ValueError("baseline method and version are required")
        if self.confidence not in {None, "High", "Medium", "Low"}:
            raise ValueError("baseline confidence is invalid")
        if any(not value.strip() for value in (*self.warnings, *self.confidence_reasons)):
            raise ValueError("baseline warnings and reasons must be nonempty")
        values = (self.low, self.base, self.high)
        if self.availability_type == AvailabilityType.NOT_AVAILABLE:
            if any(value is not None for value in values) or self.confidence is not None:
                raise ValueError("not-available baselines cannot carry values or confidence")
            return
        if any(
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
            for value in values
        ):
            raise ValueError("available baseline values must be finite")
        low, base, high = (float(value) for value in values)  # type: ignore[arg-type]
        allow_zero_floor = (
            self.availability_type == AvailabilityType.CONDITIONAL
            and low == 0
            and base == 0
            and high > 0
        )
        if not low <= base <= high or (base <= 0 and not allow_zero_floor):
            raise ValueError("baseline range must be ordered with a positive base")
        if self.confidence is None:
            raise ValueError("available baselines require confidence")

    def as_private_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["availability_type"] = self.availability_type.value
        for row in value["key_assumptions"]:
            row["classification"] = row["classification"].value
        for row in value["fallback_attempts"]:
            row["stage"] = row["stage"].value
            row["outcome"] = row["outcome"].value
        return value


class FallbackRejected(ValueError):
    """A model route is unsuitable, but later launch-first routes may be tried."""


FallbackBuilder = Callable[[], BaselineValuation | None]


def run_fallback_ladder(
    *,
    ticker: str,
    strategies: Sequence[tuple[FallbackStage, str, FallbackBuilder]],
    hard_failures: Sequence[str] = (),
) -> BaselineValuation:
    """Try governed strategies in order and retain an auditable decision trail."""

    normalized = ticker.strip().upper()
    if hard_failures:
        return BaselineValuation(
            ticker=normalized,
            method="unavailable",
            method_version="LAUNCH-FIRST-FALLBACK-1.0",
            low=None,
            base=None,
            high=None,
            confidence=None,
            availability_type=AvailabilityType.NOT_AVAILABLE,
            warnings=tuple(dict.fromkeys(str(reason) for reason in hard_failures)),
        )
    attempts: list[FallbackAttempt] = []
    for stage, method, builder in strategies:
        try:
            candidate = builder()
        except FallbackRejected as error:
            attempts.append(
                FallbackAttempt(stage, method, AttemptOutcome.REJECTED, (str(error),))
            )
            continue
        if candidate is None:
            attempts.append(
                FallbackAttempt(stage, method, AttemptOutcome.NOT_APPLICABLE)
            )
            continue
        if candidate.ticker != normalized or candidate.method != method:
            raise ValueError("fallback candidate identity or method mismatch")
        if candidate.availability_type == AvailabilityType.NOT_AVAILABLE:
            attempts.append(
                FallbackAttempt(
                    stage,
                    method,
                    AttemptOutcome.REJECTED,
                    candidate.warnings or ("route unavailable",),
                )
            )
            continue
        if stage == FallbackStage.CONDITIONAL and (
            candidate.availability_type != AvailabilityType.CONDITIONAL
        ):
            raise ValueError("conditional fallback must be labeled conditional")
        if stage == FallbackStage.RELATIVE and (
            candidate.availability_type != AvailabilityType.RELATIVE
        ):
            raise ValueError("relative fallback must be labeled relative")
        attempts.append(FallbackAttempt(stage, method, AttemptOutcome.SELECTED))
        return BaselineValuation(
            **{
                **candidate.__dict__,
                "fallback_attempts": tuple((*attempts[:-1], attempts[-1])),
            }
        )
    return BaselineValuation(
        ticker=normalized,
        method="unavailable",
        method_version="LAUNCH-FIRST-FALLBACK-1.0",
        low=None,
        base=None,
        high=None,
        confidence=None,
        availability_type=AvailabilityType.NOT_AVAILABLE,
        warnings=("No economically suitable launch-first route produced a usable value.",),
        fallback_attempts=tuple(attempts),
    )


def baseline_from_public_artifact(artifact: Mapping[str, Any]) -> BaselineValuation:
    """Project a sanitized v1.0/v1.1 artifact into the shared retail contract."""

    ticker = str(artifact.get("ticker") or artifact.get("issuer", {}).get("ticker") or "")
    policy = artifact.get("model_policy")
    primary_model = str(policy.get("primary") if isinstance(policy, Mapping) else "unavailable")
    primary = str(artifact.get("primary_valuation_method") or primary_model)
    review = artifact.get("review")
    state = review.get("publication_state") if isinstance(review, Mapping) else "withheld"
    scenario = artifact.get("scenario_range")
    scenario = scenario if isinstance(scenario, Mapping) else {}
    reliability = artifact.get("reliability")
    reliability = reliability if isinstance(reliability, Mapping) else {}
    if state == "withheld":
        availability = AvailabilityType.NOT_AVAILABLE
        low = base = high = None
        confidence = None
    else:
        availability = (
            AvailabilityType.CONDITIONAL
            if primary_model == "conditional_estimate"
            else AvailabilityType.RELATIVE
            if primary_model == "relative_value"
            else AvailabilityType.AVAILABLE
        )
        low, base, high = (scenario.get(key) for key in ("low", "base", "high"))
        confidence = reliability.get("label")
    assumptions = artifact.get("public_assumptions")
    assumptions = assumptions if isinstance(assumptions, Mapping) else {}
    selected_assumptions = []
    for name in (
        "forecast_years",
        "initial_revenue_growth",
        "target_operating_margin",
        "policy_wacc",
        "cost_of_equity",
        "terminal_growth",
    ):
        if name in assumptions:
            selected_assumptions.append(
                BaselineAssumption(
                    name=name,
                    value=assumptions[name],
                    classification=AssumptionClassification.FINSIGHT_ASSUMPTION,
                    basis="Published governed FinSight assumption.",
                )
            )
    version = str(
        assumptions.get("forecast_policy_version")
        or artifact.get("schema_version")
        or "legacy"
    )
    warnings = review.get("warnings", []) if isinstance(review, Mapping) else []
    reasons = reliability.get("reasons", [])
    return BaselineValuation(
        ticker=ticker,
        method=primary,
        method_version=version,
        low=low,
        base=base,
        high=high,
        confidence=confidence,
        availability_type=availability,
        key_assumptions=tuple(selected_assumptions),
        warnings=tuple(str(value) for value in warnings),
        confidence_reasons=tuple(str(value) for value in reasons),
        calculator_link=f"/api/us-valuations/{ticker}/calculator",
    )


def _canonical_market_comparison(value: object) -> dict[str, Any]:
    unavailable = {"status": "unavailable", "reason": "approved_eod_record_unavailable"}
    if isinstance(value, Mapping) and value.get("status") == "unavailable":
        reason = value.get("reason")
        if reason in {"approved_eod_record_unavailable", "approved_eod_record_invalid"}:
            return {"status": "unavailable", "reason": reason}
    if not isinstance(value, Mapping) or value.get("status") != "available":
        return unavailable
    allowed = {
        key: deepcopy(value[key])
        for key in ("status", "gap_pct", "label", "price_date", "denominator")
        if key in value
    }
    gap = allowed.get("gap_pct")
    if (
        isinstance(gap, bool)
        or not isinstance(gap, Real)
        or not isfinite(float(gap))
        or allowed.get("denominator") != "finsight_base_value"
        or not isinstance(allowed.get("label"), str)
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(allowed.get("price_date")))
    ):
        return unavailable
    allowed["gap_pct"] = float(gap)
    return allowed


def _canonical_relative_summary(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("status") != "available":
        return {"status": "unavailable"}
    result = {
        key: deepcopy(value[key])
        for key in ("status", "method", "low", "base", "high", "peer_count", "as_of_date", "label")
        if key in value
    }
    values = (result.get("low"), result.get("base"), result.get("high"))
    if any(
        isinstance(item, bool)
        or not isinstance(item, Real)
        or not isfinite(float(item))
        for item in values
    ):
        return {"status": "unavailable"}
    low, base, high = (float(item) for item in values)  # type: ignore[arg-type]
    if base <= 0 or not low <= base <= high:
        return {"status": "unavailable"}
    if not isinstance(result.get("method"), str) or not isinstance(result.get("label"), str):
        return {"status": "unavailable"}
    if not isinstance(result.get("peer_count"), int) or result["peer_count"] < 2:
        return {"status": "unavailable"}
    result.update({"low": low, "base": base, "high": high})
    return result


def apply_public_baseline_contract(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Upgrade a sanitized artifact to v1.2 while retaining all v1.1 fields."""

    public = deepcopy(dict(artifact))
    public["schema_version"] = "US-PUBLIC-VALUATION-1.2"
    try:
        baseline = baseline_from_public_artifact(public)
    except (KeyError, TypeError, ValueError):
        policy = public.get("model_policy")
        primary = policy.get("primary") if isinstance(policy, Mapping) else "unavailable"
        ticker = str(public.get("ticker") or public.get("issuer", {}).get("ticker") or "")
        public["availability_type"] = AvailabilityType.NOT_AVAILABLE.value
        public["primary_valuation_method"] = str(primary)
        public["confidence"] = {"label": None, "reasons": ["VALUATION_WITHHELD"]}
        public["calculator_link"] = (
            f"/api/us-valuations/{ticker}/calculator"
            if re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", ticker)
            else None
        )
    else:
        public["availability_type"] = baseline.availability_type.value
        public["primary_valuation_method"] = baseline.method
        public["confidence"] = {
            "label": baseline.confidence,
            "reasons": list(baseline.confidence_reasons),
        }
        public["calculator_link"] = baseline.calculator_link
    public["market_comparison"] = _canonical_market_comparison(
        public.get("market_comparison")
    )
    public["relative_value_summary"] = _canonical_relative_summary(
        public.get("relative_value_summary")
    )
    return public
