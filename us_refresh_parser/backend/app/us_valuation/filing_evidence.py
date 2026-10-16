"""Auditable evidence recovery from SEC filing HTML and footnote tables.

The extractor is deliberately conservative. It records context that does not
map cleanly to a balance-sheet bridge field as unresolved/context-only rather
than converting a maturity schedule or a narrative absence into a debt value.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from html.parser import HTMLParser
import re
from typing import Any, Iterable, Mapping


EVIDENCE_SCHEMA_VERSION = "US-FILING-EVIDENCE-1.0"
BRIDGE_FIELDS = frozenset(
    {
        "marketable_securities_current",
        "marketable_securities_noncurrent",
        "marketable_securities_total",
        "commercial_paper",
        "current_debt",
        "noncurrent_debt",
        "finance_lease_current",
        "finance_lease_noncurrent",
        "finance_lease_total",
        "preferred_equity",
        "noncontrolling_interests",
    }
)


class _VisibleTextParser(HTMLParser):
    """Convert filing HTML into stable, line-oriented visible text."""

    _BREAK_TAGS = {"br", "div", "li", "p", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._BREAK_TAGS:
            self._parts.append("\n")
        elif tag in {"td", "th"}:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BREAK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def lines(self) -> list[str]:
        return [
            " ".join(line.split())
            for line in "".join(self._parts).splitlines()
            if line.strip()
        ]


@dataclass(frozen=True)
class FilingEvidence:
    """One source-backed assertion or unresolved source observation."""

    ticker: str
    cik: str
    field: str
    value: float | None
    raw_value: float | None
    unit: str
    period_end: str
    filing_date: str
    source_accession: str
    source_url: str
    form: str
    source_kind: str
    status: str
    confidence: str
    locator: str
    excerpt: str
    rationale: str
    parser_version: str = EVIDENCE_SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_metadata(metadata: Mapping[str, Any]) -> None:
    required = (
        "ticker",
        "cik",
        "period_end",
        "filing_date",
        "source_accession",
        "source_url",
        "form",
    )
    missing = [key for key in required if not metadata.get(key)]
    if missing:
        raise ValueError("Filing evidence metadata is missing: " + ", ".join(missing))


def _record(
    metadata: Mapping[str, Any],
    *,
    field: str,
    value: float | None,
    raw_value: float | None = None,
    source_kind: str,
    status: str,
    confidence: str,
    locator: str,
    excerpt: str,
    rationale: str,
) -> FilingEvidence:
    return FilingEvidence(
        ticker=str(metadata["ticker"]).upper(),
        cik=str(metadata["cik"]).zfill(10),
        field=field,
        value=value,
        raw_value=raw_value if raw_value is not None else value,
        unit=str(metadata.get("unit") or "USD millions"),
        period_end=str(metadata["period_end"]),
        filing_date=str(metadata["filing_date"]),
        source_accession=str(metadata["source_accession"]),
        source_url=str(metadata["source_url"]),
        form=str(metadata["form"]),
        source_kind=source_kind,
        status=status,
        confidence=confidence,
        locator=locator,
        excerpt=excerpt,
        rationale=rationale,
    )


def _compact(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _line_excerpt(lines: list[str], index: int, radius: int = 1) -> str:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    return " ".join(_compact(line) for line in lines[start:end])


def _last_number(line: str) -> float | None:
    matches = re.findall(r"\(?\$?([0-9][0-9,]*(?:\.[0-9]+)?)\)?", line)
    if not matches:
        return None
    raw = matches[-1].replace(",", "")
    return float(raw)


def extract_filing_evidence(
    html: str, *, metadata: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Extract a small, auditable set of bridge observations from filing HTML.

    This pilot handles recurring table/note patterns found in the CRM and WDC
    filings. Unknown layouts produce no resolved values; callers should keep the
    corresponding bridge field withheld.
    """

    _require_metadata(metadata)
    parser = _VisibleTextParser()
    parser.feed(html)
    lines = parser.lines()
    compact_lines = [_compact(line) for line in lines]
    records: list[FilingEvidence] = []
    ticker = str(metadata["ticker"]).upper()

    # A note-table total is not a current/noncurrent classification by itself.
    # CRM is the governed pilot whose balance sheet separately proves the full
    # amount is current; other issuers retain the observation as an unproven
    # total candidate until coverage metadata is supplied.
    total_index = next(
        (
            index
            for index, line in enumerate(compact_lines)
            if line.lower().startswith("total marketable securities")
        ),
        None,
    )
    if total_index is not None:
        total = _last_number(compact_lines[total_index])
        if total is not None:
            records.append(
                _record(
                    metadata,
                    field=(
                        "marketable_securities_current"
                        if ticker == "CRM"
                        else "marketable_securities_total"
                    ),
                    value=total,
                    source_kind="filing_table",
                    status="resolved",
                    confidence="high",
                    locator="marketable securities table/current-period total",
                    excerpt=_line_excerpt(compact_lines, total_index),
                    rationale=(
                        "CRM's balance-sheet classification proves this full marketable-securities balance is current."
                        if ticker == "CRM"
                        else "The filing presents a marketable-securities total, but current/noncurrent and complete economic coverage remain unproven."
                    ),
                )
            )

    commercial_index = next(
        (
            index
            for index, line in enumerate(compact_lines[: total_index or len(compact_lines)])
            if line.lower().startswith("commercial paper")
        ),
        None,
    )
    if commercial_index is not None:
        reported = _last_number(compact_lines[commercial_index])
        if reported is not None:
            records.append(
                _record(
                    metadata,
                    field="commercial_paper",
                    value=0,
                    raw_value=reported,
                    source_kind="filing_note",
                    status="resolved",
                    confidence="high",
                    locator="marketable securities table/commercial paper row",
                    excerpt=_line_excerpt(compact_lines, commercial_index),
                    rationale="Commercial paper is presented within marketable securities; it is an investment asset, not commercial-paper borrowing.",
                )
            )

    lease_index = next(
        (
            index
            for index, line in enumerate(compact_lines)
            if "maturities of lease liabilities" in line.lower()
            and "finance leases" in " ".join(compact_lines[index : index + 3]).lower()
        ),
        None,
    )
    if lease_index is not None:
        lease_lines = compact_lines[lease_index : lease_index + 20]
        total_lines = [
            _last_number(line)
            for line in lease_lines
            if line.lower().startswith("total") and _last_number(line) is not None
        ]
        total_commitment = total_lines[-1] if total_lines else None
        excerpt = " ".join(lease_lines[: min(len(lease_lines), 10)])
        if total_commitment is not None:
            records.append(
                _record(
                    metadata,
                    field="finance_lease_total_commitments",
                    value=total_commitment,
                    source_kind="filing_note",
                    status="context_only",
                    confidence="high",
                    locator="lease commitments maturity table/net minimum payments",
                    excerpt=excerpt,
                    rationale="The footnote provides future minimum payments net of imputed interest, not the balance-sheet current/noncurrent carrying-value split.",
                )
            )
        for field in ("finance_lease_current", "finance_lease_noncurrent"):
            records.append(
                _record(
                    metadata,
                    field=field,
                    value=None,
                    raw_value=None,
                    source_kind="filing_note",
                    status="unresolved",
                    confidence="high",
                    locator="lease commitments maturity table",
                    excerpt=excerpt,
                    rationale="The filing identifies finance-lease commitments but does not disclose the current/noncurrent balance-sheet carrying-value split; no split is inferred.",
                )
            )

    if ticker == "WDC":
        balance_index = next(
            (
                index
                for index, line in enumerate(compact_lines)
                if line.lower().startswith("balance at")
                and "convertible preferred stock" in " ".join(
                    compact_lines[index : index + 5]
                ).lower()
                and "—" in " ".join(compact_lines[index : index + 5])
            ),
            None,
        )
        conversion_index = next(
            (
                index
                for index, line in enumerate(compact_lines)
                if "converted all remaining outstanding" in " ".join(
                    compact_lines[index : index + 3]
                ).lower()
                and "preferred" in " ".join(compact_lines[index : index + 3]).lower()
            ),
            None,
        )
        if balance_index is not None and conversion_index is not None:
            excerpt = " ".join(
                [
                    _line_excerpt(compact_lines, balance_index),
                    _line_excerpt(compact_lines, conversion_index),
                ]
            )
            records.append(
                _record(
                    metadata,
                    field="preferred_equity",
                    value=0,
                    source_kind="filing_note",
                    status="resolved",
                    confidence="high",
                    locator="Note 12/preferred-stock balance and conversion disclosure",
                    excerpt=excerpt,
                    rationale="The current-period balance is zero and the filing states that all remaining preferred shares were converted and eliminated before period end.",
                )
            )

    return [record.as_dict() for record in records]


