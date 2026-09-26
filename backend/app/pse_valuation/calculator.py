"""Interactive calculator for governed PSE V2 intrinsic and relative baselines."""

from __future__ import annotations

import json
from math import isfinite
from numbers import Real
from pathlib import Path
from typing import Any, Mapping

from .models.distributions import distribution_valuation
from .models.fcff import fcff_valuation
from .models.residual_income import residual_income_valuation
from .models.sotp import sotp_valuation


SCENARIO_MAP = {"low": "bear", "base": "base", "high": "bull"}


def _field(
    key: str,
    label: str,
    value: float,
    low: float,
    high: float,
    step: float,
    *,
    unit: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "value": value,
        "min": low,
        "max": high,
        "step": step,
        "unit": unit,
    }


def _baseline_range(artifact: Mapping[str, Any]) -> dict[str, float]:
    if artifact.get("availability_type") == "intrinsic_valuation":
        scenarios = artifact["scenarios"]
        return {
            "low": float(scenarios["bear"]["value_per_share"]),
            "base": float(scenarios["base"]["value_per_share"]),
            "high": float(scenarios["bull"]["value_per_share"]),
        }
    estimates = artifact.get("market_relative", {}).get("estimates", {})
    if set(estimates) != {"low", "base", "high"}:
        raise ValueError("PSE calculator baseline is unavailable")
    return {name: float(estimates[name]) for name in ("low", "base", "high")}


