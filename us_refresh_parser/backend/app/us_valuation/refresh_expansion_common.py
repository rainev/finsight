"""Source-bound refresh binding for the WCC/GRC common-book RI family.

This module is intentionally narrower than the general refresh dispatcher.  It
binds the two reviewed industrial common-book recipes from a cached SEC packet,
keeps the approved scenario assumptions fixed, and records every selected fact
with its filing identity.  It does not write catalogs, change admission state,
or perform a network capture.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import hashlib
from math import isclose, isfinite
from pathlib import Path
import re
from statistics import median
from typing import Any, Mapping

from .calculation_recipe import evaluate_recipe, number

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - the application bundle supplies bs4
    BeautifulSoup = None


SCHEMA_VERSION = "FINSIGHT-RESIDUAL-REFRESH-COMMON-1"
SUPPORTED = {"WCC", "GRC"}
_USD = {"USD", "iso4217:USD"}
_SHARES = {"shares", "xbrli:shares"}
_COMMON_EARNINGS = {
    "us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic",
    "us-gaap:NetIncomeLoss",
}
_DIVIDENDS = {
    "us-gaap:DividendsCommonStockCash",
    "us-gaap:DividendsCommonStock",
    "us-gaap:PaymentsOfDividendsCommonStock",
    "us-gaap:PaymentsOfOrdinaryDividends",
}


class CommonRefreshError(ValueError):
    """A source, identity, period, or recipe binding failure."""


def _iso(value: Any, name: str) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError) as exc:
        raise CommonRefreshError(f"{name} must be an ISO date") from exc


def _cik(value: Any) -> str:
    text = str(value or "")
    if not text.isdigit() or len(text) > 10:
        raise CommonRefreshError("issuer CIK is missing or invalid")
    return text.zfill(10)


def _ticker(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any]) -> str:
    value = policy.get("ticker") or recipe.get("ticker") or packet.get("issuer", {}).get("ticker")
    value = str(value or "").upper()
    if value not in SUPPORTED:
        raise CommonRefreshError("common-book refresh supports WCC and GRC only")
    return value


def _filing(policy: Mapping[str, Any], packet: Mapping[str, Any], cutoff: str) -> dict[str, Any]:
    raw = packet.get("_selected_controlling_filing") or packet.get("controlling_filing")
    if not isinstance(raw, Mapping):
        raise CommonRefreshError("controlling filing is required")
    accession = raw.get("accessionNumber") or raw.get("accession")
    filed = raw.get("filingDate") or raw.get("filed")
    period = raw.get("reportDate") or raw.get("report_date")
    form = raw.get("form")
    if not all(isinstance(item, str) and item for item in (accession, filed, period, form)):
        raise CommonRefreshError("controlling filing metadata is incomplete")
    if _iso(filed, "filing date") > cutoff or _iso(period, "report date") > cutoff:
        raise CommonRefreshError("controlling filing is after frozen cutoff")
    if form not in {"10-K", "10-K/A", "10-Q", "10-Q/A"}:
        raise CommonRefreshError("controlling filing is not a supported financial form")
    result = dict(raw)
    result.update(accessionNumber=accession, filingDate=filed, reportDate=period, form=form)
    expected = policy.get("cik")
    if expected is not None and _cik(expected) != _cik(packet.get("companyfacts", {}).get("cik", expected)):
        raise CommonRefreshError("policy and packet CIK identities do not match")
    return result


def _structural(packet: Mapping[str, Any], filing: Mapping[str, Any]) -> Mapping[str, Any]:
    structural = packet.get("structural_filing")
    if not isinstance(structural, Mapping):
        structural = packet.get("structural")
    if not isinstance(structural, Mapping):
        raise CommonRefreshError("current structural filing is required")
    if structural.get("source_accession") not in {None, filing["accessionNumber"]}:
        raise CommonRefreshError("current structural packet accession mismatch")
    return structural


def _packet_facts(packet: Mapping[str, Any], filing: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return structural facts plus cached CompanyFacts rows without mutation."""
    rows: list[dict[str, Any]] = []
    structural = packet.get("structural_filing") or packet.get("structural")
    if isinstance(structural, Mapping):
        rows.extend(dict(row, _source_kind="structural_xbrl", form=row.get("form") or structural.get("form"),
                         filed_date=row.get("filed_date") or structural.get("filed_date"),
                         _filing_form=structural.get("form"))
                    for row in structural.get("facts", []) if isinstance(row, Mapping))
    packets = packet.get("structural_packets")
    if isinstance(packets, Mapping):
        for accession, item in packets.items():
            if accession == filing["accessionNumber"] or not isinstance(item, Mapping):
                continue
            rows.extend(dict(row, _source_kind="structural_xbrl", form=row.get("form") or item.get("form"),
                             filed_date=row.get("filed_date") or item.get("filed_date"),
                             _filing_form=item.get("form"))
                        for row in item.get("facts", []) if isinstance(row, Mapping))
    annual = packet.get("annual_structural_filing")
    if isinstance(annual, Mapping) and annual.get("source_accession") not in {None, filing["accessionNumber"]}:
        rows.extend(dict(row, _source_kind="structural_xbrl", form=row.get("form") or annual.get("form"),
                         filed_date=row.get("filed_date") or annual.get("filed_date"),
                         _filing_form=annual.get("form"))
                    for row in annual.get("facts", []) if isinstance(row, Mapping))
    companyfacts = packet.get("companyfacts")
    facts = companyfacts.get("facts", {}) if isinstance(companyfacts, Mapping) else {}
    filing_dates: dict[str, tuple[Any, Any]] = {}
    for candidate in (
        packet.get("controlling_filing"),
        packet.get("latest_annual_filing"),
    ):
        if isinstance(candidate, Mapping):
            accession = candidate.get("accessionNumber") or candidate.get("accession")
            if accession:
                filing_dates[str(accession)] = (candidate.get("reportDate") or candidate.get("report_date"), candidate.get("form"))
    for candidate in (packet.get("structural_filing"), packet.get("annual_structural_filing")):
        if isinstance(candidate, Mapping) and candidate.get("source_accession"):
            filing_dates[str(candidate["source_accession"])] = (candidate.get("report_date") or candidate.get("period_end"), candidate.get("form"))
    if isinstance(packet.get("structural_packets"), Mapping):
        for candidate in packet["structural_packets"].values():
            if isinstance(candidate, Mapping) and candidate.get("source_accession"):
                filing_dates[str(candidate["source_accession"])] = (candidate.get("report_date") or candidate.get("period_end"), candidate.get("form"))
    if isinstance(facts, Mapping):
        for namespace, concepts in facts.items():
            if not isinstance(concepts, Mapping):
                continue
            for local, definition in concepts.items():
                if not isinstance(definition, Mapping) or not isinstance(definition.get("units"), Mapping):
                    continue
                for unit, values in definition["units"].items():
                    if not isinstance(values, list):
                        continue
                    for item in values:
                        if not isinstance(item, Mapping):
                            continue
                        rows.append({
                            **dict(item),
                            "qname": f"{namespace}:{local}",
                            "local_name": local,
                            "unit": unit,
                            "source_accession": item.get("accn"),
                            "filed_date": item.get("filed"),
                            "report_date": filing_dates.get(str(item.get("accn")), (item.get("end"), None))[0],
                            "form": item.get("form") or filing_dates.get(str(item.get("accn")), (None, None))[1],
                            "_source_kind": "companyfacts",
                        })
    return rows


