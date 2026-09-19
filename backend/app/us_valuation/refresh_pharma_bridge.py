"""Versioned current bridge scopes for WG39 pharmaceutical issuers.

The rules describe reporting structure only.  Amounts, accessions and dates are
selected from the frozen controlling filing on every run.
"""
from __future__ import annotations

from copy import deepcopy
from math import isclose, isfinite
from numbers import Real
import json
import re
from types import MappingProxyType
from typing import Any, Mapping

from .field_availability import FieldAvailability


SCHEMA = "FINSIGHT-PHARMA-BRIDGE-SCOPE-1"
VERSION = "FINSIGHT-PHARMA-BRIDGE-WG39-1"
DEBT_FIELDS = (
    "commercial_paper", "current_debt", "noncurrent_debt",
    "finance_lease_current", "finance_lease_noncurrent",
)


RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "BIIB": {
        "schema_version": SCHEMA, "version": VERSION, "ticker": "BIIB", "cik": "0000875045",
        "mode": "cash_and_split_debt",
        "cash_qname": "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "cash_parent": "us-gaap:AssetsCurrentAbstract",
        "marketable_zero_qnames": (
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
        ),
        "debt_current_qname": "us-gaap:SecuredDebtCurrent",
        "debt_noncurrent_qname": "us-gaap:LongTermDebt",
        "excluded_debt_qnames": (
            "us-gaap:CommercialPaper", "us-gaap:CommercialPaperAtCarryingValue",
            "us-gaap:ShortTermBorrowings", "us-gaap:FinanceLeaseLiability",
            "us-gaap:FinanceLeaseLiabilityCurrent", "us-gaap:FinanceLeaseLiabilityNoncurrent",
        ),
        "treatment": "Bind period-end cash and sum the separate current term-loan and noncurrent notes/term-loan balance once; operating leases and acquisition consideration remain separate.",
    },
    "GILD": {
        "schema_version": SCHEMA, "version": VERSION, "ticker": "GILD", "cik": "0000882095",
        "mode": "cash_debt_with_royalty_component",
        "cash_qname": "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "cash_parent": "us-gaap:AssetsCurrentAbstract",
        "searched_separate_cash_qnames": (
            "us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:RestrictedCash",
            "us-gaap:RestrictedCashCurrent", "us-gaap:RestrictedCashNoncurrent",
        ),
        "marketable_zero_qnames": (
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
        ),
        "debt_total_qname": "us-gaap:LongTermDebt",
        "debt_current_alias_qnames": ("us-gaap:DebtCurrent", "us-gaap:LongTermDebtCurrent"),
        "debt_noncurrent_qname": "us-gaap:LongTermDebtNoncurrent",
        "excluded_debt_qnames": (
            "us-gaap:CommercialPaper", "us-gaap:CommercialPaperAtCarryingValue",
            "us-gaap:ShortTermBorrowings", "us-gaap:FinanceLeaseLiability",
            "us-gaap:FinanceLeaseLiabilityCurrent", "us-gaap:FinanceLeaseLiabilityNoncurrent",
        ),
        "royalty_debt_component_qname": "us-gaap:LongTermDebt",
        "royalty_debt_axis": "us-gaap:LongtermDebtTypeAxis",
        "royalty_debt_member": "us-gaap:NotesPayableOtherPayablesMember",
        "senior_debt_component_qname": "us-gaap:DebtInstrumentCarryingAmount",
        "senior_debt_axis": "us-gaap:LongtermDebtTypeAxis",
        "senior_debt_member_local_name": "SeniorNotesAndMediumTermNotesMember",
        "royalty_qname": "us-gaap:AccruedRoyaltiesCurrentAndNoncurrent",
        "royalty_acquisition_axis": "us-gaap:BusinessAcquisitionAxis",
        "royalty_acquisition_member_local_name": "ImmunomedicsIncMember",
        "measurement_basis_axis": "us-gaap:FairValueByMeasurementBasisAxis",
        "carrying_basis_member": "us-gaap:CarryingReportedAmountFairValueDisclosureMember",
        "fair_value_basis_member": "us-gaap:EstimateOfFairValueFairValueDisclosureMember",
        "repayment_qname": "us-gaap:RepaymentsOfDebt",
        "matured_debt_qname": "us-gaap:LongTermDebt",
        "matured_debt_axis": "us-gaap:DebtInstrumentAxis",
        "matured_debt_member_local_name": "SeniorUnsecuredNotesDueInMarch2026Member",
        "treatment": "Bind current cash and total debt once. Current plus noncurrent debt reconcile to the total; the Immunomedics royalty carrying component is already inside that debt and its fair value is diagnostic, never an additional claim.",
    },
    "INCY": {
        "schema_version": SCHEMA, "version": VERSION, "ticker": "INCY", "cik": "0000879169",
        "mode": "cashlike_debt_and_strategic_investments",
        "marketable_current_qname": "us-gaap:DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent",
        "marketable_current_alias_qname": "us-gaap:DebtSecuritiesAvailableForSaleExcludingAccruedInterest",
        "marketable_maturity_qnames": (
            "us-gaap:AvailableForSaleSecuritiesDebtMaturitiesWithinOneYearFairValue",
            "us-gaap:AvailableForSaleSecuritiesDebtMaturitiesAfterOneThroughFiveYearsFairValue",
        ),
        "searched_noncurrent_marketable_qnames": (
            "us-gaap:DebtSecuritiesAvailableForSaleExcludingAccruedInterestNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
            "us-gaap:MarketableSecuritiesNoncurrent", "us-gaap:LongTermInvestments",
        ),
        "excluded_strategic_investment_qname": "us-gaap:EquitySecuritiesFVNINoncurrent",
        "fair_value_level_axis": "us-gaap:FairValueByFairValueHierarchyLevelAxis",
        "level_1_member": "us-gaap:FairValueInputsLevel1Member",
        "level_2_member": "us-gaap:FairValueInputsLevel2Member",
        "level_3_member": "us-gaap:FairValueInputsLevel3Member",
        "debt_component_qnames": (
            "us-gaap:FinanceLeaseLiabilityCurrent", "us-gaap:FinanceLeaseLiabilityNoncurrent",
        ),
        "zero_borrowing_qname": "us-gaap:LineOfCredit",
        "zero_borrowing_axis": "us-gaap:CreditFacilityAxis",
        "zero_borrowing_member": "us-gaap:RevolvingCreditFacilityMember",
        "excluded_debt_qnames": (
            "us-gaap:CommercialPaper", "us-gaap:CommercialPaperAtCarryingValue",
            "us-gaap:ShortTermBorrowings", "us-gaap:DebtCurrent", "us-gaap:LongTermDebtCurrent",
            "us-gaap:LongTermDebtNoncurrent", "us-gaap:LongTermDebt",
        ),
        "treatment": "Bind current available-for-sale debt securities and finance-lease debt once. Prove no separate noncurrent debt-security balance; keep strategic noncurrent equity investments outside excess cash.",
    },
})


