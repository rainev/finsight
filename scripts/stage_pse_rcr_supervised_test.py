#!/usr/bin/env python3
"""Stage the confirmed RCR distribution test outside the serving catalog root."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from app.pse_valuation.catalog import CATALOG_SCHEMA, POINTER_SCHEMA, load_pointer
from app.pse_valuation.contract import PseValuationArtifact, canonical_json, sha256_object
from app.pse_valuation.phase_b_batch_01 import build_batch_artifacts, load_batch_config


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/audit/evidence"
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
DECISION_PATH = EVIDENCE / "pse-rcr-staged-assumption-choices-2026-09-26.json"
WORKPAPER_PATH = EVIDENCE / "pse-rcr-supervised-refresh-2026-09-26.json"
DECISION_SHA256 = "8e0723b9b1296ad306cc1f2a40fdb9440f4fa9ebadb4dd51832b982ebfbeb923"
WORKPAPER_SHA256 = "15155cad06e61bda054f19ef02c5d98869502a4589ec3a19a9b885778673a9f7"
ACTIVE_POINTER_SHA256 = "50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92"
ACTIVE_MANIFEST_SHA256 = "8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7"
CATALOG_VERSION = "PSE-V2-RCR-SUPERVISED-2026-09-26-1.0"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pinned_json(path: Path, digest: str) -> dict:
    raw = path.read_bytes()
    if _sha256(raw) != digest:
        raise ValueError(f"pinned input changed: {path.name}")
    return json.loads(raw)


def _write_json(path: Path, value: dict) -> bytes:
    raw = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _check_active() -> None:
    active = SERVING_ROOT / "active.json"
    if _sha256(active.read_bytes()) != ACTIVE_POINTER_SHA256:
        raise ValueError("active catalog pointer changed since RCR test authorization")
    pointer = json.loads(active.read_text(encoding="utf-8"))
    manifest = SERVING_ROOT / pointer["catalog_path"] / "manifest.json"
    if _sha256(manifest.read_bytes()) != ACTIVE_MANIFEST_SHA256:
        raise ValueError("active catalog manifest changed since RCR test authorization")


def _receipt_sources(catalog_root: Path, decision: dict, workpaper: dict) -> list[dict]:
    quarterly = workpaper["quarterly_reported_distributions_per_share"]
    urls = {row["label"]: row["url"] for row in workpaper["sources"]}
    specs = [
        {
            "key": "fy2025-manager",
            "label": "RCR FY2025 Q4 fund-manager reviewed fact receipt; original PDF not hashed",
            "form": "fund_manager_report",
            "period_end": "2025-12-31",
            "published_at": "2026-02-11",
            "source_page": None,
            "url": urls["RCR FY2025 Q4 fund manager report, dividend table"],
            "facts": {"2025_Q3_dividend_per_share": quarterly["2025_Q3"], "2025_Q4_dividend_per_share": quarterly["2025_Q4"]},
        },
        {
            "key": "2026q2-manager",
            "label": "RCR 2Q2026 fund-manager reviewed fact receipt; original PDF not hashed",
            "form": "fund_manager_report",
            "period_end": "2026-06-30",
            "published_at": "2026-08-11",
            "source_page": 15,
            "url": urls["RCR 2Q2026 fund manager report, financial performance and investment return"],
            "facts": {"2026_Q1_dividend_per_share": quarterly["2026_Q1"], "2026_Q2_dividend_per_share": quarterly["2026_Q2"]},
        },
        {
            "key": "2026q2-dividend",
            "label": "RCR 2Q2026 PSE dividend reviewed fact receipt; original HTML not hashed",
            "form": "17-C",
            "period_end": "2026-06-30",
            "published_at": "2026-08-11",
            "source_page": None,
            "url": urls["RCR 2Q2026 PSE dividend disclosure"],
            "facts": {"dividend_per_share": quarterly["2026_Q2"], "distributable_income_php": workpaper["q2_2026_distributable_income_php"]},
        },
        {
            "key": "2026-stock",
            "label": "RCR 25 Sep 2026 PSE stock reviewed fact receipt; original HTML not hashed",
            "form": "stock_data",
            "period_end": "2026-09-25",
            "published_at": None,
            "source_page": None,
            "url": urls["RCR PSE stock data as of 2026-09-25"],
            "facts": {"outstanding_common_shares": workpaper["shares_outstanding"], "listed_common_shares": workpaper["active_reference"]["shares_outstanding"]},
        },
        {
            "key": "macro-choice",
            "label": "RCR June benchmark carry-forward reviewed decision receipt; original PDF not hashed",
            "form": "BTr_auction",
            "period_end": "2026-06-23",
            "published_at": "2026-06-23",
            "source_page": 2,
            "url": decision["macro_observation_for_test"]["source"],
            "facts": decision["macro_observation_for_test"],
        },
    ]
    sources = []
    for spec in specs:
        receipt = {
            "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0",
            "ticker": "RCR",
            "review_scope": "isolated_staged_test_only",
            "retrieval_date": "2026-09-26",
            "source": {key: spec[key] for key in ("label", "form", "period_end", "published_at", "source_page", "url")},
            "facts": spec["facts"],
            "original_source_sha256": None,
            "note": "SHA-256 binds this reviewed fact receipt, not original public source bytes.",
        }
        raw = canonical_json(receipt) + b"\n"
        path = catalog_root / "receipts" / f"RCR-{spec['key']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        digest = _sha256(raw)
        sources.append(
            {
                "document_id": f"RCR-{spec['key']}-{digest[:8]}",
                "label": spec["label"],
                "form": spec["form"],
                "period_end": spec["period_end"],
                "published_at": spec["published_at"],
                "source_page": spec["source_page"],
                "url": spec["url"],
                "sha256": digest,
            }
        )
    return sources


def stage(*, output_root: Path) -> Path:
    output_root = output_root.resolve()
    if output_root == ROOT or output_root in SERVING_ROOT.parents or SERVING_ROOT == output_root or SERVING_ROOT in output_root.parents:
        raise ValueError("RCR test output must not overlap the workspace or serving catalog root")
    if output_root.exists():
        raise FileExistsError(f"stage output already exists: {output_root}")
    _check_active()
    decision = _pinned_json(DECISION_PATH, DECISION_SHA256)
    workpaper = _pinned_json(WORKPAPER_PATH, WORKPAPER_SHA256)
    if (
        decision["issuer"] != "PSE:RCR"
        or decision["status"] != "selected_for_isolated_staged_test_only"
        or decision["issuer_approved"] is not False
        or decision["activation_authorized"] is not False
        or decision["assumptions_approved_for_publication"] is not False
        or decision["parent_workpaper_sha256"] != WORKPAPER_SHA256
        or workpaper["status"] != "staged_calculation_only"
        or workpaper["issuer_approved"] is not False
    ):
        raise ValueError("RCR decision and workpaper do not preserve the test-only boundary")
    selected = decision["selected_reported_input"]
    if (
        selected["trailing_four_quarter_distribution_per_share_php"] != workpaper["ttm_distribution_per_share"]
        or selected["shares_outstanding"] != workpaper["shares_outstanding"]
        or abs(sum(workpaper["quarterly_reported_distributions_per_share"].values()) - selected["trailing_four_quarter_distribution_per_share_php"]) > 1e-12
    ):
        raise ValueError("RCR selected facts differ from the confirmed workpaper")

    config = copy.deepcopy(load_batch_config())
    config["valuation_date"] = decision["decision_date"]
    config["batch_version"] = CATALOG_VERSION
    config["review_status"] = "selected_for_isolated_staged_test_only"
    issuer = config["issuers"]["RCR"]
    issuer["facts"].update(
        distribution_per_share=selected["trailing_four_quarter_distribution_per_share_php"],
        shares_millions=selected["shares_outstanding"] / 1_000_000,
        distribution_period="TTM 2025Q3-2026Q2; latest shares as of 2026-09-25",
        book_value_per_share=8.32,
    )
    issuer["source"] = {
        "label": "RCR 2Q2026 fund-manager reviewed fact receipt; original PDF not hashed",
        "form": "fund_manager_report",
        "period_end": "2026-06-30",
        "published_at": "2026-08-11",
        "url": "https://rlcommercialreit.com.ph/sites/default/files/2026-08/RL%20Fund%20Management%20Quarterly%20Report_Q2%202026.pdf",
    }
    issuer["distribution_sources"] = [row["url"] for row in workpaper["sources"]]
    policy = config["reit_policies"][issuer["policy"]]
    if policy["version"] != decision["selected_model_policy_for_test"]["version"]:
        raise ValueError("RCR policy version differs from the confirmed test choice")
    for name in ("bear", "base", "bull"):
        if policy["scenarios"][name] != decision["selected_model_policy_for_test"][name]:
            raise ValueError(f"RCR {name} policy differs from the confirmed test choice")
    built = build_batch_artifacts(config)["RCR"]
    for name in ("bear", "base", "bull"):
        actual = built.scenarios[name]
        expected = decision["expected_isolated_values_per_share_php"][name]
        if actual is None or abs(actual.value_per_share - expected) > 1e-10:
            raise ValueError(f"RCR {name} model result differs from the confirmed workpaper")

    catalog_root = output_root / CATALOG_VERSION
    sources = _receipt_sources(catalog_root, decision, workpaper)
    assumptions = {
        **built.public_assumptions,
        "shares_outstanding_millions": selected["shares_outstanding"] / 1_000_000,
        "share_count_as_of": selected["shares_as_of"],
        "benchmark_observed_at": decision["macro_observation_for_test"]["observed_at"],
        "benchmark_yield_at_observation": decision["macro_observation_for_test"]["annual_average_yield"],
        "benchmark_carry_forward_scope": "isolated_staged_test_only",
        "assumption_decision_sha256": DECISION_SHA256,
        "reliability": "Low - calculation-only supervised test",
    }
    warnings = [
        "Isolated provisional RCR calculation only; not analyst-approved, active, or published.",
        "Trailing declared DPU is not a full-period pro forma payout from the six newly infused malls.",
        "The June near-ten-year yield is 95 days old and carried forward only for this isolated test; 11% equity cost is not an approved current RCR discount rate.",
        "The 2.5% terminal distribution growth is an unapproved scenario hypothesis; most base value is terminal.",
        "Source SHA-256 values bind reviewed fact receipts, not original PDF or HTML bytes; source-storage and display rights remain unconfirmed.",
        "No dated price or current-upside comparison is supplied.",
    ]
    snapshot = {
        "decision_receipt_sha256": DECISION_SHA256,
        "workpaper_sha256": WORKPAPER_SHA256,
        "reviewed_fact_receipt_sha256": [row["sha256"] for row in sources],
        "facts": issuer["facts"],
        "scenario_policy": policy,
        "macro_observation_for_test": decision["macro_observation_for_test"],
        "model_version": built.model_version,
    }
    payload = built.model_dump(mode="json")
    payload.update(
        filing_published_at="2026-08-11",
        public_assumptions=assumptions,
        sensitivities=[
            {"type": "scenario_range", "drivers": ["current_distribution_per_share", "explicit_growth", "cost_of_equity", "terminal_growth"]},
            {"type": "one_way_base_equity_cost", **decision["base_one_way_equity_cost_checks_per_share_php"]},
        ],
        sources=sources,
        warnings=warnings,
        input_hash=sha256_object(snapshot),
        artifact_hash=None,
    )
    artifact = PseValuationArtifact.model_validate(payload).with_artifact_hash()
    if not artifact.verify_artifact_hash():
        raise ValueError("RCR internal artifact hash failed")
    artifact_raw = _write_json(catalog_root / "artifacts/RCR.json", artifact.model_dump(mode="json"))
    manifest = {
        "schema_version": CATALOG_SCHEMA,
        "catalog_version": CATALOG_VERSION,
        "universe_version": "PSE-V2-RCR-ISOLATED-TEST-1.0",
        "valuation_date": decision["decision_date"],
        "catalog_status": "staged",
        "artifact_count": 1,
        "availability_counts": {"intrinsic_valuation": 1, "market_relative_only": 0, "not_available": 0},
        "publication_counts": {"approved": 0, "blocked": 0, "provisional": 1},
        "entries": [
            {
                "ticker": "RCR",
                "availability_type": artifact.availability_type,
                "publication_state": artifact.publication_state,
                "primary_model": artifact.primary_model,
                "artifact_sha256": _sha256(artifact_raw),
                "source_audit": "docs/audit/55-pse-rcr-isolated-catalog-api-test.md",
            }
        ],
    }
    manifest_raw = _write_json(catalog_root / "manifest.json", manifest)
    _write_json(
        output_root / "staged.json",
        {
            "schema_version": POINTER_SCHEMA,
            "status": "staged",
            "catalog_version": CATALOG_VERSION,
            "catalog_path": CATALOG_VERSION,
            "manifest_sha256": _sha256(manifest_raw),
        },
    )
    catalog = load_pointer(output_root)
    if catalog.status != "staged" or set(catalog.entry_by_ticker) != {"RCR"}:
        raise ValueError("isolated RCR catalog failed to round-trip")
    _check_active()
    return catalog_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(stage(output_root=args.output))


if __name__ == "__main__":
    main()
