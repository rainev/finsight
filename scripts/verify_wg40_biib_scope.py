#!/usr/bin/env python3
"""Build the cached WG40 BIIB legal/acquisition/bridge evidence receipt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.catalog import canonical_json_bytes, sha256_bytes
from app.us_valuation.refresh_biib_scope import assess_biib_scope, biib_scope_policy
from app.us_valuation.refresh_job import atomic
from app.us_valuation.refresh_pharma_bridge import bind_pharma_bridge, pharma_bridge_policy
from app.us_valuation.refresh_pharma_claims import pharma_claim_policy, select_pharma_claim


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structural", type=Path,
        default=ROOT / "output/batch-14-structural-sources-20260829/BIIB/structural-filing.json")
    parser.add_argument("--cutoff", default="2026-08-14")
    parser.add_argument("--output", type=Path,
        default=ROOT / "output/us-refresh-runtime/biib-scope/BIIB.json")
    args = parser.parse_args()
    raw = args.structural.read_bytes()
    structural = json.loads(raw)
    accession = structural["source_accession"]
    period = structural.get("report_date") or structural["period_end"]
    filed = structural["filed_date"]
    controlling = {"accessionNumber": accession, "reportDate": period, "filingDate": filed}
    cik = str(structural["facts"][0]["entity_identifier"]).zfill(10)
    scope = assess_biib_scope(biib_scope_policy(), structural, controlling, cik, args.cutoff)
    bridge_records, bridge_proof = bind_pharma_bridge(
        pharma_bridge_policy("BIIB"), structural, accession=accession, period=period)
    acquisition = select_pharma_claim(
        pharma_claim_policy("BIIB"), structural, controlling, cik, args.cutoff)
    receipt = {
        "schema_version": "FINSIGHT-BIIB-WG40-EVIDENCE-1",
        "ticker": "BIIB", "cik": cik, "cutoff": args.cutoff,
        "source": {"path": str(args.structural), "sha256": sha256_bytes(raw),
                   "accession": accession, "period_end": period, "filed_date": filed},
        "legal_operating_scope": scope,
        "current_bridge": {
            "records": [record.as_dict() for record in bridge_records],
            "proof": bridge_proof,
        },
        "acquisition_claim": acquisition,
        "numeric_successor_issued": False,
        "production_activated": False,
    }
    payload = canonical_json_bytes(receipt)
    receipt["receipt_sha256"] = sha256_bytes(payload)
    atomic(args.output, canonical_json_bytes(receipt), immutable=False)
    print(json.dumps({"output": str(args.output), "receipt_sha256": receipt["receipt_sha256"],
                      "status": scope["status"], "review_reasons": scope["review_reasons"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
