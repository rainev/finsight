"""Safe, baseline-calibrated assumption calculator for public U.S. valuations."""

from __future__ import annotations

from math import isfinite
from numbers import Real
from typing import Any, Mapping


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


def _lane(artifact: Mapping[str, Any]) -> str:
    forecast_mode = artifact.get("public_assumptions", {}).get("forecast_mode")
    if forecast_mode == "asset_runway_equity":
        return "asset_runway"
    if forecast_mode == "normalized_equity_earnings":
        return "equity_earnings"
    primary = artifact.get("model_policy", {}).get("primary")
    if primary == "residual_income":
        return "bank"
    if primary == "ffo":
        return "reit"
    if primary in {"ddm", "fcfe_dcf"}:
        return "utility_or_equity"
    return "operating"


def _safe_rates(assumptions: Mapping[str, Any]) -> tuple[float, float, int, float]:
    growth = _number(
        assumptions.get("initial_revenue_growth", assumptions.get("high_dividend_growth")),
        0.03,
    )
    discount = _number(
        assumptions.get("policy_wacc", assumptions.get("cost_of_equity")),
        0.10,
    )
    terminal = _number(assumptions.get("terminal_growth"), 0.02)
    years = int(_number(assumptions.get("forecast_years"), 5))
    years = min(20, max(1, years))
    discount = min(0.30, max(0.04, discount))
    terminal = min(0.04, max(-0.05, terminal))
    if discount - terminal < 0.02:
        terminal = discount - 0.02
    growth = min(0.40, max(-0.20, growth))
    return growth, discount, years, terminal


def _field(key: str, label: str, value: float | int, low: float, high: float, step: float) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "value": value,
        "min": low,
        "max": high,
        "step": step,
    }


def _defaults_and_fields(artifact: Mapping[str, Any]) -> tuple[str, dict[str, float | int], list[dict[str, Any]]]:
    assumptions = artifact.get("public_assumptions")
    assumptions = assumptions if isinstance(assumptions, Mapping) else {}
    lane = _lane(artifact)
    growth, discount, years, terminal = _safe_rates(assumptions)
    if lane == "asset_runway":
        runway_factor = _number(assumptions.get("runway_value_factor"), 1.0)
        defaults = {"runway_value_factor": runway_factor}
        fields = [
            _field("runway_value_factor", "Cash-runway value factor", runway_factor, 0.25, 2.0, 0.025),
        ]
    elif lane == "equity_earnings":
        earnings_factor = _number(assumptions.get("normalized_earnings_factor"), 1.0)
        multiple = _number(assumptions.get("earnings_multiple"), 8.0)
        defaults = {
            "normalized_earnings_factor": earnings_factor,
            "earnings_multiple": multiple,
        }
        fields = [
            _field("normalized_earnings_factor", "Normalized earnings factor", earnings_factor, 0.25, 2.0, 0.025),
            _field("earnings_multiple", "Earnings multiple", multiple, 2.0, 20.0, 0.25),
        ]
    elif lane == "bank":
        roe = _number(assumptions.get("current_roe"), 0.12)
        payout = _number(assumptions.get("current_payout_ratio"), 0.40)
        defaults = {
            "sustainable_roe": roe,
            "payout_ratio": payout,
            "forecast_years": years,
            "discount_rate": discount,
            "terminal_growth": terminal,
        }
        fields = [
            _field("sustainable_roe", "Sustainable ROE", roe, 0.01, 0.35, 0.005),
            _field("payout_ratio", "Payout ratio", payout, 0.0, 1.0, 0.01),
            _field("forecast_years", "Forecast years", years, 2, 15, 1),
            _field("discount_rate", "Cost of equity", discount, 0.05, 0.25, 0.0025),
            _field("terminal_growth", "Terminal growth", terminal, -0.02, 0.04, 0.0025),
        ]
    elif lane == "reit":
        defaults = {
            "affo_growth": growth,
            "recurring_cost_ratio": 0.0,
            "forecast_years": years,
            "discount_rate": discount,
            "terminal_growth": terminal,
        }
        fields = [
            _field("affo_growth", "AFFO growth", growth, -0.10, 0.20, 0.005),
            _field("recurring_cost_ratio", "Recurring-cost adjustment", 0.0, 0.0, 0.30, 0.01),
            _field("forecast_years", "Forecast years", years, 2, 15, 1),
            _field("discount_rate", "Discount rate", discount, 0.05, 0.25, 0.0025),
            _field("terminal_growth", "Terminal growth", terminal, -0.02, 0.04, 0.0025),
        ]
    elif lane == "utility_or_equity":
        payout = _number(assumptions.get("current_payout_ratio"), 0.60)
        defaults = {
            "dividend_growth": growth,
            "payout_ratio": payout,
            "discount_rate": discount,
            "terminal_growth": terminal,
        }
        fields = [
            _field("dividend_growth", "Dividend/owner-cash growth", growth, -0.10, 0.20, 0.005),
            _field("payout_ratio", "Payout ratio", payout, 0.05, 1.0, 0.01),
            _field("discount_rate", "Cost of equity", discount, 0.05, 0.25, 0.0025),
            _field("terminal_growth", "Terminal growth", terminal, -0.02, 0.04, 0.0025),
        ]
    else:
        defaults = {
            "cash_conversion": 1.0,
            "initial_growth": growth,
            "forecast_years": years,
            "discount_rate": discount,
            "terminal_growth": terminal,
        }
        fields = [
            _field("cash_conversion", "Normalized cash conversion", 1.0, 0.25, 2.0, 0.025),
            _field("initial_growth", "Initial growth", growth, -0.20, 0.40, 0.005),
            _field("forecast_years", "Forecast years", years, 2, 15, 1),
            _field("discount_rate", "Discount rate", discount, 0.05, 0.25, 0.0025),
            _field("terminal_growth", "Terminal growth", terminal, -0.02, 0.04, 0.0025),
        ]
    return lane, defaults, fields


