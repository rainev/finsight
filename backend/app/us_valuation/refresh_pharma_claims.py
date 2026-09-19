"""Source-bound pharmaceutical acquisition claims for WG38.

The selector deliberately keeps recognized carrying liabilities, contractual
ceilings/CVRs, and acquisition cash on separate ledgers.  Company rules name
economic presentation roles and filing members; they never embed amounts or
filing dates.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import isfinite
import json
import re
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA = "FINSIGHT-PHARMA-ACQUISITION-CLAIM-1"
VERSION = "FINSIGHT-PHARMA-ACQUISITION-CLAIM-WG38-1"
BC = "us-gaap:BusinessCombinationContingentConsiderationLiability"
LEVEL_AXIS = "us-gaap:FairValueByFairValueHierarchyLevelAxis"
LEVEL_3 = "us-gaap:FairValueInputsLevel3Member"
FREQUENCY_AXIS = "us-gaap:FairValueByMeasurementFrequencyAxis"
RECURRING = "us-gaap:FairValueMeasurementsRecurringMember"
ACQUISITION_AXIS = "us-gaap:BusinessAcquisitionAxis"
ASSET_AXIS = "us-gaap:AssetAcquisitionAxis"


CLAIM_RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "BIIB": {
        "schema_version": SCHEMA, "version": VERSION, "ticker": "BIIB", "cik": "0000875045",
        "layout": "aggregate_with_narrower_rollforward",
        "carrying_qname": BC + "Noncurrent", "narrower_qname": BC,
        "purchase_qname": "us-gaap:FairValueMeasurementWithUnobservableInputsReconciliationRecurringBasisLiabilityPurchases",
        "purchase_member_local_name": "ApellisPharmaceuticalsInc.Member",
        "legal_qname": "us-gaap:LossContingencyDamagesSoughtValue",
        "legal_member_local_name": "GenentechMember",
        "treatment": "The undimensioned current carrying total controls. Its Level-3 duplicate and narrower HI-Bio balance plus the Apellis purchase reconcile but never add to the total; the Genentech judgment remains a separate legal carrying-scope review.",
    },
    "GILD": {
        "schema_version": SCHEMA, "version": VERSION, "ticker": "GILD", "cik": "0000882095",
        "layout": "business_and_asset_claims",
        "issuer_namespace_pattern": r"https?://(?:www\.)?gilead\.com/\d{8}",
        "business_qname": BC, "business_member_local_name": "MYRGmbHMember",
        "asset_qname": "us-gaap:AssetAcquisitionContingentConsiderationLiability",
        "asset_member_local_name": "OuroMedicinesLLCMember",
        "asset_maximum_local_name": "AssetAcquisitionConsiderationTransferredContingentConsiderationRangeOfOutcomesMaximumAmount",
        "cvr_local_name": "AssetAcquisitionContingentValueRightAmount",
        "cash_local_names": ("PaymentsForAssetAcquisitions", "PaymentsToAcquireBusinessesNetOfCashAcquired"),
        "settlement_qname": "us-gaap:FairValueMeasurementWithUnobservableInputsReconciliationRecurringBasisLiabilitySettlements",
        "royalty_qname": "us-gaap:AccruedRoyaltiesCurrentAndNoncurrent",
        "royalty_member_local_name": "ImmunomedicsIncMember",
        "royalty_debt_qname": "us-gaap:LongTermDebt",
        "royalty_debt_axis": "us-gaap:LongtermDebtTypeAxis",
        "royalty_debt_member": "us-gaap:NotesPayableOtherPayablesMember",
        "debt_total_qname": "us-gaap:LongTermDebt",
        "treatment": "Add the distinct current MYR and Ouro carrying liabilities once. Level-3, rollforward and typed-location views corroborate; CVRs, milestone ceilings, paid acquisition cash and settlements remain non-additive.",
    },
    "INCY": {
        "schema_version": SCHEMA, "version": VERSION, "ticker": "INCY", "cik": "0000879169",
        "layout": "recurring_with_post_period_asset_purchase",
        "issuer_namespace_pattern": r"https?://(?:www\.)?incyte\.com/\d{8}",
        "component_qnames": (BC + "Current", BC + "Noncurrent"), "aggregate_qname": BC,
        "cash_paid_qname": "us-gaap:PaymentForContingentConsiderationLiabilityFinancingActivities",
        "post_period_cash_local_name": "PaymentsForAssetAcquisitions",
        "post_period_maximum_qname": "us-gaap:AssetAcquisitionContingentConsiderationLiability",
        "post_period_member_local_name": "VegaTherapeuticsInc.Member",
        "treatment": "Sum the current and noncurrent carrying components once. Recurring fair-value views corroborate; financing cash already paid, the completed Vega cash payment and Vega contingent ceiling remain separate and non-additive.",
    },
})


def pharma_claim_policy(ticker: str) -> dict[str, Any]:
    rule = CLAIM_RULES.get(ticker)
    if rule is None:
        raise ValueError(f"no WG38 pharmaceutical claim policy for {ticker!r}")
    return deepcopy(dict(rule))


def _equal(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return json.dumps(actual, sort_keys=True, separators=(",", ":")) == json.dumps(expected, sort_keys=True, separators=(",", ":"))


def _dims(row: Mapping[str, Any]) -> dict[str, str]:
    raw = row.get("dimensions") or []
    if not isinstance(raw, (list, tuple)) or any(not isinstance(pair, (list, tuple)) or len(pair) != 2 for pair in raw):
        raise ValueError("WG38 claim dimensions are malformed")
    return dict(raw)


def _member(row: Mapping[str, Any], axis: str, local_name: str) -> bool:
    value = _dims(row).get(axis)
    return isinstance(value, str) and value.rsplit(":", 1)[-1] == local_name


def _valid(row: Mapping[str, Any], *, rule: Mapping[str, Any], accession: str, period_end: str,
           instant: bool, issuer: bool = False, allow_event_date: bool = False, cutoff: str | None = None) -> None:
    row_end = row.get("period_end")
    if (row.get("source_accession") != accession or row.get("unit") != "USD"
        or str(row.get("entity_identifier", "")).zfill(10) != rule["cik"]
        or row.get("entity_scheme") != "http://www.sec.gov/CIK"
        or (row_end != period_end and not allow_event_date)
        or (allow_event_date and (not isinstance(row_end, str) or cutoff is None or not period_end < row_end <= cutoff))
        or (instant and row.get("period_start") is not None)
        or (not instant and not isinstance(row.get("period_start"), str))
        or isinstance(row.get("value"), bool) or not isinstance(row.get("value"), (int, float))
        or not isfinite(row["value"]) or row["value"] < 0):
        raise ValueError("WG38 claim identity, period, unit or amount invalid")
    namespace = str(row.get("namespace", ""))
    if issuer:
        if not re.fullmatch(str(rule["issuer_namespace_pattern"]), namespace):
            raise ValueError("WG38 issuer namespace mismatch")
    elif not re.fullmatch(r"https?://fasb\.org/us-gaap/20\d{2}", namespace):
        raise ValueError("WG38 GAAP namespace mismatch")


def _unique_amount(rows: list[Mapping[str, Any]], label: str) -> float:
    if not rows:
        raise ValueError(f"WG38 {label} is missing")
    values = {float(row["value"]) for row in rows}
    if len(values) != 1:
        raise ValueError(f"WG38 {label} conflicts")
    return values.pop()


def _precision_tolerance(row: Mapping[str, Any]) -> float:
    raw = row.get("decimals")
    if not isinstance(raw, str) or not re.fullmatch(r"-?\d+", raw):
        raise ValueError("WG38 reconciliation needs numeric reported precision")
    decimals = int(raw)
    return 0.5 * (10.0 ** (-decimals))


def select_pharma_claim(policy: Mapping[str, Any], structural: Mapping[str, Any],
                        controlling: Mapping[str, Any], cik: str, cutoff: str) -> dict[str, Any]:
    ticker = policy.get("ticker")
    rule = CLAIM_RULES.get(str(ticker))
    if rule is None or not _equal(policy, rule) or str(cik).zfill(10) != rule["cik"]:
        raise RuntimeError("WG38 pharmaceutical claim policy identity/version mismatch")
    accession = controlling.get("accessionNumber")
    period = controlling.get("reportDate")
    filed = controlling.get("filingDate")
    if (structural.get("source_accession") != accession
        or (structural.get("report_date") or structural.get("period_end")) != period
        or not isinstance(period, str) or not isinstance(filed, str) or not period <= filed <= cutoff):
        raise ValueError("WG38 pharmaceutical claim source period/accession/cutoff mismatch")
    date.fromisoformat(period); date.fromisoformat(filed); date.fromisoformat(cutoff)
    facts = structural.get("facts")
    if not isinstance(facts, list):
        raise ValueError("WG38 structural facts are missing")

    source_rows: list[Mapping[str, Any]] = []
    excluded_rows: list[Mapping[str, Any]] = []
    review: list[str] = []
    components: dict[str, Any] = {}
    cash_adjustment = 0.0
    layout = rule["layout"]

    if layout == "aggregate_with_narrower_rollforward":
        carrying = [row for row in facts if row.get("qname") == rule["carrying_qname"]
                    and row.get("period_end") == period and row.get("period_start") is None]
        for row in carrying:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=True)
        aggregate = [row for row in carrying if not _dims(row)]
        level3 = [row for row in carrying if _dims(row) == {LEVEL_AXIS: LEVEL_3}]
        other_levels = [row for row in carrying if _dims(row).get(LEVEL_AXIS) in {
            "us-gaap:FairValueInputsLevel1Member", "us-gaap:FairValueInputsLevel2Member"}
            and set(_dims(row)) == {LEVEL_AXIS}]
        allowed_carrying = [*aggregate, *level3, *other_levels]
        if any(row not in allowed_carrying and float(row["value"]) != 0 for row in carrying):
            raise ValueError("WG38 BIIB has an unsupported nonzero carrying-liability dimension")
        claim = _unique_amount(aggregate, "BIIB aggregate carrying liability")
        if _unique_amount(level3, "BIIB Level-3 carrying liability") != claim or any(float(row["value"]) != 0 for row in other_levels):
            raise ValueError("WG38 BIIB carrying presentations do not reconcile")
        narrower = [row for row in facts if row.get("qname") == rule["narrower_qname"]
                    and row.get("period_end") == period and row.get("period_start") is None
                    and _dims(row) == {LEVEL_AXIS: LEVEL_3}]
        all_narrower = [row for row in facts if row.get("qname") == rule["narrower_qname"]
                        and row.get("period_end") == period and row.get("period_start") is None]
        for row in all_narrower:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=True)
        if any(row not in narrower and float(row["value"]) != 0 for row in all_narrower):
            raise ValueError("WG38 BIIB has an unsupported nonzero narrower-liability dimension")
        for row in narrower:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=True)
        narrower_amount = _unique_amount(narrower, "BIIB narrower acquisition balance")
        purchases = [row for row in facts if row.get("qname") == rule["purchase_qname"]
                     and row.get("period_end") == period and isinstance(row.get("period_start"), str)
                     and _member(row, ACQUISITION_AXIS, rule["purchase_member_local_name"])]
        for row in purchases:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=False)
        purchase_amount = _unique_amount(purchases, "BIIB Apellis carrying addition")
        tolerance = max(_precision_tolerance(aggregate[0]), _precision_tolerance(narrower[0]), _precision_tolerance(purchases[0]))
        if abs(narrower_amount + purchase_amount - claim) > tolerance:
            raise ValueError("WG38 BIIB narrower claim plus purchase does not reconcile to total")
        legal = [row for row in facts if row.get("qname") == rule["legal_qname"]
                 and row.get("unit") == "USD" and _member(row, next(iter(_dims(row)), ""), rule["legal_member_local_name"])]
        for row in legal:
            _valid(row, rule=rule, accession=accession, period_end=row["period_end"], instant=False)
            if row["period_end"] > cutoff:
                raise ValueError("WG38 BIIB legal evidence is outside the frozen cutoff")
        if not legal:
            raise ValueError("WG38 BIIB separate legal judgment evidence is missing")
        source_rows.extend([*aggregate, *level3, *other_levels, *narrower, *purchases])
        excluded_rows.extend(legal)
        components.update({"aggregate_carrying_liability": claim,
                           "narrower_existing_claim": narrower_amount,
                           "acquisition_purchase_added_within_aggregate": purchase_amount,
                           "legal_judgment_not_added": _unique_amount(legal, "BIIB legal judgment")})
        formula = "aggregate carrying liability; Level-3 duplicate and narrower rollforward reconcile inside it; legal judgment separate"

    elif layout == "business_and_asset_claims":
        business = [row for row in facts if row.get("qname") == rule["business_qname"]
                    and row.get("period_end") == period and row.get("period_start") is None
                    and _member(row, ACQUISITION_AXIS, rule["business_member_local_name"])]
        for row in business:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=True)
        business_aggregate = [row for row in business if LEVEL_AXIS not in _dims(row)]
        business_aggregate = [row for row in business_aggregate if set(_dims(row)) == {ACQUISITION_AXIS}]
        business_level3 = [row for row in business if _dims(row).get(LEVEL_AXIS) == LEVEL_3
                           and set(_dims(row)) == {ACQUISITION_AXIS, LEVEL_AXIS}]
        business_other = [row for row in business if _dims(row).get(LEVEL_AXIS) in {
            "us-gaap:FairValueInputsLevel1Member", "us-gaap:FairValueInputsLevel2Member"}
            and set(_dims(row)) == {ACQUISITION_AXIS, LEVEL_AXIS}]
        allowed_business = [*business_aggregate, *business_level3, *business_other]
        if any(row not in allowed_business and float(row["value"]) != 0 for row in business):
            raise ValueError("WG38 GILD has an unsupported nonzero MYR liability dimension")
        business_claim = _unique_amount(business_aggregate, "GILD MYR carrying liability")
        if _unique_amount(business_level3, "GILD MYR Level-3 liability") != business_claim or any(float(row["value"]) != 0 for row in business_other):
            raise ValueError("WG38 GILD MYR carrying presentations do not reconcile")

        asset = [row for row in facts if row.get("qname") == rule["asset_qname"]
                 and row.get("period_end") == period and row.get("period_start") is None
                 and _member(row, ASSET_AXIS, rule["asset_member_local_name"])]
        for row in asset:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=True)
        asset_aggregate = [row for row in asset if _dims(row).get(FREQUENCY_AXIS) == "us-gaap:FairValueMeasurementsNonrecurringMember"]
        asset_aggregate = [row for row in asset_aggregate if set(_dims(row)) == {ASSET_AXIS, FREQUENCY_AXIS}]
        location_axis = "us-gaap:StatementOfFinancialPositionLocationBalanceAxis"
        typed_locations = [row for row in asset if location_axis in _dims(row)
                           and set(_dims(row)) == {ASSET_AXIS, location_axis}]
        allowed_asset = [*asset_aggregate, *typed_locations]
        if any(row not in allowed_asset and float(row["value"]) != 0 for row in asset):
            raise ValueError("WG38 GILD has an unsupported nonzero Ouro liability dimension")
        asset_claim = _unique_amount(asset_aggregate, "GILD Ouro carrying liability")
        if len(typed_locations) != 2 or any(float(row["value"]) <= 0 for row in typed_locations):
            raise ValueError("WG38 GILD Ouro current/noncurrent typed locations are incomplete")
        typed_total = sum(float(row["value"]) for row in typed_locations)
        tolerance = _precision_tolerance(asset_aggregate[0]) + sum(_precision_tolerance(row) for row in typed_locations)
        if abs(typed_total - asset_claim) > tolerance:
            raise ValueError("WG38 GILD Ouro typed locations do not reconcile within reported precision")

        maxima = [row for row in facts if row.get("local_name") == rule["asset_maximum_local_name"]]
        cvrs = [row for row in facts if row.get("local_name") == rule["cvr_local_name"]]
        cash = [row for row in facts if row.get("local_name") in rule["cash_local_names"]
                and row.get("period_end") == period and isinstance(row.get("period_start"), str)]
        settlements = [row for row in facts if row.get("qname") == rule["settlement_qname"]
                       and row.get("period_end") == period and isinstance(row.get("period_start"), str)]
        for row in maxima + cvrs:
            _valid(row, rule=rule, accession=accession, period_end=row["period_end"], instant=True, issuer=True)
            if row["period_end"] > cutoff:
                raise ValueError("WG38 GILD contingent ceiling is outside the frozen cutoff")
        for row in cash:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=False,
                   issuer=not str(row.get("qname", "")).startswith("us-gaap:"))
        for row in settlements:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=False)
        if not maxima or not cvrs or not cash or not settlements:
            raise ValueError("WG38 GILD maxima, CVR, paid-cash or settlement diagnostics are incomplete")
        royalties = [row for row in facts if row.get("qname") == rule["royalty_qname"]
                     and row.get("period_end") == period and row.get("period_start") is None
                     and _member(row, ACQUISITION_AXIS, rule["royalty_member_local_name"])]
        for row in royalties:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=True)
        carrying_royalty = [row for row in royalties
                            if _dims(row).get("us-gaap:FairValueByMeasurementBasisAxis")
                            == "us-gaap:CarryingReportedAmountFairValueDisclosureMember"]
        fair_value_royalty = [row for row in royalties
                              if _dims(row).get("us-gaap:FairValueByMeasurementBasisAxis")
                              == "us-gaap:EstimateOfFairValueFairValueDisclosureMember"]
        royalty_carrying = _unique_amount(carrying_royalty, "GILD Immunomedics royalty carrying liability")
        royalty_fair_value = _unique_amount(fair_value_royalty, "GILD Immunomedics royalty fair value")
        if any(row not in carrying_royalty + fair_value_royalty and float(row["value"]) != 0 for row in royalties):
            raise ValueError("WG38 GILD has an unsupported nonzero royalty-liability dimension")
        royalty_debt = [row for row in facts if row.get("qname") == rule["royalty_debt_qname"]
                        and row.get("period_end") == period and row.get("period_start") is None
                        and _dims(row) == {rule["royalty_debt_axis"]: rule["royalty_debt_member"]}]
        for row in royalty_debt:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=True)
        royalty_debt_amount = _unique_amount(royalty_debt, "GILD royalty debt component")
        debt_total = [row for row in facts if row.get("qname") == rule["debt_total_qname"]
                      and row.get("period_end") == period and row.get("period_start") is None and not _dims(row)]
        for row in debt_total:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=True)
        debt_total_amount = _unique_amount(debt_total, "GILD total debt")
        if (abs(royalty_debt_amount - royalty_carrying)
            > _precision_tolerance(royalty_debt[0]) + _precision_tolerance(carrying_royalty[0])):
            raise ValueError("WG38 GILD royalty carrying disclosure does not reconcile to its debt component")
        if royalty_debt_amount > debt_total_amount:
            raise ValueError("WG38 GILD royalty component exceeds total debt")
        claim = business_claim + asset_claim
        source_rows.extend([*business_aggregate, *business_level3, *business_other, *asset_aggregate, *typed_locations])
        excluded_rows.extend([*maxima, *cvrs, *cash, *settlements, *royalties, *royalty_debt, *debt_total])
        components.update({"business_combination_carrying_liability": business_claim,
                           "asset_acquisition_carrying_liability": asset_claim,
                           "typed_location_total": typed_total,
                           "typed_location_rounding_difference": asset_claim - typed_total,
                           "contractual_maxima_not_added": sorted({float(row["value"]) for row in maxima}),
                           "cvr_ceiling_not_added": sorted({float(row["value"]) for row in cvrs}),
                           "paid_cash_not_added": sorted({float(row["value"]) for row in cash}),
                           "settlement_cash_not_added": sorted({float(row["value"]) for row in settlements}),
                           "future_royalty_carrying_not_added": royalty_carrying,
                           "future_royalty_fair_value_not_added": royalty_fair_value,
                           "future_royalty_debt_component": royalty_debt_amount,
                           "total_debt_containing_future_royalty": debt_total_amount,
                           "future_royalty_treatment": "included once in current total debt; fair value is diagnostic"})
        formula = "distinct MYR and Ouro carrying liabilities added once; duplicate views, ceilings, CVRs and cash excluded"

    elif layout == "recurring_with_post_period_asset_purchase":
        component_rows = []
        for qname in rule["component_qnames"]:
            all_rows = [row for row in facts if row.get("qname") == qname and row.get("period_end") == period
                        and row.get("period_start") is None]
            for row in all_rows:
                _valid(row, rule=rule, accession=accession, period_end=period, instant=True)
            rows = [row for row in all_rows if not _dims(row)]
            if any(row not in rows and float(row["value"]) != 0 for row in all_rows):
                raise ValueError("WG38 INCY has an unsupported nonzero carrying-liability dimension")
            _unique_amount(rows, f"INCY component {qname}")
            component_rows.extend(rows)
        claim = sum(float(row["value"]) for row in component_rows)
        aggregate = [row for row in facts if row.get("qname") == rule["aggregate_qname"]
                     and row.get("period_end") == period and row.get("period_start") is None
                     and _dims(row).get(FREQUENCY_AXIS) == RECURRING]
        for row in aggregate:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=True)
        level3 = [row for row in aggregate if _dims(row).get(LEVEL_AXIS) == LEVEL_3]
        level3 = [row for row in level3 if set(_dims(row)) == {LEVEL_AXIS, FREQUENCY_AXIS}]
        fair_value = [row for row in aggregate if _dims(row).get("us-gaap:FairValueByMeasurementBasisAxis") == "us-gaap:EstimateOfFairValueFairValueDisclosureMember"]
        fair_value = [row for row in fair_value if set(_dims(row)) == {
            "us-gaap:FairValueByMeasurementBasisAxis", FREQUENCY_AXIS}]
        other_levels = [row for row in aggregate if _dims(row).get(LEVEL_AXIS) in {
            "us-gaap:FairValueInputsLevel1Member", "us-gaap:FairValueInputsLevel2Member"}
            and set(_dims(row)) == {LEVEL_AXIS, FREQUENCY_AXIS}]
        allowed_aggregate = [*level3, *fair_value, *other_levels]
        if any(row not in allowed_aggregate and float(row["value"]) != 0 for row in aggregate):
            raise ValueError("WG38 INCY has an unsupported nonzero aggregate-liability dimension")
        if (_unique_amount(level3, "INCY Level-3 aggregate") != claim
            or _unique_amount(fair_value, "INCY recurring fair-value aggregate") != claim
            or any(float(row["value"]) != 0 for row in other_levels)):
            raise ValueError("WG38 INCY component and recurring aggregate presentations do not reconcile")
        paid = [row for row in facts if row.get("qname") == rule["cash_paid_qname"]
                and row.get("period_end") == period and isinstance(row.get("period_start"), str) and not _dims(row)]
        for row in paid:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=False)
        post_cash = [row for row in facts if row.get("local_name") == rule["post_period_cash_local_name"]
                     and _member(row, ASSET_AXIS, rule["post_period_member_local_name"])]
        post_maximum = [row for row in facts if row.get("qname") == rule["post_period_maximum_qname"]
                        and _member(row, ASSET_AXIS, rule["post_period_member_local_name"])]
        for row in post_cash:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=False, issuer=True,
                   allow_event_date=True, cutoff=cutoff)
        for row in post_maximum:
            _valid(row, rule=rule, accession=accession, period_end=period, instant=True,
                   allow_event_date=True, cutoff=cutoff)
        if not paid or not post_cash or not post_maximum:
            raise ValueError("WG38 INCY paid-cash and post-period diagnostics are incomplete")
        post_cash_amount = _unique_amount(post_cash, "INCY Vega cash payment")
        cash_adjustment = -post_cash_amount
        source_rows.extend([*component_rows, *level3, *fair_value, *other_levels])
        excluded_rows.extend([*paid, *post_cash, *post_maximum])
        components.update({"current_and_noncurrent_carrying_liability": claim,
                           "contingent_cash_paid_not_added": _unique_amount(paid, "INCY contingent cash paid"),
                           "post_period_asset_cash_adjustment": cash_adjustment,
                           "post_period_contingent_ceiling_not_added": _unique_amount(post_maximum, "INCY Vega contingent ceiling")})
        formula = "current plus noncurrent carrying liability; recurring duplicates corroborate; paid cash and Vega ceiling excluded"
    else:
        raise RuntimeError("unsupported WG38 pharmaceutical claim layout")

    return {
        "status": "review_required" if review else "source_bound",
        "claim_adjustment": None if review else claim,
        "current_carrying_liability": claim,
        "cash_adjustment": cash_adjustment,
        "review_reasons": review,
        "policy": dict(rule),
        "source_rows": source_rows,
        "excluded_rows": excluded_rows,
        "period_end": period,
        "formula": formula,
        "components": components,
        "cash_flow_overlap_limitation": "Recognized carrying claims are deducted once. Contractual maxima and CVRs are not current liabilities; paid or post-period acquisition cash is excluded from the claim and adjusted only once on the cash bridge.",
    }
