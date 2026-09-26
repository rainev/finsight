import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


TICKERS = ("ICT", "CEB", "PAL", "MAC", "ATI", "TUGS", "C", "LSC", "MWIDE", "EEI")


def request(base, path, token=None, body=None):
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


def main(base, catalog_root, expected_status="staged"):
    assert request(base, "/pse-valuations")[0] == 401
    status, payload = request(base, "/auth/register", body={"email": "pse-b07-verifier@example.com", "password": "PseB07!Verify2026"})
    if status == 409:
        status, payload = request(base, "/auth/login", body={"email": "pse-b07-verifier@example.com", "password": "PseB07!Verify2026"})
    token = payload["access_token"]
    status, listing = request(base, "/pse-valuations", token)
    assert status == 200 and listing["count"] == 78 and listing["catalog_status"] == expected_status
    detail_count = 0
    calculator_count = 0
    for path in sorted((catalog_root / "artifacts").glob("*.json")):
        ticker = path.stem
        stored = json.loads(path.read_text())
        status, detail = request(base, f"/pse-valuations/{ticker}", token)
        assert status == 200 and {key: detail[key] for key in stored} == stored
        detail_count += 1
        if ticker in TICKERS:
            status, baseline = request(base, f"/pse-valuations/{ticker}/calculator", token)
            post_status, calculated = request(base, f"/pse-valuations/{ticker}/calculator", token, body={"overrides": {}, "scenario": "base"})
            expected = stored["market_relative"]["estimates"]["base"]
            assert status == post_status == 200
            assert abs(baseline["baseline_result"]["base"] - expected) < 1e-9
            assert abs(calculated["result"]["base"] - expected) < 1e-9
            calculator_count += 1
    _, baseline = request(base, "/pse-valuations/ICT/calculator", token)
    _, edited = request(
        base,
        "/pse-valuations/ICT/calculator",
        token,
        body={"overrides": {"valuation_multiple": 16}, "scenario": "base", "save": True},
    )
    assert edited["result"]["base"] > baseline["baseline_result"]["base"] and edited["saved_id"]
    print(
        {
            "catalog_status": listing["catalog_status"],
            "count": 78,
            "detail_parity": detail_count,
            "calculator_parity": calculator_count,
            "ict_base": baseline["baseline_result"]["base"],
            "ict_edited": edited["result"]["base"],
            "saved_id": edited["saved_id"],
            "unauth": 401,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:4021")
    parser.add_argument("--catalog-root", type=Path, required=True)
    parser.add_argument("--expected-status", choices=("staged", "active"), default="staged")
    args = parser.parse_args()
    main(args.base, args.catalog_root, args.expected_status)
