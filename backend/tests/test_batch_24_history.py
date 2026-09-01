from pathlib import Path
import json,sys,pytest
from app.us_valuation.batch_24 import BATCH_24_MANIFEST,BATCH_24_TICKERS
from app.us_valuation.batch_24_history import PASS_TICKERS,CONDITIONAL_TICKERS,P,build_batch_24_history_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-24-sec-source-packets-20260831';STRUCT=ROOT/'output/batch-24-structural-sources-20260831'
def R(t):return build_batch_24_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCT)
EXPECTED={'NOC':(88.04214304931043,212.12894583631672,410.16789264750224),'TDG':(0.,285.06252027804044,729.4960847584991),'BLDR':(21.781785084149906,72.40667125273195,181.61927313845578),'TT':(98.97947940007514,200.69091592978498,347.78655928213783),'GNRC':(25.427398964060263,63.45759813781495,127.38502328926283),'HII':(0.,137.6861080081588,270.41902173472135),'XYL':(21.792671758837933,46.83099701332002,85.60971873338417),'UBER':(4.703856116276312,48.21775204041888,108.24779554442452),'ETN':(42.44055247200447,104.59308008804425,193.4932476286916),'ALLE':(62.13155416689109,113.44553498770335,182.5436709024724)}
def test_outcomes_ranges():
 rows={t:R(t) for t in BATCH_24_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(PASS_TICKERS)=={'BLDR','TT','XYL','ALLE'};assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(CONDITIONAL_TICKERS)
 for t,r in rows.items():v=tuple(r['scenario_range'][k] for k in ('low','base','high'));assert v==pytest.approx(EXPECTED[t]);assert 0<=v[0]<=v[1]<=v[2] and v[1]>0;assert r['history_reliability']['label']=='Low'
def test_special_claim_event_and_cash_treatments():
 noc=R('NOC');assert [x['other_equity_claims'] for x in noc['scenario_rows']]==[446e6,44e6,44e6];assert [x['value'] for x in noc['source_ledger']['event_sources'][1:]]==[552e6,508e6,402e6]
 tdg=R('TDG');assert tdg['reported_inputs']['ttm_interest']==1.783e9 and {x['concept'] for x in tdg['source_ledger']['flow_sources']['interest_expense']['sources']}=={'InterestPaidNet'} and tdg['scenario_rows'][0]['raw_value_per_share']<0 and tdg['scenario_range']['low']==0
 uber=R('UBER');assert uber['scenario_rows'][1]['cash_and_investments']==5.504e9;assert uber['scenario_rows'][1]['other_equity_claims']==1.083e9;assert uber['scenario_rows'][1]['debt_and_finance_leases']==12.723e9;assert [x['value'] for x in uber['source_ledger']['bridge_sources'][:3]]==[4.870e9,10.120e9,9.486e9]
 etn=R('ETN');assert etn['scenario_rows'][1]['debt_and_finance_leases']==20.611e9;assert etn['source_ledger']['event_sources'][1]['value']==11.079e9
 hii=R('HII');assert hii['reported_inputs']['ttm_cash_fcff']<0 and hii['scenario_range']['low']==0
def test_directions_and_independent_arithmetic():
 for t in BATCH_24_TICKERS:
  r=R(t);f=r['source_ledger']['controlling_filing'];assert f['filed']<='2026-08-14' and f['period_end']==P[t].period;a=r['scenario_rows'];assert a[0]['wacc']>a[1]['wacc']>a[2]['wacc'];assert a[0]['growth']<=a[1]['growth']<=a[2]['growth']
  for x in a:
   cash=x['starting_cash_fcff'];pv=0.
   for y in range(1,9):fade=(8-y)/7;g=x['terminal_growth']+(x['growth']-x['terminal_growth'])*fade;cash*=1+g;pv+=cash/(1+x['wacc'])**y
   ev=pv+(cash*(1+x['terminal_growth'])/(x['wacc']-x['terminal_growth']))/(1+x['wacc'])**8;raw=(ev+x['cash_and_investments']-x['debt_and_finance_leases']-x['other_equity_claims'])/x['shares'];assert raw==pytest.approx(x['raw_value_per_share']);assert max(0,raw)==pytest.approx(x['conditional_value_per_share'])
def test_public_safe_and_calculator():
 from run_batch_24_history import _public
 for i in BATCH_24_MANIFEST:
  r=R(i.ticker);p=_public(i,r);raw=json.dumps(p);assert p['availability_type']==r['availability_type'] and p['scenario_range']['base']==r['scenario_range']['base'];assert all(k not in raw for k in ('source_ledger','reported_inputs','model_trace'));assert calculator_view(p)['model_family']=='operating';assert calculate(p,overrides={},manual_price=None)['result']==r['scenario_range']
def test_runner_preserves(tmp_path):
 from run_batch_24_history import run
 r=run(source_root=SOURCE,structural_root=STRUCT,output_root=tmp_path/'x');assert (r['attempted_count'],r['pass_count'],r['conditional_count'],r['withheld_count'],r['numeric_count'])==(10,4,6,0,10);assert r['pass_tickers']==['BLDR','TT','XYL','ALLE'];assert r['conditional_tickers']==['NOC','TDG','GNRC','HII','UBER','ETN'];assert not r['serving_artifacts_changed'] and not r['watchlist_changed'] and not r['withheld_register_changed']
def test_arelle_outside_serving():
 for p in [ROOT/'backend/app/main.py',ROOT/'backend/app/deps.py',*sorted((ROOT/'backend/app/routers').glob('*.py'))]:assert 'arelle' not in p.read_text().lower()
