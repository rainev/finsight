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
WG16_VERSION = 'FINSIGHT-ACQUISITION-CLAIM-WG16-1'
WG17_VERSION = 'FINSIGHT-ACQUISITION-CLAIM-WG17-1'
WG18_VERSION = 'FINSIGHT-ACQUISITION-CLAIM-WG18-1'
WG19_VERSION = 'FINSIGHT-ACQUISITION-CLAIM-WG19-1'
WG20_VERSION = 'FINSIGHT-ACQUISITION-CLAIM-WG20-1'
WG22_VERSION = 'FINSIGHT-ACQUISITION-CLAIM-WG22-1'


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


WG16_CLAIM_RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    'BSX': {
        'schema_version':SCHEMA,'version':WG16_VERSION,'ticker':'BSX','cik':'0000885725',
        'mode':'aggregate_level3_duplicate','qname':QNAME,
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'component_axis':'us-gaap:ContingentConsiderationByTypeAxis',
        'component_members':('RevenueBasedPaymentsMember','RDRegulatoryandCommercializationbasedMilestoneMember'),
        'valuation_axis':'us-gaap:ValuationTechniqueAxis',
        'valuation_member':'us-gaap:ValuationTechniqueDiscountedCashFlowMember',
        'maximum_qname':'us-gaap:BusinessCombinationContingentConsiderationArrangementsRangeOfOutcomesValueHigh',
        'cash_paid_local_names':('PaymentOfContingentConsideration','PaymentForContingentConsiderationLiabilityFinancingActivities'),
        'issuer_namespace_pattern':r'https?://(?:www\.)?bostonscientific\.com/\d{8}',
        'treatment':'matching current aggregate and Level-3 carrying presentations count once; typed components reconcile to the total while maxima and paid cash remain non-additive',
    },
    'DGX': {
        'schema_version':SCHEMA,'version':WG16_VERSION,'ticker':'DGX','cik':'0001022079',
        'mode':'aggregate_level3_duplicate','qname':QNAME,
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'measurement_change_qname':'us-gaap:BusinessCombinationContingentConsiderationArrangementsChangeInAmountOfContingentConsiderationLiability1',
        'acquisition_cash_qname':'us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired',
        'treatment':'matching current aggregate and Level-3 contingent-consideration presentations are one carrying liability; measurement-input changes and paid cash remain separate',
    },
    'EW': {
        'schema_version':SCHEMA,'version':WG16_VERSION,'ticker':'EW','cik':'0001099800',
        'mode':'current_liability_with_maximum','qname':'us-gaap:BusinessCombinationContingentConsiderationLiabilityCurrent',
        'aggregate_qname':'us-gaap:FairValueLiabilitiesMeasuredOnRecurringBasisObligations',
        'rollforward_qname':'us-gaap:FairValueMeasurementWithUnobservableInputsReconciliationsRecurringBasisLiabilityValue',
        'rollforward_axis':'us-gaap:FairValueByLiabilityClassAxis',
        'rollforward_member_local_name':'ContingentConsiderationLiabilityMember',
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'maximum_qname':'us-gaap:BusinessCombinationContingentConsiderationArrangementsRangeOfOutcomesValueHigh',
        'maximum_member_local_name':'AutusValveTechnologiesInc.Member',
        'acquisition_axis':'us-gaap:BusinessAcquisitionAxis',
        'separate_equity_qname':'us-gaap:BusinessCombinationConsiderationTransferredEquityInterestsIssuedAndIssuable',
        'separate_equity_member_local_name':'MedicalDeviceCompanyMember',
        'treatment':'deduct the current aggregate carrying liability once, with the current portion retained as a subset; the acquisition maximum and another acquisition equity consideration are diagnostics, never scenario liabilities',
    },
})


WG17_CLAIM_RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    'CRL': {
        'schema_version':SCHEMA,'version':WG17_VERSION,'ticker':'CRL','cik':'0001100682',
        'mode':'current_noncurrent_with_deferred_review',
        'component_qnames':(QNAME+'Current',QNAME+'Noncurrent'),
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'rollforward_qname':'us-gaap:FairValueMeasurementWithUnobservableInputsReconciliationsRecurringBasisLiabilityValue',
        'rollforward_axis':'us-gaap:FairValueByLiabilityClassAxis',
        'rollforward_member_local_name':'ContingentConsiderationMember',
        'fair_value_qname':'us-gaap:LiabilitiesFairValueDisclosure',
        'deferred_qname':QNAME,'acquisition_axis':'us-gaap:BusinessAcquisitionAxis',
        'deferred_member_local_name':'K.F.CambodiaMember',
        'paid_cash_qname':'us-gaap:PaymentForContingentConsiderationLiabilityFinancingActivities',
        'acquisition_cash_qname':'us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired',
        'treatment':'reconcile current and noncurrent Level-3 contingent consideration once; keep K.F. Cambodia deferred consideration separate until its operating-cash overlap is resolved, and never add paid or acquisition cash',
    },
    'DVA': {
        'schema_version':SCHEMA,'version':WG17_VERSION,'ticker':'DVA','cik':'0000927066',
        'mode':'custom_carrying_alias','issuer_namespace_pattern':r'https?://(?:www\.)?davita\.com/\d{8}',
        'carrying_local_name':'AcquisitionObligationsAndOtherNotesPayable',
        'fair_value_local_name':'AcquisitionObligationsAndOtherNotesPayableFairValue',
        'debt_axis':'us-gaap:DebtInstrumentAxis','debt_member':'us-gaap:NotesPayableOtherPayablesMember',
        'nci_sensitivity_local_name':'PotentialIncreaseDecreaseInFairValueOfNoncontrollingInterestsDueToChangeInWeightedAverageEBITDAMultiple',
        'acquisition_cash_qname':'us-gaap:PaymentsToAcquireBusinessesGross',
        'subsequent_event_qname':'us-gaap:PaymentsToAcquireEquityMethodInvestments',
        'subsequent_event_axis':'us-gaap:SubsequentEventTypeAxis',
        'subsequent_event_member':'us-gaap:SubsequentEventMember',
        'investee_axis_local_name':'ScheduleOfEquityMethodInvestmentEquityMethodInvesteeNameAxis',
        'investee_member_local_name':'ElaraCaringMember',
        'requires_aggregate_debt_overlap_review':True,
        'requires_post_period_rollforward':True,
        'reject_unlisted_contingent_claims':True,
        'treatment':'retain the current acquisition obligation inside aggregate debt once; its fair-value alias corroborates rather than adds, while acquisition cash, NCI sensitivity and post-period investment cash remain separate review surfaces',
    },
})


