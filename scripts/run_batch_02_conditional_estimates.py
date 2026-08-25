#!/usr/bin/env python3
"""Stage six Low-reliability conditional values without changing serving data."""

from __future__ import annotations

import argparse
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

from app.us_valuation.artifacts import PUBLIC_SCHEMA_VERSION, sanitize_public_artifact
from app.us_valuation.batch_02 import BATCH_02_TICKERS
from app.us_valuation.batch_02_conditional_estimates import (
    COMMON_WARNING,
    CONDITIONAL_TICKERS,
    CONDITIONAL_VERSION,
    build_conditional_estimates,
)
from app.us_valuation.reliability import relative_movement


PROTECTED_ROOTS = (
    ROOT / "backend/app/data/us_valuations",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)
REGISTER = ROOT / "backend/app/us_valuation/config/universe_reset_withheld.json"


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
            raise FileExistsError(f"refusing to overwrite immutable conditional output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent))
    try:
        candidate = staging / path.name
        candidate.write_bytes(raw)
        candidate.replace(path)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _conditional_public(prior: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(prior))
    scenario_range = result["scenario_range"]
    movement = (
        1.0
        if scenario_range["base"] == 0
        else relative_movement(**scenario_range)
    )
    base = scenario_range["base"]
    source = result["source"]
    value["schema_version"] = PUBLIC_SCHEMA_VERSION
    value["source_financial_statement"] = {
        "form": "10-Q",
        "period_end": source["period_end"],
        "filed_date": source["filed_date"],
        "accession": source["accession"],
        "url": source["source_url"],
        "note": "Controlling cutoff-eligible SEC filing anchors reported facts; forward states are governed assumptions.",
    }
    value["model_policy"] = {
        "primary": "conditional_estimate",
        "supporting": [],
        "blend_models": False,
        "reason": "Conditional decision-support estimate; not an ordinary source-bounded intrinsic value.",
    }
    value["public_assumptions"] = {
        "forecast_policy_version": CONDITIONAL_VERSION,
        "forecast_mode": "conditional_scenarios",
        "source_policy": "Reported SEC facts plus governed hypothetical states; no stock price or analyst target.",
    }
    value["models"] = {
        "conditional_estimate": {
            "model": "conditional_estimate",
            "output_type": "conditional_value_per_share",
            "currency": "USD",
            "conditional_value_per_share": base,
            "publication_state": "review_required",
            "errors": [],
            "warnings": [result["warning"]],
        }
    }
    value["scenarios"] = {}
    value["scenario_range"] = {
        **scenario_range,
        "label": "conditional scenario range; not a confidence interval, probability-weighted expected value, or reported intrinsic value",
    }
    value["sensitivities"] = []
    value["forecast_quality"] = {
        "policy_version": CONDITIONAL_VERSION,
        "status": "review_required",
        "errors": [],
        "warnings": [result["warning"]],
        "checks": {},
    }
    value["review"] = {
        "publication_state": "review_required",
        "confidence_grade": "conditional_low",
        "errors": [],
        "warnings": [result["warning"], COMMON_WARNING],
        "price_dependent_inputs_used": False,
        "prohibited_output_check": {
            "buy_hold_sell": False,
            "current_price": False,
            "trading_multiples": False,
            "upside_downside": False,
        },
    }
    value.pop("automated_review", None)
    value.pop("bridge_quality", None)
    if result["ticker"] == "WBD":
        assumptions = result["governed_assumptions"]
        value["contractual_consideration"] = {
            "amount_per_share": assumptions["contract_cash_if_closed_by_2026_09_30"],
            "ticking_per_day": result["reported_inputs"]["ticking_cash_per_day"],
            "illustration_date": "2027-06-04",
            "illustration_amount_per_share": assumptions[
                "contract_calendar_illustration_2027_06_04"
            ],
            "status": "conditional_contract_term_not_intrinsic_value",
            "note": "Shown separately from the standalone conditional range; not probability weighted.",
        }
    else:
        value.pop("contractual_consideration", None)
    value["reliability"] = {
        "label": "Low",
        "accounting_label": "High",
        "scenario_label": "Low",
        "model_cap": "Low",
        "source_cap": "Low",
        "accounting_impact_ratio": 0.0,
        "scenario_movement_ratio": movement,
        "reasons": ["CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"],
    }
    value["methodology"] = {
        "forecast_policy": CONDITIONAL_VERSION,
        "sector_framework": "issuer-specific conditional decision states",
        "source_policy": "Reported SEC facts remain separate from governed hypothetical assumptions.",
    }
    value["data_boundary"] = {
        "raw_financial_statement_values_included": False,
        "stock_prices_used": False,
        "public_payload_contains": "conditional range, Low reliability, short warning, and filing attribution",
    }
    public = sanitize_public_artifact(value)
    if (
        public["review"]["publication_state"] != "review_required"
        or public["reliability"]["label"] != "Low"
        or public["scenario_range"] != value["scenario_range"]
    ):
        raise RuntimeError(f"{result['ticker']}: conditional artifact failed closed")
    return public


def run(*, prior_root: Path, output_root: Path) -> dict[str, Any]:
    prior_root = Path(prior_root)
    output_root = Path(output_root)
    if not (prior_root / "revision-retry-report.json").is_file():
        raise ValueError("prior root is not the verified revision retry")
    if output_root.resolve(strict=False).is_relative_to(prior_root.resolve()):
        raise ValueError("conditional output must be separate from its input")
    if any(output_root.resolve(strict=False).is_relative_to(root.resolve()) for root in PROTECTED_ROOTS):
        raise ValueError("conditional output must be outside serving roots")
    retry = json.loads((prior_root / "revision-retry-report.json").read_text())
    if retry.get("newly_recovered_numeric_count") != 0 or retry.get("still_withheld_count") != 6:
        raise ValueError("prior retry denominator/outcome mismatch")
    results = build_conditional_estimates()
    before = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    register_before = hashlib.sha256(REGISTER.read_bytes()).hexdigest()
    cases = []
    for ticker in BATCH_02_TICKERS:
        private_path = prior_root / "generated" / ticker / "valuation-private.json"
        public_path = prior_root / "staged-public" / f"{ticker}.json"
        private = json.loads(private_path.read_text())
        prior_public_raw = public_path.read_bytes()
        if ticker in results:
            private["conditional_estimate"] = results[ticker]
            public = _conditional_public(json.loads(prior_public_raw), results[ticker])
            public_raw = _json_bytes(public)
            cases.append({
                "ticker": ticker,
                "outcome": "conditional_numeric",
                "reliability": "Low",
                **results[ticker]["scenario_range"],
                "method": results[ticker]["method"],
                "warning": results[ticker]["warning"],
            })
        else:
            private["conditional_estimate"] = None
            public_raw = prior_public_raw
        _immutable(output_root / "generated" / ticker / "valuation-private.json", _json_bytes(private))
        _immutable(output_root / "staged-public" / f"{ticker}.json", public_raw)
    after = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    register_after = hashlib.sha256(REGISTER.read_bytes()).hexdigest()
    if before != after or register_before != register_after:
        raise RuntimeError("conditional run changed protected serving data or the withheld register")
    report = {
        "schema_version": "FINSIGHT-BATCH-02-CONDITIONAL-REPORT-1",
        "batch": 2,
        "valuation_date": "2026-08-14",
        "policy_version": CONDITIONAL_VERSION,
        "conditional_denominator": list(CONDITIONAL_TICKERS),
        "conditional_numeric_count": 6,
        "source_bounded_numeric_count": 4,
        "total_public_numeric_count": 10,
        "conditional_low_reliability_count": 6,
        "withheld_count_under_conditional_policy": 0,
        "register_changed": False,
        "register_sha256": register_before,
        "serving_artifacts_changed": False,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "cases": cases,
    }
    _immutable(output_root / "conditional-report.json", _json_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in (
        "conditional_numeric_count", "source_bounded_numeric_count",
        "total_public_numeric_count", "withheld_count_under_conditional_policy",
        "register_changed", "serving_artifacts_changed",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
