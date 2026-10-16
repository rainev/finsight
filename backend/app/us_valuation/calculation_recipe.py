"""Private, data-only recipes evaluated by the same engines for batch and UI use."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from math import isfinite
from typing import Any, Mapping

from app.valuation.bank import residual_income_valuation
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf, CyclicalOperatingState, practical_cyclical_fcff_range
from .practical_policy import InputRange
from .batch_02_conditional_estimates import five_year_fcff_dcf

SCHEMA = 'FINSIGHT-CALCULATION-RECIPE-1'
SCENARIOS = ('bear', 'base', 'bull')


def _recipe_name(scenario: str) -> str:
    return {"low": "bear", "base": "base", "high": "bull"}[scenario]
# Even a malformed private policy cannot unlock reported balances or ownership.
EDITABLE_FIELDS = {
    'enterprise_cash_fcff': {'cash_fcff', 'initial_growth', 'terminal_growth', 'wacc', 'forecast_years'},
    'constant_growth_fcff': {'fcff_margin', 'growth', 'wacc', 'terminal_growth'},
    'residual_income': {'current_roe', 'cost_of_equity', 'current_payout_ratio', 'terminal_roe', 'terminal_growth', 'years'},
    # The stored terminal cash numerator may include reinvestment calculations;
    # changing its growth without those inputs is not a supported edit.
    'cash_schedule': {'discount_rate'},
    'earnings_multiple': {'multiple'},
    'cyclical_fcff_quantile': {'wacc', 'normalized_tax_rate'},
    'asset_runway': set(),
}


def recipe_hash(recipe: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(recipe, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value):
        raise ValueError(f'{name} must be finite')
    return float(value)


def evaluate_scenario(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate recorded economic inputs; never infer inputs from a target value."""
    engine = spec['engine']
    inputs = deepcopy(spec['inputs'])
    if engine == 'enterprise_cash_fcff':
        years = inputs.pop('forecast_years', 8)
        result = enterprise_cash_flow_dcf(EnterpriseCashFlowState(**inputs), forecast_years=years, allow_nonpositive_equity_trace=True)
        raw = result['intrinsic_value_per_share']
    elif engine == 'constant_growth_fcff':
        result = five_year_fcff_dcf(**inputs)
        raw = result['value_per_share']
    elif engine == 'residual_income':
        result = residual_income_valuation(**inputs)
        raw = result['intrinsic_value']
    elif engine == 'cash_schedule':
        rate = number(inputs['discount_rate'], 'discount_rate')
        terminal_growth = number(inputs['terminal_growth'], 'terminal_growth')
        if rate <= terminal_growth or rate <= 0:
            raise ValueError('discount rate must exceed terminal growth')
        cash = [number(x, 'cash_flow') for x in inputs['cash_flows']]
        if not cash:
            raise ValueError('empty cash schedule')
        explicit = sum(x / (1 + rate) ** (i + 1) for i, x in enumerate(cash))
        terminal = number(inputs['terminal_cash_flow'], 'terminal_cash_flow') / (rate - terminal_growth) / (1 + rate) ** len(cash)
        shares = number(inputs['shares'], 'shares')
        if shares <= 0:
            raise ValueError('shares must be positive')
        raw = (explicit + terminal + number(inputs['net_bridge'], 'net_bridge')) / shares
        result = {'explicit_pv': explicit, 'terminal_pv': terminal}
    elif engine == 'earnings_multiple':
        shares = number(inputs['shares'], 'shares')
        if shares <= 0:
            raise ValueError('shares must be positive')
        raw = (number(inputs['earnings'], 'earnings') * number(inputs['multiple'], 'multiple') + number(inputs['net_bridge'], 'net_bridge')) / shares
        result = {}
    elif engine == 'asset_runway':
        shares = number(inputs['shares'], 'shares')
        if shares <= 0: raise ValueError('shares must be positive')
        equity = (number(inputs['liquid_assets'], 'liquid_assets')
                  - number(inputs['cash_burn_reserve'], 'cash_burn_reserve')
                  - number(inputs['debt_and_finance_leases'], 'debt_and_finance_leases')
                  + number(inputs['pipeline_terminal_value'], 'pipeline_terminal_value'))
        raw = equity / shares
        result = {'equity_after_reserves': equity, 'method': 'liquid_assets_less_burn_and_debt_plus_pipeline'}
    elif engine == 'cyclical_fcff_quantile':
        quantile = inputs.pop('quantile')
        if quantile not in {.25, .5, .75}:
            raise ValueError('unsupported cyclical quantile')
        inputs['current_state'] = CyclicalOperatingState(**inputs['current_state'])
        inputs['observed_states'] = [CyclicalOperatingState(**row) for row in inputs['observed_states']]
        inputs['other_claims'] = InputRange(**inputs['other_claims'])
        result_range, result = practical_cyclical_fcff_range(**inputs)
        raw = getattr(result_range, {.25: 'low', .5: 'base', .75: 'high'}[quantile])
    else:
        raise ValueError(f'unsupported recipe engine: {engine}')
    raw = number(raw, 'result')
    overlay = spec.get('equity_overlay')
    if overlay is not None:
        if engine != 'constant_growth_fcff' or not isinstance(overlay, Mapping) or set(overlay) != {'cash_claim', 'incremental_shares'}:
            raise ValueError('unsupported equity overlay')
        claim = number(overlay['cash_claim'], 'event cash claim')
        additional_shares = number(overlay['incremental_shares'], 'event incremental shares')
        shares = number(inputs['shares'], 'source shares')
        if claim < 0 or additional_shares < 0 or shares <= 0:
            raise ValueError('invalid event claim or share overlay')
        standalone = raw
        raw = number((raw * shares - claim) / (shares + additional_shares), 'event-adjusted result')
        result = {**result, 'event_overlay': {'standalone_value_per_share': standalone,
                  'cash_claim': claim, 'incremental_shares': additional_shares,
                  'source_shares': shares, 'combined_shares': shares + additional_shares}}
    # The floor is part of an approved scenario recipe, never inferred to fit a target.
    value = max(0., raw) if spec.get('equity_floor') == 'limited_liability' else raw
    return {'raw_value': raw, 'value': value, 'trace': result}


