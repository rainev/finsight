import json, math, sys
from pathlib import Path
from functools import lru_cache
import pytest
from app.us_valuation.batch_38 import BATCH_38_MANIFEST
from app.us_valuation.batch_38_history import build_batch_38_history_result
from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from app.valuation.bank import residual_income_valuation
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
KW=dict(source_root=ROOT/'output/batch-38-sec-source-packets-20260907',structural_root=ROOT/'output/batch-38-structural-sources-20260907',structural_cache_root=ROOT/'output/batch-38-structural-cache-20260907',event_root=ROOT/'output/batch-38-event-review-20260907')
@lru_cache(None)
def result(t):return build_batch_38_history_result(ticker=t,**KW)

def test_denominator_values_and_private_source_hashes():
    rows=[result(i.ticker) for i in BATCH_38_MANIFEST]
    assert len(rows)==10
    assert {r['ticker'] for r in rows if r['availability_type']=='not_available'}=={'GPN','CPAY'}
    for r in rows:
        assert r['source_ledger']['runtime_source_verification']['verified']
        assert r['source_ledger']['event_sources']['screened_filings']
        vals=list(r['scenario_range'].values())
        if r['availability_type']=='not_available':assert vals==[None]*3
        else:
            assert all(math.isfinite(v) for v in vals) and 0<=vals[0]<=vals[1]<=vals[2] and vals[1]>0
            assert r['history_reliability']['label']=='Low'

def test_arithmetic_replays_actual_scenarios():
    for issuer in BATCH_38_MANIFEST:
        r=result(issuer.ticker)
        for s in r['scenario_rows']:
            if 'book_value_per_share' in s:
                v=residual_income_valuation(book_value_per_share=s['book_value_per_share'],current_roe=s['current_roe'],cost_of_equity=s['cost_of_equity'],current_payout_ratio=s['current_payout_ratio'],terminal_roe=s['terminal_roe'],terminal_growth=s['terminal_growth'],years=5)['intrinsic_value']
            else:
                state=EnterpriseCashFlowState(s['starting_cash_fcff'],s['growth'],s['terminal_growth'],s['wacc'],s['cash_and_investments'],s['debt_and_finance_leases'],0.,s['other_equity_claims'],s['shares'])
                v=enterprise_cash_flow_dcf(state,forecast_years=8,allow_nonpositive_equity_trace=True)['intrinsic_value_per_share']
            assert v==pytest.approx(s['raw_value_per_share'])

def test_software_investment_and_post_close_scope():
    fis=result('FIS');ma=result('MA')
    assert fis['source_ledger']['flow_sources']['combined_h1']['software']['value']==441_000_000
    assert ma['source_ledger']['software_sources']['value']>0
    assert len(ma['source_ledger']['annual_cash_sources'])==5
    assert all(row['software_capex']['value']>0 for row in ma['source_ledger']['annual_cash_sources'])
    assert 'diagnostic only' in fis['source_ledger']['history_scope']
    assert result('GPN')['source_ledger']['raw_scenario_rows'][1]['raw_value_per_share']<0
    assert result('CPAY')['source_ledger']['unknown_customer_funding_component'] is None
    assert result('CPAY')['availability_type']=='not_available'
    funds=result('CPAY')['source_ledger']['funding_boundary']
    assert funds['customer_deposits']['value']==8_915_786_000
    assert funds['restricted_cash']['value']==7_004_803_000
    assert funds['used_as_free_cash'] is False

def test_clearing_money_excluded_and_timed_restructuring_charged():
    cme=result('CME')
    assert cme['scenario_rows'][1]['cash_and_investments']==2_275_600_000
    assert cme['scenario_rows'][1]['debt_and_finance_leases']==3_470_500_000
    for row in result('WTW')['scenario_rows']:
        pv=sum((625_000_000/3)/(1+row['wacc'])**y for y in (1,2,3))
        assert row['transformation_cost_pv']==pytest.approx(pv)
    assert result('WTW')['source_ledger']['transformation_event']['reported_annual_net_savings_excluded']==350_000_000

def test_public_calculator_default_and_direction():
    from run_batch_38_history import _public
    from app.us_valuation.calculator import calculator_view,calculate
    for issuer in BATCH_38_MANIFEST:
        r=result(issuer.ticker);p=_public(issuer,r);encoded=json.dumps(p);view=calculator_view(p)
        for key in ('source_ledger','reported_inputs','governed_assumptions','raw_scenario_rows','source_manifest_sha256'):assert key not in encoded
        if r['availability_type']=='not_available':
            assert not view['can_calculate']
            assert p['public_assumptions']['forecast_years']==8
            assert 'Batch 38' in p['issuer']['classification_reason']
            assert p['model_policy']['primary']=='fcff_dcf'
            assert 'conditional_estimate' not in json.dumps(p['automated_review'])
        else:
            assert view['can_calculate']
            assert calculate(p,overrides={},manual_price=None)['result']==pytest.approx(r['scenario_range'])
            assert calculate(p,overrides=view['defaults'],manual_price=None)['result']==pytest.approx(r['scenario_range'])
            higher=calculate(p,overrides={'discount_rate':view['defaults']['discount_rate']+.01},manual_price=None)
            assert higher['result']['base']<r['scenario_range']['base']

def test_history_and_japan_disclosures_match_inputs():
    wtw=result('WTW')
    assert wtw['source_ledger']['history_scope'].startswith(str(len(wtw['source_ledger']['annual_cash_sources'])))
    pru=result('PRU');ctx=pru['source_ledger']['earnings_attribution_context'][0]
    assert ctx['participating_earnings']['value']==21_000_000
    japan=pru['source_ledger']['japan_forward_earnings_constraint']
    assert japan['remaining_2026_pre_tax_scenarios']==(340e6,315e6,290e6)
    assert all(s['current_roe']<=ceiling for s,ceiling in zip(pru['scenario_rows'],japan['roe_ceilings']))

def test_missing_core_fact_rejected():
    from app.us_valuation.batch_38_history import point
    with pytest.raises(ValueError):point({'facts':[]},'CashAndCashEquivalentsAtCarryingValue')

def test_source_tamper_rejected(tmp_path):
    import shutil
    p=tmp_path/'sources';shutil.copytree(KW['source_root']/'MA',p/'MA')
    (p/'MA'/'companyfacts.json').write_text('{}')
    with pytest.raises(ValueError,match='hash mismatch'):
        build_batch_38_history_result(ticker='MA',**{**KW,'source_root':p})
