import json
from dataclasses import replace
from pathlib import Path
import pytest
from app.us_valuation.history import CompanyHistoryProfile,HistoryMetric,HistoryObservation
from app.us_valuation.history import summarize_history_metric
from app.us_valuation.refresh_financials import (
    ANNUAL_ONLY_CASH_MARGIN_POLICY,
    ANNUAL_ONLY_EXCLUSION_PROVENANCE_SCHEMA,
    preserve_cash_observation_policy,
)
from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.catalog import sha256_bytes
from app.us_valuation.refresh_operating_policies import compile_operating_policy_registry

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'output/us-refresh-runtime/source-validation/3a947cdb8dbf5bdc23c52a45a224b6c6bb3462f4f70e4bb54a5499ba8071efd0'
ORIGINAL={
    'GILD': ROOT/'output/batch-14-history/candidate-a/generated/GILD/valuation-private.json',
    'INCY': ROOT/'output/batch-14-history/final-a/generated/INCY/valuation-private.json',
}


def _provenance(ticker):
    path=ORIGINAL[ticker]
    private=json.loads(path.read_text())['history_backed']
    return {
        'schema_version':ANNUAL_ONLY_EXCLUSION_PROVENANCE_SCHEMA,
        'cik':private['source_ledger']['controlling_filing'].get('cik',
            {'GILD':'0000882095','INCY':'0000879169'}[ticker]),
        'source_path':str(path.relative_to(ROOT)),
        'source_sha256':sha256_bytes(path.read_bytes()),
        'source_field':'history_backed.governed_assumptions.normalization_exclusions',
        'exclusions':list(private['governed_assumptions']['normalization_exclusions']),
    }

@pytest.mark.parametrize('ticker,cik,expected',[('GILD','0000882095',0.3513762610322619),('INCY','0000879169',0.19100435426571033)])
def test_real_receipt_restores_approved_annual_only_median(ticker,cik,expected):
    raw=json.loads((EVIDENCE/f'{ticker}.json').read_text())['ledger']['normalization']['profile']
    metrics=[]
    for m in raw['metrics']:
        observations=tuple(HistoryObservation(**{**o,'sources':tuple(o['sources'])}) for o in m['observations'])
        metrics.append(HistoryMetric(**{**m,'observations':observations}))
    profile=CompanyHistoryProfile(**{**raw,'metrics':tuple(metrics),'annual_periods':tuple(raw['annual_periods'])})
    original=profile.metric('cash_conversion_margin')
    assert any(o.period_role=='operating_ttm' for o in original.observations)
    revised=preserve_cash_observation_policy(profile,{
        'cash_observation_policy':ANNUAL_ONLY_CASH_MARGIN_POLICY,
        'cash_observation_policy_provenance':_provenance(ticker),
    },cik)
    metric=revised.metric('cash_conversion_margin')
    assert metric.base==pytest.approx(expected)
    assert metric.observations==tuple(o for o in original.observations if o.period_role=='annual')
    assert profile.metric('cash_conversion_margin')==original
    with pytest.raises(ValueError,match='provenance'):
        preserve_cash_observation_policy(profile,{'cash_observation_policy':ANNUAL_ONLY_CASH_MARGIN_POLICY},cik)
    with pytest.raises(ValueError,match='issuer'):
        preserve_cash_observation_policy(profile,{
            'cash_observation_policy':ANNUAL_ONLY_CASH_MARGIN_POLICY,
            'cash_observation_policy_provenance':_provenance(ticker),
        },'0000320193')


def test_annual_only_policy_preserves_negative_annual_observation() -> None:
    raw=json.loads((EVIDENCE/'GILD.json').read_text())['ledger']['normalization']['profile']
    metrics=[]
    for m in raw['metrics']:
        observations=tuple(HistoryObservation(**{**o,'sources':tuple(o['sources'])}) for o in m['observations'])
        if m['name']=='cash_conversion_margin':
            observations=tuple(replace(o,value=-0.20) if o.period_role=='annual' and o.period_end=='2021-12-31' else o for o in observations)
            revised_metric=summarize_history_metric(m['name'],observations)
            metrics.append(revised_metric)
        else:
            metrics.append(HistoryMetric(**{**m,'observations':observations}))
    profile=CompanyHistoryProfile(**{**raw,'metrics':tuple(metrics),'annual_periods':tuple(raw['annual_periods'])})
    revised=preserve_cash_observation_policy(profile,{
        'cash_observation_policy':ANNUAL_ONLY_CASH_MARGIN_POLICY,
        'cash_observation_policy_provenance':_provenance('GILD'),
    },'0000882095')
    metric=revised.metric('cash_conversion_margin')
    assert [o.value for o in metric.observations if o.period_role=='annual'][0] == pytest.approx(-0.20)
    assert all(o.period_role=='annual' for o in metric.observations)


@pytest.mark.parametrize('ticker', ['GILD','INCY'])
def test_original_packet_exclusion_and_scenario_derivation_are_pinned(ticker):
    private=json.loads(ORIGINAL[ticker].read_text())['history_backed']
    exclusions=private['governed_assumptions']['normalization_exclusions']
    assert len(exclusions)==1 and 'Current TTM cash margin excluded' in exclusions[0]
    revenue=private['reported_inputs']['ttm_revenue']
    for row in private['scenario_rows']:
        assert row['starting_cash_fcff']==pytest.approx(revenue*row['cash_conversion_margin'])


@pytest.mark.parametrize('ticker', ['GILD','INCY'])
def test_current_source_validation_recipe_derives_cash_fcff_from_filtered_margin(ticker):
    receipt=json.loads((EVIDENCE/f'{ticker}.json').read_text())
    normalization=receipt['ledger']['normalization']
    recipe=receipt['recipe']
    for case, scenario in zip(('low','base','high'), ('bear','base','bull')):
        expected=normalization['reported']['revenue']*normalization['cash_conversion_margin'][case]
        assert recipe['scenarios'][scenario]['inputs']['cash_fcff']==pytest.approx(expected)
    replay=evaluate_recipe(recipe)['range']
    assert replay==pytest.approx(receipt['result']['range'])


def test_compiled_policy_retains_original_exclusion_lineage() -> None:
    compiled=compile_operating_policy_registry(
        registry_path=ROOT/'output/us-refresh-runtime/registry.json',
        artifacts_dir=ROOT/'output/us-refresh-runtime/baseline/artifacts',
        recipes_dir=ROOT/'output/us-refresh-runtime/recipes',
    )
    for ticker in ('GILD','INCY'):
        policy=next(row['policy'] for row in compiled['results'] if row['ticker']==ticker)
        lineage=policy['inputs']['base_cash_margin']['cash_observation_policy_provenance']
        expected=_provenance(ticker)
        assert lineage['source_path']==expected['source_path']
        assert lineage['source_sha256']==expected['source_sha256']
        assert lineage['exclusions']==expected['exclusions']
