#!/usr/bin/env python3
"""Exercise the actual isolated UAT HTTP API; keep tokens out of evidence."""
import json
from math import isclose
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.refresh_job import atomic
from app.us_valuation.catalog import canonical_json_bytes


def main():
    base = 'http://127.0.0.1:4179/api'
    token = None
    def call(path, body=None):
        headers = {'Content-Type': 'application/json'}
        if token: headers['Authorization'] = 'Bearer ' + token
        req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with urlopen(req, timeout=30) as response:
            return json.load(response)
    auth = call('/auth/login', {'email': 'refresh-uat@example.com', 'password': 'Local-UAT-only-20260908!'})
    token = auth['access_token']
    listed = call('/us-valuations')
    assert listed['count'] == 440
    cases = []
    for ticker in ('AAPL', 'XOM', 'JPM', 'MRNA', 'PLTR', 'O', 'WDC', 'CHTR'):
        view = call(f'/us-valuations/{ticker}/calculator')
        assert view['calculation_mode'] == 'exact_recipe'
        body = {'overrides': {}, 'baseline_version': view['baseline_version'], 'recipe_version': view['recipe_version']}
        result = call(f'/us-valuations/{ticker}/calculator', body)
        assert all(isclose(result['result'][key], view['baseline_result'][key], rel_tol=1e-9, abs_tol=1e-7) for key in ('low','base','high'))
        history = call(f'/us-valuations/{ticker}/history')
        assert history['ticker'] == ticker
        cases.append({'ticker': ticker, 'defaults': result['result'], 'recipe_version': view['recipe_version'], 'history_count': len(history['items'])})
    charter_view = call('/us-valuations/CHTR/calculator')
    charter = call('/us-valuations/CHTR/calculator', {'overrides': {'discount_rate': .08},
                   'baseline_version': charter_view['baseline_version'], 'recipe_version': charter_view['recipe_version']})
    charter_recipe = json.loads((ROOT / 'output/us-refresh-runtime/recipes/CHTR.json').read_text())
    from app.us_valuation.batch_02_conditional_estimates import five_year_fcff_dcf
    charter_inputs = {**charter_recipe['scenarios']['base']['inputs'], 'wacc': .08}
    standalone = five_year_fcff_dcf(**charter_inputs)
    overlay = charter_recipe['scenarios']['base']['equity_overlay']
    charter_expected = (standalone['equity_value'] - overlay['cash_claim']) / (charter_inputs['shares'] + overlay['incremental_shares'])
    assert isclose(charter['result']['base'], charter_expected, rel_tol=1e-12)
    view = call('/us-valuations/AAPL/calculator')
    override = {'discount_rate': .10}
    result = call('/us-valuations/AAPL/calculator', {'overrides': override, 'manual_price': 90., 'save': True,
                   'baseline_version': view['baseline_version'], 'recipe_version': view['recipe_version']})
    recipe = json.loads((ROOT / 'output/us-refresh-runtime/recipes/AAPL.json').read_text())
    expected = evaluate_recipe(recipe, override)['range']
    assert all(isclose(result['result'][key], expected[key], rel_tol=1e-12) for key in expected)
    saved = call(f"/valuations/{result['saved_id']}")
    # Read the real persisted row, not a test double or POST response echo.
    if 'valuation' in saved: saved = saved['valuation']
    assert saved['result']['recipe_hash'] == result['recipe_hash']
    assert saved['result']['user_overrides'] == override
    assert saved['result']['base'] == result['result']['base']
    assert float(saved['user_price']) == 90.
    # Use the redesigned UI's exact flat-preset/request contract.
    for selected in ('low','base','high'):
        preset_result = call('/us-valuations/AAPL/calculator', {'scenario': selected, 'overrides': view['scenario_presets'][selected],
                             'baseline_version': view['baseline_version'], 'recipe_version': view['recipe_version']})
        assert preset_result['selected_scenario'] == selected
        assert all(isclose(preset_result['result'][key], view['baseline_result'][key], rel_tol=1e-12) for key in ('low','base','high'))
    assert next(field for field in view['editable_assumptions'] if field['key']=='discount_rate')['unit'] == 'percent'
    bear = call('/us-valuations/AAPL/calculator', {'scenario':'low','overrides':{'discount_rate':.12},'manual_price':90.,'save':True,
                'baseline_version':view['baseline_version'],'recipe_version':view['recipe_version']})
    inputs = recipe['scenarios']['bear']['inputs']
    independent_bear = (sum(cash/(1.12)**(index+1) for index,cash in enumerate(inputs['cash_flows']))
                        + inputs['terminal_cash_flow']/(.12-inputs['terminal_growth'])/(1.12)**len(inputs['cash_flows']) + inputs['net_bridge'])/inputs['shares']
    assert isclose(bear['result']['low'], independent_bear, rel_tol=1e-12)
    assert bear['result']['base'] == view['baseline_result']['base']
    assert bear['result']['high'] == view['baseline_result']['high']
    assert isclose(bear['comparison']['gap_pct'], 1-90./independent_bear, rel_tol=1e-12)
    bear_saved = call(f"/valuations/{bear['saved_id']}")
    if 'valuation' in bear_saved: bear_saved=bear_saved['valuation']
    assert bear_saved['result']['selected_scenario']=='low'
    assert bear_saved['result']['low']==bear['result']['low']
    try:
        call('/us-valuations/AAPL/calculator', {'overrides': {}, 'baseline_version': 'stale', 'recipe_version': view['recipe_version']})
        raise AssertionError('stale request accepted')
    except HTTPError as exc:
        assert exc.code == 409
    evidence = {'scope': 'isolated localhost UAT, no catalog activation', 'issuer_count': listed['count'], 'cases': cases,
                'edited_aapl': expected, 'saved_id': result['saved_id'], 'real_database_readback': 'passed', 'stale_version': 409,
                'charter_edited_base': charter_expected, 'charter_fixed_overlay': overlay,
                'redesigned_ui': {'case_presets':'passed','percent_unit':'passed','selected_bear':independent_bear,'other_cases_unchanged':True,'saved_bear_id':bear['saved_id'],'saved_case_readback':'passed'},
                'full_refresh_acceptance': 'not_verified'}
    atomic(ROOT / 'output/us-refresh-runtime/api-uat-evidence.json', canonical_json_bytes(evidence), immutable=False)
    print(json.dumps(evidence, sort_keys=True))


if __name__ == '__main__': main()
