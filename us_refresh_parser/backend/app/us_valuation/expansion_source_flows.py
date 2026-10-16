"""Additional exact-period source observations for private expansion bindings.

Compose the existing identity/precision/provenance checks with caller-supplied
cash-period anchors. Selection never establishes an accounting role by QName,
never fills a missing fact with zero and never changes the Step 4 ledgers.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .expansion_period_inputs import (
    _assert_no_source_conflicts, _derived_ttm, _receipt_map, _source_row,
    _structural_form, _structural_role, _structural_rows, _unit,
    _verified_structural_identity,
)


def exact_flow(packet: Mapping[str, Any], anchor: Mapping[str, Any], concepts: Sequence[str], *,
               current_accession_only: bool = False) -> dict[str, Any] | None:
    cutoff = packet["cutoff"]
    cik = str(packet["issuer"]["cik"]).zfill(10)
    if str(packet["companyfacts"]["cik"]).zfill(10) != cik or str(packet["submissions"]["cik"]).zfill(10) != cik:
        raise ValueError("additional flow issuer envelopes differ")
    if not concepts or len(set(concepts)) != len(concepts):
        raise ValueError("explicit unique source concepts required")
    references = [value if ":" in value else "us-gaap:" + value for value in concepts]
    start, end = anchor["period_start"], anchor["period_end"]
    if not start or not end or end > cutoff:
        raise ValueError("additional flow anchor is not cutoff eligible")
    required_accession = packet["controlling_filing"]["accessionNumber"] if current_accession_only else None
    permitted_forms = {"10-Q", "10-Q/A"} if current_accession_only else {"10-K", "10-K/A"}
    receipts = _receipt_map(packet)
    structural, aggregate = [], []
    for fact in _structural_rows(packet):
        if (fact.get("qname") not in references or not _verified_structural_identity(fact, cik)
            or fact.get("dimensions") or _unit(fact.get("unit")) != "USD"
            or (fact.get("period_start"), fact.get("period_end")) != (start, end)
            or _structural_form(fact) not in permitted_forms
            or not fact.get("filed_date") or fact["filed_date"] > cutoff
            or (required_accession and fact.get("source_accession") != required_accession)):
            continue
        structural.append(dict(fact))
    _assert_no_source_conflicts(structural, "additional_flow")
    for reference in references:
        namespace, concept = reference.split(":", 1)
        for fact in packet["companyfacts"].get("facts", {}).get(namespace, {}).get(concept, {}).get("units", {}).get("USD", []):
            if ((fact.get("start"), fact.get("end")) != (start, end) or fact.get("form") not in permitted_forms
                or not fact.get("filed") or fact["filed"] > cutoff
                or (required_accession and fact.get("accn") != required_accession)):
                continue
            aggregate.append({**fact, "qname": reference, "unit": "USD", "value": fact.get("val"),
                              "period_start": start, "period_end": end, "source_accession": fact.get("accn")})
    # A parsed fact's reported precision controls duplicate feed rounding for
    # that same source identity. CompanyFacts-only conflicts stay fail-closed.
    structural_sources = {(fact["qname"], fact["source_accession"]) for fact in structural}
    _assert_no_source_conflicts((fact for fact in aggregate if (fact["qname"], fact["source_accession"]) not in structural_sources), "additional_flow")
    selected = None
    for reference in references:
        structural_rows = [fact for fact in structural if fact["qname"] == reference]
        aggregate_rows = [fact for fact in aggregate if fact["qname"] == reference]
        eligible = structural_rows or aggregate_rows
        if eligible:
            selected = max(eligible, key=lambda fact: (str(fact.get("filed_date", fact.get("filed", ""))), str(fact.get("source_accession", ""))))
            break
    if selected is None:
        return None
    is_structural = selected in structural
    accession = selected["source_accession"]
    return _source_row(field="additional_flow", qname=selected["qname"], value=selected["value"], unit="USD",
        start=start, end=end, accession=accession, form=_structural_form(selected) if is_structural else selected["form"],
        filed=selected.get("filed_date", selected.get("filed")),
        context_id=selected.get("context_id"), dimensions=selected.get("dimensions", []),
        statement_role=_structural_role(selected), decimals=selected.get("decimals"),
        source_kind="structural_filing_fact" if is_structural else "companyfacts_exact_annual_fact",
        receipt=receipts.get(accession), selection_reason="Exact frozen cash-period anchor; role qualification is separate.")


def additional_flow_series(packet: Mapping[str, Any], core_periods: Mapping[str, Any], concepts: Sequence[str]) -> dict[str, Any]:
    anchors = core_periods["fields"]["operating_cash_flow"]
    annual = [exact_flow(packet, anchor, concepts) for anchor in anchors["annual"]]
    current = exact_flow(packet, anchors["current_fiscal_ytd"], concepts, current_accession_only=True) if anchors["current_fiscal_ytd"] else None
    prior = exact_flow(packet, anchors["prior_fiscal_ytd"], concepts, current_accession_only=True) if anchors["prior_fiscal_ytd"] else None
    ttm = _derived_ttm([annual[-1]], current, prior) if annual and annual[-1] else None
    return {"concepts_requested": list(concepts), "annual": annual, "current_fiscal_ytd": current,
            "prior_fiscal_ytd": prior, "derived_ttm": ttm,
            "missing_annual_ends": [anchor["period_end"] for anchor, fact in zip(anchors["annual"], annual) if fact is None],
            "missing_current": current is None if anchors["current_fiscal_ytd"] else False,
            "missing_prior": prior is None if anchors["prior_fiscal_ytd"] else False,
            "role_qualified": False, "missing_value_policy": "gap_not_zero"}


__all__ = ["additional_flow_series", "exact_flow"]
