from copy import deepcopy
import json
from pathlib import Path
import sys
import pytest
from app.us_valuation.refresh_lease_capital_scope import assess_lease_capital_scope,lease_capital_policy
from app.us_valuation.refresh_narrative_evidence import validate_narrative_evidence,narrative_policy,NarrativeEvidenceError

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_wg25_lease_capital_scope import proof
INDEX=ROOT/'output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json'

def source(ticker):
    path={'INTC':'batch-26-structural-sources-20260831/INTC','JBL':'batch-28-structural-sources-20260831/JBL'}[ticker]
    st=json.loads((ROOT/'output'/path/'structural-filing.json').read_bytes())
    f={'accessionNumber':st['source_accession'],'reportDate':st['report_date'],'filingDate':st['filed_date'],'form':st['form']}
    n=json.loads((ROOT/'output/us-refresh-runtime/narrative-evidence'/f'{ticker}.json').read_bytes())
    return st,f,n

def assess(ticker,st=None,n=None):
    original,f,narrative=source(ticker)
    return assess_lease_capital_scope(lease_capital_policy(ticker),st or original,f,narrative['cik'],'2026-08-14',n or narrative)

def test_real_intc_cash_financing_noncash_and_claims_are_separate():
    r=assess('INTC')
    assert r['reported_investing_capex_cash']==6_192_000_000
    assert r['financing_extended_term_capital_cash']==1_423_000_000
    assert r['finance_lease_principal_cash']==832_000_000
    assert r['reported_noncash_extended_term_capital_amount']==626_000_000
    assert r['reported_noncash_capital_amount']==3_148_000_000
    assert r['noncash_capital_economic_scope']=='ending_obligation_and_stock_vs_flow_scope_unbound'
    assert r['reported_balance_sheet_debt_carrying_subtotal']==50_537_000_000
    assert all(v is None for v in r['current_finance_lease_carrying_facts'].values())
    assert r['claim_adjustment'] is None and r['status']=='review_required'

def test_real_jbl_new_schedule_and_combined_exclusions_are_not_current_debt():
    r=assess('JBL')
    assert r['reported_investing_capex_cash']==382_000_000
    assert r['reported_balance_sheet_debt_carrying_subtotal']==3_378_000_000
    assert r['new_only_lease_schedule']['new_finance_lease_future_payments']==51_000_000
    assert r['excluded_combined_lease_guarantee_disclosure']==80_000_000
    assert r['excluded_combined_uncommenced_payments']==181_000_000
    assert r['finance_lease_principal_cash'] is None and r['claim_adjustment'] is None

@pytest.mark.parametrize('ticker',['INTC','JBL'])
def test_missing_carrying_does_not_become_zero_and_present_flow_does_not_fill_it(ticker):
    r=assess(ticker)
    assert r['aggregate_debt_lease_overlap']=='unresolved' and not r['numeric_successor_issued']
    assert r['current_finance_lease_carrying_facts']['us-gaap:FinanceLeaseLiability'] is None

@pytest.mark.parametrize('field,value',[('unit','shares'),('value',-1),('value',float('nan')),('presentation_parents',[]),('namespace','http://wrong.org/20260627')])
def test_financing_capital_source_guards_fail_closed(field,value):
    st,_,_=source('INTC')
    for r in st['facts']:
        if r['local_name']=='PaymentsToAcquirePropertyPlantAndEquipmentFinancingActivities':r[field]=value
    with pytest.raises(ValueError,match='presentation invalid'):assess('INTC',st)

def test_conflicting_duplicate_is_not_silently_selected():
    st,_,_=source('INTC');r=deepcopy(next(r for r in st['facts'] if r['local_name']=='PaymentsToAcquirePropertyPlantAndEquipmentFinancingActivities'))
    r['value']+=1;st['facts'].append(r)
    with pytest.raises(ValueError,match='conflicting'):assess('INTC',st)

def test_noncash_purchase_window_cannot_be_combined_with_different_cash_window():
    st,_,_=source('INTC')
    for r in st['facts']:
        if r['local_name']=='CapitalExpendituresIncurredButNotYetPaidExtendedPaymentTerms':r['period_start']='2026-01-01'
    with pytest.raises(ValueError,match='windows disagree'):assess('INTC',st)

def test_multiple_duration_windows_are_not_silently_filtered():
    st,_,_=source('INTC');r=deepcopy(next(r for r in st['facts'] if r['local_name']=='FinanceLeasePrincipalPayments'))
    r.update(period_start='2026-03-29',context_id='quarter-context');st['facts'].append(r)
    with pytest.raises(ValueError,match='multiple distinct duration windows'):assess('INTC',st)

def test_reported_debt_carrying_requires_liability_presentation():
    st,_,_=source('JBL')
    for r in st['facts']:
        if r['local_name']=='LongTermDebtCurrent' and r['period_end']==st['report_date']:r['presentation_parents']=[]
    with pytest.raises(ValueError,match='presentation invalid'):assess('JBL',st)

def test_duration_payments_do_not_substitute_for_carrying_balance():
    st,_,_=source('INTC');r=deepcopy(next(r for r in st['facts'] if r['local_name']=='FinanceLeasePrincipalPayments'))
    r.update(qname='us-gaap:FinanceLeaseLiability',local_name='FinanceLeaseLiability')
    st['facts'].append(r)
    assert assess('INTC',st)['current_finance_lease_carrying_facts']['us-gaap:FinanceLeaseLiability'] is None

def test_narrative_changes_and_superseded_evidence_fail_closed():
    _,_,n=source('JBL');n['terms'][0]['value']='full_current_debt'
    with pytest.raises(NarrativeEvidenceError,match='receipt hash'):assess('JBL',n=n)
    st,_,_=source('JBL');st['filing_metadata']=[(k,'different' if k=='package_generation' else v) for k,v in st['filing_metadata']]
    with pytest.raises(ValueError,match='package disagree'):assess('JBL',st)

def test_real_cached_replay_preserves_all_legacy_adjustments():
    p=proof(ROOT/'output/us-refresh-runtime',INDEX)
    for row in p['rows']:
        assert row['previous_range']==row['retained_recipe_range']
        assert row['official_value_changes']=={'low':0.,'base':0.,'high':0.}
        assert not row['numeric_successor_issued']

def test_real_frozen_workers_reach_financial_review_not_source_root_failure():
    import subprocess
    completed=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),
        '--runtime-root',str(ROOT/'output/us-refresh-runtime'),'--output-root',str(ROOT/'output/us-refresh-group-verification'),
        '--source-index',str(INDEX),'--ticker','INTC','--ticker','JBL','--max-workers','2'],
        cwd=ROOT,text=True,capture_output=True,check=True)
    summary=json.loads(completed.stdout.strip().splitlines()[-1])
    report=json.loads(Path(summary['report_path']).read_bytes())
    assert summary['worker_count']==2
    for row in report['rows']:
        assert row['status']=='source_or_economic_review'
        assert 'complete_current_finance_lease_carrying_and_aggregate_debt_overlap_unbound' in row['reason']
        assert 'outside the allowed source root' not in row['reason']
