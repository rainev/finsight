"""One controlled recovery attempt for Batch 49 AVB."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .practical_models import two_stage_cash_flow_value

RECOVERY_VERSION = "BATCH-49-AVB-RECOVERY-1.0"
ATTEMPTED_TICKERS = ("AVB",)


def _event_document(initial: dict[str, Any], accession: str, document_name: str) -> dict[str, Any]:
    rows = [document for document in initial["source_ledger"]["event_sources"]["documents"] if document.get("accession") == accession and str(document.get("path", "")).endswith(document_name)]
    if len(rows) != 1:
        raise ValueError(f"AVB event document unresolved: {accession}/{document_name}")
    return rows[0]


def recover_batch_49_withheld(*, initial: dict[str, Any]) -> dict[str, Any]:
    if initial.get("ticker") != "AVB" or initial.get("availability_type") != "not_available":
        raise ValueError("Batch 49 recovery accepts only confirmed withheld AVB")
    annualized_core_ffo = 5.69 * 2
    diluted_shares = 141_323_779.0
    asset_preservation_capex = 106_450_000.0
    noi_enhancing_capex = 63_714_000.0
    preservation_per_share = asset_preservation_capex * 2 / diluted_shares
    total_current_capital_per_share = (asset_preservation_capex + noi_enhancing_capex) * 2 / diluted_shares
    affo_sensitivity = (annualized_core_ffo - total_current_capital_per_share, annualized_core_ffo - preservation_per_share)
    standalone_values = {name: two_stage_cash_flow_value(cash_flow_per_share=affo_sensitivity[1], growth_rate=0.02, growth_years=8, terminal_growth=0.02, discount_rate=rate) for name, rate in zip(("bear", "base", "bull"), (0.0975, 0.0925, 0.0875))}
    warning = "Withheld after recovery: AVB had only H1 Core FFO and standalone same-store guidance at the August 14 cutoff, not full-year AFFO or recurring-capital reconciliation. The EQR merger was approved August 12 and expected to close August 17, while final combined AFFO, shares, debt/cash, purchase accounting and integration costs were unavailable."
    release = "Revalue after a cutoff-safe closed-company combined AFFO/capital filing, or after explicit authorization of a dated standalone pre-close model supported by comparable AFFO history and automatic expiration at closing."
    result = deepcopy(initial)
    result["model_version"] = RECOVERY_VERSION
    result["warning"] = warning
    result["baseline"] = BaselineValuation(ticker="AVB", method="reit_affo_per_share_dcf", method_version=RECOVERY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(warning, release)).as_private_dict()
    result["governed_assumptions"] = {**result["governed_assumptions"], "recovery_attempts": 1, "recovery_status": "withheld_after_recovery", "invalidation": release}
    result["source_ledger"] = {**result["source_ledger"], "recovery_attempt": {"attempt_number": 1, "policy_version": RECOVERY_VERSION, "decision": "withheld", "final_availability_type": "not_available", "reason_codes": ("MAJOR_EVENT_UNBOUNDED", "AFFO_RECONCILIATION_UNAVAILABLE", "POST_COMBINATION_HISTORY_INCOMPLETE", "VALUATION_WITHHELD"), "hard_blockers": ("MAJOR_EVENT_UNBOUNDED", "MODEL_UNSUPPORTED"), "zero_substitution_used": False}, "standalone_preclose_diagnostic": {"publication_eligible": False, "economic_object": "AvalonBay standalone at 2026-08-14 before expected merger close", "h1_core_ffo_per_share": 5.69, "annualized_core_ffo_per_share": annualized_core_ffo, "h1_diluted_weighted_shares": diluted_shares, "h1_asset_preservation_capex": asset_preservation_capex, "h1_noi_enhancing_capex": noi_enhancing_capex, "capital_source": {"accession": "0000915912-26-000018", "document": "q22026ex-992.htm", "table_locator": "Capitalized Community Expenditures table 1, Total row", "reported_apartment_homes": 85_739, "reported_asset_preservation_capex": 106_450_000.0, "reported_noi_enhancing_capex": 63_714_000.0, "clarification": "85,739 is the apartment-home count, not asset-preservation dollars.", "reported_vs_estimated": "reported"}, "annualized_preservation_capex_per_share": preservation_per_share, "annualized_total_current_capital_per_share": total_current_capital_per_share, "normalized_affo_proxy_sensitivity": affo_sensitivity, "rate_only_values_using_preservation_proxy": standalone_values, "reason": "Asset-preservation capital excludes development and certain newly acquired-community costs, no full-year AFFO outlook exists, and the short-lived standalone object was expected to expire at closing."}, "transaction_diagnostic": {"approval_source": _event_document(initial, "0001104659-26-094930", "tm2622947d1_ex99-1.htm"), "fixed_exchange_ratio": 2.793, "expected_close": "2026-08-17", "used_as_intrinsic_value": False, "post_cutoff_facts_used": False, "combined_affo_available": False, "final_closing_bridge_available": False}, "recovery_evidence_conclusion": "Both standalone and transaction-conditioned routes were exhausted without a cutoff-safe publishable AFFO object."}
    return result


if ATTEMPTED_TICKERS != ("AVB",):
    raise RuntimeError("Batch 49 recovery contract invalid")