def _dimensions(row: Mapping[str, Any]) -> list[list[str]]:
    value = row.get("dimensions") or []
    return [list(item) for item in value if isinstance(item, (list, tuple)) and len(item) == 2]


def _same_period(row: Mapping[str, Any], *, start: str | None, end: str) -> bool:
    return (row.get("period_end") or row.get("end")) == end and (row.get("period_start") or row.get("start")) == start


def _period_match(row: Mapping[str, Any], *, start: str | None, end: str) -> bool:
    return (row.get("period_end") or row.get("end")) == end and (row.get("period_start") or row.get("start")) == start


def _value(row: Mapping[str, Any], name: str) -> float:
    raw = row.get("value", row.get("val"))
    try:
        return number(raw, name)
    except ValueError as exc:
        raise CommonRefreshError(str(exc)) from exc


def _fact_source(
    row: Mapping[str, Any],
    *,
    filing: Mapping[str, Any],
    packet: Mapping[str, Any],
    cutoff: str,
    field: str,
) -> dict[str, Any]:
    accession = row.get("source_accession") or row.get("accn") or filing["accessionNumber"]
    filed = row.get("filed_date") or row.get("filed") or filing["filingDate"]
    period_end = row.get("period_end") or row.get("end")
    if accession != filing["accessionNumber"] and row.get("_source_kind") == "structural_xbrl":
        # Historical rows are allowed to come from the cached annual filing;
        # current rows are checked separately by selectors.
        pass
    if not isinstance(filed, str) or _iso(filed, f"{field} filed date") > cutoff:
        raise CommonRefreshError(f"{field}: source filing is after cutoff")
    if not isinstance(period_end, str) or _iso(period_end, f"{field} period") > cutoff:
        raise CommonRefreshError(f"{field}: source period is after cutoff")
    structural = packet.get("structural_filing")
    source_hashes = {
        "source_packet_sha256": packet.get("structural_sha256") or packet.get("provenance", {}).get("source_packet_sha256"),
        "structural_sha256": packet.get("structural_sha256") or (structural.get("source_sha256") if isinstance(structural, Mapping) else None),
        "annual_structural_sha256": packet.get("annual_structural_sha256"),
        "raw_hashes": packet.get("raw_hashes"),
    }
    return {
        "field": field,
        "source_kind": row.get("_source_kind", "cached_source"),
        "qname": row.get("qname") or row.get("concept"),
        "local_name": row.get("local_name"),
        "value": _value(row, field),
        "unit": row.get("unit") or row.get("raw_unit"),
        "period_start": row.get("period_start") or row.get("start"),
        "period_end": period_end,
        "dimensions": _dimensions(row),
        "statement_role": (row.get("statement_roles") or row.get("statement_role") or []),
        "context_id": row.get("context_id"),
        "source_accession": accession,
        "filed_date": filed,
        "report_date": row.get("report_date") or row.get("period_end") or row.get("end"),
        "source_hashes": source_hashes,
    }


