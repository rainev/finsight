#!/usr/bin/env python3
"""Replay one official-evidence policy receipt through the real valuation consumer."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_official_evidence_full_replay import (
    PROTECTED_ROOTS,
    _canonical,
    _policy_safety,
    _read,
    _table_proof_index,
    _tree_hash,
    _valuation_replay,
)


def run(args: argparse.Namespace) -> dict:
    before = {str(root.resolve()): _tree_hash(root) for root in PROTECTED_ROOTS}
    policy = _read(args.policy_receipt)
    table = _read(args.table_receipt)
    proofs = _table_proof_index((table,), args.package_root)
    safety, statuses, tiers, attempts = _policy_safety(policy, proofs)
    cases, before_states, after_states = _valuation_replay(
        policy_receipts=(policy,),
        source_roots=(args.source_root,),
        output_root=args.output_root,
    )
    replayed = [item for item in cases if item.get("status") == "replayed"]
    unsafe = [item for item in safety if not item["safe"]]
    after = {str(root.resolve()): _tree_hash(root) for root in PROTECTED_ROOTS}
    if before != after:
        raise RuntimeError("protected serving artifacts changed")
    report = {
        "schema_version": "FINSIGHT-OFFICIAL-EVIDENCE-VALUATION-REPLAY-1",
        "valuation_date": policy["valuation_date"],
        "issuer_count": policy["issuer_count"],
        "request_count": len(safety),
        "explicit_outcome_count": sum(statuses.values()),
        "status_counts": dict(sorted(statuses.items())),
        "selected_tier_counts": dict(sorted(tiers.items())),
        "terminal_attempt_counts": dict(sorted(attempts.items())),
        "unsafe_promotion_count": len(unsafe),
        "unsafe_promotion_ledger": unsafe,
        "replayed_count": len(replayed),
        "build_error_count": sum(item.get("status") == "build_error" for item in cases),
        "source_packet_unavailable_count": sum(
            item.get("status") == "source_packet_unavailable" for item in cases
        ),
        "numeric_before_count": sum(item.get("baseline_numeric") is True for item in replayed),
        "numeric_after_count": sum(item.get("enhanced_numeric") is True for item in replayed),
        "publication_states_before": dict(sorted(before_states.items())),
        "publication_states_after": dict(sorted(after_states.items())),
        "public_changed_count": sum(item.get("public_changed") is True for item in replayed),
        "public_shape_changed_count": sum(
            item.get("public_shape_changed") is True for item in replayed
        ),
        "private_trace_present_count": sum(
            item.get("private_trace_present") is True for item in replayed
        ),
        "consumed_projection_count": sum(
            int(item.get("consumed_projection_count", 0)) for item in replayed
        ),
        "unused_or_mismatched_projection_count": sum(
            int(item.get("unused_or_mismatched_projection_count", 0)) for item in replayed
        ),
        "serving_hash_before": before,
        "serving_hash_after": after,
        "serving_artifacts_changed": False,
        "policy_receipt_sha256": hashlib.sha256(args.policy_receipt.read_bytes()).hexdigest(),
        "table_receipt_sha256": hashlib.sha256(args.table_receipt.read_bytes()).hexdigest(),
        "cases": cases,
    }
    report_path = args.output_root / "valuation-replay-report.json"
    raw = _canonical(report)
    if report_path.exists() and report_path.read_bytes() != raw:
        raise FileExistsError("refusing to overwrite valuation replay report")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(raw)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-receipt", required=True, type=Path)
    parser.add_argument("--table-receipt", required=True, type=Path)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({
        "issuer_count": result["issuer_count"],
        "request_count": result["request_count"],
        "replayed_count": result["replayed_count"],
        "build_error_count": result["build_error_count"],
        "numeric_before_count": result["numeric_before_count"],
        "numeric_after_count": result["numeric_after_count"],
        "unsafe_promotion_count": result["unsafe_promotion_count"],
        "serving_artifacts_changed": result["serving_artifacts_changed"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
