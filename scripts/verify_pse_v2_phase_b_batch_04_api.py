#!/usr/bin/env python3
"""Exercise the staged Phase B Batch 4 API against stored candidate artifacts."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


EMAIL = "pse-b04-verifier-20260922@example.com"
PASSWORD = "PseB04!Verify2026"
BATCH_TICKERS = ("MER", "FGEN", "ACEN", "MWC", "SPC", "CREC", "ALTER", "ASLAG", "SPNEC", "MYNLD")
INTRINSIC_TICKERS = {"MER", "MWC", "SPC", "MYNLD"}


def request(base: str, path: str, *, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{base}/api{path}", data=json.dumps(body).encode() if body is not None else None, headers=headers, method="POST" if body is not None else "GET")
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
    if status != 200 or listing["count"] != 48 or listing["catalog_status"] != expected_status:
        raise RuntimeError(f"unexpected Batch 4 list response: {status} {listing}")
    stored_tickers = sorted(path.stem for path in (catalog_root / "artifacts").glob("*.json"))
    if [row["ticker"] for row in listing["items"]] != stored_tickers:
        raise RuntimeError("Batch 4 list membership differs from stored artifacts")

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
            status_post, calculated = request(base, f"/pse-valuations/{ticker}/calculator", token=token, body={"overrides": {}, "scenario": "base"})
            expected = stored["scenarios"]["base"]["value_per_share"] if ticker in INTRINSIC_TICKERS else stored["market_relative"]["estimates"]["base"]
            if status != 200 or status_post != 200 or abs(calculated["result"]["base"] - expected) > 1e-9:
                raise RuntimeError(f"{ticker}: calculator default differs from stored artifact")
            if abs(view["baseline_result"]["base"] - expected) > 1e-9:
                raise RuntimeError(f"{ticker}: calculator view differs from stored artifact")
            calculators += 1

    _, mwc_view = request(base, "/pse-valuations/MWC/calculator", token=token)
    _, mwc_edit = request(base, "/pse-valuations/MWC/calculator", token=token, body={"overrides": {"explicit_growth": 0.035}, "scenario": "base", "save": True})
    if mwc_edit["result"]["base"] <= mwc_view["baseline_result"]["base"] or not mwc_edit.get("saved_id"):
        raise RuntimeError("MWC finite-life calculator or save persistence failed")
    _, acen_view = request(base, "/pse-valuations/ACEN/calculator", token=token)
    _, acen_edit = request(base, "/pse-valuations/ACEN/calculator", token=token, body={"overrides": {"valuation_multiple": 1.2}, "scenario": "base"})
    if acen_edit["result"]["base"] <= acen_view["baseline_result"]["base"]:
        raise RuntimeError("ACEN higher P/B multiple did not increase value")
    print({"catalog_version": listing["catalog_version"], "catalog_status": listing["catalog_status"], "list_count": listing["count"], "detail_parity": details, "calculator_parity": calculators, "mwc_base": mwc_view["baseline_result"]["base"], "mwc_edited": mwc_edit["result"]["base"], "acen_base": acen_view["baseline_result"]["base"], "acen_edited": acen_edit["result"]["base"], "saved_scenario_id": mwc_edit["saved_id"], "unauthenticated_status": unauth_status})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:4021")
    parser.add_argument("--catalog-root", type=Path, required=True)
    parser.add_argument("--expected-status", choices=("staged", "active"), default="staged")
    args = parser.parse_args()
    main(args.base.rstrip("/"), args.catalog_root.resolve(), args.expected_status)
