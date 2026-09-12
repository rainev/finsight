import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_preferred_claims import met_preferred_claim

ROOT = Path(__file__).parents[2]


def source():
    return json.loads((ROOT/'output/batch-37-structural-sources-20260906/MET/structural-filing.json').read_bytes())


def resolve(packet):
    return met_preferred_claim(packet, accession=packet['source_accession'], period='2026-06-30', cutoff='2026-08-14')


def test_real_met_current_series_reconcile_prior_liquidation_claim():
    result = resolve(source())
    assert result['value'] == 2905000000.
    assert result['preference_reference_period'] == '2025-12-31'
    assert sum(result['series'].values()) == 24572200
    assert result['sources']


def test_current_reported_preference_is_not_labeled_as_old_claim_continuity():
    packet = source()
    current = dict(next(r for r in packet['facts'] if r.get('qname') == 'us-gaap:PreferredStockLiquidationPreferenceValue'))
    current.update(period_end='2026-06-30',value=3000000000.)
    packet['facts'].append(current)
    result = resolve(packet)
    assert result['value'] == 3000000000.
    assert result['status'] == 'reported_current_liquidation_preference'
    assert result['preference_reference_period'] == '2026-06-30'


@pytest.mark.parametrize('mutation', ['missing_amount','changed_series','missing_comparative','wrong_issuer'])
def test_no_unproved_preferred_carry_forward(mutation):
    packet = source()
    if mutation == 'missing_amount':
        packet['facts'] = [r for r in packet['facts'] if r.get('qname') != 'us-gaap:PreferredStockLiquidationPreferenceValue']
    elif mutation == 'missing_comparative':
        packet['facts'] = [r for r in packet['facts'] if not (r.get('qname') == 'us-gaap:PreferredStockSharesOutstanding' and r.get('period_end') == '2025-12-31')]
    else:
        row = next(r for r in packet['facts'] if r.get('qname') == 'us-gaap:PreferredStockSharesOutstanding' and r.get('period_end') == '2026-06-30' and r.get('dimensions'))
        if mutation == 'changed_series':
            row['value'] += 1
        else:
            row['entity_identifier'] = '0000000001'
    with pytest.raises(ValueError):
        resolve(packet)
