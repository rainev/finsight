#!/usr/bin/env python3
"""Capture and parse controlling SEC XBRL filings for Batch 50."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_50 import BATCH_50_MANIFEST, BATCH_50_VALUATION_DATE
from app.us_valuation.sec_client import normalize_cik
from capture_batch_02_structural_sources import ELIGIBLE_FORMS, PROTECTED_ROOTS, _dependencies, _immutable_json, _json_bytes, _sha256, _tree_hash, _validate_paths
from capture_batch_12_structural_sources import _reuse_any_structural


def control(root: Path, issuer):
    path = Path(root) / issuer.ticker
    packet = json.loads((path / "source-manifest.json").read_text())
    filing = dict(max((row for row in packet["eligible_filings"] if row["form"] in ELIGIBLE_FORMS), key=lambda row: (row["filed"], row["accession"])))
    recent = json.loads((path / "submissions.json").read_text())["filings"]["recent"]
    index = recent["accessionNumber"].index(filing["accession"])
    filing["report_date"] = recent["reportDate"][index]
    return filing, packet


def capture_structural_sources(*, source_root: Path, output_root: Path, cache_root: Path, user_agent: str | None = None, refresh: bool = False, client=None, package_capture=None, parse=None, reuse_roots=(), protected_serving_roots=PROTECTED_ROOTS, parse_timeout_seconds: int = 600):
    source_root, output_root, cache_root = map(Path, (source_root, output_root, cache_root))
    _validate_paths(source_root, output_root, cache_root, protected_serving_roots)
    before = {str(root): _tree_hash(root) for root in protected_serving_roots}
    controls = {issuer.ticker: control(source_root, issuer) for issuer in BATCH_50_MANIFEST}
    cached = {issuer.ticker: _reuse_any_structural(tuple(map(Path, reuse_roots)), issuer, controls[issuer.ticker][0]) for issuer in BATCH_50_MANIFEST}
    if any(value is None for value in cached.values()) and (client is None or package_capture is None or parse is None):
        sec, pack, parser = _dependencies()
        client, package_capture, parse = client or sec(user_agent=user_agent, cache_dir=cache_root / ".sec-cache"), package_capture or pack, parse or parser
    cases, reused, captured = [], [], []
    for issuer in BATCH_50_MANIFEST:
        filing, packet = controls[issuer.ticker]
        prior = cached[issuer.ticker]
        if prior:
            value, package, source = prior
            reused.append(issuer.ticker)
        else:
            entry = package_capture(client, cik=issuer.cik, accession=filing["accession"], primary_document=filing["primary_document"], form=filing["form"], output_dir=cache_root / "filings" / issuer.ticker, refresh=refresh, filed_date=filing["filed"], report_date=filing["report_date"])
            parsed = parse(entry, accession=filing["accession"], form=filing["form"], timeout_seconds=parse_timeout_seconds)
            value, package, source = parsed.as_dict() if hasattr(parsed, "as_dict") else parsed, json.loads((entry.parent / "package-manifest.json").read_text()), None
            captured.append(issuer.ticker)
        if normalize_cik(package.get("cik", "")) != issuer.cik:
            raise ValueError(issuer.ticker)
        receipt = {"schema_version": "FINSIGHT-BATCH-50-STRUCTURAL-SOURCE-1", "valuation_date": BATCH_50_VALUATION_DATE, "ticker": issuer.ticker, "cik": issuer.cik, "filing": filing, "source_packet_manifest_sha256": _sha256(_json_bytes(packet)), "package_manifest_sha256": _sha256(_json_bytes(package)), "structural_filing_sha256": _sha256(_json_bytes(value)), "capture_mode": "reused" if prior else "captured", "reuse_source": source}
        target = output_root / issuer.ticker
        _immutable_json(target / "package-manifest.json", package)
        _immutable_json(target / "structural-filing.json", value)
        _immutable_json(target / "source-receipt.json", receipt)
        cases.append({"ticker": issuer.ticker, "accession": filing["accession"], "filed": filing["filed"], "report_date": filing["report_date"], "form": filing["form"], "result": "parsed", "capture_mode": "reused" if prior else "captured"})
    after = {str(root): _tree_hash(root) for root in protected_serving_roots}
    if before != after:
        raise RuntimeError("serving changed")
    summary = {"schema_version": "FINSIGHT-BATCH-50-STRUCTURAL-SOURCE-1", "valuation_date": BATCH_50_VALUATION_DATE, "attempted": 10, "parsed": 10, "failed": 0, "reused_tickers": reused, "captured_tickers": captured, "cases": cases, "serving_hash_before": before, "serving_hash_after": after, "serving_artifacts_changed": False}
    _immutable_json(output_root / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--cache-root", required=True, type=Path)
    parser.add_argument("--reuse-root", action="append", default=[], type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--parse-timeout-seconds", type=int, default=600)
    args = vars(parser.parse_args())
    args["reuse_roots"] = tuple(args.pop("reuse_root"))
    print(json.dumps(capture_structural_sources(**args), sort_keys=True))


if __name__ == "__main__":
    main()
