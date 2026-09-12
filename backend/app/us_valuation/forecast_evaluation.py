"""Descriptive, immutable forecast-versus-actual evaluation.

This module compares an already-issued forecast with later actuals by exact
metric and fiscal-period keys.  It does not revise the forecast, tune model
parameters, fetch data, or infer a period match.  Missing matches are
explicitly ``incomparable``.  Percentage errors use actual magnitude as the
denominator and remain ``None`` when a nonzero error has a zero actual, which
keeps the result finite and honest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from numbers import Real
from typing import Any, Iterable, Mapping

from .sustainable_inputs import SourceEvidence, validate_source_evidence


FORECAST_EVALUATION_POLICY_VERSION = "US-FORECAST-EVALUATION-1.0"


def _finite(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f"{field} must be a finite number")
    return float(value)


def _key(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty text")
    return value.strip()


@dataclass(frozen=True)
class ForecastDatum:
    """One issued forecast or one subsequent actual observation."""

    metric: str
    fiscal_period: str
    value: float
    source: SourceEvidence

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric", _key(self.metric, "metric"))
        object.__setattr__(self, "fiscal_period", _key(self.fiscal_period, "fiscal_period"))
        object.__setattr__(self, "value", _finite(self.value, "forecast/actual value"))
        if not isinstance(self.source, SourceEvidence):
            raise ValueError("forecast/actual source must be SourceEvidence")

    @property
    def match_key(self) -> tuple[str, str]:
        return self.metric, self.fiscal_period

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "source": self.source.as_dict()}


ForecastObservation = ForecastDatum


def _coerce_datum(row: ForecastDatum | Mapping[str, Any], *, value_name: str) -> ForecastDatum:
    if isinstance(row, ForecastDatum):
        return row
    if not isinstance(row, Mapping):
        raise ValueError("forecast and actual rows must be ForecastDatum or mappings")
    value = row.get(value_name, row.get("value"))
    source = row.get("source")
    if isinstance(source, Mapping):
        source = SourceEvidence(**source)
    return ForecastDatum(
        metric=row.get("metric"),
        fiscal_period=row.get("fiscal_period", row.get("period")),
        value=value,
        source=source,
    )


@dataclass(frozen=True)
class ForecastComparison:
    """One exact-period comparison; positive signed error means actual beat forecast."""

    metric: str
    fiscal_period: str
    forecast_value: float
    actual_value: float | None
    status: str
    signed_error: float | None
    absolute_error: float | None
    signed_error_ratio: float | None
    absolute_error_ratio: float | None
    signed_error_pct: float | None
    absolute_error_pct: float | None
    percentage_status: str
    reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric", _key(self.metric, "metric"))
        object.__setattr__(self, "fiscal_period", _key(self.fiscal_period, "fiscal_period"))
        forecast = _finite(self.forecast_value, "forecast_value")
        actual = None if self.actual_value is None else _finite(self.actual_value, "actual_value")
        if self.status not in {"comparable", "incomparable"}:
            raise ValueError("comparison status is invalid")
        if self.status == "incomparable":
            if actual is not None or any(value is not None for value in (self.signed_error, self.absolute_error, self.signed_error_ratio, self.absolute_error_ratio, self.signed_error_pct, self.absolute_error_pct)):
                raise ValueError("incomparable rows cannot contain actuals or errors")
            if self.percentage_status != "incomparable":
                raise ValueError("incomparable rows need incomparable percentage status")
            if self.reason not in {"missing_actual", "source_period_mismatch", "actual_not_subsequent"}:
                raise ValueError("incomparable rows need a recognized reason")
        else:
            if actual is None or self.signed_error is None or self.absolute_error is None:
                raise ValueError("comparable rows require an actual and errors")
            signed = _finite(self.signed_error, "signed_error")
            absolute = _finite(self.absolute_error, "absolute_error")
            if not math.isclose(signed, actual - forecast, rel_tol=1e-12, abs_tol=1e-9):
                raise ValueError("signed error must equal actual minus forecast")
            if not math.isclose(absolute, abs(signed), rel_tol=1e-12, abs_tol=1e-9):
                raise ValueError("absolute error must equal absolute signed error")
            if self.percentage_status not in {"defined", "zero_actual_equal", "zero_actual_nonzero_error"}:
                raise ValueError("percentage status is invalid")
            if self.reason is not None:
                raise ValueError("comparable rows cannot have an incomparable reason")
        object.__setattr__(self, "forecast_value", forecast)
        object.__setattr__(self, "actual_value", actual)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def signed_percent(self) -> float | None:
        """Signed error in percentage points (``10.0`` means ten percent)."""

        return self.signed_error_pct

    @property
    def absolute_percent(self) -> float | None:
        return self.absolute_error_pct


@dataclass(frozen=True)
class ForecastEvaluation:
    """Immutable evaluation receipt; descriptive only and never auto-tuned."""

    forecast_snapshot: tuple[ForecastDatum, ...]
    comparisons: tuple[ForecastComparison, ...]
    frozen_cutoff: str
    compared_count: int
    incomparable_count: int
    tuning_applied: bool = False

    def __post_init__(self) -> None:
        if self.compared_count < 0 or self.incomparable_count < 0:
            raise ValueError("evaluation counts must be nonnegative")
        if self.compared_count + self.incomparable_count != len(self.comparisons):
            raise ValueError("evaluation counts do not reconcile to comparisons")
        if self.tuning_applied is not False:
            raise ValueError("forecast evaluation never applies tuning")
        if not isinstance(self.frozen_cutoff, str) or not self.frozen_cutoff.strip():
            raise ValueError("frozen_cutoff is required")
        object.__setattr__(self, "frozen_cutoff", self.frozen_cutoff.strip())
        object.__setattr__(self, "forecast_snapshot", tuple(self.forecast_snapshot))
        object.__setattr__(self, "comparisons", tuple(self.comparisons))

    @property
    def status(self) -> str:
        return "incomparable" if self.compared_count == 0 else "evaluated"

    @property
    def rows(self) -> tuple[ForecastComparison, ...]:
        return self.comparisons

    @property
    def auto_tuned(self) -> bool:
        return self.tuning_applied

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_version": FORECAST_EVALUATION_POLICY_VERSION,
            "forecast_snapshot": [row.as_dict() for row in self.forecast_snapshot],
            "comparisons": [row.as_dict() for row in self.comparisons],
            "frozen_cutoff": self.frozen_cutoff,
            "compared_count": self.compared_count,
            "incomparable_count": self.incomparable_count,
            "status": self.status,
            "tuning_applied": self.tuning_applied,
        }


def evaluate_forecast(
    forecast: Iterable[ForecastDatum | Mapping[str, Any]],
    actuals: Iterable[ForecastDatum | Mapping[str, Any]],
    *,
    frozen_cutoff: str,
) -> ForecastEvaluation:
    """Compare exact fiscal-period keys and return a descriptive receipt.

    Forecast rows are captured as a tuple before matching.  Actuals are never
    used to alter, refill, or tune that snapshot.
    """

    forecast_snapshot = tuple(_coerce_datum(row, value_name="forecast_value") for row in forecast)
    actual_rows = tuple(_coerce_datum(row, value_name="actual_value") for row in actuals)
    for row in (*forecast_snapshot, *actual_rows):
        validate_source_evidence(row.source, frozen_cutoff)
    forecast_keys = [row.match_key for row in forecast_snapshot]
    actual_keys = [row.match_key for row in actual_rows]
    if len(set(forecast_keys)) != len(forecast_keys):
        raise ValueError("forecast metric/fiscal_period keys must be unique")
    if len(set(actual_keys)) != len(actual_keys):
        raise ValueError("actual metric/fiscal_period keys must be unique")
    actual_by_key = {row.match_key: row for row in actual_rows}
    comparisons: list[ForecastComparison] = []
    for row in forecast_snapshot:
        actual = actual_by_key.get(row.match_key)
        if actual is None:
            comparisons.append(
                ForecastComparison(
                    metric=row.metric,
                    fiscal_period=row.fiscal_period,
                    forecast_value=row.value,
                    actual_value=None,
                    status="incomparable",
                    signed_error=None,
                    absolute_error=None,
                    signed_error_ratio=None,
                    absolute_error_ratio=None,
                    signed_error_pct=None,
                    absolute_error_pct=None,
                    percentage_status="incomparable",
                    reason="missing_actual",
                )
            )
            continue
        if actual.source.period_end != row.source.period_end:
            comparisons.append(
                ForecastComparison(
                    metric=row.metric,
                    fiscal_period=row.fiscal_period,
                    forecast_value=row.value,
                    actual_value=None,
                    status="incomparable",
                    signed_error=None,
                    absolute_error=None,
                    signed_error_ratio=None,
                    absolute_error_ratio=None,
                    signed_error_pct=None,
                    absolute_error_pct=None,
                    percentage_status="incomparable",
                    reason="source_period_mismatch",
                )
            )
            continue
        if actual.source.filing_date <= row.source.filing_date:
            comparisons.append(
                ForecastComparison(
                    metric=row.metric,
                    fiscal_period=row.fiscal_period,
                    forecast_value=row.value,
                    actual_value=None,
                    status="incomparable",
                    signed_error=None,
                    absolute_error=None,
                    signed_error_ratio=None,
                    absolute_error_ratio=None,
                    signed_error_pct=None,
                    absolute_error_pct=None,
                    percentage_status="incomparable",
                    reason="actual_not_subsequent",
                )
            )
            continue
        signed = actual.value - row.value
        absolute = abs(signed)
        if actual.value == 0:
            ratio = 0.0 if signed == 0 else None
            pct_status = "zero_actual_equal" if signed == 0 else "zero_actual_nonzero_error"
        else:
            ratio = signed / abs(actual.value)
            pct_status = "defined"
        absolute_ratio = None if ratio is None else absolute / abs(actual.value) if actual.value != 0 else 0.0
        comparisons.append(
            ForecastComparison(
                metric=row.metric,
                fiscal_period=row.fiscal_period,
                forecast_value=row.value,
                actual_value=actual.value,
                status="comparable",
                signed_error=signed,
                absolute_error=absolute,
                signed_error_ratio=ratio,
                absolute_error_ratio=absolute_ratio,
                signed_error_pct=None if ratio is None else ratio * 100.0,
                absolute_error_pct=None if absolute_ratio is None else absolute_ratio * 100.0,
                percentage_status=pct_status,
                reason=None,
            )
        )
    compared = sum(row.status == "comparable" for row in comparisons)
    return ForecastEvaluation(
        forecast_snapshot=forecast_snapshot,
        comparisons=tuple(comparisons),
        frozen_cutoff=frozen_cutoff,
        compared_count=compared,
        incomparable_count=len(comparisons) - compared,
    )


compare_forecast_to_actuals = evaluate_forecast
evaluate_forecasts = evaluate_forecast
evaluate_forecast_accuracy = evaluate_forecast
ForecastRecord = ForecastDatum


__all__ = [
    "FORECAST_EVALUATION_POLICY_VERSION",
    "ForecastDatum",
    "ForecastRecord",
    "ForecastObservation",
    "ForecastComparison",
    "ForecastEvaluation",
    "evaluate_forecast",
    "compare_forecast_to_actuals",
    "evaluate_forecasts",
    "evaluate_forecast_accuracy",
]
