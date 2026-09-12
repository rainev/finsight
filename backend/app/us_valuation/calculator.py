"""Safe, baseline-calibrated assumption calculator for public U.S. valuations."""

from __future__ import annotations

from math import isfinite, isclose
import hashlib
import json
from numbers import Real
from typing import Any, Mapping

from app.valuation.bank import residual_income_valuation
from .calculation_recipe import evaluate_recipe, recipe_hash
from .market_comparison import public_scenario_market_comparison


def baseline_version(artifact: Mapping[str, Any]) -> str:
    fields = {key: artifact.get(key) for key in ('issuer', 'valuation_date', 'source_financial_statement', 'model_policy', 'public_assumptions', 'scenario_range')}
    return hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


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
    if forecast_mode == "residual_income_exact":
        return "residual_income"
    if forecast_mode == "enterprise_cash_fcff_exact":
        return "enterprise_fcff"
    if forecast_mode == "utility_fcfe_exact":
        return "utility_fcfe"
    if forecast_mode == "reit_affo_exact":
        return "reit"
    if forecast_mode == "timber_distribution_exact":
        return "distribution_ddm"
    primary = artifact.get("model_policy", {}).get("primary")
    if primary == "residual_income":
        return "bank"
    if primary in {"ffo", "affo_dcf"}:
        return "reit"
    if primary in {"ddm", "total_payout_ddm", "fcfe_dcf"}:
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
    unit = (
        "percent" if key in {
            "sustainable_roe", "payout_ratio", "discount_rate", "terminal_growth",
            "affo_growth", "recurring_cost_ratio", "dividend_growth", "initial_growth",
            "terminal_roe", "debt_funding_share",
        } else "years" if key in {"forecast_years"} else "multiple" if key in {"earnings_multiple", "cash_conversion"} else "number"
    )
    return {
        "key": key,
        "label": label,
        "value": value,
        "min": low,
        "max": high,
        "step": step,
        "unit": unit,
    }


def _scenario_name(value: str | None) -> str:
    normalized = str(value or "base").strip().lower()
    if normalized not in {"low", "base", "high"}:
        raise ValueError("selected scenario must be low, base, or high")
    return normalized


