#!/usr/bin/env python3
"""Capture immutable, non-serving SEC packets for frozen Batch 04."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.batch_04 import BATCH_04_MANIFEST, BATCH_04_VALUATION_DATE
from app.us_valuation.sec_client import SecClient
from capture_batch_02_sources import (
    PROTECTED_ROOTS, _assert_non_serving, _fetch_metadata, _packet_payloads,
    _publish, _tree_hash,
)


def _reuse(reuse_root: Path | None, ticker: str):
    if reuse_root is None:
        return None
    packet = reuse_root / ticker
    names = ("submissions.json", "companyfacts.json", "submissions.meta.json", "companyfacts.meta.json")
    if not all((packet / name).is_file() for name in names):
        return None
    return tuple(json.loads((packet / name).read_text()) for name in names)


def capture_sources(
    *, output_root: Path, reuse_root: Path | None = None,
    user_agent: str | None = None, refresh: bool = False,
    client: Any = None, protected_serving_roots: tuple[Path, ...] = PROTECTED_ROOTS,
) -> dict[str, Any]:
    output_root = Path(output_root)
    reuse_root = Path(reuse_root) if reuse_root else None
    roots = tuple(Path(root) for root in protected_serving_roots)
    _assert_non_serving(output_root, roots)
    before = {str(root): _tree_hash(root) for root in roots}
    client = client or SecClient(user_agent=user_agent, cache_dir=output_root.parent / ".sec-cache")
    packets = {}; reused = []; fetched = []
    for issuer in BATCH_04_MANIFEST:
        cached = _reuse(reuse_root, issuer.ticker)
        if cached:
            submissions, facts, submissions_meta, facts_meta = cached
            reused.append(issuer.ticker)
        else:
            submissions = client.submissions(issuer.cik, refresh=refresh)
            facts = client.companyfacts(issuer.cik, refresh=refresh)
            submissions_meta = _fetch_metadata(client, issuer.cik, "submissions.json")
            facts_meta = _fetch_metadata(client, issuer.cik, "companyfacts.json")
            fetched.append(issuer.ticker)
        packets[issuer.ticker] = _packet_payloads(
            issuer, submissions, facts,
            submissions_metadata=submissions_meta, facts_metadata=facts_meta,
            valuation_date=BATCH_04_VALUATION_DATE,
            schema_version="FINSIGHT-BATCH-04-SOURCE-1",
        )
    for ticker, payload in packets.items():
        _publish(output_root / ticker, payload)
    after = {str(root): _tree_hash(root) for root in roots}
    if before != after:
        raise RuntimeError("protected serving artifacts changed")
    return {
        "manifest_count": 10, "source_packet_count": 10,
        "reused_tickers": reused, "fetched_tickers": fetched,
        "serving_artifacts_changed": False,
        "serving_hash_before": before, "serving_hash_after": after,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--reuse-root", type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--refresh", action="store_true")
    print(json.dumps(capture_sources(**vars(parser.parse_args())), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

