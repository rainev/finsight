from pathlib import Path
import json,sys,pytest
from app.us_valuation.batch_27 import BATCH_27_MANIFEST,BATCH_27_TICKERS
from app.us_valuation.batch_27_history import PASS_TICKERS,CONDITIONAL_TICKERS,WITHHELD_TICKERS,build_batch_27_history_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-27-sec-source-packets-20260831';STRUCT=ROOT/'output/batch-27-structural-sources-20260831'
def R(t):return build_batch_27_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCT)
EXPECTED={'TER':(29.81404979272275,48.45802724130545,97.31977071626021),'TXN':(12.698111539601836,55.44244751719114,124.01112146977795),'KLAC':(23.873187389088603,45.277494624239104,73.54943131657231),'LRCX':(34.74939266450888,74.67811563525086,121.46767252939418),'MU':(29.184776884128944,80.97342603334381,153.48739296062772),'IT':(150.05807058714464,269.069190053228,480.66323722289894),'ADSK':(95.4508471936645,192.9716340288016,296.62810404946487),'ADBE':(245.54136803150874,421.39712467710694,612.369027501367),'COHR':(0.,16.788931960143348,41.7124972189867),'FLEX':(12.745681439545978,29.834516172489618,55.82645463276654)}
def test_outcomes_ranges_and_denominator():
 rows={t:R(t) for t in BATCH_27_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(PASS_TICKERS)=={'TER','TXN','LRCX','MU','IT','ADSK'};assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(CONDITIONAL_TICKERS)=={'KLAC','ADBE','COHR','FLEX'};assert not WITHHELD_TICKERS
 for t,v in EXPECTED.items():assert tuple(rows[t]['scenario_range'][k] for k in ('low','base','high'))==pytest.approx(v)
 assert len(rows)==10 and all(r['scenario_range']['base']>0 for r in rows.values())
def test_narrow_alias_and_bridge_repairs():
 txn=R('TXN');assert {s['concept'] for s in txn['source_ledger']['flow_sources']['interest_expense']['sources']}=={'InterestAndDebtExpense'};assert txn['source_ledger']['bridge_reconciliation']['cash_and_investments']==7.016e9
 it=R('IT');assert {s['concept'] for s in it['source_ledger']['flow_sources']['capital_expenditures']['sources']}=={'PaymentsForCapitalImprovements'};assert it['reported_inputs']['ttm_reinvestment']==93_671_000.
 cohr=R('COHR');assert {s['concept'] for s in cohr['source_ledger']['flow_sources']['interest_expense']['sources']}=={'InterestExpenseOperating'};assert cohr['reported_inputs']['ttm_cash_fcff']<0 and cohr['scenario_range']['base']>0
def test_cycle_and_share_controls():
 klac=R('KLAC');assert klac['governed_assumptions']['shares'][1]>1.3e9;assert klac['governed_assumptions']['commitment_payment_years']==(3,5,8);assert klac['governed_assumptions']['commitment_annual_cash_reserve']==(1.990e9,1.194e9,746.25e6);assert klac['scenario_rows'][1]['commitment_present_value_reserve']==pytest.approx(sum(1.194e9/(1.09**year) for year in range(1,6)))
 mu=R('MU');assert mu['governed_assumptions']['cash_conversion_margin'][1]<mu['reported_inputs']['ttm_cash_fcff']/mu['reported_inputs']['ttm_revenue'];assert mu['source_ledger']['bridge_reconciliation']['debt_and_finance_leases']==5.722e9;assert mu['source_ledger']['bridge_reconciliation']['other_equity_claims']==(6.914e9,)*3
 ter=R('TER');assert ter['source_ledger']['bridge_reconciliation']['cash_and_investments']==517.103e6 and ter['source_ledger']['bridge_reconciliation']['debt_and_finance_leases']==0;assert any(x.get('reported_vs_estimated')=='source_proven_absent' for x in ter['source_ledger']['bridge_sources'])
 ads=R('ADSK');assert ads['source_ledger']['bridge_reconciliation']['cash_and_investments']==3.309e9
def test_material_events_and_current_claims():
 adbe=R('ADBE');assert any(x.get('value')==1.56e9 for x in adbe['source_ledger']['event_sources'])
 cohr=R('COHR');assert any(x.get('value')==2.506885e9 for x in cohr['source_ledger']['event_sources']);assert any(x.get('value')==12.419e6 for x in cohr['source_ledger']['event_sources']);assert cohr['source_ledger']['bridge_reconciliation']['other_equity_claims'][0]>334.705e6;assert cohr['scenario_rows'][0]['raw_value_per_share']<0 and cohr['scenario_range']['low']==0
 flex=R('FLEX');assert any(x.get('value')==1.134e9 for x in flex['source_ledger']['event_sources']) and flex['source_ledger']['bridge_reconciliation']['debt_and_finance_leases']==5.240e9
def test_dcf_replay_and_sensitivity_directions():
 from app.us_valuation.practical_models import EnterpriseCashFlowState,enterprise_cash_flow_dcf
 for t in BATCH_27_TICKERS:
  r=R(t)
  for row in r['scenario_rows']:
   s=EnterpriseCashFlowState(row['starting_cash_fcff'],row['growth'],row['terminal_growth'],row['wacc'],row['cash_and_investments'],row['debt_and_finance_leases'],0,row['other_equity_claims'],row['shares']);raw=float(enterprise_cash_flow_dcf(s,forecast_years=8,allow_nonpositive_equity_trace=True)['intrinsic_value_per_share']);assert raw==pytest.approx(row['raw_value_per_share'])
def test_public_and_calculator_safety():
 from run_batch_27_history import _public
 for i in BATCH_27_MANIFEST:
  r=R(i.ticker);p=_public(i,r);raw=json.dumps(p);assert 'source_ledger' not in raw and 'reported_inputs' not in raw and p['availability_type']==r['availability_type'];view=calculator_view(p);assert view['can_calculate'] and view['model_family']=='operating';assert calculate(p,overrides={},manual_price=None)['result']==r['scenario_range']
def test_runner_preserves_protected_and_bookkeeping(tmp_path):
 from run_batch_27_history import run
 r=run(source_root=SOURCE,structural_root=STRUCT,output_root=tmp_path/'x');assert (r['pass_count'],r['conditional_count'],r['withheld_count'],r['numeric_count'])==(6,4,0,10);assert not r['serving_artifacts_changed'] and not r['watchlist_changed'] and not r['withheld_register_changed']
def test_arelle_outside_serving_process():
 for p in [ROOT/'backend/app/main.py',ROOT/'backend/app/deps.py',*sorted((ROOT/'backend/app/routers').glob('*.py'))]:assert 'arelle' not in p.read_text().lower()
