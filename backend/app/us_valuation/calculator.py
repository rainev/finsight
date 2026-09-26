"""Validated, baseline-calibrated calculator for published batch valuations.

The calculator changes only governed assumptions. Issuer identity, filing,
historical periods, share denominator, and private bridge facts stay locked.
Defaults exactly reproduce the confirmed catalog range.
"""

from __future__ import annotations

from math import isfinite
from numbers import Real
from typing import Any, Mapping

from .scenario_presets import case_presets


def _number(value: object, fallback: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value)):
        return fallback
    return float(value)


def _projection_factor(*, growth: float, discount: float, terminal: float, years: int) -> float:
    if not 1 <= years <= 20:
        raise ValueError("forecast_years must be between 1 and 20")
    if not -0.20 <= growth <= 0.40:
        raise ValueError("growth is outside the safe range")
    if not 0.04 <= discount <= 0.30:
        raise ValueError("discount_rate is outside the safe range")
    if not -0.05 <= terminal <= 0.04 or discount - terminal < 0.02:
        raise ValueError("terminal_growth must remain at least 2% below discount_rate")
    cash = 1.0
    present = 0.0
    for year in range(1, years + 1):
        fade = (years - year) / max(1, years - 1)
        year_growth = terminal + (growth - terminal) * fade
        cash *= 1 + year_growth
        present += cash / (1 + discount) ** year
    terminal_cash = cash * (1 + terminal)
    return present + terminal_cash / (discount - terminal) / (1 + discount) ** years


def _model_family(artifact: Mapping[str, Any]) -> str:
    assumptions = artifact.get("public_assumptions")
    assumptions = assumptions if isinstance(assumptions, Mapping) else {}
    mode = assumptions.get("forecast_mode")
    primary = artifact.get("primary_valuation_method") or artifact.get("model_policy", {}).get("primary")
    if mode == "asset_runway_equity":
        return "asset_runway"
    if mode == "normalized_equity_earnings":
        return "equity_earnings"
    if primary == "residual_income":
        return "bank"
    if primary == "ffo":
        return "reit"
    if primary in {"ddm", "fcfe_dcf"}:
        return "utility_or_equity"
    return "operating"


def _safe_rates(assumptions: Mapping[str, Any]) -> tuple[float, float, int, float]:
    growth = _number(
        assumptions.get(
            "initial_revenue_growth",
            assumptions.get("growth", assumptions.get("high_dividend_growth")),
        ),
        0.03,
    )
    discount = _number(
        assumptions.get(
            "policy_wacc",
            assumptions.get("wacc", assumptions.get("cost_of_equity")),
        ),
        0.10,
    )
    terminal = _number(assumptions.get("terminal_growth"), 0.02)
    years = min(20, max(1, int(_number(assumptions.get("forecast_years"), 5))))
    discount = min(0.30, max(0.04, discount))
    terminal = min(0.04, max(-0.05, terminal))
    if discount - terminal < 0.02:
        terminal = discount - 0.02
    return min(0.40, max(-0.20, growth)), discount, years, terminal


