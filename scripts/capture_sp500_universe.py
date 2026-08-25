#!/usr/bin/env python3
"""Capture and reconcile the authorized S&P 500 issuer universe at 2026-08-14."""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Callable
from urllib.request import Request, urlopen


VALUATION_DATE = "2026-08-14"
UNIVERSE_VERSION = "US-SP500-ISSUERS-2026-08-14-1.0"
REVISION_ID = 1369213082
REVISION_TIMESTAMP = "2026-08-13T15:09:18Z"
REVISION_API_URL = (
    "https://en.wikipedia.org/w/api.php?action=query&prop=revisions&"
    "titles=List_of_S%26P_500_companies&rvstart=2026-08-14T23%3A59%3A59Z&"
    "rvdir=older&rvlimit=1&rvprop=ids%7Ctimestamp&format=json"
)
REVISION_HTML_URL = (
    "https://en.wikipedia.org/w/index.php?title=List_of_S%26P_500_companies&"
    f"oldid={REVISION_ID}"
)
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SP_CHANGE_URL = (
    "https://press.spglobal.com/2026-08-13-Reddit-Set-to-Join-S-P-500-and-"
    "Sun-Communities-to-Join-S-P-MidCap-400"
)
PRIMARY_CLASS = {
    "0001652044": "GOOGL",
    "0001754301": "FOXA",
    "0001564708": "NWSA",
}
HISTORICAL_TICKER_EXCEPTIONS = {
    "EQR": {
        "cutoff_cik": "0000906107",
        "current_sec_cik": "0000931182",
        "reason": (
            "At the cutoff EQR identified Equity Residential CIK 0000906107. "
            "S&P's post-cutoff notice said the planned combined company would use VMRK; "
            "the captured current SEC map associates CIK 0000906107 with VMRK and now "
            "assigns EQR to an operating partnership. This exception preserves only "
            "the historical cutoff identity."
        ),
    }
}
SP_CHANGE_EVIDENCE = {
    "announcement_date": "2026-08-13",
    "effective_date": "2026-08-18",
    "index": "S&P 500",
    "addition": "RDDT",
    "deletion": "AVB",
}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _immutable(path: Path, raw: bytes) -> None:
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite immutable output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent)) / path.name
    try:
        temp.write_bytes(raw)
        temp.replace(path)
    finally:
        temp.parent.rmdir()


def _replace_own_generated_manifest(path: Path, raw: bytes) -> None:
    """Replace only this task's same-membership generated manifest."""

    existing = json.loads(path.read_text())
    replacement = json.loads(raw)
    if (
        existing.get("universe_version") != UNIVERSE_VERSION
        or existing.get("records") != replacement.get("records")
    ):
        raise ValueError("refusing to replace a different universe manifest")
    temp = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent)) / path.name
    try:
        temp.write_bytes(raw)
        temp.replace(path)
    finally:
        temp.parent.rmdir()


class _ConstituentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table" and attributes.get("id") == "constituents":
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_row = True
            self.row = []
        elif self.in_row and tag in {"td", "th"}:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.in_cell and tag in {"td", "th"}:
            self.row.append(" ".join("".join(self.cell_parts).split()))
            self.in_cell = False
        elif self.in_row and tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.in_row = False
        elif self.in_table and tag == "table":
            self.in_table = False


def parse_constituents(raw: bytes) -> list[dict[str, str]]:
    parser = _ConstituentParser()
    parser.feed(raw.decode("utf-8"))
    if not parser.rows:
        raise ValueError("constituent table is absent")
    header = parser.rows[0]
    expected = [
        "Symbol",
        "Security",
        "GICS Sector",
        "GICS Sub-Industry",
        "Headquarters Location",
        "Date added",
        "CIK",
        "Founded",
    ]
    if header != expected:
        raise ValueError("constituent table header changed")
    rows = []
    for values in parser.rows[1:]:
        if len(values) != len(expected):
            raise ValueError("constituent row has an unsupported shape")
        row = dict(zip(expected, values))
        row["Symbol"] = row["Symbol"].upper()
        row["CIK"] = "".join(character for character in row["CIK"] if character.isdigit()).zfill(10)
        rows.append(row)
    return rows