WG18_CLAIM_RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    'GLW': {
        'schema_version':SCHEMA,'version':WG18_VERSION,'ticker':'GLW','cik':'0000024741',
        'mode':'single_carrying_component',
        'component_qname':QNAME+'Noncurrent',
        'nci_qname':'us-gaap:MinorityInterest',
        'excluded_operating_qnames':('us-gaap:AccrualForEnvironmentalLossContingencies',),
        'treatment':'deduct the current noncurrent contingent-consideration carrying liability once; ordinary NCI, environmental reserves, cash flows, warrants and post-period events remain separate',
    },
    'MDT': {
        'schema_version':SCHEMA,'version':WG18_VERSION,'ticker':'MDT','cik':'0001613103',
        'mode':'aggregate_with_reconciling_components',
        'qname':QNAME,
        'location_axis':'us-gaap:StatementOfFinancialPositionLocationBalanceAxis',
        'location_typed_domain':'us-gaap:QName.domain',
        'current_location_member':'us-gaap:OtherLiabilitiesCurrent',
        'noncurrent_location_member':'us-gaap:OtherLiabilitiesNoncurrent',
        'component_axis':'us-gaap:ContingentConsiderationByTypeAxis',
        'component_members':('RevenueMilestoneMember','ProductDevelopmentMilestoneMember'),
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'acquisition_cash_qname':'us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired',
        'measurement_change_qname':'us-gaap:BusinessCombinationContingentConsiderationArrangementsChangeInAmountOfContingentConsiderationLiability1',
        'nci_qname':'us-gaap:MinorityInterest',
        'treatment':'deduct the aggregate contingent-consideration carrying liability once; typed current/noncurrent locations and Level-3 milestone components must each reconcile, while acquisition cash, measurement changes and operating legal accruals remain separate',
    },
    'PFE': {
        'schema_version':SCHEMA,'version':WG18_VERSION,'ticker':'PFE','cik':'0000078003',
        'mode':'current_noncurrent_level3_duplicates',
        'component_qnames':(QNAME+'Current',QNAME+'Noncurrent'),
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'measurement_change_qname':'us-gaap:BusinessCombinationContingentConsiderationArrangementsChangeInAmountOfContingentConsiderationLiability1',
        'nci_qname':'us-gaap:MinorityInterest',
        'treatment':'sum current and noncurrent contingent-consideration carrying liabilities once; Level-3 rows corroborate rather than add, while remeasurement flows, acquisition cash, legal settlements and restructuring costs remain separate',
    },
})


WG19_CLAIM_RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    'HSIC': {
        'schema_version':SCHEMA,'version':WG19_VERSION,'ticker':'HSIC','cik':'0001000228',
        'mode':'recurring_hierarchy_duplicates','qname':QNAME,
        'frequency_axis':'us-gaap:FairValueByMeasurementFrequencyAxis',
        'frequency_member':'us-gaap:FairValueMeasurementsRecurringMember',
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'issuer_namespace_pattern':r'https?://(?:www\.)?henryschein\.com/\d{8}',
        'payment_local_name':'BusinessCombinationContingentConsiderationArrangementsDecreaseInContingentConsiderationDueToPayments',
        'measurement_change_local_name':'BusinessCombinationContingentConsiderationArrangementsChangeInFairValueOfContingentConsiderationInConnectionWithBusinessAcquisitions',
        'deferred_local_name':'BusinessCombinationConsiderationTransferredDeferred',
        'acquisition_cash_qname':'us-gaap:PaymentsToAcquireBusinessesGross',
        'acquisition_axis':'us-gaap:BusinessAcquisitionAxis',
        'treatment':'deduct the recurring contingent-consideration carrying total once; aggregate, recurring and Level-3 rows are duplicate views while payment and fair-value changes are flows',
    },
    'ON': {
        'schema_version':SCHEMA,'version':WG19_VERSION,'ticker':'ON','cik':'0001097864',
        'mode':'aggregate_current_noncurrent','qname':QNAME,
        'component_qnames':(QNAME+'Current',QNAME+'Noncurrent'),
        'acquisition_cash_qname':'us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired',
        'treatment':'deduct the current aggregate contingent-consideration carrying liability once after exact current/noncurrent reconciliation; acquisition cash and pending transaction terms remain separate',
    },
    'ZBH': {
        'schema_version':SCHEMA,'version':WG19_VERSION,'ticker':'ZBH','cik':'0001136869',
        'mode':'recurring_hierarchy_with_acquisition_diagnostics','qname':QNAME,
        'frequency_axis':'us-gaap:FairValueByMeasurementFrequencyAxis',
        'frequency_member':'us-gaap:FairValueMeasurementsRecurringMember',
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'acquisition_axis':'us-gaap:BusinessAcquisitionAxis',
        'maximum_qname':'us-gaap:BusinessCombinationContingentConsiderationArrangementsRangeOfOutcomesValueHigh',
        'paid_cash_qname':'us-gaap:PaymentForContingentConsiderationLiabilityFinancingActivities',
        'acquisition_cash_qname':'us-gaap:PaymentsToAcquireBusinessesGross',
        'treatment':'deduct the recurring aggregate contingent-consideration carrying liability once; Level-3, acquisition-member rows, maxima, paid cash and acquisition cash remain non-additive diagnostics',
    },
})


WG20_CLAIM_RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    'TEL': {
        'schema_version':SCHEMA,'version':WG20_VERSION,'ticker':'TEL','cik':'0001385157',
        'mode':'dimensioned_noncurrent_with_pending_event',
        'qname':QNAME+'Noncurrent','acquisition_axis':'us-gaap:BusinessAcquisitionAxis',
        'acquisition_member_local_name':'Fiscal2026AcquisitionsMember',
        'acquisition_cash_qname':'us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired',
        'pending_member_local_name':'AstrodyneTDIMember',
        'subsequent_event_axis':'us-gaap:SubsequentEventTypeAxis',
        'subsequent_event_member':'us-gaap:SubsequentEventMember',
        'scenario_axis_local_name':'StatementScenarioAxis','scenario_member_local_name':'ScenarioForecastMember',
        'acquisition_cost_local_name':'BusinessAcquisitionCostOfAcquiredEntityTransactionCostsAndBusinessCombinationIntegrationRelatedCosts',
        'issuer_namespace_pattern':r'https?://(?:www\.)?te\.com/\d{8}',
        'treatment':'deduct the current noncurrent contingent-consideration carrying liability once; historical acquisition cash, integration costs and the forecast pending Astrodyne payment remain separate',
    },
    'CRWD': {
        'schema_version':SCHEMA,'version':WG20_VERSION,'ticker':'CRWD','cik':'0001535527',
        'mode':'direct_total_with_acquisition_cash','qname':QNAME,
        'acquisition_cash_qname':'us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired',
        'treatment':'deduct the current contingent-consideration carrying liability once; acquisition cash and operating loss-contingency balances remain separate',
    },
})


WG22_CLAIM_RULES = MappingProxyType({
    'ETN': {
        'schema_version':SCHEMA,'version':WG22_VERSION,'ticker':'ETN','cik':'0001551182',
        'mode':'aggregate_level3_duplicate','qname':QNAME,
        'level_axis':'us-gaap:FairValueByFairValueHierarchyLevelAxis',
        'level_member':'us-gaap:FairValueInputsLevel3Member',
        'acquisition_axis':'us-gaap:BusinessAcquisitionAxis',
        'acquisition_alias_member_local_names':('ResilientPowerSystemsInc.Member',),
        'reject_unlisted_contingent_claims':True,
        'acquisition_cash_qname':'us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired',
        'treatment':'current ordinary NCI is separate from the recurring acquisition carrying total; Level-3 and named acquisition views corroborate once, while acquisition cash and employment-contingent incentives stay operating',
    },
})


def ordinary_nci_mapping_acquisition_policy(ticker: str) -> dict[str, Any]:
    rule=WG22_CLAIM_RULES.get(ticker)
    if rule is None:raise ValueError(f'no ordinary-NCI mapping acquisition policy for {ticker!r}')
    return deepcopy(dict(rule))


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