def calculator_view(artifact: Mapping[str, Any]) -> dict[str, Any]:
    scenario = artifact.get("scenario_range")
    scenario = scenario if isinstance(scenario, Mapping) else {}
    base = scenario.get("base")
    ticker = str(artifact.get("ticker") or artifact.get("issuer", {}).get("ticker"))
    if not isinstance(base, Real) or isinstance(base, bool) or not isfinite(float(base)) or base <= 0:
        return {
            "ticker": ticker,
            "assigned_model": artifact.get("primary_valuation_method"),
            "model_version": artifact.get("public_assumptions", {}).get("forecast_policy_version", artifact.get("schema_version")),
            "availability_type": "not_available",
            "can_calculate": False,
            "defaults": {},
            "editable_assumptions": [],
            "locked_facts": ["issuer identity", "source filing", "share denominator", "historical periods"],
            "baseline_result": {"low": None, "base": None, "high": None},
            "market_comparison": artifact.get("market_comparison"),
            "warnings": ["A calculator is unavailable because the official baseline is not available."],
        }
    lane, defaults, fields = _defaults_and_fields(artifact)
    return {
        "ticker": ticker,
        "assigned_model": artifact.get("primary_valuation_method"),
        "model_family": lane,
        "model_version": artifact.get("public_assumptions", {}).get("forecast_policy_version", artifact.get("schema_version")),
        "availability_type": artifact.get("availability_type"),
        "can_calculate": True,
        "defaults": defaults,
        "editable_assumptions": fields,
        "locked_facts": ["issuer identity", "source filing", "share denominator", "historical periods"],
        "baseline_result": {key: float(scenario[key]) for key in ("low", "base", "high")},
        "market_comparison": artifact.get("market_comparison"),
        "warnings": [
            "Baseline-calibrated sensitivity: defaults reproduce FinSight's published value; locked source facts do not change."
        ],
    }


