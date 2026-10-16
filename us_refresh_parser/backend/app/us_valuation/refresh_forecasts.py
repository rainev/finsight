"""Forecast tracking integration for deterministic U.S. refresh runs.

This module turns an already-pinned calculation recipe schedule into an
immutable forecast vintage, then optionally captures later reported actuals
and evaluates them descriptively.  It never fetches sources, rewrites recipes,
changes policy parameters, or publishes a catalog.
"""

from __future__ import annotations

from datetime import date, timedelta
import calendar
from copy import deepcopy
import json
import re
from typing import Any, Iterable, Mapping

from .catalog import canonical_json_bytes, sha256_bytes
from .calculation_recipe import evaluate_recipe
from .forecast_evaluation import ForecastDatum
from .forecast_vintage_store import ForecastVintage, ForecastVintageStore, evaluate_vintage
from .sustainable_inputs import SourceEvidence


def _persist_review(store: ForecastVintageStore, company_id: str, issued_at: str, payload: Mapping[str, Any], *, suffix: str = "") -> None:
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', company_id) or '..' in company_id or '/' in suffix or '\\' in suffix:
        raise ValueError('unsafe forecast tracking identity')
    encoded = canonical_json_bytes(payload)
    digest = sha256_bytes(encoded)[:16]
    path = store.root / "tracking" / f"{company_id}-{issued_at}{suffix}-{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != encoded:
            raise ValueError("forecast tracking receipt drift")
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)


def _prior_vintage(store: ForecastVintageStore, company_id: str, issued_at: str) -> ForecastVintage | None:
    candidates: list[ForecastVintage] = []
    for path in sorted(store.vintages_root.glob("*.json")):
        try:
            vintage = store.read_vintage(path.stem)
        except (OSError, ValueError):
            continue
        if vintage.company_id == company_id and vintage.issued_at < issued_at:
            candidates.append(vintage)
    return max(candidates, key=lambda row: (row.issued_at, row.vintage_id), default=None)


def _prior_vintages(store: ForecastVintageStore, company_id: str, issued_at: str) -> tuple[ForecastVintage, ...]:
    rows: list[ForecastVintage] = []
    for path in sorted(store.vintages_root.glob("*.json")):
        vintage = store.read_vintage(path.stem)
        if vintage.company_id == company_id and vintage.issued_at < issued_at:
            rows.append(vintage)
    return tuple(sorted(rows, key=lambda row: (row.issued_at, row.vintage_id)))


def _vintage_limitations(store: ForecastVintageStore, vintage_id: str, issued_at: str) -> tuple[str, ...]:
    protected = store.read_vintage(vintage_id).comparability_limitations
    if protected:
        return protected
    paths = sorted((store.root / "tracking").glob(f"*-{issued_at}-{vintage_id}-vintage-*.json"))
    if not paths:
        return ()
    try:
        value = json.loads(paths[-1].read_text(encoding="utf-8"))
        if sha256_bytes(canonical_json_bytes(value))[:16] != paths[-1].stem.rsplit('-',1)[-1]:
            return ('prior vintage enrichment receipt hash mismatch; comparison is blocked',)
    except (OSError, json.JSONDecodeError):
        return ("prior vintage enrichment receipt is invalid; comparison is blocked",)
    limitations = value.get("limitations", [])
    return tuple(str(item) for item in limitations) if isinstance(limitations, list) else ("prior vintage limitations are invalid; comparison is blocked",)


