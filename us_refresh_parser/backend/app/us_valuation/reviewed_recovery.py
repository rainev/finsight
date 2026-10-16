"""Filing-pinned, private source bindings for the provisional BG and ALGN recipes.

The review record is a policy input. A new filing needs a new record; this
module never chooses an earnings basis, financing adjustment, or legal loss.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite, isclose
import re

from .calculation_recipe import evaluate_recipe
from .sec_client import normalize_cik
from .xbrl import CompanyFactsNormalizer, load_concept_config


SCHEMA = 'FINSIGHT-REVIEWED-RECOVERY-1'
FIELDS = {
    'BG': {'parent_equity', 'opening_parent_equity', 'group_equity', 'nci',
           'parent_earnings', 'dividends', 'shares'},
    'ALGN': {'cash', 'assets', 'liabilities', 'parent_equity', 'preferred',
             'legal', 'vat', 'shares'},
}
CONCEPTS = {
    'BG': {'parent_equity': 'StockholdersEquity', 'opening_parent_equity': 'StockholdersEquity',
           'group_equity': 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
           'nci': 'MinorityInterest', 'parent_earnings': 'NetIncomeLoss',
           'dividends': 'PaymentsOfDividendsCommonStock',
           'shares': 'WeightedAverageNumberOfDilutedSharesOutstanding'},
    'ALGN': {'cash': 'CashAndCashEquivalentsAtCarryingValue', 'assets': 'Assets',
             'liabilities': 'Liabilities', 'parent_equity': 'StockholdersEquity',
             'preferred': 'PreferredStockValue', 'legal': 'AccruedLegalSettlementCosts',
             'vat': 'UKVATLossContingency',
             'shares': 'WeightedAverageNumberOfDilutedSharesOutstanding'},
}


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f'{label}: finite reviewed number required')
    return float(value)


def _radius(row):
    digits = str(row.get('decimals', ''))
    if digits == 'INF':
        return 0.
    try:
        return .5 * 10 ** -int(digits)
    except ValueError as exc:
        raise ValueError('reviewed fact precision is missing') from exc


def _reviewed_fact(structural, review, name, *, accession, cik, cutoff):
    selected = review.get('facts', {}).get(name)
    if not isinstance(selected, dict) or set(selected) != {
        'qname', 'namespace', 'period_start', 'period_end', 'context_id',
        'unit', 'decimals', 'value',
    }:
        raise ValueError(f'{name}: exact reviewed fact selection is missing')
    if not all(isinstance(selected[key], str) and selected[key]
               for key in ('qname', 'namespace', 'period_end', 'context_id', 'unit')):
        raise ValueError(f'{name}: reviewed fact identity is incomplete')
    if selected['period_start'] is not None and not isinstance(selected['period_start'], str):
        raise ValueError(f'{name}: reviewed flow period is invalid')
    if selected['period_end'] > cutoff or selected['period_end'] > review['period_end']:
        raise ValueError(f'{name}: source period exceeds reviewed filing')
    ticker = review['ticker']
    expected_local = CONCEPTS[ticker][name]
    expected_unit = 'xbrli:shares' if name == 'shares' else 'USD'
    issuer_tag = ticker == 'ALGN' and name in {'legal', 'vat'}
    namespace = str(selected['namespace'])
    if (str(selected['qname']).rsplit(':', 1)[-1] != expected_local
        or selected['unit'] != expected_unit
        or (not issuer_tag and not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}', namespace))
        or (issuer_tag and not re.fullmatch(r'https?://(?:www\.)?aligntech\.com/20\d{6}', namespace))):
        raise ValueError(f'{name}: reviewed concept, namespace or unit changed')
    value = _finite(selected['value'], name)
    rows = [row for row in structural.get('facts', [])
            if row.get('qname') == selected['qname']
            and row.get('namespace') == selected['namespace']
            and row.get('period_start') == selected['period_start']
            and row.get('period_end') == selected['period_end']
            and row.get('unit') == selected['unit']
            and not row.get('dimensions')
            and row.get('source_accession') == accession
            and str(row.get('entity_identifier', '')).zfill(10) == cik
            and row.get('entity_scheme') == 'http://www.sec.gov/CIK']
    if not rows:
        raise ValueError(f'{name}: reviewed source fact is missing or changed in scope')
    exact = [row for row in rows if row.get('context_id') == selected['context_id']
             and row.get('value') == value and str(row.get('decimals')) == str(selected['decimals'])]
    if not exact:
        raise ValueError(f'{name}: reviewed amount or precision changed')
    # A coarse duplicate and a precise tag may coexist (ALGN VAT). Both must
    # describe overlapping numeric intervals; a conflicting context holds.
    low = max(_finite(row.get('value'), name) - _radius(row) for row in rows)
    high = min(_finite(row.get('value'), name) + _radius(row) for row in rows)
    if low > high:
        raise ValueError(f'{name}: conflicting facts in reviewed context')
    return value, selected


def _ttm(normalizer, review, name, field, accession):
    expected = _finite(review.get('ttm', {}).get(name), name)
    selected = normalizer.ttm_flow(field)
    actual = _finite(selected['value'], name)
    if not isclose(actual, expected, rel_tol=0, abs_tol=.01):
        raise ValueError(f'{name}: reviewed TTM source amount changed')
    if not any(row.get('accession') == accession for row in selected.get('sources', [])):
        raise ValueError(f'{name}: TTM source does not include controlling filing')
    return actual, selected


def ready(recipe, policy):
    if not isinstance(policy, dict) or policy.get('schema_version') != SCHEMA:
        return False
    ticker = recipe.get('ticker')
    review = policy.get('review')
    if ticker not in FIELDS or not isinstance(review, dict):
        return False
    finance = review.get('financing_review')
    if not isinstance(finance, dict) or not re.fullmatch(r'[0-9a-f]{64}', str(finance.get('source_sha256', ''))):
        return False
    if ticker == 'BG':
        specialist = (isinstance(review.get('roe_multipliers'), dict)
                      and set(review['roe_multipliers']) == {'bear', 'base', 'bull'}
                      and isinstance(review.get('earnings_annualization_factor'), (int, float))
                      and isinstance(review.get('annual_note_interest_after_tax'), (int, float)))
    else:
        specialist = (isinstance(review.get('ttm'), dict)
                      and set(review['ttm']) == {'operating_cash_flow_ttm', 'capital_expenditures_ttm'}
                      and isinstance(review.get('cash_multipliers'), dict)
                      and set(review['cash_multipliers']) == {'bear', 'base', 'bull'}
                      and isinstance(review.get('extra_legal_loss'), dict)
                      and set(review['extra_legal_loss']) == {'bear', 'base', 'bull'}
                      and finance.get('borrowings') == 0)
    return (policy.get('ticker') == ticker
            and isinstance(policy.get('cik'), str)
            and all(review.get(key) for key in ('accession', 'period_end', 'filed_date', 'structural_sha256'))
            and isinstance(review.get('facts'), dict) and set(review['facts']) == FIELDS[ticker]
            and all(isinstance(row, dict) for row in review['facts'].values())
            and specialist
            and set(recipe.get('scenarios', {})) == {'bear', 'base', 'bull'}
            and {s.get('engine') for s in recipe['scenarios'].values()}
                == ({'residual_income'} if ticker == 'BG' else {'enterprise_cash_fcff'}))


def bind_reviewed_recipe(policy, recipe, packet, controlling, *, cutoff):
    """Bind only amounts explicitly selected in this filing's reviewed policy."""
    if not ready(recipe, policy):
        raise ValueError('reviewed recovery policy is incomplete')
    ticker = recipe['ticker']
    cik = normalize_cik(policy['cik'])
    if normalize_cik(packet['submissions']['cik']) != cik or normalize_cik(packet['companyfacts']['cik']) != cik:
        raise ValueError('reviewed issuer identity mismatch')
    review = policy['review']
    review = {**review, 'ticker': ticker}
    accession, period = controlling['accessionNumber'], controlling['reportDate']
    if (review['accession'], review['period_end'], review['filed_date']) != (
            accession, period, controlling['filingDate']):
        raise ValueError('new filing needs its own reviewed input record')
    structural = packet.get('structural_packets', {}).get(accession) or packet.get('structural_filing')
    if not isinstance(structural, dict) or structural.get('source_accession') != accession:
        raise ValueError('current reviewed structural filing is missing')
    receipt = next((row for row in packet.get('structural_receipts', []) if row.get('accession') == accession), None)
    if not isinstance(receipt, dict) or receipt.get('structural_sha256') != review.get('structural_sha256'):
        raise ValueError('reviewed structural source hash is missing or changed')
    values, sources = {}, {}
    for name in sorted(FIELDS[ticker]):
        values[name], sources[name] = _reviewed_fact(structural, review, name,
            accession=accession, cik=cik, cutoff=cutoff)
    bound = deepcopy(recipe)
    if ticker == 'BG':
        if not isclose(values['group_equity'] - values['nci'], values['parent_equity'], abs_tol=.01):
            raise ValueError('BG parent equity and NCI do not reconcile')
        factor = _finite(review.get('earnings_annualization_factor'), 'BG annualization')
        stress = _finite(review.get('annual_note_interest_after_tax'), 'BG note stress')
        financing = review.get('financing_review')
        if factor <= 0 or stress < 0 or not isinstance(financing, dict) or not re.fullmatch(r'[0-9a-f]{64}', str(financing.get('source_sha256', ''))) or not financing.get('treatment'):
            raise ValueError('BG earnings basis and financing require reviewed treatment')
        earnings = factor * values['parent_earnings'] - stress
        average_equity = (values['parent_equity'] + values['opening_parent_equity']) / 2
        if min(values['parent_earnings'], average_equity, values['shares']) <= 0 or earnings <= 0:
            raise ValueError('BG reviewed parent earnings, equity or shares are nonpositive')
        observed_roe = earnings / average_equity
        baseline_roe = recipe['scenarios']['base']['inputs']['current_roe']
        for case in ('bear', 'base', 'bull'):
            inputs = bound['scenarios'][case]['inputs']
            multiplier = _finite(review.get('roe_multipliers', {}).get(case), f'BG {case} ROE multiplier')
            if not isclose(multiplier, recipe['scenarios'][case]['inputs']['current_roe'] / baseline_roe, rel_tol=1e-12):
                raise ValueError('BG reviewed ROE scenario multiplier changes existing economics')
            inputs['book_value_per_share'] = values['parent_equity'] / values['shares']
            inputs['current_roe'] = observed_roe * multiplier
            inputs['current_payout_ratio'] = values['dividends'] / values['parent_earnings']
        method = 'reviewed H1 parent earnings and financing reference; scenario economics retained'
    else:
        if not isclose(values['assets'] - values['liabilities'], values['parent_equity'], abs_tol=.01):
            raise ValueError('ALGN parent equity balance-sheet proof changed')
        if values['preferred'] != 0 or values['shares'] <= 0:
            raise ValueError('ALGN preferred claim or share basis needs review')
        financing = review.get('financing_review')
        if (not isinstance(financing, dict) or financing.get('borrowings') != 0
            or not re.fullmatch(r'[0-9a-f]{64}', str(financing.get('source_sha256', ''))) or not financing.get('treatment')):
            raise ValueError('ALGN debt and financing scope need review')
        normalizer = CompanyFactsNormalizer(packet['companyfacts'],
            concept_config=load_concept_config(), fiscal_year_end=packet['submissions'].get('fiscalYearEnd'),
            as_of_date=cutoff)
        ocf, sources['operating_cash_flow_ttm'] = _ttm(normalizer, review, 'operating_cash_flow_ttm', 'operating_cash_flow', accession)
        capex, sources['capital_expenditures_ttm'] = _ttm(normalizer, review, 'capital_expenditures_ttm', 'capital_expenditures', accession)
        owner_cash = ocf - capex
        if owner_cash <= 0 or min(values['cash'], values['legal'], values['vat']) < 0:
            raise ValueError('ALGN owner cash or recorded claims require review')
        for case in ('bear', 'base', 'bull'):
            inputs = bound['scenarios'][case]['inputs']
            multiplier = _finite(review.get('cash_multipliers', {}).get(case), f'ALGN {case} cash multiplier')
            extra = _finite(review.get('extra_legal_loss', {}).get(case), f'ALGN {case} illustrative loss')
            known_baseline = -recipe['scenarios']['bull']['inputs']['nonoperating_adjustment']
            prior_extra = -recipe['scenarios'][case]['inputs']['nonoperating_adjustment'] - known_baseline
            if extra < 0 or not isclose(multiplier, recipe['scenarios'][case]['inputs']['cash_fcff'] / recipe['scenarios']['base']['inputs']['cash_fcff'], rel_tol=1e-12):
                raise ValueError('ALGN cash multiplier changes existing economics')
            if not isclose(extra, prior_extra, rel_tol=0, abs_tol=.01):
                raise ValueError('ALGN illustrative legal loss changes existing economics')
            inputs.update(cash_fcff=owner_cash * multiplier, cash_and_investments=values['cash'],
                          diluted_shares=values['shares'], interest_bearing_debt=0,
                          preferred_equity=0, noncontrolling_interests=0,
                          nonoperating_adjustment=-(values['legal'] + values['vat'] + extra))
        method = 'reviewed TTM owner cash and known legal/VAT claims; illustrative losses retained'
    bound['source_accession'] = accession
    bound['evidence_cutoff'] = cutoff
    evaluate_recipe(bound)
    return bound, {'controlling_filing': controlling, 'period_end': period, 'frozen_cutoff': cutoff,
                   'cik': cik, 'recipe_engine': bound['scenarios']['base']['engine'],
                   'policy_version': policy['version'], 'sources': sources, 'values': values,
                   'normalization': {'method': method}, 'reviewed_filing': review['accession'],
                   'reviewed_structural_sha256': review['structural_sha256'],
                   'reviewed_financing_source': deepcopy(review['financing_review']),
                   'reviewed_economic_inputs': ({
                       'earnings_annualization_factor': review['earnings_annualization_factor'],
                       'annual_note_interest_after_tax': review['annual_note_interest_after_tax'],
                       'roe_multipliers': deepcopy(review['roe_multipliers']),
                   } if ticker == 'BG' else {
                       'cash_multipliers': deepcopy(review['cash_multipliers']),
                       'extra_legal_loss': deepcopy(review['extra_legal_loss']),
                   })}
