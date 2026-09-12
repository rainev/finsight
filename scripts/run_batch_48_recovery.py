#!/usr/bin/env python3
"""Run the one authorized Batch 48 WY/EQR recovery attempt."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_48 import BATCH_48_MANIFEST, BATCH_48_TICKERS, BATCH_48_VALUATION_DATE
from app.us_valuation.batch_48_recovery import ATTEMPTED_TICKERS, RECOVERY_VERSION, recover_batch_48_withheld
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_08_history import _base
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_48_history import _public as initial_public

CONFIRMED_INITIAL_REPORT_SHA256 = "54a03164392ae10e154621820aa2ac446efd7f08cb2ae1707a9fcb682d073132"


def _wy_public(issuer, result):
    scenario = result["scenario_range"]
    base = result["scenario_rows"][1]
    assumptions = result["governed_assumptions"]
    public_assumptions = {"forecast_policy_version": RECOVERY_VERSION, "forecast_mode": "timber_distribution_exact", "history_policy_version": assumptions["history_policy_version"], "history_years_used": assumptions["history_years_used"], "normalization_basis": assumptions["normalization_basis"], "assumption_source_mix": assumptions["assumption_source_mix"], "forecast_years": 1, "initial_revenue_growth": base["distribution_growth"], "cost_of_equity": base["cost_of_equity"], "terminal_growth": base["distribution_growth"], "owner_distribution_per_share": base["owner_distribution_per_share"], "equity_floor_applied": False, "equity_floor_basis": "not applied", "source_policy": "Reported SEC Adjusted FAD, cash-return policy, dividend history and shares; no timber NAV, stock price or analyst target."}
    model = {"model": "total_payout_ddm", "output_type": "intrinsic_value_per_share", "currency": "USD", "intrinsic_value_per_share": scenario["base"], "publication_state": "review_required", "errors": [], "warnings": [result["warning"]]}
    value = _base(issuer, result, primary="total_payout_ddm", model=model, assumptions=public_assumptions)
    value["primary_valuation_method"] = result["method"]
    value["model_policy"]["primary"] = "total_payout_ddm"
    value["model_policy"].pop("fallback_from", None)
    value["model_policy"]["reason"] = result["warning"]
    value["models"] = {"total_payout_ddm": model}
    value["scenarios"] = {name: {"total_payout_ddm": {"model": "total_payout_ddm", "intrinsic_value_per_share": scenario[key], "publication_state": "review_required"}} for name, key in zip(("bear", "base", "bull"), ("low", "base", "high"))}
    value["issuer"]["classification_reason"] = "Frozen Batch 48 timber cash-return recovery using issuer-reported distribution evidence."
    value["methodology"]["forecast_policy"] = RECOVERY_VERSION
    value["methodology"]["sector_framework"] = result["method"]
    value["forecast_quality"]["policy_version"] = RECOVERY_VERSION
    value["reliability"] = result["history_reliability"]
    value = sanitize_public_artifact(value)
    if value["availability_type"] == "available":
        value["availability_type"] = "conditional_estimate"
    if value["availability_type"] != "conditional_estimate" or value["scenario_range"]["base"] != scenario["base"] or value["model_policy"]["primary"] != "total_payout_ddm":
        raise RuntimeError("WY: recovered public mismatch")
    return value


def run(*, initial_root: Path, source_root: Path, output_root: Path) -> dict:
    initial_root, source_root, output_root = map(Path, (initial_root, source_root, output_root))
    report_path = initial_root / "batch-48-report.json"
    if hashlib.sha256(report_path.read_bytes()).hexdigest() != CONFIRMED_INITIAL_REPORT_SHA256:
        raise ValueError("confirmed Batch 48 initial report drifted")
    before = {str(path): _tree(path) for path in PROTECTED}
    watchlist_hash = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    withheld_hash = hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    cases = []
    for issuer in BATCH_48_MANIFEST:
        private_path = initial_root / "generated" / issuer.ticker / "valuation-private.json"
        public_path = initial_root / "staged-public" / f"{issuer.ticker}.json"
        private = json.loads(private_path.read_text())
        if issuer.ticker in ATTEMPTED_TICKERS:
            initial = private["history_backed"]
            facts_path = source_root / issuer.ticker / "companyfacts.json"
            verification = initial["source_ledger"]["runtime_source_verification"]
            if hashlib.sha256(facts_path.read_bytes()).hexdigest() != verification["packet_payload_sha256"]["companyfacts.json"]:
                raise ValueError(f"{issuer.ticker}: confirmed recovery source drifted")
            result = recover_batch_48_withheld(initial=initial, facts=json.loads(facts_path.read_text()))
            recovered = result["availability_type"] == "conditional_estimate"
            case = {"ticker": issuer.ticker, "initial_outcome": "withheld", "recovery_outcome": "conditional" if recovered else "withheld", "availability_type": result["availability_type"], "reliability": result["history_reliability"]["label"] if recovered else None, "method": result["method"], **result["scenario_range"], "warning": result["warning"]}
            private = {**private, "schema_version": "FINSIGHT-BATCH-48-RECOVERY-1", "history_backed": result, "controlled_outcome": case}
            public = _wy_public(issuer, result) if issuer.ticker == "WY" else initial_public(issuer, result)
            if issuer.ticker == "EQR":
                public["public_assumptions"]["forecast_policy_version"] = RECOVERY_VERSION
                public["methodology"]["forecast_policy"] = RECOVERY_VERSION
                public["forecast_quality"]["policy_version"] = RECOVERY_VERSION
                public["review"]["confidence_grade"] = "withheld"
            _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
            _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        else:
            case = {"ticker": issuer.ticker, "initial_outcome": "conditional", "recovery_outcome": "not_applicable", "availability_type": "conditional_estimate"}
            _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", private_path.read_bytes())
            _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", public_path.read_bytes())
        cases.append(case)
    after = {str(path): _tree(path) for path in PROTECTED}
    if before != after or watchlist_hash != hashlib.sha256(WATCHLIST.read_bytes()).hexdigest() or withheld_hash != hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest():
        raise RuntimeError("protected state changed")
    report = {"schema_version": "FINSIGHT-BATCH-48-RECOVERY-REPORT-1", "batch": 48, "valuation_date": BATCH_48_VALUATION_DATE, "policy_version": RECOVERY_VERSION, "denominator_tickers": list(BATCH_48_TICKERS), "attempted_recovery_tickers": list(ATTEMPTED_TICKERS), "recovery_attempt_count": 2, "recovered_to_conditional_count": 1, "still_withheld_count": 1, "still_withheld_tickers": ["EQR"], "pass_count": 0, "conditional_count": 9, "withheld_count": 1, "numeric_count": 9, "reliability_counts": {"High": 0, "Medium": 0, "Low": 9}, "confirmed_initial_report_sha256": CONFIRMED_INITIAL_REPORT_SHA256, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after, "watchlist_changed": False, "watchlist_sha256": watchlist_hash, "withheld_register_changed": False, "withheld_register_sha256": withheld_hash, "cases": cases}
    _immutable(output_root / "batch-48-recovery-report.json", _json(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    result = run(**vars(parser.parse_args()))
    print(json.dumps({key: result[key] for key in ("recovery_attempt_count", "recovered_to_conditional_count", "still_withheld_count", "pass_count", "conditional_count", "withheld_count", "numeric_count")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
