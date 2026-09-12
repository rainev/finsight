from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_litigation_claims import litigation_claim_policy,select_litigation_claim


ROOT=Path(__file__).resolve().parents[2]
SOURCES={
    'ABBV':'output/batch-17-structural-sources-20260830/ABBV/structural-filing.json',
    'STE':'output/batch-17-structural-sources-20260830/STE/structural-filing.json',
    'CAH':'output/batch-13-structural-sources-20260829/CAH/structural-filing.json',
    'COO':'output/batch-13-structural-sources-20260829/COO/structural-filing.json',
    'FIS':'output/batch-38-structural-sources-20260907/FIS/structural-filing.json',
    'V':'output/batch-39-structural-sources-20260907/V/structural-filing.json',
    'DASH':'output/batch-08-structural-sources-20260826/DASH/structural-filing.json',
}


def _source(ticker):
    structural=json.loads((ROOT/SOURCES[ticker]).read_text())
    if ticker=='DASH' and structural.get('report_date') is None:
        structural={**structural,'report_date':'2026-06-30','filed_date':'2026-08-05'}
    filing={'accessionNumber':structural['source_accession'],
            'reportDate':structural.get('report_date') or ('2026-06-30' if ticker=='DASH' else None),
            'filingDate':structural.get('filed_date') or ('2026-08-05' if ticker=='DASH' else None),
            'form':structural['form']}
    return structural,filing


@pytest.mark.parametrize('ticker,amount',[('ABBV',1_700_000_000),('STE',43_200_000),('DASH',406_000_000)])
def test_direct_current_litigation_reserve_is_source_bound_once(ticker,amount):
    structural,filing=_source(ticker);policy=litigation_claim_policy(ticker)
    result=select_litigation_claim(policy,structural,filing,policy['cik'],'2026-08-14')
    assert result['status']=='source_bound'
    assert result['claim_adjustment']==amount
    assert result['components']['litigation_reserve']==amount


def test_abbv_noncash_reserve_flow_is_overlap_evidence_not_another_claim():
    structural,filing=_source('ABBV');policy=litigation_claim_policy('ABBV')
    result=select_litigation_claim(policy,structural,filing,'0001551152','2026-08-14')
    assert any(row['local_name']=='NonCashLitigationReserveAdjustmentsNetOfCashPayments'
               and row['value']==86_000_000 for row in result['excluded_rows'])
    assert result['claim_adjustment']==1_700_000_000


def test_ste_self_insurance_is_separate_from_litigation_reserve():
    structural,filing=_source('STE');policy=litigation_claim_policy('STE')
    result=select_litigation_claim(policy,structural,filing,'0001757898','2026-08-14')
    assert {row['qname'] for row in result['excluded_rows']}=={
        'us-gaap:SelfInsuranceReserveCurrent','us-gaap:SelfInsuranceReserveNoncurrent'}
    assert sum(row['value'] for row in result['excluded_rows'])==38_800_000


def test_cah_current_reserves_are_distinct_but_post_period_cash_blocks_use():
    structural,filing=_source('CAH');policy=litigation_claim_policy('CAH')
    result=select_litigation_claim(policy,structural,filing,'0000721371','2026-08-14')
    assert result['status']=='review_required' and result['claim_adjustment'] is None
    assert result['current_carrying_claim']==4_329_000_000
    assert result['components']=={'opioid_total_reserve':4_300_000_000,
        'other_current_accrual':29_000_000,'opioid_current_portion':468_000_000}
    assert any(row['qname']=='us-gaap:LossContingencyEstimateOfPossibleLoss'
               and row['value']==448_000_000 for row in result['excluded_rows'])
    assert result['review_reasons']==['post_period_legal_cash_requires_claim_and_cash_rollforward']


def test_coo_nets_only_the_recognized_litigation_receivable():
    structural,filing=_source('COO');policy=litigation_claim_policy('COO')
    result=select_litigation_claim(policy,structural,filing,'0000711404','2026-08-14')
    assert result['status']=='source_bound'
    assert result['claim_adjustment']==272_300_000
    assert result['components']=={'litigation_reserve':324_800_000,
        'recognized_recovery_receivable':52_500_000,'net_litigation_claim':272_300_000}


def test_fis_operating_settlement_balances_do_not_become_litigation_claims():
    structural,filing=_source('FIS');policy=litigation_claim_policy('FIS')
    result=select_litigation_claim(policy,structural,filing,'0001136893','2026-08-14')
    assert result['status']=='review_required' and result['claim_adjustment'] is None
    assert result['components']=={'operating_settlement_assets':624_000_000,
        'operating_settlement_liabilities':687_000_000}
    assert result['review_reasons']==['insurance_funded_legal_event_has_no_recognized_numeric_claim_or_recovery']


def test_visa_litigation_and_operating_settlement_scopes_are_separate():
    structural,filing=_source('V');policy=litigation_claim_policy('V')
    result=select_litigation_claim(policy,structural,filing,'0001403161','2026-08-14')
    assert result['status']=='review_required' and result['claim_adjustment'] is None
    assert result['current_carrying_claim']==386_000_000
    assert result['components']['operating_settlement_net']==877_000_000
    assert result['components']['matched_customer_collateral']==4_310_000_000
    assert result['review_reasons']==['litigation_recovery_and_preferred_conversion_overlap_requires_review']


@pytest.mark.parametrize('ticker',[*SOURCES])
def test_litigation_policies_contain_no_filing_date_accession_or_amount(ticker):
    policy=litigation_claim_policy(ticker)
    assert not {'accession','filed_date','period_end','amount'} & set(policy)
    structural,filing=_source(ticker);policy['version']='tampered'
    with pytest.raises(RuntimeError,match='identity/version mismatch'):
        select_litigation_claim(policy,structural,filing,policy['cik'],'2026-08-14')


@pytest.mark.parametrize('ticker,litigation,nci',[('ABBV',1_700_000_000,47_000_000),('STE',43_200_000,14_500_000),('COO',272_300_000,200_000)])
def test_direct_claim_reclassification_preserves_prior_value(ticker,litigation,nci):
    from app.us_valuation.calculation_recipe import evaluate_recipe
    recipe=json.loads((ROOT/f'output/us-refresh-runtime/recipes/{ticker}.json').read_text())
    mapped=deepcopy(recipe)
    for spec in mapped['scenarios'].values():
        assert spec['inputs']['preferred_equity']==litigation+nci
        spec['inputs']['preferred_equity']=0.0
        spec['inputs']['noncontrolling_interests']=nci
        spec['inputs']['nonoperating_adjustment']=-litigation
    assert evaluate_recipe(mapped)['range']==evaluate_recipe(recipe)['range']