def _select(
    rows: list[Mapping[str, Any]],
    *,
    qnames: set[str],
    start: str | None,
    end: str,
    units: set[str],
    dimensions: list[list[str]] | None = None,
    require_role: str | None = None,
    current_accession: str | None = None,
    field: str,
) -> dict[str, Any]:
    candidates = []
    for row in rows:
        qname = row.get("qname") or row.get("concept")
        if qname not in qnames or not _period_match(row, start=start, end=end):
            continue
        if row.get("unit") not in units and row.get("raw_unit") not in units:
            continue
        row_dims = _dimensions(row)
        if dimensions is not None and row_dims != dimensions:
            continue
        roles = row.get("statement_roles") or row.get("statement_role") or []
        if require_role and require_role not in roles:
            continue
        if current_accession and row.get("_source_kind") == "structural_xbrl" and row.get("source_accession") != current_accession:
            continue
        if isinstance(row.get("value", row.get("val")), (int, float)):
            candidates.append(row)
    if not candidates:
        raise CommonRefreshError(f"{field}: exact source fact is missing")
    values = {_value(row, field) for row in candidates}
    if len(values) != 1:
        raise CommonRefreshError(f"{field}: conflicting source facts")
    # Prefer structural rows, then the latest filed CompanyFacts row.
    candidates.sort(key=lambda row: (row.get("_source_kind") != "structural_xbrl", str(row.get("filed_date") or row.get("filed") or "")))
    return dict(candidates[0])


def _receipt(packet: Mapping[str, Any], accession: str) -> Mapping[str, Any] | None:
    for receipt in packet.get("structural_receipts", []) if isinstance(packet.get("structural_receipts"), list) else ():
        if isinstance(receipt, Mapping) and receipt.get("accession") == accession:
            return receipt
    return None


def _table_number(text: str) -> float:
    normalized = text.replace(",", "").replace("−", "-").strip()
    match = re.search(r"\(?\s*(-?\d+(?:\.\d+)?)\s*\)?", normalized)
    if not match:
        raise CommonRefreshError(f"primary table numeric cell is missing: {text!r}")
    value = float(match.group(1))
    if "(" in normalized and not normalized.lstrip().startswith("-"):
        value = -value
    return value


def _primary_table_ttm(packet: Mapping[str, Any], filing: Mapping[str, Any], *, field: str) -> dict[str, Any]:
    """Read the exact WCC twelve-month primary table from its cached receipt."""
    if BeautifulSoup is None:
        raise CommonRefreshError("cached primary-table reader is unavailable")
    receipt = _receipt(packet, filing["accessionNumber"])
    if not receipt or not receipt.get("path"):
        raise CommonRefreshError(f"{field}: cached primary-table receipt is missing")
    path = Path(str(receipt["path"]))
    if not path.is_file() or path.is_symlink():
        raise CommonRefreshError(f"{field}: cached primary-table path is missing")
    raw = path.read_bytes()
    document_sha256 = hashlib.sha256(raw).hexdigest()
    expected = receipt.get("raw_payload_sha256")
    if not isinstance(expected,str) or re.fullmatch(r'[0-9a-fA-F]{64}',expected) is None:
        raise CommonRefreshError(f"{field}: cached primary-table receipt hash is missing")
    if document_sha256 != expected.lower():
        raise CommonRefreshError(f"{field}: cached primary-table hash mismatch")
    soup = BeautifulSoup(raw, "html.parser")
    current_label = filing["reportDate"]
    current_text = date.fromisoformat(current_label).strftime("%B %-d, %Y")
    table = None
    for candidate in soup.find_all("table"):
        text = " ".join(candidate.stripped_strings)
        if "Twelve Months Ended" in text and current_text in text and "Net income attributable to common stockholders" in text:
            table = candidate
            break
    if table is None:
        raise CommonRefreshError(f"{field}: twelve-month primary table is missing")
    table_sha256 = hashlib.sha256(" ".join(table.stripped_strings).encode()).hexdigest()
    labels = {
        "direct_common_earnings_ttm": "net income attributable to common stockholders",
        "preferred_redemption_gain": "gain on redemption of series a preferred stock",
    }
    target = labels.get(field)
    if target is None:
        raise CommonRefreshError(f"{field}: unsupported primary-table selector")
    row_values: list[float] = []
    row_label = None
    for row in table.find_all("tr"):
        cells = [" ".join(cell.stripped_strings) for cell in row.find_all(["th", "td"])]
        if not cells or target not in cells[0].lower():
            continue
        row_label = cells[0]
        row_values = [_table_number(cell) for cell in cells[1:] if re.search(r"\d", cell)]
        if row_values:
            break
    if not row_values:
        raise CommonRefreshError(f"{field}: primary-table row has no current-period value")
    reported_value = row_values[0] * 1_000_000
    # The table presents the redemption gain as a negative EBITDA
    # reconciliation adjustment.  The common-earnings binder records the
    # economic gain as a positive amount and subtracts it exactly once.
    value = abs(reported_value) if field == "preferred_redemption_gain" else reported_value
    return {
        "field": field,
        "source_kind": "reported_primary_table",
        "value": value,
        "reported_signed_value": reported_value,
        "unit": "USD",
        "period_start": None,
        "period_end": filing["reportDate"],
        "dimensions": [],
        "statement_role": ["income_statement"],
        "context_id": None,
        "source_accession": filing["accessionNumber"],
        "filed_date": filing["filingDate"],
        "report_date": filing["reportDate"],
        "source_path": str(path),
        "document_sha256": document_sha256,
        "table_sha256": table_sha256,
        "source_package_sha256": receipt.get("source_package_sha256"),
        "structural_sha256": receipt.get("structural_sha256"),
        "table_label": "Twelve Months Ended",
        "row_label": row_label,
        "unit_scale": "USD millions",
    }


