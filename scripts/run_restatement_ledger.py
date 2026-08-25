#!/usr/bin/env python3
"""Build deterministic point-in-time restatement ledgers from frozen Companyfacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.restatement_ledger import build_restatement_ledger
from app.us_valuation.sec_client import normalize_cik, sec_archive_url


def _fact_candidates(
    companyfacts: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
    submissions: Mapping[str, Any],
    *,
    cik: str,
) -> list[dict[str, Any]]:
    filings = {
        item.get("accession"): item
        for item in source_manifest.get("eligible_filings", [])
        if isinstance(item, Mapping)
    }
    recent = submissions.get("filings", {}).get("recent", {})
    submission_rows: dict[str, dict[str, Any]] = {}
    accessions = recent.get("accessionNumber", [])
    if isinstance(accessions, list):
        for index, accession in enumerate(accessions):
            if isinstance(accession, str):
                submission_rows[accession] = {
                    key: values[index]
                    for key, values in recent.items()
                    if isinstance(values, list) and index < len(values)
                }
    candidates: list[dict[str, Any]] = []
    for namespace, concepts in companyfacts.get("facts", {}).items():
        if not isinstance(concepts, Mapping):
            continue
        prefix = "us-gaap" if namespace == "us-gaap" else str(namespace)
        for concept, payload in concepts.items():
            if not isinstance(payload, Mapping):
                continue
            for unit, rows in payload.get("units", {}).items():
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if not isinstance(row, Mapping):
                        continue
                    accession = row.get("accn")
                    filed = row.get("filed")
                    period_end = row.get("end")
                    value = row.get("val")
                    if not all(isinstance(item, str) and item for item in (accession, filed, period_end)):
                        continue
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        continue
                    filing = filings.get(accession)
                    if not isinstance(filing, Mapping):
                        continue
                    primary = filing.get("primary_document") if isinstance(filing, Mapping) else None
                    source_url = (
                        sec_archive_url(cik, accession, primary)
                        if isinstance(primary, str) and primary
                        else f"https://data.sec.gov/api/xbrl/companyfacts/CIK{normalize_cik(cik)}.json"
                    )
                    candidates.append(
                        {
                            "value": value,
                            "tag": f"{prefix}:{concept}",
                            "unit": unit,
                            "period_start": row.get("start"),
                            "period_end": period_end,
                            "dimensions": None,
                            "accession": accession,
                            "filed_date": filed,
                            "source_url": source_url,
                            "entity_identifier": normalize_cik(cik),
                            "form": submission_rows.get(accession, {}).get("form") or filing.get("form"),
                            "report_date": submission_rows.get(accession, {}).get("reportDate"),
                        }
                    )
    return candidates


def run(*, source_root: Path, valuation_date: str) -> dict[str, Any]:
    issuers: list[dict[str, Any]] = []
    for packet in sorted(path for path in source_root.iterdir() if path.is_dir()):
        companyfacts_path = packet / "companyfacts.json"
        manifest_path = packet / "source-manifest.json"
        submissions_path = packet / "submissions.json"
        if not all(path.is_file() for path in (companyfacts_path, manifest_path, submissions_path)):
            continue
        companyfacts = json.loads(companyfacts_path.read_text(encoding="utf-8"))
        source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        submissions = json.loads(submissions_path.read_text(encoding="utf-8"))
        cik = normalize_cik(submissions.get("cik", ""))
        candidates = _fact_candidates(
            companyfacts, source_manifest, submissions, cik=cik
        )
        ledger = build_restatement_ledger(candidates, valuation_date=valuation_date)
        confirmed = sum(link.confirmed_restatement for link in ledger.links)
        issuers.append(
            {
                "ticker": packet.name.upper(),
                "cik": cik,
                "candidate_count": len(candidates),
                "selected_count": len(ledger.selected),
                "future_candidate_count": len(ledger.future_candidates),
                "value_change_link_count": len(ledger.links),
                "confirmed_restatement_link_count": confirmed,
                "links": [
                    {
                        **link.__dict__,
                    }
                    for link in ledger.links
                ],
            }
        )
    return {
        "schema_version": "FINSIGHT-RESTATEMENT-LEDGER-1",
        "valuation_date": valuation_date,
        "issuer_count": len(issuers),
        "candidate_count": sum(item["candidate_count"] for item in issuers),
        "selected_count": sum(item["selected_count"] for item in issuers),
        "future_candidate_count": sum(item["future_candidate_count"] for item in issuers),
        "value_change_link_count": sum(item["value_change_link_count"] for item in issuers),
        "confirmed_restatement_link_count": sum(
            item["confirmed_restatement_link_count"] for item in issuers
        ),
        "issuers": issuers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--valuation-date", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(source_root=args.source_root, valuation_date=args.valuation_date)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output.exists() and args.output.read_text(encoding="utf-8") != encoded:
        raise FileExistsError("refusing to overwrite another restatement ledger")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
