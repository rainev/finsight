"""History-backed practical baselines for controlled Universe Reset Batch 20."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from app.valuation.bank import residual_income_valuation

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling, _duration, _point
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_11_history import _dimension_fact, _no_preferred
from .batch_16_history import _history_source, _share_point
from .batch_20 import BATCH_20_TICKERS, BATCH_20_VALUATION_DATE
from .equity_fact_selection import annual_facts
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, build_cash_fcff_history_profile, summarize_history_metric
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_20_HISTORY_VERSION = "BATCH-20-INDUSTRIALS-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset({"ROL", "SWK", "PAYX"})
CONDITIONAL_TICKERS = frozenset({"PNR", "AOS", "SNA", "LUV", "UAL", "UNP", "CTAS"})
WITHHELD_TICKERS = frozenset()
EQUITY_EARNINGS_TICKERS = frozenset({"SNA", "LUV"})


def _shares(weighted: float, current: float) -> tuple[float, float, float]:
    high = max(weighted, current)
    low = min(weighted, current)
    return high, (high + low) / 2.0, low


@dataclass(frozen=True)
class Policy:
    method: str
    period: str
    cash: float
    debt: float
    claims: tuple[float, float, float]
    shares: tuple[float, float, float]
    growth: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal: tuple[float, float, float]
    warning: str
    invalidation: str
    claim_formula: str


P = {
    "PNR": Policy("pre_taco_water_solutions_faded_fcff", "2026-06-30", 91_800_000.0, 1_606_000_000.0, (0.0,) * 3, _shares(162_600_000.0, 159_637_950.0), (-.03, .02, .05), (.11, .095, .085), (.005, .015, .025), "Conditional Low pre-Taco water-solutions baseline. Current standalone cash, debt, and shares are source bounded, while the signed $1.425B acquisition and $1.4B bridge commitment remain outside the current operating history.", "Invalidate if Taco closes, terminates, or changes; or if standalone cash conversion, debt, claims, or diluted shares changes materially.", "No reported NCI or preferred claim. Historical interest is conservatively estimated from the current source-linked interest/revenue ratio because the standard annual alias is stale."),
    "ROL": Policy("route_pest_control_faded_fcff", "2026-06-30", 109_085_000.0, 703_025_000.0, (0.0,) * 3, _shares(481_397_000.0, 481_145_404.0), (.02, .07, .10), (.105, .09, .08), (.005, .015, .025), "Source-bounded route pest-control baseline. Four-year cash history, current cash, short- and long-term debt, zero preferred equity, shares, and ordinary legal/insurance treatment reconcile.", "Invalidate if route density, pricing, acquisitions, cash conversion, debt, claims, or diluted shares changes materially.", "Short-term borrowings plus long-term debt are counted once. Self-insurance accruals remain operating liabilities inside cash conversion."),
    "AOS": Policy("post_leonard_valve_building_products_faded_fcff", "2026-06-30", 181_300_000.0, 637_500_000.0, (0.0,) * 3, _shares(138_511_483.0, 135_908_573.0), (-.02, .02, .05), (.105, .09, .08), (.005, .015, .025), "Conditional Low post-Leonard Valve building-products baseline. The debt-funded $470M acquisition is included through current balances and annualized filed acquired revenue, while purchase accounting and acquired cash conversion remain preliminary.", "Invalidate if Leonard Valve purchase accounting, acquired cash conversion, debt, warranties, claims, or diluted shares changes materially.", "Current and noncurrent debt are counted once. No NCI/preferred claim is reported; the valuation revenue adds one additional filed H1 acquired-revenue amount to annualize the partial contribution."),
    "SWK": Policy("post_cam_divestiture_tools_faded_fcff", "2026-07-04", 592_400_000.0, 4_757_900_000.0, (351_200_000.0,) * 3, _shares(151_401_000.0, 151_016_641.0), (-.05, -.02, .02), (.11, .095, .085), (0.0, .01, .02), "Source-bounded post-CAM tools baseline. The $1.815B sale proceeds are already reflected in current cash and debt repayment; CAM contributed only $22.8M of first-half pretax income, while environmental and contingent-consideration claims are deducted once.", "Invalidate if post-divestiture cash conversion, remaining transition services, debt, environmental/contingent claims, or diluted shares changes materially.", "$249.8M environmental accrual plus $101.4M contingent consideration. Sale proceeds are not added again and supplier finance remains an operating liability."),
    "UAL": Policy("airline_cycle_faded_fcff", "2026-06-30", 16_637_000_000.0, 24_294_000_000.0, (0.0,) * 3, _shares(326_700_000.0, 324_583_772.0), (-.03, .04, .07), (.12, .105, .095), (0.0, .01, .02), "Conditional Low airline-cycle baseline. Current unrestricted cash/investments, debt/capital leases, shares, and four-year post-pandemic cash history reconcile, while aircraft deliveries, $19B of capacity-purchase commitments, fuel, pensions, and cycle sensitivity remain material.", "Invalidate if demand, fares, fuel, aircraft or capacity commitments, pensions, debt/leases, claims, or diluted shares changes materially.", "Restricted cash is excluded; operating leases and capacity-purchase obligations remain inside future cash-conversion scenarios rather than being deducted twice."),
    "UNP": Policy("pre_norfolk_southern_rail_faded_fcff", "2026-06-30", 1_614_000_000.0, 29_039_000_000.0, (0.0,) * 3, _shares(593_800_000.0, 594_075_498.0), (-.02, .02, .04), (.105, .09, .08), (.005, .015, .025), "Conditional Low pre-Norfolk Southern rail baseline. Current standalone cash, debt, shares, and five-year cash history reconcile; the signed transaction's expected 225M new shares and approximately $20B cash consideration remain separate from standalone intrinsic value.", "Invalidate if the Norfolk Southern transaction closes, terminates, or changes; or if standalone volumes, pricing, cash conversion, debt, claims, or shares changes materially.", "Current standalone bridge only. Restricted cash is excluded and the conditional merger consideration is not probability weighted or mixed into intrinsic value."),
    "CTAS": Policy("pre_unifirst_uniform_services_faded_fcff", "2026-05-31", 289_018_000.0, 2_436_600_000.0, (0.0,) * 3, _shares(406_197_000.0, 400_169_561.0), (.02, .07, .10), (.105, .09, .08), (.005, .015, .025), "Conditional Low pre-UniFirst uniform-services baseline. Current standalone cash, debt, shares, and five-year cash history reconcile; the pending approximately $5.5B cash-and-stock transaction remains under FTC review.", "Invalidate if the UniFirst transaction closes, terminates, or changes; or if standalone route cash conversion, debt, claims, or diluted shares changes materially.", "Current standalone bridge only. Restricted cash is excluded and the conditional $155 cash plus 0.7720-share consideration is kept separate."),
    "PAYX": Policy("client_funds_reserved_post_paycor_payroll_faded_fcff", "2026-05-31", 1_124_500_000.0, 4_556_100_000.0, (52_400_000.0,) * 3, _shares(360_000_000.0, 355_682_860.0), (.02, .07, .10), (.105, .09, .08), (.005, .015, .025), "Source-bounded post-Paycor payroll-services baseline. A complete combined fiscal year, corporate cash/securities, acquisition debt, client-fund shortfall, and shares reconcile; client funds are excluded from surplus cash.", "Invalidate if Paycor integration, payroll cash conversion, client funds/obligations, debt, claims, or diluted shares changes materially.", "$52.4M client-fund obligation excess over funds held. $4.8322B of client funds and $343.8M related restricted cash are not treated as issuer-owned surplus; $52.8M corporate restricted cash is also excluded."),
}


POINT_SPECS = {
    "PNR": (("CashAndCashEquivalentsAtCarryingValue", 91_800_000.0), ("LongTermDebt", 1_606_000_000.0)),
    "ROL": (("CashAndCashEquivalentsAtCarryingValue", 109_085_000.0), ("ShortTermBorrowings", 215_918_000.0), ("LongTermDebt", 487_107_000.0), ("PreferredStockValue", 0.0)),
    "AOS": (("CashAndCashEquivalentsAtCarryingValue", 181_300_000.0), ("LongTermDebtCurrent", 39_500_000.0), ("LongTermDebtNoncurrent", 598_000_000.0)),
    "SWK": (("CashAndCashEquivalentsAtCarryingValue", 592_400_000.0), ("LongTermDebt", 4_757_900_000.0), ("BusinessCombinationContingentConsiderationLiabilityNoncurrent", 101_400_000.0)),
    "UAL": (("CashAndCashEquivalentsAtCarryingValue", 10_166_000_000.0), ("ShortTermInvestments", 6_471_000_000.0), ("LongTermDebtAndCapitalLeaseObligations", 24_294_000_000.0), ("PreferredStockValue", 0.0)),
    "UNP": (("CashAndCashEquivalentsAtCarryingValue", 1_614_000_000.0), ("LongTermDebtAndCapitalLeaseObligations", 29_039_000_000.0), ("CommercialPaper", 0.0)),
    "CTAS": (("CashAndCashEquivalentsAtCarryingValue", 289_018_000.0), ("DebtLongtermAndShorttermCombinedAmount", 2_436_600_000.0), ("PreferredStockValue", 0.0)),
    "PAYX": (("CashAndCashEquivalentsAtCarryingValue", 1_088_200_000.0), ("MarketableSecuritiesCurrent", 36_300_000.0), ("LongTermDebt", 4_556_100_000.0), ("FundsHeldForClients", 4_832_200_000.0), ("ClientFundObligations", 4_884_600_000.0), ("RestrictedCashAndRestrictedCashEquivalentsIncludedInFundsHeldForClients", 343_800_000.0), ("RestrictedCashCurrent", 52_800_000.0)),
}


SHARE_STARTS = {"PNR": "2026-01-01", "ROL": "2026-01-01", "AOS": "2026-01-01", "SWK": "2026-01-04", "UAL": "2026-01-01", "UNP": "2026-01-01", "CTAS": "2025-06-01", "PAYX": "2025-06-01"}
SHARE_ENDS = {"PNR": "2026-06-30", "ROL": "2026-07-13", "AOS": "2026-07-28", "SWK": "2026-07-24", "UAL": "2026-07-09", "UNP": "2026-07-17", "CTAS": "2026-06-30", "PAYX": "2026-06-30"}
WEIGHTED_SHARES = {"PNR": 162_600_000.0, "ROL": 481_397_000.0, "AOS": 138_511_483.0, "SWK": 151_401_000.0, "UAL": 326_700_000.0, "UNP": 593_800_000.0, "CTAS": 406_197_000.0, "PAYX": 360_000_000.0}
CURRENT_SHARES = {"PNR": 159_637_950.0, "ROL": 481_145_404.0, "AOS": 135_908_573.0, "SWK": 151_016_641.0, "UAL": 324_583_772.0, "UNP": 594_075_498.0, "CTAS": 400_169_561.0, "PAYX": 355_682_860.0}
VALUATION_REVENUE_OVERRIDES = {"AOS": 3_836_700_000.0}


EVENTS = {
    "PNR": {"matter": "signed Taco acquisition", "reported_terms": {"purchase_price_usd": 1_425_000_000.0, "committed_bridge_usd": 1_400_000_000.0, "cutoff_status": "signed_not_closed"}},
    "ROL": {"matter": "recurring route acquisitions and ordinary claims", "reported_terms": {"management_legal_assessment": "not expected materially adverse"}},
    "AOS": {"matter": "Leonard Valve acquisition", "reported_terms": {"close_date": "2026-01-06", "purchase_price_net_cash_usd": 470_000_000.0, "purchase_accounting": "preliminary"}},
    "SWK": {"matter": "CAM divestiture", "reported_terms": {"close_date": "2026-04-06", "net_proceeds_usd": 1_814_700_000.0, "h1_pretax_income_usd": 22_800_000.0}},
    "UAL": {"matter": "aircraft and capacity-purchase commitments", "reported_terms": {"capacity_purchase_commitments_usd": 19_000_000_000.0}},
    "UNP": {"matter": "pending Norfolk Southern acquisition", "reported_terms": {"expected_new_shares": 225_000_000.0, "expected_cash_consideration_usd": 20_000_000_000.0, "cutoff_status": "signed_not_closed"}},
    "CTAS": {"matter": "pending UniFirst acquisition", "reported_terms": {"transaction_value_usd": 5_500_000_000.0, "cash_per_unifirst_share_usd": 155.0, "ctas_shares_per_unifirst_share": .7720, "cutoff_status": "pending_ftc_review"}},
    "PAYX": {"matter": "Paycor integration and client-fund state", "reported_terms": {"complete_combined_fiscal_year": True, "funds_held_usd": 4_832_200_000.0, "client_obligations_usd": 4_884_600_000.0}},
}


def _event_source(event_root: Path) -> dict[str, Any]:
    packet = Path(event_root) / "LUV"
    receipt = json.loads((packet / "source-receipt.json").read_text())
    document = packet / receipt["primary_document"]
    if receipt.get("schema_version") != "FINSIGHT-BATCH-20-EVENT-SOURCE-1" or receipt.get("valuation_date") != BATCH_20_VALUATION_DATE or receipt.get("filed", "") > BATCH_20_VALUATION_DATE or hashlib.sha256(document.read_bytes()).hexdigest() != receipt.get("document_sha256"):
        raise ValueError("LUV event source invalid")
    return {"source_kind": "sec_current_report", "accession": receipt["accession"], "filed": receipt["filed"], "form": receipt["form"], "period_end": receipt["report_date"], "url": receipt["url"], "document_sha256": receipt["document_sha256"], "reported_terms": receipt["reported_terms"], "treatment": receipt["treatment"], "reported_vs_estimated": "reported"}


def _fact_value(structural: dict[str, Any], *, name: str, expected: float, period_end: str) -> dict[str, Any]:
    rows = [row for row in structural["facts"] if row.get("local_name") == name and row.get("period_start") is None and row.get("period_end") == period_end and isinstance(row.get("value"), (int, float)) and float(row["value"]) == expected]
    if not rows:
        raise ValueError(f"{name}={expected} absent for {period_end}")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "period_end": period_end, "concept": row.get("qname"), "unit": row.get("unit"), "value": expected, "dimensions": row.get("dimensions", []), "reported_vs_estimated": "reported"}


def _aos_share_source(structural: dict[str, Any]) -> dict[str, Any]:
    expected = {"CommonClassAMember": 25_861_359.0, "CommonStockClassUndefinedMember": 110_047_214.0}
    found = {}
    sources = []
    for label, value in expected.items():
        rows = [row for row in structural["facts"] if row.get("local_name") == "EntityCommonStockSharesOutstanding" and row.get("period_start") is None and row.get("period_end") == "2026-07-28" and row.get("unit") == "xbrli:shares" and float(row.get("value", -1)) == value and any(label in str(member) for _, member in (row.get("dimensions") or []))]
        if not rows:
            raise ValueError(f"AOS {label} share fact absent")
        row = rows[0]
        found[label] = value
        sources.append({"concept": row.get("qname"), "value": value, "dimensions": row.get("dimensions")})
    return {"source_kind": "structural_xbrl_class_sum", "accession": structural["source_accession"], "period_end": "2026-07-28", "unit": "xbrli:shares", "components": found, "value": sum(found.values()), "sources": sources, "reported_vs_estimated": "reported_derived"}


def _bridge(ticker: str, structural: dict[str, Any], policy: Policy) -> list[dict[str, Any]]:
    rows = [_point(structural, name=name, expected=value, period_end=policy.period) for name, value in POINT_SPECS[ticker]]
    rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=WEIGHTED_SHARES[ticker], period_start=SHARE_STARTS[ticker], period_end=policy.period))
    rows.append(_aos_share_source(structural) if ticker == "AOS" else _share_point(structural, expected=CURRENT_SHARES[ticker], end=SHARE_ENDS[ticker]))
    rows.append(_no_preferred(structural, policy.period))
    if ticker == "SWK":
        rows.append(_fact_value(structural, name="AccrualForEnvironmentalLossContingencies", expected=249_800_000.0, period_end=policy.period))
    return rows


def _pnr_annual(normalizer, current_interest_ratio: float) -> tuple[dict[str, Any], ...]:
    rows = []
    for operating in normalizer.annual_series("operating_cash_flow", 5):
        capex = normalizer.annual_at_end("capital_expenditures", operating.end)
        revenue = normalizer.annual_at_end("revenue", operating.end)
        pretax = normalizer.annual_at_end("pretax_income", operating.end)
        tax = normalizer.annual_at_end("income_tax", operating.end)
        if capex is None or revenue is None or revenue.value <= 0:
            continue
        tax_rate = max(0.0, min(.30, tax.value / pretax.value)) if pretax is not None and tax is not None and pretax.value > 0 else .21
        interest = revenue.value * current_interest_ratio
        cash = cash_fcff_from_reported(operating_cash_flow=operating.value, capital_expenditures=capex.value, spectrum_investment=0.0, interest_expense=interest, tax_rate=tax_rate)
        rows.append({"period_end": operating.end, "operating_cash_flow": operating.as_dict(), "capital_expenditures": capex.as_dict(), "interest_expense": {"value": interest, "reported_vs_estimated": "estimated_from_current_interest_revenue_ratio", "ratio": current_interest_ratio}, "pretax_income": pretax.as_dict() if pretax else None, "income_tax": tax.as_dict() if tax else None, "revenue": revenue.as_dict(), "cash_fcff": cash, "formula": "OCF - capex + estimated after-tax interest; stale annual interest alias rejected"})
    return tuple(rows)


def _operating(ticker: str, filing: dict[str, Any], structural: dict[str, Any], submissions: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    policy = P[ticker]
    normalizer = _normalizer(submissions, facts)
    flows = {name: normalizer.ttm_flow(name) for name in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    try:
        tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    except ValueError:
        tax_rate, tax_sources = .21, ()
    if tax_rate < .05:
        tax_rate = .21
    current = cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]), capital_expenditures=float(flows["capital_expenditures"]["value"]), spectrum_investment=0.0, interest_expense=abs(float(flows["interest_expense"]["value"])), tax_rate=tax_rate)
    annual = _pnr_annual(normalizer, abs(float(flows["interest_expense"]["value"])) / float(flows["revenue"]["value"])) if ticker == "PNR" else _annual_cash_with_losses(normalizer)[2]
    if ticker == "SWK":
        annual = tuple(row for row in annual if row["period_end"] >= "2023-01-01")
    sources = [dict(row) for flow in flows.values() for row in flow.get("sources", [])]
    reported_revenue = float(flows["revenue"]["value"])
    valuation_revenue = VALUATION_REVENUE_OVERRIDES.get(ticker, reported_revenue)
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=reported_revenue, ttm_cash_fcff=current, ttm_period_end=policy.period, ttm_sources=sources, valuation_date=BATCH_20_VALUATION_DATE)
    cash_metric = profile.metric("cash_conversion_margin")
    growth_metric = profile.metric("revenue_growth")
    if not profile.full_history or cash_metric is None or growth_metric is None:
        raise ValueError(f"{ticker}: history unavailable")
    margins = tuple(max(.001, float(value)) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    growth = (max(-.10, min(policy.growth[0], growth_metric.low)), max(-.08, min(policy.growth[1], growth_metric.base)), max(0.0, min(policy.growth[2], growth_metric.high)))
    rows = []
    traces = {}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(valuation_revenue * margins[index], growth[index], policy.terminal[index], policy.wacc[index], policy.cash, policy.debt, 0.0, policy.claims[index], policy.shares[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "conditional_value_per_share": max(0.0, raw), "raw_value_per_share": raw, "starting_cash_fcff": state.cash_fcff, "cash_conversion_margin": margins[index], "growth": growth[index], "wacc": policy.wacc[index], "terminal_growth": policy.terminal[index], "cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims[index], "shares": policy.shares[index], "limited_liability_floor_applied": raw < 0.0})
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0.0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0.0:
        raise ValueError(f"{ticker}: invalid range")
    is_pass = ticker in PASS_TICKERS
    reasons = () if is_pass else ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="High" if is_pass else "Low", source_cap="High", reasons=reasons)
    public = profile.public_metadata()
    if not is_pass:
        public.update({"normalization_basis": "company_history_with_named_material_dependency", "assumption_source_mix": "reported_history_and_finsight_policy"})
    assumptions = {**public, "forecast_years": FORECAST_YEARS, "cash_conversion_margin": margins, "growth": growth, "wacc": policy.wacc, "terminal_growth": policy.terminal, "shares": policy.shares, "valuation_revenue": valuation_revenue, "valuation_revenue_basis": "reported TTM plus one filed H1 acquired-revenue amount" if ticker == "AOS" else "reported TTM", "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0.0 else "not applied", "calculator_calibration": "Calculator is calibrated to the exact faded-cash base; private bridge and event schedules remain fixed.", "invalidation": policy.invalidation}
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_20_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked annual and current cash conversion anchors the range."), BaselineAssumption("faded operating states", str({"growth": growth, "wacc": policy.wacc, "terminal": policy.terminal}), AssumptionClassification.FINSIGHT_ASSUMPTION, "Growth fades over eight years to a governed terminal state.")), warnings=(policy.warning, policy.invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link=f"/api/us-valuations/{ticker}/calculator")
    event_sources = [{"source_kind": "controlling_filing_narrative", "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "reported_vs_estimated": "reported_narrative", **EVENTS[ticker]}]
    if ticker == "AOS":
        event_sources.extend((_dimension_fact(structural, name="BusinessCombinationRecognizedIdentifiableAssetsAcquiredGoodwillAndLiabilitiesAssumedNet", expected=470_000_000.0, start=None, end=policy.period, member="LVCHoldcoLLCMember"), _dimension_fact(structural, name="BusinessCombinationProFormaInformationRevenueOfAcquireeSinceAcquisitionDateActual", expected=31_800_000.0, start="2026-01-01", end=policy.period, member="LVCHoldcoLLCMember")))
    if ticker == "SWK":
        event_sources.extend((_structural_flow(structural, name="ProceedsFromDivestitureOfBusinessesNetOfCashDivested", start="2026-01-04", end=policy.period, expected=1_814_700_000.0), _structural_flow(structural, name="GainLossOnSaleOfBusiness", start="2026-01-04", end=policy.period, expected=270_600_000.0)))
    if ticker == "UAL":
        event_sources.append(_dimension_fact(structural, name="UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", expected=19_000_000_000.0, start=None, end=policy.period, member="AirlineCapacityPurchaseArrangementsMember"))
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_20_HISTORY_VERSION, "availability_type": "available" if is_pass else "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": reported_revenue, "valuation_revenue": valuation_revenue, "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": flows["interest_expense"]["value"], "ttm_cash_fcff": current}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": list(annual), "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_sources": _bridge(ticker, structural, policy), "event_sources": event_sources, "bridge_reconciliation": {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims, "other_equity_claim_formula": policy.claim_formula, "shares": policy.shares, "operating_liability_treatment": "Ordinary operating liabilities and forward commitments remain inside cash conversion and are not deducted again."}, "model_trace": {"forecast_years": FORECAST_YEARS, "states": traces}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": policy.warning, "baseline": baseline.as_private_dict()}


@dataclass(frozen=True)
class EquityPolicy:
    method: str
    period: str
    beginning_equity: float
    ending_equity: float
    weighted_shares: float
    current_shares: float
    current_start: str
    prior_start: str
    prior_end: str
    current_earnings: float
    prior_earnings: float
    current_dividends: float
    cost_of_equity: tuple[float, float, float]
    terminal_roe: tuple[float, float, float]
    terminal_growth: tuple[float, float, float]
    warning: str
    invalidation: str


EQUITY = {
    "SNA": EquityPolicy("mixed_tools_finance_residual_income_equity_earnings", "2026-07-04", 5_931_800_000.0, 6_041_300_000.0, 52_611_800.0, 51_727_124.0, "2026-01-04", "2024-12-29", "2025-06-28", 507_600_000.0, 490_800_000.0, 253_200_000.0, (.12, .10, .085), (.12, .20, .28), (.01, .02, .025), "Conditional Low mixed tools/Financial Services residual-income baseline. Parent earnings and common equity avoid double-counting finance receivables and funding, while credit losses, customer financing, and capital allocation remain material.", "Invalidate if tool demand, finance receivables or credit losses, common equity, payout, funding, NCI, or diluted shares changes materially."),
    "LUV": EquityPolicy("airline_cycle_residual_income_equity_earnings", "2026-06-30", 7_981_000_000.0, 7_082_000_000.0, 498_000_000.0, 489_208_201.0, "2026-01-01", "2025-01-01", "2025-06-30", 460_000_000.0, 64_000_000.0, 181_000_000.0, (.14, .115, .10), (.08, .12, .18), (0.0, .01, .02), "Conditional Low airline-cycle residual-income baseline. Common equity and normalized earnings produce a finite range despite negative current post-capex cash, while Boeing deliveries, $14.8B aircraft commitments, fleet reinvestment, fuel, and turnaround execution remain material.", "Invalidate if normalized airline earnings, fleet commitments, Boeing delivery timing, fuel, debt/liquidity, payout, or diluted shares changes materially."),
}


def _equity_result(ticker: str, filing: dict[str, Any], structural: dict[str, Any], facts: dict[str, Any], event_root: Path) -> dict[str, Any]:
    policy = EQUITY[ticker]
    gaap = facts["facts"]["us-gaap"]
    annual = annual_facts(gaap, concepts=("NetIncomeLoss",), unit="USD", valuation_date=BATCH_20_VALUATION_DATE)
    observations = []
    for year in (2021, 2022, 2023, 2024, 2025):
        fact = annual[year]
        observations.append(HistoryObservation("annual", fact.period_end, fact.fiscal_year, fact.value, "USD", "reported parent-attributable earnings", (_history_source(fact),)))
    latest = observations[-1].value
    ttm = latest + policy.current_earnings - policy.prior_earnings
    observations.append(HistoryObservation("operating_ttm", policy.period, None, ttm, "USD", "latest FY + current comparable period - prior comparable period", (observations[-1].sources[0], _structural_flow(structural, name="NetIncomeLoss", start=policy.current_start, end=policy.period, expected=policy.current_earnings), _structural_flow(structural, name="NetIncomeLoss", start=policy.prior_start, end=policy.prior_end, expected=policy.prior_earnings))))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "consolidated_equity_residual_income", BATCH_20_VALUATION_DATE, tuple(row.period_end for row in observations if row.period_role == "annual"), (metric,), True, "reported_and_company_history")
    shares = _shares(policy.weighted_shares, policy.current_shares)
    earnings = (metric.low, metric.base, metric.high)
    average_equity = (policy.beginning_equity + policy.ending_equity) / 2.0
    payout = min(1.0, policy.current_dividends * 2.0 / ttm)
    rows = []
    traces = {}
    multiples = []
    for index, name in enumerate(("bear", "base", "bull")):
        trace = residual_income_valuation(book_value_per_share=policy.ending_equity / shares[index], current_roe=earnings[index] / average_equity, cost_of_equity=policy.cost_of_equity[index], current_payout_ratio=payout, terminal_roe=policy.terminal_roe[index], terminal_growth=policy.terminal_growth[index], years=5)
        raw = float(trace["intrinsic_value"])
        multiple = raw * shares[index] / earnings[index]
        rows.append({"name": name, "conditional_value_per_share": max(0.0, raw), "raw_value_per_share": raw, "normalized_common_earnings": earnings[index], "book_value_per_share": policy.ending_equity / shares[index], "current_roe": earnings[index] / average_equity, "current_payout_ratio": payout, "cost_of_equity": policy.cost_of_equity[index], "terminal_roe": policy.terminal_roe[index], "terminal_growth": policy.terminal_growth[index], "earnings_multiple": multiple, "shares": shares[index], "limited_liability_floor_applied": raw < 0.0})
        traces[name] = trace
        multiples.append(multiple)
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0.0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0.0:
        raise ValueError(f"{ticker}: invalid equity range")
    reasons = ("CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    assumptions = {**profile.public_metadata(), "normalization_basis": "reported_common_equity_and_history_residual_income", "assumption_source_mix": "reported_common_equity_earnings_dividends_and_finsight_policy", "normalized_common_earnings": earnings, "earnings_multiples": tuple(multiples), "shares": shares, "book_equity": policy.ending_equity, "average_common_equity": average_equity, "current_payout_ratio": payout, "cost_of_equity": policy.cost_of_equity, "terminal_roe": policy.terminal_roe, "terminal_growth": policy.terminal_growth, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0.0 else "not applied", "calculator_calibration": "Calculator varies normalized earnings and the residual-income-implied multiple around the base.", "invalidation": policy.invalidation}
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_20_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported common equity", policy.ending_equity, AssumptionClassification.REPORTED, "Current parent equity anchors residual income."), BaselineAssumption("company earnings history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Parent earnings history supplies the ROE range.")), warnings=(policy.warning, policy.invalidation), confidence_reasons=reasons, calculator_link=f"/api/us-valuations/{ticker}/calculator")
    context = [_point(structural, name="StockholdersEquity", expected=policy.ending_equity, period_end=policy.period), _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=policy.weighted_shares, period_start=policy.current_start, period_end=policy.period), _share_point(structural, expected=policy.current_shares, end={"SNA": "2026-07-17", "LUV": "2026-07-22"}[ticker]), _no_preferred(structural, policy.period)]
    dividend_name = "PaymentsOfDividends" if ticker == "SNA" else "PaymentsOfDividends"
    context.append(_structural_flow(structural, name=dividend_name, start=policy.current_start, end=policy.period, expected=policy.current_dividends))
    events = [{"source_kind": "controlling_filing_narrative", "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "matter": "tools and Financial Services economics" if ticker == "SNA" else "airline fleet and Boeing commitment cycle", "reported_terms": {"finance_receivables_and_credit_losses_material": True} if ticker == "SNA" else {"aircraft_purchase_commitments_usd": 14_800_000_000.0}, "reported_vs_estimated": "reported_narrative"}]
    if ticker == "LUV":
        events.extend((_dimension_fact(structural, name="UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", expected=14_800_000_000.0, start=None, end=policy.period, member="AircraftMember"), _event_source(event_root)))
    if ticker == "SNA":
        context.append(_point(structural, name="MinorityInterest", expected=25_000_000.0, period_end=policy.period))
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_20_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_common_earnings": ttm, "beginning_common_equity": policy.beginning_equity, "ending_common_equity": policy.ending_equity, "current_period_common_dividends": policy.current_dividends}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "company_history_profile": profile.as_private_dict(), "equity_model_context": context, "event_sources": events, "residual_income_trace": {"states": traces}, "bridge_treatment": "Equity-level model; finance/fleet funding, debt, and NCI remain inside parent earnings/equity and are not EV-bridged. Parent-attributable earnings already exclude NCI.", "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": policy.warning, "baseline": baseline.as_private_dict()}


def build_batch_20_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_20_TICKERS:
        raise ValueError(ticker)
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural["source_accession"] != filing["accession"]:
        raise ValueError(f"{ticker}: source mismatch")
    if ticker in EQUITY_EARNINGS_TICKERS:
        return _equity_result(ticker, filing, structural, facts, event_root)
    if filing["period_end"] != P[ticker].period:
        raise ValueError(f"{ticker}: period mismatch")
    return _operating(ticker, filing, structural, submissions, facts)


if set(P) | set(EQUITY) != set(BATCH_20_TICKERS):
    raise RuntimeError("Batch 20 denominator mismatch")
