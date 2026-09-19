#!/usr/bin/env python3
"""Verify frozen numeric baselines against unchanged SEC metadata.

This command is a qualification report only.  It never binds a new filing,
changes a recipe, stages a candidate, or publishes a catalog.
"""

from __future__ import annotations

import argparse
import io
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.calculation_recipe import evaluate_recipe  # noqa: E402
from app.us_valuation.catalog import canonical_json_bytes  # noqa: E402
from app.us_valuation.refresh_job import atomic  # noqa: E402
from app.us_valuation.refresh_disclosure_impact import (  # noqa: E402
    classify_non_economic_amendments,
)
from app.us_valuation.refresh_event_review import (  # noqa: E402
    EventReviewError,
    EventReviewIncomplete,
    review_event_records,
)


SCHEMA_VERSION = "FINSIGHT-LATEST-UNCHANGED-VERIFICATION-1"
EXPECTED_COUNT = 500
MATERIAL_FORM_PREFIXES = ("424B", "S-1", "S-3", "S-4", "S-8", "S-11", "15", "25", "SC13E", "F-")
MATERIAL_FORMS = frozenset({"FWP", "425"})
STATUS_ORDER = (
    "integrity_error",
    "prior_unavailable",
    "targeted_review",
    "acquisition_pending_or_failed",
    "event_review",
    "source_changed",
    "verified_unchanged",
)


def _read_json_bytes(path: Path) -> tuple[bytes, Any]:
    raw = path.read_bytes()
    return raw, json.loads(raw)


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _finite_range(value: Any) -> bool:
    return isinstance(value, Mapping) and all(
        isinstance(value.get(key), (int, float))
        and not isinstance(value.get(key), bool)
        and math.isfinite(float(value[key]))
        for key in ("low", "base", "high")
    )


