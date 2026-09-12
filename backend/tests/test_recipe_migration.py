import json
from pathlib import Path

import pytest

from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.recipe_migration import compile_private_recipe, discover_private_source


def artifact(ticker, low, base, high):
    return {
        "ticker": ticker,
        "issuer": {"ticker": ticker},
        "valuation_date": "2026-08-14",
        "source_financial_statement": {},
        "model_policy": {},
        "public_assumptions": {},
        "scenario_range": {"low": low, "base": base, "high": high},
    }


def private(owner):
    return {"schema_version": "private-test", "history_backed": owner}


def test_enterprise_packet_compiles_and_replays():
    rows = [
        {"name": "bear", "starting_cash_fcff": 8., "growth": .01, "terminal_growth": 0., "wacc": .11, "cash_and_investments": 5., "debt_and_finance_leases": 30., "other_equity_claims": 0., "shares": 10.},
        {"name": "base", "starting_cash_fcff": 10., "growth": .02, "terminal_growth": .01, "wacc": .10, "cash_and_investments": 5., "debt_and_finance_leases": 20., "other_equity_claims": 0., "shares": 10.},
        {"name": "bull", "starting_cash_fcff": 12., "growth": .03, "terminal_growth": .02, "wacc": .09, "cash_and_investments": 5., "debt_and_finance_leases": 10., "other_equity_claims": 0., "shares": 10.},
    ]
    owner = {"scenario_rows": rows, "governed_assumptions": {"forecast_years": 8}, "model_version": "test"}
    expected = {name: evaluate_recipe({"schema_version": "FINSIGHT-CALCULATION-RECIPE-1", "recipe_version": "x", "ticker": "X", "baseline_version": "x", "scenarios": {r["name"]: {"engine": "enterprise_cash_fcff", "inputs": {"cash_fcff": r["starting_cash_fcff"], "initial_growth": r["growth"], "terminal_growth": r["terminal_growth"], "wacc": r["wacc"], "cash_and_investments": r["cash_and_investments"], "interest_bearing_debt": r["debt_and_finance_leases"], "preferred_equity": 0., "noncontrolling_interests": 0., "diluted_shares": r["shares"], "forecast_years": 8}} for r in rows}, "editable": {}})["range"][name] for name in ("low", "base", "high")}
    result = compile_private_recipe(private(owner), artifact("X", expected["low"], expected["base"], expected["high"]), source_path="x")
    assert result["status"] == "migrated"
    assert result["recipe"]["scenarios"]["base"]["engine"] == "enterprise_cash_fcff"


@pytest.mark.parametrize("kind", ["constant", "residual", "multiple"])
def test_supported_shapes_replay(kind):
    if kind == "constant":
        rows = [{"name": n, "cash_conversion_margin": m, "growth": g, "wacc": w, "terminal_growth": t, "shares": 10.} for n,m,g,w,t in [("bear", .08, 0., .11, 0.), ("base", .10, .01, .10, .01), ("bull", .12, .02, .09, .02)]]
        owner = {"scenario_rows": rows, "reported_inputs": {"ttm_revenue": 100.}, "source_ledger": {"bridge_reconciliation": {"cash_and_investments": 5., "interest_bearing_debt": 20., "nci_status": "source_proven_absent"}}}
    elif kind == "residual":
        rows = [{"name": n, "book_value_per_share": 10., "current_roe": r, "cost_of_equity": .10, "current_payout_ratio": .20, "terminal_roe": .10, "terminal_growth": .02, "shares": 10.} for n,r in [("bear", .08), ("base", .10), ("bull", .12)]]
        owner = {"scenario_rows": rows, "governed_assumptions": {"forecast_years": 5}}
    else:
        rows = [{"name": n, "normalized_common_earnings": e, "earnings_multiple": m, "shares": 10.} for n,e,m in [("bear", 10., 5.), ("base", 20., 7.), ("bull", 30., 9.)]]
        owner = {"scenario_rows": rows}
    base_recipe = {"schema_version": "FINSIGHT-CALCULATION-RECIPE-1", "recipe_version": "x", "ticker": "X", "baseline_version": "x", "editable": {}}
    # Compile first with a provisional target derived from the same conversion.
    from app.us_valuation.recipe_migration import _constant_growth, _multiple, _residual
    scenarios = (_constant_growth(rows, owner) if kind == "constant" else _residual(rows, owner) if kind == "residual" else _multiple(rows, owner))
    base_recipe["scenarios"] = scenarios
    target = evaluate_recipe(base_recipe)["range"]
    result = compile_private_recipe(private(owner), artifact("X", target["low"], target["base"], target["high"]), source_path="x")
    assert result["status"] == "migrated"


def test_unreplayable_shape_is_explicit_gap():
    result = compile_private_recipe(private({"scenario_rows": [{"name": n, "value": 1.} for n in ("bear", "base", "bull")]}), artifact("X", 1, 2, 3), source_path="x")
    assert result["status"] == "gap"
    assert result["reason"] == "unsupported_or_incomplete_recorded_shape"


def test_discovery_accepts_recovery_private_filename(tmp_path: Path):
    packet = tmp_path / "APTV" / "recovery-private.json"
    packet.parent.mkdir()
    packet.write_text(json.dumps({"history_backed": {"scenario_range": {"low": 1., "base": 2., "high": 3.}}}))
    found = discover_private_source("APTV", {"low": 1., "base": 2., "high": 3.}, [tmp_path])
    assert found is not None and found[0] == packet


def test_chtr_event_overlay_uses_recorded_transaction_claim_and_units():
    payload = {"conditional_estimate": {
        "reported_inputs": {"fy2025_revenue": 54774000000., "cash": 509000000., "debt": 93959000000., "noncontrolling_interests": 4949000000., "diluted_shares": 123969262., "announced_common_units": 33600000., "announced_transaction_claims": 22550000000.},
        "governed_assumptions": {"current_company_dcf_states": [
            {"equity_value": -48030746080.194534, "fcff_margin": .10, "growth": -.02, "wacc": .10, "terminal_growth": 0.},
            {"equity_value": -18558958572.18213, "fcff_margin": .128, "growth": 0., "wacc": .095, "terminal_growth": .01},
            {"equity_value": 30530569230.76924, "fcff_margin": .15, "growth": .02, "wacc": .085, "terminal_growth": .02},
        ]},
    }}
    expected = {"low": 0.0, "base": 50.648007926630015, "high": 246.27531646327975}
    result = compile_private_recipe(payload, artifact("CHTR", **expected), source_path="chtr")
    assert result["status"] == "migrated"
    assert result["recipe"]["replay"] == expected
    payload["conditional_estimate"]["governed_assumptions"]["current_company_dcf_states"][2]["equity_value"] = 1.0
    replay_after_cached_output_tamper = compile_private_recipe(payload, artifact("CHTR", **expected), source_path="chtr")
    assert replay_after_cached_output_tamper["status"] == "migrated"
    assert replay_after_cached_output_tamper["recipe"]["replay"] == expected
