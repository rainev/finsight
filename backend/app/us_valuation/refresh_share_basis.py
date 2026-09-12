"""Source-bound share-class reconciliation for residual-income refreshes.

Some issuers report more than one common-stock class.  A generic CompanyFacts
weighted-average-share selector is not a safe replacement for an issuer's
class conversion rule: for Berkshire Hathaway, the BRK.B denominator is
reported Class A shares multiplied by the filing's reported conversion ratio,
plus reported Class B shares.

This module deliberately does not infer a ratio from prices or from a value
fit.  Missing, conflicting, or misidentified structural facts are explicit
review failures so a caller can withhold the refresh.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import re
from math import isfinite
from numbers import Real
from typing import Any, Mapping


class ShareBasisReviewRequired(ValueError):
    """Raised when source facts cannot prove the requested share basis."""

    def __init__(self, *reasons: str) -> None:
        self.reasons = tuple(str(reason) for reason in reasons if str(reason))
        super().__init__("share basis requires review: " + "; ".join(self.reasons))


_BRK_CIK = "0001067983"
_BRK_CLASS_BY_TICKER = {"BRK.A": "A", "BRK.B": "B"}
_CLASS_AXIS = "us-gaap:StatementClassOfStockAxis"


def _iso_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(_text(value, field))
    except ValueError as exc:
        raise ShareBasisReviewRequired(f"{field} must be an ISO date") from exc


def _canonical_qname(namespace: str, local_name: str) -> str:
    """Match the Arelle worker's deterministic namespace canonicalizer."""
    return f"ns_{hashlib.sha1(namespace.encode('utf-8')).hexdigest()[:10]}:{local_name}"


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ShareBasisReviewRequired(f"{field} is missing")
    return value.strip()


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ShareBasisReviewRequired(f"{field} is not numeric")
    result = float(value)
    if not isfinite(result) or result <= 0:
        raise ShareBasisReviewRequired(f"{field} must be positive and finite")
    return result


def _cik(value: Any) -> str:
    raw = _text(value, "CIK")
    if not raw.isdigit() or len(raw) > 10:
        raise ShareBasisReviewRequired("CIK is invalid")
    return raw.zfill(10)


def _local_name(row: Mapping[str, Any]) -> str:
    local = row.get("local_name")
    if isinstance(local, str) and local:
        return local
    qname = row.get("qname")
    return str(qname).rsplit(":", 1)[-1] if isinstance(qname, str) else ""


def _dimensions(row: Mapping[str, Any]) -> tuple[str, str] | None:
    dimensions = row.get("dimensions")
    if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 1:
        return None
    pair = dimensions[0]
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        return None
    return str(pair[0]), str(pair[1])


def _member_class(row: Mapping[str, Any]) -> str | None:
    pair = _dimensions(row)
    if pair is None or pair[0] != _CLASS_AXIS:
        return None
    member = pair[1].rsplit(":", 1)[-1]
    if pair[1] == "us-gaap:CommonClassAMember":
        return "A"
    if pair[1] == "us-gaap:CommonClassBMember":
        return "B"
    return None


def _identity_matches(
    row: Mapping[str, Any],
    *,
    local_name: str,
    unit: str,
    cik: str,
    accession: str,
    namespace_pattern: str,
) -> bool:
    entity = str(row.get("entity_identifier", ""))
    return (
        _local_name(row) == local_name
        and isinstance(row.get("namespace"), str)
        and re.fullmatch(namespace_pattern, row["namespace"]) is not None
        and row.get("qname") == _canonical_qname(row["namespace"], local_name)
        and row.get("unit") == unit
        and str(row.get("source_accession", "")) == accession
        and entity.zfill(10) == cik
        and row.get("entity_scheme") == "http://www.sec.gov/CIK"
        and row.get("period_start") is None
    )


def _unique_fact(
    rows: list[Mapping[str, Any]],
    *,
    label: str,
) -> dict[str, Any]:
    if not rows:
        raise ShareBasisReviewRequired(f"{label} source fact is missing")
    values = {_number(row.get("value"), f"{label} value") for row in rows}
    if len(values) != 1:
        raise ShareBasisReviewRequired(f"{label} source facts conflict")
    # Identical parser duplicates are harmless; retain one complete source row.
    return deepcopy(rows[0])


