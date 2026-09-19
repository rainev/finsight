from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from app.us_valuation.refresh_separation_scope import bind_separation_scope, separation_policy, extract_separation_terms
from app.us_valuation.refresh_narrative_evidence import _VisibleText, narrative_policy

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'output'

def inputs():
    st=json.loads((SOURCE/'batch-22-structural-sources-corrected-20260831/HON/structural-filing.json').read_bytes())
    n=json.loads((SOURCE/'us-refresh-runtime/narrative-evidence/HON.json').read_bytes())
    recipe=json.loads((SOURCE/'us-refresh-runtime/recipes/HON.json').read_bytes())
    return st,n,recipe

def bind(st=None,n=None,cutoff='2026-08-14'):
    s,nn,r=inputs()
    return bind_separation_scope(separation_policy('HON'),s if st is None else st,nn if n is None else n,r,source_root=SOURCE,cutoff=cutoff)

def test_real_accounting_close_events_and_already_adjusted_shares():
    r=bind();t=r['terms']
    assert r['actual_accounting_close']=='2026-06-27'
    assert r['filing']['report_date']=='2026-06-30'
    assert t['distribution_date']==t['split_date']=='2026-06-29'
    assert t['reported_shares_already_adjusted'] is True
    assert t['reported_scope_includes_distributed_business'] is True
    assert {x['value'] for x in r['reported_pre_distribution_ledger']['reported_cover_shares']}=={316940010}
    assert {x['value'] for x in r['reported_pre_distribution_ledger']['reported_diluted_shares']}=={318600000,319000000}
    assert r['ordinary_nci_proof']['source_total']==320000000

def test_real_acquisition_and_trademark_terms_never_promote_cash_or_value():
    r=bind();t=r['terms']
    assert t['acquisition_close']=={'date':'2026-07-17','ownership_percent':100,'consideration_net_cash_acquired':1750000000}
    assert t['pending_allocation']=='2026-09-30'
    assert t['trademark_payments']['total']==1125000000
    assert t['trademark_payments']['initial']==18750000
    assert t['trademark_payments']['monthly_count']==59
    assert t['trademark_payments']['actual_cash_received'] is None
    assert t['conditional_nonrenewal_reimbursement']==50000000
    assert t['conditional_termination_reimbursement']==250000000
    for key in ('distributed_balances','continuing_parent_fcff','post_acquisition_cash_debt','acquired_fcff','synergies','claim_adjustment'):
        assert r[key] is None
    assert r['numeric_successor_issued'] is False
    assert r['historical_range_only']=={'low':60.78533467481803,'base':149.61398945604896,'high':277.0528047042256}

def test_quantinuum_is_separate_noncash_accounting_event():
    t=bind()['terms']
    assert t['ipo_cash_received']==0
    assert t['quantinuum_retained_investment']+t['quantinuum_removed_nci']-t['quantinuum_removed_net_assets']==t['quantinuum_gain']==6629000000
    assert t['quantinuum_removed_nci']==703000000

@pytest.mark.parametrize('mutation',['accession','period','cik','unit','namespace','presentation','conflict','missing'])
def test_source_mutations_fail_closed(mutation):
    st,_,_=inputs()
    row=next(r for r in st['facts'] if r.get('local_name')=='CashAndCashEquivalentsAtCarryingValue' and r['period_end']=='2026-06-30')
    if mutation=='accession':st['source_accession']='wrong'
    elif mutation=='period':st['report_date']='2026-03-31'
    elif mutation=='cik':row['entity_identifier']='1'
    elif mutation=='unit':row['unit']='shares'
    elif mutation=='namespace':row['namespace']='http://wrong.example/2026'
    elif mutation=='presentation':row['statement_roles']=[]
    elif mutation=='conflict':other=deepcopy(row);other['value']+=1;st['facts'].append(other)
    elif mutation=='missing':st['facts']=[r for r in st['facts'] if r.get('local_name')!='CashAndCashEquivalentsAtCarryingValue']
    with pytest.raises(ValueError):bind(st=st)

def test_receipt_tamper_and_post_cutoff_are_rejected():
    _,n,_=inputs();next(t for t in n['terms'] if t['name']=='reported_shares_already_adjusted')['value']=False
    with pytest.raises(ValueError):bind(n=n)
    with pytest.raises(ValueError):bind(cutoff='2026-07-01')

def test_narrative_missing_scope_or_changed_ratio_requires_review():
    _,n,_=inputs();p=SOURCE/n['source']['document_path'];a=_VisibleText();a.feed(p.read_text());text=a.text
    for old,new in [('All share and per share amounts have been retrospectively adjusted','No retrospective adjustment'),('every two shares of common stock','every three shares of common stock')]:
        with pytest.raises(ValueError):extract_separation_terms(text.replace(old,new),narrative_policy('HON'))

def test_real_two_worker_flow_retains_hon_and_hca_blockers():
    p=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),'--ticker','HON','--ticker','HCA','--max-workers','2','--source-index',str(SOURCE/'us-refresh-runtime/source-indexes/d5be9454237ce017d88950e2923206e539c063b805348b2173baa9f00ad32bfb.json')],cwd=ROOT,capture_output=True,text=True,check=True)
    report=json.loads(Path(json.loads(p.stdout.strip().splitlines()[-1])['report_path']).read_bytes())
    assert report['counts']=={'implementation_gap':2}
    rows={r['ticker']:r for r in report['rows']}
    assert rows['HON']['partial_separation_scope']['continuing_parent_fcff'] is None
    assert rows['HCA']['partial_professional_liability_annual_evidence']['claim_adjustment'] is None