def calculator_view(artifact: Mapping[str, Any]) -> dict[str, Any]:
    ticker = str(artifact["ticker"])
    if artifact.get("availability_type") == "not_available":
        return {
            "ticker": ticker,
            "assigned_model": artifact["primary_model"],
            "model_version": artifact["model_version"],
            "baseline_version": artifact.get("catalog", {}).get("catalog_version"),
            "availability_type": "not_available",
            "can_calculate": False,
            "defaults": {},
            "scenario_presets": {"low": {}, "base": {}, "high": {}},
            "scenario_preset_note": "No current per-share baseline is available for editing.",
            "editable_assumptions": [],
            "locked_facts": ["issuer identity", "source evidence", "blocking reasons"],
            "baseline_result": None,
            "warnings": artifact.get("warnings", []),
        }
    baseline = _baseline_range(artifact)
    common = {
        "ticker": ticker,
        "assigned_model": artifact["primary_model"],
        "model_version": artifact["model_version"],
        "baseline_version": artifact.get("catalog", {}).get("catalog_version"),
        "availability_type": artifact["availability_type"],
        "can_calculate": True,
        "locked_facts": [
            "issuer identity",
            "source filings",
            "per-share input",
            "capital bridge",
            "publication classification",
        ],
        "baseline_result": baseline,
    }
    if artifact["availability_type"] == "intrinsic_valuation":
        published = artifact["public_assumptions"]["scenario_assumptions"]
        presets = {
            case: {key: float(value) for key, value in published[name].items()}
            for case, name in SCENARIO_MAP.items()
        }
        defaults = presets["base"]
        if artifact["primary_model"] == "residual_income":
            fields = [
                _field("current_roe", "Current ROE", defaults["current_roe"], 0.03, 0.30, 0.005, unit="percent"),
                _field("terminal_roe", "Terminal ROE", defaults["terminal_roe"], 0.05, 0.25, 0.005, unit="percent"),
                _field("cost_of_equity", "Cost of equity", defaults["cost_of_equity"], 0.08, 0.20, 0.0025, unit="percent"),
                _field("payout_ratio", "Payout ratio", defaults["payout_ratio"], 0.0, 0.90, 0.025, unit="percent"),
                _field("terminal_growth", "Terminal growth", defaults["terminal_growth"], 0.0, 0.05, 0.0025, unit="percent"),
            ]
            note = "Adjust the selected residual-income case; reported book value remains locked."
        elif artifact["primary_model"] == "sustainable_distributions":
            fields = [
                _field("explicit_growth", "Distribution growth", defaults["explicit_growth"], -0.10, 0.15, 0.005, unit="percent"),
                _field("cost_of_equity", "Cost of equity", defaults["cost_of_equity"], 0.07, 0.20, 0.0025, unit="percent"),
            ]
            if artifact["public_assumptions"].get("finite_life_years") is None:
                fields.append(
                    _field("terminal_growth", "Terminal growth", defaults["terminal_growth"], 0.0, 0.05, 0.0025, unit="percent")
                )
                note = "Adjust the selected distribution case; reviewed distribution per share remains locked."
            else:
                note = "Adjust the selected finite-life distribution case; the payout and documented expiry remain locked."
        elif artifact["primary_model"] == "sotp":
            fields = [
                _field("uplift_realization", "Fair-value uplift realized", defaults["uplift_realization"], 0.0, 1.0, 0.05, unit="percent"),
                _field("tax_leakage", "Tax and realization leakage", defaults["tax_leakage"], 0.0, 0.40, 0.025, unit="percent"),
            ]
            note = "Adjust the selected RNAV case; reported equity, property values, claims, and shares remain locked."
        else:
            fields = [
                _field("growth_rate", "Explicit growth", defaults["growth_rate"], -0.05, 0.15, 0.005, unit="percent"),
                _field("roic", "Explicit ROIC", defaults["roic"], 0.05, 0.30, 0.005, unit="percent"),
                _field("wacc", "Discount rate", defaults["wacc"], 0.06, 0.20, 0.0025, unit="percent"),
                _field("terminal_growth", "Terminal growth", defaults["terminal_growth"], 0.0, 0.04, 0.0025, unit="percent"),
                _field("terminal_roic", "Terminal ROIC", defaults["terminal_roic"], 0.05, 0.25, 0.005, unit="percent"),
            ]
            note = "Adjust the selected FCFF case; filing facts and the capital bridge remain locked."
    else:
        relative = artifact["market_relative"]
        key = "valuation_multiple" if relative["relation"] == "multiple" else "required_yield"
        presets = {case: {key: float(relative["assumptions"][case])} for case in ("low", "base", "high")}
        defaults = presets["base"]
        if key == "valuation_multiple":
            values = list(relative["assumptions"].values())
            is_subunit_multiple = relative.get("metric") in {"price_to_book", "price_to_sales"}
            fields = [
                _field(
                    key,
                    "Valuation multiple",
                    defaults[key],
                    max(0.05 if is_subunit_multiple else 1.0, min(values) * 0.5),
                    max(values) * 1.5,
                    0.05 if is_subunit_multiple else 0.25,
                    unit="multiple",
                )
            ]
        else:
            fields = [_field(key, "Required distribution yield", defaults[key], 0.03, 0.15, 0.0025, unit="percent")]
        note = "Adjust the selected screening case; the source metric and intrinsic-model limitations remain locked."
    return {
        **common,
        "defaults": defaults,
        "scenario_presets": presets,
        "scenario_preset_note": note,
        "editable_assumptions": fields,
        "warnings": artifact.get("warnings", []),
    }


def _validate(view: Mapping[str, Any], overrides: Mapping[str, Any], scenario: str) -> dict[str, float]:
    if scenario not in SCENARIO_MAP:
        raise ValueError("unknown valuation scenario")
    fields = {field["key"]: field for field in view["editable_assumptions"]}
    unknown = sorted(set(overrides) - set(fields))
    if unknown:
        raise ValueError(f"unsupported calculator assumptions: {', '.join(unknown)}")
    values = dict(view["scenario_presets"][scenario])
    for key, raw in overrides.items():
        if isinstance(raw, bool) or not isinstance(raw, Real) or not isfinite(float(raw)):
            raise ValueError(f"{key} must be a finite number")
        value = float(raw)
        field = fields[key]
        if value < field["min"] or value > field["max"]:
            raise ValueError(f"{key} must be between {field['min']} and {field['max']}")
        values[key] = value
    if {"wacc", "terminal_growth"} <= set(values) and values["wacc"] - values["terminal_growth"] < 0.02:
        raise ValueError("terminal_growth must remain at least 2% below wacc")
    if {"growth_rate", "roic"} <= set(values) and values["growth_rate"] >= values["roic"]:
        raise ValueError("growth_rate must remain below roic")
    if {"terminal_growth", "terminal_roic"} <= set(values) and values["terminal_growth"] >= values["terminal_roic"]:
        raise ValueError("terminal_growth must remain below terminal_roic")
    if {"cost_of_equity", "terminal_growth"} <= set(values) and values["cost_of_equity"] - values["terminal_growth"] < 0.02:
        raise ValueError("terminal_growth must remain at least 2% below cost_of_equity")
    if {"terminal_roe", "terminal_growth"} <= set(values) and values["terminal_growth"] >= values["terminal_roe"]:
        raise ValueError("terminal_growth must remain below terminal_roe")
    return values


