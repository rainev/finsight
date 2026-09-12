"""Deterministic private evidence extraction from hashed filing narrative.

This module is deliberately small and non-generative.  It reads only the
primary document declared by an immutable filing-package manifest, normalizes
visible HTML text, applies a versioned semantic contract, and returns exact
locators and hashes.  A missing, duplicate, or conflicting term fails closed.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping

from .catalog import canonical_json_bytes, sha256_bytes


SCHEMA = "FINSIGHT-NARRATIVE-EVIDENCE-1"
VERSION = "FINSIGHT-NARRATIVE-EVIDENCE-WG11-1"


POLICIES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "MCHP": MappingProxyType({
        "schema_version": SCHEMA,
        "version": VERSION,
        "ticker": "MCHP",
        "cik": "0000827054",
        "mechanism": "mandatory_convertible_preferred",
        "section_anchor": r"Series A Mandatory Convertible Preferred Stock In [A-Z][a-z]+ [0-9]{4}, the Company issued",
        "section_end": "Common Stock Dividends",
    }),
    "BMY": MappingProxyType({
        "schema_version": SCHEMA,
        "version": VERSION,
        "ticker": "BMY",
        "cik": "0000014272",
        "mechanism": "acquisition_and_license_payments",
        "section_anchor": r"Hengrui License Agreements In [A-Z][a-z]+ [0-9]{4}, BMS and Hengrui entered",
        "section_end": "Priority Review Voucher",
        "related_section_anchor": r"BioNTech In [A-Z][a-z]+ [0-9]{4}, BMS and BioNTech entered",
        "related_section_end": "Note 4.",
    }),
})


class NarrativeEvidenceError(ValueError):
    """The filing bytes do not satisfy the declared narrative contract."""


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"head", "script", "style", "ix:hidden"}:
            self._ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"head", "script", "style", "ix:hidden"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored:
            value = " ".join(data.replace("\xa0", " ").split())
            if value:
                self.parts.append(value)

    @property
    def text(self) -> str:
        return " ".join(self.parts)


def narrative_policy(ticker: str) -> dict[str, Any]:
    policy = POLICIES.get(ticker.upper())
    if policy is None:
        raise ValueError(f"no narrative evidence policy for {ticker!r}")
    return deepcopy(dict(policy))


def _same_policy(policy: Mapping[str, Any]) -> bool:
    expected = POLICIES.get(str(policy.get("ticker", "")).upper())
    return expected is not None and canonical_json_bytes(dict(policy)) == canonical_json_bytes(dict(expected))


def _section(text: str, anchor: str, end: str) -> tuple[str, int, int]:
    starts = list(re.finditer(anchor, text))
    candidates: list[tuple[str, int, int]] = []
    for match in starts:
        finish = text.find(end, match.end())
        if finish >= 0:
            candidates.append((text[match.start():finish], match.start(), finish))
    if len(candidates) != 1:
        raise NarrativeEvidenceError(f"narrative section is missing or ambiguous: {anchor}")
    return candidates[0]


def _one(section: str, pattern: str, *, offset: int, name: str) -> re.Match[str]:
    matches = list(re.finditer(pattern, section, re.IGNORECASE))
    if len(matches) != 1:
        raise NarrativeEvidenceError(f"narrative term is missing or ambiguous: {name}")
    return matches[0]


def _term(section: str, pattern: str, *, offset: int, name: str, value: Any, unit: str) -> dict[str, Any]:
    match = _one(section, pattern, offset=offset, name=name)
    start, end = offset + match.start(), offset + match.end()
    excerpt = section[match.start():match.end()]
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "locator": {"normalized_text_start": start, "normalized_text_end": end},
        "excerpt_sha256": sha256(excerpt.encode("utf-8")).hexdigest(),
    }


def _number(raw: str) -> float:
    return float(raw.replace(",", ""))


def _money(raw: str, scale: str) -> float:
    factor = {"million": 1_000_000.0, "billion": 1_000_000_000.0}.get(scale.lower())
    if factor is None:
        raise NarrativeEvidenceError(f"unsupported narrative money scale: {scale}")
    return _number(raw) * factor


def _date(raw: str) -> str:
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    raise NarrativeEvidenceError(f"unsupported narrative date: {raw}")


def _section_record(section: str, start: int, end: int, anchor: str) -> dict[str, Any]:
    return {
        "anchor": anchor,
        "locator": {"normalized_text_start": start, "normalized_text_end": end},
        "text_sha256": sha256(section.encode("utf-8")).hexdigest(),
    }


def _mchp(text: str, policy: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    section, start, end = _section(text, str(policy["section_anchor"]), str(policy["section_end"]))
    patterns = {
        "dividend": r"Dividends are cumulative at an annual rate of (?P<rate>[0-9]+(?:\.[0-9]+)?)\s*% on the liquidation preference of \$\s*(?P<preference>[0-9,.]+) per share",
        "schedule": r"payable on the (?P<day>[0-9]+)(?:st|nd|rd|th) of (?P<months>[A-Za-z]+, [A-Za-z]+, [A-Za-z]+ and [A-Za-z]+)",
        "declared": r"quarterly cash dividend of \$\s*(?P<amount>[0-9,.]+) per share of Series A Preferred Stock was declared on (?P<declared>[A-Z][a-z]+ [0-9]+, [0-9]{4}) and will be paid on (?P<payment>[A-Z][a-z]+ [0-9]+, [0-9]{4})",
        "conversion": r"automatically convert on (?P<date>[A-Z][a-z]+ [0-9]+, [0-9]{4}), into between (?P<minimum>[0-9,.]+) shares and (?P<maximum>[0-9,.]+) shares",
        "vwap": r"average volume-weighted average price per share.+?over the (?P<days>[0-9]+) consecutive trading day period.+?the (?P<offset>[0-9]+)(?:st|nd|rd|th) scheduled trading day immediately prior",
        "capped_call": r"capped call options subject to a cap price of \$\s*(?P<price>[0-9,.]+) per share.+?generally expected to reduce the potential dilution.+?and/or offset any cash payments",
    }
    matches = {name: _one(section, pattern, offset=start, name=name) for name, pattern in patterns.items()}
    dividend_rate = _number(matches["dividend"].group("rate")) / 100.0
    preference = _number(matches["dividend"].group("preference"))
    day = int(matches["schedule"].group("day"))
    months = [part.strip() for part in re.split(r",| and ", matches["schedule"].group("months"))]
    declared_amount = _number(matches["declared"].group("amount"))
    declared_date = _date(matches["declared"].group("declared"))
    payment_date = _date(matches["declared"].group("payment"))
    conversion_date = _date(matches["conversion"].group("date"))
    minimum = _number(matches["conversion"].group("minimum"))
    maximum = _number(matches["conversion"].group("maximum"))
    if minimum <= 0 or maximum <= minimum or not (0 < dividend_rate < 1) or preference <= 0:
        raise NarrativeEvidenceError("mandatory-convertible narrative terms are economically invalid")
    values = {
        "annual_dividend_rate": dividend_rate,
        "liquidation_preference_per_share": preference,
        "dividend_payment_day": day,
        "dividend_payment_months": months,
        "declared_quarterly_dividend_per_share": declared_amount,
        "dividend_declaration_date": declared_date,
        "next_dividend_payment_date": payment_date,
        "mandatory_conversion_date": conversion_date,
        "minimum_conversion_rate": minimum,
        "maximum_conversion_rate": maximum,
        "vwap_trading_days": int(matches["vwap"].group("days")),
        "vwap_start_trading_day_offset": int(matches["vwap"].group("offset")),
        "capped_call_cap_price": _number(matches["capped_call"].group("price")),
        "capped_call_treatment": "excluded_unless_realized_offset_is_source_bound",
    }
    units = {
        "annual_dividend_rate": "ratio", "liquidation_preference_per_share": "USD/share",
        "dividend_payment_day": "day_of_month", "dividend_payment_months": "month_names",
        "declared_quarterly_dividend_per_share": "USD/share", "dividend_declaration_date": "date",
        "next_dividend_payment_date": "date", "mandatory_conversion_date": "date",
        "minimum_conversion_rate": "common_shares/preferred_share", "maximum_conversion_rate": "common_shares/preferred_share",
        "vwap_trading_days": "trading_days", "vwap_start_trading_day_offset": "trading_days",
        "capped_call_cap_price": "USD/share", "capped_call_treatment": "classification",
    }
    term_to_pattern = {
        "annual_dividend_rate": "dividend", "liquidation_preference_per_share": "dividend",
        "dividend_payment_day": "schedule", "dividend_payment_months": "schedule",
        "declared_quarterly_dividend_per_share": "declared", "dividend_declaration_date": "declared",
        "next_dividend_payment_date": "declared", "mandatory_conversion_date": "conversion",
        "minimum_conversion_rate": "conversion", "maximum_conversion_rate": "conversion",
        "vwap_trading_days": "vwap", "vwap_start_trading_day_offset": "vwap",
        "capped_call_cap_price": "capped_call", "capped_call_treatment": "capped_call",
    }
    terms = []
    for name, value in values.items():
        key = term_to_pattern[name]
        terms.append(_term(section, patterns[key], offset=start, name=name, value=value, unit=units[name]))
    return terms, {"preferred_stock": _section_record(section, start, end, str(policy["section_anchor"]))}


def _bmy(text: str, policy: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    hengrui, hs, he = _section(text, str(policy["section_anchor"]), str(policy["section_end"]))
    biontech, bs, be = _section(text, str(policy["related_section_anchor"]), str(policy["related_section_end"]))
    specs = [
        (hengrui, hs, "hengrui_upfront_payment", r"upfront payment to Hengrui of \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) in the (?P<quarter>(?:first|second|third|fourth) quarter) of (?P<year>[0-9]{4})", "USD", lambda m: _money(m.group("amount"), m.group("scale"))),
        (hengrui, hs, "hengrui_first_anniversary_payment", r"a \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) anniversary payment, payable in (?P<year>[0-9]{4})", "USD", lambda m: _money(m.group("amount"), m.group("scale"))),
        (hengrui, hs, "hengrui_second_anniversary_payment", r"second \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) anniversary payment.+?payable in (?P<year>[0-9]{4}) provided that there is no prior termination", "USD", lambda m: _money(m.group("amount"), m.group("scale"))),
        (hengrui, hs, "hengrui_contingent_milestone_maximum", r"up to \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) of contingent development, regulatory and sales-based milestones", "USD maximum exposure", lambda m: _money(m.group("amount"), m.group("scale"))),
        (biontech, bs, "biontech_paid_upfront_payment", r"made an upfront payment to BioNTech of \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) during the (?P<quarter>(?:first|second|third|fourth) quarter) of (?P<year>[0-9]{4})", "USD paid cash", lambda m: _money(m.group("amount"), m.group("scale"))),
        (biontech, bs, "biontech_future_anniversary_payments", r"receive \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) in aggregate of anniversary payments.+?beginning in the (?P<quarter>(?:first|second|third|fourth) quarter) of (?P<start_year>[0-9]{4}) through (?P<end_year>[0-9]{4})", "USD timing envelope", lambda m: _money(m.group("amount"), m.group("scale"))),
        (biontech, bs, "biontech_contingent_milestone_maximum", r"up to \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) of contingent development, regulatory and sales-based milestones", "USD maximum exposure", lambda m: _money(m.group("amount"), m.group("scale"))),
    ]
    terms: list[dict[str, Any]] = []
    for section, offset, name, pattern, unit, parser in specs:
        match = _one(section, pattern, offset=offset, name=name)
        row = _term(section, pattern, offset=offset, name=name, value=parser(match), unit=unit)
        for key in ("year", "start_year", "end_year", "quarter"):
            if key in match.groupdict() and match.group(key) is not None:
                row[key] = int(match.group(key)) if "year" in key else match.group(key).lower()
        terms.append(row)
    return terms, {
        "hengrui": _section_record(hengrui, hs, he, str(policy["section_anchor"])),
        "biontech": _section_record(biontech, bs, be, str(policy["related_section_anchor"])),
    }


def extract_narrative_evidence(policy: Mapping[str, Any], package_manifest_path: Path, *, source_root: Path) -> dict[str, Any]:
    """Extract and hash one filing's narrative evidence under a declared rule."""
    if not _same_policy(policy):
        raise NarrativeEvidenceError("narrative evidence policy identity/version mismatch")
    source_root = Path(source_root).resolve()
    manifest_path = Path(package_manifest_path).resolve()
    if not manifest_path.is_file() or not manifest_path.is_relative_to(source_root):
        raise NarrativeEvidenceError("package manifest is outside the allowed source root")
    manifest_raw = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_raw)
    except json.JSONDecodeError as exc:
        raise NarrativeEvidenceError("package manifest is invalid JSON") from exc
    if str(manifest.get("cik", "")).zfill(10) != policy["cik"]:
        raise NarrativeEvidenceError("narrative package CIK mismatch")
    entrypoint_name = manifest.get("entrypoint_local_path")
    if not isinstance(entrypoint_name, str) or not entrypoint_name:
        raise NarrativeEvidenceError("narrative package has no primary entrypoint")
    entrypoint = (manifest_path.parent / entrypoint_name).resolve()
    if not entrypoint.is_file() or not entrypoint.is_relative_to(manifest_path.parent):
        raise NarrativeEvidenceError("narrative primary document is unavailable or unsafe")
    resource = [row for row in manifest.get("files", []) if isinstance(row, Mapping) and row.get("local_path") == entrypoint_name]
    if len(resource) != 1 or not isinstance(resource[0].get("sha256"), str):
        raise NarrativeEvidenceError("narrative package primary resource is missing or ambiguous")
    document_raw = entrypoint.read_bytes()
    document_hash = sha256_bytes(document_raw)
    if document_hash != resource[0]["sha256"]:
        raise NarrativeEvidenceError("narrative primary document hash mismatch")
    parser = _VisibleText()
    try:
        parser.feed(document_raw.decode("utf-8"))
        parser.close()
    except (UnicodeDecodeError, ValueError) as exc:
        raise NarrativeEvidenceError("narrative primary document is not valid supported HTML") from exc
    text = parser.text
    if policy["mechanism"] == "mandatory_convertible_preferred":
        terms, sections = _mchp(text, policy)
    elif policy["mechanism"] == "acquisition_and_license_payments":
        terms, sections = _bmy(text, policy)
    else:
        raise NarrativeEvidenceError("unsupported narrative mechanism")
    receipt = {
        "schema_version": SCHEMA,
        "extraction_version": VERSION,
        "policy": dict(policy),
        "ticker": policy["ticker"],
        "cik": policy["cik"],
        "filing": {key: manifest.get(key) for key in ("accession", "form", "report_date", "filed_date")},
        "source": {
            "package_manifest_path": manifest_path.relative_to(source_root).as_posix(),
            "package_manifest_sha256": sha256_bytes(manifest_raw),
            "document_path": entrypoint.relative_to(source_root).as_posix(),
            "document_name": entrypoint.name,
            "document_sha256": document_hash,
            "document_byte_count": len(document_raw),
            "normalized_text_sha256": sha256(text.encode("utf-8")).hexdigest(),
        },
        "sections": sections,
        "terms": terms,
        "method": "stdlib_html_visible_text_plus_versioned_exact_regex; no AI; no OCR",
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_json_bytes(receipt))
    return receipt


