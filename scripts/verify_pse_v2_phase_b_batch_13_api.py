"""Check all staged Batch 13 records and calculators through the real API."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


TICKERS = ("IMI", "TECH", "ION", "CIC", "MVC", "CROWN", "STN", "LFM", "VMC", "SBS")


def request(base: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
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
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def main(base: str, catalog_root: Path, expected_status: str = "staged") -> None:
    assert request(base, "/pse-valuations")[0] == 401
    credentials = {"email": "pse-b13-verifier@example.com", "password": "PseB13!Verify2026"}
    status, payload = request(base, "/auth/register", body=credentials)
    if status == 409:
        status, payload = request(base, "/auth/login", body=credentials)
    assert status in {200, 201}, (status, payload)
    token = payload["access_token"]
    status, listing = request(base, "/pse-valuations", token)
    assert status == 200 and listing["count"] == 138 and listing["catalog_status"] == expected_status
    assert set(TICKERS) <= {row["ticker"] for row in listing["items"]}
    detail_count = 0
    batch_artifacts = {}
    for path in sorted((catalog_root / "artifacts").glob("*.json")):
        ticker = path.stem
        stored = json.loads(path.read_text())
        status, detail = request(base, f"/pse-valuations/{ticker}", token)
        assert status == 200 and {key: detail[key] for key in stored} == stored, ticker
        detail_count += 1
        if ticker in TICKERS:
            batch_artifacts[ticker] = detail
        if expected_status == "active" and detail_count == 75:
            time.sleep(61)  # Respect the normal 120-request fixed window.
    assert detail_count == 138 and set(batch_artifacts) == set(TICKERS)
    assert all(row["availability_type"] == "market_relative_only" for row in batch_artifacts.values())
    assert batch_artifacts["VMC"]["filing_period"] == "2026-05-31"
    assert all(any(source["url"].startswith("https://www.bsp.gov.ph/") for source in batch_artifacts[ticker]["sources"]) for ticker in ("IMI", "TECH", "ION"))
    calculator_count = 0
    for ticker in TICKERS:
        status, view = request(base, f"/pse-valuations/{ticker}/calculator", token)
        expected = batch_artifacts[ticker]["market_relative"]["estimates"]["base"]
        assert status == 200 and view["can_calculate"] is True and abs(view["baseline_result"]["base"] - expected) < 1e-9, ticker
        calculator_count += 1
    status, edited = request(base, "/pse-valuations/TECH/calculator", token, body={"overrides": {"valuation_multiple": 0.6}, "scenario": "base", "save": True})
    assert status == 200 and abs(edited["result"]["base"] - 11.661828) < 1e-9 and edited["saved_id"]
    status, cdc = request(base, "/pse-valuations/CDC/calculator", token)
    assert status == 200 and cdc["can_calculate"] is False and cdc["baseline_result"] is None
    print({"catalog_status": listing["catalog_status"], "count": listing["count"], "detail_parity": detail_count, "calculator_states": calculator_count, "tech_base": batch_artifacts["TECH"]["market_relative"]["estimates"]["base"], "tech_edited": edited["result"]["base"], "saved_id": edited["saved_id"], "cdc_disabled": True, "unauthenticated": 401})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4021")
    parser.add_argument("--catalog-root", type=Path, required=True)
    parser.add_argument("--expected-status", choices=("staged", "active"), default="staged")
    args = parser.parse_args()
    main(args.base, args.catalog_root, args.expected_status)
