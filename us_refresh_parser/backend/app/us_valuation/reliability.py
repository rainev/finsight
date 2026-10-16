"""Pure reliability labels for valuation evidence and scenario movement."""

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Literal


ReliabilityLabel = Literal["High", "Medium", "Low"]
_LABEL_RANK: dict[ReliabilityLabel, int] = {
    "High": 0,
    "Medium": 1,
    "Low": 2,
}
@dataclass(frozen=True)
class ReliabilityAssessment:
    label: ReliabilityLabel
    accounting_label: ReliabilityLabel
    scenario_label: ReliabilityLabel
    model_cap: ReliabilityLabel
    source_cap: ReliabilityLabel
    accounting_impact_ratio: float
    scenario_movement_ratio: float
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "accounting_label": self.accounting_label,
            "scenario_label": self.scenario_label,
            "model_cap": self.model_cap,
            "source_cap": self.source_cap,
            "accounting_impact_ratio": self.accounting_impact_ratio,
            "scenario_movement_ratio": self.scenario_movement_ratio,
            "reasons": list(self.reasons),
        }


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    normalized = float(value)
    if not isfinite(normalized):
        raise ValueError(f"{name} must be a finite number")
    return normalized


def relative_movement(*, low: float, base: float, high: float) -> float:
    low_value = _finite_number(low, "low")
    base_value = _finite_number(base, "base")
    high_value = _finite_number(high, "high")
    if not low_value <= base_value <= high_value:
        raise ValueError("range must satisfy low <= base <= high")
    if base_value == 0:
        raise ValueError("base must be non-zero")
    return max(
        abs(low_value - base_value),
        abs(high_value - base_value),
    ) / abs(base_value)


def _nonnegative_ratio(value: float) -> float:
    normalized = _finite_number(value, "ratio")
    if normalized < 0:
        raise ValueError("ratio must be nonnegative")
    return normalized


def _at_or_below(value: float, boundary: float) -> bool:
    return value <= boundary


def accounting_label(impact: float) -> ReliabilityLabel:
    impact = _nonnegative_ratio(impact)
    if _at_or_below(impact, 0.05):
        return "High"
    if _at_or_below(impact, 0.20):
        return "Medium"
    return "Low"


def scenario_label(movement: float) -> ReliabilityLabel:
    movement = _nonnegative_ratio(movement)
    if _at_or_below(movement, 0.20):
        return "High"
    if _at_or_below(movement, 0.40):
        return "Medium"
    return "Low"


def lowest_label(*labels: ReliabilityLabel) -> ReliabilityLabel:
    if not labels or any(label not in _LABEL_RANK for label in labels):
        raise ValueError("labels must contain only High, Medium, or Low")
    return max(labels, key=_LABEL_RANK.__getitem__)


def assess_reliability(
    *,
    accounting_low: float,
    accounting_base: float,
    accounting_high: float,
    scenario_low: float,
    scenario_base: float,
    scenario_high: float,
    model_cap: ReliabilityLabel = "High",
    source_cap: ReliabilityLabel = "High",
    reasons: tuple[str, ...] = (),
) -> ReliabilityAssessment:
    accounting_impact = relative_movement(
        low=accounting_low,
        base=accounting_base,
        high=accounting_high,
    )
    scenario_movement = relative_movement(
        low=scenario_low,
        base=scenario_base,
        high=scenario_high,
    )
    data_label = accounting_label(accounting_impact)
    forecast_label = scenario_label(scenario_movement)
    label = lowest_label(data_label, forecast_label, model_cap, source_cap)
    if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
        raise ValueError("reasons must contain nonempty strings")
    return ReliabilityAssessment(
        label=label,
        accounting_label=data_label,
        scenario_label=forecast_label,
        model_cap=model_cap,
        source_cap=source_cap,
        accounting_impact_ratio=accounting_impact,
        scenario_movement_ratio=scenario_movement,
        reasons=tuple(dict.fromkeys(reasons)),
    )
