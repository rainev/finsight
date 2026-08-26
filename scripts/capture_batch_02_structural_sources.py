#!/usr/bin/env python3
"""Capture one cutoff-controlled, parsed SEC filing package per frozen Batch 02 issuer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.batch_02 import BATCH_02_MANIFEST, BATCH_02_VALUATION_DATE
from app.us_valuation.sec_client import normalize_cik

ELIGIBLE_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"})
PROTECTED_ROOTS = tuple(ROOT / path for path in (
    "backend/app/data/us_valuation_catalogs", "frontend/public/data", "frontend/src/research/generated",
))


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode()); digest.update(b"\0")
            digest.update(path.read_bytes()); digest.update(b"\0")
    return digest.hexdigest()


def _inside(candidate: Path, root: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _validate_paths(source_root: Path, output_root: Path, cache_root: Path, roots: tuple[Path, ...] = PROTECTED_ROOTS) -> None:
    source_root, output_root, cache_root = (path.resolve(strict=False) for path in (source_root, output_root, cache_root))
    if not source_root.is_dir():
        raise ValueError("source root must be an existing directory")
    if any(_inside(left, right) or _inside(right, left) for left, right in ((source_root, output_root), (source_root, cache_root), (output_root, cache_root))):
        raise ValueError("source, output, and cache roots must be separate")
    if any(_inside(path, root) for path in (output_root, cache_root) for root in roots):
        raise ValueError("structural output/cache must be outside protected serving roots")


def _immutable_json(path: Path, value: Any) -> None:
    raw = _json_bytes(value)
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite immutable output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent)) / path.name
    try:
        staging.write_bytes(raw); staging.replace(path)
    finally:
        shutil.rmtree(staging.parent, ignore_errors=True)


def _load_controlling_filing(source_root: Path, issuer: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    packet = source_root / issuer.ticker
    manifest_path, submissions_path = packet / "source-manifest.json", packet / "submissions.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "FINSIGHT-BATCH-02-SOURCE-1" or manifest.get("valuation_date") != BATCH_02_VALUATION_DATE:
        raise ValueError(f"{issuer.ticker}: source packet contract mismatch")
    if manifest.get("issuer") != {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}:
        raise ValueError(f"{issuer.ticker}: source packet issuer mismatch")
    declared = manifest.get("packet_payload_sha256", {})
    if not isinstance(declared, dict) or any(_sha256((packet / name).read_bytes()) != digest for name, digest in declared.items()):
        raise ValueError(f"{issuer.ticker}: source packet hash mismatch")
    submissions = json.loads(submissions_path.read_text(encoding="utf-8"))
    if normalize_cik(submissions.get("cik", "")) != issuer.cik or issuer.ticker not in submissions.get("tickers", []):
        raise ValueError(f"{issuer.ticker}: submissions identity mismatch")
    candidates = [row for row in manifest.get("eligible_filings", []) if row.get("form") in ELIGIBLE_FORMS and row.get("filed", "") <= BATCH_02_VALUATION_DATE]
    if not candidates:
        raise ValueError(f"{issuer.ticker}: no pre-cutoff 10-K/Q source filing")
    filing = max(candidates, key=lambda row: (row["filed"], row["accession"]))
    recent = submissions.get("filings", {}).get("recent", {})
    try:
        index = recent["accessionNumber"].index(filing["accession"])
    except (KeyError, ValueError) as error:
        raise ValueError(f"{issuer.ticker}: controlling accession absent from submissions") from error
    for source_name, filing_name in (("form", "form"), ("filingDate", "filed"), ("primaryDocument", "primary_document")):
        if str(recent[source_name][index]) != filing[filing_name]:
            raise ValueError(f"{issuer.ticker}: controlling filing metadata mismatch")
    return filing, manifest


def _dependencies() -> tuple[Callable[..., Any], Callable[..., Any], Callable[..., Any]]:
    from app.us_valuation.arelle_adapter import parse_structural_filing
    from app.us_valuation.filing_package import cache_structural_filing_package
    from app.us_valuation.sec_client import SecClient
    return SecClient, cache_structural_filing_package, parse_structural_filing


def capture_structural_sources(*, source_root: Path, output_root: Path, cache_root: Path, user_agent: str | None = None, refresh: bool = False, client: Any = None, package_capture: Callable[..., Path] | None = None, parse: Callable[..., Any] | None = None, protected_serving_roots: tuple[Path, ...] = PROTECTED_ROOTS) -> dict[str, Any]:
    source_root, output_root, cache_root = Path(source_root), Path(output_root), Path(cache_root)
    _validate_paths(source_root, output_root, cache_root, protected_serving_roots)
    before = {str(root): _tree_hash(root) for root in protected_serving_roots}
    if client is None or package_capture is None or parse is None:
        sec_client, package_capture_default, parse_default = _dependencies()
        client = client or sec_client(user_agent=user_agent, cache_dir=cache_root / ".sec-cache")
        package_capture, parse = package_capture or package_capture_default, parse or parse_default
    cases = []
    for issuer in BATCH_02_MANIFEST:
        filing, source_manifest = _load_controlling_filing(source_root, issuer)
        entrypoint = package_capture(client, cik=issuer.cik, accession=filing["accession"], primary_document=filing["primary_document"], form=filing["form"], output_dir=cache_root / "filings" / issuer.ticker, refresh=refresh)
        parsed = parse(entrypoint, accession=filing["accession"], form=filing["form"])
        parsed_value = parsed.as_dict() if hasattr(parsed, "as_dict") else parsed
        package_manifest = json.loads((entrypoint.parent / "package-manifest.json").read_text(encoding="utf-8"))
        if package_manifest.get("accession") != filing["accession"] or normalize_cik(package_manifest.get("cik", "")) != issuer.cik:
            raise ValueError(f"{issuer.ticker}: captured package identity mismatch")
        receipt = {"schema_version": "FINSIGHT-BATCH-02-STRUCTURAL-SOURCE-1", "valuation_date": BATCH_02_VALUATION_DATE, "ticker": issuer.ticker, "cik": issuer.cik, "filing": filing, "source_packet_manifest_sha256": _sha256(_json_bytes(source_manifest)), "package_manifest_sha256": _sha256(_json_bytes(package_manifest)), "structural_filing_sha256": _sha256(_json_bytes(parsed_value))}
        issuer_root = output_root / issuer.ticker
        _immutable_json(issuer_root / "package-manifest.json", package_manifest)
        _immutable_json(issuer_root / "structural-filing.json", parsed_value)
        _immutable_json(issuer_root / "source-receipt.json", receipt)
        cases.append({"ticker": issuer.ticker, "accession": filing["accession"], "form": filing["form"], "filed": filing["filed"], "result": "parsed", "structural_filing_sha256": receipt["structural_filing_sha256"]})
    after = {str(root): _tree_hash(root) for root in protected_serving_roots}
    if before != after:
        raise RuntimeError("protected serving artifacts changed")
    summary = {"valuation_date": BATCH_02_VALUATION_DATE, "attempted": len(cases), "parsed": len(cases), "failed": 0, "cases": cases, "serving_hash_before": before, "serving_hash_after": after, "serving_artifacts_changed": False}
    _immutable_json(output_root / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path); parser.add_argument("--output-root", required=True, type=Path); parser.add_argument("--cache-root", required=True, type=Path); parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT")); parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args(); print(json.dumps(capture_structural_sources(**vars(args)), sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
