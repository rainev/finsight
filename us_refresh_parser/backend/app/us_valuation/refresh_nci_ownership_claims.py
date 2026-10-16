"""NCI-adjacent claim scopes that must remain separate from owner balances."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from math import isfinite
import re
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA="FINSIGHT-NCI-OWNERSHIP-CLAIM-1"
VERSION="FINSIGHT-NCI-OWNERSHIP-CLAIM-WG14-1"
_GAAP=re.compile(r"^https?://(?:fasb\.org|xbrl\.us-gaap)/us-gaap/20\d{2}$")

RULES:Mapping[str,Mapping[str,Any]]=MappingProxyType({
    "APD":MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"APD","cik":"0000002969",
        "mode":"parent_equity_nci_with_vie_subset",
        "nci_qname":"us-gaap:MinorityInterest",
        "total_equity_qname":"us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "parent_member":"us-gaap:ParentMember",
        "nci_member":"us-gaap:NoncontrollingInterestMember",
        "vie_member":"us-gaap:VariableInterestEntityPrimaryBeneficiaryMember",
        "nci_income_qname":"us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
        "treatment":"use parent equity and parent/common earnings directly; retain total NCI, consolidated VIE subset and owner flows as reconciliation diagnostics without a second deduction",
    }),
    "CMI":MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"CMI","cik":"0000026172",
        "mode":"guarantee_scope_review",
        "nci_qname":"us-gaap:MinorityInterest",
        "guarantee_carrying_qname":"us-gaap:GuaranteeObligationsCurrentCarryingValue",
        "guarantee_maximum_qname":"us-gaap:GuaranteeObligationsMaximumExposure",
        "investment_qname":"us-gaap:InvestmentsInAffiliatesSubsidiariesAssociatesAndJointVentures",
        "contributed_qname":"us-gaap:PaymentsToAcquireInterestInJointVenture",
        "remaining_contribution_local_name":"TotalRemainingJointVentureContribution",
        "investee_member":"AmplifyCellTechnologiesLLCMember",
        "issuer_namespace_pattern":r"https?://(?:www\.)?cummins\.com/\d{8}",
        "treatment":"deduct current NCI once; keep recognized guarantee carrying value, guarantee maximum, unconsolidated VIE investment, paid contribution and future contribution separate until their scopes and timing reconcile",
    }),
})


def nci_ownership_claim_policy(ticker:str)->dict[str,Any]:
    rule=RULES.get(ticker.upper())
    if rule is None:raise ValueError(f"no NCI ownership claim policy for {ticker!r}")
    return deepcopy(dict(rule))


def _same(actual:Mapping[str,Any],expected:Mapping[str,Any])->bool:
    return json.dumps(dict(actual),sort_keys=True,separators=(",",":"))==json.dumps(dict(expected),sort_keys=True,separators=(",",":"))


def _one(facts:list[dict[str,Any]],qname:str|None,*,policy:Mapping[str,Any],accession:str,period:str,
         instant:bool=True,member:str|None=None,local_name:str|None=None,issuer:bool=False)->dict[str,Any]:
    def scoped(row):
        dims=row.get('dimensions') or []
        member_local=str(member).rsplit(':',1)[-1] if member else None
        has_member=any(isinstance(pair,(list,tuple)) and len(pair)==2 and str(pair[1]).rsplit(':',1)[-1]==member_local for pair in dims) if member else not dims
        return ((qname is None or row.get('qname')==qname) and (local_name is None or row.get('local_name')==local_name)
            and row.get('period_end')==period and (row.get('period_start') is None)==instant and has_member)
    rows=[row for row in facts if scoped(row)]
    for row in rows:
        if (row.get('source_accession')!=accession or row.get('unit')!='USD'
            or str(row.get('entity_identifier','')).zfill(10)!=policy['cik']
            or row.get('entity_scheme')!='http://www.sec.gov/CIK'
            or not (re.fullmatch(str(policy['issuer_namespace_pattern']),str(row.get('namespace',''))) if issuer else _GAAP.fullmatch(str(row.get('namespace',''))))
            or isinstance(row.get('value'),bool) or not isinstance(row.get('value'),(int,float))
            or not isfinite(float(row['value'])) or float(row['value'])<0):
            raise ValueError('NCI-adjacent claim identity, unit or amount invalid')
    values={float(row['value']) for row in rows}
    if not rows or len(values)!=1:raise ValueError(f'NCI-adjacent claim fact missing or conflicting: {qname or local_name}')
    return dict(rows[0])


def select_nci_ownership_claim(policy:Mapping[str,Any],structural:Mapping[str,Any],controlling:Mapping[str,Any],cik:str,cutoff:str)->dict[str,Any]:
    expected=RULES.get(policy.get('ticker'))
    if expected is None or not _same(policy,expected) or str(cik).zfill(10)!=expected['cik']:
        raise RuntimeError('NCI ownership claim policy identity/version mismatch')
    accession=controlling.get('accessionNumber') or controlling.get('accession')
    period=controlling.get('reportDate') or controlling.get('period_end')
    filed=controlling.get('filingDate') or structural.get('filed_date')
    if (structural.get('source_accession')!=accession or not isinstance(period,str) or not isinstance(filed,str)
        or not period<=filed<=cutoff):raise ValueError('NCI ownership claim source period/accession/cutoff mismatch')
    date.fromisoformat(period);date.fromisoformat(filed);date.fromisoformat(cutoff)
    facts=structural.get('facts')
    if not isinstance(facts,list):raise ValueError('NCI ownership structural facts missing')
    if policy['mode']=='parent_equity_nci_with_vie_subset':
        total=_one(facts,policy['nci_qname'],policy=policy,accession=accession,period=period)
        subset=_one(facts,policy['nci_qname'],policy=policy,accession=accession,period=period,
            member=policy['vie_member'])
        total_equity=_one(facts,policy['total_equity_qname'],policy=policy,accession=accession,period=period)
        parent_equity=_one(facts,policy['total_equity_qname'],policy=policy,accession=accession,period=period,
            member=policy['parent_member'])
        nci_component=_one(facts,policy['total_equity_qname'],policy=policy,accession=accession,period=period,
            member=policy['nci_member'])
        total_value=float(total['value']);subset_value=float(subset['value'])
        if not 0<=subset_value<=total_value:
            raise ValueError('consolidated VIE NCI subset exceeds total NCI')
        if float(nci_component['value'])!=total_value or abs(float(total_equity['value'])-float(parent_equity['value'])-total_value)>.01:
            raise ValueError('parent and total equity do not reconcile to current NCI')
        income=[dict(row) for row in facts if row.get('qname')==policy['nci_income_qname']
            and row.get('source_accession')==accession and row.get('period_end')==period
            and isinstance(row.get('period_start'),str) and row.get('unit')=='USD'
            and row.get('dimensions') in (None,[]) and str(row.get('entity_identifier','')).zfill(10)==policy['cik']]
        if not income:
            raise ValueError('current NCI earnings reconciliation is missing')
        return {'status':'source_bound','claim_adjustment':0.,'review_reasons':[],
            'policy':dict(policy),'period_end':period,'controlling_accession':accession,
            'components':{'total_nci':total_value,'consolidated_vie_nci_subset':subset_value,
                'parent_equity':float(parent_equity['value']),'total_equity':float(total_equity['value']),
                'nci_deducted_again':False},
            'source_rows':[total,subset,total_equity,parent_equity,nci_component,*income],
            'formula':'total equity minus current NCI equals parent equity; parent-equity residual income makes NCI and the VIE subset diagnostics, not additional claims'}
    if policy['mode']!='guarantee_scope_review':
        raise RuntimeError('unsupported NCI ownership claim mode')
    nci=_one(facts,policy['nci_qname'],policy=policy,accession=accession,period=period)
    carrying=_one(facts,policy['guarantee_carrying_qname'],policy=policy,accession=accession,period=period)
    maximum=_one(facts,policy['guarantee_maximum_qname'],policy=policy,accession=accession,period=period)
    investment=_one(facts,policy['investment_qname'],policy=policy,accession=accession,period=period,
        member=policy['investee_member'])
    contributed=_one(facts,policy['contributed_qname'],policy=policy,accession=accession,period=period,
        instant=False,member=policy['investee_member'])
    remaining=_one(facts,None,policy=policy,accession=accession,period=period,
        member=policy['investee_member'],local_name=policy['remaining_contribution_local_name'],issuer=True)
    # A carrying balance larger than the disclosed maximum proves these rows
    # cannot describe one additive or directly nettable obligation.
    review=[]
    if float(carrying['value'])!=float(maximum['value']):
        review.append('guarantee_carrying_value_and_maximum_have_unreconciled_scopes')
    if float(remaining['value'])>0:
        review.append('unconsolidated_vie_future_contribution_has_no_timed_payment_schedule')
    return {
        'status':'review_required' if review else 'source_bound',
        'claim_adjustment':None if review else float(carrying['value']),
        'review_reasons':review,'policy':dict(policy),'period_end':period,
        'controlling_accession':accession,
        'components':{'ordinary_nci':float(nci['value']),
            'recognized_guarantee_carrying_value':float(carrying['value']),
            'guarantee_maximum':float(maximum['value']),
            'guarantee_added_to_nci':False,
            'unconsolidated_vie_investment':float(investment['value']),
            'joint_venture_contributions_paid':float(contributed['value']),
            'future_joint_venture_contribution':float(remaining['value']),
            'vie_investment_or_contribution_added_to_nci':False},
        'source_rows':[nci,carrying,maximum,investment,contributed,remaining],
        'formula':'current NCI remains in the ownership bridge; guarantee and unconsolidated VIE investment/contribution rows remain separate until scope and timing reconcile',
    }


__all__=['RULES','SCHEMA','VERSION','nci_ownership_claim_policy','select_nci_ownership_claim']
