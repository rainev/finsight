from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from app.us_valuation.refresh_environmental_annual_evidence import (
    extract_annual_environmental_evidence,validate_annual_environmental_evidence,
)

ROOT=Path(__file__).resolve().parents[2]
RECEIPT=ROOT/'output/us-refresh-runtime/environmental-annual-evidence/LHX.json'

def receipt():return json.loads(RECEIPT.read_bytes())
def sources(r):return [{k:s[k] for k in ('package_manifest_path','structural_path')} for s in r['sources']]

def test_real_annuals_preserve_vintages_and_do_not_supply_payment_zero_or_pv():
    r=validate_annual_environmental_evidence(receipt(),source_root=ROOT/'output',cutoff='2026-08-14')
    assert len(r['observations'])==2 and r['overlapping_period_differences']==[]
    current=r['observations'][0]['related_balances'][-1]
    assert current['reported_liability']['value']==659_000_000
    assert current['recoverable_asset']['value']==483_000_000
    assert r['reported_environmental_cash_payments'] is None and r['cash_recovery_timing'] is None
    assert r['pv_reserve'] is None and r['claim_adjustment'] is None and not r['numeric_successor_issued']
    assert all(o['payment_candidates']==[] and o['recovery_cash_candidates']==[] for o in r['observations'])
    terms={t['name']:t for t in r['observations'][0]['accounting_terms']}
    assert terms['conditional_discounting_policy']['value']=='may_already_include_discounting_not_proof_all_reserves_are_pv'
    assert terms['capitalized_environmental_expenditures']['value']=='capital_expenditures_not_automatic_ocf_addback'
    assert all('locator' in t and 'excerpt_sha256' in t for t in terms.values())

@pytest.mark.parametrize('field,value',[('claim_adjustment',175_000_000),('reported_environmental_cash_payments',0),
    ('pv_reserve',660_000_000),('numeric_successor_issued',True),('cutoff','2026-09-16')])
def test_receipt_cannot_invent_cash_or_economic_approval(field,value):
    r=receipt();r[field]=value
    with pytest.raises(ValueError):validate_annual_environmental_evidence(r,source_root=ROOT/'output',cutoff='2026-08-14')

@pytest.mark.parametrize('mutation',['namespace','parent','dimension','missing','negative','filing_date'])
def test_annual_scope_rejects_wrong_or_missing_source(monkeypatch,mutation):
    r=receipt();target=(ROOT/'output'/r['sources'][0]['structural_path']).resolve()
    original=Path.read_bytes;st=json.loads(original(target))
    row=next(f for f in st['facts'] if f['local_name']=='AccrualForEnvironmentalLossContingencies')
    if mutation=='namespace':row['namespace']='http://wrong.example/2025'
    elif mutation=='parent':row['presentation_parents']=[]
    elif mutation=='dimension':row['dimensions'].append(['us-gaap:OtherAxis','wrong:Member'])
    elif mutation=='missing':st['facts']=[f for f in st['facts'] if f['local_name']!='AccrualForEnvironmentalLossContingencies']
    elif mutation=='negative':row['value']=-1
    else:st['filed_date']='2026-02-13'
    monkeypatch.setattr(Path,'read_bytes',lambda p:json.dumps(st).encode() if p.resolve()==target else original(p))
    with pytest.raises(ValueError):extract_annual_environmental_evidence('LHX',sources(r),source_root=ROOT/'output',cutoff='2026-08-14')

def test_real_frozen_workers_include_annual_receipt_and_retain_full_gaps():
    index=ROOT/'output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json'
    p=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),'--ticker','LHX','--ticker','MCK',
        '--max-workers','2','--source-index',str(index)],cwd=ROOT,check=True,capture_output=True,text=True)
    summary=json.loads(p.stdout.strip().splitlines()[-1]);report=json.loads(Path(summary['report_path']).read_bytes())
    row=next(r for r in report['rows'] if r['ticker']=='LHX')
    assert row['status']=='implementation_gap'
    assert len(row['partial_environmental_annual_evidence']['observations'])==2
    assert row['partial_environmental_annual_evidence']['reported_environmental_cash_payments'] is None
    assert 'partial_environmental_annual_evidence' not in next(r for r in report['rows'] if r['ticker']=='MCK')

@pytest.mark.parametrize('mutation',['count','bytes','duplicate'])
def test_inconsistent_package_resource_envelope_rejected(monkeypatch,mutation):
    r=receipt();target=(ROOT/'output'/r['sources'][0]['package_manifest_path']).resolve()
    original=Path.read_bytes;m=json.loads(original(target))
    if mutation=='count':m['resource_count']+=1
    elif mutation=='bytes':m['total_bytes']+=1
    else:
        row=deepcopy(m['files'][-1]);m['files'].append(row)
        m['resource_count']+=1;m['total_bytes']+=row['byte_count']
    monkeypatch.setattr(Path,'read_bytes',lambda p:json.dumps(m).encode() if p.resolve()==target else original(p))
    with pytest.raises(ValueError):extract_annual_environmental_evidence('LHX',sources(r),source_root=ROOT/'output',cutoff='2026-08-14')
