from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys
import pytest
from app.us_valuation.refresh_reported_claim_scope import REPORTED_NCI_SCOPE_RULES,reported_nci_field_availability,ClaimScopeReviewRequired
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_wg26_redeemable_ownership import proof
INDEX=ROOT/'output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json'
PATHS={'LHX':'batch-21-structural-sources-20260831/LHX','MCK':'batch-14-structural-sources-resume-20260829/MCK'}
def source(t):return json.loads((ROOT/'output'/PATHS[t]/'structural-filing.json').read_bytes())
def bound(t,st=None):
    st=st or source(t)
    return reported_nci_field_availability(ticker=t,policy=asdict(REPORTED_NCI_SCOPE_RULES[t]),structural_packet=st,
        accession=st['source_accession'],period_end=st['report_date'])[1]

@pytest.mark.parametrize('ticker,total',[('LHX',968_000_000),('MCK',2_939_000_000)])
def test_real_carrying_and_alias_proofs_do_not_add_duplicates(ticker,total):
    p=bound(ticker);assert p['source_total']==total
    st=source(ticker);st['facts'].extend(deepcopy(st['facts']))
    assert bound(ticker,st)['source_total']==total
    assert len(p['alias_components'])==1

def test_redemption_value_is_separate_from_carrying_alias_and_not_summed():
    p=bound('LHX')
    assert p['alias_components'][0]['value']==968_000_000
    assert p['nonclaim_instant_diagnostics'][0]['value']==1_422_000_000

def test_negative_ordinary_nci_does_not_offset_redeemable_claim():
    st=source('MCK')
    for r in st['facts']:
        if r['qname']=='us-gaap:MinorityInterest' and r['period_start'] is None and not r.get('dimensions'):r['value']=-1.
    with pytest.raises(ClaimScopeReviewRequired,match='negative ownership'):bound('MCK',st)

@pytest.mark.parametrize('ticker',['LHX','MCK'])
def test_wrong_alias_value_is_not_target_fitted(ticker):
    st=source(ticker);alias=REPORTED_NCI_SCOPE_RULES[ticker].allowed_alias_qnames[0]
    for r in st['facts']:
        if r['qname']==alias:r['value']+=1
    with pytest.raises(ClaimScopeReviewRequired,match='does not reconcile'):bound(ticker,st)

@pytest.mark.parametrize('mutation',['member','namespace','extra_axis','parent'])
def test_dimensional_alias_needs_declared_member_and_presentation(mutation):
    st=source('MCK')
    for r in st['facts']:
        if r['qname']=='us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount' and r['period_start'] is None:
            if mutation=='member':r['dimensions']=[['us-gaap:StatementEquityComponentsAxis','us-gaap:CommonStockMember']]
            elif mutation=='namespace':r['dimensions']=[['us-gaap:StatementEquityComponentsAxis','unrelated:RedeemableNoncontrollingInterestMember']]
            elif mutation=='extra_axis':r['dimensions'].append(['us-gaap:StatementBusinessSegmentsAxis','unrelated:SegmentMember'])
            else:r['presentation_parents']=[]
    with pytest.raises(ClaimScopeReviewRequired,match='scope mismatch'):bound('MCK',st)

def test_temporary_alias_cannot_be_replaced_by_investor_asset_or_flow():
    st=source('LHX')
    for r in st['facts']:
        if r['qname']=='us-gaap:TemporaryEquityCarryingAmountAttributableToParent':r['presentation_parents']=['us-gaap:AssetsAbstract']
    with pytest.raises(ClaimScopeReviewRequired,match='presentation scope'):bound('LHX',st)

def test_legacy_reclassification_does_not_drop_reserve_or_post_paid_claims():
    p=proof(ROOT/'output/us-refresh-runtime',INDEX)
    for r in p['rows']:
        assert r['previous_range']==r['classification_replay_range'] and not r['numeric_successor_issued']
    assert p['rows'][0]['legacy_remaining_deduction_not_current_validated_claim']['base']==660_000_000
    assert p['rows'][1]['legacy_remaining_deduction_not_current_validated_claim']['base']==5_164_000_000

def test_partial_rules_do_not_clear_full_implementation_gaps():
    from app.us_valuation.refresh_operating_policies import _policy_for_entry
    from app.us_valuation.xbrl import load_concept_config
    root=ROOT/'output/us-refresh-runtime';reg=json.loads((root/'registry.json').read_bytes())
    for t in ('LHX','MCK','HCA','HON'):
        e=next(r for r in reg['entries'] if r['ticker']==t)
        p=_policy_for_entry(e,artifact=json.loads((root/'baseline/artifacts'/f'{t}.json').read_bytes()),
            recipe=json.loads((root/'recipes'/f'{t}.json').read_bytes()),source_evidence=None,concept_config=load_concept_config())
        assert 'baseline_non_debt_claim_scope_requires_source_rule' in p.reason_codes

def test_real_frozen_workers_record_partial_proof_without_claiming_numeric_refresh():
    import subprocess
    result=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),'--ticker','LHX','--ticker','MCK',
        '--max-workers','2','--source-index',str(INDEX)],cwd=ROOT,check=True,capture_output=True,text=True)
    summary=json.loads(result.stdout.strip().splitlines()[-1]);report=json.loads(Path(summary['report_path']).read_bytes())
    assert summary['worker_count']==2
    for r in report['rows']:
        assert r['status']=='implementation_gap'
        assert r['partial_ownership_proof']['status']=='source_bound'
        assert not r['partial_ownership_proof']['numeric_successor_issued']
