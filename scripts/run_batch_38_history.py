#!/usr/bin/env python3
"""Stage Batch 38 private/public candidates without touching serving state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_38 import BATCH_38_MANIFEST, BATCH_38_TICKERS, BATCH_38_VALUATION_DATE
from app.us_valuation.batch_38_history import BATCH_38_HISTORY_VERSION, build_batch_38_history_result
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_08_history import _public as _prior_public
from run_batch_15_history import WITHHELD_REGISTER


def _public(issuer, result):
    value = _prior_public(issuer, result)
    if result["availability_type"] == "not_available":
        from run_batch_36_recovery import _public as unavailable_public
        value = unavailable_public(issuer, result)
        value["public_assumptions"]["forecast_policy_version"] = BATCH_38_HISTORY_VERSION
        value["forecast_quality"]["policy_version"] = BATCH_38_HISTORY_VERSION
        value["methodology"]["forecast_policy"] = BATCH_38_HISTORY_VERSION
        value["public_assumptions"]["forecast_mode"] = "unavailable_model_or_claim_gate"
        value["public_assumptions"]["forecast_years"] = result['governed_assumptions']['forecast_years']
        value['issuer']['classification_reason'] = 'Frozen Batch 38 source, history, event and model review.'
        value.pop("automated_review", None)
        return sanitize_public_artifact(value)
    base = result["scenario_rows"][1]
    is_fcff = "fcff" in result["method"]
    if is_fcff:
        model_name = "fcff_dcf"
        value["bridge_quality"] = {"blocking_fields": [], "bounded_fields": [], "complete": True, "decision": "complete", "intrinsic_value_range": {"low": result["scenario_range"]["base"], "midpoint": result["scenario_range"]["base"], "high": result["scenario_range"]["base"], "spread_ratio": 0., "spread_limit": .01}, "reason_codes": [], "usable": True}
        value["public_assumptions"].update({"forecast_mode": "enterprise_cash_fcff_exact", "starting_cash_fcff_per_share": base["starting_cash_fcff"] / base["shares"], "bridge_adjustment_per_share": (base["cash_and_investments"] - base["debt_and_finance_leases"] - base["other_equity_claims"]) / base["shares"], "initial_revenue_growth": base["growth"], "policy_wacc": base["wacc"], "terminal_growth": base["terminal_growth"]})
    else:
        model_name = "residual_income"
        value["public_assumptions"].pop("normalized_earnings_factor", None)
        value["public_assumptions"].pop("earnings_multiple", None)
        value["public_assumptions"].update({"forecast_mode": "residual_income_exact", "book_value_per_share": base["book_value_per_share"], "current_roe": base["current_roe"], "current_payout_ratio": base["current_payout_ratio"], "cost_of_equity": base["cost_of_equity"], "terminal_roe": base["terminal_roe"], "terminal_growth": base["terminal_growth"]})
    value["model_policy"]["primary"] = model_name
    value["model_policy"].pop("fallback_from", None)
    value["models"] = {model_name: {"model": model_name, "output_type": "intrinsic_value_per_share", "currency": "USD", "intrinsic_value_per_share": result["scenario_range"]["base"], "publication_state": "review_required", "errors": [], "warnings": [result["warning"]]}}
    value["issuer"]["classification_reason"] = "Frozen Batch 38 source, history, event and model review."
    value["public_assumptions"]["forecast_policy_version"] = BATCH_38_HISTORY_VERSION
    value["public_assumptions"]["forecast_years"] = result["governed_assumptions"]["forecast_years"]
    value["forecast_quality"]["policy_version"] = BATCH_38_HISTORY_VERSION
    value["methodology"]["forecast_policy"] = BATCH_38_HISTORY_VERSION
    value["model_policy"]["reason"] = result["warning"]
    value.pop("automated_review", None)
    value = sanitize_public_artifact(value)
    if value["availability_type"] != result["availability_type"] or value["scenario_range"]["base"] != result["scenario_range"]["base"]:
        raise RuntimeError(issuer.ticker)
    return value


def run(*, source_root: Path, structural_root: Path, event_root: Path, output_root: Path, structural_cache_root: Path | None = None):
    before = {str(path): _tree(path) for path in PROTECTED}
    watchlist_hash = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    withheld_hash = hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    cases, reliability_counts = [], {"High": 0, "Medium": 0, "Low": 0}
    for issuer in BATCH_38_MANIFEST:
        result = build_batch_38_history_result(ticker=issuer.ticker, source_root=source_root, structural_root=structural_root, event_root=event_root, structural_cache_root=structural_cache_root)
        public = _public(issuer, result)
        outcome = "pass" if result["availability_type"] == "available" else "conditional" if result["availability_type"] == "conditional_estimate" else "withheld"
        label = result["history_reliability"]["label"] if result["history_reliability"] else None
        if label:
            reliability_counts[label] += 1
        case = {"ticker": issuer.ticker, "outcome": outcome, "availability_type": result["availability_type"], "reliability": label, "method": result["method"], **result["scenario_range"], "history_years_used": result["governed_assumptions"].get("history_years_used"), "warning": result["warning"]}
        private = {"schema_version": "FINSIGHT-BATCH-38-HISTORY-1", "batch": 38, "valuation_date": BATCH_38_VALUATION_DATE, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "history_backed": result, "controlled_outcome": case}
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)
    after = {str(path): _tree(path) for path in PROTECTED}
    if before != after or watchlist_hash != hashlib.sha256(WATCHLIST.read_bytes()).hexdigest() or withheld_hash != hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest():
        raise RuntimeError("protected state changed")
    report = {"schema_version": "FINSIGHT-BATCH-38-HISTORY-REPORT-1", "batch": 38, "valuation_date": BATCH_38_VALUATION_DATE, "policy_version": BATCH_38_HISTORY_VERSION, "denominator_tickers": list(BATCH_38_TICKERS), "attempted_count": 10, "pass_count": sum(row["outcome"] == "pass" for row in cases), "conditional_count": sum(row["outcome"] == "conditional" for row in cases), "withheld_count": sum(row["outcome"] == "withheld" for row in cases), "numeric_count": sum(row["outcome"] != "withheld" for row in cases), "pass_tickers": [row["ticker"] for row in cases if row["outcome"] == "pass"], "conditional_tickers": [row["ticker"] for row in cases if row["outcome"] == "conditional"], "withheld_tickers": [row["ticker"] for row in cases if row["outcome"] == "withheld"], "reliability_counts": reliability_counts, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after, "watchlist_changed": False, "watchlist_sha256": watchlist_hash, "withheld_register_changed": False, "withheld_register_sha256": withheld_hash, "cases": cases}
    _immutable(output_root / "batch-38-report.json", _json(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path, required=True)
    parser.add_argument("--event-root", type=Path, required=True)
    parser.add_argument("--structural-cache-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "pass_count", "conditional_count", "withheld_count", "numeric_count", "reliability_counts")}, sort_keys=True))


if __name__ == "__main__":
    main()
