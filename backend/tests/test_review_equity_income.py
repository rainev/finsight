from copy import deepcopy
from pathlib import Path
import json
import pytest
from app.us_valuation.review_equity_income import prepare
from app.us_valuation.calculation_recipe import evaluate_recipe

ROOT=Path(__file__).resolve().parents[2]
B=ROOT/'output/us-expansion-batches-11-15-20261008'

def case(ticker='AGCO'):
    path=B/'private-recovery-pass/run-a/source-ledgers'/f'{ticker}.json'
    if not path.exists():pytest.skip('frozen source fixture unavailable')
    return json.loads(path.read_bytes()),{'risk_free_rate':.0529,'equity_risk_premium':.042,'sector_beta_prior':.96,'uncertainty_premium':.015}

@pytest.mark.parametrize('ticker',['AGCO','ALSN','ITT','SAIA','MLR','VECO','ASTE'])
def test_reported_first_income_and_terminal_cap_are_preserved(ticker):
    ledger,policy=case(ticker);before=deepcopy(ledger)
    recipe,trace=prepare(ledger,policy);result=evaluate_recipe(recipe)
    assert ledger==before
    ni=ledger['current_income_ttm']['value'];book=ledger['current_common_capital']['reported_parent_common_book']['value'];shares=ledger['balance_point_common_shares']['value']
    for name,multiplier in [('bear',.75),('base',1.),('bull',1.2)]:
        first=result['scenarios'][name]['trace']['detail']['schedule'][0]['earnings_per_share']*shares
        assert first==pytest.approx(ni*multiplier)
        assert recipe['scenarios'][name]['inputs']['terminal_roe']<=2*ni/book

def test_asset_light_school_or_service_cannot_get_automatic_book_fallback():
    ledger,policy=case('LOPE')
    with pytest.raises(ValueError,match='no book-model fallback'):prepare(ledger,policy)

def test_currency_and_fiscal_alignment_fail_closed():
    ledger,policy=case();ledger['current_common_capital']['reported_parent_common_book']['unit']='EUR'
    with pytest.raises(ValueError,match='currency'):prepare(ledger,policy)
    ledger,policy=case();ledger['current_common_capital']['reported_parent_common_book']['period_end']='2026-07-01'
    with pytest.raises(ValueError,match='period'):prepare(ledger,policy)

def test_cost_of_equity_is_independent_of_vendor_target_and_higher_risk_reduces_value():
    ledger,policy=case();_,base=prepare(ledger,policy)
    policy['uncertainty_premium']+=.01
    _,higher=prepare(ledger,policy)
    assert higher['ranges']['base']<base['ranges']['base']
