"""Source-bound refresh binding for the Batch 01 AIT owner-cash recipe.

This is deliberately a separate refresh lane.  AIT's approved private model is
an after-interest owner-cash schedule, not the generic operating-income or
enterprise-cash refresh lane.  The binder consumes cached SEC packets only;
it never captures sources, writes a catalog, or changes admission state.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from html.parser import HTMLParser
import hashlib
from math import isfinite
from pathlib import Path
import re
from statistics import median
from typing import Any, Mapping

from .calculation_recipe import evaluate_recipe
from .expansion_period_inputs import FIELD_CONCEPTS, FIELD_UNITS, build_expansion_period_inputs


SCHEMA_VERSION = "FINSIGHT-B01-SUPPORTED-REFRESH-1"
PROFILE = "owner_cash_ait"
TICKER = "AIT"
CIK = "0000109563"
RECIPE_SCHEMA = "FINSIGHT-CALCULATION-RECIPE-1"
SUPPORTED_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A"}
ANNUAL_FORMS = {"10-K", "10-K/A"}
QUARTER_FORMS = {"10-Q", "10-Q/A"}
SCENARIOS = ("bear", "base", "bull")


class AITRefreshError(ValueError):
    """A source, identity, contract, or explicit AIT refresh hold."""


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "head"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "head"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _fail(message: str) -> None:
    raise AITRefreshError(f"ait refresh hold: {message}")


def _iso(value: Any, name: str) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError) as exc:
        raise AITRefreshError(f"{name} must be an ISO date") from exc


def _cik(value: Any, name: str = "CIK") -> str:
    text = str(value or "")
    if not text.isdigit() or len(text) > 10:
        raise AITRefreshError(f"{name} is missing or invalid")
    return text.zfill(10)


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise AITRefreshError(f"{name} must be finite")
    return float(value)


def _unit(value: Any) -> str:
    return str(value or "").removeprefix("xbrli:")


def _qname(row: Mapping[str, Any]) -> str:
    return str(row.get("qname") or row.get("concept") or "")


def _period(row: Mapping[str, Any]) -> tuple[str | None, str | None]:
    return row.get("period_start") or row.get("start"), row.get("period_end") or row.get("end")


def _dimensions(row: Mapping[str, Any]) -> list[Any]:
    value = row.get("dimensions") or []
    return list(value) if isinstance(value, list) else []


def _value(row: Mapping[str, Any], name: str) -> float:
    return _finite(row.get("value", row.get("val")), name)


def _filing(policy: Mapping[str, Any], packet: Mapping[str, Any], cutoff: str) -> dict[str, Any]:
    raw = packet.get("_selected_controlling_filing") or packet.get("controlling_filing")
    if not isinstance(raw, Mapping):
        _fail("controlling filing is required")
    accession = raw.get("accessionNumber") or raw.get("accession")
    filed = raw.get("filingDate") or raw.get("filed")
    period = raw.get("reportDate") or raw.get("report_date")
    form = raw.get("form")
    if not all(isinstance(item, str) and item for item in (accession, filed, period, form)):
        _fail("controlling filing metadata is incomplete")
    filed, period = _iso(filed, "filing date"), _iso(period, "report date")
    if filed > cutoff or period > cutoff:
        _fail("controlling filing is after cutoff")
    if form not in SUPPORTED_FORMS:
        _fail("controlling filing form is unsupported")
    expected = _cik(policy.get("expected_cik") or policy.get("cik") or CIK, "policy CIK")
    for source_name, source in (("issuer", packet.get("issuer")), ("companyfacts", packet.get("companyfacts")), ("submissions", packet.get("submissions"))):
        if isinstance(source, Mapping) and source.get("cik") is not None and _cik(source.get("cik"), f"{source_name} CIK") != expected:
            _fail(f"{source_name} CIK differs from AIT")
    result = dict(raw)
    result.update(accessionNumber=accession, accession=accession, filingDate=filed, filed=filed,
                  reportDate=period, report_date=period, form=form)
    return result


def _receipt_values(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in ("structural_receipts", "amendment_structural_receipts", "annual_document_receipts", "document_receipts", "receipts"):
        value = packet.get(key)
        values = list(value.values()) if isinstance(value, Mapping) else value
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, Mapping):
                result.append(dict(item))
    return result


def _receipt(packet: Mapping[str, Any], accession: str, *, annual: bool = False) -> dict[str, Any] | None:
    candidates = []
    for item in _receipt_values(packet):
        item_accession = item.get("accession") or item.get("accessionNumber") or item.get("source_accession")
        form = item.get("form")
        if item_accession == accession and (not annual or form in ANNUAL_FORMS):
            candidates.append(item)
    if candidates:
        return candidates[0]
    # Some cached packets expose the annual structural receipt separately.
    annual_item = packet.get("annual_structural_receipt") or packet.get("annual_document_receipt")
    if isinstance(annual_item, Mapping):
        item_accession = annual_item.get("accession") or annual_item.get("accessionNumber") or annual_item.get("source_accession")
        if item_accession == accession:
            return dict(annual_item)
    return None


def _read_receipt(receipt: Mapping[str, Any], *, label: str, cutoff: str) -> tuple[bytes, str, str]:
    path_value = receipt.get("path") or receipt.get("source_path")
    if not path_value:
        _fail(f"{label} receipt path is missing")
    path = Path(str(path_value))
    if not path.is_file():
        _fail(f"{label} receipt path is missing")
    expected = receipt.get("raw_payload_sha256") or receipt.get("sha256") or receipt.get("document_sha256")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        _fail(f"{label} receipt SHA-256 is missing")
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected.lower():
        _fail(f"{label} receipt SHA-256 mismatch")
    filed = receipt.get("filed_date") or receipt.get("filingDate") or receipt.get("filed")
    if filed is not None and _iso(filed, f"{label} filing date") > cutoff:
        _fail(f"{label} receipt is after cutoff")
    return raw, str(path), actual


def _visible_text(raw: bytes) -> str:
    parser = _TextParser()
    try:
        parser.feed(raw.decode("utf-8", errors="strict"))
        parser.close()
    except (UnicodeDecodeError, ValueError) as exc:
        _fail(f"primary filing is not valid UTF-8 HTML: {exc}")
    return re.sub(r"\s+", " ", " ".join(parser.parts)).replace("\xa0", " ").strip()


def _number_millions(value: str) -> float:
    return float(value.replace(",", "").strip())


def _number_scaled(value: str, scale: float) -> float:
    return float(value.replace(",", "").strip()) * scale


def _parse_capex(text: str, *, expected_year: int) -> dict[str, Any]:
    match = re.search(
        r"We expect capital expenditures for\s+(?P<year>\d{4})\s+to be in the\s+\$\s*(?P<low>[\d,.]+)\s*million\s+to\s+\$\s*(?P<high>[\d,.]+)\s*million\s+range",
        text,
        re.IGNORECASE,
    )
    if not match:
        _fail("annual-equivalent total-capex guidance is missing from the captured primary filing")
    year = int(match.group("year"))
    if year != expected_year:
        _fail(f"capex guidance endpoint changed: expected fiscal year {expected_year}, got {year}")
    low, high = _number_millions(match.group("low")) * 1_000_000, _number_millions(match.group("high")) * 1_000_000
    if not 0 < low <= high:
        _fail("capex guidance range is invalid")
    return {"guidance_year": year, "reported_guidance_low_USD": low, "reported_guidance_high_USD": high,
            "amounts_USD": {"bear": high, "base": (low + high) / 2.0, "bull": low},
            "scope": "total_capex_replaces_not_adds_to_normal_budget"}


def _parse_holdbacks(raw: bytes, *, report_date: str) -> dict[str, Any]:
    """Parse only the scoped contractual-obligations table.

    The unit scale is a source fact, not a policy default.  The table must
    carry the first two maturity columns used by the model and must be tied to
    the current filing's as-of date.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover - application runtime bundles bs4
        _fail(f"contractual-obligations table parser is unavailable: {exc}")
    soup = BeautifulSoup(raw, "html.parser")
    text = re.sub(r"\s+", " ", " ".join(soup.stripped_strings)).replace("\xa0", " ").strip()
    current_date = date.fromisoformat(report_date).strftime("%B %-d, %Y")
    scope = re.search(
        rf"contractual\s+obligations.*?as\s+of\s+{re.escape(current_date)}\s*\(\s*in\s+(?P<unit>thousands|millions)\s*\)",
        text,
        re.IGNORECASE,
    )
    if not scope:
        _fail("current contractual-obligations table lacks an explicit as-of date and unit scale")
    scale = 1_000.0 if scope.group("unit").lower() == "thousands" else 1_000_000.0
    unit_scale = f"reported_{scope.group('unit').lower()}"
    header_required = (
        re.compile(r"total", re.IGNORECASE),
        re.compile(r"period\s+less\s+than\s+1\s+yr|less\s+than\s+1\s+yr", re.IGNORECASE),
        re.compile(r"period\s+2\s*[-–]\s*3\s+yrs|2\s*[-–]\s*3\s+yrs", re.IGNORECASE),
        re.compile(r"period\s+4\s*[-–]\s*5\s+yrs|4\s*[-–]\s*5\s+yrs", re.IGNORECASE),
        re.compile(r"period\s+over\s+5\s+yrs|over\s+5\s+yrs", re.IGNORECASE),
        re.compile(r"other", re.IGNORECASE),
    )
    for table in soup.find_all("table"):
        table_text = re.sub(r"\s+", " ", " ".join(table.stripped_strings)).replace("\xa0", " ").strip()
        if "acquisition holdback payments" not in table_text.lower():
            continue
        if not all(pattern.search(table_text) for pattern in header_required):
            continue
        for row in table.find_all("tr"):
            cells = [re.sub(r"\s+", " ", " ".join(cell.stripped_strings)).replace("\xa0", " ").strip()
                     for cell in row.find_all(["th", "td"])]
            if not cells or "acquisition holdback payments" not in cells[0].lower():
                continue
            row_text = " ".join(cells)
            if re.search(r"\(\s*[-+]?\s*[\d,]+(?:\.\d+)?\s*\)", row_text) or re.search(r"(?<!\w)-\s*\d[\d,]*(?:\.\d+)?", row_text):
                _fail("acquisition holdback maturity contains a parenthesized or negative amount")
            tokens = re.findall(r"(?<![\w.])(?:\d[\d,]*(?:\.\d+)?|[—–−-])(?![\w.])", row_text)
            if len(tokens) < 3:
                _fail("acquisition holdback maturity table is incomplete")
            values = [0.0 if token in {"—", "–", "−", "-"} else _number_scaled(token, scale) for token in tokens[:7]]
            total = values[0]
            buckets = values[1:]
            if abs(total - sum(buckets)) > 0.01:
                _fail("acquisition holdback maturity totals do not reconcile")
            if any(value < 0 for value in buckets):
                _fail("acquisition holdback maturity contains a negative amount")
            if any(value > 0 for value in buckets[2:]):
                _fail("acquisition holdback maturity has an unmapped later bucket")
            return {"total_USD": total, "year_1_USD": buckets[0], "year_2_USD": buckets[1],
                    "bucket_policy": "deduct_once_at_earliest_model_bucket_inside_reported_window",
                    "unit_scale": unit_scale, "maturity_headers": ["less_than_one_year", "years_two_to_three", "years_four_to_five", "over_five_years", "other"]}
    _fail("current contractual-obligations maturity table or required period columns are missing")


