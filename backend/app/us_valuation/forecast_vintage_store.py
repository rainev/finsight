"""Immutable forecast vintages and evidence-aware actual capture.

This module is deliberately an append-only boundary around
``forecast_evaluation``.  A forecast becomes a vintage only when its issued
snapshot is supplied by the caller; replaying today's model does not create
historical evidence.  Actual filings are captured as immutable first-reported
or restated observations, and evaluation produces review recommendations only
-- it never changes a policy or a model parameter.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import os
from contextlib import contextmanager
import fcntl
import math
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from .catalog import canonical_json_bytes, sha256_bytes
from .forecast_evaluation import ForecastComparison, ForecastDatum, evaluate_forecast
from .sustainable_inputs import SourceEvidence, validate_source_evidence


FORECAST_VINTAGE_SCHEMA = "FINSIGHT-FORECAST-VINTAGE-1"
ACTUAL_CAPTURE_SCHEMA = "FINSIGHT-FORECAST-ACTUAL-CAPTURE-1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty text")
    return value.strip()


def _iso(value: object, field: str) -> str:
    text = _text(value, field)
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def _hash(value: object, field: str) -> str:
    text = _text(value, field).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"{field} must be a lowercase SHA-256 hash")
    return text


def _safe_id(value: object, field: str) -> str:
    text = _text(value, field)
    if not _SAFE_ID.fullmatch(text) or text in {".", ".."}:
        raise ValueError(f"{field} is not a safe identifier")
    return text


def _source_from_dict(value: Mapping[str, Any]) -> SourceEvidence:
    return SourceEvidence(**dict(value))


def _datum_from_dict(value: Mapping[str, Any]) -> ForecastDatum:
    source = value.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("forecast/actual row source is missing")
    return ForecastDatum(
        metric=value.get("metric"),
        fiscal_period=value.get("fiscal_period"),
        value=value.get("value"),
        source=_source_from_dict(source),
    )


@dataclass(frozen=True)
class ForecastVintage:
    """An issued, immutable forecast snapshot for one company/model family."""

    vintage_id: str
    company_id: str
    company_cik: str
    company_family: str
    model_version: str
    policy_version: str
    issued_at: str
    frozen_cutoff: str
    scenarios: Mapping[str, tuple[ForecastDatum, ...]]
    source_hashes: Mapping[str, str]
    historical_evidence: bool = False
    comparability_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "vintage_id", _safe_id(self.vintage_id, "vintage_id"))
        object.__setattr__(self, "company_id", _text(self.company_id, "company_id"))
        cik = _text(self.company_cik, "company_cik")
        if not re.fullmatch(r"\d{10}", cik):
            raise ValueError("company_cik must be a ten-digit CIK")
        object.__setattr__(self, "company_cik", cik)
        object.__setattr__(self, "company_family", _text(self.company_family, "company_family"))
        object.__setattr__(self, "model_version", _text(self.model_version, "model_version"))
        object.__setattr__(self, "policy_version", _text(self.policy_version, "policy_version"))
        object.__setattr__(self, "issued_at", _iso(self.issued_at, "issued_at"))
        object.__setattr__(self, "frozen_cutoff", _iso(self.frozen_cutoff, "frozen_cutoff"))
        if not isinstance(self.scenarios, Mapping) or not self.scenarios:
            raise ValueError("vintage scenarios are required")
        normalized: dict[str, tuple[ForecastDatum, ...]] = {}
        for scenario, rows in self.scenarios.items():
            name = _text(scenario, "scenario")
            values = tuple(rows)
            if not values or any(not isinstance(row, ForecastDatum) for row in values):
                raise ValueError("each scenario needs ForecastDatum rows")
            scenario_keys = set()
            for row in values:
                if row.source.cik != self.company_cik:
                    raise ValueError("forecast source CIK does not match company")
                if row.source.filing_date > self.frozen_cutoff and row.source.reported_vs_estimated != "estimated":
                    raise ValueError("forecast source is after frozen cutoff")
                if row.source.filing_date > self.issued_at:
                    raise ValueError("forecast source was not available at issuance")
                if not math.isclose(row.value, row.source.reported_value, rel_tol=1e-12, abs_tol=1e-9):
                    raise ValueError("forecast value does not reconcile to source reported value")
                if row.match_key in scenario_keys:
                    raise ValueError("forecast metric/fiscal period keys must be unique within a scenario")
                scenario_keys.add(row.match_key)
            normalized[name] = values
        object.__setattr__(self, "scenarios", normalized)
        if self.frozen_cutoff > self.issued_at:
            raise ValueError("frozen_cutoff cannot be after issued_at")
        if set(normalized) != {'bear', 'base', 'bull'}:
            raise ValueError('forecast vintage requires bear, base and bull scenarios')
        reference = {row.match_key: row for row in normalized['base']}
        for scenario_rows in normalized.values():
            if {row.match_key for row in scenario_rows} != set(reference):
                raise ValueError('scenario fiscal-period coverage must match')
            for row in scenario_rows:
                other = reference[row.match_key].source
                if (row.source.unit, row.source.period_start, row.source.period_end) != (other.unit, other.period_start, other.period_end):
                    raise ValueError('scenario source units and periods must match')
        hashes = {str(key): _hash(value, f"source_hashes[{key}]") for key, value in dict(self.source_hashes).items()}
        source_ids = {row.source.source_id for rows in normalized.values() for row in rows}
        if source_ids - set(hashes):
            raise ValueError("source_hashes must cover every forecast source ID")
        object.__setattr__(self, "source_hashes", hashes)
        if self.historical_evidence is not False:
            raise ValueError("historical_evidence is earned from captured actual evidence")
        object.__setattr__(self,'comparability_limitations',tuple(_text(item,'comparability limitation') for item in self.comparability_limitations))

    @property
    def fiscal_periods(self) -> tuple[str, ...]:
        return tuple(sorted({row.fiscal_period for rows in self.scenarios.values() for row in rows}))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FORECAST_VINTAGE_SCHEMA,
            "vintage_id": self.vintage_id,
            "company_id": self.company_id,
            "company_cik": self.company_cik,
            "company_family": self.company_family,
            "model_version": self.model_version,
            "policy_version": self.policy_version,
            "issued_at": self.issued_at,
            "frozen_cutoff": self.frozen_cutoff,
            "scenarios": {
                name: [row.as_dict() for row in rows]
                for name, rows in self.scenarios.items()
            },
            "fiscal_periods": list(self.fiscal_periods),
            "source_hashes": dict(self.source_hashes),
            "historical_evidence": self.historical_evidence,
            'comparability_limitations':list(self.comparability_limitations),
        }


@dataclass(frozen=True)
class CapturedActual:
    actual: ForecastDatum
    source_hash: str
    status: str

    def __post_init__(self) -> None:
        if not isinstance(self.actual, ForecastDatum):
            raise ValueError("actual must be ForecastDatum")
        _hash(self.source_hash, "source_hash")
        if self.status not in {"first_reported", "repeat", "restated"}:
            raise ValueError("actual capture status is invalid")

    def as_dict(self) -> dict[str, Any]:
        return {
            "actual": self.actual.as_dict(),
            "source_hash": self.source_hash,
            "status": self.status,
        }


@dataclass(frozen=True)
class ActualCapture:
    capture_id: str
    vintage_id: str
    captured_at: str
    frozen_cutoff: str
    rows: tuple[CapturedActual, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "capture_id", _safe_id(self.capture_id, "capture_id"))
        object.__setattr__(self, "vintage_id", _safe_id(self.vintage_id, "vintage_id"))
        object.__setattr__(self, "captured_at", _iso(self.captured_at, "captured_at"))
        object.__setattr__(self, "frozen_cutoff", _iso(self.frozen_cutoff, "frozen_cutoff"))
        values = tuple(self.rows)
        if not values or any(not isinstance(row, CapturedActual) for row in values):
            raise ValueError("actual capture rows are required")
        keys = [row.actual.match_key for row in values]
        if len(set(keys)) != len(keys):
            raise ValueError("actual capture metric/fiscal period keys must be unique")
        object.__setattr__(self, "rows", values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ACTUAL_CAPTURE_SCHEMA,
            "capture_id": self.capture_id,
            "vintage_id": self.vintage_id,
            "captured_at": self.captured_at,
            "frozen_cutoff": self.frozen_cutoff,
            "rows": [row.as_dict() for row in self.rows],
        }


@dataclass(frozen=True)
class VintageReceipt:
    vintage_id: str
    sha256: str
    path: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioEvaluation:
    scenario: str
    comparisons: tuple[ForecastComparison, ...]
    compared_count: int
    incomparable_count: int

    @property
    def coverage_ratio(self) -> float:
        total = self.compared_count + self.incomparable_count
        return self.compared_count / total if total else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "comparisons": [row.as_dict() for row in self.comparisons],
            "compared_count": self.compared_count,
            "incomparable_count": self.incomparable_count,
            "coverage_ratio": self.coverage_ratio,
        }


@dataclass(frozen=True)
class VintageEvaluation:
    vintage_id: str
    company_id: str
    company_family: str
    model_version: str
    policy_version: str
    status: str
    historical_comparison_claim: bool
    scenario_evaluations: tuple[ScenarioEvaluation, ...]
    interval_coverage: Mapping[str, Mapping[str, Any]]
    metric_units: Mapping[str, str]
    recommendations: tuple[str, ...]
    policy_change_applied: bool = False

    def __post_init__(self) -> None:
        if self.status not in {"historically_comparable", "historical_data_limitation", "prospective_tracking"}:
            raise ValueError("vintage evaluation status is invalid")
        if self.policy_change_applied is not False:
            raise ValueError("vintage evaluation cannot change policy")
        if self.historical_comparison_claim and self.status != "historically_comparable":
            raise ValueError("historical comparison claim requires comparable evidence")

    def as_dict(self) -> dict[str, Any]:
        return {
            "vintage_id": self.vintage_id,
            "company_id": self.company_id,
            "company_family": self.company_family,
            "model_version": self.model_version,
            "policy_version": self.policy_version,
            "status": self.status,
            "historical_comparison_claim": self.historical_comparison_claim,
            "scenario_evaluations": [row.as_dict() for row in self.scenario_evaluations],
            "interval_coverage": {key: dict(value) for key, value in self.interval_coverage.items()},
            "metric_units": dict(self.metric_units),
            "recommendations": list(self.recommendations),
            "policy_change_applied": self.policy_change_applied,
        }


@dataclass(frozen=True)
class CoverageReport:
    company: Mapping[str, Mapping[str, Any]]
    family: Mapping[str, Mapping[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {"company": dict(self.company), "family": dict(self.family)}


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        if existing != payload:
            raise ValueError(f"immutable forecast vintage drift: {path.name}")
        return
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_with_digest(path: Path, payload: bytes) -> str:
    digest = sha256_bytes(payload)
    _atomic_write(path, payload)
    _atomic_write(path.with_suffix(".sha256"), (digest + "\n").encode("ascii"))
    return digest


def _verify_digest(path: Path) -> None:
    digest_path = path.with_suffix(".sha256")
    try:
        expected = digest_path.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise ValueError("immutable forecast record digest is missing") from exc
    if _hash(expected, "record digest") != sha256_bytes(path.read_bytes()):
        raise ValueError("immutable forecast record digest mismatch")


class ForecastVintageStore:
    """Append-only disk store for forecast vintages and actual captures."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.vintages_root = self.root / "vintages"
        self.actuals_root = self.root / "actuals"

    @contextmanager
    def _writer_lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / ".vintage-store.lock").open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def write_vintage(self, vintage: ForecastVintage) -> VintageReceipt:
        with self._writer_lock():
            payload = canonical_json_bytes(vintage.as_dict())
            path = self.vintages_root / f"{vintage.vintage_id}.json"
            digest = _write_with_digest(path, payload)
            return VintageReceipt(vintage.vintage_id, digest, str(path))

    def read_vintage(self, vintage_id: str) -> ForecastVintage:
        path = self.vintages_root / f"{_safe_id(vintage_id, 'vintage_id')}.json"
        _verify_digest(path)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("forecast vintage is missing or invalid") from exc
        if value.get("schema_version") != FORECAST_VINTAGE_SCHEMA:
            raise ValueError("forecast vintage schema is unsupported")
        scenarios = {
            name: tuple(_datum_from_dict(row) for row in rows)
            for name, rows in value.get("scenarios", {}).items()
        }
        return ForecastVintage(
            vintage_id=value["vintage_id"],
            company_id=value["company_id"],
            company_cik=value["company_cik"],
            company_family=value["company_family"],
            model_version=value["model_version"],
            policy_version=value["policy_version"],
            issued_at=value["issued_at"],
            frozen_cutoff=value["frozen_cutoff"],
            scenarios=scenarios,
            source_hashes=value["source_hashes"],
            comparability_limitations=tuple(value.get('comparability_limitations', ())),
        )

    def capture_actuals(
        self,
        vintage_id: str,
        actuals: Iterable[ForecastDatum],
        source_hashes: Mapping[str, str],
        *,
        captured_at: str,
        frozen_cutoff: str,
    ) -> ActualCapture:
        with self._writer_lock():
            vintage = self.read_vintage(vintage_id)
            cutoff = _iso(frozen_cutoff, "frozen_cutoff")
            rows = tuple(actuals)
            if not rows or any(not isinstance(row, ForecastDatum) for row in rows):
                raise ValueError("actuals are required")
            if len({row.match_key for row in rows}) != len(rows):
                raise ValueError("actual metric/fiscal period keys must be unique")
            hashes = {str(key): _hash(value, f"source_hashes[{key}]") for key, value in dict(source_hashes).items()}
            if {row.source.source_id for row in rows} - set(hashes):
                raise ValueError("source_hashes must cover every actual source ID")
            for row in rows:
                if row.source.cik != vintage.company_cik:
                    raise ValueError("actual source CIK does not match vintage company")
                if row.source.reported_vs_estimated == "estimated":
                    raise ValueError("actual evidence must be reported or derived_reported")
                if not math.isclose(row.value, row.source.reported_value, rel_tol=1e-12, abs_tol=1e-9):
                    raise ValueError("actual value does not reconcile to source reported value")
                validate_source_evidence(row.source, cutoff)
            canonical_rows = [row.as_dict() for row in rows]
            identity = {"vintage_id": vintage.vintage_id, "captured_at": _iso(captured_at, "captured_at"), "frozen_cutoff": cutoff, "rows": canonical_rows, "source_hashes": hashes}
            capture_id = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
            path = self.actuals_root / vintage.vintage_id / f"{capture_id}.json"
            if path.exists():
                return self._read_capture(path)
            prior = self.list_actual_captures(vintage.vintage_id)
            prior_by_key: dict[tuple[str, str], list[CapturedActual]] = {}
            for capture in prior:
                for prior_row in capture.rows:
                    prior_by_key.setdefault(prior_row.actual.match_key, []).append(prior_row)
            captured_rows = tuple(
                CapturedActual(
                    actual=row,
                    source_hash=hashes[row.source.source_id],
                    status=(
                        "first_reported"
                        if row.match_key not in prior_by_key
                        else "repeat"
                        if any(
                            math.isclose(previous.actual.value, row.value, rel_tol=1e-12, abs_tol=1e-9)
                            and previous.actual.source.period_end == row.source.period_end
                            for previous in prior_by_key[row.match_key]
                        )
                        else "restated"
                    ),
                )
                for row in rows
            )
            capture = ActualCapture(capture_id, vintage.vintage_id, _iso(captured_at, "captured_at"), cutoff, captured_rows)
            _write_with_digest(path, canonical_json_bytes(capture.as_dict()))
            return capture

    def _read_capture(self, path: Path) -> ActualCapture:
        _verify_digest(path)
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema_version") != ACTUAL_CAPTURE_SCHEMA:
            raise ValueError("actual capture schema is unsupported")
        rows = tuple(
            CapturedActual(_datum_from_dict(row["actual"]), row["source_hash"], row["status"])
            for row in value.get("rows", [])
        )
        return ActualCapture(value["capture_id"], value["vintage_id"], value["captured_at"], value["frozen_cutoff"], rows)

    def list_actual_captures(self, vintage_id: str) -> tuple[ActualCapture, ...]:
        directory = self.actuals_root / _safe_id(vintage_id, "vintage_id")
        if not directory.exists():
            return ()
        captures = [self._read_capture(path) for path in directory.glob("*.json")]
        return tuple(sorted(captures, key=lambda row: (row.captured_at, row.capture_id)))

    def select_actuals(self, vintage_id: str, *, basis: str = "first_reported") -> tuple[ForecastDatum, ...]:
        if basis not in {"first_reported", "latest"}:
            raise ValueError("actual basis must be first_reported or latest")
        captures = self.list_actual_captures(vintage_id)
        selected: dict[tuple[str, str], ForecastDatum] = {}
        for capture in captures:
            for row in capture.rows:
                if basis == "first_reported":
                    current = selected.get(row.actual.match_key)
                    if current is None or (row.actual.source.filing_date, row.actual.source.source_id) < (current.source.filing_date, current.source.source_id):
                        selected[row.actual.match_key] = row.actual
                else:
                    current = selected.get(row.actual.match_key)
                    if current is None or (row.actual.source.filing_date, row.actual.source.source_id) > (current.source.filing_date, current.source.source_id):
                        selected[row.actual.match_key] = row.actual
        return tuple(selected[key] for key in sorted(selected))