def _sec_map(raw: bytes) -> dict[str, tuple[str, str]]:
    value = json.loads(raw)
    result = {}
    for row in value.values():
        ticker = str(row["ticker"]).replace(".", "-").upper()
        result[ticker] = (str(row["cik_str"]).zfill(10), str(row["title"]))
    return result


def build_universe(
    *,
    constituent_html: bytes,
    sec_tickers: bytes,
    revision_metadata: bytes,
    sp_change_notice: bytes,
) -> dict[str, Any]:
    metadata = json.loads(revision_metadata)
    revisions = next(iter(metadata["query"]["pages"].values()))["revisions"]
    if revisions != [{"revid": REVISION_ID, "parentid": 1369168082, "timestamp": REVISION_TIMESTAMP}]:
        raise ValueError("Wikipedia revision metadata does not match the cutoff snapshot")
    notice_text = re.sub(r"\s+", " ", sp_change_notice.decode("utf-8", errors="ignore"))
    if not all(text in notice_text for text in ("August 18, 2026", "RDDT", "AVB")):
        raise ValueError("S&P change notice does not prove the post-cutoff AVB/RDDT change")
    rows = parse_constituents(constituent_html)
    if len(rows) != 503:
        raise ValueError("S&P snapshot must contain exactly 503 securities")
    by_cik: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_cik.setdefault(row["CIK"], []).append(row)
    if len(by_cik) != 500:
        raise ValueError("S&P snapshot must contain exactly 500 issuer CIKs")
    duplicate_groups = {
        cik: sorted(row["Symbol"] for row in grouped)
        for cik, grouped in by_cik.items()
        if len(grouped) > 1
    }
    if duplicate_groups != {
        "0001564708": ["NWS", "NWSA"],
        "0001652044": ["GOOG", "GOOGL"],
        "0001754301": ["FOX", "FOXA"],
    }:
        raise ValueError("S&P multi-class issuer set changed")
    if not any(row["Symbol"] == "AVB" for row in rows) or any(
        row["Symbol"] == "RDDT" for row in rows
    ):
        raise ValueError("cutoff snapshot must include AVB and exclude RDDT")

    sec = _sec_map(sec_tickers)
    mismatches = []
    records = []
    for cik, grouped in by_cik.items():
        symbols = sorted(row["Symbol"] for row in grouped)
        if len(grouped) == 1:
            selected = grouped[0]
            share_policy = "sole_index_security"
        else:
            primary = PRIMARY_CLASS.get(cik)
            selected = next((row for row in grouped if row["Symbol"] == primary), None)
            if selected is None:
                raise ValueError(f"primary share class is unresolved for CIK {cik}")
            share_policy = "explicit_class_a_primary"
        normalized_ticker = selected["Symbol"].replace(".", "-")
        current = sec.get(normalized_ticker)
        if current is None or current[0] != cik:
            exception = HISTORICAL_TICKER_EXCEPTIONS.get(selected["Symbol"])
            if exception is None or exception["cutoff_cik"] != cik or current is None or current[0] != exception["current_sec_cik"]:
                mismatches.append(
                    {
                        "ticker": selected["Symbol"],
                        "cutoff_cik": cik,
                        "current_sec_cik": current[0] if current else None,
                    }
                )
            if selected["Symbol"] == "EQR" and sec.get("VMRK", (None,))[0] != cik:
                raise ValueError("current SEC mapping does not corroborate the EQR/VMRK CIK")
        records.append(
            {
                "ticker": selected["Symbol"],
                "all_index_tickers": symbols,
                "issuer_name": selected["Security"],
                "cik": cik,
                "gics_sector": selected["GICS Sector"],
                "gics_sub_industry": selected["GICS Sub-Industry"],
                "headquarters": selected["Headquarters Location"],
                "date_added": selected["Date added"],
                "founded": selected["Founded"],
                "filing_regime": "pending_source_packet",
                "accounting_standard": "pending_source_packet",
                "membership_source": REVISION_HTML_URL,
                "membership_effective_date": VALUATION_DATE,
                "share_class_policy": share_policy,
                "included": True,
            }
        )
    if mismatches:
        raise ValueError(f"unapproved SEC ticker/CIK mismatches: {mismatches}")
    records.sort(key=lambda row: row["cik"])
    return {
        "universe_version": UNIVERSE_VERSION,
        "effective_date": VALUATION_DATE,
        "membership_basis": (
            "Public reconstruction from the pinned Wikipedia constituent table, "
            "corroborated by the official S&P post-cutoff AVB/RDDT change notice."
        ),
        "source_urls": {
            "revision_api": REVISION_API_URL,
            "constituent_snapshot": REVISION_HTML_URL,
            "sec_ticker_mapping": SEC_TICKERS_URL,
            "sp_change_notice": SP_CHANGE_URL,
        },
        "source_sha256": {
            "revision_metadata": _sha(revision_metadata),
            "constituent_html": _sha(constituent_html),
            "sec_tickers": _sha(sec_tickers),
            "sp_change_notice_evidence": _sha(_json_bytes(SP_CHANGE_EVIDENCE)),
        },
        "sp_change_evidence": SP_CHANGE_EVIDENCE,
        "security_count": len(rows),
        "issuer_count": len(records),
        "multi_class_policy": PRIMARY_CLASS,
        "historical_ticker_exceptions": HISTORICAL_TICKER_EXCEPTIONS,
        "records": records,
    }


