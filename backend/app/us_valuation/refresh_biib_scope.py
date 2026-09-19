"""WG40 BIIB legal-judgment and post-Apellis operating-scope ledger.

The ledger intentionally does not estimate a legal claim or acquired FCFF.  It
binds what the current filing reports and preserves the missing carrying/cash
and comparable-operating scopes as explicit review reasons.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import isfinite
import json
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA = "FINSIGHT-BIIB-LEGAL-OPERATING-SCOPE-1"
VERSION = "FINSIGHT-BIIB-LEGAL-OPERATING-SCOPE-WG40-1"


RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "BIIB": {
        "schema_version": SCHEMA, "version": VERSION, "ticker": "BIIB", "cik": "0000875045",
        "legal_judgment_qname": "us-gaap:LossContingencyDamagesSoughtValue",
        "legal_member_local_name": "GenentechMember",
        "legal_carrying_qnames": (
            "us-gaap:LitigationReserve", "us-gaap:LossContingencyAccrualAtCarryingValue",
            "us-gaap:LossContingencyAccrualCarryingValue", "us-gaap:LossContingencyAccrualCurrent",
            "us-gaap:LossContingencyAccrualNoncurrent",
        ),
        "legal_payment_qnames": (
            "us-gaap:PaymentsForLegalSettlements", "us-gaap:LitigationSettlementAmountAwardedToOtherParty",
        ),
        "legal_expense_qname": "us-gaap:LitigationSettlementExpense",
        "acquisition_axis": "us-gaap:BusinessAcquisitionAxis",
        "acquisition_member_local_name": "ApellisPharmaceuticalsInc.Member",
        "total_consideration_qname": "us-gaap:BusinessCombinationConsiderationTransferred1",
        "cash_consideration_qname": "us-gaap:PaymentsToAcquireBusinessesGross",
        "acquired_cash_qname": "us-gaap:BusinessCombinationRecognizedIdentifiableAssetsAcquiredAndLiabilitiesAssumedCashAndEquivalents",
        "net_acquisition_cash_qname": "us-gaap:OtherPaymentsToAcquireBusinesses",
        "funding_qname": "us-gaap:BusinessCombinationConsiderationTransferredLiabilitiesIncurred",
        "revolver_qname": "us-gaap:DebtInstrumentFaceAmount",
        "integration_charge_qname": "us-gaap:RestructuringCharges",
        "integration_member_local_name": "ApellisIntegrationMember",
        "integration_payment_qname": "us-gaap:PaymentsForRestructuring",
        "integration_payment_member_local_name": "WorkforceReductionMember",
        "revenue_qname": "us-gaap:Revenues",
        "product_axis_local_name": "ProductOrServiceAxis",
        "product_member_local_names": ("SYFOVREMember", "EMPAVELIMember"),
        "pro_forma_qnames": (
            "us-gaap:BusinessAcquisitionsProFormaRevenue",
            "us-gaap:BusinessAcquisitionsProFormaNetIncomeLoss",
        ),
        "operating_cash_qnames": (
            "us-gaap:NetCashProvidedByUsedInOperatingActivities",
            "us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        ),
        "treatment": "Keep the appealed judgment outside the acquisition claim until current legal carrying/payment/recovery scope is reported. Bind transaction cash, funding and observed acquired revenue, but issue no acquired FCFF or comparable combined-cash estimate without a filed operating-cash object.",
    },
})


def biib_scope_policy(ticker: str = "BIIB") -> dict[str, Any]:
    rule = RULES.get(ticker)
    if rule is None:
        raise ValueError(f"no WG40 BIIB scope policy for {ticker!r}")
    return deepcopy(dict(rule))


def _same(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return json.dumps(actual, sort_keys=True, separators=(",", ":")) == json.dumps(expected, sort_keys=True, separators=(",", ":"))


def _dims(row: Mapping[str, Any]) -> dict[str, str]:
    raw = row.get("dimensions") or []
    if not isinstance(raw, (list, tuple)) or any(not isinstance(pair, (list, tuple)) or len(pair) != 2 for pair in raw):
        raise ValueError("WG40 BIIB dimensions are malformed")
    return dict(raw)


def _member(row: Mapping[str, Any], axis_local: str, member_local: str) -> bool:
    return any(str(axis).rsplit(":", 1)[-1] == axis_local and str(member).rsplit(":", 1)[-1] == member_local
               for axis, member in _dims(row).items())


def _number(row: Mapping[str, Any], label: str, *, allow_signed: bool = False) -> float:
    value = row.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"WG40 BIIB {label} is not finite numeric evidence")
    if not allow_signed and value < 0:
        raise ValueError(f"WG40 BIIB {label} is negative")
    return float(value)


def _valid(row: Mapping[str, Any], *, rule: Mapping[str, Any], accession: str,
           period: str | None = None, instant: bool | None = None, allow_signed: bool = False) -> None:
    if (row.get("source_accession") != accession or row.get("unit") != "USD"
        or row.get("entity_scheme") != "http://www.sec.gov/CIK"
        or str(row.get("entity_identifier", "")).zfill(10) != rule["cik"]
        or (period is not None and row.get("period_end") != period)
        or (instant is True and row.get("period_start") is not None)
        or (instant is False and not isinstance(row.get("period_start"), str))):
        raise ValueError("WG40 BIIB source identity, period or unit mismatch")
    _number(row, str(row.get("qname")), allow_signed=allow_signed)


def _unique(rows: list[Mapping[str, Any]], label: str, *, allow_signed: bool = False) -> tuple[Mapping[str, Any], float]:
    if not rows:
        raise ValueError(f"WG40 BIIB required evidence is missing: {label}")
    values = {_number(row, label, allow_signed=allow_signed) for row in rows}
    if len(values) != 1:
        raise ValueError(f"WG40 BIIB evidence conflicts: {label}")
    return rows[0], values.pop()


def assess_biib_scope(policy: Mapping[str, Any], structural: Mapping[str, Any],
                      controlling: Mapping[str, Any], cik: str, cutoff: str) -> dict[str, Any]:
    rule = RULES.get(str(policy.get("ticker")))
    if rule is None or not _same(policy, rule) or str(cik).zfill(10) != rule["cik"]:
        raise RuntimeError("WG40 BIIB scope policy identity/version mismatch")
    accession, period, filed = controlling.get("accessionNumber"), controlling.get("reportDate"), controlling.get("filingDate")
    if (not isinstance(accession, str) or not isinstance(period, str) or not isinstance(filed, str)
        or structural.get("source_accession") != accession
        or (structural.get("report_date") or structural.get("period_end")) != period
        or not period <= filed <= cutoff):
        raise ValueError("WG40 BIIB controlling source or cutoff mismatch")
    date.fromisoformat(period); date.fromisoformat(filed); date.fromisoformat(cutoff)
    metadata = dict(structural.get("filing_metadata") or ())
    if metadata.get("manifest_version") != "FINSIGHT-XBRL-PACKAGE-1" or not metadata.get("package_generation"):
        raise ValueError("WG40 BIIB complete structural package receipt is required")
    facts = structural.get("facts")
    if not isinstance(facts, list):
        raise ValueError("WG40 BIIB structural facts are missing")

    judgment = [row for row in facts if row.get("qname") == rule["legal_judgment_qname"]
                and _member(row, "LitigationCaseAxis", rule["legal_member_local_name"])]
    for row in judgment:
        _valid(row, rule=rule, accession=accession, instant=False)
        if str(row.get("period_end")) > cutoff:
            raise ValueError("WG40 BIIB judgment evidence is outside cutoff")
    judgment_row, judgment_amount = _unique(judgment, "Genentech judgment")
    current_carrying = [row for row in facts if row.get("qname") in rule["legal_carrying_qnames"]
                        and row.get("period_end") == period and row.get("period_start") is None
                        and (_member(row, "LitigationCaseAxis", rule["legal_member_local_name"]) or not _dims(row))]
    for row in current_carrying:
        _valid(row, rule=rule, accession=accession, period=period, instant=True)
    legal_payments = [row for row in facts if row.get("qname") in rule["legal_payment_qnames"]
                      and row.get("period_end") == period and isinstance(row.get("period_start"), str)
                      and _member(row, "LitigationCaseAxis", rule["legal_member_local_name"])]
    for row in legal_payments:
        _valid(row, rule=rule, accession=accession, period=period, instant=False)
    legal_expense = [row for row in facts if row.get("qname") == rule["legal_expense_qname"]
                     and row.get("period_end") == period and isinstance(row.get("period_start"), str) and not _dims(row)]
    for row in legal_expense:
        _valid(row, rule=rule, accession=accession, period=period, instant=False, allow_signed=True)
    legal_expense_ytd = min(legal_expense, key=lambda row: str(row["period_start"])) if legal_expense else None

    member = rule["acquisition_member_local_name"]
    def acquisition_rows(qname: str, *, instant: bool | None = None):
        selected = [row for row in facts if row.get("qname") == qname
                    and _member(row, "BusinessAcquisitionAxis", member)]
        if instant is not None:
            selected = [row for row in selected if (row.get("period_start") is None) == instant]
        for row in selected:
            _valid(row, rule=rule, accession=accession, instant=instant, allow_signed=True)
        return selected

    total_row, total_consideration = _unique(acquisition_rows(rule["total_consideration_qname"], instant=False), "Apellis total consideration")
    cash_rows = [row for row in acquisition_rows(rule["cash_consideration_qname"], instant=False)
                 if not _member(row, "RestatementAxis", "ScenarioPreviouslyReportedMember")]
    cash_row, cash_consideration = _unique(cash_rows, "Apellis cash consideration")
    acquired_cash_row, acquired_cash = _unique(acquisition_rows(rule["acquired_cash_qname"], instant=True), "Apellis acquired cash")
    net_cash_rows = [row for row in facts if row.get("qname") == rule["net_acquisition_cash_qname"]
                     and row.get("period_end") == period and isinstance(row.get("period_start"), str) and not _dims(row)]
    for row in net_cash_rows:
        _valid(row, rule=rule, accession=accession, period=period, instant=False)
    net_cash_row, net_acquisition_cash = _unique(net_cash_rows, "Apellis net acquisition cash")
    funding = acquisition_rows(rule["funding_qname"], instant=False)
    funding = [row for row in funding if _member(row, "CreditFacilityAxis", "SecuredDebtMember")]
    funding_row, term_loan_funding = _unique(funding, "Apellis term-loan funding")
    revolver = acquisition_rows(rule["revolver_qname"], instant=True)
    revolver = [row for row in revolver if _member(row, "CreditFacilityAxis", "SecuredDebtMember")]
    revolver_row, revolver_funding = _unique(revolver, "Apellis revolver funding")

    integration = [row for row in facts if row.get("qname") == rule["integration_charge_qname"]
                   and row.get("period_end") == period and isinstance(row.get("period_start"), str)
                   and _member(row, "RestructuringPlanAxis", rule["integration_member_local_name"])]
    for row in integration:
        _valid(row, rule=rule, accession=accession, period=period, instant=False)
    integration_row, integration_charge = _unique(integration, "Apellis integration charge")
    integration_payments = [row for row in facts if row.get("qname") == rule["integration_payment_qname"]
                            and isinstance(row.get("period_start"), str) and row.get("period_end") <= period
                            and row.get("period_start", "") >= period[:4] + "-01-01"
                            and _member(row, "RestructuringCostAndReserveAxis", rule["integration_payment_member_local_name"])]
    for row in integration_payments:
        _valid(row, rule=rule, accession=accession, instant=False)
    if not integration_payments:
        raise ValueError("WG40 BIIB current workforce restructuring payments are missing")
    integration_payment_total = sum(_number(row, "workforce restructuring payment") for row in integration_payments)
    acquired_revenue_rows = [row for row in facts if row.get("qname") == rule["revenue_qname"]
                             and row.get("period_end") == period and isinstance(row.get("period_start"), str)
                             and any(_member(row, rule["product_axis_local_name"], product)
                                     for product in rule["product_member_local_names"])
                             and len(_dims(row)) == 1]
    for row in acquired_revenue_rows:
        _valid(row, rule=rule, accession=accession, period=period, instant=False)
    revenue_by_product = {}
    for product in rule["product_member_local_names"]:
        matches = [row for row in acquired_revenue_rows if _member(row, rule["product_axis_local_name"], product)]
        _, revenue_by_product[product] = _unique(matches, f"{product} reported revenue")
    pro_forma = [row for row in facts if row.get("qname") in rule["pro_forma_qnames"]]
    acquired_ocf = [row for row in facts if row.get("qname") in rule["operating_cash_qnames"]
                    and _member(row, "BusinessAcquisitionAxis", member)]

    cash_balance = [row for row in facts if row.get("qname") == "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"
                    and row.get("period_end") == period and row.get("period_start") is None and not _dims(row)]
    current_debt = [row for row in facts if row.get("qname") == "us-gaap:SecuredDebtCurrent"
                    and row.get("period_end") == period and row.get("period_start") is None and not _dims(row)]
    noncurrent_debt = [row for row in facts if row.get("qname") == "us-gaap:LongTermDebt"
                       and row.get("period_end") == period and row.get("period_start") is None and not _dims(row)]
    for row in cash_balance + current_debt + noncurrent_debt:
        _valid(row, rule=rule, accession=accession, period=period, instant=True)
    cash_balance_row, period_end_cash = _unique(cash_balance, "period-end cash")
    current_debt_row, period_end_current_debt = _unique(current_debt, "period-end current debt")
    noncurrent_debt_row, period_end_noncurrent_debt = _unique(noncurrent_debt, "period-end noncurrent debt")

    review = [
        "genentech_judgment_current_carrying_scope_unresolved",
        "genentech_judgment_payment_interest_and_recovery_scope_unresolved",
        "apellis_comparable_post_acquisition_cash_flow_not_reported",
        "apellis_integration_payment_scope_not_exclusive",
        "pending_raythera_transaction_cutoff_status_not_captured",
    ]
    if current_carrying:
        review.remove("genentech_judgment_current_carrying_scope_unresolved")
        review.append("genentech_judgment_carrying_fact_requires_legal_scope_review")
    if legal_payments:
        review.remove("genentech_judgment_payment_interest_and_recovery_scope_unresolved")
        review.append("genentech_judgment_payment_does_not_resolve_interest_or_recovery_scope")
    if pro_forma or acquired_ocf:
        review.append("apellis_reported_operating_scope_requires_comparability_review")

    return {
        "status": "review_required", "claim_adjustment": None,
        "numeric_successor_issued": False, "review_reasons": review,
        "policy": dict(rule), "period_end": period,
        "legal_scope": {
            "judgment_amount": judgment_amount,
            "judgment_source": dict(judgment_row),
            "current_carrying_rows": [dict(row) for row in current_carrying],
            "current_legal_payment_rows": [dict(row) for row in legal_payments],
            "current_unscoped_litigation_expense": None if legal_expense_ytd is None else _number(legal_expense_ytd, "litigation expense", allow_signed=True),
            "insurance_or_indemnification_recovery": None,
            "judgment_interest": None,
            "treatment": "judgment amount is neither probability weighted nor promoted to a current carrying claim",
        },
        "acquisition_scope": {
            "total_consideration": total_consideration,
            "cash_consideration_paid_or_payable": cash_consideration,
            "acquired_cash": acquired_cash,
            "reported_net_acquisition_cash": net_acquisition_cash,
            "cash_consideration_timing_difference": cash_consideration - acquired_cash - net_acquisition_cash,
            "term_loan_funding": term_loan_funding,
            "revolver_funding": revolver_funding,
            "period_end_cash": period_end_cash,
            "period_end_current_debt": period_end_current_debt,
            "period_end_noncurrent_debt": period_end_noncurrent_debt,
            "period_end_total_debt": period_end_current_debt + period_end_noncurrent_debt,
            "integration_charge": integration_charge,
            "current_workforce_restructuring_payments": integration_payment_total,
            "integration_payment_scope": "reported workforce-reduction payments are not exclusively dimensioned to Apellis",
            "reported_product_revenue": revenue_by_product,
            "pro_forma_rows": [dict(row) for row in pro_forma],
            "acquired_operating_cash_rows": [dict(row) for row in acquired_ocf],
            "acquired_fcff": None, "synergies": None,
            "pending_transaction": {
                "status": "narrative_only_not_machine_bound",
                "upfront_upon_closing": None,
                "contingent_maximum": None,
                "current_claim": None,
            },
        },
        "source_rows": [dict(row) for row in (judgment_row, total_row, cash_row, acquired_cash_row,
            net_cash_row, funding_row, revolver_row, integration_row, cash_balance_row,
            current_debt_row, noncurrent_debt_row, *integration_payments, *acquired_revenue_rows)],
        "excluded_rows": [dict(row) for row in (*legal_expense, *current_carrying, *legal_payments)],
    }
