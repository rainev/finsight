from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_reported_claim_scope import (
    REPORTED_NCI_SCOPE_RULES, reported_nci_field_availability, ClaimScopeReviewRequired,
)
from app.us_valuation.refresh_acquisition_claims import (
    ordinary_nci_mapping_acquisition_policy, select_acquisition_claim,
)
from app.us_valuation.refresh_bridge_scope_policies import (
    PREFERRED_EQUITY_ZERO_RULES, preferred_equity_zero_availability, BridgeScopeReviewRequired,
)

ROOT=Path(__file__).resolve().parents[2]
SOURCES={
    'ETN':'batch-24-structural-sources-20260831/ETN/structural-filing.json',
    'HCA':'batch-14-structural-sources-20260829/HCA/structural-filing.json',
    'HON':'batch-22-structural-sources-corrected-20260831/HON/structural-filing.json',
}

def source(ticker):
    from app.us_valuation.refresh_source_ingestion import _validate_structural_payload
    structural=json.loads((ROOT/'output'/SOURCES[ticker]).read_bytes())
    recipe=json.loads((ROOT/'output/us-refresh-runtime/recipes'/f'{ticker}.json').read_bytes())
    private=json.loads(Path(recipe['provenance']['source_path']).read_bytes())['history_backed']
    filing=private['source_ledger']['controlling_filing']
    structural=_validate_structural_payload(structural,cik=REPORTED_NCI_SCOPE_RULES[ticker].cik,
        filing={'accession':filing['accession'],'report_date':filing['period_end'],'form':filing['form']})
    return structural, {'accessionNumber':filing['accession'],'reportDate':filing['period_end'],
        'filingDate':filing['filed'],'form':filing['form']}

@pytest.mark.parametrize('ticker,total',[('ETN',45_000_000),('HCA',3_433_000_000),('HON',320_000_000)])
def test_current_ordinary_nci_reconciles_to_parent_and_member_without_owner_flows(ticker,total):
    structural,filing=source(ticker)
    availability,proof=reported_nci_field_availability(ticker=ticker,policy=asdict(REPORTED_NCI_SCOPE_RULES[ticker]),
        structural_packet=structural,accession=filing['accessionNumber'],period_end=filing['reportDate'])
    assert availability.value==proof['source_total']==total
    eq=proof['equity_reconciliation']
    assert eq['consolidated_equity']-eq['parent_equity']==eq['nci_equity_member']==total
    assert proof['duration_diagnostics']
    if ticker=='HCA':assert eq['parent_equity']==-6_642_000_000
    if ticker=='HON':assert any(r['qname']=='us-gaap:NoncontrollingInterestDecreaseFromDeconsolidation'
        and r['value']==703_000_000 for r in proof['duration_diagnostics'])

def test_equity_member_mismatch_does_not_pass_by_matching_nci_tag():
    structural,filing=source('ETN');changed=deepcopy(structural)
    for row in changed['facts']:
        if row['qname']=='us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest' and dict(row.get('dimensions') or []).get('us-gaap:StatementEquityComponentsAxis')=='us-gaap:NoncontrollingInterestMember':row['value']+=1_000_000
    with pytest.raises(ClaimScopeReviewRequired,match='does not reconcile'):
        reported_nci_field_availability(ticker='ETN',policy=asdict(REPORTED_NCI_SCOPE_RULES['ETN']),structural_packet=changed,
            accession=filing['accessionNumber'],period_end=filing['reportDate'])

def test_etn_acquisition_views_count_once_and_paid_cash_is_excluded():
    structural,filing=source('ETN');policy=ordinary_nci_mapping_acquisition_policy('ETN')
    result=select_acquisition_claim(policy,structural,filing,policy['cik'],'2026-08-14')
    assert result['status']=='source_bound' and result['claim_adjustment']==32_000_000
    assert result['components']['acquisition_alias_is_not_additive']==32_000_000
    assert 11_079_000_000 in result['components']['acquisition_cash_is_not_added']
    changed=deepcopy(structural);row=next(r for r in changed['facts'] if r['qname']==policy['qname'] and not r.get('dimensions') and r['period_end']==filing['reportDate']);extra=deepcopy(row);extra['qname']+='Current';extra['local_name']+='Current';changed['facts'].append(extra)
    with pytest.raises(ValueError,match='unlisted current'):
        select_acquisition_claim(policy,changed,filing,policy['cik'],'2026-08-14')

def test_etn_common_only_equity_uses_declared_source_precision_not_invented_component():
    structural,filing=source('ETN');policy=dict(PREFERRED_EQUITY_ZERO_RULES['ETN'])
    value,proof=preferred_equity_zero_availability(ticker='ETN',policy=policy,structural_packet=structural,
        accession=filing['accessionNumber'],period_end=filing['reportDate'])
    assert value.value==0 and proof['rounding_residual']==1_000_000
    assert proof['source_rounding_tolerance']==2_500_000
    changed=deepcopy(structural)
    for row in changed['facts']:
        if row['qname']=='us-gaap:CommonStockValueOutstanding':row['decimals']='-7'
    with pytest.raises(BridgeScopeReviewRequired,match='too coarse'):
        preferred_equity_zero_availability(ticker='ETN',policy=policy,structural_packet=changed,
            accession=filing['accessionNumber'],period_end=filing['reportDate'])
    changed=deepcopy(structural)
    preferred=deepcopy(next(row for row in changed['facts'] if row['qname']=='us-gaap:CommonStockValueOutstanding'
        and not row.get('dimensions') and row['period_end']==filing['reportDate']))
    preferred.update(qname='us-gaap:PreferredStockValue',local_name='PreferredStockValue',value=1_000_000)
    changed['facts'].append(preferred)
    with pytest.raises(BridgeScopeReviewRequired,match='nonzero preferred'):
        preferred_equity_zero_availability(ticker='ETN',policy=policy,structural_packet=changed,
            accession=filing['accessionNumber'],period_end=filing['reportDate'])

def test_partial_mappings_do_not_clear_unrelated_implementation_blockers():
    from app.us_valuation.refresh_operating_policies import _policy_for_entry
    from app.us_valuation.xbrl import load_concept_config
    root=ROOT/'output/us-refresh-runtime';registry=json.loads((root/'registry.json').read_bytes())
    for ticker,reason in [('HCA','professional_liability_forward_cash_overlap_requires_rule'),
                         ('HON','completed_separation_split_and_subsequent_acquisition_require_scope_rollforward')]:
        entry=next(r for r in registry['entries'] if r['ticker']==ticker)
        result=_policy_for_entry(entry,artifact=json.loads((root/'baseline/artifacts'/f'{ticker}.json').read_bytes()),
            recipe=json.loads((root/'recipes'/f'{ticker}.json').read_bytes()),source_evidence=None,concept_config=load_concept_config())
        assert reason in result.reason_codes and 'baseline_non_debt_claim_scope_requires_source_rule' in result.reason_codes
