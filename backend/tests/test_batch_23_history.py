from pathlib import Path
import json,sys,pytest
from app.us_valuation.batch_23 import BATCH_23_MANIFEST,BATCH_23_TICKERS
from app.us_valuation.batch_23_history import PASS_TICKERS,CONDITIONAL_TICKERS,P,build_batch_23_history_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-23-sec-source-packets-20260831';STRUCT=ROOT/'output/batch-23-structural-sources-20260831'
def R(t):return build_batch_23_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCT)
EXPECTED={'AME':(48.45014916948007,104.52681204113686,173.27654805084276),'CHRW':(14.798420399149066,47.48124838589168,113.03694451238101),'FDX':(77.03464011602604,129.24145610107348,216.2202882010991),'PWR':(64.78810145210886,163.70936634287673,289.3670372535367),'RSG':(37.797779924407266,82.80880861875114,158.6435316486605),'URI':(0.,52.305663659063995,177.33853508867068),'AXON':(14.565501601258148,48.3228234917257,140.53384274513604),'LII':(95.15791967587914,209.6046488513602,379.7750837685485),'UPS':(30.350610895864627,61.37112889336235,124.61938641091136),'LDOS':(49.28415144084905,116.72141537538658,236.15171584384663)}
def test_outcomes_ranges():
 rows={t:R(t) for t in BATCH_23_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(PASS_TICKERS);assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(CONDITIONAL_TICKERS)
 for t,r in rows.items():v=tuple(r['scenario_range'][k] for k in ('low','base','high'));assert v==pytest.approx(EXPECTED[t]);assert 0<=v[0]<=v[1]<=v[2] and v[1]>0;assert r['history_reliability']['label']=='Low'
def test_special_sources_and_no_zero_substitution():
 uri=R('URI');assert uri['reported_inputs']['ttm_reinvestment']==4.712e9;assert uri['governed_assumptions']['current_reinvestment_basis']=='bounded nonzero fleet-capex bridge';assert uri['scenario_rows'][0]['raw_value_per_share']<0 and uri['scenario_range']['low']==0
 assert R('FDX')['source_ledger']['event_sources'][1]['value']==771e6;assert R('FDX')['source_ledger']['event_sources'][2]['value']==2.5e9
 assert R('AXON')['source_ledger']['event_sources'][2]['value']==3_016_680.;assert R('UPS')['source_ledger']['bridge_sources'][-2]['value']==850_781_582.;assert R('UPS')['source_ledger']['event_sources'][1]['value']==933e6
 assert R('AME')['reported_inputs']['valuation_revenue']==8.963923e9;assert R('AME')['scenario_rows'][1]['other_equity_claims']==5e9;assert R('AME')['source_ledger']['event_sources'][2]['value']==5e9
 assert [x['other_equity_claims'] for x in R('CHRW')['scenario_rows']]==[449e6,224.5e6,0.];assert R('CHRW')['source_ledger']['event_sources'][2]['value']==604e6
 assert R('AXON')['scenario_rows'][1]['cash_and_investments']==692.533e6
def test_bridges_and_directions():
 assert R('PWR')['scenario_rows'][1]['other_equity_claims']==104.001e6;assert R('RSG')['scenario_rows'][1]['debt_and_finance_leases']==14.205e9;assert R('LDOS')['scenario_rows'][1]['other_equity_claims']==52e6
 for t in P:
  a=R(t)['scenario_rows'];assert a[0]['wacc']>a[1]['wacc']>a[2]['wacc'];assert a[0]['growth']<=a[1]['growth']<=a[2]['growth'];assert a[0]['conditional_value_per_share']<=a[1]['conditional_value_per_share']<=a[2]['conditional_value_per_share']
def test_independent_arithmetic_and_cutoff():
 for t in BATCH_23_TICKERS:
  r=R(t);f=r['source_ledger']['controlling_filing'];assert f['filed']<='2026-08-14' and f['period_end']==P[t].period
  for x in r['scenario_rows']:
   cash=x['starting_cash_fcff'];pv=0.
   for year in range(1,9):fade=(8-year)/7;g=x['terminal_growth']+(x['growth']-x['terminal_growth'])*fade;cash*=1+g;pv+=cash/(1+x['wacc'])**year
   ev=pv+(cash*(1+x['terminal_growth'])/(x['wacc']-x['terminal_growth']))/(1+x['wacc'])**8;raw=(ev+x['cash_and_investments']-x['debt_and_finance_leases']-x['other_equity_claims'])/x['shares'];assert raw==pytest.approx(x['raw_value_per_share']);assert max(0,raw)==pytest.approx(x['conditional_value_per_share'])
def test_public_and_calculator():
 from run_batch_23_history import _public
 for i in BATCH_23_MANIFEST:
  r=R(i.ticker);p=_public(i,r);raw=json.dumps(p);assert p['availability_type']==r['availability_type'] and p['scenario_range']['base']==r['scenario_range']['base'];assert all(k not in raw for k in ('source_ledger','model_trace','reported_inputs','annual_cash_sources'));assert calculator_view(p)['model_family']=='operating';assert calculate(p,overrides={},manual_price=None)['result']==r['scenario_range']
def test_runner_preserves(tmp_path):
 from run_batch_23_history import run
 r=run(source_root=SOURCE,structural_root=STRUCT,output_root=tmp_path/'x');assert (r['attempted_count'],r['pass_count'],r['conditional_count'],r['withheld_count'],r['numeric_count'])==(10,2,8,0,10);assert r['pass_tickers']==['RSG','LII'];assert r['conditional_tickers']==['AME','CHRW','FDX','PWR','URI','AXON','UPS','LDOS'];assert not r['serving_artifacts_changed'] and not r['watchlist_changed'] and not r['withheld_register_changed']
def test_arelle_outside_serving():
 for p in [ROOT/'backend/app/main.py',ROOT/'backend/app/deps.py',*sorted((ROOT/'backend/app/routers').glob('*.py'))]:assert 'arelle' not in p.read_text().lower()
