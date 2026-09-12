import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.us_valuation.newrefresh_family_policies import reconcile_no_outside_equity_claim

ROOT = Path(__file__).parents[2]


def packet():
    return json.loads((ROOT/'output/batch-30-structural-replay-a-20260901/BR/structural-filing.json').read_text())


def reconcile(source):
    return reconcile_no_outside_equity_claim(source,cik='0001383312',accession=source['source_accession'],period_end=source['report_date'])


def test_real_broadridge_closes_at_explicit_reported_precision():
    result = reconcile(packet())
    assert result['value'] == 0
    assert result['common_equity']['rounding_reconciliation']['reported_residual'] == 100000
    assert result['rounding_reconciliation']['reported_residual'] == -100000
    assert result['rounding_reconciliation']['maximum_rounding_difference'] == 150000


@pytest.mark.parametrize('mutation', ['large_gap','missing_precision','unknown_component','nonzero_nci'])
def test_precision_does_not_hide_missing_or_conflicting_economic_scope(mutation):
    source = packet()
    current = [r for r in source['facts'] if r.get('period_end') == source['report_date'] and r.get('period_start') is None]
    if mutation in ('large_gap','missing_precision'):
        for row in current:
            if row['qname'] == 'us-gaap:StockholdersEquity' and not row.get('dimensions'):
                if mutation == 'large_gap': row['value'] += 1000000
                else: row.pop('decimals',None)
    else:
        row = deepcopy(next(r for r in current if r['qname']=='us-gaap:StockholdersEquity' and not r.get('dimensions')))
        if mutation == 'unknown_component':
            row['dimensions'] = [['us-gaap:StatementEquityComponentsAxis','us-gaap:UnknownEquityMember']]
        else:
            row['qname'] = 'us-gaap:MinorityInterest'; row['local_name']='MinorityInterest'; row['value']=1
        source['facts'].append(row)
    with pytest.raises(ValueError):
        reconcile(source)
