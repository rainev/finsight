import copy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_financials import (
    POLICY_VERSION, LEGACY_POLICY_VERSION, cash_history, financing_adjustment, _financing_normalizer,
    CDW_CASH_INTEREST_POLICY,
    MCO_CASH_INTEREST_POLICY,
)
from app.us_valuation.xbrl import CompanyFactsNormalizer

ROOT = Path(__file__).parents[2]


def cdw_packet():
    root = ROOT/'output/batch-31-sec-replay-a-20260902/CDW'
    return {name:json.loads((root/f'{name}.json').read_text()) for name in ('submissions','companyfacts')}


def test_cdw_cash_interest_uses_consistent_real_current_and_annual_sources():
    source = cdw_packet()
    before = copy.deepcopy(source)
    result = cash_history(normalizer(source),period='2026-06-30',cutoff='2026-08-14',
        rule={'normalization_version':POLICY_VERSION,'financing_policy':CDW_CASH_INTEREST_POLICY})
    assert result['financing_adjustment_basis']=='cash_interest_paid_proxy'
    assert result['reported']['interest_expense']==234300000+116900000-120400000
    assert [row['interest_expense']['value'] for row in result['annual']] == [134300000,224300000,233200000,217500000,234300000]
    assert all(row['interest_expense']['concept'].split(':')[-1]=='InterestPaidNet' for row in result['annual'])
    expected = result['reported']['operating_cash_flow']-result['reported']['capital_expenditures']+230800000*(1-result['tax_rate'])
    assert result['ttm_cash_fcff']==pytest.approx(expected)
    assert source==before


def test_cash_interest_does_not_fallback_or_accept_wrong_issuer():
    source = cdw_packet()
    source['companyfacts']['facts']['us-gaap'].pop('InterestPaidNet')
    with pytest.raises(ValueError,match='consistently scoped'):
        _financing_normalizer(normalizer(source),'2026-06-30',CDW_CASH_INTEREST_POLICY)
    with pytest.raises(ValueError,match='issuer-specific'):
        _financing_normalizer(normalizer(packet()),'2026-04-30',CDW_CASH_INTEREST_POLICY)


def test_cash_interest_rejects_negative_comparative_even_when_ttm_is_positive():
    source = cdw_packet()
    for row in source['companyfacts']['facts']['us-gaap']['InterestPaidNet']['units']['USD']:
        if row.get('end')=='2025-06-30':
            row['val'] = -abs(row['val'])
    with pytest.raises(ValueError,match='nonnegative reported payments'):
        _financing_normalizer(normalizer(source),'2026-06-30',CDW_CASH_INTEREST_POLICY)


def test_mco_preserves_cash_interest_and_does_not_deduct_sale_gains_again():
    root=ROOT/'output/batch-37-sec-source-packets-20260906/MCO'
    source={name:json.loads((root/f'{name}.json').read_text()) for name in ('submissions','companyfacts')}
    result=cash_history(normalizer(source),period='2026-06-30',cutoff='2026-08-14',
        rule={'normalization_version':POLICY_VERSION,'financing_policy':MCO_CASH_INTEREST_POLICY})
    assert result['reported']['operating_cash_flow']==3319000000
    assert result['reported']['capital_expenditures']==352000000
    assert result['reported']['interest_expense']==235000000+107000000-136000000
    assert result['financing_adjustment_basis']=='cash_interest_paid_proxy'
    assert all(row['interest_expense']['concept'].split(':')[-1]=='InterestPaidNet' for row in result['annual'])
    assert result['ttm_cash_fcff']==pytest.approx(3319000000-352000000+206000000*(1-result['tax_rate']))
    assert 'cash_receipt_adjustment' not in result
    with pytest.raises(ValueError,match='issuer-specific'):
        _financing_normalizer(normalizer(source),'2026-06-30',CDW_CASH_INTEREST_POLICY)


def packet():
    return json.loads((ROOT/'output/us-refresh-runtime/acquisitions/506c1ecff5edd36238a72e9a6ebe30be11e2679946d4c9342e329b811cd466bc/packets/CPRT.json').read_text())['packet']


def normalizer(source):
    recent = source['submissions']['filings']['recent']
    records = [{key:values[i] for key,values in recent.items() if isinstance(values,list) and i<len(values)} for i in range(len(recent['accessionNumber']))]
    return CompanyFactsNormalizer(source['companyfacts'],fiscal_year_end=source['submissions']['fiscalYearEnd'],
        as_of_date='2026-08-14',filing_records=records)


def test_real_net_interest_income_is_removed_not_added_as_expense():
    source = packet()
    result = cash_history(normalizer(source),period='2026-04-30',cutoff='2026-08-14',rule={'normalization_version':POLICY_VERSION})
    assert result['financing_adjustment_basis'] == 'net_nonoperating_interest'
    assert result['reported']['interest_expense'] == 192144000.
    assert result['financing_adjustment_before_tax'] == -192144000.
    assert result['financing_adjustment_after_tax'] < 0
    expected = result['reported']['operating_cash_flow'] - result['reported']['capital_expenditures'] - 192144000.*(1-result['tax_rate'])
    assert result['ttm_cash_fcff'] == pytest.approx(expected)
    legacy = cash_history(normalizer(source),period='2026-04-30',cutoff='2026-08-14',rule={'normalization_version':LEGACY_POLICY_VERSION})
    assert legacy['ttm_cash_fcff'] > result['ttm_cash_fcff']


def test_gross_and_net_interest_cannot_be_spliced_into_one_ttm():
    source = packet()
    gaap = source['companyfacts']['facts']['us-gaap']
    net = gaap['InterestIncomeExpenseNonoperatingNet']['units']['USD']
    annual = copy.deepcopy(next(row for row in net if row.get('form') == '10-K' and row.get('end') == '2025-07-31'))
    gaap['InterestIncomeExpenseNonoperatingNet']['units']['USD'] = [row for row in net if row.get('end') != '2025-07-31']
    for concept in ('InterestExpenseNonOperating','InterestAndDebtExpense','InterestExpenseDebt','InterestExpense'):
        gaap.pop(concept,None)
    gaap['InterestExpense'] = {'units':{'USD':[annual]}}
    with pytest.raises(ValueError,match='consistently scoped'):
        _financing_normalizer(normalizer(source),'2026-04-30')


def test_financing_signs_are_explicit_not_absolute_values():
    assert financing_adjustment(10,basis='gross_expense_proxy') == 10
    assert financing_adjustment(10,basis='net_nonoperating_interest') == -10
    assert financing_adjustment(-10,basis='net_nonoperating_interest') == 10
    with pytest.raises(ValueError):
        financing_adjustment(-10,basis='gross_expense_proxy')
