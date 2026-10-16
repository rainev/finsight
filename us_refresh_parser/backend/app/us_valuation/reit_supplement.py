"""Discovery and deterministic parsing for SEC-filed REIT Exhibit 99 supplements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
from html.parser import HTMLParser
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from .specialist_evidence import SpecialistFact


@dataclass(frozen=True)
class FiledExhibit:
    accession: str
    exhibit: str
    name: str
    source_url: str
    filed_date: str


def _sec_url(value: object) -> str:
    text = str(value or "")
    parsed = urlparse(text)
    if parsed.scheme != "https" or parsed.hostname not in {"www.sec.gov", "sec.gov"}:
        raise ValueError("Exhibit 99 source must be an official SEC HTTPS URL")
    return text


def discover_filed_exhibit99(
    filings: Sequence[Mapping[str, Any]], *, valuation_date: str
) -> FiledExhibit:
    date.fromisoformat(valuation_date)
    candidates: list[FiledExhibit] = []
    for filing in filings:
        if str(filing.get("form") or "").upper() not in {"8-K", "8-K/A"}:
            continue
        filed = str(filing.get("filed") or "")
        try:
            date.fromisoformat(filed)
        except ValueError:
            continue
        if filed > valuation_date:
            continue
        accession = str(filing.get("accession") or "")
        for attachment in filing.get("attachments", ()):
            if not isinstance(attachment, Mapping):
                continue
            exhibit = str(attachment.get("exhibit") or "").upper().removeprefix("EX-")
            if not exhibit.startswith("99"):
                continue
            candidates.append(
                FiledExhibit(
                    accession=accession,
                    exhibit=exhibit,
                    name=str(attachment.get("name") or ""),
                    source_url=_sec_url(attachment.get("url")),
                    filed_date=filed,
                )
            )
    if not candidates:
        raise ValueError("no pre-cutoff SEC-filed Exhibit 99 attachment")

    def score(item: FiledExhibit) -> tuple[str, int, str, str]:
        name = item.name.casefold()
        supplement = 2 if "supp" in name else 1 if item.exhibit.startswith("99.2") else 0
        return item.filed_date, supplement, item.accession, item.name

    return max(candidates, key=score)


class _Rows(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] = []
        self._cell: list[str] = []
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() == "tr":
            self._row = []
        elif tag.casefold() in {"td", "th"}:
            self._cell, self._in_cell = [], True

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"td", "th"} and self._in_cell:
            self._row.append(" ".join("".join(self._cell).split()))
            self._in_cell = False
        elif tag.casefold() == "tr" and self._row:
            self.rows.append(self._row)


@dataclass(frozen=True)
class ReitReconciliationPacket:
    accession: str
    source_url: str
    period_end: str
    filed_date: str
    affo_definition: str
    facts: tuple[SpecialistFact, ...]
    source_sha256: str
    raw_signed_values: dict[str, float]
    reconciliation_status: str
    unexplained_affo_residual: float


_LABELS = {
    "ffo": "ffo",
    "ffo available to common stockholders": "ffo",
    "straight line rent": "straight_line_rent_adjustment",
    "straight line rent and expenses net": "straight_line_rent_adjustment",
    "recurring maintenance capital": "recurring_maintenance_capex",
    "recurring capital expenditures": "recurring_maintenance_capex",
    "affo": "affo",
    "affo available to common stockholders": "affo",
    "occupancy": "occupancy",
}


def _number(value: str, amount_unit: str) -> tuple[float, str] | None:
    text = value.strip()
    match = re.search(r"\(?\$?([0-9][0-9,]*(?:\.[0-9]+)?)\)?\s*(%)?", text)
    if match is None:
        return None
    result = float(match.group(1).replace(",", ""))
    if "(" in text and ")" in text:
        result = -result
    if match.group(2):
        return round(result / 100.0, 12), "ratio"
    return result, amount_unit


def parse_reit_reconciliation(
    html: str,
    *,
    accession: str,
    source_url: str,
    period_end: str,
    filed_date: str,
    valuation_date: str,
    amount_unit: str = "USD millions",
) -> ReitReconciliationPacket:
    _sec_url(source_url)
    date.fromisoformat(period_end)
    date.fromisoformat(filed_date)
    date.fromisoformat(valuation_date)
    if filed_date > valuation_date or period_end > valuation_date:
        raise ValueError("REIT supplement is after the valuation cutoff")
    parser = _Rows()
    parser.feed(html)
    target_column: int | None = None
    for row in parser.rows:
        matches = [
            index
            for index, cell in enumerate(row)
            if cell in {period_end, date.fromisoformat(period_end).strftime("%B %d, %Y").replace(" 0", " ")}
        ]
        if len(matches) == 1:
            target_column = matches[0]
            break
    selected: dict[str, SpecialistFact] = {}
    raw_signed_values: dict[str, float] = {}
    for row in parser.rows:
        if len(row) < 2:
            continue
        label = " ".join(re.sub(r"[^a-z0-9]+", " ", row[0].casefold()).split())
        field = next((field for phrase, field in _LABELS.items() if label == phrase), None)
        if field is None:
            continue
        if len(row) > 2 and target_column is None:
            raise ValueError("REIT supplement has multiple columns without one exact period column")
        cell = row[target_column] if target_column is not None and target_column < len(row) else row[-1]
        parsed = _number(cell, amount_unit)
        if parsed is None:
            continue
        raw_value, unit = parsed
        raw_signed_values[field] = raw_value
        value = (
            abs(raw_value)
            if field in {"straight_line_rent_adjustment", "recurring_maintenance_capex"}
            else raw_value
        )
        if field in selected:
            raise ValueError(f"ambiguous REIT supplement row for {field}")
        selected[field] = SpecialistFact(
            field=field,
            value=value,
            unit=unit,
            period_end=period_end,
            filed_date=filed_date,
            source_url=source_url,
            source_record_id=f"{accession}:{row[0]}",
            extraction_method="sec_filed_exhibit99_table",
        )
    required = {
        "ffo", "affo", "straight_line_rent_adjustment",
        "recurring_maintenance_capex", "occupancy",
    }
    if required - set(selected):
        raise ValueError(f"REIT reconciliation is incomplete: {sorted(required - set(selected))}")
    explained_affo = (
        selected["ffo"].value
        - selected["straight_line_rent_adjustment"].value
        - selected["recurring_maintenance_capex"].value
    )
    residual = round(selected["affo"].value - explained_affo, 12)
    return ReitReconciliationPacket(
        accession=accession,
        source_url=source_url,
        period_end=period_end,
        filed_date=filed_date,
        affo_definition="issuer_defined",
        facts=tuple(selected[field] for field in sorted(selected)),
        source_sha256=hashlib.sha256(html.encode()).hexdigest(),
        raw_signed_values=dict(sorted(raw_signed_values.items())),
        reconciliation_status="pass" if abs(residual) <= 0.01 else "unresolved_residual",
        unexplained_affo_residual=residual,
    )
