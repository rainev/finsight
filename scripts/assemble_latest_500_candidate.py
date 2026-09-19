#!/usr/bin/env python3
"""Assemble a non-activated 500-company latest-refresh release candidate.

This script is deliberately a release boundary, not a refresh engine.  It
accepts only a source-validation report whose fingerprints match the selected
runtime and whose evidence wrappers match the frozen discovery capture.  All
other issuers retain their approved dated baseline with an explicit
disposition.  It never changes an active pointer or publishes a catalog.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.calculator import baseline_version
from app.us_valuation.catalog import (
    CATALOG_SCHEMA,
    artifact_tree_sha256,
    canonical_json_bytes,
    load_catalog_version,
    sha256_bytes,
)
from app.us_valuation.refresh_work_register import implementation_fingerprint


NUMERIC_RECIPE_COUNT = 474
SOURCE_BOUND_STATUSES = {"cached_source_bound", "source_bound", "verified_source_bound"}
TARGETED_BLOCK_STATUSES = {"targeted_review", "source_or_economic_review", "implementation_failure"}


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _sha(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{field}: expected finite number")
    return float(value)


def _range(value: Mapping[str, Any], field: str) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for key in ("low", "base", "high"):
        raw = value.get(key)
        result[key] = None if raw is None else _finite(raw, f"{field}.{key}")
    present = [result[key] for key in ("low", "base", "high")]
    if any(item is not None for item in present) and any(item is None for item in present):
        raise ValueError(f"{field}: partial range")
    if all(item is not None for item in present) and not present[0] <= present[1] <= present[2]:
        raise ValueError(f"{field}: unordered range")
    return result


def _rows(value: Mapping[str, Any], *, label: str) -> dict[str, dict[str, Any]]:
    raw = value.get("rows")
    if raw is None and isinstance(value.get("companies"), Mapping):
        raw = [dict(row, ticker=ticker) for ticker, row in value["companies"].items()]
    if not isinstance(raw, list):
        raise ValueError(f"{label}: rows or companies mapping is required")
    result: dict[str, dict[str, Any]] = {}
    for row in raw:
        if not isinstance(row, dict) or not isinstance(row.get("ticker"), str):
            raise ValueError(f"{label}: invalid ticker row")
        ticker = row["ticker"]
        if ticker in result:
            raise ValueError(f"{label}: duplicate ticker {ticker}")
        result[ticker] = row
    return result


def _fingerprints(runtime_root: Path) -> dict[str, str]:
    registry = runtime_root / "registry.json"
    policies = runtime_root / "refresh-policies.json"
    return {
        "registry_sha256": _sha(registry),
        "policy_sha256": _sha(policies),
        "implementation_sha256": implementation_fingerprint(ROOT),
        "baseline_manifest_sha256": _sha(runtime_root / "baseline" / "manifest.json"),
    }


def _validate_runtime(runtime_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str]]:
    baseline = load_catalog_version(runtime_root / "baseline")
    if len(baseline.entries) != 500:
        raise ValueError(f"latest baseline must contain exactly 500 entries, got {len(baseline.entries)}")
    registry = _json(runtime_root / "registry.json")
    if len(registry.get("entries", [])) != 500:
        raise ValueError("latest registry must contain exactly 500 entries")
    if registry.get("baseline_manifest_sha256") != baseline.manifest_sha256:
        raise ValueError("runtime registry is not bound to the latest baseline manifest")
    if registry.get("baseline_catalog_version") != baseline.catalog_version:
        raise ValueError("runtime registry baseline version drift")
    recipe_root = runtime_root / "recipes"
    recipe_files = {path.stem for path in recipe_root.glob("*.json")}
    numeric = {entry.ticker for entry in baseline.entries if entry.availability_type != "not_available"}
    if len(numeric) != NUMERIC_RECIPE_COUNT or recipe_files != numeric:
        raise ValueError(f"runtime must contain exactly {NUMERIC_RECIPE_COUNT} numeric recipes")
    for ticker in sorted(numeric):
        recipe = _json(recipe_root / f"{ticker}.json")
        public = _json(baseline.verify_artifact(ticker))
        if recipe.get("ticker") != ticker or recipe.get("baseline_version") != baseline_version(public):
            raise ValueError(f"{ticker}: runtime recipe baseline binding is invalid")
        replay = evaluate_recipe(recipe)["range"]
        expected = public["scenario_range"]
        if any(not math.isclose(replay[key], float(expected[key]), rel_tol=1e-9, abs_tol=1e-7) for key in ("low", "base", "high")):
            raise ValueError(f"{ticker}: runtime recipe does not replay baseline")
    return (
        _json(runtime_root / "baseline" / "manifest.json"),
        registry,
        {"baseline": baseline, "numeric": numeric, "policies": _json(runtime_root / "refresh-policies.json")},
        _fingerprints(runtime_root),
    )


def _validate_discovery(
    report_path: Path,
    capture_root: Path,
    expected_tickers: set[str],
    *,
    required_capture_tickers: set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    report = _json(report_path)
    if report.get("expected_count") != 500 or report.get("cutoff") != "2026-09-19":
        raise ValueError("discovery capture report is not the frozen 500-company 2026-09-19 report")
    rows = _rows(report, label="discovery capture report")
    captures: dict[str, dict[str, Any]] = {}
    for ticker in expected_tickers:
        path = capture_root / f"{ticker}.json.gz"
        if not path.is_file():
            if required_capture_tickers and ticker in required_capture_tickers:
                raise ValueError(f"{ticker}: required frozen discovery capture is missing")
            captures[ticker] = {
                "path": None,
                "wrapper_sha256": None,
                "packet_sha256": None,
                "discovery_sha256": report.get("discovery_sha256"),
                "cutoff": report["cutoff"],
                "report_row": rows.get(ticker),
            }
            continue
        if not required_capture_tickers or ticker not in required_capture_tickers:
            captures[ticker] = {
                "path": path,
                "wrapper_sha256": None,
                "packet_sha256": None,
                "discovery_sha256": report.get("discovery_sha256"),
                "cutoff": report["cutoff"],
                "report_row": rows.get(ticker),
            }
            continue
        outer = json.loads(gzip.open(path, "rt", encoding="utf-8").read())
        if outer.get("ticker") != ticker:
            raise ValueError(f"{ticker}: discovery capture ticker mismatch")
        captures[ticker] = {
            "path": path,
            "wrapper_sha256": _sha(path),
            "packet_sha256": outer.get("packet_sha256"),
            "discovery_sha256": outer.get("discovery_sha256"),
            "cutoff": outer.get("cutoff"),
            "report_row": rows.get(ticker),
        }
        if captures[ticker]["cutoff"] != report["cutoff"]:
            raise ValueError(f"{ticker}: discovery capture cutoff mismatch")
    return report, captures


def _validate_fingerprint_report(report: Mapping[str, Any], expected: Mapping[str, str], label: str) -> None:
    for key in ("registry_sha256", "policy_sha256", "implementation_sha256"):
        if report.get(key) != expected[key]:
            raise ValueError(f"{label}: {key} does not match current runtime")


def _merge_source_reports(
    paths: list[Path],
    expected: Mapping[str, str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    """Merge source-validation tranches without allowing overwrite by order."""
    if not paths:
        raise ValueError("at least one source-validation report is required")
    records: dict[str, dict[str, Any]] = {}
    reports: dict[str, dict[str, Any]] = {}
    global_policy_matches: list[bool] = []
    for path in paths:
        report = _json(path)
        for key in ("registry_sha256", "implementation_sha256"):
            if report.get(key) != expected[key]:
                raise ValueError(f"source-validation report {path}: {key} does not match current runtime")
        policy_matches = report.get("policy_sha256") == expected["policy_sha256"]
        global_policy_matches.append(policy_matches)
        rows = _source_rows(report)
        evidence_hashes = report.get("evidence_sha256", {})
        if not isinstance(evidence_hashes, Mapping):
            raise ValueError(f"source-validation report {path}: evidence_sha256 must be an object")
        for ticker, row in rows.items():
            candidate = {
                "row": row,
                "report_path": str(path),
                "evidence_sha256": evidence_hashes.get(ticker),
                "global_policy_fingerprint_match": policy_matches,
            }
            previous = records.get(ticker)
            if previous is not None:
                if (
                    canonical_json_bytes(previous["row"]) != canonical_json_bytes(row)
                    or previous.get("evidence_sha256") != candidate.get("evidence_sha256")
                ):
                    raise ValueError(f"source-validation reports disagree for duplicate ticker {ticker}")
                # Keep the first identical record; report order cannot overwrite it.
                continue
            records[ticker] = candidate
            reports[ticker] = report
    return records, reports, {
        "global_policy_fingerprint_matches": all(global_policy_matches),
        "global_policy_fingerprint_mismatch_count": sum(not item for item in global_policy_matches),
    }


def _source_rows(report: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return _rows(report, label="source-validation report")


def _source_candidate(
    ticker: str,
    row: Mapping[str, Any],
    source_report_path: Path,
    captures: Mapping[str, Mapping[str, Any]],
    baseline_artifact: Mapping[str, Any],
    baseline_recipe: Mapping[str, Any] | None,
    current_policy_version: str | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if row.get("status") not in SOURCE_BOUND_STATUSES:
        raise ValueError(f"{ticker}: source row is not source_bound")
    # Evidence receipts are sibling JSON files named by ticker.
    evidence_path = source_report_path.parent / f"{ticker}.json"
    if not evidence_path.is_file():
        raise ValueError(f"{ticker}: source evidence receipt is missing")
    proof_raw = evidence_path.read_bytes()
    proof = json.loads(proof_raw)
    report = _json(source_report_path)
    if report.get("evidence_sha256", {}).get(ticker) != sha256_bytes(proof_raw):
        raise ValueError(f"{ticker}: source evidence hash mismatch")
    capture = captures[ticker]
    if capture.get("path") is None:
        raise ValueError(f"{ticker}: frozen discovery capture is missing")
    source_capture = proof.get("source_capture")
    if not isinstance(source_capture, Mapping):
        raise ValueError(f"{ticker}: source capture wrapper is missing")
    if source_capture.get("wrapper_sha256") != capture["wrapper_sha256"] or source_capture.get("packet_sha256") != capture["packet_sha256"]:
        raise ValueError(f"{ticker}: source capture wrapper/packet does not match frozen discovery capture")
    proof_policy_version = proof.get("ledger", {}).get("policy_version") if isinstance(proof.get("ledger"), Mapping) else None
    if not isinstance(current_policy_version, str) or not current_policy_version:
        raise ValueError(f"{ticker}: current per-ticker policy version is unavailable")
    if proof_policy_version != current_policy_version:
        raise ValueError(f"{ticker}: source proof policy version is stale")
    public = proof.get("public_artifact")
    recipe = proof.get("recipe")
    if not isinstance(public, dict) or not isinstance(recipe, dict):
        raise ValueError(f"{ticker}: source evidence public artifact or recipe is missing")
    if public.get("issuer", {}).get("ticker") != ticker or str(public.get("issuer", {}).get("cik", "")).zfill(10) != str(baseline_artifact.get("issuer", {}).get("cik", "")).zfill(10):
        raise ValueError(f"{ticker}: source successor identity mismatch")
    if baseline_recipe is None or recipe.get("baseline_version") != baseline_recipe.get("baseline_version"):
        raise ValueError(f"{ticker}: source successor baseline recipe identity mismatch")
    if recipe.get("provenance", {}).get("private_sha256") != baseline_recipe.get("provenance", {}).get("private_sha256"):
        raise ValueError(f"{ticker}: source successor private lineage mismatch")
    calculated = evaluate_recipe(recipe)
    result_range = _range(proof.get("result", {}).get("range", {}), f"{ticker}.source_result")
    public_range = _range(public.get("scenario_range", {}), f"{ticker}.source_public")
    if calculated["range"] != {key: result_range[key] for key in ("low", "base", "high")}:
        raise ValueError(f"{ticker}: source recipe/result replay mismatch")
    if public_range != result_range:
        raise ValueError(f"{ticker}: source public/result range mismatch")
    # The source verifier proves economics against the predecessor. The
    # immutable successor recipe must be rebound to the successor artifact so
    # stale calculator submissions fail against the new baseline version.
    recipe=dict(recipe)
    recipe['baseline_version']=baseline_version(public)
    recipe['replay']={key:result_range[key] for key in ('low','base','high')}
    rebound=evaluate_recipe(recipe)
    if rebound['range']!=recipe['replay']:
        raise ValueError(f"{ticker}: rebound successor recipe replay mismatch")
    status = {
        "outcome": "source_bound",
        "recommendation": "source-bound successor retained; separate economic/publication gate remains required",
        "source_report": str(source_report_path),
        "source_evidence": str(evidence_path),
        "source_date": public.get("source_financial_statement", {}).get("filed_date"),
        "source_accession": public.get("source_financial_statement", {}).get("accession"),
        "global_policy_fingerprint_match": row.get("global_policy_fingerprint_match"),
        "per_ticker_policy_version_match": True,
    }
    return public, recipe, status


def _verification_rows(path: Path, expected: Mapping[str, str], tickers: set[str]) -> dict[str, dict[str, Any]]:
    report = _json(path)
    if report.get("schema_version") == "FINSIGHT-LATEST-UNCHANGED-VERIFICATION-1":
        if report.get("expected_count") != 500 or report.get("identity_count") != 500:
            raise ValueError("unchanged-verification report does not cover exactly 500 identities")
        inputs = report.get("input_hashes")
        if not isinstance(inputs, Mapping) or inputs.get("baseline_manifest_sha256") != expected["baseline_manifest_sha256"] or inputs.get("registry_sha256") != expected["registry_sha256"]:
            raise ValueError("unchanged-verification report is not bound to the current baseline/registry")
        rows = _rows(report, label="unchanged-verification report")
        if set(rows) != tickers:
            raise ValueError("unchanged-verification report must cover exactly 500 tickers")
        return rows
    _validate_fingerprint_report(report, expected, "unchanged-verification report")
    rows = _rows(report, label="unchanged-verification report")
    if set(rows) != tickers:
        raise ValueError("unchanged-verification report must cover exactly 500 tickers")
    return rows


def _targeted_rows(path: Path, tickers: set[str]) -> dict[str, dict[str, Any]]:
    report = _json(path)
    companies = report.get("companies")
    if not isinstance(companies, Mapping):
        raise ValueError("targeted-reviews report must contain a companies mapping")
    return {str(ticker): dict(row) for ticker, row in companies.items() if isinstance(row, Mapping)}


def _copy_json(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def assemble(
    *,
    runtime_root: Path,
    discovery_report: Path,
    source_validation_report: Path | list[Path],
    targeted_reviews: Path,
    unchanged_verification: Path,
    output_root: Path,
) -> dict[str, Any]:
    baseline_manifest, registry, runtime, fingerprints = _validate_runtime(runtime_root)
    baseline = runtime["baseline"]
    tickers = {entry.ticker for entry in baseline.entries}
    source_paths = [source_validation_report] if isinstance(source_validation_report, Path) else list(source_validation_report)
    source_records, source_reports, source_fingerprint_summary = _merge_source_reports(source_paths, fingerprints)
    source_rows = {ticker: record["row"] for ticker, record in source_records.items()}
    required_captures = {ticker for ticker, row in source_rows.items() if row.get("status") in SOURCE_BOUND_STATUSES}
    discovery, captures = _validate_discovery(
        discovery_report,
        discovery_report.parent / "captures",
        tickers,
        required_capture_tickers=required_captures,
    )
    targeted = _targeted_rows(targeted_reviews, tickers)
    unchanged = _verification_rows(unchanged_verification, fingerprints, tickers)
    source_snapshots = sorted({
        str(report.get("source_capture_snapshot") or report.get("retrieval_snapshot_timestamp"))
        for report in source_reports.values()
        if report.get("source_capture_snapshot") or report.get("retrieval_snapshot_timestamp")
    })
    discovery_snapshot=discovery.get('retrieval_snapshot_timestamp') or discovery.get('snapshot_timestamp')
    if not source_snapshots and discovery_snapshot:
        source_snapshots = [str(discovery_snapshot)]
    if not source_snapshots:
        raise ValueError("source-validation/discovery inputs do not identify a capture snapshot")
    source_snapshot = source_snapshots[0] if len(source_snapshots) == 1 else source_snapshots
    if source_snapshot is None:
        raise ValueError("source-validation report must identify its capture snapshot")
    input_fingerprint = {
        "baseline_manifest_sha256": fingerprints["baseline_manifest_sha256"],
        "registry_sha256": fingerprints["registry_sha256"],
        "policy_sha256": fingerprints["policy_sha256"],
        "implementation_sha256": fingerprints["implementation_sha256"],
        "discovery_report_sha256": _sha(discovery_report),
        "source_validation_report_sha256": sorted(_sha(path) for path in source_paths),
        "targeted_reviews_sha256": _sha(targeted_reviews),
        "unchanged_verification_sha256": _sha(unchanged_verification),
        "cutoff": discovery["cutoff"],
        "source_snapshot": source_snapshot,
    }
    candidate_id = sha256_bytes(canonical_json_bytes(input_fingerprint))[:24]
    candidate_root = output_root / candidate_id
    if candidate_root.exists():
        raise ValueError(f"immutable release candidate already exists: {candidate_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{candidate_id}-", dir=output_root))
    try:
        artifacts = stage / "artifacts"
        recipes = stage / "recipes"
        artifacts.mkdir()
        recipes.mkdir()
        entries = []
        report_rows = []
        status_counts: Counter[str] = Counter()
        for entry in sorted(baseline.entries, key=lambda item: item.ticker):
            ticker = entry.ticker
            baseline_artifact_path = baseline.verify_artifact(ticker)
            baseline_artifact = json.loads(baseline_artifact_path.read_text())
            baseline_recipe_path = runtime_root / "recipes" / f"{ticker}.json"
            baseline_recipe = json.loads(baseline_recipe_path.read_text()) if baseline_recipe_path.is_file() else None
            old_range = _range(baseline_artifact.get("scenario_range", {}), f"{ticker}.old")
            targeted_row = targeted.get(ticker)
            source_record = source_records.get(ticker)
            source_row = source_record["row"] if source_record else None
            verification = unchanged[ticker]
            public = baseline_artifact
            recipe = baseline_recipe
            status = "verified_unchanged"
            recommendation = str(verification.get("recommendation") or "retain approved dated baseline")
            source_date = baseline_artifact.get("source_financial_statement", {}).get("filed_date")
            source_accession = baseline_artifact.get("source_financial_statement", {}).get("accession")
            verification_status = str(verification.get("status") or verification.get("state") or "")
            source_status = verification_status
            if source_row is not None and source_row.get("status") in SOURCE_BOUND_STATUSES:
                if targeted_row is not None:
                    status = "targeted_review_historical_only"
                    recommendation = str(targeted_row.get("reason") or "targeted review blocks current successor promotion")
                else:
                    try:
                        public, recipe, proof_status = _source_candidate(
                            ticker,
                            source_row,
                            Path(source_record["report_path"]),
                            captures,
                            baseline_artifact,
                            baseline_recipe,
                            runtime.get("policies", {}).get(ticker, {}).get("version"),
                        )
                        status = proof_status["outcome"]
                        recommendation = proof_status["recommendation"]
                        source_date = proof_status["source_date"]
                        source_accession = proof_status["source_accession"]
                    except ValueError as exc:
                        status = "source_retrieval_failure"
                        recommendation = f"retain approved dated baseline; source successor rejected: {exc}"
            elif verification_status == "prior_unavailable":
                status = "prior_unavailable_verified"
                recommendation = str(verification.get("recommendation") or verification.get("reason") or "retain prior unavailable status")
            elif verification_status not in {"verified_unchanged", "prior_unavailable"}:
                status = verification_status or "verification_gap"
                recommendation = str(verification.get("recommendation") or verification.get("reason") or "retain approved dated baseline; current promotion blocked")
            if targeted_row is not None and status == "verified_unchanged":
                status = "targeted_review_historical_only"
                recommendation = str(targeted_row.get("reason") or "targeted review blocks current successor promotion")
            if status == "verified_unchanged":
                recommendation = "retain approved dated baseline as a historical-only estimate; verified unchanged and not relabeled as current"
            elif status == "prior_unavailable_verified":
                recommendation = "retain prior unavailable status; no current numeric value is asserted"
            elif status != "source_bound":
                recommendation = "retain approved dated baseline as a historical-only estimate; do not present as current. " + recommendation
            if status != "source_bound":
                public = baseline_artifact
                recipe = baseline_recipe
                source_date = baseline_artifact.get("source_financial_statement", {}).get("filed_date")
                source_accession = baseline_artifact.get("source_financial_statement", {}).get("accession")
            raw_artifact = canonical_json_bytes(public)
            (artifacts / f"{ticker}.json").write_bytes(raw_artifact)
            if recipe is not None:
                (recipes / f"{ticker}.json").write_bytes(canonical_json_bytes(recipe))
            new_range = _range(public.get("scenario_range", {}), f"{ticker}.new")
            status_counts[status] += 1
            report_rows.append({
                "ticker": ticker,
                "cik": entry.cik,
                "batch": entry.batch,
                "outcome": status,
                "recommendation": recommendation,
                "old_range": old_range,
                "new_range": new_range,
                "old_reliability": baseline_artifact.get("reliability"),
                "new_reliability": public.get("reliability"),
                "old_source_date": baseline_artifact.get("source_financial_statement", {}).get("filed_date"),
                "new_source_date": source_date,
                "old_source_accession": baseline_artifact.get("source_financial_statement", {}).get("accession"),
                "new_source_accession": source_accession,
                "targeted_review": targeted_row,
                "verification_status": source_status,
                "global_policy_fingerprint_match": (
                    source_record.get("global_policy_fingerprint_match") if source_record else None
                ),
            })
            entries.append({
                "ticker": ticker,
                "cik": entry.cik,
                "batch": entry.batch,
                "availability_type": public.get("availability_type", entry.availability_type),
                "artifact_sha256": sha256_bytes(raw_artifact),
                "source_audit": entry.source_audit,
            })
        if len(entries) != 500 or len({row["ticker"] for row in entries}) != 500:
            raise ValueError("candidate does not contain exactly 500 unique artifacts")
        recipe_hashes = {path.stem: sha256_bytes(path.read_bytes()) for path in sorted(recipes.glob("*.json"))}
        if len(recipe_hashes) != NUMERIC_RECIPE_COUNT:
            raise ValueError(f"candidate must contain exactly {NUMERIC_RECIPE_COUNT} recipes")
        counts = Counter(entry["availability_type"] for entry in entries)
        manifest = {
            "schema_version": CATALOG_SCHEMA,
            "candidate_schema_version": "FINSIGHT-US-LATEST-500-CANDIDATE-1",
            "catalog_schema_version": CATALOG_SCHEMA,
            "catalog_kind": "latest_refresh_candidate",
            "catalog_version": f"US-RESET-2026-08-14-B01-B50-LATEST-{candidate_id}",
            "base_catalog_version": baseline.catalog_version,
            "base_manifest_sha256": baseline.manifest_sha256,
            "universe_version": baseline.universe_version,
            "valuation_date": baseline.valuation_date,
            "refresh_cutoff": discovery["cutoff"],
            "source_snapshot": source_snapshot,
            "created_at": input_fingerprint["source_snapshot"],
            "artifact_count": 500,
            "availability_counts": {name: counts.get(name, 0) for name in sorted({"available", "conditional_estimate", "not_available"})},
            "publication_counts": dict(sorted(Counter(str(json.loads((artifacts / f"{entry['ticker']}.json").read_text()).get("review", {}).get("publication_state", "missing")) for entry in entries).items())),
            "included_batches": list(baseline.included_batches),
            "entries": entries,
            "private_recipe_sha256": recipe_hashes,
            "refresh_status": {row["ticker"]: {key: row[key] for key in ("outcome", "recommendation", "new_source_date", "new_source_accession")} for row in report_rows},
            "input_fingerprints": input_fingerprint,
            "source_fingerprint_summary": source_fingerprint_summary,
        }
        manifest["artifact_tree_sha256"] = artifact_tree_sha256(entries)
        (stage / "manifest.json").write_bytes(canonical_json_bytes(manifest))
        # The catalog loader validates the standard artifact/manifest contract.
        load_catalog_version(stage)
        assembly_report = {
            "schema_version": "FINSIGHT-LATEST-500-ASSEMBLY-1",
            "candidate_id": candidate_id,
            "catalog_version": manifest["catalog_version"],
            "scope": "non-activated latest 500 release candidate",
            "cutoff": discovery["cutoff"],
            "source_snapshot": source_snapshot,
            "counts": dict(sorted(status_counts.items())),
            "rows": report_rows,
            "input_fingerprints": input_fingerprint,
            "source_fingerprint_summary": source_fingerprint_summary,
            "activated": False,
        }
        (stage / "assembly-report.json").write_bytes(canonical_json_bytes(assembly_report))
        lines = ["# Latest 500 release candidate", "", json.dumps(assembly_report["counts"], sort_keys=True), "", "| Company | Outcome | Old Low / Base / High | New Low / Base / High | Source date | Recommendation |", "|---|---|---:|---:|---|---|"]
        for row in report_rows:
            old = " / ".join("—" if row["old_range"][key] is None else f"{row['old_range'][key]:.8f}" for key in ("low", "base", "high"))
            new = " / ".join("—" if row["new_range"][key] is None else f"{row['new_range'][key]:.8f}" for key in ("low", "base", "high"))
            lines.append(f"| {row['ticker']} | {row['outcome']} | {old} | {new} | {row['new_source_date'] or '—'} | {row['recommendation'].replace('|', '/')} |")
        (stage / "assembly-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        stage.replace(candidate_root)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return {"candidate_id": candidate_id, "candidate_root": str(candidate_root), "catalog_version": manifest["catalog_version"], "counts": dict(sorted(status_counts.items())), "activated": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--discovery-report", type=Path, required=True)
    parser.add_argument("--source-validation-report", type=Path, action="append", required=True)
    parser.add_argument("--targeted-reviews", type=Path, required=True)
    parser.add_argument("--unchanged-verification", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(assemble(**vars(args)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
