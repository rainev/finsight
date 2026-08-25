#!/usr/bin/env python3
"""Capture immutable, non-serving SEC packets for frozen Batch 03."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Protocol


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.batch_03 import (
    BATCH_03_MANIFEST,
    BATCH_03_VALUATION_DATE,
)
from app.us_valuation.sec_client import SecClient
from capture_batch_02_sources import (
    PROTECTED_ROOTS,
    _assert_non_serving,
    _fetch_metadata,
    _packet_payloads,
    _publish,
    _tree_hash,
)


class _SecClient(Protocol):
    def submissions(self, cik: str, *, refresh: bool = False) -> dict[str, Any]: ...
    def companyfacts(self, cik: str, *, refresh: bool = False) -> dict[str, Any]: ...


def _reuse_packet(
    reuse_root: Path | None, ticker: str
) -> tuple[dict[str, Any], dict[str, Any], Mapping[str, object], Mapping[str, object]] | None:
    if reuse_root is None:
        return None
    packet = reuse_root / ticker
    required = (
        "submissions.json", "companyfacts.json",
        "submissions.meta.json", "companyfacts.meta.json",
    )
    if not all((packet / name).is_file() for name in required):
        return None
    submissions = json.loads((packet / "submissions.json").read_text())
    companyfacts = json.loads((packet / "companyfacts.json").read_text())
    submissions_meta = json.loads((packet / "submissions.meta.json").read_text())
    companyfacts_meta = json.loads((packet / "companyfacts.meta.json").read_text())
    return submissions, companyfacts, submissions_meta, companyfacts_meta


def capture_sources(
    *,
    output_root: Path,
    reuse_root: Path | None = None,
    user_agent: str | None = None,
    refresh: bool = False,
    client: _SecClient | None = None,
    protected_serving_roots: tuple[Path, ...] = PROTECTED_ROOTS,
) -> dict[str, object]:
    output_root = Path(output_root)
    reuse_root = Path(reuse_root) if reuse_root is not None else None
    roots = tuple(Path(root) for root in protected_serving_roots)
    _assert_non_serving(output_root, roots)
    before = {str(root): _tree_hash(root) for root in roots}
    client = client or SecClient(
        user_agent=user_agent,
        cache_dir=output_root.parent / ".sec-cache",
    )
    packets = {}
    reused = []
    fetched = []
    for issuer in BATCH_03_MANIFEST:
        reuse = _reuse_packet(reuse_root, issuer.ticker)
        if reuse is not None:
            submissions, companyfacts, submissions_meta, companyfacts_meta = reuse
            reused.append(issuer.ticker)
        else:
            submissions = client.submissions(issuer.cik, refresh=refresh)
            companyfacts = client.companyfacts(issuer.cik, refresh=refresh)
            submissions_meta = _fetch_metadata(client, issuer.cik, "submissions.json")
            companyfacts_meta = _fetch_metadata(client, issuer.cik, "companyfacts.json")
            fetched.append(issuer.ticker)
        packets[issuer.ticker] = _packet_payloads(
            issuer,
            submissions,
            companyfacts,
            submissions_metadata=submissions_meta,
            facts_metadata=companyfacts_meta,
            valuation_date=BATCH_03_VALUATION_DATE,
            schema_version="FINSIGHT-BATCH-03-SOURCE-1",
        )
    if output_root.exists():
        unexpected = {
            path.name for path in output_root.iterdir() if path.is_dir()
        } - set(packets)
        if unexpected:
            raise FileExistsError(f"unexpected Batch 03 packet directories: {sorted(unexpected)}")
    for ticker, payloads in packets.items():
        _publish(output_root / ticker, payloads)
    after = {str(root): _tree_hash(root) for root in roots}
    if before != after:
        raise RuntimeError("protected serving artifacts changed")
    return {
        "manifest_count": 10,
        "source_packet_count": len(packets),
        "reused_tickers": reused,
        "fetched_tickers": fetched,
        "serving_artifacts_changed": False,
        "serving_hash_before": before,
        "serving_hash_after": after,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--reuse-root", type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--refresh", action="store_true")
    result = capture_sources(**vars(parser.parse_args()))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

