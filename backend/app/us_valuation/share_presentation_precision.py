"""Corroborate duplicate share presentations against an exact reported anchor.

No arbitrary percentage tolerance and no preference for the largest/smallest
count. Only a whole-share (or INF-precision) structural fact, corroborated by
CompanyFacts, can establish the anchor. Every sibling must reconcile to it.
"""
from decimal import Decimal, InvalidOperation
import re

SHARE_PRECISION_POLICY = 'FINSIGHT-SHARE-PRESENTATION-PRECISION-1'


def _amount(value):
    if isinstance(value, bool):
        raise ValueError('share count must be finite and positive')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('share count must be numeric') from exc
    if not result.is_finite() or result <= 0:
        raise ValueError('share count must be finite and positive')
    return result


def reconcile_share_presentations(rows, companyfacts_rows, *, cik, accession, start, end, concept):
    if concept != 'us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding' or not rows or not companyfacts_rows:
        raise ValueError('unsupported or empty share corroboration scope')
    values, precise, presentations = [], set(), []
    for row in rows:
        if (row.get('qname') != concept or row.get('source_accession') != accession
            or row.get('period_start') != start or row.get('period_end') != end
            or row.get('unit') not in {'shares','xbrli:shares'} or row.get('dimensions') != []
            or str(row.get('entity_identifier','')).zfill(10) != cik
            or row.get('entity_scheme') != 'http://www.sec.gov/CIK'
            or not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',str(row.get('namespace','')))):
            raise ValueError('share presentation source identity or period mismatch')
        amount = _amount(row.get('value'))
        decimals = str(row.get('decimals'))
        if decimals == 'INF':
            tolerance = Decimal(0)
            precise.add(amount)
        elif re.fullmatch(r'-?\d{1,2}',decimals) and -9 <= int(decimals) <= 0:
            tolerance = Decimal(10) ** -int(decimals) / 2
            if int(decimals)==0:
                precise.add(amount)
        else:
            raise ValueError('explicit supported share precision is required')
        values.append((amount,tolerance))
        presentations.append({'value':float(amount),'decimals':decimals,'context_id':row.get('context_id'),
            'maximum_rounding_difference':float(tolerance)})
    if len(precise)!=1:
        raise ValueError('unique precise structural share anchor is required')
    anchor = next(iter(precise))
    if any(abs(value-anchor)>tolerance for value,tolerance in values):
        raise ValueError('share presentations disagree outside explicit rounding precision')
    cf_values = []
    for row in companyfacts_rows:
        if row.get('accn') != accession or row.get('start') != start or row.get('end') != end:
            raise ValueError('CompanyFacts share corroboration period or accession mismatch')
        cf_values.append(_amount(row.get('val')))
    if anchor not in cf_values or any(value not in {amount for amount,_ in values} for value in cf_values):
        raise ValueError('CompanyFacts share values lack precise structural corroboration')
    return {'value':float(anchor),'exact_companyfacts_corroboration':True,
        'concept':concept,'cik':cik,'source_accession':accession,'period_start':start,'period_end':end,
        'reported_presentations':presentations,'companyfacts_presentations':[float(value) for value in cf_values]}
