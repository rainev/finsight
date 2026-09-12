#!/usr/bin/env python3
"""Capture cutoff-safe SEC Companyfacts/submissions packets for Batch 48."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_48 import BATCH_48_MANIFEST, BATCH_48_VALUATION_DATE
from app.us_valuation.sec_client import SecClient
from capture_batch_02_sources import PROTECTED_ROOTS, _assert_non_serving, _fetch_metadata, _json_bytes, _packet_payloads, _publish, _tree_hash
from capture_batch_11_sources import _reuse


def capture_sources(*, output_root: Path, reuse_roots=(), user_agent: str | None = None, refresh: bool = False, client=None, protected_serving_roots=PROTECTED_ROOTS) -> dict:
    output_root = Path(output_root)
    roots = tuple(map(Path, protected_serving_roots))
    candidates = tuple(map(Path, reuse_roots))
    _assert_non_serving(output_root, roots)
    before = {str(root): _tree_hash(root) for root in roots}
    cached = {issuer.ticker: next((value for root in candidates if (value := _reuse(root, issuer.ticker)) is not None), None) for issuer in BATCH_48_MANIFEST}
    reused = [issuer.ticker for issuer in BATCH_48_MANIFEST if cached[issuer.ticker]]
    client = client or SecClient(user_agent=user_agent, cache_dir=output_root.parent / ".sec-cache")
    fetched = []
    for issuer in BATCH_48_MANIFEST:
        prior = cached[issuer.ticker]
        if prior:
            submissions, facts, submissions_meta, facts_meta = prior
        else:
            submissions = client.submissions(issuer.cik, refresh=refresh)
            facts = client.companyfacts(issuer.cik, refresh=refresh)
            submissions_meta = _fetch_metadata(client, issuer.cik, "submissions.json")
            facts_meta = _fetch_metadata(client, issuer.cik, "companyfacts.json")
            fetched.append(issuer.ticker)
        try:
            payloads = _packet_payloads(issuer, submissions, facts, submissions_metadata=submissions_meta, facts_metadata=facts_meta, valuation_date=BATCH_48_VALUATION_DATE, schema_version="FINSIGHT-BATCH-48-SOURCE-1")
        except ValueError as error:
            alias = issuer.ticker == "EQR" and submissions.get("tickers") == ["VMRK"] and submissions.get("name") == "VIVMARK RESIDENTIAL"
            empty_ticker_list = not submissions.get("tickers") and bool(submissions.get("name"))
            if "ticker identity mismatch" not in str(error) or not (alias or empty_ticker_list):
                raise
            patched = deepcopy(submissions)
            patched["tickers"] = [issuer.ticker]
            payloads = _packet_payloads(issuer, patched, facts, submissions_metadata=submissions_meta, facts_metadata=facts_meta, valuation_date=BATCH_48_VALUATION_DATE, schema_version="FINSIGHT-BATCH-48-SOURCE-1")
            original = _json_bytes(submissions)
            manifest = json.loads(payloads["source-manifest.json"])
            manifest["packet_payload_sha256"]["submissions.json"] = hashlib.sha256(original).hexdigest()
            manifest["source_identity"]["submissions_tickers"] = submissions.get("tickers", [])
            manifest["ticker_identity_override"] = {
                "accepted": True,
                "basis": (
                    "Exact normalized CIK 0000906107 identifies the same legal registrant; SEC submissions now reports VIVMARK RESIDENTIAL / VMRK while the frozen universe member remains EQR. Raw source identity is preserved and the corporate identity change must remain a valuation gate."
                    if alias
                    else "Exact normalized CIK and issuer name; SEC submissions ticker list is empty, so no raw source field was rewritten."
                ),
                "reported_name": submissions.get("name"),
                "reported_tickers": submissions.get("tickers", []),
            }
            payloads["submissions.json"] = original
            payloads["source-manifest.json"] = _json_bytes(manifest)
        _publish(output_root / issuer.ticker, payloads)
    after = {str(root): _tree_hash(root) for root in roots}
    if before != after:
        raise RuntimeError("serving changed")
    return {"manifest_count": 10, "source_packet_count": 10, "reused_tickers": reused, "fetched_tickers": fetched, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--reuse-root", action="append", default=[], type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--refresh", action="store_true")
    args = vars(parser.parse_args())
    args["reuse_roots"] = tuple(args.pop("reuse_root"))
    print(json.dumps(capture_sources(**args), sort_keys=True))


if __name__ == "__main__":
    main()
