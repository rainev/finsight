"""Reviewed, dated after-tax adjustments; never generic non-GAAP addbacks."""
from copy import deepcopy
from math import isfinite, isclose


ALLOWED={'completed_transaction_cost','disposed_business_gain','one_time_tax_interest'}


def normalize_earnings(state, packet, record):
    source=state['sources']['common_earnings'];filing=packet['controlling_filing']
    if record['accession']!=filing['accessionNumber'] or str(record['cik']).zfill(10)!=str(packet['submissions']['cik']).zfill(10):
        raise ValueError('one-off review requires the same issuer and filing; review new filings separately')
    if record['period_start']!=source['period_start'] or record['period_end']!=source['period_end']:
        raise ValueError('one-off review period mismatch')
    scope='continuing_common' if state['continuing_scope'] else 'common'
    if record['scope']!=scope or record['currency']!='USD' or record['basis']!='after_tax_attributable_to_common':
        raise ValueError('one-off ownership, tax or currency scope mismatch')
    if not isclose(record['reported_earnings'],source['value'],rel_tol=1e-9,abs_tol=1):
        raise ValueError('one-off reconciliation does not start at reported common earnings')
    if not record.get('document_sha256') or not record.get('source_url') or not record.get('review_reason'):
        raise ValueError('one-off source evidence missing')
    seen=set();delta=0.
    for item in record['items']:
        if item['id'] in seen:raise ValueError('duplicate one-off event')
        seen.add(item['id'])
        amount=item['after_tax_adjustment']
        if isinstance(amount,bool) or not isinstance(amount,(int,float)) or not isfinite(amount):raise ValueError('invalid one-off amount')
        if item['category'] not in ALLOWED or not item.get('source_row') or not item.get('reason'):
            raise ValueError('unsupported one-off category or evidence')
        if (item['category']=='completed_transaction_cost' and amount<0) or (item['category']!='completed_transaction_cost' and amount>0):
            raise ValueError('one-off adjustment sign mismatch')
        delta+=amount
    result=deepcopy(state)
    result['earnings']=(source['value']+delta)*state['annualization_factor']
    # Actual book, cash, debt and share count do not change when forecasting
    # without a historical one-off. Never add the same expense to book as well.
    result['earnings_normalization']={'reported_period_earnings':source['value'],
        'after_tax_period_adjustment':delta,'normalized_period_earnings':source['value']+delta,
        'annualization_factor':state['annualization_factor'],'record':deepcopy(record)}
    return result