def _recipe_scenario_name(value: str) -> str:
    return {"low": "bear", "base": "base", "high": "bull"}[value]


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
    elif lane == "residual_income":
        book = _number(assumptions.get("book_value_per_share"), 0.0)
        roe = _number(assumptions.get("current_roe"), 0.12)
        payout = _number(assumptions.get("current_payout_ratio"), 0.40)
        terminal_roe = _number(assumptions.get("terminal_roe"), 0.10)
        defaults = {
            "book_value_per_share": book,
            "sustainable_roe": roe,
            "payout_ratio": payout,
            "terminal_roe": terminal_roe,
            "forecast_years": years,
            "discount_rate": discount,
            "terminal_growth": terminal,
        }
        fields = [
            _field("sustainable_roe", "Sustainable ROE", roe, 0.01, 0.35, 0.005),
            _field("payout_ratio", "Payout ratio", payout, 0.0, 1.0, 0.01),
            _field("terminal_roe", "Terminal ROE", terminal_roe, 0.01, 0.25, 0.005),
            _field("forecast_years", "Forecast years", years, 2, 15, 1),
            _field("discount_rate", "Cost of equity", discount, 0.05, 0.25, 0.0025),
            _field("terminal_growth", "Terminal growth", terminal, 0.0, 0.04, 0.0025),
        ]
    elif lane == "enterprise_fcff":
        starting_cash = _number(assumptions.get("starting_cash_fcff_per_share"), 0.0)
        bridge = _number(assumptions.get("bridge_adjustment_per_share"), 0.0)
        defaults = {
            "starting_cash_fcff_per_share": starting_cash,
            "bridge_adjustment_per_share": bridge,
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
            _field("terminal_growth", "Terminal growth", terminal, -0.05, 0.04, 0.0025),
        ]
    elif lane == "utility_fcfe":
        cfo = _number(assumptions.get("operating_cash_flow_per_share"), 0.0)
        capex = _number(assumptions.get("capital_expenditures_per_share"), 0.0)
        income = _number(assumptions.get("model_income_before_parent_allocation_per_share"), 0.0)
        parent = _number(assumptions.get("parent_cash_flow_share"), 1.0)
        funding = _number(assumptions.get("debt_funding_share"), 0.5)
        defaults = {"operating_cash_flow_per_share": cfo, "capital_expenditures_per_share": capex, "model_income_before_parent_allocation_per_share": income, "parent_cash_flow_share": parent, "debt_funding_share": funding, "initial_growth": growth, "forecast_years": years, "discount_rate": discount, "terminal_growth": terminal}
        fields = [_field("debt_funding_share", "Debt-funded reinvestment", funding, 0.0, 1.0, 0.01), _field("initial_growth", "Owner-cash growth", growth, -0.10, 0.20, 0.005), _field("forecast_years", "Forecast years", years, 2, 15, 1), _field("discount_rate", "Cost of equity", discount, 0.05, 0.25, 0.0025), _field("terminal_growth", "Terminal growth", terminal, -0.02, 0.04, 0.0025)]
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
        normalized_affo = _number(assumptions.get("normalized_affo_per_share"), 1.0)
        value_adjustment = _number(assumptions.get("nonrecurring_value_adjustment_per_share"), 0.0)
        exact_affo = assumptions.get("forecast_mode") == "reit_affo_exact"
        defaults = {
            "normalized_affo_per_share": normalized_affo,
            "nonrecurring_value_adjustment_per_share": value_adjustment,
            "affo_growth": growth,
            "recurring_cost_ratio": 0.0,
            "forecast_years": years,
            "discount_rate": discount,
            "terminal_growth": terminal,
        }
        fields = [
            _field("affo_growth", "AFFO growth", growth, -0.10, 0.20, 0.005),
            _field("discount_rate", "Discount rate", discount, 0.05, 0.25, 0.0025),
        ]
        if not exact_affo:
            fields[1:1] = [
                _field("recurring_cost_ratio", "Recurring-cost adjustment", 0.0, 0.0, 0.30, 0.01),
                _field("forecast_years", "Forecast years", years, 2, 15, 1),
            ]
            fields.append(_field("terminal_growth", "Terminal growth", terminal, -0.02, 0.04, 0.0025))
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
    elif lane == "distribution_ddm":
        distribution = _number(assumptions.get("owner_distribution_per_share"), 0.0)
        defaults = {
            "owner_distribution_per_share": distribution,
            "dividend_growth": growth,
            "discount_rate": discount,
        }
        fields = [
            _field("dividend_growth", "Distribution growth", growth, -0.10, 0.10, 0.0025),
            _field("discount_rate", "Cost of equity", discount, 0.05, 0.25, 0.0025),
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


def calculator_view(
    artifact: Mapping[str, Any],
    *,
    recipe: Mapping[str, Any] | None = None,
    selected_scenario: str | None = None,
) -> dict[str, Any]:
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
            "scenario_presets": {},
            "selected_scenario": "base",
            "market_comparison": artifact.get("market_comparison"),
            "warnings": ["A calculator is unavailable because the official baseline is not available."],
        }
    selected = _scenario_name(selected_scenario)
    lane, defaults, fields = _defaults_and_fields(artifact)
    scenario_presets: dict[str, Any] = {}
    if recipe is not None:
        if recipe.get('ticker') != ticker or recipe.get('baseline_version') != baseline_version(artifact):
            raise ValueError('recipe does not match the current baseline')
        reproduced = evaluate_recipe(recipe)['range']
        if any(not isclose(reproduced[key], float(scenario[key]), rel_tol=1e-9, abs_tol=1e-7) for key in ('low', 'base', 'high')):
            raise ValueError('recipe does not reproduce the published scenarios')
        defaults = {}
        fields = []
        for key, rule in recipe.get('editable', {}).items():
            value = 1.0 if rule.get('operation') == 'multiply' else recipe['scenarios']['base']['inputs'][rule['field']]
            defaults[key] = value
            fields.append(_field(key, rule.get('label', key.replace('_', ' ').title()), value, rule['min'], rule['max'], rule.get('step', .005)))
        for preset in ("low", "base", "high"):
            source_name = _recipe_scenario_name(preset)
            preset_defaults = {}
            for key, rule in recipe.get('editable', {}).items():
                value = 1.0 if rule.get('operation') == 'multiply' else recipe['scenarios'][source_name]['inputs'][rule['field']]
                preset_defaults[key] = value
            scenario_presets[preset] = {
                **preset_defaults,
            }
        defaults = dict(scenario_presets[selected])
    else:
        # A legacy range does not supply independently verified case inputs.
        scenario_presets = {"base": dict(defaults)}
    warnings = [
        "Baseline-calibrated sensitivity: defaults reproduce FinSight's published value; locked source facts do not change."
    ]
    if recipe is not None:
        warnings = ['Each scenario is recalculated with the original model and locked filing inputs.']
    if lane == "enterprise_fcff":
        warnings.append("Cash conversion is a multiplier over the fixed source-derived base FCFF per share.")
    return {
        "ticker": ticker,
        "assigned_model": artifact.get("primary_valuation_method"),
        "model_family": lane,
        "model_version": artifact.get("public_assumptions", {}).get("forecast_policy_version", artifact.get("schema_version")),
        "availability_type": artifact.get("availability_type"),
        "can_calculate": True,
        "defaults": defaults,
        "editable_assumptions": fields,
        "scenario_presets": scenario_presets,
        "selected_scenario": selected,
        "locked_facts": ["issuer identity", "source filing", "share denominator", "historical periods"],
        "baseline_result": {key: float(scenario[key]) for key in ("low", "base", "high")},
        "market_comparison": artifact.get("market_comparison"),
        "warnings": warnings,
        "baseline_version": baseline_version(artifact),
        "recipe_version": recipe.get('recipe_version') if recipe else None,
        "recipe_hash": recipe_hash(recipe) if recipe else None,
        "calculation_mode": 'exact_recipe' if recipe else 'legacy_sensitivity',
    }


