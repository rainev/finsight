#!/usr/bin/env python3
"""Exercise the standalone Batch 42 list/detail/calculator API surface."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.security.jwt import sign_access_token


FORBIDDEN = {"source_ledger", "reported_inputs", "governed_assumptions", "runtime_source_verification", "raw_scenario_rows"}


def _private(value):
    if isinstance(value, dict):
        return bool(FORBIDDEN & set(value)) or any(_private(child) for child in value.values())
    if isinstance(value, list):
        return any(_private(child) for child in value)
    return False


def _call(base_url: str, path: str, *, token: str | None = None, body: dict | None = None):
    request = Request(f"{base_url.rstrip('/')}{path}", data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST", headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def run(*, base_url: str, stage_root: Path) -> dict:
    stage_root = Path(stage_root)
    expected = {path.stem: json.loads(path.read_text()) for path in stage_root.glob("*.json")}
    status, listed = _call(base_url, "/api/us-valuations")
    if status != 200 or listed.get("count") != 10 or {row["ticker"] for row in listed["items"]} != set(expected):
        raise ValueError("Batch 42 list mismatch")
    token = sign_access_token(42, "batch42@example.com", "user")
    rows = []
    for ticker, artifact in sorted(expected.items()):
        detail_status, detail = _call(base_url, f"/api/us-valuations/{ticker}")
        view_status, view = _call(base_url, f"/api/us-valuations/{ticker}/calculator")
        post_status, calculated = _call(base_url, f"/api/us-valuations/{ticker}/calculator", token=token, body={"overrides": {}, "save": False})
        expected_post = 400 if artifact["availability_type"] == "not_available" else 200
        expected_range = {key: detail["scenario_range"][key] for key in ("low", "base", "high")}
        parity = post_status == expected_post and ((expected_post == 400 and detail["scenario_range"]["base"] is None) or calculated["result"] == expected_range)
        if detail_status != 200 or view_status != 200 or _private(detail) or not parity:
            raise ValueError(f"{ticker}: Batch 42 API boundary failed")
        rows.append({"ticker": ticker, "detail_status": detail_status, "calculator_get_status": view_status, "calculator_post_status": post_status, "default_parity": parity, "private_leak": _private(detail)})
    return {"schema_version": "FINSIGHT-BATCH-42-STANDALONE-API-1", "list_count": listed["count"], "detail_200_count": sum(row["detail_status"] == 200 for row in rows), "calculator_get_200_count": sum(row["calculator_get_status"] == 200 for row in rows), "calculator_default_parity_count": sum(row["default_parity"] for row in rows), "calculator_post_200_count": sum(row["calculator_post_status"] == 200 for row in rows), "calculator_post_400_count": sum(row["calculator_post_status"] == 400 for row in rows), "private_leak_count": sum(row["private_leak"] for row in rows), "stage_tree_sha256": hashlib.sha256(b"".join(path.name.encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest() for path in sorted(stage_root.glob("*.json")))).hexdigest(), "rows": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--stage-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(base_url=args.base_url, stage_root=args.stage_root)
    raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    if args.output.exists() and args.output.read_bytes() != raw:
        raise FileExistsError("refusing to overwrite Batch 42 API receipt")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(json.dumps({key: result[key] for key in ("list_count", "detail_200_count", "calculator_get_200_count", "calculator_default_parity_count", "calculator_post_200_count", "calculator_post_400_count", "private_leak_count")}, sort_keys=True))


if __name__ == "__main__":
    main()
