"""Opt-in reported-debt scope assumption for private staged refreshes only."""
from copy import deepcopy
from datetime import date
import re

from .bridge_policy import BridgeAssessment, BridgeRange, _bounded_review_warning
from .calculation_recipe import evaluate_scenario, number
from .family_forecast import fact
from .reliability import accounting_label
from .sec_client import normalize_cik

VERSION = 'US-STAGED-REPORTED-DEBT-LEASE-1'


def validate_authorization(scope, entry, *, staged_only):
    if staged_only is not True:
        raise ValueError('reported-debt fallback requires staged-only execution')
    approval = scope.get('authorization', {})
    if (scope.get('version') != VERSION or scope.get('cash_scope') != 'reported_cash_only'
            or approval.get('decision') != 'confirmed_staged_only'
            or approval.get('ticker') != entry.get('ticker')
            or normalize_cik(approval.get('cik')) != normalize_cik(entry.get('cik'))
            or not re.fullmatch(r'[0-9a-f]{64}', str(approval.get('review_receipt_sha256', '')))):
        raise ValueError('staged lease scope lacks matching reviewed authorization')
    date.fromisoformat(approval['review_date'])


def claim_envelope(packet, disclosure, liabilities, current, noncurrent, aggregate):
    # Statement rows are source-checked, subtotal-resolved and ownership-closed
    # by shared_bridge before this function. Do not infer a missing lease zero.
    from .shared_statement_bridge import source_radius
    rows = disclosure['debt_rows']
    recorded = sum(r['value'] for r in rows)
    lease_names = {'FinanceLeaseLiabilityCurrent', 'FinanceLeaseLiabilityNoncurrent',
                   'CapitalLeaseObligationsCurrent', 'CapitalLeaseObligationsNoncurrent'}
    dedicated = [r for r in rows if r['source']['qname'].split(':')[-1] in lease_names]
    if disclosure['all_leases_operating'] and any(s is not None and s['value'] > 0 for s in (current, noncurrent, aggregate)):
        raise ValueError('operating-only disclosure conflicts with finance-lease balances')
    if any(r['includes_finance_leases'] for r in rows if r not in dedicated) and any(
            s is not None and s['value'] > 0 for s in (current, noncurrent, aggregate)):
        raise ValueError('known lease claim overlaps combined debt; disjoint scope required')
    known = []
    for source in (current, noncurrent):
        if source is None:
            continue
        if source['value'] < 0:
            raise ValueError('negative lease claim requires reconciliation')
        matches = [r for r in dedicated if r['source']['qname'] == source['qname']]
        if matches:
            if len(matches) != 1 or matches[0]['source']['context_id'] != source['context_id'] or matches[0]['value'] != source['value']:
                raise ValueError('dedicated lease row conflicts with selected source')
        else:
            known.append(source)
    if aggregate is not None:
        if aggregate['value'] < 0:
            raise ValueError('negative aggregate lease claim')
        if current is not None and noncurrent is not None:
            residual = abs(aggregate['value'] - current['value'] - noncurrent['value'])
            if residual > sum(source_radius(packet, s) for s in (aggregate, current, noncurrent)) + 1e-8:
                raise ValueError('aggregate lease claim conflicts with maturity components')
        elif dedicated:
            raise ValueError('aggregate and partial dedicated lease rows need disjoint scope')
        else:
            known = [aggregate]
    minimum = sum(s['value'] for s in known)
    operating = [s for s in (fact(packet, ['OperatingLeaseLiabilityCurrent'], optional=True),
                             fact(packet, ['OperatingLeaseLiabilityNoncurrent'], optional=True)) if s]
    if any(s['value'] < 0 for s in operating):
        raise ValueError('negative operating lease claim')
    rounding = (source_radius(packet, liabilities)
                + sum(source_radius(packet, r['source']) for r in rows)
                + sum(source_radius(packet, s) for s in operating))
    maximum = liabilities['value'] - recorded - sum(s['value'] for s in operating) + rounding
    if maximum < minimum or not rows:
        raise ValueError('recognized liability envelope does not cover identified lease claims')
    return {'version': VERSION, 'recorded_debt': recorded, 'additional_minimum': minimum,
            'additional_maximum': maximum, 'known_uncovered_lease_sources': known,
            'liabilities_source': liabilities, 'operating_lease_sources': operating,
            'reported_rounding_allowance': rounding,
            'base_classification': 'explicit_staged_scope_assumption_not_reported_zero',
            'limitation': 'Recognized book-liability stress only; not a bound on off-balance commitments or fair values.'}


def assess_staged_stress(bridge, recipe, valued):
    proof = bridge['shared_statement_bridge']['staged_lease_fallback']
    delta = proof['additional_maximum'] - proof['additional_minimum']
    stress = {}
    for name, original in recipe['scenarios'].items():
        spec = deepcopy(original)
        debt_key = {'enterprise_cash_fcff': 'interest_bearing_debt', 'constant_growth_fcff': 'debt'}.get(spec['engine'])
        if debt_key is None:
            raise ValueError('staged lease fallback requires an existing enterprise cash model')
        if spec['inputs'][debt_key] != bridge['resolution']['total_debt']['midpoint']:
            raise ValueError('operating debt differs from approved reported-debt base')
        spec['inputs'][debt_key] += delta
        result = evaluate_scenario(spec)
        if number(result['raw_value'], 'raw lease stress') <= 0:
            raise ValueError('broad lease stress erases raw equity; prior estimate retained')
        stress[name] = result['raw_value']
    base = valued['scenarios']['base']['raw_value']
    if base <= 0:
        raise ValueError('nonpositive staged equity base')
    spread = (base - stress['base']) / base
    resolution = bridge['resolution']
    assessment = BridgeAssessment(decision='bounded_review', usable=True,
        intrinsic_value_range=BridgeRange(stress['base'], base, base),
        spread_ratio=spread, spread_limit=.01, accounting_impact_ratio=spread,
        reliability_cap=accounting_label(spread), bounded_fields=('finance_lease_current', 'finance_lease_noncurrent'),
        blocking_fields=(), reason_codes=tuple(resolution['reason_codes']),
        warning=_bounded_review_warning(spread), policy_version=VERSION)
    return {**assessment.as_dict(), 'complete': False}, {
        'version': VERSION, 'raw_scenario_values': stress,
        'base_stress': assessment.intrinsic_value_range.as_dict(), 'additional_claim_stress': delta,
        'separate_from_operating_scenarios': True, 'limitation': proof['limitation']}
