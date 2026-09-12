#!/usr/bin/env python3
"""Capture Batch 50 cutoff-event filings and exhibits."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_50 import BATCH_50_MANIFEST, BATCH_50_VALUATION_DATE
from app.us_valuation.sec_client import SecClient
from capture_batch_37_event_sources import _immutable, _json

EVENT_FORMS = {"8-K", "8-K/A", "424B5"}


def capture_events(*, source_root: Path, output_root: Path, user_agent: str | None = None) -> dict:
    source_root, output_root = Path(source_root).resolve(), Path(output_root).resolve()
    client = SecClient(user_agent=user_agent, cache_dir=output_root / ".cache")
    cases = []
    for issuer in BATCH_50_MANIFEST:
        recent = json.loads((source_root / issuer.ticker / "submissions.json").read_text())["filings"]["recent"]
        entries = []
        for index, filed in enumerate(recent["filingDate"]):
            form = recent["form"][index]
            if not ("2026-06-30" <= filed <= BATCH_50_VALUATION_DATE and form in EVENT_FORMS):
                continue
            accession, primary = recent["accessionNumber"][index], recent["primaryDocument"][index]
            raw = client.filing_attachment(issuer.cik, accession, primary)
            documents = [(primary, raw)]
            for link in sorted(set(re.findall(r'href=["\x27]([^"\x27]+)', raw.decode(errors="ignore"), re.I))):
                low = link.lower()
                if "/" in link or not low.endswith((".htm", ".html")) or not any(token in low for token in ("99", "exhibit", "release", "earnings", "supp", "presentation", "ex10", "ex4", "livemaster")):
                    continue
                documents.append((link, client.filing_attachment(issuer.cik, accession, link)))
            captured = []
            for name, data in documents[:24]:
                target = output_root / issuer.ticker / accession / name
                _immutable(target, data)
                captured.append({"path": str(target.relative_to(ROOT)), "sha256": hashlib.sha256(data).hexdigest()})
            entries.append({"accession": accession, "filed": filed, "report_date": recent["reportDate"][index], "form": form, "items": recent["items"][index], "primary_document": primary, "documents": captured})
        inventory = _json(entries)
        _immutable(output_root / issuer.ticker / "inventory.json", inventory)
        cases.append({"ticker": issuer.ticker, "filing_count": len(entries), "document_count": sum(len(row["documents"]) for row in entries), "inventory_sha256": hashlib.sha256(inventory).hexdigest()})
    summary = {"schema_version": "FINSIGHT-BATCH-50-EVENT-SCREEN-1", "valuation_date": BATCH_50_VALUATION_DATE, "attempted": 10, "cases": cases, "serving_artifacts_changed": False}
    _immutable(output_root / "summary.json", _json(summary))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    print(json.dumps(capture_events(**vars(parser.parse_args())), sort_keys=True))


if __name__ == "__main__":
    main()
