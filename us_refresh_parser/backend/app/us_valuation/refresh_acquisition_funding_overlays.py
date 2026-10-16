"""Completed-acquisition funding overlays without invented post-close economics.

The source rules contain issuer structure and approved scenario factors, never
filing amounts, accessions, or dates.  Narrative values are re-extracted from
hashed filing bytes and reconciled to the current structural balance sheet.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from math import isclose, isfinite
import re
from types import MappingProxyType
from typing import Any, Mapping

from .refresh_narrative_evidence import narrative_policy, terms_by_name


SCHEMA = "FINSIGHT-ACQUISITION-FUNDING-OVERLAY-1"
VERSION = "FINSIGHT-ACQUISITION-FUNDING-OVERLAY-WG21-1"
_GAAP = re.compile(r"^https?://(?:fasb\.org|xbrl\.us-gaap)/us-gaap/20\d{2}$")


RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "ECL": MappingProxyType({
        "schema_version": SCHEMA, "version": VERSION, "ticker": "ECL", "cik": "0000031462",
        "mode": "preclose_financing_in_current_balance",
        "narrative_evidence_policy": narrative_policy("ECL"),
        "cash_qname": "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "debt_total_qname": "us-gaap:DebtAndCapitalLeaseObligations",
        "debt_component_qnames": (
            "us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent",
            "us-gaap:LongTermDebtAndCapitalLeaseObligations",
        ),
        "nci_qname": "us-gaap:MinorityInterest",
        "benefit_liability_qname": "us-gaap:PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",
        "benefit_asset_qname": "us-gaap:DefinedBenefitPlanAssetsForPlanBenefitsNoncurrent",
        "benefit_contribution_qname": "us-gaap:PensionAndOtherPostretirementBenefitContributions",
        "benefit_expense_qname": "us-gaap:PensionAndOtherPostretirementBenefitExpense",
        "asset_proxy_factors": (0.75, 1.0, 1.25),
        "cash_consideration_factors": (1.05, 1.0, 0.95),
        "treatment": "convert pre-close acquisition cash into a bounded post-close operating-asset proxy while preserving current debt; transaction price is not intrinsic value",
    }),
    "PH": MappingProxyType({
        "schema_version": SCHEMA, "version": VERSION, "ticker": "PH", "cik": "0000076334",
        "mode": "postclose_new_loans_unreconciled_residual",
        "narrative_evidence_policy": narrative_policy("PH"),
        "cash_qname": "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "debt_component_qnames": (
            "us-gaap:CommercialPaper",
            "us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent",
            "us-gaap:LongTermDebtAndCapitalLeaseObligations",
        ),
        "nci_qname": "us-gaap:MinorityInterest",
        "preferred_qname": "us-gaap:PreferredStockValue",
        "preferred_shares_qname": "us-gaap:PreferredStockSharesIssued",
        "treatment": "retain the completed transaction and drawn loans as event evidence but block valuation until residual funding and the post-close cash/debt/share state are source-bound",
    }),
})


def acquisition_funding_overlay_policy(ticker: str) -> dict[str, Any]:
    rule = RULES.get(ticker.upper())
    if rule is None:
        raise ValueError(f"no acquisition funding overlay policy for {ticker!r}")
    return deepcopy(dict(rule))


def _context(policy: Mapping[str, Any], structural: Mapping[str, Any],
             controlling: Mapping[str, Any], cik: str, cutoff: str):
    expected = RULES.get(str(policy.get("ticker", "")))
    actual = deepcopy(dict(policy))
    canonical = deepcopy(dict(expected or {}))
    for value in (actual, canonical):
        value["debt_component_qnames"] = tuple(value.get("debt_component_qnames", ()))
        value["asset_proxy_factors"] = tuple(value.get("asset_proxy_factors", ()))
        value["cash_consideration_factors"] = tuple(value.get("cash_consideration_factors", ()))
    if expected is None or actual != canonical or str(cik).zfill(10) != canonical["cik"]:
        raise RuntimeError("acquisition funding overlay policy identity/version mismatch")
    accession = controlling.get("accessionNumber") or controlling.get("accession")
    period = controlling.get("reportDate") or controlling.get("period_end")
    filed = controlling.get("filingDate") or structural.get("filed_date")
    if (structural.get("source_accession") != accession
            or (structural.get("report_date") or structural.get("period_end")) != period
            or not isinstance(filed, str) or not str(period) <= filed <= cutoff):
        raise ValueError("acquisition funding structural identity/period/cutoff mismatch")
    date.fromisoformat(str(period)); date.fromisoformat(str(filed)); date.fromisoformat(cutoff)
    facts = structural.get("facts")
    if not isinstance(facts, list):
        raise ValueError("acquisition funding structural facts are missing")
    receipt = structural.get("narrative_evidence")
    if (not isinstance(receipt, Mapping)
            or receipt.get("policy") != canonical["narrative_evidence_policy"]
            or receipt.get("ticker") != canonical["ticker"]
            or str(receipt.get("cik", "")).zfill(10) != canonical["cik"]
            or receipt.get("extraction_version") != canonical["narrative_evidence_policy"]["version"]):
        raise ValueError("acquisition funding narrative evidence is missing or mismatched")
    narrative_filing = receipt.get("filing")
    if not isinstance(narrative_filing, Mapping) or not isinstance(narrative_filing.get("filed_date"), str):
        raise ValueError("acquisition funding narrative filing identity is incomplete")
    if narrative_filing["filed_date"] > cutoff:
        raise ValueError("acquisition funding narrative filing is after cutoff")
    if canonical["narrative_evidence_policy"].get("source_role") == "controlling_filing":
        if narrative_filing.get("accession") != accession:
            raise ValueError("acquisition funding narrative is not the controlling filing")
    elif narrative_filing.get("form") not in {"8-K", "8-K/A"}:
        raise ValueError("acquisition funding event narrative is not a current report")
    return canonical, str(accession), str(period), facts, receipt, terms_by_name(receipt)


def _one(facts: list[dict[str, Any]], *, policy: Mapping[str, Any], accession: str,
         period: str, qname: str, instant: bool = True) -> tuple[dict[str, Any], float]:
    rows = []
    for row in facts:
        if (not isinstance(row, Mapping) or row.get("qname") != qname
                or row.get("source_accession") != accession or row.get("period_end") != period
                or row.get("unit") != "USD" or bool(row.get("period_start") is None) != instant
                or row.get("dimensions") not in (None, [])):
            continue
        if (row.get("entity_scheme") != "http://www.sec.gov/CIK"
                or str(row.get("entity_identifier", "")).zfill(10) != policy["cik"]
                or not _GAAP.fullmatch(str(row.get("namespace", "")))):
            raise ValueError("acquisition funding structural fact identity mismatch")
        value = row.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
            raise ValueError("acquisition funding structural amount is invalid")
        rows.append(dict(row))
    values = {float(row["value"]) for row in rows}
    if not instant and rows:
        start = min(str(row["period_start"]) for row in rows)
        rows = [row for row in rows if row["period_start"] == start]
        values = {float(row["value"]) for row in rows}
    if not rows or len(values) != 1:
        raise ValueError(f"acquisition funding fact is missing or conflicting: {qname}")
    return rows[0], values.pop()


def select_acquisition_funding_overlay(policy: Mapping[str, Any], structural: Mapping[str, Any],
                                       controlling: Mapping[str, Any], cik: str, cutoff: str) -> dict[str, Any]:
    policy, accession, period, facts, receipt, narrative = _context(
        policy, structural, controlling, cik, cutoff
    )
    required = ({"acquisition_price", "close_date", "acquired_operating_scope",
                 "purchase_price_allocation_status", "pro_forma_status",
                 "integration_cost_treatment", "issued_note_principal", "issued_note_use",
                 "delayed_draw_facility_status"}
                if policy["ticker"] == "ECL" else
                {"acquisition_price", "close_date", "short_term_loan_principal",
                 "three_year_loan_principal", "loan_use"})
    if set(narrative) != required:
        raise ValueError("acquisition funding narrative term set changed")
    close_date = str(narrative["close_date"]["value"])
    if not period < close_date <= cutoff:
        raise ValueError("completed acquisition date is not after the balance date and inside cutoff")
    price = float(narrative["acquisition_price"]["value"])
    if not isfinite(price) or price <= 0:
        raise ValueError("acquisition price is not finite positive evidence")
    cash_row, cash = _one(facts, policy=policy, accession=accession, period=period,
                          qname=policy["cash_qname"])
    debt_rows = []
    debt_components = []
    for qname in policy["debt_component_qnames"]:
        row, value = _one(facts, policy=policy, accession=accession, period=period, qname=qname)
        debt_rows.append(row); debt_components.append(value)
    nci_row, nci = _one(facts, policy=policy, accession=accession, period=period,
                        qname=policy["nci_qname"])
    if min(cash, nci, *debt_components) < 0:
        raise ValueError("acquisition funding current balance sign requires review")
    sources = [cash_row, *debt_rows, nci_row]
    excluded: list[dict[str, Any]] = []
    components: dict[str, Any] = {
        "transaction_price_event_proxy": price,
        "close_date": close_date,
        "period_end_cash": cash,
        "period_end_debt_components": debt_components,
        "period_end_nci": nci,
        "transaction_price_is_intrinsic_value": False,
        "invented_acquired_fcff": None,
        "invented_synergies": None,
    }
    if policy["mode"] == "preclose_financing_in_current_balance":
        total_row, debt_total = _one(facts, policy=policy, accession=accession, period=period,
                                     qname=policy["debt_total_qname"])
        if not isclose(debt_total, sum(debt_components), rel_tol=1e-12, abs_tol=.01):
            raise ValueError("current acquisition financing debt does not reconcile")
        issued = float(narrative["issued_note_principal"]["value"])
        if (issued <= 0 or debt_total < issued or cash < price
                or narrative["issued_note_use"]["value"] != "acquisition_and_general_corporate_purposes"
                or narrative["delayed_draw_facility_status"]["value"] != "terminated_undrawn"):
            raise ValueError("pre-close acquisition funding does not reconcile to current balance")
        liability_row, liability = _one(
            facts, policy=policy, accession=accession, period=period,
            qname=policy["benefit_liability_qname"]
        )
        asset_row, asset = _one(
            facts, policy=policy, accession=accession, period=period,
            qname=policy["benefit_asset_qname"]
        )
        contribution_row, contribution = _one(
            facts, policy=policy, accession=accession, period=period,
            qname=policy["benefit_contribution_qname"], instant=False
        )
        expense_row, expense = _one(
            facts, policy=policy, accession=accession, period=period,
            qname=policy["benefit_expense_qname"], instant=False
        )
        if min(liability, asset, contribution, expense) < 0 or liability < asset:
            raise ValueError("benefit funded-status overlap requires review")
        benefit_claim = liability - asset
        adjustments = {}
        for case, asset_factor, cash_factor in zip(
            ("bear", "base", "bull"), policy["asset_proxy_factors"],
            policy["cash_consideration_factors"], strict=True,
        ):
            adjustments[f"{case}_cash_adjustment"] = round(price * (asset_factor - cash_factor), 2)
        sources.extend([total_row, liability_row, asset_row])
        excluded.extend([contribution_row, expense_row])
        components.update({
            "period_end_debt": debt_total,
            "issued_note_principal": issued,
            "financing_use": narrative["issued_note_use"]["value"],
            "terminated_delayed_draw_facility": True,
            "benefit_liability": liability,
            "benefit_plan_asset": asset,
            "benefit_net_claim": benefit_claim,
            "benefit_contributions_already_in_cash_flow": contribution,
            "benefit_expense_already_in_operating_results": expense,
            "asset_proxy_factors": list(policy["asset_proxy_factors"]),
            "cash_consideration_factors": list(policy["cash_consideration_factors"]),
            **adjustments,
        })
        return {
            "status": "source_bound", "claim_adjustment": benefit_claim,
            **adjustments, "scenario_adjustments": adjustments, "review_reasons": [],
            "policy": dict(policy), "source_rows": sources, "excluded_rows": excluded,
            "components": components, "period_end": period,
            "controlling_accession": accession, "narrative_evidence": dict(receipt),
            "formula": "current cash plus bounded acquired-asset proxy less acquisition cash; current debt once; net benefit claim once",
            "treatment": policy["treatment"],
        }
    if policy["mode"] == "postclose_new_loans_unreconciled_residual":
        preferred_row, preferred = _one(facts, policy=policy, accession=accession, period=period,
                                        qname=policy["preferred_qname"])
        loan_total = (float(narrative["short_term_loan_principal"]["value"])
                      + float(narrative["three_year_loan_principal"]["value"]))
        funding_gap = price - loan_total
        if min(preferred, loan_total, funding_gap) < 0:
            raise ValueError("post-close acquisition funding arithmetic is invalid")
        sources.append(preferred_row)
        components.update({
            "period_end_debt": sum(debt_components),
            "event_term_loans": loan_total,
            "arithmetic_funding_gap_not_a_reported_liability": funding_gap,
            "loan_use": narrative["loan_use"]["value"],
            "period_end_preferred_equity": preferred,
        })
        return {
            "status": "review_required", "claim_adjustment": None,
            "scenario_adjustments": None,
            "review_reasons": [
                "residual_purchase_funding_source_is_not_reported",
                "post_close_cash_debt_share_and_acquired_operating_scope_are_not_source_bound",
            ],
            "policy": dict(policy), "source_rows": sources, "excluded_rows": excluded,
            "components": components, "period_end": period,
            "controlling_accession": accession, "narrative_evidence": dict(receipt),
            "formula": "purchase price less drawn term loans is an unreconciled funding gap, not an invented claim",
            "treatment": policy["treatment"],
        }
    raise RuntimeError("unsupported acquisition funding overlay mode")


__all__ = ["RULES", "SCHEMA", "VERSION", "acquisition_funding_overlay_policy",
           "select_acquisition_funding_overlay"]
