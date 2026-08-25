import json
from pathlib import Path

import pytest

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.calculator import calculate, calculator_view


def _artifact(ticker: str = "NWSA") -> dict:
    root = Path("output/launch-first/batch-03-run-g/staged-public")
    return sanitize_public_artifact(json.loads((root / f"{ticker}.json").read_text()))


def test_default_calculator_reproduces_published_range() -> None:
    artifact = _artifact()
    view = calculator_view(artifact)
    result = calculate(artifact, overrides={}, manual_price=None)

    assert view["can_calculate"] is True
    assert result["result"] == pytest.approx(
        {key: artifact["scenario_range"][key] for key in ("low", "base", "high")}
    )
    assert result["baseline_change_pct"] == pytest.approx(0)


def test_higher_discount_rate_lowers_value() -> None:
    artifact = _artifact()
    view = calculator_view(artifact)
    result = calculate(
        artifact,
        overrides={"discount_rate": view["defaults"]["discount_rate"] + 0.01},
        manual_price=None,
    )
    assert result["result"]["base"] < artifact["scenario_range"]["base"]


def test_better_cash_conversion_increases_value() -> None:
    artifact = _artifact()
    result = calculate(artifact, overrides={"cash_conversion": 1.20}, manual_price=None)
    assert result["result"]["base"] > artifact["scenario_range"]["base"]


def test_invalid_or_unknown_assumptions_are_rejected() -> None:
    artifact = _artifact()
    with pytest.raises(ValueError, match="unsupported"):
        calculate(artifact, overrides={"shares": 1}, manual_price=None)
    with pytest.raises(ValueError, match="between"):
        calculate(artifact, overrides={"discount_rate": 0.99}, manual_price=None)
    with pytest.raises(ValueError, match="2% below"):
        calculate(
            artifact,
            overrides={"discount_rate": 0.05, "terminal_growth": 0.04},
            manual_price=None,
        )


def test_manual_price_changes_only_comparison() -> None:
    artifact = _artifact()
    automatic = calculate(artifact, overrides={}, manual_price=None)
    manual = calculate(artifact, overrides={}, manual_price=10.0)

    assert manual["result"] == automatic["result"]
    assert manual["comparison_source"] == "manual"
    assert manual["comparison"]["gap_pct"] == pytest.approx(
        (manual["result"]["base"] - 10.0) / manual["result"]["base"]
    )
    assert automatic["comparison_source"] == "automatic_eod"


def test_not_available_company_has_no_calculator() -> None:
    artifact = _artifact("ECHO")
    view = calculator_view(artifact)
    assert view["can_calculate"] is False
    with pytest.raises(ValueError, match="unavailable"):
        calculate(artifact, overrides={}, manual_price=None)
