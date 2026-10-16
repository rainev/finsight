"""A completed settlement payment moves cash and its liability together, once."""
from dataclasses import asdict
from datetime import datetime
from calendar import monthrange
from math import isfinite
from pathlib import Path
import json
import re
from .catalog import canonical_json_bytes
from .refresh_narrative_evidence import narrative_policy,validate_narrative_evidence,terms_by_name
from .refresh_reported_claim_scope import REPORTED_NCI_SCOPE_RULES,reported_nci_field_availability

VERSION='FINSIGHT-SETTLEMENT-PAYMENT-BRIDGE-WG30-1'
RULES={'MCK':{'version':VERSION,'ticker':'MCK','cik':'0000927653',
    'case_member':'NationalPrescriptionOpiateLitigationMember','issuer_namespace_pattern':r'https?://mckesson123\.com/\d{8}'}}

def settlement_payment_policy(ticker):return dict(RULES[ticker])

def reconcile_payment_only(*,cash,liability,payment):
    for value in (cash,liability,payment):
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not isfinite(value) or value<0:
            raise ValueError('settlement payment needs finite nonnegative source amounts')
    if payment>cash or payment>liability:raise ValueError('payment exceeds bound cash or liability; financing/claim movement needed')
    return {'cash_after_payment_only_not_closing_balance':cash-payment,
        'liability_after_payment_only_not_closing_balance':liability-payment,
        'payment_only_net_cash_minus_claim_change':(cash-payment)-(liability-payment)-(cash-liability),
        'actual_post_period_cash':None,'actual_post_period_liability':None,
        'other_cash_and_liability_movements':'not_reconciled','claim_adjustment':None,'numeric_successor_issued':False}

