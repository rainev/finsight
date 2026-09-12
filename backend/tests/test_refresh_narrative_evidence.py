from __future__ import annotations

import copy
from pathlib import Path

import pytest

from app.us_valuation.refresh_narrative_evidence import (
    NarrativeEvidenceError, extract_narrative_evidence, narrative_policy,
    terms_by_name, validate_narrative_evidence,
)


ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'output'
MCHP=OUTPUT/'official-evidence-difficult-106-part-1/packages/MCHP/CIK0000827054-000082705426000038/2a4f3ba24bbed01ae8ff38908a6520bcd48e33dafdaec46bcd7b015cb0942abc/package-manifest.json'
BMY=OUTPUT/'batch-12-structural-cache-20260828/filings/BMY/CIK0000014272-000001427226000020/b0e0f096eec44b843c485dc9093655bd66563a08cfddc2f5e7d7aa0ed98ba498/package-manifest.json'


def test_mchp_receipt_has_exact_hashed_provenance_and_terms():
    receipt=extract_narrative_evidence(narrative_policy('MCHP'),MCHP,source_root=OUTPUT)
    terms=terms_by_name(receipt)
    assert receipt['source']['document_sha256']=='43bc8ef18e558929d6bb289ce345827f40edc5cdacf81379265071c333a69ad6'
    assert terms['mandatory_conversion_date']['value']=='2028-03-15'
    assert terms['minimum_conversion_rate']['value']==16.006
    assert terms['maximum_conversion_rate']['value']==19.608
    assert terms['annual_dividend_rate']['value']==.075
    assert terms['declared_quarterly_dividend_per_share']['value']==18.75
    assert terms['capped_call_cap_price']['value']==71.4
    assert all(row['locator']['normalized_text_end']>row['locator']['normalized_text_start'] for row in terms.values())
    assert validate_narrative_evidence(receipt,narrative_policy('MCHP'),source_root=OUTPUT)==receipt


def test_bmy_receipt_separates_paid_fixed_and_contingent_terms():
    terms=terms_by_name(extract_narrative_evidence(narrative_policy('BMY'),BMY,source_root=OUTPUT))
    assert terms['hengrui_upfront_payment']['value']==600_000_000
    assert terms['hengrui_first_anniversary_payment']['year']==2027
    assert terms['hengrui_second_anniversary_payment']['year']==2028
    assert terms['hengrui_contingent_milestone_maximum']['value']==14_300_000_000
    assert terms['biontech_paid_upfront_payment']['value']==1_500_000_000
    assert terms['biontech_future_anniversary_payments']['value']==2_000_000_000
    assert terms['biontech_contingent_milestone_maximum']['value']==7_600_000_000


def test_receipt_and_policy_tampering_fail_closed():
    policy=narrative_policy('MCHP');receipt=extract_narrative_evidence(policy,MCHP,source_root=OUTPUT)
    changed=copy.deepcopy(receipt);changed['terms'][0]['value']=0
    with pytest.raises(NarrativeEvidenceError,match='receipt hash mismatch'):
        validate_narrative_evidence(changed,policy,source_root=OUTPUT)
    changed_policy=copy.deepcopy(policy);changed_policy['version']='tampered'
    with pytest.raises(NarrativeEvidenceError,match='policy identity'):
        extract_narrative_evidence(changed_policy,MCHP,source_root=OUTPUT)
