from __future__ import annotations

import copy,json
from pathlib import Path

import pytest

from app.us_valuation.refresh_narrative_evidence import extract_narrative_evidence,narrative_policy
from app.us_valuation.refresh_transaction_claims import select_transaction_claim,transaction_claim_policy


ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'output/batch-12-structural-sources-20260828/BMY/structural-filing.json'
PACKAGE=ROOT/'output/batch-12-structural-cache-20260828/filings/BMY/CIK0000014272-000001427226000020/b0e0f096eec44b843c485dc9093655bd66563a08cfddc2f5e7d7aa0ed98ba498/package-manifest.json'


def _source():
    structural=json.loads(SOURCE.read_text());policy=transaction_claim_policy('BMY')
    structural['narrative_evidence']=extract_narrative_evidence(narrative_policy('BMY'),PACKAGE,source_root=ROOT/'output')
    filing={'accessionNumber':structural['source_accession'],'reportDate':structural['report_date'],
            'filingDate':structural['filed_date'],'form':structural['form']}
    return policy,structural,filing


def test_bmy_reconciles_hengrui_and_preserves_biontech_timing_blocker():
    policy,structural,filing=_source();result=select_transaction_claim(policy,structural,filing,policy['cik'],'2026-08-14')
    assert result['status']=='review_required'
    assert result['review_reasons']==['biontech_fixed_payment_schedule_has_only_a_timing_envelope']
    assert result['components']=={
        'recognized_cvr_liability':607_000_000,
        'hengrui_fixed_unpaid_payments':950_000_000,
        'currently_modeled_claim':1_557_000_000,
        'hengrui_contingent_maximum_excluded':14_300_000_000,
        'biontech_paid_cash_excluded':1_500_000_000,
        'biontech_fixed_payment_timing_envelope':2_000_000_000,
        'biontech_contingent_maximum_excluded':7_600_000_000,
    }


def test_bmy_narrative_structural_conflict_fails_closed():
    policy,structural,filing=_source();changed=copy.deepcopy(structural)
    row=next(item for item in changed['facts'] if item.get('local_name')==policy['upfront_local_name'])
    row['value']+=1
    with pytest.raises(ValueError,match='narrative and structural value conflict'):
        select_transaction_claim(policy,changed,filing,policy['cik'],'2026-08-14')
