#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_32 import BATCH_32_MANIFEST, BATCH_32_VALUATION_DATE
from app.us_valuation.sec_client import SecClient
from capture_batch_02_sources import PROTECTED_ROOTS, _assert_non_serving, _fetch_metadata, _packet_payloads, _publish, _tree_hash
from capture_batch_11_sources import _reuse


def capture_sources(*, output_root: Path, reuse_root: Path | None = None, user_agent: str | None = None, refresh: bool = False, client=None, protected_serving_roots=PROTECTED_ROOTS) -> dict:
    output_root = Path(output_root)
    roots = tuple(map(Path, protected_serving_roots))
    _assert_non_serving(output_root, roots)
    before = {str(root): _tree_hash(root) for root in roots}
    cached = {issuer.ticker: _reuse(reuse_root, issuer.ticker) for issuer in BATCH_32_MANIFEST}
    reused = [issuer.ticker for issuer in BATCH_32_MANIFEST if cached[issuer.ticker]]
    client = client or SecClient(user_agent=user_agent, cache_dir=output_root.parent / ".sec-cache")
    fetched: list[str] = []
    for issuer in BATCH_32_MANIFEST:
        prior = cached[issuer.ticker]
        if prior:
            submissions, facts, submissions_meta, facts_meta = prior
        else:
            submissions = client.submissions(issuer.cik, refresh=refresh)
            facts = client.companyfacts(issuer.cik, refresh=refresh)
            submissions_meta = _fetch_metadata(client, issuer.cik, "submissions.json")
            facts_meta = _fetch_metadata(client, issuer.cik, "companyfacts.json")
            fetched.append(issuer.ticker)
        _publish(output_root / issuer.ticker, _packet_payloads(issuer, submissions, facts, submissions_metadata=submissions_meta, facts_metadata=facts_meta, valuation_date=BATCH_32_VALUATION_DATE, schema_version="FINSIGHT-BATCH-32-SOURCE-1"))
    after = {str(root): _tree_hash(root) for root in roots}
    if before != after:
        raise RuntimeError("serving changed")
    return {"manifest_count": 10, "source_packet_count": 10, "reused_tickers": reused, "fetched_tickers": fetched, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--reuse-root", type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--refresh", action="store_true")
    print(json.dumps(capture_sources(**vars(parser.parse_args())), sort_keys=True))


if __name__ == "__main__":
    main()