def _source_doc(packet: Mapping[str, Any], filing: Mapping[str, Any], cutoff: str, *, annual: bool = False) -> dict[str, Any]:
    receipt = _receipt(packet, filing["accessionNumber"], annual=annual)
    if receipt is None:
        _fail(f"{'annual ' if annual else ''}primary receipt is missing")
    receipt_accession = receipt.get("accession") or receipt.get("accessionNumber") or receipt.get("source_accession")
    if receipt_accession is not None and receipt_accession != filing["accessionNumber"]:
        _fail(f"{'annual ' if annual else ''}primary receipt accession does not match filing")
    receipt_filed = receipt.get("filed_date") or receipt.get("filingDate") or receipt.get("filed")
    if receipt_filed is not None and _iso(receipt_filed, "receipt filing date") != filing["filingDate"]:
        _fail(f"{'annual ' if annual else ''}primary receipt filing date does not match filing")
    receipt_report = receipt.get("report_date") or receipt.get("reportDate") or receipt.get("period_end")
    if receipt_report is not None and _iso(receipt_report, "receipt report date") != filing["reportDate"]:
        _fail(f"{'annual ' if annual else ''}primary receipt report period does not match filing")
    receipt_cik = receipt.get("cik") or receipt.get("issuer_cik") or receipt.get("entity_cik")
    if receipt_cik is not None and _cik(receipt_cik, "receipt CIK") != CIK:
        _fail(f"{'annual ' if annual else ''}primary receipt CIK does not match AIT")
    raw, path, sha = _read_receipt(receipt, label="annual" if annual else "current", cutoff=cutoff)
    return {"accession": filing["accessionNumber"], "filed_date": filing["filingDate"], "report_date": filing["reportDate"],
            "form": filing["form"], "path": path, "sha256": sha, "raw": raw, "text": _visible_text(raw)}


