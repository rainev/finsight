#!/usr/bin/env python3
"""Produce non-serving structural diagnostics for Batch 01 source packets."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping


_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
from app.us_valuation.batch_01 import BATCH_01_MANIFEST, BATCH_01_VALUATION_DATE


_OPERATING_LANES = frozenset(
    {
        "mature_operating_fcff",
        "intangible_investment_fcff",
        "growth_operating_fcff",
        "normalized_cyclical_fcff",
        "captive_finance_sotp",
    }
)
_DEFAULT_PROTECTED = (
    _ROOT / "backend/app/data/us_valuation_catalogs",
    _ROOT / "frontend/public/data",
    _ROOT / "frontend/src/research/generated",
)


def _encoded(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _immutable(path: Path, payload: object) -> None:
    raw = _encoded(payload)
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite immutable output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent)) / path.name
    try:
        staging.write_bytes(raw)
        staging.replace(path)
    finally:
        shutil.rmtree(staging.parent, ignore_errors=True)


def _load_packet(
    packet: Path, issuer: Any
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = json.loads((packet / "source-manifest.json").read_text())
    if manifest.get("valuation_date") != BATCH_01_VALUATION_DATE:
        raise ValueError("packet valuation date mismatch")
    identity = manifest.get("issuer", {})
    if identity.get("ticker") != issuer.ticker or identity.get("cik") != issuer.cik:
        raise ValueError("packet issuer identity mismatch")
    if any(
        row.get("filed", "") > BATCH_01_VALUATION_DATE
        for row in manifest.get("eligible_filings", [])
    ):
        raise ValueError("future filing present in eligible ledger")
    declared_hashes = manifest.get("packet_payload_sha256")
    if not isinstance(declared_hashes, dict) or not declared_hashes:
        raise ValueError("packet payload hashes are missing")
    for filename, expected in declared_hashes.items():
        path = packet / filename
        if (
            not isinstance(filename, str)
            or not isinstance(expected, str)
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise ValueError(f"packet payload hash mismatch: {filename}")
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    if (
        str(submissions.get("cik", "")).zfill(10) != issuer.cik
        or str(facts.get("cik", "")).zfill(10) != issuer.cik
    ):
        raise ValueError("packet source CIK identity mismatch")
    return manifest, submissions, facts


def _dependencies() -> tuple[
    Callable[..., Any],
    Callable[..., Any],
    Callable[..., Any],
    Callable[..., Any],
    Callable[..., Any],
    Callable[..., Any],
]:
    from app.us_valuation.pipeline import build_us_valuation
    from app.us_valuation.structural_shadow import evaluate_shadow_case, shadow_requests_from_artifact
    from app.us_valuation.filing_package import cache_structural_filing_package
    from app.us_valuation.arelle_adapter import parse_structural_filing
    from app.us_valuation.sec_client import SecClient
    return (
        build_us_valuation,
        shadow_requests_from_artifact,
        cache_structural_filing_package,
        parse_structural_filing,
        evaluate_shadow_case,
        SecClient,
    )


def run_structural_shadow(
    *,
    source_root: Path,
    output_root: Path,
    cache_root: Path,
    user_agent: str | None = None,
    refresh: bool = False,
    client: Any = None,
    protected_serving_roots: tuple[Path, ...] = _DEFAULT_PROTECTED,
    build: Callable[..., Any] | None = None,
    shadow_requests: Callable[..., Any] | None = None,
    cache_package: Callable[..., Any] | None = None,
    parse: Callable[..., Any] | None = None,
    evaluate: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    source_root, output_root, cache_root = Path(source_root), Path(output_root), Path(cache_root)
    if not source_root.is_dir():
        raise ValueError("source root must be an existing directory")
    if (
        output_root.resolve().is_relative_to(source_root.resolve())
        or cache_root.resolve().is_relative_to(source_root.resolve())
        or output_root.resolve().is_relative_to(cache_root.resolve())
        or cache_root.resolve().is_relative_to(output_root.resolve())
    ):
        raise ValueError("source, structural cache, and output roots must be separate")
    if any(
        output_root.resolve().is_relative_to(root.resolve())
        or cache_root.resolve().is_relative_to(root.resolve())
        for root in protected_serving_roots
    ):
        raise ValueError("structural cache and output must be outside protected serving roots")
    before = {str(root): _hash_tree(root) for root in protected_serving_roots}
    if None in {build, shadow_requests, cache_package, parse, evaluate}:
        build, shadow_requests, cache_package, parse, evaluate, sec_client_type = _dependencies()
        client = client or sec_client_type(user_agent=user_agent, cache_dir=cache_root / ".sec-cache")
    summary: dict[str, Any] = {
        name: 0
        for name in (
            "attempted",
            "skipped",
            "parsed",
            "failure",
            "accepted",
            "review",
            "rejected",
            "unresolved",
        )
    }
    summary["requested_field_counts"] = {}
    summary["cases"] = []
    requested_counts: Counter[str] = Counter()
    for issuer in BATCH_01_MANIFEST:
        if issuer.lane_hypothesis not in _OPERATING_LANES:
            summary["skipped"] += 1
            summary["cases"].append(
                {"ticker": issuer.ticker, "result": "non_operating_lane_skipped"}
            )
            continue
        packet = source_root / issuer.ticker
        manifest, submissions, facts = _load_packet(packet, issuer)
        artifact = build(submissions=submissions, companyfacts=facts, valuation_date=BATCH_01_VALUATION_DATE, source_manifest=manifest)
        _immutable(output_root / issuer.ticker / "diagnostic-private.json", artifact)
        requests = shadow_requests(artifact)
        if not requests:
            summary["skipped"] += 1
            summary["cases"].append(
                {"ticker": issuer.ticker, "result": "companyfacts_sufficient"}
            )
            continue
        summary["attempted"] += 1
        requested_fields = [request.normalized_concept for request in requests]
        requested_counts.update(requested_fields)
        try:
            filing = artifact["financials"]["ttm"]["controlling_filing"]
            entrypoint = cache_package(
                client,
                cik=issuer.cik,
                accession=filing["accession"],
                primary_document=filing["primary_document"],
                form=filing["form"],
                output_dir=cache_root / issuer.ticker,
                refresh=refresh,
            )
            parsed = parse(entrypoint, accession=filing["accession"], form=filing["form"])
            report = evaluate(artifact, parsed)
            _immutable(output_root / issuer.ticker / "structural-filing.json", parsed.as_dict())
            package_manifest = entrypoint.parent / "package-manifest.json"
            if package_manifest.exists():
                _immutable(output_root / issuer.ticker / "package-manifest.json", json.loads(package_manifest.read_text()))
            summary["parsed"] += 1
            for decision in report.get("decisions", []):
                status = decision.get("status")
                if status in {"accepted", "review", "rejected", "unresolved"}:
                    summary[status] += 1
            summary["cases"].append(
                {
                    "ticker": issuer.ticker,
                    "result": "parsed",
                    "requested_fields": requested_fields,
                }
            )
        except Exception as error:
            report = {"ticker": issuer.ticker, "parser_failure": str(error), "decisions": []}
            summary["failure"] += 1
            summary["cases"].append(
                {
                    "ticker": issuer.ticker,
                    "result": "failure",
                    "requested_fields": requested_fields,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
        _immutable(output_root / issuer.ticker / "structural-report.json", report)
    after = {str(root): _hash_tree(root) for root in protected_serving_roots}
    if before != after:
        raise RuntimeError("protected serving artifacts changed")
    summary["requested_field_counts"] = dict(sorted(requested_counts.items()))
    summary["serving_artifacts_changed"] = False
    _immutable(output_root / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            run_structural_shadow(
                source_root=args.source_root,
                output_root=args.output_root,
                cache_root=args.cache_root,
                user_agent=args.user_agent,
                refresh=args.refresh,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