def _date_ytd(period: str) -> tuple[str, str, str]:
    current = date.fromisoformat(period)
    annual_end = date(current.year - 1, 12, 31).isoformat()
    current_start = date(current.year, 1, 1).isoformat()
    prior_start = date(current.year - 1, 1, 1).isoformat()
    prior_end = date(current.year - 1, current.month, current.day).isoformat()
    return annual_end, current_start, prior_start, prior_end


def _latest_unique(rows: list[Mapping[str, Any]], *, qnames: set[str], start: str | None, end: str,
                   units: set[str], field: str, current_accession: str | None = None,
                   dimensions: list[list[str]] | None = None, annual_only: bool = False) -> dict[str, Any]:
    candidates = [row for row in rows if (row.get("qname") or row.get("concept")) in qnames
                  and _period_match(row, start=start, end=end)
                  and (row.get("unit") or row.get("raw_unit")) in units
                  and (dimensions is None or _dimensions(row) == dimensions)
                  and (not annual_only or row.get("form") in {"10-K", "10-K/A"} or row.get("_filing_form") in {"10-K", "10-K/A"})
                  and (current_accession is None or row.get("source_accession") == current_accession)]
    if not candidates:
        raise CommonRefreshError(f"{field}: exact period fact is missing")
    values = {_value(row, field) for row in candidates}
    if len(values) != 1:
        raise CommonRefreshError(f"{field}: conflicting exact period facts")
    candidates.sort(key=lambda row: (row.get("_source_kind") != "structural_xbrl", str(row.get("filed_date") or row.get("filed") or "")))
    return dict(candidates[0])


def _preferred_gain_ttm(rows: list[Mapping[str, Any]], *, period: str, filing: Mapping[str, Any], packet: Mapping[str, Any], cutoff: str,
                        field: str = "preferred_redemption_gain") -> tuple[float, list[dict[str, Any]]]:
    accession = filing["accessionNumber"]
    annual_end, current_start, prior_start, prior_end = _date_ytd(period)
    qnames = {q for q in {row.get("qname") for row in rows} if isinstance(q, str) and ("Redemption" in q or "redemption" in q)}
    if not qnames:
        return 0.0, []
    selected = []
    for start, end in ((annual_end[:4] + "-01-01", annual_end), (current_start, period), (prior_start, prior_end)):
        candidates = [row for row in rows if (row.get("qname") or "") in qnames and _period_match(row, start=start, end=end)
                      and (row.get("unit") or row.get("raw_unit")) in _USD]
        if not candidates:
            continue
        values = {_value(row, field) for row in candidates}
        if len(values) != 1:
            raise CommonRefreshError("preferred redemption gain facts conflict")
        selected.append(_fact_source(candidates[0], filing=filing, packet=packet, cutoff=cutoff, field=field))
    annual = next((row["value"] for row in selected if row["period_end"] == annual_end), 0.0)
    current = next((row["value"] for row in selected if row["period_start"] == current_start), 0.0)
    prior = next((row["value"] for row in selected if row["period_start"] == prior_start), 0.0)
    return annual + current - prior, selected


def _ttm_fact(rows: list[Mapping[str, Any]], *, qnames: set[str], period: str, units: set[str], field: str,
              filing: Mapping[str, Any], packet: Mapping[str, Any], cutoff: str) -> tuple[float, list[dict[str, Any]]]:
    accession = filing["accessionNumber"]
    annual_end, current_start, prior_start, prior_end = _date_ytd(period)
    exact_starts = {
        (date.fromisoformat(period).replace(year=date.fromisoformat(period).year - 1) + timedelta(days=1)).isoformat(),
        (date.fromisoformat(period).replace(year=date.fromisoformat(period).year - 1)).isoformat(),
    }
    exact = [row for row in rows if (row.get("qname") or row.get("concept")) in qnames
             and (row.get("period_end") or row.get("end")) == period
             and (row.get("period_start") or row.get("start")) in exact_starts
             and (row.get("unit") or row.get("raw_unit")) in units
             and row.get("source_accession") == accession]
    if exact:
        values = {_value(row, field) for row in exact}
        if len(values) != 1:
            raise CommonRefreshError(f"{field}: conflicting exact TTM facts")
        return values.pop(), [_fact_source(exact[0], filing=filing, packet=packet, cutoff=cutoff, field=field)]
    selected = []
    for start, end in ((date.fromisoformat(annual_end).replace(month=1, day=1).isoformat(), annual_end), (current_start, period), (prior_start, prior_end)):
        row = _latest_unique(rows, qnames=qnames, start=start, end=end, units=units, field=field,
                             current_accession=accession if end != annual_end else None,
                             annual_only=end == annual_end)
        selected.append(_fact_source(row, filing=filing, packet=packet, cutoff=cutoff, field=field))
    value = selected[0]["value"] + selected[1]["value"] - selected[2]["value"]
    return value, selected


