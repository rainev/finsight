"""Reconciled subsidiary financing evidence, not an invented instrument value."""
from math import isfinite
from pathlib import Path
from datetime import date
import json
import re
from .refresh_narrative_evidence import narrative_policy,validate_narrative_evidence,terms_by_name
from .refresh_reported_claim_scope import REPORTED_NCI_SCOPE_RULES,reported_nci_field_availability
from dataclasses import asdict

VERSION='FINSIGHT-SUBSIDIARY-PREFERRED-BRIDGE-WG27-1'
RULES={'LHX':{'version':VERSION,'ticker':'LHX','cik':'0000202058',
    'feature_member':'SubsidiarySeriesAPreferredStockConversionFeatureMember',
    'warrant_member':'SubsidiaryWarrantsMember',
    'issuer_namespace_pattern':r'https?://harris\.com/\d{8}'}}

def subsidiary_preferred_policy(ticker):
    if ticker not in RULES:raise ValueError('unsupported subsidiary preferred scope')
    return dict(RULES[ticker])

def claim_basis_diagnostic(basis, *, host,feature,warrant,cash_claim=None,converted_shares=None):
    for v in (host,feature,warrant):
        if isinstance(v,bool) or not isinstance(v,(float,int)) or not isfinite(v) or v<0:
            raise ValueError('claim basis needs nonnegative finite reported components')
    if cash_claim is not None and converted_shares is not None:
        raise ValueError('cash settlement and conversion dilution are mutually exclusive')
    for v in (cash_claim,converted_shares):
        if v is not None and (isinstance(v,bool) or not isinstance(v,(float,int)) or not isfinite(v) or v<=0):
            raise ValueError('alternative claim basis requires positive finite source-backed quantities')
    if (basis=='cash_settlement' and converted_shares is not None) or (basis=='conversion_dilution' and cash_claim is not None):
        raise ValueError('alternative quantity does not match selected preferred basis')
    if basis=='reported_accounting_diagnostic':
        if cash_claim is not None or converted_shares is not None:raise ValueError('accounting exposure cannot include alternative settlement/dilution')
        return {'basis':basis,'reported_accounting_exposure':host+feature+warrant,
            'economic_claim_value':None,'numeric_valuation_approved':False}
    if basis not in {'cash_settlement','conversion_dilution'}:raise ValueError('unknown preferred claim basis')
    if feature!=0 or host!=0:
        raise ValueError('full preferred settlement/dilution cannot also deduct host or bifurcated conversion/redemption features')
    return {'basis':basis,'economic_claim_value':None,'numeric_valuation_approved':False,
        'reason':'source_supported_subsidiary_value_or_settlement_and_parent_scope_required'}