def overlapping_claim_policy(ticker: str) -> dict[str, Any]:
    rule = WG16_CLAIM_RULES.get(ticker)
    if rule is None:
        raise ValueError(f'no WG16 overlapping acquisition claim policy for {ticker!r}')
    return deepcopy(dict(rule))


def nci_contingent_claim_policy(ticker: str) -> dict[str, Any]:
    rule = WG17_CLAIM_RULES.get(ticker)
    if rule is None:
        raise ValueError(f'no WG17 NCI/contingent claim policy for {ticker!r}')
    return deepcopy(dict(rule))


def ordinary_nci_acquisition_claim_policy(ticker: str) -> dict[str, Any]:
    rule = WG18_CLAIM_RULES.get(ticker)
    if rule is None:
        raise ValueError(f'no WG18 ordinary-NCI/acquisition claim policy for {ticker!r}')
    return deepcopy(dict(rule))


def mixed_ordinary_nci_claim_policy(ticker: str) -> dict[str, Any]:
    rule = WG19_CLAIM_RULES.get(ticker)
    if rule is None:
        raise ValueError(f'no WG19 mixed ordinary-NCI claim policy for {ticker!r}')
    return deepcopy(dict(rule))


def nci_acquisition_special_claim_policy(ticker: str) -> dict[str, Any]:
    rule = WG20_CLAIM_RULES.get(ticker)
    if rule is None:
        raise ValueError(f'no WG20 NCI/acquisition special-situation policy for {ticker!r}')
    return deepcopy(dict(rule))


