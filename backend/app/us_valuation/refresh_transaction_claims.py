"""Source-bound acquisition/licensing payment classification for WG11."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import isclose, isfinite
import re
from types import MappingProxyType
from typing import Any, Mapping

from .refresh_narrative_evidence import narrative_policy, terms_by_name


SCHEMA = "FINSIGHT-TRANSACTION-CLAIMS-1"
VERSION = "FINSIGHT-TRANSACTION-CLAIMS-WG11-1"
_ISSUER_NAMESPACE = re.compile(r"^https?://www\.bms\.com/[0-9]{8}$")

RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "BMY": MappingProxyType({
        "schema_version": SCHEMA,
        "version": VERSION,
        "ticker": "BMY",
        "cik": "0000014272",
        "recognized_cvr_local_name": "ContingentValueRightsNoncurrent",
        "upfront_local_name": "LicenseAndOtherArrangementsUpfrontPayments",
        "anniversary_local_name": "LicenseAndOtherArrangementsAnniversaryPayments",
        "milestone_maximum_local_name": "ContingentAndRegulatoryMilestonePaymentsMaximumAggregate",
        "agreement_member": "HengruiLicenseAgreementsMember",
        "counterparty_member": "HengruiMember",
        "forecast_member": "ScenarioForecastMember",
        "treatment": "deduct recognized CVR and fixed unpaid consideration once; paid cash and contingent maxima remain separate; incomplete fixed-payment timing blocks valuation",
    }),
})


def transaction_claim_policy(ticker: str) -> dict[str, Any]:
    rule = RULES.get(ticker.upper())
    if rule is None:
        raise ValueError(f"no transaction claim policy for {ticker!r}")
    return {**deepcopy(dict(rule)), "narrative_evidence_policy": narrative_policy(ticker)}


def _local(value: Any) -> str:
    return str(value).split(":")[-1]


def _valid(row: Mapping[str, Any], *, policy: Mapping[str, Any], accession: str) -> None:
    if (
        row.get("source_accession") != accession
        or row.get("unit") != "USD"
        or str(row.get("entity_identifier", "")).zfill(10) != policy["cik"]
        or row.get("entity_scheme") != "http://www.sec.gov/CIK"
        or not _ISSUER_NAMESPACE.fullmatch(str(row.get("namespace", "")))
        or isinstance(row.get("value"), bool)
        or not isinstance(row.get("value"), (int, float))
        or not isfinite(float(row["value"]))
        or float(row["value"]) < 0
    ):
        raise ValueError("transaction claim source identity, unit, namespace or amount is invalid")


def _dimensions(row: Mapping[str, Any]) -> set[str]:
    return {_local(member) for pair in row.get("dimensions", []) if isinstance(pair, list) and len(pair) == 2 for member in pair[1:]}


def _one(facts: list[dict[str, Any]], *, policy: Mapping[str, Any], accession: str, local_name: str,
         period_start: str | None = None, period_end: str | None = None, dimensions: bool) -> dict[str, Any]:
    rows = []
    required = {policy["agreement_member"], policy["counterparty_member"], policy["forecast_member"]}
    for row in facts:
        if row.get("local_name") != local_name:
            continue
        if period_start is not None and row.get("period_start") != period_start:
            continue
        if period_end is not None and row.get("period_end") != period_end:
            continue
        if dimensions and _dimensions(row) != required:
            continue
        if not dimensions and row.get("dimensions") not in (None, []):
            continue
        _valid(row, policy=policy, accession=accession)
        rows.append(dict(row))
    if len(rows) != 1:
        raise ValueError(f"transaction claim source fact is missing or ambiguous: {local_name} {period_end or 'any period'}")
    return rows[0]


def select_transaction_claim(policy: Mapping[str, Any], structural: Mapping[str, Any], controlling: Mapping[str, Any], cik: str, cutoff: str) -> dict[str, Any]:
    expected = transaction_claim_policy(str(policy.get("ticker", "")))
    if dict(policy) != expected or str(cik).zfill(10) != expected["cik"]:
        raise RuntimeError("transaction claim policy identity/version mismatch")
    accession = controlling.get("accessionNumber") or controlling.get("accession")
    period = controlling.get("reportDate") or controlling.get("period_end")
    filed = controlling.get("filingDate") or structural.get("filed_date")
    if structural.get("source_accession") != accession or not isinstance(period, str) or not isinstance(filed, str) or not period <= filed <= cutoff:
        raise ValueError("transaction claim filing identity/cutoff mismatch")
    date.fromisoformat(period); date.fromisoformat(filed); date.fromisoformat(cutoff)
    receipt = structural.get("narrative_evidence")
    if not isinstance(receipt, Mapping) or receipt.get("policy") != policy["narrative_evidence_policy"]:
        raise ValueError("transaction narrative evidence is missing or mismatched")
    if (receipt.get("ticker"), receipt.get("cik")) != (policy["ticker"], policy["cik"]):
        raise ValueError("transaction narrative issuer identity mismatch")
    filing = receipt.get("filing") or {}
    if (filing.get("accession"), filing.get("form"), filing.get("report_date"), filing.get("filed_date")) != (accession, controlling.get("form"), period, filed):
        raise ValueError("transaction narrative filing identity mismatch")
    narrative = terms_by_name(receipt)
    required_terms = {
        "hengrui_upfront_payment", "hengrui_first_anniversary_payment", "hengrui_second_anniversary_payment",
        "hengrui_contingent_milestone_maximum", "biontech_paid_upfront_payment",
        "biontech_future_anniversary_payments", "biontech_contingent_milestone_maximum",
    }
    if set(narrative) != required_terms:
        raise ValueError("transaction narrative term set changed")
    facts = structural.get("facts")
    if not isinstance(facts, list):
        raise ValueError("transaction structural facts are missing")
    quarter_starts={"first quarter":("01-01","03-31"),"second quarter":("04-01","06-30"),
                    "third quarter":("07-01","09-30"),"fourth quarter":("10-01","12-31")}
    upfront_term=narrative["hengrui_upfront_payment"]
    quarter=upfront_term.get("quarter");upfront_year=upfront_term.get("year")
    if quarter not in quarter_starts or not isinstance(upfront_year,int):
        raise ValueError("Hengrui upfront timing is invalid")
    upfront_start,upfront_end=(f"{upfront_year}-{part}" for part in quarter_starts[quarter])
    first_year=narrative["hengrui_first_anniversary_payment"].get("year")
    second_year=narrative["hengrui_second_anniversary_payment"].get("year")
    if not isinstance(first_year,int) or not isinstance(second_year,int) or second_year<=first_year:
        raise ValueError("Hengrui anniversary timing is invalid")
    cvr = _one(facts, policy=policy, accession=accession, local_name=policy["recognized_cvr_local_name"],
               period_start=None, period_end=period, dimensions=False)
    upfront = _one(facts, policy=policy, accession=accession, local_name=policy["upfront_local_name"],
                   period_start=upfront_start, period_end=upfront_end, dimensions=True)
    first = _one(facts, policy=policy, accession=accession, local_name=policy["anniversary_local_name"],
                 period_start=f"{first_year}-01-01", period_end=f"{first_year}-12-31", dimensions=True)
    second = _one(facts, policy=policy, accession=accession, local_name=policy["anniversary_local_name"],
                  period_start=f"{second_year}-01-01", period_end=f"{second_year}-12-31", dimensions=True)
    maximum = _one(facts, policy=policy, accession=accession, local_name=policy["milestone_maximum_local_name"],
                   dimensions=True)
    checks = {
        "hengrui_upfront_payment": upfront, "hengrui_first_anniversary_payment": first,
        "hengrui_second_anniversary_payment": second, "hengrui_contingent_milestone_maximum": maximum,
    }
    for name, row in checks.items():
        if not isclose(float(row["value"]), float(narrative[name]["value"]), rel_tol=0, abs_tol=.01):
            raise ValueError(f"transaction narrative and structural value conflict: {name}")
    fixed_hengrui = sum(float(row["value"]) for row in (upfront, first, second))
    recognized_cvr = float(cvr["value"])
    current_claim = recognized_cvr + fixed_hengrui
    return {
        "status": "review_required",
        "claim_adjustment": None,
        "review_reasons": ["biontech_fixed_payment_schedule_has_only_a_timing_envelope"],
        "policy": dict(policy),
        "period_end": period,
        "controlling_accession": accession,
        "components": {
            "recognized_cvr_liability": recognized_cvr,
            "hengrui_fixed_unpaid_payments": fixed_hengrui,
            "currently_modeled_claim": current_claim,
            "hengrui_contingent_maximum_excluded": float(maximum["value"]),
            "biontech_paid_cash_excluded": float(narrative["biontech_paid_upfront_payment"]["value"]),
            "biontech_fixed_payment_timing_envelope": float(narrative["biontech_future_anniversary_payments"]["value"]),
            "biontech_contingent_maximum_excluded": float(narrative["biontech_contingent_milestone_maximum"]["value"]),
        },
        "source_rows": [cvr, upfront, first, second, maximum],
        "narrative_evidence": dict(receipt),
        "formula": "recognized CVR plus separately dated fixed unpaid consideration; paid cash and contingent maxima excluded; timing-incomplete fixed envelope blocks valuation",
    }


__all__ = ["RULES", "SCHEMA", "VERSION", "select_transaction_claim", "transaction_claim_policy"]
