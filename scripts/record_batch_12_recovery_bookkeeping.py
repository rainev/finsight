#!/usr/bin/env python3
"""Atomically record final Batch 12 recovery learning and still-Withheld state."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.batch_12 import BATCH_12_MANIFEST, BATCH_12_TICKERS
from app.us_valuation.batch_12_recovery import BATCH_12_RECOVERY_VERSION
from app.us_valuation.universe_reset_recovery_learning_watchlist import (
    RecoveryLearningEntry,
)
from app.us_valuation.universe_reset_withheld import UniverseResetWithheldEntry
from run_batch_07_history import PROTECTED, _tree
from run_batch_12_history import WATCHLIST, WITHHELD_REGISTER


AUDIT = "docs/audit/69-batch-12-whole-recovery-result.md"
INITIAL_AUDIT = "docs/audit/67-controlled-batch-12-result.md"

MODELS = {
    "ABT": "post_exact_pro_forma_faded_cash_fcff",
    "BAX": "post_disposition_claim_adjusted_faded_cash_fcff",
    "BDX": "post_spin_continuing_faded_cash_fcff",
    "BMY": "patent_pipeline_faded_cash_fcff",
    "RVTY": "acquisition_restructuring_faded_cash_fcff",
    "HUM": "managed_care_residual_income_normalized_equity_earnings",
    "LLY": "pipeline_high_growth_faded_cash_fcff",
    "CVS": "mixed_health_services_residual_income_normalized_equity_earnings",
    "WST": "post_smartdose_faded_cash_fcff",
    "UHS": "unavailable_post_period_multi_event_state",
}

WHY = {
    "ABT": "Pro-forma combined scale repairs the partial-Exact mismatch, but post-acquisition cash conversion, integration, legal accruals, debt, claims, R&D, and dilution remain load-bearing.",
    "BAX": "Continuing cash is usable, but retained separation claims, the governed tax policy, debt, and uneven post-disposition history keep the result conditional.",
    "BDX": "Continuing cash and spin proceeds reconcile, but post-spin history, product-liability accruals, impairment, separation costs, and R&D remain material.",
    "BMY": "The fixed Hengrui payments and CVR are reserved, while patent loss and contingent pipeline/milestone outcomes remain unmodeled event dependencies.",
    "RVTY": "ACD consideration, restructuring, gross debt, and contingent claims reconcile, but integration and the shorter life-sciences cash history remain material.",
    "HUM": "Residual income anchors value to common equity and ROE, while medical claims, regulated capital, member funds, and underwriting normalization remain material.",
    "LLY": "A source-haircut high-growth fade repairs the generic cap, but pipeline probability, July acquisitions, pending AtaiBeckley, patent/pricing, and manufacturing capex remain load-bearing.",
    "CVS": "Residual income anchors the mixed-health equity object, while claims, PBM/retail mix, reimbursement, capital, debt, and normalized ROE remain material.",
    "WST": "Sale cash is included once, but the available history still contains SmartDose and no filed post-sale continuing cash series exists.",
    "UHS": "Ireland funding, Provo Canyon license revocations, CMG operating responsibility, and pending Talkspace leave no single post-period operating and cash/debt object after one attempt.",
}

THEMES = {
    "ABT": ["post-acquisition pro-forma cash scale", "recorded legal claims and diagnostics integration"],
    "BAX": ["post-disposition continuing cash", "retained separation liabilities and tax normalization"],
    "BDX": ["post-spin continuing cash", "product-liability settlement and separation history"],
    "BMY": ["patent and pipeline cash fade", "fixed versus contingent licensing payments"],
    "RVTY": ["life-sciences acquisition integration", "restructuring and gross-principal debt"],
    "HUM": ["managed-care residual income", "claims, capital, and underwriting normalization"],
    "LLY": ["high-growth pharma fade", "pipeline, acquisition, and manufacturing-capex cash"],
    "CVS": ["mixed-health residual income", "insurance/PBM/retail ROE normalization"],
    "WST": ["post-divestiture continuing cash", "quality risk and capacity reinvestment"],
    "UHS": ["post-period hospital operating state", "acquisition funding and licensing disruption"],
}

TRIGGERS = {
    "ABT": ["three comparable post-Exact annual cash periods", "stable acquisition debt, legal claims, and cancer-diagnostics cash conversion"],
    "BAX": ["three stable continuing post-Vantive cash periods", "retained indemnification and capex-reimbursement runoff"],
    "BDX": ["three comparable post-spin annual cash periods", "material product-liability settlement runoff and stable continuing R&D cash"],
    "BMY": ["patent-loss and launch cash evidence", "Hengrui fixed-payment funding and milestone outcomes"],
    "RVTY": ["stable ACD integration and restructuring runoff", "five comparable life-sciences cash periods"],
    "HUM": ["stable medical-cost trend and regulated capital", "source-bounded normalized ROE after current underwriting pressure"],
    "LLY": ["reported post-July acquisition cash/debt", "durable product growth with normalized manufacturing capex"],
    "CVS": ["stable insurance/PBM/retail segment economics", "source-bounded common ROE and capital requirements"],
    "WST": ["three comparable post-SmartDose annual cash periods", "stable quality/regulatory and capacity-capex cash"],
    "UHS": ["filed post-Ireland/Provo/CMG operating and cash-debt state", "Talkspace closing or termination with final financing"],
}


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=False) + "\n").encode()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def build_updates(report: dict, watchlist: dict, withheld: dict) -> tuple[dict, dict, dict]:
    if (
        report.get("policy_version") != BATCH_12_RECOVERY_VERSION
        or tuple(report.get("recovery_attempted_tickers", ())) != BATCH_12_TICKERS
        or report.get("recovery_attempted_count") != 10
        or (report.get("final_pass_count"), report.get("final_conditional_count"), report.get("final_withheld_count")) != (0, 9, 1)
        or report.get("final_withheld_tickers") != ["UHS"]
    ):
        raise ValueError("Batch 12 recovery report is not final bookkeeping evidence")
    existing_tickers = {row["ticker"] for row in watchlist["entries"]}
    existing_ciks = {row["cik"] for row in watchlist["entries"]}
    additions = []
    for issuer in BATCH_12_MANIFEST:
        if issuer.ticker in existing_tickers or issuer.cik in existing_ciks:
            raise ValueError(f"{issuer.ticker}: duplicate watchlist identity")
        withheld_after = issuer.ticker == "UHS"
        entry = {
            "batch": 12,
            "ticker": issuer.ticker,
            "cik": issuer.cik,
            "issuer_name": issuer.issuer_name,
            "initial_outcome": "withheld" if withheld_after else "conditional_numeric_low",
            "recovery_outcome": "withheld" if withheld_after else "conditional_numeric_low",
            "current_status": "withheld_after_recovery" if withheld_after else "conditional_numeric_low",
            "provisional_model": MODELS[issuer.ticker],
            "why_not_fully_recovered": WHY[issuer.ticker],
            "learning_themes": THEMES[issuer.ticker],
            "revisit_triggers": TRIGGERS[issuer.ticker],
            "evidence_reports": [INITIAL_AUDIT, AUDIT],
        }
        RecoveryLearningEntry.from_dict(entry)
        additions.append(entry)
    updated_watchlist = deepcopy_json(watchlist)
    updated_watchlist["entries"] = sorted(
        [*watchlist["entries"], *additions], key=lambda row: (row["batch"], row["cik"])
    )
    uhs = next(issuer for issuer in BATCH_12_MANIFEST if issuer.ticker == "UHS")
    if any(row["ticker"] == "UHS" or row["cik"] == uhs.cik for row in withheld["entries"]):
        raise ValueError("UHS is already in the withheld register")
    withheld_entry = {
        "batch": 12,
        "ticker": "UHS",
        "cik": uhs.cik,
        "issuer_name": uhs.issuer_name,
        "model_version": BATCH_12_RECOVERY_VERSION,
        "recovery_attempts": 1,
        "final_outcome": "withheld",
        "reason_codes": ["CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"],
        "hard_blockers": [
            "POST_PERIOD_CASH_DEBT_STATE_UNAVAILABLE",
            "POST_PERIOD_OPERATING_STATE_CHANGED",
            "PENDING_TRANSACTION_FINANCING_UNRESOLVED",
        ],
        "evidence_report": AUDIT,
    }
    UniverseResetWithheldEntry.from_dict(withheld_entry)
    updated_withheld = deepcopy_json(withheld)
    updated_withheld["entries"] = sorted(
        [*withheld["entries"], withheld_entry], key=lambda row: (row["batch"], row["cik"])
    )
    receipt = {
        "schema_version": "FINSIGHT-BATCH-12-BOOKKEEPING-1",
        "batch": 12,
        "recovery_attempted_count": 10,
        "watchlist_before_count": len(watchlist["entries"]),
        "watchlist_after_count": len(updated_watchlist["entries"]),
        "watchlist_added_tickers": list(BATCH_12_TICKERS),
        "withheld_before_count": len(withheld["entries"]),
        "withheld_after_count": len(updated_withheld["entries"]),
        "withheld_added_tickers": ["UHS"],
    }
    return updated_watchlist, updated_withheld, receipt


def deepcopy_json(value: object):
    return json.loads(json.dumps(value))


def _atomic_write(path: Path, raw: bytes) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def run(*, recovery_root: Path, output: Path, dry_run: bool = False) -> dict:
    recovery_root, output = Path(recovery_root), Path(output)
    report = json.loads((recovery_root / "batch-12-recovery-report.json").read_text())
    watchlist = json.loads(WATCHLIST.read_text())
    withheld = json.loads(WITHHELD_REGISTER.read_text())
    serving_before = {str(root): _tree(root) for root in PROTECTED}
    watch_before = _sha(WATCHLIST)
    withheld_before = _sha(WITHHELD_REGISTER)
    if watch_before != report.get("watchlist_sha256") or withheld_before != report.get("withheld_register_sha256"):
        raise ValueError("bookkeeping pre-hash differs from recovery staging receipt")
    new_watchlist, new_withheld, receipt = build_updates(report, watchlist, withheld)
    watch_raw = _json_bytes(new_watchlist)
    withheld_raw = _json_bytes(new_withheld)
    receipt.update(
        {
            "watchlist_before_sha256": watch_before,
            "watchlist_after_sha256": _sha_bytes(watch_raw),
            "withheld_before_sha256": withheld_before,
            "withheld_after_sha256": _sha_bytes(withheld_raw),
            "serving_hash_before": serving_before,
            "dry_run": dry_run,
        }
    )
    if not dry_run:
        _atomic_write(WATCHLIST, watch_raw)
        _atomic_write(WITHHELD_REGISTER, withheld_raw)
        if _sha(WATCHLIST) != receipt["watchlist_after_sha256"] or _sha(WITHHELD_REGISTER) != receipt["withheld_after_sha256"]:
            raise RuntimeError("bookkeeping write hash mismatch")
    serving_after = {str(root): _tree(root) for root in PROTECTED}
    if serving_before != serving_after:
        raise RuntimeError("bookkeeping changed protected serving roots")
    receipt["serving_hash_after"] = serving_after
    receipt["serving_artifacts_changed"] = False
    raw = _json_bytes(receipt)
    if output.exists() and output.read_bytes() != raw:
        raise FileExistsError("refusing to overwrite another Batch 12 bookkeeping receipt")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recovery-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    receipt = run(**vars(parser.parse_args()))
    print(json.dumps({key: receipt[key] for key in ("watchlist_before_count", "watchlist_after_count", "withheld_before_count", "withheld_after_count", "serving_artifacts_changed", "dry_run")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