def _ledger_source(
    ledger: Mapping[str, Any],
    metric: str,
    value: float,
    *,
    company_cik: str,
    issued_at: str,
    ledger_hash: str,
) -> tuple[SourceEvidence | None, str | None]:
    raw_sources = ledger.get("reported_sources") or ledger.get("sources")
    raw = raw_sources.get(metric) if isinstance(raw_sources, Mapping) else None
    if raw is None and isinstance(raw_sources, Mapping):
        aliases = {"cash_fcff": ("ttm_cash_fcff", "cash_fcff"), "affo": ("ttm_affo", "affo"), "fcfe": ("ttm_fcfe", "fcfe"), "residual_income": ("ttm_residual_income_per_share", "residual_income_per_share")}
        for key in aliases.get(metric, (metric,)):
            if key in raw_sources:
                raw = raw_sources[key]
                break
    if isinstance(raw, Mapping) and isinstance(raw.get("source"), Mapping):
        raw = raw["source"]
    if isinstance(raw, Mapping):
        nested: list[Mapping[str, Any]] = [raw]
        for container_name in ("reported_sources", "reported", "sources"):
            container = raw.get(container_name)
            if isinstance(container, Mapping):
                for key in (metric, f"ttm_{metric}", "cash_fcff", "ttm_cash_fcff"):
                    item = container.get(key)
                    if isinstance(item, Mapping):
                        nested.append(item)
                        source_rows = item.get("sources")
                        if isinstance(source_rows, list):
                            nested.extend(row for row in source_rows if isinstance(row, Mapping))
            elif isinstance(container, list):
                nested.extend(row for row in container if isinstance(row, Mapping))
        raw = next((item for item in nested if any(key in item for key in ("source_id", "accession"))), raw)
    if not isinstance(raw, Mapping):
        return None, f"reported source for {metric} is missing"
    source_id = raw.get("source_id", raw.get("accession"))
    period_end = raw.get("period_end", raw.get("end"))
    filing_date = raw.get("filing_date", raw.get("filed"))
    field = raw.get("field", raw.get("concept", metric))
    required_values = (source_id, raw.get("cik", company_cik), field, raw.get("unit"), period_end, filing_date)
    if any(not isinstance(value, str) or not value for value in required_values):
        return None, f"reported source for {metric} lacks explicit source identity/timing/unit"
    source = {"source_id": source_id, "cik": raw.get("cik", company_cik), "field": field, "unit": raw["unit"], "period_end": period_end, "filing_date": filing_date}
    source["reported_value"] = raw.get("reported_value", raw.get("value", value))
    if raw.get("period_start") is not None:
        source["period_start"] = raw["period_start"]
    source["reported_vs_estimated"] = raw.get("reported_vs_estimated", "reported")
    try:
        return SourceEvidence(**source), ledger_hash
    except ValueError as exc:
        return None, f"reported source for {metric} is invalid: {exc}"


def _current_actuals_for_vintage(
    vintage: ForecastVintage,
    ledger: Mapping[str, Any],
    *,
    company_cik: str,
    issued_at: str,
) -> tuple[tuple[ForecastDatum, ...], list[str], dict[str, str]]:
    ledger_hash = sha256_bytes(canonical_json_bytes(ledger))
    period_end = _period_end_from_ledger(ledger).isoformat()
    limitations: list[str] = []
    actuals: list[ForecastDatum] = []
    hashes: dict[str, str] = {}
    calendar_standard = str(ledger.get("calendar_standard") or ledger.get("fiscal_calendar") or "calendar").lower()
    period_date = date.fromisoformat(period_end)
    if calendar_standard in {"52_week", "53_week", "52/53_week", "retail_52_53_week"} or period_date.day != calendar.monthrange(period_date.year, period_date.month)[1]:
        return (), ["current fiscal calendar is unmapped; actual comparison is blocked"], {}
    for key in sorted({row.match_key for rows in vintage.scenarios.values() for row in rows}):
        metric, fiscal_period = key
        if not fiscal_period.startswith("TTM:") or fiscal_period.removeprefix("TTM:") != period_end:
            limitations.append(f"no exact current period match for {metric}/{fiscal_period}")
            continue
        metric_policy = metric
        values_map = ledger.get("values") if isinstance(ledger.get("values"), Mapping) else {}
        if metric == "cash_fcff":
            value = ledger.get("ttm_cash_fcff", ledger.get("cash_fcff", values_map.get("ttm_cash_fcff")))
        elif metric == "residual_income":
            value = ledger.get("ttm_residual_income_per_share", ledger.get("residual_income_per_share", values_map.get("residual_income_per_share")))
            if value is None:
                limitations.append("residual-income per-share actual is unavailable; common earnings cannot be relabeled")
                continue
        else:
            value = ledger.get(f"ttm_{metric}", ledger.get(metric, values_map.get(f"ttm_{metric}", values_map.get(metric))))
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            limitations.append(f"current ledger metric {metric} is unavailable")
            continue
        source, error = _ledger_source(ledger, metric_policy, float(value), company_cik=company_cik, issued_at=issued_at, ledger_hash=ledger_hash)
        if source is None:
            limitations.append(error or f"current ledger source for {metric} is unavailable")
            continue
        if source.period_end != period_end or source.filing_date <= vintage.issued_at:
            limitations.append(f"current source for {metric}/{fiscal_period} is not subsequent and exact")
            continue
        expected_intervals = {(row.source.period_start, row.source.period_end, row.source.unit)
                              for rows in vintage.scenarios.values() for row in rows if row.match_key == key}
        if expected_intervals != {(source.period_start, source.period_end, source.unit)}:
            limitations.append(f'current source for {metric}/{fiscal_period} has an incomparable interval or unit')
            continue
        actuals.append(ForecastDatum(metric, fiscal_period, float(value), source))
        hashes[source.source_id] = ledger_hash
    return tuple(actuals), limitations, hashes


