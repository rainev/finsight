#!/usr/bin/env python3
"""Exercise the staged Phase B Batch 1 API against stored candidate artifacts."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


EMAIL = "pse-b01-verifier-20260922@example.com"
PASSWORD = "PseB01!Verify2026"
BATCH_TICKERS = ("BPI", "MBT", "SECB", "CBC", "EW", "RCR", "MREIT", "CREIT", "FILRT", "DDMPR")


def request(base: str, path: str, *, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    raw = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{base}/api{path}",
        data=raw,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read() or b"{}")
        return exc.code, payload


def authenticate(base: str) -> str:
    status, payload = request(base, "/auth/register", body={"email": EMAIL, "password": PASSWORD})
    if status == 409:
        status, payload = request(base, "/auth/login", body={"email": EMAIL, "password": PASSWORD})
    if status not in {200, 201}:
        raise RuntimeError(f"authentication failed: {status} {payload}")
    return str(payload["access_token"])


def main(base: str, catalog_root: Path, expected_status: str = "staged") -> None:
    unauth_status, _ = request(base, "/pse-valuations")
    if unauth_status != 401:
        raise RuntimeError(f"expected unauthenticated 401, got {unauth_status}")
    token = authenticate(base)
    status, listing = request(base, "/pse-valuations", token=token)
    if status != 200 or listing["count"] != 18 or listing["catalog_status"] != expected_status:
        raise RuntimeError(f"unexpected staged list response: {status} {listing}")
    tickers = [row["ticker"] for row in listing["items"]]
    expected = sorted(["AC", "ACR", "ALI", "AP", "AREIT", "BDO", "PERC", "SCC", *BATCH_TICKERS])
    if tickers != expected:
        raise RuntimeError(f"staged issuer set mismatch: {tickers}")

    detail_matches = 0
    calculator_matches = 0
    for ticker in tickers:
        status, detail = request(base, f"/pse-valuations/{ticker}", token=token)
        if status != 200:
            raise RuntimeError(f"{ticker}: detail returned {status}")
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = {key: detail[key] for key in stored}
        if served != stored:
            raise RuntimeError(f"{ticker}: served detail differs from stored artifact")
        detail_matches += 1
        if ticker in BATCH_TICKERS:
            status, view = request(base, f"/pse-valuations/{ticker}/calculator", token=token)
            if status != 200:
                raise RuntimeError(f"{ticker}: calculator view returned {status}")
            status, calculated = request(
                base,
                f"/pse-valuations/{ticker}/calculator",
                token=token,
                body={"overrides": {}, "scenario": "base"},
            )
            if status != 200:
                raise RuntimeError(f"{ticker}: calculator default returned {status}")
            expected_base = stored["scenarios"]["base"]["value_per_share"]
            if abs(calculated["result"]["base"] - expected_base) > 1e-9:
                raise RuntimeError(f"{ticker}: calculator base differs from stored artifact")
            calculator_matches += 1

    _, bpi_view = request(base, "/pse-valuations/BPI/calculator", token=token)
    _, bpi_edit = request(
        base,
        "/pse-valuations/BPI/calculator",
        token=token,
        body={"overrides": {"cost_of_equity": 0.13}, "scenario": "base", "save": True},
    )
    _, mreit_view = request(base, "/pse-valuations/MREIT/calculator", token=token)
    _, mreit_edit = request(
        base,
        "/pse-valuations/MREIT/calculator",
        token=token,
        body={"overrides": {"cost_of_equity": 0.12}, "scenario": "base"},
    )
    if bpi_edit["result"]["base"] >= bpi_view["baseline_result"]["base"]:
        raise RuntimeError("BPI higher cost of equity did not reduce value")
    if mreit_edit["result"]["base"] >= mreit_view["baseline_result"]["base"]:
        raise RuntimeError("MREIT higher cost of equity did not reduce value")
    if not bpi_edit.get("saved_id"):
        raise RuntimeError("BPI saved scenario did not persist")

    print(
        {
            "catalog_version": listing["catalog_version"],
            "catalog_status": listing["catalog_status"],
            "list_count": listing["count"],
            "detail_parity": detail_matches,
            "calculator_parity": calculator_matches,
            "bpi_base": bpi_view["baseline_result"]["base"],
            "bpi_edited": bpi_edit["result"]["base"],
            "mreit_base": mreit_view["baseline_result"]["base"],
            "mreit_edited": mreit_edit["result"]["base"],
            "saved_scenario_id": bpi_edit["saved_id"],
            "unauthenticated_status": unauth_status,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:4011")
    parser.add_argument("--catalog-root", type=Path, required=True)
    parser.add_argument("--expected-status", choices=("staged", "active"), default="staged")
    args = parser.parse_args()
    main(args.base.rstrip("/"), args.catalog_root.resolve(), args.expected_status)
