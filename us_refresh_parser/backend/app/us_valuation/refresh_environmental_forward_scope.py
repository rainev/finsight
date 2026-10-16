"""Related environmental balances are not automatically timed net cash claims."""
from datetime import date
from pathlib import Path
from math import isfinite
import re
from .refresh_narrative_evidence import narrative_policy,validate_narrative_evidence,terms_by_name
from .xbrl import CompanyFactsNormalizer
from .catalog import canonical_json_bytes

VERSION='FINSIGHT-ENVIRONMENTAL-FORWARD-SCOPE-WG28-1'
RULES={'LHX':{'version':VERSION,'ticker':'LHX','cik':'0000202058',
    'reserve_qname':'us-gaap:AccrualForEnvironmentalLossContingencies',
    'recovery_local_name':'RecoverableEnvironmentalRemediationCosts',
    'axis':'us-gaap:EnvironmentalRemediationContingencyAxis','member_local_name':'VariousEnvironmentalMattersMember',
    'issuer_namespace_pattern':r'https?://harris\.com/\d{8}',
    'payment_concepts':('PaymentsForEnvironmentalRemediation','PaymentsForEnvironmentalRemediationCosts'),
    'recovery_cash_concepts':('ProceedsFromEnvironmentalRecoveries','ProceedsFromEnvironmentalRemediationRecoveries')}}

def environmental_forward_policy(ticker):
    if ticker not in RULES:raise ValueError('unsupported environmental forward scope')
    return dict(RULES[ticker])

def bind_environmental_forward_scope(policy,structural,narrative,companyfacts,submissions, *, cutoff,source_root):
    if canonical_json_bytes(policy)!=canonical_json_bytes(RULES.get(policy.get('ticker'))):raise ValueError('environmental forward policy identity/version mismatch')
    date.fromisoformat(cutoff)
    receipt=validate_narrative_evidence(narrative,narrative_policy(policy['ticker']),source_root=Path(source_root))
    f=receipt['filing'];period=f['report_date'];acc=f['accession']
    if (structural.get('source_accession')!=acc or structural.get('report_date')!=period
        or not period<=f['filed_date']<=cutoff or str(companyfacts.get('cik','')).zfill(10)!=policy['cik']):
        raise ValueError('environmental source identity/cutoff mismatch')
    terms=terms_by_name(receipt)
    if terms['environmental_recovery_mechanism']['value']!='future_government_contract_pricing_not_surplus_cash':
        raise ValueError('environmental recovery mechanism not source bound')
    facts=structural['facts']
    prefixes={r['qname'].split(':',1)[0] for r in facts if re.fullmatch(policy['issuer_namespace_pattern'],str(r.get('namespace','')))}
    def balances(qname=None,local=None):
        rows=[r for r in facts if (r.get('qname')==qname if qname else r.get('local_name')==local)
            and r.get('period_start') is None and r.get('unit')=='USD']
        result={}
        for r in rows:
            dims=dict(r.get('dimensions') or [])
            if (len(dims)!=1 or str(dims.get(policy['axis'],'')).rsplit(':',1)[-1]!=policy['member_local_name']
                or str(dims[policy['axis']]).split(':',1)[0] not in prefixes
                or r.get('entity_scheme')!='http://www.sec.gov/CIK' or str(r.get('entity_identifier','')).zfill(10)!=policy['cik']
                or r.get('source_accession')!=acc or 'us-gaap:LossContingenciesLineItems' not in r.get('presentation_parents',[])
                or not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}' if qname else policy['issuer_namespace_pattern'],str(r.get('namespace','')))
                or isinstance(r['value'],bool) or not isinstance(r['value'],(int,float)) or not isfinite(r['value']) or r['value']<0):
                raise ValueError('environmental balance dimension/entity/presentation invalid')
            key=r['period_end']
            if key in result and (result[key]['value']!=r['value'] or result[key]['context_id']!=r['context_id']):
                raise ValueError('environmental balance conflicting contexts/amounts')
            result[key]=r
        if period not in result:raise ValueError('current environmental balance missing; absence is not zero')
        return result
    gross=balances(qname=policy['reserve_qname']);recoveries=balances(local=policy['recovery_local_name'])
    if gross[period]['context_id']!=recoveries[period]['context_id']:raise ValueError('environmental gross/recovery scopes do not share context')
    normalizer=CompanyFactsNormalizer(companyfacts,fiscal_year_end=submissions.get('fiscalYearEnd'),as_of_date=cutoff)
    annual_cash=[r.as_dict() for r in normalizer.annual_series('operating_cash_flow',5)]
    annual_ends={r['end'] for r in annual_cash};captured={}
    for concept in (*policy['payment_concepts'],*policy['recovery_cash_concepts']):
        captured[concept]=[dict(r) for r in companyfacts.get('facts',{}).get('us-gaap',{}).get(concept,{}).get('units',{}).get('USD',[])
            if r.get('form')=='10-K' and r.get('end') in annual_ends and r.get('filed','')<=cutoff and r.get('start')]
    current_payment_rows=[r for r in facts if r.get('local_name') in policy['payment_concepts'] and r.get('period_end')==period]
    return {'status':'related_balances_verified_forward_cash_review','version':VERSION,'ticker':policy['ticker'],
        'accession':acc,'period_end':period,'gross_reserve':gross[period]['value'],'recoverable_asset':recoveries[period]['value'],
        'related_book_difference_not_pv_or_claim':gross[period]['value']-recoveries[period]['value'],
        'balance_history_from_same_current_packet':{'gross':gross,'recovery':recoveries},
        'annual_reported_operating_cash_flow_inventory':annual_cash,'captured_annual_cash_concept_candidates':captured,
        'current_payment_source_candidates':current_payment_rows,
        'reported_environmental_cash_payments':None,'cash_recovery_timing':None,'payment_schedule':None,
        'forecast_cash_overlap':'not_source_reconciled; reported total OCF retained, no addback or new deduction',
        'claim_adjustment':None,'pv_reserve':None,'numeric_successor_issued':False,
        'recovery_mechanism':terms['environmental_recovery_mechanism'],
        'unquantified_site_scope':terms['environmental_unquantified_scope'],
        'source_receipt_sha256':receipt['receipt_sha256'],
        'review_reasons':['environmental_cash_payments_and_recovery_timing_not_bound',
            'current_reserve_vs_normalized_forecast_cash_overlap_not_reconciled','some_site_cost_shares_undetermined']}
