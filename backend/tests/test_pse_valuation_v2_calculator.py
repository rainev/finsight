from __future__ import annotations

import pytest

from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.pipeline import build_pilot_artifacts
from app.routers import pse_valuations
from app.models.valuation import UsCalculatorInput


USER = {"sub": 7, "role": "user"}


@pytest.fixture(scope="module")
def artifacts():
    return build_pilot_artifacts()


def test_ap_calculator_defaults_reproduce_catalog(artifacts) -> None:
    artifact = artifacts["AP"].model_dump(mode="json")
    view = calculator_view(artifact)
    assert view["can_calculate"] is True
    for case, scenario in (("low", "bear"), ("base", "base"), ("high", "bull")):
        result = calculate(artifact, overrides=view["scenario_presets"][case], scenario=case, manual_price=None)
        assert result["result"][case] == pytest.approx(
            artifact["scenarios"][scenario]["value_per_share"]
        )


def test_ap_edit_changes_only_selected_case(artifacts) -> None:
    artifact = artifacts["AP"].model_dump(mode="json")
    baseline = calculator_view(artifact)["baseline_result"]
    result = calculate(
        artifact,
        overrides={"growth_rate": 0.04},
        scenario="base",
        manual_price=25,
    )
    assert result["result"]["base"] != pytest.approx(baseline["base"])
    assert result["result"]["low"] == baseline["low"]
    assert result["result"]["high"] == baseline["high"]
    assert result["comparison"]["source"] == "manual"


def test_bdo_multiple_calculator_reproduces_and_edits(artifacts) -> None:
    artifact = artifacts["BDO"].model_dump(mode="json")
    view = calculator_view(artifact)
    assert view["editable_assumptions"][0]["key"] == "valuation_multiple"
    baseline = calculate(artifact, overrides={"valuation_multiple": 10}, scenario="base", manual_price=None)
    edited = calculate(artifact, overrides={"valuation_multiple": 11}, scenario="base", manual_price=None)
    assert baseline["result"]["base"] == pytest.approx(162.8)
    assert edited["result"]["base"] == pytest.approx(179.08)


def test_areit_yield_calculator_is_inverse(artifacts) -> None:
    artifact = artifacts["AREIT"].model_dump(mode="json")
    view = calculator_view(artifact)
    assert view["editable_assumptions"][0]["key"] == "required_yield"
    lower_yield = calculate(artifact, overrides={"required_yield": 0.06}, scenario="base", manual_price=None)
    higher_yield = calculate(artifact, overrides={"required_yield": 0.08}, scenario="base", manual_price=None)
    assert lower_yield["result"]["base"] > higher_yield["result"]["base"]


def test_calculator_rejects_unknown_or_out_of_range_inputs(artifacts) -> None:
    artifact = artifacts["BDO"].model_dump(mode="json")
    with pytest.raises(ValueError, match="unsupported"):
        calculate(artifact, overrides={"wacc": 0.10}, scenario="base", manual_price=None)
    with pytest.raises(ValueError, match="between"):
        calculate(artifact, overrides={"valuation_multiple": 100}, scenario="base", manual_price=None)


def test_pse_calculator_api_and_save(monkeypatch) -> None:
    view = pse_valuations.get_pse_valuation_calculator("BDO", USER)
    assert view["baseline_result"]["base"] == pytest.approx(162.8)
    monkeypatch.setattr(
        pse_valuations.valuation_service,
        "save_pse_v2",
        lambda **kwargs: {"id": 321},
    )
    result = pse_valuations.post_pse_valuation_calculator(
        "BDO",
        UsCalculatorInput(
            scenario="base",
            overrides={"valuation_multiple": 11},
            manual_price=150,
            save=True,
        ),
        USER,
    )
    assert result["saved_id"] == 321
    assert result["result"]["base"] == pytest.approx(179.08)


def test_pse_history_retains_blocked_and_fallback_versions() -> None:
    history = pse_valuations.get_pse_valuation_history("BDO", USER)
    versions = {row["catalog_version"]: row for row in history["items"]}
    assert versions["PSE-V2-PILOT-2026-09-21-1.0"]["availability_type"] == "not_available"
    assert versions["PSE-V2-PILOT-2026-09-21-1.1"]["availability_type"] == "market_relative_only"

