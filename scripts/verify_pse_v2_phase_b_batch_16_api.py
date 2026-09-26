"""Check exact staged Batch 16 list/detail parity and calculator states over HTTP."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

from app.pse_valuation.phase_b_batch_16 import FROZEN_BATCH_TICKERS


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


def main(base: str, catalog_root: Path) -> None:
    assert request(base, "/pse-valuations")[0] == 401
    credentials = {"email": "pse-b16-verifier@example.com", "password": "PseB16!Verify2026"}
    status, payload = request(base, "/auth/register", body=credentials)
    if status == 409:
        status, payload = request(base, "/auth/login", body=credentials)
    assert status in {200, 201}, (status, payload)
    token = payload["access_token"]
    status, listing = request(base, "/pse-valuations", token)
    assert status == 200 and listing["count"] == 168 and listing["catalog_status"] == "staged", (status, listing)
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
    assert count == 168 and len(details) == 10
    for ticker, detail in details.items():
        assert detail["availability_type"] == "market_relative_only" and detail["publication_state"] == "provisional", ticker
        assert all(value is None for value in detail["scenarios"].values()), ticker
    assert details["FCG"]["filing_period"] == "2026-03-31" and details["BCOR"]["filing_period"] == "2026-03-31"
    assert details["FOOD"]["public_assumptions"]["fx_rate_php_per_usd"] == 62.698
    assert details["FOOD"]["public_assumptions"]["fx_observed_at"] == "2026-09-23"
    assert any(source["url"].startswith("https://www.bsp.gov.ph/") for source in details["FOOD"]["sources"])
    calculator_count = 0
    for ticker in FROZEN_BATCH_TICKERS:
        status, view = request(base, f"/pse-valuations/{ticker}/calculator", token)
        assert status == 200 and view["can_calculate"] is True
        assert abs(view["baseline_result"]["base"] - details[ticker]["market_relative"]["estimates"]["base"]) < 1e-9, ticker
        calculator_count += 1
    status, edited = request(base, "/pse-valuations/AXLM/calculator", token, body={"overrides": {"valuation_multiple": 11}, "scenario": "base", "save": True})
    assert status == 200 and abs(edited["result"]["base"] - 2.97) < 1e-9 and edited["saved_id"], (status, edited)
    status, sfi = request(base, "/pse-valuations/SFI/calculator", token, body={"overrides": {"valuation_multiple": 0.2}, "scenario": "base", "save": False})
    assert status == 200 and abs(sfi["result"]["base"] - details["SFI"]["market_relative"]["estimates"]["high"]) < 1e-9
    for ticker in ("CDC", "HOUSE"):
        status, view = request(base, f"/pse-valuations/{ticker}/calculator", token)
        assert status == 200 and view["can_calculate"] is False and view["baseline_result"] is None
    print({"catalog_status": listing["catalog_status"], "count": listing["count"], "detail_parity": count, "new_calculator_states": calculator_count, "axlm_edited": edited["result"]["base"], "saved_id": edited["saved_id"], "sfi_edited": sfi["result"]["base"], "cdc_house_disabled": True, "unauthenticated": 401})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4021")
    parser.add_argument("--catalog-root", type=Path, required=True)
    args = parser.parse_args()
    main(args.base, args.catalog_root)
