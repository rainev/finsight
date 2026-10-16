"""History-backed regulated and merchant utility baselines for Batch 47."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any

from app.valuation.bank import residual_income_valuation
from .baseline import AvailabilityType, BaselineValuation
from .batch_04_launch_first import _controlling
from .batch_35_history import _instant
from .batch_40_history import _latest_shares
from .batch_46_history import _annual_fact, _annual_instant, _combine, _structural_flow
from .batch_47 import BATCH_47_MANIFEST, BATCH_47_TICKERS, BATCH_47_VALUATION_DATE
from .batch_47_sources import verify_source_bundle
from .reliability import assess_reliability

BATCH_47_HISTORY_VERSION = "BATCH-47-REGULATED-MERCHANT-UTILITY-1.0"
PERIOD = "2026-06-30"
PASS_TICKERS = frozenset()
WITHHELD_TICKERS = frozenset({"NRG", "VST", "CEG"})
CONDITIONAL_TICKERS = frozenset(set(BATCH_47_TICKERS) - WITHHELD_TICKERS)
INCOME = {
    "NRG": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "ED": ("NetIncomeLoss",),
    "EXC": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "NI": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "CNP": ("NetIncomeLoss",),
    "DUK": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "AWK": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "VST": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "EVRG": ("NetIncomeLoss",),
    "CEG": ("NetIncomeLoss",),
}

WARNINGS = {
    "NRG": "Withheld: merchant generation and retail earnings, hedge/collateral cash, acquisitions, preferred claims and recourse/nonrecourse debt are not normalized into one source-bounded parent-common state.",
    "ED": "Conditional Low regulated-utility residual-income baseline. Electric, gas and steam scope, regulatory recovery, capital spending, commercial paper and subsidiary financing remain material.",
    "EXC": "Conditional Low regulated-utility residual-income baseline. Nuclear decommissioning trusts, fuel, financing trusts, environmental obligations, subsidiary allocation and rate recovery remain material.",
    "NI": "Conditional Low regulated gas/electric residual-income baseline. Seasonal gas activity, infrastructure capex, NCI, subsidiary funding, preferred redemption and rate recovery remain material.",
    "CNP": "Conditional Low regulated-utility residual-income baseline. Storm/recovery bonds, regulatory accounts, parent-versus-utility financing and July debt events remain material.",
    "DUK": "Conditional Low regulated-utility residual-income baseline. Nuclear fuel/decommissioning, project capex, preferred/NCI, recent financing and rate recovery remain material.",
    "AWK": "Conditional Low regulated water-utility residual-income baseline. Infrastructure replacement, acquisitions, water-quality compliance, rate cases, debt funding and redeemable preferred claims remain material.",
    "VST": "Withheld: merchant power prices, hedges, retail/generation scope, preferred claims, nuclear/coal/renewables cash and project financing are not source-bounded for a regulated-utility model.",
    "EVRG": "Conditional Low regulated-utility residual-income baseline. Nuclear/deferred fuel, coal transition, storm exposure, capital spending, NCI, financing and rate recovery remain material.",
    "CEG": "Withheld: merchant nuclear earnings, hedge and tax-credit effects, decommissioning trusts, PPAs, asset transactions, project debt and NCI are not normalized into one repeatable parent-common state.",
}
EVENT_TREATMENTS = {
    "NRG": "Earnings and July transaction/financing filings are retained as hard scope context; no acquisition, hedge or financing benefit is added as recurring earnings.",
    "ED": "Earnings and governance filings add no separate value; forward rate and capital plans remain context only.",
    "EXC": "The earnings filing is current operating context; nuclear and regulated investment plans are not capitalized as value.",
    "NI": "Earnings and August financing/regulatory filings are recorded; subsidiary funding and preferred redemption are not added twice.",
    "CNP": "July earnings and financing filings are recorded; recovery bonds and new debt are not treated as surplus parent cash.",
    "DUK": "Debt/prospectus and earnings filings are recorded; announced financing and nuclear/capex plans are not added independently to value.",
    "AWK": "Rate, acquisition and infrastructure filings are context only; projected capex and approval benefits are not added as assets.",
    "VST": "Merchant power, hedge and financing events remain a specialist-model gate; no regulated rate-base assumptions are used.",
    "EVRG": "Rate, capex, demand and financing events remain scenario context and are not capitalized as current value.",
    "CEG": "Nuclear/merchant, transaction and financing events remain a specialist-model gate; tax credits and decommissioning assets are not treated as free cash.",
}
RELEASE = {
    "NRG": "Revalue with normalized parent earnings/cash after acquisitions and hedges plus a complete preferred, collateral and recourse/nonrecourse debt bridge.",
    "VST": "Revalue with merchant generation/retail earnings and cash normalized for hedges, tax credits and project financing, including preferred/NCI claims.",
    "CEG": "Revalue with normalized merchant-nuclear parent earnings/cash, decommissioning trust obligations, PPAs, tax credits, project debt and NCI allocation.",
}
DIRECT_RESIDUAL_REASON = {
    "ED": "Residual income is preferred because electric/gas/steam capex and commercial-paper funding require subsidiary allocation.",
    "EXC": "Residual income keeps nuclear trust, financing-trust debt and regulated subsidiary capital inside common equity rather than an EV bridge.",
    "NI": "Residual income avoids treating seasonal gas working capital, NCI issuance and subsidiary funding as recurring parent FCFE.",
    "CNP": "Residual income avoids double-counting storm/recovery bonds and July financing across parent and utility cash flows.",
    "DUK": "Residual income avoids mixing nuclear-fuel, construction capex, preferred/NCI and recent offerings in a consolidated FCFE ratio.",
    "AWK": "Residual income is used because water-system acquisitions and compliance capex are not interchangeable with ordinary electric-utility reinvestment.",
    "EVRG": "Residual income avoids mixing nuclear/deferred-fuel, coal retirement and commercial-paper flows into a generic FCFE ratio.",
}


def _maybe(structural: dict[str, Any], names: tuple[str, ...], period: str) -> dict[str, Any] | None:
    try:
        return _instant(structural, names, period)
    except ValueError:
        return None


def _annual_common_equity(ticker: str, facts: dict[str, Any], year: int) -> dict[str, Any]:
    if ticker == "NRG":
        total = _annual_instant(facts, ticker, ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",), year)
        preferred = _annual_instant(facts, ticker, ("PreferredStockValue", "PreferredStockLiquidationPreferenceValue"), year)
        return _combine("total_equity-preferred", [(total, 1), (preferred, -1)])
    parent = _annual_instant(facts, ticker, ("StockholdersEquity",), year)
    if ticker == "VST":
        preferred = _annual_instant(facts, ticker, ("PreferredStockValue",), year)
        return _combine("stockholders_equity-preferred", [(parent, 1), (preferred, -1)])
    return parent


def _equity(structural: dict[str, Any], ticker: str, period: str) -> dict[str, Any]:
    preferred = _maybe(structural, ("PreferredStockValue", "PreferredStockLiquidationPreferenceValue", "PreferredStockValueOutstanding"), period)
    nci = _maybe(structural, ("MinorityInterest", "OtherMinorityInterests"), period)
    temporary = _maybe(structural, ("PreferredStockRedemptionAmount", "TemporaryEquityCarryingAmount"), period) if ticker == "AWK" else None
    if ticker == "NRG":
        total = _instant(structural, ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",), period)
        parent = _combine("total_equity-preferred", [(total, 1), (preferred, -1)])
    elif ticker == "VST":
        parent_total = _instant(structural, ("StockholdersEquity",), period)
        parent = _combine("stockholders_equity-preferred", [(parent_total, 1), (preferred, -1)])
        total = _instant(structural, ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",), period)
    else:
        parent = _instant(structural, ("StockholdersEquity",), period)
        total = _maybe(structural, ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",), period) or parent
    denominator = total["value"] + (temporary["value"] if temporary and ticker == "AWK" else 0.0)
    share = parent["value"] / denominator
    if not 0 < share <= 1:
        raise ValueError(f"{ticker}: parent equity share invalid")
    return {"parent_common_equity": parent, "total_equity": total, "preferred_equity": preferred, "noncontrolling_interest": nci, "temporary_or_redeemable_equity": temporary, "parent_equity_share": share}


def _events(ticker: str, root: Path, source_hash: str) -> dict[str, Any]:
    path = root / ticker / "inventory.json"
    rows = json.loads(path.read_text())
    if not rows or any(row.get("filed", "") > BATCH_47_VALUATION_DATE for row in rows):
        raise ValueError(f"{ticker}: invalid event inventory")
    documents = []
    for row in rows:
        for document in row.get("documents", []):
            p = Path(document["path"])
            if not p.is_absolute():
                p = root.parent.parent / p
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != document["sha256"]:
                raise ValueError(f"{ticker}: event hash mismatch")
            documents.append(document)
    return {"source_kind": "sec_event_screening", "screened_filings": rows, "documents": documents, "inventory_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "source_manifest_sha256": source_hash, "treatment": EVENT_TREATMENTS[ticker], "reported_vs_estimated": "reported_and_screened"}


def _history(ticker: str, facts: dict[str, Any], structural: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    annual = []
    for year in (2024, 2025):
        income = _annual_fact(facts, ticker, INCOME[ticker], year)
        equity = _annual_common_equity(ticker, facts, year)
        annual.append({"period_end": f"{year}-12-31", "common_net_income": income, "common_equity": equity, "roe_on_ending_equity": income["value"] / equity["value"]})
    current = _structural_flow(structural, INCOME[ticker], "2026-01-01", PERIOD)
    prior = _structural_flow(structural, INCOME[ticker], "2025-01-01", "2025-06-30")
    ttm_income = _combine("FY2025+H1_2026-H1_2025", [(annual[-1]["common_net_income"], 1), (current, 1), (prior, -1)])
    ttm_income["period_end"] = PERIOD
    beginning = _equity(structural, ticker, "2025-12-31")["parent_common_equity"]
    ending = _equity(structural, ticker, PERIOD)["parent_common_equity"]
    ttm_roe = ttm_income["value"] / ((beginning["value"] + ending["value"]) / 2)
    return annual, {"period_end": PERIOD, "common_net_income": ttm_income, "beginning_common_equity": beginning, "ending_common_equity": ending, "roe_on_average_equity": ttm_roe}


def _residual(ticker: str, *, filing, annual, current, equity, shares, event, verification, structural) -> dict[str, Any]:
    observed = tuple(row["roe_on_ending_equity"] for row in annual) + (current["roe_on_average_equity"],)
    roe = median(observed)
    end = current["ending_common_equity"]["value"]
    coe = (0.095, 0.085, 0.075)
    terminal_roe = min(0.105, max(0.075, roe))
    rows, traces = [], {}
    for name, cost in zip(("bear", "base", "bull"), coe):
        trace = residual_income_valuation(book_value_per_share=end / shares["value"], current_roe=roe, cost_of_equity=cost, current_payout_ratio=0.65, terminal_roe=terminal_roe, terminal_growth=0.02, years=5)
        rows.append({"name": name, "raw_value_per_share": trace["intrinsic_value"], "conditional_value_per_share": trace["intrinsic_value"], "book_value_per_share": end / shares["value"], "current_roe": roe, "cost_of_equity": cost, "current_payout_ratio": 0.65, "terminal_roe": terminal_roe, "terminal_growth": 0.02, "shares": shares["value"]})
        traces[name] = trace
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid residual range")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("CONSOLIDATED_MIXED_UTILITY_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"))
    invalidation = "Revalue if parent common earnings/equity, normalized ROE, rate recovery, claims, preferred/NCI, shares, financing or cutoff events leave the recorded range."
    baseline = BaselineValuation(ticker=ticker, method="regulated_utility_residual_income", method_version=BATCH_47_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(WARNINGS[ticker], invalidation))
    assumptions = {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 3, "forecast_years": 5, "normalization_basis": "median FY2024, FY2025 and current-TTM parent-common ROE", "assumption_source_mix": "reported common equity/earnings and governed cost-of-equity range", "observed_common_roe": observed, "current_roe": (roe,) * 3, "current_payout_ratio": (0.65,) * 3, "cost_of_equity": coe, "terminal_roe": (terminal_roe,) * 3, "terminal_growth": (0.02,) * 3, "shares": (shares["value"],) * 3, "scenario_calibration": "cost_of_equity_only; source/history-normalized ROE and other inputs fixed", "route_is_equity_level": True, "ev_debt_bridge_applied": False, "equity_floor_basis": "not applied", "calculator_calibration": "Exact residual-income assumptions replay through the public calculator.", "invalidation": invalidation}
    return {"ticker": ticker, "method": "regulated_utility_residual_income", "model_version": BATCH_47_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_common_earnings": current["common_net_income"]["value"], "beginning_common_equity": current["beginning_common_equity"]["value"], "ending_common_equity": end, "share_count": shares["value"]}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "annual_common_equity_history": annual, "ttm_common_equity_state": current, "equity_allocation": equity, "share_source": shares, "event_sources": event, "residual_income_trace": {"states": traces}, "fcfe_route_not_selected": {"reason": DIRECT_RESIDUAL_REASON[ticker], "missing_values_zero_imputed": False}, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS[ticker], "baseline": baseline.as_private_dict()}


def _withheld(ticker: str, *, filing, annual, current, equity, shares, event, verification, structural) -> dict[str, Any]:
    method = "merchant_energy_parent_equity_residual_income" if ticker in {"NRG", "VST"} else "merchant_nuclear_parent_equity_residual_income"
    baseline = BaselineValuation(ticker=ticker, method=method, method_version=BATCH_47_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(WARNINGS[ticker], RELEASE[ticker]))
    return {"ticker": ticker, "method": method, "model_version": BATCH_47_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {"ttm_common_earnings_diagnostic": current["common_net_income"]["value"], "ending_common_equity_diagnostic": current["ending_common_equity"]["value"], "share_count": shares["value"]}, "governed_assumptions": {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 3, "forecast_years": 5, "normalization_basis": "merchant/nuclear specialist normalization gate; common history retained as diagnostic only", "assumption_source_mix": "reported history with unresolved merchant normalization", "equity_floor_basis": "not applied", "availability_separate_from_model_identity": True, "invalidation": RELEASE[ticker]}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "annual_common_equity_history": annual, "ttm_common_equity_state": current, "equity_allocation": equity, "share_source": shares, "event_sources": event, "specialist_gate": {"passed": False, "reason": WARNINGS[ticker], "release_condition": RELEASE[ticker]}, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS[ticker], "baseline": baseline.as_private_dict()}


def build_batch_47_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_47_TICKERS:
        raise ValueError(ticker)
    packet, structural_packet = Path(source_root) / ticker, Path(structural_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((structural_packet / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural.get("source_accession") != filing["accession"] or structural.get("report_date") != PERIOD:
        raise ValueError(f"{ticker}: controlling mismatch")
    verification = verify_source_bundle(ticker=ticker, packet=packet, structural_packet=structural_packet, structural_cache_root=Path(structural_cache_root), filing=filing)
    annual, current = _history(ticker, facts, structural)
    equity, shares = _equity(structural, ticker, PERIOD), _latest_shares(ticker, structural)
    event = _events(ticker, Path(event_root), verification["source_manifest_sha256"])
    if ticker in WITHHELD_TICKERS:
        return _withheld(ticker, filing=filing, annual=annual, current=current, equity=equity, shares=shares, event=event, verification=verification, structural=structural)
    return _residual(ticker, filing=filing, annual=annual, current=current, equity=equity, shares=shares, event=event, verification=verification, structural=structural)


if PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_47_TICKERS):
    raise RuntimeError("Batch 47 classification mismatch")
