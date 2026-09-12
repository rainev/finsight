"""Narrow, source-bound acquisition liability rules; no missing-fact zeros."""
from copy import deepcopy
from datetime import date, timedelta
from math import isfinite
import re
import hashlib
from types import MappingProxyType
from typing import Any, Mapping

SCHEMA = 'FINSIGHT-ACQUISITION-CLAIM-1'
QNAME = 'us-gaap:BusinessCombinationContingentConsiderationLiability'
COMPONENTS = (QNAME + 'Current', QNAME + 'Noncurrent')
WG2_VERSION = 'FINSIGHT-ACQUISITION-CLAIM-WG2-1'
WG15_VERSION = 'FINSIGHT-ACQUISITION-CLAIM-WG15-1'


WG2_CLAIM_RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    'VRTX': {
        'schema_version':SCHEMA,'version':WG2_VERSION,'ticker':'VRTX','cik':'0000875320',
        'mode':'direct_total','qname':QNAME,
        'allowed_current_qnames':(QNAME,QNAME+'Current',QNAME+'Noncurrent'),
        'treatment':'current reported carrying liability deducted once; subsequent signed acquisition consideration stays on the event surface',
    },
    'LLY': {
        'schema_version':SCHEMA,'version':WG2_VERSION,'ticker':'LLY','cik':'0000059478',
        'mode':'level3_components','component_qnames':COMPONENTS,
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'requires_post_period_cash_paid_source':True,
        'treatment':'current and noncurrent Level-3 carrying liabilities summed once; acquisition maxima and transferred consideration are not current liabilities',
    },
    'CTSH': {
        'schema_version':SCHEMA,'version':WG2_VERSION,'ticker':'CTSH','cik':'0001058290',
        'mode':'duplicate_presentations','qname':QNAME,
        'location_axis':'us-gaap:BalanceSheetLocationAxis',
        'location_member':'us-gaap:OtherCurrentLiabilitiesMember',
        'frequency_axis':'us-gaap:FairValueByMeasurementFrequencyAxis',
        'frequency_member':'us-gaap:FairValueMeasurementsRecurringMember',
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'treatment':'matching aggregate and Level-3 presentations are one current liability, never a sum',
    },
    'VRT': {
        'schema_version':SCHEMA,'version':WG2_VERSION,'ticker':'VRT','cik':'0001674101',
        'mode':'custom_total_corroborated','issuer_namespace_pattern':r'https?://(?:www\.)?vertiv\.com/\d{8}',
        'custom_local_name':'ContingentConsiderationLiabilityCurrent',
        'corroborating_qname':'us-gaap:DerivativeLiabilitiesCurrent',
        'risk_axis':'us-gaap:DerivativeInstrumentRiskAxis',
        'risk_member_local_name':'ContingentConsiderationMember',
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'component_qname':QNAME,
        'treatment':'issuer current total controls and is corroborated by the derivative-liability table; overlapping acquisition slices are diagnostic, not additive',
    },
    'REGN': {
        'schema_version':SCHEMA,'version':WG2_VERSION,'ticker':'REGN','cik':'0000872589',
        'mode':'duration_accrual_requires_carrying_scope','issuer_namespace_pattern':r'https?://(?:www\.)?regeneron\.com/\d{8}',
        'custom_local_name':'AcquisitionsContingentConsiderationAccruedButNotYetPaid',
        'separate_cash_local_name':'PaymentsToAcquireIntangibleAssets1',
        'treatment':'duration supplemental noncash disclosure is not silently converted to an instant liability; cash and carrying-liability overlap must be proved first',
    },
})


