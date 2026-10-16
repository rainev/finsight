"""Source-bound nonrecurring cash-receipt evidence for refresh calculations.

This module is intentionally a pure evidence boundary.  It does not alter a
recipe, write an event store, or decide whether a receipt is economically
recurring.  For the CF/Orica event it proves three separate facts from the
controlling filing:

* the settlement amount and cash-receipt date from the litigation note,
* the operating-cash-flow classification from the MD&A cash narrative, and
* the exact standard litigation-gain fact from the structural packet.

The March recognition period is retained as provenance, but is never used as
the cash date.  This distinction matters when a rolling TTM window includes
the cash receipt after the gain was recognized.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from html.parser import HTMLParser
import json
from math import isfinite
from numbers import Real
import calendar
import re
from typing import Any, Iterable, Mapping


STANDARD_LITIGATION_GAIN_QNAME = "us-gaap:GainLossRelatedToLitigationSettlement"
EVENT_LITIGATION_GAIN_QNAME = "us-gaap:LitigationSettlementGain"
USD_UNIT = "USD"
CF_CIK = "0001324404"
CF_ORICA_EVENT_KEY = "CF_ORICA_LITIGATION_SETTLEMENT"
_CIK_SCHEME = "http://www.sec.gov/CIK"
_US_GAAP_NAMESPACE_RE = re.compile(r"^https?://fasb\.org/us-gaap/[0-9]{4}$")
_AMOUNT_RE = re.compile(
    r"Orica\s+agreed\s+to\s+pay\s+us\s+approximately\s+\$\s*"
    r"(?P<amount>[0-9][0-9,]*(?:\.[0-9]+)?)\s*million\s+in\s+cash",
    re.IGNORECASE,
)
_CASH_DATE_RE = re.compile(
    r"On\s+(?P<month>January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(?P<day>[0-9]{1,2}),\s+"
    r"(?P<year>[0-9]{4}),\s+we\s+received\s+the\s+cash\s+payment\s+from\s+Orica",
    re.IGNORECASE,
)
_OCF_RE = re.compile(
    r"cash\s+flow\s+from\s+operations.*?includes\s+\$\s*"
    r"(?P<amount>[0-9][0-9,]*(?:\.[0-9]+)?)\s*million\s+of\s+"
    r"litigation\s+settlement\s+proceeds",
    re.IGNORECASE | re.DOTALL,
)
_NOTE_HEADING_RE = re.compile(r"\b[0-9]{1,2}\s*\.\s*Litigation Settlement Gain\b", re.IGNORECASE)
_NEXT_NOTE_RE = re.compile(r"\b[0-9]{1,2}\s*\.\s+[A-Z][A-Za-z]", re.IGNORECASE)


class CashReceiptReviewRequired(ValueError):
    """Raised when receipt evidence is missing, conflicting, or misidentified."""

    def __init__(self, *reasons: str) -> None:
        self.reasons = tuple(str(reason) for reason in reasons if str(reason))
        super().__init__("cash receipt requires review: " + "; ".join(self.reasons))


class _VisibleTextParser(HTMLParser):
    """Collect visible filing prose without depending on a third-party parser."""

    _ignored = frozenset({"script", "style", "ix:header", "ix:hidden"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._ignored:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._ignored and self._depth:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._depth:
            self.parts.append(data)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CashReceiptReviewRequired(f"{field} is missing")
    return value.strip()


def _iso(value: Any, field: str) -> str:
    raw = _text(value, field)
    try:
        date.fromisoformat(raw)
    except ValueError as exc:
        raise CashReceiptReviewRequired(f"{field} is not an ISO date") from exc
    return raw


def _cik(value: Any) -> str:
    raw = _text(value, "CIK")
    if not raw.isdigit() or len(raw) > 10:
        raise CashReceiptReviewRequired("CIK is invalid")
    return raw.zfill(10)


def _finite(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise CashReceiptReviewRequired(f"{field} is not numeric")
    result = float(value)
    if not isfinite(result) or (positive and result <= 0):
        raise CashReceiptReviewRequired(f"{field} is not finite and positive")
    return result


def _amount_millions(value: str) -> float:
    try:
        return float(value.replace(",", "")) * 1_000_000.0
    except ValueError as exc:
        raise CashReceiptReviewRequired("receipt amount is not numeric") from exc


def _canonical_fact(row: Mapping[str, Any]) -> tuple[Any, ...]:
    """A parser duplicate key; presentation link role is deliberately ignored."""

    return (
        row.get("qname"),
        row.get("local_name"),
        row.get("value"),
        row.get("unit"),
        row.get("period_start"),
        row.get("period_end"),
        row.get("context_id"),
        tuple(tuple(item) for item in (row.get("dimensions") or ())),
        row.get("source_accession"),
    )


def _fact_identity(
    row: Mapping[str, Any],
    *,
    qname: str,
    cik: str,
    accession: str,
    filing_date: str,
) -> bool:
    entity = str(row.get("entity_identifier", ""))
    return (
        row.get("qname") == qname
        and isinstance(row.get("namespace"), str)
        and _US_GAAP_NAMESPACE_RE.fullmatch(row["namespace"]) is not None
        and row.get("unit") == USD_UNIT
        and row.get("dimensions") in (None, [])
        and entity.zfill(10) == cik
        and row.get("entity_scheme") == _CIK_SCHEME
        and row.get("source_accession") == accession
        and row.get("filed_date") == filing_date
        and row.get("filing_form") in {'10-Q','10-Q/A','10-K','10-K/A'}
    )


def _deduplicate(rows: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        key = _canonical_fact(row)
        if key not in seen:
            seen.add(key)
            result.append(dict(row))
    return tuple(result)


def _fact_period(row: Mapping[str, Any]) -> tuple[str | None, str | None]:
    start = row.get("period_start")
    end = row.get("period_end")
    return (str(start) if start else None, str(end) if end else None)


@dataclass(frozen=True)
class CashReceiptEvent:
    """Immutable, JSON-ready proof for one cash receipt."""

    event_id: str
    logical_event_key: str
    cik: str
    accession: str
    filing_date: str
    amount: float
    currency: str
    cash_received_date: str
    recognized_period_start: str | None
    recognized_period_end: str | None
    standard_gain_qname: str
    standard_gain_periods: tuple[tuple[str | None, str | None], ...]
    event_gain_qname: str | None
    ocf_narrative_amount: float
    tax_adjustment_supported: bool
    tax_limitation: str
    source_sha256: str
    structural_sha256: str
    source_locators: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "logical_event_key": self.logical_event_key,
            "cik": self.cik,
            "accession": self.accession,
            "filing_date": self.filing_date,
            "amount": self.amount,
            "currency": self.currency,
            "cash_received_date": self.cash_received_date,
            "recognized_period_start": self.recognized_period_start,
            "recognized_period_end": self.recognized_period_end,
            "standard_gain_qname": self.standard_gain_qname,
            "standard_gain_periods": [list(period) for period in self.standard_gain_periods],
            "event_gain_qname": self.event_gain_qname,
            "ocf_narrative_amount": self.ocf_narrative_amount,
            "tax_adjustment_supported": self.tax_adjustment_supported,
            "tax_limitation": self.tax_limitation,
            "source_sha256": self.source_sha256,
            "structural_sha256": self.structural_sha256,
            "source_locators": list(self.source_locators),
        }


@dataclass(frozen=True)
class CashReceiptEvidence:
    """Immutable evidence bundle returned by :func:`extract_cash_receipt_evidence`."""

    schema: str
    ticker: str
    cik: str
    accession: str
    filing_date: str
    report_period_end: str
    event: CashReceiptEvent
    standard_fact_count: int
    event_fact_count: int
    ocf_narrative_verified: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "ticker": self.ticker,
            "cik": self.cik,
            "accession": self.accession,
            "filing_date": self.filing_date,
            "report_period_end": self.report_period_end,
            "event": self.event.as_dict(),
            "standard_fact_count": self.standard_fact_count,
            "event_fact_count": self.event_fact_count,
            "ocf_narrative_verified": self.ocf_narrative_verified,
        }


def _visible_text(raw_html: bytes) -> str:
    parser = _VisibleTextParser()
    try:
        parser.feed(raw_html.decode("utf-8", errors="strict"))
        parser.close()
    except (UnicodeDecodeError, ValueError) as exc:
        raise CashReceiptReviewRequired("primary HTML is not valid UTF-8 filing content") from exc
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _canonical_json_sha256(value: Mapping[str, Any]) -> str:
    try:
        from .catalog import canonical_json_bytes
        raw = canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise CashReceiptReviewRequired("structural packet is not canonical JSON") from exc
    return sha256(raw).hexdigest()


def canonical_structural_sha256(structural_packet: Mapping[str, Any]) -> str:
    """Return the canonical JSON hash required by the extractor boundary."""

    if not isinstance(structural_packet, Mapping):
        raise CashReceiptReviewRequired("structural packet is missing")
    return _canonical_json_sha256(structural_packet)


def _note_scope(text: str) -> tuple[str, str]:
    headings = tuple(_NOTE_HEADING_RE.finditer(text))
    if len(headings) != 1:
        raise CashReceiptReviewRequired("litigation settlement gain note is missing or ambiguous")
    start = headings[0].start()
    next_note = _NEXT_NOTE_RE.search(text, headings[0].end())
    return text[start : next_note.start() if next_note else len(text)], headings[0].group()


def _ocf_sentence_matches(text: str) -> tuple[float, ...]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    matches: list[float] = []
    for sentence in sentences:
        if "cash flow from operations" not in sentence.lower() or "litigation settlement proceeds" not in sentence.lower():
            continue
        matches.extend(_amount_millions(match.group("amount")) for match in _OCF_RE.finditer(sentence))
    return tuple(matches)


def extract_cash_receipt_evidence(
    raw_html: bytes,
    *,
    expected_sha256: str,
    structural_packet: Mapping[str, Any],
    expected_structural_sha256: str,
    cik: str,
    accession: str,
    filing_date: str,
    cutoff: str,
    ticker: str = "CF",
) -> CashReceiptEvidence:
    """Extract and cross-check the CF/Orica receipt from one controlling filing.

    The function accepts bytes rather than a path so callers cannot silently
    substitute an unverified file.  Amount/date evidence comes from filing
    prose; structural facts corroborate the recognized gain and are never
    treated as the cash date.
    """

    if not isinstance(raw_html, (bytes, bytearray)):
        raise CashReceiptReviewRequired("primary HTML must be bytes")
    expected_sha256 = _text(expected_sha256, "expected SHA-256").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise CashReceiptReviewRequired("expected SHA-256 is invalid")
    source_sha = sha256(bytes(raw_html)).hexdigest()
    if source_sha != expected_sha256:
        raise CashReceiptReviewRequired("primary HTML SHA-256 mismatch")
    if not isinstance(structural_packet, Mapping):
        raise CashReceiptReviewRequired("structural packet is missing")
    expected_structural_sha256 = _text(expected_structural_sha256, "expected structural SHA-256").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_structural_sha256):
        raise CashReceiptReviewRequired("expected structural SHA-256 is invalid")
    structural_sha = _canonical_json_sha256(structural_packet)
    if structural_sha != expected_structural_sha256:
        raise CashReceiptReviewRequired("canonical structural SHA-256 mismatch")
    cik = _cik(cik)
    if cik != CF_CIK:
        raise CashReceiptReviewRequired("cash receipt extractor is governed only for CF CIK 0001324404")
    accession = _text(accession, "accession")
    filing_date = _iso(filing_date, "filing date")
    cutoff = _iso(cutoff, "cutoff")
    if filing_date > cutoff:
        raise CashReceiptReviewRequired("filing date is after cutoff")
    ticker = _text(ticker, "ticker")
    if ticker != "CF":
        raise CashReceiptReviewRequired("cash receipt extractor is governed only for ticker CF")
    if structural_packet.get("source_accession") != accession:
        raise CashReceiptReviewRequired("structural accession mismatch")
    if structural_packet.get("filed_date") != filing_date:
        raise CashReceiptReviewRequired("structural filing date mismatch")
    report_period_end = _iso(
        structural_packet.get("report_date") or structural_packet.get("period_end"),
        "structural report period end",
    )
    facts = structural_packet.get("facts")
    if not isinstance(facts, list):
        raise CashReceiptReviewRequired("structural packet has no fact rows")
    standard = _deduplicate(
        row
        for row in facts
        if isinstance(row, Mapping)
        and _fact_identity(row, qname=STANDARD_LITIGATION_GAIN_QNAME, cik=cik, accession=accession, filing_date=filing_date)
        and row.get("period_end") == report_period_end
    )
    event_rows = _deduplicate(
        row
        for row in facts
        if isinstance(row, Mapping)
        and _fact_identity(row, qname=EVENT_LITIGATION_GAIN_QNAME, cik=cik, accession=accession, filing_date=filing_date)
    )
    if not standard:
        raise CashReceiptReviewRequired("standard litigation gain source is missing")
    positive_standard = tuple(row for row in standard if _finite(row.get("value"), "standard litigation gain") > 0)
    if not positive_standard:
        raise CashReceiptReviewRequired("standard litigation gain has no positive current-period fact")
    standard_values = {_finite(row.get("value"), "standard litigation gain") for row in positive_standard}
    if len(standard_values) != 1:
        raise CashReceiptReviewRequired("standard litigation gain facts conflict")
    standard_amount = next(iter(standard_values))

    text = _visible_text(bytes(raw_html))
    note_scope, note_heading = _note_scope(text)
    amount_matches = tuple(_amount_millions(match.group("amount")) for match in _AMOUNT_RE.finditer(note_scope))
    if not amount_matches:
        raise CashReceiptReviewRequired(f"{note_heading}: cash amount is missing")
    if len(set(amount_matches)) != 1:
        raise CashReceiptReviewRequired(f"{note_heading}: cash amounts conflict")
    amount = amount_matches[0]
    if amount != standard_amount:
        raise CashReceiptReviewRequired(f"{note_heading}: cash amount disagrees with standard litigation gain")
    cash_matches = tuple(_CASH_DATE_RE.finditer(note_scope))
    if not cash_matches:
        raise CashReceiptReviewRequired(f"{note_heading}: cash receipt date is missing")
    cash_match = cash_matches[0]
    # Convert the month name without introducing a hardcoded event date.
    month_number = list(calendar.month_name).index(cash_match.group("month").title())
    cash_date = _iso(f"{cash_match.group('year')}-{month_number:02d}-{int(cash_match.group('day')):02d}", "cash receipt date")
    cash_dates = {
        _iso(
            f"{match.group('year')}-{list(calendar.month_name).index(match.group('month').title()):02d}-{int(match.group('day')):02d}",
            "cash receipt date",
        )
        for match in cash_matches
    }
    if len(cash_dates) != 1:
        raise CashReceiptReviewRequired(f"{note_heading}: cash receipt dates conflict")
    if cash_date > filing_date or filing_date > cutoff:
        raise CashReceiptReviewRequired("cash receipt/filing date is outside cutoff ordering")
    ocf_matches = _ocf_sentence_matches(text)
    if not ocf_matches:
        raise CashReceiptReviewRequired("operating-cash-flow narrative is missing")
    if len(set(ocf_matches)) != 1 or ocf_matches[0] != amount:
        raise CashReceiptReviewRequired(f"operating-cash-flow narrative disagrees with {note_heading}")
    event_periods = tuple(_fact_period(row) for row in event_rows if _finite(row.get("value"), "event litigation gain") == amount)
    event_periods = tuple(dict.fromkeys(event_periods))
    recognized = event_periods[0] if len(event_periods) == 1 else _fact_period(positive_standard[0])
    event_qname = EVENT_LITIGATION_GAIN_QNAME if event_periods else None
    event = CashReceiptEvent(
        event_id=CF_ORICA_EVENT_KEY,
        logical_event_key=CF_ORICA_EVENT_KEY,
        cik=cik,
        accession=accession,
        filing_date=filing_date,
        amount=amount,
        currency=USD_UNIT,
        cash_received_date=cash_date,
        recognized_period_start=recognized[0],
        recognized_period_end=recognized[1],
        standard_gain_qname=STANDARD_LITIGATION_GAIN_QNAME,
        standard_gain_periods=tuple(dict.fromkeys(_fact_period(row) for row in standard)),
        event_gain_qname=event_qname,
        ocf_narrative_amount=ocf_matches[0],
        tax_adjustment_supported=False,
        tax_limitation="No separate tax basis for the settlement receipt is tagged or disclosed; gross cash removal only.",
        source_sha256=source_sha,
        structural_sha256=structural_sha,
        source_locators=(
            f"primary_html:{note_heading}",
            "primary_html:MD&A Cash Flows",
            "structural_filing.facts:us-gaap:GainLossRelatedToLitigationSettlement",
        ),
    )
    return CashReceiptEvidence(
        schema="FINSIGHT-CASH-RECEIPT-EVIDENCE-1",
        ticker=ticker,
        cik=cik,
        accession=accession,
        filing_date=filing_date,
        report_period_end=report_period_end,
        event=event,
        standard_fact_count=len(standard),
        event_fact_count=len(event_rows),
        ocf_narrative_verified=True,
    )


def _event_from(value: CashReceiptEvidence | CashReceiptEvent | Mapping[str, Any]) -> CashReceiptEvent:
    if isinstance(value, CashReceiptEvidence):
        return value.event
    if isinstance(value, CashReceiptEvent):
        return value
    if isinstance(value, Mapping):
        raw = value.get("event") if isinstance(value.get("event"), Mapping) else value
        try:
            return CashReceiptEvent(
                event_id=_text(raw["event_id"], "event_id"),
                logical_event_key=_text(raw["logical_event_key"], "logical event key"),
                cik=_cik(raw["cik"]),
                accession=_text(raw["accession"], "accession"),
                filing_date=_iso(raw["filing_date"], "filing date"),
                amount=_finite(raw["amount"], "amount", positive=True),
                currency=_text(raw["currency"], "currency"),
                cash_received_date=_iso(raw["cash_received_date"], "cash receipt date"),
                recognized_period_start=raw.get("recognized_period_start"),
                recognized_period_end=raw.get("recognized_period_end"),
                standard_gain_qname=_text(raw["standard_gain_qname"], "standard gain qname"),
                standard_gain_periods=tuple(tuple(period) for period in raw.get("standard_gain_periods", ())),
                event_gain_qname=raw.get("event_gain_qname"),
                ocf_narrative_amount=_finite(raw["ocf_narrative_amount"], "OCF narrative amount", positive=True),
                tax_adjustment_supported=bool(raw.get("tax_adjustment_supported", False)),
                tax_limitation=_text(raw["tax_limitation"], "tax limitation"),
                source_sha256=_text(raw["source_sha256"], "source SHA-256"),
                structural_sha256=_text(raw["structural_sha256"], "structural SHA-256"),
                source_locators=tuple(str(item) for item in raw.get("source_locators", ())),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CashReceiptReviewRequired("serialized cash receipt event is invalid") from exc
    raise CashReceiptReviewRequired("cash receipt event type is unsupported")


def sum_cash_receipts(
    events: Iterable[CashReceiptEvidence | CashReceiptEvent | Mapping[str, Any]],
    *,
    window_start: str,
    window_end: str,
    cutoff: str,
) -> dict[str, Any]:
    """Sum receipts whose *cash* dates fall in an explicit inclusive window.

    Recognition dates are intentionally ignored.  Duplicate corroborating
    facts/events are counted once by event ID; conflicting values for one ID
    are rejected.  Tax reversal remains unsupported and is reported rather
    than inferred.
    """

    start = date.fromisoformat(_iso(window_start, "window start"))
    end = date.fromisoformat(_iso(window_end, "window end"))
    cutoff_value = date.fromisoformat(_iso(cutoff, "cutoff"))
    if start > end:
        raise CashReceiptReviewRequired("cash window start is after end")
    unique: dict[str, CashReceiptEvent] = {}
    for value in events:
        event = _event_from(value)
        if event.logical_event_key != CF_ORICA_EVENT_KEY or event.event_id != CF_ORICA_EVENT_KEY:
            raise CashReceiptReviewRequired("unknown cash receipt logical event key")
        if event.cik != CF_CIK or event.currency != USD_UNIT:
            raise CashReceiptReviewRequired("cash receipt issuer or currency is not governed")
        if not isinstance(event.source_sha256,str) or not isinstance(event.structural_sha256,str) or not re.fullmatch(r"[0-9a-f]{64}", event.source_sha256) or not re.fullmatch(r"[0-9a-f]{64}", event.structural_sha256):
            raise CashReceiptReviewRequired("serialized cash receipt hash is invalid")
        _finite(event.amount,'cash receipt amount',positive=True)
        _finite(event.ocf_narrative_amount,'cash receipt corroboration',positive=True)
        if event.ocf_narrative_amount != event.amount or event.tax_adjustment_supported is not False:
            raise CashReceiptReviewRequired("serialized cash receipt amount does not match OCF evidence")
        cash_date = date.fromisoformat(_iso(event.cash_received_date,'cash date'))
        filing_date = date.fromisoformat(_iso(event.filing_date,'filing date'))
        if cash_date > filing_date or filing_date > cutoff_value:
            raise CashReceiptReviewRequired("serialized cash receipt date ordering is invalid")
        if event.recognized_period_start is not None or event.recognized_period_end is not None:
            if event.recognized_period_start is None or event.recognized_period_end is None:
                raise CashReceiptReviewRequired("serialized recognition period is incomplete")
            if not date.fromisoformat(_iso(event.recognized_period_start,'recognition start')) <= date.fromisoformat(_iso(event.recognized_period_end,'recognition end')) <= filing_date:
                raise CashReceiptReviewRequired("serialized recognition period is invalid")
        existing = unique.get(event.event_id)
        if existing is not None:
            if (existing.amount, existing.cash_received_date) != (event.amount, event.cash_received_date):
                raise CashReceiptReviewRequired("duplicate event ID has conflicting receipt evidence")
            continue
        unique[event.event_id] = event
    included = tuple(event for event in unique.values() if start <= date.fromisoformat(event.cash_received_date) <= end)
    return {
        "schema": "FINSIGHT-CASH-RECEIPT-ADJUSTMENT-1",
        "window_start": window_start,
        "window_end": window_end,
        "amount": sum(event.amount for event in included),
        "currency": USD_UNIT,
        "included_event_ids": [event.event_id for event in included],
        "included_events": [event.as_dict() for event in included],
        "tax_adjustment_supported": False,
        "tax_limitation": "Receipt adjustment is gross cash only; no separate tax reversal is supported.",
    }


cash_receipt_adjustment = sum_cash_receipts


__all__ = [
    "CashReceiptEvent",
    "CashReceiptEvidence",
    "CashReceiptReviewRequired",
    "EVENT_LITIGATION_GAIN_QNAME",
    "STANDARD_LITIGATION_GAIN_QNAME",
    "cash_receipt_adjustment",
    "canonical_structural_sha256",
    "extract_cash_receipt_evidence",
    "sum_cash_receipts",
]
