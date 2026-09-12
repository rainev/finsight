"""Arithmetic reconciliation at explicitly reported, uniform XBRL precision."""
from decimal import Decimal
import re


def reconcile_reported_sum(total, components, *, cik, accession, period):
    rows = [total, *components]
    decimals = {str(row.get('decimals')) for row in rows}
    if len(decimals) != 1 or not re.fullmatch(r'-?\d{1,2}', next(iter(decimals))):
        raise ValueError('uniform explicit reported precision is required')
    precision = int(next(iter(decimals)))
    if not -9 <= precision <= 6:
        raise ValueError('reported precision is outside the supported range')
    for row in rows:
        if (row.get('source_accession') != accession or row.get('period_end') != period
            or row.get('period_start') is not None or row.get('unit') != 'USD'
            or str(row.get('entity_identifier','')).zfill(10) != cik
            or row.get('entity_scheme') != 'http://www.sec.gov/CIK'
            or not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',str(row.get('namespace','')))):
            raise ValueError('precision reconciliation source identity mismatch')
    values = [Decimal(str(row['value'])) for row in rows]
    if not all(value.is_finite() for value in values):
        raise ValueError('precision reconciliation needs finite amounts')
    residual = sum(values[1:]) - values[0]
    half_unit = Decimal(10) ** -precision / 2
    tolerance = half_unit * len(rows)
    if abs(residual) > tolerance:
        raise ValueError('components do not reconcile within reported precision')
    return {'reported_total':float(values[0]),'reported_component_sum':float(sum(values[1:])),
            'reported_residual':float(residual),'decimals':precision,
            'maximum_rounding_difference':float(tolerance),'interval_overlap':True,
            'source_contexts':[row.get('context_id') for row in rows]}
