from __future__ import annotations
import json,sys
from pathlib import Path
from app.us_valuation.batch_10_recovery import build_kmb_recovery_result
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));SOURCE=ROOT/'output'/'batch-10-sec-source-packets-final-a';STRUCT=ROOT/'output'/'batch-10-structural-sources-final-a'
def _result():return build_kmb_recovery_result(source_root=SOURCE,structural_root=STRUCT)
def test_kmb_recovery_is_conditional_and_source_bounded():
 r=_result();assert r['availability_type']=='conditional_estimate';assert r['history_reliability']['label']=='Low';assert 0<r['scenario_range']['low']<r['scenario_range']['base']<r['scenario_range']['high'];assert r['source_ledger']['bridge_reconciliation']['remaining_debt_and_capital_leases']==6_517_000_000;assert r['source_ledger']['bridge_reconciliation']['nci_and_redeemable_claims']==146_000_000;assert r['governed_assumptions']['cash_sale_proceeds']==(1_170_000_000.,1_300_000_000.,1_300_000_000.);assert r['governed_assumptions']['retained_ifp_stake_value']==(1_080_000_000.,1_200_000_000.,1_200_000_000.);assert r['governed_assumptions']['history_years_used']==0;assert r['governed_assumptions']['transition_capex_reserve']==(81_000_000.,0.,0.)
def test_kmb_recovery_directions_and_no_transaction_double_count():
 r=_result();rows=r['scenario_rows'];assert rows[0]['continuing_cash_fcff_proxy']<rows[1]['continuing_cash_fcff_proxy']<rows[2]['continuing_cash_fcff_proxy'];assert rows[0]['growth']<rows[1]['growth']<rows[2]['growth'];assert rows[0]['wacc']>rows[1]['wacc']>rows[2]['wacc'];assert rows[0]['conditional_value_per_share']<rows[1]['conditional_value_per_share']<rows[2]['conditional_value_per_share'];assert r['source_ledger']['bridge_reconciliation']['IFP_gain'].startswith('Not added separately');assert r['reported_inputs']['continuing_h1_capex_proxy']==695_000_000.
def test_kmb_recovery_public_contract_is_safe():
 from app.us_valuation.batch_10 import BATCH_10_MANIFEST
 from run_batch_10_history import _public
 r=_result();public=_public(next(i for i in BATCH_10_MANIFEST if i.ticker=='KMB'),r);raw=json.dumps(public);assert public['availability_type']=='conditional_estimate';assert public['scenario_range']['base']==r['scenario_range']['base'];assert public['public_assumptions']['forecast_mode']=='current_state_post_ifp_pre_kenvue';assert public['public_assumptions']['forecast_policy_version']=='BATCH-10-KMB-RECOVERY-1.0';assert public['model_policy']['reason'].startswith('Conditional Low current-state');assert 'source_ledger' not in raw and 'event_and_bridge_sources' not in raw
