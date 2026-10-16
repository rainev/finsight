"""Professional-liability reserve/asset/cash overlap without stock double count."""
from dataclasses import asdict
from copy import deepcopy
from datetime import date
from math import isfinite
from pathlib import Path
import json,re
from .arelle_worker import _QNameCanonicalizer
from .refresh_narrative_evidence import narrative_policy,validate_narrative_evidence,terms_by_name
from .refresh_reported_claim_scope import REPORTED_NCI_SCOPE_RULES,reported_nci_field_availability
from .xbrl import CompanyFactsNormalizer
from .calculation_recipe import evaluate_scenario

VERSION='FINSIGHT-PROFESSIONAL-LIABILITY-FORWARD-SCOPE-WG34-1'
RULES={'HCA':{'version':VERSION,'ticker':'HCA','cik':'0000860730','issuer_namespace_pattern':r'https?://hcahealthcare\.com/\d{8}',
    'liability_local':'ProfessionalLiabilityRisks','total_investment_qname':'us-gaap:InvestmentOwnedAtFairValue',
    'current_investment_qname':'us-gaap:InvestmentsFairValueDisclosure','noncurrent_investment_qname':'us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent',
    'legacy_reserve_stress':{'bear':1.,'base':.5,'bull':0.},'annual_ocf_observations_required':5}}
def professional_liability_policy(ticker):return deepcopy(RULES[ticker])

