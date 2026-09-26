"""Check exact staged Batch 18 list/detail and calculator parity over local HTTP."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import requests
from dotenv import dotenv_values

from app.pse_valuation.phase_b_batch_18 import FROZEN_BATCH_TICKERS


def get(session: requests.Session, base: str, path: str) -> requests.Response:
    for _ in range(4):
        response = session.get(base + "/api" + path, timeout=30)
        if response.status_code != 429:
            return response
        wait = min(int(response.headers.get("Retry-After", "60")) + 1, 60)
        print(f"PSE API rate limit reached; waiting {wait}s for reset", flush=True)
        time.sleep(wait)
    raise AssertionError(f"{path}: repeated 429")


def main(base: str, candidate_root: Path, pointer_name: str = "staged.json", expected_status: str = "staged") -> None:
    if not base.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise ValueError("Batch 18 verifier is local-only")
    root = Path(__file__).resolve().parents[1]
    secret = dotenv_values(root / ".env")["JWT_ACCESS_SECRET"]
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": "1", "email": "batch18-local-check@example.invalid", "role": "user", "iat": now, "exp": now + timedelta(minutes=10)}, secret, algorithm="HS256")
    assert requests.get(base + "/api/pse-valuations", timeout=30).status_code == 401
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + token
    candidate_root = Path(candidate_root)
    pointer = json.loads((candidate_root / pointer_name).read_text())
    catalog_root = candidate_root / pointer["catalog_path"]
    manifest = json.loads((catalog_root / "manifest.json").read_text())
    response = get(session, base, "/pse-valuations")
    assert response.status_code == 200, response.status_code
    listing = response.json()
    assert listing["count"] == 188 and listing["catalog_status"] == expected_status and listing["catalog_version"] == manifest["catalog_version"]
    assert {item["ticker"] for item in listing["items"]} == {entry["ticker"] for entry in manifest["entries"]}
    details = {}
    for index, entry in enumerate(manifest["entries"], start=1):
        ticker = entry["ticker"]
        response = get(session, base, f"/pse-valuations/{ticker}")
        assert response.status_code == 200, (ticker, response.status_code)
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = response.json()
        assert {key: served[key] for key in stored} == stored, ticker
        assert served["catalog"]["catalog_status"] == expected_status, ticker
        if ticker in FROZEN_BATCH_TICKERS:
            details[ticker] = served
        if index % 60 == 0:
            print(f"stored/detail parity {index}/188", flush=True)
    assert len(details) == 10
    for ticker in FROZEN_BATCH_TICKERS:
        response = get(session, base, f"/pse-valuations/{ticker}/calculator")
        assert response.status_code == 200, ticker
        view = response.json()
        assert view["can_calculate"] is True and abs(view["baseline_result"]["base"] - details[ticker]["market_relative"]["estimates"]["base"]) < 1e-9, ticker
    for ticker in ("CDC", "HOUSE"):
        response = get(session, base, f"/pse-valuations/{ticker}/calculator")
        assert response.status_code == 200 and response.json()["can_calculate"] is False, ticker
    edited = session.post(base + "/api/pse-valuations/ECP/calculator", json={"overrides": {"valuation_multiple": 0.6}, "scenario": "base", "save": False}, timeout=30)
    assert edited.status_code == 200 and abs(edited.json()["result"]["base"] - 0.98874236) < 1e-9
    assert "zero parent" in details["PTC"]["warnings"][-1]
    assert "zero gross revenue" in details["APC"]["warnings"][-1]
    for ticker in ("IPM", "REG", "ECP"):
        assert "parent equity per common share" in details[ticker]["warnings"][-1]
    print({"catalog_status": listing["catalog_status"], "count": listing["count"], "detail_parity": "188/188", "new_calculators": "10/10", "blocked_calculators": "CDC/HOUSE disabled", "ecp_edited": edited.json()["result"]["base"], "unauthenticated": 401})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4031")
    parser.add_argument("--candidate-root", type=Path, default=Path(__file__).resolve().parents[1] / "output/pse-valuation-candidates/phase-b-batch-18-candidate-a")
    parser.add_argument("--pointer-name", default="staged.json")
    parser.add_argument("--expected-status", choices=("staged", "active"), default="staged")
    args = parser.parse_args()
    main(args.base, args.candidate_root, args.pointer_name, args.expected_status)