def pharma_bridge_policy(ticker: str) -> dict[str, Any]:
    rule = RULES.get(ticker)
    if rule is None:
        raise ValueError(f"no WG39 pharmaceutical bridge policy for {ticker!r}")
    return deepcopy(dict(rule))


def _same(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return json.dumps(actual, sort_keys=True, separators=(",", ":")) == json.dumps(expected, sort_keys=True, separators=(",", ":"))


def _number(value: Any, label: str, *, signed: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value)):
        raise ValueError(f"WG39 {label} is not finite numeric evidence")
    result = float(value)
    if not signed and result < 0:
        raise ValueError(f"WG39 {label} is negative")
    return result


def _dims(row: Mapping[str, Any]) -> dict[str, str]:
    raw = row.get("dimensions") or []
    if not isinstance(raw, (list, tuple)) or any(not isinstance(pair, (list, tuple)) or len(pair) != 2 for pair in raw):
        raise ValueError("WG39 dimensions are malformed")
    return dict(raw)


def _current_rows(structural: Mapping[str, Any], *, rule: Mapping[str, Any], accession: str, period: str) -> list[Mapping[str, Any]]:
    if structural.get("source_accession") != accession or (structural.get("report_date") or structural.get("period_end")) != period:
        raise ValueError("WG39 structural source identity mismatch")
    metadata = dict(structural.get("filing_metadata") or ())
    if metadata.get("manifest_version") != "FINSIGHT-XBRL-PACKAGE-1" or not metadata.get("package_generation"):
        raise ValueError("WG39 complete structural package receipt is required")
    facts = structural.get("facts")
    if not isinstance(facts, list):
        raise ValueError("WG39 structural facts are missing")
    rows = [row for row in facts if isinstance(row, Mapping)
            and row.get("source_accession") == accession and row.get("period_end") == period
            and row.get("period_start") is None and row.get("unit") == "USD"
            and row.get("entity_scheme") == "http://www.sec.gov/CIK"
            and str(row.get("entity_identifier", "")).zfill(10) == rule["cik"]]
    if not rows:
        raise ValueError("WG39 current issuer USD facts are missing")
    return rows


