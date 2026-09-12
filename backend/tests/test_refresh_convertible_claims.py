from __future__ import annotations

import copy,json
from pathlib import Path
import pytest

from app.us_valuation.refresh_convertible_claims import convertible_claim_policy,select_convertible_claim
from app.us_valuation.refresh_narrative_evidence import extract_narrative_evidence,narrative_policy

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'output/batch-28-structural-sources-20260831/MCHP/structural-filing.json'
PACKAGE=ROOT/'output/official-evidence-difficult-106-part-1/packages/MCHP/CIK0000827054-000082705426000038/2a4f3ba24bbed01ae8ff38908a6520bcd48e33dafdaec46bcd7b015cb0942abc/package-manifest.json'

def _source():
    structural=json.loads(SOURCE.read_text());policy=convertible_claim_policy('MCHP',{'bear':.12,'base':.105,'bull':.095})
    structural['narrative_evidence']=extract_narrative_evidence(narrative_policy('MCHP'),PACKAGE,source_root=ROOT/'output')
    filing={'accessionNumber':structural['source_accession'],'reportDate':structural['report_date'],
            'filingDate':structural['filed_date'],'form':structural['form']}
    return policy,structural,filing

def test_mchp_binds_hashed_narrative_schedule_without_double_counting_liquidation():
    policy,structural,filing=_source();result=select_convertible_claim(
        policy,structural,filing,policy['cik'],'2026-08-14')
    assert result['status']=='source_bound' and result['review_reasons']==[]
    assert result['components']['preferred_shares']==1_485_000
    assert result['components']['liquidation_preference']==1_485_000_000
    assert result['components']['liquidation_preference_deducted'] is False
    assert result['components']['payment_dates']==['2026-09-15','2026-12-15','2027-03-15','2027-06-15','2027-09-15','2027-12-15','2028-03-15']
    assert result['bear_conversion_shares']==pytest.approx(29_117_880)
    assert result['base_conversion_shares']==pytest.approx(26_443_394.5)
    assert result['bull_conversion_shares']==pytest.approx(23_768_909)
    assert result['bear_adjustment'] < result['base_adjustment'] < result['bull_adjustment']
    assert result['components']['capped_call_treatment']=='excluded_unless_realized_offset_is_source_bound'

def test_mchp_changed_preferred_state_fails_closed():
    policy,structural,filing=_source();changed=copy.deepcopy(structural)
    row=next(item for item in changed['facts'] if item.get('qname')==policy['current_conversion_increment_qname']
             and item.get('period_end')==filing['reportDate'] and not item.get('dimensions'))
    row['value']=1
    with pytest.raises(ValueError,match='state changed'):
        select_convertible_claim(policy,changed,filing,policy['cik'],'2026-08-14')

def test_mchp_policy_contains_no_filing_amount_or_date_constants_and_rejects_tampering():
    policy,structural,filing=_source()
    assert not {'accession','filed_date','period_end','amount'}&set(policy)
    changed=copy.deepcopy(policy);changed['version']='tampered'
    with pytest.raises(RuntimeError,match='identity/version mismatch'):
        select_convertible_claim(changed,structural,filing,policy['cik'],'2026-08-14')

def test_mchp_missing_narrative_receipt_fails_closed():
    policy,structural,filing=_source();structural.pop('narrative_evidence')
    with pytest.raises(ValueError,match='narrative evidence is missing'):
        select_convertible_claim(policy,structural,filing,policy['cik'],'2026-08-14')
