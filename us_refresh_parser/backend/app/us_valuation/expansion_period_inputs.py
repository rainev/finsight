"""Source-only period and history inputs for the US expansion review.

This module is deliberately narrower than a valuation normalizer.  It selects
reported annual and cumulative-interim facts, keeps the issuer's actual tags,
periods, units, and accessions, and records what could not be selected.  A
TTM row is only the transparent FY + current fiscal YTD - prior comparable
fiscal YTD accounting identity; it is not a forecast, recipe, or valuation.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import isfinite
import re
from typing import Any, Iterable, Mapping, Sequence

from .table_first import inspect_tables
from .xbrl import CompanyFactsNormalizer, load_concept_config


VERSION = "US-EXPANSION-PERIOD-INPUTS-1"

# These are shared concept families, not issuer overrides.  The selected row's
# actual concept is always retained in the output.  In particular, net
# interest is intentionally not an alias for gross borrowing interest.
FIELD_CONCEPTS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",
        "us-gaap:Revenues",
        "us-gaap:SalesRevenueNet",
    ),
    "diluted_shares": (
        "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
        "us-gaap:WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
    ),
    "basic_shares": (
        "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
    ),
    "gross_interest_expense": (
        "us-gaap:InterestExpense",
        "us-gaap:InterestExpenseDebt",
        "us-gaap:InterestExpenseNonoperating",
    ),
    "net_interest_expense": (
        "us-gaap:InterestIncomeExpenseNonoperatingNet",
        "us-gaap:InterestExpenseNet",
    ),
    "operating_cash_flow": (
        "us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        "us-gaap:NetCashProvidedByUsedInOperatingActivities",
    ),
    "capital_expenditures": (
        "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
        "us-gaap:PaymentsToAcquireProductiveAssets",
        "us-gaap:PaymentsToAcquireOtherProductiveAssets",
    ),
    "sbc": (
        "us-gaap:AllocatedShareBasedCompensationExpense",
        "us-gaap:ShareBasedCompensation",
        "us-gaap:ShareBasedCompensationExpense",
    ),
}

FIELD_UNITS = {
    "revenue": "USD",
    "gross_interest_expense": "USD",
    "net_interest_expense": "USD",
    "diluted_shares": "shares",
    "basic_shares": "shares",
    "operating_cash_flow": "USD",
    "capital_expenditures": "USD",
    "sbc": "USD",
}


class SourceConflict(ValueError):
    """Raised internally when one source identity reports incompatible values."""


def _assert_no_source_conflicts(rows: Iterable[Mapping[str, Any]], field: str) -> None:
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = {}
    for row in rows:
        value = row.get("value", row.get("val"))
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        key = (
            row.get("qname") or row.get("concept"),
            row.get("source_accession") or row.get("accn"),
            row.get("period_start") or row.get("start"),
            row.get("period_end") or row.get("end"),
            row.get("unit"),
            row.get("form"),
        )
        grouped.setdefault(key, []).append(row)
    conflicts = []
    for key, candidates in grouped.items():
        values = {float(row.get("value", row.get("val"))) for row in candidates}
        if len(values) <= 1:
            continue
        # Structural parser duplicates can carry a precise value and a
        # rounded presentation duplicate.  Treat them as compatible only when
        # their reported decimal intervals overlap; CompanyFacts rows without
        # decimals therefore remain exact and fail closed on disagreement.
        lower, upper = max(values), min(values)
        intervals: list[tuple[float, float]] = []
        for row in candidates:
            value = float(row.get("value", row.get("val")))
            decimals = row.get("decimals")
            try:
                precision = int(decimals)
                radius = 0.5 * (10 ** (-precision))
            except (TypeError, ValueError, OverflowError):
                radius = 0.0
            intervals.append((value - radius, value + radius))
        lower = max(interval[0] for interval in intervals)
        upper = min(interval[1] for interval in intervals)
        if lower > upper:
            conflicts.append(key)
    if conflicts:
        raise SourceConflict(f"conflicting duplicate source facts for {field}: {conflicts[0]}")


def _date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _duration(start: object, end: object) -> int | None:
    first, last = _date(start), _date(end)
    if first is None or last is None or last < first:
        return None
    return (last - first).days + 1


def _unit(value: object) -> str:
    return str(value or "").removeprefix("xbrli:")


def _structural_form(row: Mapping[str, Any]) -> object:
    return row.get("form") or row.get("filing_form")


def _structural_role(row: Mapping[str, Any]) -> object:
    if row.get("statement_role"):
        return row.get("statement_role")
    roles = row.get("statement_roles")
    if isinstance(roles, list) and roles:
        return roles[0]
    return None


def _verified_structural_identity(row: Mapping[str, Any], cik: str | None) -> bool:
    """Require a parsed official US-GAAP fact with issuer identity."""

    qname = str(row.get("qname") or "")
    namespace = str(row.get("namespace") or "")
    if not qname.startswith("us-gaap:"):
        return False
    if not re.fullmatch(r"https?://fasb.org/us-gaap/20\d{2}", namespace):
        return False
    if not cik:
        return False
    entity = row.get("entity_identifier")
    if not isinstance(entity, str) or not entity:
        return False
    if str(entity).zfill(10) != str(cik).zfill(10):
        return False
    if row.get("entity_scheme") != "http://www.sec.gov/CIK":
        return False
    return True


def _qname(reference: str) -> tuple[str, str]:
    namespace, concept = reference.split(":", 1)
    return namespace, concept


def _filing_value(filing: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = filing.get(key)
        if value not in (None, ""):
            return value
    return None


def _controlling_filing(packet: Mapping[str, Any]) -> dict[str, Any]:
    value = packet.get("controlling_filing")
    return dict(value) if isinstance(value, Mapping) else {}


def _cutoff(packet: Mapping[str, Any], filing: Mapping[str, Any]) -> str | None:
    value = packet.get("cutoff") or filing.get("cutoff")
    if value is None:
        value = _filing_value(filing, "filingDate", "filed")
    return str(value) if value else None


def _filing_records(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Flatten the SEC submissions arrays for CompanyFactsNormalizer."""

    submissions = packet.get("submissions")
    if not isinstance(submissions, Mapping):
        return []
    recent = submissions.get("filings", {}).get("recent", {})
    if not isinstance(recent, Mapping):
        return []
    forms = recent.get("form", [])
    records: list[dict[str, Any]] = []
    for index, form in enumerate(forms):
        record = {
            "form": form,
            "accessionNumber": (recent.get("accessionNumber", [None] * len(forms))[index]),
            "filingDate": (recent.get("filingDate", [None] * len(forms))[index]),
            "reportDate": (recent.get("reportDate", [None] * len(forms))[index]),
            "primaryDocument": (recent.get("primaryDocument", [None] * len(forms))[index]),
        }
        records.append(record)
    return records


