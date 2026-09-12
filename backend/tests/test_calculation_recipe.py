from copy import deepcopy
import pytest
from app.us_valuation.calculation_recipe import SCHEMA, evaluate_recipe


def recipe():
    scenarios = {}
    for name, cash, debt in [('bear', 8., 40.), ('base', 10., 30.), ('bull', 12., 20.)]:
        scenarios[name] = {'engine': 'enterprise_cash_fcff', 'inputs': {
            'cash_fcff': cash, 'initial_growth': .02, 'terminal_growth': .01, 'wacc': .1,
            'cash_and_investments': 5., 'interest_bearing_debt': debt, 'preferred_equity': 0.,
            'noncontrolling_interests': 0., 'diluted_shares': 10., 'forecast_years': 8}}
    return {'schema_version': SCHEMA, 'recipe_version': 'test1', 'scenarios': scenarios,
            'editable': {'cash_conversion': {'field': 'cash_fcff', 'operation': 'multiply', 'min': .5, 'max': 2.}}}


def test_scenarios_are_recalculated_and_debt_is_not_scaled():
    source = recipe()
    before = deepcopy(source)
    base = evaluate_recipe(source)
    edited = evaluate_recipe(source, {'cash_conversion': 1.2})
    for key, name in [('low', 'bear'), ('base', 'base'), ('high', 'bull')]:
        assert edited['range'][key] > base['range'][key]
        assert edited['range'][key] != pytest.approx(base['range'][key] * 1.2)
        assert edited['scenarios'][name]['trace']['detail']['interest_bearing_debt'] == source['scenarios'][name]['inputs']['interest_bearing_debt']
    assert source == before


def test_source_facts_cannot_be_overridden():
    with pytest.raises(ValueError, match='locked'):
        evaluate_recipe(recipe(), {'diluted_shares': 1})


def test_private_policy_cannot_unlock_reported_share_count():
    source = recipe()
    source['editable']['shares'] = {'field': 'diluted_shares', 'min': 1, 'max': 100}
    with pytest.raises(ValueError, match='locked source fact'):
        evaluate_recipe(source, {'shares': 2})


def test_unrecognized_or_base_floor_is_not_accepted():
    source = recipe()
    source['scenarios']['bear']['equity_floor'] = 'auto'
    with pytest.raises(ValueError, match='unknown equity'):
        evaluate_recipe(source)
    source['scenarios']['bear']['equity_floor'] = 'limited_liability'
    source['scenarios']['base']['equity_floor'] = 'limited_liability'
    with pytest.raises(ValueError, match='only in the bear'):
        evaluate_recipe(source)


def test_recipe_disallows_nonfinite_and_unordered_results():
    with pytest.raises(ValueError, match='finite'):
        evaluate_recipe(recipe(), {'cash_conversion': float('nan')})
    source = recipe()
    source['scenarios']['bear']['inputs']['cash_fcff'] = 100
    with pytest.raises(ValueError, match='ordered'):
        evaluate_recipe(source)
