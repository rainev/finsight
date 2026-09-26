"""Market-relative cross-checks; never blended into intrinsic value."""

from __future__ import annotations

from statistics import median
from typing import Any


def comparable_cross_check(
    *,
    metric: str,
    peer_multiples: list[float],
    target_metric_per_share: float,
) -> dict[str, Any]:
    valid = [float(value) for value in peer_multiples if isinstance(value, (int, float)) and value > 0]
    if not valid:
        raise ValueError("at least one positive peer multiple is required")
    if target_metric_per_share <= 0:
        raise ValueError("target_metric_per_share must be positive")
    selected = median(valid)
    return {
        "output_type": "market_relative_only",
        "metric": metric,
        "peer_count": len(valid),
        "median_multiple": selected,
        "estimate_per_share": selected * target_metric_per_share,
    }


def market_relative_range(
    *,
    metric: str,
    metric_value_per_share: float,
    assumptions: dict[str, float],
    relation: str = "multiple",
) -> dict[str, Any]:
    """Produce a transparent low/base/high screening range."""

    if metric_value_per_share <= 0:
        raise ValueError("metric_value_per_share must be positive")
    if set(assumptions) != {"low", "base", "high"}:
        raise ValueError("assumptions must contain low, base, and high")
    if any(not isinstance(value, (int, float)) or value <= 0 for value in assumptions.values()):
        raise ValueError("all market-relative assumptions must be positive")
    if relation == "multiple":
        estimates = {name: metric_value_per_share * value for name, value in assumptions.items()}
    elif relation == "yield":
        estimates = {name: metric_value_per_share / value for name, value in assumptions.items()}
    else:
        raise ValueError("relation must be multiple or yield")
    if not estimates["low"] <= estimates["base"] <= estimates["high"]:
        raise ValueError("market-relative estimates must be ordered low <= base <= high")
    return {
        "output_type": "market_relative_only",
        "metric": metric,
        "relation": relation,
        "metric_value_per_share": metric_value_per_share,
        "assumptions": assumptions,
        "estimates": estimates,
    }