def bind_professional_liability_scope(policy,structural,narrative,companyfacts,submissions,recipe, *,cutoff,source_root):
    if policy!=RULES.get(policy.get('ticker')):raise ValueError('professional liability policy identity/version mismatch')
    date.fromisoformat(cutoff);receipt=validate_narrative_evidence(narrative,narrative_policy(policy['ticker']),source_root=Path(source_root));filing=receipt['filing'];period=filing['report_date'];acc=filing['accession']
    manifest=json.loads((Path(source_root)/receipt['source']['package_manifest_path']).read_bytes());metadata=dict(structural.get('filing_metadata',()))
    if (metadata.get('package_generation')!=manifest.get('generation') or metadata.get('primary_document')!=receipt['source']['document_name']
        or structural.get('source_accession')!=acc or structural.get('report_date')!=period or structural.get('filed_date')!=filing['filed_date']
        or not period<=filing['filed_date']<=cutoff or str(companyfacts.get('cik','')).zfill(10)!=policy['cik']):
        raise ValueError('professional liability source identity/cutoff mismatch')
    facts=structural['facts'];canonical=_QNameCanonicalizer()
    def one(qname=None,local=None, *,end=period,parent=None,role=None,issuer=False):
        rows=[r for r in facts if (r.get('qname')==qname if qname else r.get('local_name')==local) and r.get('period_end')==end and r.get('period_start') is None and not r.get('dimensions')]
        if not rows:raise ValueError('professional liability source fact missing; absence is not zero')
        for r in rows:
            if (r.get('unit')!='USD' or r.get('source_accession')!=acc or r.get('entity_scheme')!='http://www.sec.gov/CIK'
                or str(r.get('entity_identifier','')).zfill(10)!=policy['cik'] or isinstance(r['value'],bool)
                or not isinstance(r['value'],(int,float)) or not isfinite(r['value']) or r['value']<0
                or r.get('qname')!=canonical.prefix(str(r.get('namespace','')))+':'+str(r.get('local_name',''))
                or (issuer and not re.fullmatch(policy['issuer_namespace_pattern'],str(r.get('namespace',''))))
                or (not issuer and not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',str(r.get('namespace',''))))
                or (parent and parent not in r.get('presentation_parents',[])) or (role and role not in r.get('statement_roles',[]))):
                raise ValueError('professional liability fact identity/value/presentation invalid')
        if len({(r['value'],r['context_id']) for r in rows})!=1:raise ValueError('professional liability source fact conflicts')
        return rows[0]
    liability_periods={r['period_end'] for r in facts if r.get('local_name')==policy['liability_local'] and r.get('period_start') is None and not r.get('dimensions')}
    comparative_periods=liability_periods-{period}
    if len(comparative_periods)!=1:raise ValueError('professional liability comparative period missing/ambiguous')
    comparative_period=next(iter(comparative_periods))
    liability=one(local=policy['liability_local'],parent='us-gaap:LiabilitiesAndStockholdersEquityAbstract',role='balance_sheet',issuer=True)
    comparative=one(local=policy['liability_local'],end=comparative_period,parent='us-gaap:LiabilitiesAndStockholdersEquityAbstract',role='balance_sheet',issuer=True)
    total_investments=one(qname=policy['total_investment_qname'],parent='us-gaap:ScheduleOfAvailableForSaleSecuritiesLineItems')
    current_investments=one(qname=policy['current_investment_qname'],parent='us-gaap:ScheduleOfAvailableForSaleSecuritiesLineItems')
    noncurrent_investments=one(qname=policy['noncurrent_investment_qname'],parent='us-gaap:AssetsAbstract',role='balance_sheet')
    if total_investments['value']!=current_investments['value']+noncurrent_investments['value']:raise ValueError('insurance current/noncurrent investments do not reconcile')
    comparative_total=one(qname=policy['total_investment_qname'],end=comparative_period,parent='us-gaap:ScheduleOfAvailableForSaleSecuritiesLineItems')
    comparative_current=one(qname=policy['current_investment_qname'],end=comparative_period,parent='us-gaap:ScheduleOfAvailableForSaleSecuritiesLineItems')
    comparative_noncurrent=one(qname=policy['noncurrent_investment_qname'],end=comparative_period,parent='us-gaap:AssetsAbstract',role='balance_sheet')
    if comparative_total['value']!=comparative_current['value']+comparative_noncurrent['value']:raise ValueError('comparative insurance investments do not reconcile')
    terms={key:value['value'] for key,value in terms_by_name(receipt).items()}
    if terms['insurance_investments']['current']!=total_investments['value'] or terms['insurance_investments']['comparative']!=comparative_total['value']:
        raise ValueError('professional liability narrative/source investments disagree')
    total_reserves=terms['insurance_subsidiary_reserve']['current']+terms['self_insured_reserve']['current']
    if terms['next_12_month_retained_payments']>terms['next_12_month_payments'] or terms['next_12_month_payments']>total_reserves:raise ValueError('professional liability expected payments exceed reserve scope')
    _,ownership=reported_nci_field_availability(ticker='HCA',policy=asdict(REPORTED_NCI_SCOPE_RULES['HCA']),structural_packet=structural,accession=acc,period_end=period)
    normalizer=CompanyFactsNormalizer(companyfacts,fiscal_year_end=submissions.get('fiscalYearEnd'),as_of_date=cutoff)
    annual_ocf=[row.as_dict() for row in normalizer.annual_series('operating_cash_flow',5)]
    if len(annual_ocf)!=policy['annual_ocf_observations_required']:raise ValueError('professional liability overlap requires complete reported cash history')
    diagnostics={};ownership_claim=ownership['source_total']
    for name,spec in recipe['scenarios'].items():
        old=spec['inputs'];old_claim=old['preferred_equity']+old['noncontrolling_interests']-old.get('nonoperating_adjustment',0.)
        stress=liability['value']*policy['legacy_reserve_stress'][name]
        if old_claim!=ownership_claim+stress:raise ValueError('legacy professional reserve stress does not reconcile')
        proposed={**spec,'inputs':{**old,'preferred_equity':0.,'noncontrolling_interests':ownership_claim,'nonoperating_adjustment':-stress}}
        old_value=evaluate_scenario(spec)['value'];new_value=evaluate_scenario(proposed)['value']
        if old_value!=new_value:raise ValueError('professional reserve semantic reclassification changed value')
        diagnostics[name]={'legacy_claim':old_claim,'approved_ownership_claim':ownership_claim,'noncurrent_reserve_sensitivity':stress,
            'proposed_signed_reserve_adjustment':-stress,'old_value':old_value,'reclassified_value':new_value,'value_change':new_value-old_value}
    residual=total_reserves-liability['value']
    return {'status':'noncurrent_reserve_sensitivity_reconciled_forward_cash_review','version':VERSION,'ticker':'HCA','accession':acc,'period_end':period,'source_receipt_sha256':receipt['receipt_sha256'],
        'reported_balance_sheet_professional_liability':liability,'comparative_balance_sheet_professional_liability':comparative,
        'insurance_investments':{'total':total_investments,'current':current_investments,'noncurrent':noncurrent_investments,
            'comparative':{'total':comparative_total,'current':comparative_current,'noncurrent':comparative_noncurrent},
            'treatment':'dedicated statutory/claims assets; not surplus cash or automatic recovery netting'},
        'narrative_terms':terms,'total_narrative_professional_reserves':total_reserves,'ownership_carrying_proof':ownership,
        'annual_reported_operating_cash_flow_inventory':annual_ocf,'reported_claim_cash_payments':None,'recognized_reinsurance_receivable':None,
        'claim_payment_schedule':{'next_12_month_aggregate':terms['next_12_month_payments'],'retained_portion_aggregate':terms['next_12_month_retained_payments'],'exact_timing':None},
        'arithmetic_current_portion_diagnostic_not_reported':{'total_reserves_less_balance_sheet_line':residual,'equals_expected_retained_payments':residual==terms['next_12_month_retained_payments'],'treatment':'arithmetic coincidence only; not a tagged current reserve'},
        'professional_reserve_treatment':'recurring premiums/ordinary claims remain in reported cash history; preserve source-bounded noncurrent reserve scenario sensitivity while paid-claims/forecast overlap is incomplete; no additional full-reserve deduction or addback',
        'scenario_diagnostics_not_candidate':diagnostics,'claim_adjustment':None,'numeric_successor_issued':False,
        'review_reasons':['balance_sheet_line_appears_noncurrent_but_structural_parent_not_explicitly_noncurrent','current_professional_reserve_not_separately_tagged_and_532m_equality_is_inference_only','claim_cash_payments_and_reinsurance_recoveries_not_separately_bound',
            'next_12_month_aggregate_not_exact_timing_or_full_forward_schedule','forecast_cash_history_overlap_not_quantified','preferred_absence_and_complete_numeric_bridge_not_approved']}
