#!/usr/bin/env python3
"""Capture exact SEC filings and directly linked relevant exhibits immutably."""
from __future__ import annotations

import argparse
from datetime import date
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.us_valuation.sec_client import SecClient, normalize_cik
from capture_batch_02_structural_sources import (
    PROTECTED_ROOTS, _immutable_json, _json_bytes, _sha256, _tree_hash, _validate_paths,
)

SCHEMA = "FINSIGHT-SELECTED-SEC-FILINGS-WG37-2"
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
MAX_DOCUMENTS_PER_FILING = 20


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.names = set()
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a": return
        href = dict(attrs).get("href")
        if isinstance(href, str):
            name = Path(urlparse(href).path).name
            if name: self.names.add(name)


def _relevant(row: dict, primary: str, linked: set[str]) -> bool:
    name = row.get("name")
    if name == primary:
        return True
    lower = str(name).lower()
    return name in linked and (lower.startswith("exhibit2") or lower.startswith("exhibit10") or lower.startswith("exhibit99"))


def run(*, source_root, output_root, cache_root, ticker, accessions, cutoff, user_agent, client=None):
    source_root, output_root, cache_root = map(Path, (source_root, output_root, cache_root))
    _validate_paths(source_root, output_root, cache_root)
    cutoff = date.fromisoformat(cutoff).isoformat()
    submissions_raw = (source_root / "submissions.json").read_bytes()
    submissions = json.loads(submissions_raw)
    source_manifest = json.loads((source_root / "source-manifest.json").read_bytes())
    if source_manifest.get("packet_payload_sha256", {}).get("submissions.json") != _sha256(submissions_raw):
        raise ValueError("selected filing frozen submissions hash mismatch")
    cik = normalize_cik(submissions["cik"])
    issuer = source_manifest.get("issuer", {})
    if issuer.get("ticker") != ticker or normalize_cik(issuer.get("cik", "")) != cik or ticker not in submissions.get("tickers", []):
        raise ValueError("selected filing issuer identity mismatch")
    if not accessions or len(set(accessions)) != len(accessions):
        raise ValueError("explicit unique accessions required")
    recent = submissions["filings"]["recent"]
    selected = []
    for accession in accessions:
        indexes = [i for i, value in enumerate(recent["accessionNumber"]) if value == accession]
        if len(indexes) != 1:
            raise ValueError("selected filing accession missing or ambiguous")
        index = indexes[0]
        filing = {key: recent[key][index] for key in ("accessionNumber", "filingDate", "reportDate", "form", "items", "primaryDocument")}
        if filing["form"] != "8-K" or not filing["reportDate"] <= filing["filingDate"] <= cutoff:
            raise ValueError("selected filing form/date/cutoff mismatch")
        selected.append({"accession": accession, "filed_date": filing["filingDate"], "report_date": filing["reportDate"],
                         "form": filing["form"], "items": filing["items"], "primary_document": filing["primaryDocument"]})
    client = client or SecClient(user_agent=user_agent, cache_dir=cache_root / ".sec-cache")
    before = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    cases = []
    try:
        for filing in selected:
            case = {"ticker": ticker, "cik": cik, "filing": filing, "submissions_sha256": _sha256(submissions_raw)}
            try:
                index = client.filing_index(cik, filing["accession"], refresh=False)
                directory = index.get("directory") if isinstance(index, dict) else None
                items = directory.get("item") if isinstance(directory, dict) else None
                if not isinstance(items, list):
                    raise ValueError("SEC filing index has no directory items")
                primary_raw = client.filing_attachment(cik, filing["accession"], filing["primary_document"], refresh=False, max_bytes=MAX_DOCUMENT_BYTES)
                links = _Links(); links.feed(primary_raw.decode("utf-8")); links.close()
                rows = [row for row in items if isinstance(row, dict) and _relevant(row, filing["primary_document"], links.names)]
                if not rows or len(rows) > MAX_DOCUMENTS_PER_FILING or sum(row.get("name") == filing["primary_document"] for row in rows) != 1:
                    raise ValueError("selected filing relevant document set invalid")
                documents = []
                target_root = output_root / ticker / filing["accession"]
                for row in sorted(rows, key=lambda value: value["name"]):
                    raw = primary_raw if row["name"] == filing["primary_document"] else client.filing_attachment(cik, filing["accession"], row["name"], refresh=False, max_bytes=MAX_DOCUMENT_BYTES)
                    target = target_root / row["name"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists() and target.read_bytes() != raw:
                        raise FileExistsError("immutable selected SEC document differs: " + str(target))
                    target.write_bytes(raw) if not target.exists() else None
                    documents.append({"name": row["name"], "type": row.get("type"), "description": row.get("description"),
                                      "byte_count": len(raw), "sha256": _sha256(raw),
                                      "directly_linked_from_primary": row["name"] == filing["primary_document"] or row["name"] in links.names,
                                      "path": target.relative_to(output_root).as_posix()})
                index_raw = _json_bytes(index)
                index_path = target_root / "filing-index.json"
                if index_path.exists() and index_path.read_bytes() != index_raw:
                    raise FileExistsError("immutable selected SEC index differs: " + str(index_path))
                index_path.write_bytes(index_raw) if not index_path.exists() else None
                case.update(status="captured", filing_index_sha256=_sha256(index_raw), documents=documents)
                _immutable_json(target_root / "source-receipt.json", case)
            except Exception as exc:
                case.update(status="acquisition_failed", error_type=type(exc).__name__, reason=str(exc))
            cases.append(case)
    finally:
        after = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
        if before != after:
            raise RuntimeError("selected SEC capture changed protected serving artifacts")
    report = {"schema_version": SCHEMA, "cutoff": cutoff, "attempted": len(cases),
              "captured": sum(row["status"] == "captured" for row in cases), "cases": cases,
              "serving_hash_before": before, "serving_hash_after": after, "economic_validation": False}
    _immutable_json(output_root / "capture-report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-root", "output-root", "cache-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--accession", action="append", dest="accessions", required=True)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    print(json.dumps(run(**vars(parser.parse_args())), sort_keys=True))
