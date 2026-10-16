"""Governed preferred-claim continuity, without confusing par and liquidation value."""
from copy import deepcopy

from .calculation_recipe import number


def met_preferred_claim(structural, *, accession, period, cutoff):
    """Reuse MET's approved liquidation-preference basis only for an unchanged stack.

    The controlling filing must itself report the earlier aggregate preference
    and matching current/comparative outstanding series. Any changed or missing
    series blocks continuity; an old dollar amount alone is not sufficient.
    """
    if structural.get('source_accession') != accession or structural.get('filed_date','9999') > cutoff:
        raise ValueError('preferred continuity structural identity/cutoff mismatch')
    facts = [r for r in structural.get('facts', []) if r.get('period_start') is None]
    relevant = [r for r in facts if r.get('qname') in {
        'us-gaap:PreferredStockLiquidationPreferenceValue', 'us-gaap:PreferredStockSharesOutstanding'}]
    if any(str(r.get('entity_identifier','')).zfill(10) != '0001099219'
           or r.get('source_accession') != accession for r in relevant):
        raise ValueError('MET preferred continuity source identity mismatch')
    values = [r for r in relevant if r.get('qname') == 'us-gaap:PreferredStockLiquidationPreferenceValue'
              and r.get('unit') == 'USD' and not r.get('dimensions') and r.get('period_end','') <= period]
    if not values:
        raise ValueError('MET filing does not report a liquidation-preference amount')
    previous = max(r['period_end'] for r in values)
    values = [r for r in values if r['period_end'] == previous]
    amounts = {number(r['value'],'liquidation preference') for r in values}
    if len(amounts) != 1 or min(amounts) <= 0:
        raise ValueError('MET liquidation preference is conflicting or nonpositive')
    sources = list(values)

    def stack(end):
        rows = [r for r in relevant if r.get('qname') == 'us-gaap:PreferredStockSharesOutstanding'
                and r.get('period_end') == end and r.get('unit') in {'shares','xbrli:shares'}]
        selected = {}
        totals = set()
        for row in rows:
            value = number(row['value'],'preferred shares')
            if value < 0:
                raise ValueError('negative preferred shares')
            dims = row.get('dimensions')
            if not dims:
                totals.add(value)
                continue
            if len(dims) != 1 or dims[0][0] != 'us-gaap:StatementClassOfStockAxis':
                raise ValueError('unfamiliar preferred-share dimension')
            member = dims[0][1]
            if not member.startswith('us-gaap:Series') or not member.endswith('PreferredStockMember'):
                if value != 0:
                    raise ValueError('unfamiliar preferred series requires review')
                continue
            if member in selected and selected[member] != value:
                raise ValueError('conflicting preferred series shares')
            selected[member] = value
        if not selected or len(totals) != 1 or abs(sum(selected.values())-next(iter(totals))) > .01:
            raise ValueError('preferred series do not reconcile to reported total')
        sources.extend(rows)
        return selected

    current_stack = stack(period)
    # A contemporaneously reported liquidation amount is direct evidence,
    # not continuity inferred by comparing the current stack to itself.
    direct_current = previous == period
    previous_stack = stack(previous) if not direct_current else None
    if not direct_current and current_stack != previous_stack:
        raise ValueError('preferred series changed; prior liquidation preference cannot be carried forward')
    return {'value':amounts.pop(), 'status':'reported_current_liquidation_preference' if direct_current else 'reported_liquidation_preference_with_unchanged_series',
            'period_end':period, 'preference_reference_period':previous, 'source_accession':accession,
            'series':current_stack, 'sources':deepcopy(sources)}
