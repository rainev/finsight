from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from app.us_valuation.refresh_subsidiary_ownership_scope import subsidiary_ownership_policy,bind_subsidiary_ownership_scope,ownership_basis_diagnostic

ROOT=Path(__file__).resolve().parents[2]
def source():return json.loads((ROOT/'output/batch-14-structural-sources-resume-20260829/MCK/structural-filing.json').read_bytes())
def narrative():return json.loads((ROOT/'output/us-refresh-runtime/narrative-evidence/MCK.json').read_bytes())
def bind(st=None,n=None):return bind_subsidiary_ownership_scope(subsidiary_ownership_policy('MCK'),st if st is not None else source(),n if n is not None else narrative(),cutoff='2026-08-14',source_root=ROOT/'output')

def test_real_ordinary_redeemable_rolls_terms_proceeds_not_intrinsic_claim():
    r=bind();t=r['reported_terms']
    assert r['reported_ordinary_carrying']==376_000_000 and r['reported_redeemable_carrying']==2_563_000_000
    assert r['net_proceeds_source']['value']==1_238_000_000
    assert t['apollo_approximate_investment']['value']==1_250_000_000
    assert t['apollo_subsidiary_ownership_percent']['value']==13 and t['core_put_cadence_years']['value']==5
    assert t['historical_prism_rni']['value']==25_000_000 and t['historical_core_rni']['value']==700_000_000
    assert r['parent_preferred_source']['value']==0
    assert r['instrument_economic_basis']['economic_claim'] is None
    assert r['instrument_economic_basis']['parent_conversion_shares'] is None
    assert r['first_put_exercise_date'] is None and r['put_payment_schedule'] is None
    assert r['financing_cash_adjustment'] is None and not r['numeric_successor_issued']

def test_aliases_duplicates_and_redemption_movements_not_added_as_new_claims():
    st=source();st['facts'].extend(deepcopy(st['facts']));r=bind(st)
    assert r['ownership_carrying_proof']['source_total']==2_939_000_000
    assert sum(s['value'] for s in r['redemption_movement_sources'].values())==374_000_000

@pytest.mark.parametrize('mutation',['namespace','parent','period','negative','conflict','missing','redemption_axis','redemption_value','ending','generation','gaap_qname','arbitrary_prefix','duplicate_role'])
def test_source_scope_and_actual_rollforward_fail_closed(mutation):
    st=source();p=next(r for r in st['facts'] if r.get('local_name')=='ProceedsFromSaleOfNoncontrollingInterests' and r['period_end']=='2026-06-30')
    if mutation=='namespace':p['namespace']='http://wrong.example/20260630'
    elif mutation=='parent':p['presentation_parents']=[]
    elif mutation=='period':p['period_start']='2026-04-02'
    elif mutation=='negative':p['value']=-1
    elif mutation=='conflict':
        row=deepcopy(p);row['value']+=1;st['facts'].append(row)
    elif mutation=='missing':st['facts'].remove(p)
    elif mutation=='gaap_qname':p['qname']='us-gaap:ProceedsFromSaleOfNoncontrollingInterests'
    elif mutation=='arbitrary_prefix':p['qname']='unverified:ProceedsFromSaleOfNoncontrollingInterests'
    elif mutation=='duplicate_role':
        row=deepcopy(p);row['statement_roles']=[];st['facts'].append(row)
    elif mutation=='ending':next(r for r in st['facts'] if r['qname']=='us-gaap:MinorityInterest' and r['period_end']=='2026-06-30')['value']+=1
    elif mutation=='generation':st['filing_metadata']=[(key,'wrong' if key=='package_generation' else value) for key,value in st['filing_metadata']]
    else:
        row=next(r for r in st['facts'] if r['qname']=='us-gaap:TemporaryEquityAccretionToRedemptionValueAdjustment' and r['period_end']=='2026-06-30')
        if mutation=='redemption_axis':row['dimensions'].append(['us-gaap:OtherAxis','us-gaap:OtherMember'])
        else:row['value']+=1
    with pytest.raises(ValueError):bind(st)

@pytest.mark.parametrize('cash,shares',[(1,None),(None,1),(1,1)])
def test_no_invented_alternative_claim_or_parent_percentage_dilution(cash,shares):
    with pytest.raises(ValueError):ownership_basis_diagnostic(cash_claim=cash,parent_conversion_shares=shares)

def test_no_receipt_override_of_governed_contract_terms():
    n=narrative();next(t for t in n['terms'] if t['name']=='core_put_cadence_years')['value']=1
    with pytest.raises(ValueError):bind(n=n)

def test_policy_copy_cannot_mutate_versioned_component_mapping():
    p=subsidiary_ownership_policy('MCK');p['redemption_component_members']['CoreVenturesMember']='wrong'
    assert subsidiary_ownership_policy('MCK')['redemption_component_members']['CoreVenturesMember']=='core_redemption'
    with pytest.raises(ValueError,match='policy identity'):bind_subsidiary_ownership_scope(p,source(),narrative(),cutoff='2026-08-14',source_root=ROOT/'output')

def test_real_frozen_workers_process_new_scope_preserve_cash_and_lhx_blockers():
    p=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),'--ticker','MCK','--ticker','LHX','--max-workers','2',
        '--source-index',str(ROOT/'output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json')],cwd=ROOT,check=True,capture_output=True,text=True)
    summary=json.loads(p.stdout.strip().splitlines()[-1]);report=json.loads(Path(summary['report_path']).read_bytes())
    mck=next(r for r in report['rows'] if r['ticker']=='MCK')
    assert mck['status']=='implementation_gap' and mck['partial_subsidiary_ownership_scope']['reported_redeemable_carrying']==2_563_000_000
    assert mck['partial_settlement_payment_bridge']['payment_only_bridge']['actual_post_period_cash'] is None
    lhx=next(r for r in report['rows'] if r['ticker']=='LHX')
    assert lhx['status']=='implementation_gap' and lhx['partial_environmental_annual_evidence']['claim_adjustment'] is None
