#!/usr/bin/env python3
"""Capture the cutoff-safe official DOJ sources used by Batch 15 recovery."""
from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from pypdf import PdfReader


ANNOUNCEMENT_URL = "https://www.justice.gov/opa/pr/labcorp-agrees-pay-145m-resolve-false-claims-act-allegations"
AGREEMENT_URL = "https://www.justice.gov/usao-ma/media/1452676/dl"
USER_AGENT = "FinSight valuation research cv.ventures7@gmail.com"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _immutable(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"immutable source differs: {path}")
        return
    path.write_bytes(data)


def _fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        final_url = response.geturl()
        if not final_url.startswith("https://www.justice.gov/"):
            raise RuntimeError(f"unexpected redirect: {final_url}")
        return response.read()


def _validate(announcement: bytes, agreement: bytes) -> None:
    html = announcement.decode("utf-8", errors="replace")
    if "Labcorp Agrees to Pay $14.5M" not in html or "July 15, 2026" not in html:
        raise RuntimeError("DOJ announcement identity or date changed")
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(agreement)).pages)
    required = ("$14,500,000", "4.5 percent per annum", "May 14, 2025", "$8,286,000")
    if any(value not in text for value in required):
        raise RuntimeError("DOJ agreement terms changed")


def capture(output_root: Path) -> dict:
    output_root = Path(output_root)
    if any(part in {"backend", "frontend"} for part in output_root.parts):
        raise ValueError("recovery evidence must remain outside serving roots")
    announcement_path = output_root / "LH" / "doj-announcement.html"
    agreement_path = output_root / "LH" / "doj-settlement-agreement.pdf"
    receipt_path = output_root / "LH" / "source-receipt.json"
    reused = announcement_path.exists() and agreement_path.exists() and receipt_path.exists()
    if reused:
        announcement = announcement_path.read_bytes()
        agreement = agreement_path.read_bytes()
    else:
        announcement = _fetch(ANNOUNCEMENT_URL)
        agreement = _fetch(AGREEMENT_URL)
    _validate(announcement, agreement)
    receipt = {
        "schema_version": "FINSIGHT-BATCH-15-RECOVERY-SOURCE-1",
        "valuation_date": "2026-08-14",
        "ticker": "LH",
        "announcement": {"url": ANNOUNCEMENT_URL, "date": "2026-07-15", "sha256": _sha(announcement)},
        "agreement": {"url": AGREEMENT_URL, "effective_date": "2026-07-15", "sha256": _sha(agreement)},
        "reported_terms": {
            "principal_usd": 14_500_000,
            "annual_interest_rate": 0.045,
            "interest_start": "2025-05-14",
            "restitution_usd": 8_286_000,
            "payment_due_days_after_effective_date": 30,
        },
    }
    raw_receipt = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    _immutable(announcement_path, announcement)
    _immutable(agreement_path, agreement)
    _immutable(receipt_path, raw_receipt)
    return {"ticker": "LH", "reused": reused, "announcement_sha256": receipt["announcement"]["sha256"], "agreement_sha256": receipt["agreement"]["sha256"], "serving_artifacts_changed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    print(json.dumps(capture(parser.parse_args().output_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