def _unique(rows: list[Mapping[str, Any]], qname: str, *, dimensions: Mapping[str, str] | None = None) -> Mapping[str, Any]:
    matches = [row for row in rows if row.get("qname") == qname
               and (not _dims(row) if dimensions is None else _dims(row) == dict(dimensions))]
    if not matches:
        raise ValueError(f"WG39 required fact is missing: {qname}")
    values = {_number(row.get("value"), qname, signed=True) for row in matches}
    if len(values) != 1:
        raise ValueError(f"WG39 required fact conflicts: {qname}")
    return matches[0]


def _precision(row: Mapping[str, Any]) -> float:
    raw = row.get("decimals")
    if not isinstance(raw, str) or not re.fullmatch(r"-?\d+", raw):
        raise ValueError("WG39 reported precision is missing")
    return 0.5 * (10.0 ** (-int(raw)))


def _ref(accession: str, period: str, row: Mapping[str, Any]) -> str:
    context = row.get("context_id")
    source_period = row.get("period_end")
    if not isinstance(context, str) or not context:
        raise ValueError("WG39 source context is missing")
    if not isinstance(source_period, str) or not source_period:
        raise ValueError("WG39 source period is missing")
    return f"{accession}|{source_period}|{row['qname']}|{context}"


def _availability(*, field: str, value: float, state: str, reason: str,
                  accession: str, period: str, sources: list[Mapping[str, Any]],
                  covered_fields: tuple[str, ...], scope: str) -> FieldAvailability:
    return FieldAvailability(
        field=field, value=value, state=state, reason_code=reason,
        period_end=period, source_accession=accession, source_kind="practical_policy",
        evidence_class="reported_component_reconciliation", freshness="current",
        fallback_level="reported_aggregate", covered_fields=covered_fields,
        coverage_basis="reconciled_disjoint_components",
        coverage_source_facts=tuple(sorted({_ref(accession, period, row) for row in sources})),
        economic_scope=scope, extraction_complete=True,
        searched_concepts=tuple(sorted({str(row["qname"]) for row in sources})),
        authority="production", mapping_version=VERSION,
    )


