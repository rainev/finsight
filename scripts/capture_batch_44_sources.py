#!/usr/bin/env python3
"""Capture cutoff-safe SEC Companyfacts/submissions packets for Batch 44."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_44 import BATCH_44_MANIFEST, BATCH_44_VALUATION_DATE
from app.us_valuation.sec_client import SecClient
from capture_batch_02_sources import PROTECTED_ROOTS, _assert_non_serving, _fetch_metadata, _packet_payloads, _publish, _tree_hash
from capture_batch_11_sources import _reuse


def capture_sources(*, output_root: Path, reuse_roots=(), user_agent: str | None = None, refresh: bool = False, client=None, protected_serving_roots=PROTECTED_ROOTS) -> dict:
    output_root = Path(output_root)
    roots = tuple(map(Path, protected_serving_roots)); candidates = tuple(map(Path, reuse_roots))
    _assert_non_serving(output_root, roots)
    before = {str(root): _tree_hash(root) for root in roots}
    cached = {issuer.ticker: next((value for reuse_root in candidates if (value := _reuse(reuse_root, issuer.ticker)) is not None), None) for issuer in BATCH_44_MANIFEST}
    reused = [issuer.ticker for issuer in BATCH_44_MANIFEST if cached[issuer.ticker]]
    client = client or SecClient(user_agent=user_agent, cache_dir=output_root.parent / ".sec-cache")
    fetched = []
    for issuer in BATCH_44_MANIFEST:
        prior = cached[issuer.ticker]
        if prior:
            submissions, facts, submissions_meta, facts_meta = prior
        else:
            submissions = client.submissions(issuer.cik, refresh=refresh); facts = client.companyfacts(issuer.cik, refresh=refresh)
            submissions_meta = _fetch_metadata(client, issuer.cik, "submissions.json"); facts_meta = _fetch_metadata(client, issuer.cik, "companyfacts.json"); fetched.append(issuer.ticker)
        _publish(output_root / issuer.ticker, _packet_payloads(issuer, submissions, facts, submissions_metadata=submissions_meta, facts_metadata=facts_meta, valuation_date=BATCH_44_VALUATION_DATE, schema_version="FINSIGHT-BATCH-44-SOURCE-1"))
    after = {str(root): _tree_hash(root) for root in roots}
    if before != after: raise RuntimeError("serving changed")
    return {"manifest_count": 10, "source_packet_count": 10, "reused_tickers": reused, "fetched_tickers": fetched, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output-root", required=True, type=Path); parser.add_argument("--reuse-root", action="append", default=[], type=Path); parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT")); parser.add_argument("--refresh", action="store_true")
    args = vars(parser.parse_args()); args["reuse_roots"] = tuple(args.pop("reuse_root")); print(json.dumps(capture_sources(**args), sort_keys=True))


if __name__ == "__main__": main()
