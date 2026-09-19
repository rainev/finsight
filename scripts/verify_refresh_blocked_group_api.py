#!/usr/bin/env python3
"""Verify a blocked refresh group leaves the isolated real API baseline intact."""
from __future__ import annotations

import argparse
import json
from math import isclose
from pathlib import Path
import sys
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.us_valuation.catalog import canonical_json_bytes
from app.us_valuation.refresh_job import atomic


def _call(base: str, path: str, *, token: str | None = None, body: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(
        base + path,
        data=None if body is None else json.dumps(body).encode(),
        headers=headers,
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:4179/api")
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/us-refresh-runtime/blocked-group-api-evidence.json")
    args = parser.parse_args()

    auth = _call(args.base, "/auth/login", body={
        "email": "refresh-uat@example.com",
        "password": "Local-UAT-only-20260908!",
    })
    token = auth["access_token"]
    listed = _call(args.base, "/us-valuations", token=token)
    if listed["count"] != 440:
        raise AssertionError("isolated API no longer exposes the frozen 440-company baseline")

    rows = []
    for ticker in args.ticker:
        artifact = json.loads((ROOT / "output/us-refresh-runtime/baseline/artifacts" / f"{ticker}.json").read_bytes())
        detail = _call(args.base, f"/us-valuations/{ticker}", token=token)
        view = _call(args.base, f"/us-valuations/{ticker}/calculator", token=token)
        calculated = _call(args.base, f"/us-valuations/{ticker}/calculator", token=token, body={
            "overrides": {},
            "baseline_version": view["baseline_version"],
            "recipe_version": view["recipe_version"],
        })
        expected = artifact["scenario_range"]
        for key in ("low", "base", "high"):
            if not isclose(detail["scenario_range"][key], expected[key], rel_tol=1e-12, abs_tol=1e-9):
                raise AssertionError(f"{ticker} detail differs from frozen baseline")
            if not isclose(calculated["result"][key], expected[key], rel_tol=1e-12, abs_tol=1e-9):
                raise AssertionError(f"{ticker} calculator differs from frozen baseline")
        rows.append({
            "ticker": ticker,
            "catalog_version": detail["catalog_version"],
            "scenario_range": {key: expected[key] for key in ("low", "base", "high")},
            "detail_parity": True,
            "calculator_parity": True,
        })
    result = {
        "status": "blocked_group_api_verified",
        "scope": "isolated localhost API; no candidate activation or production mutation",
        "issuer_count": listed["count"],
        "rows": rows,
    }
    atomic(args.output, canonical_json_bytes(result), immutable=False)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