def bind_pharma_bridge(policy: Mapping[str, Any], structural: Mapping[str, Any],
                       *, accession: str, period: str) -> tuple[tuple[FieldAvailability, ...], dict[str, Any]]:
    ticker = str(policy.get("ticker"))
    rule = RULES.get(ticker)
    if rule is None or not _same(policy, rule):
        raise RuntimeError("WG39 pharmaceutical bridge policy identity/version mismatch")
    rows = _current_rows(structural, rule=rule, accession=accession, period=period)
    records: list[FieldAvailability] = []
    proof: dict[str, Any] = {"status": "source_bound", "policy_version": VERSION,
                            "ticker": ticker, "accession": accession, "period_end": period}

    if rule["mode"] == "cash_and_split_debt":
        cash = _unique(rows, rule["cash_qname"])
        if rule["cash_parent"] not in cash.get("presentation_parents", ()):
            raise ValueError("WG39 BIIB cash fact is not in current assets")
        marketable = [_unique(rows, qname) for qname in rule["marketable_zero_qnames"]]
        if any(_number(row.get("value"), "BIIB marketable securities") != 0 for row in marketable):
            raise ValueError("WG39 BIIB marketable securities are no longer zero")
        current = _unique(rows, rule["debt_current_qname"])
        noncurrent = _unique(rows, rule["debt_noncurrent_qname"])
        excluded_debt = [row for row in rows if row.get("qname") in rule["excluded_debt_qnames"]]
        if any(_number(row.get("value"), "BIIB additional debt") != 0 for row in excluded_debt):
            raise ValueError("WG39 BIIB has additional debt or finance-lease balance outside the split debt scope")
        cash_value = _number(cash["value"], "BIIB cash")
        current_value = _number(current["value"], "BIIB current debt")
        noncurrent_value = _number(noncurrent["value"], "BIIB noncurrent debt")
        debt_value = current_value + noncurrent_value
        records.extend((
            _availability(field="cash", value=cash_value, state="reported", reason="CURRENT_CASH_REPORTED",
                accession=accession, period=period, sources=[cash], covered_fields=("cash",),
                scope="period-end cash and cash equivalents"),
            _availability(field="marketable_securities_current", value=0., state="evidence_backed_zero",
                reason="CURRENT_MARKETABLE_SECURITIES_REPORTED_ZERO", accession=accession, period=period,
                sources=marketable, covered_fields=("marketable_securities_current",),
                scope="reported current available-for-sale debt securities"),
            _availability(field="marketable_securities_noncurrent", value=0., state="evidence_backed_zero",
                reason="NONCURRENT_MARKETABLE_SECURITIES_REPORTED_ZERO", accession=accession, period=period,
                sources=marketable, covered_fields=("marketable_securities_noncurrent",),
                scope="reported noncurrent available-for-sale debt securities"),
            _availability(field="total_interest_bearing_debt", value=debt_value, state="reported",
                reason="CURRENT_AND_NONCURRENT_DEBT_COMPONENTS_RECONCILED", accession=accession, period=period,
                sources=[current, noncurrent, *excluded_debt], covered_fields=DEBT_FIELDS,
                scope="current secured term loan plus noncurrent notes payable and term loan, counted once"),
        ))
        proof.update({"cash":cash_value,"current_debt":current_value,
                      "noncurrent_debt":noncurrent_value,"total_debt":debt_value})

    elif rule["mode"] == "cash_debt_with_royalty_component":
        cash = _unique(rows, rule["cash_qname"])
        if rule["cash_parent"] not in cash.get("presentation_parents", ()):
            raise ValueError("WG39 GILD cash fact is not in current assets")
        separate_cash = [row for row in rows if row.get("qname") in rule["searched_separate_cash_qnames"]]
        if any(_number(row.get("value"), "separate cash") != 0 for row in separate_cash):
            raise ValueError("WG39 GILD combined cash conflicts with a separate cash or restricted-cash balance")
        marketable = [_unique(rows, qname) for qname in rule["marketable_zero_qnames"]]
        if any(_number(row.get("value"), "GILD marketable securities") != 0 for row in marketable):
            raise ValueError("WG39 GILD marketable securities are no longer zero")
        total = _unique(rows, rule["debt_total_qname"])
        current_aliases = [_unique(rows, qname) for qname in rule["debt_current_alias_qnames"]]
        current_values = {_number(row["value"], "GILD current debt") for row in current_aliases}
        if len(current_values) != 1:
            raise ValueError("WG39 GILD current-debt aliases conflict")
        current = current_values.pop()
        noncurrent_row = _unique(rows, rule["debt_noncurrent_qname"])
        noncurrent = _number(noncurrent_row["value"], "GILD noncurrent debt")
        total_value = _number(total["value"], "GILD total debt")
        if not isclose(total_value, current + noncurrent, rel_tol=1e-12, abs_tol=max(_precision(total), *(_precision(row) for row in current_aliases), _precision(noncurrent_row))):
            raise ValueError("WG39 GILD current and noncurrent debt do not reconcile to total")
        excluded_debt = [row for row in rows if row.get("qname") in rule["excluded_debt_qnames"]]
        if any(_number(row.get("value"), "GILD additional debt") != 0 for row in excluded_debt):
            raise ValueError("WG39 GILD has an additional debt or finance-lease balance outside total debt")

        royalty_component = _unique(rows, rule["royalty_debt_component_qname"], dimensions={
            rule["royalty_debt_axis"]: rule["royalty_debt_member"]})
        senior_matches = [row for row in rows if row.get("qname") == rule["senior_debt_component_qname"]
                          and str(_dims(row).get(rule["senior_debt_axis"], "")).rsplit(":", 1)[-1]
                          == rule["senior_debt_member_local_name"]]
        if not senior_matches:
            raise ValueError("WG39 GILD senior-debt component total is missing")
        senior_values = {_number(row.get("value"), "GILD senior debt") for row in senior_matches}
        if len(senior_values) != 1:
            raise ValueError("WG39 GILD senior-debt component total conflicts")
        senior = senior_matches[0]
        royalty_rows = [row for row in rows if row.get("qname") == rule["royalty_qname"]
                        and str(_dims(row).get(rule["royalty_acquisition_axis"], "")).rsplit(":", 1)[-1]
                        == rule["royalty_acquisition_member_local_name"]]
        carrying = [row for row in royalty_rows if _dims(row).get(rule["measurement_basis_axis"]) == rule["carrying_basis_member"]]
        fair_value = [row for row in royalty_rows if _dims(row).get(rule["measurement_basis_axis"]) == rule["fair_value_basis_member"]]
        if not carrying or len({_number(row["value"], "GILD royalty carrying") for row in carrying}) != 1:
            raise ValueError("WG39 GILD royalty carrying presentation is missing or conflicting")
        if not fair_value or len({_number(row["value"], "GILD royalty fair value") for row in fair_value}) != 1:
            raise ValueError("WG39 GILD royalty fair-value presentation is missing or conflicting")
        carrying_row, fair_row = carrying[0], fair_value[0]
        component_value = _number(royalty_component["value"], "GILD royalty debt component")
        carrying_value = _number(carrying_row["value"], "GILD royalty carrying")
        if abs(component_value - carrying_value) > _precision(royalty_component) + _precision(carrying_row):
            raise ValueError("WG39 GILD royalty debt component does not reconcile to carrying disclosure")
        if abs(_number(senior["value"], "GILD senior debt") + component_value - total_value) > _precision(senior) + _precision(royalty_component) + _precision(total):
            raise ValueError("WG39 GILD senior debt plus royalty component does not reconcile to total debt")

        all_facts = [row for row in structural.get("facts", ()) if isinstance(row, Mapping)
                     and row.get("source_accession") == accession and row.get("unit") == "USD"
                     and row.get("entity_scheme") == "http://www.sec.gov/CIK"
                     and str(row.get("entity_identifier", "")).zfill(10) == rule["cik"]]
        prior_royalty = [row for row in all_facts if row.get("qname") == rule["royalty_debt_component_qname"]
                         and row.get("period_start") is None and isinstance(row.get("period_end"), str)
                         and row["period_end"] < period
                         and _dims(row) == {rule["royalty_debt_axis"]: rule["royalty_debt_member"]}]
        if not prior_royalty:
            raise ValueError("WG39 GILD prior royalty debt component is missing")
        prior_period = max(str(row["period_end"]) for row in prior_royalty)
        prior_royalty = [row for row in prior_royalty if row["period_end"] == prior_period]
        if len({_number(row["value"], "GILD prior royalty debt") for row in prior_royalty}) != 1:
            raise ValueError("WG39 GILD prior royalty debt component conflicts")
        prior_royalty_row = prior_royalty[0]
        matured = [row for row in all_facts if row.get("qname") == rule["matured_debt_qname"]
                   and row.get("period_start") is None
                   and str(_dims(row).get(rule["matured_debt_axis"], "")).rsplit(":", 1)[-1]
                   == rule["matured_debt_member_local_name"]]
        current_matured = [row for row in matured if row.get("period_end") == period]
        prior_matured = [row for row in matured if row.get("period_end") == prior_period]
        if (not current_matured or not prior_matured
            or len({_number(row["value"], "GILD matured debt") for row in current_matured}) != 1
            or len({_number(row["value"], "GILD prior matured debt") for row in prior_matured}) != 1):
            raise ValueError("WG39 GILD matured debt rollforward is missing or conflicting")
        repayment = [row for row in all_facts if row.get("qname") == rule["repayment_qname"]
                     and row.get("period_end") == period and isinstance(row.get("period_start"), str)
                     and not _dims(row)]
        if not repayment or len({_number(row["value"], "GILD debt repayment") for row in repayment}) != 1:
            raise ValueError("WG39 GILD financing repayment is missing or conflicting")
        repayment_row = repayment[0]
        royalty_principal = _number(prior_royalty_row["value"], "GILD prior royalty debt") - component_value
        matured_principal = _number(prior_matured[0]["value"], "GILD prior matured debt") - _number(current_matured[0]["value"], "GILD current matured debt")
        repayment_value = _number(repayment_row["value"], "GILD debt repayment")
        if royalty_principal < 0 or matured_principal < 0:
            raise ValueError("WG39 GILD debt rollforward has an unsupported increase")
        if abs(royalty_principal + matured_principal - repayment_value) > (
            _precision(prior_royalty_row) + _precision(royalty_component)
            + _precision(prior_matured[0]) + _precision(current_matured[0]) + _precision(repayment_row)
        ):
            raise ValueError("WG39 GILD royalty and matured-debt reductions do not reconcile to financing repayments")

        cash_sources = [cash, *separate_cash]
        debt_sources = [total, *current_aliases, noncurrent_row, *excluded_debt, senior, royalty_component,
                        carrying_row, fair_row, current_matured[0], repayment_row]
        records.extend((
            _availability(field="cash", value=_number(cash["value"], "GILD cash"), state="reported",
                reason="CURRENT_CASH_REPORTED", accession=accession, period=period, sources=cash_sources,
                covered_fields=("cash",), scope="current cash and cash equivalents; no separate restricted-cash balance"),
            _availability(field="marketable_securities_current", value=0., state="evidence_backed_zero",
                reason="CURRENT_MARKETABLE_SECURITIES_REPORTED_ZERO", accession=accession, period=period,
                sources=marketable, covered_fields=("marketable_securities_current",), scope="reported current marketable securities"),
            _availability(field="marketable_securities_noncurrent", value=0., state="evidence_backed_zero",
                reason="NONCURRENT_MARKETABLE_SECURITIES_REPORTED_ZERO", accession=accession, period=period,
                sources=marketable, covered_fields=("marketable_securities_noncurrent",), scope="reported noncurrent marketable securities"),
            _availability(field="total_interest_bearing_debt", value=total_value, state="reported",
                reason="TOTAL_DEBT_INCLUDES_FUTURE_ROYALTY_COMPONENT", accession=accession, period=period,
                sources=debt_sources, covered_fields=DEBT_FIELDS,
                scope="all current and noncurrent debt, including the Immunomedics future-royalty carrying component, counted once"),
        ))
        proof.update({"cash": _number(cash["value"], "GILD cash"), "total_debt": total_value,
                      "current_debt": current, "noncurrent_debt": noncurrent,
                      "royalty_debt_component": component_value,
                      "royalty_carrying_disclosure": carrying_value,
                      "royalty_fair_value_diagnostic": _number(fair_row["value"], "GILD royalty fair value"),
                      "royalty_principal_financing_reduction": royalty_principal,
                      "matured_note_financing_reduction": matured_principal,
                      "reported_financing_repayments": repayment_value,
                      "royalty_cash_reconciliation_sources": [
                          {"qname":row["qname"], "value":float(row["value"]),
                           "period_start":row.get("period_start"), "period_end":row["period_end"],
                           "context_id":row.get("context_id"), "dimensions":row.get("dimensions") or []}
                          for row in (prior_royalty_row, royalty_component, prior_matured[0], current_matured[0], repayment_row)
                      ],
                      "royalty_treatment": "included once in total debt; principal reduction reconciles inside financing repayments; fair value is diagnostic and not additive"})

    elif rule["mode"] == "cashlike_debt_and_strategic_investments":
        current = _unique(rows, rule["marketable_current_qname"])
        alias = _unique(rows, rule["marketable_current_alias_qname"])
        maturity = [_unique(rows, qname) for qname in rule["marketable_maturity_qnames"]]
        marketable_value = _number(current["value"], "INCY current marketable securities")
        if _number(alias["value"], "INCY marketable alias") != marketable_value:
            raise ValueError("WG39 INCY current marketable-security aliases conflict")
        if not isclose(sum(_number(row["value"], "INCY security maturity") for row in maturity), marketable_value,
                       rel_tol=1e-12, abs_tol=_precision(current) + sum(_precision(row) for row in maturity)):
            raise ValueError("WG39 INCY maturity schedule does not reconcile to current marketable securities")
        noncurrent = [row for row in rows if row.get("qname") in rule["searched_noncurrent_marketable_qnames"]]
        if any(_number(row.get("value"), "INCY noncurrent marketable security") != 0 for row in noncurrent):
            raise ValueError("WG39 INCY has a separate noncurrent marketable debt security")
        strategic = _unique(rows, rule["excluded_strategic_investment_qname"])
        hierarchy = [row for row in rows if row.get("qname") == rule["excluded_strategic_investment_qname"]
                     and _dims(row).get(rule["fair_value_level_axis"]) in {
                         rule["level_1_member"], rule["level_2_member"], rule["level_3_member"]}]
        hierarchy_by_level: dict[str, float] = {}
        hierarchy_rows: list[Mapping[str, Any]] = []
        for member in (rule["level_1_member"], rule["level_2_member"], rule["level_3_member"]):
            matches = [row for row in hierarchy if _dims(row).get(rule["fair_value_level_axis"]) == member]
            if not matches or len({_number(row["value"], "INCY strategic investment hierarchy") for row in matches}) != 1:
                raise ValueError("WG39 INCY strategic-investment hierarchy is incomplete or conflicting")
            hierarchy_by_level[member] = _number(matches[0]["value"], "INCY strategic investment hierarchy")
            hierarchy_rows.append(matches[0])
        if not isclose(sum(hierarchy_by_level.values()), _number(strategic["value"], "INCY strategic investments"),
                       rel_tol=1e-12, abs_tol=_precision(strategic) + sum(_precision(row) for row in hierarchy_rows)):
            raise ValueError("WG39 INCY strategic-investment hierarchy does not reconcile")

        debt_rows = [_unique(rows, qname) for qname in rule["debt_component_qnames"]]
        zero_borrowing = _unique(rows, rule["zero_borrowing_qname"], dimensions={
            rule["zero_borrowing_axis"]: rule["zero_borrowing_member"]})
        if _number(zero_borrowing["value"], "INCY revolving credit borrowing") != 0:
            raise ValueError("WG39 INCY revolving credit facility has a nonzero borrowing")
        excluded_debt = [row for row in rows if row.get("qname") in rule["excluded_debt_qnames"]]
        if any(_number(row.get("value"), "INCY additional debt") != 0 for row in excluded_debt):
            raise ValueError("WG39 INCY has additional debt outside the finance-lease components")
        debt_value = sum(_number(row["value"], "INCY finance lease") for row in debt_rows)
        marketable_sources = [current, alias, *maturity, *noncurrent, strategic, *hierarchy_rows]
        records.extend((
            _availability(field="marketable_securities_current", value=marketable_value, state="reported",
                reason="CURRENT_AVAILABLE_FOR_SALE_DEBT_SECURITIES_RECONCILED", accession=accession,
                period=period, sources=marketable_sources, covered_fields=("marketable_securities_current",),
                scope="current available-for-sale debt securities; strategic noncurrent equity investments excluded"),
            _availability(field="marketable_securities_noncurrent", value=0., state="evidence_backed_zero",
                reason="NO_SEPARATE_NONCURRENT_MARKETABLE_DEBT_SECURITY", accession=accession,
                period=period, sources=marketable_sources, covered_fields=("marketable_securities_noncurrent",),
                scope="no separate noncurrent cash-like debt security; strategic equity investments remain non-cash assets"),
            _availability(field="total_interest_bearing_debt", value=debt_value, state="reported",
                reason="FINANCE_LEASE_DEBT_COMPONENTS_RECONCILED", accession=accession, period=period,
                sources=[*debt_rows, zero_borrowing, *excluded_debt], covered_fields=DEBT_FIELDS,
                scope="current and noncurrent finance-lease obligations; zero revolving-credit borrowing and complete debt search have no other nonzero financing balance"),
        ))
        proof.update({"marketable_securities_current": marketable_value,
                      "marketable_securities_noncurrent": 0., "finance_lease_debt": debt_value,
                      "revolving_credit_borrowing": 0.,
                      "strategic_equity_investments_excluded_from_cash": _number(strategic["value"], "INCY strategic investments"),
                      "strategic_investment_hierarchy": hierarchy_by_level})
    else:
        raise RuntimeError("unsupported WG39 pharmaceutical bridge mode")

    return tuple(records), proof
