"""Governed semantic split of one mixed legacy claim; not numeric publication."""
from copy import deepcopy
from math import isfinite
from .calculation_recipe import evaluate_scenario

VERSION='FINSIGHT-GOVERNED-CLAIM-BRIDGE-WG33-1'
RULES={'MCK':{'version':VERSION,'ticker':'MCK','cik':'0000927653',
    'ownership_basis':'reported_consolidated_current_carrying_proxy_not_contract_intrinsic_value',
    'legal_basis':'conditional_same_program_payment_only_proxy_not_actual_closing_balance'}}
def governed_claim_bridge_policy(ticker):return dict(RULES[ticker])

def bind_governed_claim_bridge(policy,recipe,ownership,settlement,public):
    if policy!=RULES.get(policy.get('ticker')):raise ValueError('governed claim bridge policy identity/version mismatch')
    if recipe.get('ticker')!=policy['ticker'] or recipe.get('source_accession')!=ownership.get('accession'):
        raise ValueError('governed claim recipe/source identity mismatch')
    if ownership.get('status')!='carrying_rollforward_and_mechanisms_verified_economic_basis_review' or ownership.get('numeric_successor_issued') is not False:raise ValueError('ownership source scope unavailable or promoted')
    if settlement.get('status')!='payment_only_cash_liability_reconciled_full_scope_review' or settlement.get('numeric_successor_issued') is not False:raise ValueError('conditional legal bridge unavailable or promoted')
    if public.get('version')!='FINSIGHT-PUBLIC-CONTRACT-EVIDENCE-WG32-1' or public.get('claim_adjustment') is not None or public.get('numeric_successor_issued') is not False:
        raise ValueError('public contract evidence promoted or wrong version')
    ordinary=ownership['reported_ordinary_carrying'];redeemable=ownership['reported_redeemable_carrying'];ownership_total=ordinary+redeemable
    components={row['qname']:row['value'] for row in ownership['ownership_carrying_proof']['components']}
    if (set(components)!={'us-gaap:MinorityInterest','us-gaap:RedeemableNoncontrollingInterestEquityCommonCarryingAmount'}
        or components['us-gaap:MinorityInterest']!=ordinary
        or components['us-gaap:RedeemableNoncontrollingInterestEquityCommonCarryingAmount']!=redeemable
        or ownership_total!=ownership['ownership_carrying_proof']['source_total']
        or public['core_put']['source_arithmetic_floor']>redeemable
        or ownership['instrument_economic_basis'].get('economic_claim') is not None
        or ownership['instrument_economic_basis'].get('parent_conversion_shares') is not None):
        raise ValueError('governed ownership carrying/contract alternatives do not reconcile')
    legal=settlement['payment_only_bridge']['liability_after_payment_only_not_closing_balance']
    if (settlement['payment_only_bridge']['actual_post_period_liability'] is not None
        or settlement['payment_only_bridge']['actual_post_period_cash'] is not None
        or settlement['payment_only_bridge']['claim_adjustment'] is not None):
        raise ValueError('conditional payment-only bridge was promoted to closing state')
    if not all(isinstance(x,(int,float)) and not isinstance(x,bool) and isfinite(x) and x>=0 for x in (ordinary,redeemable,legal)):
        raise ValueError('governed claim components must be finite nonnegative source values')
    scenario_checks={}
    for name,spec in recipe['scenarios'].items():
        old=spec['inputs'];legacy=old['preferred_equity']+old['noncontrolling_interests']-old.get('nonoperating_adjustment',0.)
        if legacy!=ownership_total+legal:raise ValueError('legacy mixed claim does not equal source-classified components')
        proposed=deepcopy(spec);proposed['inputs']['preferred_equity']=0.;proposed['inputs']['noncontrolling_interests']=ownership_total;proposed['inputs']['nonoperating_adjustment']=-legal
        old_result=evaluate_scenario(spec);new_result=evaluate_scenario(proposed)
        if old_result['raw_value']!=new_result['raw_value'] or old_result['value']!=new_result['value']:
            raise ValueError('semantic claim reclassification changed scenario value')
        scenario_checks[name]={'legacy_mixed_claim':legacy,'proposed_preferred_equity':0.,'proposed_noncontrolling_interests':ownership_total,
            'proposed_signed_legal_adjustment':-legal,'legacy_value':old_result['value'],'reclassified_value':new_result['value'],'value_change':new_result['value']-old_result['value']}
    return {'status':'ownership_carrying_treatment_approved_legal_bridge_review','version':VERSION,'ticker':policy['ticker'],
        'ordinary_nci_claim':ordinary,'redeemable_nci_claim':redeemable,'approved_ownership_claim':ownership_total,
        'ownership_basis':policy['ownership_basis'],'legal_conditional_claim':legal,'legal_basis':policy['legal_basis'],
        'legacy_mixed_claim':ownership_total+legal,'scenario_checks':scenario_checks,
        'nonadditive_diagnostics':{'core_floor':public['core_put']['source_arithmetic_floor'],'apollo_transaction_descriptor':public['apollo_announcement']['terms'][0]['value'],
            'annual_fair_value_adjustment':public['historical_component_evidence']['annual_fair_value_adjustment'][0]['value'],
            'annual_core_redemption_adjustment':public['historical_component_evidence']['annual_core_redemption_adjustment'][0]['value'],
            'current_redemption_movements':{key:row['value'] for key,row in ownership['redemption_movement_sources'].items()},
            'net_financing_proceeds':ownership['net_proceeds_source']['value']},
        'preferred_equity_treatment':'legacy mixed bucket semantically zero after ownership/legal split; not evidence of no subsidiary preferred economics',
        'parent_conversion_shares':None,'claim_adjustment':None,'numeric_successor_issued':False,
        'review_reasons':['legal_claim_and_cash_are_conditional_not_actual_post_period_balances','legal_payment_allocation_funding_and_forecast_cash_overlap_unresolved',
            'cash_securities_and_complete_post_period_financing_unresolved','contract_intrinsic_outcomes_and_current_components_unavailable','all_prior_company_and_operational_gaps_retained']}
