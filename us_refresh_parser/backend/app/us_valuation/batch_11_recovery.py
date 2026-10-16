"""Single authorized recovery attempt for Batch 11's withheld SYY and BG issuers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .batch_02_practical_inputs import cash_fcff_from_reported
from .batch_07_history import _structural_flow
from .batch_11_history import build_batch_11_history_result


BATCH_11_RECOVERY_VERSION = "BATCH-11-SYY-BG-RECOVERY-1.0"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_syy_recovery_result(
    *, source_root: Path, structural_root: Path
) -> dict:
    source_root = Path(source_root)
    structural_root = Path(structural_root)
    result = build_batch_11_history_result(
        ticker="SYY",
        source_root=source_root,
        structural_root=structural_root,
        allow_syy_current_state_recovery=True,
        model_version=BATCH_11_RECOVERY_VERSION,
    )
    if (
        result["availability_type"] != "conditional_estimate"
        or result["scenario_range"]["base"] is None
        or result["method"] != "pre_jetro_current_state_cash_fcff"
    ):
        raise ValueError("SYY recovery did not produce the governed current-state result")
    result["source_ledger"]["recovery_attempt"] = {
        "attempt_number": 1,
        "economic_state": "pre_jetro_current_state",
        "recovered": True,
        "transaction_value_included": False,
        "transaction_terms_retained_as_invalidation_only": True,
        "interest_sign_treatment": "The reported TTM net-interest fact is negative; cash FCFF uses its $678M expense magnitude exactly once.",
        "release_basis": "The current standalone company has a complete source-linked cash, debt, claims, and diluted-share object. Signed Jetro consideration is not probability-weighted or blended into intrinsic value.",
        "source_hashes": {
            "package_manifest_sha256": _sha(
                structural_root / "SYY" / "package-manifest.json"
            ),
            "structural_filing_sha256": _sha(
                structural_root / "SYY" / "structural-filing.json"
            ),
            "source_receipt_sha256": _sha(
                structural_root / "SYY" / "source-receipt.json"
            ),
            "source_packet_manifest_sha256": _sha(
                source_root / "SYY" / "source-manifest.json"
            ),
        },
    }
    return result


def build_bg_recovery_result(
    *, source_root: Path, structural_root: Path
) -> dict:
    source_root = Path(source_root)
    structural_root = Path(structural_root)
    result = build_batch_11_history_result(
        ticker="BG", source_root=source_root, structural_root=structural_root
    )
    if result["availability_type"] != "not_available":
        raise ValueError("BG recovery must remain fail-closed")

    structural_dir = structural_root / "BG"
    structural_path = structural_dir / "structural-filing.json"
    package_path = structural_dir / "package-manifest.json"
    receipt_path = structural_dir / "source-receipt.json"
    structural = json.loads(structural_path.read_text())
    current_ocf = _structural_flow(
        structural,
        name="NetCashProvidedByUsedInOperatingActivities",
        start="2026-01-01",
        end="2026-06-30",
        expected=-1_126_000_000.,
    )
    current_capex = _structural_flow(
        structural,
        name="PaymentsToAcquirePropertyPlantAndEquipment",
        start="2026-01-01",
        end="2026-06-30",
        expected=779_000_000.,
    )
    current_interest = _structural_flow(
        structural,
        name="InterestExpense",
        start="2026-01-01",
        end="2026-06-30",
        expected=378_000_000.,
    )
    current_pretax = _structural_flow(
        structural,
        name="IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        start="2026-01-01",
        end="2026-06-30",
        expected=1_004_000_000.,
    )
    current_tax = _structural_flow(
        structural,
        name="IncomeTaxExpenseBenefit",
        start="2026-01-01",
        end="2026-06-30",
        expected=222_000_000.,
    )
    tax_rate = current_tax["value"] / current_pretax["value"]
    current_cash_fcff = cash_fcff_from_reported(
        operating_cash_flow=current_ocf["value"],
        capital_expenditures=current_capex["value"],
        spectrum_investment=0.,
        interest_expense=current_interest["value"],
        tax_rate=tax_rate,
    )
    pro_forma_facts = sorted(
        {
            str(row.get("local_name"))
            for row in structural["facts"]
            if "proforma" in str(row.get("local_name", "")).casefold()
        }
    )
    if pro_forma_facts:
        raise ValueError("BG recovery unexpectedly found a pro-forma structural fact")

    warning = (
        "Withheld after one recovery attempt. Viterra closed on 2025-07-02; the comparative H1 excludes Viterra, no filed pro-forma cash-flow facts exist, and current combined H1 cash FCFF remains negative."
    )
    result["model_version"] = BATCH_11_RECOVERY_VERSION
    result["warning"] = warning
    result["baseline"]["method_version"] = BATCH_11_RECOVERY_VERSION
    result["baseline"]["warnings"] = [
        warning,
        "No further automatic recovery is permitted; revisit only on the recorded learning triggers.",
    ]
    result["governed_assumptions"].update(
        {
            "recovery_attempts": 1,
            "current_combined_h1_cash_fcff": current_cash_fcff,
            "current_combined_h1_cash_positive": False,
        }
    )
    result["source_ledger"]["recovery_attempt"] = {
        "attempt_number": 1,
        "recovered": False,
        "official_source_tiers": [
            {
                "tier": "controlling_structural_filing",
                "outcome": "accepted_current_combined_h1",
                "sources": [
                    current_ocf,
                    current_capex,
                    current_interest,
                    current_pretax,
                    current_tax,
                ],
                "cash_fcff": current_cash_fcff,
            },
            {
                "tier": "filed_pro_forma_cash_flow",
                "outcome": "not_disclosed",
                "matched_structural_concepts": pro_forma_facts,
            },
            {
                "tier": "comparable_combined_annual_history",
                "outcome": "unavailable",
                "combined_annual_period_count": 0,
                "basis": "Viterra closed on 2025-07-02; the controlling filing states comparative H1 2025 excludes Viterra.",
            },
        ],
        "release_condition_cleared": False,
        "hard_blockers": [
            "PREDECESSOR_HISTORY_NOT_COMPARABLE",
            "PRO_FORMA_CASH_FLOW_NOT_DISCLOSED",
            "NONFINITE_OR_NONPOSITIVE_VALUE",
        ],
        "reason_codes": [
            "CONDITIONAL_EVENT_MODEL",
            "SPECIALIST_MODEL_UNCERTAINTY",
        ],
        "source_hashes": {
            "package_manifest_sha256": _sha(package_path),
            "structural_filing_sha256": _sha(structural_path),
            "source_receipt_sha256": _sha(receipt_path),
            "source_packet_manifest_sha256": _sha(
                source_root / "BG" / "source-manifest.json"
            ),
        },
    }
    return result
