"""Current preferred/temporary-equity lifecycle scopes for ordinary FCFF.

The rules contain semantic selectors only.  Filing identities, dates and
amounts come from the current structural packet and fail closed on change.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
from numbers import Real
from types import MappingProxyType
from typing import Any, Mapping

from .field_availability import FieldAvailability


SCHEMA = "FINSIGHT-PREFERRED-LIFECYCLE-1"
VERSION = "FINSIGHT-PREFERRED-LIFECYCLE-WG12-1"

RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "ABT": MappingProxyType({
        "schema_version": SCHEMA, "version": VERSION, "ticker": "ABT", "cik": "0000001800",
        "mode": "reported_zero",
        "current_carrying_local_name": "PreferredStockValue",
        "current_shares_local_name": "PreferredStockSharesIssued",
        "treatment": "current preferred equity is zero only when both reported carrying value and issued shares are zero; authorized shares and par value are diagnostics, not claims",
    }),
    "COHR": MappingProxyType({
        "schema_version": SCHEMA, "version": VERSION, "ticker": "COHR", "cik": "0000820318",
        "mode": "settled_conversion_zero",
        "current_carrying_local_name": "TemporaryEquityCarryingAmountAttributableToParent",
        "current_redemption_local_name": "TemporaryEquityRedemptionValue",
        "current_shares_local_name": "TemporaryEquitySharesOutstanding",
        "current_issued_local_name": "TemporaryEquitySharesIssued",
        "conversion_shares_local_name": "TemporaryEquityStockIssuedDuringPeriodSharesConversionOfConvertibleSecurities",
        "conversion_value_local_name": "TemporaryEquityStockIssuedDuringPeriodValueConversionOfConvertibleSecurities",
        "common_conversion_effect_local_name": "IncrementalCommonSharesAttributableToConversionOfPreferredStock",
        "treatment": "current preferred claim is zero only after current carrying, redemption and share balances are zero and the same filing reports the completed conversion roll-forward; historical terms are not carried forward",
    }),
    "WMB": MappingProxyType({
        "schema_version": SCHEMA, "version": VERSION, "ticker": "WMB", "cik": "0000107263",
        "mode": "current_carrying_claim",
        "current_carrying_local_name": "PreferredStockValue",
        "current_shares_local_name": "PreferredStockSharesIssued",
        "par_per_share_local_name": "PreferredStockParOrStatedValuePerShare",
        "equity_total_local_name": "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "equity_member": "us-gaap:PreferredStockMember",
        "treatment": "use the current issuer carrying claim once; par value and authorized/share counts are diagnostics, and NCI remains separate",
    }),
})


class PreferredLifecycleReviewRequired(ValueError):
    pass


def preferred_lifecycle_policy(ticker: str) -> dict[str, Any]:
    rule = RULES.get(ticker.upper())
    if rule is None:
        raise ValueError(f"no preferred lifecycle policy for {ticker!r}")
    return deepcopy(dict(rule))


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value)):
        raise PreferredLifecycleReviewRequired(f"{label} is not finite numeric evidence")
    return float(value)


def _current_rows(structural: Mapping[str, Any], *, policy: Mapping[str, Any], accession: str, period: str) -> list[dict[str, Any]]:
    if structural.get("source_accession") != accession or (structural.get("report_date") or structural.get("period_end")) != period:
        raise PreferredLifecycleReviewRequired("preferred lifecycle structural identity mismatch")
    rows = [dict(row) for row in structural.get("facts", []) if isinstance(row, Mapping)
            and row.get("source_accession") == accession and row.get("period_end") == period
            and row.get("entity_scheme") == "http://www.sec.gov/CIK"
            and str(row.get("entity_identifier", "")).zfill(10) == policy["cik"]]
    if not rows:
        raise PreferredLifecycleReviewRequired("preferred lifecycle current filing facts are missing")
    return rows


def _one(rows: list[dict[str, Any]], local_name: str, *, unit: str, instant: bool,
         undimensioned: bool | None = True, member: str | None = None) -> dict[str, Any]:
    selected = []
    for row in rows:
        if row.get("local_name") != local_name or row.get("unit") != unit:
            continue
        if instant != (row.get("period_start") is None):
            continue
        dimensions = row.get("dimensions") or []
        if undimensioned is True and dimensions:
            continue
        if undimensioned is False and not dimensions:
            continue
        if member is not None and not any(isinstance(pair, (list, tuple)) and len(pair) == 2 and pair[1] == member for pair in dimensions):
            continue
        _number(row.get("value"), local_name)
        selected.append(row)
    values = {_number(row["value"], local_name) for row in selected}
    if not selected or len(values) != 1:
        raise PreferredLifecycleReviewRequired(f"preferred lifecycle fact is missing or conflicting: {local_name}")
    return selected[0]


def bind_preferred_lifecycle(*, ticker: str, policy: Mapping[str, Any], structural: Mapping[str, Any],
                             accession: str, period: str) -> tuple[FieldAvailability, dict[str, Any]]:
    expected = RULES.get(ticker)
    if expected is None or dict(policy) != dict(expected):
        raise PreferredLifecycleReviewRequired("preferred lifecycle policy identity/version mismatch")
    rows = _current_rows(structural, policy=policy, accession=accession, period=period)
    sources: list[dict[str, Any]] = []
    if policy["mode"] == "reported_zero":
        carrying = _one(rows, policy["current_carrying_local_name"], unit="USD", instant=True)
        issued = _one(rows, policy["current_shares_local_name"], unit="xbrli:shares", instant=True)
        if _number(carrying["value"], "current preferred carrying value") != 0 or _number(issued["value"], "current preferred issued shares") != 0:
            raise PreferredLifecycleReviewRequired("reported-zero preferred instrument became a current claim")
        value, state, reason = 0.0, "explicit_zero", "CURRENT_PREFERRED_CARRYING_AND_ISSUED_SHARES_ZERO"
        sources = [carrying, issued]
        components = {"current_carrying_value":0.0,"current_shares_issued":0.0,
            "authorized_or_par_disclosures_are_not_claims":True}
    elif policy["mode"] == "settled_conversion_zero":
        carrying = _one(rows, policy["current_carrying_local_name"], unit="USD", instant=True)
        redemption = _one(rows, policy["current_redemption_local_name"], unit="USD", instant=True)
        outstanding = _one(rows, policy["current_shares_local_name"], unit="xbrli:shares", instant=True)
        issued = _one(rows, policy["current_issued_local_name"], unit="xbrli:shares", instant=True)
        converted = _one(rows, policy["conversion_shares_local_name"], unit="xbrli:shares", instant=False)
        conversion_value = _one(rows, policy["conversion_value_local_name"], unit="USD", instant=False)
        common_effect = _one(rows, policy["common_conversion_effect_local_name"], unit="xbrli:shares", instant=False)
        if any(_number(row["value"], "current settled balance") != 0 for row in (carrying, redemption, outstanding, issued)):
            raise PreferredLifecycleReviewRequired("settled preferred instrument has a nonzero current balance")
        if _number(converted["value"], "converted preferred shares") <= 0 or _number(conversion_value["value"], "converted preferred value") >= 0:
            raise PreferredLifecycleReviewRequired("preferred conversion roll-forward is missing its outflow")
        if _number(common_effect["value"], "common conversion effect") <= _number(converted["value"], "converted preferred shares"):
            raise PreferredLifecycleReviewRequired("preferred conversion did not produce a positive common-share effect")
        value, state, reason = 0.0, "evidence_backed_zero", "PREFERRED_CONVERSION_SETTLED_CURRENT_BALANCES_ZERO"
        sources = [carrying, redemption, outstanding, issued, converted, conversion_value, common_effect]
        components = {
            "current_carrying_value": 0.0, "current_redemption_value": 0.0,
            "current_shares_outstanding": 0.0, "current_shares_issued": 0.0,
            "converted_preferred_shares": float(converted["value"]),
            "converted_preferred_value": float(conversion_value["value"]),
            "common_share_conversion_effect": float(common_effect["value"]),
        }
    elif policy["mode"] == "current_carrying_claim":
        carrying = _one(rows, policy["current_carrying_local_name"], unit="USD", instant=True)
        shares = _one(rows, policy["current_shares_local_name"], unit="xbrli:shares", instant=True, undimensioned=False)
        par = _one(rows, policy["par_per_share_local_name"], unit="USD", instant=True, undimensioned=False)
        component = _one(rows, policy["equity_total_local_name"], unit="USD", instant=True,
                         undimensioned=False, member=policy["equity_member"])
        value = _number(carrying["value"], "preferred carrying claim")
        if value <= 0 or _number(shares["value"], "preferred shares") <= 0 or _number(par["value"], "preferred par") < 0:
            raise PreferredLifecycleReviewRequired("current preferred carrying evidence is invalid")
        if _number(component["value"], "preferred equity component") != value:
            raise PreferredLifecycleReviewRequired("preferred carrying claim conflicts with equity roll-forward")
        state, reason = "reported", "CURRENT_PREFERRED_CARRYING_CLAIM_RECONCILED"
        sources = [carrying, shares, par, component]
        components = {
            "current_carrying_value": value, "current_shares_issued": float(shares["value"]),
            "par_value_per_share": float(par["value"]), "equity_component": float(component["value"]),
            "par_is_not_claim_measure": True,
        }
    else:
        raise PreferredLifecycleReviewRequired("unsupported preferred lifecycle mode")
    refs = tuple(f"{accession}|{period}|{row['qname']}|{row['context_id']}" for row in sources)
    availability = FieldAvailability(
        field="preferred_equity", value=value, state=state, reason_code=reason,
        period_end=period, source_accession=accession, source_kind="structural_xbrl",
        evidence_class="reported_component_reconciliation", freshness="current",
        fallback_level="current_structural", covered_fields=("preferred_equity",),
        coverage_basis="reconciled_disjoint_components", coverage_source_facts=refs,
        economic_scope="current issuer preferred or temporary-equity claim after lifecycle reconciliation",
        extraction_complete=True, searched_concepts=tuple(sorted({row["qname"] for row in sources})),
        authority="production", mapping_version=VERSION,
    )
    return availability, {
        "status": "source_bound", "schema_version": SCHEMA, "policy_version": VERSION,
        "ticker": ticker, "cik": policy["cik"], "accession": accession, "period_end": period,
        "mode": policy["mode"], "preferred_equity": value, "components": components,
        "sources": sources, "treatment": policy["treatment"],
    }


__all__ = ["PreferredLifecycleReviewRequired", "RULES", "SCHEMA", "VERSION",
           "bind_preferred_lifecycle", "preferred_lifecycle_policy"]
