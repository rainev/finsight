"""Reliability threshold and validation behavior tests."""

from __future__ import annotations

import math

import pytest

from app.us_valuation.reliability import (
    accounting_label,
    assess_reliability,
    lowest_label,
    relative_movement,
    scenario_label,
)


def test_relative_movement_uses_largest_distance_from_base() -> None:
    assert relative_movement(low=94.0, base=100.0, high=105.0) == 0.06


@pytest.mark.parametrize(
    ("low", "base", "high", "expected"),
    [
        (95.0, 100.0, 105.0, "High"),
        (94.99, 100.0, 105.0, "Medium"),
        (80.0, 100.0, 120.0, "Medium"),
        (79.99, 100.0, 120.0, "Low"),
    ],
)
def test_accounting_boundaries(low, base, high, expected) -> None:
    result = assess_reliability(
        accounting_low=low,
        accounting_base=base,
        accounting_high=high,
        scenario_low=80.0,
        scenario_base=100.0,
        scenario_high=120.0,
    )
    assert result.accounting_label == expected


@pytest.mark.parametrize(
    ("low", "base", "high", "expected"),
    [
        (80.0, 100.0, 120.0, "High"),
        (79.99, 100.0, 120.0, "Medium"),
        (60.0, 100.0, 140.0, "Medium"),
        (59.99, 100.0, 140.0, "Low"),
    ],
)
def test_scenario_boundaries(low, base, high, expected) -> None:
    result = assess_reliability(
        accounting_low=100.0,
        accounting_base=100.0,
        accounting_high=100.0,
        scenario_low=low,
        scenario_base=base,
        scenario_high=high,
    )
    assert result.scenario_label == expected


def test_sector_or_unproven_model_cap_forces_low() -> None:
    result = assess_reliability(
        accounting_low=100.0,
        accounting_base=100.0,
        accounting_high=100.0,
        scenario_low=90.0,
        scenario_base=100.0,
        scenario_high=110.0,
        model_cap="Low",
        source_cap="High",
        reasons=("UNPROVEN_SPECIALIST_LANE",),
    )
    assert result.label == "Low"


def test_assessment_uses_the_lowest_qualitative_input_and_serializes_reasons() -> None:
    result = assess_reliability(
        accounting_low=95.0,
        accounting_base=100.0,
        accounting_high=105.0,
        scenario_low=80.0,
        scenario_base=100.0,
        scenario_high=120.0,
        model_cap="High",
        source_cap="Medium",
        reasons=("SOURCE_GAP", "SOURCE_GAP", "MODEL_LANE"),
    )

    assert result.label == "Medium"
    assert result.reasons == ("SOURCE_GAP", "MODEL_LANE")
    assert result.as_dict()["reasons"] == ["SOURCE_GAP", "MODEL_LANE"]


@pytest.mark.parametrize("value", [True, False, math.inf, -math.inf, math.nan])
def test_relative_movement_rejects_boolean_and_nonfinite_values(value: object) -> None:
    with pytest.raises(ValueError, match="low must be a finite number"):
        relative_movement(low=value, base=100.0, high=100.0)


@pytest.mark.parametrize(
    ("low", "base", "high"),
    [
        (101.0, 100.0, 102.0),
        (98.0, 100.0, 99.0),
    ],
)
def test_relative_movement_rejects_unordered_ranges(
    low: float, base: float, high: float
) -> None:
    with pytest.raises(ValueError, match="range must satisfy low <= base <= high"):
        relative_movement(low=low, base=base, high=high)


def test_relative_movement_rejects_zero_base() -> None:
    with pytest.raises(ValueError, match="base must be non-zero"):
        relative_movement(low=0.0, base=0.0, high=0.0)


@pytest.mark.parametrize("function", [accounting_label, scenario_label])
@pytest.mark.parametrize("value", [True, -0.01, math.inf, math.nan])
def test_ratio_labels_reject_invalid_ratios(function, value: object) -> None:
    with pytest.raises(ValueError):
        function(value)


@pytest.mark.parametrize(
    "labels",
    [(), ("Unknown",), ("High", "Unknown")],
)
def test_lowest_label_rejects_empty_or_unknown_labels(labels: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="labels must contain only High, Medium, or Low"):
        lowest_label(*labels)


@pytest.mark.parametrize("cap_name", ["model_cap", "source_cap"])
def test_assessment_rejects_unknown_qualitative_caps(cap_name: str) -> None:
    kwargs = {cap_name: "Unknown"}
    with pytest.raises(ValueError, match="labels must contain only High, Medium, or Low"):
        assess_reliability(
            accounting_low=100.0,
            accounting_base=100.0,
            accounting_high=100.0,
            scenario_low=100.0,
            scenario_base=100.0,
            scenario_high=100.0,
            **kwargs,
        )


@pytest.mark.parametrize("reasons", [("",), ("  ",), ("VALID", 1)])
def test_assessment_rejects_empty_or_nonstrings_reasons(reasons: tuple[object, ...]) -> None:
    with pytest.raises(ValueError, match="reasons must contain nonempty strings"):
        assess_reliability(
            accounting_low=100.0,
            accounting_base=100.0,
            accounting_high=100.0,
            scenario_low=100.0,
            scenario_base=100.0,
            scenario_high=100.0,
            reasons=reasons,  # type: ignore[arg-type]
        )