WG15_CLAIM_RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    'ABT': {
        'schema_version':SCHEMA,'version':WG15_VERSION,'ticker':'ABT','cik':'0000001800',
        'mode':'aggregate_level3_duplicate','qname':QNAME,
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'pro_forma_revenue_qname':'us-gaap:BusinessAcquisitionsProFormaRevenue',
        'acquisition_axis':'us-gaap:BusinessAcquisitionAxis',
        'acquisition_member_local_name':'ExactSciencesCorporationMember',
        'treatment':'matching current aggregate and Level-3 contingent-consideration presentations are one carrying liability; NCI, legal accruals, transaction prices and cash payments remain separate',
    },
    'BAX': {
        'schema_version':SCHEMA,'version':WG15_VERSION,'ticker':'BAX','cik':'0000010456',
        'mode':'separation_claim_stack','issuer_namespace_pattern':r'https?://(?:www\.)?baxter\.com/\d{8}',
        'contingent_qname':QNAME,
        'indemnification_local_name':'BusinessSeparationIndemnificationLiability',
        'indemnification_alias_local_name':'IndemnificationAgreementLiabilityNet',
        'disposal_local_name':'DisposalGroupIncludingDiscontinuedOperationsContingentLiability',
        'disposal_member':'us-gaap:IndemnificationGuaranteeMember',
        'aggregate_maximum_local_name':'DisposalGroupIncludingDiscontinuedOperationContingentLiabilityHeld',
        'retained_guarantee_local_name':'BusinessGuaranteesRetainedValue',
        'litigation_reserve_qname':'us-gaap:LitigationReserve',
        'environmental_accrual_qname':'us-gaap:AccrualForEnvironmentalLossContingencies',
        'environmental_axes':(
            'us-gaap:EnvironmentalRemediationContingencyAxis',
            'us-gaap:EnvironmentalRemediationSiteAxis',
        ),
        'environmental_members':('EnviromentalCleanUpMember','SuperfundSitesMember'),
        'cash_paid_qname':'us-gaap:PaymentForContingentConsiderationLiabilityFinancingActivities',
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'treatment':'sum the three distinct current carrying claims once; keep aggregate historical maxima, retained guarantees, operating legal/environmental reserves and paid cash separate',
    },
})


def wg2_claim_policy(ticker: str) -> dict[str, Any]:
    rule = WG2_CLAIM_RULES.get(ticker)
    if rule is None:
        raise ValueError(f'no WG2 acquisition claim policy for {ticker!r}')
    return deepcopy(dict(rule))


def mixed_claim_policy(ticker: str) -> dict[str, Any]:
    rule = WG15_CLAIM_RULES.get(ticker)
    if rule is None:
        raise ValueError(f'no WG15 mixed acquisition claim policy for {ticker!r}')
    return deepcopy(dict(rule))


