#!/usr/bin/env python3
"""Stage SEC-backed repairs for legacy FCFF bridge fallbacks.

By default this command never changes serving artifacts. It writes source
evidence, private candidates, sanitized public candidates, and an acceptance
report to a staging directory. ``--promote`` rechecks and publishes only
explicitly accepted candidates.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.artifacts import public_result, sec_cache_manifest, write_json  # noqa: E402
from app.us_valuation.bridge_recovery import (  # noqa: E402
    LegacyFcffCase,
    conflicting_resolved_evidence_fields,
    controlling_filing_record,
    discover_legacy_fcff_cases,
    evaluate_recovery_candidate,
    relevant_filing_evidence,
    recovery_source_metadata,
)
from app.us_valuation.filing_evidence import extract_filing_evidence  # noqa: E402
from app.us_valuation.pipeline import build_us_valuation  # noqa: E402
from app.us_valuation.sec_client import SecClient  # noqa: E402


DATA_ROOT = ROOT / "backend" / "app" / "data" / "us_valuations"
DEFAULT_OUTPUT = ROOT / "output" / "legacy-fcff-bridge-recovery"
FIRST_COHORT = (
    "A", "ABBV", "AMD", "COST", "MCHP",
    "ADBE", "AMGN", "APD", "CL", "COHR", "CSCO", "HSY", "IDXX",
    "ILMN", "KO", "META", "NVDA", "ORCL", "PG", "PH", "RTX", "SNPS",
    "T", "TWLO",
)


def promote_staged_candidate(
    ticker: str, *, output_root: Path, data_root: Path = DATA_ROOT
) -> Path:
    """Promote one accepted staged artifact after repeating all safety gates."""
    normalized = ticker.upper()
    case_root = output_root / normalized
    result = json.loads((case_root / "recovery-result.json").read_text(encoding="utf-8"))
    if result.get("accepted") is not True:
        raise ValueError(f"Staged recovery is not accepted: {normalized}")
    private = json.loads((case_root / "valuation-private.json").read_text(encoding="utf-8"))
    public = json.loads(
        (case_root / "valuation-public-candidate.json").read_text(encoding="utf-8")
    )
    if public.get("issuer", {}).get("ticker") != normalized:
        raise ValueError(f"Staged recovery identity mismatch: {normalized}")
    decision = evaluate_recovery_candidate(private, public)
    if not decision.accepted:
        raise ValueError(
            f"Staged recovery failed promotion gate: {normalized}: "
            + ", ".join(decision.reasons)
        )
    target = data_root / f"{normalized}.json"
    write_json(target, public)
    return target


def _exposes_intrinsic_value(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            (key == "intrinsic_value_per_share" and nested is not None)
            or _exposes_intrinsic_value(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_exposes_intrinsic_value(item) for item in value)
    return False


def quarantine_staged_candidate(
    ticker: str, *, output_root: Path, data_root: Path = DATA_ROOT
) -> Path:
    """Replace a legacy fallback only with a fresh, value-free withheld FCFF artifact."""
    normalized = ticker.upper()
    case_root = output_root / normalized
    result = json.loads((case_root / "recovery-result.json").read_text(encoding="utf-8"))
    if result.get("accepted") is not False or "bridge_incomplete" not in result.get(
        "reasons", []
    ):
        raise ValueError(f"Staged recovery is not an unresolved bridge case: {normalized}")
    private = json.loads((case_root / "valuation-private.json").read_text(encoding="utf-8"))
    public = json.loads(
        (case_root / "valuation-public-candidate.json").read_text(encoding="utf-8")
    )
    if public.get("issuer", {}).get("ticker") != normalized:
        raise ValueError(f"Staged quarantine identity mismatch: {normalized}")
    for artifact in (private, public):
        policy = artifact.get("model_policy", {})
        if policy.get("primary") != "fcff_dcf" or policy.get("fallback_from") is not None:
            raise ValueError(f"Staged quarantine retains a legacy fallback: {normalized}")
    bridge = private.get("financials", {}).get("balance_sheet", {})
    if bridge.get("bridge_complete") is not False or not bridge.get(
        "bridge_missing_fields"
    ):
        raise ValueError(f"Staged quarantine does not prove an incomplete bridge: {normalized}")
    if public.get("review", {}).get("publication_state") != "withheld":
        raise ValueError(f"Staged quarantine is not withheld: {normalized}")
    if _exposes_intrinsic_value(public):
        raise ValueError(f"Staged quarantine exposes intrinsic value: {normalized}")
    target = data_root / f"{normalized}.json"
    write_json(target, public)
    return target


def quarantine_technical_failure_artifact(
    ticker: str, *, reason: str, data_root: Path = DATA_ROOT
) -> Path:
    """Fail closed when current inputs cannot produce even a staged FCFF candidate."""
    normalized = ticker.upper()
    if not reason.startswith("technical_error:"):
        raise ValueError(f"Technical quarantine requires a technical error: {normalized}")
    target = data_root / f"{normalized}.json"
    artifact = json.loads(target.read_text(encoding="utf-8"))
    if artifact.get("issuer", {}).get("ticker") != normalized:
        raise ValueError(f"Technical quarantine identity mismatch: {normalized}")
    if artifact.get("model_policy", {}).get("fallback_from") != "fcff_dcf":
        raise ValueError(f"Technical quarantine target is not a legacy FCFF fallback: {normalized}")
    if artifact.get("review", {}).get("publication_state") != "withheld":
        raise ValueError(f"Technical quarantine target is not already withheld: {normalized}")
    if _exposes_intrinsic_value(artifact):
        raise ValueError(f"Technical quarantine target exposes intrinsic value: {normalized}")

    artifact["model_policy"] = {
        "primary": "fcff_dcf",
        "supporting": [],
        "blend_models": False,
        "reason": "FCFF valuation withheld because current required inputs could not be established.",
    }
    artifact["public_assumptions"] = {}
    artifact["models"] = {
        "fcff_dcf": {
            "model": "fcff_dcf",
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
    artifact.setdefault("source_financial_statement", {})["note"] = (
        "Technical quarantine; no intrinsic value was produced."
    )
    prohibited = artifact.get("review", {}).get("prohibited_output_check", {})
    artifact["review"] = {
        "publication_state": "withheld",
        "confidence_grade": "insufficient",
        "errors": [reason],
        "warnings": [],
        "prohibited_output_check": prohibited,
    }
    write_json(target, artifact)
    return target


def quarantine_superseded_staging(
    ticker: str,
    *,
    reason: str,
    output_root: Path,
    data_root: Path = DATA_ROOT,
) -> Path:
    """Replace a superseded staged value with the current value-free artifact."""
    normalized = ticker.upper()
    case_root = output_root / normalized
    current = json.loads((data_root / f"{normalized}.json").read_text(encoding="utf-8"))
    if current.get("issuer", {}).get("ticker") != normalized:
        raise ValueError(f"Superseded staging identity mismatch: {normalized}")
    if current.get("review", {}).get("publication_state") != "withheld":
        raise ValueError(f"Superseded staging replacement is not withheld: {normalized}")
    if current.get("model_policy", {}).get("fallback_from") is not None:
        raise ValueError(f"Superseded staging replacement retains fallback: {normalized}")
    if _exposes_intrinsic_value(current):
        raise ValueError(f"Superseded staging replacement exposes intrinsic value: {normalized}")
    result_path = case_root / "recovery-result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["accepted"] = False
    result["reasons"] = [reason, "public_withheld"]
    result["resolved_requested_fields"] = []
    write_json(case_root / "valuation-private.json", current)
    write_json(case_root / "valuation-public-candidate.json", current)
    write_json(result_path, result)
    return case_root


def _filing_records(submissions: dict[str, Any]) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    return [
        {
            key: values[index]
            for key, values in recent.items()
            if isinstance(values, list) and index < len(values)
        }
        for index in range(len(recent.get("accessionNumber", [])))
    ]


def _controlling_accession(private: dict[str, Any]) -> str:
    controlling = private.get("financials", {}).get("ttm", {}).get("controlling_filing") or {}
    accession = str(controlling.get("accession") or "")
    if not accession:
        raise ValueError("Valuation did not identify a controlling SEC filing")
    return accession


def recover_case(
    case: LegacyFcffCase,
    *,
    client: SecClient,
    cache_dir: Path,
    output_root: Path,
    refresh: bool,
) -> dict[str, Any]:
    """Build and stage one candidate without mutating any public artifact."""
    case_root = output_root / case.ticker
    submissions = client.submissions(case.cik, refresh=refresh)
    companyfacts = client.companyfacts(case.cik, refresh=refresh)
    manifest = sec_cache_manifest(cache_dir, case.cik)
    initial = build_us_valuation(
        submissions=submissions,
        companyfacts=companyfacts,
        valuation_date=case.valuation_date,
        source_manifest=manifest,
    )
    current_missing_fields = tuple(
        initial.get("financials", {})
        .get("balance_sheet", {})
        .get("bridge_missing_fields", [])
    )
    accession = _controlling_accession(initial)
    filing = controlling_filing_record(submissions, accession)
    html = client.filing_document(
        case.cik,
        filing["accession"],
        filing["primary_document"],
        refresh=refresh,
    )
    metadata = recovery_source_metadata(ticker=case.ticker, cik=case.cik, filing=filing)
    evidence = extract_filing_evidence(html, metadata=metadata)
    conflicting_fields = conflicting_resolved_evidence_fields(evidence)
    used_evidence = relevant_filing_evidence(evidence, current_missing_fields)
    repaired = build_us_valuation(
        submissions=submissions,
        companyfacts=companyfacts,
        valuation_date=case.valuation_date,
        source_manifest=manifest,
        filing_evidence=used_evidence,
    )
    public = public_result(repaired, submissions)
    decision = evaluate_recovery_candidate(repaired, public)

    write_json(case_root / "filing-evidence.json", evidence)
    write_json(case_root / "filing-evidence-used.json", used_evidence)
    write_json(case_root / "valuation-private.json", repaired)
    write_json(case_root / "valuation-public-candidate.json", public)
    result = {
        "ticker": case.ticker,
        "cik": case.cik,
        "artifact_missing_fields": list(case.missing_fields),
        "current_missing_fields_before": list(current_missing_fields),
        "controlling_filing": filing,
        "evidence_record_count": len(evidence),
        "conflicting_evidence_fields": list(conflicting_fields),
        "resolved_requested_fields": sorted(
            {
                str(record.get("field"))
                for record in used_evidence
                if record.get("field") in current_missing_fields
                and record.get("status") == "resolved"
            }
        ),
        "accepted": decision.accepted,
        "reasons": list(decision.reasons),
        "staging_directory": str(case_root),
    }
    write_json(case_root / "recovery-result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", help="Comma-separated legacy tickers; defaults to first cohort")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Stage every remaining legacy FCFF fallback instead of the first cohort",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_OUTPUT / "sec-cache")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Publish only staged candidates that pass the repeated acceptance gate",
    )
    parser.add_argument(
        "--quarantine-unresolved",
        action="store_true",
        help=(
            "Replace legacy fallbacks only with fresh FCFF artifacts that remain "
            "withheld and expose no intrinsic value"
        ),
    )
    args = parser.parse_args()

    if args.all and args.tickers:
        parser.error("--all and --tickers are mutually exclusive")
    discovered = discover_legacy_fcff_cases(DATA_ROOT)
    selected = (
        {case.ticker for case in discovered}
        if args.all
        else {
            ticker.strip().upper()
            for ticker in args.tickers.split(",")
            if ticker.strip()
        }
        if args.tickers
        else set(FIRST_COHORT) & {case.ticker for case in discovered}
    )
    cases = [case for case in discovered if case.ticker in selected]
    found = {case.ticker for case in cases}
    missing = sorted(selected - found)
    if missing:
        parser.error("Not current legacy FCFF cases: " + ", ".join(missing))

    client = SecClient(
        user_agent=os.environ.get("SEC_USER_AGENT"),
        cache_dir=args.cache_dir,
    )
    results: list[dict[str, Any]] = []
    for case in cases:
        try:
            results.append(
                recover_case(
                    case,
                    client=client,
                    cache_dir=args.cache_dir,
                    output_root=args.output_root,
                    refresh=args.refresh,
                )
            )
        except Exception as exc:
            results.append(
                {
                    "ticker": case.ticker,
                    "accepted": False,
                    "reasons": [f"technical_error:{type(exc).__name__}:{exc}"],
                }
            )

    report = {
        "schema_version": "US-LEGACY-FCFF-RECOVERY-1.0",
        "dry_run": not (args.promote or args.quarantine_unresolved),
        "selected_count": len(cases),
        "accepted_count": sum(result["accepted"] for result in results),
        "unresolved_count": sum(not result["accepted"] for result in results),
        "results": results,
    }
    write_json(args.output_root / "recovery-report.json", report)
    if args.promote:
        report["promoted"] = [
            str(promote_staged_candidate(result["ticker"], output_root=args.output_root))
            for result in results
            if result.get("accepted") is True
        ]
        write_json(args.output_root / "recovery-report.json", report)
    if args.quarantine_unresolved:
        quarantined = [
            str(
                quarantine_staged_candidate(
                    result["ticker"], output_root=args.output_root
                )
            )
            for result in results
            if result.get("accepted") is False
            and "bridge_incomplete" in result.get("reasons", [])
        ]
        quarantined.extend(
            str(
                quarantine_technical_failure_artifact(
                    result["ticker"],
                    reason=next(
                        reason
                        for reason in result.get("reasons", [])
                        if reason.startswith("technical_error:")
                    ),
                )
            )
            for result in results
            if any(
                reason.startswith("technical_error:")
                for reason in result.get("reasons", [])
            )
        )
        report["quarantined"] = quarantined
        write_json(args.output_root / "recovery-report.json", report)
    print(json.dumps(report, indent=2))
    return 0 if results and not all("technical_error" in " ".join(result["reasons"]) for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
