from pathlib import Path
import json,sys,pytest
from app.us_valuation.batch_26 import BATCH_26_MANIFEST,BATCH_26_TICKERS
from app.us_valuation.batch_26_history import PASS_TICKERS,CONDITIONAL_TICKERS,WITHHELD_TICKERS,build_batch_26_history_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-26-sec-source-packets-20260831';STRUCT=ROOT/'output/batch-26-structural-sources-20260831'
def R(t):return build_batch_26_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCT)
EXPECTED={'AMD':(28.394635147594368,58.21275752698704,103.94954962691004),'SWKS':(34.85376427199426,61.533740860342874,134.61460404141968),'ADI':(65.38823831965416,118.5553871412836,198.53754985614276),'AMAT':(68.168681304851,115.03957682409067,213.99720393525638),'GLW':(3.350978640724463,15.157336392596388,31.59951088000838),'HPQ':(23.949858905877,39.178510213093006,59.692103743238654),'INTC':(0.,3.001327108470505,16.50488639459598),'IBM':(39.393309229911075,86.9433313401928,176.95652347564453),'MSI':(87.73920019271736,184.8209398809354,328.8075107338896),'APH':(16.462854421964604,39.56308563211693,70.84184345801795)}
def test_outcomes_ranges_and_denominator():
 rows={t:R(t) for t in BATCH_26_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(PASS_TICKERS)=={'SWKS','ADI','AMAT','GLW','HPQ','MSI'};assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(CONDITIONAL_TICKERS)=={'AMD','INTC','IBM','APH'};assert set(WITHHELD_TICKERS)==set()
 for t,v in EXPECTED.items():assert tuple(rows[t]['scenario_range'][k] for k in ('low','base','high'))==pytest.approx(v)
 assert len(rows)==10 and all(r['scenario_range']['base']>0 for r in rows.values())
def test_glw_structural_capex_and_warrant_bridge():
 r=R('GLW');assert r['reported_inputs']['ttm_reinvestment']==1.520e9;assert r['reported_inputs']['ttm_operating_cash_flow']==3.915e9;assert r['source_ledger']['flow_sources']['capital_expenditures']['method']=='latest_fy_plus_structural_current_ytd_minus_prior_ytd';assert r['source_ledger']['bridge_reconciliation']['other_equity_claims']==723e6;assert r['governed_assumptions']['shares'][0]==879_388_331.
def test_intc_transformation_is_finite_and_floor_is_not_missing_zero():
 r=R('INTC');assert r['governed_assumptions']['cash_conversion_margin']==(.03,.07,.12);assert r['governed_assumptions']['growth']==(-.03,.02,.06);assert r['scenario_rows'][0]['raw_value_per_share']<0 and r['scenario_range']['low']==0 and r['scenario_rows'][0]['limited_liability_floor_applied'];assert r['scenario_range']['base']>0
def test_event_and_cash_scope_controls():
 amd=R('AMD');assert amd['reported_inputs']['ttm_cash_fcff']==pytest.approx(amd['reported_inputs']['ttm_operating_cash_flow']-amd['reported_inputs']['ttm_reinvestment']+amd['reported_inputs']['ttm_interest']*(1-amd['reported_inputs']['tax_rate']));assert any(row.get('value')==1.4e9 for row in amd['source_ledger']['event_sources']);assert any(row.get('value')==4.409e9 for row in amd['source_ledger']['event_sources']);assert any(row.get('reported_terms',{}).get('current_claim_usd')==0 for row in amd['source_ledger']['event_sources']);assert amd['source_ledger']['tax_rate_treatment']['fallback_applied'] is True
 hpq=R('HPQ');assert hpq['source_ledger']['event_sources'][1]['value']==9.1e9 and hpq['source_ledger']['bridge_reconciliation']['other_equity_claims']==0
 aph=R('APH');assert aph['source_ledger']['event_sources'][1]['value']==10.684e9 and aph['source_ledger']['bridge_reconciliation']['other_equity_claims']==130.5e6
 glw=R('GLW');assert any(row.get('value')==796e6 for row in glw['source_ledger']['event_sources']);assert any(row.get('value')==180 for row in glw['source_ledger']['event_sources'])
def test_ibm_equity_route_avoids_finance_debt_double_count():
 r=R('IBM');assert r['governed_assumptions']['ev_debt_bridge_applied'] is False;assert r['reported_inputs']['ttm_common_earnings']==10.725e9;assert r['reported_inputs']['ttm_common_dividends']==6.309e9;assert len(r['source_ledger']['ttm_dividend_sources'])==3;assert 'not EV-bridged' in r['source_ledger']['bridge_treatment']
def test_public_and_calculator_safety():
 from run_batch_26_history import _public
 for i in BATCH_26_MANIFEST:
  r=R(i.ticker);p=_public(i,r);raw=json.dumps(p);assert 'source_ledger' not in raw and 'reported_inputs' not in raw and p['availability_type']==r['availability_type'];view=calculator_view(p);assert view['can_calculate'] and view['model_family']==('equity_earnings' if i.ticker=='IBM' else 'operating');assert calculate(p,overrides={},manual_price=None)['result']==r['scenario_range']
def test_runner_preserves_protected_and_bookkeeping(tmp_path):
 from run_batch_26_history import run
 r=run(source_root=SOURCE,structural_root=STRUCT,output_root=tmp_path/'x');assert (r['pass_count'],r['conditional_count'],r['withheld_count'],r['numeric_count'])==(6,4,0,10);assert not r['serving_artifacts_changed'] and not r['watchlist_changed'] and not r['withheld_register_changed']
def test_arelle_outside_serving_process():
 for p in [ROOT/'backend/app/main.py',ROOT/'backend/app/deps.py',*sorted((ROOT/'backend/app/routers').glob('*.py'))]:assert 'arelle' not in p.read_text().lower()