def _iso(value: str, field: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    return value.strip()


def _source(value: object, *, source_evidence: Mapping[str, SourceEvidence], source_id: str) -> SourceEvidence:
    if isinstance(value, SourceEvidence):
        return value
    if isinstance(value, Mapping):
        return SourceEvidence(**dict(value))
    found = source_evidence.get(source_id)
    if not isinstance(found, SourceEvidence):
        raise ValueError(f"forecast source evidence is missing for {source_id}")
    return found


def _schedule_for(recipe: Mapping[str, Any], scenario: str) -> list[Mapping[str, Any]]:
    candidates = []
    top = recipe.get("forecast_schedule")
    if isinstance(top, Mapping):
        candidates.extend((top.get(scenario), top.get("rows")))
    spec = recipe.get("scenarios", {}).get(scenario)
    if isinstance(spec, Mapping):
        candidates.extend((spec.get("forecast_schedule"), spec.get("schedule")))
        inputs = spec.get("inputs")
        if isinstance(inputs, Mapping):
            candidates.extend((inputs.get("forecast_schedule"), inputs.get("schedule")))
    for candidate in candidates:
        if isinstance(candidate, list) and candidate and all(isinstance(row, Mapping) for row in candidate):
            return [dict(row) for row in candidate]
    raise ValueError(f"recipe forecast schedule is missing for {scenario}")


def _source_hashes(recipe: Mapping[str, Any], supplied: Mapping[str, str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    provenance = recipe.get("provenance")
    if isinstance(provenance, Mapping):
        raw = provenance.get("source_hashes")
        if isinstance(raw, Mapping):
            result.update({str(key): str(value) for key, value in raw.items()})
        source_hash = provenance.get("private_sha256")
        if isinstance(source_hash, str) and source_hash:
            result.setdefault("recipe-private", source_hash)
    if supplied:
        result.update({str(key): str(value) for key, value in supplied.items()})
    return result


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def _anniversary_start(period_end: date) -> str:
    try:
        prior = period_end.replace(year=period_end.year - 1)
    except ValueError:
        prior = period_end.replace(year=period_end.year - 1, day=28)
    return (prior + timedelta(days=1)).isoformat()


def _period_end_from_ledger(ledger: Mapping[str, Any]) -> date:
    filing = ledger.get("controlling_filing") if isinstance(ledger.get("controlling_filing"), Mapping) else ledger
    value = filing.get("reportDate", filing.get("period_end")) if isinstance(filing, Mapping) else None
    if not isinstance(value, str):
        raise ValueError("current ledger period_end is required for forecast labels")
    return date.fromisoformat(value)


def enrich_recipe_forecast(
    recipe: Mapping[str, Any],
    ledger: Mapping[str, Any],
    *,
    issued_at: str,
    company_cik: str,
) -> tuple[dict[str, Any], dict[str, SourceEvidence], dict[str, str], tuple[str, ...]]:
    """Build explicitly dated, source-hashed prospective rows from a recipe trace."""
    issued = _iso(issued_at, "issued_at")
    current_period = _period_end_from_ledger(ledger)
    source_filing_date = issued
    recipe_copy = deepcopy(dict(recipe))
    source_evidence: dict[str, SourceEvidence] = {}
    source_hashes: dict[str, str] = {}
    limitations: list[str] = []
    calendar_standard = str(ledger.get("calendar_standard") or ledger.get("fiscal_calendar") or "calendar").lower()
    month_end = calendar.monthrange(current_period.year, current_period.month)[1]
    if calendar_standard in {"52_week", "53_week", "52/53_week", "retail_52_53_week"} or current_period.day != month_end:
        limitations.append("52/53-week fiscal calendar mapping is unverified; exact actual-period comparisons remain incomparable")
    ledger_hash = sha256_bytes(canonical_json_bytes(ledger))
    recipe_hash_value = sha256_bytes(canonical_json_bytes(recipe))
    evaluated = evaluate_recipe(recipe)
    schedules: dict[str, list[dict[str, Any]]] = {}
    for scenario in ("bear", "base", "bull"):
        spec = recipe["scenarios"][scenario]
        inputs = spec.get("inputs", {}) if isinstance(spec, Mapping) else {}
        trace = evaluated["scenarios"][scenario].get("trace", {})
        detail = trace.get("detail") if isinstance(trace, Mapping) else None
        values: list[float]
        metric = "cash_fcff"
        unit = "USD"
        if isinstance(detail, Mapping) and isinstance(detail.get("forecast_schedule"), list):
            values = [float(row["cash_fcff"]) for row in detail["forecast_schedule"] if isinstance(row, Mapping) and "cash_fcff" in row]
        elif spec.get("engine") == "cash_schedule" and isinstance(inputs.get("cash_flows"), list):
            metric = str(recipe.get("forecast_metric") or "")
            if metric not in {"affo", "fcfe", "cash_fcff"}:
                raise ValueError("cash_schedule recipe requires explicit forecast_metric (affo, fcfe, or cash_fcff)")
            values = [float(value) for value in inputs["cash_flows"]]
        elif spec.get("engine") == "constant_growth_fcff":
            metric = "cash_fcff"
            revenue = float(inputs["revenue"])
            margin = float(inputs["fcff_margin"])
            growth = float(inputs["growth"])
            values = [revenue * margin * (1.0 + growth) ** year for year in range(1, 6)]
        elif spec.get("engine") == "residual_income":
            metric = "residual_income"
            unit = "USD/share"
            schedule = detail.get("schedule") if isinstance(detail, Mapping) else None
            if not isinstance(schedule, list):
                raise ValueError("residual-income trace schedule is missing")
            values = [float(row["residual_income_per_share"]) for row in schedule if isinstance(row, Mapping) and "residual_income_per_share" in row]
        else:
            raise ValueError(f"recipe engine {spec.get('engine')} has no supported forecast schedule")
        if not values:
            raise ValueError(f"recipe forecast schedule is empty for {scenario}")
        rows: list[dict[str, Any]] = []
        for index, value in enumerate(values, start=1):
            period_end = _add_months(current_period, 12 * index)
            fiscal_period = f"TTM:{period_end.isoformat()}"
            source_id = f"recipe-{recipe_hash_value[:12]}-{scenario}-{index}"
            source_hash = sha256_bytes(canonical_json_bytes({"recipe": recipe_hash_value, "ledger": ledger_hash, "source_id": source_id, "value": value, "period_end": period_end.isoformat()}))
            source_evidence[source_id] = SourceEvidence(
                source_id=source_id,
                cik=str(company_cik).zfill(10),
                field=metric,
                unit=unit,
                reported_value=value,
                period_end=period_end.isoformat(),
                period_start=_anniversary_start(period_end),
                filing_date=source_filing_date,
                reported_vs_estimated="estimated",
            )
            source_hashes[source_id] = source_hash
            rows.append({"metric": metric, "fiscal_period": fiscal_period, "value": value, "source_id": source_id})
        schedules[scenario] = rows
    recipe_copy["forecast_schedule"] = schedules
    recipe_copy["forecast_current_period_end"] = current_period.isoformat()
    recipe_copy["forecast_labeling"] = "annual_ttm_forward_from_current_ledger_period"
    return recipe_copy, source_evidence, source_hashes, tuple(limitations)


def issue_recipe_vintage(
    *,
    store: ForecastVintageStore,
    recipe: Mapping[str, Any],
    vintage_id: str,
    company_id: str,
    company_cik: str,
    company_family: str,
    model_version: str | None = None,
    policy_version: str | None = None,
    issued_at: str,
    source_cutoff: str,
    source_evidence: Mapping[str, SourceEvidence] | None = None,
    source_hashes: Mapping[str, str] | None = None,
    ledger: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Issue one immutable vintage from an explicitly labeled recipe schedule."""
    issued = _iso(issued_at, "issued_at")
    cutoff = _iso(source_cutoff, "source_cutoff")
    if cutoff > issued:
        raise ValueError("source_cutoff cannot be after issued_at")
    evidence = dict(source_evidence or {})
    recipe_input = recipe
    enrichment_limitations: tuple[str, ...] = ()
    if ledger is not None and "forecast_schedule" not in recipe:
        recipe_input, enriched_evidence, enriched_hashes, enrichment_limitations = enrich_recipe_forecast(
            recipe, ledger, issued_at=issued, company_cik=company_cik
        )
        evidence.update(enriched_evidence)
        source_hashes = {**enriched_hashes, **(source_hashes or {})}
    hashes = _source_hashes(recipe_input, source_hashes)
    scenarios: dict[str, tuple[ForecastDatum, ...]] = {}
    for scenario in ("bear", "base", "bull"):
        rows: list[ForecastDatum] = []
        for row in _schedule_for(recipe_input, scenario):
            metric = _text(row.get("metric") or recipe_input.get("forecast_metric"), "forecast metric")
            fiscal_period = _text(row.get("fiscal_period"), "forecast fiscal_period")
            source_value = row.get("source")
            source_id_value = row.get("source_id")
            if source_id_value is None and isinstance(source_value, Mapping):
                source_id_value = source_value.get("source_id")
            source_id = _text(source_id_value, "forecast source_id")
            source = _source(source_value, source_evidence=evidence, source_id=source_id)
            value = row.get("value", row.get("forecast_value"))
            if value is None:
                raise ValueError(f"forecast value is missing for {scenario}/{fiscal_period}")
            rows.append(ForecastDatum(metric, fiscal_period, float(value), source))
        scenarios[scenario] = tuple(rows)
    vintage = ForecastVintage(
        vintage_id=_text(vintage_id, "vintage_id"),
        company_id=_text(company_id, "company_id"),
        company_cik=_text(company_cik, "company_cik").zfill(10),
        company_family=_text(company_family, "company_family"),
        model_version=_text(model_version or recipe.get("model_version") or recipe.get("recipe_version"), "model_version"),
        policy_version=_text(
            policy_version
            or recipe.get("policy_version")
            or (recipe.get("provenance", {}).get("private_schema_version") if isinstance(recipe.get("provenance"), Mapping) else None)
            or recipe.get("recipe_version"),
            "policy_version",
        ),
        issued_at=issued,
        frozen_cutoff=cutoff,
        scenarios=scenarios,
        source_hashes=hashes,
        comparability_limitations=enrichment_limitations,
    )
    receipt = store.write_vintage(vintage)
    result = {"vintage": vintage.as_dict(), "receipt": receipt.as_dict(), "review_only": True, "limitations": list(enrichment_limitations)}
    _persist_review(store, vintage.company_id, issued, result, suffix=f"-{vintage.vintage_id}-vintage")
    return result


def refresh_forecast_tracking(
    *,
    store: ForecastVintageStore,
    recipe: Mapping[str, Any],
    vintage_id: str,
    company_id: str,
    company_cik: str,
    company_family: str,
    model_version: str | None = None,
    policy_version: str | None = None,
    issued_at: str,
    source_cutoff: str,
    actuals: Iterable[ForecastDatum] = (),
    actual_source_hashes: Mapping[str, str] | None = None,
    actual_captured_at: str | None = None,
    actual_cutoff: str | None = None,
    corporate_event_periods: Iterable[str] = (),
    source_evidence: Mapping[str, SourceEvidence] | None = None,
    source_hashes: Mapping[str, str] | None = None,
    ledger: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Issue/evaluate a vintage and return review-only tracking evidence."""
    issued = issue_recipe_vintage(
        store=store,
        recipe=recipe,
        vintage_id=vintage_id,
        company_id=company_id,
        company_cik=company_cik,
        company_family=company_family,
        model_version=model_version,
        policy_version=policy_version,
        issued_at=issued_at,
        source_cutoff=source_cutoff,
        source_evidence=source_evidence,
        source_hashes=source_hashes,
        ledger=ledger,
    )
    vintage = store.read_vintage(vintage_id)
    rows = tuple(actuals)
    report: dict[str, Any] = {**issued, "recommendations": [], "corporate_event_incomparability": [], "actual_capture": None}
    if not rows:
        evaluation = evaluate_vintage(vintage, (), frozen_cutoff=issued_at)
    else:
        if actual_captured_at is None or actual_cutoff is None:
            raise ValueError("actual_captured_at and actual_cutoff are required when actuals are supplied")
        capture = store.capture_actuals(
            vintage_id,
            rows,
            actual_source_hashes or {},
            captured_at=actual_captured_at,
            frozen_cutoff=actual_cutoff,
        )
        report["actual_capture"] = capture.as_dict()
        selected = store.select_actuals(vintage_id, basis="first_reported")
        event_periods = {_text(str(period), "corporate event period") for period in corporate_event_periods}
        comparable_rows = tuple(row for row in selected if row.fiscal_period not in event_periods)
        evaluation = evaluate_vintage(vintage, comparable_rows, frozen_cutoff=actual_cutoff)
        report["corporate_event_incomparability"] = sorted(event_periods)
        if event_periods:
            report["recommendations"].append("Corporate-event periods remain incomparable; review event treatment before any model change.")
    evaluation_payload = evaluation.as_dict()
    compared_count = sum(row.compared_count for row in evaluation.scenario_evaluations)
    if report["corporate_event_incomparability"] and compared_count == 0:
        evaluation_payload["status"] = "historical_data_limitation"
        evaluation_payload["historical_comparison_claim"] = False
    report["evaluation"] = evaluation_payload
    report["recommendations"].extend(evaluation.recommendations)
    report["review_only"] = True
    report["policy_change_applied"] = False
    return report


def track_company_refresh(
    *,
    store: ForecastVintageStore,
    recipe: Mapping[str, Any],
    ledger: Mapping[str, Any],
    issued_at: str,
    source_cutoff: str,
    company_id: str,
    company_cik: str,
    company_family: str,
    model_version: str | None = None,
    policy_version: str | None = None,
    vintage_id: str | None = None,
    corporate_event_periods: Iterable[str] = (),
) -> dict[str, Any]:
    """Evaluate the prior vintage first, then issue the next prospective vintage.

    The current ledger is never compared against the vintage created by this
    call.  If no prior vintage exists, the historical result is explicitly
    limited rather than fabricated.
    """
    issued = _iso(issued_at, "issued_at")
    cutoff = _iso(source_cutoff, "source_cutoff")
    priors = _prior_vintages(store, company_id, issued)
    limitations: list[str] = []
    evaluations: list[dict[str, Any]] = []
    captures: list[dict[str, Any]] = []
    if not priors:
        limitations.append("no previously issued immutable vintage exists for historical comparison")
    else:
        event_periods = {_text(str(period), "corporate event period") for period in corporate_event_periods}
        for prior in priors:
            prior_limitations = _vintage_limitations(store, prior.vintage_id, prior.issued_at)
            if prior_limitations:
                limitations.extend(f"{prior.vintage_id}: {item}" for item in prior_limitations)
                evaluation_payload = evaluate_vintage(prior, (), frozen_cutoff=issued).as_dict()
                evaluation_payload["status"] = "historical_data_limitation"
                evaluation_payload["historical_comparison_claim"] = False
                evaluations.append({"vintage_id": prior.vintage_id, "evaluation": evaluation_payload})
                continue
            actuals, actual_limitations, actual_hashes = _current_actuals_for_vintage(
                prior, ledger, company_cik=company_cik, issued_at=issued
            )
            limitations.extend(f"{prior.vintage_id}: {item}" for item in actual_limitations)
            if actuals:
                capture = store.capture_actuals(prior.vintage_id, actuals, actual_hashes, captured_at=issued, frozen_cutoff=issued)
                captures.append(capture.as_dict())
                selected = store.select_actuals(prior.vintage_id, basis="first_reported")
                comparable = tuple(row for row in selected if row.fiscal_period not in event_periods)
                evaluation_payload = evaluate_vintage(prior, comparable, frozen_cutoff=issued).as_dict()
                if event_periods:
                    limitations.append(f"{prior.vintage_id}: corporate-event periods remain incomparable until event mapping is verified")
                    evaluation_payload["historical_comparison_claim"] = False
                    evaluation_payload["status"] = "historical_data_limitation"
            else:
                evaluation_payload = evaluate_vintage(prior, (), frozen_cutoff=issued).as_dict()
                evaluation_payload["status"] = "historical_data_limitation"
                evaluation_payload["historical_comparison_claim"] = False
            evaluations.append({"vintage_id": prior.vintage_id, "evaluation": evaluation_payload})
    new_id = vintage_id or f"{company_id}-{issued}"
    try:
        issued_payload = issue_recipe_vintage(
            store=store,
            recipe=recipe,
            ledger=ledger,
            vintage_id=new_id,
            company_id=company_id,
            company_cik=company_cik,
            company_family=company_family,
            model_version=model_version,
            policy_version=policy_version,
            issued_at=issued,
            source_cutoff=cutoff,
        )
    except ValueError as exc:
        if "supported forecast schedule" not in str(exc) and "forecast_metric" not in str(exc):
            raise
        limitations.append(f"new prospective vintage was not issued: {exc}")
        report = {
            "company_id": company_id,
            "issued_at": issued,
            "source_cutoff": cutoff,
            "prior_vintage_ids": [prior.vintage_id for prior in priors],
            "prior_evaluations": evaluations,
            "actual_captures": captures,
            "new_vintage": None,
            "limitations": limitations,
            "review_only": True,
            "policy_change_applied": False,
        }
        report["prior_vintage_id"] = report["prior_vintage_ids"][-1] if report["prior_vintage_ids"] else None
        report["prior_evaluation"] = evaluations[-1]["evaluation"] if evaluations else None
        report["actual_capture"] = captures[-1] if captures else None
        _persist_review(store, company_id, issued, report)
        return report
    report = {
        "company_id": company_id,
        "issued_at": issued,
        "source_cutoff": cutoff,
        "prior_vintage_ids": [prior.vintage_id for prior in priors],
        "prior_evaluations": evaluations,
        "actual_captures": captures,
        "new_vintage": issued_payload,
        "limitations": limitations + list(issued_payload.get("limitations", [])),
        "review_only": True,
        "policy_change_applied": False,
    }
    report["prior_vintage_id"] = report["prior_vintage_ids"][-1] if report["prior_vintage_ids"] else None
    report["prior_evaluation"] = evaluations[-1]["evaluation"] if evaluations else None
    report["actual_capture"] = captures[-1] if captures else None
    _persist_review(store, company_id, issued, report, suffix=f"-{new_id}")
    return report


__all__ = ["enrich_recipe_forecast", "issue_recipe_vintage", "refresh_forecast_tracking", "track_company_refresh"]