def resolve_class_equivalent_share_basis(
    structural_packet: Mapping[str, Any],
    *,
    ticker: str,
    selected_class: str,
    cik: str,
    accession: str,
    report_period_end: str,
    filing_date: str,
    cutoff: str,
    expected_equivalent_shares: float | None = None,
) -> dict[str, Any]:
    """Resolve a class-equivalent share denominator from one filing.

    ``report_period_end`` is the controlling filing's reporting period.  The
    class outstanding facts may have a later observation date (as BRK.B's
    2026-07-29 cover-page counts do), but must share one exact date with each
    other and the same accession/issuer.  The conversion ratio must be an
    explicit structural fact from that filing.

    The result's ``value`` and ``equivalent_shares`` are the only derived
    denominator values.  Every source component and the formula are retained
    for auditability.  No market price is accepted or consulted.
    """
    if not isinstance(structural_packet, Mapping):
        raise ShareBasisReviewRequired("structural packet is missing")
    ticker = _text(ticker, "ticker")
    selected_class = _text(selected_class, "selected class").upper()
    if selected_class not in {"A", "B"}:
        raise ShareBasisReviewRequired("selected class must be A or B")
    cik = _cik(cik)
    governed_class = _BRK_CLASS_BY_TICKER.get(ticker)
    if governed_class is None:
        raise ShareBasisReviewRequired("ticker is outside the governed BRK.A/BRK.B share basis")
    if cik != _BRK_CIK:
        raise ShareBasisReviewRequired("CIK is not the governed Berkshire Hathaway CIK")
    if selected_class != governed_class:
        raise ShareBasisReviewRequired("ticker and selected class do not match")
    accession = _text(accession, "accession")
    report_period_end = _text(report_period_end, "report period end")
    filing_date_value = _iso_date(filing_date, "filing date")
    cutoff_value = _iso_date(cutoff, "cutoff")
    report_period_value = _iso_date(report_period_end, "report period end")
    if filing_date_value > cutoff_value:
        raise ShareBasisReviewRequired("filing date is after cutoff")
    if structural_packet.get("source_accession") != accession:
        raise ShareBasisReviewRequired("structural packet accession mismatch")
    if structural_packet.get("filed_date") != filing_date:
        raise ShareBasisReviewRequired("structural packet filing date mismatch")
    packet_report_period = structural_packet.get("report_date") or structural_packet.get("period_end")
    if packet_report_period is not None and str(packet_report_period) != report_period_end:
        raise ShareBasisReviewRequired("structural packet report period mismatch")
    facts = structural_packet.get("facts")
    if not isinstance(facts, list):
        raise ShareBasisReviewRequired("structural packet has no fact rows")

    class_rows: dict[str, list[Mapping[str, Any]]] = {"A": [], "B": []}
    ratio_rows: list[Mapping[str, Any]] = []
    for row in facts:
        if not isinstance(row, Mapping) or not _identity_matches(
            row,
            local_name="EntityCommonStockSharesOutstanding",
            unit="xbrli:shares",
            cik=cik,
            accession=accession,
            namespace_pattern=r"http://xbrl\.sec\.gov/dei/\d{4}",
        ):
            if isinstance(row, Mapping) and _identity_matches(
                row,
                local_name="NumberOfSharesObtainableFromConvertingOneShareFromOneClassToAnotherClass",
                unit="xbrli:shares",
                cik=cik,
                accession=accession,
                namespace_pattern=r"http://www\.berkshirehathaway\.com/\d{8}",
            ):
                if _member_class(row) == "B":
                    ratio_rows.append(row)
            continue
        klass = _member_class(row)
        if klass is not None:
            class_rows[klass].append(row)

    selected: dict[str, dict[str, Any]] = {}
    for klass in ("A", "B"):
        row = _unique_fact(class_rows[klass], label=f"Class {klass} outstanding")
        if not row.get("period_end"):
            raise ShareBasisReviewRequired(f"Class {klass} outstanding period is missing")
        selected[klass] = row
    share_periods = {str(row.get("period_end")) for row in selected.values()}
    if len(share_periods) != 1:
        raise ShareBasisReviewRequired("Class A and Class B outstanding periods conflict")
    share_period_value = _iso_date(next(iter(share_periods)), "share observation period")
    if not report_period_value <= share_period_value <= filing_date_value:
        raise ShareBasisReviewRequired("share observation period is outside report/filing window")
    for row in (*selected.values(), *ratio_rows):
        if row.get("filed_date") != filing_date or row.get("report_date") != report_period_end:
            raise ShareBasisReviewRequired("source fact filing identity or report period mismatch")

    ratio = _unique_fact(ratio_rows, label="Class conversion ratio")
    ratio_period = str(ratio.get("period_end", ""))
    if ratio_period != report_period_end:
        raise ShareBasisReviewRequired("Class conversion ratio period mismatch")
    conversion_ratio = _number(ratio.get("value"), "Class conversion ratio")
    class_a = _number(selected["A"].get("value"), "Class A shares")
    class_b = _number(selected["B"].get("value"), "Class B shares")
    if selected_class == "B":
        value = class_a * conversion_ratio + class_b
        formula = f"Class A shares * {conversion_ratio:g} + Class B shares"
        source_kind = "derived_class_b_equivalent_shares"
    else:
        value = class_a + class_b / conversion_ratio
        formula = f"Class A shares + Class B shares / {conversion_ratio:g}"
        source_kind = "derived_class_a_equivalent_shares"
    if not isfinite(value) or value <= 0:
        raise ShareBasisReviewRequired("derived equivalent share count is invalid")
    if expected_equivalent_shares is not None:
        expected = _number(expected_equivalent_shares, "expected equivalent shares")
        if value != expected:
            raise ShareBasisReviewRequired(
                f"derived equivalent shares {value:g} do not match expected {expected:g}"
            )
    return {
        "status": "verified",
        "ticker": ticker,
        "selected_class": selected_class,
        "unit": "xbrli:shares",
        "value": value,
        "equivalent_shares": value,
        "class_a_shares": class_a,
        "class_b_shares": class_b,
        "conversion_ratio": conversion_ratio,
        "formula": formula,
        "source_kind": source_kind,
        "reported_vs_estimated": "reported_components_with_derived_conversion",
        "source_accession": accession,
        "report_period_end": report_period_end,
        "share_observation_period_end": next(iter(share_periods)),
        "sources": [deepcopy(selected["A"]), deepcopy(selected["B"]), deepcopy(ratio)],
    }


__all__ = ["ShareBasisReviewRequired", "resolve_class_equivalent_share_basis"]
