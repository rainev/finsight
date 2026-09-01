from __future__ import annotations
import json,sys
from pathlib import Path
import pytest
from app.us_valuation.batch_18 import BATCH_18_MANIFEST,BATCH_18_TICKERS
from app.us_valuation.batch_18_history import CONDITIONAL_TICKERS,PASS_TICKERS,P,build_batch_18_history_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-18-sec-source-packets-20260830';STRUCTURAL=ROOT/'output/batch-18-structural-sources-20260830';EVENT=ROOT/'output/batch-18-event-sources-20260830'
def _result(t):return build_batch_18_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCTURAL,event_root=EVENT)
EXPECTED={'HWM':(21.309407769777962,46.97971269414414,93.61612744421485),'ADP':(133.14906942972547,217.04972359971458,303.2220725897557),'BA':(0.,4.039475664565482,60.95483472313898),'CAT':(59.983247289782966,159.69657342768494,334.6347927700216),'CMI':(65.62106314103318,235.41395352983125,444.9462166832929),'DAL':(10.5928843632608,55.571848330920545,92.2974227619365),'DOV':(63.881665069820805,101.42695915123933,157.86702955732756),'EMR':(35.651011717488295,71.97761684234388,122.39998501669199),'EFX':(32.15613793652338,105.540446687529,171.05579474936857),'GD':(172.32570927395253,318.80176892579544,457.60852324531305)}
def test_batch_18_exact_outcomes_ranges_and_reliability():
 rows={t:_result(t) for t in BATCH_18_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(PASS_TICKERS)=={'HWM','ADP','DOV','EFX','GD'};assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(CONDITIONAL_TICKERS)=={'BA','CAT','CMI','DAL','EMR'}
 for t,r in rows.items():
  vals=tuple(r['scenario_range'][k] for k in ('low','base','high'));assert vals==pytest.approx(EXPECTED[t]);assert 0<=vals[0]<=vals[1]<=vals[2] and vals[1]>0;assert r['history_reliability']['label'] in {'Low','Medium'}
 assert _result('ADP')['history_reliability']['label']=='Medium';assert all(_result(t)['history_reliability']['label']=='Low' for t in set(BATCH_18_TICKERS)-{'ADP'})
def test_operating_directions_and_boeing_floor():
 for t in P:
  states=_result(t)['scenario_rows'];assert states[0]['wacc']>states[1]['wacc']>states[2]['wacc'];assert states[0]['growth']<=states[1]['growth']<=states[2]['growth'];assert states[0]['conditional_value_per_share']<=states[1]['conditional_value_per_share']<=states[2]['conditional_value_per_share']
 ba=_result('BA');assert ba['scenario_rows'][0]['raw_value_per_share']<0 and ba['scenario_range']['low']==0;assert ba['scenario_range']['base']>0;assert ba['governed_assumptions']['cash_conversion_margin'][1]==pytest.approx((.012341925719204876+.05340550544484998)/2)
def test_client_funds_finance_and_events_are_bound_once():
 adp=_result('ADP');assert adp['scenario_rows'][1]['other_equity_claims']==475_700_000.;assert 'client funds are not treated as issuer-owned cash' in adp['source_ledger']['bridge_reconciliation']['other_equity_claim_formula']
 cat=_result('CAT');assert cat['governed_assumptions']['route_is_equity_level'] is True and cat['governed_assumptions']['ev_debt_bridge_applied'] is False
 efx=_result('EFX');assert efx['scenario_rows'][1]['cash_and_investments']==1_160_600_000.;assert efx['scenario_rows'][1]['debt_and_finance_leases']==6_485_300_000.;assert efx['source_ledger']['event_sources'][1]['reported_terms']['aggregate_principal_usd']==1_000_000_000.
 gd=_result('GD');assert gd['source_ledger']['event_sources'][1]['reported_terms']['maximum_rescission_shares']==1_010_925.
def test_recorded_claims_and_scoped_concepts():
 assert _result('BA')['scenario_rows'][1]['other_equity_claims']==1_130_000_000.;assert _result('CMI')['scenario_rows'][1]['other_equity_claims']==1_109_000_000.;assert _result('EFX')['scenario_rows'][1]['other_equity_claims']==139_700_000.
 assert {x['concept'] for x in _result('ADP')['source_ledger']['flow_sources']['capital_expenditures']['sources']}=={'PaymentsToAcquireOtherPropertyPlantAndEquipment'}
 assert {x['concept'] for x in _result('BA')['source_ledger']['flow_sources']['interest_expense']['sources']}=={'InterestAndDebtExpense'}
 assert {x['concept'] for x in _result('GD')['source_ledger']['flow_sources']['interest_expense']['sources']}=={'InterestExpenseOperating'}
def test_public_contract_safe_and_calculator_family():
 from run_batch_18_history import _public
 for issuer in BATCH_18_MANIFEST:
  r=_result(issuer.ticker);p=_public(issuer,r);raw=json.dumps(p);assert p['availability_type']==r['availability_type'] and p['scenario_range']['base']==r['scenario_range']['base'];assert all(k not in raw for k in ('source_ledger','model_trace','reported_inputs'));view=calculator_view(p);assert view['model_family']==('equity_earnings' if issuer.ticker=='CAT' else 'operating');assert calculate(p,overrides={},manual_price=None)['result']==r['scenario_range']
def test_runner_preserves_serving_and_bookkeeping(tmp_path):
 from run_batch_18_history import run
 report=run(source_root=SOURCE,structural_root=STRUCTURAL,event_root=EVENT,output_root=tmp_path/'b18');assert (report['pass_count'],report['conditional_count'],report['withheld_count'],report['numeric_count'])==(5,5,0,10);assert report['serving_artifacts_changed'] is False and report['watchlist_changed'] is False and report['withheld_register_changed'] is False
def test_arelle_outside_serving_imports():
 for p in [ROOT/'backend/app/main.py',ROOT/'backend/app/deps.py',*sorted((ROOT/'backend/app/routers').glob('*.py'))]:assert 'arelle' not in p.read_text().lower()