def _annual_roe(rows: list[Mapping[str, Any]], *, period: str, ticker: str,
                filing: Mapping[str, Any], packet: Mapping[str, Any], cutoff: str) -> tuple[float | None, list[dict[str, Any]], str]:
    if ticker == "WCC":
        return None, [], "current_common_earnings_over_current_common_book"
    annual_rows = [row for row in rows if row.get("form") in {"10-K", "10-K/A"}
                   or row.get("_filing_form") in {"10-K", "10-K/A"}]
    if not annual_rows:
        raise CommonRefreshError("annual common-book ROE history has no annual filing facts")
    current = date.fromisoformat(period)
    observations = []
    for year in range(current.year - 5, current.year):
        end = date(year, 12, 31).isoformat()
        begin = date(year - 1, 12, 31).isoformat()
        earnings = _latest_unique(annual_rows, qnames={"us-gaap:NetIncomeLoss"}, start=date(year, 1, 1).isoformat(), end=end,
                                   units=_USD, field="annual_common_earnings", dimensions=[])
        book = _latest_unique(annual_rows, qnames={"us-gaap:StockholdersEquity"}, start=None, end=end,
                              units=_USD, field="annual_common_book", dimensions=[])
        beginning = _latest_unique(annual_rows, qnames={"us-gaap:StockholdersEquity"}, start=None, end=begin,
                                   units=_USD, field="beginning_common_book", dimensions=[])
        current_value = _value(book, "annual_common_book")
        beginning_value = _value(beginning, "beginning_common_book")
        if current_value <= 0 or beginning_value <= 0:
            raise CommonRefreshError("annual common-book ROE has a non-positive denominator")
        observations.append({
            "fiscal_year": year,
            "period_end": end,
            "value": _value(earnings, "annual_common_earnings") / ((current_value + beginning_value) / 2),
            "earnings": _fact_source(earnings, filing=filing, packet=packet, cutoff=cutoff, field="annual_common_earnings"),
            "equity": _fact_source(book, filing=filing, packet=packet, cutoff=cutoff, field="annual_common_book"),
            "beginning_equity": _fact_source(beginning, filing=filing, packet=packet, cutoff=cutoff, field="beginning_common_book"),
        })
    return median(row["value"] for row in observations), observations, "annual_common_book_roe_median"


def _material_changes(policy: Mapping[str, Any], packet: Mapping[str, Any]) -> list[str]:
    changes: list[str] = []
    for root in (policy, packet):
        for key in ("material_financial_changes", "material_changes", "economic_events"):
            value = root.get(key) if isinstance(root, Mapping) else None
            if isinstance(value, list):
                changes.extend(str(item) for item in value if item)
            elif isinstance(value, Mapping):
                changes.extend(str(item) for item in value.get("reasons", []) if item)
    for event in packet.get("events", []) if isinstance(packet.get("events"), list) else []:
        if isinstance(event, Mapping) and event.get("material") is True:
            changes.append(str(event.get("reason") or event.get("event") or "material event"))
    return sorted(set(changes))


def _current_claim_gaps(rows: list[Mapping[str, Any]], period: str) -> list[str]:
    gaps: list[str] = []
    for row in rows:
        if not _period_match(row, start=None, end=period) or _dimensions(row):
            continue
        qname = str(row.get("qname") or row.get("local_name") or "").lower()
        value = row.get("value", row.get("val"))
        if not isinstance(value, (int, float)) or float(value) == 0:
            continue
        if any(token in qname for token in ("preferredstock", "preferredequity", "temporaryequity")):
            gaps.append("nonzero_current_preferred_or_temporary_equity_claim")
    return sorted(set(gaps))


