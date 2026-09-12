from __future__ import annotations

import copy
import ast
import hashlib
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_growth_policies import compile_history_growth_policy


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"


TICKERS = ("GWW", "GNRC", "IR", "BR", "HLT", "KO", "PEP", "HRL", "PG",
    "ADI", "ADP", "ADSK", "ALLE", "AMAT", "BBY", "BF.B", "BKNG", "BLDR", "CASY",
    "CDW", "CIEN", "CPRT", "CSX", "DDOG", "DOV", "DPZ", "CMG", "DECK", "DRI", "MAS", "MSI", "MCO",
    "FTV", "GEV", "HUBB", "JCI", "LDOS", "OTIS", "PWR", "ROK", "VLTO", "WAB", "WM")


@pytest.mark.parametrize('expression', [
    'tuple(max(-.1,min(.2,v)) for v in (gm.low,gm.base,gm.high,0))',
    'tuple(max(-.1,min(.2,v)) for v in (gm.low,gm.base,gm.high) if v > 0)',
    'tuple(max(-.1,min(.2,v)) async for v in (gm.low,gm.base,gm.high))',
    'tuple(max(-.1,min(.2,v),key=float) for v in (gm.low,gm.base,gm.high))',
    'tuple(max(-.1,min(.2,v,key=float)) for v in (gm.low,gm.base,gm.high))',
    'tuple(max(-.1,min(.2,v)) for v in (gm.low,hist_growth.base,gm.high))',
])
def test_rejects_non_governed_generator_structure(expression):
    from app.us_valuation.refresh_growth_policies import _find_clamps,_metric_bindings
    tree = ast.parse("gm = profile.metric('revenue_growth')\nhist_growth = profile.metric('revenue_growth')\ngrowth = " + expression)
    assert _find_clamps(tree,_metric_bindings(tree)) is None


def test_lookalike_metric_name_and_nonfinite_literals_are_not_accepted():
    from app.us_valuation.refresh_growth_policies import _find_clamps,_metric_bindings,_number
    tree = ast.parse("gm = profile.metric('cash_conversion_margin')\ngrowth = tuple(max(-.1,min(.2,v)) for v in (gm.low,gm.base,gm.high))")
    assert _find_clamps(tree,_metric_bindings(tree)) is None
    assert _number(ast.parse('1e999',mode='eval').body) is None


