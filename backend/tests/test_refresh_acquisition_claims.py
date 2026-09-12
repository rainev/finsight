import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.us_valuation.refresh_acquisition_claims import broadridge_claim_policy, select_acquisition_claim, QNAME
from app.us_valuation.refresh_acquisition_claims import wg2_claim_policy

ROOT = Path(__file__).parents[2]


def source():
    structural = json.loads((ROOT/'output/batch-30-structural-sources-20260901/BR/structural-filing.json').read_text())
    return structural, {'accessionNumber':structural['source_accession'],'reportDate':structural['report_date'],'filingDate':structural['filed_date']}


def test_reported_current_acquisition_claim_is_not_preferred_equity():
    packet, filing = source()
    result = select_acquisition_claim(broadridge_claim_policy(),packet,filing,'0001383312','2026-08-14')
    assert result['claim_adjustment'] == 59900000
    assert result['source_rows'][0]['qname'] == QNAME
    assert 'recurring cash deduction' in result['formula']


@pytest.mark.parametrize('field,value', [('value',-1),('value',float('nan')),('unit','shares'),('entity_identifier','0000000001'),('source_accession','wrong'),('namespace','http://attacker.invalid/us-gaap/2026')])
def test_bad_current_liability_is_rejected(field,value):
    packet, filing = source()
    for row in packet['facts']:
        if row.get('qname') == QNAME and row.get('period_end') == filing['reportDate'] and not row.get('dimensions'):
            row[field] = value
    with pytest.raises(ValueError):
        select_acquisition_claim(broadridge_claim_policy(),packet,filing,'0001383312','2026-08-14')


def test_new_source_amount_changes_claim_and_missing_amount_is_not_zero():
    packet, filing = source()
    rows = [row for row in packet['facts'] if row.get('qname') in (QNAME,QNAME+'Noncurrent') and row.get('period_end') == filing['reportDate'] and not row.get('dimensions')]
    for row in rows:
        row['value'] = 70000000
    assert select_acquisition_claim(broadridge_claim_policy(),packet,filing,'0001383312','2026-08-14')['claim_adjustment'] == 70000000
    packet['facts'] = [row for row in packet['facts'] if row.get('qname') != QNAME]
    with pytest.raises(ValueError, match='absence is not zero'):
        select_acquisition_claim(broadridge_claim_policy(),packet,filing,'0001383312','2026-08-14')


def test_claim_reclassification_preserves_original_value_without_double_deduction():
    from app.us_valuation.calculation_recipe import evaluate_recipe
    recipe = json.loads((ROOT/'output/us-refresh-runtime/recipes/BR.json').read_text())
    original = evaluate_recipe(recipe)
    packet, filing = source()
    claim = select_acquisition_claim(broadridge_claim_policy(),packet,filing,'0001383312','2026-08-14')['claim_adjustment']
    mapped = deepcopy(recipe)
    for case in mapped['scenarios'].values():
        assert case['inputs']['preferred_equity'] == claim
        case['inputs']['preferred_equity'] = 0.0  # Reclassification test only; runtime requires separate current proof.
        case['inputs']['nonoperating_adjustment'] = -claim
    assert evaluate_recipe(mapped)['range'] == original['range']


def test_component_mismatch_or_new_claim_structure_cannot_be_silently_ignored():
    packet, filing = source()
    for row in packet['facts']:
        if row.get('qname') == QNAME+'Noncurrent' and row.get('period_end') == filing['reportDate'] and not row.get('dimensions'):
            row['value'] += 1000000
    with pytest.raises(ValueError, match='do not reconcile'):
        select_acquisition_claim(broadridge_claim_policy(),packet,filing,'0001383312','2026-08-14')


def test_real_idexx_prior_estimate_is_not_a_current_liability_or_maximum():
    from app.us_valuation.refresh_acquisition_claims import idexx_claim_policy
    from app.us_valuation.refresh_source_ingestion import _validate_structural_payload
    raw = json.loads((ROOT/'output/batch-14-structural-sources-20260829/IDXX/structural-filing.json').read_text())
    filing = {'accessionNumber':'0000874716-26-000123','reportDate':'2026-06-30','filingDate':'2026-08-04','form':'10-Q'}
    packet = _validate_structural_payload(raw,cik='0000874716',filing=filing)
    with pytest.raises(ValueError,match='prior estimated payment'):
        select_acquisition_claim(idexx_claim_policy(),packet,filing,'0000874716','2026-08-14')
    # Synthetic current disclosure tests the reusable selector, not a repair
    # to the historical filing or permission to publish a current IDXX value.
    current = deepcopy(packet)
    for row in current['facts']:
        if row['qname'] == idexx_claim_policy()['concept']:
            row['period_end'] = '2026-06-30'
    assert select_acquisition_claim(idexx_claim_policy(),current,filing,'0000874716','2026-08-14')['claim_adjustment'] == 2300000