def _common_capital_scope(rows: list[Mapping[str, Any]], *, period: str, parent_book: float,
                          filing: Mapping[str, Any], packet: Mapping[str, Any], cutoff: str) -> dict[str, Any]:
    """Prove current common capital without treating authorization as a claim."""
    current = [row for row in rows if row.get("_source_kind") == "structural_xbrl"
               and _period_match(row, start=None, end=period) and (row.get("unit") or row.get("raw_unit")) in _USD]
    def amounts(qnames: set[str], dimensions: list[list[str]] | None = None) -> list[Mapping[str, Any]]:
        return [row for row in current if (row.get("qname") or row.get("concept")) in qnames
                and (dimensions is None or _dimensions(row) == dimensions)
                and "balance_sheet" in (row.get("statement_roles") or [])]
    preferred_claims = []
    for row in current:
        qname = str(row.get("qname") or row.get("local_name") or "")
        lower = qname.lower()
        if any(token in lower for token in ("preferredstock", "preferredequity", "temporaryequity")):
            if "authorized" in lower:
                continue
            if _value(row, "preferred current claim") != 0:
                preferred_claims.append(_fact_source(row, filing=filing, packet=packet, cutoff=cutoff, field="preferred current claim"))
    shares = []
    for row in current:
        local = str(row.get("local_name") or row.get("qname") or "").lower()
        if "preferredstockshares" in local and any(token in local for token in ("issued", "outstanding")) and _value(row, "preferred shares") != 0:
            shares.append(_value(row, "preferred shares"))
    if preferred_claims or shares:
        raise CommonRefreshError("current preferred issued/outstanding/carrying claim requires lifecycle reconciliation")
    common = amounts({"us-gaap:CommonStockValue"}, dimensions=[["us-gaap:StatementClassOfStockAxis", "us-gaap:CommonStockMember"]])
    if not common:
        common = amounts({"us-gaap:CommonStockValue"}, dimensions=[])
    if not common:
        common = amounts({"us-gaap:CommonStockNoParValue"}, dimensions=[])
    apic = amounts({"us-gaap:AdditionalPaidInCapitalCommonStock", "us-gaap:AdditionalPaidInCapital"}, dimensions=[])
    retained = amounts({"us-gaap:RetainedEarningsAccumulatedDeficit"}, dimensions=[])
    aoci = amounts({"us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax"}, dimensions=[])
    treasury = amounts({"us-gaap:TreasuryStockValue", "us-gaap:TreasuryStockCommonValue"}, dimensions=[])
    if not common or not apic or not retained or not aoci:
        raise CommonRefreshError("current common-capital component proof is incomplete")
    component_rows = [common[0], apic[0], retained[0], aoci[0]]
    treasury_value = _value(treasury[0], "treasury stock") if treasury else 0.0
    total = sum(_value(row, "common capital component") for row in component_rows) - treasury_value
    if not isclose(total, parent_book, rel_tol=0.0, abs_tol=0.01):
        raise CommonRefreshError("current common-capital components do not reconcile to parent book")
    nci = [row for row in current if (row.get("qname") or "").lower() in {"us-gaap:minorityinterest", "us-gaap:noncontrollinginterestinconsolidatedentity"}]
    return {
        "status": "current_common_capital_reconciled",
        "parent_common_book": parent_book,
        "components": [_fact_source(row, filing=filing, packet=packet, cutoff=cutoff, field="common capital component") for row in component_rows],
        "treasury_stock_value": treasury_value,
        "negative_or_nonzero_nci_observation": [_value(row, "NCI observation") for row in nci if isinstance(row.get("value", row.get("val")), (int, float))],
        "authorized_preferred_shares_are_not_claims": True,
    }


def _gate(ticker: str, packet: Mapping[str, Any], *, source_status: str, material_changes: list[str], preferred_gain: float) -> dict[str, Any]:
    reasons = list(material_changes)
    if source_status != "source_complete":
        reasons.append(source_status)
    return {
        "ready": not reasons,
        "reasons": sorted(set(reasons)),
        "preferred_redemption_gain_removed_once_USD": preferred_gain,
        "new_filing_alone_is_not_a_hold": True,
    }