def _recipe_entry(ticker: str):
    recipe = json.loads((OUTPUT / f"us-refresh-runtime/recipes/{ticker}.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    return recipe, next(row for row in registry["entries"] if row["ticker"] == ticker)


@pytest.mark.parametrize("ticker", TICKERS)
def test_audited_growth_rules_compile_and_forward_verify(ticker: str) -> None:
    recipe, entry = _recipe_entry(ticker)
    result = compile_history_growth_policy(entry, recipe)
    assert result["status"] == "compiled", result
    assert result["verification"]["matches_frozen_recipe"] is True
    assert result["rule"]["metric"] == "revenue_growth"
    assert result["provenance"]["generator_sha256"]
    assert result["provenance"]["private_sha256"] == recipe["provenance"]["private_sha256"]


def test_common_summary_uses_min_max_below_four_and_quartiles_at_four() -> None:
    gww, gww_entry = _recipe_entry("GWW")
    hlt, hlt_entry = _recipe_entry("HLT")
    assert compile_history_growth_policy(gww_entry, gww)["rule"]["history_summary"]["below_threshold"] == "minimum_median_maximum"
    assert compile_history_growth_policy(hlt_entry, hlt)["rule"]["history_summary"]["at_or_above_threshold"] == "quantile_25_median_quantile_75"


def test_declared_caps_are_read_from_policy_ast_for_gww_and_gnrc() -> None:
    gww, gww_entry = _recipe_entry("GWW")
    gnrc, gnrc_entry = _recipe_entry("GNRC")
    assert compile_history_growth_policy(gww_entry, gww)["rule"]["caps"] == (0.01, 0.05, 0.08)
    assert compile_history_growth_policy(gnrc_entry, gnrc)["rule"]["caps"] == (-0.06, 0.02, 0.07)
    assert compile_history_growth_policy(gww_entry, gww)["provenance"]["caps_source"] == "declared_P[ticker].growth"


def test_literal_asymmetric_batch10_rule_is_preserved() -> None:
    pep, entry = _recipe_entry("PEP")
    result = compile_history_growth_policy(entry, pep)
    assert result["rule"]["floors"] == (-0.05, -0.03, 0.0)
    assert result["rule"]["caps"] == (0.03, 0.04, 0.05)
    assert result["provenance"]["caps_source"] == "generator_literal_clamp"


def test_ko_uses_batch09_uniform_minus10_to_plus15_clamp() -> None:
    ko, entry = _recipe_entry("KO")
    result = compile_history_growth_policy(entry, ko)
    assert result["rule"]["floors"] == (-0.10, -0.10, -0.10)
    assert result["rule"]["caps"] == (0.15, 0.15, 0.15)
    assert result["provenance"]["generator_path"].endswith("batch_09_history.py")


def test_history_summary_is_dynamic_not_frozen_observation_count() -> None:
    recipe, entry = _recipe_entry("GWW")
    summary = compile_history_growth_policy(entry, recipe)["rule"]["history_summary"]
    assert summary == {
        "threshold": 4,
        "below_threshold": "minimum_median_maximum",
        "at_or_above_threshold": "quantile_25_median_quantile_75",
    }
    assert "observation_count" not in summary


def test_private_sha_mismatch_is_explicitly_unsupported() -> None:
    recipe, entry = _recipe_entry("BR")
    mutated = copy.deepcopy(recipe)
    mutated["provenance"]["private_sha256"] = "0" * 64
    result = compile_history_growth_policy(entry, mutated)
    assert result["status"] == "unsupported"
    assert "SHA mismatch" in result["reason"]


def test_unknown_ticker_or_unrecognized_pattern_is_not_guessed() -> None:
    recipe, entry = _recipe_entry("BR")
    mutated = copy.deepcopy(recipe)
    mutated["ticker"] = "UNKNOWN"
    result = compile_history_growth_policy(entry, mutated)
    assert result["status"] == "unsupported"
    assert "audited" in result["reason"]


def test_rejects_malformed_retained_metric_instead_of_trusting_summary(tmp_path: Path) -> None:
    recipe, entry = _recipe_entry("BR")
    private = json.loads(Path(recipe["provenance"]["source_path"]).read_text())
    metric = next(row for row in private["history_backed"]["source_ledger"]["company_history_profile"]["metrics"] if row["name"] == "revenue_growth")
    metric["observations"][0]["value"] += 0.01
    private_path = tmp_path / "valuation-private.json"
    private_path.write_text(json.dumps(private))
    mutated = copy.deepcopy(recipe)
    mutated["provenance"]["source_path"] = str(private_path)
    mutated["provenance"]["private_sha256"] = hashlib.sha256(private_path.read_bytes()).hexdigest()
    result = compile_history_growth_policy(entry, mutated)
    assert result["status"] == "unsupported"
    assert "summary does not recompute" in result["reason"]


def test_rejects_nonfinite_retained_observation(tmp_path: Path) -> None:
    recipe, entry = _recipe_entry("BR")
    private = json.loads(Path(recipe["provenance"]["source_path"]).read_text())
    metric = next(row for row in private["history_backed"]["source_ledger"]["company_history_profile"]["metrics"] if row["name"] == "revenue_growth")
    metric["observations"][0]["value"] = float("nan")
    private_path = tmp_path / "valuation-private.json"
    private_path.write_text(json.dumps(private))
    mutated = copy.deepcopy(recipe)
    mutated["provenance"]["source_path"] = str(private_path)
    mutated["provenance"]["private_sha256"] = hashlib.sha256(private_path.read_bytes()).hexdigest()
    result = compile_history_growth_policy(entry, mutated)
    assert result["status"] == "unsupported"
    assert "malformed or nonfinite" in result["reason"]


def test_rejects_ast_operand_that_is_not_revenue_growth(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.us_valuation.refresh_growth_policies as module

    source_root = tmp_path / "repo"
    generator = source_root / "backend/app/us_valuation/batch_21_history.py"
    generator.parent.mkdir(parents=True)
    generator.write_text(
        "P = {'GWW': Policy(0, 0, 0, 0, 0, 0, 0, 0, (0.01, 0.05, 0.08))}\n"
        "class Policy: pass\n"
        "def f():\n"
        "    growth = (max(-.1, min(p.growth[0], foo.low)), max(-.08, min(p.growth[1], foo.base)), max(0., min(p.growth[2], foo.high)))\n"
    )
    monkeypatch.setattr(module, "_source_root", lambda: source_root)
    recipe, entry = _recipe_entry("GWW")
    result = compile_history_growth_policy(entry, recipe)
    assert result["status"] == "unsupported"
    assert "recognized growth clamp" in result["reason"]


def test_rejects_ambiguous_matching_growth_assignments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.us_valuation.refresh_growth_policies as module

    source_root = tmp_path / "repo"
    generator = source_root / "backend/app/us_valuation/batch_21_history.py"
    generator.parent.mkdir(parents=True)
    generator.write_text(
        "P = {'GWW': Policy(0, 0, 0, 0, 0, 0, 0, 0, (0.01, 0.05, 0.08))}\n"
        "class Policy: pass\n"
        "def f():\n"
        "    cm, gm = profile.metric('cash_conversion_margin'), profile.metric('revenue_growth')\n"
        "    growth = (max(-.1, min(p.growth[0], gm.low)), max(-.08, min(p.growth[1], gm.base)), max(0., min(p.growth[2], gm.high)))\n"
        "    growth = (max(-.1, min(p.growth[0], gm.low)), max(-.08, min(p.growth[1], gm.base)), max(0., min(p.growth[2], gm.high)))\n"
    )
    monkeypatch.setattr(module, "_source_root", lambda: source_root)
    recipe, entry = _recipe_entry("GWW")
    result = compile_history_growth_policy(entry, recipe)
    assert result["status"] == "unsupported"
    assert "ambiguous" in result["reason"]
