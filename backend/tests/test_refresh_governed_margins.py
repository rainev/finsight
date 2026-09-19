from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.refresh_governed_margins import (
    governed_margin_policy,validate_governed_margin_policy,compile_governed_margin_policy,
    governed_source_validity,
)

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_wg24_governed_margins import proof
INDEX=ROOT/'output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json'

@pytest.fixture(scope='module')
def real_proof():
    return proof(ROOT/'output/us-refresh-runtime',INDEX)

def test_real_governed_margin_replay_does_not_rewrite_history_or_floor(real_proof):
    p=real_proof;n=p['normalization']
    assert n['governed_cash_conversion_margin']=={'low':.03,'base':.07,'high':.12}
    assert n['cash_conversion_margin']!=n['governed_cash_conversion_margin']
    assert n['reported']['revenue']==57_032_000_000
    assert n['reported']['interest_expense']==1_150_000_000
    assert n['ttm_cash_fcff']==3_739_500_000
    assert n['tax_rate']==.21 and 'fallback_not_reported' in n['tax_selection']
    assert [r['cash_fcff']<0 for r in n['annual']]==[False,True,True,True,True]
    assert [r['interest_expense']['concept'] for r in n['annual']]==['InterestExpense',*(['InterestExpenseNonoperating']*4)]
    assert all(r['income_tax'] is not None and r['pretax_income'] is not None for r in n['annual'])
    assert p['reconstructed_starting_cash']=={'bear':1_710_960_000.,'base':3_992_240_000.0000005,'bull':6_843_840_000.}
    assert p['previous_range']==p['narrow_replayed_range']=={'low':0.,'base':3.001327108470505,'high':16.50488639459598}
    assert not p['numeric_successor_issued']

def test_real_financing_capex_is_review_not_implicitly_zero_or_deducted(real_proof):
    v=real_proof['normalization']['governed_validity']
    assert v['current_ytd_financing_capital_payments']==1_423_000_000
    assert v['reported_current_cash_after_investing_capex']==2_831_000_000
    assert not v['passed'] and not v['total_reinvestment_scope_complete']
    assert 'financing_capital_payment_cash_and_debt_overlap_requires_reconciliation' in v['review_reasons']

@pytest.mark.parametrize('field,value',[('scenario_margins',(.03,.08,.12)),('version','unknown'),('cik','0000000001'),('economic_review_required',False)])
def test_unapproved_governed_changes_fail_closed(field,value):
    p=governed_margin_policy('INTC');p[field]=value
    with pytest.raises(ValueError,match='identity/version'):
        validate_governed_margin_policy(p,cik='0000050863')

def structural():
    return json.loads((ROOT/'output/batch-26-structural-sources-20260831/INTC/structural-filing.json').read_bytes())

def validity(real_proof,st,reported=None):
    n=real_proof['normalization']
    return governed_source_validity(governed_margin_policy('INTC'),reported or n['reported'],n['annual'],st,period=st['report_date'])

def test_missing_financing_capital_payment_is_not_zero(real_proof):
    st=structural();st['facts']=[r for r in st['facts'] if r['local_name']!='PaymentsToAcquirePropertyPlantAndEquipmentFinancingActivities']
    v=validity(real_proof,st)
    assert v['current_ytd_financing_capital_payments'] is None and not v['passed']

def test_reported_zero_financing_line_does_not_certify_total_reinvestment(real_proof):
    st=structural()
    for r in st['facts']:
        if r['local_name']=='PaymentsToAcquirePropertyPlantAndEquipmentFinancingActivities':r['value']=0.
    v=validity(real_proof,st)
    assert v['financing_capital_payment_line_zero']
    assert not v['total_reinvestment_scope_complete'] and not v['passed']

def test_financing_payment_window_must_match_current_source_flow(real_proof):
    n=real_proof['normalization'];st=structural()
    with pytest.raises(ValueError,match='interval does not align'):
        governed_source_validity(governed_margin_policy('INTC'),n['reported'],n['annual'],st,
            period=st['report_date'],current_flow_start='2026-01-01')

@pytest.mark.parametrize('field,value',[('namespace','http://other.com/20260627'),('unit','shares'),('value',float('nan'))])
def test_financing_capital_payment_identity_unit_and_finiteness(real_proof,field,value):
    st=structural()
    for r in st['facts']:
        if r['local_name']=='PaymentsToAcquirePropertyPlantAndEquipmentFinancingActivities' and r['period_end']==st['report_date']:r[field]=value
    with pytest.raises(ValueError,match='scope invalid'):
        validity(real_proof,st)

def test_difficult_real_loss_year_cannot_qualify_using_interest_addback(real_proof):
    n=real_proof['normalization'];loss=n['annual'][3]
    reported={field:loss[field]['value'] for field in ('revenue','operating_cash_flow','capital_expenditures')}
    v=validity(real_proof,structural(),reported)
    assert v['reported_current_cash_after_investing_capex']<0
    assert 'current_reported_cash_after_investing_capex_is_not_positive' in v['review_reasons']

def test_retained_recipe_must_reconcile_to_approved_rule():
    root=ROOT/'output/us-refresh-runtime'
    e=next(r for r in json.loads((root/'registry.json').read_bytes())['entries'] if r['ticker']=='INTC')
    recipe=json.loads((root/'recipes/INTC.json').read_bytes())
    assert compile_governed_margin_policy(e,recipe)['scenario_margins']==(.03,.07,.12)
    recipe['scenarios']['base']['inputs']['cash_fcff']+=1
    with pytest.raises(ValueError,match='does not execute'):
        compile_governed_margin_policy(e,recipe)
