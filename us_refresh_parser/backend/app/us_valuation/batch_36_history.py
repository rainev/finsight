"""Cutoff-safe, history-backed valuation candidates for Universe Reset Batch 36.

FISV is valued as an operating payments processor after separating settlement
cash.  Eight financial issuers use common-equity residual income.  VLO remains
withheld because the Port Arthur claim identified by the controlling filing is
material and cannot presently be bounded without invention.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from app.valuation.bank import residual_income_valuation

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling
from .batch_08_history import _annual_cash_with_losses
from .batch_35_history import _equity, _instant, _period_flow, _rows, _share, _source
from .batch_36 import BATCH_36_MANIFEST, BATCH_36_TICKERS, BATCH_36_VALUATION_DATE
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, build_cash_fcff_history_profile, summarize_history_metric
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_36_HISTORY_VERSION = "BATCH-36-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset()
CONDITIONAL_TICKERS = frozenset(set(BATCH_36_TICKERS) - {"VLO"})
WITHHELD_TICKERS = frozenset({"VLO"})
FINANCIAL_TICKERS = tuple(ticker for ticker in BATCH_36_TICKERS if ticker not in {"FISV", "VLO"})


EARNINGS: dict[str, tuple[str, ...]] = {
    "AMP": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
    "C": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "HIG": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "GS": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "MS": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "CB": ("NetIncomeLoss",),
    "ALL": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "COF": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
}


POLICY: dict[str, dict[str, Any]] = {
    "AMP": {"method": "asset_manager_insurance_residual_income_equity_earnings", "roe": (.10, .14, .18), "payout": (.20, .35, .50), "coe": (.105, .095, .085), "warning": "Conditional Low mixed wealth-and-insurance residual-income baseline. Client assets and policy reserves remain inside equity economics; fee cycles, insurance claims, capital and parent distributions remain material."},
    "C": {"method": "diversified_bank_residual_income_equity_earnings", "roe": (.06, .09, .12), "payout": (.25, .35, .45), "coe": (.12, .105, .095), "warning": "Conditional Low diversified-bank residual-income baseline. Banamex and Poland exits, legacy portfolios, credit costs, deposits and capital make older periods less comparable."},
    "HIG": {"method": "multiline_insurance_residual_income_equity_earnings", "roe": (.08, .12, .16), "payout": (.20, .30, .40), "coe": (.11, .095, .085), "warning": "Conditional Low multiline-insurance residual-income baseline. Catastrophe losses, reserve development, benefits, investment marks and regulatory capital remain material."},
    "GS": {"method": "investment_broker_dealer_residual_income_equity_earnings", "roe": (.08, .12, .16), "payout": (.25, .35, .45), "coe": (.115, .10, .09), "warning": "Conditional Low broker-dealer residual-income baseline. Trading and investment-banking cycles, regulatory capital and the cutoff preferred-stock changes remain material."},
    "MS": {"method": "wealth_broker_dealer_residual_income_equity_earnings", "roe": (.08, .12, .16), "payout": (.30, .40, .50), "coe": (.11, .095, .085), "warning": "Conditional Low wealth-and-broker-dealer residual-income baseline. Client assets are not issuer cash; market levels, compensation, capital and acquisition effects remain material."},
    "CB": {"method": "property_casualty_insurance_residual_income_equity_earnings", "roe": (.08, .12, .16), "payout": (.20, .30, .40), "coe": (.11, .095, .085), "warning": "Conditional Low P&C-insurance residual-income baseline. Catastrophe losses, reserve development, reinsurance, FX and the preferred-claim absence check remain material."},
    "ALL": {"method": "property_casualty_insurance_residual_income_equity_earnings", "roe": (.08, .12, .16), "payout": (.20, .30, .40), "coe": (.11, .095, .085), "warning": "Conditional Low P&C-insurance residual-income baseline. Auto/home pricing, catastrophe losses, reserves, investments and the new Oklahoma litigation remain material; no unreported litigation reserve is invented."},
    "COF": {"method": "post_discover_consumer_finance_residual_income_equity_earnings", "roe": (.06, .09, .12), "payout": (.25, .35, .45), "coe": (.12, .105, .095), "warning": "Conditional Low post-Discover consumer-finance residual-income baseline. It uses a combined-company TTM anchor and current equity only; pre-close histories are retained as diagnostics but are not spliced into the valuation. Brex purchase accounting remains provisional."},
}


def _annual(facts: dict[str, Any], ticker: str) -> tuple[dict[str, Any], ...]:
    selected: dict[str, tuple[dict[str, Any], str]] = {}
    for concept in EARNINGS[ticker]:
        for row in _rows(facts, concept):
            if row.get("form") not in {"10-K", "10-K/A"} or row.get("filed", "") > BATCH_36_VALUATION_DATE or not row.get("start") or not row.get("end"):
                continue
            try:
                span = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
            except ValueError:
                continue
            if not 300 <= span <= 380:
                continue
            old = selected.get(row["end"])
            if old is None or (row.get("filed", ""), row.get("accn", "")) > (old[0].get("filed", ""), old[0].get("accn", "")):
                selected[row["end"]] = (row, concept)
        if len(selected) >= 5:
            break
    if len(selected) < 5:
        raise ValueError(f"{ticker}: fewer than five exact annual common-earnings periods")
    return tuple({"period_end": end, "value": float(selected[end][0]["val"]), "source": _source(selected[end][0], selected[end][1])} for end in sorted(selected)[-5:])


def _structural_rows(structural: dict[str, Any], names: Iterable[str], *, period_start: str | None, period_end: str, unit: str | None = None) -> list[dict[str, Any]]:
    for name in names:
        rows = [row for row in structural.get("facts", []) if row.get("local_name") == name and row.get("period_start") == period_start and row.get("period_end") == period_end and not row.get("dimensions") and isinstance(row.get("value"), (int, float)) and (unit is None or row.get("unit") == unit)]
        if rows:
            return rows
    return []


def _preferred(ticker: str, structural: dict[str, Any], period_end: str, total_equity: float) -> tuple[float, str, list[dict[str, Any]], tuple[float, float, float]]:
    names = ("PreferredStockLiquidationPreferenceValue", "PreferredStockCarryingValue", "PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount", "PreferredStockValue")
    zero = None
    for name in names:
        try:
            row = _instant(structural, (name,), period_end)
        except ValueError:
            continue
        if float(row["value"]) > 0:
            value = float(row["value"])
            return value, "reported_preferred_claim", [row], (value, value, value)
        zero = row
    if ticker == "AMP":
        absence = {"source_kind": "statement_equity_scope_check", "accession": structural.get("source_accession"), "period_end": period_end, "finding": "issuer equity statement presents common stock and retained earnings without a preferred class", "reported_vs_estimated": "source_bounded_absence_check"}
        return 0., "statement_proven_preferred_absence", [absence] + ([zero] if zero else []), (0., 0., 0.)
    if ticker == "CB":
        absence = {"source_kind": "structural_xbrl_absence_check", "accession": structural.get("source_accession"), "period_end": period_end, "searched_concepts": list(names), "treatment": "Absence is bounded with an adverse common-equity sensitivity; it is not substituted with zero.", "reported_vs_estimated": "source_bounded_absence_check"}
        values = (0., total_equity * .01, total_equity * .03)
        return values[1], "preferred_claim_bounded_from_no_reported_claim_row", [absence], values
    if zero is not None:
        return 0., "reported_preferred_absence", [zero], (0., 0., 0.)
    raise ValueError(f"{ticker}: preferred claim is neither reported nor bounded")


def _event_rows(ticker: str, event_root: Path | None, source_manifest_sha256: str) -> list[dict[str, Any]]:
    if event_root is None:
        raise ValueError(f"{ticker}: event ledger required")
    packet = Path(event_root) / ticker
    receipt_path = packet / "source-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    filings = receipt.get("screened_filings") or []
    if receipt.get("schema_version") != "FINSIGHT-BATCH-36-EVENT-LEDGER-1" or receipt.get("ticker") != ticker or receipt.get("valuation_date") != BATCH_36_VALUATION_DATE or receipt.get("source_manifest_sha256") != source_manifest_sha256 or receipt.get("decision") not in {"accepted", "rejected"} or not filings or any(row.get("filed", "") > BATCH_36_VALUATION_DATE for row in filings):
        raise ValueError(f"{ticker}: invalid event source")
    documents = []
    for document in receipt.get("documents", []):
        path = packet / document["document"]
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != document.get("sha256"):
            raise ValueError(f"{ticker}: event document hash mismatch")
        documents.append(document)
    return [{"source_kind": "sec_event_screening", "decision": receipt["decision"], "screened_filings": filings, "documents": documents, "source_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(), "reported_terms": receipt.get("reported_terms", {}), "treatment": receipt.get("treatment"), "reported_vs_estimated": "reported" if receipt["decision"] == "accepted" else "screened_and_rejected"}]


def _verify_source_bundle(*, ticker: str, packet: Path, structural_packet: Path, structural_cache_root: Path, filing: dict[str, Any]) -> dict[str, Any]:
    issuer = next(row for row in BATCH_36_MANIFEST if row.ticker == ticker)
    source_manifest_path = packet / "source-manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text())
    if source_manifest.get("issuer", {}).get("ticker") != ticker or source_manifest.get("issuer", {}).get("cik") != issuer.cik:
        raise ValueError(f"{ticker}: source packet identity mismatch")
    packet_hashes = {}
    for name, expected in source_manifest.get("packet_payload_sha256", {}).items():
        path = packet / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if actual != expected:
            raise ValueError(f"{ticker}: source packet hash mismatch for {name}")
        packet_hashes[name] = actual
    receipt_path = structural_packet / "source-receipt.json"
    structural_path = structural_packet / "structural-filing.json"
    package_path = structural_packet / "package-manifest.json"
    receipt = json.loads(receipt_path.read_text())
    package = json.loads(package_path.read_text())
    expected_filing = {"accession": filing["accession"], "filed": filing["filed"], "form": filing["form"], "report_date": filing["period_end"]}
    actual_filing = receipt.get("filing") or {}
    if receipt.get("schema_version") != "FINSIGHT-BATCH-36-STRUCTURAL-SOURCE-1" or receipt.get("ticker") != ticker or receipt.get("cik") != issuer.cik or receipt.get("valuation_date") != BATCH_36_VALUATION_DATE or any(actual_filing.get(key) != value for key, value in expected_filing.items()):
        raise ValueError(f"{ticker}: structural receipt identity mismatch")
    structural_hash = hashlib.sha256(structural_path.read_bytes()).hexdigest()
    package_hash = hashlib.sha256(package_path.read_bytes()).hexdigest()
    if structural_hash != receipt.get("structural_filing_sha256") or package_hash != receipt.get("package_manifest_sha256"):
        raise ValueError(f"{ticker}: structural source hash mismatch")
    entrypoint = package.get("entrypoint_local_path")
    package_entry = next((row for row in package.get("files", []) if row.get("local_path") == entrypoint), None)
    html_path = next((Path(structural_cache_root) / "filings" / ticker).glob(f"**/{entrypoint}"), None) if entrypoint else None
    if package_entry is None or html_path is None or hashlib.sha256(html_path.read_bytes()).hexdigest() != package_entry.get("sha256"):
        raise ValueError(f"{ticker}: primary filing document hash mismatch")
    return {"source_kind": "runtime_verified_source_bundle", "ticker": ticker, "cik": issuer.cik, "source_manifest_sha256": hashlib.sha256(source_manifest_path.read_bytes()).hexdigest(), "packet_payload_sha256": packet_hashes, "structural_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(), "structural_filing_sha256": structural_hash, "package_manifest_sha256": package_hash, "primary_document": entrypoint, "primary_document_sha256": package_entry["sha256"], "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "verified": True}


def _financial_result(ticker: str, facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], event_root: Path, manifest_sha: str) -> dict[str, Any]:
    policy = POLICY[ticker]
    event_rows = _event_rows(ticker, event_root, manifest_sha)
    event_terms = event_rows[0]["reported_terms"] if event_rows[0]["decision"] == "accepted" else {}
    period = filing["period_end"]
    annual = _annual(facts, ticker)
    current = _period_flow(structural, EARNINGS[ticker], period)
    duration = (date.fromisoformat(period) - date.fromisoformat(current["period_start"])).days
    prior = _period_flow(structural, EARNINGS[ticker], "2025-06-30", target_days=duration)
    earnings_attribution_context: list[dict[str, Any]] = []
    if ticker == "CB":
        # CB labels NetIncomeLoss as "Net income attributable to Chubb" and
        # ProfitLoss as consolidated net income.  Prove the identity, but do
        # not subtract NCI twice from the already-parent-attributable line.
        current_parent = current
        prior_parent = prior
        current_consolidated = _period_flow(structural, ("ProfitLoss",), period, target_days=duration)
        current_nci = _period_flow(structural, ("NetIncomeLossAttributableToNoncontrollingInterest",), period, target_days=duration)
        prior_consolidated = _period_flow(structural, ("ProfitLoss",), "2025-06-30", target_days=duration)
        prior_nci = _period_flow(structural, ("NetIncomeLossAttributableToNoncontrollingInterest",), "2025-06-30", target_days=duration)
        if current_consolidated["value"] - current_nci["value"] != current_parent["value"] or prior_consolidated["value"] - prior_nci["value"] != prior_parent["value"]:
            raise ValueError("CB: parent earnings attribution does not reconcile")
        earnings_attribution_context = [{"period": "current_h1", "parent_attributable": current_parent, "consolidated": current_consolidated, "nci": current_nci, "formula": "ProfitLoss - NetIncomeLossAttributableToNoncontrollingInterest = NetIncomeLoss (attributable to Chubb); selected parent line is not reduced again"}, {"period": "prior_h1", "parent_attributable": prior_parent, "consolidated": prior_consolidated, "nci": prior_nci, "formula": "ProfitLoss - NetIncomeLossAttributableToNoncontrollingInterest = NetIncomeLoss (attributable to Chubb); selected parent line is not reduced again"}]
    ttm = float(annual[-1]["value"]) + float(current["value"]) - float(prior["value"])
    end_total = _equity(structural, period, facts)
    prior_total = _equity(structural, "2025-12-31", facts)
    preferred, preferred_status, preferred_context, preferred_range = _preferred(ticker, structural, period, float(end_total["value"]))
    prior_preferred, prior_status, prior_context, prior_range = _preferred(ticker, structural, "2025-12-31", float(prior_total["value"]))
    event_claim = float(event_terms.get("net_preferred_claim_and_proceeds", 0.)) if ticker == "GS" else 0.
    if ticker == "GS":
        preferred_drag = float(event_terms.get("net_annual_preferred_dividend_increase", 0.))
        after_tax_interest = float(event_terms.get("annualized_after_tax_interest", 0.))
        event_drag = tuple(preferred_drag + after_tax_interest * factor for factor in (1., .5, 0.))
    else:
        event_drag = (0., 0., 0.)
    post_event_total = float(end_total["value"]) + event_claim
    preferred_range = tuple(value + event_claim for value in preferred_range)
    begin_common = float(prior_total["value"]) - prior_preferred
    share = _share(structural, facts, period)
    share_value = float(share["value"])
    if min(ttm, begin_common, post_event_total - preferred_range[2], share_value) <= 0:
        raise ValueError(f"{ticker}: nonpositive common inputs")
    observations = [HistoryObservation("annual", row["period_end"], int(row["period_end"][:4]), row["value"], "USD", "reported annual common earnings", (row["source"],)) for row in annual]
    observations.append(HistoryObservation("operating_ttm", period, None, ttm, "USD", "latest FY plus current H1 less prior H1", (annual[-1]["source"], current, prior)))
    metric_observations = observations if ticker != "COF" else observations[-1:]
    metric = summarize_history_metric("normalized_common_earnings", metric_observations)
    if metric is None:
        raise ValueError(f"{ticker}: earnings history unavailable")
    comparable = ticker != "COF"
    history_periods = tuple(row["period_end"] for row in annual) if comparable else (period,)
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "financial_equity_residual_income", BATCH_36_VALUATION_DATE, history_periods, (metric,), comparable, "reported_and_company_history" if comparable else "reported_history_and_finsight_policy")
    common_mid = post_event_total - preferred_range[1]
    if comparable:
        history_low = max(.02, min(metric.low, ttm) / max(common_mid, 1.))
        history_high = max(history_low, max(metric.high, ttm) / max(common_mid, 1.))
        roes = tuple(min(value, history_high) for value in policy["roe"])
        # A high observed ROE is not a floor.  The policy may deliberately be
        # more conservative than every recent observation; history caps
        # optimism but never forces a current-cycle spike into the forecast.
        if not 0 < roes[0] <= roes[1] <= roes[2] <= history_high or roes[0] == roes[2]:
            roes = (max(.02, history_high * .5), max(.025, history_high * .75), history_high)
    else:
        current_roe = ttm / max((begin_common + common_mid) / 2., 1.)
        roes = tuple(min(value, max(.06, current_roe)) for value in policy["roe"])
        if roes[0] == roes[2]:
            roes = (max(.03, current_roe * .67), current_roe, min(.15, current_roe * 1.33))
    claims = (preferred_range[2], preferred_range[1], preferred_range[0])
    shares = (share_value * 1.015, share_value, share_value * .985)
    rows, traces = [], {}
    for idx, name in enumerate(("bear", "base", "bull")):
        common_equity = post_event_total - claims[idx]
        roe = max(.01, roes[idx] - event_drag[idx] / max(common_equity, 1.))
        trace = residual_income_valuation(book_value_per_share=common_equity / shares[idx], current_roe=roe, cost_of_equity=policy["coe"][idx], current_payout_ratio=policy["payout"][idx], terminal_roe=(.085, .105, .115)[idx], terminal_growth=(.01, .02, .025)[idx], years=5)
        raw = float(trace["intrinsic_value"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": raw, "book_value_per_share": common_equity / shares[idx], "current_roe": roe, "current_payout_ratio": policy["payout"][idx], "cost_of_equity": policy["coe"][idx], "terminal_roe": (.085, .105, .115)[idx], "terminal_growth": (.01, .02, .025)[idx], "shares": shares[idx], "preferred_claim": claims[idx], "ending_common_equity": common_equity, "event_forward_common_earnings_drag": event_drag[idx], "limited_liability_floor_applied": False})
        traces[name] = trace
    scenario = {"low": rows[0]["raw_value_per_share"], "base": rows[1]["raw_value_per_share"], "high": rows[2]["raw_value_per_share"]}
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid residual-income range")
    reasons = ("SPECIALIST_MODEL_UNCERTAINTY", "PROVISIONAL_BANK_CAPITAL_RANGE") if ticker in {"C", "GS", "MS", "COF"} else ("SPECIALIST_MODEL_UNCERTAINTY",)
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    warning = policy["warning"]
    if preferred_status == "preferred_claim_bounded_from_no_reported_claim_row":
        warning += f" Missing preferred detail is not treated as zero: bear/base/bull common-equity claims are ${preferred_range[2]/1e9:.2f}B/${preferred_range[1]/1e9:.2f}B/$0."
    if ticker == "GS":
        warning += " The cutoff bridge adds the July $2.5B Series AA issue and removes the completed $0.75B Series U redemption once; common book equity is unchanged by equal proceeds and claims. The July $10B notes add $567.775M annual gross interest. Using a governed 21% tax rate and 0%/50%/100% proceeds-income offset, total preferred-plus-debt earnings drag is applied across bear/base/bull without EV-bridging the funding."
    assumptions = {**profile.public_metadata(), "forecast_years": 5, "normalization_basis": "reported_parent_common_equity_with_history_bounded_roe" if comparable else "post_discover_combined_ttm_and_current_common_equity", "assumption_source_mix": "reported_equity_earnings_company_history_and_finsight_policy" if comparable else "reported_combined_ttm_current_equity_and_finsight_policy", "equity_floor_basis": "not applied", "earnings_multiples": tuple(row["raw_value_per_share"] * row["shares"] / ttm for row in rows), "current_roe": tuple(row["current_roe"] for row in rows), "current_payout_ratio": policy["payout"], "cost_of_equity": policy["coe"], "terminal_roe": (.085, .105, .115), "terminal_growth": (.01, .02, .025), "shares": shares, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "preferred_claim_status": preferred_status, "preferred_claim_range": preferred_range, "event_preferred_claim_and_proceeds": event_claim, "event_forward_common_earnings_drag": event_drag, "event_debt_principal": float(event_terms.get("debt_principal", 0.)), "event_annualized_gross_interest": float(event_terms.get("annualized_gross_interest", 0.)), "event_interest_tax_rate": event_terms.get("governed_interest_tax_rate"), "event_proceeds_income_offset": (0., .5, 1.) if ticker == "GS" else (0., 0., 0.), "calculator_calibration": "Calculator replays the exact residual-income assumptions.", "invalidation": "Invalidate if parent earnings, common equity, preferred claims, shares, capital or the named business-cycle conditions leave the bounded range."}
    baseline = BaselineValuation(ticker=ticker, method=policy["method"], method_version=BATCH_36_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported common equity", common_mid, AssumptionClassification.REPORTED, "Current parent equity less separately identified preferred claims."),), warnings=(warning, assumptions["invalidation"]), confidence_reasons=reasons, calculator_link=f"/api/us-valuations/{ticker}/calculator")
    reported_preferred = preferred if preferred_status.startswith("reported_") else None
    reported_prior_preferred = prior_preferred if prior_status.startswith("reported_") else None
    return {"ticker": ticker, "method": policy["method"], "model_version": BATCH_36_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_common_earnings": ttm, "beginning_total_equity": float(prior_total["value"]), "ending_total_equity": float(end_total["value"]), "post_event_total_equity": post_event_total, "reported_beginning_preferred_equity": reported_prior_preferred, "reported_preferred_equity": reported_preferred, "beginning_preferred_claim_midpoint": prior_preferred, "preferred_claim_midpoint": preferred, "beginning_common_equity": begin_common, "ending_common_equity": common_mid}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "common_earnings_reconstruction": {"latest_fy": annual[-1], "current_ytd": current, "prior_ytd": prior, "ttm": ttm}, "earnings_attribution_context": earnings_attribution_context, "company_history_profile": profile.as_private_dict(), "predecessor_history_treatment": "rejected_from_model_due_post_discover_scope" if ticker == "COF" else "accepted_as_comparable_history", "equity_model_context": [end_total, prior_total, *preferred_context, *prior_context, share], "preferred_context": {"current_status": preferred_status, "prior_status": prior_status, "current": preferred_context, "prior": prior_context, "prior_range": prior_range}, "event_sources": event_rows, "bridge_treatment": "Equity-level model: deposits, policy reserves, client assets, repo funding and investments remain inside common earnings/equity; no EV debt bridge and no double NCI subtraction.", "residual_income_trace": {"states": traces}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def _fisv_result(submissions: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], event_root: Path, manifest_sha: str) -> dict[str, Any]:
    event_rows = _event_rows("FISV", event_root, manifest_sha)
    normalizer = _normalizer(submissions, facts)
    flows = {field: normalizer.ttm_flow(field) for field in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    # Keep one consistent interest lineage.  The normalizer selects the newer
    # InterestExpenseNonoperating lineage; it must never sum the overlapping alias.
    interest_sources = flows["interest_expense"]["sources"]
    if len({row.get("concept") for row in interest_sources}) != 1 or interest_sources[0].get("concept") != "InterestExpenseNonoperating":
        raise ValueError("FISV: mixed interest concepts")
    tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    cash_fcff = cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]), capital_expenditures=float(flows["capital_expenditures"]["value"]), spectrum_investment=0., interest_expense=abs(float(flows["interest_expense"]["value"])), tax_rate=tax_rate)
    annual_cash, _, annual_rows = _annual_cash_with_losses(normalizer)
    profile = build_cash_fcff_history_profile(annual_cash_states=annual_rows, ttm_revenue=float(flows["revenue"]["value"]), ttm_cash_fcff=cash_fcff, ttm_period_end=filing["period_end"], ttm_sources=[source for flow in flows.values() for source in flow["sources"]], valuation_date=BATCH_36_VALUATION_DATE)
    cash_metric = profile.metric("cash_conversion_margin")
    growth_metric = profile.metric("revenue_growth")
    if not profile.full_history or cash_metric is None or growth_metric is None or len(annual_cash) < 5:
        raise ValueError("FISV: history unavailable")
    finance_asset_burden = (300_000_000., 150_000_000., 0.)
    merchant_originations = _period_flow(structural, ("PaymentsForMerchantCashAdvances",), filing["period_end"])
    merchant_collections = _period_flow(structural, ("RepaymentsAndSalesForMerchantCashAdvances",), filing["period_end"])
    settlement_anticipation = _period_flow(structural, ("PaymentsForSettlementOfAnticipationProgram",), filing["period_end"])
    current_net_finance_asset_collection = abs(float(merchant_collections["value"])) - float(merchant_originations["value"]) + abs(float(settlement_anticipation["value"]))
    if current_net_finance_asset_collection != finance_asset_burden[0]:
        raise ValueError("FISV: captive-finance flow reconciliation changed")
    margins = tuple(max(.001, value) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    growth = (max(-.05, min(0., growth_metric.low)), max(-.03, min(.03, growth_metric.base)), max(0., min(.06, growth_metric.high)))
    cash_row = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), filing["period_end"])
    settlement_asset = _instant(structural, ("SettlementAssetsCurrent",), filing["period_end"])
    settlement_liability = _instant(structural, ("SettlementLiabilitiesCurrent",), filing["period_end"])
    debt_current = _instant(structural, ("LongTermDebtAndCapitalLeaseObligationsCurrent",), filing["period_end"])
    debt_noncurrent = _instant(structural, ("LongTermDebtAndCapitalLeaseObligations",), filing["period_end"])
    nci = _instant(structural, ("MinorityInterest",), filing["period_end"])
    preferred = _instant(structural, ("PreferredStockValue",), filing["period_end"])
    share = _share(structural, facts, filing["period_end"])
    if settlement_asset["value"] != settlement_liability["value"] or cash_row["value"] != 627_000_000:
        raise ValueError("FISV: settlement bridge mismatch")
    debt = float(debt_current["value"] + debt_noncurrent["value"])
    claims = float(nci["value"] + preferred["value"])
    shares = (float(share["value"]) * 1.015, float(share["value"]), float(share["value"]) * .985)
    rows, traces = [], {}
    for idx, name in enumerate(("bear", "base", "bull")):
        starting = float(flows["revenue"]["value"]) * margins[idx] - finance_asset_burden[idx]
        state = EnterpriseCashFlowState(starting, growth[idx], (.01, .02, .025)[idx], (.105, .095, .085)[idx], float(cash_row["value"]), debt, 0., claims, shares[idx])
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": max(0., raw), "starting_cash_fcff": starting, "cash_conversion_margin": margins[idx], "captive_finance_reinvestment_burden": finance_asset_burden[idx], "growth": growth[idx], "wacc": state.wacc, "terminal_growth": state.terminal_growth, "cash_and_investments": state.cash_and_investments, "debt_and_finance_leases": debt, "other_equity_claims": claims, "shares": shares[idx], "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError("FISV: invalid FCFF range")
    reasons = ("CONSOLIDATED_MODEL_FALLBACK", "CAPEX_CASH_CONVERSION_SENSITIVITY", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    warning = "Conditional Low payments-processor FCFF baseline. Reported operating cash flow excludes settlement cash; only $627M unrestricted issuer cash enters the bridge, while equal $17.561B settlement assets and obligations are excluded. Captive-finance reinvestment is not treated as recurring inflow: a governed $300M/$150M/$0 bear/base/bull burden is deducted once. The July President resignation and interim Financial Solutions leadership are an execution warning, not an invented cash adjustment."
    assumptions = {**profile.public_metadata(), "forecast_years": FORECAST_YEARS, "normalization_basis": "reported_cash_fcff_with_settlement_and_captive_finance_separation", "assumption_source_mix": "reported_company_history_and_finsight_policy", "cash_conversion_margin": margins, "growth": growth, "wacc": (.105, .095, .085), "terminal_growth": (.01, .02, .025), "cash_and_investments": (cash_row["value"],) * 3, "debt_and_finance_leases": (debt,) * 3, "other_equity_claims": (claims,) * 3, "shares": shares, "captive_finance_reinvestment_burden": finance_asset_burden, "captive_finance_range_basis": "The filing reports a $300M H1 net collection across merchant and settlement-anticipation advances. FinSight excludes that inflow from recurring FCFF and stress-tests an equal/full, half, and zero future reinvestment burden; the reported collection is not added to value.", "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0 else "not applied", "cash_bridge_range": {"low": scenario["base"], "midpoint": scenario["base"], "high": scenario["base"], "spread_ratio": 0.}, "calculator_calibration": "Calculator replays the exact enterprise FCFF base assumptions.", "invalidation": "Invalidate if settlement ownership, captive-finance reinvestment, cash conversion, debt, claims or shares leave the bounded range."}
    baseline = BaselineValuation(ticker="FISV", method="payments_processor_operating_fcff", method_version=BATCH_36_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("five-year cash history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Reported annual and TTM cash conversion anchors the range."),), warnings=(warning, assumptions["invalidation"]), confidence_reasons=reasons, calculator_link="/api/us-valuations/FISV/calculator")
    return {"ticker": "FISV", "method": "payments_processor_operating_fcff", "model_version": BATCH_36_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": flows["revenue"]["value"], "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": flows["interest_expense"]["value"], "tax_rate": tax_rate, "ttm_cash_fcff": cash_fcff}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": list(annual_rows), "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "captive_finance_reinvestment_reconciliation": {"merchant_originations": merchant_originations, "merchant_repayments_and_sales": merchant_collections, "settlement_anticipation_net_collection": settlement_anticipation, "reported_current_net_collection": current_net_finance_asset_collection, "governed_future_burden_range": finance_asset_burden, "formula": "abs(merchant repayments and sales) - merchant originations + abs(settlement-anticipation net collection) = $300M current net collection; exclude that inflow from recurring FCFF and deduct full/half/zero as a future reinvestment stress", "non_overlap": "These investing cash flows are outside reported OCF and capex, are not included as cash or bridge assets, and are applied only once through starting cash FCFF."}, "bridge_sources": [cash_row, settlement_asset, settlement_liability, debt_current, debt_noncurrent, nci, preferred, share], "event_sources": event_rows, "bridge_reconciliation": {"unrestricted_cash": cash_row["value"], "settlement_assets_excluded": settlement_asset["value"], "settlement_liabilities_excluded": settlement_liability["value"], "debt_and_finance_leases": debt, "other_equity_claims": claims, "shares": share["value"]}, "model_trace": {"states": traces}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def _vlo_withheld(filing: dict[str, Any], structural: dict[str, Any], event_rows: list[dict[str, Any]]) -> dict[str, Any]:
    cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), filing["period_end"])
    cash_restricted = _instant(structural, ("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",), filing["period_end"])
    debt_current = _instant(structural, ("DebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent"), filing["period_end"])
    debt_noncurrent = _instant(structural, ("LongTermDebtAndCapitalLeaseObligations",), filing["period_end"])
    nci = _instant(structural, ("MinorityInterest",), filing["period_end"])
    capex_current = _period_flow(structural, ("SegmentExpenditureAdditionToLongLivedAssets",), filing["period_end"])
    capex_prior = _period_flow(structural, ("SegmentExpenditureAdditionToLongLivedAssets",), "2025-06-30", target_days=180)
    warning = "Withheld: the March 2026 Port Arthur fire produced lawsuits and possible regulatory action whose full loss cannot reasonably be estimated. Insurance and planned repair capital do not bound those third-party claims, so publishing a value now would require guessing. The current filing supplies exact comparative H1 custom capex, but recovery also needs a cutoff-safe FY2025 full-year capex anchor rather than a stale standard tag."
    assumptions = {"history_policy_version": HISTORY_POLICY_VERSION, "history_years_used": 0, "normalization_basis": "resource_cycle_fcff_blocked_by_unbounded_port_arthur_claim_and_full_year_capex_gap", "assumption_source_mix": "reported_current_filing_and_event_ledger", "invalidation": "Recovery requires both a defensible finite Port Arthur claim bound (or immateriality evidence) and a cutoff-safe FY2025 full-year capex anchor for the through-cycle FCFF history."}
    baseline = BaselineValuation(ticker="VLO", method="resource_cycle_fcff", method_version=BATCH_36_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(warning, assumptions["invalidation"]))
    return {"ticker": "VLO", "method": "resource_cycle_fcff", "model_version": BATCH_36_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {}, "governed_assumptions": assumptions, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "bridge_sources": [cash, cash_restricted, debt_current, debt_noncurrent, nci, capex_current, capex_prior], "bridge_reconciliation": {"unrestricted_cash": cash["value"], "restricted_cash_excluded": cash_restricted["value"] - cash["value"], "debt_and_finance_leases_at_2026_06_30": debt_current["value"] + debt_noncurrent["value"], "post_quarter_debt_repayment": 100_000_000., "nci": nci["value"], "custom_capex_current_h1": capex_current["value"], "custom_capex_prior_h1": capex_prior["value"], "treatment": "Custom capex is retained; alternate debt aggregates are excluded to prevent overlap. July debt repayment would be bridged once only after the claim gate clears."}, "event_sources": event_rows, "release_condition": assumptions["invalidation"], "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def build_batch_36_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path | None = None, structural_cache_root: Path | None = None) -> dict[str, Any]:
    if ticker not in BATCH_36_TICKERS:
        raise ValueError(ticker)
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural_packet = Path(structural_root) / ticker
    structural = json.loads((structural_packet / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural.get("source_accession") != filing["accession"] or structural.get("report_date") != filing["period_end"]:
        raise ValueError(f"{ticker}: controlling source mismatch")
    cache_root = Path(structural_cache_root) if structural_cache_root else Path(structural_root).parent / "batch-36-structural-cache-20260905"
    verification = _verify_source_bundle(ticker=ticker, packet=packet, structural_packet=structural_packet, structural_cache_root=cache_root, filing=filing)
    events = _event_rows(ticker, Path(event_root) if event_root else None, verification["source_manifest_sha256"])
    if ticker == "VLO":
        result = _vlo_withheld(filing, structural, events)
    elif ticker == "FISV":
        result = _fisv_result(submissions, facts, structural, filing, Path(event_root), verification["source_manifest_sha256"])
    else:
        result = _financial_result(ticker, facts, structural, filing, Path(event_root), verification["source_manifest_sha256"])
    result["source_ledger"]["runtime_source_verification"] = verification
    return result


if set(POLICY) != set(FINANCIAL_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_36_TICKERS):
    raise RuntimeError("Batch 36 policy mismatch")
