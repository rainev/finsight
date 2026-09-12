"""One controlled recovery attempt for Batch 38 GPN and CPAY."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
import json
from typing import Any

from app.valuation.bank import residual_income_valuation

from .baseline import AvailabilityType, BaselineValuation
from .batch_35_history import _instant, _rows, _source
from .batch_38 import BATCH_38_TICKERS
from .batch_38_history import build_batch_38_history_result
from .batch_38_insurers import _nci_claims, _period_flow, _preferred, _share_exact
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, summarize_history_metric
from .reliability import assess_reliability


BATCH_38_RECOVERY_VERSION = "BATCH-38-GPN-CPAY-RECOVERY-1.0"
PERIOD = "2026-06-30"
VALUATION_DATE = "2026-08-14"
RECOVERED_PASS_TICKERS = frozenset()
RECOVERED_CONDITIONAL_TICKERS = frozenset(set(BATCH_38_TICKERS) - {"GPN"})
RECOVERED_WITHHELD_TICKERS = frozenset({"GPN"})


def _annual_common_earnings(facts: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    selected: dict[str, dict[str, Any]] = {}
    concept = "NetIncomeLossAvailableToCommonStockholdersBasic"
    for row in _rows(facts, concept):
        if row.get("form") not in {"10-K", "10-K/A"} or row.get("filed", "") > VALUATION_DATE:
            continue
        if not row.get("start") or not row.get("end"):
            continue
        try:
            span = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
        except (KeyError, TypeError, ValueError):
            continue
        if not 300 <= span <= 380 or not isinstance(row.get("val"), (int, float)):
            continue
        old = selected.get(row["end"])
        if old is None or (row.get("filed", ""), row.get("accn", "")) > (old.get("filed", ""), old.get("accn", "")):
            selected[row["end"]] = row
    ends = sorted(selected)[-3:]
    if ends != ["2023-12-31", "2024-12-31", "2025-12-31"]:
        raise ValueError("CPAY: three exact common-earnings years are required")
    return tuple(
        {"period_end": end, "value": float(selected[end]["val"]), "source": _source(selected[end], concept)}
        for end in ends
    )


def _cpay_attempt(initial: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any]) -> dict[str, Any]:
    annual = _annual_common_earnings(facts)
    current = _period_flow(structural, ("NetIncomeLossAvailableToCommonStockholdersBasic",), PERIOD, target_days=180)
    prior = _period_flow(structural, ("NetIncomeLossAvailableToCommonStockholdersBasic",), "2025-06-30", target_days=180)
    ttm = annual[-1]["value"] + current["value"] - prior["value"]

    equity = _instant(structural, ("StockholdersEquity",), PERIOD)
    opening_equity = _instant(structural, ("StockholdersEquity",), "2025-12-31")
    preferred, preferred_status, preferred_sources = _preferred(structural, PERIOD)
    share = _share_exact(structural, facts, PERIOD)
    nci, redeemable_nci = _nci_claims(structural, PERIOD)
    common_equity = equity["value"] - preferred
    if min(ttm, common_equity, share["value"]) <= 0:
        raise ValueError("CPAY: nonpositive parent/common input")

    customer_current = _instant(structural, ("ContractWithCustomerLiabilityCurrent",), PERIOD)
    customer_prior = _instant(structural, ("ContractWithCustomerLiabilityCurrent",), "2025-12-31")
    restricted = _instant(structural, ("RestrictedCashAndCashEquivalents",), PERIOD)
    cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), PERIOD)
    payable_current = _instant(structural, ("AccountsPayableCurrent",), PERIOD)
    payable_prior = _instant(structural, ("AccountsPayableCurrent",), "2025-12-31")
    accrued_current = _instant(structural, ("AccruedLiabilitiesCurrent",), PERIOD)
    accrued_prior = _instant(structural, ("AccruedLiabilitiesCurrent",), "2025-12-31")
    pooled = _period_flow(structural, ("IncreaseDecreaseInAccountsPayableAndAccruedLiabilities",), PERIOD, target_days=180)
    ftc = _period_flow(structural, ("LitigationSettlementLoss",), PERIOD, target_days=180)
    movements = {
        "accounts_payable": payable_current["value"] - payable_prior["value"],
        "accrued_expenses": accrued_current["value"] - accrued_prior["value"],
        "customer_deposits": customer_current["value"] - customer_prior["value"],
    }
    movement_total = sum(movements.values())
    residual = pooled["value"] - movement_total
    if abs(residual - ftc["value"]) > 100_000:
        raise ValueError("CPAY: pooled funding reconciliation changed")

    observations = [
        HistoryObservation("annual", row["period_end"], int(row["period_end"][:4]), row["value"], "USD", "reported annual common earnings", (row["source"],))
        for row in annual
    ]
    observations.append(HistoryObservation("operating_ttm", PERIOD, None, ttm, "USD", "latest FY plus current H1 less prior H1", (annual[-1]["source"], current, prior)))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    if metric is None:
        raise ValueError("CPAY: common-earnings history unavailable")
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "payments_parent_equity_residual_income_equity_earnings", VALUATION_DATE, tuple(row["period_end"] for row in annual), (metric,), True, "reported_and_company_history")

    grant = 328_213.0
    shares = (share["value"] + grant, share["value"], share["value"])
    roes = (.10, .14, .18)
    payouts = (.20, .30, .40)
    costs = (.11, .095, .085)
    terminal_roes = (.085, .105, .115)
    terminal_growth = (.01, .02, .025)
    rows: list[dict[str, Any]] = []
    traces: dict[str, Any] = {}
    for index, name in enumerate(("bear", "base", "bull")):
        book = common_equity / shares[index]
        trace = residual_income_valuation(
            book_value_per_share=book,
            current_roe=roes[index],
            cost_of_equity=costs[index],
            current_payout_ratio=payouts[index],
            terminal_roe=terminal_roes[index],
            terminal_growth=terminal_growth[index],
            years=5,
        )
        raw = float(trace["intrinsic_value"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": raw, "book_value_per_share": book, "current_roe": roes[index], "current_payout_ratio": payouts[index], "cost_of_equity": costs[index], "terminal_roe": terminal_roes[index], "terminal_growth": terminal_growth[index], "shares": shares[index], "preferred_claim": preferred, "ending_common_equity": common_equity, "limited_liability_floor_applied": False})
        traces[name] = trace
    scenario = {"low": rows[0]["raw_value_per_share"], "base": rows[1]["raw_value_per_share"], "high": rows[2]["raw_value_per_share"]}
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError("CPAY: invalid recovery range")

    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"))
    warning = (
        "Conditional Low parent/common-equity earnings baseline. Customer deposits, restricted cash, securitized receivables and related funding remain inside the equity economics and are never treated as free issuer cash. "
        "The recorded $100M FTC charge is already included in current earnings and is not deducted twice. The Maintenance sale is pending, so its expected proceeds and gain are excluded. July performance units are bounded through bear-case dilution. "
        "Customer-funding behavior, credit losses, leverage, the pending disposal and legal outcomes can move actual value outside this range."
    )
    invalidation = "Revalue if common earnings/equity, customer-fund segregation, FTC terms, Maintenance closing economics, NCI or diluted shares move outside the source-bounded range."
    baseline = BaselineValuation(ticker="CPAY", method="payments_parent_equity_residual_income_equity_earnings", method_version=BATCH_38_RECOVERY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(warning, invalidation))

    value = deepcopy(initial)
    event_sources = deepcopy(initial["source_ledger"]["event_sources"])
    event_sources["treatment"] = "FTC charge is already in earnings; July PSUs are a bounded dilution sensitivity; unclosed Maintenance proceeds and gain are excluded."
    for receipt in event_sources["screened_filings"]:
        receipt["treatment"] = event_sources["treatment"]
    value.update({"method": baseline.method, "model_version": BATCH_38_RECOVERY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"raw_ttm_common_earnings": ttm, "beginning_total_equity": opening_equity["value"], "ending_total_equity": equity["value"], "ending_common_equity": common_equity, "preferred_claim": preferred, "share_count": share["value"]}, "history_reliability": reliability.as_dict(), "warning": warning, "baseline": baseline.as_private_dict()})
    value["governed_assumptions"] = {**profile.public_metadata(), "forecast_years": 5, "history_years_used": 3, "normalization_basis": "three_annual_common_earnings_periods_plus_current_ttm", "assumption_source_mix": "reported_parent_equity_earnings_and_governed_low_reliability_scenarios", "current_roe": roes, "current_payout_ratio": payouts, "cost_of_equity": costs, "terminal_roe": terminal_roes, "terminal_growth": terminal_growth, "shares": shares, "earnings_multiples": tuple(row["raw_value_per_share"] * row["shares"] / ttm for row in rows), "equity_floor_basis": "not applied", "route_is_equity_level": True, "ev_debt_bridge_applied": False, "customer_cash_used_as_free_cash": False, "preferred_claim_status": preferred_status, "reason_codes": ["CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"], "calculator_calibration": "Exact residual-income default replay.", "invalidation": invalidation}
    value["source_ledger"] = {**initial["source_ledger"], "event_sources": event_sources, "common_earnings_reconstruction": {"annual_history": list(annual), "latest_fy": annual[-1], "current_ytd": current, "prior_ytd": prior, "ttm": ttm, "formula": "FY2025 + H1 2026 - H1 2025"}, "company_history_profile": profile.as_private_dict(), "equity_model_context": {"ending_parent_equity": equity, "opening_parent_equity": opening_equity, "preferred_status": preferred_status, "preferred_sources": preferred_sources, "current_share_count": share, "nonredeemable_nci": nci, "redeemable_nci": redeemable_nci, "treatment": "Parent stockholders' equity and common-attributable earnings are used; NCI is disclosed and not deducted twice."}, "customer_funding_reconciliation": {"corporate_cash": cash, "restricted_cash": restricted, "customer_deposits_current": customer_current, "customer_deposits_prior": customer_prior, "accounts_payable_current": payable_current, "accounts_payable_prior": payable_prior, "accrued_expenses_current": accrued_current, "accrued_expenses_prior": accrued_prior, "pooled_cash_flow_line": pooled, "balance_sheet_movements": movements, "movement_total": movement_total, "residual": residual, "recorded_ftc_charge": ftc, "formula": "pooled AP/accrued/customer-deposit OCF line less balance-sheet movements; residual reconciles to recorded FTC charge", "used_as_free_cash": False}, "pending_maintenance_disposition": {"accession": filing["accession"], "period_end": PERIOD, "status": "signed_pending_regulatory_approval_at_cutoff", "expected_gross_proceeds": 800_000_000.0, "expected_pre_tax_gain_range": [460_000_000.0, 515_000_000.0], "cash_held_for_sale": 24_725_000.0, "proceeds_or_gain_included_in_value": False, "reported_vs_estimated": "reported filing narrative; excluded while unclosed"}, "post_cutoff_share_event": {"accession": "0001175454-26-000042", "filed": "2026-07-24", "grant_date": "2026-07-22", "maximum_psus": grant, "bear_case_dilution_only": True, "reported_vs_estimated": "reported event filing"}, "residual_income_trace": {"states": traces}, "recovery_attempt": {"attempted": True, "initial_availability_type": "not_available", "final_availability_type": "conditional_estimate", "customer_funding_fcff_gate_closed": False, "parent_equity_fallback_gate_closed": True, "market_price_used": False, "analyst_target_used": False, "competitor_value_used": False}}
    return value


def _gpn_attempt(initial: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(initial)
    total_cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), PERIOD)
    settlement_line = _instant(structural, ("LinesOfCreditCurrent",), PERIOD)
    base_rows = initial["source_ledger"]["raw_scenario_rows"]
    favorable = []
    from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
    for row in base_rows:
        state = EnterpriseCashFlowState(row["starting_cash_fcff"], row["growth"], row["terminal_growth"], row["wacc"], total_cash["value"], row["debt_and_finance_leases"], 0.0, 0.0, row["shares"])
        trace = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
        favorable.append({"name": row["name"], "raw_value_per_share": trace["intrinsic_value_per_share"], "state": {"starting_cash_fcff": state.cash_fcff, "growth": state.initial_growth, "terminal_growth": state.terminal_growth, "wacc": state.wacc, "cash": state.cash_and_investments, "debt": state.interest_bearing_debt, "claims": 0.0, "shares": state.diluted_shares}, "trace": trace})
    if favorable[1]["raw_value_per_share"] >= 0:
        raise ValueError("GPN: favorable bridge unexpectedly supports recovery")
    reason = "Recovery attempted; GPN remains withheld. Reported post-Worldpay H1 cash FCFF and even a favorable all-cash/no-NCI bridge stress remain negative after debt. A positive base would require an unsupported integration cash-flow uplift."
    release = "Revalue after a full comparable post-close period separates recurring corporate cash flow, integration cash costs, software/capex, settlement/customer funds and matched settlement-line borrowing."
    baseline = BaselineValuation(ticker="GPN", method="payments_operating_fcff", method_version=BATCH_38_RECOVERY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(reason, release))
    q2_operating_income = _period_flow(structural, ("OperatingIncomeLoss",), PERIOD, target_days=90)
    q2_depreciation_amortization = _period_flow(structural, ("DepreciationAndAmortization",), PERIOD, target_days=90)
    h1_capex = _period_flow(structural, ("PaymentsToAcquireProductiveAssets",), PERIOD, target_days=180)
    tax_source = initial["source_ledger"]["tax_rate_sources"][-1]
    tax_rate = tax_source["effective_tax_rate"]
    estimated_q2_capex = h1_capex["value"] / 2
    q2_cash_earnings = q2_operating_income["value"] * (1 - tax_rate) + q2_depreciation_amortization["value"] - estimated_q2_capex
    q2_annualized = q2_cash_earnings * 4
    q2_rows = []
    for index, row in enumerate(base_rows):
        starting = q2_annualized * ((.70, 1.0, 1.0)[index])
        state = EnterpriseCashFlowState(starting, row["growth"], row["terminal_growth"], row["wacc"], row["cash_and_investments"], row["debt_and_finance_leases"], 0.0, row["other_equity_claims"], row["shares"])
        trace = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
        q2_rows.append({"name": row["name"], "raw_value_per_share": trace["intrinsic_value_per_share"], "starting_cash_fcff": starting, "trace": trace})
    value.update({"model_version": BATCH_38_RECOVERY_VERSION, "warning": reason, "baseline": baseline.as_private_dict()})
    value["governed_assumptions"] = {**initial["governed_assumptions"], "reason_codes": ["POST_COMBINATION_HISTORY_INCOMPLETE", "NONPOSITIVE_BASE_VALUE", "VALUATION_WITHHELD"], "invalidation": release}
    value["source_ledger"] = {**initial["source_ledger"], "settlement_line_matching": {"settlement_line_of_credit": settlement_line, "total_balance_sheet_cash": total_cash, "treatment": "Settlement-line debt and settlement/customer cash are both excluded from the corporate bridge. Including the debt without its matched cash would only reduce value."}, "favorable_bridge_challenge": {"description": "Uses all reported balance-sheet cash and removes NCI claims while retaining reported long-term debt; still not a publishable state because customer/settlement cash is not issuer cash.", "scenario_rows": favorable, "base_still_negative": True}, "q2_cash_earnings_diagnostic": {"publication_allowed": False, "q2_operating_income": q2_operating_income, "q2_depreciation_and_amortization": q2_depreciation_amortization, "reported_h1_capex": h1_capex, "estimated_q2_capex": estimated_q2_capex, "tax_rate": tax_rate, "tax_source": tax_source, "q2_cash_earnings": q2_cash_earnings, "annualized_cash_earnings": q2_annualized, "scenario_rows": q2_rows, "formula": "Q2 operating income times (1-tax) plus Q2 D&A less estimated half-H1 capex; annualized times four", "why_rejected": "Quarterly capex is estimated, working-capital and settlement/customer-funding cash are omitted, and software/reinvestment is not separately reported. Positive base/bull values are therefore diagnostic, not publishable."}, "recovery_attempt": {"attempted": True, "initial_availability_type": "not_available", "final_availability_type": "not_available", "positive_base_gate_closed": False, "market_price_used": False, "analyst_target_used": False, "competitor_value_used": False}}
    return value


def build_batch_38_recovery_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path | None = None) -> dict[str, Any]:
    if ticker not in BATCH_38_TICKERS:
        raise ValueError(ticker)
    initial = build_batch_38_history_result(ticker=ticker, source_root=source_root, structural_root=structural_root, event_root=event_root, structural_cache_root=structural_cache_root)
    if ticker not in {"GPN", "CPAY"}:
        value = deepcopy(initial)
        value["model_version"] = BATCH_38_RECOVERY_VERSION
        value["baseline"] = {**value["baseline"], "method_version": BATCH_38_RECOVERY_VERSION}
        return value
    packet = Path(source_root) / ticker
    facts = json.loads((packet / "companyfacts.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    filing = initial["source_ledger"]["controlling_filing"]
    return _cpay_attempt(initial, facts, structural, filing) if ticker == "CPAY" else _gpn_attempt(initial, structural)


if RECOVERED_PASS_TICKERS | RECOVERED_CONDITIONAL_TICKERS | RECOVERED_WITHHELD_TICKERS != set(BATCH_38_TICKERS):
    raise RuntimeError("Batch 38 recovery classification mismatch")