def _fetch(url: str, *, user_agent: str) -> bytes:
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "*/*"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def capture(
    *,
    output_root: Path,
    manifest_output: Path,
    user_agent: str,
    fetch: Callable[..., bytes] = _fetch,
    replace_generated_manifest: bool = False,
) -> dict[str, Any]:
    if not user_agent.strip():
        raise ValueError("a monitored user agent is required")
    raw = {
        "revision-metadata.json": fetch(REVISION_API_URL, user_agent=user_agent),
        "constituents.html": fetch(REVISION_HTML_URL, user_agent=user_agent),
        "sec-company-tickers.json": fetch(SEC_TICKERS_URL, user_agent=user_agent),
        "sp-change-notice.html": fetch(SP_CHANGE_URL, user_agent=user_agent),
    }
    universe = build_universe(
        constituent_html=raw["constituents.html"],
        sec_tickers=raw["sec-company-tickers.json"],
        revision_metadata=raw["revision-metadata.json"],
        sp_change_notice=raw["sp-change-notice.html"],
    )
    for name, payload in raw.items():
        _immutable(output_root / "raw" / name, payload)
    manifest_raw = _json_bytes(universe)
    _immutable(output_root / "universe.json", manifest_raw)
    if manifest_output.exists() and replace_generated_manifest:
        _replace_own_generated_manifest(manifest_output, manifest_raw)
    else:
        _immutable(manifest_output, manifest_raw)
    receipt = {
        "universe_version": UNIVERSE_VERSION,
        "effective_date": VALUATION_DATE,
        "security_count": universe["security_count"],
        "issuer_count": universe["issuer_count"],
        "manifest_sha256": _sha(manifest_raw),
        "source_sha256": universe["source_sha256"],
        "raw_source_sha256": {name: _sha(payload) for name, payload in raw.items()},
    }
    _immutable(output_root / "receipt.json", _json_bytes(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-output", required=True, type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--replace-generated-manifest", action="store_true")
    args = parser.parse_args()
    if args.user_agent is None:
        raise SystemExit("--user-agent or SEC_USER_AGENT is required")
    print(json.dumps(capture(**vars(args)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