def governed_bridge_fields_from_evidence(
    records: Iterable[Mapping[str, Any]], *, as_of_date: str | None = None
) -> dict[str, dict[str, Any]]:
    """Convert only high-confidence resolved observations into bridge evidence."""

    governed: dict[str, dict[str, Any]] = {}
    for record in records:
        field = str(record.get("field") or "")
        value = record.get("value")
        if (
            field not in BRIDGE_FIELDS
            or record.get("status") != "resolved"
            or record.get("confidence") != "high"
            or not isinstance(value, (int, float))
            or isinstance(value, bool)
        ):
            continue
        filing_date = str(record.get("filing_date") or "")
        if as_of_date and (not filing_date or filing_date > as_of_date):
            continue
        candidate = {
            "value": float(value),
            "rationale": record.get("rationale"),
            "source_accession": record.get("source_accession"),
            "controlled_period_end": record.get("period_end"),
            "form": record.get("form"),
            "filing_date": filing_date,
            "unit": record.get("unit"),
            "source_url": record.get("source_url"),
            "reviewer": "FinSight filing evidence extractor",
            "verification_version": EVIDENCE_SCHEMA_VERSION,
            "source_kind": record.get("source_kind"),
            "source_locator": record.get("locator"),
            "evidence_excerpt": record.get("excerpt"),
        }
        existing = governed.get(field)
        if existing and (
            existing["value"] != candidate["value"]
            or existing["source_accession"] != candidate["source_accession"]
        ):
            raise ValueError(f"Conflicting resolved filing evidence for {field}")
        governed[field] = candidate
    return governed


def reconcile_total(
    *, total: float, components: Mapping[str, float], tolerance: float = 0.01
) -> dict[str, Any]:
    """Reconcile a reported total to extracted component values."""

    reported_total = float(total)
    component_total = float(sum(components.values()))
    difference = round(reported_total - component_total, 10)
    return {
        "status": "pass" if abs(difference) <= tolerance else "fail",
        "reported_total": reported_total,
        "component_total": component_total,
        "difference": difference,
        "tolerance": float(tolerance),
    }
