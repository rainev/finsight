"""Pure compiler for Batch 6 governed cash-conversion margin stresses."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from .history import HistoryObservation, summarize_history_metric
from .refresh_growth_policies import _read_private, _source_root


_SCHEMA = "FINSIGHT-MARGIN-STRESS-POLICY-1"
_GENERATOR = "backend/app/us_valuation/batch_06_launch_first.py"
_TICKERS = {"BBY", "DECK", "DRI"}


def _unsupported(ticker: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"schema_version": _SCHEMA, "status": "unsupported", "ticker": ticker, "reason": reason, **extra}


def _literal_numbers(node: ast.AST) -> tuple[float, ...] | None:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return None
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        return None
    numbers = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
            return None
        numbers.append(float(item))
    return tuple(numbers)


def _policy_rates(tree: ast.Module, ticker: str) -> tuple[float, float, float] | None:
    fields: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Policy":
            fields = [child.target.id for child in node.body if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name)]
            break
    if "working_capital_adjustment" not in fields:
        return None
    adjustment_index = fields.index("working_capital_adjustment")
    matches = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not any(isinstance(target, ast.Name) and target.id == "P" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            if not isinstance(key, ast.Constant) or key.value != ticker:
                continue
            if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name) or value.func.id != "Policy":
                continue
            keyword_values = [keyword.value for keyword in value.keywords if keyword.arg == "working_capital_adjustment"]
            argument = keyword_values[0] if keyword_values else (value.args[adjustment_index] if len(value.args) > adjustment_index else None)
            if argument is None or keyword_values and len(keyword_values) != 1:
                return None
            rates = _literal_numbers(argument)
            if rates is None or any(rate < 0 for rate in rates):
                return None
            matches.append(rates)
    if len(matches) != 1:
        return None
    return matches[0]


def _cash_metric(private: Mapping[str, Any]) -> tuple[dict[str, float] | None, dict[str, Any]]:
    profile = ((private.get("history_backed") or {}).get("source_ledger") or {}).get("company_history_profile") or {}
    rows = [row for row in profile.get("metrics", []) if isinstance(row, Mapping) and row.get("name") == "cash_conversion_margin"]
    if len(rows) != 1 or not isinstance(rows[0].get("observations"), list):
        return None, {"reason": "retained cash_conversion_margin metric is missing or ambiguous"}
    metric = rows[0]
    observations = []
    try:
        for row in metric["observations"]:
            if row.get("formula") not in {"annual cash FCFF / annual revenue", "TTM cash FCFF / TTM revenue"}:
                return None, {"reason": "cash_conversion_margin observation formula is not the governed annual formula"}
            sources = row.get("sources")
            if not isinstance(sources, list) or not sources or not all(isinstance(source, Mapping) for source in sources):
                return None, {"reason": "cash_conversion_margin observation sources are missing"}
            observations.append(HistoryObservation(
                period_role=str(row["period_role"]), period_end=str(row["period_end"]),
                fiscal_year=row.get("fiscal_year"), value=float(row["value"]),
                unit=str(row["unit"]), formula=str(row["formula"]),
                sources=tuple(dict(source) for source in sources),
            ))
    except (KeyError, TypeError, ValueError, OverflowError):
        return None, {"reason": "cash_conversion_margin observations are malformed or nonfinite"}
    recomputed = summarize_history_metric("cash_conversion_margin", observations)
    if recomputed is None:
        return None, {"reason": "cash_conversion_margin observations are empty"}
    try:
        retained = {key: float(metric[key]) for key in ("low", "base", "high")}
    except (KeyError, TypeError, ValueError):
        return None, {"reason": "cash_conversion_margin summary is incomplete"}
    if not all(math.isfinite(value) for value in retained.values()):
        return None, {"reason": "cash_conversion_margin summary is nonfinite"}
    calculated = {key: float(getattr(recomputed, key)) for key in ("low", "base", "high")}
    if any(abs(retained[key] - calculated[key]) > 1e-12 for key in retained):
        return None, {"reason": "cash_conversion_margin summary does not recompute from observations"}
    if str(metric.get("normalization_basis")) != recomputed.normalization_basis:
        return None, {"reason": "cash_conversion_margin normalization basis differs from common summarizer"}
    return calculated, {"observation_count": len(observations), "normalization_basis": recomputed.normalization_basis}


def compile_margin_stress_policy(entry: Mapping[str, Any], recipe: Mapping[str, Any]) -> dict[str, Any]:
    ticker = str(recipe.get("ticker", ""))
    if ticker not in _TICKERS:
        return _unsupported(ticker, "ticker is outside the audited Batch 6 margin-stress set")
    if not isinstance(entry, Mapping) or str(entry.get("ticker", "")) != ticker or entry.get("batch") != 6:
        return _unsupported(ticker, "registry entry is not the audited Batch 6 record")
    private, provenance = _read_private(recipe)
    if private is None:
        return _unsupported(ticker, provenance["reason"], provenance=provenance)
    issuer = private.get("issuer") if isinstance(private.get("issuer"), Mapping) else {}
    cik = str(entry.get("cik", "")).zfill(10)
    if str(issuer.get("cik", "")).zfill(10) != cik:
        return _unsupported(ticker, "retained private issuer CIK conflicts with registry", provenance=provenance)
    source_path = _source_root() / _GENERATOR
    if not source_path.is_file():
        return _unsupported(ticker, "Batch 6 generator source is unavailable", provenance=provenance)
    raw = source_path.read_bytes()
    generator_sha = hashlib.sha256(raw).hexdigest()
    try:
        tree = ast.parse(raw.decode("utf-8"), filename=_GENERATOR)
    except (SyntaxError, UnicodeDecodeError):
        return _unsupported(ticker, "Batch 6 generator source is not parseable", provenance=provenance)
    rates = _policy_rates(tree, ticker)
    if rates is None:
        return _unsupported(ticker, "working_capital_adjustment policy is missing, ambiguous, or nonfinite", provenance=provenance, generator_sha256=generator_sha)
    expected = ast.parse('tuple(max(.001,margin-policy.working_capital_adjustment[index]) for index,margin in enumerate(margins))',mode='eval').body
    formulas = [node.value for node in ast.walk(tree) if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name) and target.id=='margins' for target in node.targets)
        and ast.dump(node.value)==ast.dump(expected)]
    if len(formulas)!=1:
        return _unsupported(ticker,'governed margin stress formula or floor has changed',provenance=provenance)
    metric, metric_meta = _cash_metric(private)
    if metric is None:
        return _unsupported(ticker, metric_meta["reason"], provenance=provenance, generator_sha256=generator_sha)
    observed = tuple(metric[key] for key in ("low", "base", "high"))
    recomputed = tuple(max(0.001, observed[index] - rates[index]) for index in range(3))
    scenarios = recipe.get("scenarios")
    try:
        if any(scenarios[name].get('engine')!='constant_growth_fcff' or isinstance(scenarios[name]['inputs']['fcff_margin'],bool) for name in ('bear','base','bull')):
            raise ValueError('unsupported recipe margin scope')
        recipe_margins = tuple(float(scenarios[name]["inputs"]["fcff_margin"]) for name in ("bear", "base", "bull"))
    except (KeyError, TypeError, ValueError):
        return _unsupported(ticker, "recipe fcff_margin inputs are missing or nonnumeric", provenance=provenance, generator_sha256=generator_sha)
    if not all(math.isfinite(value) for value in recipe_margins) or any(abs(recomputed[index] - recipe_margins[index]) > 1e-12 for index in range(3)):
        return _unsupported(ticker, "recomputed margin stress does not reproduce frozen recipe", provenance=provenance, verification={"history_margin": observed, "rates": rates, "recomputed_margin": recomputed, "recipe_margin": recipe_margins})
    return {
        "schema_version": _SCHEMA,
        "status": "compiled",
        "ticker": ticker,
        "cik": cik,
        "rule": {
            "metric": "cash_conversion_margin",
            "adjustment_type": "governed_margin_stress",
            "reported_working_capital_correction": False,
            "scenario_rates": rates,
            "floor": 0.001,
            "formula": "max(0.001, history_cash_conversion_margin - scenario_rate)",
        },
        "provenance": {
            **provenance,
            "private_sha256": provenance.get("sha256"),
            "generator_path": _GENERATOR,
            "generator_sha256": generator_sha,
            "generator_policy_field": "Policy.working_capital_adjustment",
        },
        "verification": {
            "observation_count": metric_meta["observation_count"],
            "normalization_basis": metric_meta["normalization_basis"],
            "history_margin": observed,
            "scenario_rates": rates,
            "recomputed_margin": recomputed,
            "recipe_margin": recipe_margins,
            "matches_frozen_recipe": True,
        },
    }
