from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from app.us_valuation.refresh_subsidiary_preferred_bridge import bind_subsidiary_preferred_bridge,subsidiary_preferred_policy,claim_basis_diagnostic
from app.us_valuation.refresh_narrative_evidence import narrative_policy,validate_narrative_evidence,NarrativeEvidenceError
ROOT=Path(__file__).resolve().parents[2]
INDEX=ROOT/'output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json'
def inputs():
    return (json.loads((ROOT/'output/batch-21-structural-sources-20260831/LHX/structural-filing.json').read_bytes()),
        json.loads((ROOT/'output/us-refresh-runtime/narrative-evidence/LHX.json').read_bytes()))
def bind(st=None,n=None):
    original,narrative=inputs()
    return bind_subsidiary_preferred_bridge(subsidiary_preferred_policy('LHX'),st or original,n or narrative,
        cutoff='2026-08-14',source_root=ROOT/'output')

def test_real_financing_allocation_and_host_rollforward_are_not_economic_value():
    r=bind();t=r['terms']
    assert t['initial_host']+t['initial_feature']+t['initial_warrant']==t['gross_cash']+t['program_asset']==1_386_000_000
    assert t['initial_host']-t['deferred_tax']-t['transaction_costs']+t['deemed_dividend']==r['current_host_carrying']==968_000_000
    assert t['net_cash']==973_000_000 and t['program_asset']==386_000_000
    assert t['amortization_years']==20
    assert r['claim_basis']['reported_accounting_exposure']==1_284_000_000
    assert r['claim_basis']['economic_claim_value'] is None and not r['numeric_successor_issued']
    assert r['parent_as_converted_shares'] is None
    assert r['reported_period_end_parent_shares']==186_155_804

def test_future_dates_and_exclusive_outcomes_are_preserved_without_invented_payoff():
    t=bind()['terms']
    assert t['exclusive_outcomes'] and t['not_currently_redeemable']
    assert t['qipo_deadline']=='2027-12-31'
    assert t['nonipo_reference_date']=='2031-04-17' and t['valuation_not_before']=='2031-04-16'
    assert t['dividend_rate']==.07 and t['conversion_discount']==.20 and t['warrant_fraction']==.03

@pytest.mark.parametrize('basis',['cash_settlement','conversion_dilution'])
def test_full_settlement_or_dilution_cannot_also_deduct_host_features(basis):
    with pytest.raises(ValueError,match='cannot also deduct'):
        claim_basis_diagnostic(basis,host=968_000_000,feature=130_000_000,warrant=186_000_000)

def test_cash_and_dilution_cannot_both_enter_a_claim_basis():
    with pytest.raises(ValueError,match='mutually exclusive'):
        claim_basis_diagnostic('cash_settlement',host=0.,feature=0.,warrant=186_000_000,cash_claim=1_422_000_000,converted_shares=10.)

@pytest.mark.parametrize('quantity',[0.,-1.,float('nan'),float('inf')])
def test_missing_or_invalid_alternative_quantities_are_not_zero_claims(quantity):
    with pytest.raises(ValueError,match='positive finite'):
        claim_basis_diagnostic('cash_settlement',host=0.,feature=0.,warrant=186_000_000,cash_claim=quantity)

def test_valid_placeholder_alternative_is_still_unapproved_not_a_new_estimate():
    r=claim_basis_diagnostic('cash_settlement',host=0.,feature=0.,warrant=186_000_000,cash_claim=1_422_000_000)
    assert not r['numeric_valuation_approved'] and r['economic_claim_value'] is None

def test_only_current_derivatives_are_selected_not_initial_or_duplicates():
    st,_=inputs();st['facts'].extend(deepcopy(st['facts']));r=bind(st)
    assert r['current_feature_liability']==130_000_000 and r['current_warrant_liability']==186_000_000
    assert all(x['period_end']=='2026-07-03' for x in r['current_derivative_sources'])

@pytest.mark.parametrize('mutation',['missing','wrong_dimension','wrong_parent','conflict'])
def test_derivative_scope_failures_do_not_invent_zero_or_ignore_claim(mutation):
    st,_=inputs();rows=[r for r in st['facts'] if r['qname']=='us-gaap:DerivativeLiabilitiesNoncurrent' and r['period_end']=='2026-07-03']
    if mutation=='missing':st['facts']=[r for r in st['facts'] if r not in rows]
    elif mutation=='conflict':
        r=deepcopy(rows[0]);r['value']+=1;st['facts'].append(r)
    elif mutation=='wrong_dimension':rows[0]['dimensions'].append(['us-gaap:StatementBusinessSegmentsAxis','unrelated:Member'])
    else:rows[0]['presentation_parents']=[]
    with pytest.raises(ValueError,match='derivative'):bind(st)

def test_stale_or_tampered_narrative_cannot_bind_current_bridge():
    _,n=inputs();n['terms'][0]['value']=False
    with pytest.raises(NarrativeEvidenceError,match='receipt hash'):bind(n=n)

def test_different_source_package_cannot_be_joined_even_with_same_filing_dates():
    st,_=inputs();st['filing_metadata']=[(k,'other' if k=='package_generation' else v) for k,v in st['filing_metadata']]
    with pytest.raises(ValueError,match='packages disagree'):bind(st)

def test_real_frozen_group_executes_ledger_and_preserves_full_model_gaps():
    p=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),'--ticker','LHX','--ticker','MCK',
        '--max-workers','2','--source-index',str(INDEX)],cwd=ROOT,check=True,capture_output=True,text=True)
    summary=json.loads(p.stdout.strip().splitlines()[-1]);report=json.loads(Path(summary['report_path']).read_bytes())
    lhx=next(r for r in report['rows'] if r['ticker']=='LHX')
    assert lhx['status']=='implementation_gap'
    assert lhx['partial_subsidiary_preferred_bridge']['status']=='accounting_reconciled_economic_review'
    assert lhx['partial_subsidiary_preferred_bridge']['claim_basis']['economic_claim_value'] is None
    assert not lhx['partial_subsidiary_preferred_bridge']['numeric_successor_issued']
    assert next(r for r in report['rows'] if r['ticker']=='MCK')['status']=='implementation_gap'
