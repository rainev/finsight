"""Source carrying movements and contract evidence do not invent subsidiary value."""
from dataclasses import asdict
from copy import deepcopy
from math import isfinite
from pathlib import Path
import re
from .refresh_narrative_evidence import narrative_policy,validate_narrative_evidence,terms_by_name
from .refresh_settlement_payment_bridge import bind_settlement_payment_bridge,settlement_payment_policy
from .refresh_reported_claim_scope import REPORTED_NCI_SCOPE_RULES,reported_nci_field_availability
from .arelle_worker import _QNameCanonicalizer

VERSION='FINSIGHT-SUBSIDIARY-OWNERSHIP-SCOPE-WG31-1'
RULES={'MCK':{'version':VERSION,'ticker':'MCK','cik':'0000927653',
    'issuer_namespace_pattern':r'https?://mckesson123\.com/\d{8}',
    'redemption_component_members':{'MedicalSurgicalSolutionsSegmentMember':'mms_redemption','CoreVenturesMember':'core_redemption'}}}

def subsidiary_ownership_policy(ticker):return deepcopy(RULES[ticker])

def ownership_basis_diagnostic(*,cash_claim=None,parent_conversion_shares=None):
    if cash_claim is not None and parent_conversion_shares is not None:
        raise ValueError('preferred cash claim and conversion dilution cannot both apply')
    if cash_claim is not None or parent_conversion_shares is not None:
        raise ValueError('source-supported subsidiary outcomes and parent attribution required; no invented quantities')
    return {'economic_claim':None,'parent_conversion_shares':None,'cash_redemption_claim':None,
        'claim_adjustment':None,'numeric_successor_issued':False}

