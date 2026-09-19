from copy import deepcopy
import json
from pathlib import Path
import subprocess,sys

import pytest
from app.us_valuation.refresh_separation_event_evidence import (
    bind_separation_event_evidence, separation_event_policy, validate_separation_event_evidence,
)
from app.us_valuation.refresh_separation_scope import bind_separation_scope,separation_policy

ROOT=Path(__file__).resolve().parents[2];SOURCE=ROOT/'output'

def receipt():return json.loads((SOURCE/'us-refresh-runtime/separation-event-evidence/HON.json').read_bytes())
def current():
    st=json.loads((SOURCE/'batch-22-structural-sources-corrected-20260831/HON/structural-filing.json').read_bytes())
    n=json.loads((SOURCE/'us-refresh-runtime/narrative-evidence/HON.json').read_bytes())
    r=json.loads((SOURCE/'us-refresh-runtime/recipes/HON.json').read_bytes())
    return bind_separation_scope(separation_policy('HON'),st,n,r,source_root=SOURCE,cutoff='2026-08-14'),r

def test_real_capture_and_pro_forma_balance_reconcile():
    e=validate_separation_event_evidence(receipt(),source_root=SOURCE,cutoff='2026-08-14')
    assert len(e['sources'])==9 and all(row['sha256'] and row['byte_count']>0 for row in e['sources'])
    b=e['pro_forma_balance']
    assert b['cash']==10_977_000_000 and b['short_investments']==413_000_000
    assert b['cash_and_short_investments']==11_390_000_000
    assert b['short_borrowings']==4_630_000_000 and b['current_debt']==3_094_000_000 and b['long_debt']==13_164_000_000
    assert b['interest_bearing_debt']==20_888_000_000
    assert b['nci']==973_000_000 and b['total_assets']==b['liabilities_and_equity']==52_879_000_000

def test_pro_forma_history_is_continuing_earnings_not_cash_history():
    h=receipt()['pro_forma_history']
    assert h['fy2023']=={'interest':582_000_000,'parent_net_income':1_236_000_000,'revenue':19_407_000_000}
    assert h['fy2024']=={'interest':797_000_000,'parent_net_income':1_302_000_000,'revenue':19_281_000_000}
    assert h['fy2025']=={'interest':788_000_000,'parent_net_income':1_368_000_000,'revenue':19_945_000_000}
    assert h['q1_2026']=={'interest':232_000_000,'parent_net_income':120_000_000,'revenue':4_823_000_000}
    assert receipt()['continuing_fcff'] is None

def test_current_quarter_and_guidance_cash_reconcile_but_do_not_become_fcff():
    e=receipt();q=e['current_quarter_continuing_parent'];g=e['management_guidance']
    assert q['revenue']==5_187_000_000 and q['operating_income']==662_000_000
    assert q['operating_cash_flow']==563_000_000 and q['capital_expenditures']==187_000_000
    assert q['separation_cost_payment_addback']==49_000_000 and q['quantinuum_cash_addback']==31_000_000
    assert q['adjusted_free_cash_flow']==456_000_000
    assert g['operating_cash_flow_range']==[1_900_000_000,2_200_000_000]
    assert g['adjusted_free_cash_flow_range']==[1_800_000_000,2_100_000_000]
    assert g['capital_expenditures']==600_000_000 and g['separation_cost_payment_addback']==400_000_000 and g['quantinuum_cash_addback']==100_000_000
    assert g['includes_johnson_matthey_and_expected_divestitures'] and not g['gaap_reconciliation_complete']

def test_agreements_keep_cash_distribution_intercompany_and_license_separate():
    terms={row['name']:row['value'] for row in receipt()['agreement_terms']}
    assert terms['aerospace_cash_distribution']=={'fixed':15_100_000_000,'additional_maximum':1_500_000_000,'exact_total':None}
    assert terms['intergroup_accounts']=='settled_cash_dividend_contribution_or_extinguished_amount_undisclosed'
    assert terms['aerospace_cash_assets']=='transferred_by_group_ownership_amount_in_schedules_not_disclosed'
    assert terms['trademark_fixed_schedule']=={'total':1_125_000_000,'upfront':18_750_000,'monthly_count':59,'monthly':18_750_000}

def test_event_evidence_preserves_historical_values_and_blocks_numeric_successor():
    scope,recipe=current();value=bind_separation_event_evidence(separation_event_policy('HON'),receipt(),scope,recipe,source_root=SOURCE,cutoff='2026-08-14')
    assert value['historical_range_only']=={'low':60.78533467481803,'base':149.61398945604896,'high':277.0528047042256}
    for key in ('continuing_fcff','post_close_cash_and_investments','post_close_debt','post_close_nci','acquired_fcff','claim_adjustment'):assert value[key] is None
    assert not value['numeric_successor_issued'] and len(value['review_reasons'])>=8

def test_receipt_policy_and_cutoff_drift_fail_closed():
    e=receipt();e['management_guidance']['operating_cash_flow']=0
    with pytest.raises(ValueError,match='drift'):validate_separation_event_evidence(e,source_root=SOURCE,cutoff='2026-08-14')
    scope,recipe=current();p=separation_event_policy('HON');p['mechanism']='wrong'
    with pytest.raises(ValueError,match='identity'):bind_separation_event_evidence(p,receipt(),scope,recipe,source_root=SOURCE,cutoff='2026-08-14')
    with pytest.raises(ValueError,match='version/cutoff'):validate_separation_event_evidence(receipt(),source_root=SOURCE,cutoff='2026-06-30')

def test_policy_contains_no_filing_amounts_or_dates():
    encoded=json.dumps(separation_event_policy('HON'),sort_keys=True)
    for forbidden in ('0000773840-26-000084','2026-06-29','15100000000','1750000000'):assert forbidden not in encoded

def test_real_two_worker_flow_executes_event_evidence_and_preserves_hca():
    p=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),'--ticker','HON','--ticker','HCA','--max-workers','2','--source-index',str(SOURCE/'us-refresh-runtime/source-indexes/d5be9454237ce017d88950e2923206e539c063b805348b2173baa9f00ad32bfb.json')],cwd=ROOT,capture_output=True,text=True,check=True)
    report=json.loads(Path(json.loads(p.stdout.strip().splitlines()[-1])['report_path']).read_bytes());rows={r['ticker']:r for r in report['rows']}
    assert report['counts']=={'implementation_gap':2}
    assert rows['HON']['partial_separation_event_evidence']['numeric_successor_issued'] is False
    assert rows['HON']['partial_separation_event_evidence']['continuing_fcff'] is None
    assert rows['HCA']['partial_professional_liability_annual_evidence']['claim_adjustment'] is None
