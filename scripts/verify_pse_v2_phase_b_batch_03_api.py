#!/usr/bin/env python3
"""Exercise the staged Phase B Batch 3 API against stored candidate artifacts."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


EMAIL = "pse-b03-verifier-20260922@example.com"
PASSWORD = "PseB03!Verify2026"
BATCH_TICKERS = ("SM", "AEV", "JGS", "GTCAP", "DMC", "SMPH", "RLC", "MEG", "FLI", "CLI")
INTRINSIC_TICKERS = {"SMPH", "RLC", "FLI"}


def request(base: str, path: str, *, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{base}/api{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


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
    if status != 200 or listing["count"] != 38 or listing["catalog_status"] != expected_status:
        raise RuntimeError(f"unexpected staged list response: {status} {listing}")
    stored_tickers = sorted(path.stem for path in (catalog_root / "artifacts").glob("*.json"))
    if [row["ticker"] for row in listing["items"]] != stored_tickers:
        raise RuntimeError("staged list membership differs from stored artifacts")

    details = 0
    calculators = 0
    for ticker in stored_tickers:
        status, detail = request(base, f"/pse-valuations/{ticker}", token=token)
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        if status != 200 or {key: detail[key] for key in stored} != stored:
            raise RuntimeError(f"{ticker}: served detail differs from stored artifact")
        details += 1
        if ticker in BATCH_TICKERS:
            status, view = request(base, f"/pse-valuations/{ticker}/calculator", token=token)
            status_post, calculated = request(
                base,
                f"/pse-valuations/{ticker}/calculator",
                token=token,
                body={"overrides": {}, "scenario": "base"},
            )
            expected = (
                stored["scenarios"]["base"]["value_per_share"]
                if ticker in INTRINSIC_TICKERS
                else stored["market_relative"]["estimates"]["base"]
            )
            if status != 200 or status_post != 200 or abs(calculated["result"]["base"] - expected) > 1e-9:
                raise RuntimeError(f"{ticker}: calculator default differs from stored artifact")
            if abs(view["baseline_result"]["base"] - expected) > 1e-9:
                raise RuntimeError(f"{ticker}: calculator view differs from stored artifact")
            calculators += 1

    _, sm_view = request(base, "/pse-valuations/SM/calculator", token=token)
    _, sm_edit = request(
        base,
        "/pse-valuations/SM/calculator",
        token=token,
        body={"overrides": {"valuation_multiple": 1.2}, "scenario": "base", "save": True},
    )
    if sm_edit["result"]["base"] <= sm_view["baseline_result"]["base"]:
        raise RuntimeError("SM higher P/B multiple did not increase the selected value")
    if not sm_edit.get("saved_id"):
        raise RuntimeError("SM edited scenario did not persist")
    _, rlc_view = request(base, "/pse-valuations/RLC/calculator", token=token)
    _, rlc_edit = request(
        base,
        "/pse-valuations/RLC/calculator",
        token=token,
        body={"overrides": {"uplift_realization": 0.6}, "scenario": "base"},
    )
    if rlc_edit["result"]["base"] <= rlc_view["baseline_result"]["base"]:
        raise RuntimeError("RLC higher fair-value realization did not increase the selected value")
    print(
        {
            "catalog_version": listing["catalog_version"],
            "catalog_status": listing["catalog_status"],
            "list_count": listing["count"],
            "detail_parity": details,
            "calculator_parity": calculators,
            "sm_base": sm_view["baseline_result"]["base"],
            "sm_edited": sm_edit["result"]["base"],
            "rlc_base": rlc_view["baseline_result"]["base"],
            "rlc_edited": rlc_edit["result"]["base"],
            "saved_scenario_id": sm_edit["saved_id"],
            "unauthenticated_status": unauth_status,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:4021")
    parser.add_argument("--catalog-root", type=Path, required=True)
    parser.add_argument("--expected-status", choices=("staged", "active"), default="staged")
    args = parser.parse_args()
    main(args.base.rstrip("/"), args.catalog_root.resolve(), args.expected_status)
