from app.us_valuation.recipe_migration import compile_private_recipe
import pytest


def _artifact(ticker, values):
    return {
        "ticker": ticker,
        "issuer": {"ticker": ticker},
        "valuation_date": "2026-08-14",
        "source_financial_statement": {},
        "model_policy": {},
        "public_assumptions": {},
        "scenario_range": dict(zip(("low", "base", "high"), values)),
    }


def _payload(owner):
    return {"schema_version": "private-test", "history_backed": owner}


def _compile(ticker, owner, values):
    result = compile_private_recipe(
        _payload(owner), _artifact(ticker, values), source_path=ticker
    )
    assert result["status"] == "migrated"
    assert result["recipe"]["replay"] == pytest.approx(
        {"low": values[0], "base": values[1], "high": values[2]}
    )
    return result["recipe"]


def test_reit_affo_shape_replays_without_share_invention():
    rows = [
        {"name": "bear", "normalized_affo_per_share": 10.0, "growth_rate": 0.02,
         "terminal_growth": 0.02, "discount_rate": 0.0975, "forecast_years": 8},
        {"name": "base", "normalized_affo_per_share": 10.0, "growth_rate": 0.02,
         "terminal_growth": 0.02, "discount_rate": 0.0925, "forecast_years": 8},
        {"name": "bull", "normalized_affo_per_share": 10.0, "growth_rate": 0.02,
         "terminal_growth": 0.02, "discount_rate": 0.0875, "forecast_years": 8},
    ]
    recipe = _compile("REIT", {"scenario_rows": rows},
                      (131.61290322580655, 140.6896551724138, 151.11111111111126))
    assert recipe["scenarios"]["base"]["engine"] == "cash_schedule"
    assert recipe["scenarios"]["base"]["inputs"]["shares"] == 1.0


def test_reit_event_adjustment_is_retained_as_recorded_bridge():
    rows = [
        {"name": name, "normalized_affo_per_share": 10.0, "growth_rate": 0.02,
         "terminal_growth": 0.02, "discount_rate": rate, "forecast_years": 8,
         "nonrecurring_value_adjustment_per_share": -3.25}
        for name, rate in (("bear", 0.0975), ("base", 0.0925), ("bull", 0.0875))
    ]
    recipe = _compile("REIT-EVENT", {"scenario_rows": rows},
                      (128.36290322580655, 137.4396551724138, 147.86111111111126))
    assert recipe["scenarios"]["base"]["inputs"]["net_bridge"] == -3.25


def test_later_enterprise_rows_map_combined_claim_once():
    rows = [
        {"name": "bear", "starting_cash_fcff": 8.0, "growth_rate": 0.01,
         "terminal_growth": 0.0, "wacc": 0.11, "cash": 5.0, "debt": 30.0,
         "preferred_and_nci": 4.0, "shares": 10.0, "forecast_years": 8},
        {"name": "base", "starting_cash_fcff": 10.0, "growth_rate": 0.02,
         "terminal_growth": 0.01, "wacc": 0.10, "cash": 5.0, "debt": 20.0,
         "preferred_and_nci": 4.0, "shares": 10.0, "forecast_years": 8},
        {"name": "bull", "starting_cash_fcff": 12.0, "growth_rate": 0.03,
         "terminal_growth": 0.02, "wacc": 0.09, "cash": 5.0, "debt": 10.0,
         "preferred_and_nci": 4.0, "shares": 10.0, "forecast_years": 8},
    ]
    recipe = _compile("TRACE", {"scenario_rows": rows},
                      (4.616035354154228, 9.706450614841861, 17.199058138403473))
    assert recipe["scenarios"]["base"]["inputs"]["preferred_equity"] == 4.0
    assert recipe["scenarios"]["base"]["inputs"]["noncontrolling_interests"] == 0.0


def test_utility_fcfe_rows_replay_cash_schedule():
    rows = [
        {"name": "bear", "cash_flow": 5.0, "growth_rate": 0.02,
         "terminal_growth": 0.02, "cost_of_equity": 0.085, "shares": 10.0},
        {"name": "base", "cash_flow": 6.0, "growth_rate": 0.02,
         "terminal_growth": 0.02, "cost_of_equity": 0.085, "shares": 10.0},
        {"name": "bull", "cash_flow": 7.0, "growth_rate": 0.02,
         "terminal_growth": 0.02, "cost_of_equity": 0.085, "shares": 10.0},
    ]
    recipe = _compile("UTILITY", {"scenario_rows": rows,
                                  "governed_assumptions": {"forecast_years": 10}},
                      (7.846153846153851, 9.41538461538462, 10.98461538461539))
    assert recipe["scenarios"]["base"]["engine"] == "cash_schedule"


def test_one_period_distribution_ddm_replays_gordon_value():
    rows = [
        {"name": "bear", "owner_distribution_per_share": 0.55,
         "distribution_growth": 0.0, "cost_of_equity": 0.10},
        {"name": "base", "owner_distribution_per_share": 0.84,
         "distribution_growth": 0.0, "cost_of_equity": 0.10},
        {"name": "bull", "owner_distribution_per_share": 1.18,
         "distribution_growth": 0.0, "cost_of_equity": 0.10},
    ]
    recipe = _compile("DISTRIBUTION", {"scenario_rows": rows,
                                       "governed_assumptions": {"forecast_years": 1}},
                      (5.5, 8.4, 11.8))
    assert recipe["scenarios"]["base"]["inputs"]["cash_flows"] == [0.84]
