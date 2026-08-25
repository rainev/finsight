#!/usr/bin/env python3
"""Capture immutable SEC source packets for an arbitrary frozen ticker cohort."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.sec_client import SecClient, normalize_cik
from capture_batch_02_sources import (
    PROTECTED_ROOTS,
    _assert_non_serving,
    _fetch_metadata,
    _packet_payloads,
    _publish,
    _tree_hash,
)


@dataclass(frozen=True)
class CohortIssuer:
    ticker: str
    cik: str
    issuer_name: str


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _issuers(
    cohort_report: Path,
    universe: Path,
    sec_ticker_map: Path | None = None,
) -> tuple[CohortIssuer, ...]:
    cohort = _read(cohort_report)
    tickers = [str(item["ticker"]).upper() for item in cohort.get("cases", [])]
    if len(tickers) != 106 or len(set(tickers)) != 106:
        raise ValueError("difficult cohort must contain exactly 106 unique tickers")
    universe_rows = {
        str(item["ticker"]).upper(): item
        for item in _read(universe).get("records", [])
        if item.get("included") is True
    }
    if sec_ticker_map is not None:
        for raw in _read(sec_ticker_map).values():
            if not isinstance(raw, dict):
                continue
            ticker = str(raw.get("ticker") or "").upper()
            if ticker and ticker not in universe_rows:
                universe_rows[ticker] = {
                    "ticker": ticker,
                    "cik": raw.get("cik_str"),
                    "issuer_name": raw.get("title"),
                    "included": True,
                }
    missing = sorted(set(tickers) - set(universe_rows))
    if missing:
        raise ValueError(f"cohort tickers missing from frozen universe: {missing}")
    return tuple(
        CohortIssuer(
            ticker=ticker,
            cik=normalize_cik(universe_rows[ticker]["cik"]),
            issuer_name=str(universe_rows[ticker]["issuer_name"]),
        )
        for ticker in tickers
    )


def capture(
    *,
    cohort_report: Path,
    universe: Path,
    sec_ticker_map: Path | None,
    valuation_date: str,
    output_root: Path,
    user_agent: str | None,
    requested_tickers: tuple[str, ...] = (),
    refresh: bool = False,
    client: Any = None,
    protected_roots: tuple[Path, ...] = PROTECTED_ROOTS,
) -> dict[str, Any]:
    issuers = _issuers(cohort_report, universe, sec_ticker_map)
    requested = {ticker.upper() for ticker in requested_tickers}
    if requested:
        unknown = requested - {issuer.ticker for issuer in issuers}
        if unknown:
            raise ValueError(f"requested tickers are outside the difficult cohort: {sorted(unknown)}")
        issuers = tuple(issuer for issuer in issuers if issuer.ticker in requested)
    output_root = Path(output_root)
    _assert_non_serving(output_root, tuple(Path(root) for root in protected_roots))
    before = {str(root.resolve()): _tree_hash(root) for root in protected_roots}
    client = client or SecClient(
        user_agent=user_agent,
        cache_dir=output_root.parent / ".official-evidence-sec-cache",
    )
    cases = []
    for issuer in issuers:
        submissions = client.submissions(issuer.cik, refresh=refresh)
        facts = client.companyfacts(issuer.cik, refresh=refresh)
        packet = _packet_payloads(
            issuer,
            submissions,
            facts,
            submissions_metadata=_fetch_metadata(client, issuer.cik, "submissions.json"),
            facts_metadata=_fetch_metadata(client, issuer.cik, "companyfacts.json"),
            valuation_date=valuation_date,
            schema_version="FINSIGHT-OFFICIAL-SOURCE-1",
        )
        _publish(output_root / issuer.ticker, packet)
        cases.append(
            {
                "ticker": issuer.ticker,
                "cik": issuer.cik,
                "packet_sha256": hashlib.sha256(
                    (output_root / issuer.ticker / "source-manifest.json").read_bytes()
                ).hexdigest(),
            }
        )
    after = {str(root.resolve()): _tree_hash(root) for root in protected_roots}
    if before != after:
        raise RuntimeError("protected serving artifacts changed during source capture")
    return {
        "schema_version": "FINSIGHT-OFFICIAL-SOURCE-CAPTURE-1",
        "valuation_date": valuation_date,
        "cohort_denominator": 106,
        "captured_count": len(cases),
        "captured_tickers": [item["ticker"] for item in cases],
        "serving_artifacts_changed": False,
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-report", required=True, type=Path)
    parser.add_argument("--universe", required=True, type=Path)
    parser.add_argument("--sec-ticker-map", type=Path)
    parser.add_argument("--valuation-date", required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--ticker", action="append", default=[])
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    result = capture(
        cohort_report=args.cohort_report,
        universe=args.universe,
        sec_ticker_map=args.sec_ticker_map,
        valuation_date=args.valuation_date,
        output_root=args.output_root,
        user_agent=args.user_agent,
        requested_tickers=tuple(args.ticker),
        refresh=args.refresh,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
