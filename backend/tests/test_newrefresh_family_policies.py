import json
from pathlib import Path
import pytest

from app.us_valuation.newrefresh_family_policies import (
    bind_and_evaluate_existing_recipe,
    compile_residual_income_policy,
    reconcile_common_equity_components,
    reconcile_no_outside_equity_claim,
)


ROOT = Path(__file__).parents[2]
OUTPUT = ROOT / "output"


def _load(path: Path):
    return json.loads(path.read_text())


def test_complete_five_components_do_not_hide_unknown_equity_member():
    structural = _load(OUTPUT/'batch-33-structural-replay-a-20260903/AFL/structural-filing.json')
    extra = dict(next(row for row in structural['facts'] if row.get('qname') == 'us-gaap:StockholdersEquity'
        and row.get('period_end') == '2026-06-30' and row.get('dimensions')))
    extra.update(value=1., dimensions=[['us-gaap:StatementEquityComponentsAxis','issuer:UnknownMember']])
    structural['facts'].append(extra)
    with pytest.raises(ValueError, match='unknown equity component'):
        reconcile_common_equity_components(structural,cik='0000004977',accession=structural['source_accession'],period_end='2026-06-30')


def test_preferred_share_identity_is_checked_even_for_zero_rows():
    from app.us_valuation.newrefresh_family_policies import reconcile_brk_common_equity
    structural = _load(OUTPUT/'batch-37-structural-sources-20260906/BRK.B/structural-filing.json')
    structural['facts'].append({'qname':'us-gaap:PreferredStockSharesOutstanding','unit':'xbrli:shares',
        'period_end':'2026-06-30','period_start':None,'value':0.,'entity_identifier':'0000000001',
        'entity_scheme':'http://www.sec.gov/CIK','source_accession':structural['source_accession']})
    with pytest.raises(ValueError,match='preferred-share source identity'):
        reconcile_brk_common_equity(structural,accession=structural['source_accession'],period='2026-06-30')


def test_real_msft_aoci_details_reconcile_without_becoming_extra_equity():
    from app.us_valuation.newrefresh_family_policies import reconcile_no_outside_equity_claim
    structural = _load(OUTPUT/'us-refresh-runtime/acquisitions/0a0a47feb71d0ecdf4f4f1cc82bbbab937dc31f55876e119a3a97feb4d7e3c3d/packets/MSFT.json')['packet']['structural_filing']
    result = reconcile_no_outside_equity_claim(structural,cik='0000789019',accession=structural['source_accession'],period_end='2026-06-30')
    assert result['value'] == 0.
    changed = json.loads(json.dumps(structural))
    for row in changed['facts']:
        if row.get('qname') == 'us-gaap:StockholdersEquity' and row.get('period_end') == '2026-06-30' and row.get('dimensions') == [['us-gaap:StatementEquityComponentsAxis','us-gaap:AccumulatedNetUnrealizedInvestmentGainLossMember']]:
            row['value'] += 1.
    with pytest.raises(ValueError,match='AOCI subcomponents'):
        reconcile_no_outside_equity_claim(changed,cik='0000789019',accession=structural['source_accession'],period_end='2026-06-30')


def test_chubb_uses_current_structural_facts_missing_from_companyfacts():
    recipe = _load(OUTPUT/'us-refresh-runtime/recipes/CB.json')
    entry = next(row for row in _load(OUTPUT/'us-refresh-runtime/registry.json')['entries'] if row['ticker']=='CB')
    source = OUTPUT/'batch-36-sec-source-packets-20260905/CB'
    structural = _load(OUTPUT/'batch-36-structural-sources-20260905/CB/structural-filing.json')
    packet = {'submissions':_load(source/'submissions.json'),'companyfacts':_load(source/'companyfacts.json'),
        '_selected_controlling_filing':{'accession':structural['source_accession'],'period_end':'2026-06-30'}}
    original = json.dumps(packet['companyfacts'],sort_keys=True)
    policy = compile_residual_income_policy(recipe,entry)
    result = bind_and_evaluate_existing_recipe(policy,recipe,packet,structural_packet=structural,cutoff='2026-08-14')
    assert result['bound']['inputs']['common_equity'] == 75372000000.
    assert result['bound']['inputs']['diluted_shares'] == 393010295.
    assert result['bound']['controlling_filing']['period_end'] == '2026-06-30'
    supplements = result['bound']['source_rows']['structural_supplements']['added_facts']
    assert any(row['concept']=='us-gaap:NetIncomeLoss' and row['labels'] for row in supplements)
    assert json.dumps(packet['companyfacts'],sort_keys=True) == original
    packet['companyfacts']['facts']['us-gaap'].setdefault('NetIncomeLoss',{}).setdefault('units',{}).setdefault('USD',[]).append({
        'val':1.,'start':'2026-01-01','end':'2026-06-30','form':'10-Q','filed':structural['filed_date'],'accn':structural['source_accession']})
    with pytest.raises(ValueError,match='CompanyFacts/structural amount conflict'):
        bind_and_evaluate_existing_recipe(policy,recipe,packet,structural_packet=structural,cutoff='2026-08-14')


