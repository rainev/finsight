"""Versioned operating-reserve and benefit-liability claim scopes.

These rules classify current filing facts without embedding amounts, filing
dates, or accessions.  Ownership claims, funded-status liabilities, operating
reserves, and cash-flow movements remain separate so no balance or payment is
counted twice.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from math import isclose, isfinite
import re
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA = "FINSIGHT-OPERATING-CLAIM-1"
VERSION = "FINSIGHT-OPERATING-CLAIM-WG7-1"
_GAAP = re.compile(r"^https?://(?:fasb\.org|xbrl\.us-gaap)/us-gaap/20\d{2}$")


RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "AVY": MappingProxyType({
        "schema_version": SCHEMA, "version": VERSION, "ticker": "AVY", "cik": "0000008818",
        "mode": "mixed_reserves_review",
        "restructuring_qname": "us-gaap:RestructuringReserve",
        "restructuring_charge_qname": "us-gaap:RestructuringCharges",
        "restructuring_payment_qname": "us-gaap:PaymentsForRestructuring",
        "restructuring_noncash_qname": "us-gaap:RestructuringReserveSettledWithoutCash2",
        "environmental_qname": "us-gaap:AccrualForEnvironmentalLossContingencies",
        "environmental_current_qname": "us-gaap:AccruedEnvironmentalLossContingenciesCurrent",
        "environmental_payment_qname": "us-gaap:AccrualForEnvironmentalLossContingenciesPayments1",
        "environmental_charge_local_name": "EnvironmentalChargesNetOfReversals",
        "issuer_namespace_pattern": r"https?://(?:www\.)?averydennison\.com/\d{8}",
        "acquisition_qname": "us-gaap:BusinessCombinationContingentConsiderationLiability",
        "treatment": "keep restructuring and environmental ending reserves, payments and charges separate; keep current acquisition consideration separate; require a forward-cash overlap decision before binding a combined claim",
    }),
    "BALL": MappingProxyType({
        "schema_version": SCHEMA, "version": VERSION, "ticker": "BALL", "cik": "0000009389",
        "mode": "benefit_liability_components",
        "nci_qname": "us-gaap:MinorityInterest",
        "pension_total_qname": "us-gaap:DefinedBenefitPensionPlanCurrentAndNoncurrentLiabilities",
        "pension_current_qname": "us-gaap:DefinedBenefitPensionPlanLiabilitiesCurrent",
        "pension_noncurrent_qname": "us-gaap:DefinedBenefitPensionPlanLiabilitiesNoncurrent",
        "postemployment_qname": "us-gaap:PostemploymentBenefitsLiabilityNoncurrent",
        "benefit_aggregate_qnames": (
            "us-gaap:PensionAndOtherPostretirementAndPostemploymentBenefitPlansLiabilitiesNoncurrent",
            "us-gaap:PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",
        ),
        "deferred_compensation_qname": "us-gaap:DeferredCompensationLiabilityClassifiedNoncurrent",
        "other_employee_local_name": "OtherEmployeeRelatedLiabilitiesNoncurrent",
        "environmental_qname": "us-gaap:AccrualForEnvironmentalLossContingencies",
        "operating_flow_local_name": "RestructuringAndOtherActivities",
        "pension_noncash_qname": "us-gaap:PensionExpenseReversalOfExpenseNoncash",
        "pension_contribution_qname": "us-gaap:PensionContributions",
        "treatment": "deduct reported pension funded-status and retiree-medical obligations once; keep NCI in the ownership bridge and compensation, environmental and cash-flow items in operating scope",
    }),
    "MPC": MappingProxyType({
        "schema_version": SCHEMA, "version": VERSION, "ticker": "MPC", "cik": "0001510295",
        "mode": "bear_operating_stress",
        "nci_qname": "us-gaap:MinorityInterest",
        "pension_qname": "us-gaap:PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",
        "environmental_qname": "us-gaap:AccrualForEnvironmentalLossContingencies",
        "environmental_recovery_qname": "us-gaap:RecordedThirdPartyEnvironmentalRecoveriesReceivable",
        "pension_noncash_qname": "us-gaap:PensionAndOtherPostretirementBenefitsExpenseReversalOfExpenseNoncash",
        "benefits_paid_qname": "us-gaap:DefinedBenefitPlanBenefitObligationBenefitsPaid",
        "contribution_qname": "us-gaap:DefinedBenefitPlanContributionsByEmployer",
        "pension_member": "us-gaap:OtherPensionPlansDefinedBenefitMember",
        "postretirement_member": "us-gaap:OtherPostretirementBenefitPlansDefinedBenefitMember",
        "contribution_member": "us-gaap:PensionPlansDefinedBenefitMember",
        "equity_method_qname": "us-gaap:EquityMethodInvestments",
        "treatment": "deduct NCI in every scenario; retain gross pension and environmental balances only as a bear operating-liability stress, without relabeling them debt or inventing timing; do not net an unlinked recovery",
    }),
})


def operating_claim_policy(ticker: str) -> dict[str, Any]:
    rule = RULES.get(ticker)
    if rule is None:
        raise ValueError(f"no operating claim rule for {ticker!r}")
    return deepcopy(dict(rule))


def _same_policy(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return json.dumps(dict(actual), sort_keys=True, separators=(",", ":")) == json.dumps(
        dict(expected), sort_keys=True, separators=(",", ":")
    )


def _context(policy, structural, controlling, cik, cutoff):
    expected = RULES.get(policy.get("ticker"))
    if expected is None or not _same_policy(policy, expected) or str(cik).zfill(10) != expected["cik"]:
        raise RuntimeError("operating claim policy identity/version mismatch")
    accession = controlling.get("accessionNumber") or controlling.get("accession")
    period = controlling.get("reportDate") or controlling.get("period_end")
    filed = controlling.get("filingDate") or structural.get("filed_date")
    if (structural.get("source_accession") != accession
        or (structural.get("report_date") or structural.get("period_end")) != period
        or not isinstance(filed, str) or not str(period) <= filed <= cutoff):
        raise ValueError("operating claim source period/accession/cutoff mismatch")
    date.fromisoformat(str(period)); date.fromisoformat(filed); date.fromisoformat(cutoff)
    facts = structural.get("facts")
    if not isinstance(facts, list):
        raise ValueError("operating claim structural facts are missing")
    return expected, str(accession), str(period), facts


def _valid(row, *, policy, accession, period, instant=True, issuer=False):
    if (row.get("source_accession") != accession or row.get("unit") != "USD"
        or str(row.get("entity_identifier", "")).zfill(10) != policy["cik"]
        or row.get("entity_scheme") != "http://www.sec.gov/CIK"
        or row.get("period_end") != period
        or (instant and row.get("period_start") is not None)
        or (not instant and not isinstance(row.get("period_start"), str))
        or isinstance(row.get("value"), bool) or not isinstance(row.get("value"), (int, float))
        or not isfinite(float(row["value"]))):
        raise ValueError("operating claim identity, period, unit or amount invalid")
    namespace = str(row.get("namespace", ""))
    if issuer:
        ticker = str(policy["ticker"]).lower()
        pattern = policy.get("issuer_namespace_pattern") or rf"https?://(?:www\.)?{ticker}\.(?:com|net)/\d{{8}}"
        if not re.fullmatch(str(pattern), namespace):
            raise ValueError("operating claim issuer namespace mismatch")
    elif not _GAAP.fullmatch(namespace):
        raise ValueError("operating claim GAAP namespace mismatch")


def _select(facts, *, policy, accession, period, qname=None, local_name=None,
            instant=True, undimensioned=True, member=None, issuer=False):
    rows = []
    for row in facts:
        if qname is not None and row.get("qname") != qname:
            continue
        if local_name is not None and row.get("local_name") != local_name:
            continue
        if row.get("period_end") != period:
            continue
        if instant and row.get("period_start") is not None:
            continue
        if not instant and not isinstance(row.get("period_start"), str):
            continue
        dims = row.get("dimensions") or []
        if undimensioned and dims:
            continue
        if member is not None and not any(
            isinstance(pair, (list, tuple)) and len(pair) == 2 and pair[1] == member for pair in dims
        ):
            continue
        _valid(row, policy=policy, accession=accession, period=period, instant=instant, issuer=issuer)
        rows.append(row)
    if not rows:
        label = qname or local_name
        raise ValueError(f"required operating claim fact is missing: {label}")
    # For flows, use the longest current YTD duration and collapse duplicate
    # presentations with the same value.  Quarter-only facts are not additive.
    if not instant:
        start = min(str(row["period_start"]) for row in rows)
        rows = [row for row in rows if row["period_start"] == start]
    values = {float(row["value"]) for row in rows}
    if len(values) != 1:
        raise ValueError(f"required operating claim fact conflicts: {qname or local_name}")
    return dict(rows[0]), values.pop()


def _dimensioned_components(facts, *, policy, accession, period, qname):
    rows = []
    for row in facts:
        if (row.get("qname") == qname and row.get("period_end") == period
            and row.get("period_start") is None and row.get("dimensions")):
            _valid(row, policy=policy, accession=accession, period=period)
            rows.append(dict(row))
    return rows


def select_operating_claim(policy: Mapping[str, Any], structural: Mapping[str, Any],
                           controlling: Mapping[str, Any], cik: str, cutoff: str) -> dict[str, Any]:
    policy, accession, period, facts = _context(policy, structural, controlling, cik, cutoff)
    mode = policy["mode"]
    sources: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    components: dict[str, float] = {}
    review: list[str] = []
    claim_adjustment = None
    scenario_adjustments = None

    def one(qname, *, instant=True, member=None):
        row, value = _select(facts, policy=policy, accession=accession, period=period,
                             qname=qname, instant=instant, member=member)
        return row, value

    if mode == "mixed_reserves_review":
        restructuring_row, restructuring = one(policy["restructuring_qname"])
        reserve_parts = _dimensioned_components(
            facts, policy=policy, accession=accession, period=period,
            qname=policy["restructuring_qname"],
        )
        if not reserve_parts or not isclose(sum(float(row["value"]) for row in reserve_parts), restructuring,
                                            rel_tol=1e-12, abs_tol=0.01):
            raise ValueError("restructuring reserve components do not reconcile to ending total")
        charge_row, charges = one(policy["restructuring_charge_qname"], instant=False)
        payment_row, payments = one(policy["restructuring_payment_qname"], instant=False)
        noncash_row, noncash = one(policy["restructuring_noncash_qname"], instant=False)
        environmental_row, environmental = one(policy["environmental_qname"])
        current_row, environmental_current = one(policy["environmental_current_qname"])
        if min(restructuring, charges, payments, noncash, environmental, environmental_current) < 0:
            raise ValueError("operating reserve sign requires review")
        if environmental_current > environmental:
            raise ValueError("environmental current portion exceeds total reserve")
        environmental_payment_row, environmental_payments = one(policy["environmental_payment_qname"], instant=False)
        environmental_charge_row, environmental_charges = _select(
            facts, policy=policy, accession=accession, period=period,
            local_name=policy["environmental_charge_local_name"], instant=False, issuer=True,
        )
        acquisition_row, acquisition = one(policy["acquisition_qname"])
        acquisition_levels = _dimensioned_components(
            facts, policy=policy, accession=accession, period=period, qname=policy["acquisition_qname"]
        )
        nonzero_levels = {float(row["value"]) for row in acquisition_levels if float(row["value"]) != 0.0}
        if nonzero_levels != {acquisition}:
            raise ValueError("acquisition carrying liability lacks matching Level-3 presentation")
        sources = [restructuring_row, *reserve_parts, environmental_row, acquisition_row, *acquisition_levels]
        excluded = [charge_row, payment_row, noncash_row, current_row,
                    environmental_payment_row, environmental_charge_row]
        components = {
            "restructuring_reserve": restructuring,
            "restructuring_charges": charges,
            "restructuring_cash_payments": payments,
            "restructuring_noncash_settlements": noncash,
            "environmental_reserve": environmental,
            "environmental_current_portion": environmental_current,
            "environmental_cash_payments": environmental_payments,
            "environmental_charges": environmental_charges,
            "acquisition_contingent_consideration": acquisition,
        }
        review.append("operating_reserves_and_acquisition_claim_lack_one_forward_cash_overlap_rule")
        formula = "ending restructuring, environmental and acquisition balances retained separately; charges, payments, current portions and duplicate fair-value levels are not added"
    elif mode == "benefit_liability_components":
        nci_row, nci = one(policy["nci_qname"])
        pension_total_row, pension_total = one(policy["pension_total_qname"])
        pension_current_row, pension_current = one(policy["pension_current_qname"])
        pension_noncurrent_row, pension_noncurrent = one(policy["pension_noncurrent_qname"])
        postemployment_row, postemployment = one(policy["postemployment_qname"])
        if not isclose(pension_total, pension_current + pension_noncurrent, rel_tol=1e-12, abs_tol=0.01):
            raise ValueError("pension total does not reconcile to current and noncurrent components")
        aggregate_rows = [one(qname) for qname in policy["benefit_aggregate_qnames"]]
        if len({value for _, value in aggregate_rows}) != 1:
            raise ValueError("benefit aggregate aliases conflict")
        aggregate = aggregate_rows[0][1]
        deferred_row, deferred = one(policy["deferred_compensation_qname"])
        other_row, other = _select(
            facts, policy=policy, accession=accession, period=period,
            local_name=policy["other_employee_local_name"], issuer=True,
        )
        if not isclose(aggregate, pension_noncurrent + postemployment + deferred + other,
                       rel_tol=1e-12, abs_tol=0.01):
            raise ValueError("noncurrent benefit aggregate does not reconcile to disjoint components")
        environmental_row, environmental = one(policy["environmental_qname"])
        operating_flow_row, operating_flow = _select(
            facts, policy=policy, accession=accession, period=period,
            local_name=policy["operating_flow_local_name"], instant=False, issuer=True,
        )
        noncash_row, pension_noncash = one(policy["pension_noncash_qname"], instant=False)
        contribution_row, pension_contribution = _select(
            facts, policy=policy, accession=accession, period=period,
            qname=policy["pension_contribution_qname"], instant=False,
            undimensioned=False, member="us-gaap:PensionPlansDefinedBenefitMember",
        )
        if min(nci, pension_total, postemployment, aggregate, deferred, other, environmental, pension_contribution) < 0:
            raise ValueError("benefit or operating liability sign requires review")
        claim_adjustment = pension_total + postemployment
        sources = [pension_total_row, pension_current_row, pension_noncurrent_row,
                   postemployment_row, *[row for row, _ in aggregate_rows]]
        excluded = [nci_row, deferred_row, other_row, environmental_row,
                    operating_flow_row, noncash_row, contribution_row]
        components = {
            "nci_separate_bridge_claim": nci,
            "pension_total": pension_total,
            "pension_current": pension_current,
            "pension_noncurrent": pension_noncurrent,
            "postemployment_liability": postemployment,
            "benefit_claim_adjustment": claim_adjustment,
            "benefit_noncurrent_aggregate": aggregate,
            "deferred_compensation_operating": deferred,
            "other_employee_liabilities_operating": other,
            "environmental_reserve_operating": environmental,
            "operating_restructuring_flow": operating_flow,
            "pension_noncash_ocf_adjustment": pension_noncash,
            "pension_cash_contribution": pension_contribution,
        }
        formula = "pension current-plus-noncurrent funded-status liability plus retiree-medical liability; NCI, compensation liabilities, environmental reserve and OCF movements remain separate"
    elif mode == "bear_operating_stress":
        nci_row, nci = one(policy["nci_qname"])
        pension_row, pension = one(policy["pension_qname"])
        environmental_row, environmental = one(policy["environmental_qname"])
        recovery_row, recovery = one(policy["environmental_recovery_qname"])
        noncash_row, noncash = one(policy["pension_noncash_qname"], instant=False)
        pension_paid_row, pension_paid = _select(
            facts, policy=policy, accession=accession, period=period,
            qname=policy["benefits_paid_qname"], instant=False, undimensioned=False,
            member=policy["pension_member"],
        )
        postretirement_paid_row, postretirement_paid = _select(
            facts, policy=policy, accession=accession, period=period,
            qname=policy["benefits_paid_qname"], instant=False, undimensioned=False,
            member=policy["postretirement_member"],
        )
        contribution_row, contribution = _select(
            facts, policy=policy, accession=accession, period=period,
            qname=policy["contribution_qname"], instant=False, undimensioned=False,
            member=policy["contribution_member"],
        )
        equity_method_row, equity_method = one(policy["equity_method_qname"])
        if min(nci, pension, environmental, recovery, noncash, pension_paid,
               postretirement_paid, contribution, equity_method) < 0:
            raise ValueError("MPC operating claim sign requires review")
        bear = pension + environmental
        scenario_adjustments = {"bear": bear, "base": 0.0, "bull": 0.0}
        claim_adjustment = bear
        sources = [pension_row, environmental_row]
        excluded = [nci_row, recovery_row, noncash_row, pension_paid_row,
                    postretirement_paid_row, contribution_row, equity_method_row]
        components = {
            "nci_separate_bridge_claim": nci,
            "pension_postretirement_liability": pension,
            "environmental_reserve_gross": environmental,
            "environmental_recovery_not_netted": recovery,
            "pension_postretirement_noncash_ocf_adjustment": noncash,
            "pension_benefits_paid": pension_paid,
            "postretirement_benefits_paid": postretirement_paid,
            "employer_pension_contribution": contribution,
            "equity_method_investment_not_surplus_cash": equity_method,
            "bear_operating_liability_stress": bear,
        }
        formula = "gross pension/postretirement plus environmental reserve in bear only; recovery, paid cash, noncash OCF adjustment and equity-method investment remain separate diagnostics"
    else:
        raise RuntimeError("unsupported operating claim mode")

    return {
        "status": "review_required" if review else "source_bound",
        "claim_adjustment": None if review else claim_adjustment,
        "scenario_adjustments": scenario_adjustments,
        "review_reasons": review,
        "policy": dict(policy),
        "source_rows": sources,
        "excluded_rows": excluded,
        "components": components,
        "period_end": period,
        "controlling_accession": accession,
        "formula": formula,
        "cash_flow_overlap_limitation": "Ending balances, recognized recoveries, cash payments, noncash movements and ordinary operating liabilities are retained separately; only the declared scenario treatment is bound.",
    }


__all__ = ["RULES", "SCHEMA", "VERSION", "operating_claim_policy", "select_operating_claim"]
