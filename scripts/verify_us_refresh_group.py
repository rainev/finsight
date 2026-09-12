#!/usr/bin/env python3
"""Run a bounded two-worker cached U.S. refresh verification group.

The command freezes the selected runtime/code bytes, runs up to two isolated
workers in-process, and reduces their per-company results into one immutable
diagnostic report.  It performs no acquisition, network retrieval, catalog
activation, database publication, or subprocess execution.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.refresh_group_verification import (  # noqa: E402
    freeze_manifest,
    materialize_implementation_snapshot,
    make_worker_specs,
    reduce_worker_results,
    run_worker,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=ROOT / "output" / "us-refresh-runtime",
        help="frozen refresh runtime containing registry, policies, recipes and baseline",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "output" / "us-refresh-group-verification",
        help="diagnostic output root; never a serving/catalog directory",
    )
    parser.add_argument("--ticker", action="append", default=[], help="ticker to include; repeat for a group")
    parser.add_argument("--source-index", type=Path, required=True, help="frozen cached source-index file; required to avoid recursive source discovery")
    parser.add_argument("--max-workers", type=int, choices=(1, 2), default=2)
    parser.add_argument(
        "--allow-broader-recheck",
        action="store_true",
        help="record an unknown source dependency as blocked; workers will still refuse it",
    )
    args = parser.parse_args(argv)

    runtime_root = args.runtime_root.resolve()
    output_root = args.output_root.resolve()
    registry = json.loads((runtime_root / "registry.json").read_bytes())
    tickers = args.ticker or [row["ticker"] for row in registry.get("entries", [])]
    prepare_started = time.perf_counter()
    manifest = freeze_manifest(
        runtime_root,
        tickers,
        source_index=args.source_index,
        allow_broader_recheck=args.allow_broader_recheck,
    )
    prepare_elapsed = time.perf_counter() - prepare_started
    snapshot_checkout=materialize_implementation_snapshot(manifest,output_root)
    specs = make_worker_specs(manifest, output_root, max_workers=args.max_workers,snapshot_checkout=snapshot_checkout)
    from app.us_valuation.refresh_group_verification import run_workers

    reports = run_workers(specs, manifest, runtime_root)
    report = reduce_worker_results(
        manifest,
        reports,
        output_root,
        runtime_root=runtime_root,
        prepare_elapsed_seconds=prepare_elapsed,
        snapshot_checkout=snapshot_checkout,
    )
    print(
        json.dumps(
            {
                "manifest_sha256": manifest["manifest_sha256"],
                "worker_count": len(specs),
                "expected_ticker_count": len(manifest["closure_tickers"]),
                "counts": report["counts"],
                "report_path": report["report_path"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