def _policy_equal(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    import json
    return json.dumps(actual,sort_keys=True,separators=(',',':')) == json.dumps(expected,sort_keys=True,separators=(',',':'))


def _wg2_context(policy, structural, controlling, cik, cutoff):
    ticker = policy.get('ticker')
    expected = (WG2_CLAIM_RULES.get(ticker) or WG15_CLAIM_RULES.get(ticker)
                or WG16_CLAIM_RULES.get(ticker) or WG17_CLAIM_RULES.get(ticker)
                or WG18_CLAIM_RULES.get(ticker) or WG19_CLAIM_RULES.get(ticker)
                or WG20_CLAIM_RULES.get(ticker) or WG22_CLAIM_RULES.get(ticker))
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


def _valid_row(row, *, policy, accession, period, instant=True, issuer=False, allow_signed=False):
    if (row.get('source_accession') != accession or row.get('unit') != 'USD'
        or str(row.get('entity_identifier','')).zfill(10) != policy['cik']
        or row.get('entity_scheme') != 'http://www.sec.gov/CIK'
        or row.get('period_end') != period
        or (instant and row.get('period_start') is not None)
        or (not instant and not isinstance(row.get('period_start'),str))
        or isinstance(row.get('value'),bool) or not isinstance(row.get('value'),(int,float))
        or not isfinite(row['value']) or (row['value'] < 0 and not allow_signed)):
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
        def allowed_dimensions(row):
            dimensions=_dims(row)
            if not dimensions:return True
            if dimensions.keys()=={policy['level_axis']} and dimensions.get(policy['level_axis']) in allowed_levels:
                return True
            if (policy.get('acquisition_alias_member_local_names')
                and dimensions.keys()=={policy['acquisition_axis']}
                and str(dimensions[policy['acquisition_axis']]).rsplit(':',1)[-1]
                    in policy['acquisition_alias_member_local_names']):
                return True
            return bool(policy.get('component_members')
                and set(dimensions)=={policy['component_axis'],policy['valuation_axis']}
                and str(dimensions[policy['component_axis']]).rsplit(':',1)[-1] in policy['component_members']
                and dimensions[policy['valuation_axis']]==policy['valuation_member'])
        if any(not allowed_dimensions(row) for row in rows):
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
        if policy.get('reject_unlisted_contingent_claims'):
            unknown=[row for row in facts if row.get('period_end')==period
                     and row.get('period_start') is None and row.get('source_accession')==accession
                     and 'contingentconsideration' in str(row.get('local_name','')).lower()
                     and isinstance(row.get('value'),(int,float)) and not isinstance(row.get('value'),bool)
                     and float(row['value'])!=0 and row.get('qname')!=policy['qname']]
            if unknown:raise ValueError('unlisted current contingent-consideration claim requires review')
        if policy.get('acquisition_alias_member_local_names'):
            aliases=[row for row in rows if _dims(row).keys()=={policy['acquisition_axis']}]
            for member in policy['acquisition_alias_member_local_names']:
                selected=[row for row in aliases if str(_dims(row)[policy['acquisition_axis']]).rsplit(':',1)[-1]==member]
                if not selected or {float(row['value']) for row in selected}!={claim}:
                    raise ValueError('named acquisition alias does not reconcile to carrying total')
            excluded_rows.extend(aliases)
            cash=[row for row in facts if row.get('qname')==policy['acquisition_cash_qname']
                  and row.get('period_end')==period and isinstance(row.get('period_start'),str)
                  and not row.get('dimensions')]
            for row in cash:_valid_row(row,policy=policy,accession=accession,period=period,instant=False)
            if not cash:raise ValueError('current acquisition cash diagnostic is missing')
            excluded_rows.extend(cash)
            components.update({'acquisition_alias_is_not_additive':claim,
                'acquisition_cash_is_not_added':sorted({float(row['value']) for row in cash})})
        if policy.get('component_members'):
            component_rows=[]
            for member in policy['component_members']:
                matches=[row for row in rows if set(_dims(row))=={policy['component_axis'],policy['valuation_axis']}
                         and str(_dims(row)[policy['component_axis']]).rsplit(':',1)[-1]==member
                         and _dims(row)[policy['valuation_axis']]==policy['valuation_member']]
                if not matches or len({float(row['value']) for row in matches})!=1:
                    raise ValueError(f'current acquisition claim component is missing or conflicting: {member}')
                component_rows.append(matches[0])
            if sum(float(row['value']) for row in component_rows)!=claim:
                raise ValueError('current acquisition claim components do not reconcile to aggregate')
            source_rows.extend(component_rows)
            maximum=[row for row in facts if row.get('qname')==policy['maximum_qname']
                     and row.get('period_end')==period and row.get('period_start') is None]
            for row in maximum:_valid_row(row,policy=policy,accession=accession,period=period)
            if not maximum: raise ValueError('current acquisition maximum diagnostic is missing')
            paid=[]
            for local_name in policy['cash_paid_local_names']:
                matches=[row for row in facts if row.get('local_name')==local_name and row.get('period_end')==period
                         and isinstance(row.get('period_start'),str) and not row.get('dimensions')]
                for row in matches:_valid_row(row,policy=policy,accession=accession,period=period,instant=False,
                                              issuer=not str(row.get('qname','')).startswith('us-gaap:'))
                if not matches: raise ValueError(f'current acquisition cash diagnostic is missing: {local_name}')
                paid.extend(matches)
            excluded_rows.extend([*maximum,*paid])
            components={'carrying_components':{member:float(row['value']) for member,row in zip(policy['component_members'],component_rows)},
                        'maximum_is_not_current_claim':max(float(row['value']) for row in maximum),
                        'paid_cash_is_not_added':[float(row['value']) for row in paid]}
        if policy.get('pro_forma_revenue_qname'):
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
        if policy.get('measurement_change_qname'):
            changes=[row for row in facts if row.get('qname')==policy['measurement_change_qname']
                     and row.get('period_end')==period and isinstance(row.get('period_start'),str)]
            cash=[row for row in facts if row.get('qname')==policy['acquisition_cash_qname']
                  and row.get('period_end')==period and isinstance(row.get('period_start'),str)
                  and not row.get('dimensions')]
            for row in changes:_valid_row(row,policy=policy,accession=accession,period=period,instant=False,allow_signed=True)
            for row in cash:_valid_row(row,policy=policy,accession=accession,period=period,instant=False)
            if not changes or not cash:
                raise ValueError('current acquisition change/cash diagnostics are missing')
            excluded_rows.extend([*changes,*cash])
            components.update({'measurement_changes_are_not_claims':[float(row['value']) for row in changes],
                               'acquisition_cash_is_not_contingent_payment':list({float(row['value']) for row in cash})})
        formula='matching current aggregate and Level-3 carrying-liability presentations, counted once'
    elif mode == 'current_liability_with_maximum':
        current=[row for row in facts if row.get('qname')==policy['qname'] and row.get('period_end')==period
                 and row.get('period_start') is None and not row.get('dimensions')]
        for row in current:_valid_row(row,policy=policy,accession=accession,period=period)
        if not current or len({float(row['value']) for row in current})!=1:
            raise ValueError('current acquisition carrying liability is missing or conflicting')
        current_portion=float(current[0]['value'])
        aggregate=[row for row in facts if row.get('qname')==policy['aggregate_qname']
                   and row.get('period_end')==period and row.get('period_start') is None
                   and (not _dims(row) or _dims(row)=={policy['level_axis']:policy['level_member']})]
        rollforward=[row for row in facts if row.get('qname')==policy['rollforward_qname']
                     and row.get('period_end')==period and row.get('period_start') is None
                     and _dims(row).keys()=={policy['rollforward_axis']}
                     and str(_dims(row)[policy['rollforward_axis']]).rsplit(':',1)[-1]==policy['rollforward_member_local_name']]
        for row in (*aggregate,*rollforward):_valid_row(row,policy=policy,accession=accession,period=period)
        carrying_values={float(row['value']) for row in (*aggregate,*rollforward)}
        if (not aggregate or not any(not _dims(row) for row in aggregate)
            or not any(_dims(row) for row in aggregate) or not rollforward
            or len(carrying_values)!=1):
            raise ValueError('aggregate contingent carrying value does not reconcile')
        claim=carrying_values.pop()
        if current_portion>claim:
            raise ValueError('current contingent consideration exceeds aggregate carrying value')
        maximum=[row for row in facts if row.get('qname')==policy['maximum_qname']
                 and row.get('period_start') is None and row.get('period_end','')<=period
                 and _dims(row).keys()=={policy['acquisition_axis']}
                 and str(_dims(row)[policy['acquisition_axis']]).rsplit(':',1)[-1]==policy['maximum_member_local_name']]
        for row in maximum:_valid_row(row,policy=policy,accession=accession,period=row['period_end'])
        if not maximum or max(float(row['value']) for row in maximum)<claim:
            raise ValueError('acquisition maximum diagnostic is missing or below current liability')
        equity=[row for row in facts if row.get('qname')==policy['separate_equity_qname']
                and row.get('period_start')==row.get('period_end') and row.get('period_end','')<=period
                and str(_dims(row).get(policy['acquisition_axis'],'')).rsplit(':',1)[-1]==policy['separate_equity_member_local_name']]
        for row in equity:_valid_row(row,policy=policy,accession=accession,period=row['period_end'],instant=False)
        if not equity: raise ValueError('separate acquisition equity diagnostic is missing')
        source_rows=[*aggregate,*rollforward,*current];excluded_rows=[*maximum,*equity]
        components={'aggregate_carrying_liability':claim,'current_carrying_portion':current_portion,
                    'maximum_is_not_current_claim':max(float(row['value']) for row in maximum),
                    'separate_acquisition_equity_not_contingent_claim':[float(row['value']) for row in equity]}
        formula='current acquisition carrying liability only; historical maximum and separate acquisition equity consideration excluded'
    elif mode == 'custom_carrying_alias':
        expected_dimensions={policy['debt_axis']:policy['debt_member']}
        carrying=[row for row in facts if row.get('local_name')==policy['carrying_local_name']
                  and row.get('period_end')==period and row.get('period_start') is None
                  and _dims(row)==expected_dimensions]
        fair_value=[row for row in facts if row.get('local_name')==policy['fair_value_local_name']
                    and row.get('period_end')==period and row.get('period_start') is None
                    and _dims(row)==expected_dimensions]
        for row in (*carrying,*fair_value):_valid_row(
            row,policy=policy,accession=accession,period=period,issuer=True)
        amounts={float(row['value']) for row in (*carrying,*fair_value)}
        if not carrying or not fair_value or len(amounts)!=1:
            raise ValueError('acquisition obligation carrying/fair-value aliases do not reconcile')
        claim=amounts.pop()
        if any('us-gaap:DebtInstrumentLineItems' not in (row.get('presentation_ancestry') or [])
               for row in (*carrying,*fair_value)):
            raise ValueError('acquisition obligation is not presented in the debt instrument table')
        if policy.get('reject_unlisted_contingent_claims'):
            unexpected=[row for row in facts if row.get('source_accession')==accession
                        and row.get('period_end')==period and row.get('period_start') is None
                        and 'contingentconsideration' in str(row.get('local_name','')).lower()
                        and row.get('local_name') not in {policy['carrying_local_name'],policy['fair_value_local_name']}
                        and isinstance(row.get('value'),(int,float)) and not isinstance(row.get('value'),bool)
                        and float(row['value'])!=0]
            if unexpected:
                raise ValueError('unlisted current contingent-consideration claim requires review')
        sensitivity=[row for row in facts if row.get('local_name')==policy['nci_sensitivity_local_name']
                     and row.get('period_end')==period and row.get('period_start') is None
                     and not row.get('dimensions')]
        cash=[row for row in facts if row.get('qname')==policy['acquisition_cash_qname']
              and row.get('period_end')==period and isinstance(row.get('period_start'),str)
              and not row.get('dimensions')]
        for row in sensitivity:_valid_row(row,policy=policy,accession=accession,period=period,issuer=True)
        for row in cash:_valid_row(row,policy=policy,accession=accession,period=period,instant=False)
        if not sensitivity or not cash:
            raise ValueError('acquisition obligation diagnostics are incomplete')
        event=[row for row in facts if row.get('qname')==policy['subsequent_event_qname']
               and isinstance(row.get('period_start'),str) and row.get('period_start')==row.get('period_end')
               and period<row.get('period_end','')<=cutoff
               and _dims(row).get(policy['subsequent_event_axis'])==policy['subsequent_event_member']
               and any(str(axis).rsplit(':',1)[-1]==policy['investee_axis_local_name']
                       and str(member).rsplit(':',1)[-1]==policy['investee_member_local_name']
                       for axis,member in (row.get('dimensions') or []))]
        for row in event:_valid_row(row,policy=policy,accession=accession,period=row['period_end'],instant=False)
        if policy.get('requires_post_period_rollforward') and not event:
            raise ValueError('post-period acquisition cash evidence is missing')
        source_rows=[*carrying,*fair_value];excluded_rows=[*sensitivity,*cash,*event]
        components={'acquisition_obligation_carrying_value':claim,
                    'fair_value_alias_is_not_additive':float(fair_value[0]['value']),
                    'acquisition_obligation_in_aggregate_debt':True,
                    'nci_fair_value_sensitivity_is_not_claim':list({float(row['value']) for row in sensitivity}),
                    'acquisition_cash_is_not_added':list({float(row['value']) for row in cash}),
                    'post_period_investment_cash_requires_rollforward':list({float(row['value']) for row in event})}
        if policy.get('requires_aggregate_debt_overlap_review'):
            review.append('acquisition_obligation_already_in_aggregate_debt')
        if policy.get('requires_post_period_rollforward'):
            review.append('post_period_investment_cash_lacks_cash_debt_share_and_operating_rollforward')
        if review:
            extra['current_carrying_liability']=claim
            claim=None
        formula='current acquisition obligation retained inside aggregate debt; fair-value alias, NCI sensitivity, acquisition cash and post-period investment cash are non-additive review evidence'
    elif mode == 'current_noncurrent_with_deferred_review':
        carrying_rows=[];carrying_total=0.
        allowed_levels={'us-gaap:FairValueInputsLevel1Member','us-gaap:FairValueInputsLevel2Member',policy['level_member']}
        for qname in policy['component_qnames']:
            rows=[row for row in facts if row.get('qname')==qname and row.get('period_end')==period
                  and row.get('period_start') is None]
            for row in rows:_valid_row(row,policy=policy,accession=accession,period=period)
            if any(_dims(row) and (_dims(row).keys()!={policy['level_axis']}
                                  or _dims(row).get(policy['level_axis']) not in allowed_levels) for row in rows):
                raise ValueError('unexpected contingent-liability component dimension')
            aggregate=[row for row in rows if not _dims(row)]
            level3=[row for row in rows if _dims(row)=={policy['level_axis']:policy['level_member']}]
            other=[row for row in rows if _dims(row).get(policy['level_axis']) in allowed_levels-{policy['level_member']}]
            values={float(row['value']) for row in (*aggregate,*level3)}
            if not aggregate or not level3 or len(values)!=1 or any(float(row['value'])!=0 for row in other):
                raise ValueError('current/noncurrent contingent-liability presentations do not reconcile')
            carrying_total+=values.pop();carrying_rows.extend([*aggregate,*level3,*other])
        rollforward=[row for row in facts if row.get('qname')==policy['rollforward_qname']
                     and row.get('period_end')==period and row.get('period_start') is None
                     and _dims(row).keys()=={policy['rollforward_axis']}
                     and str(_dims(row)[policy['rollforward_axis']]).rsplit(':',1)[-1]==policy['rollforward_member_local_name']]
        fair_value=[row for row in facts if row.get('qname')==policy['fair_value_qname']
                    and row.get('period_end')==period and row.get('period_start') is None
                    and (not _dims(row) or _dims(row)=={policy['level_axis']:policy['level_member']})]
        for row in (*rollforward,*fair_value):_valid_row(row,policy=policy,accession=accession,period=period)
        if (not rollforward or not fair_value
            or {float(row['value']) for row in (*rollforward,*fair_value)}!={carrying_total}):
            raise ValueError('aggregate contingent-liability corroboration does not reconcile')
        deferred=[row for row in facts if row.get('qname')==policy['deferred_qname']
                  and row.get('period_end')==period and row.get('period_start') is None
                  and _dims(row).keys()=={policy['acquisition_axis']}
                  and str(_dims(row)[policy['acquisition_axis']]).rsplit(':',1)[-1]==policy['deferred_member_local_name']]
        for row in deferred:_valid_row(row,policy=policy,accession=accession,period=period)
        if not deferred or len({float(row['value']) for row in deferred})!=1:
            raise ValueError('current deferred acquisition consideration is missing or conflicting')
        deferred_value=float(deferred[0]['value'])
        paid=[row for row in facts if row.get('qname')==policy['paid_cash_qname']
              and row.get('period_end')==period and isinstance(row.get('period_start'),str)
              and not row.get('dimensions')]
        acquisition_cash=[row for row in facts if row.get('qname')==policy['acquisition_cash_qname']
                          and row.get('period_end')==period and isinstance(row.get('period_start'),str)
                          and not row.get('dimensions')]
        for row in (*paid,*acquisition_cash):_valid_row(row,policy=policy,accession=accession,period=period,instant=False)
        if not paid or not acquisition_cash:
            raise ValueError('current acquisition cash diagnostics are missing')
        source_rows=[*carrying_rows,*deferred]
        excluded_rows=[*rollforward,*fair_value,*paid,*acquisition_cash]
        current_total=carrying_total+deferred_value
        components={'current_and_noncurrent_contingent_consideration':carrying_total,
                    'deferred_acquisition_consideration':deferred_value,
                    'current_claim_stack_pending_overlap_review':current_total,
                    'paid_contingent_cash_is_not_added':list({float(row['value']) for row in paid}),
                    'acquisition_cash_is_not_added':list({float(row['value']) for row in acquisition_cash})}
        review.append('deferred_acquisition_consideration_cash_flow_overlap_unresolved')
        extra['current_carrying_liability']=current_total
        claim=None
        formula='current and noncurrent contingent carrying liabilities plus separately recorded deferred consideration; paid cash excluded and deferred-consideration operating overlap requires review'
    elif mode == 'single_carrying_component':
        rows=[row for row in facts if row.get('qname')==policy['component_qname']
              and row.get('period_end')==period and row.get('period_start') is None
              and not row.get('dimensions')]
        for row in rows:_valid_row(row,policy=policy,accession=accession,period=period)
        if not rows or len({float(row['value']) for row in rows})!=1:
            raise ValueError('single acquisition carrying component is missing or conflicting')
        claim=float(rows[0]['value'])
        nci=[row for row in facts if row.get('qname')==policy['nci_qname']
             and row.get('period_end')==period and row.get('period_start') is None
             and not row.get('dimensions')]
        for row in nci:_valid_row(row,policy=policy,accession=accession,period=period)
        if not nci or len({float(row['value']) for row in nci})!=1:
            raise ValueError('ordinary NCI carrying diagnostic is missing or conflicting')
        operating=[]
        for qname in policy.get('excluded_operating_qnames',()):
            selected=[row for row in facts if row.get('qname')==qname
                      and row.get('period_end')==period and row.get('period_start') is None]
            for row in selected:_valid_row(row,policy=policy,accession=accession,period=period)
            operating.extend(selected)
        accepted={id(row) for row in rows}
        unexpected=[row for row in facts if row.get('period_end')==period
                    and row.get('period_start') is None and row.get('source_accession')==accession
                    and 'contingentconsideration' in str(row.get('local_name','')).lower()
                    and isinstance(row.get('value'),(int,float)) and not isinstance(row.get('value'),bool)
                    and float(row['value'])!=0 and id(row) not in accepted]
        if unexpected:
            raise ValueError('unlisted current contingent-consideration claim requires review')
        source_rows=rows;excluded_rows=[*nci,*operating]
        components={'acquisition_carrying_liability':claim,
                    'ordinary_nci_is_separate':float(nci[0]['value']),
                    'operating_reserves_not_added':sorted({float(row['value']) for row in operating})}
        formula='single current-period acquisition carrying component, deducted once; NCI and operating reserves excluded'
    elif mode == 'aggregate_with_reconciling_components':
        aggregate=[row for row in facts if row.get('qname')==policy['qname']
                   and row.get('period_end')==period and row.get('period_start') is None
                   and not row.get('dimensions')]
        for row in aggregate:_valid_row(row,policy=policy,accession=accession,period=period)
        if not aggregate or len({float(row['value']) for row in aggregate})!=1:
            raise ValueError('aggregate acquisition carrying liability is missing or conflicting')
        claim=float(aggregate[0]['value'])
        location=[]
        for row in facts:
            if (row.get('qname')!=policy['qname'] or row.get('period_end')!=period
                or row.get('period_start') is not None
                or _dims(row)!={policy['location_axis']:'typed'}):
                continue
            _valid_row(row,policy=policy,accession=accession,period=period)
            typed=row.get('typed_dimensions')
            if not isinstance(typed,(list,tuple)) or len(typed)!=1 or len(typed[0])!=3:
                raise ValueError('typed current/noncurrent acquisition locations are not preserved')
            axis,domain,member=typed[0]
            if axis!=policy['location_axis'] or domain!=policy['location_typed_domain'] or member not in {
                policy['current_location_member'],policy['noncurrent_location_member']}:
                raise ValueError('typed acquisition location member is unsupported')
            location.append(row)
        location_by_member={row['typed_dimensions'][0][2]:float(row['value']) for row in location}
        required_locations={policy['current_location_member'],policy['noncurrent_location_member']}
        if set(location_by_member)!=required_locations or sum(location_by_member.values())!=claim:
            raise ValueError('typed current/noncurrent acquisition locations do not reconcile')
        level3=[]
        for member in policy['component_members']:
            selected=[row for row in facts if row.get('qname')==policy['qname']
                      and row.get('period_end')==period and row.get('period_start') is None
                      and _dims(row).get(policy['level_axis'])==policy['level_member']
                      and str(_dims(row).get(policy['component_axis'],'')).rsplit(':',1)[-1]==member]
            for row in selected:_valid_row(row,policy=policy,accession=accession,period=period)
            if not selected or len({float(row['value']) for row in selected})!=1:
                raise ValueError(f'Level-3 acquisition component is missing or conflicting: {member}')
            level3.append(selected[0])
        if sum(float(row['value']) for row in level3)!=claim:
            raise ValueError('Level-3 acquisition components do not reconcile')
        cash=[row for row in facts if row.get('qname')==policy['acquisition_cash_qname']
              and row.get('period_end')==period and isinstance(row.get('period_start'),str)
              and not row.get('dimensions')]
        changes=[row for row in facts if row.get('qname')==policy['measurement_change_qname']
                 and row.get('period_end')==period and isinstance(row.get('period_start'),str)
                 and not row.get('dimensions')]
        for row in cash:_valid_row(row,policy=policy,accession=accession,period=period,instant=False)
        for row in changes:_valid_row(row,policy=policy,accession=accession,period=period,instant=False,allow_signed=True)
        if not cash or not changes:
            raise ValueError('acquisition cash or measurement-change diagnostic is missing')
        accepted={id(row) for row in (*aggregate,*location,*level3)}
        unexpected=[row for row in facts if row.get('qname')==policy['qname']
                    and row.get('period_end')==period and row.get('period_start') is None
                    and isinstance(row.get('value'),(int,float)) and not isinstance(row.get('value'),bool)
                    and float(row['value'])!=0 and id(row) not in accepted]
        if unexpected:
            raise ValueError('unlisted current acquisition presentation requires review')
        source_rows=[*aggregate,*location,*level3];excluded_rows=[*cash,*changes]
        components={'aggregate_carrying_liability':claim,
                    'current_portion':location_by_member[policy['current_location_member']],
                    'noncurrent_portion':location_by_member[policy['noncurrent_location_member']],
                    'level3_components':{member:float(row['value']) for member,row in zip(policy['component_members'],level3)},
                    'acquisition_cash_is_not_added':sorted({float(row['value']) for row in cash}),
                    'measurement_changes_are_not_claims':sorted({float(row['value']) for row in changes})}
        formula='aggregate acquisition carrying liability counted once; typed locations and Level-3 components independently reconcile'
    elif mode == 'current_noncurrent_level3_duplicates':
        carrying=[];parts={}
        allowed_levels={'us-gaap:FairValueInputsLevel1Member','us-gaap:FairValueInputsLevel2Member',policy['level_member']}
        for qname in policy['component_qnames']:
            rows=[row for row in facts if row.get('qname')==qname and row.get('period_end')==period
                  and row.get('period_start') is None]
            for row in rows:_valid_row(row,policy=policy,accession=accession,period=period)
            if any(_dims(row) and (_dims(row).keys()!={policy['level_axis']}
                                  or _dims(row).get(policy['level_axis']) not in allowed_levels) for row in rows):
                raise ValueError('unexpected current/noncurrent acquisition dimension')
            aggregate=[row for row in rows if not _dims(row)]
            level3=[row for row in rows if _dims(row)=={policy['level_axis']:policy['level_member']}]
            other=[row for row in rows if _dims(row).get(policy['level_axis']) in allowed_levels-{policy['level_member']}]
            values={float(row['value']) for row in (*aggregate,*level3)}
            if not aggregate or not level3 or len(values)!=1 or any(float(row['value'])!=0 for row in other):
                raise ValueError('current/noncurrent acquisition presentations do not reconcile')
            parts[qname]=values.pop();carrying.extend([*aggregate,*level3,*other])
        claim=sum(parts.values())
        changes=[row for row in facts if row.get('qname')==policy['measurement_change_qname']
                 and row.get('period_end')==period and isinstance(row.get('period_start'),str)
                 and not row.get('dimensions')]
        for row in changes:_valid_row(row,policy=policy,accession=accession,period=period,instant=False,allow_signed=True)
        if not changes:
            raise ValueError('current acquisition measurement-change diagnostic is missing')
        accepted={id(row) for row in carrying}
        unexpected=[row for row in facts if row.get('period_end')==period
                    and row.get('period_start') is None and row.get('source_accession')==accession
                    and 'contingentconsideration' in str(row.get('local_name','')).lower()
                    and isinstance(row.get('value'),(int,float)) and not isinstance(row.get('value'),bool)
                    and float(row['value'])!=0 and id(row) not in accepted]
        if unexpected:
            raise ValueError('unlisted current contingent-consideration presentation requires review')
        source_rows=carrying;excluded_rows=changes
        components={'current_carrying_portion':parts[QNAME+'Current'],
                    'noncurrent_carrying_portion':parts[QNAME+'Noncurrent'],
                    'aggregate_carrying_liability':claim,
                    'measurement_changes_are_not_claims':sorted({float(row['value']) for row in changes})}
        formula='current and noncurrent carrying components summed once; matching Level-3 presentations excluded as duplicates'
    elif mode == 'recurring_hierarchy_duplicates':
        rows=[row for row in facts if row.get('qname')==policy['qname']
              and row.get('period_end')==period and row.get('period_start') is None]
        for row in rows:_valid_row(row,policy=policy,accession=accession,period=period)
        aggregate=[row for row in rows if not _dims(row)]
        recurring=[row for row in rows if _dims(row)=={
            policy['frequency_axis']:policy['frequency_member']}]
        level3=[row for row in rows if _dims(row)=={
            policy['level_axis']:policy['level_member'],
            policy['frequency_axis']:policy['frequency_member']}]
        other_levels=[row for row in rows if _dims(row).get(policy['frequency_axis'])==policy['frequency_member']
                      and _dims(row).get(policy['level_axis']) in {
                          'us-gaap:FairValueInputsLevel1Member','us-gaap:FairValueInputsLevel2Member'}]
        if not aggregate or not recurring or not level3:
            raise ValueError('recurring acquisition carrying presentations are incomplete')
        amounts={float(row['value']) for row in (*aggregate,*recurring,*level3)}
        if len(amounts)!=1 or any(float(row['value'])!=0 for row in other_levels):
            raise ValueError('recurring acquisition carrying presentations conflict')
        claim=amounts.pop();source_rows=[*aggregate,*recurring,*level3,*other_levels]
        accepted={id(row) for row in source_rows}
        unexpected=[row for row in rows if isinstance(row.get('value'),(int,float))
                    and not isinstance(row.get('value'),bool) and float(row['value'])!=0
                    and id(row) not in accepted]
        if unexpected:
            raise ValueError('unlisted current recurring acquisition presentation requires review')
        paid=[row for row in facts if row.get('local_name')==policy['payment_local_name']
              and row.get('period_end')==period and isinstance(row.get('period_start'),str)
              and not row.get('dimensions')]
        changes=[row for row in facts if row.get('local_name')==policy['measurement_change_local_name']
                 and row.get('period_end')==period and isinstance(row.get('period_start'),str)
                 and not row.get('dimensions')]
        for row in (*paid,*changes):_valid_row(
            row,policy=policy,accession=accession,period=period,instant=False,issuer=True,allow_signed=True)
        if not paid or not changes:
            raise ValueError('current acquisition payment or measurement-change diagnostic is missing')
        deferred=[row for row in facts if row.get('local_name')==policy['deferred_local_name']
                  and row.get('period_end')==period and isinstance(row.get('period_start'),str)
                  and policy['acquisition_axis'] in _dims(row)]
        acquisition_cash=[row for row in facts if row.get('qname')==policy['acquisition_cash_qname']
                          and row.get('period_end')==period and isinstance(row.get('period_start'),str)
                          and policy['acquisition_axis'] in _dims(row)]
        for row in deferred:_valid_row(
            row,policy=policy,accession=accession,period=period,instant=False,issuer=True)
        for row in acquisition_cash:_valid_row(
            row,policy=policy,accession=accession,period=period,instant=False)
        if not deferred or not acquisition_cash:
            raise ValueError('deferred-consideration or acquisition-cash diagnostic is missing')
        excluded_rows=[*paid,*changes,*deferred,*acquisition_cash]
        components={'aggregate_carrying_liability':claim,
                    'recurring_view_is_not_additive':claim,
                    'level3_view_is_not_additive':claim,
                    'paid_cash_is_not_added':sorted({float(row['value']) for row in paid}),
                    'measurement_changes_are_not_claims':sorted({float(row['value']) for row in changes}),
                    'deferred_consideration_duration_disclosures_are_not_current_claims':sorted({float(row['value']) for row in deferred}),
                    'acquisition_cash_is_not_added':sorted({float(row['value']) for row in acquisition_cash})}
        formula='matching aggregate, recurring and Level-3 carrying presentations counted once; payment and measurement flows excluded'
    elif mode == 'aggregate_current_noncurrent':
        rows=[row for row in facts if row.get('qname') in {policy['qname'],*policy['component_qnames']}
              and row.get('period_end')==period and row.get('period_start') is None]
        for row in rows:_valid_row(row,policy=policy,accession=accession,period=period)
        aggregate=[row for row in rows if row.get('qname')==policy['qname'] and not _dims(row)]
        if not aggregate or len({float(row['value']) for row in aggregate})!=1:
            raise ValueError('aggregate acquisition carrying liability is missing or conflicting')
        claim=float(aggregate[0]['value']);part_rows=[];parts={}
        for qname in policy['component_qnames']:
            selected=[row for row in rows if row.get('qname')==qname and not _dims(row)]
            if not selected or len({float(row['value']) for row in selected})!=1:
                raise ValueError(f'acquisition carrying component is missing or conflicting: {qname}')
            parts[qname]=float(selected[0]['value']);part_rows.extend(selected)
        if sum(parts.values())!=claim:
            raise ValueError('current and noncurrent acquisition carrying components do not reconcile')
        accepted={id(row) for row in (*aggregate,*part_rows)}
        unexpected=[row for row in rows if isinstance(row.get('value'),(int,float))
                    and not isinstance(row.get('value'),bool) and float(row['value'])!=0
                    and id(row) not in accepted]
        if unexpected:
            raise ValueError('unlisted current acquisition presentation requires review')
        cash=[row for row in facts if row.get('qname')==policy['acquisition_cash_qname']
              and row.get('period_end')==period and isinstance(row.get('period_start'),str)
              and not row.get('dimensions')]
        for row in cash:_valid_row(row,policy=policy,accession=accession,period=period,instant=False)
        if not cash:
            raise ValueError('current acquisition cash diagnostic is missing')
        source_rows=[*aggregate,*part_rows];excluded_rows=cash
        components={'aggregate_carrying_liability':claim,
                    'current_carrying_portion':parts[QNAME+'Current'],
                    'noncurrent_carrying_portion':parts[QNAME+'Noncurrent'],
                    'acquisition_cash_is_not_added':sorted({float(row['value']) for row in cash})}
        formula='aggregate acquisition carrying liability counted once after exact current/noncurrent reconciliation; acquisition cash excluded'
    elif mode == 'recurring_hierarchy_with_acquisition_diagnostics':
        rows=[row for row in facts if row.get('qname')==policy['qname']
              and row.get('period_end')==period and row.get('period_start') is None]
        for row in rows:_valid_row(row,policy=policy,accession=accession,period=period)
        recurring=[row for row in rows if _dims(row)=={
            policy['frequency_axis']:policy['frequency_member']}]
        level3=[row for row in rows if _dims(row)=={
            policy['level_axis']:policy['level_member'],
            policy['frequency_axis']:policy['frequency_member']}]
        other_levels=[row for row in rows if _dims(row).get(policy['frequency_axis'])==policy['frequency_member']
                      and _dims(row).get(policy['level_axis']) in {
                          'us-gaap:FairValueInputsLevel1Member','us-gaap:FairValueInputsLevel2Member'}]
        if not recurring or not level3:
            raise ValueError('recurring and Level-3 acquisition carrying presentations are incomplete')
        amounts={float(row['value']) for row in (*recurring,*level3)}
        if len(amounts)!=1 or any(float(row['value'])!=0 for row in other_levels):
            raise ValueError('recurring and Level-3 acquisition carrying presentations conflict')
        claim=amounts.pop()
        acquisition_rows=[row for row in rows if policy['acquisition_axis'] in _dims(row)]
        if not acquisition_rows:
            raise ValueError('current acquisition-member diagnostics are missing')
        accepted={id(row) for row in (*recurring,*level3,*other_levels,*acquisition_rows)}
        unexpected=[row for row in rows if isinstance(row.get('value'),(int,float))
                    and not isinstance(row.get('value'),bool) and float(row['value'])!=0
                    and id(row) not in accepted]
        if unexpected:
            raise ValueError('unlisted current acquisition presentation requires review')
        maximum=[row for row in facts if row.get('qname')==policy['maximum_qname']
                 and row.get('period_end')==period and row.get('period_start') is None]
        paid=[row for row in facts if row.get('qname')==policy['paid_cash_qname']
              and row.get('period_end')==period and isinstance(row.get('period_start'),str)
              and not row.get('dimensions')]
        acquisition_cash=[row for row in facts if row.get('qname')==policy['acquisition_cash_qname']
                          and row.get('period_end')==period and isinstance(row.get('period_start'),str)
                          and policy['acquisition_axis'] in _dims(row)]
        for row in maximum:_valid_row(row,policy=policy,accession=accession,period=period)
        for row in paid:_valid_row(row,policy=policy,accession=accession,period=period,instant=False)
        for row in acquisition_cash:_valid_row(row,policy=policy,accession=accession,period=period,instant=False)
        if not maximum or not paid or not acquisition_cash:
            raise ValueError('maximum, paid-cash or acquisition-cash diagnostic is missing')
        source_rows=[*recurring,*level3,*other_levels]
        excluded_rows=[*acquisition_rows,*maximum,*paid,*acquisition_cash]
        components={'aggregate_carrying_liability':claim,
                    'level3_view_is_not_additive':claim,
                    'acquisition_member_values_are_not_additive':sorted({float(row['value']) for row in acquisition_rows}),
                    'maximum_is_not_current_claim':max(float(row['value']) for row in maximum),
                    'paid_cash_is_not_added':sorted({float(row['value']) for row in paid}),
                    'acquisition_cash_is_not_added':sorted({float(row['value']) for row in acquisition_cash})}
        formula='recurring aggregate and Level-3 carrying presentations counted once; acquisition details, maxima and cash flows excluded'
    elif mode == 'dimensioned_noncurrent_with_pending_event':
        current=[row for row in facts if row.get('qname')==policy['qname']
                 and row.get('period_end')==period and row.get('period_start') is None
                 and _dims(row).keys()=={policy['acquisition_axis']}
                 and str(_dims(row)[policy['acquisition_axis']]).rsplit(':',1)[-1]
                    ==policy['acquisition_member_local_name']]
        for row in current:_valid_row(row,policy=policy,accession=accession,period=period)
        if not current or len({float(row['value']) for row in current})!=1:
            raise ValueError('dimensioned current acquisition carrying liability is missing or conflicting')
        claim=float(current[0]['value'])
        all_current=[row for row in facts if row.get('period_end')==period
                     and row.get('period_start') is None and row.get('source_accession')==accession
                     and 'contingentconsideration' in str(row.get('local_name','')).lower()
                     and isinstance(row.get('value'),(int,float)) and not isinstance(row.get('value'),bool)
                     and float(row['value'])!=0]
        if any(row not in current for row in all_current):
            raise ValueError('unlisted current contingent-consideration claim requires review')
        cash=[row for row in facts if row.get('qname')==policy['acquisition_cash_qname']
              and row.get('period_end')==period and isinstance(row.get('period_start'),str)
              and (not _dims(row) or (_dims(row).keys()=={policy['acquisition_axis']}
                  and str(_dims(row)[policy['acquisition_axis']]).rsplit(':',1)[-1]
                     ==policy['acquisition_member_local_name']))]
        for row in cash:_valid_row(row,policy=policy,accession=accession,period=period,instant=False)
        cash_values={float(row['value']) for row in cash}
        if not cash or len(cash_values)!=1:
            raise ValueError('aggregate and acquisition-member cash payments do not reconcile')
        pending=[row for row in facts if row.get('qname')==policy['acquisition_cash_qname']
                 and isinstance(row.get('period_start'),str) and row.get('period_start')==row.get('period_end')
                 and period<row.get('period_end','')<=cutoff
                 and str(_dims(row).get(policy['acquisition_axis'],'')).rsplit(':',1)[-1]
                    ==policy['pending_member_local_name']
                 and _dims(row).get(policy['subsequent_event_axis'])==policy['subsequent_event_member']
                 and any(str(axis).rsplit(':',1)[-1]==policy['scenario_axis_local_name']
                         and str(member).rsplit(':',1)[-1]==policy['scenario_member_local_name']
                         for axis,member in (row.get('dimensions') or []))]
        for row in pending:_valid_row(row,policy=policy,accession=accession,period=row['period_end'],instant=False)
        if not pending or len({float(row['value']) for row in pending})!=1:
            raise ValueError('pending acquisition payment evidence is missing or conflicting')
        costs=[row for row in facts if row.get('local_name')==policy['acquisition_cost_local_name']
               and row.get('period_end')==period and isinstance(row.get('period_start'),str)
               and not row.get('dimensions')]
        for row in costs:_valid_row(row,policy=policy,accession=accession,period=period,instant=False,issuer=True)
        if not costs:
            raise ValueError('acquisition integration-cost diagnostic is missing')
        source_rows=current;excluded_rows=[*cash,*pending,*costs]
        components={'noncurrent_acquisition_carrying_liability':claim,
                    'acquisition_cash_is_not_added':cash_values.pop(),
                    'pending_forecast_acquisition_payment_is_not_current_claim':float(pending[0]['value']),
                    'acquisition_and_integration_cost_flows':sorted({float(row['value']) for row in costs})}
        formula='dimensioned noncurrent acquisition carrying liability deducted once; paid cash, integration expense and forecast post-period payment excluded'
    elif mode == 'direct_total_with_acquisition_cash':
        current=[row for row in facts if row.get('qname')==policy['qname']
                 and row.get('period_end')==period and row.get('period_start') is None
                 and not row.get('dimensions')]
        for row in current:_valid_row(row,policy=policy,accession=accession,period=period)
        if not current or len({float(row['value']) for row in current})!=1:
            raise ValueError('current acquisition carrying total is missing or conflicting')
        claim=float(current[0]['value'])
        unexpected=[row for row in facts if row.get('period_end')==period and row.get('period_start') is None
                    and row.get('source_accession')==accession
                    and 'contingentconsideration' in str(row.get('local_name','')).lower()
                    and isinstance(row.get('value'),(int,float)) and not isinstance(row.get('value'),bool)
                    and float(row['value'])!=0 and row not in current]
        if unexpected:
            raise ValueError('unlisted current contingent-consideration claim requires review')
        cash=[row for row in facts if row.get('qname')==policy['acquisition_cash_qname']
              and row.get('period_end')==period and isinstance(row.get('period_start'),str)
              and not row.get('dimensions')]
        for row in cash:_valid_row(row,policy=policy,accession=accession,period=period,instant=False)
        if not cash or len({float(row['value']) for row in cash})!=1:
            raise ValueError('current acquisition cash diagnostic is missing or conflicting')
        source_rows=current;excluded_rows=cash
        components={'acquisition_carrying_liability':claim,
                    'acquisition_cash_is_not_added':float(cash[0]['value'])}
        formula='current acquisition carrying total deducted once; acquisition cash excluded'
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
            'current_carrying_liability':extra.get('current_carrying_liability',
                sum(float(row['value']) for row in source_rows[:2]) if mode=='level3_components' else claim),
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
    if (policy.get('ticker') in WG2_CLAIM_RULES or policy.get('ticker') in WG15_CLAIM_RULES
        or policy.get('ticker') in WG16_CLAIM_RULES or policy.get('ticker') in WG17_CLAIM_RULES
        or policy.get('ticker') in WG18_CLAIM_RULES or policy.get('ticker') in WG19_CLAIM_RULES
        or policy.get('ticker') in WG20_CLAIM_RULES or policy.get('ticker') in WG22_CLAIM_RULES):
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