def _annual_ends(packet: Mapping[str, Any], cutoff: str) -> list[str]:
    candidates: set[str] = set()
    facts = packet.get("companyfacts", {}).get("facts", {}) if isinstance(packet.get("companyfacts"), Mapping) else {}
    for namespace, concepts in facts.items() if isinstance(facts, Mapping) else ():
        if not isinstance(concepts, Mapping):
            continue
        for definition in concepts.values():
            if not isinstance(definition, Mapping) or not isinstance(definition.get("units"), Mapping):
                continue
            for rows in definition["units"].values():
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if not isinstance(row, Mapping) or row.get("form") not in ANNUAL_FORMS or str(row.get("filed") or "") > cutoff:
                        continue
                    start, end = row.get("start"), row.get("end")
                    if not start or not end:
                        continue
                    try:
                        days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
                    except ValueError:
                        continue
                    if 330 <= days <= 385:
                        candidates.add(str(end))
    if isinstance(packet.get("structural_packets"), Mapping):
        for structural in packet["structural_packets"].values():
            if not isinstance(structural, Mapping):
                continue
            for row in structural.get("facts", []):
                if not isinstance(row, Mapping) or row.get("form") not in ANNUAL_FORMS or str(row.get("filed_date") or "") > cutoff:
                    continue
                start, end = row.get("period_start"), row.get("period_end")
                if start and end:
                    try:
                        if 330 <= (date.fromisoformat(end) - date.fromisoformat(start)).days + 1 <= 385:
                            candidates.add(str(end))
                    except ValueError:
                        pass
    if len(candidates) < 5:
        _fail("fewer than five cutoff-eligible annual source periods")
    return sorted(candidates)[-5:]


