"""Pure compiler for audited history-bounded revenue-growth rules.

The compiler reads retained evidence and parses the legacy generator source as
data with ``ast``/``literal_eval``.  It never imports or executes the legacy
generator and emits no source amounts or dates as policy constants.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from .history import HistoryObservation, summarize_history_metric


_SUPPORTED_BATCHES = {
    5: "backend/app/us_valuation/batch_05_launch_first.py",
    6: "backend/app/us_valuation/batch_06_launch_first.py",
    7: "backend/app/us_valuation/batch_07_history.py",
    8: "backend/app/us_valuation/batch_08_history.py",
    9: "backend/app/us_valuation/batch_09_history.py",
    10: "backend/app/us_valuation/batch_10_history.py",
    18: "backend/app/us_valuation/batch_18_history.py",
    19: "backend/app/us_valuation/batch_19_history.py",
    21: "backend/app/us_valuation/batch_21_history.py",
    22: "backend/app/us_valuation/batch_22_history.py",
    23: "backend/app/us_valuation/batch_23_history.py",
    24: "backend/app/us_valuation/batch_24_history.py",
    25: "backend/app/us_valuation/batch_25_history.py",
    26: "backend/app/us_valuation/batch_26_history.py",
    27: "backend/app/us_valuation/batch_27_history.py",
    29: "backend/app/us_valuation/batch_29_history.py",
    30: "backend/app/us_valuation/batch_30_history.py",
    31: "backend/app/us_valuation/batch_31_history.py",
    32: "backend/app/us_valuation/batch_32_history.py",
    37: "backend/app/us_valuation/batch_37_history.py",
}
AUDITED_GROWTH_TICKERS = frozenset({"GWW", "GNRC", "IR", "BR", "HLT", "KO", "PEP", "HRL", "PG",
    "ADI", "ADP", "ADSK", "ALLE", "AMAT", "BBY", "BF.B", "BKNG", "BLDR", "CASY",
    "CDW", "CIEN", "CPRT", "CSX", "DDOG", "DOV", "DPZ", "CMG", "DECK", "DRI", "MAS", "MSI", "MCO",
    "FTV", "GEV", "HUBB", "JCI", "LDOS", "OTIS", "PWR", "ROK", "VLTO", "WAB", "WM"})
_REVENUE_GROWTH_NAMES = {"gm", "hist_growth", "growth_metric"}
_SCHEMA = "FINSIGHT-HISTORY-GROWTH-POLICY-1"


@dataclass(frozen=True)
class _Clamp:
    floor: float
    cap: float | None
    cap_index: int | None
    operand: str


def _unsupported(ticker: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"schema_version": _SCHEMA, "status": "unsupported", "ticker": ticker, "reason": reason, **extra}


def _number(node: ast.AST) -> float | None:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _target_name(node: ast.AST) -> str | None:
    return node.id if isinstance(node, ast.Name) else None


def _policy_fields(tree: ast.Module) -> list[str]:
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Policy":
            continue
        fields: list[str] = []
        for child in node.body:
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                fields.append(child.target.id)
        return fields
    return []


def _policy_growth_caps(tree: ast.Module, ticker: str) -> tuple[tuple[float, float, float] | None, str | None]:
    fields = _policy_fields(tree)
    if "growth" not in fields:
        return None, None
    growth_index = fields.index("growth")
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not any(_target_name(t) == "P" for t in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            if _number(key) is not None or not isinstance(key, ast.Constant) or key.value != ticker:
                continue
            if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name) or value.func.id != "Policy":
                continue
            if len(value.args) <= growth_index:
                return None, "declared Policy growth tuple is missing"
            try:
                growth = ast.literal_eval(value.args[growth_index])
            except (ValueError, TypeError, SyntaxError):
                return None, "declared Policy growth tuple is not a literal"
            if not isinstance(growth, (tuple, list)) or len(growth) != 3:
                return None, "declared Policy growth tuple is not three-sided"
            if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(float(x)) for x in growth):
                return None, "declared Policy growth tuple is nonnumeric"
            return tuple(float(x) for x in growth), "declared_P[ticker].growth"
    return None, "ticker has no declared Policy growth tuple"


def _parse_clamp(node: ast.AST) -> _Clamp | None:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "max" or len(node.args) != 2 or node.keywords:
        return None
    floor = _number(node.args[0])
    inner = node.args[1]
    if floor is None or not isinstance(inner, ast.Call) or not isinstance(inner.func, ast.Name) or inner.func.id != "min" or len(inner.args) != 2 or inner.keywords:
        return None
    cap = _number(inner.args[0])
    cap_index = None
    cap_node = inner.args[0]
    if isinstance(cap_node, ast.Subscript) and isinstance(cap_node.value, ast.Attribute):
        if isinstance(cap_node.value.value, ast.Name) and cap_node.value.value.id in {"p", "policy"} and cap_node.value.attr == "growth":
            index_node = cap_node.slice
            cap_index = _number(index_node)
            if cap_index is not None and cap_index.is_integer():
                cap_index = int(cap_index)
            else:
                cap_index = None
    if cap is None and cap_index is None:
        return None
    operand = inner.args[1]
    if isinstance(operand, ast.Attribute) and isinstance(operand.value, ast.Name):
        operand_name = f"{operand.value.id}.{operand.attr}"
    elif isinstance(operand, ast.Name):
        operand_name = operand.id
    else:
        return None
    return _Clamp(floor=floor, cap=cap, cap_index=cap_index, operand=operand_name)


def _metric_bindings(tree: ast.Module) -> set[str]:
    bound: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        targets: list[str] = []
        if len(node.targets) == 1 and isinstance(node.targets[0], (ast.Tuple, ast.List)):
            if not all(isinstance(target, ast.Name) for target in node.targets[0].elts):
                continue
            targets = [target.id for target in node.targets[0].elts]
            values = list(node.value.elts) if isinstance(node.value, (ast.Tuple, ast.List)) else []
            if len(targets) != len(values):
                continue
            for target, value in zip(targets, values):
                if (
                    isinstance(value, ast.Call)
                    and not value.keywords
                    and isinstance(value.func, ast.Attribute)
                    and value.func.attr == "metric"
                    and len(value.args) == 1
                    and isinstance(value.args[0], ast.Constant)
                    and value.args[0].value == "revenue_growth"
                ):
                    bound.add(target)
        elif len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
            if (
                isinstance(value, ast.Call)
                and not value.keywords
                and isinstance(value.func, ast.Attribute)
                and value.func.attr == "metric"
                and len(value.args) == 1
                and isinstance(value.args[0], ast.Constant)
                and value.args[0].value == "revenue_growth"
            ):
                bound.add(node.targets[0].id)
    return bound


def _find_clamps(tree: ast.Module, metric_bindings: set[str]) -> tuple[list[_Clamp], str] | str | None:
    matches: list[tuple[list[_Clamp], str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(_target_name(target) == "growth" for target in node.targets):
            continue
        value = node.value
        if isinstance(value, ast.Tuple) and len(value.elts) == 3:
            clamps = [_parse_clamp(element) for element in value.elts]
            if (
                all(clamp is not None for clamp in clamps)
                and all(clamp.operand.split(".")[0] in _REVENUE_GROWTH_NAMES for clamp in clamps if clamp is not None)
                and len({clamp.operand.split(".")[0] for clamp in clamps if clamp is not None}) == 1
                and next(iter({clamp.operand.split(".")[0] for clamp in clamps if clamp is not None}), None) in metric_bindings
                and [clamp.operand.split(".")[-1] for clamp in clamps if clamp is not None] == ["low", "base", "high"]
            ):
                matches.append(([clamp for clamp in clamps if clamp is not None], "three_sided_clamp"))
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "tuple" and len(value.args) == 1 and not value.keywords:
            generator = value.args[0]
            if isinstance(generator, ast.GeneratorExp):
                clamp = _parse_clamp(generator.elt)
                comprehension = generator.generators[0] if len(generator.generators) == 1 else None
                generator_iter = comprehension.iter if comprehension is not None else None
                generator_target = comprehension.target if comprehension is not None else None
                metric_elts = generator_iter if isinstance(generator_iter, ast.Tuple) else None
                expected = []
                if isinstance(metric_elts, ast.Tuple) and comprehension is not None and not comprehension.ifs and not comprehension.is_async and len(metric_elts.elts) == 3:
                    expected = [
                        f"{elt.value.id}.{elt.attr}"
                        for elt in metric_elts.elts
                        if isinstance(elt, ast.Attribute) and isinstance(elt.value, ast.Name)
                    ]
                if (
                    clamp is not None
                    and isinstance(generator_target, ast.Name)
                    and clamp.operand == generator_target.id
                    and [item.split(".")[-1] for item in expected] == ["low", "base", "high"]
                    and all(item.split(".")[0] in _REVENUE_GROWTH_NAMES for item in expected)
                    and len({item.split(".")[0] for item in expected}) == 1
                    and (expected[0].split(".")[0] if expected else None) in metric_bindings
                ):
                    matches.append(([clamp, clamp, clamp], "uniform_clamp"))
    if len(matches) > 1:
        return "ambiguous"
    if matches:
        return matches[0]
    return None


def _source_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_private(recipe: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    provenance = recipe.get("provenance") if isinstance(recipe.get("provenance"), Mapping) else {}
    source_path = provenance.get("source_path")
    if not isinstance(source_path, str):
        return None, {"reason": "recipe provenance source_path is missing"}
    path = Path(source_path)
    if not path.is_file():
        return None, {"reason": "recipe provenance source_path is unavailable", "source_path": source_path}
    raw = path.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    expected_sha = provenance.get("private_sha256")
    if not isinstance(expected_sha,str) or len(expected_sha)!=64 or any(char not in '0123456789abcdef' for char in expected_sha):
        return None, {'reason':'private provenance SHA is missing or malformed','source_path':source_path}
    if isinstance(expected_sha, str) and actual_sha != expected_sha:
        return None, {"reason": "private provenance SHA mismatch", "source_path": source_path, "actual_sha256": actual_sha, "expected_sha256": expected_sha}
    try:
        private = json.loads(raw)
    except json.JSONDecodeError:
        return None, {"reason": "private provenance is not valid JSON", "source_path": source_path}
    return private, {"source_path": source_path, "sha256": actual_sha, "expected_sha256": expected_sha}


def _metric(private: Mapping[str, Any]) -> tuple[dict[str, float] | None, dict[str, Any]]:
    profile = ((private.get("history_backed") or {}).get("source_ledger") or {}).get("company_history_profile") or {}
    metrics = profile.get("metrics")
    if not isinstance(metrics, list):
        return None, {"reason": "retained company history profile is missing"}
    rows = [row for row in metrics if isinstance(row, Mapping) and row.get("name") == "revenue_growth"]
    if len(rows) != 1:
        return None, {"reason": "retained revenue_growth metric is missing or ambiguous"}
    row = rows[0]
    observations = row.get("observations")
    if not isinstance(observations, list) or not observations:
        return None, {"reason": "retained revenue_growth observations are missing"}
    history_rows: list[HistoryObservation] = []
    try:
        for observation in observations:
            if observation.get("formula") != "current annual revenue / prior annual revenue - 1":
                return None, {"reason": "retained revenue_growth observation formula is not the governed annual formula"}
            sources = observation.get("sources")
            if not isinstance(sources, list) or not sources or not all(isinstance(source, Mapping) for source in sources):
                return None, {"reason": "retained revenue_growth observation sources are missing"}
            history_rows.append(
                HistoryObservation(
                    period_role=str(observation["period_role"]),
                    period_end=str(observation["period_end"]),
                    fiscal_year=observation.get("fiscal_year"),
                    value=float(observation["value"]),
                    unit=str(observation["unit"]),
                    formula=str(observation["formula"]),
                    sources=tuple(dict(source) for source in sources),
                )
            )
    except (KeyError, TypeError, ValueError, OverflowError):
        return None, {"reason": "retained revenue_growth observations are malformed or nonfinite"}
    recomputed = summarize_history_metric("revenue_growth", history_rows)
    if recomputed is None:
        return None, {"reason": "retained revenue_growth observations are empty"}
    try:
        retained = {key: float(row[key]) for key in ("low", "base", "high")}
    except (KeyError, TypeError, ValueError):
        return None, {"reason": "retained revenue_growth metric is incomplete"}
    if not all(math.isfinite(value) for value in retained.values()):
        return None, {"reason": "retained revenue_growth summary is malformed or nonfinite"}
    calculated = {key: float(getattr(recomputed, key)) for key in ("low", "base", "high")}
    if any(abs(retained[key] - calculated[key]) > 1e-12 for key in retained):
        return None, {"reason": "retained revenue_growth summary does not recompute from observations"}
    basis = str(row.get("normalization_basis", ""))
    if basis != recomputed.normalization_basis:
        return None, {"reason": "retained revenue_growth normalization basis differs from common summarizer"}
    count = len(history_rows)
    expected_summary = "minimum_median_maximum" if count < 4 else "quantile_25_median_quantile_75"
    return calculated, {"summary_rule": expected_summary, "observation_count": count, "normalization_basis": basis}


def _generator_rule(ticker: str, batch: Any) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if isinstance(batch, bool) or not isinstance(batch, int) or batch not in _SUPPORTED_BATCHES:
        return None, {"reason": "no audited generator mapping for batch"}
    relative = _SUPPORTED_BATCHES[batch]
    path = _source_root() / relative
    if not path.is_file():
        return None, {"reason": "audited generator source is unavailable", "generator_path": relative}
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        tree = ast.parse(raw.decode("utf-8"), filename=relative)
    except (SyntaxError, UnicodeDecodeError):
        return None, {"reason": "audited generator source is not parseable", "generator_path": relative}
    # A ticker-specific override supersedes the common expression. Never
    # silently compile that expression for an overridden issuer.
    override_keys_verified = False
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(_target_name(target)=='GROWTH_OVERRIDES' for target in node.targets):
            try:
                if not isinstance(node.value, ast.Dict):
                    raise ValueError('not an explicit override dictionary')
                override_keys = [ast.literal_eval(key) for key in node.value.keys]
            except (ValueError, TypeError, SyntaxError):
                return None, {'reason':'growth override keys are not literal'}
            if not all(isinstance(key,str) for key in override_keys) or ticker in override_keys:
                return None, {'reason':'ticker-specific growth override requires its own rule'}
            override_keys_verified = True
    if override_keys_verified:
        for node in ast.walk(tree):
            if not isinstance(node,ast.Assign) or not any(_target_name(target)=='growth' for target in node.targets):
                continue
            call = node.value
            if (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)
                and isinstance(call.func.value,ast.Name) and call.func.value.id=='GROWTH_OVERRIDES'
                and call.func.attr=='get' and len(call.args)==2 and not call.keywords
                and isinstance(call.args[0],ast.Name) and call.args[0].id=='ticker'):
                node.value = call.args[1]
    scope_tree = tree
    generator_function = '_operating_data_result' if ticker=='MCO' else None
    if generator_function:
        functions = [node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==generator_function]
        if len(functions)!=1:
            return None, {'reason':'audited issuer generator function is missing or ambiguous'}
        scope_tree = ast.Module(body=functions,type_ignores=[])
    clamps = _find_clamps(scope_tree, _metric_bindings(scope_tree))
    if clamps == "ambiguous":
        return None, {"reason": "generator contains ambiguous matching growth clamps", "generator_path": relative, "generator_sha256": digest}
    if clamps is None:
        return None, {"reason": "audited generator does not contain a recognized growth clamp", "generator_path": relative, "generator_sha256": digest}
    clamp_rows, pattern = clamps
    declared_caps, cap_source = _policy_growth_caps(tree, ticker)
    if any(row.cap_index is not None for row in clamp_rows):
        if declared_caps is None:
            return None, {"reason": cap_source or "declared growth caps unavailable", "generator_path": relative, "generator_sha256": digest}
        if tuple(row.cap_index for row in clamp_rows) != (0, 1, 2):
            return None, {"reason": "generator growth cap references are not ordered p.growth[0:3]", "generator_path": relative, "generator_sha256": digest}
        caps = declared_caps
        caps_source = cap_source
    else:
        if any(row.cap is None for row in clamp_rows):
            return None, {"reason": "generator growth caps are not literal", "generator_path": relative, "generator_sha256": digest}
        caps = tuple(float(row.cap) for row in clamp_rows)
        caps_source = "generator_literal_clamp"
    floors = tuple(float(row.floor) for row in clamp_rows)
    if not all(floors[i] <= caps[i] for i in range(3)):
        return None, {"reason": "generator growth floor exceeds cap", "generator_path": relative, "generator_sha256": digest}
    return {
        "floors": floors,
        "caps": tuple(float(value) for value in caps),
        "caps_source": caps_source,
        "generator_pattern": pattern,
        "generator_path": relative,
        "generator_sha256": digest,
        "generator_function": generator_function,
    }, {}


def compile_history_growth_policy(entry: Mapping[str, Any], recipe: Mapping[str, Any]) -> dict[str, Any]:
    """Compile an audited, source-independent growth rule or return unsupported."""

    ticker = str(recipe.get("ticker", ""))
    if ticker not in AUDITED_GROWTH_TICKERS:
        return _unsupported(ticker, "ticker is not in the audited growth-policy set")
    if not isinstance(entry, Mapping) or str(entry.get("ticker", "")) != ticker:
        return _unsupported(ticker, "registry entry ticker does not match recipe")
    private, provenance = _read_private(recipe)
    if private is None:
        return _unsupported(ticker, provenance["reason"], provenance=provenance)
    private_issuer = private.get("issuer") if isinstance(private.get("issuer"), Mapping) else {}
    entry_cik = str(entry.get("cik", "")).zfill(10)
    if str(private_issuer.get("cik", "")).zfill(10) != entry_cik:
        return _unsupported(ticker, "retained private issuer CIK conflicts with registry entry", provenance=provenance)
    metric, metric_meta = _metric(private)
    if metric is None:
        return _unsupported(ticker, metric_meta["reason"], provenance=provenance)
    generator, generator_error = _generator_rule(ticker, entry.get("batch"))
    if generator is None:
        return _unsupported(ticker, generator_error["reason"], provenance={**provenance, **generator_error})
    observed = tuple(metric[key] for key in ("low", "base", "high"))
    floors = generator["floors"]
    caps = generator["caps"]
    recomputed = tuple(max(floors[i], min(caps[i], observed[i])) for i in range(3))
    scenario_inputs = recipe.get("scenarios")
    if not isinstance(scenario_inputs, Mapping):
        return _unsupported(ticker, "recipe scenarios are missing", provenance=provenance)
    recipe_growth: list[float] = []
    field = "initial_growth" if recipe.get("scenarios", {}).get("base", {}).get("engine") == "enterprise_cash_fcff" else "growth"
    try:
        for name in ("bear", "base", "bull"):
            value = scenario_inputs[name]["inputs"][field]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return _unsupported(ticker, f"recipe {field} is not numeric", provenance=provenance)
            recipe_growth.append(float(value))
    except (KeyError, TypeError):
        return _unsupported(ticker, f"recipe {field} is missing", provenance=provenance)
    matches = all(abs(recomputed[i] - recipe_growth[i]) <= 1e-12 for i in range(3))
    if not matches:
        return _unsupported(ticker, "recomputed growth rule does not reproduce frozen recipe", provenance=provenance, verification={"observed_metric": observed, "recomputed": recomputed, "recipe_growth": tuple(recipe_growth)})
    return {
        "schema_version": _SCHEMA,
        "status": "compiled",
        "ticker": ticker,
        "cik": entry_cik,
        "rule": {
            "metric": "revenue_growth",
            "history_summary": {
                "threshold": 4,
                "below_threshold": "minimum_median_maximum",
                "at_or_above_threshold": "quantile_25_median_quantile_75",
            },
            "floors": floors,
            "caps": caps,
            "formula": "max(floor, min(declared_cap, history_revenue_growth_quantile))",
        },
        "provenance": {
            **provenance,
            "private_sha256": provenance.get("sha256"),
            "generator_path": generator["generator_path"],
            "generator_sha256": generator["generator_sha256"],
            "caps_source": generator["caps_source"],
            "generator_pattern": generator["generator_pattern"],
            "generator_function": generator.get('generator_function'),
        },
        "verification": {
            "observation_count": metric_meta["observation_count"],
            "normalization_basis": metric_meta["normalization_basis"],
            "observed_metric": observed,
            "recomputed_growth": recomputed,
            "recipe_growth": tuple(recipe_growth),
            "matches_frozen_recipe": True,
        },
    }
