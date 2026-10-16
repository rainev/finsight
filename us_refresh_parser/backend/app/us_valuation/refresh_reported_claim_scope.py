"""Validated source scope for the ordinary reported-NCI refresh mappings.

The legacy recipe field named ``preferred_equity`` contains reported
noncontrolling-interest amounts for several ordinary FCFF recipes.  This
module makes that semantic mapping explicit without changing the normalized
bridge or embedding any filing amount/date in the rule table.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import isclose, isfinite
from numbers import Real
import re
from types import MappingProxyType
from typing import Any, Mapping

from .bridge_policy import BridgeRange, BridgeResolution
from .field_availability import FieldAvailability


CLAIM_SCOPE_MAPPING_VERSION = "FINSIGHT-REPORTED-NCI-SCOPE-2"
_US_GAAP_NAMESPACE_RE = re.compile(r"^https?://(?:fasb\.org|xbrl\.us-gaap)/us-gaap/[0-9]{4}$")
_NCI_LOCAL_MARKERS = ("noncontrollinginterest", "minorityinterest")


class ClaimScopeReviewRequired(ValueError):
    """Raised when current NCI source scope is missing or ambiguous."""

    def __init__(self, *reasons: str) -> None:
        self.reasons = tuple(str(reason) for reason in reasons if str(reason))
        super().__init__("reported NCI scope requires review: " + "; ".join(self.reasons))


@dataclass(frozen=True)
class ReportedNciScopeRule:
    ticker: str
    cik: str
    required_qnames: tuple[str, ...]
    allowed_alias_qnames: tuple[str, ...] = ()
    excluded_nonpositive_qnames: tuple[str, ...] = ()
    diagnostic_duration_qnames: tuple[str, ...] = ()
    diagnostic_duration_local_names: tuple[str, ...] = ()
    nonclaim_instant_local_names: tuple[str, ...] = ()
    nonclaim_instant_qnames: tuple[str, ...] = ()
    issuer_namespace_pattern: str | None = None
    negative_balance_treatment: str = "preserve_reported_claim"
    clears_legacy_claim_scope: bool = True
    require_equity_reconciliation: bool = False
    reconciled_subset_axis_local_name: str | None = None
    reconciled_subset_member_local_names: tuple[str, ...] = ()
    version: str = CLAIM_SCOPE_MAPPING_VERSION
    alias_component_targets: tuple[tuple[str, str], ...] = ()
    alias_member_scopes: tuple[tuple[str, str, str], ...] = ()
    alias_parent_scopes: tuple[tuple[str, str], ...] = ()


# Frozen semantic mappings only.  No source amounts or filing dates belong in
# this table; those are validated from the current structural packet below.
REPORTED_NCI_SCOPE_RULES: Mapping[str, ReportedNciScopeRule] = MappingProxyType({
    "ABT": ReportedNciScopeRule("ABT", "0000001800", ("us-gaap:MinorityInterest",)),
    "ABBV": ReportedNciScopeRule("ABBV", "0001551152", ("us-gaap:MinorityInterest",)),
    "ACN": ReportedNciScopeRule("ACN", "0001467373", ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount")),
    "APH": ReportedNciScopeRule("APH", "0000820313", ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount")),
    "BALL": ReportedNciScopeRule("BALL", "0000009389", ("us-gaap:MinorityInterest",)),
    "BA": ReportedNciScopeRule(
        "BA",
        "0000012927",
        ("us-gaap:MinorityInterest",),
        clears_legacy_claim_scope=False,
    ),
    "BAX": ReportedNciScopeRule(
        "BAX",
        "0000010456",
        ("us-gaap:MinorityInterest",),
        negative_balance_treatment="diagnostic_zero_fail_if_positive",
    ),
    "BSX": ReportedNciScopeRule(
        "BSX", "0000885725", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=(
            "us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
            "us-gaap:ComprehensiveIncomeNetOfTaxAttributableToNoncontrollingInterest",
            "us-gaap:OtherComprehensiveIncomeLossNetOfTaxPortionAttributableToNoncontrollingInterest",
        ),
        clears_legacy_claim_scope=False,
    ),
    "CARR": ReportedNciScopeRule("CARR", "0001783180", ("us-gaap:MinorityInterest",)),
    "CAH": ReportedNciScopeRule("CAH", "0000721371", ("us-gaap:MinorityInterest",)),
    "CF": ReportedNciScopeRule("CF", "0001324404", ("us-gaap:MinorityInterest",)),
    "CMI": ReportedNciScopeRule("CMI", "0000026172", ("us-gaap:MinorityInterest",)),
    "CPRT": ReportedNciScopeRule("CPRT", "0000900075", ("us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount",)),
    "CRL": ReportedNciScopeRule(
        "CRL", "0001100682",
        ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount"),
        diagnostic_duration_qnames=(
            "us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
            "us-gaap:ComprehensiveIncomeNetOfTaxAttributableToNoncontrollingInterest",
            "us-gaap:TemporaryEquityAccretionToRedemptionValue",
            "us-gaap:TemporaryEquityNetIncome",
        ),
        diagnostic_duration_local_names=(
            "NoncontrollingInterestIncreaseDecreaseInRedemptionValue",
            "TemporaryEquityDividendsToRedeemableNoncontrollingInterest",
            "TemporaryEquityOtherComprehensiveIncomeLossNetOfTax",
        ),
        nonclaim_instant_qnames=("us-gaap:RedeemableNoncontrollingInterestEquityRedemptionValue",),
        issuer_namespace_pattern=r"https?://(?:www\.)?crl\.com/\d{8}",
    ),
    "COO": ReportedNciScopeRule("COO", "0000711404", ("us-gaap:MinorityInterest",)),
    "COHR": ReportedNciScopeRule("COHR", "0000820318", ("us-gaap:MinorityInterest",)),
    "CSX": ReportedNciScopeRule("CSX", "0000277948", ("us-gaap:MinorityInterest",)),
    "DD": ReportedNciScopeRule("DD", "0001666700", ("us-gaap:MinorityInterest",)),
    "DVA": ReportedNciScopeRule(
        "DVA", "0000927066",
        ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount"),
        allowed_alias_qnames=(
            "us-gaap:RedeemableNoncontrollingInterestEquityFairValue",
            "us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
        ),
        diagnostic_duration_qnames=(
            "us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
            "us-gaap:ComprehensiveIncomeNetOfTaxAttributableToNoncontrollingInterest",
            "us-gaap:MinorityInterestDecreaseFromDistributionsToNoncontrollingInterestHolders",
            "us-gaap:MinorityInterestPeriodIncreaseDecrease",
            "us-gaap:PaymentsToMinorityShareholders",
        ),
        diagnostic_duration_local_names=(
            "NoncontrollingInterestIncreaseDueToAcquisitionsAndDivestitures",
            "TemporaryEquityDecreasePurchaseOfInterests",
            "TemporaryEquityDecreasefromDistributionstoNoncontrollingInterestHolders",
            "TemporaryEquityIncreaseFromContributionsFromNoncontrollingInterestHolders",
        ),
        nonclaim_instant_local_names=(
            "PotentialIncreaseDecreaseInFairValueOfNoncontrollingInterestsDueToChangeInWeightedAverageEBITDAMultiple",
        ),
        issuer_namespace_pattern=r"https?://(?:www\.)?davita\.com/\d{8}",
    ),
    "DGX": ReportedNciScopeRule(
        "DGX",
        "0001022079",
        ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount"),
        allowed_alias_qnames=("us-gaap:RedeemableNoncontrollingInterestEquityFairValue",),
        diagnostic_duration_qnames=(
            "us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
            "us-gaap:MinorityInterestDecreaseFromDistributionsToNoncontrollingInterestHolders",
            "us-gaap:PaymentsOfDividendsMinorityInterest",
        ),
        diagnostic_duration_local_names=("NoncontrollingInterestIncreaseFromContributions",),
        issuer_namespace_pattern=r"https?://(?:www\.)?questdiagnostics\.com/\d{8}",
    ),
    "DASH": ReportedNciScopeRule("DASH", "0001792789", ("us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",)),
    "EME": ReportedNciScopeRule("EME", "0000105634", ("us-gaap:MinorityInterest",)),
    "EMR": ReportedNciScopeRule("EMR", "0000032604", ("us-gaap:MinorityInterest",)),
    "EW": ReportedNciScopeRule(
        "EW", "0001099800", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=(
            "us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
            "us-gaap:ComprehensiveIncomeNetOfTaxAttributableToNoncontrollingInterest",
            "us-gaap:MinorityInterestPeriodIncreaseDecrease",
        ),
    ),
    "ECL": ReportedNciScopeRule("ECL", "0000031462", ("us-gaap:MinorityInterest",)),
    "ETN": ReportedNciScopeRule("ETN", "0001551182", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",),
        clears_legacy_claim_scope=False, require_equity_reconciliation=True, version="FINSIGHT-REPORTED-NCI-WG22-1"),
    "EXPD": ReportedNciScopeRule("EXPD", "0000746515", ("us-gaap:MinorityInterest",)),
    "FIS": ReportedNciScopeRule("FIS", "0001136893", ("us-gaap:MinorityInterest",)),
    "FTV": ReportedNciScopeRule("FTV", "0001659166", ("us-gaap:MinorityInterest",)),
    "GEV": ReportedNciScopeRule("GEV", "0001996810", ("us-gaap:MinorityInterest",)),
    "GLW": ReportedNciScopeRule(
        "GLW", "0000024741", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",),
    ),
    "GNRC": ReportedNciScopeRule("GNRC", "0001474735", ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount")),
    "GWW": ReportedNciScopeRule("GWW", "0000277135", ("us-gaap:MinorityInterest",)),
    "GILD": ReportedNciScopeRule(
        "GILD", "0000882095", ("us-gaap:MinorityInterest",),
        negative_balance_treatment="diagnostic_zero_fail_if_positive",
    ),
    "HLT": ReportedNciScopeRule("HLT", "0001585689", ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount"), ("us-gaap:RedeemableNoncontrollingInterestEquityCommonCarryingAmount",)),
    "HRL": ReportedNciScopeRule("HRL", "0000048465", ("us-gaap:MinorityInterest",)),
    "KR": ReportedNciScopeRule(
        "KR",
        "0000056873",
        ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=(
            "us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
            "us-gaap:ComprehensiveIncomeNetOfTaxAttributableToNoncontrollingInterest",
        ),
        require_equity_reconciliation=True,
        version="FINSIGHT-REPORTED-NCI-LATEST-500-1",
    ),
    "HSIC": ReportedNciScopeRule(
        "HSIC", "0001000228",
        ("us-gaap:MinorityInterest", "us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests"),
        diagnostic_duration_local_names=(
            "ComprehensiveIncomeAttributableToNoncontrollingInterestsExcludingComprehensiveIncomeAttributableToRedeemableNoncontrollingInterests",
            "ComprehensiveIncomeNetOfTaxAttributableToRedeemableNoncontrollingInterest",
        ),
        nonclaim_instant_local_names=(
            "AccumulatedOtherComprehensiveIncomeLossForeignCurrencyTranslationAdjustmentAttributableToNonredeemableNoncontrollingInterestsNetOfTax",
            "AccumulatedOtherComprehensiveIncomeLossForeignCurrencyTranslationAdjustmentAttributableToRedeemableNoncontrollingInterestNetOfTax",
            "AccumulatedOtherComprehensiveIncomeLossNetOfTaxIncludingPortionAttributableToRedeemableAndNonredeemableNoncontrollingInterests",
        ),
        issuer_namespace_pattern=r"https?://(?:www\.)?henryschein\.com/\d{8}",
    ),
    "HUBB": ReportedNciScopeRule("HUBB", "0000048898", ("us-gaap:MinorityInterest",)),
    "HCA": ReportedNciScopeRule("HCA", "0000860730", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
            "us-gaap:ComprehensiveIncomeNetOfTaxAttributableToNoncontrollingInterest",
            "us-gaap:PaymentsToMinorityShareholders"),
        clears_legacy_claim_scope=False, require_equity_reconciliation=True, version="FINSIGHT-REPORTED-NCI-WG22-1"),
    "HON": ReportedNciScopeRule("HON", "0000773840", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
            "us-gaap:MinorityInterestDecreaseFromDistributionsToNoncontrollingInterestHolders",
            "us-gaap:NoncontrollingInterestDecreaseFromDeconsolidation"),
        clears_legacy_claim_scope=False, require_equity_reconciliation=True, version="FINSIGHT-REPORTED-NCI-WG22-1"),
    "LHX": ReportedNciScopeRule("LHX","0000202058",
        ("us-gaap:RedeemableNoncontrollingInterestEquityPreferredCarryingAmount",),
        allowed_alias_qnames=("us-gaap:TemporaryEquityCarryingAmountAttributableToParent",),
        alias_component_targets=(("us-gaap:TemporaryEquityCarryingAmountAttributableToParent",
            "us-gaap:RedeemableNoncontrollingInterestEquityPreferredCarryingAmount"),),
        alias_parent_scopes=(("us-gaap:TemporaryEquityCarryingAmountAttributableToParent",
            "us-gaap:IncreaseDecreaseInTemporaryEquityRollForward"),),
        nonclaim_instant_qnames=("us-gaap:RedeemableNoncontrollingInterestEquityPreferredRedemptionValue",),
        clears_legacy_claim_scope=False,version="FINSIGHT-REPORTED-NCI-WG26-1"),
    "MCK": ReportedNciScopeRule("MCK","0000927653",
        ("us-gaap:MinorityInterest","us-gaap:RedeemableNoncontrollingInterestEquityCommonCarryingAmount"),
        allowed_alias_qnames=("us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount",),
        alias_component_targets=(("us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount",
            "us-gaap:RedeemableNoncontrollingInterestEquityCommonCarryingAmount"),),
        alias_member_scopes=(("us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount",
            "us-gaap:StatementEquityComponentsAxis","RedeemableNoncontrollingInterestMember"),),
        alias_parent_scopes=(("us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount",
            "us-gaap:MinorityInterestLineItems"),),
        diagnostic_duration_qnames=("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",),
        issuer_namespace_pattern=r"https?://mckesson123\.com/\d{8}",
        clears_legacy_claim_scope=False,version="FINSIGHT-REPORTED-NCI-WG26-1"),
    "IQV": ReportedNciScopeRule("IQV", "0001478242", ("us-gaap:MinorityInterest",)),
    "JBL": ReportedNciScopeRule("JBL", "0000898293", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",),
        diagnostic_duration_local_names=("NoncontrollingInterestCapitalContribution",),
        issuer_namespace_pattern=r"https?://(?:www\.)?jabil\.com/\d{8}",
        clears_legacy_claim_scope=False, require_equity_reconciliation=True,
        version="FINSIGHT-REPORTED-NCI-WG23-1"),
    "INTC": ReportedNciScopeRule("INTC", "0000050863", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
            "us-gaap:MinorityInterestDecreaseFromDistributionsToNoncontrollingInterestHolders",
            "us-gaap:ProceedsFromMinorityShareholders","us-gaap:PaymentsToMinorityShareholders"),
        require_equity_reconciliation=True,
        reconciled_subset_axis_local_name="ConsolidatedEntitiesAxis",
        reconciled_subset_member_local_names=("SubsidiariesIrelandSCIPMember","SubsidiariesArizonaSCIPMember",
            "SubsidiariesMobileyeMember","SubsidiariesIMSNanofabricationGmbHIMSMember"),
        version="FINSIGHT-REPORTED-NCI-WG23-1"),
    "ICE": ReportedNciScopeRule("ICE", "0001571949", ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount")),
    "IR": ReportedNciScopeRule("IR", "0001699150", ("us-gaap:MinorityInterest",)),
    "JCI": ReportedNciScopeRule("JCI", "0000833444", ("us-gaap:MinorityInterest",)),
    "KO": ReportedNciScopeRule("KO", "0000021344", ("us-gaap:MinorityInterest",)),
    "KDP": ReportedNciScopeRule("KDP", "0001418135", ("us-gaap:MinorityInterest",)),
    "LDOS": ReportedNciScopeRule("LDOS", "0001336920", ("us-gaap:MinorityInterest",)),
    "MAS": ReportedNciScopeRule("MAS", "0000062996", ("us-gaap:MinorityInterest",)),
    "MDT": ReportedNciScopeRule(
        "MDT", "0001613103", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",),
    ),
    "MCO": ReportedNciScopeRule("MCO", "0001059556", ("us-gaap:MinorityInterest",)),
    "MRK": ReportedNciScopeRule("MRK", "0000310158", ("us-gaap:MinorityInterest",)),
    "MPC": ReportedNciScopeRule("MPC", "0001510295", ("us-gaap:MinorityInterest",)),
    "MSI": ReportedNciScopeRule("MSI", "0000068505", ("us-gaap:MinorityInterest",)),
    "NUE": ReportedNciScopeRule("NUE", "0000073309", ("us-gaap:MinorityInterest",)),
    "NXPI": ReportedNciScopeRule("NXPI", "0001413447", ("us-gaap:MinorityInterest",)),
    "OTIS": ReportedNciScopeRule("OTIS", "0001781335", ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount")),
    "ON": ReportedNciScopeRule(
        "ON", "0001097864", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",),
    ),
    "PEP": ReportedNciScopeRule("PEP", "0000077476", ("us-gaap:MinorityInterest",)),
    "PG": ReportedNciScopeRule("PG", "0000080424", ("us-gaap:MinorityInterest",)),
    "PFE": ReportedNciScopeRule(
        "PFE", "0000078003", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",),
    ),
    "PH": ReportedNciScopeRule("PH", "0000076334", ("us-gaap:MinorityInterest",)),
    "PWR": ReportedNciScopeRule("PWR", "0001050915", ("us-gaap:MinorityInterest",)),
    "ROK": ReportedNciScopeRule("ROK", "0001024478", ("us-gaap:MinorityInterest",)),
    "RSG": ReportedNciScopeRule("RSG", "0001060391", ("us-gaap:MinorityInterest",)),
    "STE": ReportedNciScopeRule("STE", "0001757898", ("us-gaap:MinorityInterest",)),
    "STLD": ReportedNciScopeRule(
        "STLD",
        "0001022671",
        ("us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount",),
        excluded_nonpositive_qnames=("us-gaap:MinorityInterest",),
    ),
    "TDG": ReportedNciScopeRule("TDG", "0001260221", ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount"), ("us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",)),
    "TEL": ReportedNciScopeRule(
        "TEL", "0001385157", ("us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount",),
        diagnostic_duration_qnames=("us-gaap:ComprehensiveIncomeNetOfTaxAttributableToNoncontrollingInterest",),
    ),
    "TER": ReportedNciScopeRule("TER", "0000097210", ("us-gaap:MinorityInterest",)),
    "TT": ReportedNciScopeRule("TT", "0001466258", ("us-gaap:MinorityInterest",)),
    "UPS": ReportedNciScopeRule("UPS", "0001090727", ("us-gaap:MinorityInterest",)),
    "VLTO": ReportedNciScopeRule("VLTO", "0001967680", ("us-gaap:MinorityInterest",)),
    "CRWD": ReportedNciScopeRule(
        "CRWD", "0001535527", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",),
    ),
    "WAB": ReportedNciScopeRule("WAB", "0000943452", ("us-gaap:MinorityInterest",)),
    "WMT": ReportedNciScopeRule(
        "WMT",
        "0000104169",
        (
            "us-gaap:MinorityInterest",
            "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount",
        ),
        diagnostic_duration_qnames=(
            "us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
            "us-gaap:ComprehensiveIncomeNetOfTaxAttributableToNoncontrollingInterest",
        ),
        version="FINSIGHT-REPORTED-NCI-LATEST-500-1",
    ),
    "WM": ReportedNciScopeRule("WM", "0000823768", ("us-gaap:MinorityInterest",)),
    "WMB": ReportedNciScopeRule("WMB", "0000107263", ("us-gaap:MinorityInterest",)),
    "ZBH": ReportedNciScopeRule(
        "ZBH", "0001136869", ("us-gaap:MinorityInterest",),
        diagnostic_duration_qnames=("us-gaap:MinorityInterestDecreaseFromDistributionsToNoncontrollingInterestHolders",),
    ),
})


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ClaimScopeReviewRequired(f"{field} is not finite numeric evidence")
    result = float(value)
    if not isfinite(result):
        raise ClaimScopeReviewRequired(f"{field} is not finite numeric evidence")
    return result


def _rule(ticker: str) -> ReportedNciScopeRule:
    if not isinstance(ticker, str) or ticker not in REPORTED_NCI_SCOPE_RULES:
        raise ClaimScopeReviewRequired(f"ticker has no immutable reported-NCI mapping: {ticker!r}")
    return REPORTED_NCI_SCOPE_RULES[ticker]


def _resolution(value: BridgeResolution | Mapping[str, Any]) -> BridgeResolution:
    if isinstance(value, BridgeResolution):
        return value
    if isinstance(value, Mapping):
        try:
            return BridgeResolution.from_dict(value)
        except (KeyError, TypeError, ValueError) as exc:
            raise ClaimScopeReviewRequired(f"normalized bridge is invalid: {exc}") from exc
    raise ClaimScopeReviewRequired("normalized bridge must be BridgeResolution or serialized BridgeResolution")


def _validated_policy(
    ticker: str,
    policy: Mapping[str, Any],
) -> ReportedNciScopeRule:
    """Require the compiled policy to match the immutable source-scope rule."""
    rule = _rule(ticker)
    if not isinstance(policy, Mapping):
        raise ClaimScopeReviewRequired("reported NCI policy is missing")
    expected = asdict(rule)
    actual = dict(policy)
    for field in ("required_qnames", "allowed_alias_qnames", "excluded_nonpositive_qnames",
                  "diagnostic_duration_qnames", "diagnostic_duration_local_names",
                  "nonclaim_instant_local_names", "nonclaim_instant_qnames",
                  "reconciled_subset_member_local_names"):
        expected[field] = tuple(expected.get(field, ()))
        actual[field] = tuple(actual.get(field, ()))
    for field in ('alias_component_targets','alias_member_scopes','alias_parent_scopes'):
        expected[field]=tuple(tuple(row) for row in expected.get(field,()))
        actual[field]=tuple(tuple(row) for row in actual.get(field,()))
    if actual != expected:
        raise ClaimScopeReviewRequired("reported NCI policy identity/version mismatch")
    if rule.negative_balance_treatment not in {
        "preserve_reported_claim",
        "diagnostic_zero_fail_if_positive",
    }:
        raise ClaimScopeReviewRequired("reported NCI negative-balance treatment is invalid")
    return rule


def _typed_explicit_alias_proof(proof,rule):
    if not rule.alias_component_targets:return proof
    rows=proof.get('alias_components',[])
    def unique(items):
        result=[]
        for item in items:
            if item not in result:result.append(item)
        return result
    proof['nonclaim_instant_diagnostics']=unique([r for r in rows if r['qname'] in rule.nonclaim_instant_qnames])
    proof['alias_components']=unique([r for r in rows if r['qname'] in rule.allowed_alias_qnames])
    return proof


def _current_duration_diagnostics(
    structural_packet: Mapping[str, Any], *, rule: ReportedNciScopeRule,
    accession: str, period_end: str,
) -> tuple[dict[str, Any], ...]:
    if not rule.diagnostic_duration_qnames and not rule.diagnostic_duration_local_names:
        return ()
    facts = structural_packet.get("facts")
    if not isinstance(facts, list):
        raise ClaimScopeReviewRequired("structural packet has no facts")
    selected = []
    targets=[("qname",qname) for qname in rule.diagnostic_duration_qnames]
    targets.extend(("local_name",name) for name in rule.diagnostic_duration_local_names)
    for field_name, target in targets:
        rows = [row for row in facts if isinstance(row, Mapping)
                and row.get(field_name) == target and row.get("source_accession") == accession
                and row.get("period_end") == period_end and isinstance(row.get("period_start"), str)
                and row.get("unit") == "USD" and row.get("entity_scheme") == "http://www.sec.gov/CIK"
                and str(row.get("entity_identifier", "")).zfill(10) == rule.cik
                and (_US_GAAP_NAMESPACE_RE.fullmatch(str(row.get("namespace", "")))
                     if field_name=="qname" else rule.issuer_namespace_pattern is not None
                     and re.fullmatch(rule.issuer_namespace_pattern,str(row.get("namespace", ""))))]
        if not rows:
            raise ClaimScopeReviewRequired(f"required current NCI duration diagnostic is missing: {target}")
        for row in rows:
            _finite(row.get("value"), f"{target} value")
            selected.append(dict(row))
    return tuple(selected)


def _current_fact_rows(
    structural_packet: Mapping[str, Any],
    *,
    rule: ReportedNciScopeRule,
    accession: str,
    period_end: str,
) -> tuple[dict[str, Any], ...]:
    facts = structural_packet.get("facts")
    if not isinstance(facts, list):
        raise ClaimScopeReviewRequired("structural packet has no facts")
    rows: dict[str, list[Mapping[str, Any]]] = {qname: [] for qname in rule.required_qnames}
    for raw in facts:
        if not isinstance(raw, Mapping):
            continue
        qname = raw.get("qname")
        if qname not in rows:
            continue
        if (
            raw.get("source_accession") != accession
            or raw.get("period_end") != period_end
            or raw.get("period_start") is not None
            or raw.get("unit") != "USD"
            or raw.get("dimensions") not in (None, [])
            or raw.get("entity_scheme") != "http://www.sec.gov/CIK"
            or str(raw.get("entity_identifier", "")).zfill(10) != rule.cik
            or not _US_GAAP_NAMESPACE_RE.fullmatch(str(raw.get("namespace", "")))
            or str(raw.get("local_name", "")) != qname.rsplit(":", 1)[-1]
        ):
            continue
        rows[qname].append(raw)
    selected: list[dict[str, Any]] = []
    for qname in rule.required_qnames:
        candidates = rows[qname]
        if not candidates:
            raise ClaimScopeReviewRequired(f"required current NCI component is missing: {qname}")
        values = {_finite(row.get("value"), f"{qname} value") for row in candidates}
        if rule.alias_component_targets and any(value<0 for value in values):
            raise ClaimScopeReviewRequired('negative ownership component cannot offset another carrying claim')
        if rule.alias_component_targets and any('balance_sheet' not in row.get('statement_roles',[]) or
            'us-gaap:LiabilitiesAndStockholdersEquityAbstract' not in row.get('presentation_parents',[]) for row in candidates):
            raise ClaimScopeReviewRequired('explicit ownership carrying presentation scope mismatch')
        if len(values) != 1:
            raise ClaimScopeReviewRequired(f"required current NCI component conflicts: {qname}")
        selected.append(dict(candidates[0]))
    return tuple(selected)


def _reject_unknown_nonzero_components(
    structural_packet: Mapping[str, Any],
    *,
    rule: ReportedNciScopeRule,
    accession: str,
    period_end: str,
    required_values: Mapping[str, float],
) -> tuple[dict[str, Any], ...]:
    facts = structural_packet.get("facts")
    assert isinstance(facts, list)
    required = set(rule.required_qnames)
    aliases = set(rule.allowed_alias_qnames)
    excluded_nonpositive = set(rule.excluded_nonpositive_qnames)
    alias_rows: list[dict[str, Any]] = []
    for raw in facts:
        if not isinstance(raw, Mapping):
            continue
        qname = str(raw.get("qname", ""))
        local = qname.rsplit(":", 1)[-1].lower()
        if not any(marker in local for marker in _NCI_LOCAL_MARKERS) and qname not in aliases:
            continue
        # This is a consolidated equity total (and may repeat the NCI member
        # in dimensional component rows), not an additional NCI claim.
        if local == "stockholdersequityincludingportionattributabletononcontrollinginterest":
            continue
        if raw.get("source_accession") != accession or raw.get("period_end") != period_end or raw.get("period_start") is not None or raw.get("unit") != "USD":
            continue
        if qname in aliases:
            if (raw.get("entity_scheme") != "http://www.sec.gov/CIK"
                or str(raw.get("entity_identifier", "")).zfill(10) != rule.cik
                or not _US_GAAP_NAMESPACE_RE.fullmatch(str(raw.get("namespace", "")))):
                raise ClaimScopeReviewRequired(f"NCI alias source identity mismatch: {qname}")
            value = _finite(raw.get("value"), f"{qname} value")
            dimensions=dict(raw.get("dimensions") or [])
            explicit_target=dict(rule.alias_component_targets).get(qname)
            if explicit_target:
                scope=[(axis,member) for name,axis,member in rule.alias_member_scopes if name==qname]
                if (scope and (len(dimensions)!=len(scope) or any(
                    str(dimensions.get(axis,'')).rsplit(':',1)[-1]!=member for axis,member in scope))) or (not scope and dimensions):
                    raise ClaimScopeReviewRequired('explicit NCI alias dimensional scope mismatch')
                if scope:
                    prefixes={str(r.get('qname','')).split(':',1)[0] for r in facts
                        if rule.issuer_namespace_pattern and re.fullmatch(rule.issuer_namespace_pattern,str(r.get('namespace','')))
                        and str(r.get('entity_identifier','')).zfill(10)==rule.cik}
                    if any(str(dimensions[axis]).split(':',1)[0] not in prefixes for axis,_ in scope):
                        raise ClaimScopeReviewRequired('explicit NCI alias namespace scope mismatch')
                parent=dict(rule.alias_parent_scopes).get(qname)
                if parent is None or parent not in raw.get('presentation_parents',[]):
                    raise ClaimScopeReviewRequired('explicit NCI alias presentation scope mismatch')
                if value!=required_values.get(explicit_target):
                    raise ClaimScopeReviewRequired('explicit NCI alias does not reconcile to its carrying component')
                alias_rows.append(dict(raw));continue
            hierarchy=dimensions.get("us-gaap:FairValueByFairValueHierarchyLevelAxis")
            if value==0.0 and hierarchy in {
                "us-gaap:FairValueInputsLevel1Member","us-gaap:FairValueInputsLevel2Member"
            }:
                alias_rows.append(dict(raw))
                continue
            target = {'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests': 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount',
                      'us-gaap:RedeemableNoncontrollingInterestEquityCommonCarryingAmount': 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount',
                      'us-gaap:RedeemableNoncontrollingInterestEquityFairValue': 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount'}.get(qname)
            if target is None or value != required_values.get(target):
                raise ClaimScopeReviewRequired(f"NCI alias does not match required component: {qname}")
            alias_rows.append(dict(raw))
            continue
        if qname in rule.nonclaim_instant_qnames:
            if (raw.get("entity_scheme") != "http://www.sec.gov/CIK"
                or str(raw.get("entity_identifier", "")).zfill(10) != rule.cik
                or not _US_GAAP_NAMESPACE_RE.fullmatch(str(raw.get("namespace", "")))):
                raise ClaimScopeReviewRequired(f"NCI nonclaim diagnostic identity mismatch: {qname}")
            _finite(raw.get("value"), f"{qname} value")
            alias_rows.append(dict(raw))
            continue
        if raw.get("dimensions") not in (None, []):
            # Dimensioned fair-value/detail rows are not the undimensioned
            # bridge component.  The required carrying component is selected
            # and validated separately above.
            continue
        value = _finite(raw.get("value"), f"{qname} value")
        if raw.get("local_name") in rule.nonclaim_instant_local_names:
            if (rule.issuer_namespace_pattern is None
                or not re.fullmatch(rule.issuer_namespace_pattern,str(raw.get("namespace", "")))
                or raw.get("entity_scheme") != "http://www.sec.gov/CIK"
                or str(raw.get("entity_identifier", "")).zfill(10) != rule.cik):
                raise ClaimScopeReviewRequired("NCI nonclaim diagnostic identity mismatch")
            alias_rows.append(dict(raw))
            continue
        if qname in excluded_nonpositive:
            if value > 0.0:
                raise ClaimScopeReviewRequired(
                    f"excluded NCI component became a positive outside-owner claim: {qname}"
                )
            alias_rows.append(dict(raw))
            continue
        if value != 0.0 and qname not in required:
            raise ClaimScopeReviewRequired(f"unknown nonzero current NCI component: {qname}")
    return tuple(alias_rows)


def _ordinary_equity_reconciliation(structural_packet, *, rule, accession, period_end, total):
    if not rule.require_equity_reconciliation:
        return None
    if total<0:
        raise ClaimScopeReviewRequired('ordinary NCI became negative and needs an explicit non-inversion rule')
    rows=[row for row in structural_packet['facts'] if isinstance(row,Mapping)
          and row.get('source_accession')==accession and row.get('period_end')==period_end
          and row.get('period_start') is None and row.get('unit')=='USD'
          and row.get('entity_scheme')=='http://www.sec.gov/CIK'
          and str(row.get('entity_identifier','')).zfill(10)==rule.cik
          and _US_GAAP_NAMESPACE_RE.fullmatch(str(row.get('namespace','')))]
    combined='us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'
    def one(qname,dimensions):
        selected=[row for row in rows if row.get('qname')==qname
                  and dict(row.get('dimensions') or [])==dimensions]
        values={_finite(row['value'],qname) for row in selected}
        if len(values)!=1:raise ClaimScopeReviewRequired('ordinary NCI equity reconciliation is missing or conflicting')
        return values.pop()
    consolidated=one(combined,{})
    parent=one('us-gaap:StockholdersEquity',{})
    member=one(combined,{'us-gaap:StatementEquityComponentsAxis':'us-gaap:NoncontrollingInterestMember'})
    if not (isclose(consolidated-parent,total,rel_tol=1e-12,abs_tol=.01)
            and isclose(member,total,rel_tol=1e-12,abs_tol=.01)):
        raise ClaimScopeReviewRequired('ordinary NCI does not reconcile to consolidated-minus-parent equity and equity member')
    proof={'consolidated_equity':consolidated,'parent_equity':parent,'nci_equity_member':member,
            'formula':'consolidated equity minus parent equity equals current ordinary NCI equals NCI equity member'}
    if rule.reconciled_subset_axis_local_name:
        parts={}
        for row in rows:
            if row.get('qname') not in rule.required_qnames or not row.get('dimensions'):continue
            dims=row['dimensions']
            if len(dims)!=1 or str(dims[0][0]).rsplit(':',1)[-1]!=rule.reconciled_subset_axis_local_name:
                raise ClaimScopeReviewRequired('ordinary NCI subset structure is unfamiliar')
            name=str(dims[0][1]).rsplit(':',1)[-1]
            if name not in rule.reconciled_subset_member_local_names:
                raise ClaimScopeReviewRequired('ordinary NCI subset member is unfamiliar')
            value=_finite(row['value'],'ordinary NCI subset')
            if value<0:raise ClaimScopeReviewRequired('negative ordinary NCI subset needs review')
            if name in parts and parts[name]!=value:
                raise ClaimScopeReviewRequired('ordinary NCI subset conflicts')
            parts[name]=value
        if (set(parts)!=set(rule.reconciled_subset_member_local_names)
            or not isclose(sum(parts.values()),total,rel_tol=1e-12,abs_tol=.01)):
            raise ClaimScopeReviewRequired('ordinary NCI subsets do not reconcile to issuer total')
        proof['nonadditive_subsets']=parts
    return proof


def validate_reported_nci_scope(
    *,
    ticker: str,
    structural_packet: Mapping[str, Any],
    normalized_bridge: BridgeResolution | Mapping[str, Any],
    accession: str,
    period_end: str,
) -> dict[str, Any]:
    """Validate one current reported-NCI mapping against the official bridge.

    This function never builds or replaces a bridge.  It checks that the
    current structural facts named by the immutable ticker rule reconcile to
    the already-normalized ``BridgeResolution.noncontrolling_interests``.
    """
    rule = _rule(ticker)
    if not isinstance(structural_packet, Mapping):
        raise ClaimScopeReviewRequired("structural packet is missing")
    if structural_packet.get("source_accession") != accession:
        raise ClaimScopeReviewRequired("structural packet accession mismatch")
    packet_period = structural_packet.get("report_date") or structural_packet.get("period_end")
    if packet_period != period_end:
        raise ClaimScopeReviewRequired("structural packet report period mismatch")
    rows = _current_fact_rows(structural_packet, rule=rule, accession=accession, period_end=period_end)
    source_total = sum(_finite(row["value"], f"{row['qname']} value") for row in rows)
    equity_proof=_ordinary_equity_reconciliation(structural_packet,rule=rule,accession=accession,
        period_end=period_end,total=source_total)
    alias_rows = _reject_unknown_nonzero_components(
        structural_packet,
        rule=rule,
        accession=accession,
        period_end=period_end,
        required_values={row['qname']:_finite(row["value"], f"{row['qname']} value") for row in rows},
    )
    duration_rows = _current_duration_diagnostics(
        structural_packet, rule=rule, accession=accession, period_end=period_end)
    bridge = _resolution(normalized_bridge)
    nci = bridge.noncontrolling_interests
    if not isinstance(nci, BridgeRange) or not (nci.low == nci.midpoint == nci.high):
        raise ClaimScopeReviewRequired("normalized bridge NCI is not an exact point")
    normalized_total = _finite(nci.midpoint, "normalized bridge NCI")
    if not isclose(source_total, normalized_total, rel_tol=1e-12, abs_tol=1e-6):
        raise ClaimScopeReviewRequired(
            f"source NCI total {source_total:g} does not reconcile to normalized bridge {normalized_total:g}"
        )
    proof = {
        "status": "verified",
        "mapping_version": rule.version,
        "ticker": rule.ticker,
        "cik": rule.cik,
        "accession": accession,
        "period_end": period_end,
        "required_qnames": list(rule.required_qnames),
        "source_total": source_total,
        "equity_reconciliation":equity_proof,
        "normalized_bridge_nci": normalized_total,
        "valuation_nci": (
            0.0
            if rule.negative_balance_treatment == "diagnostic_zero_fail_if_positive"
            and source_total <= 0.0
            else source_total
        ),
        "components": [
            {
                "qname": row["qname"],
                "value": float(row["value"]),
                "unit": row["unit"],
                "period_end": row["period_end"],
                "accession": row["source_accession"],
                "context_id": row.get("context_id"),
            }
            for row in rows
        ],
        "alias_components": [
            {
                "qname": row["qname"],
                "value": float(row["value"]),
                "unit": row["unit"],
                "period_end": row["period_end"],
                "accession": row["source_accession"],
                "context_id": row.get("context_id"),
            }
            for row in alias_rows
        ],
        "duration_diagnostics": [
            {"qname":row["qname"],"value":float(row["value"]),
             "period_start":row["period_start"],"period_end":row["period_end"],
             "context_id":row.get("context_id"),"dimensions":row.get("dimensions") or []}
            for row in duration_rows
        ],
        "trace": {
            "formula": "sum(required current undimensioned USD NCI components)",
            "unknown_nonzero_component_policy": "reject",
            "nonpositive_component_policy": "retain as diagnostic; never invert into common equity value",
            "bridge_policy_version": bridge.policy_version,
        },
    }
    return _typed_explicit_alias_proof(proof,rule)


def project_reported_nci_scope(
    *,
    ticker: str,
    policy: Mapping[str, Any],
    normalized_bridge: BridgeResolution | Mapping[str, Any],
    proof: Mapping[str, Any],
) -> BridgeResolution:
    """Apply an explicitly governed nonpositive-NCI treatment after proof.

    A negative ordinary NCI book balance is retained in the source ledger but
    cannot become an asset for common shareholders. A later positive balance
    fails closed so this rule cannot silently erase a real outside-owner claim.
    """
    rule = _validated_policy(ticker, policy)
    bridge = _resolution(normalized_bridge)
    if rule.negative_balance_treatment == "preserve_reported_claim":
        return bridge
    source_total = _finite(proof.get("source_total"), "reported NCI source total")
    if source_total > 0.0:
        raise ClaimScopeReviewRequired(
            "negative-NCI diagnostic became a positive outside-owner claim"
        )
    if not (
        bridge.noncontrolling_interests.low
        == bridge.noncontrolling_interests.midpoint
        == bridge.noncontrolling_interests.high
        == source_total
    ):
        raise ClaimScopeReviewRequired(
            "negative-NCI diagnostic does not reconcile before projection"
        )
    zero = BridgeRange(0.0, 0.0, 0.0)
    adjustment = BridgeRange(
        bridge.cash_and_investments.low
        - bridge.total_debt.high
        - bridge.preferred_equity.high,
        bridge.cash_and_investments.midpoint
        - bridge.total_debt.midpoint
        - bridge.preferred_equity.midpoint,
        bridge.cash_and_investments.high
        - bridge.total_debt.low
        - bridge.preferred_equity.low,
    )
    return replace(
        bridge,
        noncontrolling_interests=zero,
        bridge_adjustment=adjustment,
        reason_codes=tuple(
            sorted(
                set(bridge.reason_codes)
                | {"NEGATIVE_NCI_RETAINED_AS_DIAGNOSTIC_NOT_COMMON_ASSET"}
            )
        ),
    )


def reported_nci_field_availability(
    *,
    ticker: str,
    policy: Mapping[str, Any],
    structural_packet: Mapping[str, Any],
    accession: str,
    period_end: str,
) -> tuple[FieldAvailability, dict[str, Any]]:
    """Bind a verified current reported-NCI point before bridge resolution.

    The generic bridge cannot infer that an issuer's legacy non-debt claim is
    specifically NCI.  This adapter validates the immutable semantic mapping
    and the current filing facts first, then supplies that exact point to the
    ordinary bridge resolver.  It does not infer a zero or alter another claim.
    """
    rule = _validated_policy(ticker, policy)
    if not isinstance(structural_packet, Mapping):
        raise ClaimScopeReviewRequired("structural packet is missing")
    if structural_packet.get("source_accession") != accession:
        raise ClaimScopeReviewRequired("structural packet accession mismatch")
    packet_period = structural_packet.get("report_date") or structural_packet.get("period_end")
    if packet_period != period_end:
        raise ClaimScopeReviewRequired("structural packet report period mismatch")
    rows = _current_fact_rows(
        structural_packet,
        rule=rule,
        accession=accession,
        period_end=period_end,
    )
    required_values = {
        row["qname"]: _finite(row["value"], f"{row['qname']} value")
        for row in rows
    }
    alias_rows = _reject_unknown_nonzero_components(
        structural_packet,
        rule=rule,
        accession=accession,
        period_end=period_end,
        required_values=required_values,
    )
    duration_rows = _current_duration_diagnostics(
        structural_packet, rule=rule, accession=accession, period_end=period_end)
    source_total = sum(required_values.values())
    equity_proof=_ordinary_equity_reconciliation(structural_packet,rule=rule,accession=accession,
        period_end=period_end,total=source_total)
    availability = FieldAvailability(
        field="noncontrolling_interests",
        value=source_total,
        state="reported",
        reason_code="REPORTED_NCI_SCOPE_VERIFIED",
        period_end=period_end,
        source_accession=accession,
        source_kind="structural_xbrl",
        evidence_class="reported_component_reconciliation",
        freshness="current",
        fallback_level="current_structural",
        extraction_complete=True,
        searched_concepts=tuple((*rule.required_qnames, *rule.allowed_alias_qnames,
                                 *rule.excluded_nonpositive_qnames, *rule.diagnostic_duration_qnames,
                                 *rule.diagnostic_duration_local_names, *rule.nonclaim_instant_local_names,
                                 *rule.nonclaim_instant_qnames)),
        authority="production",
        mapping_version=rule.version,
    )
    proof = {
        "status": "source_bound",
        "mapping_version": rule.version,
        "ticker": rule.ticker,
        "cik": rule.cik,
        "accession": accession,
        "period_end": period_end,
        "source_total": source_total,
        "equity_reconciliation":equity_proof,
        "required_qnames": list(rule.required_qnames),
        "components": [
            {
                "qname": row["qname"],
                "value": float(row["value"]),
                "context_id": row.get("context_id"),
            }
            for row in rows
        ],
        "alias_components": [
            {
                "qname": row["qname"],
                "value": float(row["value"]),
                "context_id": row.get("context_id"),
            }
            for row in alias_rows
        ],
        "duration_diagnostics": [
            {"qname":row["qname"],"value":float(row["value"]),
             "period_start":row["period_start"],"period_end":row["period_end"],"context_id":row.get("context_id"),
             "dimensions":row.get("dimensions") or []}
            for row in duration_rows
        ],
    }
    return availability, _typed_explicit_alias_proof(proof,rule)


__all__ = [
    "CLAIM_SCOPE_MAPPING_VERSION",
    "ClaimScopeReviewRequired",
    "REPORTED_NCI_SCOPE_RULES",
    "ReportedNciScopeRule",
    "reported_nci_field_availability",
    "project_reported_nci_scope",
    "validate_reported_nci_scope",
]