def _validate_overrides(view: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, float | int]:
    fields = {row["key"]: row for row in view["editable_assumptions"]}
    unknown = sorted(set(overrides) - set(fields))
    if unknown:
        raise ValueError(f"unsupported calculator assumptions: {', '.join(unknown)}")
    values = dict(view["defaults"])
    for key, raw in overrides.items():
        if isinstance(raw, bool) or not isinstance(raw, Real) or not isfinite(float(raw)):
            raise ValueError(f"{key} must be a finite number")
        field = fields[key]
        value: float | int = int(raw) if key == "forecast_years" else float(raw)
        if value < field["min"] or value > field["max"]:
            raise ValueError(f"{key} must be between {field['min']} and {field['max']}")
        values[key] = value
    discount = values.get("discount_rate")
    terminal = values.get("terminal_growth")
    if isinstance(discount, Real) and isinstance(terminal, Real) and discount - terminal < 0.02:
        raise ValueError("terminal_growth must remain at least 2% below discount_rate")
    return values


def _factor(lane: str, values: Mapping[str, float | int]) -> float:
    if lane == "asset_runway":
        return float(values["runway_value_factor"])
    if lane == "equity_earnings":
        return float(values["normalized_earnings_factor"]) * float(values["earnings_multiple"])
    if lane == "bank":
        roe = float(values["sustainable_roe"])
        payout = float(values["payout_ratio"])
        sustainable_growth = min(0.15, max(-0.05, roe * (1 - payout)))
        return roe * _projection_factor(
            growth=sustainable_growth,
            discount=float(values["discount_rate"]),
            terminal=float(values["terminal_growth"]),
            years=int(values["forecast_years"]),
        )
    if lane == "reit":
        return (1 - float(values["recurring_cost_ratio"])) * _projection_factor(
            growth=float(values["affo_growth"]),
            discount=float(values["discount_rate"]),
            terminal=float(values["terminal_growth"]),
            years=int(values["forecast_years"]),
        )
    if lane == "utility_or_equity":
        discount = float(values["discount_rate"])
        terminal = float(values["terminal_growth"])
        growth = float(values["dividend_growth"])
        return float(values["payout_ratio"]) * _projection_factor(
            growth=growth,
            discount=discount,
            terminal=terminal,
            years=5,
        )
    return float(values["cash_conversion"]) * _projection_factor(
        growth=float(values["initial_growth"]),
        discount=float(values["discount_rate"]),
        terminal=float(values["terminal_growth"]),
        years=int(values["forecast_years"]),
    )


def _manual_comparison(base: float, manual_price: float) -> dict[str, Any]:
    if not isfinite(manual_price) or manual_price <= 0:
        raise ValueError("manual_price must be positive and finite")
    gap = (base - manual_price) / base
    label = (
        "Near FinSight's base value"
        if abs(gap) <= 0.05
        else f"{'Undervalued' if gap > 0 else 'Overvalued'} by {abs(gap):.1%} versus FinSight value"
    )
    return {
        "status": "available",
        "source": "manual",
        "gap_pct": gap,
        "label": label,
        "denominator": "finsight_base_value",
    }


def calculate(
    artifact: Mapping[str, Any],
    *,
    overrides: Mapping[str, Any],
    manual_price: float | None,
) -> dict[str, Any]:
    view = calculator_view(artifact)
    if not view["can_calculate"]:
        raise ValueError("calculator is unavailable for this valuation")
    values = _validate_overrides(view, overrides)
    default_factor = _factor(view["model_family"], view["defaults"])
    user_factor = _factor(view["model_family"], values)
    if default_factor <= 0 or user_factor <= 0 or not isfinite(user_factor):
        raise ValueError("calculator assumptions produce an unusable value")
    multiplier = user_factor / default_factor
    baseline = view["baseline_result"]
    result = {key: baseline[key] * multiplier for key in ("low", "base", "high")}
    comparison = (
        _manual_comparison(result["base"], manual_price)
        if manual_price is not None
        else artifact.get("market_comparison")
    )
    return {
        **view,
        "assumptions": values,
        "result": result,
        "baseline_change_pct": result["base"] / baseline["base"] - 1,
        "comparison": comparison,
        "comparison_source": "manual" if manual_price is not None else "automatic_eod",
        "manual_price": manual_price,
    }
