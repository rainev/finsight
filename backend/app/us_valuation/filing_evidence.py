"""Auditable evidence recovery from SEC filing HTML and footnote tables.

The extractor is deliberately conservative. It records context that does not
map cleanly to a balance-sheet bridge field as unresolved/context-only rather
than converting a maturity schedule or a narrative absence into a debt value.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html.parser import HTMLParser
import re
from typing import Any, Iterable, Mapping


EVIDENCE_SCHEMA_VERSION = "US-FILING-EVIDENCE-1.0"
BRIDGE_FIELDS = frozenset(
    {
        "marketable_securities_current",
        "marketable_securities_noncurrent",
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
    _IGNORED_TAGS = {
        "head",
        "link",
        "meta",
        "noscript",
        "script",
        "style",
        "svg",
        "title",
        "ix:header",
        "ix:hidden",
        "ix:references",
        "ix:resources",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag in self._BREAK_TAGS:
            self._parts.append("\n")
        elif tag in {"td", "th"}:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            if tag.lower() in self._IGNORED_TAGS:
                self._ignored_depth -= 1
            return
        if tag in self._BREAK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self._parts.append(re.sub(r"\s+", " ", data))

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
    evidence_class: str
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
    evidence_class: str | None = None,
) -> FilingEvidence:
    if evidence_class is None:
        if status in {"context_only", "unresolved"}:
            evidence_class = status
        elif "inferred_zero" in source_kind or "reconciled_classification" in source_kind:
            evidence_class = "inferred_zero"
        elif value == 0:
            evidence_class = "reported_zero"
        else:
            evidence_class = "reported"
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
        evidence_class=evidence_class,
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


def _value_tokens(line: str) -> list[float | None]:
    """Return numeric/dash column tokens without interpreting footnotes."""

    tokens = re.findall(
        r"(?:\(?\$?[0-9][0-9,]*(?:\.[0-9]+)?\)?|[—–-])", line
    )
    values: list[float | None] = []
    for token in tokens:
        if token in {"—", "–", "-"}:
            values.append(0.0)
        else:
            values.append(float(token.replace("$", "").replace(",", "").replace("(", "").replace(")", "")))
    return values


def _row_value(lines: list[str], index: int, label: str) -> float | None:
    """Read the first reporting-period column from a balance-sheet row."""

    label_match = re.search(re.escape(label), lines[index], re.IGNORECASE)
    remainder = lines[index][label_match.end() :] if label_match else lines[index]
    values = _value_tokens(remainder)
    if values:
        return values[0]
    for following in lines[index + 1 : index + 5]:
        values = _value_tokens(following)
        if values:
            return values[0]
    return None


def _balance_sheet_window(lines: list[str]) -> tuple[int, int]:
    """Locate the first actual balance-sheet table, excluding the table of contents."""
    candidates: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        lower = line.lower()
        if not re.fullmatch(
            r"(?:unaudited )?(?:condensed )?consolidated "
            r"(?:balance sheets?|statements of financial position)(?: as of .*)?",
            lower.strip(),
        ):
            continue
        total_assets_index = next(
            (
                candidate
                for candidate in range(index + 1, min(len(lines), index + 120))
                if lines[candidate].lower().startswith("total assets")
            ),
            None,
        )
        if total_assets_index is not None:
            candidates.append((total_assets_index - index, index))
    if not candidates:
        return 0, 0
    _, start = min(candidates)
    end = len(lines)
    saw_balance_totals = False
    for index in range(start + 1, min(len(lines), start + 180)):
        lower = lines[index].lower()
        if "total liabilities" in lower or "total assets" in lower:
            saw_balance_totals = True
        if saw_balance_totals and (
            "see accompanying notes" in lower
            or "the accompanying notes" in lower
            or "see notes to" in lower
        ):
            end = index
            break
    return start, end


def _statement_unit(lines: list[str], default: str = "USD millions") -> str:
    header = " ".join(lines[:20]).lower()
    if "in thousands" in header:
        return "USD thousands"
    if "in billions" in header:
        return "USD billions"
    if "in millions" in header:
        return "USD millions"
    return default


def _human_period(period_end: str) -> str:
    try:
        return date.fromisoformat(period_end).strftime("%B %-d, %Y")
    except (ValueError, TypeError):
        return period_end


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

    balance_start, balance_end = _balance_sheet_window(compact_lines)
    balance_lines = compact_lines[balance_start:balance_end]
    balance_metadata = {
        **metadata,
        "unit": _statement_unit(
            balance_lines,
            default=str(metadata.get("unit") or "USD millions"),
        ),
    }

    def add_record(record: FilingEvidence) -> None:
        if not any(
            existing.field == record.field
            and existing.value == record.value
            and existing.status == record.status
            for existing in records
        ):
            records.append(record)

    def add_balance_field(
        *, field: str, label: str, index: int, rationale: str
    ) -> None:
        value = _row_value(balance_lines, index, label)
        if value is None:
            return
        add_record(
            _record(
                balance_metadata,
                field=field,
                value=value,
                source_kind="filing_balance_sheet",
                status="resolved",
                confidence="high",
                locator=f"balance sheet/{label}",
                excerpt=_line_excerpt(balance_lines, index, radius=2),
                rationale=rationale,
            )
        )

    for index, line in enumerate(balance_lines):
        lower = line.lower()
        if lower.startswith(("marketable securities", "short-term marketable securities")):
            add_balance_field(
                field="marketable_securities_current",
                label=(
                    "short-term marketable securities"
                    if lower.startswith("short-term marketable securities")
                    else "marketable securities"
                ),
                index=index,
                rationale="The current-period balance-sheet row reports marketable securities as a current asset.",
            )
        elif lower.startswith("short-term investments"):
            add_balance_field(
                field="marketable_securities_current",
                label="short-term investments",
                index=index,
                rationale="The current-period balance-sheet row reports short-term investments as a current asset.",
            )
        elif lower.startswith("long-term marketable securities"):
            add_balance_field(
                field="marketable_securities_noncurrent",
                label="long-term marketable securities",
                index=index,
                rationale="The current-period balance-sheet row reports long-term marketable securities as a noncurrent asset.",
            )
        elif lower.startswith("current portion of long-term debt"):
            add_balance_field(
                field="current_debt",
                label="current portion of long-term debt",
                index=index,
                rationale="The current-period balance-sheet row reports the current portion of long-term debt.",
            )
        elif lower.startswith("short-term debt"):
            add_balance_field(
                field="current_debt",
                label="short-term debt",
                index=index,
                rationale="The current-period balance-sheet row reports short-term debt.",
            )
        elif lower.startswith("long-term debt currently due"):
            add_balance_field(
                field="current_debt",
                label="long-term debt currently due",
                index=index,
                rationale="The current-period balance-sheet row reports long-term debt currently due as current debt.",
            )
        elif lower.startswith("long-term debt") and "related party" not in lower[:80]:
            add_balance_field(
                field="noncurrent_debt",
                label="long-term debt",
                index=index,
                rationale="The current-period balance-sheet row reports noncurrent long-term debt.",
            )
        elif lower.startswith("long-term notes payable"):
            add_balance_field(
                field="noncurrent_debt",
                label="long-term notes payable",
                index=index,
                rationale="The current-period balance-sheet row reports noncurrent notes payable.",
            )
        elif lower.startswith(("noncontrolling interests", "non-controlling interests")):
            label = (
                "non-controlling interests"
                if lower.startswith("non-controlling interests")
                else "noncontrolling interests"
            )
            add_balance_field(
                field="noncontrolling_interests",
                label=label,
                index=index,
                rationale="The current-period balance sheet directly reports noncontrolling interests.",
            )

    if ticker == "ANET" and balance_lines:
        has_complete_liability_section = any(
            line.lower().startswith("total current liabilities")
            for line in balance_lines
        ) and any(
            line.lower().startswith("total liabilities") for line in balance_lines
        )
        has_financing_line = any(
            line.lower().startswith(
                (
                    "short-term debt",
                    "current portion of long-term debt",
                    "long-term debt",
                    "finance lease",
                    "capital lease",
                )
            )
            for line in balance_lines
        )
        if has_complete_liability_section and not has_financing_line:
            liabilities_index = next(
                index
                for index, line in enumerate(balance_lines)
                if line.lower().startswith("total liabilities")
            )
            for field in (
                "current_debt",
                "noncurrent_debt",
                "finance_lease_current",
                "finance_lease_noncurrent",
            ):
                if any(record.field == field for record in records):
                    continue
                add_record(
                    _record(
                        metadata,
                        field=field,
                        value=0,
                        source_kind="filing_balance_sheet_inferred_zero",
                        status="resolved",
                        confidence="high",
                        locator="balance sheet/complete liability section",
                        excerpt=_line_excerpt(
                            balance_lines, liabilities_index, radius=8
                        ),
                        rationale="The complete current-period liability presentation contains no debt or finance-lease liability line; this zero is a filing-statement inference rather than a separately reported fact.",
                    )
                )

    # Some issuers state the classification in a note rather than repeating a
    # zero row in the balance sheet. These are explicit classifications, not
    # generic absence-based zero overrides.
    if not any(
        record.field == "marketable_securities_noncurrent" for record in records
    ) and any(
        "maturities beyond 12 months as current assets" in line.lower()
        for line in compact_lines
    ) and any(
        record.field == "marketable_securities_current" for record in records
    ):
        index = next(
            index
            for index, line in enumerate(compact_lines)
            if "maturities beyond 12 months as current assets" in line.lower()
        )
        add_record(
            _record(
                metadata,
                field="marketable_securities_noncurrent",
                value=0,
                source_kind="filing_note",
                status="resolved",
                confidence="high",
                locator="marketable securities classification note",
                excerpt=_line_excerpt(compact_lines, index),
                rationale="The filing explicitly classifies securities with maturities beyond 12 months as current assets; no noncurrent marketable-securities balance is reported.",
            )
        )

    if not any(
        record.field == "marketable_securities_current" for record in records
    ):
        long_term_investment_index = next(
            (
                index
                for index in range(len(compact_lines))
                if "recorded as long-term investments" in " ".join(
                    compact_lines[index : index + 3]
                ).lower()
                and "marketable" in " ".join(compact_lines[index : index + 3]).lower()
            ),
            None,
        )
        if long_term_investment_index is not None:
            add_record(
                _record(
                    metadata,
                    field="marketable_securities_current",
                    value=0,
                    source_kind="filing_note",
                    status="resolved",
                    confidence="high",
                    locator="investments classification note/long-term investments",
                    excerpt=_line_excerpt(compact_lines, long_term_investment_index),
                    rationale="The filing states that its marketable and non-marketable investment balances are recorded as long-term investments, so no current marketable-securities balance is reported.",
                )
            )

    if not any(
        record.field == "marketable_securities_noncurrent" for record in records
    ):
        all_current_index = next(
            (
                index
                for index in range(len(compact_lines))
                if (
                    "classify all of our investments in debt securities"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    and "as current assets"
                    in " ".join(compact_lines[index : index + 3]).lower()
                )
                or (
                    "all of our marketable debt securities"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    and "mature within one year"
                    in " ".join(compact_lines[index : index + 3]).lower()
                )
                or (
                    "classifies marketable securities"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    and "less than one year"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    and "short-term investments"
                    in " ".join(compact_lines[index : index + 3]).lower()
                )
            ),
            None,
        )
        if all_current_index is not None:
            add_record(
                _record(
                    metadata,
                    field="marketable_securities_noncurrent",
                    value=0,
                    source_kind="filing_note_explicit_classification",
                    status="resolved",
                    confidence="high",
                    locator="investment note/explicit current-only portfolio policy",
                    excerpt=_line_excerpt(compact_lines, all_current_index, radius=2),
                    rationale="The filing explicitly classifies the complete marketable debt-securities portfolio as current or maturing within one year, so no noncurrent marketable-securities amount enters the bridge.",
                    evidence_class="inferred_zero",
                )
            )

    if ticker == "ADSK" and not any(
        record.field == "current_debt" for record in records
    ) and any(
        "no outstanding borrowings under" in line.lower() for line in compact_lines
    ) and any(
        "notes due at various times from june 2027" in line.lower()
        for line in compact_lines
    ):
        index = next(
            index
            for index, line in enumerate(compact_lines)
            if "no outstanding borrowings under" in line.lower()
        )
        add_record(
            _record(
                metadata,
                field="current_debt",
                value=0,
                source_kind="filing_note",
                status="resolved",
                confidence="high",
                locator="borrowing arrangements/no outstanding borrowings",
                excerpt=_line_excerpt(compact_lines, index),
                rationale="The filing reports no outstanding revolver borrowings and states that all notes mature beginning in June 2027, leaving no current debt balance at the reporting date.",
            )
        )

    preferred_index = next(
        (
            index
            for index in range(len(compact_lines))
            if (
                (
                    "preferred stock"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    or "preferred shares"
                    in " ".join(compact_lines[index : index + 3]).lower()
                )
                and (
                    "no shares issued"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    or "no shares were issued or outstanding"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    or "no shares of preferred stock were issued"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    or "none were issued or outstanding"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    or "none issued and outstanding"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    or "zero shares issued and outstanding"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    or re.search(
                        r"no shares (?:of )?preferred stock (?:are |were )?(?:currently )?issued and outstanding",
                        " ".join(compact_lines[index : index + 3]).lower(),
                    )
                    or re.search(
                        r"issued and outstanding\s*[–—:-]+\s*none",
                        " ".join(compact_lines[index : index + 3]).lower(),
                    )
                    or "none of which was outstanding"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    or "no preferred stock outstanding"
                    in " ".join(compact_lines[index : index + 3]).lower()
                    or "no preferred shares had been issued"
                    in " ".join(compact_lines[index : index + 3]).lower()
                )
            )
        ),
        None,
    )
    if preferred_index is not None:
        add_record(
            _record(
                metadata,
                field="preferred_equity",
                value=0,
                source_kind="filing_balance_sheet",
                status="resolved",
                confidence="high",
                locator="preferred stock issuance status",
                excerpt=_line_excerpt(compact_lines, preferred_index),
                rationale="The filing explicitly states that no preferred shares were issued or outstanding at the reporting date.",
            )
        )

    if preferred_index is None:
        preferred_amount_index = next(
            (
                index
                for index, line in enumerate(balance_lines)
                if "mandatory convertible preferred stock" in line.lower()
                and "aggregate liquidation preference" in line.lower()
                and re.search(
                    r"aggregate liquidation preference\s+\$[0-9][0-9,.]*",
                    line,
                    re.IGNORECASE,
                )
            ),
            None,
        )
        if preferred_amount_index is not None:
            match = re.search(
                r"aggregate liquidation preference\s+\$([0-9][0-9,.]*)",
                balance_lines[preferred_amount_index],
                re.IGNORECASE,
            )
            if match:
                add_record(
                    _record(
                        balance_metadata,
                        field="preferred_equity",
                        value=float(match.group(1).replace(",", "")),
                        source_kind="filing_balance_sheet",
                        status="resolved",
                        confidence="high",
                        locator="balance sheet/mandatory convertible preferred stock",
                        excerpt=_line_excerpt(balance_lines, preferred_amount_index),
                        rationale="The controlling balance sheet directly reports the mandatory convertible preferred stock's aggregate liquidation preference.",
                    )
                )

    if (
        ticker == "FTNT"
        and not any(record.field == "noncontrolling_interests" for record in records)
    ):
        full_ownership_index = next(
            (
                index
                for index, line in enumerate(compact_lines)
                if "acquired all of the remaining" in line.lower()
                and "now own 100%" in line.lower()
            ),
            None,
        )
        if full_ownership_index is not None:
            add_record(
                _record(
                    metadata,
                    field="noncontrolling_interests",
                    value=0,
                    source_kind="filing_note",
                    status="resolved",
                    confidence="high",
                    locator="acquisition note/full ownership disclosure",
                    excerpt=_line_excerpt(compact_lines, full_ownership_index),
                    rationale="The filing states that the remaining ownership interest was acquired and the company now owns 100% of the outstanding equity.",
                )
            )

    if (
        ticker == "NTAP"
        and any(record.field == "marketable_securities_current" for record in records)
        and not any(
            record.field == "marketable_securities_noncurrent" for record in records
        )
        and not any(
            line.lower().startswith(("long-term investments", "long-term marketable securities"))
            for line in balance_lines
        )
    ):
        classification_index = next(
            (
                index
                for index, line in enumerate(compact_lines)
                if "classified as available-for-sale investments" in line.lower()
            ),
            None,
        )
        if classification_index is not None:
            add_record(
                _record(
                    balance_metadata,
                    field="marketable_securities_noncurrent",
                    value=0,
                    source_kind="filing_balance_sheet_inferred_zero",
                    status="resolved",
                    confidence="high",
                    locator="balance sheet and available-for-sale investment classification",
                    excerpt=" ".join(
                        (
                            _line_excerpt(balance_lines, 0, radius=8),
                            _line_excerpt(compact_lines, classification_index),
                        )
                    ),
                    rationale="The current balance sheet reports the available-for-sale investment portfolio as short-term investments and presents no noncurrent investment line.",
                )
            )

    if ticker == "STX" and balance_lines:
        cash_equivalent_policy_index = next(
            (
                index
                for index, line in enumerate(compact_lines)
                if "cash and cash equivalents are maintained in investments with remaining maturities of 90 days or less"
                in line.lower()
            ),
            None,
        )
        separate_investment_line = any(
            line.lower().startswith(
                ("marketable securities", "short-term investments", "long-term investments")
            )
            for line in balance_lines
        )
        if cash_equivalent_policy_index is not None and not separate_investment_line:
            for field in (
                "marketable_securities_current",
                "marketable_securities_noncurrent",
            ):
                add_record(
                    _record(
                        metadata,
                        field=field,
                        value=0,
                        source_kind="filing_balance_sheet_inferred_zero",
                        status="resolved",
                        confidence="high",
                        locator="balance sheet and cash-equivalent investment policy",
                        excerpt=_line_excerpt(
                            compact_lines, cash_equivalent_policy_index
                        ),
                        rationale="The filing classifies its investment holdings with maturities of 90 days or less within cash equivalents and reports no separate current or noncurrent marketable-securities line.",
                    )
                )

    # Dell presents noncontrolling interests as a dedicated column in its
    # statement of stockholders' equity. The second-to-last column is NCI; the
    # final column is total equity.
    nci_header = next(
        (
            index
            for index, line in enumerate(compact_lines)
            if "non-controlling interests" in line.lower()
        ),
        None,
    )
    period_text = _human_period(str(metadata["period_end"]))
    nci_balance = next(
        (
            index
            for index, line in enumerate(compact_lines)
            if nci_header is not None
            and index > nci_header
            and index < nci_header + 50
            and f"balances as of {period_text.lower()}" in line.lower()
        ),
        None,
    )
    if nci_balance is not None:
        tokens = _value_tokens(compact_lines[nci_balance])
        if len(tokens) >= 2:
            add_record(
                _record(
                    metadata,
                    field="noncontrolling_interests",
                    value=tokens[-2],
                    source_kind="filing_equity_statement",
                    status="resolved",
                    confidence="high",
                    locator="statement of stockholders' equity/non-controlling interests column",
                    excerpt=_line_excerpt(compact_lines, nci_balance),
                    rationale="The filing presents a dedicated non-controlling-interests column in the current-period equity roll-forward.",
                )
            )

    if not any(record.field == "noncontrolling_interests" for record in records):
        direct_nci_index = next(
            (
                index
                for index, line in enumerate(compact_lines)
                if period_text.lower() in line.lower()
                and "noncontrolling interest" in line.lower()
                and "included in the equity section of the consolidated balance sheets"
                in line.lower()
                and re.search(
                    r"noncontrolling interest.*?was\s+\$[0-9][0-9,.]*\s*"
                    r"(?:thousand|million|billion)",
                    line,
                    re.IGNORECASE,
                )
            ),
            None,
        )
        if direct_nci_index is not None:
            match = re.search(
                r"noncontrolling interest.*?was\s+\$([0-9][0-9,.]*)\s*"
                r"(thousand|million|billion)",
                compact_lines[direct_nci_index],
                re.IGNORECASE,
            )
            if match:
                amount = float(match.group(1).replace(",", "")) * {
                    "thousand": 0.001,
                    "million": 1.0,
                    "billion": 1_000.0,
                }[match.group(2).lower()]
                add_record(
                    _record(
                        metadata,
                        field="noncontrolling_interests",
                        value=amount,
                        source_kind="filing_equity_note",
                        status="resolved",
                        confidence="high",
                        locator="equity note/current-period noncontrolling interest",
                        excerpt=_line_excerpt(compact_lines, direct_nci_index),
                        rationale="The filing directly reports the current-period noncontrolling interest and states that it is included in consolidated balance-sheet equity.",
                    )
                )

    # Commercial paper is a bridge debt only when the filing identifies the
    # borrowing at the controlling period end. Keep this separate from a row
    # carrying commercial paper as an investment asset.
    period_text = _human_period(str(metadata["period_end"])).lower()
    for commercial_borrowing_index, line in enumerate(compact_lines):
        lower = line.lower()
        if period_text not in lower:
            continue
        if "outstanding" not in lower and not re.search(
            r"(?:included|includes)\s+commercial paper borrowings of\s+\$",
            lower,
        ):
            continue
        preceding_context = " ".join(
            compact_lines[max(0, commercial_borrowing_index - 12) : commercial_borrowing_index]
        ).lower()
        if "commercial paper" not in lower and "commercial paper program" not in preceding_context:
            continue
        no_outstanding = bool(
            (
                "commercial paper" in lower
                and re.search(
                    r"(?:"
                    r"no (?:amounts?|balances?|borrowings?|debt|commercial paper(?: borrowings| notes)?) "
                    r"(?:were |was )?outstanding|"
                    r"no outstanding (?:commercial paper|borrowings|debt)|"
                    r"no [^.]{0,80}commercial paper (?:were |was )?outstanding|"
                    r"none of .*commercial paper program was outstanding"
                    r")",
                    lower,
                )
            )
            or (
                "commercial paper program" in preceding_context
                and re.search(
                    r"no outstanding balance under (?:this|the|our) program",
                    lower,
                )
            )
        )
        amount_match = next(
            (
                match
                for pattern in (
                    r"\$(?P<amount>[0-9][0-9,.]*)\s*(?P<magnitude>thousand|million|billion)\s+"
                    r"and\s+\$[0-9][0-9,.]*\s*(?:thousand|million|billion)\s+"
                    r"(?:in|of)\s+commercial paper(?:\s+(?:notes|borrowings))?\s+outstanding",
                    r"\$(?P<amount>[0-9][0-9,.]*)\s*(?P<magnitude>thousand|million|billion)?\s+"
                    r"(?:in|of)\s+commercial paper(?:\s+(?:notes|borrowings))?\s+outstanding",
                    r"commercial paper(?:\s+(?:notes|borrowings))?\s+outstanding\s+"
                    r"(?:totaled|was|were)\s+\$(?P<amount>[0-9][0-9,.]*)\s*"
                    r"(?P<magnitude>thousand|million|billion)?",
                    r"outstanding borrowings under .*?commercial paper program\s+"
                    r"(?:totaled|was|were)\s+\$(?P<amount>[0-9][0-9,.]*)\s*"
                    r"(?P<magnitude>thousand|million|billion)?",
                    r"(?:included|includes)\s+commercial paper borrowings of\s+"
                    r"\$(?P<amount>[0-9][0-9,.]*)\s*(?P<magnitude>thousand|million|billion)?",
                    r"\$(?P<amount>[0-9][0-9,.]*)\s*(?P<magnitude>thousand|million|billion)?\s+"
                    r"outstanding(?:\s+principal)?\s+amount\s+under\s+"
                    r"(?:our|the)\s+commercial paper",
                )
                if (match := re.search(pattern, line, re.IGNORECASE))
            ),
            None,
        )
        if not no_outstanding and not amount_match:
            continue
        value = 0.0
        rationale = (
            "The debt note explicitly reports no commercial-paper borrowing "
            "outstanding at the controlling period end."
        )
        if amount_match:
            reported = float(amount_match.group("amount").replace(",", ""))
            magnitude = (amount_match.group("magnitude") or "million").lower()
            value = reported * {
                "thousand": 0.001,
                "million": 1.0,
                "billion": 1_000.0,
            }[magnitude]
            rationale = (
                "The debt note explicitly reports commercial-paper borrowing "
                "outstanding at the controlling period end."
            )
        add_record(
            _record(
                metadata,
                field="commercial_paper",
                value=value,
                source_kind="filing_debt_note",
                status="resolved",
                confidence="high",
                locator="commercial paper debt note/period-end outstanding balance",
                excerpt=_line_excerpt(compact_lines, commercial_borrowing_index),
                rationale=rationale,
            )
        )
        break

    # Marketable securities: the first current-period total is the balance-sheet
    # classification. Later tables are historical or contractual-maturity views.
    total_index = next(
        (
            index
            for index, line in enumerate(compact_lines)
            if (
                "total marketable securities"
                in " ".join(compact_lines[index : index + 2]).lower()
                or line.lower().startswith("total short-term investments")
            )
        ),
        None,
    )
    if total_index is not None:
        total = _last_number(compact_lines[total_index])
        if total is not None and not any(
            record.field == "marketable_securities_current" for record in records
        ):
            records.append(
                _record(
                    metadata,
                    field="marketable_securities_current",
                    value=total,
                    source_kind="filing_table",
                    status="resolved",
                    confidence="high",
                    locator="marketable securities table/current-period total",
                    excerpt=_line_excerpt(compact_lines, total_index),
                    rationale="The filing presents the total marketable-securities balance in the current-period table.",
                )
            )

        current_record = next(
            (
                record
                for record in records
                if record.field == "marketable_securities_current"
                and record.source_kind == "filing_balance_sheet"
            ),
            None,
        )
        total_window = " ".join(compact_lines[total_index : total_index + 2])
        table_values = [value for value in _value_tokens(total_window) if value is not None]
        has_noncurrent_statement_line = any(
            line.lower().startswith(
                (
                    "long-term marketable securities",
                    "noncurrent marketable securities",
                    "non-current marketable securities",
                )
            )
            for line in balance_lines
        )
        if (
            current_record is not None
            and current_record.value in table_values
            and not has_noncurrent_statement_line
            and not any(
                record.field == "marketable_securities_noncurrent"
                for record in records
            )
        ):
            add_record(
                _record(
                    balance_metadata,
                    field="marketable_securities_noncurrent",
                    value=0,
                    source_kind="filing_table_reconciled_classification",
                    status="resolved",
                    confidence="high",
                    locator="balance sheet current securities row reconciled to complete marketable-securities table",
                    excerpt=" ".join(
                        (current_record.excerpt, _line_excerpt(compact_lines, total_index))
                    ),
                    rationale="The complete marketable-securities table reconciles to the current balance-sheet caption and the balance sheet reports no separate noncurrent marketable-securities caption.",
                    evidence_class="inferred_zero",
                )
            )

    commercial_index = next(
        (
            index
            for index, line in enumerate(
                compact_lines[:total_index] if total_index is not None else []
            )
            if line.lower().startswith("commercial paper")
        ),
        None,
    )
    if commercial_index is not None and not any(
        record.field == "commercial_paper" for record in records
    ):
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
        lease_metadata = {
            **metadata,
            "unit": _statement_unit(
                lease_lines,
                default=str(metadata.get("unit") or "USD millions"),
            ),
        }
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
                    lease_metadata,
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
            lease_context = " ".join(lease_lines).lower()
            if (
                period_text in lease_context
                and "lease liabilities" in lease_context
                and "finance leases" in lease_context
                and "total minimum lease payments" in lease_context
                and "less: imputed interest" in lease_context
            ):
                add_record(
                    _record(
                        lease_metadata,
                        field="finance_lease_total",
                        value=total_commitment,
                        source_kind="filing_lease_liability_reconciliation",
                        status="resolved",
                        confidence="high",
                        locator="reporting-date lease-liability table/net of imputed interest",
                        excerpt=excerpt,
                        rationale="The reporting-date finance-lease liability table reconciles minimum payments less imputed interest to the aggregate present-value liability used in the bridge; no current/noncurrent split is fabricated.",
                        evidence_class="aggregate_reported",
                    )
                )
        for field in ("finance_lease_current", "finance_lease_noncurrent"):
            records.append(
                _record(
                    lease_metadata,
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
        reported_unit = str(record.get("unit") or "").strip().lower()
        unit_multipliers = {
            "usd": 1.0,
            "usd thousands": 1_000.0,
            "usd millions": 1_000_000.0,
            "usd billions": 1_000_000_000.0,
        }
        if reported_unit not in unit_multipliers:
            continue
        base_value = float(value) * unit_multipliers[reported_unit]
        candidate = {
            "value": base_value,
            "reported_value": float(value),
            "reported_unit": record.get("unit"),
            "evidence_class": record.get("evidence_class", "reported"),
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
