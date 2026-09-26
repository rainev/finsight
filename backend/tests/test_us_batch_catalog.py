import pytest

from app.routers.us_valuations import CATALOG, list_us_valuations, load_generated_result
from app.us_valuation.calculator import calculate, calculator_view


def test_active_website_catalog_is_exactly_confirmed_batches_01_through_10():
    assert CATALOG.version == "US-RESET-2026-08-14-B01-B10-1.0"
    assert CATALOG.included_batches == tuple(range(1, 11))
    assert len(CATALOG.entries) == 100
    assert {entry.availability_type for entry in CATALOG.entries} == {
        "available",
        "conditional_estimate",
        "not_available",
    }
    assert "AAPL" in CATALOG.entry_by_ticker
    assert "NVDA" not in CATALOG.entry_by_ticker


def test_list_uses_catalog_not_loose_206_artifact_directory():
    result = list_us_valuations()
    assert result["count"] == 100
    assert result["included_batches"] == list(range(1, 11))
    assert result["catalog_version"] == "US-RESET-2026-08-14-B01-B10-1.0"
    assert len({row["ticker"] for row in result["items"]}) == 100
    assert {row["availability_type"] for row in result["items"]} == {
        "available",
        "conditional_estimate",
        "not_available",
    }


def test_detail_carries_catalog_batch_and_evidence_health():
    result = load_generated_result("AAPL")
    assert result["catalog"]["batch"] == 1
    assert result["catalog"]["included_batches"] == list(range(1, 11))
    assert len(result["evidence_health"]) == 4
    assert result["scenario_range"]["base"] == pytest.approx(103.3303976983317)


def test_calculator_defaults_reproduce_confirmed_baseline():
    artifact = load_generated_result("AAPL")
    view = calculator_view(artifact)
    result = calculate(artifact, overrides={}, manual_price=200)
    assert view["can_calculate"] is True
    assert result["result"] == pytest.approx(view["baseline_result"])
    assert result["comparison"]["source"] == "manual"
    assert result["comparison"]["verdict"] == "overvalued"


def test_calculator_rejects_unsafe_terminal_spread():
    artifact = load_generated_result("AAPL")
    with pytest.raises(ValueError, match="at least 2% below"):
        calculate(
            artifact,
            overrides={"discount_rate": 0.055, "terminal_growth": 0.04},
            manual_price=None,
        )


def test_unavailable_batch_company_fails_closed():
    artifact = load_generated_result("NEE")
    view = calculator_view(artifact)
    assert artifact["availability_type"] == "not_available"
    assert view["can_calculate"] is False
    assert view["baseline_result"] == {"low": None, "base": None, "high": None}