def _policy_equal(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    import json
    return json.dumps(actual,sort_keys=True,separators=(',',':')) == json.dumps(expected,sort_keys=True,separators=(',',':'))


def _wg2_context(policy, structural, controlling, cik, cutoff):
    ticker = policy.get('ticker')
    expected = WG2_CLAIM_RULES.get(ticker) or WG15_CLAIM_RULES.get(ticker)
    if expected is None or not _policy_equal(policy, expected) or str(cik).zfill(10) != expected['cik']:
        raise RuntimeError('acquisition claim policy identity/version mismatch')
    accession, period = controlling['accessionNumber'], controlling['reportDate']
    filed = controlling['filingDate']
    if (structural.get('source_accession') != accession
        or (structural.get('report_date') or structural.get('period_end')) != period
        or not period <= filed <= cutoff):
        raise ValueError('WG2 acquisition claim source period/accession/cutoff mismatch')
    date.fromisoformat(period); date.fromisoformat(filed); date.fromisoformat(cutoff)
    facts = structural.get('facts')
    if not isinstance(facts,list):
        raise ValueError('WG2 acquisition claim structural facts are missing')
    return expected,accession,period,facts


def _valid_row(row, *, policy, accession, period, instant=True, issuer=False):
    if (row.get('source_accession') != accession or row.get('unit') != 'USD'
        or str(row.get('entity_identifier','')).zfill(10) != policy['cik']
        or row.get('entity_scheme') != 'http://www.sec.gov/CIK'
        or row.get('period_end') != period
        or (instant and row.get('period_start') is not None)
        or (not instant and not isinstance(row.get('period_start'),str))
        or isinstance(row.get('value'),bool) or not isinstance(row.get('value'),(int,float))
        or not isfinite(row['value']) or row['value'] < 0):
        raise ValueError('WG2 acquisition claim identity, period, unit or amount invalid')
    namespace = str(row.get('namespace',''))
    if issuer:
        if not re.fullmatch(str(policy['issuer_namespace_pattern']),namespace):
            raise ValueError('WG2 issuer claim namespace mismatch')
    elif not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',namespace):
        raise ValueError('WG2 GAAP claim namespace mismatch')


def _dims(row) -> dict[str,str]:
    raw=row.get('dimensions') or []
    if not isinstance(raw,(list,tuple)) or any(not isinstance(pair,(list,tuple)) or len(pair)!=2 for pair in raw):
        raise ValueError('WG2 claim dimensions are malformed')
    return dict(raw)


def _select_wg2_claim(policy, structural, controlling, cik, cutoff):
    policy,accession,period,facts = _wg2_context(policy,structural,controlling,cik,cutoff)
    mode,ticker = policy['mode'],policy['ticker']
    source_rows=[];excluded_rows=[];review=[];claim=None;formula='';components={};extra={}
    if mode == 'direct_total':
        rows=[row for row in facts if row.get('qname')==policy['qname'] and row.get('period_end')==period
              and row.get('period_start') is None and not row.get('dimensions')]
        if not rows: raise ValueError('current acquisition liability missing; absence is not zero')
        for row in rows: _valid_row(row,policy=policy,accession=accession,period=period)
        values={float(row['value']) for row in rows}
        if len(values)!=1: raise ValueError('current acquisition liability conflicts')
        claim=values.pop();source_rows=rows
        corroboration=[row for row in facts if row.get('qname') in policy['allowed_current_qnames']
                       and row.get('period_end')==period and row.get('period_start') is None]
        for row in corroboration: _valid_row(row,policy=policy,accession=accession,period=period)
        if any(float(row['value']) not in {0.,claim} for row in corroboration):
            raise ValueError('current acquisition liability detail does not reconcile to total')
        source_rows += [row for row in corroboration if row not in source_rows]
        excluded_rows=[row for row in facts if row.get('qname')=='us-gaap:BusinessCombinationPriceOfAcquisitionExpected'
                       and row.get('period_end','')>period]
        formula='current reported contingent-consideration carrying liability, deducted once'
    elif mode == 'level3_components':
        for qname in policy['component_qnames']:
            rows=[row for row in facts if row.get('qname')==qname and row.get('period_end')==period
                  and row.get('period_start') is None and _dims(row)=={policy['level_axis']:policy['level_member']}]
            if not rows: raise ValueError(f'current Level-3 acquisition liability component missing: {qname}')
            for row in rows: _valid_row(row,policy=policy,accession=accession,period=period)
            values={float(row['value']) for row in rows}
            if len(values)!=1: raise ValueError('current Level-3 acquisition liability component conflicts')
            source_rows.append(rows[0])
        current_carrying=sum(float(row['value']) for row in source_rows)
        excluded_rows=[row for row in facts if row.get('qname') in {
            'us-gaap:BusinessCombinationConsiderationTransferred1',
            'us-gaap:BusinessCombinationConsiderationTransferredLiabilitiesIncurred',
            'us-gaap:BusinessCombinationContingentConsiderationArrangementsRangeOfOutcomesValueHigh',
            'us-gaap:BusinessCombinationPriceOfAcquisitionExpected'}]
        if policy.get('requires_post_period_cash_paid_source'):
            review.append('post_period_cash_paid_evidence_not_machine_bound')
        claim=None if review else current_carrying
        formula='current + noncurrent Level-3 carrying liability; transaction prices, maxima and post-period cash are separate'
    elif mode == 'duplicate_presentations':
        rows=[row for row in facts if row.get('qname')==policy['qname'] and row.get('period_end')==period and row.get('period_start') is None]
        for row in rows: _valid_row(row,policy=policy,accession=accession,period=period)
        recurring=[row for row in rows if _dims(row).get(policy['location_axis'])==policy['location_member']
                   and _dims(row).get(policy['frequency_axis'])==policy['frequency_member']]
        level3=[row for row in recurring if _dims(row).get(policy['level_axis'])==policy['level_member']]
        aggregates=[row for row in recurring if policy['level_axis'] not in _dims(row)]
        if not level3 or not aggregates: raise ValueError('duplicate claim presentations are incomplete')
        nonzero={float(row['value']) for row in recurring if float(row['value'])!=0.}
        if len(nonzero)!=1: raise ValueError('duplicate claim presentations conflict')
        claim=nonzero.pop();source_rows=recurring
        excluded_rows=[row for row in facts if row.get('qname') in {
            'us-gaap:BusinessCombinationContingentConsiderationArrangementsRangeOfOutcomesValueHigh',QNAME}
            and row.get('period_end')!=period]
        formula='matching current aggregate and Level-3 presentations, counted once'
    elif mode == 'aggregate_level3_duplicate':
        rows=[row for row in facts if row.get('qname')==policy['qname'] and row.get('period_end')==period
              and row.get('period_start') is None]
        for row in rows:_valid_row(row,policy=policy,accession=accession,period=period)
        allowed_levels={'us-gaap:FairValueInputsLevel1Member','us-gaap:FairValueInputsLevel2Member',policy['level_member']}
        if any(_dims(row) and (_dims(row).keys()!={policy['level_axis']}
                              or _dims(row).get(policy['level_axis']) not in allowed_levels) for row in rows):
            raise ValueError('unexpected current acquisition claim dimension')
        aggregate=[row for row in rows if not _dims(row)]
        level3=[row for row in rows if _dims(row)=={policy['level_axis']:policy['level_member']}]
        other_levels=[row for row in rows if _dims(row).get(policy['level_axis']) in allowed_levels-{policy['level_member']}]
        if not aggregate or not level3:
            raise ValueError('aggregate and Level-3 acquisition claim presentations are incomplete')
        amounts={float(row['value']) for row in (*aggregate,*level3)}
        if len(amounts)!=1 or any(float(row['value'])!=0 for row in other_levels):
            raise ValueError('aggregate and Level-3 acquisition claim presentations conflict')
        claim=amounts.pop();source_rows=[*aggregate,*level3,*other_levels]
        pro_forma=[row for row in facts if row.get('qname')==policy['pro_forma_revenue_qname']
                   and row.get('period_end')==period and isinstance(row.get('period_start'),str)
                   and _dims(row).keys()=={policy['acquisition_axis']}
                   and str(_dims(row)[policy['acquisition_axis']]).rsplit(':',1)[-1]==policy['acquisition_member_local_name']]
        for row in pro_forma:_valid_row(row,policy=policy,accession=accession,period=period,instant=False)
        if pro_forma:
            earliest=min(row['period_start'] for row in pro_forma)
            pro_forma=[row for row in pro_forma if row['period_start']==earliest]
        if not pro_forma or len({float(row['value']) for row in pro_forma})!=1:
            raise ValueError('current acquisition pro-forma revenue is missing or conflicting')
        start=date.fromisoformat(pro_forma[0]['period_start']);end=date.fromisoformat(pro_forma[0]['period_end'])
        months=(end.year-start.year)*12+end.month-start.month+1
        if start.day!=1 or (end+timedelta(days=1)).day!=1 or not 1<=months<=12:
            raise ValueError('acquisition pro-forma revenue period is not an exact monthly interval')
        annualization=12/months
        source_rows.extend(pro_forma)
        extra={'annualized_pro_forma_revenue':float(pro_forma[0]['value'])*annualization,
               'pro_forma_revenue':float(pro_forma[0]['value']),'pro_forma_months':months,
               'pro_forma_annualization_factor':annualization}
        formula='matching current aggregate and Level-3 carrying-liability presentations, counted once'
    elif mode == 'separation_claim_stack':
        def exact_duplicate(*, qname=None, local_name=None, issuer=False):
            rows=[row for row in facts if (qname is None or row.get('qname')==qname)
                  and (local_name is None or row.get('local_name')==local_name)
                  and row.get('period_end')==period and row.get('period_start') is None]
            for row in rows:_valid_row(row,policy=policy,accession=accession,period=period,issuer=issuer)
            allowed_levels={'us-gaap:FairValueInputsLevel1Member','us-gaap:FairValueInputsLevel2Member',policy['level_member']}
            if any(_dims(row) and (_dims(row).keys()!={policy['level_axis']}
                                  or _dims(row).get(policy['level_axis']) not in allowed_levels) for row in rows):
                raise ValueError('unexpected separation claim dimension')
            aggregate=[row for row in rows if not _dims(row)]
            level3=[row for row in rows if _dims(row)=={policy['level_axis']:policy['level_member']}]
            other=[row for row in rows if policy['level_axis'] in _dims(row)
                   and _dims(row).get(policy['level_axis'])!=policy['level_member']]
            if not aggregate or not level3:
                raise ValueError('separation claim aggregate/Level-3 presentations are incomplete')
            amounts={float(row['value']) for row in (*aggregate,*level3)}
            if len(amounts)!=1 or any(float(row['value'])!=0 for row in other):
                raise ValueError('separation claim aggregate/Level-3 presentations conflict')
            return amounts.pop(),[*aggregate,*level3,*other]
        contingent,contingent_rows=exact_duplicate(qname=policy['contingent_qname'])
        indemnification,indemnification_rows=exact_duplicate(
            local_name=policy['indemnification_local_name'],issuer=True)
        disposal_rows=[row for row in facts if row.get('local_name')==policy['disposal_local_name']
                       and row.get('period_end')==period and row.get('period_start') is None
                       and _dims(row)=={'us-gaap:LossContingenciesByNatureOfContingencyAxis':policy['disposal_member']}]
        for row in disposal_rows:_valid_row(row,policy=policy,accession=accession,period=period,issuer=True)
        if not disposal_rows or len({float(row['value']) for row in disposal_rows})!=1:
            raise ValueError('current disposal-group carrying claim is missing or conflicting')
        disposal=float(disposal_rows[0]['value'])
        alias_rows=[row for row in facts if row.get('local_name')==policy['indemnification_alias_local_name']
                    and row.get('period_end')==period and row.get('period_start') is None
                    and _dims(row)=={'us-gaap:LossContingenciesByNatureOfContingencyAxis':policy['disposal_member']}]
        for row in alias_rows:_valid_row(row,policy=policy,accession=accession,period=period,issuer=True)
        if not alias_rows or {float(row['value']) for row in alias_rows}!={indemnification}:
            raise ValueError('separation indemnification alias does not reconcile')
        diagnostic_specs=(
            ('aggregate_maximum_local_name',True,True,'indemnification'),
            ('retained_guarantee_local_name',True,True,'indemnification'),
            ('litigation_reserve_qname',False,True,'undimensioned'),
            ('environmental_accrual_qname',False,True,'environmental'),
            ('cash_paid_qname',False,False,'undimensioned'),
        )
        diagnostics=[]
        diagnostic_values={}
        for key,issuer,instant,dimension_scope in diagnostic_specs:
            target=policy[key]
            rows=[row for row in facts if (row.get('local_name')==target if issuer else row.get('qname')==target)
                  and row.get('period_end')==period and ((row.get('period_start') is None)==instant)
                  and (not _dims(row) if dimension_scope=='undimensioned' else
                       _dims(row)=={'us-gaap:LossContingenciesByNatureOfContingencyAxis':policy['disposal_member']}
                       if dimension_scope=='indemnification' else
                       tuple(_dims(row).keys())==policy['environmental_axes']
                       and tuple(str(value).rsplit(':',1)[-1] for value in _dims(row).values())==policy['environmental_members'])]
            for row in rows:_valid_row(row,policy=policy,accession=accession,period=period,instant=instant,issuer=issuer)
            if not rows:
                raise ValueError(f'required non-additive claim diagnostic is missing: {target}')
            amounts={float(row['value']) for row in rows}
            if len(amounts)!=1:
                raise ValueError(f'non-additive claim diagnostic conflicts: {target}')
            diagnostic_values[key]=amounts.pop()
            diagnostics.extend(rows)
        if diagnostic_values['environmental_accrual_qname']>diagnostic_values['litigation_reserve_qname']:
            raise ValueError('environmental reserve exceeds its total legal/environmental reserve')
        claim=contingent+indemnification+disposal
        components={
            'contingent_consideration':contingent,
            'separation_indemnification':indemnification,
            'disposal_group_claim':disposal,
        }
        source_rows=[*contingent_rows,*indemnification_rows,*disposal_rows]
        excluded_rows=[*alias_rows,*diagnostics]
        formula='current contingent consideration + separation indemnification + disposal-group carrying liability; duplicate views, aggregate maximum, retained guarantee, operating reserves and paid cash excluded'
    elif mode == 'custom_total_corroborated':
        custom=[row for row in facts if row.get('local_name')==policy['custom_local_name'] and row.get('period_end')==period
                and row.get('period_start') is None and not row.get('dimensions')]
        for row in custom: _valid_row(row,policy=policy,accession=accession,period=period,issuer=True)
        if not custom or len({float(row['value']) for row in custom})!=1:
            raise ValueError('issuer current acquisition-liability total missing or conflicting')
        claim=float(custom[0]['value'])
        corroborating=[row for row in facts if row.get('qname')==policy['corroborating_qname']
                       and row.get('period_end')==period and row.get('period_start') is None
                       and _dims(row).get(policy['risk_axis'],'').rsplit(':',1)[-1]==policy['risk_member_local_name']]
        for row in corroborating: _valid_row(row,policy=policy,accession=accession,period=period)
        aggregate=[row for row in corroborating if policy['level_axis'] not in _dims(row)]
        level3=[row for row in corroborating if _dims(row).get(policy['level_axis'])==policy['level_member']]
        zero_levels={'us-gaap:FairValueInputsLevel1Member','us-gaap:FairValueInputsLevel2Member'}
        invalid=[row for row in corroborating if float(row['value']) not in {0.,claim}
                 or (float(row['value'])==0. and _dims(row).get(policy['level_axis']) not in zero_levels)]
        if (not aggregate or not level3 or invalid
            or {float(row['value']) for row in (*aggregate,*level3)}!={claim}):
            raise ValueError('issuer current total lacks matching derivative-liability corroboration')
        components=[row for row in facts if row.get('qname')==policy['component_qname']
                    and row.get('period_end')==period and row.get('period_start') is None]
        for row in components: _valid_row(row,policy=policy,accession=accession,period=period)
        if any(float(row['value'])>claim for row in components):
            raise ValueError('acquisition component exceeds current total')
        source_rows=[custom[0],*corroborating];excluded_rows=components
        formula='issuer current total corroborated by the contingent derivative-liability total; narrower acquisition slices are not added'
    elif mode == 'duration_accrual_requires_carrying_scope':
        rows=[row for row in facts if row.get('local_name')==policy['custom_local_name'] and row.get('period_end')==period]
        for row in rows: _valid_row(row,policy=policy,accession=accession,period=period,instant=False,issuer=True)
        if not rows or len({float(row['value']) for row in rows})!=1:
            raise ValueError('duration acquisition accrual missing or conflicting')
        cash=[row for row in facts if row.get('local_name')==policy['separate_cash_local_name'] and row.get('period_end')==period]
        for row in cash: _valid_row(row,policy=policy,accession=accession,period=period,instant=False,issuer=True)
        if not cash: raise ValueError('separate acquisition cash payment evidence is missing')
        source_rows=rows;excluded_rows=cash
        review.append('duration_accrual_has_no_reconciled_period_end_carrying_liability')
        formula='duration supplemental noncash accrual retained diagnostically; no instant liability inferred'
    else:
        raise RuntimeError('unsupported WG2 acquisition claim mode')
    return {'status':'review_required' if review else 'source_bound','claim_adjustment':claim,**extra,
            'current_carrying_liability':sum(float(row['value']) for row in source_rows[:2]) if mode=='level3_components' else claim,
            'review_reasons':review,'policy':dict(policy),'source_rows':source_rows,'excluded_rows':excluded_rows,
            'period_end':period,'formula':formula,'components':components,
            'cash_flow_overlap_limitation':'Acquisition cash and noncash accrual disclosures remain separate from the current carrying claim and are never added without an explicit overlap rule.'}


def broadridge_claim_policy():
    return {'schema_version': SCHEMA, 'ticker': 'BR', 'cik': '0001383312',
            'concept': QNAME, 'treatment': 'reported acquisition liability deducted once outside operating cash conversion'}


def idexx_claim_policy():
    return {'schema_version':SCHEMA,'ticker':'IDXX','cik':'0000874716',
            'concept':'us-gaap:AssetAcquisitionContingentConsiderationLiability',
            'treatment':'current named acquisition liability only; prior estimated consideration is not a contractual ceiling'}


def _idexx_claim(policy, structural, controlling, cik, cutoff):
    if policy != idexx_claim_policy() or str(cik).zfill(10) != policy['cik']:
        raise RuntimeError('IDXX acquisition claim policy identity/version mismatch')
    accession, period = controlling['accessionNumber'], controlling['reportDate']
    if structural.get('source_accession') != accession or (structural.get('report_date') or structural.get('period_end')) != period or not period <= controlling['filingDate'] <= cutoff:
        raise ValueError('IDXX acquisition claim source period/accession/cutoff mismatch')
    namespaces = {str(row.get('namespace','')) for row in structural.get('facts', [])}
    members = {'ns_'+hashlib.sha1(uri.encode()).hexdigest()[:10]+':PrivatelyOwnedReferenceLaboratoryMember'
               for uri in namespaces if re.fullmatch(r'https?://www\.idexx\.com/\d{8}',uri)}
    def scope(row):
        dims = row.get('dimensions') or []
        return isinstance(dims,(list,tuple)) and len(dims) == 2 and all(isinstance(pair,(list,tuple)) and len(pair)==2 and all(isinstance(part,str) for part in pair) for pair in dims) and any(dict(dims) == {'us-gaap:AssetAcquisitionAxis':member,
            'us-gaap:FiniteLivedIntangibleAssetsByMajorClassAxis':'us-gaap:CustomerRelationshipsMember'} for member in members)
    rows = [row for row in structural.get('facts', []) if row.get('qname') == policy['concept']
            and row.get('period_end') == period and row.get('period_start') is None and scope(row)]
    if not rows:
        raise ValueError('current IDXX acquisition liability or settlement proof missing; a prior estimated payment is not a current balance or contractual maximum')
    for row in rows:
        if (row.get('source_accession') != accession or row.get('unit') != 'USD'
            or str(row.get('entity_identifier','')).zfill(10) != policy['cik'] or row.get('entity_scheme') != 'http://www.sec.gov/CIK'
            or not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',str(row.get('namespace','')))
            or isinstance(row.get('value'),bool) or not isinstance(row.get('value'),(int,float)) or not isfinite(row['value']) or row['value'] < 0):
            raise ValueError('IDXX acquisition claim identity/unit/amount invalid')
    values = {float(row['value']) for row in rows}
    if len(values) != 1:
        raise ValueError('current IDXX acquisition liability conflicts')
    for row in structural.get('facts', []):
        if (row.get('period_end') == period and row.get('period_start') is None and row.get('unit') == 'USD'
            and 'ContingentConsideration' in str(row.get('qname','')) and row.get('value') not in (0,0.,None)
            and not (row.get('qname') == policy['concept'] and scope(row))):
            raise ValueError('additional IDXX acquisition claim requires a scope rule')
    return {'status':'source_bound','claim_adjustment':values.pop(),'review_reasons':[],
            'policy':policy,'source_rows':rows,'period_end':period,
            'formula':'current named acquisition contingent liability, deducted once'}


def select_acquisition_claim(policy, structural, controlling, cik, cutoff):
    if policy.get('ticker') in WG2_CLAIM_RULES or policy.get('ticker') in WG15_CLAIM_RULES:
        return _select_wg2_claim(policy,structural,controlling,cik,cutoff)
    if policy.get('ticker') == 'IDXX':
        return _idexx_claim(policy,structural,controlling,cik,cutoff)
    if policy != broadridge_claim_policy() or str(cik).zfill(10) != policy['cik']:
        raise RuntimeError('acquisition claim rule identity/version mismatch')
    accession, period = controlling['accessionNumber'], controlling['reportDate']
    if structural.get('source_accession') != accession or (structural.get('report_date') or structural.get('period_end')) != period:
        raise ValueError('acquisition claim packet period/accession mismatch')
    if not period <= controlling['filingDate'] <= cutoff:
        raise ValueError('acquisition claim evidence is outside cutoff')
    date.fromisoformat(period); date.fromisoformat(cutoff)
    candidates = [row for row in structural.get('facts', []) if row.get('qname') == QNAME
                  and row.get('period_end') == period and row.get('period_start') is None and not row.get('dimensions')]
    if not candidates:
        raise ValueError('current acquisition liability missing; absence is not zero')
    components = [row for row in structural.get('facts', []) if row.get('qname') in COMPONENTS
                  and row.get('period_end') == period and row.get('period_start') is None and not row.get('dimensions')]
    for row in candidates + components:
        if (row.get('source_accession') != accession or row.get('unit') != 'USD'
            or str(row.get('entity_identifier', '')).zfill(10) != policy['cik']
            or row.get('entity_scheme') != 'http://www.sec.gov/CIK'
            or not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}', str(row.get('namespace', '')))
            or isinstance(row.get('value'), bool) or not isinstance(row.get('value'), (int, float))
            or not isfinite(row['value']) or row['value'] < 0):
            raise ValueError('acquisition liability identity, unit, namespace or amount invalid')
    amounts = {float(row['value']) for row in candidates}
    if len(amounts) != 1:
        raise ValueError('current acquisition liability conflicts')
    amount = next(iter(amounts))
    if components:
        component_values = []
        for qname in COMPONENTS:
            values = {float(row['value']) for row in components if row['qname'] == qname}
            if len(values) > 1:
                raise ValueError('acquisition liability components conflict')
            component_values.extend(values)
        if sum(component_values) != amount:
            raise ValueError('reported acquisition liability components do not reconcile to total')
    # A newly introduced liability structure needs a new reconciled rule.
    for row in structural.get('facts', []):
        if (row.get('source_accession') == accession and row.get('period_end') == period
            and row.get('period_start') is None and not row.get('dimensions')
            and 'ContingentConsideration' in str(row.get('qname', ''))
            and row.get('qname') not in (QNAME, *COMPONENTS) and row.get('unit') == 'USD'
            and row.get('value') not in (0, 0.0, None)):
            raise ValueError('additional contingent consideration structure requires reconciliation')
    return {'status': 'source_bound', 'claim_adjustment': amount, 'review_reasons': [],
            'policy': policy, 'source_rows': candidates, 'component_reconciliation': components, 'period_end': period,
            'formula': 'reported acquisition liability; no capitalization or recurring cash deduction',
            'cash_flow_overlap_limitation': 'Historical operating cash is not adjusted without separately evidenced acquisition-payment classification.'}
