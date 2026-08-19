"""Deterministic period-aware fallback ranges for valuation inputs."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import median
from typing import Literal, Sequence

from .field_availability import FallbackLevel, UncertaintyRange
from .reliability import ReliabilityLabel


PeriodRole = Literal["operating_ttm", "balance_sheet_snapshot"]
MINIMUM_UNCERTAINTY = 0.10
MINIMUM_SECTOR_PEERS = 5


def _finite_nonnegative(value: object, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"{name} must be a finite nonnegative number")
    return float(value)


def _accessions(values: Sequence[str]) -> tuple[str, ...]:
    result = tuple(dict.fromkeys(str(value) for value in values if str(value)))
    if not result:
        raise ValueError("source_accessions must not be empty")
    return result


@dataclass(frozen=True)
class FallbackDecision:
    field: str
    low: float
    base: float
    high: float
    period_role: PeriodRole
    fallback_level: FallbackLevel
    source_age_days: int | None
    source_accessions: tuple[str, ...]
    basis: str
    major_change_flags: tuple[str, ...] = ()
    reliability_cap: ReliabilityLabel = "High"

    def __post_init__(self) -> None:
        low = _finite_nonnegative(self.low, "low")
        base = _finite_nonnegative(self.base, "base")
        high = _finite_nonnegative(self.high, "high")
        if not low <= base <= high:
            raise ValueError("fallback range must satisfy low <= base <= high")
        if self.period_role not in {"operating_ttm", "balance_sheet_snapshot"}:
            raise ValueError("fallback period role is invalid")
        if self.fallback_level not in {
            "annual_carried_forward",
            "company_history",
            "sector_estimate",
        }:
            raise ValueError("fallback level is not range-producing")
        if self.reliability_cap not in {"High", "Medium", "Low"}:
            raise ValueError("reliability cap is invalid")
        _accessions(self.source_accessions)
        if not isinstance(self.basis, str) or not self.basis.strip():
            raise ValueError("basis must be nonempty")

    def uncertainty(self) -> UncertaintyRange:
        return UncertaintyRange(
            low=self.low,
            high=self.high,
            basis=self.basis,
            source_accessions=self.source_accessions,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "low": self.low,
            "base": self.base,
            "high": self.high,
            "period_role": self.period_role,
            "fallback_level": self.fallback_level,
            "source_age_days": self.source_age_days,
            "source_accessions": list(self.source_accessions),
            "basis": self.basis,
            "major_change_flags": list(self.major_change_flags),
            "reliability_cap": self.reliability_cap,
        }


def _annual_change_rate(values: Sequence[float]) -> float:
    changes: list[float] = []
    for previous, current in zip(values, values[1:]):
        previous = _finite_nonnegative(previous, "annual history value")
        current = _finite_nonnegative(current, "annual history value")
        if previous == 0:
            changes.append(1.0 if current else 0.0)
        else:
            changes.append(abs(current - previous) / previous)
    return max([MINIMUM_UNCERTAINTY, *changes])


def annual_carried_forward_decision(
    *,
    field: str,
    base: float,
    annual_values: Sequence[float],
    source_age_days: int,
    source_accessions: Sequence[str],
    major_change_flags: Sequence[str] = (),
    quantified_change: float | None = None,
) -> FallbackDecision:
    base = _finite_nonnegative(base, "base")
    if isinstance(source_age_days, bool) or not 0 <= source_age_days <= 365:
        raise ValueError("annual source age must be between 0 and 365 days")
    history = [_finite_nonnegative(value, "annual history value") for value in annual_values][-3:]
    if not history or history[-1] != base:
        raise ValueError("annual history must end with the carried base value")
    uncertainty = _annual_change_rate(history)
    flags = tuple(
        dict.fromkeys(str(flag) for flag in major_change_flags if str(flag))
    )
    if flags and quantified_change is None:
        raise ValueError("material annual-to-quarter change is unquantified")
    low = max(0.0, base * (1.0 - uncertainty))
    high = base * (1.0 + uncertainty)
    if quantified_change is not None:
        change = float(quantified_change)
        if not isfinite(change):
            raise ValueError("quantified change must be finite")
        changed = max(0.0, base + change)
        low = min(low, changed)
        high = max(high, changed)
        base = changed
    return FallbackDecision(
        field=field,
        low=low,
        base=base,
        high=high,
        period_role="balance_sheet_snapshot",
        fallback_level="annual_carried_forward",
        source_age_days=source_age_days,
        source_accessions=_accessions(source_accessions),
        basis=(
            f"Latest annual {field} with a {uncertainty:.6f} uncertainty band "
            "from the larger of 10% or recent annual movement."
        ),
        major_change_flags=flags,
    )


def company_history_decision(
    *,
    field: str,
    observations: Sequence[tuple[float, float, str]],
    current_total_assets: float,
    source_age_days: int | None,
) -> FallbackDecision:
    if len(observations) < 2:
        raise ValueError("company-history fallback requires at least two observations")
    assets = _finite_nonnegative(current_total_assets, "current_total_assets")
    if assets == 0:
        raise ValueError("current_total_assets must be positive")
    ratios: list[float] = []
    accessions: list[str] = []
    for value, historical_assets, accession in observations[-3:]:
        value = _finite_nonnegative(value, "history value")
        historical_assets = _finite_nonnegative(historical_assets, "history assets")
        if historical_assets == 0:
            raise ValueError("history assets must be positive")
        ratios.append(value / historical_assets)
        accessions.append(accession)
    raw_low = min(ratios) * assets
    base = median(ratios) * assets
    raw_high = max(ratios) * assets
    low = min(raw_low, max(0.0, base * (1.0 - MINIMUM_UNCERTAINTY)))
    high = max(raw_high, base * (1.0 + MINIMUM_UNCERTAINTY))
    return FallbackDecision(
        field=field,
        low=low,
        base=base,
        high=high,
        period_role="balance_sheet_snapshot",
        fallback_level="company_history",
        source_age_days=source_age_days,
        source_accessions=_accessions(accessions),
        basis=(
            f"{field}-to-total-assets range from {len(ratios)} recent annual "
            "company observations with a 10% minimum band."
        ),
        reliability_cap="Medium",
    )


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def sector_estimate_decision(
    *,
    field: str,
    peer_ratios: Sequence[tuple[float, str]],
    current_total_assets: float,
) -> FallbackDecision:
    if len(peer_ratios) < MINIMUM_SECTOR_PEERS:
        raise ValueError("sector fallback requires at least five source-verified peers")
    assets = _finite_nonnegative(current_total_assets, "current_total_assets")
    if assets == 0:
        raise ValueError("current_total_assets must be positive")
    ratios = [_finite_nonnegative(value, "peer ratio") for value, _ in peer_ratios]
    accessions = [accession for _, accession in peer_ratios]
    low = _quantile(ratios, 0.25) * assets
    base = _quantile(ratios, 0.50) * assets
    high = _quantile(ratios, 0.75) * assets
    return FallbackDecision(
        field=field,
        low=low,
        base=base,
        high=high,
        period_role="balance_sheet_snapshot",
        fallback_level="sector_estimate",
        source_age_days=None,
        source_accessions=_accessions(accessions),
        basis=(
            f"Source-verified peer {field}-to-total-assets 25th, 50th, and "
            f"75th percentiles across {len(ratios)} peers."
        ),
        reliability_cap="Low",
    )