def _fcff_value(artifact: Mapping[str, Any], values: Mapping[str, float]) -> float:
    bridge = artifact["public_assumptions"].get("capital_bridge")
    if bridge is None:
        if artifact["ticker"] != "AP":
            raise ValueError("FCFF calculator capital bridge is unavailable")
        seed_path = Path(__file__).resolve().parents[1] / "seed" / "financials_data.json"
        payload = json.loads(seed_path.read_text(encoding="utf-8"))
        company = next(row for row in payload["companies"] if row["symbol"] == "AP")
        financials = company["financials"]
        bridge = {
            "cash_php_millions": float(financials["cash"]) / 1_000_000,
            "debt_php_millions": float(financials["debt"]) / 1_000_000,
            "shares_millions": float(financials["shares"]) / 1_000_000,
        }
    normalized_fcff = float(artifact["public_assumptions"]["normalized_fcff_proxy_php_millions"])
    starting_nopat = normalized_fcff / (1 - values["growth_rate"] / values["roic"])
    result = fcff_valuation(
        starting_nopat=starting_nopat,
        growth_rate=values["growth_rate"],
        roic=values["roic"],
        wacc=values["wacc"],
        terminal_growth=values["terminal_growth"],
        terminal_roic=values["terminal_roic"],
        cash=float(bridge["cash_php_millions"]),
        nonoperating_assets=float(bridge.get("nonoperating_assets_php_millions", 0.0)),
        debt=float(bridge["debt_php_millions"]),
        preferred_claims=float(bridge.get("preferred_claims_php_millions", 0.0)),
        minority_value=float(bridge.get("minority_value_php_millions", 0.0)),
        other_claims=float(bridge.get("other_claims_php_millions", 0.0)),
        shares_outstanding=float(bridge["shares_millions"]),
    )
    value = float(result["value_per_share"])
    if value <= 0 or not isfinite(value):
        raise ValueError("calculator assumptions produce a non-positive common-equity value")
    return value


def _residual_income_value(artifact: Mapping[str, Any], values: Mapping[str, float]) -> float:
    result = residual_income_valuation(
        opening_common_equity=float(artifact["public_assumptions"]["book_value_per_share"]),
        shares_outstanding=1.0,
        forecast_years=int(artifact["public_assumptions"]["forecast_years"]),
        current_roe=values["current_roe"],
        terminal_roe=values["terminal_roe"],
        cost_of_equity=values["cost_of_equity"],
        payout_ratio=values["payout_ratio"],
        terminal_growth=values["terminal_growth"],
    )
    return float(result["value_per_share"])


def _distribution_value(artifact: Mapping[str, Any], values: Mapping[str, float]) -> float:
    finite_life = artifact["public_assumptions"].get("finite_life_years")
    result = distribution_valuation(
        current_distribution_per_share=float(
            artifact["public_assumptions"]["current_distribution_per_share"]
        ),
        forecast_years=int(artifact["public_assumptions"]["forecast_years"]),
        explicit_growth=values["explicit_growth"],
        cost_of_equity=values["cost_of_equity"],
        terminal_growth=values.get("terminal_growth"),
        finite_life_years=int(finite_life) if finite_life is not None else None,
    )
    return float(result["value_per_share"])


