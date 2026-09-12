from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_margin_stress import compile_margin_stress_policy


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"


def _recipe_entry(ticker: str):
    recipe = json.loads((OUTPUT / f"us-refresh-runtime/recipes/{ticker}.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    return recipe, next(row for row in registry["entries"] if row["ticker"] == ticker)


@pytest.mark.parametrize("ticker,rates", [("BBY", (0.015, 0.005, 0.0)), ("DECK", (0.02, 0.005, 0.0)), ("DRI", (0.01, 0.003, 0.0))])
def test_real_batch06_margin_stress_reproduces_recipe(ticker: str, rates: tuple[float, float, float]) -> None:
    recipe, entry = _recipe_entry(ticker)
    result = compile_margin_stress_policy(entry, recipe)
    assert result["status"] == "compiled", result
    assert result["rule"]["scenario_rates"] == rates
    assert result["rule"]["reported_working_capital_correction"] is False
    assert result["verification"]["matches_frozen_recipe"] is True
    assert result["provenance"]["private_sha256"] == recipe["provenance"]["private_sha256"]


def test_margin_stress_is_not_a_reported_working_capital_fact() -> None:
    recipe, entry = _recipe_entry("DECK")
    result = compile_margin_stress_policy(entry, recipe)
    assert result["rule"]["adjustment_type"] == "governed_margin_stress"
    assert "working capital" not in result["rule"]["formula"]


def test_private_summary_mutation_is_rejected(tmp_path: Path) -> None:
    recipe, entry = _recipe_entry("DRI")
    private = json.loads(Path(recipe["provenance"]["source_path"]).read_text())
    metric = next(row for row in private["history_backed"]["source_ledger"]["company_history_profile"]["metrics"] if row["name"] == "cash_conversion_margin")
    metric["observations"][0]["value"] += 0.01
    path = tmp_path / "private.json"
    path.write_text(json.dumps(private))
    mutated = copy.deepcopy(recipe)
    mutated["provenance"]["source_path"] = str(path)
    mutated["provenance"]["private_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = compile_margin_stress_policy(entry, mutated)
    assert result["status"] == "unsupported"
    assert "summary does not recompute" in result["reason"]


def test_recipe_margin_mismatch_is_rejected() -> None:
    recipe, entry = _recipe_entry("BBY")
    mutated = copy.deepcopy(recipe)
    mutated["scenarios"]["base"]["inputs"]["fcff_margin"] += 0.001
    result = compile_margin_stress_policy(entry, mutated)
    assert result["status"] == "unsupported"
    assert "does not reproduce" in result["reason"]


def test_unknown_batch_or_rate_policy_is_explicitly_unsupported() -> None:
    recipe, entry = _recipe_entry("DECK")
    mutated = copy.deepcopy(entry)
    mutated["batch"] = 99
    result = compile_margin_stress_policy(mutated, recipe)
    assert result["status"] == "unsupported"