def evaluate_vintage(
    vintage: ForecastVintage,
    actuals: Iterable[ForecastDatum],
    *,
    basis: str = "first_reported",
    frozen_cutoff: str,
) -> VintageEvaluation:
    """Evaluate captured evidence without changing the issued vintage."""

    if basis not in {"first_reported", "latest"}:
        raise ValueError("actual basis must be first_reported or latest")
    actual_rows = tuple(actuals)
    cutoff = _iso(frozen_cutoff, "frozen_cutoff")
    if cutoff < vintage.issued_at:
        raise ValueError("evaluation frozen_cutoff cannot precede vintage issuance")
    if any(not isinstance(row, ForecastDatum) for row in actual_rows):
        raise ValueError("actuals must contain ForecastDatum rows")
    if actual_rows and vintage.comparability_limitations:
        raise ValueError('forecast vintage has unresolved comparability limitations')
    if basis == "first_reported":
        # Callers may pass already-selected first-reported rows.  Preserve
        # exact keys and reject duplicates rather than silently picking one.
        if len({row.match_key for row in actual_rows}) != len(actual_rows):
            raise ValueError("first-reported actual rows must have unique keys")
    forecast_by_key = {
        row.match_key: row
        for rows in vintage.scenarios.values()
        for row in rows
    }
    metric_units: dict[str, str] = {}
    for row in forecast_by_key.values():
        prior_unit = metric_units.setdefault(row.metric, row.source.unit)
        if prior_unit != row.source.unit:
            raise ValueError("forecast metric has inconsistent source units")
    for actual in actual_rows:
        if actual.source.cik != vintage.company_cik:
            raise ValueError("actual source CIK does not match vintage company")
        if actual.source.reported_vs_estimated == "estimated":
            raise ValueError("actual evidence must be reported or derived_reported")
        if not math.isclose(actual.value, actual.source.reported_value, rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("actual value does not reconcile to source reported value")
        if actual.source.filing_date <= vintage.issued_at:
            raise ValueError("actual filing must be after vintage issued_at")
        forecast_row = forecast_by_key.get(actual.match_key)
        if forecast_row is not None and (
            actual.source.unit != forecast_row.source.unit
            or actual.source.period_end != forecast_row.source.period_end
            or actual.source.period_start != forecast_row.source.period_start
        ):
            raise ValueError("actual source unit or period does not match forecast")
        validate_source_evidence(actual.source, cutoff)
    scenario_results: list[ScenarioEvaluation] = []
    for scenario, rows in vintage.scenarios.items():
        result = evaluate_forecast(rows, actual_rows, frozen_cutoff=cutoff)
        scenario_results.append(ScenarioEvaluation(scenario, result.comparisons, result.compared_count, result.incomparable_count))
    compared = sum(row.compared_count for row in scenario_results)
    interval_accumulator: dict[str, dict[str, Any]] = {
        metric: {"unit": unit, "comparable_count": 0, "covered_count": 0}
        for metric, unit in metric_units.items()
    }
    actual_by_key = {row.match_key: row for row in actual_rows}
    for key, forecast_row in forecast_by_key.items():
        actual = actual_by_key.get(key)
        if actual is None:
            continue
        bucket = interval_accumulator[forecast_row.metric]
        bucket["comparable_count"] += 1
        scenario_values = [rows_by_key[key].value for rows_by_key in (
            {row.match_key: row for row in rows} for rows in vintage.scenarios.values()
        ) if key in rows_by_key]
        if scenario_values and min(scenario_values) <= actual.value <= max(scenario_values):
            bucket["covered_count"] += 1
    interval_coverage = {
        metric: {
            **bucket,
            "coverage_ratio": bucket["covered_count"] / bucket["comparable_count"] if bucket["comparable_count"] else 0.0,
        }
        for metric, bucket in interval_accumulator.items()
    }
    if not actual_rows:
        status = "prospective_tracking"
        claim = False
        recommendations = ("Capture subsequent first-reported actuals before making a historical accuracy claim.",)
    elif compared == 0:
        status = "historical_data_limitation"
        claim = False
        recommendations = ("No exact fiscal-period actual matched this vintage; retain as a historical-data limitation.",)
    else:
        status = "historically_comparable"
        claim = True
        recommendations = ("Review signed and absolute errors and scenario interval coverage; do not auto-tune policy parameters.",)
    return VintageEvaluation(
        vintage_id=vintage.vintage_id,
        company_id=vintage.company_id,
        company_family=vintage.company_family,
        model_version=vintage.model_version,
        policy_version=vintage.policy_version,
        status=status,
        historical_comparison_claim=claim,
        scenario_evaluations=tuple(scenario_results),
        interval_coverage=interval_coverage,
        metric_units=metric_units,
        recommendations=recommendations,
    )


def summarize_coverage(evaluations: Iterable[VintageEvaluation]) -> CoverageReport:
    """Group scenario coverage by company and company family for review."""

    rows = tuple(evaluations)
    def aggregate(key: str) -> dict[str, dict[str, Any]]:
        output: dict[str, dict[str, Any]] = {}
        for evaluation in rows:
            group = getattr(evaluation, key)
            target = output.setdefault(group, {"vintage_count": 0, "historical_comparison_count": 0, "errors_by_metric_unit": {}, "interval_coverage": {}, "scenarios": {}})
            target["vintage_count"] += 1
            target["historical_comparison_count"] += int(evaluation.historical_comparison_claim)
            for scenario in evaluation.scenario_evaluations:
                summary = target["scenarios"].setdefault(scenario.scenario, {"forecast_count": 0, "compared_count": 0, "incomparable_count": 0})
                summary["forecast_count"] += scenario.compared_count + scenario.incomparable_count
                summary["compared_count"] += scenario.compared_count
                summary["incomparable_count"] += scenario.incomparable_count
                for row in scenario.comparisons:
                    metric_unit = f"{row.metric}|{evaluation.metric_units.get(row.metric, 'unknown')}"
                    errors = target["errors_by_metric_unit"].setdefault(metric_unit, {"signed_error_total": 0.0, "absolute_error_total": 0.0, "comparable_count": 0})
                    if row.signed_error is not None:
                        errors["signed_error_total"] += row.signed_error
                        errors["absolute_error_total"] += row.absolute_error or 0.0
                        errors["comparable_count"] += 1
            for metric, interval in evaluation.interval_coverage.items():
                metric_unit = f"{metric}|{evaluation.metric_units.get(metric, interval.get('unit', 'unknown'))}"
                coverage = target["interval_coverage"].setdefault(metric_unit, {"comparable_count": 0, "covered_count": 0})
                coverage["comparable_count"] += interval["comparable_count"]
                coverage["covered_count"] += interval["covered_count"]
        for target in output.values():
            for summary in target["scenarios"].values():
                total = summary["forecast_count"]
                summary["coverage_ratio"] = summary["compared_count"] / total if total else 0.0
            for coverage in target["interval_coverage"].values():
                coverage["coverage_ratio"] = coverage["covered_count"] / coverage["comparable_count"] if coverage["comparable_count"] else 0.0
        return output
    return CoverageReport(company=aggregate("company_id"), family=aggregate("company_family"))


__all__ = [
    "FORECAST_VINTAGE_SCHEMA",
    "ACTUAL_CAPTURE_SCHEMA",
    "ForecastVintage",
    "CapturedActual",
    "ActualCapture",
    "VintageReceipt",
    "ScenarioEvaluation",
    "VintageEvaluation",
    "CoverageReport",
    "ForecastVintageStore",
    "evaluate_vintage",
    "summarize_coverage",
]
