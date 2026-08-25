#!/usr/bin/env python3
"""Stage public artifacts with private evidence traces and prove sanitizer parity."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import sanitize_public_artifact


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _policy_index(paths: list[Path]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    valuation_date: str | None = None
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "FINSIGHT-EVIDENCE-POLICY-1":
            raise ValueError("unsupported policy receipt schema")
        if valuation_date is None:
            valuation_date = payload.get("valuation_date")
        elif payload.get("valuation_date") != valuation_date:
            raise ValueError("policy receipt valuation dates disagree")
        for issuer in payload["issuers"]:
            if issuer["ticker"] in result:
                raise ValueError(f"duplicate policy ticker {issuer['ticker']}")
            result[issuer["ticker"]] = {
                "schema_version": payload["schema_version"],
                "valuation_date": payload["valuation_date"],
                "decisions": issuer["decisions"],
                "private_only": True,
            }
    return result


def run(*, staged_roots: list[Path], policy_receipts: list[Path], output_root: Path) -> dict[str, Any]:
    policy = _policy_index(policy_receipts)
    cases: list[dict[str, Any]] = []
    for root in staged_roots:
        for path in sorted(root.glob("*.json")):
            baseline = json.loads(path.read_text(encoding="utf-8"))
            ticker = str(baseline.get("ticker") or baseline.get("issuer", {}).get("ticker") or path.stem)
            if ticker not in policy or not policy[ticker]["decisions"]:
                raise ValueError(f"{ticker}: missing private policy trace")
            augmented = dict(baseline)
            augmented["official_evidence"] = policy[ticker]
            sanitized_baseline = sanitize_public_artifact(baseline)
            sanitized_augmented = sanitize_public_artifact(augmented)
            if sanitized_baseline != sanitized_augmented:
                raise ValueError(f"{ticker}: private evidence changed the public artifact")
            destination = output_root / f"{ticker}.json"
            raw = _canonical(augmented)
            if destination.exists() and destination.read_bytes() != raw:
                raise FileExistsError(f"refusing to overwrite staged artifact {ticker}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            cases.append(
                {
                    "ticker": ticker,
                    "public_sha256": hashlib.sha256(_canonical(sanitized_augmented)).hexdigest(),
                    "public_keys": sorted(sanitized_augmented),
                    "private_trace_decision_count": len(augmented["official_evidence"].get("decisions", [])),
                    "private_leak": "official_evidence" in sanitized_augmented,
                }
            )
    return {
        "schema_version": "FINSIGHT-OFFICIAL-EVIDENCE-API-STAGE-1",
        "count": len(cases),
        "private_leak_count": sum(item["private_leak"] for item in cases),
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged-root", type=Path, action="append", required=True)
    parser.add_argument("--policy-receipt", type=Path, action="append", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        staged_roots=args.staged_root,
        policy_receipts=args.policy_receipt,
        output_root=args.output_root,
    )
    raw = _canonical(result)
    if args.report.exists() and args.report.read_bytes() != raw:
        raise FileExistsError("refusing to overwrite another API stage report")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(raw)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
