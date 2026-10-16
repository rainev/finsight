"""Deterministic, date-aware numeric table evidence extraction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import json
import re
from typing import Any, Mapping, Sequence


def _clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _normalized(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def _date_label(value: str) -> str | None:
    cleaned = _clean(value).replace("Sept ", "Sep ")
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _number(value: str) -> float | None:
    text = _clean(value)
    match = re.fullmatch(r"\s*\(?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*\)?\s*", text)
    if match is None:
        return None
    result = float(match.group(1).replace(",", ""))
    return -result if "(" in text and ")" in text else result


@dataclass(frozen=True)
class _Table:
    title: str
    scope_text: str
    rows: tuple[tuple[str, ...], ...]


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[_Table] = []
        self._in_table = False
        self._in_caption = False
        self._in_cell = False
        self._caption: list[str] = []
        self._cell: list[str] = []
        self._row: list[str] = []
        self._rows: list[tuple[str, ...]] = []
        self._recent_text: list[str] = []
        self._scope_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag == "table":
            self._scope_text = " ".join(self._recent_text[-5:])
            self._in_table = True
            self._caption, self._rows = [], []
        elif self._in_table and tag == "caption":
            self._in_caption = True
        elif self._in_table and tag == "tr":
            self._row = []
        elif self._in_table and tag in {"td", "th"}:
            self._in_cell = True
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._in_caption:
            self._caption.append(data)
        if self._in_cell:
            self._cell.append(data)
        elif not self._in_table:
            cleaned = _clean(data)
            if cleaned:
                self._recent_text.append(cleaned)
                self._recent_text = self._recent_text[-20:]

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if self._in_table and tag in {"td", "th"} and self._in_cell:
            self._row.append(_clean("".join(self._cell)))
            self._in_cell = False
        elif self._in_table and tag == "tr":
            if any(self._row):
                self._rows.append(tuple(self._row))
            self._row = []
        elif self._in_table and tag == "caption":
            self._in_caption = False
        elif tag == "table" and self._in_table:
            self.tables.append(
                _Table(
                    title=_clean("".join(self._caption)) or self._scope_text or "Untitled table",
                    scope_text=self._scope_text,
                    rows=tuple(self._rows),
                )
            )
            self._in_table = False


@dataclass(frozen=True)
class TableEvidence:
    required_field: str
    status: str
    value: float | None
    table_title: str | None
    row_label: str | None
    column_label: str | None
    period_end: str
    unit: str
    scale: float
    source_accession: str
    source_url: str
    filed_date: str
    entity_identifier: str
    consolidation_scope: str
    package_sha256: str
    excerpt: str
    reason_codes: tuple[str, ...]
    candidate_locators: tuple[str, ...]
    searched_table_count: int
    search_scope_hash: str


@dataclass(frozen=True)
class TableExtractionResult:
    evidence: tuple[TableEvidence, ...]
    complete_search: bool
    searched_table_count: int
    search_scope_hash: str
    scope_kind: str


def _row_matches(field: str, label: str, section: str = "") -> bool:
    text = _normalized(label)
    context = _normalized(section)
    if field == "cash":
        return text in {"cash and cash equivalents", "cash and equivalents"}
    if field == "marketable_securities_current":
        return text in {"marketable securities", "current marketable securities"} and (
            "current" in text or "current assets" in context
        )
    if field == "marketable_securities_noncurrent":
        return text in {"marketable securities", "noncurrent marketable securities"} and (
            "noncurrent" in text or "noncurrent assets" in context
        )
    if field == "marketable_securities_total":
        return text == "total marketable securities"
    if field == "commercial_paper":
        return text in {"commercial paper", "commercial paper outstanding"}
    if field == "current_debt":
        return text in {
            "current debt",
            "short term debt",
            "current portion of long term debt",
            "current maturities of long term debt",
        }
    if field == "noncurrent_debt":
        return text in {"noncurrent debt", "long term debt", "long term debt noncurrent"}
    if field == "finance_lease_current":
        return text in {"current finance lease liabilities", "finance lease liabilities current"}
    if field == "finance_lease_noncurrent":
        return text in {"noncurrent finance lease liabilities", "finance lease liabilities noncurrent"}
    if field == "finance_lease_total":
        return text in {"finance lease liabilities", "total finance lease liabilities"}
    if field == "preferred_equity":
        return text in {"preferred stock", "preferred equity", "temporary equity"}
    if field == "noncontrolling_interests":
        return text in {"noncontrolling interests", "noncontrolling interest in consolidated entities"}
    tokens = tuple(token for token in _normalized(field).split() if token not in {"the", "and"})
    return bool(tokens) and all(token in set(text.split()) for token in tokens)


def _scope_hash(tables: Sequence[_Table], salt: object = None) -> str:
    payload = [
        {"title": table.title, "scope_text": table.scope_text, "rows": table.rows}
        for table in tables
    ]
    encoded = json.dumps(
        {"tables": payload, "resource_scope": salt},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _unit_scale(value: object, table: _Table) -> tuple[str | None, float | None]:
    text = _normalized(str(value or "") + " " + table.title + " " + table.scope_text)
    if "usd billions" in text or "dollars in billions" in text or "in billions" in text:
        return "USD billions", 1_000_000_000.0
    if "usd millions" in text or "dollars in millions" in text or "in millions" in text:
        return "USD millions", 1_000_000.0
    if "usd thousands" in text or "dollars in thousands" in text or "in thousands" in text:
        return "USD thousands", 1_000.0
    if str(value or "").strip() == "USD":
        return "USD", 1.0
    return None, None


def extract_numeric_table_evidence(
    html: str,
    requests: Sequence[Mapping[str, Any]],
    metadata: Mapping[str, Any],
) -> TableExtractionResult:
    required_metadata = (
        "source_accession",
        "source_url",
        "filed_date",
        "period_end",
        "entity_identifier",
        "consolidation_scope",
        "package_sha256",
    )
    if any(not isinstance(metadata.get(key), str) or not metadata[key] for key in required_metadata):
        raise ValueError("table evidence requires complete filing, entity, scope, and package lineage")
    parser = _TableParser()
    parser.feed(html)
    parser.close()
    tables = tuple(parser.tables)
    scope_hash = _scope_hash(tables, metadata.get("search_scope_hash_salt"))
    scope_complete = metadata.get("search_scope_complete", True) is True
    scope_kind = str(
        metadata.get("search_scope_kind")
        or ("complete_governed_scope" if scope_complete else "primary_document_only")
    )
    evidence: list[TableEvidence] = []

    for request in requests:
        field = str(request.get("required_field") or "")
        if not field:
            raise ValueError("table request required_field is missing")
        candidates: list[tuple[float, str, float, str, str, str, str]] = []
        unscaled_locators: list[str] = []
        for table_index, table in enumerate(tables):
            if not table.rows:
                continue
            role = str(request.get("statement_role") or "")
            table_context = _normalized(table.title + " " + table.scope_text)
            if role == "balance_sheet" and any(
                phrase in table_context
                for phrase in (
                    "maturities", "maturity schedule", "future payments",
                    "commitments", "contractual obligations",
                )
            ):
                continue
            if field in {"cash", "commercial_paper"} and any(
                phrase in table_context
                for phrase in (
                    "marketable securities", "investment category",
                    "available for sale", "financial instruments",
                )
            ):
                continue
            header = table.rows[0]
            dated_headers = [
                (_date_label(label), label, index)
                for index, label in enumerate(header)
                if _date_label(label) is not None
            ]
            current_headers = [item for item in dated_headers if item[0] == metadata["period_end"]]
            if len(current_headers) != 1:
                continue
            _, column_label, _ = current_headers[0]
            target_rank = dated_headers.index(current_headers[0])
            section = ""
            for row_index, row in enumerate(table.rows[1:], start=1):
                if not row:
                    continue
                label = row[0]
                row_numbers = [value for cell in row[1:] if (value := _number(cell)) is not None]
                if not row_numbers and label:
                    section = label
                if not _row_matches(field, label, section):
                    continue
                if target_rank >= len(row_numbers):
                    continue
                value = row_numbers[target_rank]
                locator = f"table[{table_index}]/{table.title}/row[{row_index}]/{row[0]}/{column_label}"
                excerpt = " | ".join(row)
                unit, scale = _unit_scale(metadata.get("unit"), table)
                if unit is None or scale is None:
                    unscaled_locators.append(locator)
                    continue
                candidates.append((value, unit, scale, table.title, row[0], column_label, locator + "\n" + excerpt))

        locators = tuple(item[6].split("\n", 1)[0] for item in candidates)
        if len(candidates) == 1:
            value, unit, scale, title, row_label, column_label, located = candidates[0]
            consolidated_scope = (
                "consolidated_parent"
                if "consolidated" in _normalized(title)
                else "unknown"
            )
            evidence.append(
                TableEvidence(
                    required_field=field,
                    status="reported",
                    value=value,
                    table_title=title,
                    row_label=row_label,
                    column_label=column_label,
                    period_end=str(metadata["period_end"]),
                    unit=unit,
                    scale=scale,
                    source_accession=str(metadata["source_accession"]),
                    source_url=str(metadata["source_url"]),
                    filed_date=str(metadata["filed_date"]),
                    entity_identifier=str(metadata["entity_identifier"]),
                    consolidation_scope=consolidated_scope,
                    package_sha256=str(metadata["package_sha256"]),
                    excerpt=located.split("\n", 1)[1],
                    reason_codes=("DETERMINISTIC_DATED_TABLE_CELL",),
                    candidate_locators=locators,
                    searched_table_count=len(tables),
                    search_scope_hash=scope_hash,
                )
            )
        elif len(candidates) > 1:
            evidence.append(
                TableEvidence(
                    required_field=field,
                    status="unresolved",
                    value=None,
                    table_title=None,
                    row_label=None,
                    column_label=None,
                    period_end=str(metadata["period_end"]),
                    unit=str(metadata.get("unit") or "unknown"),
                    scale=1.0,
                    source_accession=str(metadata["source_accession"]),
                    source_url=str(metadata["source_url"]),
                    filed_date=str(metadata["filed_date"]),
                    entity_identifier=str(metadata["entity_identifier"]),
                    consolidation_scope=str(metadata["consolidation_scope"]),
                    package_sha256=str(metadata["package_sha256"]),
                    excerpt="",
                    reason_codes=("AMBIGUOUS", "AMBIGUOUS_TABLE_CANDIDATES"),
                    candidate_locators=locators,
                    searched_table_count=len(tables),
                    search_scope_hash=scope_hash,
                )
            )
        elif unscaled_locators:
            evidence.append(
                TableEvidence(
                    required_field=field,
                    status="unresolved",
                    value=None,
                    table_title=None,
                    row_label=None,
                    column_label=None,
                    period_end=str(metadata["period_end"]),
                    unit="unknown",
                    scale=1.0,
                    source_accession=str(metadata["source_accession"]),
                    source_url=str(metadata["source_url"]),
                    filed_date=str(metadata["filed_date"]),
                    entity_identifier=str(metadata["entity_identifier"]),
                    consolidation_scope=str(metadata["consolidation_scope"]),
                    package_sha256=str(metadata["package_sha256"]),
                    excerpt="",
                    reason_codes=("TABLE_UNIT_SCALE_UNRESOLVED",),
                    candidate_locators=tuple(unscaled_locators),
                    searched_table_count=len(tables),
                    search_scope_hash=scope_hash,
                )
            )
        else:
            evidence.append(
                TableEvidence(
                    required_field=field,
                    status="not_disclosed" if scope_complete else "unresolved",
                    value=None,
                    table_title=None,
                    row_label=None,
                    column_label=None,
                    period_end=str(metadata["period_end"]),
                    unit=str(metadata.get("unit") or "unknown"),
                    scale=1.0,
                    source_accession=str(metadata["source_accession"]),
                    source_url=str(metadata["source_url"]),
                    filed_date=str(metadata["filed_date"]),
                    entity_identifier=str(metadata["entity_identifier"]),
                    consolidation_scope=str(metadata["consolidation_scope"]),
                    package_sha256=str(metadata["package_sha256"]),
                    excerpt="",
                    reason_codes=(
                        ("COMPLETE_TABLE_SEARCH_NO_MATCH",)
                        if scope_complete
                        else ("INCOMPLETE_PACKAGE_TABLE_SCOPE",)
                    ),
                    candidate_locators=(),
                    searched_table_count=len(tables),
                    search_scope_hash=scope_hash,
                )
            )
    return TableExtractionResult(
        evidence=tuple(evidence),
        complete_search=scope_complete,
        searched_table_count=len(tables),
        search_scope_hash=scope_hash,
        scope_kind=scope_kind,
    )
