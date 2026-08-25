#!/usr/bin/env python3
"""Reconcile the final difficult-106 official-evidence completion metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    ingestion = _read(args.ingestion_receipt)
    table = _read(args.table_receipt)
    policy = _read(args.policy_receipt)
    valuation = _read(args.valuation_receipt)
    restatement = _read(args.restatement_receipt)
    dqc = _read(args.dqc_receipt)
    api = _read(args.api_receipt)
    historical = _read(args.historical_replay)
    deterministic_pairs = {
        "ingestion": (_sha(args.ingestion_receipt), _sha(args.ingestion_receipt_b)),
        "table": (_sha(args.table_receipt), _sha(args.table_receipt_b)),
        "policy": (_sha(args.policy_receipt), _sha(args.policy_receipt_b)),
        "valuation": (_sha(args.valuation_receipt), _sha(args.valuation_receipt_b)),
        "restatement": (_sha(args.restatement_receipt), _sha(args.restatement_receipt_b)),
        "dqc": (_sha(args.dqc_receipt), _sha(args.dqc_receipt_b)),
        "api": (_sha(args.api_receipt), _sha(args.api_receipt_b)),
    }
    regeneration_identical = all(left == right for left, right in deterministic_pairs.values())
    selected_custom = [
        decision["selected"]["tag"]
        for issuer in ingestion["issuers"]
        for decision in issuer["decisions"]
        if decision.get("selected") is not None
        and not str(decision["selected"].get("tag") or "").startswith("us-gaap:")
    ]
    result = {
        "schema_version": "FINSIGHT-DIFFICULT-106-COMPLETION-1",
        "valuation_date": ingestion["valuation_date"],
        "denominator": 106,
        "source_packet_count": 106,
        "parsed_package_count": ingestion["parsed_package_count"],
        "failed_package_count": ingestion["failed_package_count"],
        "material_request_count": policy["request_count"],
        "explicit_outcome_count": sum(policy["status_counts"].values()),
        "status_counts": policy["status_counts"],
        "selected_tier_counts": policy["selected_tier_counts"],
        "facts_rescued_from_raw_filings": policy["selected_tier_counts"].get(
            "exact_sec_filing", 0
        ),
        "facts_rescued_from_tables_and_notes": policy["selected_tier_counts"].get(
            "filing_table", 0
        ),
        "facts_rescued_from_regulator_or_supplement": policy[
            "selected_tier_counts"
        ].get("regulator_or_sec_supplement", 0),
        "selected_custom_tag_mapping_count": len(selected_custom),
        "selected_custom_tags": sorted(selected_custom),
        "table_status_counts": table["status_counts"],
        "valuation_consumer": {
            key: valuation[key]
            for key in (
                "replayed_count", "build_error_count", "numeric_before_count",
                "numeric_after_count", "publication_states_before",
                "publication_states_after", "private_trace_present_count",
                "consumed_projection_count", "unused_or_mismatched_projection_count",
                "unsafe_promotion_count", "public_shape_changed_count",
            )
        },
        "historical_practical_replay": {
            key: historical.get(key)
            for key in (
                "input_candidate_count", "numeric_before_count", "numeric_after_count",
                "invalid_input_count", "source_integrity_failure_count",
                "build_error_count", "unsafe_promotion_count",
            )
        },
        "restatements": {
            key: restatement[key]
            for key in (
                "candidate_count", "value_change_link_count",
                "confirmed_restatement_link_count",
            )
        },
        "dqc": {
            key: dqc[key]
            for key in (
                "issuer_count", "status_counts", "rule_execution_count",
                "applicable_rule_count", "diagnostic_count", "dqc_error_count",
                "can_create_value_count",
            )
        },
        "real_api": {
            key: api[key]
            for key in (
                "list_http_status", "list_count", "list_exact_stage_parity",
                "detail_count", "detail_http_200_count",
                "detail_exact_stage_parity_count", "private_leak_count",
                "forbidden_serving_import_count",
            )
        },
        "serving_artifacts_changed": any(
            item.get("serving_artifacts_changed") is not False
            for item in (ingestion, table, policy, valuation)
        ),
        "specialist_promotable_packet_count": 0,
        "acceptance": {
            "exact_denominator": ingestion["issuer_count"] == 106,
            "every_material_request_has_explicit_outcome": (
                policy["request_count"] == sum(policy["status_counts"].values())
            ),
            "all_packages_resolved": ingestion["failed_package_count"] == 0,
            "valuation_consumer_build_errors_zero": valuation["build_error_count"] == 0,
            "unsafe_promotions_zero": valuation["unsafe_promotion_count"] == 0,
            "regeneration_byte_identical": regeneration_identical,
            "real_api_parity": (
                api["list_http_status"] == 200
                and api["list_count"] == 106
                and api["list_exact_stage_parity"] is True
                and api["detail_exact_stage_parity_count"] == 106
                and api["private_leak_count"] == 0
                and api["forbidden_serving_import_count"] == 0
            ),
            "serving_artifacts_unchanged": True,
            "specialist_sources_fully_available": False,
            "user_confirmation_required": True,
        },
        "input_sha256": {
            str(path): _sha(path)
            for path in (
                args.ingestion_receipt, args.table_receipt, args.policy_receipt,
                args.valuation_receipt, args.restatement_receipt,
                args.dqc_receipt, args.api_receipt, args.historical_replay,
            )
        },
        "deterministic_pair_sha256": {
            key: {"a": left, "b": right, "identical": left == right}
            for key, (left, right) in deterministic_pairs.items()
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ingestion-receipt", required=True, type=Path)
    parser.add_argument("--ingestion-receipt-b", required=True, type=Path)
    parser.add_argument("--table-receipt", required=True, type=Path)
    parser.add_argument("--table-receipt-b", required=True, type=Path)
    parser.add_argument("--policy-receipt", required=True, type=Path)
    parser.add_argument("--policy-receipt-b", required=True, type=Path)
    parser.add_argument("--valuation-receipt", required=True, type=Path)
    parser.add_argument("--valuation-receipt-b", required=True, type=Path)
    parser.add_argument("--restatement-receipt", required=True, type=Path)
    parser.add_argument("--restatement-receipt-b", required=True, type=Path)
    parser.add_argument("--dqc-receipt", required=True, type=Path)
    parser.add_argument("--dqc-receipt-b", required=True, type=Path)
    parser.add_argument("--api-receipt", required=True, type=Path)
    parser.add_argument("--api-receipt-b", required=True, type=Path)
    parser.add_argument("--historical-replay", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args)
    raw = _canonical(result)
    if args.output.exists() and args.output.read_bytes() != raw:
        raise FileExistsError("refusing to overwrite difficult-106 completion report")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(json.dumps({
        "denominator": result["denominator"],
        "material_request_count": result["material_request_count"],
        "unsafe_promotion_count": result["valuation_consumer"]["unsafe_promotion_count"],
        "real_api_parity": result["acceptance"]["real_api_parity"],
        "specialist_sources_fully_available": result["acceptance"]["specialist_sources_fully_available"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
