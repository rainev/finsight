from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_reported_claim_scope import (
    REPORTED_NCI_SCOPE_RULES,reported_nci_field_availability,ClaimScopeReviewRequired,
)
from app.us_valuation.refresh_commitment_claims import commitment_claim_policy,select_commitment_claim
from app.us_valuation.calculation_recipe import evaluate_recipe

ROOT=Path(__file__).resolve().parents[2]
SOURCES={'JBL':'batch-28-structural-sources-20260831/JBL/structural-filing.json',
         'INTC':'batch-26-structural-sources-20260831/INTC/structural-filing.json'}

def source(ticker):
    st=json.loads((ROOT/'output'/SOURCES[ticker]).read_bytes())
    from app.us_valuation.refresh_source_ingestion import _validate_structural_payload
    filing={'accessionNumber':st['source_accession'],'reportDate':st.get('report_date') or st['period_end'],
            'filingDate':st['filed_date'],'form':st['form']}
    st=_validate_structural_payload(st,cik=REPORTED_NCI_SCOPE_RULES[ticker].cik,
        filing={'accession':filing['accessionNumber'],'report_date':filing['reportDate'],'form':filing['form']})
    return st,filing

def proof(ticker,st=None):
    original,filing=source(ticker)
    return reported_nci_field_availability(ticker=ticker,policy=asdict(REPORTED_NCI_SCOPE_RULES[ticker]),
        structural_packet=st or original,accession=filing['accessionNumber'],period_end=filing['reportDate'])[1]

@pytest.mark.parametrize('ticker,total',[('JBL',4_000_000),('INTC',15_601_000_000)])
def test_ordinary_nci_balance_and_member_reconcile_without_owner_flows(ticker,total):
    p=proof(ticker);eq=p['equity_reconciliation']
    assert p['source_total']==eq['nci_equity_member']==eq['consolidated_equity']-eq['parent_equity']==total
    assert p['duration_diagnostics']

def test_intc_subsidiaries_are_disjoint_reconciling_subsets_not_extra_claims():
    st,_=source('INTC');p=proof('INTC');parts=p['equity_reconciliation']['nonadditive_subsets']
    assert sorted(parts.values())==[0,123_000_000,2_050_000_000,13_428_000_000]
    duplicate=deepcopy(st);duplicate['facts'].extend(deepcopy([r for r in st['facts'] if r.get('qname')=='us-gaap:MinorityInterest' and r.get('dimensions')]))
    assert proof('INTC',duplicate)['source_total']==15_601_000_000
    changed=deepcopy(st)
    for r in changed['facts']:
        if r.get('qname')=='us-gaap:MinorityInterest' and r.get('period_start') is None and any('SubsidiariesArizonaSCIPMember' in str(d[1]) for d in r.get('dimensions') or []):r['value']+=1_000_000
    with pytest.raises(ClaimScopeReviewRequired,match='subsets do not reconcile'):
        proof('INTC',changed)

def test_jbl_new_finance_lease_buckets_remain_review_not_current_debt_or_pv():
    st,f=source('JBL');policy=commitment_claim_policy('JBL')
    r=select_commitment_claim(policy,st,f,policy['cik'],'2026-08-14')
    assert r['status']=='review_required' and r['claim_adjustment'] is None
    assert r['components']['new_finance_lease_future_payments']==51_000_000
    assert sorted(r['components']['reported_nonannual_payment_buckets'].values())==[0,6_000_000,8_000_000,37_000_000]
    assert r['components']['current_total_carrying_finance_lease_claim'] is None
    changed=deepcopy(st)
    for row in changed['facts']:
        if row['qname']==policy['total_qname'] and row['period_end']==f['reportDate']:row['value']+=1
    with pytest.raises(ValueError,match='does not reconcile'):
        select_commitment_claim(policy,changed,f,policy['cik'],'2026-08-14')

@pytest.mark.parametrize('ticker,nci,remaining',[('JBL',4_000_000,51_000_000),('INTC',15_601_000_000,0)])
def test_nci_reclassification_preserves_every_legacy_deduction(ticker,nci,remaining):
    recipe=json.loads((ROOT/'output/us-refresh-runtime/recipes'/f'{ticker}.json').read_bytes());old=evaluate_recipe(recipe)['range'];changed=deepcopy(recipe)
    for spec in changed['scenarios'].values():
        spec['inputs'].update(preferred_equity=0.,noncontrolling_interests=nci,nonoperating_adjustment=-remaining)
    assert evaluate_recipe(changed)['range']==old

def test_intc_approved_margin_override_is_not_silently_replaced_by_median():
    from app.us_valuation.refresh_operating_policies import _policy_for_entry
    from app.us_valuation.xbrl import load_concept_config
    root=ROOT/'output/us-refresh-runtime';entry=next(r for r in json.loads((root/'registry.json').read_bytes())['entries'] if r['ticker']=='INTC')
    recipe=json.loads((root/'recipes/INTC.json').read_bytes());artifact=json.loads((root/'baseline/artifacts/INTC.json').read_bytes())
    r=_policy_for_entry(entry,artifact=artifact,recipe=recipe,source_evidence=None,concept_config=load_concept_config())
    assert not r.reason_codes
    assert r.policy['governed_margin_policy']['scenario_margins']==(.03,.07,.12)
    from app.us_valuation.batch_26_history import MARGIN_OVERRIDES
    assert MARGIN_OVERRIDES['INTC']==(.03,.07,.12)
