#!/usr/bin/env python3
"""Run the controlled source-bounded Batch 03 initial pass."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import PUBLIC_SCHEMA_VERSION, public_result, sanitize_public_artifact
from app.us_valuation.batch_03 import BATCH_03_MANIFEST, BATCH_03_TICKERS, BATCH_03_VALUATION_DATE
from app.us_valuation.batch_03_practical_models import (
    BATCH_03_NUMERIC_TICKERS,
    BATCH_03_POLICY_VERSION,
    WITHHELD_DECISIONS,
    build_batch_03_practical_result,
)
from app.us_valuation.pipeline import build_us_valuation


PROTECTED_ROOTS = (
    ROOT / "backend/app/data/us_valuations",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)
WATCHLIST = ROOT / "backend/app/us_valuation/config/universe_reset_recovery_learning_watchlist.json"


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


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
            raise FileExistsError(f"refusing to overwrite immutable Batch 03 output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent))
    try:
        candidate = staging / path.name
        candidate.write_bytes(raw)
        candidate.replace(path)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _issuer_surface(issuer: Any, source: Mapping[str, Any], confidence: float) -> dict[str, Any]:
    return {
        "cik": issuer.cik,
        "ticker": issuer.ticker,
        "issuer_name": issuer.issuer_name,
        "filing_regime": "10-K_10-Q",
        "accounting_standard": "US-GAAP",
        "sec_sic_code": None,
        "sec_sic_label": issuer.gics_sub_industry,
        "finsight_sector": issuer.gics_sector,
        "primary_archetype": issuer.primary_lane_id,
        "secondary_archetypes": [],
        "classification_confidence": confidence,
        "mapping_version": "US-RESET-PARTITION-2026-08-14-2.0",
        "classification_reason": "Frozen Batch 03 economic lane with issuer-specific source/model review.",
        "override_applied": True,
        "source_accessions": [source["accession"]],
    }


def _numeric_public(issuer: Any, result: Mapping[str, Any]) -> dict[str, Any]:
    base = result["scenario_range"]["base"]
    public = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "valuation_date": BATCH_03_VALUATION_DATE,
        "market": "US",
        "currency": "USD",
        "ticker": issuer.ticker,
        "issuer": _issuer_surface(issuer, result["source_financial_statement"], 0.8),
        "source_financial_statement": result["source_financial_statement"],
        "model_policy": {
            "primary": "fcff_dcf",
            "supporting": [],
            "blend_models": False,
            "reason": result["model_selection_reason"],
        },
        "public_assumptions": result["public_assumptions"],
        "models": result["models"],
        "scenarios": result["scenarios"],
        "scenario_range": result["scenario_range"],
        "sensitivities": result["sensitivities"],
        "forecast_quality": result["forecast_quality"],
        "review": result["review"],
        "bridge_quality": {
            "decision": "complete",
            "complete": True,
            "usable": True,
            "bounded_fields": [],
            "blocking_fields": [],
            "reason_codes": [],
            "intrinsic_value_range": {
                "low": base,
                "midpoint": base,
                "high": base,
                "spread_ratio": 0.0,
                "spread_limit": 0.01,
            },
        },
        "reliability": result["reliability"],
        "methodology": {
            "forecast_policy": BATCH_03_POLICY_VERSION,
            "sector_framework": "source-bounded company-history operating cash-FCFF",
            "source_policy": "SEC facts filed on or before 2026-08-14; no stock price or analyst target.",
        },
        "data_boundary": {
            "raw_financial_statement_values_included": False,
            "stock_prices_used": False,
            "public_payload_contains": "derived range, Low reliability, warnings, assumptions, and filing attribution",
        },
    }
    sanitized = sanitize_public_artifact(public)
    if sanitized["review"]["publication_state"] == "withheld":
        raise RuntimeError(f"{issuer.ticker}: numeric Batch 03 public artifact failed closed")
    return sanitized


def _withheld_public(
    issuer: Any,
    *,
    source: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = list(policy["hard_blockers"])
    public = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "valuation_date": BATCH_03_VALUATION_DATE,
        "market": "US",
        "currency": "USD",
        "ticker": issuer.ticker,
        "issuer": _issuer_surface(issuer, source, 0.65),
        "source_financial_statement": dict(source),
        "model_policy": {
            "primary": "fcff_dcf",
            "supporting": [],
            "blend_models": False,
            "reason": f"Target economic model: {policy['model']}.",
        },
        "public_assumptions": {},
        "models": {
            "fcff_dcf": {
                "model": "fcff_dcf",
                "output_type": "intrinsic_value_per_share",
                "currency": "USD",
                "intrinsic_value_per_share": None,
                "publication_state": "withheld",
                "errors": blockers,
                "warnings": [],
            }
        },
        "scenarios": {},
        "scenario_range": {
            "low": None, "base": None, "high": None,
            "label": "assumption range, not a statistical confidence interval",
        },
        "sensitivities": [],
        "forecast_quality": {
            "policy_version": BATCH_03_POLICY_VERSION,
            "status": "withheld",
            "errors": blockers,
            "warnings": [],
            "checks": {},
        },
        "review": {
            "publication_state": "withheld",
            "confidence_grade": "insufficient",
            "errors": blockers,
            "warnings": [],
            "price_dependent_inputs_used": False,
            "prohibited_output_check": {
                "buy_hold_sell": False,
                "current_price": False,
                "trading_multiples": False,
                "upside_downside": False,
            },
        },
        "bridge_quality": {
            "decision": "withheld",
            "complete": False,
            "usable": False,
            "bounded_fields": [],
            "blocking_fields": [],
            "reason_codes": ["BRIDGE_QUALITY_INVALID_OR_MISSING"],
            "intrinsic_value_range": {
                "low": None, "midpoint": None, "high": None,
                "spread_ratio": None, "spread_limit": 0.01,
            },
        },
        "reliability": {
            "label": "Low", "accounting_label": "Low", "scenario_label": "Low",
            "model_cap": "Low", "source_cap": "Low",
            "accounting_impact_ratio": None, "scenario_movement_ratio": None,
            "reasons": ["VALUATION_WITHHELD"],
        },
        "methodology": {
            "forecast_policy": BATCH_03_POLICY_VERSION,
            "sector_framework": policy["archetype"],
            "source_policy": "SEC facts filed on or before 2026-08-14.",
        },
        "data_boundary": {
            "raw_financial_statement_values_included": False,
            "stock_prices_used": False,
            "public_payload_contains": "withheld state, blockers, and filing attribution",
        },
    }
    return sanitize_public_artifact(public)


def _source_statement(
    issuer: Any, manifest: Mapping[str, Any], submissions: Mapping[str, Any]
) -> dict[str, Any]:
    filing = max(manifest["eligible_filings"], key=lambda row: (row["filed"], row["accession"]))
    index = submissions["filings"]["recent"]["accessionNumber"].index(filing["accession"])
    period_end = submissions["filings"]["recent"]["reportDate"][index]
    return {
        "form": filing["form"],
        "period_end": period_end,
        "filed_date": filing["filed"],
        "accession": filing["accession"],
        "url": "https://www.sec.gov/Archives/edgar/data/"
        f"{int(issuer.cik)}/{filing['accession'].replace('-', '')}/{filing['primary_document']}",
        "note": "Controlling cutoff-eligible SEC filing used for the Batch 03 initial decision.",
    }


def run_batch(
    *, source_root: Path, structural_root: Path, output_root: Path
) -> dict[str, Any]:
    source_root, structural_root, output_root = map(Path, (source_root, structural_root, output_root))
    if not source_root.is_dir() or not structural_root.is_dir():
        raise ValueError("Batch 03 source and structural roots must exist")
    if any(output_root.resolve(strict=False).is_relative_to(root.resolve()) for root in PROTECTED_ROOTS):
        raise ValueError("Batch 03 output must be outside serving roots")
    before = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    watchlist_before = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    cases = []
    for issuer in BATCH_03_MANIFEST:
        packet = source_root / issuer.ticker
        submissions = json.loads((packet / "submissions.json").read_text())
        companyfacts = json.loads((packet / "companyfacts.json").read_text())
        manifest = json.loads((packet / "source-manifest.json").read_text())
        structural = json.loads((structural_root / issuer.ticker / "structural-filing.json").read_text())
        source = _source_statement(issuer, manifest, submissions)
        if structural.get("source_accession") != source["accession"]:
            raise ValueError(f"{issuer.ticker}: structural/source accession mismatch")
        strict = None
        strict_error = None
        try:
            strict = build_us_valuation(
                submissions=submissions,
                companyfacts=companyfacts,
                valuation_date=BATCH_03_VALUATION_DATE,
                source_manifest=manifest,
            )
            public_result(strict, submissions if strict.get("model_policy", {}).get("primary") == "fcff_dcf" else None)
        except Exception as error:
            strict_error = f"{type(error).__name__}: {error}"
        if issuer.ticker in BATCH_03_NUMERIC_TICKERS:
            practical = build_batch_03_practical_result(
                ticker=issuer.ticker,
                source_root=source_root,
                structural_root=structural_root,
            )
            public = _numeric_public(issuer, practical)
            outcome = "numeric"
            low, base, high = (
                practical["scenario_range"][key] for key in ("low", "base", "high")
            )
            reliability = "Low"
            blockers: list[str] = []
            model = "enterprise_cash_fcff"
            reason = practical["model_selection_reason"]
        else:
            policy = WITHHELD_DECISIONS[issuer.ticker]
            practical = None
            public = _withheld_public(issuer, source=source, policy=policy)
            outcome = "withheld"
            low = base = high = reliability = None
            blockers = list(policy["hard_blockers"])
            model = policy["model"]
            reason = policy["reason"]
        case = {
            "ticker": issuer.ticker,
            "cik": issuer.cik,
            "issuer_name": issuer.issuer_name,
            "outcome": outcome,
            "target_model": model,
            "model_selection_reason": reason,
            "low": low,
            "base": base,
            "high": high,
            "reliability": reliability,
            "blockers": blockers,
            "source_accession": source["accession"],
            "source_period_end": source["period_end"],
            "source_filed_date": source["filed_date"],
            "strict_error": strict_error,
        }
        private = {
            "schema_version": "FINSIGHT-CONTROLLED-BATCH-OUTCOME-1",
            "batch": 3,
            "valuation_date": BATCH_03_VALUATION_DATE,
            "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name},
            "controlled_outcome": case,
            "strict_diagnostic": strict,
            "strict_error": strict_error,
            "practical_private": practical,
            "source_manifest": manifest,
            "structural_source": {
                "accession": structural["source_accession"],
                "fact_count": len(structural["facts"]),
                "diagnostic_count": len(structural["diagnostics"]),
            },
        }
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json_bytes(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json_bytes(public))
        cases.append(case)
    after = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    watchlist_after = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    if before != after or watchlist_before != watchlist_after:
        raise RuntimeError("Batch 03 initial pass changed serving data or the Recovery Learning Watchlist")
    numeric = sum(row["outcome"] == "numeric" for row in cases)
    report = {
        "schema_version": "FINSIGHT-CONTROLLED-BATCH-REPORT-1",
        "batch": 3,
        "policy": "practical_source_bounded_initial_pass",
        "valuation_date": BATCH_03_VALUATION_DATE,
        "denominator_tickers": list(BATCH_03_TICKERS),
        "attempted_count": 10,
        "numeric_count": numeric,
        "withheld_count": 10 - numeric,
        "invalid_input_count": 0,
        "reliability_counts": {"High": 0, "Medium": 0, "Low": numeric},
        "watchlist_changed": False,
        "watchlist_sha256": watchlist_before,
        "serving_artifacts_changed": False,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "cases": cases,
    }
    _immutable(output_root / "batch-report.json", _json_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--structural-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    result = run_batch(**vars(parser.parse_args()))
    print(json.dumps({key: result[key] for key in (
        "attempted_count", "numeric_count", "withheld_count", "invalid_input_count",
        "watchlist_changed", "serving_artifacts_changed",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

