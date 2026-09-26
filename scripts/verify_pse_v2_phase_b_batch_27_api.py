"""Check exact staged Batch 27 list/detail and blocked-calculator parity over local HTTP."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import requests
from dotenv import dotenv_values

from app.pse_valuation.phase_b_batch_27 import FROZEN_BATCH_TICKERS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-27-candidate-a"


def request(session: requests.Session, method: str, base: str, path: str, **kwargs) -> requests.Response:
    for _ in range(6):
        response = session.request(method, base + "/api" + path, timeout=30, **kwargs)
        if response.status_code != 429:
            return response
        wait = min(int(response.headers.get("Retry-After", "60")) + 1, 60)
        print(f"PSE API rate limit reached; waiting {wait}s for reset", flush=True)
        time.sleep(wait)
    raise AssertionError(f"{path}: repeated 429")


def main(base: str, candidate_root: Path, pointer_name: str = "staged.json", expected_status: str = "staged") -> None:
    if not base.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise ValueError("Batch 27 verifier is local-only")
    secret = dotenv_values(ROOT / ".env")["JWT_ACCESS_SECRET"]
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": "1", "email": "batch27-local-check@example.invalid", "role": "user", "iat": now, "exp": now + timedelta(minutes=20)}, secret, algorithm="HS256")
    assert requests.get(base + "/api/pse-valuations", timeout=30).status_code == 401
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + token
    root = Path(candidate_root)
    pointer = json.loads((root / pointer_name).read_text())
    catalog_root = root / pointer["catalog_path"]
    manifest = json.loads((catalog_root / "manifest.json").read_text())
    response = request(session, "GET", base, "/pse-valuations")
    assert response.status_code == 200, response.status_code
    listing = response.json()
    assert listing["count"] == 278 and listing["catalog_status"] == expected_status and listing["catalog_version"] == manifest["catalog_version"]
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
        assert response.status_code == 200 and response.json()["can_calculate"] is False, ticker
        assert response.json()["baseline_result"] is None
        rejected = request(session, "POST", base, f"/pse-valuations/{ticker}/calculator", json={"overrides": {"valuation_multiple": 0.5}, "scenario": "base", "save": False})
        assert rejected.status_code == 400, ticker
    disabled = 0
    for entry in manifest["entries"]:
        if entry["publication_state"] != "blocked":
            continue
        response = request(session, "GET", base, f"/pse-valuations/{entry['ticker']}/calculator")
        assert response.status_code == 200 and response.json()["can_calculate"] is False, entry["ticker"]
        disabled += 1
    pnc = request(session, "GET", base, "/pse-valuations/PNC").json()
    assert pnc["filing_period"] is None and pnc["price"] is None
    mm = request(session, "GET", base, "/pse-valuations/MM").json()
    assert mm["availability_type"] == "market_relative_only" and mm["market_relative"]["estimates"]["base"] == 0.158165952
    print({"catalog_status": expected_status, "count": 278, "detail_parity": f"{detail_count}/278", "new_calculators": "0/10 enabled", "blocked_calculators": disabled, "pnc_filing_period": None, "inherited_mm_base": mm["market_relative"]["estimates"]["base"], "unauthenticated": 401})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4043")
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    parser.add_argument("--pointer-name", default="staged.json")
    parser.add_argument("--expected-status", choices=("staged", "active"), default="staged")
    args = parser.parse_args()
    main(args.base, args.candidate_root, args.pointer_name, args.expected_status)