def bind(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any], cutoff: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind one WCC/GRC frozen residual-income recipe to a cached current filing."""
    if not isinstance(policy, Mapping) or not isinstance(recipe, Mapping) or not isinstance(packet, Mapping):
        raise CommonRefreshError("policy, recipe, and packet must be mappings")
    cutoff = _iso(cutoff, "cutoff")
    ticker = _ticker(policy, recipe, packet)
    if recipe.get("schema_version") not in {None, "FINSIGHT-CALCULATION-RECIPE-1"}:
        raise CommonRefreshError("unsupported residual-income recipe schema")
    if any(spec.get("engine") != "residual_income" for spec in recipe.get("scenarios", {}).values() if isinstance(spec, Mapping)):
        raise CommonRefreshError("common-book refresh requires residual-income scenarios")
    filing = _filing(policy, packet, cutoff)
    cik = _cik(policy.get("cik") or packet.get("companyfacts", {}).get("cik") or packet.get("issuer", {}).get("cik"))
    structural = _structural(packet, filing)
    rows = _packet_facts(packet, filing)
    period = filing["reportDate"]
    current_book_row = _select(rows, qnames={"us-gaap:StockholdersEquity"}, start=None, end=period, units=_USD,
                               dimensions=[], require_role="balance_sheet", current_accession=filing["accessionNumber"], field="common_equity")
    current_shares_candidates = [row for row in rows if (row.get("qname") or row.get("concept")) == "us-gaap:CommonStockSharesOutstanding"
                                 and _period_match(row, start=None, end=period) and (row.get("unit") or row.get("raw_unit")) in _SHARES
                                 and row.get("_source_kind") == "structural_xbrl" and row.get("source_accession") == filing["accessionNumber"]]
    common_member = [row for row in current_shares_candidates if any("CommonStockMember" in member for dim in _dimensions(row) for member in dim)]
    no_dimension = [row for row in current_shares_candidates if not _dimensions(row)]
    shares_pool = common_member or no_dimension
    if not shares_pool:
        raise CommonRefreshError("point common shares are missing from current controlling filing")
    if len({_value(row, "point_common_shares") for row in shares_pool}) != 1:
        raise CommonRefreshError("point common shares conflict across class facts")
    shares_row = shares_pool[0]
    current_book = _fact_source(current_book_row, filing=filing, packet=packet, cutoff=cutoff, field="common_equity")
    point_shares = _fact_source(shares_row, filing=filing, packet=packet, cutoff=cutoff, field="point_common_shares")
    capital_scope = _common_capital_scope(rows, period=period, parent_book=current_book["value"], filing=filing, packet=packet, cutoff=cutoff)
    common_qnames = {"us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic"} if ticker == "WCC" else {"us-gaap:NetIncomeLoss"}
    if ticker == "WCC":
        try:
            direct_source = _primary_table_ttm(packet, filing, field="direct_common_earnings_ttm")
            direct_value = direct_source["value"]
            direct_sources = [direct_source]
        except CommonRefreshError:
            direct_value, direct_sources = _ttm_fact(rows, qnames=common_qnames, period=period, units=_USD,
                                                     field="direct_common_earnings_ttm", filing=filing, packet=packet, cutoff=cutoff)
            direct_source = None
        direct_status = "source_complete" if direct_source is not None else "direct_common_ttm_table_not_captured"
        try:
            bridge_value, bridge_sources = _ttm_fact(rows, qnames=common_qnames, period=period, units=_USD,
                                                     field="direct_common_earnings_ttm_bridge", filing=filing, packet=packet, cutoff=cutoff)
        except CommonRefreshError:
            bridge_value, bridge_sources = None, []
    else:
        direct_value, direct_sources = _ttm_fact(rows, qnames=common_qnames, period=period, units=_USD,
                                                 field="direct_common_earnings_ttm", filing=filing, packet=packet, cutoff=cutoff)
        bridge_value, bridge_sources = direct_value, direct_sources
        direct_source = None
        direct_status = "source_complete"
    if ticker == "WCC" and direct_source is not None:
        preferred_source = _primary_table_ttm(packet, filing, field="preferred_redemption_gain")
        preferred_gain = preferred_source["value"]
        preferred_sources = [preferred_source]
    else:
        preferred_gain, preferred_sources = _preferred_gain_ttm(rows, period=period, filing=filing, packet=packet, cutoff=cutoff)
    common_earnings = direct_value - preferred_gain
    if common_earnings <= 0:
        raise CommonRefreshError("current common earnings must remain positive")
    dividends, dividend_sources = _ttm_fact(rows, qnames=_DIVIDENDS, period=period, units=_USD,
                                            field="common_dividends_ttm", filing=filing, packet=packet, cutoff=cutoff)
    if dividends < 0:
        raise CommonRefreshError("common dividends cannot be negative")
    payout = dividends / common_earnings
    if not 0 <= payout < 1:
        raise CommonRefreshError("common payout ratio is outside [0,1)")
    roe_base, roe_history, roe_status = _annual_roe(rows, period=period, ticker=ticker, filing=filing, packet=packet, cutoff=cutoff)
    if roe_base is None:
        roe_base = common_earnings / _value(current_book_row, "common_equity")
    if roe_base <= 0 or not isfinite(roe_base):
        raise CommonRefreshError("current common ROE is not positive and finite")
    material_changes = _material_changes(policy, packet) + _current_claim_gaps(rows, period)
    gate = _gate(ticker, packet, source_status=direct_status, material_changes=material_changes, preferred_gain=preferred_gain)
    if not gate["ready"]:
        raise CommonRefreshError("common refresh gate failed: " + "; ".join(gate["reasons"]))
    # Preserve all approved scenario assumptions except source-dependent book,
    # payout, and current ROE.  Scenario ROE factors are retained exactly.
    refreshed = deepcopy(recipe)
    base_old = recipe["scenarios"]["base"]["inputs"]
    old_base_roe = float(base_old["current_roe"])
    if old_base_roe <= 0:
        raise CommonRefreshError("frozen base current ROE must be positive")
    refreshed_base_roe = roe_base
    for name, spec in refreshed["scenarios"].items():
        inputs = spec["inputs"]
        factor = float(inputs["current_roe"]) / old_base_roe
        inputs["book_value_per_share"] = _value(current_book_row, "common_equity") / _value(shares_row, "point_common_shares")
        inputs["current_payout_ratio"] = payout
        inputs["current_roe"] = refreshed_base_roe * factor
    refreshed["evidence_cutoff"] = cutoff
    refreshed["source_accession"] = filing["accessionNumber"]
    refreshed["refresh_binding_version"] = SCHEMA_VERSION
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "ticker": ticker,
        "cik": cik,
        "evidence_cutoff": cutoff,
        "required_source_fields": [
            "current_parent_common_book",
            "current_common_stock_shares_outstanding_point_not_issued_or_weighted_average",
            "ttm_common_earnings",
            "ttm_common_dividends",
            "preferred_redemption_and_preferred_lifecycle",
            "current_nci_and_non_common_book_claims",
        ],
        "controlling_filing": {"accession": filing["accessionNumber"], "filed_date": filing["filingDate"], "report_date": period, "form": filing["form"]},
        "inputs": {
            "common_equity_USD": current_book["value"],
            "point_common_shares": point_shares["value"],
            "common_earnings_ttm_USD": common_earnings,
            "direct_common_earnings_ttm_USD": direct_value,
            "preferred_redemption_gain_removed_once_USD": preferred_gain,
            "common_dividends_ttm_USD": dividends,
            "book_value_per_share": current_book["value"] / point_shares["value"],
            "current_payout_ratio": payout,
            "current_roe": refreshed_base_roe,
        },
        "source_facts": {
            "common_equity": current_book,
            "point_common_shares": point_shares,
            "current_common_capital_scope": capital_scope,
            "direct_common_earnings_ttm": direct_sources,
            "annual_ytd_bridge_diagnostic": {"value": bridge_value, "difference_from_reported_USD": (direct_value - bridge_value) if bridge_value is not None else None, "sources": bridge_sources},
            "preferred_redemption_gain": preferred_sources,
            "common_dividends_ttm": dividend_sources,
            "annual_roe_history": roe_history,
        },
        "roe_history": {"status": roe_status, "median": roe_base if roe_history else None, "observations": len(roe_history)},
        "warnings": list(refreshed.get("warnings", [])) + ([
            "Historical preferred lifecycle and acquisition comparability remain a Low uncertainty warning; current-common ROE uses current adjusted common earnings / current parent common book.",
            "Negative NCI is retained as an observation outside parent/common book and common earnings; it is neither clipped nor credited.",
        ] if ticker == "WCC" else []),
        "assumptions_retained": {
            "cost_of_equity": True,
            "terminal_growth": True,
            "terminal_roe": True,
            "years": True,
            "scenario_roe_factors": True,
            "warnings": refreshed.get("warnings") == recipe.get("warnings"),
        },
        "baseline_replay": evaluate_recipe(recipe)["range"],
        "refreshed_replay": evaluate_recipe(refreshed)["range"],
        "gate": gate,
        "source_status": direct_status,
        "no_network_or_capture": packet.get("network_mode") in {None, "cache_only", "offline", "replay"},
    }
    return refreshed, ledger


def validate_ready(ledger: Mapping[str, Any]) -> dict[str, Any]:
    gate = ledger.get("gate") if isinstance(ledger, Mapping) else None
    if not isinstance(gate, Mapping):
        return {"ready": False, "reasons": ["missing_common_refresh_gate"]}
    reasons = gate.get("reasons", [])
    return {"ready": gate.get("ready") is True and not reasons, "reasons": list(reasons)}


def is_ready(ledger: Mapping[str, Any]) -> bool:
    return bool(validate_ready(ledger)["ready"])


def policy_readiness(policy: Mapping[str, Any], recipe: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the narrow dispatch contract without inspecting filing data."""
    reasons: list[str] = []
    if policy.get("schema_version") != "FINSIGHT-B01-SUPPORTED-REFRESH-1":
        reasons.append("unsupported_common_refresh_policy_schema")
    if policy.get("profile") != "parent_common_ri":
        reasons.append("unsupported_common_refresh_profile")
    ticker = str(policy.get("ticker") or recipe.get("ticker") or "").upper()
    if ticker not in SUPPORTED:
        reasons.append("unsupported_common_refresh_ticker")
    expected_cik = policy.get("expected_cik") or policy.get("cik")
    recipe_cik = policy.get("cik") or recipe.get("cik")
    if not expected_cik:
        reasons.append("expected_cik_missing")
    if expected_cik is not None and recipe_cik is not None:
        try:
            if _cik(expected_cik) != _cik(recipe_cik):
                reasons.append("policy_recipe_cik_mismatch")
        except CommonRefreshError:
            reasons.append("invalid_policy_cik")
    if not policy.get("source_epoch"):
        reasons.append("source_epoch_missing")
    declared_fields = policy.get("required_source_fields")
    required_fields = {"current_parent_common_book", "current_common_stock_shares_outstanding_point_not_issued_or_weighted_average", "ttm_common_earnings"}
    if declared_fields is not None and not required_fields <= set(declared_fields):
        reasons.append("required_source_field_contract_mismatch")
    if recipe.get("schema_version") not in {None, "FINSIGHT-CALCULATION-RECIPE-1"}:
        reasons.append("unsupported_recipe_schema")
    scenarios = recipe.get("scenarios")
    if not isinstance(scenarios, Mapping) or set(scenarios) != {"bear", "base", "bull"}:
        reasons.append("scenario_contract_mismatch")
    else:
        required = {"book_value_per_share", "cost_of_equity", "current_payout_ratio", "current_roe", "terminal_growth", "terminal_roe", "years"}
        for name, spec in scenarios.items():
            if not isinstance(spec, Mapping) or spec.get("engine") != "residual_income" or not required <= set(spec.get("inputs", {})):
                reasons.append(f"{name}_scenario_contract_mismatch")
    return {"ready": not reasons, "reasons": reasons, "ticker": ticker, "profile": policy.get("profile")}


def ready(policy: Mapping[str, Any], recipe: Mapping[str, Any]) -> bool:
    """Boolean policy/recipe validator used by dispatch readiness."""
    return bool(policy_readiness(policy, recipe)["ready"])


bind_common_book_refresh = bind