def test_investee_preferred_asset_is_not_issuer_preferred_claim():
    from app.us_valuation.newrefresh_family_policies import _is_preferred_investment_asset
    structural = _load(OUTPUT/'batch-37-structural-sources-20260906/BRK.B/structural-filing.json')
    asset = next(row for row in structural['facts'] if row.get('local_name') == 'PreferredStockInvestmentLiquidationValue')
    assert _is_preferred_investment_asset(asset)
    assert not _is_preferred_investment_asset({**asset, 'presentation_ancestry': []})
    assert not _is_preferred_investment_asset({**asset, 'local_name': 'PreferredStockValue'})
    assert not _is_preferred_investment_asset({**asset, 'statement_roles': ['balance_sheet']})


def test_brk_refresh_preserves_class_basis_and_approved_dilution_scenarios():
    recipe = _load(OUTPUT/'us-refresh-runtime/recipes/BRK.B.json')
    entry = next(row for row in _load(OUTPUT/'us-refresh-runtime/registry.json')['entries'] if row['ticker']=='BRK.B')
    source = OUTPUT/'batch-37-sec-source-packets-20260906/BRK.B'
    structural = _load(OUTPUT/'batch-37-structural-sources-20260906/BRK.B/structural-filing.json')
    packet = {'submissions':_load(source/'submissions.json'), 'companyfacts':_load(source/'companyfacts.json'),
              '_selected_controlling_filing':{'accession':'0001193125-26-341032','period_end':'2026-06-30'}}
    policy = compile_residual_income_policy(recipe, entry)
    result = bind_and_evaluate_existing_recipe(policy,recipe,packet,structural_packet=structural,cutoff='2026-08-14')
    assert result['bound']['inputs']['diluted_shares'] == 2140710161.
    assert result['bound']['inputs']['common_equity'] == 747910000000.
    assert result['refreshed_replay'] == pytest.approx(recipe['replay'])
    assert result['bound']['scenario_share_counts']['bear'] == 2140710161. * 1.015
    from app.us_valuation.newrefresh_family_policies import reconcile_brk_common_equity
    broken = json.loads(json.dumps(structural))
    broken['facts'] = [row for row in broken['facts'] if row.get('local_name') != 'TreasuryStockValue']
    with pytest.raises(ValueError, match='component missing'):
        reconcile_brk_common_equity(broken, accession='0001193125-26-341032', period='2026-06-30')


def test_jpm_residual_policy_binds_cached_filing_and_replays_recipe():
    recipe = _load(OUTPUT / "us-refresh-runtime" / "recipes" / "JPM.json")
    registry = _load(OUTPUT / "us-refresh-runtime" / "registry.json")
    entry = next(row for row in registry["entries"] if row["ticker"] == "JPM")
    policy = compile_residual_income_policy(recipe, entry)
    source = OUTPUT / "batch-01-controlled" / "sources" / "JPM"
    packet = {"submissions": _load(source / "submissions.json"), "companyfacts": _load(source / "companyfacts.json"), "_selected_controlling_filing": {"accession": "0001628280-26-054343", "period_end": "2026-06-30"}}
    result = bind_and_evaluate_existing_recipe(policy, recipe, packet, structural_packet=None, cutoff="2026-08-14")
    assert result["bound"]["status"] == "bound_successor_candidate"
    assert result["bound"]["controlling_filing"]["accession"] == "0001628280-26-054343"
    assert result["bound"]["inputs"]["book_value_per_share"] > 0
    assert result["bound"]["claim_status"]["preferred_equity"] == "reported"
    annual = next(row for row in result['bound']['source_rows']['roe_history'] if row['period_end']=='2025-12-31')
    assert annual['beginning_common_equity'] == 324708000000.
    assert annual['common_equity'] == 342393000000.
    assert annual['average_common_equity'] == 333550500000.
    assert annual['roe'] == pytest.approx(55681000000. / 333550500000.)
    assert annual['roe_denominator_basis'] == 'average_beginning_ending_common_equity'
    assert annual['beginning_equity_source']['end'] == '2024-12-31'
    assert result['bound']['inputs']['book_value_per_share'] == pytest.approx(353558000000. / 2707200000.)
    assert result["baseline_replay"] == recipe["replay"]
    assert result["refreshed_replay"] != result["baseline_replay"]
    changed = json.loads(json.dumps(result["refreshed_recipe"]))
    changed["scenarios"]["base"]["inputs"]["book_value_per_share"] += 1.0
    from app.us_valuation.calculation_recipe import evaluate_recipe
    assert evaluate_recipe(changed)["range"]["base"] != result["refreshed_replay"]["base"]


