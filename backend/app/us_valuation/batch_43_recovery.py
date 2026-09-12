"""One controlled recovery attempt for Batch 43 DVN, NEM and LYB."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_35_history import _period_flow
from .batch_43 import BATCH_43_TICKERS
from .batch_43_history import build_batch_43_history_result


BATCH_43_RECOVERY_VERSION = "BATCH-43-DVN-NEM-LYB-RECOVERY-1.0"
PERIOD = "2026-06-30"
ATTEMPTED = frozenset({"DVN", "NEM", "LYB"})
RECOVERED_PASS_TICKERS = frozenset()
RECOVERED_CONDITIONAL_TICKERS = frozenset(set(BATCH_43_TICKERS) - ATTEMPTED)
RECOVERED_WITHHELD_TICKERS = ATTEMPTED


def _document(initial: dict[str, Any], suffix: str) -> dict[str, Any]:
    rows = [row for row in initial["source_ledger"]["event_sources"]["documents"] if str(row.get("path", "")).endswith(suffix)]
    if len(rows) != 1:
        raise ValueError(f"event document unresolved: {suffix}")
    return rows[0]


def _finish(initial: dict[str, Any], *, reason: str, release: str, reason_codes: list[str], evidence: dict[str, Any], rejected_diagnostic: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(initial)
    ticker = value["ticker"]
    baseline = BaselineValuation(ticker=ticker, method=value["method"], method_version=BATCH_43_RECOVERY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(reason, release))
    value.update({"model_version": BATCH_43_RECOVERY_VERSION, "warning": reason, "baseline": baseline.as_private_dict()})
    value["governed_assumptions"] = {**initial["governed_assumptions"], "normalization_basis": "source_exhaustive_recovery_attempt_rejected_at_current_company_scope_gate", "reason_codes": reason_codes, "invalidation": release}
    value["source_ledger"] = {**initial["source_ledger"], "recovery_evidence": evidence, "rejected_recovery_diagnostic": {**rejected_diagnostic, "publication_allowed": False}, "recovery_attempt": {"attempted": True, "initial_availability_type": "not_available", "final_availability_type": "not_available", "source_exhaustion_complete": True, "market_price_used": False, "analyst_target_used": False, "competitor_value_used": False}}
    return value


def _dvn(initial: dict[str, Any]) -> dict[str, Any]:
    verification = initial["source_ledger"]["runtime_source_verification"]
    pro_forma = {
        "source_kind": "issuer_filed_unaudited_pro_forma_table",
        "accession": verification["accession"],
        "filed": verification["filed"],
        "primary_document": verification["primary_document"],
        "primary_document_sha256": verification["primary_document_sha256"],
        "merger_assumed_effective": "2025-01-01",
        "revenue": {"q2_2026": 8_150_000_000., "q2_2025": 6_240_000_000., "h1_2026": 13_894_000_000., "h1_2025": 12_586_000_000.},
        "net_earnings": {"q2_2026": 2_048_000_000., "q2_2025": 1_298_000_000., "h1_2026": 2_464_000_000., "h1_2025": 2_138_000_000.},
        "reported_cash_flow_fields": [],
        "reported_vs_estimated": "reported_revenue_and_earnings_only",
    }
    actual = {"coterra_revenue_since_close": 1_300_000_000., "coterra_earnings_since_close": 230_000_000., "close_date": "2026-05-07"}
    reason = "Recovery attempted; DVN remains withheld. The filing adds combined-company pro-forma revenue and earnings, but no matching OCF, capex, interest or working-capital history. Converting those earnings into FCFF or applying legacy Devon cash conversion to Coterra would invent the load-bearing cash assumptions."
    release = "Revalue when issuer-filed combined pro-forma cash flows or sufficient post-close history establish OCF, capex, interest and working-capital conversion on the current debt and share base."
    return _finish(initial, reason=reason, release=release, reason_codes=["POST_COMBINATION_CASH_HISTORY_INCOMPLETE", "PRO_FORMA_EARNINGS_NOT_CASH_FLOW", "VALUATION_WITHHELD"], evidence={"pro_forma_table": pro_forma, "actual_coterra_since_close": actual}, rejected_diagnostic={"reported_ttm_cash_fcff": initial["reported_inputs"]["ttm_cash_fcff"], "reported_ttm_revenue": initial["reported_inputs"]["ttm_revenue"], "why_rejected": "The TTM is a partial combined period; the pro-forma table does not supply cash-flow conversion or capital intensity."})


def _nem(initial: dict[str, Any]) -> dict[str, Any]:
    press = _document(initial, "tm2623048d1_ex99-1.htm")
    agreement = _document(initial, "tm2623048d1_ex10-1.htm")
    terms = {
        "source_kind": "issuer_filed_jv_amendment_and_press_release",
        "press_release": press,
        "agreement": agreement,
        "newmont_payment_after_fourmile_contribution": 1_950_000_000.,
        "newmont_deemed_contribution": 1_950_000_000.,
        "barrick_deemed_contribution": 3_114_935_064.94,
        "illustrative_pre_recalculation_membership": {"barrick": .615, "newmont": .385},
        "project_contribution_timing": "as soon as reasonably practicable",
        "assumed_project_liabilities": None,
        "confidential_settlement_value": None,
        "final_membership_after_valuation": None,
        "reported_vs_estimated": "reported_known_terms_with_explicit_unavailable_claims",
    }
    reason = "Recovery attempted; NEM remains withheld. The $1.95B payment is exact, but project fair values, assumed liabilities, final ownership recalculation and confidential settlement economics are not. Deducting only the payment would falsely bound a larger transaction; using deemed contributions as fair value would be unsupported."
    release = "Revalue after implementation evidence supplies contribution dates, project valuation, assumed liabilities, final NGM ownership, retained royalties and settlement treatment."
    return _finish(initial, reason=reason, release=release, reason_codes=["MATERIAL_JV_EVENT_UNBOUNDED", "CONFIDENTIAL_SETTLEMENT_UNQUANTIFIED", "ASSUMED_PROJECT_LIABILITIES_UNAVAILABLE", "VALUATION_WITHHELD"], evidence={"ngm_fourmile_terms": terms}, rejected_diagnostic={"known_payment_reserve": 1_950_000_000., "why_rejected": "A known cash payment does not cap the transferred project rights, assumed liabilities, ownership adjustment or settlement economics."})


def _lyb(initial: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    loss = _period_flow(structural, ("GainLossOnSaleOfBusiness",), PERIOD, target_days=180)
    cash_contribution = _period_flow(structural, ("ProceedsFromDivestitureOfBusinessesNetOfCashDivested",), PERIOD, target_days=180)
    discontinued = _period_flow(structural, ("IncomeLossFromDiscontinuedOperationsNetOfTax",), PERIOD, target_days=180)
    release_doc = _document(initial, "a2026q2ex991_pressrelease.htm")
    segment_doc = _document(initial, "a2026q2ex992_businessresul.htm")
    evidence = {"reported_event_facts": {"european_sale_loss": loss, "cash_contribution_to_sold_businesses": cash_contribution, "discontinued_operations_net_income_loss": discontinued}, "event_documents": {"earnings_release": release_doc, "segment_results": segment_doc}, "continuing_company_ocf": None, "continuing_company_capex": None, "continuing_company_working_capital_cash": None, "reported_vs_estimated": "reported_event_and_segment_earnings_with_unavailable_continuing_cash_fields"}
    reason = "Recovery attempted; LYB remains withheld. The filing quantifies the $310M cash contribution, $734M sale loss and discontinued earnings, and provides segment EBITDA, but it does not provide continuing-company OCF, working-capital cash or capex. Converting segment earnings into FCFF would require invented allocations."
    release = "Revalue with issuer-filed continuing-company cash flow and capex, pro-forma continuing periods, or sufficient post-disposal history after the European sale and refinery discontinuation."
    return _finish(initial, reason=reason, release=release, reason_codes=["CONTINUING_COMPANY_CASH_SCOPE_UNAVAILABLE", "DISPOSED_OPERATIONS_CASH_NOT_SEPARABLE", "SEGMENT_EARNINGS_NOT_FCFF", "VALUATION_WITHHELD"], evidence=evidence, rejected_diagnostic={"reported_consolidated_ttm_cash_fcff": initial["reported_inputs"]["ttm_cash_fcff"], "reported_consolidated_ttm_revenue": initial["reported_inputs"]["ttm_revenue"], "why_rejected": "Consolidated cash history mixes sold European assets, refinery discontinued operations and continuing operations."})


def build_batch_43_recovery_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path, cop_annual_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_43_TICKERS:
        raise ValueError(ticker)
    initial = build_batch_43_history_result(ticker=ticker, source_root=source_root, structural_root=structural_root, event_root=event_root, structural_cache_root=structural_cache_root, cop_annual_root=cop_annual_root)
    if ticker not in ATTEMPTED:
        value = deepcopy(initial)
        value["model_version"] = BATCH_43_RECOVERY_VERSION
        value["baseline"] = {**value["baseline"], "method_version": BATCH_43_RECOVERY_VERSION}
        return value
    if ticker == "DVN":
        return _dvn(initial)
    if ticker == "NEM":
        return _nem(initial)
    structural = json.loads((Path(structural_root) / "LYB/structural-filing.json").read_text())
    return _lyb(initial, structural)


if RECOVERED_PASS_TICKERS | RECOVERED_CONDITIONAL_TICKERS | RECOVERED_WITHHELD_TICKERS != set(BATCH_43_TICKERS):
    raise RuntimeError("Batch 43 recovery classification mismatch")
