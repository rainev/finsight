from pathlib import Path
import json,sys,pytest
from app.us_valuation.batch_28 import BATCH_28_MANIFEST,BATCH_28_TICKERS
from app.us_valuation.batch_28_history import PASS_TICKERS,CONDITIONAL_TICKERS,WITHHELD_TICKERS,build_batch_28_history_result
from app.us_valuation.calculator import calculate,calculator_view
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output/batch-28-sec-source-packets-20260831';STRUCT=ROOT/'output/batch-28-structural-sources-20260831'
def R(t):return build_batch_28_history_result(ticker=t,source_root=SOURCE,structural_root=STRUCT)
EXPECTED={'QCOM':(74.30954933149283,141.71660890891766,230.9638760732424),'CDNS':(64.39446765303288,107.39439088499527,156.2348826176444),'FICO':(142.04604383205339,465.36145255177854,892.2715596059304),'MCHP':(3.0508679571950985,17.758157215797535,46.424128171930924),'GEN':(14.670825884887904,28.779597766201267,48.950417119488606),'PTC':(54.40163693389,124.66731677508264,191.63229502696748),'CSCO':(27.81703783666699,52.33616910960072,93.27652342339172),'TYL':(105.85546531727114,240.13362249797316,347.79484398172076),'ZBRA':(41.273137285970066,205.49991384107813,350.3567136265877),'JBL':(19.535888894649034,104.26190555010285,220.1997056672033)}
def test_outcomes_ranges_and_denominator():
 rows={t:R(t) for t in BATCH_28_TICKERS};assert {t for t,r in rows.items() if r['availability_type']=='available'}==set(PASS_TICKERS)=={'FICO','ZBRA'};assert {t for t,r in rows.items() if r['availability_type']=='conditional_estimate'}==set(CONDITIONAL_TICKERS)=={'QCOM','CDNS','MCHP','GEN','PTC','CSCO','TYL','JBL'};assert not WITHHELD_TICKERS
 for t,v in EXPECTED.items():assert tuple(rows[t]['scenario_range'][k] for k in ('low','base','high'))==pytest.approx(v)
 assert len(rows)==10 and all(r['scenario_range']['base']>0 for r in rows.values())
def test_narrow_lineage_and_bridge_controls():
 cdns=R('CDNS');assert all(v['period_end']=='2026-06-30' for v in cdns['source_ledger']['flow_sources'].values());assert cdns['source_ledger']['flow_sources']['revenue']['method']=='latest_fy_plus_structural_current_ytd_minus_prior_ytd'
 gen=R('GEN');assert {s['concept'] for s in gen['source_ledger']['flow_sources']['interest_expense']['sources']}=={'InterestAndDebtExpense'};assert gen['source_ledger']['bridge_reconciliation']['cash_and_investments']==533e6
 zbra=R('ZBRA');assert {s['concept'] for s in zbra['source_ledger']['flow_sources']['interest_expense']['sources']}=={'InterestPaidNet'};assert zbra['source_ledger']['bridge_reconciliation']['debt_and_finance_leases']==2.776e9
 csco=R('CSCO');assert csco['source_ledger']['bridge_reconciliation']['debt_and_finance_leases']==31.303e9 and csco['source_ledger']['bridge_reconciliation']['cash_and_investments']==16.640e9
def test_material_events_are_traceable():
 qcom=R('QCOM');assert any(x.get('value')==2.3e9 for x in qcom['source_ledger']['event_sources']);assert any(x.get('value')==3.1e9 for x in qcom['source_ledger']['event_sources']);assert qcom['scenario_rows'][2]['shares']==1.068e9
 cdns=R('CDNS');assert any(x.get('value')==2_100_292_000. for x in cdns['source_ledger']['event_sources']) and any(x.get('value')==902_208_000. for x in cdns['source_ledger']['event_sources'])
 mchp=R('MCHP');schedule=mchp['source_ledger']['bridge_reconciliation']['mandatory_convertible_preferred_schedule'];assert schedule['reported_liquidation_preference']==1.485e9 and schedule['automatic_conversion_date']=='2028-03-15' and schedule['remaining_quarters']==7;assert schedule['conversion_shares'][0]>schedule['conversion_shares'][2];assert next(x for x in mchp['source_ledger']['bridge_sources'] if x.get('concept')=='us-gaap:PreferredStockSharesOutstanding')['unit']=='xbrli:shares'
 gen=R('GEN');assert any(x.get('value')==-1.193e9 for x in gen['source_ledger']['event_sources']) and any(x.get('value')==1.107e9 for x in gen['source_ledger']['event_sources'])
 ptc=R('PTC');assert any(x.get('value')==523.306e6 for x in ptc['source_ledger']['event_sources']) and any(x.get('value')==462.6e6 for x in ptc['source_ledger']['event_sources'])
 tyl=R('TYL');assert any(x.get('value')==257_771_000. for x in tyl['source_ledger']['event_sources']);assert tyl['source_ledger']['bridge_reconciliation']['purchase_obligation_schedule']['reported_total']==537.4e6
 jbl=R('JBL');assert any(x.get('value')==852e6 for x in jbl['source_ledger']['event_sources']) and jbl['source_ledger']['bridge_reconciliation']['other_equity_claims']==(55e6,)*3
def test_dcf_replay():
 from app.us_valuation.practical_models import EnterpriseCashFlowState,enterprise_cash_flow_dcf
 for t in BATCH_28_TICKERS:
  r=R(t)
  for row in r['scenario_rows']:
   s=EnterpriseCashFlowState(row['starting_cash_fcff'],row['growth'],row['terminal_growth'],row['wacc'],row['cash_and_investments'],row['debt_and_finance_leases'],0,row['other_equity_claims'],row['shares']);assert float(enterprise_cash_flow_dcf(s,forecast_years=8,allow_nonpositive_equity_trace=True)['intrinsic_value_per_share'])==pytest.approx(row['raw_value_per_share'])
def test_public_and_calculator_safety():
 from run_batch_28_history import _public
 for i in BATCH_28_MANIFEST:
  r=R(i.ticker);p=_public(i,r);raw=json.dumps(p);assert 'source_ledger' not in raw and 'reported_inputs' not in raw and p['availability_type']==r['availability_type'];view=calculator_view(p);assert view['can_calculate'] and view['model_family']=='operating';assert calculate(p,overrides={},manual_price=None)['result']==r['scenario_range']
def test_runner_preserves_protected_and_bookkeeping(tmp_path):
 from run_batch_28_history import run
 r=run(source_root=SOURCE,structural_root=STRUCT,output_root=tmp_path/'x');assert (r['pass_count'],r['conditional_count'],r['withheld_count'],r['numeric_count'])==(2,8,0,10);assert not r['serving_artifacts_changed'] and not r['watchlist_changed'] and not r['withheld_register_changed']
def test_arelle_outside_serving_process():
 for p in [ROOT/'backend/app/main.py',ROOT/'backend/app/deps.py',*sorted((ROOT/'backend/app/routers').glob('*.py'))]:assert 'arelle' not in p.read_text().lower()
