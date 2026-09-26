"""Check exact Batch 22 list/detail and calculator parity over local HTTP."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import requests
from dotenv import dotenv_values

from app.pse_valuation.phase_b_batch_22 import FROZEN_BATCH_TICKERS


def request(session: requests.Session, method: str, base: str, path: str, **kwargs) -> requests.Response:
    for _ in range(5):
        response = session.request(method, base + "/api" + path, timeout=30, **kwargs)
        if response.status_code != 429:
            return response
        wait = min(int(response.headers.get("Retry-After", "60")) + 1, 60)
        print(f"PSE API rate limit reached; waiting {wait}s for reset", flush=True)
        time.sleep(wait)
    raise AssertionError(f"{path}: repeated 429")


def main(base: str, candidate_root: Path, pointer_name: str = "staged.json", expected_status: str = "staged") -> None:
    if not base.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise ValueError("Batch 22 verifier is local-only")
    root = Path(__file__).resolve().parents[1]
    secret = dotenv_values(root / ".env")["JWT_ACCESS_SECRET"]
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": "1", "email": "batch22-local-check@example.invalid", "role": "user", "iat": now, "exp": now + timedelta(minutes=10)}, secret, algorithm="HS256")
    assert requests.get(base + "/api/pse-valuations", timeout=30).status_code == 401
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + token
    candidate_root = Path(candidate_root)
    pointer = json.loads((candidate_root / pointer_name).read_text())
    catalog_root = candidate_root / pointer["catalog_path"]
    manifest = json.loads((catalog_root / "manifest.json").read_text())
    response = request(session, "GET", base, "/pse-valuations")
    assert response.status_code == 200, response.status_code
    listing = response.json()
    assert listing["count"] == 228 and listing["catalog_status"] == expected_status and listing["catalog_version"] == manifest["catalog_version"]
    assert {row["ticker"] for row in listing["items"]} == {entry["ticker"] for entry in manifest["entries"]}
    detail_count = 0
    for entry in manifest["entries"]:
        ticker = entry["ticker"]
        response = request(session, "GET", base, f"/pse-valuations/{ticker}")
        assert response.status_code == 200, (ticker, response.status_code)
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = response.json()
        assert {key: served[key] for key in stored} == stored, ticker
        assert served["catalog"]["catalog_status"] == expected_status
        detail_count += 1
    for ticker in FROZEN_BATCH_TICKERS:
        response = request(session, "GET", base, f"/pse-valuations/{ticker}/calculator")
        assert response.status_code == 200, ticker
        view = response.json()
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        assert view["can_calculate"] is True
        assert abs(view["baseline_result"]["base"] - stored["market_relative"]["estimates"]["base"]) < 1e-9
    for ticker in ("CDC", "HOUSE", "IS", "PAX", "PRIM"):
        response = request(session, "GET", base, f"/pse-valuations/{ticker}/calculator")
        assert response.status_code == 200 and response.json()["can_calculate"] is False, ticker
        rejected = request(session, "POST", base, f"/pse-valuations/{ticker}/calculator", json={"overrides": {"valuation_multiple": 0.5}, "scenario": "base", "save": False})
        assert rejected.status_code == 400, ticker
    edited = request(session, "POST", base, "/pse-valuations/CSB/calculator", json={"overrides": {"valuation_multiple": 1.0}, "scenario": "base", "save": False})
    assert edited.status_code == 200
    assert abs(edited.json()["result"]["base"] - 1466087430 / 173865000 * 1.0) < 1e-9
    print({"catalog_status": expected_status, "count": 228, "detail_parity": f"{detail_count}/228", "new_calculators": "10/10 enabled", "inherited_blocked": "CDC/HOUSE/IS/PAX/PRIM", "csb_edited_base": edited.json()["result"]["base"], "unauthenticated": 401})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4035")
    parser.add_argument("--candidate-root", type=Path, default=Path(__file__).resolve().parents[1] / "output/pse-valuation-candidates/phase-b-batch-22-candidate-a")
    parser.add_argument("--pointer-name", default="staged.json")
    parser.add_argument("--expected-status", choices=("staged", "active"), default="staged")
    args = parser.parse_args()
    main(args.base, args.candidate_root, args.pointer_name, args.expected_status)
