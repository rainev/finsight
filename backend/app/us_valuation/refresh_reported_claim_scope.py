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
    negative_balance_treatment: str = "preserve_reported_claim"
    clears_legacy_claim_scope: bool = True
    version: str = CLAIM_SCOPE_MAPPING_VERSION


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
    "CARR": ReportedNciScopeRule("CARR", "0001783180", ("us-gaap:MinorityInterest",)),
    "CAH": ReportedNciScopeRule("CAH", "0000721371", ("us-gaap:MinorityInterest",)),
    "CF": ReportedNciScopeRule("CF", "0001324404", ("us-gaap:MinorityInterest",)),
    "CMI": ReportedNciScopeRule("CMI", "0000026172", ("us-gaap:MinorityInterest",)),
    "CPRT": ReportedNciScopeRule("CPRT", "0000900075", ("us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount",)),
    "COO": ReportedNciScopeRule("COO", "0000711404", ("us-gaap:MinorityInterest",)),
    "COHR": ReportedNciScopeRule("COHR", "0000820318", ("us-gaap:MinorityInterest",)),
    "CSX": ReportedNciScopeRule("CSX", "0000277948", ("us-gaap:MinorityInterest",)),
    "DD": ReportedNciScopeRule("DD", "0001666700", ("us-gaap:MinorityInterest",)),
    "DASH": ReportedNciScopeRule("DASH", "0001792789", ("us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",)),
    "EME": ReportedNciScopeRule("EME", "0000105634", ("us-gaap:MinorityInterest",)),
    "EMR": ReportedNciScopeRule("EMR", "0000032604", ("us-gaap:MinorityInterest",)),
    "EXPD": ReportedNciScopeRule("EXPD", "0000746515", ("us-gaap:MinorityInterest",)),
    "FIS": ReportedNciScopeRule("FIS", "0001136893", ("us-gaap:MinorityInterest",)),
    "FTV": ReportedNciScopeRule("FTV", "0001659166", ("us-gaap:MinorityInterest",)),
    "GEV": ReportedNciScopeRule("GEV", "0001996810", ("us-gaap:MinorityInterest",)),
    "GNRC": ReportedNciScopeRule("GNRC", "0001474735", ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount")),
    "GWW": ReportedNciScopeRule("GWW", "0000277135", ("us-gaap:MinorityInterest",)),
    "HLT": ReportedNciScopeRule("HLT", "0001585689", ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount"), ("us-gaap:RedeemableNoncontrollingInterestEquityCommonCarryingAmount",)),
    "HRL": ReportedNciScopeRule("HRL", "0000048465", ("us-gaap:MinorityInterest",)),
    "HUBB": ReportedNciScopeRule("HUBB", "0000048898", ("us-gaap:MinorityInterest",)),
    "IQV": ReportedNciScopeRule("IQV", "0001478242", ("us-gaap:MinorityInterest",)),
    "ICE": ReportedNciScopeRule("ICE", "0001571949", ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount")),
    "IR": ReportedNciScopeRule("IR", "0001699150", ("us-gaap:MinorityInterest",)),
    "JCI": ReportedNciScopeRule("JCI", "0000833444", ("us-gaap:MinorityInterest",)),
    "KO": ReportedNciScopeRule("KO", "0000021344", ("us-gaap:MinorityInterest",)),
    "KDP": ReportedNciScopeRule("KDP", "0001418135", ("us-gaap:MinorityInterest",)),
    "LDOS": ReportedNciScopeRule("LDOS", "0001336920", ("us-gaap:MinorityInterest",)),
    "MAS": ReportedNciScopeRule("MAS", "0000062996", ("us-gaap:MinorityInterest",)),
    "MCO": ReportedNciScopeRule("MCO", "0001059556", ("us-gaap:MinorityInterest",)),
    "MRK": ReportedNciScopeRule("MRK", "0000310158", ("us-gaap:MinorityInterest",)),
    "MPC": ReportedNciScopeRule("MPC", "0001510295", ("us-gaap:MinorityInterest",)),
    "MSI": ReportedNciScopeRule("MSI", "0000068505", ("us-gaap:MinorityInterest",)),
    "NUE": ReportedNciScopeRule("NUE", "0000073309", ("us-gaap:MinorityInterest",)),
    "NXPI": ReportedNciScopeRule("NXPI", "0001413447", ("us-gaap:MinorityInterest",)),
    "OTIS": ReportedNciScopeRule("OTIS", "0001781335", ("us-gaap:MinorityInterest", "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount")),
    "PEP": ReportedNciScopeRule("PEP", "0000077476", ("us-gaap:MinorityInterest",)),
    "PG": ReportedNciScopeRule("PG", "0000080424", ("us-gaap:MinorityInterest",)),
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
    "TER": ReportedNciScopeRule("TER", "0000097210", ("us-gaap:MinorityInterest",)),
    "TT": ReportedNciScopeRule("TT", "0001466258", ("us-gaap:MinorityInterest",)),
    "UPS": ReportedNciScopeRule("UPS", "0001090727", ("us-gaap:MinorityInterest",)),
    "VLTO": ReportedNciScopeRule("VLTO", "0001967680", ("us-gaap:MinorityInterest",)),
    "WAB": ReportedNciScopeRule("WAB", "0000943452", ("us-gaap:MinorityInterest",)),
    "WM": ReportedNciScopeRule("WM", "0000823768", ("us-gaap:MinorityInterest",)),
    "WMB": ReportedNciScopeRule("WMB", "0000107263", ("us-gaap:MinorityInterest",)),
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
    for field in ("required_qnames", "allowed_alias_qnames", "excluded_nonpositive_qnames"):
        expected[field] = tuple(expected.get(field, ()))
        actual[field] = tuple(actual.get(field, ()))
    if actual != expected:
        raise ClaimScopeReviewRequired("reported NCI policy identity/version mismatch")
    if rule.negative_balance_treatment not in {
        "preserve_reported_claim",
        "diagnostic_zero_fail_if_positive",
    }:
        raise ClaimScopeReviewRequired("reported NCI negative-balance treatment is invalid")
    return rule


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
        if not any(marker in local for marker in _NCI_LOCAL_MARKERS):
            continue
        # This is a consolidated equity total (and may repeat the NCI member
        # in dimensional component rows), not an additional NCI claim.
        if local == "stockholdersequityincludingportionattributabletononcontrollinginterest":
            continue
        if raw.get("source_accession") != accession or raw.get("period_end") != period_end or raw.get("period_start") is not None or raw.get("unit") != "USD":
            continue
        if raw.get("dimensions") not in (None, []):
            # Dimensioned fair-value/detail rows are not the undimensioned
            # bridge component.  The required carrying component is selected
            # and validated separately above.
            continue
        value = _finite(raw.get("value"), f"{qname} value")
        if qname in excluded_nonpositive:
            if value > 0.0:
                raise ClaimScopeReviewRequired(
                    f"excluded NCI component became a positive outside-owner claim: {qname}"
                )
            alias_rows.append(dict(raw))
            continue
        if value != 0.0 and qname in aliases:
            target = {'us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests': 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount',
                      'us-gaap:RedeemableNoncontrollingInterestEquityCommonCarryingAmount': 'us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount'}.get(qname)
            if target is None or value != required_values.get(target):
                raise ClaimScopeReviewRequired(f"NCI alias does not match required component: {qname}")
            alias_rows.append(dict(raw))
            continue
        if value != 0.0 and qname not in required:
            raise ClaimScopeReviewRequired(f"unknown nonzero current NCI component: {qname}")
    return tuple(alias_rows)


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
    alias_rows = _reject_unknown_nonzero_components(
        structural_packet,
        rule=rule,
        accession=accession,
        period_end=period_end,
        required_values={row['qname']:_finite(row["value"], f"{row['qname']} value") for row in rows},
    )
    bridge = _resolution(normalized_bridge)
    nci = bridge.noncontrolling_interests
    if not isinstance(nci, BridgeRange) or not (nci.low == nci.midpoint == nci.high):
        raise ClaimScopeReviewRequired("normalized bridge NCI is not an exact point")
    normalized_total = _finite(nci.midpoint, "normalized bridge NCI")
    if not isclose(source_total, normalized_total, rel_tol=1e-12, abs_tol=1e-6):
        raise ClaimScopeReviewRequired(
            f"source NCI total {source_total:g} does not reconcile to normalized bridge {normalized_total:g}"
        )
    return {
        "status": "verified",
        "mapping_version": rule.version,
        "ticker": rule.ticker,
        "cik": rule.cik,
        "accession": accession,
        "period_end": period_end,
        "required_qnames": list(rule.required_qnames),
        "source_total": source_total,
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
        "trace": {
            "formula": "sum(required current undimensioned USD NCI components)",
            "unknown_nonzero_component_policy": "reject",
            "nonpositive_component_policy": "retain as diagnostic; never invert into common equity value",
            "bridge_policy_version": bridge.policy_version,
        },
    }


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
    source_total = sum(required_values.values())
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
        searched_concepts=tuple((*rule.required_qnames, *rule.allowed_alias_qnames, *rule.excluded_nonpositive_qnames)),
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
    }
    return availability, proof


__all__ = [
    "CLAIM_SCOPE_MAPPING_VERSION",
    "ClaimScopeReviewRequired",
    "REPORTED_NCI_SCOPE_RULES",
    "ReportedNciScopeRule",
    "reported_nci_field_availability",
    "project_reported_nci_scope",
    "validate_reported_nci_scope",
]