def bind_subsidiary_ownership_scope(policy,structural,narrative, *,cutoff,source_root):
    if policy!=RULES.get(policy.get('ticker')):raise ValueError('subsidiary ownership policy identity/version mismatch')
    receipt=validate_narrative_evidence(narrative,narrative_policy(policy['ticker']),source_root=Path(source_root))
    payment=bind_settlement_payment_bridge(settlement_payment_policy(policy['ticker']),structural,narrative,cutoff=cutoff,source_root=source_root)
    filing=receipt['filing'];period=filing['report_date'];acc=filing['accession']
    terms=terms_by_name(receipt);t={name:term['value'] for name,term in terms.items()}
    _,ownership=reported_nci_field_availability(ticker=policy['ticker'],policy=asdict(REPORTED_NCI_SCOPE_RULES[policy['ticker']]),
        structural_packet=structural,accession=acc,period_end=period)
    stocks={r['qname']:r['value'] for r in ownership['components']}
    ordinary=t['ordinary_begin']+t['ordinary_income']-t['ordinary_distribution']-t['ordinary_other']
    redeemable=t['redeemable_begin']+t['redeemable_income']+t['redeemable_fair']+t['redeemable_redemption']+t['net_sale']-t['redeemable_other']
    if (ordinary!=t['ordinary_end'] or redeemable!=t['redeemable_end']
        or ordinary!=stocks['us-gaap:MinorityInterest']
        or redeemable!=stocks['us-gaap:RedeemableNoncontrollingInterestEquityCommonCarryingAmount']
        or t['mms_redemption']+t['core_redemption']!=t['redeemable_redemption']):
        raise ValueError('subsidiary ordinary/redeemable/redemption rollforward does not reconcile')
    facts=structural['facts'];start=payment['sources']['reported_period_payment']['period_start']
    prefixes={r['qname'].split(':',1)[0]:r.get('namespace','') for r in facts}
    canonicalizer=_QNameCanonicalizer()
    def one(rows,label, *,parent,issuer=False,role=None):
        if not rows:raise ValueError('subsidiary '+label+' missing; absence is not zero')
        for r in rows:
            if (r.get('source_accession')!=acc or r.get('unit')!='USD' or r.get('entity_scheme')!='http://www.sec.gov/CIK'
                or str(r.get('entity_identifier','')).zfill(10)!=policy['cik']
                or not re.fullmatch(policy['issuer_namespace_pattern'] if issuer else r'https?://fasb\.org/us-gaap/20\d{2}',str(r.get('namespace','')))
                or r.get('qname')!=canonicalizer.prefix(str(r.get('namespace','')))+':'+str(r.get('local_name',''))
                or (role is not None and role not in r.get('statement_roles',[]))
                or parent not in r.get('presentation_parents',[]) or isinstance(r['value'],bool)
                or not isinstance(r['value'],(float,int)) or not isfinite(r['value']) or r['value']<0):
                raise ValueError('subsidiary '+label+' source scope invalid')
        if len({(r['value'],r['context_id']) for r in rows})!=1:raise ValueError('subsidiary '+label+' conflicting source')
        return rows[0]
    proceeds=one([r for r in facts if r.get('local_name')=='ProceedsFromSaleOfNoncontrollingInterests'
        and r.get('period_start')==start and r['period_end']==period and not r.get('dimensions')],
        'net financing proceeds',parent='us-gaap:NetCashProvidedByUsedInFinancingActivitiesAbstract',issuer=True,role='cash_flow')
    if proceeds['value']!=t['net_sale'] or 'cash_flow' not in proceeds.get('statement_roles',[]):
        raise ValueError('subsidiary net proceeds and ownership rollforward disagree')
    components={}
    for member,name in policy['redemption_component_members'].items():
        rows=[]
        for r in facts:
            if r.get('qname')!='us-gaap:TemporaryEquityAccretionToRedemptionValueAdjustment' or r.get('period_start')!=start or r['period_end']!=period:continue
            dims=list(r.get('dimensions') or [])
            if len(dims)!=1 or dims[0][1].rsplit(':',1)[-1]!=member:continue
            axis,mem=dims[0]
            expected_axis='StatementBusinessSegmentsAxis' if member=='MedicalSurgicalSolutionsSegmentMember' else 'BusinessAcquisitionAxis'
            if (axis.rsplit(':',1)[-1]!=expected_axis or not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',prefixes.get(axis.split(':',1)[0],''))
                or not re.fullmatch(policy['issuer_namespace_pattern'],prefixes.get(mem.split(':',1)[0],''))):
                raise ValueError('subsidiary redemption component axis/member invalid')
            rows.append(r)
        component=one(rows,name,parent='us-gaap:MinorityInterestLineItems')
        if component['value']!=t[name]:raise ValueError('subsidiary redemption source/narrative mismatch')
        components[member]=component
    parent_preferred=one([r for r in facts if r.get('qname')=='us-gaap:PreferredStockValue' and r['period_end']==period
        and r.get('period_start') is None and not r.get('dimensions')],'parent preferred',parent='us-gaap:StockholdersEquityAbstract',role='balance_sheet')
    if 'balance_sheet' not in parent_preferred.get('statement_roles',[]):raise ValueError('subsidiary parent preferred balance-sheet role missing')
    if not period>=t['apollo_event_date'] or t['historical_rni_period_end']>=period:
        raise ValueError('subsidiary current event/historical acquisition period mismatch')
    return {'status':'carrying_rollforward_and_mechanisms_verified_economic_basis_review','version':VERSION,
        'ticker':policy['ticker'],'accession':acc,'period_end':period,'source_receipt_sha256':receipt['receipt_sha256'],
        'reported_ordinary_carrying':ordinary,'reported_redeemable_carrying':redeemable,'ownership_carrying_proof':ownership,
        'reported_terms':terms,'redemption_movement_sources':components,'net_proceeds_source':proceeds,
        'parent_preferred_source':parent_preferred,'financing_cash_adjustment':None,
        'proceeds_treatment':'already reflected in reported ending cash; no second cash addition; approximate gross investment not net proceeds',
        'instrument_economic_basis':ownership_basis_diagnostic(),'first_put_exercise_date':None,'put_payment_schedule':None,
        'numeric_successor_issued':False,'review_reasons':['apollo_conversion_redemption_strike_coupon_and_parent_scope_not_captured',
            'prism_core_put_formula_exercise_state_and_current_component_values_not_captured',
            'reported_carrying_and_issuer_monte_carlo_not_independent_intrinsic_claim',
            'mck_cash_securities_funding_allocation_and_legal_overlap_remain_required']}
