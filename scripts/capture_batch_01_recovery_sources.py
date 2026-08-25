#!/usr/bin/env python3
"""Capture the minimum immutable source evidence for Batch 01 recovery."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.batch_01 import BATCH_01_VALUATION_DATE


TARGET_FILINGS = (
    {
        "output_key": "NEE-Q2",
        "ticker": "NEE",
        "cik": "0000753308",
        "accession": "0000753308-26-000060",
        "form": "10-Q",
        "filed": "2026-07-24",
        "period_end": "2026-06-30",
        "primary_document": "nee-20260630.htm",
    },
    {
        "output_key": "NEE-FY2025",
        "ticker": "NEE",
        "cik": "0000753308",
        "accession": "0000753308-26-000015",
        "form": "10-K",
        "filed": "2026-02-13",
        "period_end": "2025-12-31",
        "primary_document": "nee-20251231.htm",
    },
    {
        "output_key": "DELL-FY2026",
        "ticker": "DELL",
        "cik": "0001571996",
        "accession": "0001571996-26-000008",
        "form": "10-K",
        "filed": "2026-03-16",
        "period_end": "2026-01-30",
        "primary_document": "dell-20260130.htm",
    },
)
PEER = {"ticker": "STX", "cik": "0001137789", "issuer_name": "Seagate Technology Holdings plc"}
PROTECTED_ROOTS = (
    ROOT / "backend/app/data/us_valuations",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _immutable_json(path: Path, value: Any) -> None:
    raw = _json_bytes(value)
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite immutable output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent)) / path.name
    try:
        temporary.write_bytes(raw)
        temporary.replace(path)
    finally:
        if temporary.parent.exists():
            temporary.parent.rmdir()


def _validate_paths(
    output_root: Path,
    cache_root: Path,
    protected_roots: tuple[Path, ...] = PROTECTED_ROOTS,
) -> None:
    output = output_root.resolve(strict=False)
    cache = cache_root.resolve(strict=False)
    if output == cache or output.is_relative_to(cache) or cache.is_relative_to(output):
        raise ValueError("output and cache roots must be separate")
    for protected in protected_roots:
        resolved = protected.resolve(strict=False)
        if output.is_relative_to(resolved) or cache.is_relative_to(resolved):
            raise ValueError("recovery output/cache must be outside serving roots")


def _submission_row(submissions: dict[str, Any], accession: str) -> dict[str, Any]:
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    if accession not in accessions:
        raise ValueError(f"target accession is absent from submissions: {accession}")
    index = accessions.index(accession)
    return {
        "accession": accession,
        "form": recent.get("form", [])[index],
        "filed": recent.get("filingDate", [])[index],
        "period_end": recent.get("reportDate", [])[index],
        "primary_document": recent.get("primaryDocument", [])[index],
    }


def capture_recovery_sources(
    *,
    output_root: Path,
    cache_root: Path,
    user_agent: str | None = None,
    refresh: bool = False,
    client: Any = None,
    package_capture: Callable[..., Path] | None = None,
    parse: Callable[..., Any] | None = None,
    protected_serving_roots: tuple[Path, ...] = PROTECTED_ROOTS,
) -> dict[str, Any]:
    """Capture exact recovery filings plus one cutoff-aware Seagate peer packet."""

    _validate_paths(output_root, cache_root, protected_serving_roots)
    before = {str(root): _tree_hash(root) for root in protected_serving_roots}
    if client is None or package_capture is None or parse is None:
        from app.us_valuation.arelle_adapter import parse_structural_filing
        from app.us_valuation.filing_package import cache_structural_filing_package
        from app.us_valuation.sec_client import SecClient

        client = client or SecClient(user_agent=user_agent, cache_dir=cache_root / ".sec-cache")
        package_capture = package_capture or cache_structural_filing_package
        parse = parse or parse_structural_filing

    cases: list[dict[str, Any]] = []
    for target in TARGET_FILINGS:
        if target["filed"] > BATCH_01_VALUATION_DATE:
            raise ValueError("target filing is after the valuation cutoff")
        submissions = client.submissions(target["cik"], refresh=refresh)
        if str(submissions.get("cik", "")).zfill(10) != target["cik"]:
            raise ValueError("target submissions CIK mismatch")
        row = _submission_row(submissions, target["accession"])
        expected = {key: target[key] for key in row}
        if row != expected:
            raise ValueError(f"target filing metadata mismatch for {target['ticker']}")
        entrypoint = package_capture(
            client,
            cik=target["cik"],
            accession=target["accession"],
            primary_document=target["primary_document"],
            form=target["form"],
            output_dir=cache_root / "filings" / target["ticker"],
            refresh=refresh,
        )
        parsed = parse(entrypoint, accession=target["accession"], form=target["form"])
        package_manifest = json.loads((entrypoint.parent / "package-manifest.json").read_text())
        parsed_value = parsed.as_dict() if hasattr(parsed, "as_dict") else parsed
        receipt = {
            "valuation_date": BATCH_01_VALUATION_DATE,
            "ticker": target["ticker"],
            "cik": target["cik"],
            "filing": row,
            "package_generation": package_manifest["generation"],
            "package_manifest_sha256": hashlib.sha256(_json_bytes(package_manifest)).hexdigest(),
            "structural_filing_sha256": hashlib.sha256(_json_bytes(parsed_value)).hexdigest(),
        }
        issuer_root = output_root / target["output_key"]
        _immutable_json(issuer_root / "package-manifest.json", package_manifest)
        _immutable_json(issuer_root / "structural-filing.json", parsed_value)
        _immutable_json(issuer_root / "source-receipt.json", receipt)
        cases.append(
            {
                "ticker": target["ticker"],
                "output_key": target["output_key"],
                "result": "captured",
                "accession": target["accession"],
            }
        )

    submissions = client.submissions(PEER["cik"], refresh=refresh)
    companyfacts = client.companyfacts(PEER["cik"], refresh=refresh)
    if (
        str(submissions.get("cik", "")).zfill(10) != PEER["cik"]
        or str(companyfacts.get("cik", "")).zfill(10) != PEER["cik"]
        or PEER["ticker"] not in submissions.get("tickers", [])
    ):
        raise ValueError("peer source identity mismatch")
    peer_root = output_root / "STX"
    _immutable_json(peer_root / "submissions.json", submissions)
    _immutable_json(peer_root / "companyfacts.json", companyfacts)
    peer_receipt = {
        "valuation_date": BATCH_01_VALUATION_DATE,
        "ticker": PEER["ticker"],
        "cik": PEER["cik"],
        "issuer_name": PEER["issuer_name"],
        "submissions_sha256": hashlib.sha256(_json_bytes(submissions)).hexdigest(),
        "companyfacts_sha256": hashlib.sha256(_json_bytes(companyfacts)).hexdigest(),
        "fact_cutoff_policy": "Only 10-K facts with filed <= valuation_date are eligible.",
    }
    _immutable_json(peer_root / "source-receipt.json", peer_receipt)
    cases.append({"ticker": "STX", "result": "captured", "accession": None})

    after = {str(root): _tree_hash(root) for root in protected_serving_roots}
    if before != after:
        raise RuntimeError("protected serving artifacts changed")
    summary = {
        "valuation_date": BATCH_01_VALUATION_DATE,
        "case_count": len(cases),
        "cases": cases,
        "serving_artifacts_changed": False,
    }
    _immutable_json(output_root / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--cache-root", required=True, type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print(json.dumps(capture_recovery_sources(**vars(args)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