def bind_settlement_payment_bridge(policy,structural,narrative, *,cutoff,source_root):
    if canonical_json_bytes(policy)!=canonical_json_bytes(RULES.get(policy.get('ticker'))):raise ValueError('settlement policy identity/version mismatch')
    receipt=validate_narrative_evidence(narrative,narrative_policy(policy['ticker']),source_root=Path(source_root))
    f=receipt['filing'];acc=f['accession'];period=f['report_date']
    manifest=json.loads((Path(source_root)/receipt['source']['package_manifest_path']).read_bytes())
    metadata=dict(structural.get('filing_metadata',()))
    if metadata.get('package_generation')!=manifest.get('generation') or metadata.get('primary_document')!=receipt['source']['document_name']:
        raise ValueError('settlement narrative and structural packages disagree')
    if (structural.get('source_accession')!=acc or structural.get('report_date')!=period
        or structural.get('filed_date')!=f['filed_date'] or not period<=f['filed_date']<=cutoff):
        raise ValueError('settlement filing/cutoff mismatch')
    terms=terms_by_name(receipt);facts=structural['facts']
    prefixes={r['qname'].split(':',1)[0]:r.get('namespace','') for r in facts}
    def dimensions(r):
        result={}
        for axis,member in r.get('dimensions') or []:
            local=axis.rsplit(':',1)[-1]
            if local in result:raise ValueError('settlement duplicate dimension')
            result[local]=(prefixes.get(axis.split(':',1)[0],''),member.rsplit(':',1)[-1],prefixes.get(member.split(':',1)[0],''))
        return result
    def case_scope(r,axis):
        dims=dimensions(r);term=dims.get(axis)
        return bool(term and re.fullmatch(r'https?://fasb\.org/(?:srt|us-gaap)/20\d{2}',term[0])
            and term[1]==policy['case_member'] and re.fullmatch(policy['issuer_namespace_pattern'],term[2]))
    def one(rows,label,parent):
        if not rows:raise ValueError('settlement '+label+' missing; absence is not zero')
        for r in rows:
            if (r.get('unit')!='USD' or r.get('source_accession')!=acc
                or r.get('entity_scheme')!='http://www.sec.gov/CIK' or str(r.get('entity_identifier','')).zfill(10)!=policy['cik']
                or not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',str(r.get('namespace','')))
                or parent not in r.get('presentation_parents',[]) or isinstance(r['value'],bool)
                or not isinstance(r['value'],(float,int)) or not isfinite(r['value']) or r['value']<0):
                raise ValueError('settlement '+label+' fact identity/value/presentation invalid')
        if len({(r['value'],r['context_id']) for r in rows})!=1:raise ValueError('settlement '+label+' conflicting fact')
        return rows[0]
    balances={}
    for name in ('LossContingencyAccrualAtCarryingValue','LossContingencyAccrualCarryingValueCurrent','LossContingencyAccrualCarryingValueNoncurrent'):
        rows=[r for r in facts if r['qname']=='us-gaap:'+name and r['period_end']==period and r.get('period_start') is None
            and len(dimensions(r))==1 and case_scope(r,'LossContingenciesByNatureOfContingencyAxis')]
        balances[name]=one(rows,name,'us-gaap:LossContingenciesLineItems')
    total=balances['LossContingencyAccrualAtCarryingValue'];current=balances['LossContingencyAccrualCarryingValueCurrent'];noncurrent=balances['LossContingencyAccrualCarryingValueNoncurrent']
    if total['value']!=current['value']+noncurrent['value'] or len({r['context_id'] for r in balances.values()})!=1:
        raise ValueError('settlement aggregate/current/noncurrent do not reconcile')
    cash=one([r for r in facts if r['qname']=='us-gaap:CashAndCashEquivalentsAtCarryingValue' and r['period_end']==period
        and r.get('period_start') is None and not r.get('dimensions')],'cash','us-gaap:AssetsCurrentAbstract')
    payments=[r for r in facts if r['qname']=='us-gaap:PaymentsForLegalSettlements' and case_scope(r,'LitigationCaseAxis')]
    subsequent=[];reported=[]
    for r in payments:
        dims=dimensions(r)
        if len(dims)==1 and r['period_end']==period:reported.append(r)
        if len(dims)==2 and 'SubsequentEventTypeAxis' in dims:
            ns,member,_=dims['SubsequentEventTypeAxis']
            if not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',ns) or member!='SubsequentEventMember':
                raise ValueError('settlement subsequent event scope invalid')
            if not period<r['period_start']<=r['period_end']<=f['filed_date']<=cutoff:raise ValueError('settlement payment date scope invalid')
            subsequent.append(r)
    paid=one(subsequent,'subsequent payment','us-gaap:LossContingenciesLineItems')
    zero=one(reported,'reported period payment','us-gaap:LossContingenciesLineItems')
    # Select the independently reported quarter, not a start date inferred from
    # the settlement fact itself. The duration window only discovers candidates;
    # acceptance below requires exact equality with the issuer's EPS period.
    quarter_refs=[r for r in facts if r.get('qname')=='us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding'
        and r.get('period_end')==period and r.get('period_start') and not r.get('dimensions')
        and 80 <= (datetime.fromisoformat(period)-datetime.fromisoformat(r['period_start'])).days <= 100]
    if not quarter_refs or any(r.get('unit')!='xbrli:shares' or r.get('source_accession')!=acc
        or r.get('entity_scheme')!='http://www.sec.gov/CIK' or str(r.get('entity_identifier','')).zfill(10)!=policy['cik']
        or not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',str(r.get('namespace','')))
        or 'income_statement' not in r.get('statement_roles',[])
        or 'us-gaap:EarningsPerShareDilutedLineItems' not in r.get('presentation_parents',[]) for r in quarter_refs):
        raise ValueError('settlement independent reported quarter reference missing/invalid')
    quarter_starts={r['period_start'] for r in quarter_refs}
    if len(quarter_starts)!=1 or zero['period_start'] not in quarter_starts:
        raise ValueError('settlement payment interval differs from independently reported quarter')
    month=datetime.strptime(terms['payment_month']['value'],'%B %Y')
    month_end=month.replace(day=monthrange(month.year,month.month)[1]).strftime('%Y-%m-%d')
    if (paid['period_start']!=month.strftime('%Y-%m-01') or paid['period_end']!=month_end
        or not zero.get('period_start') or not 80 <= (datetime.fromisoformat(period)-datetime.fromisoformat(zero['period_start'])).days <= 100):
        raise ValueError('settlement narrative month/quarter interval mismatch')
    if (paid['value']!=terms['subsequent_settlement_payment']['value'] or zero['value']!=terms['reported_period_payments']['value']
        or terms['reported_zero_period_end']['value']!=period or datetime.strptime(terms['payment_month']['value'],'%B %Y').strftime('%Y-%m')!=paid['period_start'][:7]
        or paid['period_start'][:7]!=paid['period_end'][:7] or not zero.get('period_start')):
        raise ValueError('settlement narrative/tagged payment do not agree')
    _,ownership=reported_nci_field_availability(ticker=policy['ticker'],policy=asdict(REPORTED_NCI_SCOPE_RULES[policy['ticker']]),
        structural_packet=structural,accession=acc,period_end=period)
    return {'status':'payment_only_cash_liability_reconciled_full_scope_review','version':VERSION,'ticker':policy['ticker'],
        'accession':acc,'period_end':period,'source_receipt_sha256':receipt['receipt_sha256'],'sources':{'cash':cash,'liabilities':balances,
        'reported_period_payment':zero,'subsequent_payment':paid,'independent_quarter_period_sources':quarter_refs},'ownership_carrying_proof':ownership,
        'payment_only_bridge':reconcile_payment_only(cash=cash['value'],liability=total['value'],payment=paid['value']),
        'payment_only_assumption':'same-program cash payment reduces accrued liability dollar-for-dollar; not a reported closing-balance rollforward',
        'remaining_liability_payment_schedule':None,'payment_day':None,'numeric_successor_issued':False,
        'review_reasons':['complete_post_period_cash_debt_and_other_movements_not_reconciled',
            'payment_allocation_to_accrual_components_not_source_bound','payment_funding_source_not_reconciled',
            'redeemable_preferred_and_put_right_economic_basis_unapproved','securities_cash_like_classification_not_approved',
            'remaining_legal_payment_schedule_and_forecast_cash_overlap_unbound','unrelated_acquisition_and_operating_claims_retained']}
