#!/usr/bin/env python3
"""Capture cutoff-safe financing events used by controlled Batch 33."""
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


def _immutable(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise RuntimeError(f"immutable event evidence differs: {path}")
        return
    path.write_bytes(raw)


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _text(raw: bytes) -> str:
    parser = _Text()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return " ".join(parser.parts)


DEFINITIONS = {
    "AXP": {"cik": "0000004962", "accession": "0000004962-26-000338", "filed": "2026-08-12", "report_date": "2026-08-12", "form": "8-K", "document": "axp-20260812.htm", "required": ("AMERICAN EXPRESS COMPANY", "issued 1,600 shares", "liquidation preference of $1,000,000 per share", "redemption in full on September 15, 2026"), "reported_terms": {"series_e_preferred_shares_issued": 1600, "series_e_liquidation_preference_per_share": 1_000_000, "series_e_total_liquidation_preference": 1_600_000_000, "series_d_redemption_planned": True, "series_d_redemption_date": "2026-09-15", "series_d_redemption_completed_at_cutoff": False}, "treatment": "Series E closed before cutoff; Series D remained outstanding at cutoff and its planned redemption is not treated as completed."},
    "FITB": {"cik": "0000035527", "accession": "0001193125-26-342707", "filed": "2026-08-10", "report_date": "2026-08-10", "form": "S-4", "document": "d134471ds4.htm", "required": ("FIFTH THIRD BANCORP", "$334,650,000", "$938,141,000", "equal principal amount"), "reported_terms": {"registered_2029_notes": 334_650_000, "registered_2030_notes": 938_141_000, "total_exchange_principal": 1_272_791_000, "new_principal_created": False}, "treatment": "Registration exchange replaces restricted notes with equal-principal registered notes; it does not create a second debt claim."},
    "MTB": {"cik": "0000036270", "accession": "0001193125-26-310413", "filed": "2026-07-21", "report_date": "2026-07-17", "form": "8-K", "document": "d127076d8k.htm", "required": ("M&T BANK CORPORATION", "24,000,000 depositary shares", "liquidation preference $10,000 per share", "6.625%"), "reported_terms": {"series_l_depositary_shares": 24_000_000, "depositary_share_price": 25, "series_l_preferred_equity": 600_000_000, "annual_preferred_dividend": 39_750_000, "offering_completed": True}, "treatment": "The cutoff issuance adds $600M to total equity and preferred equity equally, leaving common book unchanged while adding a future preferred-dividend burden."},
    "BEN": {"cik": "0000038777", "accession": "0001552781-26-000423", "filed": "2026-08-10", "report_date": "2026-08-05", "form": "8-K", "document": "e26341_ben-8k.htm", "required": ("Resources, Inc.", "$750,000,000 aggregate principal amount", "repay approximately $700,000,000", "5.500%"), "reported_terms": {"new_notes_principal": 750_000_000, "revolver_repayment_expected": 700_000_000, "net_debt_increase_before_fees": 50_000_000, "coupon": .055, "maturity": "2036-08-10"}, "treatment": "Debt refinancing is retained in the equity-level warning; client assets are not treated as issuer cash and no EV bridge is applied."},
}


def capture(*, output_root: Path, user_agent: str) -> dict:
    output_root = Path(output_root)
    if any(part in {"backend", "frontend"} for part in output_root.parts):
        raise ValueError("event evidence must remain outside serving roots")
    client = SecClient(user_agent=user_agent, cache_dir=output_root / ".sec-cache")
    cases = []
    for ticker, definition in DEFINITIONS.items():
        target = output_root / ticker / definition["document"]
        reused = target.exists()
        raw = target.read_bytes() if reused else client.filing_attachment(definition["cik"], definition["accession"], definition["document"], max_bytes=12 * 1024 * 1024)
        text = _text(raw)
        if any(value not in text for value in definition["required"]):
            raise RuntimeError(f"{ticker} event identity or terms changed")
        digest = hashlib.sha256(raw).hexdigest()
        receipt = {"schema_version": "FINSIGHT-BATCH-33-EVENT-SOURCE-1", "valuation_date": "2026-08-14", "ticker": ticker, "accession": definition["accession"], "filed": definition["filed"], "report_date": definition["report_date"], "form": definition["form"], "document": definition["document"], "url": sec_archive_url(definition["cik"], definition["accession"], definition["document"]), "document_sha256": digest, "reported_terms": definition["reported_terms"], "treatment": definition["treatment"]}
        _immutable(target, raw)
        _immutable(output_root / ticker / "source-receipt.json", (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
        cases.append({"ticker": ticker, "accession": definition["accession"], "reused": reused, "document_sha256": digest})
    return {"attempted": 4, "captured": 4, "cases": cases, "serving_artifacts_changed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--user-agent", required=True)
    print(json.dumps(capture(**vars(parser.parse_args())), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
