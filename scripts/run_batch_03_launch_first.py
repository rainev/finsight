#!/usr/bin/env python3
"""Stage launch-first Batch 03 outcomes without changing serving artifacts."""

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

from app.us_valuation.artifacts import PUBLIC_SCHEMA_VERSION, sanitize_public_artifact
from app.us_valuation.baseline import baseline_from_public_artifact
from app.us_valuation.batch_03 import BATCH_03_TICKERS, BATCH_03_VALUATION_DATE
from app.us_valuation.batch_03_launch_first import (
    LAUNCH_FIRST_BATCH_03_VERSION,
    LAUNCH_FIRST_CONDITIONAL_TICKERS,
    LAUNCH_FIRST_HARD_FAILURES,
    build_batch_03_launch_first_hard_failure,
    build_batch_03_launch_first_result,
)
from app.us_valuation.reliability import relative_movement


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
            raise FileExistsError(f"refusing to overwrite immutable launch-first output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent))
    try:
        candidate = staging / path.name
        candidate.write_bytes(raw)
        candidate.replace(path)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _conditional_public(prior: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(prior)
    scenario = result["scenario_range"]
    base = scenario["base"]
    movement = 1.0 if base == 0 else relative_movement(**scenario)
    assumptions = result["governed_assumptions"]
    margin_derivation = result["source_ledger"]["margin_derivation"]
    bridge = result["source_ledger"]["bridge"]
    extra_assumptions: dict[str, Any] = {
        "bridge_claims_basis": bridge["special_treatment"],
    }
    if "commitment_horizons_years" in margin_derivation:
        horizons = margin_derivation["commitment_horizons_years"]
        extra_assumptions.update(
            {
                "commitment_horizon_years_bear": horizons[0],
                "commitment_horizon_years_base": horizons[1],
                "commitment_horizon_years_bull": horizons[2],
            }
        )
    if "incremental_reserve_amounts" in margin_derivation:
        reserves = margin_derivation["incremental_reserve_amounts"]
        extra_assumptions.update(
            {
                "commitment_reserve_bear": reserves[0],
                "commitment_reserve_base": reserves[1],
                "commitment_reserve_bull": reserves[2],
            }
        )
    if result["ticker"] == "APP":
        claims = bridge["other_claims"]
        extra_assumptions.update(
            {
                "unresolved_claims_reserve_bear": claims[0],
                "unresolved_claims_reserve_base": claims[1],
                "unresolved_claims_reserve_bull": claims[2],
            }
        )
    if "nci_share_reconciliation" in bridge:
        extra_assumptions.update(
            {
                "nci_share_reconciled": bridge["nci_share_reconciliation"]["difference"] == 0,
                "nci_share_reconciliation_difference": bridge["nci_share_reconciliation"]["difference"],
            }
        )
    value.update(
        {
            "schema_version": PUBLIC_SCHEMA_VERSION,
            "primary_valuation_method": result["method"],
            "model_policy": {
                "primary": "conditional_estimate",
                "supporting": [],
                "blend_models": False,
                "reason": "Launch-first current-legal-state conditional baseline after the source-bounded primary route failed.",
                "fallback_from": prior.get("model_policy", {}).get("primary", "fcff_dcf"),
            },
            "public_assumptions": {
                "forecast_policy_version": LAUNCH_FIRST_BATCH_03_VERSION,
                "forecast_years": assumptions["forecast_years"],
                "forecast_mode": "normalized_cash_conversion",
                "initial_revenue_growth": assumptions["initial_growth"][1],
                "cash_conversion_margin_low": assumptions["cash_conversion_margin"][0],
                "cash_conversion_margin": assumptions["cash_conversion_margin"][1],
                "cash_conversion_margin_high": assumptions["cash_conversion_margin"][2],
                "policy_wacc_low": assumptions["wacc"][2],
                "policy_wacc": assumptions["wacc"][1],
                "policy_wacc_high": assumptions["wacc"][0],
                "terminal_growth_low": assumptions["terminal_growth"][0],
                "terminal_growth": assumptions["terminal_growth"][1],
                "terminal_growth_high": assumptions["terminal_growth"][2],
                "diluted_shares": assumptions["shares"][1],
                "diluted_shares_low": assumptions["shares"][2],
                "diluted_shares_high": assumptions["shares"][0],
                "equity_floor_applied": assumptions["limited_liability_floor"]["applied"],
                "equity_floor_basis": assumptions["limited_liability_floor"]["basis"],
                **extra_assumptions,
            },
            "models": {
                "conditional_estimate": {
                    "model": "conditional_estimate",
                    "output_type": "conditional_value_per_share",
                    "currency": "USD",
                    "conditional_value_per_share": base,
                    "publication_state": "review_required",
                    "errors": [],
                    "warnings": [result["warning"]],
                }
            },
            "scenarios": {},
            "scenario_range": {
                **scenario,
                "label": "conditional current-state range; not a probability-weighted forecast or recommendation",
            },
            "sensitivities": [],
            "forecast_quality": {
                "policy_version": LAUNCH_FIRST_BATCH_03_VERSION,
                "status": "review_required",
                "errors": [],
                "warnings": [result["warning"]],
                "checks": {},
            },
            "review": {
                "publication_state": "review_required",
                "confidence_grade": "conditional_low",
                "errors": [],
                "warnings": [result["warning"], assumptions["invalidation"]],
                "price_dependent_inputs_used": False,
                "prohibited_output_check": {
                    "buy_hold_sell": False,
                    "current_price": False,
                    "trading_multiples": False,
                    "upside_downside": False,
                },
            },
            "reliability": {
                "label": "Low",
                "accounting_label": "High",
                "scenario_label": "Low",
                "model_cap": "Low",
                "source_cap": "Low",
                "accounting_impact_ratio": 0.0,
                "scenario_movement_ratio": movement,
                "reasons": ["CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"],
            },
            "methodology": {
                "forecast_policy": LAUNCH_FIRST_BATCH_03_VERSION,
                "sector_framework": result["method"],
                "source_policy": "Reported SEC facts remain private and separate from governed FinSight assumptions.",
            },
            "data_boundary": {
                "raw_financial_statement_values_included": False,
                "stock_prices_used": False,
                "public_payload_contains": "conditional range, confidence reasons, warnings, assumptions, and filing attribution",
            },
        }
    )
    value.pop("automated_review", None)
    value.pop("bridge_quality", None)
    value.pop("contractual_consideration", None)
    public = sanitize_public_artifact(value)
    if (
        public["availability_type"] != "conditional_estimate"
        or public["review"]["publication_state"] != "review_required"
        or public["confidence"]["label"] != "Low"
        or public["scenario_range"]["base"] != base
    ):
        raise RuntimeError(f"{result['ticker']}: launch-first public artifact failed closed")
    return public


def run(
    *,
    prior_root: Path,
    source_root: Path,
    structural_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    prior_root, source_root, structural_root, output_root = map(
        Path, (prior_root, source_root, structural_root, output_root)
    )
    prior_report = json.loads((prior_root / "batch-report.json").read_text())
    if (
        prior_report.get("denominator_tickers") != list(BATCH_03_TICKERS)
        or prior_report.get("numeric_count") != 3
        or prior_report.get("withheld_count") != 7
    ):
        raise ValueError("launch-first input is not the verified Batch 03 initial result")
    if any(output_root.resolve(strict=False).is_relative_to(root.resolve()) for root in PROTECTED_ROOTS):
        raise ValueError("launch-first output must remain outside serving roots")
    before = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    watchlist_before = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    cases = []
    for ticker in BATCH_03_TICKERS:
        private = json.loads((prior_root / "generated" / ticker / "valuation-private.json").read_text())
        prior_public = json.loads((prior_root / "staged-public" / f"{ticker}.json").read_text())
        if ticker in LAUNCH_FIRST_CONDITIONAL_TICKERS:
            controlled = private["controlled_outcome"]
            rejection_reasons = tuple(
                str(value)
                for value in (
                    *controlled.get("blockers", []),
                    controlled.get("model_selection_reason"),
                )
                if value
            )
            launch = build_batch_03_launch_first_result(
                ticker=ticker,
                source_root=source_root,
                structural_root=structural_root,
                primary_rejection_reasons=rejection_reasons,
            )
            public = _conditional_public(prior_public, launch)
            case = {
                "ticker": ticker,
                "outcome": "conditional_numeric",
                "availability_type": "conditional_estimate",
                "reliability": "Low",
                "method": launch["method"],
                **launch["scenario_range"],
                "warning": launch["warning"],
            }
        elif ticker in LAUNCH_FIRST_HARD_FAILURES:
            launch = build_batch_03_launch_first_hard_failure(
                ticker,
                source_root=source_root,
                structural_root=structural_root,
            )
            public = sanitize_public_artifact(prior_public)
            case = {
                "ticker": ticker,
                "outcome": "not_available",
                "availability_type": "not_available",
                "reliability": None,
                "method": "unavailable",
                "low": None,
                "base": None,
                "high": None,
                "hard_failures": launch["hard_failures"],
            }
        else:
            public = sanitize_public_artifact(prior_public)
            launch = {
                "ticker": ticker,
                "model_version": LAUNCH_FIRST_BATCH_03_VERSION,
                "availability_type": public["availability_type"],
                "baseline": baseline_from_public_artifact(public).as_private_dict(),
                "retained_source_bounded_result": True,
            }
            case = {
                "ticker": ticker,
                "outcome": "source_bounded_numeric",
                "availability_type": "available",
                "reliability": public["confidence"]["label"],
                "method": public["primary_valuation_method"],
                **{key: public["scenario_range"][key] for key in ("low", "base", "high")},
            }
        private["launch_first"] = launch
        _immutable(output_root / "generated" / ticker / "valuation-private.json", _json_bytes(private))
        _immutable(output_root / "staged-public" / f"{ticker}.json", _json_bytes(public))
        cases.append(case)
    after = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    watchlist_after = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    if before != after or watchlist_before != watchlist_after:
        raise RuntimeError("launch-first staging changed serving data or the watchlist")
    report = {
        "schema_version": "FINSIGHT-BATCH-03-LAUNCH-FIRST-REPORT-1",
        "batch": 3,
        "valuation_date": BATCH_03_VALUATION_DATE,
        "policy_version": LAUNCH_FIRST_BATCH_03_VERSION,
        "denominator_tickers": list(BATCH_03_TICKERS),
        "attempted_count": 10,
        "source_bounded_numeric_count": 3,
        "conditional_numeric_count": 5,
        "numeric_count": 8,
        "not_available_count": 2,
        "withheld_count": 0,
        "legacy_withheld_alias_count": 2,
        "reliability_counts": {"High": 0, "Medium": 0, "Low": 8},
        "market_comparison_available_count": 0,
        "watchlist_changed": False,
        "watchlist_sha256": watchlist_before,
        "serving_artifacts_changed": False,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "cases": cases,
    }
    _immutable(output_root / "launch-first-report.json", _json_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-root", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--structural-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    result = run(**vars(parser.parse_args()))
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "attempted_count",
                    "numeric_count",
                    "conditional_numeric_count",
                    "not_available_count",
                    "serving_artifacts_changed",
                    "watchlist_changed",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