def _core(periods: Mapping[str, Any], mode: str) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    ledger = periods.get("source_ledger") if isinstance(periods, Mapping) else None
    if not isinstance(ledger, Mapping):
        _fail("source period ledger is unavailable")
    fields = ledger.get("fields")
    if not isinstance(fields, Mapping):
        _fail("source period fields are unavailable")
    annual: dict[str, list[dict[str, Any]]] = {}
    selected: dict[str, dict[str, Any]] = {}
    for field in ("revenue", "operating_cash_flow", "sbc", "capital_expenditures"):
        entry = fields.get(field)
        if not isinstance(entry, Mapping):
            _fail(f"{field} source field is missing")
        rows = [dict(row) for row in entry.get("annual", []) if isinstance(row, Mapping)]
        if len(rows) != 5 or len({row.get("period_end") for row in rows}) != 5:
            _fail(f"{field} has incomplete annual history")
        annual[field] = rows
        for candidate in [*rows, entry.get("current_fiscal_ytd"), entry.get("prior_fiscal_ytd")]:
            if isinstance(candidate, Mapping) and field in {"sbc", "capital_expenditures"} and _value(candidate, field) < 0:
                _fail(f"{field} source spending cannot be negative")
        source = entry.get("derived_ttm") if mode == "fiscal_ttm" else rows[-1]
        if not isinstance(source, Mapping):
            gap_text = " ".join(str(gap.get("detail") or gap.get("code") or "") for gap in periods.get("gaps", [])
                                 if isinstance(gap, Mapping) and gap.get("field") == field)
            _fail(f"{field} has no valid {'TTM' if mode == 'fiscal_ttm' else 'current annual'} source" + (f": {gap_text}" if gap_text else ""))
        selected[field] = dict(source)
        if _unit(source.get("unit")) != FIELD_UNITS[field]:
            _fail(f"{field} unit is not {FIELD_UNITS[field]}")
        if mode == "fiscal_ttm" and source.get("period_end") != ledger.get("controlling_filing", {}).get("reportDate"):
            _fail(f"{field} TTM period does not end at the controlling filing")
    for index in range(5):
        windows = {_period(rows[index]) for rows in annual.values()}
        if len(windows) != 1:
            _fail("annual cash, revenue, SBC, and capex periods are not aligned")
    if mode == "fiscal_ttm":
        ttm_windows = {_period(source) for source in selected.values()}
        if len(ttm_windows) != 1:
            _fail("fiscal-TTM cash, revenue, SBC, and capex periods are not aligned")
        for field in ("revenue", "operating_cash_flow", "sbc", "capital_expenditures"):
            entry = fields[field]
            current = entry.get("current_fiscal_ytd")
            prior = entry.get("prior_fiscal_ytd")
            if not isinstance(current, Mapping) or not isinstance(prior, Mapping):
                _fail(f"{field} current/prior fiscal YTD comparatives are incomplete")
            if _period(current) != _period(fields["revenue"].get("current_fiscal_ytd")) or _period(prior) != _period(fields["revenue"].get("prior_fiscal_ytd")):
                _fail("same-accession fiscal YTD periods are not aligned")
    return annual, selected


