"""History-backed practical baselines for controlled Universe Reset Batch 39."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from app.valuation.bank import residual_income_valuation

from .baseline import AvailabilityType, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling
from .batch_08_history import _annual_cash_with_losses
from .batch_35_history import _instant, _period_flow, _rows, _source
from .batch_39 import BATCH_39_MANIFEST, BATCH_39_TICKERS, BATCH_39_VALUATION_DATE
from .batch_39_sources import _verify_source_bundle
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, build_cash_fcff_history_profile, summarize_history_metric
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_39_HISTORY_VERSION = "BATCH-39-HISTORY-1.0"
PERIOD = "2026-06-30"
FINANCIAL_TICKERS = frozenset({"ARES", "RF", "IBKR", "BNY", "BX", "KKR"})
OPERATING_TICKERS = frozenset({"CBOE", "V", "TRGP", "KMI"})
PASS_TICKERS = frozenset()
CONDITIONAL_TICKERS = frozenset(set(BATCH_39_TICKERS) - PASS_TICKERS)
WITHHELD_TICKERS = frozenset()


EARNINGS: dict[str, tuple[str, ...]] = {
    "ARES": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "RF": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "IBKR": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "BNY": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "BX": ("NetIncomeLoss",),
    "KKR": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
}


POLICY: dict[str, dict[str, Any]] = {
    "ARES": {"method": "alternative_asset_manager_residual_income_equity_earnings", "roe": (.06, .10, .14), "payout": (.25, .35, .45), "coe": (.11, .095, .085), "warning": "Conditional Low alternative-manager residual-income baseline. Fund assets, AUM, available capital, partnership NCI and consolidated funds are not parent cash; performance fees, carried interest and mandatory preferred conversion remain cyclical."},
    "RF": {"method": "regional_bank_residual_income_equity_earnings", "roe": (.06, .09, .12), "payout": (.25, .35, .45), "coe": (.115, .10, .09), "warning": "Conditional Low regional-bank residual-income baseline. Deposits, securities, credit costs, AOCI, preferred claims and regulatory capital remain inside bank equity economics; no EV debt bridge is used."},
    "IBKR": {"method": "broker_dealer_residual_income_equity_earnings", "roe": (.08, .12, .16), "payout": (.15, .25, .35), "coe": (.11, .095, .085), "warning": "Conditional Low broker-dealer residual-income baseline. Client reserve cash and securities-financing balances are not issuer cash; the holding-company NCI structure and registered share dilution remain material."},
    "BNY": {"method": "custody_bank_residual_income_equity_earnings", "roe": (.08, .12, .16), "payout": (.20, .30, .40), "coe": (.105, .095, .085), "warning": "Conditional Low custody-bank residual-income baseline. Deposits, custody assets, repo, securities-lending collateral and central-bank balances stay inside equity economics. The July Series N preferred issue is bridged once with a governed dividend drag."},
    "BX": {"method": "alternative_asset_manager_residual_income_equity_earnings", "roe": (.08, .12, .16), "payout": (.25, .35, .45), "coe": (.11, .095, .085), "warning": "Conditional Low alternative-manager residual-income baseline. Consolidated fund assets and partnership NCI are not parent cash; performance revenues, tax-receivable obligations and realization cycles remain material."},
    "KKR": {"method": "alternative_asset_manager_insurance_residual_income_equity_earnings", "roe": (.06, .09, .12), "payout": (.20, .30, .40), "coe": (.11, .095, .085), "warning": "Conditional Low alternative-manager/insurance residual-income baseline. Fund, Global Atlantic and CLO financing remain inside parent equity economics; preferred claims, share scope, FRE and carry cycles remain material."},
}


EVENT_TREATMENTS = {
    "ARES": "July earnings and AUM materials corroborate current operations; client AUM is not issuer cash and no separate proceeds overlay is used.",
    "RF": "July/August earnings and capital materials corroborate the 10-Q; the completed Frazer Lanier acquisition stays in current earnings and equity, while management changes are qualitative.",
    "CBOE": "The July credit agreement is capacity, not drawn debt; pending Cboe Australia/Canada disposals remain invalidation events and no sale proceeds are assumed.",
    "IBKR": "July earnings corroborate current results; up to 920,000 promotion shares and 2,499,567 registered shares are bounded as potential dilution, not assumed proceeds.",
    "TRGP": "The receivables amendment and earnings release are current financing/operating context; growth projects and Stakeholder acquisition remain inside the broad reinvestment scenarios.",
    "BNY": "The July Series N preferred issue and August note issues are cutoff events; preferred proceeds/claim are bridged once and debt remains inside the bank equity model.",
    "BX": "The July earnings release corroborates current parent/fund performance; no AUM, realization, or fund-asset amount is treated as parent cash.",
    "V": "The July earnings release confirms the current litigation charge and dividend; customer collateral stays matched and no future legal recovery is assumed.",
    "KKR": "The July earnings release and subordinated-note agreement are context; fund/insurance financing remains inside equity economics and no proceeds overlay is added.",
    "KMI": "The July $1.75B senior-note issue is treated as refinancing with net debt unchanged; no new-project value is added before cash flow is reported.",
}


def _event_sources(ticker: str, event_root: Path, source_manifest_sha256: str) -> dict[str, Any]:
    inventory_path = Path(event_root) / ticker / "inventory.json"
    entries = json.loads(inventory_path.read_text())
    if not entries or any(row.get("filed", "") > BATCH_39_VALUATION_DATE for row in entries):
        raise ValueError(f"{ticker}: invalid event inventory")
    documents = []
    for row in entries:
        for document in row.get("documents", []):
            path = Path(document["path"])
            if not path.is_absolute():
                path = Path(event_root).parent.parent / path
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != document.get("sha256"):
                raise ValueError(f"{ticker}: event document hash mismatch")
            documents.append(document)
    return {"source_kind": "sec_event_screening", "decision": "accepted_context", "screened_filings": entries, "documents": documents, "inventory_sha256": hashlib.sha256(inventory_path.read_bytes()).hexdigest(), "source_manifest_sha256": source_manifest_sha256, "treatment": EVENT_TREATMENTS[ticker], "reported_vs_estimated": "reported_and_screened"}


def _annual_common(facts: dict[str, Any], ticker: str) -> tuple[dict[str, Any], ...]:
    selected: dict[str, tuple[dict[str, Any], str]] = {}
    for concept in EARNINGS[ticker]:
        for row in _rows(facts, concept):
            if row.get("form") not in {"10-K", "10-K/A"} or row.get("filed", "") > BATCH_39_VALUATION_DATE or not row.get("start") or not row.get("end") or not isinstance(row.get("val"), (int, float)):
                continue
            try:
                span = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
            except (TypeError, ValueError):
                continue
            if not 300 <= span <= 380:
                continue
            old = selected.get(row["end"])
            if old is None or (row.get("filed", ""), row.get("accn", "")) > (old[0].get("filed", ""), old[0].get("accn", "")):
                selected[row["end"]] = (row, concept)
    ends = [end for end in sorted(selected) if end >= "2020-01-01"][-5:]
    if len(ends) != 5:
        raise ValueError(f"{ticker}: five annual common-earnings periods required")
    values = []
    for end in ends:
        row, concept = selected[end]
        value = float(row["val"])
        sources = [_source(row, concept)]
        if ticker == "BX":
            adjustments = [item for item in _rows(facts, "NetIncomeLossAttributableToRedeemableNoncontrollingInterest") if item.get("start") == row.get("start") and item.get("end") == end and item.get("form") in {"10-K", "10-K/A"} and item.get("filed", "") <= BATCH_39_VALUATION_DATE and isinstance(item.get("val"), (int, float))]
            if not adjustments:
                raise ValueError("BX: redeemable-NCI annual earnings absent")
            adjustment = max(adjustments, key=lambda item: (item.get("filed", ""), item.get("accn", "")))
            value -= float(adjustment["val"])
            sources.append(_source(adjustment, "NetIncomeLossAttributableToRedeemableNoncontrollingInterest"))
        values.append({"period_end": end, "value": value, "sources": sources, "formula": "reported common earnings" if ticker != "BX" else "parent NetIncomeLoss less redeemable-NCI earnings"})
    return tuple(values)


def _dimensional_source(structural: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {"source_kind": "structural_xbrl", "accession": structural.get("source_accession"), "filed": structural.get("filed_date"), "form": structural.get("form"), "period_start": row.get("period_start"), "period_end": row.get("period_end"), "concept": row.get("qname"), "unit": row.get("unit"), "value": float(row["value"]), "dimensions": row.get("dimensions"), "reported_vs_estimated": "reported"}


def _preferred(ticker: str, structural: dict[str, Any], period: str) -> tuple[float, str, list[dict[str, Any]]]:
    if ticker in {"ARES", "KKR"}:
        rows = [row for row in structural.get("facts", []) if row.get("local_name") == "PreferredStockValue" and row.get("period_start") is None and row.get("period_end") == period and row.get("unit") == "USD" and isinstance(row.get("value"), (int, float)) and float(row["value"]) > 0]
        if not rows:
            raise ValueError(f"{ticker}: preferred claim absent")
        value = max(float(row["value"]) for row in rows)
        source = next(row for row in rows if float(row["value"]) == value)
        return value, "reported_dimensional_preferred_claim", [_dimensional_source(structural, source)]
    for name in ("PreferredStockLiquidationPreferenceValue", "PreferredStockValueOutstanding", "PreferredStockCarryingValue", "PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount", "PreferredStockValue"):
        try:
            source = _instant(structural, (name,), period)
        except ValueError:
            continue
        return float(source["value"]), "reported_preferred_claim" if source["value"] > 0 else "reported_preferred_absence", [source]
    issued = [row for row in structural.get("facts", []) if row.get("local_name") == "PreferredStockSharesIssued" and row.get("period_start") is None and row.get("period_end") == period and row.get("unit") == "xbrli:shares" and isinstance(row.get("value"), (int, float))]
    if issued and all(float(row["value"]) == 0 for row in issued):
        return 0.0, "reported_preferred_absence", [_dimensional_source(structural, row) for row in issued]
    if ticker == "BX":
        return 0.0, "statement_proven_nominal_voting_preferred_only", [{"source_kind": "statement_scope_check", "accession": structural.get("source_accession"), "period_end": period, "treatment": "Series I/II each have one voting share and zero reported economic value; no economic preferred claim is deducted.", "reported_vs_estimated": "source_bounded_absence_check"}]
    if ticker == "IBKR":
        return 0.0, "statement_proven_preferred_absence", [{"source_kind": "statement_scope_check", "accession": structural.get("source_accession"), "period_end": period, "treatment": "The filing authorizes preferred shares but reports none issued or outstanding and no preferred dividend; no economic preferred claim is deducted.", "reported_vs_estimated": "source_bounded_absence_check"}]
    raise ValueError(f"{ticker}: preferred claim unresolved")


def _latest_shares(ticker: str, structural: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in structural.get("facts", []) if row.get("local_name") == "EntityCommonStockSharesOutstanding" and row.get("period_start") is None and row.get("unit") == "xbrli:shares" and PERIOD <= str(row.get("period_end", "")) <= BATCH_39_VALUATION_DATE and isinstance(row.get("value"), (int, float))]
    if rows:
        latest = max(str(row["period_end"]) for row in rows)
        current = [row for row in rows if row["period_end"] == latest]
        if ticker == "ARES":
            economic = [row for row in current if any(member.endswith("CommonClassAMember") or member.endswith("NonvotingCommonStockMember") for _, member in row.get("dimensions", []))]
            if len(economic) != 2:
                raise ValueError("ARES: economic common classes unresolved")
            return {"source_kind": "derived_current_economic_common_share_count", "accession": structural.get("source_accession"), "period_end": latest, "unit": "xbrli:shares", "value": sum(float(row["value"]) for row in economic), "formula": "Class A plus non-voting common; Class B/C are non-economic and excluded", "sources": [_dimensional_source(structural, row) for row in economic], "reported_vs_estimated": "reported_components"}
        nondimensional = [row for row in current if not row.get("dimensions")]
        if nondimensional:
            return {**_dimensional_source(structural, nondimensional[-1]), "source_kind": "structural_dei_current_share_count"}
        unique: dict[tuple[tuple[str, str], ...], dict[str, Any]] = {}
        for row in current:
            dimensions = tuple(tuple(item) for item in row.get("dimensions", []))
            if any("StatementClassOfStockAxis" in axis for axis, _ in dimensions) and not any("Preferred" in member for _, member in dimensions):
                unique[dimensions] = row
        if unique:
            return {"source_kind": "derived_current_class_share_count", "accession": structural.get("source_accession"), "period_end": latest, "unit": "xbrli:shares", "value": sum(float(row["value"]) for row in unique.values()), "formula": "sum current DEI common classes", "sources": [_dimensional_source(structural, row) for row in unique.values()], "reported_vs_estimated": "reported_components"}
    names = ("CommonStockSharesOutstanding",)
    source = _instant(structural, names, PERIOD, unit="xbrli:shares")
    return source


def _financial_result(ticker: str, facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    annual = _annual_common(facts, ticker)
    current = _period_flow(structural, EARNINGS[ticker], PERIOD, target_days=180)
    prior = _period_flow(structural, EARNINGS[ticker], "2025-06-30", target_days=180)
    if ticker == "BX":
        current_rnci = _period_flow(structural, ("NetIncomeLossAttributableToRedeemableNoncontrollingInterest",), PERIOD, target_days=180)
        prior_rnci = _period_flow(structural, ("NetIncomeLossAttributableToRedeemableNoncontrollingInterest",), "2025-06-30", target_days=180)
        current = {**current, "value": current["value"] - current_rnci["value"], "formula": "parent NetIncomeLoss less redeemable-NCI earnings", "components": [current, current_rnci]}
        prior = {**prior, "value": prior["value"] - prior_rnci["value"], "formula": "parent NetIncomeLoss less redeemable-NCI earnings", "components": [prior, prior_rnci]}
    ttm = annual[-1]["value"] + current["value"] - prior["value"]
    equity = _instant(structural, ("StockholdersEquity",), PERIOD)
    opening_equity = _instant(structural, ("StockholdersEquity",), "2025-12-31")
    preferred, preferred_status, preferred_sources = _preferred(ticker, structural, PERIOD)
    prior_preferred, prior_status, prior_sources = _preferred(ticker, structural, "2025-12-31")
    share = _latest_shares(ticker, structural)
    event_claim = 500_000_000.0 if ticker == "BNY" else 0.0
    post_event_equity = equity["value"] + event_claim
    common_equity = post_event_equity - preferred - event_claim
    opening_common = opening_equity["value"] - prior_preferred
    if min(ttm, common_equity, opening_common, share["value"]) <= 0:
        raise ValueError(f"{ticker}: nonpositive parent/common input")
    observations = [HistoryObservation("annual", row["period_end"], int(row["period_end"][:4]), row["value"], "USD", row["formula"], tuple(row["sources"])) for row in annual]
    observations.append(HistoryObservation("operating_ttm", PERIOD, None, ttm, "USD", "latest FY plus current H1 less prior H1", tuple(annual[-1]["sources"] + [current, prior])))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    if metric is None:
        raise ValueError(f"{ticker}: earnings history unavailable")
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "financial_equity_residual_income", BATCH_39_VALUATION_DATE, tuple(row["period_end"] for row in annual), (metric,), True, "reported_and_company_history")
    history_high = max(metric.high, ttm) / common_equity
    roes = tuple(min(value, history_high) for value in POLICY[ticker]["roe"])
    if not 0 < roes[0] <= roes[1] <= roes[2] or roes[0] == roes[2]:
        roes = (max(.02, history_high * .5), max(.025, history_high * .75), history_high)
    share_value = float(share["value"])
    if ticker == "IBKR":
        shares = (share_value + 3_419_567.0, share_value + 920_000.0, share_value)
    else:
        shares = (share_value * 1.015, share_value, share_value * .985)
    policy = POLICY[ticker]
    bny_preferred_drag = (40_000_000.0, 30_000_000.0, 25_000_000.0) if ticker == "BNY" else (0.0, 0.0, 0.0)
    if ticker == "BNY":
        fixed_note_interest = 1_200_000_000.0 * .04755 + 1_000_000_000.0 * .05182
        floating_note_interest = (300_000_000.0 * .065, 300_000_000.0 * .055, 300_000_000.0 * .045)
        gross_note_interest = tuple(fixed_note_interest + value for value in floating_note_interest)
        after_tax_note_interest = tuple(value * .79 for value in gross_note_interest)
        note_interest_drag = (after_tax_note_interest[0], after_tax_note_interest[1] * .5, 0.0)
    else:
        fixed_note_interest = 0.0
        floating_note_interest = gross_note_interest = after_tax_note_interest = note_interest_drag = (0.0, 0.0, 0.0)
    total_event_drag = tuple(preferred + interest for preferred, interest in zip(bny_preferred_drag, note_interest_drag))
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        roe = max(.01, roes[index] - total_event_drag[index] / common_equity)
        trace = residual_income_valuation(book_value_per_share=common_equity / shares[index], current_roe=roe, cost_of_equity=policy["coe"][index], current_payout_ratio=policy["payout"][index], terminal_roe=(.085, .105, .115)[index], terminal_growth=(.01, .02, .025)[index], years=5)
        raw = float(trace["intrinsic_value"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": raw, "book_value_per_share": common_equity / shares[index], "current_roe": roe, "current_payout_ratio": policy["payout"][index], "cost_of_equity": policy["coe"][index], "terminal_roe": (.085, .105, .115)[index], "terminal_growth": (.01, .02, .025)[index], "shares": shares[index], "preferred_claim": preferred + event_claim, "ending_common_equity": common_equity, "event_forward_common_earnings_drag": total_event_drag[index], "limited_liability_floor_applied": False})
        traces[name] = trace
    scenario = {"low": rows[0]["raw_value_per_share"], "base": rows[1]["raw_value_per_share"], "high": rows[2]["raw_value_per_share"]}
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid residual-income range")
    reasons = ("SPECIALIST_MODEL_UNCERTAINTY", "PROVISIONAL_BANK_CAPITAL_RANGE") if ticker in {"RF", "BNY"} else ("SPECIALIST_MODEL_UNCERTAINTY",)
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    warning = policy["warning"]
    if ticker == "ARES":
        warning += " The denominator includes only Class A and economically identical non-voting shares; non-economic Class B/C are excluded. Series B remains a current preferred claim, while its October 2027 mandatory conversion at 0.2717–0.3260 Class A shares per preferred share is an explicit future invalidation event rather than double-counted dilution."
    if ticker == "BNY":
        warning += " Series N adds $500M of proceeds and preferred claim once, leaving common book equity unchanged; its uncaptured exact coupon is bounded by $25M–$40M annual common-earnings drag. The August $2.5B note issue applies fixed coupons plus a 4.5%–6.5% floating-note range, with 0%/50%/100% proceeds-income offset across bear/base/bull."
    invalidation = "Revalue if parent/common earnings, equity, preferred/NCI claims, shares, capital, performance cycles, credit losses, or cutoff events leave the bounded range."
    assumptions = {**profile.public_metadata(), "forecast_years": 5, "normalization_basis": "reported_parent_common_equity_with_history_bounded_roe", "assumption_source_mix": "reported_equity_earnings_history_and_governed_scenarios", "equity_floor_basis": "not applied", "earnings_multiples": tuple(row["raw_value_per_share"] * row["shares"] / ttm for row in rows), "current_roe": tuple(row["current_roe"] for row in rows), "current_payout_ratio": policy["payout"], "cost_of_equity": policy["coe"], "terminal_roe": (.085, .105, .115), "terminal_growth": (.01, .02, .025), "shares": shares, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "preferred_claim_status": preferred_status, "event_preferred_claim_and_proceeds": event_claim, "event_debt_principal": 2_500_000_000.0 if ticker == "BNY" else 0.0, "event_forward_common_earnings_drag": total_event_drag, "calculator_calibration": "Exact residual-income default replay.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker=ticker, method=policy["method"], method_version=BATCH_39_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(warning, invalidation))
    return {"ticker": ticker, "method": policy["method"], "model_version": BATCH_39_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_common_earnings": ttm, "beginning_total_equity": opening_equity["value"], "ending_total_equity": equity["value"], "post_event_total_equity": post_event_equity, "beginning_preferred_claim": prior_preferred, "preferred_claim": preferred + event_claim, "beginning_common_equity": opening_common, "ending_common_equity": common_equity, "share_count": share_value}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "common_earnings_reconstruction": {"annual_history": list(annual), "latest_fy": annual[-1], "current_ytd": current, "prior_ytd": prior, "ttm": ttm, "formula": "latest FY + current H1 - prior H1"}, "company_history_profile": profile.as_private_dict(), "equity_model_context": {"ending_parent_equity": equity, "opening_parent_equity": opening_equity, "preferred_status": preferred_status, "prior_preferred_status": prior_status, "preferred_sources": preferred_sources, "prior_preferred_sources": prior_sources, "current_share_count": share, "event_preferred_claim_and_proceeds": event_claim, "ares_mandatory_conversion": {"preferred_shares": 30_000_000.0, "minimum_conversion_rate": .2717, "maximum_conversion_rate": .3260, "minimum_future_class_a_shares": 8_151_000.0, "maximum_future_class_a_shares": 9_780_000.0, "mandatory_conversion_date": "2027-10-01", "current_model_treatment": "Series B remains a preferred claim; future conversion shares are not added simultaneously.", "source": filing} if ticker == "ARES" else None}, "bny_note_event": {"accession": "0001193125-26-347061" if ticker == "BNY" else None, "principal": 2_500_000_000.0 if ticker == "BNY" else 0.0, "fixed_note_interest": fixed_note_interest, "floating_note_interest_range": floating_note_interest, "gross_interest_range": gross_note_interest, "after_tax_interest_range": after_tax_note_interest, "proceeds_income_offset": (0.0, .5, 1.0) if ticker == "BNY" else (0.0, 0.0, 0.0), "note_interest_drag": note_interest_drag}, "event_sources": event, "bridge_treatment": "Parent/common-equity model: client, fund, deposit, insurance, repo, clearing and securities-financing balances remain inside equity economics; no EV debt bridge and no NCI double subtraction.", "residual_income_trace": {"states": traces}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def _visa_flows(submissions: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any]) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], float, list[dict[str, Any]]]:
    normalizer = _normalizer(submissions, facts)
    tax, tax_sources = _normalized_tax_rate(normalizer)
    annual = tuple(_annual_cash_with_losses(normalizer)[2])
    latest = {field: normalizer.annual_at_end(field, "2025-09-30") for field in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    if any(value is None for value in latest.values()):
        raise ValueError("V: FY2025 flow absent")
    current_names = {"revenue": "RevenueFromContractWithCustomerExcludingAssessedTax", "operating_cash_flow": "NetCashProvidedByUsedInOperatingActivities", "capital_expenditures": "PaymentsToAcquireProductiveAssets", "interest_expense": "InterestExpenseNonoperating"}
    current = {field: _period_flow(structural, (name,), PERIOD, target_days=270) for field, name in current_names.items()}
    prior = {field: _period_flow(structural, (name,), "2025-06-30", target_days=270) for field, name in current_names.items()}
    values = {field: latest[field].value + current[field]["value"] - prior[field]["value"] for field in current_names}
    fcff = cash_fcff_from_reported(operating_cash_flow=values["operating_cash_flow"], capital_expenditures=values["capital_expenditures"], spectrum_investment=0.0, interest_expense=abs(values["interest_expense"]), tax_rate=tax)
    ledger = {"method": "FY2025 + current nine months - prior nine months", "latest_fy": {field: latest[field].as_dict() for field in latest}, "current_nine_months": current, "prior_nine_months": prior, "values": values, "period_end": PERIOD, "cash_fcff": fcff}
    return ledger, annual, tax, list(tax_sources)


def _operating_result(ticker: str, submissions: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    normalizer = _normalizer(submissions, facts)
    tax, tax_sources = _normalized_tax_rate(normalizer)
    if ticker == "V":
        reconstruction, annual, tax, tax_sources = _visa_flows(submissions, facts, structural)
        revenue = reconstruction["values"]["revenue"]
        fcff = reconstruction["cash_fcff"]
        flow_sources = reconstruction
        ttm_sources = [source for group in (reconstruction["latest_fy"], reconstruction["current_nine_months"], reconstruction["prior_nine_months"]) for value in group.values() for source in ([value] if isinstance(value, dict) else [])]
    else:
        flows = {field: normalizer.ttm_flow(field) for field in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
        if any(value["period_end"] != PERIOD for value in flows.values()):
            raise ValueError(f"{ticker}: stale TTM flow")
        revenue = flows["revenue"]["value"]
        fcff = cash_fcff_from_reported(operating_cash_flow=flows["operating_cash_flow"]["value"], capital_expenditures=flows["capital_expenditures"]["value"], spectrum_investment=0.0, interest_expense=abs(flows["interest_expense"]["value"]), tax_rate=tax)
        annual = tuple(_annual_cash_with_losses(normalizer)[2])
        flow_sources = flows
        ttm_sources = [source for value in flows.values() for source in value["sources"]]
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=revenue, ttm_cash_fcff=fcff, ttm_period_end=PERIOD, ttm_sources=ttm_sources, valuation_date=BATCH_39_VALUATION_DATE)
    metric = profile.metric("cash_conversion_margin")
    if metric is None:
        raise ValueError(f"{ticker}: no cash-conversion history")
    starting = [revenue * value for value in (metric.low, metric.base, metric.high)]
    special_reinvestment = None
    if ticker == "TRGP":
        reported_ocf_h1 = flows["operating_cash_flow"]["current_ytd"]["value"]
        reported_interest_h1 = abs(flows["interest_expense"]["current_ytd"]["value"])
        after_tax_interest_h1 = reported_interest_h1 * (1 - tax)
        maintenance_h1 = 90_000_000.0
        growth_h1 = 2_027_700_000.0
        starting = [2 * (reported_ocf_h1 + after_tax_interest_h1 - maintenance_h1 - growth_h1), 2 * (reported_ocf_h1 + after_tax_interest_h1 - maintenance_h1 - .50 * growth_h1), 2 * (reported_ocf_h1 + after_tax_interest_h1 - maintenance_h1 - .25 * growth_h1)]
        special_reinvestment = {"source_kind": "controlling_cash_flow_and_cutoff_event_earnings_release", "accession": "0001193125-26-336525", "filed": "2026-08-06", "reported_operating_cash_flow_h1": reported_ocf_h1, "reported_cash_interest_h1": reported_interest_h1, "normalized_tax_rate": tax, "after_tax_interest_h1": after_tax_interest_h1, "reported_maintenance_capex_h1": maintenance_h1, "reported_growth_capex_h1": growth_h1, "governed_growth_capex_retention": (1.0, .50, .25), "starting_cash_fcff": tuple(starting), "formula": "2 x (reported OCF + after-tax interest - maintenance capex - scenario share of growth capex)", "reported_vs_estimated": "reported cash amounts with governed growth-capex normalization range"}
    if ticker == "CBOE":
        cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), PERIOD)["value"]
        debt = _instant(structural, ("LongTermDebtCurrent",), PERIOD)["value"] + _instant(structural, ("LongTermDebtNoncurrent",), PERIOD)["value"]
        claims = 0.0
        share = _latest_shares(ticker, structural)
        clearing_cash = _instant(structural, ("MarginDepositsDefaultFundAndInteroperabilityFundAssets",), PERIOD)["value"]
        clearing_liability = _instant(structural, ("MarginDepositsDefaultFundAndInteroperabilityFundLiabilities",), PERIOD)["value"]
        if clearing_cash != clearing_liability:
            raise ValueError("CBOE: clearing collateral mismatch")
        bridge_context = {"clearing_assets": clearing_cash, "clearing_liabilities": clearing_liability, "treatment": "Matched clearing collateral is excluded from issuer cash."}
        growth, wacc, terminal = (-.03, .03, .06), (.11, .095, .085), (0.0, .015, .02)
    elif ticker == "V":
        cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), PERIOD)["value"] + _instant(structural, ("Investments",), PERIOD)["value"]
        debt = _instant(structural, ("DebtLongtermAndShorttermCombinedAmount",), PERIOD)["value"]
        settlement_gap = max(0.0, _instant(structural, ("SettlementPayable",), PERIOD)["value"] - _instant(structural, ("SettlementReceivable",), PERIOD)["value"])
        litigation_gap = max(0.0, _instant(structural, ("LitigationReserveCurrent",), PERIOD)["value"] - _instant(structural, ("RestrictedCashAndCashEquivalentsU.S.LitigationEscrow",), PERIOD)["value"])
        claims = settlement_gap + litigation_gap
        share = _instant(structural, ("SharesOutstandingAsConvertedBasis",), PERIOD, unit="xbrli:shares")
        collateral_assets = _instant(structural, ("CustomerCollateralAssets",), PERIOD)["value"]
        collateral_liabilities = _instant(structural, ("CustomerCollateralLiabilities",), PERIOD)["value"]
        if collateral_assets != collateral_liabilities:
            raise ValueError("V: customer collateral mismatch")
        bridge_context = {"matched_customer_collateral": collateral_assets, "settlement_gap": settlement_gap, "accrued_litigation_less_restricted_escrow": litigation_gap, "preferred_treatment": "As-converted share denominator includes preferred conversion; the $514M preferred balance is not deducted again.", "treatment": "Customer collateral and restricted litigation escrow are not issuer cash."}
        growth, wacc, terminal = (.02, .06, .09), (.095, .085, .075), (.015, .02, .025)
    elif ticker == "TRGP":
        cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), PERIOD)["value"]
        debt = _instant(structural, ("DebtCurrentNetOfIssuanceCost",), PERIOD)["value"] + _instant(structural, ("LongTermDebtAndCapitalLeaseObligations",), PERIOD)["value"]
        claims = _instant(structural, ("MinorityInterest",), PERIOD)["value"]
        share = _latest_shares(ticker, structural)
        bridge_context = {"finance_lease_liability": _instant(structural, ("FinanceLeaseLiability",), PERIOD), "treatment": "The reported long-term debt balance includes finance-lease obligations; the separate lease fact is disclosed but not added twice."}
        growth, wacc, terminal = (-.02, .02, .05), (.115, .10, .09), (0.0, .015, .02)
    elif ticker == "KMI":
        cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), PERIOD)["value"]
        debt = _instant(structural, ("DebtCurrent",), PERIOD)["value"] + _instant(structural, ("LongTermDebtNoncurrent",), PERIOD)["value"]
        claims = _instant(structural, ("MinorityInterest",), PERIOD)["value"]
        share = _latest_shares(ticker, structural)
        bridge_context = {"cutoff_refinancing": {"issued_debt": 1_750_000_000.0, "issued_cash": 1_750_000_000.0, "net_debt_change": 0.0, "accession": "0001104659-26-089797", "treatment": "Proceeds are designated for commercial-paper repayment and upcoming maturities; debt and cash are overlaid once with no net-debt change."}, "treatment": "Equity-method investments are operating assets and are not added as surplus cash."}
        growth, wacc, terminal = (-.01, .015, .03), (.105, .09, .08), (.005, .015, .02)
    else:
        raise ValueError(ticker)
    share_values = (share["value"] * 1.015, share["value"], share["value"] * .985)
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(starting[index], growth[index], terminal[index], wacc[index], cash, debt, 0.0, claims, share_values[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": max(0.0, raw), "starting_cash_fcff": starting[index], "growth": growth[index], "wacc": wacc[index], "terminal_growth": terminal[index], "cash_and_investments": cash, "debt_and_finance_leases": debt, "other_equity_claims": claims, "shares": share_values[index], "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError(f"{ticker}: invalid operating range")
    availability = "available" if ticker in PASS_TICKERS else "conditional_estimate"
    model_cap = "Medium" if availability == "available" else "Low"
    reasons = () if availability == "available" else ("SPECIALIST_MODEL_UNCERTAINTY",)
    if ticker == "TRGP":
        reasons += ("CAPEX_CASH_CONVERSION_SENSITIVITY",)
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap=model_cap, source_cap="High", reasons=reasons)
    method = "financial_exchange_operating_fcff" if ticker == "CBOE" else "payments_operating_fcff" if ticker == "V" else "midstream_resource_cycle_fcff"
    warnings = {
        "CBOE": "Conditional Low exchange/data FCFF baseline. Five annual periods plus current TTM bound cash conversion; matched clearing collateral is excluded from issuer cash. Pending Australia/Canada disposals and the amended credit facility remain material scope events.",
        "V": "Conditional Low payments FCFF baseline. Four annual periods plus current TTM include reported technology investment. Customer collateral is matched and excluded; settlement and litigation gaps are reserved conservatively, and preferred shares use the reported as-converted denominator.",
        "TRGP": "Conditional Low midstream FCFF baseline. Reported adjusted cash flow, maintenance capex and growth capex are mapped through full/half/quarter growth-capex retention. Stakeholder acquisition, project execution, finance leases, leverage and optimization margins remain material.",
        "KMI": "Conditional Low midstream FCFF baseline. Five annual periods plus current TTM preserve cash conversion and project spending. The cutoff $1.75B note issue is treated as net-debt-neutral refinancing; project backlog, leverage and equity-method cash remain material.",
    }
    invalidation = "Revalue if recurring cash conversion, reinvestment, settlement/clearing funds, litigation, debt/lease/NCI claims, shares, project execution or cutoff events leave the bounded range."
    assumptions = {**profile.public_metadata(), "forecast_years": 8, "history_years_used": len(annual), "normalization_basis": "reported_cash_fcff_history" if ticker != "TRGP" else "reported_adjusted_cash_flow_with_growth_capex_sensitivity", "assumption_source_mix": "reported_history_and_governed_scenarios", "cash_conversion_margin": tuple(value / revenue for value in starting), "growth": growth, "wacc": wacc, "terminal_growth": terminal, "shares": share_values, "equity_floor_basis": "bear-only limited liability floor; raw residual retained privately", "calculator_calibration": "Exact enterprise cash-FCFF default replay.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker=ticker, method=method, method_version=BATCH_39_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE if availability == "available" else AvailabilityType.CONDITIONAL, warnings=(warnings[ticker], invalidation))
    return {"ticker": ticker, "method": method, "model_version": BATCH_39_HISTORY_VERSION, "availability_type": availability, "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": revenue, "ttm_cash_fcff": fcff, "share_count": share["value"]}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flow_sources, "annual_cash_sources": list(annual), "tax_rate": tax, "tax_rate_sources": tax_sources, "company_history_profile": profile.as_private_dict(), "bridge_context": bridge_context, "special_reinvestment": special_reinvestment, "event_sources": event, "model_trace": {"states": traces}, "raw_scenario_rows": rows, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warnings[ticker], "baseline": baseline.as_private_dict()}


def build_batch_39_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path | None = None) -> dict[str, Any]:
    if ticker not in BATCH_39_TICKERS:
        raise ValueError(ticker)
    packet = Path(source_root) / ticker
    structural_packet = Path(structural_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    source_manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((structural_packet / "structural-filing.json").read_text())
    filing = _controlling(source_manifest, submissions)
    if structural.get("source_accession") != filing["accession"] or structural.get("report_date") != PERIOD:
        raise ValueError(f"{ticker}: controlling identity mismatch")
    verification = _verify_source_bundle(ticker=ticker, packet=packet, structural_packet=structural_packet, structural_cache_root=Path(structural_cache_root), filing=filing)
    event = _event_sources(ticker, Path(event_root), verification["source_manifest_sha256"])
    result = _financial_result(ticker, facts, structural, filing, event) if ticker in FINANCIAL_TICKERS else _operating_result(ticker, submissions, facts, structural, filing, event)
    result["source_ledger"]["runtime_source_verification"] = verification
    return result


if FINANCIAL_TICKERS | OPERATING_TICKERS != set(BATCH_39_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_39_TICKERS):
    raise RuntimeError("Batch 39 policy mismatch")
