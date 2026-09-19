#!/usr/bin/env python3
"""Serve one immutable latest-500 candidate from an isolated local runtime."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.catalog import canonical_json_bytes, load_catalog_version, sha256_bytes
from app.us_valuation.refresh_catalog_store import RefreshCatalogStore, load_frozen_registry
from verify_refresh_persistence import configure_database


def prepare(runtime: Path, candidate: Path, isolated_root: Path) -> str:
    runtime, candidate, isolated_root = runtime.resolve(), candidate.resolve(), isolated_root.resolve()
    if "latest-candidate-browser-uat" not in isolated_root.name:
        raise ValueError("isolated root name must contain latest-candidate-browser-uat")
    if isolated_root.exists():
        raise ValueError("isolated browser UAT root already exists")
    catalog = load_catalog_version(candidate)
    registry = load_frozen_registry(runtime / "registry.json", expected_count=500)
    if len(catalog.entries) != 500:
        raise ValueError("candidate must contain exactly 500 companies")
    isolated_root.mkdir(parents=True)
    shutil.copy2(runtime / "registry.json", isolated_root / "registry.json")
    shutil.copytree(runtime / "baseline", isolated_root / "baseline")
    store = RefreshCatalogStore(
        isolated_root / "catalogs",
        frozen_registry=isolated_root / "registry.json",
        expected_registry_count=500,
    )
    store.runtime_root.mkdir()
    policy = "latest-candidate-browser-uat-policy"
    fingerprint = sha256_bytes(policy.encode())
    store.approved_policy_path.write_bytes(canonical_json_bytes({
        "approved": True,
        "status": "approved",
        "policy_fingerprint": fingerprint,
        "registry_sha256": registry.registry_sha256,
        "scope": "isolated latest candidate browser UAT",
    }))
    successor = store.stage_catalog(candidate)
    receipt = store.activate(
        successor,
        policy_fingerprint=fingerprint,
        activated_at=datetime.now(timezone.utc).isoformat(),
        reason="isolated browser UAT candidate activation",
    )
    (isolated_root / "browser-uat.json").write_bytes(canonical_json_bytes({
        "candidate": str(candidate),
        "catalog_version": successor.catalog_version,
        "activation_receipt": str(receipt["receipt_path"]),
        "production": False,
    }))
    return successor.catalog_version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--isolated-root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=4196)
    parser.add_argument("--client-url", default="http://127.0.0.1:4197")
    args = parser.parse_args()
    catalog_version = prepare(args.runtime_root, args.candidate, args.isolated_root)
    configure_database()
    os.environ["FINSIGHT_US_REFRESH_ROOT"] = str(args.isolated_root.resolve())
    os.environ["CLIENT_URL"] = args.client_url
    from app.main import app
    import uvicorn

    print(json.dumps({
        "catalog_version": catalog_version,
        "isolated_root": str(args.isolated_root.resolve()),
        "production": False,
    }), flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
