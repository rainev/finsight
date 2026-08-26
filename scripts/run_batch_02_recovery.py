#!/usr/bin/env python3
"""Apply one controlled recovery attempt to Batch 02's six withheld issuers."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_02 import BATCH_02_MANIFEST, BATCH_02_TICKERS
from app.us_valuation.batch_02_recovery import (
    PUBLIC_METHOD_REFERENCES,
    RECOVERY_DECISIONS,
    RECOVERY_TICKERS,
    RECOVERY_VERSION,
)


PROTECTED_ROOTS = (
    ROOT / "backend/app/data/us_valuation_catalogs",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
            digest.update(b"\n")
    return digest.hexdigest()


def _immutable(path: Path, raw: bytes) -> None:
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite immutable recovery output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent))
    try:
        candidate = staging / path.name
        candidate.write_bytes(raw)
        candidate.replace(path)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _validate_roots(
    initial_root: Path,
    source_root: Path,
    structural_root: Path,
    output_root: Path,
) -> None:
    inputs = tuple(
        path.resolve(strict=True)
        for path in (initial_root, source_root, structural_root)
    )
    target = output_root.resolve(strict=False)
    if any(not path.is_dir() for path in inputs):
        raise ValueError("recovery input roots must be directories")
    if any(target == path or target.is_relative_to(path) or path.is_relative_to(target) for path in inputs):
        raise ValueError("recovery output must be separate from every input root")
    if any(target.is_relative_to(root.resolve()) for root in PROTECTED_ROOTS):
        raise ValueError("recovery output must be outside serving roots")


def _recovery_source_identity(
    source_root: Path,
    structural_root: Path,
    issuer: Any,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    packet = source_root / issuer.ticker
    source_manifest = json.loads(
        (packet / "source-manifest.json").read_text()
    )
    submissions = json.loads((packet / "submissions.json").read_text())
    structural = json.loads(
        (structural_root / issuer.ticker / "structural-filing.json").read_text()
    )
    if source_manifest.get("valuation_date") != "2026-08-14":
        raise ValueError(f"{issuer.ticker}: recovery valuation date mismatch")
    eligible = source_manifest.get("eligible_filings", [])
    if not eligible or any(row.get("filed", "") > "2026-08-14" for row in eligible):
        raise ValueError(f"{issuer.ticker}: recovery filing ledger violates cutoff")
    latest = max(eligible, key=lambda row: (row["filed"], row["accession"]))
    recent = submissions.get("filings", {}).get("recent", {})
    try:
        index = recent["accessionNumber"].index(latest["accession"])
    except (KeyError, ValueError) as error:
        raise ValueError(
            f"{issuer.ticker}: recovery accession is absent from submissions"
        ) from error
    report_date = recent.get("reportDate", [])[index]
    if (
        source_manifest["issuer"]["cik"] != issuer.cik
        or str(submissions.get("cik", "")).zfill(10) != issuer.cik
        or structural["source_accession"] != latest["accession"]
        or recent["filingDate"][index] != latest["filed"]
        or recent["form"][index] != latest["form"]
        or recent["primaryDocument"][index] != latest["primary_document"]
        or not isinstance(report_date, str)
        or not report_date
    ):
        raise ValueError(f"{issuer.ticker}: recovery source identity mismatch")
    return latest, report_date, structural


def run_recovery(
    *,
    initial_root: Path,
    source_root: Path,
    structural_root: Path,
    output_root: Path,
    sanitize: Callable[[dict[str, Any]], dict[str, Any]] = sanitize_public_artifact,
) -> dict[str, Any]:
    initial_root = Path(initial_root)
    source_root = Path(source_root)
    structural_root = Path(structural_root)
    output_root = Path(output_root)
    _validate_roots(initial_root, source_root, structural_root, output_root)
    report = json.loads((initial_root / "batch-report.json").read_text())
    if (
        report.get("denominator_tickers") != list(BATCH_02_TICKERS)
        or report.get("numeric_count") != 4
        or report.get("withheld_count") != 6
        or tuple(
            case["ticker"]
            for case in report.get("cases", [])
            if case.get("outcome") == "withheld"
        )
        != RECOVERY_TICKERS
    ):
        raise ValueError("initial Batch 02 report does not match the recovery contract")
    before = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    decisions = {decision.ticker: decision for decision in RECOVERY_DECISIONS}
    cases = []
    for issuer in BATCH_02_MANIFEST:
        private_path = initial_root / "generated" / issuer.ticker / "valuation-private.json"
        public_path = initial_root / "staged-public" / f"{issuer.ticker}.json"
        private = json.loads(private_path.read_text())
        public = json.loads(public_path.read_text())
        if sanitize(public) != public:
            raise ValueError(f"{issuer.ticker}: initial public artifact is not canonical")
        latest, report_date, structural = _recovery_source_identity(
            source_root, structural_root, issuer
        )
        if issuer.ticker in decisions:
            decision = decisions[issuer.ticker]
            private["recovery_attempt"] = {
                **asdict(decision),
                "attempt_number": 1,
                "method_references": PUBLIC_METHOD_REFERENCES,
                "source_accession": latest["accession"],
                "source_filed_date": latest["filed"],
                "source_period_end": report_date,
                "public_artifact_changed": False,
            }
            cases.append(
                {
                    "ticker": issuer.ticker,
                    "attempted": True,
                    "recovered_numeric": False,
                    "final_outcome": "withheld",
                    "recovery_model": decision.recovery_model,
                    "hard_blockers": list(decision.hard_blockers),
                    "next_eligible_trigger": decision.next_eligible_trigger,
                }
            )
        else:
            private["recovery_attempt"] = None
        _immutable(
            output_root / "generated" / issuer.ticker / "valuation-private.json",
            _json_bytes(private),
        )
        _immutable(output_root / "staged-public" / public_path.name, public_path.read_bytes())
    after = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    if before != after:
        raise RuntimeError("protected serving artifacts changed")
    summary = {
        "schema_version": "FINSIGHT-BATCH-02-RECOVERY-REPORT-1",
        "batch": 2,
        "recovery_version": RECOVERY_VERSION,
        "valuation_date": "2026-08-14",
        "recovery_attempted_count": 6,
        "recovered_numeric_count": 0,
        "still_withheld_count": 6,
        "final_batch_numeric_count": 4,
        "final_batch_withheld_count": 6,
        "invalid_input_count": 0,
        "register_addition_count": 6,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "serving_artifacts_changed": False,
        "cases": cases,
    }
    _immutable(output_root / "recovery-report.json", _json_bytes(summary))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-root", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--structural-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    summary = run_recovery(**vars(args))
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "recovery_attempted_count",
                    "recovered_numeric_count",
                    "still_withheld_count",
                    "final_batch_numeric_count",
                    "final_batch_withheld_count",
                    "serving_artifacts_changed",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
