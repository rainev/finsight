import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_operating_policies import _policy_for_entry
from app.us_valuation.refresh_financials import cash_history
from app.us_valuation.xbrl import CompanyFactsNormalizer, load_concept_config

ROOT = Path(__file__).parents[2]


def test_broadridge_total_investment_includes_separate_software_cash_outflow():
    runtime = ROOT/'output/us-refresh-runtime'
    entry = next(row for row in json.loads((runtime/'registry.json').read_text())['entries'] if row['ticker']=='BR')
    recipe = json.loads((runtime/'recipes/BR.json').read_text())
    public = json.loads((runtime/'baseline/artifacts/BR.json').read_text())
    policy = _policy_for_entry(entry,artifact=public,recipe=recipe,source_evidence=None,concept_config=load_concept_config()).policy
    source = ROOT/'output/batch-30-sec-replay-a-20260901/BR'
    submissions = json.loads((source/'submissions.json').read_text())
    facts = json.loads((source/'companyfacts.json').read_text())
    recent = submissions['filings']['recent']
    records = [{key:values[i] for key,values in recent.items() if isinstance(values,list) and i<len(values)} for i in range(len(recent['accessionNumber']))]
    normalizer = CompanyFactsNormalizer(facts,concept_config=policy['concept_config'],fiscal_year_end=submissions['fiscalYearEnd'],as_of_date='2026-08-14',filing_records=records)
    rule = policy['inputs']['base_cash_margin']
    total = cash_history(normalizer,period='2026-06-30',cutoff='2026-08-14',rule=rule)
    ppe_only = cash_history(normalizer,period='2026-06-30',cutoff='2026-08-14',rule={k:v for k,v in rule.items() if k!='additional_capex_fields'})
    assert total['reported']['capital_expenditures'] == 67200000
    assert total['additional_capex_components'] == {'capitalized_software':45400000}
    assert total['total_capital_spending'] == 112600000
    assert ppe_only['ttm_cash_fcff'] - total['ttm_cash_fcff'] == pytest.approx(45400000)
    annual = {row['period_end']:row for row in total['annual']}
    assert annual['2025-06-30']['capitalized_software']['value'] == 71100000
    assert annual['2024-06-30']['capitalized_software']['value'] == 55600000
    assert len(annual) == 5