def _validate_overrides(view: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, float | int]:
    fields = {row["key"]: row for row in view["editable_assumptions"]}
    defaults = dict(view["defaults"])
    locked = set(defaults) - set(fields)
    unknown = sorted(set(overrides) - set(fields) - locked)
    if unknown:
        raise ValueError(f"unsupported calculator assumptions: {', '.join(unknown)}")
    for key in sorted(set(overrides) & locked):
        raw = overrides[key]
        if isinstance(raw, bool) or not isinstance(raw, Real) or not isfinite(float(raw)) or float(raw) != float(defaults[key]):
            raise ValueError(f"{key} is a locked source-derived input")
    values = defaults
    for key, raw in overrides.items():
        if key in locked:
            continue
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
    if view.get("model_family") == "residual_income":
        if float(discount) - float(terminal) < 0.03:
            raise ValueError("terminal_growth must remain at least 3% below cost of equity")
        if float(terminal) >= float(values["terminal_roe"]):
            raise ValueError("terminal_growth must remain below terminal ROE")
    if view.get("model_family") == "enterprise_fcff" and float(discount) - float(terminal) < 0.025:
        raise ValueError("terminal_growth must remain at least 2.5% below discount_rate")
    return values


def _factor(lane: str, values: Mapping[str, float | int]) -> float:
    if lane == "asset_runway":
        return float(values["runway_value_factor"])
    if lane == "equity_earnings":
        return float(values["normalized_earnings_factor"]) * float(values["earnings_multiple"])
    if lane == "residual_income":
        return float(residual_income_valuation(
            book_value_per_share=float(values["book_value_per_share"]),
            current_roe=float(values["sustainable_roe"]),
            cost_of_equity=float(values["discount_rate"]),
            current_payout_ratio=float(values["payout_ratio"]),
            terminal_roe=float(values["terminal_roe"]),
            terminal_growth=float(values["terminal_growth"]),
            years=int(values["forecast_years"]),
        )["intrinsic_value"])
    if lane == "enterprise_fcff":
        return (
            float(values["starting_cash_fcff_per_share"])
            * float(values["cash_conversion"])
            * _projection_factor(
                growth=float(values["initial_growth"]),
                discount=float(values["discount_rate"]),
                terminal=float(values["terminal_growth"]),
                years=int(values["forecast_years"]),
            )
            + float(values["bridge_adjustment_per_share"])
        )
    if lane == "utility_fcfe":
        cfo = float(values["operating_cash_flow_per_share"])
        capex = float(values["capital_expenditures_per_share"])
        income = float(values["model_income_before_parent_allocation_per_share"])
        parent = float(values["parent_cash_flow_share"])
        funding = float(values["debt_funding_share"])
        owner_cash = parent * (cfo - capex + funding * (capex + income - cfo))
        return owner_cash * _projection_factor(growth=float(values["initial_growth"]), discount=float(values["discount_rate"]), terminal=float(values["terminal_growth"]), years=int(values["forecast_years"]))
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
        return float(values["normalized_affo_per_share"]) * (1 - float(values["recurring_cost_ratio"])) * _projection_factor(
            growth=float(values["affo_growth"]),
            discount=float(values["discount_rate"]),
            terminal=float(values["terminal_growth"]),
            years=int(values["forecast_years"]),
        ) + float(values["nonrecurring_value_adjustment_per_share"])
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
    if lane == "distribution_ddm":
        growth = float(values["dividend_growth"])
        discount = float(values["discount_rate"])
        if discount <= growth:
            raise ValueError("cost of equity must exceed distribution growth")
        return float(values["owner_distribution_per_share"]) * (1 + growth) / (discount - growth)
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
        "price": manual_price,
        "gap_pct": gap,
        "label": label,
        "verdict": "undervalued" if gap > 0.05 else "overvalued" if gap < -0.05 else "fair_value",
        "denominator": "finsight_base_value",
    }