def _sotp_value(artifact: Mapping[str, Any], values: Mapping[str, float]) -> float:
    bridge = artifact["public_assumptions"].get("nav_bridge")
    if not isinstance(bridge, Mapping):
        raise ValueError("SOTP calculator NAV bridge is unavailable")
    property_by_owner = bridge.get("property_by_owner")
    if property_by_owner is not None:
        if not isinstance(property_by_owner, list) or not property_by_owner:
            raise ValueError("SOTP calculator property-by-owner bridge is invalid")
        property_components = [
            {
                "name": row["name"],
                "equity_value": (
                    float(row["fair_value_php_millions"])
                    - float(row["carrying_value_php_millions"])
                ) * values["uplift_realization"] * (1 - values["tax_leakage"]),
                "ownership": float(row["ownership"]),
            }
            for row in property_by_owner
        ]
    else:
        raw_uplift = float(bridge["investment_property_fair_value_php_millions"]) - float(
            bridge["investment_property_carrying_value_php_millions"]
        )
        adjusted_uplift = raw_uplift * values["uplift_realization"] * (1 - values["tax_leakage"])
        property_components = [
            {"name": "after_tax_property_fair_value_uplift", "equity_value": adjusted_uplift, "ownership": 1.0}
        ]
    result = sotp_valuation(
        components=[
            {
                "name": "reported_parent_equity",
                "equity_value": float(bridge["parent_equity_php_millions"]),
                "ownership": 1.0,
            },
            *property_components,
        ],
        shares_outstanding=float(bridge["shares_millions"]),
        other_parent_claims=float(bridge.get("preferred_claims_php_millions", 0.0)),
    )
    return float(result["value_per_share"])


def _intrinsic_value(artifact: Mapping[str, Any], values: Mapping[str, float]) -> float:
    model = artifact["primary_model"]
    if model == "residual_income":
        value = _residual_income_value(artifact, values)
    elif model == "sustainable_distributions":
        value = _distribution_value(artifact, values)
    elif model == "sotp":
        value = _sotp_value(artifact, values)
    elif model in {"fcff_dcf", "normalized_fcff"}:
        value = _fcff_value(artifact, values)
    else:
        raise ValueError(f"calculator is unavailable for intrinsic model: {model}")
    if value <= 0 or not isfinite(value):
        raise ValueError("calculator assumptions produce a non-positive common-equity value")
    return value


def _relative_value(artifact: Mapping[str, Any], values: Mapping[str, float]) -> float:
    relative = artifact["market_relative"]
    metric = float(relative["metric_value_per_share"])
    if relative["relation"] == "multiple":
        return metric * values["valuation_multiple"]
    return metric / values["required_yield"]


def _comparison(value: float, price: float) -> dict[str, Any]:
    if not isfinite(price) or price <= 0:
        raise ValueError("manual_price must be positive and finite")
    gap = value / price - 1
    if abs(gap) <= 0.05:
        verdict, label = "fair_value", "Near FinSight's selected value"
    elif gap > 0:
        verdict, label = "undervalued", f"Price is {abs(gap):.1%} below FinSight's selected value"
    else:
        verdict, label = "overvalued", f"Price is {abs(gap):.1%} above FinSight's selected value"
    return {"status": "available", "source": "manual", "price": price, "gap_pct": gap, "label": label, "verdict": verdict}


def calculate(
    artifact: Mapping[str, Any],
    *,
    overrides: Mapping[str, Any],
    scenario: str,
    manual_price: float | None,
) -> dict[str, Any]:
    view = calculator_view(artifact)
    if not view["can_calculate"]:
        raise ValueError("PSE calculator baseline is unavailable")
    values = _validate(view, overrides, scenario)
    selected = _intrinsic_value(artifact, values) if artifact["availability_type"] == "intrinsic_valuation" else _relative_value(artifact, values)
    result = dict(view["baseline_result"])
    result[scenario] = selected
    comparison = _comparison(selected, manual_price) if manual_price is not None else None
    return {
        **view,
        "selected_scenario": scenario,
        "assumptions": values,
        "result": result,
        "baseline_change_pct": selected / view["baseline_result"][scenario] - 1,
        "comparison": comparison,
        "manual_price": manual_price,
    }
