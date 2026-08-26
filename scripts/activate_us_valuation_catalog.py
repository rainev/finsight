#!/usr/bin/env python3
"""Atomically activate one already-built U.S. valuation catalog."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.catalog import (  # noqa: E402
    ACTIVE_SCHEMA,
    canonical_json_bytes,
    load_catalog_version,
)


CONFIRMATION = "ACTIVATE_VERIFIED_US_VALUATION_CATALOG"


def activate(
    *,
    catalogs_root: Path,
    catalog_path: str,
    confirmation: str,
    activated_at: str,
    dry_run: bool = False,
) -> dict:
    if confirmation != CONFIRMATION:
        raise ValueError("explicit catalog activation confirmation is required")
    catalogs_root = Path(catalogs_root).resolve()
    candidate = load_catalog_version(catalogs_root / catalog_path)
    active = {
        "schema_version": ACTIVE_SCHEMA,
        "catalog_version": candidate.catalog_version,
        "catalog_path": catalog_path,
        "manifest_sha256": candidate.manifest_sha256,
        "activated_at": activated_at,
    }
    if dry_run:
        return active
    catalogs_root.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".active-", suffix=".json", dir=catalogs_root
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json_bytes(active))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, catalogs_root / "active.json")
    finally:
        if temporary.exists():
            temporary.unlink()
    return active


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogs-root", type=Path, required=True)
    parser.add_argument("--catalog-path", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--activated-at", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = activate(**vars(args))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
