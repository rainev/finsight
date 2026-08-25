from pathlib import Path
from app.us_valuation.batch_05 import BATCH_05_MANIFEST,BATCH_05_TICKERS
from app.us_valuation.batch_05_launch_first import build_batch_05_launch_first_result
from app.us_valuation.calculator import calculate,calculator_view
from app.us_valuation.reliability import accounting_label
from run_batch_05_launch_first import _public
S=Path('output/batch-05-sec-source-packets-20260825');X=Path('output/batch-05-structural-sources-20260825')
def test_all_batch05_baselines_are_conditional_low_ordered():
 for t in BATCH_05_TICKERS:
  r=build_batch_05_launch_first_result(ticker=t,source_root=S,structural_root=X);v=r['scenario_range'];assert 0<=v['low']<=v['base']<=v['high'];assert v['base']>0;assert r['baseline']['availability_type']=='conditional_estimate';assert r['baseline']['confidence']=='Low';assert len(r['source_ledger']['bridge_sources'])>=3
def test_higher_risk_states_are_lower():
 for t in BATCH_05_TICKERS:
  rows=build_batch_05_launch_first_result(ticker=t,source_root=S,structural_root=X)['scenario_rows'];assert rows[0]['wacc']>rows[1]['wacc']>rows[2]['wacc'];assert rows[0]['conditional_value_per_share']<=rows[1]['conditional_value_per_share']<=rows[2]['conditional_value_per_share']
def test_homebuilders_use_honest_consolidated_equity_earnings_routes():
 for t in ('PHM','DHI','NVR'):
  r=build_batch_05_launch_first_result(ticker=t,source_root=S,structural_root=X);a=r['governed_assumptions'];assert r['method']=='homebuilder_normalized_equity_earnings_baseline';assert a['route_is_mortgage_separated_fcff'] is False;assert a['ev_debt_bridge_applied'] is False;assert 'no EV debt bridge' in r['source_ledger']['bridge_treatment']

def test_homebuilder_reconstruction_and_context_are_source_traced():
 for t in ('PHM','DHI','NVR'):
  r=build_batch_05_launch_first_result(ticker=t,source_root=S,structural_root=X);ledger=r['source_ledger'];components=ledger['net_income_reconstruction']['components']
  assert set(components)=={'fy','current_ytd','prior_ytd'}
  assert all(row['accession'] and row['concept']=='us-gaap:NetIncomeLoss' and row['unit']=='USD' for row in components.values())
  assert components['fy']['value']+components['current_ytd']['value']-components['prior_ytd']['value']==ledger['net_income_reconstruction']['ttm']
  assert all(row['accession'] and row['concept'] and row['unit']=='USD' for row in ledger['mortgage_and_land_context'])
  assert any('Inventory' in row['concept'] or 'Land' in row['concept'] for row in ledger['mortgage_and_land_context'])
  assert ledger['accounting_uncertainty']['source_linked_exposure']>0

def test_homebuilder_public_calculator_uses_equity_earnings_inputs():
 for issuer in (row for row in BATCH_05_MANIFEST if row.ticker in {'PHM','DHI','NVR'}):
  r=build_batch_05_launch_first_result(ticker=issuer.ticker,source_root=S,structural_root=X);artifact=_public(issuer,r);view=calculator_view(artifact)
  assert artifact['public_assumptions']['forecast_mode']=='normalized_equity_earnings'
  assert view['model_family']=='equity_earnings'
  assert {'normalized_earnings_factor','earnings_multiple'}==set(view['defaults'])
  assert calculate(artifact,overrides={'normalized_earnings_factor':1.1},manual_price=None)['result']['base']>artifact['scenario_range']['base']

def test_azo_finance_lease_is_explicitly_bounded_once():
 r=build_batch_05_launch_first_result(ticker='AZO',source_root=S,structural_root=X);sources=r['source_ledger']['bridge_sources']
 reported=[row for row in sources if row.get('concept')=='us-gaap:FinanceLeasePrincipalPayments']
 reserve=[row for row in sources if row.get('field')=='unresolved_finance_lease_reserve']
 assert reported[0]['value']==82_161_000
 assert reserve[0]['value_range']=={'bear':82_161_000.,'base':41_080_500.,'bull':0.}

def test_public_accounting_reliability_reflects_bounded_uncertainty():
 for issuer in BATCH_05_MANIFEST:
  r=build_batch_05_launch_first_result(ticker=issuer.ticker,source_root=S,structural_root=X);artifact=_public(issuer,r);reliability=artifact['reliability']
  assert reliability['label']=='Low'
  if issuer.ticker in {'PHM','DHI','NVR','AZO'}:
   assert reliability['accounting_impact_ratio']>0
  if issuer.ticker in {'PHM','DHI','NVR'}:
   assert reliability['accounting_impact_ratio']==r['source_ledger']['accounting_uncertainty']['impact_ratio']
   assert reliability['accounting_label']==accounting_label(reliability['accounting_impact_ratio'])
