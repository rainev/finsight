#!/usr/bin/env python3
"""Capture Batch 39 cutoff-event filings for later source review."""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_39 import BATCH_39_MANIFEST
from app.us_valuation.sec_client import SecClient
from capture_batch_37_event_sources import _immutable, _json


def run():
    output = ROOT / "output/batch-39-event-review-20260907"
    client = SecClient(user_agent="FinSight research cv.ventures7@gmail.com", cache_dir=output / ".cache")
    for issuer in BATCH_39_MANIFEST:
        recent = json.loads((ROOT / "output/batch-39-sec-source-packets-20260907" / issuer.ticker / "submissions.json").read_text())["filings"]["recent"]
        entries = []
        for index, filed in enumerate(recent["filingDate"]):
            if not ("2026-06-30" <= filed <= "2026-08-14" and recent["form"][index] in ("8-K", "8-K/A", "424B5")):
                continue
            accession = recent["accessionNumber"][index]
            name = recent["primaryDocument"][index]
            raw = client.filing_attachment(issuer.cik, accession, name)
            documents = [(name, raw)]
            for link in sorted(set(re.findall(r"href=[\"']([^\"']+)", raw.decode(errors="ignore"), re.I))):
                if "/" not in link and link.endswith((".htm", ".html")) and any(value in link.lower() for value in ("99", "exhibit", "release")):
                    documents.append((link, client.filing_attachment(issuer.cik, accession, link)))
            captured = []
            for filename, data in documents:
                path = output / issuer.ticker / accession / filename
                _immutable(path, data)
                captured.append({"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(data).hexdigest()})
            entries.append({"accession": accession, "filed": filed, "form": recent["form"][index], "items": recent["items"][index], "documents": captured})
        _immutable(output / issuer.ticker / "inventory.json", _json(entries))
        print(issuer.ticker, len(entries), flush=True)


if __name__ == "__main__":
    run()