def _same_range(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(math.isclose(float(left[key]),float(right[key]),rel_tol=1e-9,abs_tol=1e-7)
               for key in ("low", "base", "high"))


def _ticker_equivalent(original: str, reported: Any) -> bool:
    if not isinstance(reported, str):
        return False
    # SEC occasionally presents BF.B as BF-B. No other normalization is allowed.
    return original.upper().replace(".", "-") == reported.upper().replace(".", "-")


def _material_form(form: Any) -> bool:
    if not isinstance(form, str):
        return False
    upper = form.upper().strip()
    return (
        upper in MATERIAL_FORMS
        or upper.startswith(MATERIAL_FORM_PREFIXES)
        or upper.endswith("/A")
        or upper in {"8-K", "8-K/A"}
    )


def _recent_submissions(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_bytes())
    if not isinstance(payload, Mapping) or not isinstance(payload.get("filings", {}).get("recent"), Mapping):
        raise ValueError(f"{path}: submissions recent metadata missing")
    return dict(payload)


def _records(submissions: Mapping[str, Any]) -> list[dict[str, Any]]:
    recent = submissions["filings"]["recent"]
    accessions = recent.get("accessionNumber")
    if not isinstance(accessions, list):
        raise ValueError("submissions accession metadata missing")
    return [
        {
            key: values[index]
            for key, values in recent.items()
            if isinstance(values, list) and index < len(values)
        }
        for index in range(len(accessions))
    ]


def _frozen_capture_inputs(latest_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    # Read the report and descriptors once. Later checks operate on these frozen
    # objects, so a concurrent writer cannot change the qualification decision.
    capture_input_raw, capture_input = _read_json_bytes(latest_root / "capture-input.json")
    discovery_raw, discovery = _read_json_bytes(latest_root / "discovery-report.json")
    capture_raw, capture = _read_json_bytes(latest_root / "capture-report.json")
    if capture_input.get("schema_version") != "FINSIGHT-LATEST-500-CAPTURE-1":
        raise ValueError("unsupported latest capture descriptor")
    if capture_input.get("discovery_sha256") != _sha_bytes(discovery_raw):
        raise ValueError("discovery report hash does not match capture descriptor")
    if capture.get("cutoff") != capture_input.get("cutoff"):
        raise ValueError("capture report cutoff does not match capture descriptor")
    if capture.get("retrieval_snapshot_timestamp") != capture_input.get("retrieval_snapshot_timestamp"):
        raise ValueError("capture report snapshot does not match capture descriptor")
    return capture_input, discovery, capture, {
        "capture_input_sha256": _sha_bytes(capture_input_raw),
        "discovery_sha256": _sha_bytes(discovery_raw),
        "capture_report_sha256": _sha_bytes(capture_raw),
    }


def _freeze_wrappers(latest_root: Path, capture: Mapping[str, Any], capture_input: Mapping[str, Any], registry: Mapping[str, Any], *, wanted: set[str] | None = None) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    entries = {str(row["ticker"]): row for row in registry.get("entries", []) if isinstance(row, Mapping)}
    rows = capture.get("rows")
    if not isinstance(rows, list):
        raise ValueError("capture report rows missing")
    wrappers: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("ticker"), str):
            errors[str(row.get("ticker", ""))] = "invalid capture report row"
            continue
        ticker = str(row["ticker"])
        if wanted is not None and ticker not in wanted:
            continue
        if row.get("status") != "captured":
            errors[ticker] = "capture_pending_or_failed: " + str(row.get("error") or row.get("cause") or "capture did not complete")
            continue
        path_value = row.get("receipt_path")
        if not isinstance(path_value, str):
            errors[ticker] = "captured row has no receipt path"
            continue
        path = Path(path_value)
        if not path.is_absolute():
            path = latest_root / path
        path = path.resolve()
        try:
            path.relative_to(latest_root)
        except ValueError:
            errors[ticker] = "capture receipt is outside frozen latest-root"
            continue
        try:
            raw = path.read_bytes()
            if row.get("receipt_sha256") != _sha_bytes(raw):
                raise ValueError("capture wrapper byte hash mismatch")
            if path.suffix == ".gz":
                with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as stream:
                    wrapper = json.load(stream)
            else:
                wrapper = json.loads(raw)
            entry = entries.get(ticker)
            if entry is None or wrapper.get("ticker") != ticker or str(wrapper.get("cik", "")).zfill(10) != str(entry["cik"]).zfill(10):
                raise ValueError("capture wrapper identity mismatch")
            for key in ("cutoff", "expected_count", "discovery_sha256", "retrieval_snapshot_timestamp"):
                expected = capture_input.get(key) if key != "discovery_sha256" else capture_input.get("discovery_sha256")
                if wrapper.get(key) != expected:
                    raise ValueError(f"capture wrapper {key} mismatch")
            packet = wrapper.get("packet")
            if not isinstance(packet, Mapping) or wrapper.get("packet_sha256") != _sha_bytes(canonical_json_bytes(packet)):
                raise ValueError("capture wrapper packet hash mismatch")
            issuer = packet.get("issuer")
            if not isinstance(issuer, Mapping) or issuer.get("ticker") != ticker or str(issuer.get("cik", "")).zfill(10) != str(entry["cik"]).zfill(10):
                raise ValueError("capture packet issuer identity mismatch")
            wrappers[ticker] = {
                "receipt_path": str(path),
                "receipt_sha256": row.get("receipt_sha256"),
                "packet_sha256": wrapper.get("packet_sha256"),
                "retrieval_snapshot_timestamp": wrapper.get("retrieval_snapshot_timestamp"),
                "packet": packet,
            }
        except (OSError, ValueError, json.JSONDecodeError, gzip.BadGzipFile) as exc:
            errors[ticker] = str(exc)
    return wrappers, errors


def _load_targeted(runtime_root: Path) -> set[str]:
    path = runtime_root / "targeted-reviews.json"
    if not path.is_file():
        return set()
    value = json.loads(path.read_bytes())
    companies = value.get("companies", {}) if isinstance(value, Mapping) else {}
    return set(companies) if isinstance(companies, Mapping) else set()


def _baseline_and_recipe(runtime_root: Path, registry: Mapping[str, Any], ticker: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    recipe_path = runtime_root / "recipes" / f"{ticker}.json"
    artifact_path = runtime_root / "baseline" / "artifacts" / f"{ticker}.json"
    if not recipe_path.is_file() or not artifact_path.is_file():
        return None, None, "numeric baseline recipe or artifact missing"
    try:
        recipe = json.loads(recipe_path.read_bytes())
        artifact = json.loads(artifact_path.read_bytes())
        baseline_entry = next(row for row in registry["entries"] if row.get("ticker") == ticker)
        if baseline_entry.get("baseline_sha256") != _sha_bytes(artifact_path.read_bytes()):
            return recipe, artifact, "baseline artifact hash mismatch"
        replay = evaluate_recipe(recipe)["range"]
        recorded_replay = recipe.get("replay")
        recorded_range = artifact.get("scenario_range")
        if not _finite_range(replay) or not _finite_range(recorded_replay) or not _finite_range(recorded_range):
            return recipe, artifact, "baseline replay is not finite"
        if not _same_range(replay, recorded_replay) or not _same_range(replay, recorded_range):
            return recipe, artifact, "original recipe replay differs from baseline"
        return recipe, artifact, None
    except Exception as exc:  # qualification report records, rather than hides, malformed baselines
        return None, None, f"baseline replay error: {exc}"


def verify_latest_unchanged(
    *,
    runtime_root: Path,
    latest_root: Path,
    output_path: Path,
    mandatory_targets: set[str] | None = None,
) -> dict[str, Any]:
    runtime_root = Path(runtime_root).resolve()
    latest_root = Path(latest_root).resolve()
    capture_input, discovery, capture, frozen_hashes = _frozen_capture_inputs(latest_root)
    registry_raw, registry = _read_json_bytes(runtime_root / "registry.json")
    manifest_raw, manifest = _read_json_bytes(runtime_root / "baseline" / "manifest.json")
    if _sha_bytes(manifest_raw) != registry.get("baseline_manifest_sha256"):
        raise ValueError("baseline manifest hash does not match registry")
    entries = registry.get("entries")
    discovery_rows = discovery.get("rows")
    if not isinstance(entries, list) or not isinstance(discovery_rows, list):
        raise ValueError("registry/discovery rows missing")
    registry_by_ticker = {str(row.get("ticker")): row for row in entries if isinstance(row, Mapping)}
    discovery_by_ticker = {str(row.get("ticker")): row for row in discovery_rows if isinstance(row, Mapping)}
    all_tickers = set(registry_by_ticker)
    global_errors: list[str] = []
    if len(all_tickers) != EXPECTED_COUNT or len(discovery_by_ticker) != EXPECTED_COUNT or set(discovery_by_ticker) != all_tickers:
        global_errors.append("frozen registry/discovery does not contain exactly 500 matching identities")
    targeted = _load_targeted(runtime_root) | set(mandatory_targets or ())
    policies_raw, policies = _read_json_bytes(runtime_root / "refresh-policies.json")
    reviewed_tickers = {
        ticker for ticker, policy in policies.items()
        if isinstance(policy, Mapping) and isinstance(policy.get("reviewed_events"), Mapping)
        and policy["reviewed_events"]
    }
    # Load full wrappers only for the small set carrying exact, hash-bound event
    # reviews.  The other unchanged rows still avoid repeated structural-tree
    # decompression.
    wrappers, wrapper_errors = _freeze_wrappers(
        latest_root,
        capture,
        capture_input,
        registry,
        wanted=reviewed_tickers,
    )
    capture_by_ticker={str(row.get('ticker')):row for row in capture.get('rows',[]) if isinstance(row,Mapping)}
    rows: list[dict[str, Any]] = []
    # The verifier accepts either the refresh root (which contains a
    # final-discovery child) or the frozen discovery root itself.  Bind the
    # submissions directory once and fail later per issuer if it is absent.
    final_sec = latest_root / "sec-cache"
    if not final_sec.is_dir():
        final_sec = latest_root / "final-discovery" / "sec-cache"
    cutoff = str(capture_input.get("cutoff"))
    snapshot = capture_input.get("retrieval_snapshot_timestamp")
    for ticker in sorted(all_tickers):
        entry = registry_by_ticker[ticker]
        row = {"ticker": ticker, "cik": str(entry.get("cik", "")).zfill(10), "verification_snapshot": snapshot}
        recipe, artifact, replay_error = _baseline_and_recipe(runtime_root, registry, ticker)
        if replay_error:
            row.update(state="prior_unavailable" if "missing" in replay_error or recipe is None else "integrity_error", reason=replay_error)
            rows.append(row)
            continue
        row.update(previous_range=dict(recipe["replay"]), financial_date=recipe.get("evidence_cutoff"), baseline_source_accession=recipe.get("source_accession"))
        capture_row=capture_by_ticker.get(ticker)
        capture_state=('captured' if capture_row and capture_row.get('status')=='captured'
            else 'failed' if capture_row else 'pending')
        row['capture_wrapper']={'state':capture_state,
            'receipt_sha256':capture_row.get('receipt_sha256') if capture_row else None,
            'reason':capture_row.get('error') if capture_row else None}
        if ticker in wrapper_errors:
            wrapper_pending = str(wrapper_errors[ticker]).startswith("capture_pending_or_failed:")
            row["capture_wrapper"] = {"state": "acquisition_pending_or_failed" if wrapper_pending else "integrity_error", "reason": wrapper_errors[ticker]}
        elif ticker in wrappers:
            row["capture_wrapper"] = {k: v for k, v in wrappers[ticker].items() if k != "packet"}
        discovery_row = discovery_by_ticker.get(ticker, {})
        latest_regular = discovery_row.get("latest_regular") or {}
        latest_annual = discovery_row.get("latest_annual") or {}
        current_accession = latest_regular.get("accessionNumber")
        changed_regular = bool(discovery_row.get("changed_regular"))
        post_forms: list[dict[str, Any]] = []
        submissions_path = final_sec / f"CIK{row['cik']}-submissions.json"
        try:
            submissions = _recent_submissions(submissions_path)
            sec_tickers = submissions.get("tickers", [])
            if not any(_ticker_equivalent(ticker, value) for value in sec_tickers):
                raise ValueError("original ticker is absent from SEC ticker metadata")
            for record in _records(submissions):
                filed = record.get("filingDate")
                if not isinstance(filed, str) or not recipe.get("evidence_cutoff") < filed <= cutoff:
                    continue
                form = record.get("form")
                if _material_form(form):
                    post_forms.append({key: record.get(key) for key in ("accessionNumber", "filingDate", "reportDate", "form", "items", "primaryDocument")})
        except Exception as exc:
            row.update(state="integrity_error", reason=f"SEC submissions metadata error: {exc}")
            rows.append(row)
            continue
        row["post_baseline_material_forms"] = post_forms
        non_economic_disclosures = classify_non_economic_amendments(
            post_forms,
            prior_cutoff=str(recipe.get("evidence_cutoff")),
            cutoff=cutoff,
            submissions_sha256=str(discovery_row.get("submissions_sha256") or ""),
            changed_regular=bool(discovery_row.get("changed_regular")),
        )
        if non_economic_disclosures is not None:
            row["disclosure_impact"] = non_economic_disclosures
        reviewed_event_impact = None
        policy = policies.get(ticker)
        wrapper = wrappers.get(ticker)
        if (
            not changed_regular
            and post_forms
            and isinstance(policy, Mapping)
            and isinstance(wrapper, Mapping)
            and all(record.get("form") in {"8-K", "8-K/A"} for record in post_forms)
        ):
            try:
                event_rows = review_event_records(
                    post_forms,
                    list(wrapper["packet"].get("events", [])),
                    policy,
                    prior_cutoff=str(recipe.get("evidence_cutoff")),
                    cutoff=cutoff,
                    require_exhibits=True,
                    controlling_filing=latest_regular,
                )
                expected_accessions = {str(record.get("accessionNumber")) for record in post_forms}
                reviewed_accessions = {str(record.get("accession")) for record in event_rows}
                if expected_accessions == reviewed_accessions:
                    reviewed_event_impact = {
                        "classification": "exact_reviewed_no_current_input_change",
                        "policy_sha256": _sha_bytes(policies_raw),
                        "capture_receipt_sha256": wrapper["receipt_sha256"],
                        "events": event_rows,
                    }
                    row["reviewed_event_impact"] = reviewed_event_impact
            except (EventReviewError, EventReviewIncomplete, TypeError, ValueError):
                reviewed_event_impact = None
        annual_ok = (
            isinstance(latest_annual.get("filingDate"), str)
            and latest_annual.get("filingDate") <= recipe["evidence_cutoff"]
            and (not latest_annual.get("reportDate") or latest_annual.get("reportDate") <= recipe["evidence_cutoff"])
        )
        same_regular = current_accession == recipe.get("source_accession")
        capture_missing_for_change = (changed_regular or bool(post_forms)) and capture_state!='captured'
        wrapper_pending = str(wrapper_errors.get(ticker, "")).startswith("capture_pending_or_failed:")
        wrapper_integrity = ticker in wrapper_errors and not wrapper_pending
        if global_errors:
            state, reason = "integrity_error", "; ".join(global_errors)
        elif wrapper_integrity:
            state, reason = "integrity_error", wrapper_errors[ticker]
        elif not annual_ok:
            state, reason = "source_changed", "latest annual filing is newer than original recipe cutoff"
        elif ticker in targeted:
            state, reason = "targeted_review", "excluded by mandatory/runtime targeted review list"
        elif non_economic_disclosures is not None and not changed_regular:
            state, reason = "verified_unchanged", "only source-identified non-economic ownership or insider amendments followed the approved evidence cutoff"
        elif reviewed_event_impact is not None:
            state, reason = "verified_unchanged", "all newer current reports have exact hash-bound reviews proving no current numeric input change"
        elif wrapper_pending or capture_missing_for_change:
            state, reason = "acquisition_pending_or_failed", (capture_row or {}).get('error') or "changed/event filing lacks a captured wrapper"
        elif post_forms:
            state, reason = "event_review", "post-baseline potentially material SEC filing(s) require review"
        elif not same_regular:
            state, reason = "source_changed", "controlling regular filing accession changed"
        else:
            state, reason = "verified_unchanged", "controlling regular and annual filings remain unchanged"
        row.update(state=state, reason=reason, current_regular_accession=current_accession, current_regular_period=latest_regular.get("reportDate"), latest_annual_accession=latest_annual.get("accessionNumber"))
        rows.append(row)
    counts = {state: sum(1 for row in rows if row.get("state") == state) for state in STATUS_ORDER}
    report = {
        "schema_version": SCHEMA_VERSION,
        "cutoff": cutoff,
        "verification_snapshot": snapshot,
        "expected_count": EXPECTED_COUNT,
        "identity_count": len(rows),
        "counts": counts,
        "input_hashes": {**frozen_hashes, "registry_sha256": _sha_bytes(registry_raw), "baseline_manifest_sha256": _sha_bytes(manifest_raw), "refresh_policies_sha256": _sha_bytes(policies_raw)},
        "rows": rows,
    }
    report["report_sha256"] = _sha_bytes(canonical_json_bytes(report))
    payload = canonical_json_bytes(report)
    atomic(Path(output_path), payload, immutable=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--latest-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mandatory-target", action="append", default=[])
    args = parser.parse_args()
    report = verify_latest_unchanged(
        runtime_root=args.runtime_root,
        latest_root=args.latest_root,
        output_path=args.output,
        mandatory_targets=set(args.mandatory_target),
    )
    print(json.dumps({"output": str(args.output), "report_sha256": report["report_sha256"], "counts": report["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
