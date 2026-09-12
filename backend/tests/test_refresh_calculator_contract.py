from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from app.us_valuation.calculator import calculate, calculator_view, baseline_version
from app.us_valuation.artifacts import sanitize_public_artifact


def public():
    root = Path('output/batch-44-recovery-api-runtime-final-b/catalogs/US-RESET-2026-08-14-B01-B44-RECOVERY-1.0/artifacts')
    return sanitize_public_artifact(json.loads((root / 'XOM.json').read_text()))


def exact_recipe(artifact):
    path = Path('output/batch-44-recovery-run-d-20260907/generated/XOM/valuation-private.json')
    private = json.loads(path.read_text())['recovery']
    scenarios = {}
    for row in private['scenario_rows']:
        scenarios[row['name']] = {'engine': 'enterprise_cash_fcff', 'inputs': {
            'cash_fcff': row['starting_cash_fcff'], 'initial_growth': row['growth'], 'terminal_growth': row['terminal_growth'],
            'wacc': row['wacc'], 'cash_and_investments': row['cash_and_investments'],
            'interest_bearing_debt': row['debt_and_finance_leases'], 'preferred_equity': 0.,
            'noncontrolling_interests': row['other_equity_claims'], 'diluted_shares': row['shares'], 'forecast_years': 8}}
    return {'schema_version': 'FINSIGHT-CALCULATION-RECIPE-1', 'ticker': 'XOM', 'baseline_version': baseline_version(artifact),
            'recipe_version': 'XOM-migration1', 'scenarios': scenarios,
            'editable': {'cash_conversion': {'field': 'cash_fcff', 'operation': 'multiply', 'min': .25, 'max': 2., 'step': .025}}}


def test_exact_real_recipe_recomputes_each_scenario():
    artifact = public()
    recipe = exact_recipe(artifact)
    view = calculator_view(artifact, recipe=recipe)
    assert view['calculation_mode'] == 'exact_recipe'
    assert all(field['unit'] in {'percent','number','multiple','years'} for field in view['editable_assumptions'])
    default = calculate(artifact, recipe=recipe, overrides={}, manual_price=None)
    for key in ('low', 'base', 'high'):
        assert default['result'][key] == pytest.approx(artifact['scenario_range'][key])
    edited = calculate(artifact, recipe=recipe, overrides={'cash_conversion': 1.2}, manual_price=None)
    assert edited['result']['low'] / default['result']['low'] != pytest.approx(edited['result']['base'] / default['result']['base'])


def test_exact_recipe_presets_expose_recorded_case_inputs_and_units():
    artifact = public()
    recipe = exact_recipe(artifact)
    view = calculator_view(artifact, recipe=recipe, selected_scenario='low')
    assert view['selected_scenario'] == 'low'
    assert view['scenario_presets']['low']['cash_conversion'] == pytest.approx(1.0)
    assert view['scenario_presets']['base']['cash_conversion'] == pytest.approx(1.0)
    assert all('unit' in field for field in view['editable_assumptions'])
    assert view['defaults']['cash_conversion'] == pytest.approx(1.0)


def test_selected_recipe_anchor_is_not_blindly_base_anchored():
    artifact = public()
    recipe = exact_recipe(artifact)
    selected = calculate(
        artifact,
        recipe=recipe,
        selected_scenario='low',
        overrides={'cash_conversion': 1.2},
        manual_price=None,
    )
    from app.us_valuation.calculation_recipe import evaluate_recipe
    expected = evaluate_recipe(recipe, {'cash_conversion': 1.2}, anchor_scenario='low')['range']
    assert selected['selected_scenario'] == 'low'
    assert selected['result'] == pytest.approx(expected)


def test_automatic_gap_follows_edited_value_and_zero_bear_is_unavailable():
    artifact = public()
    artifact['market_comparison'] = {'status': 'available', 'gap_pct': .2, 'price_date': '2026-09-04', 'denominator': 'finsight_base_value'}
    result = calculate(artifact, overrides={'cash_conversion': 1.2}, manual_price=None)
    implied_price = artifact['scenario_range']['base'] * .8
    assert result['comparison']['gap_pct'] == pytest.approx(1 - implied_price / result['result']['base'])
    assert result['scenario_comparisons']['high']['gap_pct'] == pytest.approx(1 - implied_price / result['result']['high'])
    assert 'split_adjusted_close' not in json.dumps(result)


def test_stale_recipe_is_rejected_before_evaluation():
    artifact = public()
    recipe = exact_recipe(artifact)
    artifact['scenario_range']['base'] += 1
    with pytest.raises(ValueError, match='current baseline'):
        calculator_view(artifact, recipe=recipe)


def test_real_wdc_cycle_recipe_replays_zero_claims_without_scaling():
    from app.us_valuation.recipe_migration import compile_private_recipe
    from app.us_valuation.calculation_recipe import evaluate_recipe
    source = Path('output/batch-01-recovery/final-confirmation-a/generated/WDC/valuation-private.json')
    artifact = json.loads(Path('output/us-refresh-runtime/baseline/artifacts/WDC.json').read_text())
    compiled = compile_private_recipe(json.loads(source.read_text()), artifact, source_path=source)
    assert compiled['status'] == 'migrated'
    recipe = compiled['recipe']
    assert evaluate_recipe(recipe)['range'] == pytest.approx({key: artifact['scenario_range'][key] for key in ('low','base','high')})
    recipe['editable']['discount_rate'] = {'field': 'wacc', 'min': .04, 'max': .30}
    edited = evaluate_recipe(recipe, {'discount_rate': .11})
    for scenario in ('bear','base','bull'):
        assert edited['scenarios'][scenario]['trace']['other_claims'] == {'low': 0., 'base': 0., 'high': 0.}
    assert edited['range']['base'] < artifact['scenario_range']['base']


def test_http_rejects_stale_recipe_request(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app import deps
    import app.routers.us_valuations as router
    artifact = public()
    recipe = exact_recipe(artifact)
    monkeypatch.setattr(router, 'DATA_ROOT', tmp_path / 'artifacts')
    monkeypatch.setattr(router, 'RECIPE_ROOT', tmp_path / 'recipes')
    monkeypatch.setattr(router, 'EOD_DATA_ROOT', None)
    for directory, value in [('artifacts', artifact), ('recipes', recipe)]:
        (tmp_path / directory).mkdir()
        (tmp_path / directory / 'XOM.json').write_text(json.dumps(value))
    prior = app.dependency_overrides.copy()
    app.dependency_overrides[deps.current_user] = lambda: {'sub': 7, 'role': 'user'}
    try:
        client = TestClient(app)
        response = client.post('/api/us-valuations/XOM/calculator', json={'overrides': {}, 'baseline_version': 'stale'})
        assert response.status_code == 409
        response = client.post('/api/us-valuations/XOM/calculator', json={'scenario': 'low', 'overrides': {}, 'manual_price': 10, 'baseline_version': recipe['baseline_version'], 'recipe_version': recipe['recipe_version']})
        assert response.status_code == 200
        assert response.json()['result']['base'] == pytest.approx(artifact['scenario_range']['base'])
        body = response.json()
        assert body['selected_scenario'] == 'low'
        assert body['comparison']['gap_pct'] == pytest.approx((body['result']['low'] - 10) / body['result']['low'])
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prior)