def bind_subsidiary_preferred_bridge(policy,structural,narrative, *, cutoff,source_root):
    if policy!=RULES.get(policy.get('ticker')):raise ValueError('subsidiary preferred policy identity/version mismatch')
    receipt=validate_narrative_evidence(narrative,narrative_policy(policy['ticker']),source_root=Path(source_root))
    f=receipt['filing'];acc=f['accession'];period=f['report_date']
    date.fromisoformat(cutoff)
    manifest=json.loads((Path(source_root)/receipt['source']['package_manifest_path']).read_bytes())
    metadata=dict(structural.get('filing_metadata',()))
    if metadata.get('package_generation')!=manifest.get('generation') or metadata.get('primary_document')!=receipt['source']['document_name']:
        raise ValueError('preferred narrative and structural source packages disagree')
    if (structural['source_accession']!=acc or structural['report_date']!=period
        or structural['filed_date']!=f['filed_date'] or not period<=f['filed_date']<=cutoff):
        raise ValueError('subsidiary preferred filing/cutoff scope mismatch')
    terms={k:v['value'] for k,v in terms_by_name(receipt).items()}
    if terms['host_balance_date']!=period:raise ValueError('host rollforward does not reach current reporting period')
    _,ownership=reported_nci_field_availability(ticker=policy['ticker'],policy=asdict(REPORTED_NCI_SCOPE_RULES[policy['ticker']]),
        structural_packet=structural,accession=acc,period_end=period)
    def derivative(member):
        rows=[r for r in structural['facts'] if r['qname']=='us-gaap:DerivativeLiabilitiesNoncurrent' and r['period_end']==period
            and r.get('period_start') is None and dict(r.get('dimensions') or []).get('us-gaap:DerivativeInstrumentRiskAxis','').rsplit(':',1)[-1]==member]
        prefixes={r['qname'].split(':',1)[0] for r in structural['facts'] if re.fullmatch(policy['issuer_namespace_pattern'],str(r.get('namespace','')))}
        for r in rows:
            dims=dict(r.get('dimensions') or [])
            if (len(dims)!=1 or str(dims['us-gaap:DerivativeInstrumentRiskAxis']).split(':',1)[0] not in prefixes
                or r.get('unit')!='USD' or r.get('entity_scheme')!='http://www.sec.gov/CIK'
                or str(r.get('entity_identifier','')).zfill(10)!=policy['cik'] or r.get('source_accession')!=acc
                or not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',str(r.get('namespace','')))
                or 'balance_sheet' not in r.get('statement_roles',[]) or 'us-gaap:LiabilitiesNoncurrentAbstract' not in r.get('presentation_parents',[])
                or isinstance(r['value'],bool) or not isinstance(r['value'],(int,float)) or not isfinite(r['value']) or r['value']<0):
                raise ValueError('subsidiary derivative identity/dimension/presentation invalid')
        values={r['value'] for r in rows}
        if len(values)!=1:raise ValueError('current subsidiary derivative missing/conflicting; absence is not zero')
        return float(values.pop()),rows
    feature,fs=derivative(policy['feature_member']);warrant,ws=derivative(policy['warrant_member'])
    if terms['initial_host']+terms['initial_feature']+terms['initial_warrant']!=terms['gross_cash']+terms['program_asset']:
        raise ValueError('initial financing allocation does not reconcile to cash and noncash program asset')
    if (terms['roll_tax']!=terms['deferred_tax'] or terms['roll_costs']!=terms['transaction_costs']
        or terms['initial_host']-terms['roll_tax']-terms['roll_costs']+terms['deemed_dividend']!=terms['current_host']
        or terms['current_host']!=ownership['source_total'] or terms['gross_cash']-terms['transaction_costs']!=terms['net_cash']):
        raise ValueError('preferred carrying/proceeds rollforward does not reconcile')
    proceeds=[r for r in structural['facts'] if r['qname']=='us-gaap:ProceedsFromIssuanceOfRedeemableConvertiblePreferredStock'
        and r.get('period_end')==period and r.get('period_start') and not r.get('dimensions')]
    if not proceeds:raise ValueError('current reported preferred financing proceeds missing; not zero')
    for r in proceeds:
        if (r.get('unit')!='USD' or r.get('source_accession')!=acc or str(r.get('entity_identifier','')).zfill(10)!=policy['cik']
            or r.get('entity_scheme')!='http://www.sec.gov/CIK' or 'cash_flow' not in r.get('statement_roles',[])
            or 'us-gaap:NetCashProvidedByUsedInFinancingActivitiesAbstract' not in r.get('presentation_parents',[])
            or r['value']!=terms['net_cash']):raise ValueError('reported financing proceeds and narrative scope do not reconcile')
    shares=[r for r in structural['facts'] if r.get('qname')=='us-gaap:CommonStockSharesOutstanding'
        and r.get('period_end')==period and r.get('period_start') is None and not r.get('dimensions')]
    if not shares or any(r.get('unit')!='xbrli:shares' or r.get('source_accession')!=acc or
        str(r.get('entity_identifier','')).zfill(10)!=policy['cik'] or isinstance(r.get('value'),bool) or
        not isinstance(r.get('value'),(int,float)) or not isfinite(r['value']) or r['value']<=0 for r in shares):
        raise ValueError('current reported parent shares missing/invalid; subsidiary percentages cannot substitute')
    if len({r['value'] for r in shares})!=1:raise ValueError('current parent shares conflict')
    return {'status':'accounting_reconciled_economic_review','version':VERSION,'ticker':policy['ticker'],
        'accession':acc,'period_end':period,'source_receipt_sha256':receipt['receipt_sha256'],'terms':terms,
        'current_host_carrying':ownership['source_total'],'current_feature_liability':feature,'current_warrant_liability':warrant,
        'current_derivative_sources':fs+ws,'claim_basis':claim_basis_diagnostic('reported_accounting_diagnostic',host=ownership['source_total'],feature=feature,warrant=warrant),
        'program_asset_treatment':'noncash operating intangible; no surplus cash or unproved intrinsic-value addback',
        'proceeds_treatment':'already in ending cash; no second cash addition',
        'parent_as_converted_shares':None,'numeric_successor_issued':False,
        'reported_period_end_parent_shares':shares[0]['value'],'parent_share_basis':'reported parent common; no subsidiary percentage applied; legacy recipe unchanged',
        'review_reasons':['subsidiary_preferred_economic_settlement_or_conversion_and_parent_scope_unapproved',
            'program_operating_cash_benefit_not_source_bounded','environmental_forward_cash_recovery_overlap_required']}
