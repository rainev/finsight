#!/usr/bin/env python3
"""Exercise the staged Phase B Batch 2 API against stored candidate artifacts."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


EMAIL = "pse-b02-verifier-20260922@example.com"
PASSWORD = "PseB02!Verify2026"
BATCH_TICKERS = ("URC", "CNPF", "MONDE", "JFC", "DNL", "PGOLD", "RRHI", "WLCON", "SEVN", "SSI")


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
    if status != 200 or listing["count"] != 28 or listing["catalog_status"] != expected_status:
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
                if stored["availability_type"] == "intrinsic_valuation"
                else stored["market_relative"]["estimates"]["base"]
            )
            if status != 200 or status_post != 200 or abs(calculated["result"]["base"] - expected) > 1e-9:
                raise RuntimeError(f"{ticker}: calculator default differs from stored artifact")
            if abs(view["baseline_result"]["base"] - expected) > 1e-9:
                raise RuntimeError(f"{ticker}: calculator view differs from stored artifact")
            calculators += 1

    _, urc_view = request(base, "/pse-valuations/URC/calculator", token=token)
    _, urc_edit = request(
        base,
        "/pse-valuations/URC/calculator",
        token=token,
        body={"overrides": {"growth_rate": 0.05}, "scenario": "base", "save": True},
    )
    _, dnl_view = request(base, "/pse-valuations/DNL/calculator", token=token)
    _, dnl_edit = request(
        base,
        "/pse-valuations/DNL/calculator",
        token=token,
        body={"overrides": {"valuation_multiple": 11.0}, "scenario": "base"},
    )
    if urc_edit["result"]["base"] <= urc_view["baseline_result"]["base"]:
        raise RuntimeError("URC higher growth did not increase the selected value")
    if dnl_edit["result"]["base"] <= dnl_view["baseline_result"]["base"]:
        raise RuntimeError("DNL higher multiple did not increase the selected value")
    if not urc_edit.get("saved_id"):
        raise RuntimeError("URC edited scenario did not persist")
    print(
        {
            "catalog_version": listing["catalog_version"],
            "catalog_status": listing["catalog_status"],
            "list_count": listing["count"],
            "detail_parity": details,
            "calculator_parity": calculators,
            "urc_base": urc_view["baseline_result"]["base"],
            "urc_edited": urc_edit["result"]["base"],
            "dnl_base": dnl_view["baseline_result"]["base"],
            "dnl_edited": dnl_edit["result"]["base"],
            "saved_scenario_id": urc_edit["saved_id"],
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
