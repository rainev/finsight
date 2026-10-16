"""Safe staged Quality03 disclosures; no source packets or recipe exposure."""
from copy import deepcopy
from math import isfinite
import json
from . import quality03_staged as stage

PUBLIC_FIELDS=frozenset({'forecast_policy_version','classification','forecast_mode','forecast_years','terminal_growth',
    'automatic_new_filing_revaluation','sustainable_income_or_cash_proven','legal_absence_of_unrecorded_claims_proven',
    'wacc','initial_growth','retained_tax_convention','cash_paid_interest_convention','net_fleet_receipts_offset_gross_purchases_once',
    'full_reported_purchases_charged','maintenance_growth_split_proven','prior_annual_finance_leased_replacement_allowance',
    'allowance_is_not_reported_current_TTM','current_leased_replacement_reconciled','share_count_basis','cost_of_equity',
    'initial_forecast_roe_seed','future_payout_ratio','terminal_roe','clean_surplus_and_payout_recurrence_proven',
    'no_reconciled_owner_cash_claim','sector_assignment','sector_beta_prior','risk_free_rate','ERP','uncertainty_premium'})


def public_forecast_assumptions(value):
    stage.require(isinstance(value,dict) and set(value)<=PUBLIC_FIELDS,'safe analyst assumptions only')
    result=deepcopy(value)
    for key,item in result.items():
        stage.require(isinstance(item,(str,bool,int,float)) and not (isinstance(item,float) and not isfinite(item)),'scalar assumption '+key)
    stage.require(result.get('forecast_policy_version')==stage.MODEL_VERSION and result.get('classification')=='ANALYST_ASSUMPTIONS_NOT_REPORTED_FACTS','assumption scope')
    stage.require(result.get('automatic_new_filing_revaluation') is False,'no new-source permission')
    return result


def consumer_disclosures(root,manifest,artifact,payload,*,proof_reader):
    ticker=artifact['issuer']['ticker']
    a=stage.anchors()
    binding=stage.proof(root,'quality-source-binding.json',a['binding_sha256'],proof_reader)
    stage.require(set(binding['records'])==stage.TARGETS|stage.CARRY_FORWARD,'disclosure scope')
    if ticker not in binding['records']: return payload
    record=binding['records'][ticker]
    result=deepcopy(payload)
    warnings=list(dict.fromkeys([*result.get('warnings',[]),*artifact.get('review',{}).get('warnings',[])]))
    source_date=artifact['source_financial_statement']['period_end']; valuation_date=artifact['valuation_date']
    updated=ticker in stage.TARGETS
    if updated:
        assumptions=public_forecast_assumptions(record['forecast_assumptions'])
        result['quality_forecast_assumptions']=assumptions
        warnings.append('Forecast assumptions, not reported facts: '+json.dumps(assumptions,sort_keys=True))
        filing_hold=True
    else:
        warnings.append('Authentic prior dated public estimate and recipe retained; no revised private diagnostic or held-update assumptions are exposed.')
        filing_hold=not record['existing_refresh_contract_ready']
    warnings.append('Financial reference date is '+str(source_date)+'; artifact valuation date is '+str(valuation_date)+'. Review date does not advance the financial cutoff.')
    result['warnings']=list(dict.fromkeys(warnings))
    status='revised_value_staged' if updated else 'unchanged_FAST_control' if ticker=='FAST' else 'private_only_diagnostic' if ticker in stage.PRIVATE_ONLY else 'private_held_update'
    result['staged_scope']={'schema_version':stage.REVIEW_SCHEMA,'read_only':True,'admission':False,'activation':False,'publication':False,
        'valuation_date':valuation_date,'financial_reference_date':source_date,'sourceDate':source_date,
        'financial_evidence_cutoff':record['proposed_evidence_cutoff'] if updated else valuation_date,
        'new_filing_hold':filing_hold,'quality_update_held':ticker in stage.HELD or ticker in stage.PRIVATE_ONLY,
        'quality_update_status':status,'revised_value_staged':updated,'prior_dated_public_estimate_retained':not updated,
        'private_only_recovery_diagnostic':ticker in stage.PRIVATE_ONLY,'unchanged_FAST_control':ticker=='FAST',
        'source_public_approved_low_version':stage.MODEL_VERSION,'facts_and_forecast_assumptions_separate':True,
        'updated_recipe_source_adapter_ready':False if updated else record['existing_refresh_contract_ready']}
    return result
