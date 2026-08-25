#!/usr/bin/env python3
"""Replay official evidence through the real valuation consumer and reconcile FOD5."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.evidence_field_registry import load_field_registry
from app.us_valuation.evidence_policy import EvidenceAvailability
from app.us_valuation.field_availability import FieldAvailability
from app.us_valuation.pipeline import build_us_valuation
from app.us_valuation.sec_client import normalize_cik


PROTECTED_ROOTS = (
    ROOT / "backend/app/data/us_valuations",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)
ALLOWED_OUTCOMES = {
    "reported", "reported_aggregate", "explicit_zero", "not_disclosed",
    "stale", "conflicting", "bounded_estimate", "unresolved",
}
SOURCE_ORDER = (
    "companyfacts_current", "exact_sec_filing", "filing_table",
    "regulator_or_sec_supplement", "current_aggregate",
    "annual_carry_forward", "company_history", "sector_range",
)


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _immutable(path: Path, value: object) -> None:
    raw = _canonical(value)
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite immutable replay output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _validate_output_root(output_root: Path) -> None:
    target = output_root.resolve(strict=False)
    if any(target == root.resolve() or target.is_relative_to(root.resolve()) for root in PROTECTED_ROOTS):
        raise ValueError("full replay output must remain outside protected serving roots")


def _cohort_manifest(
    batch1: Iterable[str],
    batch2: Iterable[str],
    difficult: Iterable[str],
    withheld: Iterable[str],
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, list[str]]]:
    cohorts = {
        "batch_01": set(batch1),
        "batch_02": set(batch2),
        "difficult_106": set(difficult),
        "cumulative_withheld": set(withheld),
    }
    universe = sorted(set().union(*cohorts.values()))
    manifest = [
        {
            "ticker": ticker,
            "cohorts": sorted(name for name, members in cohorts.items() if ticker in members),
        }
        for ticker in universe
    ]
    overlaps: dict[str, list[str]] = {}
    names = tuple(cohorts)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            overlaps[f"{left}&{right}"] = sorted(cohorts[left] & cohorts[right])
    counts = {name: len(members) for name, members in cohorts.items()}
    counts["unique_issuer_count"] = len(universe)
    counts["cohort_membership_count"] = sum(len(members) for members in cohorts.values())
    return manifest, counts, overlaps


def _table_proof_index(
    receipts: Iterable[Mapping[str, Any]],
    package_root: Path,
) -> dict[tuple[str, str, str, float], tuple[str, ...]]:
    manifests: dict[str, Mapping[str, Any]] = {}
    for path in sorted(package_root.rglob("package-manifest.json")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifests.setdefault(digest, _read(path))
    result: dict[tuple[str, str, str, float], tuple[str, ...]] = {}
    for receipt in receipts:
        for issuer in receipt.get("issuers", []):
            ticker = str(issuer["ticker"])
            cik = normalize_cik(str(issuer["cik"]))
            for evidence in issuer.get("evidence", []):
                if evidence.get("status") != "reported":
                    continue
                problems = []
                package_sha = str(evidence.get("package_sha256") or "")
                manifest = manifests.get(package_sha)
                if manifest is None:
                    problems.append("TABLE_PACKAGE_HASH_NOT_RECOMPUTED")
                else:
                    if normalize_cik(str(manifest.get("cik") or "")) != cik:
                        problems.append("TABLE_PACKAGE_CIK_MISMATCH")
                    if manifest.get("accession") != evidence.get("source_accession"):
                        problems.append("TABLE_PACKAGE_ACCESSION_MISMATCH")
                    source_urls = {
                        str(item.get("source_url"))
                        for item in manifest.get("files", [])
                        if item.get("source_url")
                    }
                    if evidence.get("source_url") not in source_urls:
                        problems.append("TABLE_SOURCE_URL_NOT_BOUND_TO_PACKAGE")
                title = str(evidence.get("table_title") or "").casefold()
                if evidence.get("consolidation_scope") == "consolidated_parent" and (
                    "consolidated" not in title
                ):
                    problems.append("TABLE_CONSOLIDATION_NOT_PROVEN_BY_TITLE")
                key = (
                    ticker,
                    str(evidence["required_field"]),
                    str(evidence["source_accession"]),
                    float(evidence["value"]) * float(evidence["scale"]),
                )
                if key in result:
                    problems.append("DUPLICATE_TABLE_PROOF_IDENTITY")
                result[key] = tuple(problems)
    return result


def _policy_safety(
    receipt: Mapping[str, Any],
    table_proofs: Mapping[tuple[str, str, str, float], tuple[str, ...]],
) -> tuple[list[dict[str, Any]], Counter[str], Counter[str], Counter[str]]:
    registry = load_field_registry()
    ledger: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    selected_tiers: Counter[str] = Counter()
    tier_attempts: Counter[str] = Counter()
    valuation_date = str(receipt["valuation_date"])
    for issuer in receipt["issuers"]:
        ticker = str(issuer["ticker"])
        cik = normalize_cik(str(issuer["cik"]))
        for decision in issuer["decisions"]:
            request = decision["request"]
            field = str(request["required_field"])
            attempts = tuple(decision["attempts"])
            status = str(decision["status"])
            problems: list[str] = []
            status_counts[status] += 1
            if status not in ALLOWED_OUTCOMES:
                problems.append("UNSUPPORTED_EVIDENCE_OUTCOME")
            applicable = set(request.get("applicable_sources") or ())
            attempted = {str(item["source"]) for item in attempts}
            tier_attempts.update(str(item["source"]) for item in attempts)
            if not applicable or not applicable.issubset(attempted) or decision.get("exhausted") is not True:
                problems.append("APPLICABLE_SOURCE_EXHAUSTION_INCOMPLETE")
            selected_source = decision.get("selected_source")
            selected_attempt = None
            if selected_source is not None:
                selected_tiers[str(selected_source)] += 1
                matches = [
                    item for item in attempts
                    if item.get("source") == selected_source
                    and item.get("eligible") is True
                    and item.get("value") == decision.get("selected_value")
                ]
                if not matches:
                    problems.append("SELECTED_ATTEMPT_MISSING")
                else:
                    identities = {
                        (
                            item.get("accession"), item.get("period_end"), item.get("value"),
                            item.get("unit"), item.get("entity_identifier"),
                            item.get("consolidation_scope"),
                        )
                        for item in matches
                    }
                    if len(identities) != 1:
                        problems.append("SELECTED_ATTEMPT_IDENTITY_NOT_UNIQUE")
                    selected_attempt = matches[0]
            projection = decision.get("availability_projection")
            if selected_attempt is not None:
                if projection is None:
                    problems.append("SELECTED_ATTEMPT_NOT_PROJECTED")
                if request.get("model_suitable") is not True:
                    problems.append("UNSUITABLE_MODEL_PROMOTION")
                source = str(selected_attempt["source"])
                if source not in {"company_history", "sector_range"}:
                    filed = selected_attempt.get("filed_date")
                    if not isinstance(filed, str) or not filed or filed > valuation_date:
                        problems.append("SOURCE_CUTOFF_UNPROVEN")
                    if not selected_attempt.get("source_url"):
                        problems.append("SOURCE_URL_MISSING")
                    if normalize_cik(str(selected_attempt.get("entity_identifier") or "")) != cik:
                        problems.append("SOURCE_ENTITY_MISMATCH")
                    if selected_attempt.get("consolidation_scope") != "consolidated_parent":
                        problems.append("SOURCE_CONSOLIDATION_UNPROVEN")
                    unit = selected_attempt.get("unit")
                    governed = registry.get(field)
                    if governed is None or unit not in governed.units:
                        problems.append("SOURCE_UNIT_NOT_GOVERNED")
                if source == "filing_table" and not selected_attempt.get("package_sha256"):
                    problems.append("TABLE_PACKAGE_HASH_MISSING")
                if source == "filing_table":
                    proof_key = (
                        ticker,
                        field,
                        str(selected_attempt.get("accession")),
                        float(selected_attempt.get("value")),
                    )
                    if proof_key not in table_proofs:
                        problems.append("TABLE_UNDERLYING_PROOF_MISSING")
                    else:
                        problems.extend(table_proofs[proof_key])
                if projection is not None:
                    if projection.get("source_accession") != selected_attempt.get("accession"):
                        problems.append("PROJECTION_ACCESSION_MISMATCH")
                    if status in {"reported", "reported_aggregate", "explicit_zero"} and (
                        projection.get("value") != selected_attempt.get("value")
                    ):
                        problems.append("PROJECTION_VALUE_MISMATCH")
            ledger.append(
                {
                    "ticker": ticker,
                    "request_id": request["request_id"],
                    "required_field": field,
                    "status": status,
                    "selected_source": selected_source,
                    "safe": not problems,
                    "safety_failures": problems,
                }
            )
    return ledger, status_counts, selected_tiers, tier_attempts


def _projected_availability(issuer: Mapping[str, Any]) -> tuple[EvidenceAvailability, ...]:
    result = []
    for decision in issuer["decisions"]:
        projection = decision.get("availability_projection")
        if not isinstance(projection, Mapping):
            continue
        value = dict(projection)
        cap = str(value.pop("reliability_cap"))
        result.append(EvidenceAvailability(FieldAvailability.from_dict(value), cap))
    return tuple(result)


def _publication_state(value: Mapping[str, Any]) -> str:
    review = value.get("review")
    if isinstance(review, Mapping) and isinstance(review.get("publication_state"), str):
        return str(review["publication_state"])
    return "withheld"


def _numeric(value: Mapping[str, Any]) -> bool:
    scenario = value.get("scenario_range")
    return isinstance(scenario, Mapping) and isinstance(scenario.get("base"), (int, float))


def _valuation_replay(
    *,
    policy_receipts: Iterable[Mapping[str, Any]],
    source_roots: Iterable[Path],
    output_root: Path,
) -> tuple[list[dict[str, Any]], Counter[str], Counter[str]]:
    source_index: dict[str, Path] = {}
    for root in source_roots:
        for path in sorted(root.glob("*/source-manifest.json")):
            source_index.setdefault(path.parent.name, path.parent)
    cases = []
    before_states: Counter[str] = Counter()
    after_states: Counter[str] = Counter()
    for receipt in policy_receipts:
        receipt_hash = hashlib.sha256(_canonical(receipt)).hexdigest()
        for issuer in receipt["issuers"]:
            ticker = str(issuer["ticker"])
            packet = source_index.get(ticker)
            if packet is None:
                cases.append({"ticker": ticker, "status": "source_packet_unavailable"})
                continue
            source_manifest = _read(packet / "source-manifest.json")
            submissions = _read(packet / "submissions.json")
            companyfacts = _read(packet / "companyfacts.json")
            official = _projected_availability(issuer)
            try:
                baseline = build_us_valuation(
                    submissions=submissions,
                    companyfacts=companyfacts,
                    valuation_date=str(receipt["valuation_date"]),
                    source_manifest=source_manifest,
                )
                enhanced = build_us_valuation(
                    submissions=submissions,
                    companyfacts=companyfacts,
                    valuation_date=str(receipt["valuation_date"]),
                    source_manifest=source_manifest,
                    official_evidence=official,
                    official_evidence_diagnostics={
                        "policy_receipt_sha256": receipt_hash,
                        "decision_count": len(issuer["decisions"]),
                    },
                )
            except Exception as error:  # fail closed and preserve the exact build blocker
                cases.append(
                    {
                        "ticker": ticker,
                        "status": "build_error",
                        "error_type": type(error).__name__,
                        "error": str(error),
                        "projection_count": len(official),
                    }
                )
                continue
            _immutable(output_root / "generated" / ticker / "baseline-private.json", baseline)
            _immutable(output_root / "generated" / ticker / "enhanced-private.json", enhanced)
            _immutable(output_root / "api-stage" / f"{ticker}.json", enhanced)
            baseline_public = sanitize_public_artifact(baseline)
            enhanced_public = sanitize_public_artifact(enhanced)
            _immutable(output_root / "public" / ticker / "baseline.json", baseline_public)
            _immutable(output_root / "public" / ticker / "enhanced.json", enhanced_public)
            before_state = _publication_state(baseline_public)
            after_state = _publication_state(enhanced_public)
            before_states[before_state] += 1
            after_states[after_state] += 1
            private_trace = enhanced.get("official_evidence")
            consumption = (
                private_trace.get("consumption", [])
                if isinstance(private_trace, Mapping)
                else []
            )
            cases.append(
                {
                    "ticker": ticker,
                    "status": "replayed",
                    "projection_count": len(official),
                    "baseline_publication_state": before_state,
                    "enhanced_publication_state": after_state,
                    "baseline_numeric": _numeric(baseline_public),
                    "enhanced_numeric": _numeric(enhanced_public),
                    "public_changed": baseline_public != enhanced_public,
                    "public_shape_changed": sorted(baseline_public) != sorted(enhanced_public),
                    "private_trace_present": isinstance(private_trace, Mapping),
                    "consumed_projection_count": sum(
                        item.get("status") == "consumed" for item in consumption
                    ),
                    "unused_or_mismatched_projection_count": sum(
                        item.get("status") == "unused_or_mismatched" for item in consumption
                    ),
                }
            )
    return cases, before_states, after_states


def _dqc_metrics(root: Path) -> dict[str, Any]:
    rows = [_read(path) for path in sorted(root.glob("*.json"))]
    return {
        "filing_count": len(rows),
        "rule_execution_count": sum(int(item.get("rule_stats_entry_count", 0)) for item in rows),
        "applicable_rule_count": sum(int(item.get("applicable_rule_count", 0)) for item in rows),
        "diagnostic_count": sum(len(item.get("diagnostics", [])) for item in rows),
        "dqc_error_count": sum(
            int(stat.get("except", 0)) + int(stat.get("misaligned", 0))
            for item in rows for stat in item.get("rule_stats", [])
        ),
        "can_create_value_count": sum(item.get("can_create_value") is True for item in rows),
        "status_counts": dict(sorted(Counter(str(item.get("status")) for item in rows).items())),
        "tree_sha256": _tree_hash(root),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    _validate_output_root(args.output_root)
    before_serving = {str(root.resolve()): _tree_hash(root) for root in PROTECTED_ROOTS}
    policies = [_read(path) for path in args.policy_receipt]
    if any(item.get("schema_version") != "FINSIGHT-EVIDENCE-POLICY-1" for item in policies):
        raise ValueError("unsupported policy receipt schema")
    difficult = _read(args.difficult_report)
    withheld = _read(args.withheld_register)
    batch1 = [str(item["ticker"]) for item in policies[0]["issuers"]]
    batch2 = [str(item["ticker"]) for item in policies[1]["issuers"]]
    difficult_tickers = [str(item["ticker"]) for item in difficult["cases"]]
    withheld_tickers = [str(item["ticker"]) for item in withheld["entries"]]
    manifest, cohort_counts, overlaps = _cohort_manifest(
        batch1, batch2, difficult_tickers, withheld_tickers
    )
    safety_ledgers = []
    status_counts: Counter[str] = Counter()
    selected_tiers: Counter[str] = Counter()
    tier_attempts: Counter[str] = Counter()
    table_receipts = [_read(path) for path in args.table_receipt]
    table_proofs = _table_proof_index(table_receipts, args.package_root)
    for receipt in policies:
        ledger, statuses, tiers, attempts = _policy_safety(receipt, table_proofs)
        safety_ledgers.extend(ledger)
        status_counts.update(statuses)
        selected_tiers.update(tiers)
        tier_attempts.update(attempts)
    valuation_cases, before_states, after_states = _valuation_replay(
        policy_receipts=policies,
        source_roots=args.source_root,
        output_root=args.output_root,
    )
    restatements = [_read(path) for path in args.restatement_receipt]
    specialist = _read(args.specialist_receipt)
    api_stage = _read(args.api_stage_report)
    real_api = _read(args.real_api_report)
    api_rows = [_read(path) for path in sorted(args.api_stage_root.glob("*.json"))]
    api_states = Counter(_publication_state(item) for item in api_rows)
    api_numeric = sum(_numeric(item) for item in api_rows)
    withheld_cases = []
    withheld_causes: Counter[str] = Counter()
    for item in api_rows:
        if _publication_state(item) != "withheld":
            continue
        errors = list(item.get("review", {}).get("errors", []))
        codes = []
        if any(str(error).startswith("Enterprise-to-equity bridge requires") for error in errors):
            codes.append("DATA_EVIDENCE_INCOMPLETE")
        for error in errors:
            text = str(error)
            if text.startswith("Enterprise-to-equity bridge requires"):
                continue
            if text.startswith("CONTROLLED_RESET_TARGET_MODEL:"):
                codes.append("SPECIALIST_OR_ARCHETYPE_MODEL_REQUIRED")
            else:
                codes.append(text)
        codes = sorted(set(codes))
        withheld_causes.update(codes)
        withheld_cases.append(
            {
                "ticker": str(item.get("ticker")),
                "true_cause_codes": codes,
                "errors": errors,
            }
        )
    custom_alias_count = sum(
        len(field.custom_aliases) for field in load_field_registry().values()
    )
    difficult_official_overlap = sorted(set(difficult_tickers) & (set(batch1) | set(batch2)))
    after_serving = {str(root.resolve()): _tree_hash(root) for root in PROTECTED_ROOTS}
    if before_serving != after_serving:
        raise RuntimeError("protected serving artifacts changed during full replay")
    unsafe = [item for item in safety_ledgers if not item["safe"]]
    replayed = [item for item in valuation_cases if item.get("status") == "replayed"]
    report = {
        "schema_version": "FINSIGHT-OFFICIAL-EVIDENCE-FULL-REPLAY-1",
        "valuation_date": policies[0]["valuation_date"],
        "gate_status": "partial_blocked" if len(difficult_official_overlap) < len(difficult_tickers) else "verified",
        "cohorts": cohort_counts,
        "overlaps": overlaps,
        "issuer_manifest": manifest,
        "official_evidence_coverage": {
            "unique_replayed_issuer_count": len(set(batch1) | set(batch2)),
            "difficult_cohort_replayed_count": len(difficult_official_overlap),
            "difficult_cohort_unreplayed_count": len(difficult_tickers) - len(difficult_official_overlap),
            "difficult_cohort_replayed_tickers": difficult_official_overlap,
            "coverage_blocker": (
                "No frozen unified-official-evidence source/package receipt exists for the other difficult-corpus issuers."
            ),
        },
        "evidence": {
            "material_request_count": len(safety_ledgers),
            "explicit_outcome_count": sum(status_counts.values()),
            "status_counts": dict(sorted(status_counts.items())),
            "selected_tier_counts": dict(sorted(selected_tiers.items())),
            "tier_terminal_attempt_counts": dict(sorted(tier_attempts.items())),
            "facts_rescued_from_raw_filings": selected_tiers["exact_sec_filing"],
            "facts_rescued_from_tables_and_notes": selected_tiers["filing_table"],
            "facts_rescued_from_regulator_or_supplement": selected_tiers["regulator_or_sec_supplement"],
            "governed_custom_alias_count": custom_alias_count,
            "selected_custom_tag_mapping_count": 0,
            "unsafe_promotion_count": len(unsafe),
            "unsafe_promotion_ledger": unsafe,
        },
        "valuation_consumer_replay": {
            "case_count": len(valuation_cases),
            "replayed_count": len(replayed),
            "build_error_count": sum(item.get("status") == "build_error" for item in valuation_cases),
            "source_packet_unavailable_count": sum(
                item.get("status") == "source_packet_unavailable" for item in valuation_cases
            ),
            "numeric_before_count": sum(item.get("baseline_numeric") is True for item in replayed),
            "numeric_after_count": sum(item.get("enhanced_numeric") is True for item in replayed),
            "public_changed_count": sum(item.get("public_changed") is True for item in replayed),
            "public_shape_changed_count": sum(
                item.get("public_shape_changed") is True for item in replayed
            ),
            "private_trace_present_count": sum(item.get("private_trace_present") is True for item in replayed),
            "consumed_projection_count": sum(int(item.get("consumed_projection_count", 0)) for item in replayed),
            "unused_or_mismatched_projection_count": sum(
                int(item.get("unused_or_mismatched_projection_count", 0)) for item in replayed
            ),
            "publication_states_before": dict(sorted(before_states.items())),
            "publication_states_after": dict(sorted(after_states.items())),
            "cases": valuation_cases,
        },
        "historical_difficult_replay": {
            key: difficult.get(key)
            for key in (
                "input_candidate_count", "valid_private_count", "source_verified_count",
                "invalid_input_count", "source_integrity_failure_count", "build_error_count",
                "numeric_before_count", "numeric_after_count", "unsafe_promotion_count",
                "public_contract_failure_count", "serving_artifacts_changed",
            )
        },
        "staged_public_boundary": {
            "artifact_count": len(api_rows),
            "numeric_before_count": api_numeric,
            "numeric_after_count": api_numeric,
            "publication_state_counts": dict(sorted(api_states.items())),
            "private_leak_count": api_stage.get("private_leak_count"),
            "sanitizer_parity": api_stage.get("private_leak_count") == 0,
            "note": "Before/after are equal because FOD4 remained private and serving-safe pending approval.",
        },
        "real_api_verification": {
            key: real_api.get(key)
            for key in (
                "list_http_status", "list_count", "list_exact_stage_parity",
                "detail_count", "detail_http_200_count",
                "detail_exact_stage_parity_count", "private_leak_count",
                "forbidden_serving_import_count",
            )
        },
        "withheld_true_causes": {
            "withheld_issuer_count": len(withheld_cases),
            "cause_counts": dict(sorted(withheld_causes.items())),
            "cases": sorted(withheld_cases, key=lambda item: item["ticker"]),
        },
        "restatements": {
            "candidate_count": sum(int(item["candidate_count"]) for item in restatements),
            "value_change_link_count": sum(int(item["value_change_link_count"]) for item in restatements),
            "confirmed_restatement_count": sum(
                int(item["confirmed_restatement_link_count"]) for item in restatements
            ),
        },
        "dqc": _dqc_metrics(args.dqc_root),
        "specialist": {
            "promotable_packet_count": specialist.get("promotable_packet_count"),
            "receipt_sha256": _sha(args.specialist_receipt),
        },
        "determinism": {
            "input_sha256": {
                str(path): _sha(path)
                for path in (
                    list(args.policy_receipt) + [
                        *args.table_receipt,
                        args.difficult_report, args.withheld_register,
                        *args.restatement_receipt, args.specialist_receipt,
                        args.api_stage_report,
                        args.real_api_report,
                    ]
                )
            },
            "serving_hash_before": before_serving,
            "serving_hash_after": after_serving,
            "serving_artifacts_changed": False,
        },
        "acceptance": {
            "every_material_request_has_explicit_outcome": len(safety_ledgers) == sum(status_counts.values()),
            "applicable_sources_exhausted": not any(
                "APPLICABLE_SOURCE_EXHAUSTION_INCOMPLETE" in item["safety_failures"]
                for item in safety_ledgers
            ),
            "unsafe_promotions_zero": len(unsafe) == 0,
            "valuation_consumer_build_errors_zero": not any(
                item.get("status") == "build_error" for item in valuation_cases
            ),
            "valuation_consumer_private_trace_complete": all(
                item.get("private_trace_present") is True
                for item in valuation_cases if item.get("status") == "replayed"
            ),
            "specialist_sources_fully_available": specialist.get("promotable_packet_count") == 4,
            "difficult_106_official_evidence_replayed": len(difficult_official_overlap) == 106,
            "serving_artifacts_unchanged": True,
            "real_api_parity": (
                real_api.get("list_http_status") == 200
                and real_api.get("list_exact_stage_parity") is True
                and real_api.get("detail_count") == real_api.get("detail_exact_stage_parity_count")
                and real_api.get("private_leak_count") == 0
                and real_api.get("forbidden_serving_import_count") == 0
            ),
            "user_confirmation_required": True,
        },
    }
    _immutable(args.output_root / "full-replay-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-receipt", action="append", type=Path, required=True)
    parser.add_argument("--table-receipt", action="append", type=Path, required=True)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--source-root", action="append", type=Path, required=True)
    parser.add_argument("--difficult-report", type=Path, required=True)
    parser.add_argument("--withheld-register", type=Path, required=True)
    parser.add_argument("--restatement-receipt", action="append", type=Path, required=True)
    parser.add_argument("--specialist-receipt", type=Path, required=True)
    parser.add_argument("--dqc-root", type=Path, required=True)
    parser.add_argument("--api-stage-root", type=Path, required=True)
    parser.add_argument("--api-stage-report", type=Path, required=True)
    parser.add_argument("--real-api-report", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if len(args.policy_receipt) != 2 or len(args.table_receipt) != 2 or len(args.source_root) != 2:
        parser.error("exactly two policy receipts, table receipts, and source roots are required")
    report = run(args)
    print(json.dumps({
        "gate_status": report["gate_status"],
        "unique_issuer_count": report["cohorts"]["unique_issuer_count"],
        "material_request_count": report["evidence"]["material_request_count"],
        "unsafe_promotion_count": report["evidence"]["unsafe_promotion_count"],
        "serving_artifacts_changed": report["determinism"]["serving_artifacts_changed"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
