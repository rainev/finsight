from copy import deepcopy

import pytest

from app.models.valuation import UsCalculatorInput
from app.routers.us_valuations import CATALOG, load_generated_result
from app.routers.us_valuations import post_us_valuation_calculator
from app.us_valuation.calculator import calculate, calculator_view


@pytest.mark.parametrize("case,growth,discount,terminal,value", [
    ("low", 0.06166084576940628, 0.10118064378138147, 0.015, 79.80130329911236),
    ("base", 0.08166084576940628, 0.09118064378138147, 0.02, 103.3303976983317),
    ("high", 0.09666084576940628, 0.08618064378138147, 0.023, 123.1625608382377),
])
def test_confirmed_case_inputs_and_values(case, growth, discount, terminal, value):
    artifact = load_generated_result("AAPL")
    view = calculator_view(artifact)
    preset = view["scenario_presets"][case]
    assert preset["initial_growth"] == pytest.approx(growth)
    assert preset["discount_rate"] == pytest.approx(discount)
    assert preset["terminal_growth"] == pytest.approx(terminal)
    result = calculate(artifact, overrides=preset, manual_price=200, scenario=case)
    assert result["result"][case] == pytest.approx(value)
    assert result["result"] == pytest.approx(view["baseline_result"])
    assert result["selected_scenario"] == case
    assert result["assumptions"] == preset
    assert result["comparison"]["gap_pct"] == pytest.approx(1 - 200 / value)


def test_case_sensitivity_uses_own_anchor_without_double_stress():
    artifact = load_generated_result("AAPL")
    view = calculator_view(artifact)
    for case in ("low", "base", "high"):
        preset = view["scenario_presets"][case]
        default = calculate(artifact, overrides={}, manual_price=None, scenario=case)
        assert default["result"][case] == view["baseline_result"][case]
        changed = calculate(artifact, overrides={"initial_growth": preset["initial_growth"] + .01}, manual_price=None, scenario=case)
        assert changed["result"][case] > default["result"][case]
        restored = calculate(artifact, overrides=preset, manual_price=None, scenario=case)
        assert restored["result"] == default["result"]


@pytest.mark.parametrize("field", ["valuation_date", "scenario_range", "source_financial_statement"])
def test_preset_is_not_silently_reused_for_a_changed_baseline(field):
    artifact = deepcopy(load_generated_result("AAPL"))
    if field == "valuation_date": artifact[field] = "2026-09-07"
    elif field == "scenario_range": artifact[field]["high"] += .01
    else: artifact[field]["accession"] = "different-filing"
    assert set(calculator_view(artifact)["scenario_presets"]) == {"base"}
    with pytest.raises(ValueError, match="unavailable"):
        calculate(artifact, overrides={"initial_growth": .10}, manual_price=None, scenario="high")


def test_all_catalog_base_defaults_still_replay():
    for entry in CATALOG.entries:
        artifact = load_generated_result(entry.ticker)
        view = calculator_view(artifact)
        if not view["can_calculate"]: continue
        result = calculate(artifact, overrides={}, manual_price=None)
        assert result["result"] == pytest.approx(view["baseline_result"]), entry.ticker


def test_unknown_case_rejected_and_legacy_api_defaults_to_base():
    assert UsCalculatorInput().scenario == "base"
    with pytest.raises(ValueError): UsCalculatorInput(scenario="invented")
    with pytest.raises(ValueError, match="unknown"):
        calculate(load_generated_result("AAPL"), overrides={}, manual_price=None, scenario="invented")


def test_router_carries_selected_case_without_saving(monkeypatch):
    def unexpected_save(**kwargs):
        raise AssertionError("a calculation must not save a record")
    monkeypatch.setattr("app.routers.us_valuations.valuation_service.save_us", unexpected_save)
    result = post_us_valuation_calculator("AAPL", UsCalculatorInput(scenario="high", manual_price=123.1625608382377), {"sub": "unit-test-only"})
    assert result["selected_scenario"] == "high"
    assert result["assumptions"]["terminal_growth"] == pytest.approx(.023)
    assert result["comparison"]["verdict"] == "fair_value"
    assert "selected case" in result["comparison"]["label"]


def test_explicit_save_carries_case_metadata_using_stub_only(monkeypatch):
    captured = {}
    def stub_save(**kwargs):
        captured.update(kwargs)
        return {"id": 42}
    monkeypatch.setattr("app.routers.us_valuations.valuation_service.save_us", stub_save)
    result = post_us_valuation_calculator("AAPL", UsCalculatorInput(scenario="low", save=True), {"sub": "unit-test-only"})
    assert captured["result"]["selected_scenario"] == "low"
    assert captured["assumptions"]["initial_growth"] == pytest.approx(.06166084576940628)
    assert result["saved_id"] == 42
