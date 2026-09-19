"""Versioned governed post-capex margins, distinct from reported cash history."""
from copy import deepcopy
from hashlib import sha256
import json
from math import isclose, isfinite
import re
from pathlib import Path
from types import MappingProxyType

from .catalog import canonical_json_bytes

SCHEMA='FINSIGHT-GOVERNED-CASH-MARGINS-1'
VERSION='FINSIGHT-GOVERNED-CASH-MARGINS-WG24-1'
RULES=MappingProxyType({
    'INTC': {
        'schema_version':SCHEMA,'version':VERSION,'ticker':'INTC','cik':'0000050863',
        'engine':'enterprise_cash_fcff','scenario_margins':(.03,.07,.12),
        'minimum_annual_periods':5,'minimum_profitable_tax_periods':3,
        'current_tax_median_minimum':.05,'annual_tax_cap':.30,'loss_tax_fallback':.21,
        'require_positive_reported_cash_after_total_capex':True,
        'financing_capital_payment_local_name':'PaymentsToAcquirePropertyPlantAndEquipmentFinancingActivities',
        'issuer_namespace_pattern':r'https?://(?:www\.)?intel\.com/\d{8}',
        'classification':'finsight_assumption',
        'economic_scope':'governed cash after total reinvestment; not reported margin or historical median',
        'reinvestment_treatment':'all ordinary reinvestment is assumed inside post-total-capex margins; no maintenance/growth split, SBC or unusual-item addback',
        'review_conditions':('financing capital payments and lease/debt overlap',
            'cash-equivalent/AFS overlap and restricted investments',
            'escrowed-share derivatives, contingent shares and warrants',
            'government incentives, customer deposits and working-capital cash',
            'foundry transformation, restructuring and deconsolidated operating scope'),
        'economic_review_required':True,
    },
})

def governed_margin_policy(ticker):
    if ticker not in RULES:raise ValueError('no approved governed cash-margin rule')
    return deepcopy(RULES[ticker])

def validate_governed_margin_policy(policy, *, cik):
    expected=RULES.get(policy.get('ticker')) if isinstance(policy,dict) else None
    if (expected is None or str(cik).zfill(10)!=expected['cik']
        or canonical_json_bytes(policy)!=canonical_json_bytes(expected)):
        raise ValueError('governed cash-margin policy identity/version mismatch')
    return deepcopy(expected)

def compile_governed_margin_policy(entry,recipe):
    """Validate assumptions against retained private evidence, never target-fit."""
    policy=governed_margin_policy(entry['ticker'])
    if str(entry['cik']).zfill(10)!=policy['cik']:
        raise ValueError('governed margin registry identity mismatch')
    provenance=recipe.get('provenance',{})
    path=Path(str(provenance.get('source_path','')))
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=provenance.get('private_sha256'):
        raise ValueError('governed margin retained evidence hash mismatch')
    private=json.loads(raw).get('history_backed',{})
    assumptions=private.get('governed_assumptions',{})
    if tuple(assumptions.get('cash_conversion_margin',()))!=policy['scenario_margins']:
        raise ValueError('retained governed cash-margin assumption rule changed')
    revenue=private.get('reported_inputs',{}).get('ttm_revenue')
    if not isinstance(revenue,(float,int)) or isinstance(revenue,bool) or not isfinite(revenue) or revenue<=0:
        raise ValueError('retained governed-margin revenue evidence missing')
    for index,case in enumerate(('bear','base','bull')):
        spec=recipe.get('scenarios',{}).get(case,{})
        if spec.get('engine')!=policy['engine'] or not isclose(
            spec.get('inputs',{}).get('cash_fcff',float('nan')),
            revenue*policy['scenario_margins'][index],rel_tol=1e-12,abs_tol=.01):
            raise ValueError('retained recipe does not execute the approved governed-margin rule')
    return policy

def governed_source_validity(policy,reported,annual,structural, *, period, current_flow_start=None):
    """Expose unbound reinvestment cash rather than calling investing capex total."""
    policy=validate_governed_margin_policy(policy,cik=policy['cik'])
    review=[]
    if policy['economic_review_required']:
        review.append('special_situation_economic_validity_requires_source_backed_review')
    post_investing=reported['operating_cash_flow']-reported['capital_expenditures']
    if reported['revenue']<=0 or post_investing<=0:
        review.append('current_reported_cash_after_investing_capex_is_not_positive')
    if not isinstance(structural,dict) or structural.get('report_date')!=period:
        raise ValueError('governed margin validity requires current structural filing')
    accession=structural.get('source_accession')
    rows=[r for r in structural.get('facts',[]) if r.get('local_name')==policy['financing_capital_payment_local_name']
          and r.get('period_end')==period and isinstance(r.get('period_start'),str) and not r.get('dimensions')]
    for row in rows:
        if (row.get('source_accession')!=accession or row.get('unit')!='USD'
            or str(row.get('entity_identifier','')).zfill(10)!=policy['cik']
            or row.get('entity_scheme')!='http://www.sec.gov/CIK'
            or not re.fullmatch(policy['issuer_namespace_pattern'],str(row.get('namespace','')))
            or 'cash_flow' not in row.get('statement_roles',[])
            or 'us-gaap:NetCashProvidedByUsedInFinancingActivitiesAbstract' not in row.get('presentation_parents',[])
            or isinstance(row.get('value'),bool) or not isinstance(row.get('value'),(float,int))
            or not isfinite(row['value'])):
            raise ValueError('governed financing-capital-payment source scope invalid')
    if rows:
        start=min(row['period_start'] for row in rows);rows=[row for row in rows if row['period_start']==start]
        if current_flow_start is not None and start!=current_flow_start:
            raise ValueError('governed financing-capital-payment interval does not align to current source flow')
        values={float(row['value']) for row in rows}
        if len(values)!=1 or next(iter(values))<0:raise ValueError('governed financing-capital-payment amount conflicts')
        value=values.pop()
        if value!=0:review.append('financing_capital_payment_cash_and_debt_overlap_requires_reconciliation')
    else:
        value=None
        review.append('financing_capital_payment_scope_is_not_reported_missing_is_not_zero')
    return {'complete_annual_periods':len(annual),
        'negative_annual_cash_periods':sum(row['cash_fcff']<0 for row in annual),
        'reported_current_cash_after_investing_capex':post_investing,
        'current_ytd_financing_capital_payments':value,
        'financing_capital_payment_source_rows':rows,
        'passed':not review,'review_reasons':review,
        'financing_capital_payment_line_zero':value==0,
        'total_reinvestment_scope_complete':False}

__all__=['SCHEMA','VERSION','RULES','governed_margin_policy',
         'validate_governed_margin_policy','compile_governed_margin_policy','governed_source_validity']
