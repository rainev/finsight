"""Check every staged Batch 15 detail and all new calculator states through HTTP."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

from app.pse_valuation.phase_b_batch_15 import BLOCKED_TICKERS, FROZEN_BATCH_TICKERS


def request(base: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{base}/api{path}", data=json.dumps(body).encode() if body is not None else None, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def main(base: str, catalog_root: Path, expected_status: str = "staged") -> None:
    assert request(base, "/pse-valuations")[0] == 401
    credentials = {"email": "pse-b15-verifier@example.com", "password": "PseB15!Verify2026"}
    status, payload = request(base, "/auth/register", body=credentials)
    if status == 409:
        status, payload = request(base, "/auth/login", body=credentials)
    assert status in {200, 201}, (status, payload)
    token = payload["access_token"]
    status, listing = request(base, "/pse-valuations", token)
    assert status == 200 and listing["count"] == 158 and listing["catalog_status"] == expected_status, (status, listing)
    assert set(FROZEN_BATCH_TICKERS) <= {row["ticker"] for row in listing["items"]}
    details = {}
    count = 0
    for path in sorted((catalog_root / "artifacts").glob("*.json")):
        stored = json.loads(path.read_text())
        status, detail = request(base, f"/pse-valuations/{path.stem}", token)
        assert status == 200 and {key: detail[key] for key in stored} == stored, path.stem
        count += 1
        if path.stem in FROZEN_BATCH_TICKERS:
            details[path.stem] = detail
    assert count == 158 and len(details) == 10
    for ticker, detail in details.items():
        assert all(value is None for value in detail["scenarios"].values())
        assert (detail["availability_type"], detail["publication_state"]) == (("not_available", "blocked") if ticker in BLOCKED_TICKERS else ("market_relative_only", "provisional"))
    assert details["ALCO"]["filing_period"] == "2026-03-31" and details["HOUSE"]["filing_period"] == "2025-06-30"
    for ticker in FROZEN_BATCH_TICKERS:
        status, view = request(base, f"/pse-valuations/{ticker}/calculator", token)
        assert status == 200
        if ticker in BLOCKED_TICKERS:
            assert view["can_calculate"] is False and view["baseline_result"] is None
        else:
            assert view["can_calculate"] is True and abs(view["baseline_result"]["base"] - details[ticker]["market_relative"]["estimates"]["base"]) < 1e-9, ticker
    status, edited = request(base, "/pse-valuations/KPPI/calculator", token, body={"overrides": {"valuation_multiple": 0.5}, "scenario": "base", "save": True})
    assert status == 200 and abs(edited["result"]["base"] - 2.13) < 1e-9 and edited["saved_id"], (status, edited)
    status, cdc = request(base, "/pse-valuations/CDC/calculator", token)
    assert status == 200 and cdc["can_calculate"] is False and cdc["baseline_result"] is None
    status, blocked_post = request(base, "/pse-valuations/HOUSE/calculator", token, body={"overrides": {"valuation_multiple": 0.5}, "scenario": "base", "save": True})
    assert status in {400, 422} and blocked_post, (status, blocked_post)
    print({"catalog_status": listing["catalog_status"], "count": listing["count"], "detail_parity": count, "new_calculator_states": 10, "kppi_edited": edited["result"]["base"], "saved_id": edited["saved_id"], "house_disabled": True, "house_post": status, "cdc_disabled": True, "unauthenticated": 401})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4021")
    parser.add_argument("--catalog-root", type=Path, required=True)
    parser.add_argument("--expected-status", choices=("staged", "active"), default="staged")
    args = parser.parse_args()
    main(args.base, args.catalog_root, args.expected_status)
