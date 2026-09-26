#!/usr/bin/env python3
"""Stage AP/BPI/RCR/RLC reruns from pinned, reviewed local JSON receipts only."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.pse_valuation.internal_refresh import stage_internal_refresh


ROOT = Path(__file__).resolve().parents[1]
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True, help="Local reviewed input bundle")
    parser.add_argument("--output", type=Path, required=True, help="New isolated output directory")
    args = parser.parse_args()
    print(stage_internal_refresh(args.bundle, args.output, SERVING_ROOT))


if __name__ == "__main__":
    main()
