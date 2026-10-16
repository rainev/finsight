from copy import deepcopy
import pytest
from app.us_valuation.review_cash_dcf import prepare,CashReviewGap
from app.us_valuation.calculation_recipe import evaluate_recipe

def inputs():
    facts={'ticker':'TEST','cutoff':'2026-10-08','source_verified':True,'common_owner_accounting_bound_verified':True,
        'existing_hold':None,'common_shares':10.,'common_income_ttm':30.,'revenue_ttm':200.,
        'cfo_ttm':50.,'capex_ttm':10.,'sbc_ttm':5.,'annual_finance_lease_principal_budget':1.,'finance_lease_budget_reviewed':True,
        'history':[{'common_income':25.,'cfo':45.,'capex':10.,'sbc':5.,'revenue':150.,'role_verified':True,'period_aligned':True},
            {'common_income':28.,'cfo':48.,'capex':10.,'sbc':5.,'revenue':175.,'role_verified':True,'period_aligned':True},
            {'common_income':30.,'cfo':50.,'capex':10.,'sbc':5.,'revenue':200.,'role_verified':True,'period_aligned':True}]}
    policy={'risk_free_rate':.0529,'equity_risk_premium':.042,'sector_beta_prior':.91,'uncertainty_premium':.015,
        'rate_kind':'cost_of_equity','debt_net_borrowing_assumption':0,'cash_debt_bridge':0,
        'forecast_years':10,'future_acquisition_cash_budget_fraction':.05,'initial_growth_cap':.08,
        'incremental_growth_cash_intensity':.2}
    return facts,policy

def test_cash_budget_includes_productive_compensation_claim_and_lease_cost_once():
    facts,policy=inputs();before=deepcopy((facts,policy));recipe,trace=prepare(facts,policy)
    assert (facts,policy)==before
    assert trace['reported_core_cash']==35.
    for case in trace['forecast_budgets'].values():
        for row in case:
            assert row['common_cash']==pytest.approx(row['operating_cash']-row['productive_asset_cash']-row['SBC_economic_cost']
                -row['future_acquisition_cash_budget']-row['finance_lease_principal']-row['additional_growth_funding'])
    assert evaluate_recipe(recipe)['range']==trace['ranges']
    assert 0<trace['ranges']['low']<trace['ranges']['base']<trace['ranges']['high']

@pytest.mark.parametrize('field,value,message',[
    ('source_verified',False,'source rows'),('common_owner_accounting_bound_verified',False,'ownership'),
    ('finance_lease_budget_reviewed',False,'lease'),('existing_hold','unresolved acquisition','existing'),
    ('common_shares',0,'positive'),('cfo_ttm',float('nan'),'finite')])
def test_invalid_sources_and_claims_fail_closed(field,value,message):
    facts,policy=inputs();facts[field]=value
    with pytest.raises(CashReviewGap,match=message):prepare(facts,policy)

@pytest.mark.parametrize('field,value', [('cash_debt_bridge',100),('debt_net_borrowing_assumption',100),('rate_kind','WACC')])
def test_equity_cash_cannot_receive_enterprise_bridge_or_unsourced_borrowing(field,value):
    facts,policy=inputs();policy[field]=value
    with pytest.raises(CashReviewGap):prepare(facts,policy)

def test_higher_economic_costs_and_rates_lower_base_value():
    facts,policy=inputs();_,original=prepare(facts,policy)
    for field in ['capex_ttm','sbc_ttm','annual_finance_lease_principal_budget']:
        altered=deepcopy(facts);altered[field]+=1
        assert prepare(altered,policy)[1]['ranges']['base']<original['ranges']['base']
    changed=deepcopy(policy);changed['uncertainty_premium']+=.01
    assert prepare(facts,changed)[1]['ranges']['base']<original['ranges']['base']

def test_vendor_target_and_share_override_are_rejected():
    facts,policy=inputs();facts['competitor_value']=999.
    with pytest.raises(CashReviewGap,match='target'):prepare(facts,policy)
    del facts['competitor_value'];recipe,_=prepare(facts,policy)
    with pytest.raises(ValueError,match='locked'):evaluate_recipe(recipe,{'shares':1})

def test_negative_historical_cash_is_retained_not_cherry_picked():
    facts,policy=inputs();facts['history'][0]['cfo']=10.
    _,trace=prepare(facts,policy)
    assert trace['historical_cash_to_common_income_ratios'][0]<0
    facts['history'][1]['cfo']=10.
    with pytest.raises(CashReviewGap,match='median'):prepare(facts,policy)

def test_zero_growth_cash_has_no_hidden_book_ROE_or_future_buyback_credit():
    facts,policy=inputs()
    for row in facts['history']:row['revenue']=facts['revenue_ttm']
    recipe,trace=prepare(facts,policy)
    assert trace['base_initial_growth_assumption']==0
    assert all(case['inputs']['net_bridge']==0 and case['inputs']['shares']==facts['common_shares'] for case in recipe['scenarios'].values())
    assert all(case['engine']=='cash_schedule' for case in recipe['scenarios'].values())

def test_reported_cash_lane_does_not_recouple_cash_to_depressed_gaap_income():
    facts,policy=inputs();facts['common_income_ttm']=5.
    policy['cash_anchor_mode']='reported_TTM_cash'
    _,trace=prepare(facts,policy)
    assert trace['reported_core_cash']==trace['normalized_common_cash_before_future_budgets']==35.
    assert trace['median_conversion'] is None
