from __future__ import annotations

import copy,json
from pathlib import Path

import pytest

from app.us_valuation.refresh_nci_ownership_claims import nci_ownership_claim_policy,select_nci_ownership_claim


ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'output/batch-18-structural-sources-20260830/CMI/structural-filing.json'
APD_SOURCE=ROOT/'output/batch-41-structural-sources-20260907/APD/structural-filing.json'


def _source():
    structural=json.loads(SOURCE.read_bytes());policy=nci_ownership_claim_policy('CMI')
    filing={'accessionNumber':structural['source_accession'],'reportDate':structural['report_date'],
            'filingDate':structural['filed_date'],'form':structural['form']}
    return policy,structural,filing


def test_cmi_keeps_current_nci_separate_and_blocks_unreconciled_guarantee_scopes():
    policy,structural,filing=_source();result=select_nci_ownership_claim(
        policy,structural,filing,policy['cik'],'2026-08-14')
    assert result['status']=='review_required' and result['claim_adjustment'] is None
    assert result['review_reasons']==[
        'guarantee_carrying_value_and_maximum_have_unreconciled_scopes',
        'unconsolidated_vie_future_contribution_has_no_timed_payment_schedule']
    assert result['components']=={
        'ordinary_nci':1_059_000_000.,'recognized_guarantee_carrying_value':257_000_000.,
        'guarantee_maximum':50_000_000.,'guarantee_added_to_nci':False,
        'unconsolidated_vie_investment':350_000_000.,
        'joint_venture_contributions_paid':412_000_000.,
        'future_joint_venture_contribution':418_000_000.,
        'vie_investment_or_contribution_added_to_nci':False}


def test_apd_parent_equity_reconciles_total_nci_and_vie_subset_without_second_deduction():
    structural=json.loads(APD_SOURCE.read_bytes());policy=nci_ownership_claim_policy('APD')
    filing={'accessionNumber':structural['source_accession'],'reportDate':structural['report_date'],
            'filingDate':structural['filed_date'],'form':structural['form']}
    result=select_nci_ownership_claim(policy,structural,filing,policy['cik'],'2026-08-14')
    assert result['status']=='source_bound' and result['claim_adjustment']==0
    assert result['components']=={
        'total_nci':2_712_600_000.,'consolidated_vie_nci_subset':1_831_600_000.,
        'parent_equity':13_883_800_000.,'total_equity':16_596_400_000.,
        'nci_deducted_again':False}
    assert all(row.get('period_start') is not None for row in result['source_rows'][5:])


def test_cmi_claim_policy_contains_no_filing_amounts_or_dates_and_rejects_conflict():
    policy,structural,filing=_source()
    assert not {'accession','filed_date','period_end','amount'}&set(policy)
    changed=copy.deepcopy(structural)
    duplicate=copy.deepcopy(next(row for row in changed['facts'] if row.get('qname')==policy['nci_qname']
        and row.get('period_end')==filing['reportDate'] and row.get('period_start') is None and not row.get('dimensions')))
    duplicate['value']+=1;changed['facts'].append(duplicate)
    with pytest.raises(ValueError,match='missing or conflicting'):
        select_nci_ownership_claim(policy,changed,filing,policy['cik'],'2026-08-14')
