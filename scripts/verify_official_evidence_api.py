#!/usr/bin/env python3
"""Persist real localhost list/detail parity and serving import evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import sanitize_public_artifact


FORBIDDEN_IMPORT_PARTS = (
    "arelle", "arelle_adapter", "arelle_worker", "bank_regulatory",
    "ferc_regulatory", "reit_supplement", "official_filing_ingestion",
)


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _get(url: str) -> tuple[int, dict[str, Any]]:
    with urlopen(url, timeout=10) as response:
        status = int(response.status)
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise ValueError(f"{url}: expected a JSON object")
    return status, payload


def _contains_private_key(value: object) -> bool:
    if isinstance(value, dict):
        private_keys = {
            "official_evidence",
            "reported_inputs",
            "governed_assumptions",
            "input_source_ledger",
            "scenario_rows",
            "pipeline_revision_retry",
        }
        return bool(private_keys.intersection(value)) or any(
            _contains_private_key(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_private_key(item) for item in value)
    return False


def run(*, base_url: str, stage_root: Path) -> dict[str, Any]:
    expected = {}
    for path in sorted(stage_root.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        expected[path.stem] = sanitize_public_artifact(raw)
    list_status, list_payload = _get(f"{base_url.rstrip('/')}/api/us-valuations")
    expected_list = {
        "count": len(expected),
        "items": [
            {
                "ticker": value.get("issuer", {}).get("ticker", ticker),
                "name": value.get("issuer", {}).get("issuer_name"),
                "sector": value.get("issuer", {}).get("finsight_sector"),
                "model": value.get("model_policy", {}).get("primary"),
                "base": value.get("scenario_range", {}).get("base"),
                "publication_state": value.get("review", {}).get("publication_state"),
                "reliability": value["reliability"]["label"],
            }
            for ticker, value in sorted(expected.items())
        ],
    }
    details = []
    for ticker, expected_detail in sorted(expected.items()):
        status, payload = _get(f"{base_url.rstrip('/')}/api/us-valuations/{ticker}")
        details.append(
            {
                "ticker": ticker,
                "http_status": status,
                "exact_stage_parity": payload == expected_detail,
                "private_leak": _contains_private_key(payload),
                "response_sha256": hashlib.sha256(_canonical(payload)).hexdigest(),
                "expected_sha256": hashlib.sha256(_canonical(expected_detail)).hexdigest(),
            }
        )
    import app.main  # noqa: F401 - import is the boundary under audit
    forbidden = sorted(
        name for name in sys.modules
        if name.startswith("app.us_valuation.")
        and any(part in name.casefold() for part in FORBIDDEN_IMPORT_PARTS)
    )
    return {
        "schema_version": "FINSIGHT-OFFICIAL-EVIDENCE-REAL-API-1",
        "base_url": base_url,
        "list_http_status": list_status,
        "list_count": list_payload.get("count"),
        "list_exact_stage_parity": list_payload == expected_list,
        "list_response_sha256": hashlib.sha256(_canonical(list_payload)).hexdigest(),
        "detail_count": len(details),
        "detail_http_200_count": sum(item["http_status"] == 200 for item in details),
        "detail_exact_stage_parity_count": sum(item["exact_stage_parity"] for item in details),
        "private_leak_count": sum(item["private_leak"] for item in details),
        "forbidden_serving_import_count": len(forbidden),
        "forbidden_serving_imports": forbidden,
        "details": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--stage-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(base_url=args.base_url, stage_root=args.stage_root)
    raw = _canonical(result)
    if args.output.exists() and args.output.read_bytes() != raw:
        raise FileExistsError("refusing to overwrite another real API verification receipt")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(json.dumps({
        "list_status": result["list_http_status"],
        "list_count": result["list_count"],
        "detail_parity": result["detail_exact_stage_parity_count"],
        "private_leaks": result["private_leak_count"],
        "forbidden_imports": result["forbidden_serving_import_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