def test_afl_component_reconciliation_proves_common_equity_scope():
    recipe = _load(OUTPUT / "us-refresh-runtime" / "recipes" / "AFL.json")
    registry = _load(OUTPUT / "us-refresh-runtime" / "registry.json")
    entry = next(row for row in registry["entries"] if row["ticker"] == "AFL")
    policy = compile_residual_income_policy(recipe, entry)
    source = OUTPUT / "batch-33-sec-source-packets-20260903" / "AFL"
    packet = {"submissions": _load(source / "submissions.json"), "companyfacts": _load(source / "companyfacts.json"), "_selected_controlling_filing": {"accession": "0001628280-26-054618", "period_end": "2026-06-30"}}
    structural = _load(OUTPUT / "batch-33-structural-replay-a-20260903" / "AFL" / "structural-filing.json")
    result = bind_and_evaluate_existing_recipe(policy, recipe, packet, structural_packet=structural, cutoff="2026-08-14")
    assert result["bound"]["claim_status"]["preferred_equity"] == "component_reconciliation_proved_absent"
    assert result["bound"]["inputs"]["common_equity"] == 30312000000.0
    assert result["baseline_replay"] == recipe["replay"]


def test_apd_parent_equity_keeps_total_nci_and_vie_subset_diagnostic():
    recipe=_load(OUTPUT/'us-refresh-runtime/recipes/APD.json')
    entry=next(row for row in _load(OUTPUT/'us-refresh-runtime/registry.json')['entries'] if row['ticker']=='APD')
    policy=compile_residual_income_policy(recipe,entry)
    source=OUTPUT/'batch-41-sec-source-packets-20260907/APD'
    structural=_load(OUTPUT/'batch-41-structural-replay-a-20260907/APD/structural-filing.json')
    packet={'submissions':_load(source/'submissions.json'),'companyfacts':_load(source/'companyfacts.json'),
        '_selected_controlling_filing':{'accession':structural['source_accession'],'period_end':'2026-06-30'}}
    result=bind_and_evaluate_existing_recipe(policy,recipe,packet,structural_packet=structural,cutoff='2026-08-14')
    ownership=result['bound']['claim_status']['nci_ownership_scope']
    assert ownership['components']['total_nci']==2_712_600_000
    assert ownership['components']['consolidated_vie_nci_subset']==1_831_600_000
    assert ownership['components']['nci_deducted_again'] is False
    assert result['bound']['inputs']['common_equity']==13_883_800_000


def test_residual_policy_does_not_assume_preferred_absent():
    recipe = _load(OUTPUT / "us-refresh-runtime" / "recipes" / "AFL.json")
    registry = _load(OUTPUT / "us-refresh-runtime" / "registry.json")
    entry = next(row for row in registry["entries"] if row["ticker"] == "AFL")
    policy = compile_residual_income_policy(recipe, entry)
    source = OUTPUT / "batch-33-sec-source-packets-20260903" / "AFL"
    packet = {"submissions": _load(source / "submissions.json"), "companyfacts": _load(source / "companyfacts.json"), "_selected_controlling_filing": {"accession": "0001628280-26-054618", "period_end": "2026-06-30"}}
    try:
        bind_and_evaluate_existing_recipe(policy, recipe, packet, structural_packet={"facts": [{"local_name": "PreferredStockValue", "value": 1}]}, cutoff="2026-08-14")
    except ValueError as exc:
        assert any(token in str(exc).lower() for token in ("preferred", "structural equity packet"))
    else:
        raise AssertionError("preferred claim absence must not be assumed")


