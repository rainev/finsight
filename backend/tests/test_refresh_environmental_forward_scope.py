from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from app.us_valuation.refresh_environmental_forward_scope import environmental_forward_policy,bind_environmental_forward_scope
ROOT=Path(__file__).resolve().parents[2]
INDEX=ROOT/'output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json'
def inputs():
    st=json.loads((ROOT/'output/batch-21-structural-sources-20260831/LHX/structural-filing.json').read_bytes())
    n=json.loads((ROOT/'output/us-refresh-runtime/narrative-evidence/LHX.json').read_bytes())
    folder=ROOT/'output/batch-21-sec-source-packets-20260831/LHX'
    return st,n,json.loads((folder/'companyfacts.json').read_bytes()),json.loads((folder/'submissions.json').read_bytes())
def bind(st=None):
    original,n,cf,sub=inputs()
    return bind_environmental_forward_scope(environmental_forward_policy('LHX'),st or original,n,cf,sub,
        cutoff='2026-08-14',source_root=ROOT/'output')

def test_real_related_book_balances_do_not_become_net_reserve_or_surplus_cash():
    r=bind()
    assert r['gross_reserve']==660_000_000 and r['recoverable_asset']==485_000_000
    assert r['related_book_difference_not_pv_or_claim']==175_000_000
    assert r['claim_adjustment'] is None and r['pv_reserve'] is None and not r['numeric_successor_issued']
    assert r['recovery_mechanism']['value']=='future_government_contract_pricing_not_surplus_cash'

def test_missing_current_annual_payments_are_unknown_not_zero():
    r=bind()
    assert r['reported_environmental_cash_payments'] is None and r['payment_schedule'] is None
    assert all(not rows for rows in r['captured_annual_cash_concept_candidates'].values())
    assert r['current_payment_source_candidates']==[]
    assert len(r['annual_reported_operating_cash_flow_inventory'])==5

def test_balance_movements_do_not_infer_cash_payment_or_recovery():
    r=bind();h=r['balance_history_from_same_current_packet']
    assert h['gross']['2026-01-02']['value']==659_000_000
    assert h['recovery']['2026-01-02']['value']==483_000_000
    assert r['cash_recovery_timing'] is None and r['reported_environmental_cash_payments'] is None

@pytest.mark.parametrize('mutation',['member','extra_axis','namespace','parent','negative','conflict','missing'])
def test_gross_reserve_scope_and_missing_sources_fail_closed(mutation):
    st,_,_,_=inputs();rows=[r for r in st['facts'] if r['qname']=='us-gaap:AccrualForEnvironmentalLossContingencies' and r['period_end']=='2026-07-03']
    if mutation=='missing':st['facts']=[r for r in st['facts'] if r not in rows]
    elif mutation=='conflict':
        r=deepcopy(rows[0]);r['value']+=1;st['facts'].append(r)
    elif mutation=='member':rows[0]['dimensions']=[['us-gaap:EnvironmentalRemediationContingencyAxis','unrelated:OtherProgramMember']]
    elif mutation=='extra_axis':rows[0]['dimensions'].append(['us-gaap:StatementBusinessSegmentsAxis','unrelated:SegmentMember'])
    elif mutation=='namespace':rows[0]['namespace']='http://other.example/2026'
    elif mutation=='parent':rows[0]['presentation_parents']=[]
    else:rows[0]['value']=-1
    with pytest.raises(ValueError,match='environmental'):bind(st)

def test_unrelated_recovery_context_cannot_be_netted_against_gross():
    st,_,_,_=inputs()
    for r in st['facts']:
        if r['local_name']=='RecoverableEnvironmentalRemediationCosts' and r['period_end']=='2026-07-03':r['context_id']='other-program'
    with pytest.raises(ValueError,match='share context'):bind(st)

def test_real_frozen_workers_process_economic_ledger_without_model_gap_bypass():
    p=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),'--ticker','LHX','--ticker','MCK',
        '--max-workers','2','--source-index',str(INDEX)],cwd=ROOT,check=True,capture_output=True,text=True)
    summary=json.loads(p.stdout.strip().splitlines()[-1]);report=json.loads(Path(summary['report_path']).read_bytes())
    r=next(r for r in report['rows'] if r['ticker']=='LHX')
    assert summary['worker_count']==2 and r['status']=='implementation_gap'
    assert r['partial_environmental_forward_scope']['status']=='related_balances_verified_forward_cash_review'
    assert r['partial_environmental_forward_scope']['reported_environmental_cash_payments'] is None
    assert not r['partial_environmental_forward_scope']['numeric_successor_issued']
