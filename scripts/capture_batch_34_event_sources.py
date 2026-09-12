#!/usr/bin/env python3
"""Capture material cutoff-safe financing and preferred-stock events for Batch 34."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.sec_client import SecClient, sec_archive_url


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.parts: list[str] = []
    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _text(raw: bytes) -> str:
    parser = _Text(); parser.feed(raw.decode("utf-8", errors="replace")); return " ".join(parser.parts)


def _immutable(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw: raise RuntimeError(f"immutable evidence differs: {path}")
    else: path.write_bytes(raw)


EVENTS = [
    {"ticker":"STT","cik":"0000093751","accession":"0001193125-26-346938","filed":"2026-08-12","report_date":"2026-08-12","document":"d167699d8k.htm","required":["issued and sold 500,000 depositary shares","liquidation preference of $100,000 per share","net proceeds from the offering of the Depositary Shares of approximately $495"],"terms":{"series_l_depositary_shares":500000,"liquidation_preference_per_share":100000,"liquidation_preference_total":500000000,"net_proceeds_approx":495000000},"treatment":"Series L preferred issuance closed before the valuation cutoff; the preferred claim is retained separately from common equity."},
    {"ticker":"TFC","cik":"0000092230","accession":"0001193125-26-313404","filed":"2026-07-23","report_date":"2026-07-23","document":"d307505d8k.htm","required":["issued and sold $1,250,000,000 aggregate principal amount","Truist Financial Corporation"],"terms":{"senior_or_subordinated_notes_principal":1250000000},"treatment":"The July debt offering is retained as a financing event and reconciled against the controlling balance-sheet debt; it is not added twice."},
    {"ticker":"TRV","cik":"0000086312","accession":"0001193125-26-316247","filed":"2026-07-24","report_date":"2026-07-21","document":"d659242d8k.htm","required":["$750,000,000 aggregate principal amount","4.950% Senior Notes due 2031"],"terms":{"senior_notes_principal":750000000,"coupon":0.0495,"maturity":"2031"},"treatment":"The offering is recorded as a debt-event check; the controlling June 30 debt bridge remains authoritative unless the filing proves a post-quarter balance change."},
    {"ticker":"KEY","cik":"0000091576","accession":"0001628280-26-057141","filed":"2026-08-14","report_date":"2026-08-14","document":"key-20260814.htm","required":["525,000 depositary shares representing 21,000 shares of Preferred Stock","aggregate liquidation preference of $525,000,000","redeemed for cash"],"terms":{"series_e_depositary_shares":525000,"series_e_preferred_shares":21000,"liquidation_preference_total":525000000,"redemption_date":"2026-09-15","completed_at_cutoff":False},"treatment":"The redemption was announced at the cutoff but scheduled after it; it is not treated as completed in the Batch 34 valuation."},
    {"ticker":"NTRS","cik":"0000073124","accession":"0000073124-26-000051","filed":"2026-08-03","report_date":"2026-08-03","document":"ntrs-20260803.htm","required":["redemption, on October 1, 2026","all of the issued and outstanding shares","Series D Non-Cumulative Perpetual Preferred Stock"],"terms":{"series_d_redemption_date":"2026-10-01","completed_at_cutoff":False},"treatment":"The announced preferred redemption is after the valuation cutoff and remains a warning/event ledger item, not a completed claim removal."},
]


def capture(*, output_root: Path, user_agent: str) -> dict:
    output_root = Path(output_root)
    if any(part in {"backend", "frontend"} for part in output_root.parts): raise ValueError("event evidence must remain outside serving roots")
    client = SecClient(user_agent=user_agent, cache_dir=output_root / ".sec-cache")
    cases = []
    for event in EVENTS:
        path = output_root / event["ticker"] / event["document"]
        reused = path.exists()
        raw = path.read_bytes() if reused else client.filing_attachment(event["cik"], event["accession"], event["document"], max_bytes=12 * 1024 * 1024)
        text = _text(raw)
        if any(term not in text for term in event["required"]): raise RuntimeError(f"{event['ticker']} event identity or terms changed")
        digest = hashlib.sha256(raw).hexdigest(); _immutable(path, raw)
        receipt = {"schema_version":"FINSIGHT-BATCH-34-EVENT-SOURCE-1","valuation_date":"2026-08-14","ticker":event["ticker"],"accession":event["accession"],"filed":event["filed"],"report_date":event["report_date"],"form":"8-K","document":event["document"],"url":sec_archive_url(event["cik"],event["accession"],event["document"]),"document_sha256":digest,"reported_terms":event["terms"],"treatment":event["treatment"]}
        _immutable(output_root / event["ticker"] / "source-receipt.json", (json.dumps(receipt, indent=2, sort_keys=True)+"\n").encode())
        cases.append({"ticker":event["ticker"],"accession":event["accession"],"document_sha256":digest,"reused":reused})
    summary={"valuation_date":"2026-08-14","attempted":len(EVENTS),"captured":len(cases),"cases":cases,"serving_artifacts_changed":False}
    _immutable(output_root / "summary.json", (json.dumps(summary,indent=2,sort_keys=True)+"\n").encode())
    return summary


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--output-root",required=True,type=Path); parser.add_argument("--user-agent",required=True); print(json.dumps(capture(**vars(parser.parse_args())),sort_keys=True))


if __name__ == "__main__": main()
