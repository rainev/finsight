#!/usr/bin/env python3
"""Replay staged Batches 01-03 through the launch-first public contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import PUBLIC_SCHEMA_VERSION, sanitize_public_artifact


PROTECTED_ROOTS = (
    ROOT / "backend/app/data/us_valuations",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)
FORBIDDEN_KEYS = {
    "raw_price",
    "split_adjusted_close",
    "provider",
    "payload_hash",
    "peer_prices",
    "reported_inputs",
    "source_ledger",
    "governed_assumptions",
}


def _bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


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
            raise FileExistsError(f"refusing to overwrite immutable launch-first replay: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent))
    try:
        candidate = staging / path.name
        candidate.write_bytes(raw)
        candidate.replace(path)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _contains_forbidden(value: object) -> bool:
    if isinstance(value, dict):
        return bool(FORBIDDEN_KEYS.intersection(value)) or any(
            _contains_forbidden(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_forbidden(item) for item in value)
    return False


def run(*, batch_roots: dict[int, Path], output_root: Path) -> dict[str, Any]:
    if set(batch_roots) != {1, 2, 3}:
        raise ValueError("launch-first replay requires exactly Batches 01, 02, and 03")
    output_root = Path(output_root)
    if any(output_root.resolve(strict=False).is_relative_to(root.resolve()) for root in PROTECTED_ROOTS):
        raise ValueError("launch-first replay output must remain outside serving roots")
    before = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    seen: set[str] = set()
    cases = []
    for batch, root in sorted(batch_roots.items()):
        staged = Path(root) / "staged-public"
        paths = sorted(staged.glob("*.json"))
        if len(paths) != 10:
            raise ValueError(f"Batch {batch:02d} must contain exactly ten staged artifacts")
        for path in paths:
            public = sanitize_public_artifact(json.loads(path.read_text()))
            ticker = public.get("ticker") or public.get("issuer", {}).get("ticker")
            if ticker in seen:
                raise ValueError(f"duplicate launch-first replay ticker {ticker}")
            seen.add(str(ticker))
            if public["schema_version"] != PUBLIC_SCHEMA_VERSION or _contains_forbidden(public):
                raise ValueError(f"{ticker}: public contract or safety projection failed")
            numeric = public["scenario_range"]["base"] is not None
            _immutable(
                output_root / "public" / f"batch-{batch:02d}" / f"{ticker}.json",
                _bytes(public),
            )
            _immutable(output_root / "public" / "all" / f"{ticker}.json", _bytes(public))
            cases.append(
                {
                    "batch": batch,
                    "ticker": ticker,
                    "availability_type": public["availability_type"],
                    "numeric": numeric,
                    "confidence": public["confidence"]["label"],
                    "method": public["primary_valuation_method"],
                    "base": public["scenario_range"]["base"],
                    "market_comparison_status": public["market_comparison"]["status"],
                }
            )
    after = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    if before != after:
        raise RuntimeError("launch-first replay changed protected serving roots")
    report = {
        "schema_version": "FINSIGHT-LAUNCH-FIRST-BATCH-REPLAY-1",
        "public_schema_version": PUBLIC_SCHEMA_VERSION,
        "batches": [1, 2, 3],
        "issuer_count": len(cases),
        "unique_ticker_count": len(seen),
        "numeric_count": sum(row["numeric"] for row in cases),
        "not_available_count": sum(row["availability_type"] == "not_available" for row in cases),
        "conditional_count": sum(row["availability_type"] == "conditional_estimate" for row in cases),
        "relative_baseline_count": sum(row["availability_type"] == "relative_baseline" for row in cases),
        "market_comparison_available_count": sum(row["market_comparison_status"] == "available" for row in cases),
        "serving_artifacts_changed": False,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "cases": cases,
    }
    _immutable(output_root / "replay-report.json", _bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-01-root", required=True, type=Path)
    parser.add_argument("--batch-02-root", required=True, type=Path)
    parser.add_argument("--batch-03-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    report = run(
        batch_roots={1: args.batch_01_root, 2: args.batch_02_root, 3: args.batch_03_root},
        output_root=args.output_root,
    )
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "issuer_count",
                    "numeric_count",
                    "conditional_count",
                    "not_available_count",
                    "market_comparison_available_count",
                    "serving_artifacts_changed",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
