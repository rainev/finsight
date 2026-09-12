"""Source-bound exclusion of unconsolidated VIE investment exposure from NCI."""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
from numbers import Real
from types import MappingProxyType
from typing import Any, Mapping

from .field_availability import FieldAvailability


SCHEMA = "FINSIGHT-UNCONSOLIDATED-VIE-SCOPE-1"
VERSION = "FINSIGHT-UNCONSOLIDATED-VIE-SCOPE-WG13-1"

RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "A": MappingProxyType({
        "schema_version": SCHEMA, "version": VERSION, "ticker": "A", "cik": "0001090872",
        "exposure_qname": "us-gaap:NoncontrollingInterestInVariableInterestEntity",
        "investment_qname": "us-gaap:LongTermInvestments",
        "required_ancestry": "us-gaap:VariableInterestEntityNotPrimaryBeneficiaryDisclosuresAbstract",
        "treatment": "retain the unconsolidated not-primary-beneficiary VIE carrying exposure as an investment diagnostic; do not deduct it as issuer NCI or add it separately to investments",
    }),
})


class VieScopeReviewRequired(ValueError):
    pass


def unconsolidated_vie_scope_policy(ticker: str) -> dict[str, Any]:
    rule=RULES.get(ticker.upper())
    if rule is None:
        raise ValueError(f"no unconsolidated VIE scope policy for {ticker!r}")
    return deepcopy(dict(rule))


def _number(value: Any,label: str) -> float:
    if isinstance(value,bool) or not isinstance(value,Real) or not isfinite(float(value)):
        raise VieScopeReviewRequired(f"{label} is not finite numeric evidence")
    return float(value)


def bind_unconsolidated_vie_scope(*, ticker: str, policy: Mapping[str, Any], structural: Mapping[str, Any],
                                  accession: str, period: str) -> tuple[FieldAvailability,dict[str,Any]]:
    expected=RULES.get(ticker)
    if expected is None or dict(policy)!=dict(expected):
        raise VieScopeReviewRequired("unconsolidated VIE policy identity/version mismatch")
    if structural.get('source_accession')!=accession or (structural.get('report_date') or structural.get('period_end'))!=period:
        raise VieScopeReviewRequired("unconsolidated VIE structural identity mismatch")
    metadata=dict(structural.get('filing_metadata',()))
    if metadata.get('manifest_version')!='FINSIGHT-XBRL-PACKAGE-1' or not metadata.get('package_generation'):
        raise VieScopeReviewRequired("complete structural filing package receipt is required")
    facts=structural.get('facts')
    if not isinstance(facts,list):
        raise VieScopeReviewRequired("unconsolidated VIE facts are missing")
    current=[row for row in facts if isinstance(row,Mapping) and row.get('source_accession')==accession
        and row.get('period_end')==period and row.get('period_start') is None
        and row.get('entity_scheme')=='http://www.sec.gov/CIK'
        and str(row.get('entity_identifier','')).zfill(10)==policy['cik']]
    exposure=[row for row in current if row.get('qname')==policy['exposure_qname'] and row.get('unit')=='USD'
        and row.get('dimensions') in (None,[]) and policy['required_ancestry'] in (row.get('presentation_ancestry') or [])
        and 'balance_sheet' not in (row.get('statement_roles') or [])]
    exposure_values={_number(row.get('value'),'VIE exposure') for row in exposure}
    if len(exposure_values)!=1 or min(exposure_values)<=0:
        raise VieScopeReviewRequired("unconsolidated VIE exposure is missing, conflicting or nonpositive")
    investment=[row for row in current if row.get('qname')==policy['investment_qname'] and row.get('unit')=='USD'
        and row.get('dimensions') in (None,[]) and 'balance_sheet' in (row.get('statement_roles') or [])]
    investment_values={_number(row.get('value'),'long-term investments') for row in investment}
    if len(investment_values)!=1 or min(investment_values)<next(iter(exposure_values)):
        raise VieScopeReviewRequired("VIE exposure does not fit the reported investment balance")
    ordinary=[]
    for row in current:
        local=str(row.get('local_name','')).lower()
        if row.get('qname')==policy['exposure_qname'] or row.get('unit')!='USD' or row.get('dimensions') not in (None,[]):
            continue
        if local=='stockholdersequityincludingportionattributabletononcontrollinginterest':
            continue
        if any(token in local for token in ('minorityinterest','noncontrollinginterest','redeemablenoncontrolling')):
            if _number(row.get('value'),'ordinary NCI marker')!=0:
                ordinary.append(row)
    if ordinary:
        raise VieScopeReviewRequired("ordinary consolidated NCI conflicts with unconsolidated-only scope")
    sources=[exposure[0],investment[0]]
    refs=tuple(f"{accession}|{period}|{row['qname']}|{row['context_id']}" for row in sources)
    availability=FieldAvailability(
        field='noncontrolling_interests',value=0.,state='evidence_backed_zero',
        reason_code='UNCONSOLIDATED_VIE_EXPOSURE_IS_NOT_ISSUER_NCI',period_end=period,
        source_accession=accession,source_kind='structural_xbrl',
        evidence_class='reported_component_reconciliation',freshness='current',
        fallback_level='current_structural',covered_fields=('noncontrolling_interests',),
        coverage_basis='reconciled_disjoint_components',coverage_source_facts=refs,
        economic_scope='issuer NCI excludes unconsolidated not-primary-beneficiary VIE investments and loans',
        extraction_complete=True,searched_concepts=(policy['exposure_qname'],policy['investment_qname'],'ordinary NCI concepts'),
        authority='production',mapping_version=VERSION)
    return availability,{
        'status':'source_bound','schema_version':SCHEMA,'policy_version':VERSION,
        'ticker':ticker,'cik':policy['cik'],'accession':accession,'period_end':period,
        'issuer_nci':0.,'unconsolidated_vie_exposure':next(iter(exposure_values)),
        'reported_long_term_investments':next(iter(investment_values)),
        'sources':sources,'treatment':policy['treatment']}


__all__=['RULES','SCHEMA','VERSION','VieScopeReviewRequired','bind_unconsolidated_vie_scope','unconsolidated_vie_scope_policy']
