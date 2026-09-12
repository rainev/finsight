import json
from pathlib import Path
from copy import deepcopy

import pytest

from app.us_valuation.refresh_financials import cash_history, POLICY_VERSION, CMG_OWNER_CASH_POLICY
from app.us_valuation.xbrl import CompanyFactsNormalizer

ROOT = Path(__file__).resolve().parents[2]


def source():
    root=ROOT/'output/batch-06-sec-source-packets-20260826/CMG'
    return {name:json.loads((root/f'{name}.json').read_text()) for name in ('submissions','companyfacts')}


def run(packet):
    recent=packet['submissions']['filings']['recent']
    records=[{key:values[i] for key,values in recent.items() if isinstance(values,list) and i<len(values)} for i in range(len(recent['accessionNumber']))]
    normalizer=CompanyFactsNormalizer(packet['companyfacts'],fiscal_year_end=packet['submissions']['fiscalYearEnd'],
        as_of_date='2026-08-14',filing_records=records)
    return cash_history(normalizer,period='2026-06-30',cutoff='2026-08-14',
        rule={'normalization_version':POLICY_VERSION,'cash_policy':CMG_OWNER_CASH_POLICY})


def test_real_cmg_owner_cash_reproduces_without_interest_or_tax_adjustments():
    packet=source(); before=deepcopy(packet)
    result=run(packet)
    assert result['reported']['operating_cash_flow']==2327527000
    assert result['reported']['capital_expenditures']==758542000
    assert result['ttm_cash_fcff']==1568985000
    assert result['tax_rate'] is None
    assert result['financing_adjustment_basis']=='owner_cash_no_financing_adjustment'
    assert 'interest_expense' not in result['reported']
    assert all(row['interest_expense'] is None and row['tax_rate'] is None for row in result['annual'])
    assert len(result['annual'])==5
    for row in result['annual']:
        assert row['cash_fcff']==row['operating_cash_flow']['value']-row['capital_expenditures']['value']
    recipe=json.loads((ROOT/'output/us-refresh-runtime/recipes/CMG.json').read_text())
    for case,stat in [('bear','low'),('base','base'),('bull','high')]:
        assert result['cash_conversion_margin'][stat]==pytest.approx(recipe['scenarios'][case]['inputs']['fcff_margin'])
    assert packet==before


def test_owner_cash_is_not_sensitive_to_unconsumed_tax_or_interest_fields():
    packet=source(); expected=run(packet)
    gaap=packet['companyfacts']['facts']['us-gaap']
    for name in list(gaap):
        if 'Interest' in name or 'IncomeTax' in name or 'IncomeLossFromContinuingOperationsBeforeIncomeTaxes' in name:
            del gaap[name]
    result=run(packet)
    assert result['ttm_cash_fcff']==expected['ttm_cash_fcff']
    assert result['cash_conversion_margin']==expected['cash_conversion_margin']


def test_owner_cash_policy_cannot_be_applied_to_another_issuer():
    packet=source(); packet['companyfacts']['cik']=1402057
    with pytest.raises(ValueError,match='owner-cash policy or issuer'):
        run(packet)
