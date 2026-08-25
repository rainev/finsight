#!/usr/bin/env python3
"""Run offline DQC diagnostics for every controlling filing in an ingestion receipt."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_dqc_diagnostics import run_dqc


YEAR = re.compile(r"fasb\.org/us-gaap/(20\d{2})")


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _package_index(roots: list[Path]) -> dict[tuple[str, str], tuple[Path, int]]:
    result = {}
    for root in roots:
        for path in sorted(root.rglob("package-manifest.json")):
            manifest = _read(path)
            namespaces = {
                str(item.get("taxonomy_namespace") or "")
                for item in manifest.get("files", [])
            }
            years = {
                int(match.group(1))
                for namespace in namespaces
                if (match := YEAR.search(namespace)) is not None
            }
            if len(years) != 1:
                continue
            entrypoint = path.parent / str(manifest.get("entrypoint_local_path") or "")
            if entrypoint.is_file():
                result.setdefault(
                    (str(manifest.get("cik")), str(manifest.get("accession"))),
                    (entrypoint, next(iter(years))),
                )
    return result


def run(
    *,
    ingestion_receipt: Path,
    package_roots: list[Path],
    runtime_root: Path,
    output_root: Path,
    workers: int,
) -> dict[str, Any]:
    receipt = _read(ingestion_receipt)
    packages = _package_index(package_roots)

    def evaluate(issuer: dict[str, Any]) -> dict[str, Any]:
        ticker = str(issuer["ticker"])
        filing = issuer["controlling_filing"]
        package = packages.get((str(issuer["cik"]), str(filing["accession"])))
        if package is None:
            return {
                "ticker": ticker,
                "status": "unavailable",
                "reason_codes": ["DQC_TAXONOMY_OR_PACKAGE_UNAVAILABLE"],
                "diagnostics": [],
                "value": None,
                "can_create_value": False,
            }
        entrypoint, year = package
        try:
            result = run_dqc(
                entrypoint=entrypoint,
                taxonomy_year=year,
                runtime_root=runtime_root,
            )
        except Exception as error:
            result = {
                "status": "unavailable",
                "reason_codes": ["DQC_EXECUTION_FAILURE", type(error).__name__],
                "diagnostics": [],
                "value": None,
                "can_create_value": False,
                "failure": str(error),
            }
        return {"ticker": ticker, **result}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        rows = list(executor.map(evaluate, receipt["issuers"]))
    rows.sort(key=lambda item: item["ticker"])
    for row in rows:
        path = output_root / "filings" / f"{row['ticker']}.json"
        raw = _canonical(row)
        if path.exists() and path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite DQC result {row['ticker']}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    statuses = Counter(str(item["status"]) for item in rows)
    summary = {
        "schema_version": "FINSIGHT-DQC-BATCH-1",
        "issuer_count": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "diagnostic_count": sum(len(item.get("diagnostics", [])) for item in rows),
        "dqc_error_count": sum(
            item.get("severity") == "error"
            for row in rows for item in row.get("diagnostics", [])
        ),
        "rule_execution_count": sum(
            int(item.get("rule_stats_entry_count", 0)) for item in rows
        ),
        "applicable_rule_count": sum(
            int(item.get("applicable_rule_count", 0)) for item in rows
        ),
        "can_create_value_count": sum(item.get("can_create_value") is True for item in rows),
        "ingestion_receipt_sha256": hashlib.sha256(ingestion_receipt.read_bytes()).hexdigest(),
        "issuers": rows,
    }
    path = output_root / "dqc-batch-report.json"
    raw = _canonical(summary)
    if path.exists() and path.read_bytes() != raw:
        raise FileExistsError("refusing to overwrite DQC batch report")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ingestion-receipt", required=True, type=Path)
    parser.add_argument("--package-root", action="append", required=True, type=Path)
    parser.add_argument("--runtime-root", default=ROOT / "output/dqc-runtime", type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    result = run(
        ingestion_receipt=args.ingestion_receipt,
        package_roots=args.package_root,
        runtime_root=args.runtime_root,
        output_root=args.output_root,
        workers=args.workers,
    )
    print(json.dumps({
        "issuer_count": result["issuer_count"],
        "status_counts": result["status_counts"],
        "diagnostic_count": result["diagnostic_count"],
        "dqc_error_count": result["dqc_error_count"],
        "rule_execution_count": result["rule_execution_count"],
        "applicable_rule_count": result["applicable_rule_count"],
        "can_create_value_count": result["can_create_value_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
