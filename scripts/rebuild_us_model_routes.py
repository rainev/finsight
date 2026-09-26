#!/usr/bin/env python3
"""Stage and optionally publish issuer-reviewed U.S. model-route rebuilds."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.artifacts import public_result, sec_cache_manifest, write_json  # noqa: E402
from app.us_valuation.classification import classify_issuer  # noqa: E402
from app.us_valuation.pipeline import build_us_valuation  # noqa: E402
from app.us_valuation.sec_client import SecClient  # noqa: E402


DATA_ROOT = ROOT / "backend" / "app" / "data" / "us_valuations"
DEFAULT_OUTPUT = ROOT / "output" / "model-route-rebuild"


def evaluate_route_candidate(
    old: Mapping[str, Any], private: Mapping[str, Any], public: Mapping[str, Any]
) -> tuple[bool, tuple[str, ...]]:
    """Require an actual governed route change with no legacy fallback residue."""
    reasons: list[str] = []
    ticker = str(old.get("issuer", {}).get("ticker") or "")
    if private.get("issuer", {}).get("ticker") != ticker or public.get("issuer", {}).get(
        "ticker"
    ) != ticker:
        reasons.append("identity_mismatch")
    old_route = (
        old.get("issuer", {}).get("primary_archetype"),
        old.get("model_policy", {}).get("primary"),
    )
    new_route = (
        private.get("issuer", {}).get("primary_archetype"),
        private.get("model_policy", {}).get("primary"),
    )
    if old_route == new_route:
        reasons.append("route_unchanged")
    if public.get("issuer", {}).get("primary_archetype") != new_route[0]:
        reasons.append("public_archetype_mismatch")
    if public.get("model_policy", {}).get("primary") != new_route[1]:
        reasons.append("public_model_mismatch")
    if private.get("model_policy", {}).get("fallback_from") is not None or public.get(
        "model_policy", {}
    ).get("fallback_from") is not None:
        reasons.append("legacy_fallback")
    if new_route[1] not in public.get("models", {}):
        reasons.append("primary_model_missing")
    unique = tuple(dict.fromkeys(reasons))
    return not unique, unique


def quarantine_route_technical_failure(
    ticker: str,
    *,
    reason: str,
    classification: Mapping[str, Any],
    data_root: Path = DATA_ROOT,
) -> Path:
    """Remove an invalid old-model value when the corrected route cannot build."""
    normalized = ticker.upper()
    if not reason.startswith("technical_error:"):
        raise ValueError(f"Route quarantine requires a technical error: {normalized}")
    target = data_root / f"{normalized}.json"
    artifact = json.loads(target.read_text(encoding="utf-8"))
    old_route = (
        artifact.get("issuer", {}).get("primary_archetype"),
        artifact.get("model_policy", {}).get("primary"),
    )
    policy = classification.get("valuation_policy", {})
    new_route = (
        classification.get("primary_archetype"),
        policy.get("primary_model"),
    )
    if artifact.get("issuer", {}).get("ticker") != normalized:
        raise ValueError(f"Route quarantine identity mismatch: {normalized}")
    if old_route == new_route or not all(new_route):
        raise ValueError(f"Route quarantine does not change the governed route: {normalized}")

    issuer = artifact.setdefault("issuer", {})
    for key in (
        "finsight_sector",
        "primary_archetype",
        "secondary_archetypes",
        "classification_confidence",
        "mapping_version",
        "classification_reason",
        "model_route_eligible",
        "model_route_reason",
    ):
        if key in classification:
            issuer[key] = classification[key]
    model = str(policy["primary_model"])
    artifact["model_policy"] = {
        "primary": model,
        "supporting": list(policy.get("supporting_models", [])),
        "blend_models": False,
        "reason": str(policy.get("model_policy_reason") or classification.get("model_route_reason")),
    }
    artifact["public_assumptions"] = {}
    artifact["models"] = {
        model: {
            "model": model,
            "output_type": "intrinsic_value_per_share",
            "currency": artifact.get("currency", "USD"),
            "intrinsic_value_per_share": None,
            "publication_state": "withheld",
            "errors": [reason],
            "warnings": [],
        }
    }
    artifact["scenarios"] = {}
    artifact["scenario_range"] = {
        "low": None,
        "base": None,
        "high": None,
        "label": "assumption range, not a statistical confidence interval",
    }
    artifact["review"] = {
        "publication_state": "withheld",
        "confidence_grade": "insufficient",
        "errors": [reason],
        "warnings": [],
        "prohibited_output_check": {
            "current_price": False,
            "upside_downside": False,
            "buy_hold_sell": False,
            "trading_multiples": False,
        },
    }
    write_json(target, artifact)
    return target


def _user_agent() -> str | None:
    configured = (os.environ.get("SEC_USER_AGENT") or "").strip()
    if configured:
        return configured
    completed = subprocess.run(
        ["git", "config", "user.email"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    email = completed.stdout.strip()
    return f"FinSight {email}" if "@" in email else None


def rebuild_route(
    ticker: str,
    *,
    client: SecClient,
    cache_dir: Path,
    output_root: Path,
    promote: bool,
) -> dict[str, Any]:
    normalized = ticker.upper()
    source_path = DATA_ROOT / f"{normalized}.json"
    old = json.loads(source_path.read_text(encoding="utf-8"))
    cik = str(old.get("issuer", {}).get("cik") or "")
    submissions = client.submissions(cik)
    companyfacts = client.companyfacts(cik)
    private = build_us_valuation(
        submissions=submissions,
        companyfacts=companyfacts,
        valuation_date=str(old.get("valuation_date") or ""),
        source_manifest=sec_cache_manifest(cache_dir, cik),
    )
    public = public_result(private, submissions)
    accepted, reasons = evaluate_route_candidate(old, private, public)
    case_root = output_root / normalized
    write_json(case_root / "valuation-private.json", private)
    write_json(case_root / "valuation-public-candidate.json", public)
    result = {
        "ticker": normalized,
        "old_archetype": old.get("issuer", {}).get("primary_archetype"),
        "old_model": old.get("model_policy", {}).get("primary"),
        "new_archetype": private.get("issuer", {}).get("primary_archetype"),
        "new_model": private.get("model_policy", {}).get("primary"),
        "publication_state": public.get("review", {}).get("publication_state"),
        "accepted": accepted,
        "reasons": list(reasons),
    }
    if promote and accepted:
        write_json(source_path, public)
        result["promoted"] = str(source_path)
    write_json(case_root / "route-result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", required=True, help="Comma-separated ticker list")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_OUTPUT / "sec-cache")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    tickers = tuple(
        dict.fromkeys(
            ticker.strip().upper()
            for ticker in args.tickers.split(",")
            if ticker.strip()
        )
    )
    client = SecClient(user_agent=_user_agent(), cache_dir=args.cache_dir)
    results: list[dict[str, Any]] = []
    for ticker in tickers:
        try:
            results.append(
                rebuild_route(
                    ticker,
                    client=client,
                    cache_dir=args.cache_dir,
                    output_root=args.output_root,
                    promote=args.promote,
                )
            )
        except Exception as exc:
            reason = f"technical_error:{type(exc).__name__}:{exc}"
            failed: dict[str, Any] = {
                "ticker": ticker,
                "accepted": False,
                "reasons": [reason],
            }
            if args.promote:
                old = json.loads((DATA_ROOT / f"{ticker}.json").read_text(encoding="utf-8"))
                submissions = client.submissions(old["issuer"]["cik"])
                failed["quarantined"] = str(
                    quarantine_route_technical_failure(
                        ticker,
                        reason=reason,
                        classification=classify_issuer(submissions),
                    )
                )
            results.append(failed)
    report = {
        "schema_version": "US-MODEL-ROUTE-REBUILD-1.0",
        "dry_run": not args.promote,
        "selected_count": len(tickers),
        "accepted_count": sum(result.get("accepted") is True for result in results),
        "promoted_count": sum("promoted" in result for result in results),
        "results": results,
    }
    write_json(args.output_root / "route-report.json", report)
    print(json.dumps(report, indent=2))
    return 0 if results and all("technical_error" not in " ".join(result["reasons"]) for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
