#!/usr/bin/env python3
"""Stage history-backed Batch 07 outcomes without serving or watchlist writes."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import PUBLIC_SCHEMA_VERSION, sanitize_public_artifact
from app.us_valuation.batch_07 import BATCH_07_MANIFEST, BATCH_07_TICKERS, BATCH_07_VALUATION_DATE
from app.us_valuation.batch_07_history import BATCH_07_HISTORY_VERSION, PASS_TICKERS, build_batch_07_history_result


PROTECTED = (ROOT / "backend/app/data/us_valuation_catalogs", ROOT / "frontend/public/data", ROOT / "frontend/src/research/generated")
WATCHLIST = ROOT / "backend/app/us_valuation/config/universe_reset_recovery_learning_watchlist.json"


def _json(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def _tree(root):
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
            digest.update(b"\n")
    return digest.hexdigest()


def _immutable(path, raw):
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent)) / path.name
    try:
        stage.write_bytes(raw)
        stage.replace(path)
    finally:
        shutil.rmtree(stage.parent, ignore_errors=True)


def _public(issuer, result):
    scenario = result["scenario_range"]
    base = scenario["base"]
    source = result["source_ledger"]["controlling_filing"]
    assumptions = result["governed_assumptions"]
    is_pass = issuer.ticker in PASS_TICKERS
    primary = "fcff_dcf" if is_pass else "conditional_estimate"
    value_field = "intrinsic_value_per_share" if is_pass else "conditional_value_per_share"
    model = {"model": primary, "output_type": value_field, "currency": "USD", value_field: base, "publication_state": "review_required", "errors": [], "warnings": [result["warning"]]}
    public_assumptions = {
        "forecast_policy_version": BATCH_07_HISTORY_VERSION,
        "forecast_years": 5,
        "forecast_mode": "history_backed_normalized_cash_conversion",
        "cash_conversion_margin_low": assumptions["cash_conversion_margin"][0],
        "cash_conversion_margin": assumptions["cash_conversion_margin"][1],
        "cash_conversion_margin_high": assumptions["cash_conversion_margin"][2],
        "revenue_growth_low": assumptions["growth"][0],
        "revenue_growth": assumptions["growth"][1],
        "revenue_growth_high": assumptions["growth"][2],
        "diluted_shares": assumptions["shares"][1],
        "diluted_shares_low": assumptions["shares"][2],
        "diluted_shares_high": assumptions["shares"][0],
        "history_policy_version": assumptions["history_policy_version"],
        "history_years_used": assumptions["history_years_used"],
        "normalization_basis": assumptions["normalization_basis"],
        "assumption_source_mix": assumptions["assumption_source_mix"],
        "equity_floor_applied": scenario["low"] == 0,
        "equity_floor_basis": assumptions["equity_floor_basis"],
        "source_policy": "Reported SEC facts plus source-linked company history and transparent FinSight assumptions; no stock price or analyst target.",
    }
    url = f"https://www.sec.gov/Archives/edgar/data/{int(issuer.cik)}/{source['accession'].replace('-', '')}/{source['primary_document']}"
    public = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "valuation_date": BATCH_07_VALUATION_DATE,
        "market": "US",
        "currency": "USD",
        "ticker": issuer.ticker,
        "issuer": {"cik": issuer.cik, "ticker": issuer.ticker, "issuer_name": issuer.issuer_name, "filing_regime": "10-K_10-Q", "accounting_standard": "US-GAAP", "sec_sic_code": None, "sec_sic_label": issuer.gics_sub_industry, "finsight_sector": issuer.gics_sector, "primary_archetype": issuer.primary_lane_id, "secondary_archetypes": [], "classification_confidence": .8, "mapping_version": "US-RESET-PARTITION-2026-08-14-2.0", "classification_reason": "Frozen Batch 07 lane plus issuer-specific history review.", "override_applied": True, "source_accessions": [source["accession"]]},
        "source_financial_statement": {"form": source["form"], "period_end": source["period_end"], "filed_date": source["filed"], "accession": source["accession"], "url": url, "note": "Controlling filing anchors current inputs; company history anchors normalized operating assumptions."},
        "primary_valuation_method": result["method"],
        "model_policy": {"primary": primary, "supporting": [], "blend_models": False, "reason": "History-backed source-bounded normalized cash-FCFF." if is_pass else "History-backed Conditional Low baseline with a material named dependency.", **({} if is_pass else {"fallback_from": "fcff_dcf"})},
        "public_assumptions": public_assumptions,
        "models": {primary: model},
        "scenarios": {},
        "scenario_range": {**scenario, "label": "assumption range, not a statistical confidence interval or recommendation"},
        "sensitivities": [],
        "forecast_quality": {"policy_version": BATCH_07_HISTORY_VERSION, "status": "review_required", "errors": [], "warnings": [result["warning"]], "checks": {}},
        "review": {"publication_state": "review_required", "confidence_grade": "source_bounded" if is_pass else "conditional_low", "errors": [], "warnings": [result["warning"], assumptions["invalidation"], assumptions["calculator_calibration"]], "price_dependent_inputs_used": False, "prohibited_output_check": {"buy_hold_sell": False, "current_price": False, "trading_multiples": False, "upside_downside": False}},
        "reliability": result["history_reliability"],
        "confidence": {"label": result["history_reliability"]["label"], "reasons": result["history_reliability"]["reasons"]},
        "methodology": {"forecast_policy": BATCH_07_HISTORY_VERSION, "sector_framework": result["method"], "source_policy": "Reported facts remain private and separate from historical summaries and governed assumptions."},
        "data_boundary": {"raw_financial_statement_values_included": False, "stock_prices_used": False, "public_payload_contains": "value range, reliability, warnings, historical-policy summary, assumptions and filing attribution"},
    }
    if is_pass:
        public["bridge_quality"] = {"blocking_fields": [], "bounded_fields": [], "complete": True, "decision": "complete", "intrinsic_value_range": {"low": base, "midpoint": base, "high": base, "spread_ratio": 0.0, "spread_limit": .01}, "reason_codes": [], "usable": True}
    value = sanitize_public_artifact(public)
    expected = "available" if is_pass else "conditional_estimate"
    if value.get("availability_type") != expected or value.get("scenario_range", {}).get("base") != base:
        raise RuntimeError(f"{issuer.ticker}: public sanitizer changed the controlled outcome")
    return value


def run(*, source_root: Path, structural_root: Path, output_root: Path):
    source_root, structural_root, output_root = map(Path, (source_root, structural_root, output_root))
    before = {str(root): _tree(root) for root in PROTECTED}
    watch_before = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    cases = []
    reliability_counts = {"High": 0, "Medium": 0, "Low": 0}
    for issuer in BATCH_07_MANIFEST:
        result = build_batch_07_history_result(ticker=issuer.ticker, source_root=source_root, structural_root=structural_root)
        public = _public(issuer, result)
        availability = result["availability_type"]
        outcome = "pass" if availability == "available" else "conditional"
        reliability = result["history_reliability"]["label"]
        reliability_counts[reliability] += 1
        case = {"ticker": issuer.ticker, "outcome": outcome, "availability_type": availability, "reliability": reliability, "method": result["method"], **result["scenario_range"], "history_years_used": result["governed_assumptions"]["history_years_used"], "warning": result["warning"]}
        private = {"schema_version": "FINSIGHT-BATCH-07-HISTORY-1", "batch": 7, "valuation_date": BATCH_07_VALUATION_DATE, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "history_backed": result, "controlled_outcome": case}
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)
    after = {str(root): _tree(root) for root in PROTECTED}
    watch_after = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    if before != after or watch_before != watch_after:
        raise RuntimeError("Batch 07 changed protected serving or watchlist state")
    report = {"schema_version": "FINSIGHT-BATCH-07-HISTORY-REPORT-1", "batch": 7, "valuation_date": BATCH_07_VALUATION_DATE, "policy_version": BATCH_07_HISTORY_VERSION, "denominator_tickers": list(BATCH_07_TICKERS), "attempted_count": 10, "pass_count": sum(row["outcome"] == "pass" for row in cases), "conditional_count": sum(row["outcome"] == "conditional" for row in cases), "withheld_count": 0, "numeric_count": 10, "pass_tickers": [row["ticker"] for row in cases if row["outcome"] == "pass"], "conditional_tickers": [row["ticker"] for row in cases if row["outcome"] == "conditional"], "reliability_counts": reliability_counts, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after, "watchlist_changed": False, "watchlist_sha256": watch_before, "cases": cases}
    _immutable(output_root / "batch-07-report.json", _json(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--structural-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "pass_count", "conditional_count", "withheld_count", "numeric_count", "reliability_counts", "serving_artifacts_changed", "watchlist_changed")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
