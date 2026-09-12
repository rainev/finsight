from __future__ import annotations

import copy,json
from pathlib import Path

import pytest

from app.us_valuation.refresh_preferred_lifecycle import (
    PreferredLifecycleReviewRequired, bind_preferred_lifecycle, preferred_lifecycle_policy,
)


ROOT=Path(__file__).resolve().parents[2]
SOURCES={
    'COHR':ROOT/'output/batch-27-structural-sources-20260831/COHR/structural-filing.json',
    'WMB':ROOT/'output/batch-35-structural-sources-20260904/WMB/structural-filing.json',
}


def _bind(ticker):
    structural=json.loads(SOURCES[ticker].read_bytes());policy=preferred_lifecycle_policy(ticker)
    return bind_preferred_lifecycle(ticker=ticker,policy=policy,structural=structural,
        accession=structural['source_accession'],period=structural['report_date'])


def test_cohr_settled_conversion_proves_zero_current_preferred_claim():
    availability,proof=_bind('COHR')
    assert availability.state=='evidence_backed_zero' and availability.value==0
    assert proof['mode']=='settled_conversion_zero'
    assert proof['components']=={
        'current_carrying_value':0.0,'current_redemption_value':0.0,
        'current_shares_outstanding':0.0,'current_shares_issued':0.0,
        'converted_preferred_shares':215_000.0,
        'converted_preferred_value':-2_506_885_000.0,
        'common_share_conversion_effect':12_419_000.0,
    }


def test_wmb_current_carrying_claim_is_not_par_or_nci():
    availability,proof=_bind('WMB')
    assert availability.state=='reported' and availability.value==35_000_000
    assert proof['components']=={
        'current_carrying_value':35_000_000.0,'current_shares_issued':35_000.0,
        'par_value_per_share':1.0,'equity_component':35_000_000.0,
        'par_is_not_claim_measure':True,
    }


def test_preferred_lifecycle_policy_has_no_filing_amounts_or_dates_and_fails_closed():
    policy=preferred_lifecycle_policy('COHR')
    assert not {'accession','filed_date','period_end','amount'}&set(policy)
    structural=json.loads(SOURCES['COHR'].read_bytes())
    row=next(item for item in structural['facts'] if item.get('local_name')=='TemporaryEquitySharesOutstanding'
             and item.get('period_end')==structural['report_date'] and not item.get('dimensions'))
    changed=copy.deepcopy(structural);changed['facts'][structural['facts'].index(row)]['value']=1
    with pytest.raises(PreferredLifecycleReviewRequired,match='nonzero current balance'):
        bind_preferred_lifecycle(ticker='COHR',policy=policy,structural=changed,
            accession=changed['source_accession'],period=changed['report_date'])