def _field(
    key: str,
    label: str,
    value: float | int,
    low: float,
    high: float,
    step: float,
    *,
    unit: str = "number",
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


def _defaults_and_fields(
    artifact: Mapping[str, Any],
) -> tuple[str, dict[str, float | int], list[dict[str, Any]]]:
    assumptions = artifact.get("public_assumptions")
    assumptions = assumptions if isinstance(assumptions, Mapping) else {}
    family = _model_family(artifact)
    growth, discount, years, terminal = _safe_rates(assumptions)
    pct = {"unit": "percent"}
    if family == "asset_runway":
        factor = _number(assumptions.get("runway_value_factor"), 1.0)
        defaults = {"runway_value_factor": factor}
        fields = [_field("runway_value_factor", "Cash-runway value factor", factor, 0.25, 2.0, 0.025)]
    elif family == "equity_earnings":
        earnings = _number(assumptions.get("normalized_earnings_factor"), 1.0)
        multiple = _number(assumptions.get("earnings_multiple"), 8.0)
        defaults = {"normalized_earnings_factor": earnings, "earnings_multiple": multiple}
        fields = [
            _field("normalized_earnings_factor", "Normalized earnings factor", earnings, 0.25, 2.0, 0.025),
            _field("earnings_multiple", "Earnings multiple", multiple, 2.0, 20.0, 0.25, unit="multiple"),
        ]
    elif family == "bank":
        roe = _number(assumptions.get("current_roe", assumptions.get("terminal_roe")), 0.12)
        payout = _number(assumptions.get("current_payout_ratio"), 0.40)
        defaults = {
            "sustainable_roe": roe,
            "discount_rate": discount,
            "terminal_growth": terminal,
            "payout_ratio": payout,
            "forecast_years": years,
        }
        fields = [
            _field("sustainable_roe", "Sustainable ROE", roe, 0.01, 0.35, 0.005, **pct),
            _field("discount_rate", "Cost of equity", discount, 0.05, 0.25, 0.0025, **pct),
            _field("terminal_growth", "Terminal growth", terminal, -0.02, 0.04, 0.0025, **pct),
            _field("payout_ratio", "Payout ratio", payout, 0.0, 1.0, 0.01, **pct),
            _field("forecast_years", "Forecast years", years, 2, 15, 1, unit="years"),
        ]
    elif family == "reit":
        defaults = {
            "affo_growth": growth,
            "discount_rate": discount,
            "terminal_growth": terminal,
            "recurring_cost_ratio": 0.0,
            "forecast_years": years,
        }
        fields = [
            _field("affo_growth", "AFFO growth", growth, -0.10, 0.20, 0.005, **pct),
            _field("discount_rate", "Discount rate", discount, 0.05, 0.25, 0.0025, **pct),
            _field("terminal_growth", "Terminal growth", terminal, -0.02, 0.04, 0.0025, **pct),
            _field("recurring_cost_ratio", "Recurring-cost adjustment", 0.0, 0.0, 0.30, 0.01, **pct),
            _field("forecast_years", "Forecast years", years, 2, 15, 1, unit="years"),
        ]
    elif family == "utility_or_equity":
        payout = _number(assumptions.get("current_payout_ratio"), 0.60)
        defaults = {
            "dividend_growth": growth,
            "discount_rate": discount,
            "terminal_growth": terminal,
            "payout_ratio": payout,
        }
        fields = [
            _field("dividend_growth", "Dividend growth", growth, -0.10, 0.20, 0.005, **pct),
            _field("discount_rate", "Cost of equity", discount, 0.05, 0.25, 0.0025, **pct),
            _field("terminal_growth", "Terminal growth", terminal, -0.02, 0.04, 0.0025, **pct),
            _field("payout_ratio", "Payout ratio", payout, 0.05, 1.0, 0.01, **pct),
        ]
    else:
        defaults = {
            "initial_growth": growth,
            "discount_rate": discount,
            "terminal_growth": terminal,
            "cash_conversion": 1.0,
            "forecast_years": years,
        }
        fields = [
            _field("initial_growth", "Initial growth", growth, -0.20, 0.40, 0.005, **pct),
            _field("discount_rate", "Discount rate", discount, 0.05, 0.25, 0.0025, **pct),
            _field("terminal_growth", "Terminal growth", terminal, -0.02, 0.04, 0.0025, **pct),
            _field("cash_conversion", "Normalized cash conversion", 1.0, 0.25, 2.0, 0.025),
            _field("forecast_years", "Forecast years", years, 2, 15, 1, unit="years"),
        ]
    return family, defaults, fields


def calculator_view(artifact: Mapping[str, Any]) -> dict[str, Any]:
    scenario = artifact.get("scenario_range")
    scenario = scenario if isinstance(scenario, Mapping) else {}
    base = scenario.get("base")
    ticker = str(artifact.get("ticker") or artifact.get("issuer", {}).get("ticker"))
    common = {
        "ticker": ticker,
        "assigned_model": artifact.get("primary_valuation_method")
        or artifact.get("model_policy", {}).get("primary"),
        "model_version": artifact.get("public_assumptions", {}).get(
            "forecast_policy_version", artifact.get("schema_version")
        ),
        "locked_facts": [
            "issuer identity",
            "source filing",
            "share denominator",
            "historical periods",
            "capital bridge",
        ],
    }
    if not isinstance(base, Real) or isinstance(base, bool) or not isfinite(float(base)) or base <= 0:
        return {
            **common,
            "availability_type": "not_available",
            "can_calculate": False,
            "defaults": {},
            "editable_assumptions": [],
            "baseline_result": {"low": None, "base": None, "high": None},
            "warnings": ["Calculator unavailable because the confirmed baseline is unavailable."],
        }
    family, defaults, fields = _defaults_and_fields(artifact)
    presets = case_presets(artifact, defaults)
    return {
        **common,
        "model_family": family,
        "availability_type": artifact.get("availability_type"),
        "can_calculate": True,
        "defaults": defaults,
        "scenario_presets": presets,
        "scenario_preset_note": (
            "Confirmed case inputs. Published cases also include margin, capital-efficiency and bridge adjustments. "
            "Edits use a sensitivity anchored to the selected case, not a full model rerun."
            if len(presets) == 3 else
            "Only Base-case inputs have been verified for this baseline; Bear/Bull input presets are unavailable."
        ),
        "editable_assumptions": fields,
        "baseline_result": {key: float(scenario[key]) for key in ("low", "base", "high")},
        "warnings": [
            "Defaults reproduce the confirmed FinSight baseline; locked filing facts do not change."
        ],
    }


def _validate_overrides(view: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, float | int]:
    fields = {field["key"]: field for field in view["editable_assumptions"]}
    unknown = sorted(set(overrides) - set(fields))
    if unknown:
        raise ValueError(f"unsupported calculator assumptions: {', '.join(unknown)}")
    values = dict(view["defaults"])
    for key, raw in overrides.items():
        if isinstance(raw, bool) or not isinstance(raw, Real) or not isfinite(float(raw)):
            raise ValueError(f"{key} must be a finite number")
        field = fields[key]
        value: float | int = int(raw) if field.get("unit") == "years" else float(raw)
        if value < field["min"] or value > field["max"]:
            raise ValueError(f"{key} must be between {field['min']} and {field['max']}")
        values[key] = value
    discount = values.get("discount_rate")
    terminal = values.get("terminal_growth")
    if isinstance(discount, Real) and isinstance(terminal, Real) and discount - terminal < 0.02:
        raise ValueError("terminal_growth must remain at least 2% below discount_rate")
    return values


def _factor(family: str, values: Mapping[str, float | int]) -> float:
    if family == "asset_runway":
        return float(values["runway_value_factor"])
    if family == "equity_earnings":
        return float(values["normalized_earnings_factor"]) * float(values["earnings_multiple"])
    if family == "bank":
        roe = float(values["sustainable_roe"])
        payout = float(values["payout_ratio"])
        growth = min(0.15, max(-0.05, roe * (1 - payout)))
        return roe * _projection_factor(
            growth=growth,
            discount=float(values["discount_rate"]),
            terminal=float(values["terminal_growth"]),
            years=int(values["forecast_years"]),
        )
    if family == "reit":
        return (1 - float(values["recurring_cost_ratio"])) * _projection_factor(
            growth=float(values["affo_growth"]),
            discount=float(values["discount_rate"]),
            terminal=float(values["terminal_growth"]),
            years=int(values["forecast_years"]),
        )
    if family == "utility_or_equity":
        return float(values["payout_ratio"]) * _projection_factor(
            growth=float(values["dividend_growth"]),
            discount=float(values["discount_rate"]),
            terminal=float(values["terminal_growth"]),
            years=5,
        )
    return float(values["cash_conversion"]) * _projection_factor(
        growth=float(values["initial_growth"]),
        discount=float(values["discount_rate"]),
        terminal=float(values["terminal_growth"]),
        years=int(values["forecast_years"]),
    )


def _manual_comparison(base: float, price: float) -> dict[str, Any]:
    if not isfinite(price) or price <= 0:
        raise ValueError("manual_price must be positive and finite")
    gap = (base - price) / base
    if abs(gap) <= 0.05:
        label = "Near FinSight's base value"
        verdict = "fair_value"
    elif gap > 0:
        label = f"Undervalued by {abs(gap):.1%} versus FinSight value"
        verdict = "undervalued"
    else:
        label = f"Overvalued by {abs(gap):.1%} versus FinSight value"
        verdict = "overvalued"
    return {
        "status": "available",
        "source": "manual",
        "price": price,
        "gap_pct": gap,
        "label": label,
        "verdict": verdict,
        "denominator": "finsight_base_value",
    }


def calculate(
    artifact: Mapping[str, Any],
    *,
    overrides: Mapping[str, Any],
    manual_price: float | None,
    scenario: str = "base",
) -> dict[str, Any]:
    view = calculator_view(artifact)
    if not view["can_calculate"]:
        raise ValueError("calculator is unavailable for this valuation")
    if scenario not in ("low", "base", "high"):
        raise ValueError("unknown valuation scenario")
    preset = view["scenario_presets"].get(scenario)
    if preset is None and overrides:
        raise ValueError("Case-specific assumptions are unavailable; select Base to edit inputs.")
    anchor = preset if preset is not None else view["defaults"]
    values = _validate_overrides({**view, "defaults": anchor}, overrides)
    default_factor = _factor(view["model_family"], anchor)
    user_factor = _factor(view["model_family"], values)
    if default_factor <= 0 or user_factor <= 0 or not isfinite(user_factor):
        raise ValueError("calculator assumptions produce an unusable value")
    multiplier = user_factor / default_factor
    baseline = view["baseline_result"]
    result = {key: baseline[key] * multiplier for key in ("low", "base", "high")}
    comparison = _manual_comparison(result[scenario], manual_price) if manual_price is not None else None
    if comparison is not None and scenario != "base":
        comparison["denominator"] = "finsight_selected_case_value"
        if comparison["verdict"] == "fair_value":
            comparison["label"] = "Near FinSight's selected case value"
    return {
        **view,
        "selected_scenario": scenario,
        "assumptions": values,
        "result": result,
        "baseline_change_pct": result["base"] / baseline["base"] - 1,
        "comparison": comparison,
        "comparison_source": "manual" if manual_price is not None else None,
        "manual_price": manual_price,
    }