def _structural_rows(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    structural = packet.get("structural_filing") or packet.get("structural")
    if not isinstance(structural, Mapping):
        _fail("current structural filing is required")
    return [dict(row) for row in structural.get("facts", []) if isinstance(row, Mapping)]


def _current_fact(rows: list[Mapping[str, Any]], qnames: set[str], *, filing: Mapping[str, Any], units: set[str], field: str, positive: bool | None = None) -> dict[str, Any]:
    candidates = []
    for row in rows:
        start, end = _period(row)
        if _qname(row) not in qnames or start is not None or end != filing["reportDate"] or _unit(row.get("unit")) not in units:
            continue
        if _dimensions(row):
            continue
        if row.get("source_accession") != filing["accessionNumber"]:
            continue
        if row.get("entity_identifier") is not None and _cik(row.get("entity_identifier"), f"{field} entity") != CIK:
            continue
        if positive is True and _value(row, field) <= 0:
            continue
        if positive is False and _value(row, field) < 0:
            continue
        candidates.append(dict(row))
    if not candidates:
        _fail(f"{field} current source fact is missing")
    values = {_value(row, field) for row in candidates}
    if len(values) != 1:
        _fail(f"{field} current source facts conflict")
    return candidates[0]


def _ownership_proof(packet: Mapping[str, Any], filing: Mapping[str, Any], rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    assets = _current_fact(rows, {"us-gaap:Assets"}, filing=filing, units={"USD"}, field="assets", positive=True)
    liabilities = _current_fact(rows, {"us-gaap:Liabilities"}, filing=filing, units={"USD"}, field="liabilities", positive=False)
    parent = _current_fact(rows, {"us-gaap:StockholdersEquity"}, filing=filing, units={"USD"}, field="parent_equity", positive=False)
    if abs(_value(assets, "assets") - _value(liabilities, "liabilities") - _value(parent, "parent_equity")) > 0.01:
        _fail("outside-owner equity proof does not reconcile")
    preferred = _current_fact(rows, {"us-gaap:PreferredStockValue"}, filing=filing, units={"USD"}, field="preferred_book", positive=False)
    preferred_shares = _current_fact(rows, {"us-gaap:PreferredStockSharesOutstanding"}, filing=filing, units={"shares"}, field="preferred_shares", positive=False)
    if _value(preferred, "preferred_book") != 0 or _value(preferred_shares, "preferred_shares") != 0:
        _fail("preferred equity or preferred shares are nonzero")
    shares = _current_fact(rows, {"us-gaap:CommonStockSharesOutstanding"}, filing=filing, units={"shares"}, field="point_common_shares", positive=True)
    return {"assets": dict(assets), "liabilities": dict(liabilities), "parent_equity": dict(parent),
            "preferred": dict(preferred), "preferred_shares": dict(preferred_shares), "point_common_shares": dict(shares),
            "NCI_claim_basis_USD": 0, "preferred_claim_basis_USD": 0,
            "proof": "exact_assets_minus_liabilities_equals_parent"}


def _policy_contract(policy: Mapping[str, Any], recipe: Mapping[str, Any]) -> Mapping[str, Any]:
    contract = policy.get("contract") or policy.get("approved_contract")
    if not isinstance(contract, Mapping):
        _fail("approved AIT cash-schedule contract is missing")
    if contract.get("model") != "cash_schedule" or contract.get("growth_metric") != "revenue" or contract.get("years") != 5:
        _fail("AIT approved contract changed")
    if contract.get("growth_rule") != "absolute_initial_growth_linear_fade_to_terminal_no_observed_growth_override":
        _fail("AIT fixed-growth contract changed")
    if contract.get("discount_metric") != "cost_of_equity":
        _fail("AIT discount metric changed")
    scenarios = contract.get("scenarios")
    if not isinstance(scenarios, Mapping) or set(scenarios) != set(SCENARIOS):
        _fail("AIT scenario contract is incomplete")
    if recipe.get("schema_version") not in {None, RECIPE_SCHEMA} or recipe.get("ticker") not in {None, TICKER}:
        _fail("AIT recipe schema or ticker is unsupported")
    return contract


def _guidance(packet: Mapping[str, Any], filing: Mapping[str, Any], cutoff: str, annual_end: str) -> dict[str, Any]:
    expected_year = date.fromisoformat(annual_end).year + 1
    current = _source_doc(packet, filing, cutoff)
    documents = [current]
    if filing["form"] in QUARTER_FORMS:
        annual_filing = packet.get("latest_annual_filing") or packet.get("annual_controlling_filing")
        if isinstance(annual_filing, Mapping):
            annual_accession = annual_filing.get("accessionNumber") or annual_filing.get("accession")
            annual_end_source = annual_filing.get("reportDate") or annual_filing.get("report_date")
            if annual_accession and annual_end_source and str(annual_end_source) <= cutoff:
                    annual_filing = dict(annual_filing)
                    annual_filing.update(accessionNumber=annual_accession, filingDate=annual_filing.get("filingDate") or annual_filing.get("filed"), reportDate=annual_end_source,
                                         form=annual_filing.get("form") or "10-K")
                    if annual_filing["form"] in ANNUAL_FORMS:
                        annual_receipt = _receipt(packet, annual_accession, annual=True)
                        if annual_receipt is not None:
                            receipt_accession = annual_receipt.get("accession") or annual_receipt.get("accessionNumber") or annual_receipt.get("source_accession")
                            if receipt_accession is not None and receipt_accession != annual_accession:
                                _fail("annual guidance receipt accession does not match filing")
                            receipt_filed = annual_receipt.get("filed_date") or annual_receipt.get("filingDate") or annual_receipt.get("filed")
                            if receipt_filed is not None and annual_filing.get("filingDate") and _iso(receipt_filed, "annual guidance receipt filing date") != _iso(annual_filing["filingDate"], "annual guidance filing date"):
                                _fail("annual guidance receipt filing date does not match filing")
                            receipt_report = annual_receipt.get("report_date") or annual_receipt.get("reportDate") or annual_receipt.get("period_end")
                            if receipt_report is not None and _iso(receipt_report, "annual guidance receipt report date") != _iso(annual_end_source, "annual guidance report date"):
                                _fail("annual guidance receipt report period does not match filing")
                                raw, path, sha = _read_receipt(annual_receipt, label="annual guidance", cutoff=cutoff)
                                documents.append({"accession": annual_accession, "filed_date": annual_filing.get("filingDate"), "report_date": annual_end_source,
                                                 "form": annual_filing["form"], "path": path, "sha256": sha, "text": _visible_text(raw)})
    for document in documents:
        try:
            parsed = _parse_capex(document["text"], expected_year=expected_year)
            parsed.update({"source_accession": document["accession"], "filed_date": document["filed_date"], "source_date": document["report_date"],
                           "source_path": document["path"], "source_html_sha256": document["sha256"],
                           "source_role": "primary_filing_html",
                           "guidance_fiscal_end": f"{expected_year}-{annual_end[5:]}", "source_reference": "captured primary filing capital expenditures guidance"})
            return parsed
        except AITRefreshError:
            continue
    _fail("annual-equivalent total-capex guidance is missing from the eligible captured annual/current filing")


def _claims(packet: Mapping[str, Any], filing: Mapping[str, Any], cutoff: str) -> dict[str, Any]:
    current = _source_doc(packet, filing, cutoff)
    parsed = _parse_holdbacks(current["raw"], report_date=current["report_date"])
    parsed.update({"source_accession": current["accession"], "source_date": current["report_date"], "source_path": current["path"],
                   "source_html_sha256": current["sha256"], "source_role": "primary_filing_html",
                   "classification": "reported_dated_cash_claim_not_recurring_capex",
                   "reported_payment_windows": {"year_1_USD": "less_than_one_year", "year_2_USD": "years_two_to_three"}})
    return parsed


def _warnings(*, mode: str, annual_end: str, guidance_year: int, claims_changed: bool = False) -> list[str]:
    warnings = [
        "Low reliability; forecast assumptions and economic calibration remain unvalidated.",
        f"{'Fiscal-TTM reconstruction' if mode == 'fiscal_ttm' else 'Annual-equivalent'} forecast from {annual_end} source revenue; year1 is one model year after valuation, not actual FY{guidance_year} guidance timing.",
        "Guidance-normalized capex replaces the normal budget once and scales with forecast revenue.",
        "Holdbacks are frontloaded into earliest annual model buckets (year1/year2); exact settlement dates are not known.",
        "After-interest owner cash: no second interest addback, gross-debt deduction or cash bridge credit.",
        "Rounded balance-date point common shares, not fully diluted; no assumed buyback benefit.",
    ]
    if mode == "fiscal_ttm":
        warnings.insert(2, "Fiscal TTM is FY plus current fiscal YTD less same-accession prior fiscal YTD; no naive YTD annualization.")
    if claims_changed:
        warnings.insert(4, "Reported holdback amounts/windows were refreshed from the current primary filing; exact settlement dates remain unknown.")
    return warnings


def bind(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any], cutoff: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind a cached current annual or fiscal-TTM AIT source packet."""
    if not all(isinstance(value, Mapping) for value in (policy, recipe, packet)):
        raise AITRefreshError("policy, recipe, and packet must be mappings")
    cutoff = _iso(cutoff, "cutoff")
    ticker = str(policy.get("ticker") or recipe.get("ticker") or packet.get("issuer", {}).get("ticker") or "").upper()
    if ticker != TICKER:
        _fail("owner-cash AIT refresh supports AIT only")
    expected_cik = _cik(policy.get("expected_cik") or policy.get("cik") or CIK, "policy CIK")
    if expected_cik != CIK:
        _fail("owner-cash AIT refresh CIK is not 0000109563")
    if policy.get("schema_version") not in {None, SCHEMA_VERSION, "US-EXPANSION-POLICY-BINDING-1"}:
        _fail("unsupported AIT refresh policy schema")
    contract = _policy_contract(policy, recipe)
    filing = _filing(policy, packet, cutoff)
    mode = "annual" if filing["form"] in ANNUAL_FORMS else "fiscal_ttm"
    annual_ends = _annual_ends(packet, cutoff)
    try:
        periods = build_expansion_period_inputs(packet, annual_ends)
    except (TypeError, ValueError) as exc:
        _fail(f"source period selector rejected the cached packet: {exc}")
    annual, selected = _core(periods, mode)
    controlling_period = filing["reportDate"]
    if mode == "annual" and annual_ends[-1] != controlling_period:
        _fail("controlling 10-K is not the latest selected annual source period")
    rows = _structural_rows(packet)
    ownership = _ownership_proof(packet, filing, rows)
    current_doc = _source_doc(packet, filing, cutoff)
    if "All leases are considered to be operating leases" not in current_doc["text"]:
        _fail("current lease classification is not explicitly operating-only")
    finance_qnames = {
        "us-gaap:FinanceLeaseLiabilityCurrent", "us-gaap:FinanceLeaseLiabilityNoncurrent",
        "us-gaap:CapitalLeaseObligationsCurrent", "us-gaap:CapitalLeaseObligationsNoncurrent",
    }
    for row in rows:
        start, end = _period(row)
        if (_qname(row) in finance_qnames and start is None and end == filing["reportDate"]
                and row.get("source_accession") == filing["accessionNumber"] and not _dimensions(row)
                and _unit(row.get("unit")) == "USD" and _value(row, "finance lease liability") > 0):
            _fail("reported finance-lease principal requires a separate cash allocation")
    for field, row in selected.items():
        value = _value(row, field)
        if field == "revenue" and value <= 0:
            _fail("revenue must be positive")
        if field in {"sbc", "capital_expenditures"} and value < 0:
            _fail(f"{field} spending cannot be negative")
    current_revenue = _value(selected["revenue"], "revenue")
    historical_revenue = [_value(row, "revenue") for row in annual["revenue"]]
    historical_cfo = [_value(row, "CFO") for row in annual["operating_cash_flow"]]
    historical_sbc = [_value(row, "SBC") for row in annual["sbc"]]
    historical_capex = [_value(row, "capex") for row in annual["capital_expenditures"]]
    current_pre = _value(selected["operating_cash_flow"], "CFO") - _value(selected["sbc"], "SBC")
    if current_pre <= 0:
        _fail("current after-interest CFO less SBC is nonpositive")
    historical_pre = [cfo - sbc for cfo, sbc in zip(historical_cfo, historical_sbc)]
    margins = [cash / revenue for cash, revenue in zip(historical_pre, historical_revenue)]
    current_margin = current_pre / current_revenue
    base_margin = min(current_margin, median(margins))
    investment_ratios = [capex / revenue for capex, revenue in zip(historical_capex, historical_revenue)]
    current_investment_ratio = _value(selected["capital_expenditures"], "capex") / current_revenue
    base_investment_ratio = max(current_investment_ratio, median(investment_ratios))
    guidance = _guidance(packet, filing, cutoff, annual_ends[-1])
    claims = _claims(packet, filing, cutoff)
    scenarios: dict[str, dict[str, Any]] = {}
    schedules: dict[str, dict[str, Any]] = {}
    prior_recipe = deepcopy(recipe)
    for name in SCENARIOS:
        approved = contract["scenarios"][name]
        cash_multiplier = float(approved["pre_investment_cash_multiplier"])
        investment_multiplier = float(approved["investment_budget_multiplier"])
        cash_margin = base_margin * cash_multiplier
        if name == "bull":
            cash_margin = min(cash_margin, max(margins))
        investment_ratio = base_investment_ratio * investment_multiplier
        investment_ratio = max(investment_ratio, guidance["amounts_USD"][name] / current_revenue)
        revenue = current_revenue
        schedule = []
        for year in range(1, 6):
            initial = float(approved["initial_growth"])
            terminal = float(approved["terminal_growth"])
            growth = terminal + (initial - terminal) * (5 - year) / 4
            revenue *= 1 + growth
            pre_cash = revenue * cash_margin
            investment = revenue * investment_ratio
            claim = claims["year_1_USD"] if year == 1 else claims["year_2_USD"] if year == 2 else 0.0
            schedule.append({"year": year, "growth": growth, "revenue_USD": revenue,
                             "pre_investment_owner_cash_USD": pre_cash, "full_investment_USD": investment,
                             "one_time_acquisition_claim_USD": claim, "owner_cash_USD": pre_cash - investment - claim})
        terminal_revenue = revenue * (1 + float(approved["terminal_growth"]))
        terminal_cash = terminal_revenue * (cash_margin - investment_ratio)
        if terminal_cash <= 0:
            _fail(f"{name} terminal owner cash is nonpositive")
        schedules[name] = {"schedule": schedule, "terminal_revenue_USD": terminal_revenue, "terminal_owner_cash_USD": terminal_cash,
                           "terminal_one_time_claim_USD": 0.0, "cash_margin": cash_margin, "full_investment_ratio": investment_ratio}
        scenarios[name] = {"engine": "cash_schedule", "inputs": {
            "cash_flows": [row["owner_cash_USD"] for row in schedule],
            "discount_rate": float(approved["discount_rate"]), "net_bridge": 0.0,
            "shares": _value(ownership["point_common_shares"], "point_common_shares"),
            "terminal_cash_flow": terminal_cash, "terminal_growth": float(approved["terminal_growth"]),
        }}
    refreshed = deepcopy(prior_recipe)
    refreshed.update({"schema_version": RECIPE_SCHEMA, "ticker": TICKER, "evidence_cutoff": cutoff,
                      "valuation_date": refreshed.get("valuation_date", cutoff), "private_only": True,
                      "refresh_binding_version": SCHEMA_VERSION, "source_accession": filing["accessionNumber"],
                      "scenarios": scenarios, "warnings": _warnings(mode=mode, annual_end=annual_ends[-1], guidance_year=guidance["guidance_year"],
                                                                       claims_changed=True)})
    try:
        baseline_range = evaluate_recipe(prior_recipe)["range"]
        refreshed_range = evaluate_recipe(refreshed)["range"]
    except ValueError as exc:
        _fail(f"AIT recipe consumer rejected refreshed schedule: {exc}")
    if not 0 < refreshed_range["low"] <= refreshed_range["base"] <= refreshed_range["high"]:
        _fail("refreshed owner-cash range is not positive and ordered")
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "refresh_binding_version": SCHEMA_VERSION,
        "profile": PROFILE,
        "ticker": TICKER,
        "cik": CIK,
        "evidence_cutoff": cutoff,
        "source_mode": mode,
        "controlling_filing": {"accession": filing["accessionNumber"], "filed_date": filing["filingDate"], "report_date": filing["reportDate"], "form": filing["form"]},
        "inputs": {"current_revenue_USD": current_revenue, "current_CFO_USD": _value(selected["operating_cash_flow"], "CFO"),
                   "current_SBC_USD": _value(selected["sbc"], "SBC"), "current_capex_USD": _value(selected["capital_expenditures"], "capex"),
                   "current_pre_investment_owner_cash_USD": current_pre, "current_owner_cash_USD": current_pre - _value(selected["capital_expenditures"], "capex"),
                   "base_pre_investment_cash_margin": base_margin, "base_full_investment_ratio": base_investment_ratio,
                   "historical_pre_investment_cash_USD": historical_pre, "historical_pre_investment_cash_margins": margins,
                   "historical_investment_ratios": investment_ratios},
        "source_facts": {"annual": annual, "selected": selected, "periods": periods, "ownership": ownership,
                         "current_primary": {key: value for key, value in current_doc.items() if key not in {"text", "raw"}}},
        "guidance": guidance,
        "acquisition_holdbacks": claims,
        "scenario_schedules": schedules,
        "warnings": refreshed["warnings"],
        "baseline_replay": baseline_range,
        "refreshed_replay": refreshed_range,
        "assumptions_retained": {"cost_of_equity": True, "initial_growth": True, "terminal_growth": True, "years": True,
                                 "after_interest_CFO_less_SBC": True, "no_cash_debt_bridge": True, "point_common_shares": True,
                                 "capex_scope_total_replaces_normal_budget": True, "holdback_bucket_rule": True},
        "gate": {"ready": True, "reasons": [], "new_filing_alone_is_not_a_hold": True},
        "no_network_or_capture": packet.get("network_mode") in {None, "cache_only", "offline", "replay"},
    }
    return refreshed, ledger


def policy_readiness(policy: Mapping[str, Any], recipe: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if policy.get("schema_version") != SCHEMA_VERSION:
        reasons.append("unsupported_ait_refresh_policy_schema")
    if policy.get("profile") != PROFILE:
        reasons.append("unsupported_ait_refresh_profile")
    if str(policy.get("ticker") or recipe.get("ticker") or "").upper() != TICKER:
        reasons.append("unsupported_ait_refresh_ticker")
    try:
        if _cik(policy.get("expected_cik") or policy.get("cik"), "policy CIK") != CIK:
            reasons.append("unsupported_ait_refresh_cik")
    except AITRefreshError:
        reasons.append("ait_refresh_cik_missing_or_invalid")
    if not policy.get("source_epoch"):
        reasons.append("source_epoch_missing")
    try:
        _policy_contract(policy, recipe)
    except AITRefreshError as exc:
        reasons.append(str(exc).removeprefix("ait refresh hold: "))
    return {"ready": not reasons, "reasons": reasons, "ticker": TICKER, "profile": PROFILE}


def ready(policy: Mapping[str, Any], recipe: Mapping[str, Any]) -> bool:
    return bool(policy_readiness(policy, recipe)["ready"])


__all__ = ["AITRefreshError", "SCHEMA_VERSION", "PROFILE", "bind", "policy_readiness", "ready"]
