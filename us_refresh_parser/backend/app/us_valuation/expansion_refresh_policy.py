"""Versioned, staged-only source contracts for the three public Batch01 models."""
from copy import deepcopy
from datetime import date
from .xbrl import load_concept_config

SCHEMA='FINSIGHT-B01-SUPPORTED-REFRESH-1'
SUPPORTED={'AIT':('0000109563','owner_cash_ait','cash_schedule'),
           'WCC':('0000929008','parent_common_ri','residual_income'),
           'GRC':('0000042682','parent_common_ri','residual_income')}


def compile_policy(ticker,recipe,*,epoch='2026-10-03',ait_contract=None):
    if ticker not in SUPPORTED or recipe.get('ticker')!=ticker:
        raise ValueError('unsupported Batch01 refresh identity')
    cik,profile,engine=SUPPORTED[ticker]
    if set(recipe.get('scenarios',{}))!={'bear','base','bull'} or any(s['engine']!=engine for s in recipe['scenarios'].values()):
        raise ValueError('unsupported Batch01 model contract')
    config=deepcopy(load_concept_config())
    policy={'schema_version':SCHEMA,'version':'US-B01-SOURCE-MODEL-REFRESH-1','ticker':ticker,'cik':cik,
        'profile':profile,'source_epoch':epoch,'auto_revaluation':True,'stage_only':True,
        'publication_authorized':False,'activation_authorized':False,'admission_authorized':False,
        'source_requirements':{'companyfacts':True,'structural':True,'regular_filing':True},
        'routine_8k_items':['2.02','9.01'],'concept_config':config,
        'required_source_fields':(['revenue','operating_cash_flow','sbc','capital_expenditures','point_common_shares','capex_guidance','acquisition_holdbacks']
            if ticker=='AIT' else ['current_parent_common_book','current_common_stock_shares_outstanding_point_not_issued_or_weighted_average','ttm_common_earnings','ttm_common_dividends','preferred_lifecycle']),
        'assumptions_retained':True,'reliability_cap':'Low'}
    if ticker=='AIT':
        if not isinstance(ait_contract,dict) or ait_contract.get('model')!='cash_schedule':
            raise ValueError('approved AIT contract required')
        policy['approved_contract']=deepcopy(ait_contract)
        policy['scenario_assumptions']=deepcopy(ait_contract['scenarios'])
        policy['statement_required_fields']={'revenue':'flow','operating_cash_flow':'flow','total_assets':'instant'}
    else:
        config['fields']['parent_earnings']={'concepts':(['us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic','us-gaap:NetIncomeLoss']
            if ticker=='WCC' else ['us-gaap:NetIncomeLoss']),'kind':'flow','unit':'USD'}
        config['fields']['parent_equity']={'concepts':['us-gaap:StockholdersEquity'],'kind':'instant','unit':'USD'}
        policy['statement_required_fields']={'parent_earnings':'flow','parent_equity':'instant','total_assets':'instant'}
        base=recipe['scenarios']['base']['inputs']['current_roe']
        policy['scenario_assumptions']={name:{**{k:spec['inputs'][k] for k in ('cost_of_equity','terminal_roe','terminal_growth','years')},
            'roe_multiplier':spec['inputs']['current_roe']/base} for name,spec in recipe['scenarios'].items()}
    return policy


def ready(recipe,policy):
    try:
        ticker=recipe['ticker'];cik,profile,engine=SUPPORTED[ticker]
        if (policy.get('schema_version')!=SCHEMA or policy.get('ticker')!=ticker or policy.get('cik')!=cik
                or recipe.get('cik')!=cik or policy.get('profile')!=profile
                or policy.get('stage_only') is not True or policy.get('auto_revaluation') is not True
                or any(policy.get(k) is not False for k in ('publication_authorized','activation_authorized','admission_authorized'))
                or policy.get('reliability_cap')!='Low' or not policy.get('required_source_fields')
                or not policy.get('statement_required_fields') or not policy.get('scenario_assumptions')
                or not policy.get('source_requirements',{}).get('structural')
                or set(recipe['scenarios'])!={'bear','base','bull'}
                or any(s['engine']!=engine for s in recipe['scenarios'].values())):
            return False
        date.fromisoformat(policy['source_epoch'])
        return True
    except (ValueError,KeyError,TypeError):
        return False
