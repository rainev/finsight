from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from app.us_valuation.refresh_settlement_payment_bridge import settlement_payment_policy,bind_settlement_payment_bridge,reconcile_payment_only
from app.us_valuation.calculation_recipe import evaluate_scenario

ROOT=Path(__file__).resolve().parents[2]
def source():return json.loads((ROOT/'output/batch-14-structural-sources-resume-20260829/MCK/structural-filing.json').read_bytes())
def bind(st=None):
    return bind_settlement_payment_bridge(settlement_payment_policy('MCK'),st if st is not None else source(),
        json.loads((ROOT/'output/us-refresh-runtime/narrative-evidence/MCK.json').read_bytes()),
        cutoff='2026-08-14',source_root=ROOT/'output')

def test_real_payment_moves_cash_and_claim_once_not_actual_closing_balances():
    r=bind();b=r['payment_only_bridge']
    assert b['cash_after_payment_only_not_closing_balance']==4_668_000_000
    assert b['liability_after_payment_only_not_closing_balance']==5_164_000_000
    assert b['payment_only_net_cash_minus_claim_change']==0
    assert b['actual_post_period_cash'] is None and b['actual_post_period_liability'] is None
    assert b['claim_adjustment'] is None and not r['numeric_successor_issued']
    assert r['ownership_carrying_proof']['source_total']==2_939_000_000
    assert r['sources']['reported_period_payment']['value']==0

def test_aggregate_parts_aliases_and_historical_maxima_are_nonadditive():
    st=source();st['facts'].extend(deepcopy(st['facts']))
    r=bind(st)
    assert r['sources']['liabilities']['LossContingencyAccrualAtCarryingValue']['value']==5_660_000_000
    assert r['sources']['subsequent_payment']['value']==496_000_000
    assert r['ownership_carrying_proof']['source_total']==2_939_000_000

@pytest.mark.parametrize('mutation',['missing','namespace','member','extra_axis','parent','negative','conflict','date','zero_duration','zero_missing','part'])
def test_source_scope_unknowns_conflicts_dates_and_wrong_program_fail_closed(mutation):
    st=source();row=next(r for r in st['facts'] if r['local_name']=='PaymentsForLegalSettlements' and r['period_end']=='2026-07-31')
    if mutation=='missing':st['facts'].remove(row)
    elif mutation=='namespace':row['namespace']='http://wrong.example/2026'
    elif mutation=='member':row['dimensions'][0][1]='wrong:OtherLitigationMember'
    elif mutation=='extra_axis':row['dimensions'].append(['us-gaap:OtherAxis','us-gaap:OtherMember'])
    elif mutation=='parent':row['presentation_parents']=[]
    elif mutation=='negative':row['value']=-1
    elif mutation=='conflict':
        other=deepcopy(row);other['value']+=1;st['facts'].append(other)
    elif mutation=='date':row['period_start']='2026-07-20'
    elif mutation=='part':
        next(r for r in st['facts'] if r['local_name']=='LossContingencyAccrualCarryingValueCurrent' and r['period_end']=='2026-06-30')['value']+=1
    else:
        zero=next(r for r in st['facts'] if r['local_name']=='PaymentsForLegalSettlements' and r['value']==0)
        if mutation=='zero_missing':st['facts'].remove(zero)
        else:zero['period_start']='2025-04-01'
    with pytest.raises(ValueError):bind(st)

@pytest.mark.parametrize('values',[(1,2,3),(-1,2,0),(True,2,0),(1,float('nan'),0)])
def test_payment_needs_bounded_nonnegative_cash_and_liability(values):
    with pytest.raises(ValueError):reconcile_payment_only(cash=values[0],liability=values[1],payment=values[2])

def test_real_frozen_workers_execute_payment_ledger_preserve_lhx_and_full_gaps():
    p=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),'--ticker','MCK','--ticker','LHX','--max-workers','2',
        '--source-index',str(ROOT/'output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json')],cwd=ROOT,check=True,capture_output=True,text=True)
    summary=json.loads(p.stdout.strip().splitlines()[-1]);report=json.loads(Path(summary['report_path']).read_bytes())
    mck=next(r for r in report['rows'] if r['ticker']=='MCK')
    assert mck['status']=='implementation_gap'
    assert mck['partial_settlement_payment_bridge']['payment_only_bridge']['claim_adjustment'] is None
    lhx=next(r for r in report['rows'] if r['ticker']=='LHX')
    assert lhx['status']=='implementation_gap' and 'partial_environmental_annual_evidence' in lhx

@pytest.mark.parametrize('case',['bear','base','bull'])
def test_independent_engine_payment_pair_preserves_claims_and_scenario_value(case):
    recipe=json.loads((ROOT/'output/us-refresh-runtime/recipes/MCK.json').read_bytes())
    after=recipe['scenarios'][case];before=deepcopy(after)
    payment=bind()['sources']['subsequent_payment']['value']
    # Synthetic inverse move over the retained recipe is a calculator identity,
    # not newly reported balances or economic approval for the historical claims.
    before['inputs']['cash_and_investments']+=payment
    before['inputs']['preferred_equity']+=payment
    assert evaluate_scenario(before)['value']==pytest.approx(evaluate_scenario(after)['value'],abs=1e-10,rel=0)
    assert before['inputs']['noncontrolling_interests']==after['inputs']['noncontrolling_interests']

@pytest.mark.parametrize('start',['2026-04-02','2026-04-10','2026-03-31'])
def test_nearby_quarter_dates_cannot_replace_exact_reported_interval(start):
    st=source();zero=next(r for r in st['facts'] if r['local_name']=='PaymentsForLegalSettlements' and r['value']==0)
    zero['period_start']=start
    with pytest.raises(ValueError,match='independently reported quarter'):bind(st)