def validate_narrative_evidence(receipt: Mapping[str, Any], policy: Mapping[str, Any], *, source_root: Path) -> dict[str, Any]:
    """Re-extract a receipt from current bytes and require exact equality."""
    stored = dict(receipt)
    digest = stored.pop("receipt_sha256", None)
    if not isinstance(digest, str) or sha256_bytes(canonical_json_bytes(stored)) != digest:
        raise NarrativeEvidenceError("narrative receipt hash mismatch")
    source = receipt.get("source")
    if not isinstance(source, Mapping) or not isinstance(source.get("package_manifest_path"), str):
        raise NarrativeEvidenceError("narrative receipt source locator is invalid")
    rebuilt = extract_narrative_evidence(policy, Path(source_root) / source["package_manifest_path"], source_root=source_root)
    if canonical_json_bytes(rebuilt) != canonical_json_bytes(dict(receipt)):
        raise NarrativeEvidenceError("narrative receipt no longer matches extracted source bytes")
    return rebuilt


def terms_by_name(receipt: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = receipt.get("terms")
    if not isinstance(rows, list):
        raise NarrativeEvidenceError("narrative receipt has no terms")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("name"), str) or row["name"] in result:
            raise NarrativeEvidenceError("narrative receipt term index is malformed")
        result[row["name"]] = dict(row)
    return result


__all__ = [
    "NarrativeEvidenceError", "POLICIES", "SCHEMA", "VERSION",
    "extract_narrative_evidence", "narrative_policy", "terms_by_name",
    "validate_narrative_evidence",
]