def calculate(
    artifact: Mapping[str, Any],
    *,
    overrides: Mapping[str, Any],
    manual_price: float | None,
    recipe: Mapping[str, Any] | None = None,
    selected_scenario: str | None = None,
) -> dict[str, Any]:
    selected = _scenario_name(selected_scenario)
    if recipe is None and selected != 'base':
        raise ValueError('An exact recipe is required to edit a non-base scenario')
    view = calculator_view(artifact, recipe=recipe, selected_scenario=selected)
    if not view["can_calculate"]:
        raise ValueError("calculator is unavailable for this valuation")
    values = {**view['defaults'], **overrides} if recipe is not None else _validate_overrides(view, overrides)
    baseline = view["baseline_result"]
    if recipe is not None:
        result = evaluate_recipe(recipe, overrides, anchor_scenario=selected_scenario)['range']
    else:
        default_factor = _factor(view["model_family"], view["defaults"])
        user_factor = _factor(view["model_family"], values)
        if default_factor <= 0 or user_factor <= 0 or not isfinite(user_factor):
            raise ValueError("calculator assumptions produce an unusable value")
        multiplier = user_factor / default_factor
        result = {key: baseline[key] * multiplier for key in ("low", "base", "high")}
    base_comparison = (
        _manual_comparison(result["base"], manual_price)
        if manual_price is not None
        else artifact.get("market_comparison")
    )
    scenario_comparisons = None
    if manual_price is not None:
        scenario_comparisons = public_scenario_market_comparison(scenario_range=result, manual_price=manual_price)
    elif isinstance(base_comparison, Mapping) and base_comparison.get('status') == 'available':
        # Recover the comparison basis privately from the official derived gap;
        # do not return or persist the implied vendor price.
        old_gap = base_comparison.get('gap_pct')
        if isinstance(old_gap, (int, float)) and not isinstance(old_gap, bool) and isfinite(old_gap):
            implied_price = baseline['base'] * (1 - old_gap)
            if implied_price > 0:
                scenario_comparisons = public_scenario_market_comparison(scenario_range=result, manual_price=implied_price)
                scenario_comparisons['price_date'] = base_comparison.get('price_date')
    comparison = base_comparison
    if isinstance(scenario_comparisons, Mapping):
        selected_row = scenario_comparisons.get(selected)
        if isinstance(selected_row, Mapping):
            comparison = {
                **selected_row,
                'price_date': scenario_comparisons.get('price_date'),
                'denominator': 'finsight_base_value' if selected == 'base' else 'finsight_scenario_value',
            }
            if manual_price is not None:
                comparison['source'] = 'manual'
                comparison['price'] = manual_price
    if isinstance(scenario_comparisons, Mapping):
        for key in ("low", "base", "high"):
            row = scenario_comparisons.get(key)
            if isinstance(row, dict) and row.get("status") == "available":
                gap = row.get("gap_pct")
                row["verdict"] = "undervalued" if isinstance(gap, (int, float)) and gap > 0.05 else "overvalued" if isinstance(gap, (int, float)) and gap < -0.05 else "fair_value"
            elif isinstance(row, dict):
                row["verdict"] = None
    if isinstance(comparison, dict) and "verdict" not in comparison:
        gap = comparison.get("gap_pct")
        comparison["verdict"] = "undervalued" if isinstance(gap, (int, float)) and gap > 0.05 else "overvalued" if isinstance(gap, (int, float)) and gap < -0.05 else "fair_value" if isinstance(gap, (int, float)) else None
    return {
        **view,
        "assumptions": values,
        "result": result,
        "baseline_change_pct": result["base"] / baseline["base"] - 1,
        "comparison": comparison,
        "comparison_source": "manual" if manual_price is not None else "automatic_eod",
        "manual_price": manual_price,
        "scenario_comparisons": scenario_comparisons,
        "selected_scenario": selected,
    }
