#!/usr/bin/env python3
"""Run one internal PSE filing-watch tick or keep one local tick loop running."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from app.pse_valuation.refresh_watch import run_once


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "backend/app/pse_valuation/config/internal_filing_watch.json"
CATALOGS = ROOT / "backend/app/data/pse_valuation_catalogs"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-config", type=Path, default=CONFIG)
    parser.add_argument("--bundle-inbox", type=Path, required=True)
    parser.add_argument("--stage-root", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--summary-dir", type=Path, help="Compare locally saved PSE summary JSON snapshots; disables all external index polling")
    parser.add_argument("--watch", action="store_true", help="Repeat locally; no service is installed")
    parser.add_argument("--interval-minutes", type=int, default=1440)
    args = parser.parse_args()
    if args.watch and args.interval_minutes < 1:
        parser.error("--interval-minutes must be positive")
    if args.watch and args.summary_dir is not None:
        parser.error("offline summary comparison is one tick only; omit --watch")
    while True:
        report = run_once(
            config_path=args.source_config,
            bundle_inbox=args.bundle_inbox,
            stage_root=args.stage_root,
            state_dir=args.state_dir,
            catalogs_root=CATALOGS,
            summary_dir=args.summary_dir,
        )
        print(json.dumps(report, sort_keys=True), flush=True)
        if not args.watch:
            return
        time.sleep(args.interval_minutes * 60)


if __name__ == "__main__":
    main()