WG2_SOURCES = {
    'VRTX':'output/batch-14-structural-sources-20260829/VRTX/structural-filing.json',
    'LLY':'output/batch-12-structural-sources-20260828/LLY/structural-filing.json',
    'CTSH':'output/batch-30-structural-sources-20260901/CTSH/structural-filing.json',
    'VRT':'output/batch-32-structural-sources-20260903/VRT/structural-filing.json',
    'REGN':'output/batch-14-structural-sources-20260829/REGN/structural-filing.json',
}


def _wg2_source(ticker):
    structural=json.loads((ROOT/WG2_SOURCES[ticker]).read_text())
    filing={'accessionNumber':structural['source_accession'],'reportDate':structural['report_date'],
            'filingDate':structural['filed_date'],'form':structural['form']}
    return structural,filing


@pytest.mark.parametrize('ticker,amount', [('VRTX',79_600_000),('CTSH',25_000_000),('VRT',222_500_000)])
def test_wg2_source_bound_current_claims_are_counted_once(ticker,amount):
    structural,filing=_wg2_source(ticker)
    result=select_acquisition_claim(wg2_claim_policy(ticker),structural,filing,
                                    wg2_claim_policy(ticker)['cik'],'2026-08-14')
    assert result['status']=='source_bound'
    assert result['claim_adjustment']==amount
    assert result['current_carrying_liability']==amount
    assert result['review_reasons']==[]


def test_lly_level3_components_bind_current_claim_but_post_period_cash_blocks_full_use():
    structural,filing=_wg2_source('LLY')
    result=select_acquisition_claim(wg2_claim_policy('LLY'),structural,filing,'0000059478','2026-08-14')
    assert result['status']=='review_required'
    assert result['current_carrying_liability']==2_518_000_000
    assert result['claim_adjustment'] is None
    assert result['review_reasons']==['post_period_cash_paid_evidence_not_machine_bound']
    assert {row['qname'] for row in result['source_rows']} == {
        QNAME+'Current',QNAME+'Noncurrent'}
    assert any(row['qname']=='us-gaap:BusinessCombinationPriceOfAcquisitionExpected'
               for row in result['excluded_rows'])


def test_regn_duration_accrual_is_not_silently_converted_to_instant_claim():
    structural,filing=_wg2_source('REGN')
    result=select_acquisition_claim(wg2_claim_policy('REGN'),structural,filing,'0000872589','2026-08-14')
    assert result['status']=='review_required'
    assert result['claim_adjustment'] is None
    assert result['source_rows'][0]['value']==67_200_000
    assert result['source_rows'][0]['period_start']=='2026-01-01'
    assert any(row['value']==99_900_000 for row in result['excluded_rows'])
    assert result['review_reasons']==['duration_accrual_has_no_reconciled_period_end_carrying_liability']


def test_ctsh_duplicate_views_are_not_summed():
    structural,filing=_wg2_source('CTSH')
    result=select_acquisition_claim(wg2_claim_policy('CTSH'),structural,filing,'0001058290','2026-08-14')
    assert [row['value'] for row in result['source_rows']].count(25_000_000)==2
    assert result['claim_adjustment']==25_000_000


def test_vrt_custom_total_is_corroborated_while_gaap_slices_stay_diagnostic():
    structural,filing=_wg2_source('VRT')
    result=select_acquisition_claim(wg2_claim_policy('VRT'),structural,filing,'0001674101','2026-08-14')
    assert result['claim_adjustment']==222_500_000
    assert {row['value'] for row in result['source_rows'] if row['value']}=={222_500_000}
    assert {row['value'] for row in result['source_rows']}=={0,222_500_000}
    assert 206_100_000 in {row['value'] for row in result['excluded_rows']}
    assert 12_100_000 in {row['value'] for row in result['excluded_rows']}


@pytest.mark.parametrize('ticker', ['VRTX','LLY','CTSH','VRT','REGN'])
def test_wg2_policy_identity_and_current_source_are_fail_closed(ticker):
    structural,filing=_wg2_source(ticker)
    policy=wg2_claim_policy(ticker);policy['version']='tampered'
    with pytest.raises(RuntimeError,match='identity/version mismatch'):
        select_acquisition_claim(policy,structural,filing,policy['cik'],'2026-08-14')


@pytest.mark.parametrize('ticker', ['VRTX','CTSH','VRT'])
def test_wg2_claim_reclassification_preserves_prior_value_when_scope_is_unchanged(ticker):
    from app.us_valuation.calculation_recipe import evaluate_recipe
    recipe=json.loads((ROOT/f'output/us-refresh-runtime/recipes/{ticker}.json').read_text())
    structural,filing=_wg2_source(ticker)
    claim=select_acquisition_claim(wg2_claim_policy(ticker),structural,filing,
                                   wg2_claim_policy(ticker)['cik'],'2026-08-14')['claim_adjustment']
    mapped=deepcopy(recipe)
    for spec in mapped['scenarios'].values():
        assert spec['inputs']['preferred_equity']==claim
        spec['inputs']['preferred_equity']=0.0
        spec['inputs']['nonoperating_adjustment']=-claim
    assert evaluate_recipe(mapped)['range']==evaluate_recipe(recipe)['range']
