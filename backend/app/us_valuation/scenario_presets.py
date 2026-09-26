"""Verified, public calculator presets; never infer cases from a price range.

The Apple mapping is the original PRACTICAL_FCFF_STATES policy in the confirmed
Batch 01 run (see docs/audit/08-case-assumption-sync.md). Match its exact dated
baseline before using it. Other models keep Base-only controls until their own
case inputs are verified. No raw filing or private policy packets are exposed.
"""
from math import isclose
from typing import Any, Mapping


def case_presets(artifact: Mapping[str, Any], defaults: Mapping[str, Any]) -> dict[str, dict]:
    result = {"base": dict(defaults)}
    if (
        artifact.get("ticker") != "AAPL"
        or artifact.get("valuation_date") != "2026-08-14"
        or artifact.get("source_financial_statement", {}).get("accession") != "0000320193-26-000020"
        or artifact.get("primary_valuation_method") != "fcff_dcf"
    ):
        return result
    expected = {"low": 79.80130329911236, "base": 103.3303976983317, "high": 123.1625608382377}
    expected_inputs = {"initial_growth": 0.08166084576940628, "discount_rate": 0.09118064378138147, "terminal_growth": 0.02, "cash_conversion": 1.0, "forecast_years": 5}
    for source, reference in ((artifact.get("scenario_range", {}), expected), (defaults, expected_inputs)):
        if any(not isinstance(source.get(k), (int, float)) or not isclose(source[k], v, rel_tol=0, abs_tol=1e-12) for k, v in reference.items()):
            return result
    for case, growth, discount, terminal in (("low", -0.02, 0.01, -0.005), ("high", 0.015, -0.005, 0.003)):
        result[case] = {
            **defaults,
            "initial_growth": defaults["initial_growth"] + growth,
            "discount_rate": defaults["discount_rate"] + discount,
            "terminal_growth": defaults["terminal_growth"] + terminal,
        }
    return result