def _normalizer(packet: Mapping[str, Any], cutoff: str | None) -> CompanyFactsNormalizer | None:
    companyfacts = packet.get("companyfacts")
    if not isinstance(companyfacts, Mapping):
        return None
    try:
        config = deepcopy(load_concept_config())
        config["fields"] = dict(config.get("fields", {}))
        for field, concepts in FIELD_CONCEPTS.items():
            config["fields"][field] = {"unit": FIELD_UNITS[field], "concepts": list(concepts)}
        return CompanyFactsNormalizer(
            dict(companyfacts),
            config,
            as_of_date=cutoff,
            filing_records=_filing_records(packet),
        )
    except (TypeError, ValueError):
        # A source packet with an incomplete companyfacts fixture can still
        # provide structural facts.  The caller records the resulting gaps.
        return None


def _receipt_map(packet: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Collect any receipt topology present without requiring a new fetch."""

    result: dict[str, dict[str, Any]] = {}
    for key in (
        "structural_receipts",
        "annual_document_receipts",
        "document_receipts",
        "receipts",
    ):
        receipts = packet.get(key)
        if isinstance(receipts, Mapping):
            receipts = list(receipts.values())
        if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)):
            continue
        for receipt in receipts:
            if not isinstance(receipt, Mapping):
                continue
            accession = _filing_value(receipt, "accession", "accessionNumber")
            if accession:
                result[str(accession)] = dict(receipt)
    return result


def _source_row(
    *,
    field: str,
    qname: str,
    value: object,
    unit: object,
    start: object,
    end: object,
    accession: object,
    form: object,
    filed: object,
    fy: object = None,
    fp: object = None,
    frame: object = None,
    context_id: object = None,
    dimensions: object = None,
    statement_role: object = None,
    decimals: object = None,
    source_kind: str,
    receipt: Mapping[str, Any] | None,
    selection_reason: str,
) -> dict[str, Any] | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(float(value)):
        return None
    if not isinstance(end, str) or not isinstance(accession, str) or not accession:
        return None
    namespace, concept = qname.split(":", 1) if ":" in qname else ("us-gaap", qname)
    normalized_unit = _unit(unit)
    row = {
        "field": field,
        "value": float(value),
        "namespace": namespace,
        "concept": concept,
        "qname": qname,
        "unit": normalized_unit,
        "raw_unit": str(unit or ""),
        "currency": "USD" if normalized_unit == "USD" else None,
        "period_start": start,
        "period_end": end,
        "duration_days": _duration(start, end),
        "source_accession": accession,
        "form": form,
        "filed_date": filed,
        "fiscal_year": fy,
        "fiscal_period": fp,
        "frame": frame,
        "context_id": context_id,
        "dimensions": dimensions or [],
        "statement_role": statement_role,
        "decimals": decimals,
        "source_kind": source_kind,
        "selection_reason": selection_reason,
        "sign_policy": "reported_sign_preserved",
    }
    if concept == "RevenueFromContractWithCustomerIncludingAssessedTax":
        row["tax_scope"] = "including_assessed_tax"
    elif concept == "RevenueFromContractWithCustomerExcludingAssessedTax":
        row["tax_scope"] = "excluding_assessed_tax"
    if receipt is not None:
        row["source_receipt"] = dict(receipt)
        row["receipt_status"] = "captured_receipt_in_packet"
    else:
        row["source_receipt"] = None
        row["receipt_status"] = "accession_from_companyfacts_or_structural_packet"
    return row


def _structural_rows(packet: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    structures: list[Mapping[str, Any]] = []
    packets = packet.get("structural_packets")
    if isinstance(packets, Mapping):
        structures.extend(value for value in packets.values() if isinstance(value, Mapping))
    for key in ("structural_filing", "annual_structural_filing"):
        value = packet.get(key)
        if isinstance(value, Mapping):
            structures.append(value)
    for structure in structures:
        for row in structure.get("facts", []) if isinstance(structure.get("facts"), list) else []:
            if not isinstance(row, Mapping):
                continue
            identity = (
                row.get("qname"), row.get("value"), row.get("unit"),
                row.get("period_start"), row.get("period_end"), row.get("source_accession"),
                tuple(tuple(item) for item in row.get("dimensions", []) or []),
            )
            if identity in seen:
                continue
            seen.add(identity)
            yield row


def _structural_candidates(
    packet: Mapping[str, Any],
    field: str,
    *,
    end: str,
    start: str | None = None,
    accession: str | None = None,
    form: str | None = None,
    cutoff: str | None = None,
    cik: str | None = None,
) -> list[Mapping[str, Any]]:
    references = FIELD_CONCEPTS[field]
    ranks = {reference.split(":", 1)[1]: index for index, reference in enumerate(references)}
    expected_unit = FIELD_UNITS[field]
    rows: list[Mapping[str, Any]] = []
    for row in _structural_rows(packet):
        qname = str(row.get("qname") or "")
        concept = qname.split(":", 1)[-1]
        if concept not in ranks or row.get("period_end") != end:
            continue
        if not _verified_structural_identity(row, cik):
            continue
        if start is not None and row.get("period_start") != start:
            continue
        if accession is not None and row.get("source_accession") != accession:
            continue
        row_form = _structural_form(row)
        if form is not None and row_form != form:
            continue
        if cutoff and str(row.get("filed_date") or "") > cutoff:
            continue
        if _unit(row.get("unit")) != expected_unit:
            continue
        dimensions = row.get("dimensions") or []
        if dimensions:
            continue
        rows.append(row)
    return rows


def _companyfacts_rows(
    packet: Mapping[str, Any],
    field: str,
    *,
    end: str,
    start: str | None = None,
    accession: str | None = None,
    form: str | None = None,
    cutoff: str | None = None,
) -> list[tuple[str, str, Mapping[str, Any]]]:
    companyfacts = packet.get("companyfacts")
    namespaces = companyfacts.get("facts", {}) if isinstance(companyfacts, Mapping) else {}
    rows: list[tuple[str, str, Mapping[str, Any]]] = []
    for reference_rank, reference in enumerate(FIELD_CONCEPTS[field]):
        namespace, concept = _qname(reference)
        units = namespaces.get(namespace, {}).get(concept, {}).get("units", {})
        for unit, facts in units.items():
            if _unit(unit) != FIELD_UNITS[field] or not isinstance(facts, list):
                continue
            for fact in facts:
                if not isinstance(fact, Mapping) or fact.get("end") != end:
                    continue
                if start is not None and fact.get("start") != start:
                    continue
                if accession is not None and fact.get("accn") != accession:
                    continue
                if form is not None and fact.get("form") != form:
                    continue
                if cutoff and str(fact.get("filed") or "") > cutoff:
                    continue
                if not isinstance(fact.get("val"), (int, float)) or isinstance(fact.get("val"), bool):
                    continue
                enriched = dict(fact)
                enriched.update(
                    {
                        "qname": reference,
                        "source_accession": fact.get("accn"),
                        "period_start": fact.get("start"),
                        "period_end": fact.get("end"),
                        "value": fact.get("val"),
                        "unit": unit,
                    }
                )
                rows.append((str(reference_rank), reference, enriched))
    rows.sort(key=lambda item: (int(item[0]), str(item[2].get("filed") or ""), str(item[2].get("accn") or "")))
    return rows


def _dedupe_fact_rows(rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    deduped: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for row in rows:
        key = (row.get("qname"), row.get("value"), row.get("unit"), row.get("period_start"), row.get("period_end"), row.get("source_accession"))
        deduped[key] = row
    return list(deduped.values())


def _annual_row(
    packet: Mapping[str, Any],
    normalizer: CompanyFactsNormalizer | None,
    field: str,
    end: str,
    *,
    cutoff: str | None,
    cik: str | None,
    receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    structural = _structural_candidates(packet, field, end=end, form=None, cutoff=cutoff, cik=cik)
    structural = [row for row in structural if _structural_form(row) in {"10-K", "10-K/A"} and _duration(row.get("period_start"), row.get("period_end")) in range(330, 386)]
    if structural:
        _assert_no_source_conflicts(structural, field)
        best_rank = min(
            FIELD_CONCEPTS[field].index(f"us-gaap:{str(row.get('qname')).split(':', 1)[-1]}")
            for row in structural
            if f"us-gaap:{str(row.get('qname')).split(':', 1)[-1]}" in FIELD_CONCEPTS[field]
        )
        candidates = [
            row for row in structural
            if FIELD_CONCEPTS[field].index(f"us-gaap:{str(row.get('qname')).split(':', 1)[-1]}") == best_rank
        ]
        row = max(candidates, key=lambda item: (str(item.get("filed_date") or ""), str(item.get("source_accession") or ""), _structural_form(item) == "10-K/A"))
        return _source_row(
            field=field, qname=str(row.get("qname")), value=row.get("value"), unit=row.get("unit"),
            start=row.get("period_start"), end=row.get("period_end"), accession=row.get("source_accession"),
            form=_structural_form(row), filed=row.get("filed_date"), fy=row.get("fiscal_year"), fp=row.get("fiscal_period"),
            frame=row.get("frame"), context_id=row.get("context_id"), dimensions=row.get("dimensions"),
            statement_role=_structural_role(row), decimals=row.get("decimals"), source_kind="structural_filing_fact", receipt=receipts.get(str(row.get("source_accession"))),
            selection_reason="Exact recent annual period from a captured structural filing fact.",
        )
    companyfacts_candidates = [
        fact for _, reference, fact in _companyfacts_rows(packet, field, end=end, form=None, cutoff=cutoff)
        if fact.get("form") in {"10-K", "10-K/A"}
        and fact.get("start")
        and _duration(fact.get("start"), fact.get("end")) in range(330, 386)
        and reference in FIELD_CONCEPTS[field]
    ]
    _assert_no_source_conflicts(companyfacts_candidates, field)
    selected = normalizer.annual_at_end(field, end) if normalizer else None
    if selected is None:
        return None
    row = selected.as_dict()
    if _duration(row.get("start"), row.get("end")) not in range(330, 386):
        return None
    return _source_row(
        field=field, qname=f"{selected.namespace}:{selected.concept}", value=selected.value, unit=selected.unit,
        start=selected.start, end=selected.end, accession=selected.accession, form=selected.form, filed=selected.filed,
        fy=selected.fiscal_year, fp=selected.fiscal_period, frame=selected.frame,
        dimensions=row.get("dimensions"), source_kind="companyfacts_annual", receipt=receipts.get(selected.accession),
        selection_reason="Latest cutoff-eligible annual CompanyFacts fact for the requested captured annual end.",
    )


def _ytd_candidates(
    packet: Mapping[str, Any],
    field: str,
    *,
    end: str,
    accession: str,
    form: str,
    cutoff: str | None,
    cik: str | None,
    receipts: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    structural = _structural_candidates(packet, field, end=end, accession=accession, form=form, cutoff=cutoff, cik=cik)
    _assert_no_source_conflicts(structural, field)
    for row in structural:
        days = _duration(row.get("period_start"), row.get("period_end"))
        if row.get("period_start") and days is not None and 70 <= days <= 310:
            source = _source_row(
                field=field, qname=str(row.get("qname")), value=row.get("value"), unit=row.get("unit"),
                start=row.get("period_start"), end=row.get("period_end"), accession=row.get("source_accession"),
                form=_structural_form(row), filed=row.get("filed_date"), fy=row.get("fiscal_year"), fp=row.get("fiscal_period"),
                frame=row.get("frame"), context_id=row.get("context_id"), dimensions=row.get("dimensions"),
                statement_role=_structural_role(row), decimals=row.get("decimals"), source_kind="structural_filing_fact", receipt=receipts.get(str(row.get("source_accession"))),
                selection_reason="Exact current-controlling-filing cumulative fiscal fact.",
            )
            if source:
                rows.append(source)
    companyfacts_rows = _companyfacts_rows(packet, field, end=end, accession=accession, form=form, cutoff=cutoff)
    try:
        _assert_no_source_conflicts((fact for _, _, fact in companyfacts_rows), field)
    except SourceConflict:
        # When the same accession is represented by a validated structural
        # packet, its decimal-aware duplicate check is authoritative.  A
        # CompanyFacts-only conflict remains fail-closed below.
        if not structural:
            raise
    for _, reference, fact in companyfacts_rows:
        days = _duration(fact.get("start"), fact.get("end"))
        if not fact.get("start") or days is None or not 70 <= days <= 310:
            continue
        source = _source_row(
            field=field, qname=reference, value=fact.get("val"), unit=FIELD_UNITS[field],
            start=fact.get("start"), end=fact.get("end"), accession=fact.get("accn"), form=fact.get("form"),
            filed=fact.get("filed"), fy=fact.get("fy"), fp=fact.get("fp"), frame=fact.get("frame"),
            source_kind="companyfacts_current_fiscal_ytd", receipt=None,
            selection_reason="Current controlling accession cumulative fiscal fact.",
        )
        if source:
            rows.append(source)
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = (row["source_accession"], row["period_start"], row["period_end"], row["concept"], row["value"])
        # Structural facts are preferred when both the parsed filing and
        # CompanyFacts carry the same observation; CompanyFacts remains the
        # fallback for older comparative periods.
        unique.setdefault(key, row)
    return sorted(unique.values(), key=lambda row: (-int(row["duration_days"] or 0), str(row.get("filed_date") or ""), row["concept"]))


def _select_ytd_pair(
    packet: Mapping[str, Any],
    normalizer: CompanyFactsNormalizer | None,
    field: str,
    *,
    annual_end: str,
    controlling: Mapping[str, Any],
    cutoff: str | None,
    cik: str | None,
    receipts: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    accession = _filing_value(controlling, "accessionNumber", "accession")
    end = _filing_value(controlling, "reportDate", "report_date")
    form = controlling.get("form")
    if not accession or not end or form not in {"10-Q", "10-Q/A"}:
        return None, None
    current = _ytd_candidates(packet, field, end=str(end), accession=str(accession), form=str(form), cutoff=cutoff, cik=cik, receipts=receipts)
    if not current:
        # CompanyFactsNormalizer remains the common selector fallback.  The
        # accession guard prevents a later fiscal quarter from replacing the
        # frozen controlling filing.
        pair = normalizer.latest_ytd_pair(field, after_end=annual_end) if normalizer else None
        if pair and pair[0].accession == str(accession) and pair[0].end == str(end):
            current = [
                _source_row(
                    field=field, qname=f"{pair[0].namespace}:{pair[0].concept}", value=pair[0].value, unit=pair[0].unit,
                    start=pair[0].start, end=pair[0].end, accession=pair[0].accession, form=pair[0].form,
                    filed=pair[0].filed, fy=pair[0].fiscal_year, fp=pair[0].fiscal_period, frame=pair[0].frame,
                    source_kind="companyfacts_current_fiscal_ytd", receipt=receipts.get(pair[0].accession),
                    selection_reason="CompanyFactsNormalizer cumulative-fiscal selector constrained to the controlling accession.",
                )
            ]
    if not current:
        return None, None
    selected_current = max(
        current,
        key=lambda row: (
            int(row["duration_days"] or 0),
            str(row.get("filed_date") or ""),
            -_field_rank(field, row),
            row.get("source_kind") == "structural_filing_fact",
        ),
    )
    current_days = int(selected_current["duration_days"] or 0)
    prior_rows: list[dict[str, Any]] = []
    structural_prior = _structural_ytd_for_accession(packet, field, str(accession), str(form), cutoff, cik, receipts)
    companyfacts_prior = _all_companyfacts_ytd_for_accession(packet, field, str(accession), str(form), cutoff, allow_conflicts=bool(structural_prior))
    prior_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for source_row in [*structural_prior, *companyfacts_prior]:
        if source_row["period_end"] >= str(end) or source_row["duration_days"] is None:
            continue
        if abs(int(source_row["duration_days"]) - current_days) <= 8:
            key = (source_row["source_accession"], source_row["period_start"], source_row["period_end"], source_row["concept"], source_row["value"])
            prior_by_key.setdefault(key, source_row)
    prior_rows.extend(prior_by_key.values())
    if not prior_rows and normalizer:
        pair = normalizer.latest_ytd_pair(field, after_end=annual_end)
        if pair and pair[0].accession == str(accession) and pair[0].end == str(end):
            prior = pair[1]
            source = _source_row(
                field=field, qname=f"{prior.namespace}:{prior.concept}", value=prior.value, unit=prior.unit,
                start=prior.start, end=prior.end, accession=prior.accession, form=prior.form, filed=prior.filed,
                fy=prior.fiscal_year, fp=prior.fiscal_period, frame=prior.frame, source_kind="companyfacts_prior_fiscal_ytd",
                receipt=receipts.get(prior.accession), selection_reason="Prior comparable cumulative fiscal fact from the same controlling 10-Q accession.",
            )
            if source:
                prior_rows.append(source)
    prior = max(prior_rows, key=lambda row: (str(row["period_end"]), str(row.get("filed_date") or "")), default=None)
    return selected_current, prior


def _all_companyfacts_ytd_for_accession(
    packet: Mapping[str, Any], field: str, accession: str, form: str, cutoff: str | None, *, allow_conflicts: bool = False
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    raw_rows = list(_companyfacts_rows_for_accession(packet, field, accession, form, cutoff))
    if not allow_conflicts:
        _assert_no_source_conflicts((fact for _, _, fact in raw_rows), field)
    for _, reference, fact in raw_rows:
        source = _source_row(
            field=field, qname=reference, value=fact.get("val"), unit=FIELD_UNITS[field], start=fact.get("start"),
            end=fact.get("end"), accession=fact.get("accn"), form=fact.get("form"), filed=fact.get("filed"),
            fy=fact.get("fy"), fp=fact.get("fp"), frame=fact.get("frame"), source_kind="companyfacts_prior_fiscal_ytd",
            receipt=None, selection_reason="Prior comparable cumulative fiscal fact from the same controlling 10-Q accession.",
        )
        if source and source["period_start"] and source["duration_days"] is not None and 70 <= source["duration_days"] <= 310:
            result.append(source)
    return result


def _companyfacts_rows_for_accession(packet: Mapping[str, Any], field: str, accession: str, form: str, cutoff: str | None):
    companyfacts = packet.get("companyfacts")
    namespaces = companyfacts.get("facts", {}) if isinstance(companyfacts, Mapping) else {}
    for reference in FIELD_CONCEPTS[field]:
        namespace, concept = _qname(reference)
        for unit, facts in namespaces.get(namespace, {}).get(concept, {}).get("units", {}).items():
            if _unit(unit) != FIELD_UNITS[field] or not isinstance(facts, list):
                continue
            for fact in facts:
                if fact.get("accn") == accession and fact.get("form") == form and (not cutoff or str(fact.get("filed") or "") <= cutoff):
                    enriched = dict(fact)
                    enriched.update(
                        {
                            "qname": reference,
                            "source_accession": fact.get("accn"),
                            "period_start": fact.get("start"),
                            "period_end": fact.get("end"),
                            "value": fact.get("val"),
                            "unit": unit,
                        }
                    )
                    yield "", reference, enriched


def _structural_ytd_for_accession(packet: Mapping[str, Any], field: str, accession: str, form: str, cutoff: str | None, cik: str | None, receipts: Mapping[str, Mapping[str, Any]]):
    result: list[dict[str, Any]] = []
    references = {reference.split(":", 1)[1] for reference in FIELD_CONCEPTS[field]}
    expected_unit = FIELD_UNITS[field]
    for row in _structural_rows(packet):
        qname = str(row.get("qname") or "")
        if qname.split(":", 1)[-1] not in references or row.get("source_accession") != accession or _structural_form(row) != form:
            continue
        if not _verified_structural_identity(row, cik):
            continue
        if cutoff and str(row.get("filed_date") or "") > cutoff:
            continue
        if _unit(row.get("unit")) != expected_unit or row.get("dimensions"):
            continue
        days = _duration(row.get("period_start"), row.get("period_end"))
        if row.get("period_start") and days is not None and 70 <= days <= 310:
            source = _source_row(
                field=field, qname=str(row.get("qname")), value=row.get("value"), unit=row.get("unit"), start=row.get("period_start"),
                end=row.get("period_end"), accession=row.get("source_accession"), form=_structural_form(row), filed=row.get("filed_date"),
                fy=row.get("fiscal_year"), fp=row.get("fiscal_period"), frame=row.get("frame"), context_id=row.get("context_id"),
                decimals=row.get("decimals"), source_kind="structural_filing_fact", receipt=receipts.get(str(row.get("source_accession"))), selection_reason="Prior comparable cumulative fiscal fact from the same controlling 10-Q accession.",
            )
            if source:
                result.append(source)
    _assert_no_source_conflicts(result, field)
    return result


def _derived_ttm(annual: Sequence[Mapping[str, Any]], current: Mapping[str, Any] | None, prior: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not current or not prior:
        return None
    current_start = _date(current.get("period_start"))
    prior_end = _date(prior.get("period_end"))
    if current_start is None or prior_end is None:
        return None
    eligible = [row for row in annual if _date(row.get("period_end")) and _date(row.get("period_end")) < current_start]
    if not eligible:
        return None
    fy = max(eligible, key=lambda row: str(row.get("period_end")))
    fy_end = _date(fy.get("period_end"))
    annual_start = _date(fy.get("period_start"))
    prior_start = _date(prior.get("period_start"))
    current_days = current.get("duration_days")
    prior_days = prior.get("duration_days")
    # The FY must directly precede the current fiscal YTD, and the prior YTD
    # must begin on the same fiscal start.  One day of duration drift is
    # allowed for leap/calendar endpoint drift. A reported extra-week interim
    # difference remains an explicit alignment review rather than being hidden.
    if (
        fy_end is None
        or annual_start is None
        or prior_start is None
        or (current_start - fy_end).days != 1
        or prior_start != annual_start
        or not isinstance(current_days, int)
        or not isinstance(prior_days, int)
        or abs(current_days - prior_days) > 1
    ):
        return None
    ttm_start = prior_end.fromordinal(prior_end.toordinal() + 1)
    ttm_end = _date(current.get("period_end"))
    if ttm_end is None:
        return None
    return {
        "value": float(fy["value"]) + float(current["value"]) - float(prior["value"]),
        "unit": fy["unit"],
        "currency": "USD" if fy.get("unit") == "USD" else None,
        "period_start": ttm_start.isoformat(),
        "period_end": current.get("period_end"),
        "duration_days": _duration(ttm_start.isoformat(), ttm_end.isoformat()),
        "formula": "annual_fy + current_fiscal_ytd - prior_fiscal_ytd",
        "classification": "derived_accounting_ttm",
        "alignment": {
            "annual_fiscal_start": fy.get("period_start"),
            "annual_fiscal_end": fy.get("period_end"),
            "current_ytd_start": current.get("period_start"),
            "current_ytd_end": current.get("period_end"),
            "prior_ytd_start": prior.get("period_start"),
            "prior_ytd_end": prior.get("period_end"),
            "current_ytd_duration_days": current_days,
            "prior_ytd_duration_days": prior_days,
            "fiscal_start_match": prior_start == annual_start,
            "annual_to_current_adjacent": (current_start - fy_end).days == 1,
        },
        "operands": [dict(fy), dict(current), dict(prior)],
    }


def _gap(code: str, field: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "field": field, "detail": detail, **extra}


def _field_rank(field: str, row: Mapping[str, Any]) -> int:
    reference = f"{row.get('namespace', 'us-gaap')}:{row.get('concept')}"
    try:
        return FIELD_CONCEPTS[field].index(reference)
    except ValueError:
        return 999


def build_expansion_period_inputs(
    packet: Mapping[str, Any], recent_annual_ends: Sequence[str]
) -> dict[str, Any]:
    """Return a source ledger and explicit gaps for one captured issuer packet.

    ``recent_annual_ends`` must come from the caller's captured annual-document
    inventory.  It is intentionally not inferred from the potentially stale
    historical helper inventory.  The function performs no forecast, recipe,
    or valuation work.
    """

    if not isinstance(packet, Mapping):
        raise TypeError("packet must be a mapping")
    ends = [str(value) for value in recent_annual_ends]
    gaps: list[dict[str, Any]] = []
    for value in ends:
        if _date(value) is None:
            raise ValueError(f"recent annual end is not ISO date: {value}")
    if len(set(ends)) != len(ends):
        raise ValueError("recent annual ends must be unique")
    if len(ends) != 5:
        gaps.append(_gap("recent_annual_end_count", "annual_history", "Caller supplied a recent annual inventory other than five ends; no dates were inferred."))
    ends = sorted(ends)
    filing = _controlling_filing(packet)
    cutoff = _cutoff(packet, filing)
    cik = str(packet.get("issuer", {}).get("cik") or packet.get("companyfacts", {}).get("cik") or packet.get("submissions", {}).get("cik") or "").zfill(10)
    normalizer = _normalizer(packet, cutoff)
    receipts = _receipt_map(packet)
    fields: dict[str, Any] = {}
    latest_annual_end = ends[-1] if ends else None

    for field in FIELD_CONCEPTS:
        annual: list[dict[str, Any]] = []
        missing: list[str] = []
        for end in ends:
            try:
                row = _annual_row(packet, normalizer, field, end, cutoff=cutoff, cik=cik, receipts=receipts)
            except SourceConflict as exc:
                row = None
                gaps.append(_gap("conflicting_source_facts", field, str(exc), period_end=end))
            if row is None:
                missing.append(end)
            else:
                row["period_role"] = "annual_fiscal_year"
                annual.append(row)
        if missing:
            gaps.append(_gap("missing_recent_annual_fact", field, "No cutoff-eligible annual fact for one or more captured annual ends; no carry-forward was applied.", period_ends=missing))
        current, prior = (None, None)
        if latest_annual_end and filing:
            try:
                current, prior = _select_ytd_pair(packet, normalizer, field, annual_end=latest_annual_end, controlling=filing, cutoff=cutoff, cik=cik, receipts=receipts)
            except SourceConflict as exc:
                current, prior = None, None
                gaps.append(_gap("conflicting_source_facts", field, str(exc), period_end=_filing_value(filing, "reportDate", "report_date")))
        form = filing.get("form")
        if form in {"10-Q", "10-Q/A"} and current is None:
            gaps.append(_gap("missing_current_fiscal_ytd", field, "The controlling 10-Q has no eligible cumulative fiscal fact for this field."))
        if form in {"10-Q", "10-Q/A"} and current is not None and prior is None:
            gaps.append(_gap("missing_prior_fiscal_ytd", field, "The controlling 10-Q has no same-accession comparable fiscal YTD fact; calendar-year substitution is forbidden."))
        if current is not None:
            current["period_role"] = "current_fiscal_ytd"
        if prior is not None:
            prior["period_role"] = "prior_fiscal_ytd"
        # Shares are point/weighted-period denominators, not additive flows;
        # keep their annual and fiscal-YTD observations without fabricating a
        # TTM share count.  Only the accounting-flow families can be summed
        # as FY + current YTD - prior comparable YTD.
        derived = None if field in {"diluted_shares", "basic_shares"} else _derived_ttm(annual, current, prior)
        period_rows = [*annual, current, prior]
        units = {row.get("unit") for row in period_rows if row}
        if len(units) > 1 or (units and units != {FIELD_UNITS[field]}):
            gaps.append(_gap("incompatible_units", field, "Annual and fiscal-YTD source rows do not share one unit; no arithmetic may combine them."))
            derived = None
        scopes = {row.get("tax_scope") for row in period_rows if row and row.get("tax_scope")}
        if field == "revenue" and len(scopes) > 1:
            gaps.append(_gap("incompatible_tax_scope", field, "Annual and fiscal-YTD revenue concepts differ in assessed-tax scope; no TTM arithmetic was emitted.", scopes=sorted(scopes)))
            derived = None
        if field not in {"diluted_shares", "basic_shares"} and current is not None and prior is not None and derived is None:
            gaps.append(_gap("unaligned_fiscal_periods", field, "Annual and fiscal-YTD starts/ends are not directly adjacent/comparable; no TTM arithmetic was emitted."))
        if field == "revenue":
            scoped = [row for row in [*annual, current, prior] if row and row.get("tax_scope") == "including_assessed_tax"]
            if scoped:
                gaps.append(_gap("assessed_tax_scope_requires_policy", field, "Reported revenue uses IncludingAssessedTax; the tax scope is retained and not treated as excluding-tax equivalent.", periods=[row.get("period_end") for row in scoped]))
        fields[field] = {
            "annual": annual,
            "current_fiscal_ytd": current,
            "prior_fiscal_ytd": prior,
            "derived_ttm": derived,
            "annual_period_ends_observed": [row["period_end"] for row in annual],
            "missing_annual_period_ends": missing,
        }

    # Keep the short reviewer-facing SBC name while making the accounting
    # meaning explicit for downstream callers.
    fields["share_based_compensation"] = fields["sbc"]

    table_audit = None
    if filing and cik and packet.get("structural_filing"):
        try:
            table_audit = inspect_tables(packet, cik=cik, cutoff=cutoff or str(_filing_value(filing, "filingDate", "filed") or ""))
            for issue in table_audit.get("exceptions", []):
                gaps.append(_gap("current_table_exception", str(issue.get("field") or "table"), str(issue.get("detail") or issue.get("code") or "Current statement-table exception."), issue_code=issue.get("code")))
        except (TypeError, ValueError) as exc:
            table_audit = {"status": "unavailable", "error": str(exc)}
            gaps.append(_gap("table_selector_unavailable", "current_statement_tables", str(exc)))

    if not filing:
        gaps.append(_gap("missing_controlling_filing", "filing", "Packet has no controlling financial filing identity."))
    if cutoff and _filing_value(filing, "filingDate", "filed") and str(_filing_value(filing, "filingDate", "filed")) > cutoff:
        gaps.append(_gap("filing_after_cutoff", "filing", "Controlling filing is later than the supplied cutoff."))

    ledger = {
        "version": VERSION,
        "source_only": True,
        "ticker": packet.get("issuer", {}).get("ticker"),
        "cik": cik,
        "cutoff": cutoff,
        "controlling_filing": dict(filing),
        "requested_recent_annual_ends": ends,
        "fields": fields,
        "table_audit": table_audit,
        "selection_policy": {
            "annual": "Five caller-supplied captured annual report ends; latest cutoff-eligible reported fact per end.",
            "interim": "Current controlling 10-Q cumulative fiscal period plus same-accession prior fiscal comparative, preserving actual starts/ends and 52/53-week durations.",
            "interest": "Gross interest concepts and signed net interest concepts are separate; abs(net) is never used as gross.",
            "cash_flow_fields": ["operating_cash_flow", "capital_expenditures", "sbc"],
            "missing_value": "Missing is a gap, never an inferred zero or carry-forward.",
            "forecast_performed": False,
            "recipes_built": False,
            "valuation_performed": False,
        },
    }
    return {
        "source_ledger": ledger,
        "gaps": gaps,
        "forecast_performed": False,
        "recipes_built": False,
        "valuation_performed": False,
    }


def build_period_input_ledger(packet: Mapping[str, Any], recent_annual_ends: Sequence[str]) -> dict[str, Any]:
    """Compatibility name for callers that use the shorter ledger wording."""

    return build_expansion_period_inputs(packet, recent_annual_ends)


__all__ = [
    "FIELD_CONCEPTS",
    "FIELD_UNITS",
    "VERSION",
    "build_expansion_period_inputs",
    "build_period_input_ledger",
]