def evaluate_recipe(
    recipe: Mapping[str, Any],
    overrides: Mapping[str, Any] | None = None,
    *,
    anchor_scenario: str | None = None,
) -> dict[str, Any]:
    if recipe.get('schema_version') != SCHEMA or set(recipe.get('scenarios', {})) != set(SCENARIOS):
        raise ValueError('invalid calculation recipe contract')
    if anchor_scenario is not None and anchor_scenario not in {"low", "base", "high"}:
        raise ValueError('selected scenario must be low, base, or high')
    editable = recipe.get('editable', {})
    overrides = overrides or {}
    if set(overrides) - set(editable):
        raise ValueError('unsupported or locked assumption')
    specs = deepcopy(recipe['scenarios'])
    for name, spec in specs.items():
        if spec.get('engine') not in EDITABLE_FIELDS or not isinstance(spec.get('inputs'), Mapping):
            raise ValueError('invalid scenario engine or inputs')
        if spec.get('equity_floor') not in {None, 'limited_liability'}:
            raise ValueError('unknown equity-floor policy')
        for key, value in spec['inputs'].items():
            if spec['engine'] == 'cyclical_fcff_quantile' and key in {'current_state', 'observed_states', 'other_claims'}:
                rows = value if isinstance(value, list) else [value]
                for row in rows:
                    if not isinstance(row, Mapping): raise ValueError('invalid cyclical state')
                    for field, scalar in row.items():
                        if field in {'issuer', 'period_end'}:
                            if not isinstance(scalar, str) or not scalar: raise ValueError('invalid cyclical identity or period')
                        else:
                            number(scalar, field)
                continue
            for item in (value if isinstance(value, list) else [value]):
                number(item, key)
        if name != 'bear' and spec.get('equity_floor') == 'limited_liability':
            raise ValueError('limited-liability floor is permitted only in the bear scenario')
    for key, rule in editable.items():
        if not isinstance(rule, Mapping) or rule.get('operation', 'delta') not in {'multiply', 'delta', 'replace'}:
            raise ValueError('invalid recipe edit rule')
        if number(rule.get('min'), key) > number(rule.get('max'), key):
            raise ValueError('invalid recipe edit bounds')
        for spec in specs.values():
            if rule.get('field') not in EDITABLE_FIELDS[spec['engine']] or rule['field'] not in spec['inputs']:
                raise ValueError('recipe edit targets a locked source fact or unsupported assumption')
    for key, raw in overrides.items():
        rule = editable[key]
        value = number(raw, key)
        if not rule['min'] <= value <= rule['max']:
            raise ValueError(f'{key} is outside approved limits')
        if rule.get('integer') and value != int(value):
            raise ValueError(f'{key} must be an integer')
        selected_targets = (
            (_recipe_name(anchor_scenario),) if anchor_scenario is not None else SCENARIOS
        )
        anchor_name = _recipe_name(anchor_scenario or 'base')
        baseline = recipe['scenarios'][anchor_name]['inputs'][rule['field']]
        for scenario in selected_targets:
            target = specs[scenario]['inputs']
            field = rule['field']
            operation = rule.get('operation', 'delta')
            if operation == 'multiply':
                target[field] *= value
            elif operation == 'delta':
                target[field] += value - baseline
            elif operation == 'replace':
                target[field] = int(value) if rule.get('integer') else value
            else:
                raise ValueError('invalid recipe edit operation')
    rows = {name: evaluate_scenario(specs[name]) for name in SCENARIOS}
    low, base, high = (rows[name]['value'] for name in SCENARIOS)
    if not 0 <= low <= base <= high or base <= 0:
        raise ValueError('edited recipe does not produce a positive, ordered equity range')
    return {'range': {'low': low, 'base': base, 'high': high}, 'scenarios': rows,
            'recipe_version': recipe['recipe_version'], 'recipe_hash': recipe_hash(recipe),
            'effective_recipe_hash': recipe_hash({**recipe, 'scenarios': specs}),
            'overrides': dict(overrides)}