def test_component_reconciliation_rejects_tampered_component_and_identity():
    structural = _load(OUTPUT / "batch-33-structural-replay-a-20260903" / "AFL" / "structural-filing.json")
    good = reconcile_common_equity_components(structural, cik="0000004977", accession="0001628280-26-054618", period_end="2026-06-30")
    assert good["value"] == 30312000000.0
    tampered = json.loads(json.dumps(structural))
    for row in tampered["facts"]:
        if row.get("local_name") == "StockholdersEquity" and row.get("dimensions") == [["us-gaap:StatementEquityComponentsAxis", "us-gaap:RetainedEarningsMember"]] and row.get("period_end") == "2026-06-30":
            row["value"] += 1.0
            break
    try:
        reconcile_common_equity_components(tampered, cik="0000004977", accession="0001628280-26-054618", period_end="2026-06-30")
    except ValueError as exc:
        assert "reconcile" in str(exc).lower()
    else:
        raise AssertionError("tampered equity component must be rejected")
    preferred = json.loads(json.dumps(structural))
    preferred["facts"].append({"source_accession": "0001628280-26-054618", "period_end": "2026-06-30", "unit": "USD", "local_name": "PreferredStockValue", "value": 1.0, "dimensions": [], "entity_identifier": "0000004977"})
    try:
        reconcile_common_equity_components(preferred, cik="0000004977", accession="0001628280-26-054618", period_end="2026-06-30")
    except ValueError as exc:
        assert "preferred" in str(exc).lower()
    else:
        raise AssertionError("nonzero preferred claim must be rejected")
    try:
        reconcile_common_equity_components(structural, cik="0000004977", accession="0001628280-26-000000", period_end="2026-06-30")
    except ValueError as exc:
        assert "accession" in str(exc).lower()
    else:
        raise AssertionError("source identity mismatch must be rejected")


@pytest.mark.parametrize('dimension', [
    ['us-gaap:StatementEquityComponentsAxis', 'issuer:RetainedEarningsMember'],
    [],
    'malformed',
])
def test_equity_component_requires_exact_taxonomy_member_and_dimension_pair(dimension):
    structural = _load(OUTPUT / 'batch-33-structural-replay-a-20260903' / 'AFL' / 'structural-filing.json')
    for row in structural['facts']:
        if row.get('dimensions') == [['us-gaap:StatementEquityComponentsAxis', 'us-gaap:RetainedEarningsMember']]:
            row['dimensions'] = [dimension]
    with pytest.raises(ValueError, match='component set is missing'):
        reconcile_common_equity_components(structural, cik='0000004977', accession='0001628280-26-054618', period_end='2026-06-30')


def test_reparsed_aapl_equity_proof_rejects_offsetting_claims_and_unknown_components():
    from copy import deepcopy
    structural = _load(OUTPUT/'us-refresh-aapl-source-verification/structural-filing.json')
    kwargs = {'cik':'0000320193','accession':'0000320193-26-000020','period_end':'2026-06-27'}
    proof = reconcile_no_outside_equity_claim(structural,**kwargs)
    assert proof['value'] == 0.
    assert proof['balance_totals']['Assets'] - proof['balance_totals']['Liabilities'] == proof['common_equity']['value']
    tampered = deepcopy(structural)
    base = next(row for row in structural['facts'] if row.get('qname') == 'us-gaap:StockholdersEquity' and not row.get('dimensions') and row.get('period_end') == '2026-06-27')
    tampered['facts'].extend([{**base,'qname':'us-gaap:MinorityInterest','local_name':'MinorityInterest','value':-100.},
                              {**base,'qname':'us-gaap:TemporaryEquityCarryingAmountAttributableToParent','local_name':'TemporaryEquityCarryingAmountAttributableToParent','value':100.}])
    with pytest.raises(ValueError,match='preferred|outside equity'):
        reconcile_no_outside_equity_claim(tampered,**kwargs)
    unknown = deepcopy(structural)
    unknown['facts'].append({**base,'dimensions':[['us-gaap:StatementEquityComponentsAxis','issuer:SpecialCapitalMember']],'value':0.})
    with pytest.raises(ValueError,match='unknown'):
        reconcile_no_outside_equity_claim(unknown,**kwargs)
