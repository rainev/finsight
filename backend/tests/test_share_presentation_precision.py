import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.us_valuation.share_presentation_precision import reconcile_share_presentations

ROOT = Path(__file__).resolve().parents[2] / 'output'
CASES = [
    ('APO','batch-40-structural-sources-20260907','batch-40-source-replay-a-20260907','2026-01-01','2026-06-30',593298193),
    ('BLK','batch-40-structural-sources-20260907','batch-40-source-replay-a-20260907','2026-01-01','2026-06-30',164823915),
    ('FITB','batch-33-structural-replay-b-20260903','batch-33-sec-source-replay-a-20260903','2026-01-01','2026-06-30',873353249),
    ('IBM','batch-26-structural-replay-b-20260831','batch-26-sec-replay-b-20260831','2026-01-01','2026-06-30',952697295),
    ('SNA','batch-20-structural-replay-b','batch-20-source-replay-b','2026-01-04','2026-07-04',52611800),
]
CONCEPT = 'us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding'


def source(case):
    ticker, structural_dir, cf_dir, start, end, expected = case
    structural = json.loads((ROOT/structural_dir/ticker/'structural-filing.json').read_text())
    facts = json.loads((ROOT/cf_dir/ticker/'companyfacts.json').read_text())
    accession = structural['source_accession']
    rows = [row for row in structural['facts'] if row.get('qname')==CONCEPT and row.get('dimensions')==[]
        and row.get('period_start')==start and row.get('period_end')==end]
    cf = [row for row in facts['facts']['us-gaap'][CONCEPT.split(':')[1]]['units']['shares']
        if row.get('accn')==accession and row.get('start')==start and row.get('end')==end]
    context = dict(cik=str(facts['cik']).zfill(10), accession=accession, start=start, end=end, concept=CONCEPT)
    return rows, cf, context, expected


@pytest.mark.parametrize('case',CASES,ids=[case[0] for case in CASES])
def test_real_exact_and_rounded_presentations_reconcile_without_changing_source(case):
    rows, cf, context, expected = source(case)
    before = deepcopy((rows,cf))
    proof = reconcile_share_presentations(rows,cf,**context)
    assert proof['value']==expected
    assert proof['exact_companyfacts_corroboration'] is True
    assert len(proof['reported_presentations'])==len(rows)
    assert (rows,cf)==before


@pytest.mark.parametrize('field,value',[
    ('entity_identifier','0000000001'),('entity_scheme','invalid'),('unit','USD'),
    ('namespace','https://example.invalid/us-gaap/2026'),('period_start','2026-04-01'),
    ('dimensions',[['custom:Axis','custom:Member']]),('source_accession','wrong'),
    ('decimals',None),('value',float('nan')),
])
def test_unsafe_structural_sibling_is_not_ignored(field,value):
    rows, cf, context, _ = source(CASES[0])
    rows[0][field]=value
    with pytest.raises(ValueError):
        reconcile_share_presentations(rows,cf,**context)


def test_unknown_cf_value_or_conflicting_precise_fact_remains_a_conflict():
    rows,cf,context,_ = source(CASES[0])
    bad = {**cf[0],'val':123456789}
    with pytest.raises(ValueError):
        reconcile_share_presentations(rows,[*cf,bad],**context)
    precise = next(row for row in rows if str(row['decimals'])=='0')
    with pytest.raises(ValueError):
        reconcile_share_presentations([*rows,{**precise,'value':precise['value']+1}],cf,**context)


def test_no_exact_anchor_and_outside_rounding_interval_are_rejected():
    rows,cf,context,_ = source(CASES[0])
    rounded = [row for row in rows if str(row['decimals'])!='0']
    with pytest.raises(ValueError):
        reconcile_share_presentations(rounded,cf,**context)
    rounded[0]['value'] += 1000000
    with pytest.raises(ValueError):
        reconcile_share_presentations(rows,cf,**context)


def test_family_binding_versions_precision_rule_and_preserves_raw_packet():
    from app.us_valuation.newrefresh_family_policies import bind_residual_income_sources,compile_residual_income_policy
    ticker,structural_dir,cf_dir,start,end,expected = CASES[0]
    load = lambda path: json.loads(path.read_text())
    structural = load(ROOT/structural_dir/ticker/'structural-filing.json')
    packet = {'submissions':load(ROOT/cf_dir/ticker/'submissions.json'),
        'companyfacts':load(ROOT/cf_dir/ticker/'companyfacts.json'),
        '_selected_controlling_filing':{'accession':structural['source_accession'],'period_end':end}}
    recipe = load(ROOT/'us-refresh-runtime/recipes'/f'{ticker}.json')
    entry = next(row for row in load(ROOT/'us-refresh-runtime/registry.json')['entries'] if row['ticker']==ticker)
    policy = compile_residual_income_policy(recipe,entry)
    before = deepcopy(packet)
    bound = bind_residual_income_sources(policy,packet,structural_packet=structural,cutoff='2026-08-14')
    assert bound['inputs']['diluted_shares']==expected
    assert bound['source_rows']['structural_supplements']['corroborated_share_precision']
    assert packet==before
    policy.pop('share_precision_policy')
    with pytest.raises(ValueError,match='CompanyFacts/structural amount conflict'):
        bind_residual_income_sources(policy,packet,structural_packet=structural,cutoff='2026-08-14')
