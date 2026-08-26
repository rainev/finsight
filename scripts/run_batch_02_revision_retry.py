#!/usr/bin/env python3
"""Retry Batch 02 holdouts against the revised official-evidence pipeline."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_02 import BATCH_02_MANIFEST, BATCH_02_TICKERS
from app.us_valuation.batch_02_recovery import RECOVERY_DECISIONS, RECOVERY_TICKERS
from app.us_valuation.batch_02_revision_retry import (
    REVISION_RETRY_DECISIONS,
    REVISION_RETRY_VERSION,
)


PROTECTED_ROOTS = (
    ROOT / "backend/app/data/us_valuation_catalogs",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
            digest.update(b"\n")
    return digest.hexdigest()


def _immutable(path: Path, raw: bytes) -> None:
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite immutable retry output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent))
    try:
        candidate = staging / path.name
        candidate.write_bytes(raw)
        candidate.replace(path)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _validate_inputs(
    prior_root: Path,
    policy_a_path: Path,
    policy_b_path: Path,
    full_replay_path: Path,
    output_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    for path in (prior_root, policy_a_path, policy_b_path, full_replay_path):
        if not path.exists():
            raise ValueError(f"retry input does not exist: {path}")
    target = output_root.resolve(strict=False)
    if target.is_relative_to(prior_root.resolve()) or prior_root.resolve().is_relative_to(target):
        raise ValueError("retry output must be separate from the prior recovery root")
    if any(target.is_relative_to(root.resolve()) for root in PROTECTED_ROOTS):
        raise ValueError("retry output must be outside serving roots")
    if policy_a_path.read_bytes() != policy_b_path.read_bytes():
        raise ValueError("official-evidence policy A/B inputs are not deterministic")
    policy = json.loads(policy_a_path.read_text())
    if (
        policy.get("valuation_date") != "2026-08-14"
        or policy.get("issuer_count") != 10
        or policy.get("serving_artifacts_changed") is not False
        or {row.get("ticker") for row in policy.get("issuers", [])}
        != set(BATCH_02_TICKERS)
    ):
        raise ValueError("official-evidence policy input violates Batch 02 contract")
    replay = json.loads(full_replay_path.read_text())
    consumer = replay.get("valuation_consumer_replay", {})
    if (
        replay.get("valuation_date") != "2026-08-14"
        or consumer.get("build_error_count") != 0
        or consumer.get("unused_or_mismatched_projection_count") != 0
        or replay.get("acceptance", {}).get("serving_artifacts_unchanged") is not True
    ):
        raise ValueError("full replay does not pass the real-consumer safety contract")
    return policy, replay


def _evidence_summary(issuer: dict[str, Any]) -> dict[str, Any]:
    selected = []
    status_counts: dict[str, int] = {}
    for decision in issuer.get("decisions", []):
        request = decision.get("request", {})
        status = decision.get("status")
        field = request.get("required_field")
        if not isinstance(field, str) or not isinstance(status, str):
            raise ValueError(f"{issuer.get('ticker')}: malformed policy decision")
        status_counts[status] = status_counts.get(status, 0) + 1
        selected.append(
            {
                "required_field": field,
                "status": status,
                "selected_source": decision.get("selected_source"),
                "selected_value": decision.get("selected_value"),
                "selected_range": decision.get("selected_range"),
                "reason_codes": decision.get("reason_codes", []),
                "request_id": request.get("request_id"),
            }
        )
    return {
        "request_count": len(selected),
        "status_counts": dict(sorted(status_counts.items())),
        "decisions": sorted(selected, key=lambda row: row["required_field"]),
    }


def run_revision_retry(
    *,
    prior_root: Path,
    policy_a_path: Path,
    policy_b_path: Path,
    full_replay_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    prior_root = Path(prior_root)
    policy_a_path = Path(policy_a_path)
    policy_b_path = Path(policy_b_path)
    full_replay_path = Path(full_replay_path)
    output_root = Path(output_root)
    policy, replay = _validate_inputs(
        prior_root, policy_a_path, policy_b_path, full_replay_path, output_root
    )
    prior_report = json.loads((prior_root / "recovery-report.json").read_text())
    if (
        prior_report.get("recovery_attempted_count") != 6
        or prior_report.get("recovered_numeric_count") != 0
        or prior_report.get("still_withheld_count") != 6
    ):
        raise ValueError("prior recovery report violates the retry baseline")

    policy_by_ticker = {row["ticker"]: row for row in policy["issuers"]}
    replay_cases = {
        row["ticker"]: row
        for row in replay["valuation_consumer_replay"]["cases"]
        if row.get("ticker") in RECOVERY_TICKERS
    }
    if set(replay_cases) != set(RECOVERY_TICKERS):
        raise ValueError("full replay does not contain the exact six retry issuers")
    decisions = {row.ticker: row for row in REVISION_RETRY_DECISIONS}
    recovery = {row.ticker: row for row in RECOVERY_DECISIONS}
    before = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    cases = []

    for issuer in BATCH_02_MANIFEST:
        private_path = prior_root / "generated" / issuer.ticker / "valuation-private.json"
        public_path = prior_root / "staged-public" / f"{issuer.ticker}.json"
        private = json.loads(private_path.read_text())
        public_raw = public_path.read_bytes()
        public = json.loads(public_raw)
        if sanitize_public_artifact(public) != public:
            raise ValueError(f"{issuer.ticker}: prior public artifact is not canonical")

        if issuer.ticker in decisions:
            replay_case = replay_cases[issuer.ticker]
            if (
                replay_case.get("status") != "replayed"
                or replay_case.get("private_trace_present") is not True
                or replay_case.get("enhanced_numeric") is not False
                or replay_case.get("enhanced_publication_state") != "withheld"
                or replay_case.get("projection_count")
                != replay_case.get("consumed_projection_count")
                or replay_case.get("unused_or_mismatched_projection_count") != 0
            ):
                raise ValueError(f"{issuer.ticker}: revised real-consumer replay is unsafe")
            assessment = decisions[issuer.ticker]
            original = recovery[issuer.ticker]
            evidence = _evidence_summary(policy_by_ticker[issuer.ticker])
            private["pipeline_revision_retry"] = {
                **asdict(assessment),
                "retry_number": 1,
                "retry_version": REVISION_RETRY_VERSION,
                "final_outcome": "withheld",
                "recovery_model": original.recovery_model,
                "hard_blockers": list(original.hard_blockers),
                "official_evidence": evidence,
                "consumer_replay": replay_case,
                "public_artifact_changed": False,
            }
            cases.append(
                {
                    "ticker": issuer.ticker,
                    "attempted": True,
                    "prior_blocker_cleared": False,
                    "recovered_numeric": False,
                    "final_outcome": "withheld",
                    "evidence_status_counts": evidence["status_counts"],
                    "remaining_release_condition": assessment.remaining_release_condition,
                }
            )
        else:
            private["pipeline_revision_retry"] = None

        _immutable(
            output_root / "generated" / issuer.ticker / "valuation-private.json",
            _json_bytes(private),
        )
        _immutable(output_root / "staged-public" / public_path.name, public_raw)

    after = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    if before != after:
        raise RuntimeError("protected serving artifacts changed")
    summary = {
        "schema_version": "FINSIGHT-BATCH-02-REVISION-RETRY-REPORT-1",
        "batch": 2,
        "retry_version": REVISION_RETRY_VERSION,
        "valuation_date": "2026-08-14",
        "denominator_tickers": list(RECOVERY_TICKERS),
        "pipeline_revision_retry_count": 6,
        "newly_recovered_numeric_count": 0,
        "still_withheld_count": 6,
        "final_batch_numeric_count": 4,
        "final_batch_withheld_count": 6,
        "public_artifact_changed_count": 0,
        "official_policy_sha256": _sha256(policy_a_path),
        "full_replay_sha256": _sha256(full_replay_path),
        "prior_recovery_report_sha256": _sha256(prior_root / "recovery-report.json"),
        "serving_hash_before": before,
        "serving_hash_after": after,
        "serving_artifacts_changed": False,
        "cases": cases,
    }
    _immutable(output_root / "revision-retry-report.json", _json_bytes(summary))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-root", required=True, type=Path)
    parser.add_argument("--policy-a-path", required=True, type=Path)
    parser.add_argument("--policy-b-path", required=True, type=Path)
    parser.add_argument("--full-replay-path", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    summary = run_revision_retry(**vars(parser.parse_args()))
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "pipeline_revision_retry_count",
                    "newly_recovered_numeric_count",
                    "still_withheld_count",
                    "final_batch_numeric_count",
                    "final_batch_withheld_count",
                    "serving_artifacts_changed",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
