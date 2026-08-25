#!/usr/bin/env python3
"""Capture one cutoff-controlled parsed SEC filing per Batch 03 issuer."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.batch_03 import BATCH_03_MANIFEST, BATCH_03_VALUATION_DATE
from app.us_valuation.sec_client import normalize_cik
from capture_batch_02_structural_sources import (
    ELIGIBLE_FORMS,
    PROTECTED_ROOTS,
    _dependencies,
    _immutable_json,
    _json_bytes,
    _sha256,
    _tree_hash,
    _validate_paths,
)


def _load_controlling_filing(
    source_root: Path, issuer: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    packet = source_root / issuer.ticker
    manifest = json.loads((packet / "source-manifest.json").read_text())
    if (
        manifest.get("schema_version") != "FINSIGHT-BATCH-03-SOURCE-1"
        or manifest.get("valuation_date") != BATCH_03_VALUATION_DATE
        or manifest.get("issuer")
        != {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}
    ):
        raise ValueError(f"{issuer.ticker}: Batch 03 source packet mismatch")
    declared = manifest.get("packet_payload_sha256", {})
    if not isinstance(declared, dict) or any(
        _sha256((packet / name).read_bytes()) != digest
        for name, digest in declared.items()
    ):
        raise ValueError(f"{issuer.ticker}: source packet hash mismatch")
    submissions = json.loads((packet / "submissions.json").read_text())
    if (
        normalize_cik(submissions.get("cik", "")) != issuer.cik
        or issuer.ticker not in submissions.get("tickers", [])
    ):
        raise ValueError(f"{issuer.ticker}: submissions identity mismatch")
    candidates = [
        row for row in manifest.get("eligible_filings", [])
        if row.get("form") in ELIGIBLE_FORMS
        and row.get("filed", "") <= BATCH_03_VALUATION_DATE
    ]
    if not candidates:
        raise ValueError(f"{issuer.ticker}: no cutoff-eligible 10-K/Q")
    filing = max(candidates, key=lambda row: (row["filed"], row["accession"]))
    return filing, manifest


def capture_structural_sources(
    *,
    source_root: Path,
    output_root: Path,
    cache_root: Path,
    user_agent: str | None = None,
    refresh: bool = False,
    client: Any = None,
    package_capture: Callable[..., Path] | None = None,
    parse: Callable[..., Any] | None = None,
    protected_serving_roots: tuple[Path, ...] = PROTECTED_ROOTS,
) -> dict[str, Any]:
    source_root, output_root, cache_root = map(
        Path, (source_root, output_root, cache_root)
    )
    _validate_paths(source_root, output_root, cache_root, protected_serving_roots)
    before = {str(root): _tree_hash(root) for root in protected_serving_roots}
    if client is None or package_capture is None or parse is None:
        sec_client, package_capture_default, parse_default = _dependencies()
        client = client or sec_client(user_agent=user_agent, cache_dir=cache_root / ".sec-cache")
        package_capture = package_capture or package_capture_default
        parse = parse or parse_default
    cases = []
    for issuer in BATCH_03_MANIFEST:
        filing, source_manifest = _load_controlling_filing(source_root, issuer)
        entrypoint = package_capture(
            client,
            cik=issuer.cik,
            accession=filing["accession"],
            primary_document=filing["primary_document"],
            form=filing["form"],
            output_dir=cache_root / "filings" / issuer.ticker,
            refresh=refresh,
        )
        parsed = parse(entrypoint, accession=filing["accession"], form=filing["form"])
        parsed_value = parsed.as_dict() if hasattr(parsed, "as_dict") else parsed
        package_manifest = json.loads((entrypoint.parent / "package-manifest.json").read_text())
        if (
            package_manifest.get("accession") != filing["accession"]
            or normalize_cik(package_manifest.get("cik", "")) != issuer.cik
        ):
            raise ValueError(f"{issuer.ticker}: structural package identity mismatch")
        receipt = {
            "schema_version": "FINSIGHT-BATCH-03-STRUCTURAL-SOURCE-1",
            "valuation_date": BATCH_03_VALUATION_DATE,
            "ticker": issuer.ticker,
            "cik": issuer.cik,
            "filing": filing,
            "source_packet_manifest_sha256": _sha256(_json_bytes(source_manifest)),
            "package_manifest_sha256": _sha256(_json_bytes(package_manifest)),
            "structural_filing_sha256": _sha256(_json_bytes(parsed_value)),
        }
        issuer_root = output_root / issuer.ticker
        _immutable_json(issuer_root / "package-manifest.json", package_manifest)
        _immutable_json(issuer_root / "structural-filing.json", parsed_value)
        _immutable_json(issuer_root / "source-receipt.json", receipt)
        cases.append({
            "ticker": issuer.ticker,
            "accession": filing["accession"],
            "form": filing["form"],
            "filed": filing["filed"],
            "result": "parsed",
            "structural_filing_sha256": receipt["structural_filing_sha256"],
        })
    after = {str(root): _tree_hash(root) for root in protected_serving_roots}
    if before != after:
        raise RuntimeError("protected serving artifacts changed")
    summary = {
        "valuation_date": BATCH_03_VALUATION_DATE,
        "attempted": len(cases),
        "parsed": len(cases),
        "failed": 0,
        "cases": cases,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "serving_artifacts_changed": False,
    }
    _immutable_json(output_root / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--cache-root", required=True, type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--refresh", action="store_true")
    result = capture_structural_sources(**vars(parser.parse_args()))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

