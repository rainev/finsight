"""History-backed practical baselines for controlled Universe Reset Batch 19."""

from __future__ import annotations

from copy import deepcopy
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
from .batch_19 import BATCH_19_TICKERS, BATCH_19_VALUATION_DATE
from .equity_fact_selection import annual_facts
from .history import (
    HISTORY_POLICY_VERSION,
    CompanyHistoryProfile,
    HistoryObservation,
    build_cash_fcff_history_profile,
    summarize_history_metric,
)
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_19_HISTORY_VERSION = "BATCH-19-INDUSTRIALS-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset({"ITW", "J", "MAS", "NDSN"})
CONDITIONAL_TICKERS = frozenset({"GE", "HUBB", "MMM", "PCAR", "PH", "DE"})
WITHHELD_TICKERS = frozenset()
EQUITY_EARNINGS_TICKERS = frozenset({"GE", "PCAR", "DE"})


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
    enterprise_overlay: tuple[float, float, float]
    warning: str
    invalidation: str
    claim_formula: str


P = {
    "HUBB": Policy(
        "post_nsi_electrical_products_faded_fcff",
        "2026-06-30",
        394_700_000.0,
        5_372_600_000.0,
        (11_100_000.0,) * 3,
        _shares(53_200_000.0, 52_832_571.0),
        (-.02, .04, .07),
        (.11, .095, .085),
        (.005, .015, .025),
        (0.0,) * 3,
        "Conditional Low post-NSI electrical-products baseline. The June acquisition added only a short reported operating period and materially increased debt; filed pro-forma revenue helps bound scale but not acquired cash conversion.",
        "Invalidate if NSI integration, acquired cash conversion, debt, securities, NCI, claims, or diluted shares changes materially.",
        "$11.1M reported NCI. Cash and short-term investments are counted once; current plus noncurrent debt includes the acquisition-funded increase.",
    ),
    "ITW": Policy(
        "post_refinancing_diversified_industrial_faded_fcff",
        "2026-06-30",
        2_328_000_000.0,
        11_194_000_000.0,
        (1_000_000.0,) * 3,
        _shares(288_100_000.0, 284_800_000.0),
        (-.02, .02, .04),
        (.105, .09, .08),
        (.005, .015, .025),
        (0.0,) * 3,
        "Source-bounded diversified-industrial baseline. Five-year cash history and the cutoff bridge include the August note principal and estimated net proceeds once; intended commercial-paper repayment is not assumed completed.",
        "Invalidate if note proceeds or repayment, industrial cash conversion, debt, claims, or diluted shares changes materially.",
        "$1M reported NCI. The cutoff bridge adds $1.5B issued principal and $1.489B estimated net proceeds once, leaving an $11M conservative net-debt increase before repayment evidence.",
    ),
    "J": Policy(
        "post_amentum_engineering_services_faded_fcff",
        "2026-06-26",
        1_172_914_000.0,
        3_579_376_000.0,
        (0.0,) * 3,
        _shares(118_486_000.0, 117_038_611.0),
        (-.04, .04, .07),
        (.11, .095, .085),
        (.005, .015, .025),
        (0.0,) * 3,
        "Source-bounded continuing engineering-services baseline. The Amentum separation is reflected in continuing operations, the PA Consulting employee interest was repurchased, and current cash, debt, shares, and remaining NCI reconcile.",
        "Invalidate if continuing-company scope, PA Consulting cash conversion, debt, NCI, pension obligations, claims, or diluted shares changes materially.",
        "Redeemable PA Consulting NCI was eliminated by the reported repurchase. The remaining reported NCI balance is negative and is not invented as a positive claim; no preferred claim is reported.",
    ),
    "MAS": Policy(
        "building_products_cycle_faded_fcff",
        "2026-06-30",
        548_000_000.0,
        3_247_000_000.0,
        (247_000_000.0,) * 3,
        _shares(201_000_000.0, 197_187_430.0),
        (-.05, -.02, .01),
        (.11, .095, .085),
        (0.0, .01, .02),
        (0.0,) * 3,
        "Source-bounded building-products baseline. Five-year cash history, current cash, notes, long-term debt, NCI, preferred absence, and shares reconcile; the housing cycle is handled through the range rather than a special event assumption.",
        "Invalidate if repair/remodel demand, cash conversion, debt, NCI, claims, or diluted shares changes materially.",
        "$247M reported NCI; $2M current notes and $3.245B noncurrent debt are counted once. Negative parent book equity does not replace the operating cash model.",
    ),
    "MMM": Policy(
        "reported_operations_legal_settlement_adjusted_faded_fcff",
        "2026-06-30",
        3_330_000_000.0,
        12_551_000_000.0,
        (9_809_000_000.0,) * 3,
        _shares(527_600_000.0, 515_722_417.0),
        (-.08, -.02, .02),
        (.12, .105, .095),
        (0.0, .01, .02),
        (0.0,) * 3,
        "Conditional Low 3M reported-operations baseline. Current cash, securities, debt, shares, and $9.756B of recorded environmental, Combat Arms, and respirator liabilities are deducted once; unquantified PFAS and personal-injury tails remain outside the range.",
        "Invalidate if settlement schedules, PFAS or personal-injury exposure, insurance recovery, cash conversion, debt, NCI, or diluted shares changes materially.",
        "$7.4B environmental accrual + $1.9B Combat Arms accrual + $456M respirator/asbestos accrual + $53M NCI. No unquantified excess claim or insurance recovery is replaced with zero.",
    ),
    "NDSN": Policy(
        "precision_technology_faded_fcff",
        "2026-04-30",
        102_017_000.0,
        1_904_814_000.0,
        (0.0,) * 3,
        _shares(56_113_000.0, 55_717_948.0),
        (-.02, .04, .06),
        (.11, .095, .085),
        (.005, .015, .025),
        (0.0,) * 3,
        "Source-bounded precision-technology baseline. Five-year cash history, current debt and finance leases, shares, and ordinary claims reconcile; the new $1.2B commercial-paper program is capacity, not issued debt.",
        "Invalidate if commercial paper is issued, precision-market cash conversion, acquisitions, debt/leases, claims, or diluted shares changes materially.",
        "$1.886356B current/noncurrent debt plus $18.458M finance leases. The $1.2B authorized commercial-paper ceiling is not substituted as outstanding debt or cash.",
    ),
    "PH": Policy(
        "post_filtration_group_cost_overlay_faded_fcff",
        "2026-03-31",
        476_000_000.0,
        16_619_000_000.0,
        (1_508_000_000.0,) * 3,
        _shares(128_200_000.0, 126_086_389.0),
        (-.02, .05, .08),
        (.11, .095, .085),
        (.005, .015, .025),
        (9_250_000_000.0,) * 3,
        "Conditional Low post-Filtration Group baseline. The cutoff state adds the reported $9.25B acquired enterprise-value cost, $7.75B term loans, and a $1.5B residual purchase-funding reserve, but does not invent acquired cash flow or synergies.",
        "Invalidate when Filtration Group purchase accounting, final funding, acquired cash flow, integration costs, debt, NCI, claims, or diluted shares is filed or changes materially.",
        "$8M reported NCI plus $1.5B purchase funding not covered by the two reported term loans. The $9.25B cost overlay is a conditional acquisition-cost proxy, not an independent intrinsic valuation of Filtration Group.",
    ),
}


POINT_SPECS = {
    "HUBB": (("CashAndCashEquivalentsAtCarryingValue", 378_600_000.0), ("ShortTermInvestments", 16_100_000.0), ("DebtCurrent", 568_700_000.0), ("LongTermDebtNoncurrent", 4_803_900_000.0), ("MinorityInterest", 11_100_000.0)),
    "ITW": (("CashAndCashEquivalentsAtCarryingValue", 839_000_000.0), ("DebtLongtermAndShorttermCombinedAmount", 9_694_000_000.0), ("MinorityInterest", 1_000_000.0)),
    "J": (("CashAndCashEquivalentsAtCarryingValue", 1_172_914_000.0), ("LongTermDebtNoncurrent", 3_579_376_000.0), ("MinorityInterest", -13_841_000.0), ("PreferredStockValue", 0.0)),
    "MAS": (("CashAndCashEquivalentsAtCarryingValue", 548_000_000.0), ("NotesPayableCurrent", 2_000_000.0), ("LongTermDebtNoncurrent", 3_245_000_000.0), ("MinorityInterest", 247_000_000.0), ("PreferredStockValue", 0.0)),
    "MMM": (("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", 2_955_000_000.0), ("DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent", 375_000_000.0), ("DebtCurrent", 1_647_000_000.0), ("LongTermDebtNoncurrent", 10_904_000_000.0), ("MinorityInterest", 53_000_000.0)),
    "NDSN": (("CashAndCashEquivalentsAtCarryingValue", 102_017_000.0), ("LongTermDebtCurrent", 50_000_000.0), ("LongTermDebtNoncurrent", 1_836_356_000.0), ("FinanceLeaseLiabilityCurrent", 9_697_000.0), ("FinanceLeaseLiabilityNoncurrent", 8_761_000.0)),
    "PH": (("CashAndCashEquivalentsAtCarryingValue", 476_000_000.0), ("CommercialPaper", 2_100_000_000.0), ("LongTermDebtAndCapitalLeaseObligations", 6_769_000_000.0), ("MinorityInterest", 8_000_000.0), ("PreferredStockValue", 0.0)),
}


SHARE_STARTS = {"HUBB": "2026-01-01", "ITW": "2026-01-01", "J": "2025-09-27", "MAS": "2026-01-01", "MMM": "2026-01-01", "NDSN": "2025-11-01", "PH": "2025-07-01"}
SHARE_ENDS = {"HUBB": "2026-07-23", "ITW": "2026-06-30", "J": "2026-07-24", "MAS": "2026-06-30", "MMM": "2026-06-30", "NDSN": "2026-05-19", "PH": "2026-03-31"}
WEIGHTED_SHARES = {ticker: P[ticker].shares[0] for ticker in P}
CURRENT_SHARES = {ticker: P[ticker].shares[2] for ticker in P}
ANNUAL_MIN_END = {"J": "2022-01-01", "MMM": "2022-01-01"}
MARGIN_OVERRIDES: dict[str, tuple[float, float, float]] = {}
VALUATION_REVENUE_OVERRIDES = {"HUBB": 6_489_300_000.0}


EVENT_ACCESSIONS = {
    "ITW": ("0001193125-26-349149", "0001193125-26-346824"),
    "NDSN": ("0000072331-26-000034",),
    "PH": ("0001193125-26-349148",),
    "DE": ("0001104659-26-083910", "0001104659-26-083165"),
}


EVENTS = {
    "HUBB": {"matter": "NSI Industries acquisition", "reported_terms": {"close_date": "2026-06-09", "h1_pro_forma_revenue_usd": 3_475_100_000.0}},
    "ITW": {"matter": "August notes issuance and intended commercial-paper repayment", "reported_terms": {"event_source_required": True}},
    "J": {"matter": "Amentum separation and PA Consulting employee-interest repurchase", "reported_terms": {"redeemable_nci_after_repurchase_usd": 0.0}},
    "MAS": {"matter": "ordinary building-products cycle", "reported_terms": {"preferred_shares_outstanding": 0}},
    "MMM": {"matter": "environmental, PFAS, Combat Arms, and respirator proceedings", "reported_terms": {"recorded_claims_usd": 9_756_000_000.0, "unquantified_tail": True}},
    "NDSN": {"matter": "commercial-paper program authorization", "reported_terms": {"event_source_required": True}},
    "PH": {"matter": "Filtration Group acquisition close and term-loan funding", "reported_terms": {"event_source_required": True}},
}


def _event_sources(event_root: Path, ticker: str) -> list[dict[str, Any]]:
    rows = []
    for accession in EVENT_ACCESSIONS.get(ticker, ()):
        packet = Path(event_root) / ticker / accession
        receipt = json.loads((packet / "source-receipt.json").read_text())
        document = packet / receipt["primary_document"]
        if (
            receipt.get("schema_version") != "FINSIGHT-BATCH-19-EVENT-SOURCE-1"
            or receipt.get("valuation_date") != BATCH_19_VALUATION_DATE
            or receipt.get("accession") != accession
            or receipt.get("filed", "") > BATCH_19_VALUATION_DATE
            or hashlib.sha256(document.read_bytes()).hexdigest() != receipt.get("document_sha256")
        ):
            raise ValueError(f"{ticker}: event source invalid")
        rows.append({
            "source_kind": "sec_current_report_or_prospectus",
            "accession": receipt["accession"],
            "filed": receipt["filed"],
            "form": receipt["form"],
            "period_end": receipt["report_date"],
            "url": receipt["url"],
            "document_sha256": receipt["document_sha256"],
            "reported_terms": receipt["reported_terms"],
            "treatment": receipt["treatment"],
            "reported_vs_estimated": "reported",
        })
    return rows


def _fact_value(structural: dict[str, Any], *, name: str, expected: float, period_end: str) -> dict[str, Any]:
    rows = [
        row for row in structural["facts"]
        if row.get("local_name") == name
        and row.get("period_start") is None
        and row.get("period_end") == period_end
        and row.get("unit") == "USD"
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) == expected
    ]
    if not rows:
        raise ValueError(f"{name}={expected} absent for {period_end}")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "period_end": period_end, "concept": row.get("qname"), "unit": row.get("unit"), "value": expected, "dimensions": row.get("dimensions", []), "reported_vs_estimated": "reported"}


def _no_preferred_excluding_redeemable_nci(structural: dict[str, Any], period: str) -> dict[str, Any]:
    names = ("PreferredStockValue", "PreferredStockValueOutstanding", "PreferredStockNoParValue", "PreferredStockSharesIssued")
    rows = [
        row for row in structural["facts"]
        if row.get("local_name") in names
        and row.get("period_start") is None
        and row.get("period_end") == period
        and not row.get("dimensions")
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) != 0.0
    ]
    if rows:
        raise ValueError("unreconciled preferred equity")
    return {"source_kind": "controlling_filing_structure", "accession": structural["source_accession"], "period_end": period, "field": "preferred_equity", "reported_vs_estimated": "source_proven_absent_or_zero", "checked_concepts": list(names), "separate_temporary_equity_treatment": "Redeemable NCI is recorded separately and remains inside parent earnings/common equity treatment."}


def _bridge(ticker: str, structural: dict[str, Any], policy: Policy) -> list[dict[str, Any]]:
    rows = [_point(structural, name=name, expected=value, period_end=policy.period) for name, value in POINT_SPECS[ticker]]
    rows.extend((
        _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=WEIGHTED_SHARES[ticker], period_start=SHARE_STARTS[ticker], period_end=policy.period),
        _share_point(structural, expected=CURRENT_SHARES[ticker], end=SHARE_ENDS[ticker]),
        _no_preferred(structural, policy.period),
    ))
    if ticker == "MMM":
        rows.extend((
            _fact_value(structural, name="LossContingencyAccrualAtCarryingValue", expected=7_400_000_000.0, period_end=policy.period),
            _fact_value(structural, name="LossContingencyAccrualAtCarryingValue", expected=1_900_000_000.0, period_end=policy.period),
            _fact_value(structural, name="LossContingencyAccrualAtCarryingValue", expected=456_000_000.0, period_end=policy.period),
        ))
    return rows


def _operating(ticker: str, filing: dict[str, Any], structural: dict[str, Any], submissions: dict[str, Any], facts: dict[str, Any], event_root: Path) -> dict[str, Any]:
    policy = P[ticker]
    normalizer = _normalizer(submissions, facts)
    flows = {name: normalizer.ttm_flow(name) for name in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    try:
        tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    except ValueError:
        tax_rate, tax_sources = .21, ()
    if tax_rate < .05:
        tax_rate = .21
    current = cash_fcff_from_reported(
        operating_cash_flow=float(flows["operating_cash_flow"]["value"]),
        capital_expenditures=float(flows["capital_expenditures"]["value"]),
        spectrum_investment=0.0,
        interest_expense=abs(float(flows["interest_expense"]["value"])),
        tax_rate=tax_rate,
    )
    annual = _annual_cash_with_losses(normalizer)[2]
    if ticker in ANNUAL_MIN_END:
        annual = [row for row in annual if row["period_end"] >= ANNUAL_MIN_END[ticker]]
    sources = [dict(row) for flow in flows.values() for row in flow.get("sources", [])]
    reported_revenue = float(flows["revenue"]["value"])
    valuation_revenue = VALUATION_REVENUE_OVERRIDES.get(ticker, reported_revenue)
    profile = build_cash_fcff_history_profile(
        annual_cash_states=annual,
        ttm_revenue=reported_revenue,
        ttm_cash_fcff=current,
        ttm_period_end=policy.period,
        ttm_sources=sources,
        valuation_date=BATCH_19_VALUATION_DATE,
    )
    cash_metric = profile.metric("cash_conversion_margin")
    growth_metric = profile.metric("revenue_growth")
    if not profile.full_history or cash_metric is None or growth_metric is None:
        raise ValueError(f"{ticker}: history unavailable")
    margins = MARGIN_OVERRIDES.get(ticker, (cash_metric.low, cash_metric.base, cash_metric.high))
    margins = tuple(max(.001, float(value)) for value in margins)
    growth = (
        max(-.10, min(policy.growth[0], growth_metric.low)),
        max(-.08, min(policy.growth[1], growth_metric.base)),
        max(0.0, min(policy.growth[2], growth_metric.high)),
    )
    rows = []
    traces = {}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(
            valuation_revenue * margins[index],
            growth[index],
            policy.terminal[index],
            policy.wacc[index],
            policy.cash,
            policy.debt,
            0.0,
            policy.claims[index],
            policy.shares[index],
        )
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw_before_overlay = float(trace["intrinsic_value_per_share"])
        raw = raw_before_overlay + policy.enterprise_overlay[index] / policy.shares[index]
        rows.append({
            "name": name,
            "conditional_value_per_share": max(0.0, raw),
            "raw_value_per_share": raw,
            "raw_value_before_enterprise_overlay_per_share": raw_before_overlay,
            "starting_cash_fcff": state.cash_fcff,
            "cash_conversion_margin": margins[index],
            "growth": growth[index],
            "wacc": policy.wacc[index],
            "terminal_growth": policy.terminal[index],
            "cash_and_investments": policy.cash,
            "debt_and_finance_leases": policy.debt,
            "other_equity_claims": policy.claims[index],
            "enterprise_value_overlay": policy.enterprise_overlay[index],
            "shares": policy.shares[index],
            "limited_liability_floor_applied": raw < 0.0,
        })
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0.0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0.0:
        raise ValueError(f"{ticker}: invalid range")
    is_pass = ticker in PASS_TICKERS
    reasons = () if is_pass else ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(
        accounting_low=scenario["base"],
        accounting_base=scenario["base"],
        accounting_high=scenario["base"],
        scenario_low=scenario["low"],
        scenario_base=scenario["base"],
        scenario_high=scenario["high"],
        model_cap="High" if is_pass else "Low",
        source_cap="High",
        reasons=reasons,
    )
    public = profile.public_metadata()
    if not is_pass:
        public.update({"normalization_basis": "company_history_with_named_material_dependency", "assumption_source_mix": "reported_history_and_finsight_policy"})
    assumptions = {
        **public,
        "forecast_years": FORECAST_YEARS,
        "cash_conversion_margin": margins,
        "growth": growth,
        "wacc": policy.wacc,
        "terminal_growth": policy.terminal,
        "shares": policy.shares,
        "enterprise_value_overlay": policy.enterprise_overlay,
        "valuation_revenue": valuation_revenue,
        "valuation_revenue_basis": "reported TTM plus annualized filed pro-forma acquisition increment" if ticker == "HUBB" else "reported TTM",
        "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0.0 else "not applied",
        "calculator_calibration": "Calculator is calibrated to the exact faded-cash base; private bridge and event schedules remain fixed.",
        "invalidation": policy.invalidation,
    }
    baseline = BaselineValuation(
        ticker=ticker,
        method=policy.method,
        method_version=BATCH_19_HISTORY_VERSION,
        low=scenario["low"],
        base=scenario["base"],
        high=scenario["high"],
        confidence=reliability.label,
        availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL,
        key_assumptions=(
            BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked annual and current cash conversion anchors the range."),
            BaselineAssumption("faded operating states", str({"growth": growth, "wacc": policy.wacc, "terminal": policy.terminal}), AssumptionClassification.FINSIGHT_ASSUMPTION, "Growth fades over eight years to a governed terminal state."),
        ),
        warnings=(policy.warning, policy.invalidation),
        confidence_reasons=tuple(reliability.reasons),
        calculator_link=f"/api/us-valuations/{ticker}/calculator",
    )
    narrative = {"source_kind": "controlling_filing_narrative", "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "reported_vs_estimated": "reported_narrative", **EVENTS[ticker]}
    event_sources = [narrative, *_event_sources(event_root, ticker)]
    if ticker == "HUBB":
        event_sources.extend((
            _structural_flow(structural, name="RevenueFromContractWithCustomerExcludingAssessedTax", start="2026-01-01", end=policy.period, expected=3_228_500_000.0),
            _dimension_fact(structural, name="BusinessAcquisitionsProFormaRevenue", expected=3_475_100_000.0, start="2026-01-01", end=policy.period, member="A2026AcquisitionsMember"),
        ))
    return {
        "ticker": ticker,
        "method": policy.method,
        "model_version": BATCH_19_HISTORY_VERSION,
        "availability_type": "available" if is_pass else "conditional_estimate",
        "scenario_rows": rows,
        "scenario_range": scenario,
        "reported_inputs": {"ttm_revenue": reported_revenue, "valuation_revenue": valuation_revenue, "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": flows["interest_expense"]["value"], "ttm_cash_fcff": current},
        "governed_assumptions": assumptions,
        "history_reliability": reliability.as_dict(),
        "source_ledger": {
            "controlling_filing": filing,
            "flow_sources": flows,
            "tax_rate_sources": list(tax_sources),
            "company_history_profile": profile.as_private_dict(),
            "bridge_sources": _bridge(ticker, structural, policy),
            "event_sources": event_sources,
            "bridge_reconciliation": {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims, "enterprise_value_overlay": policy.enterprise_overlay, "other_equity_claim_formula": policy.claim_formula, "shares": policy.shares, "operating_liability_treatment": "Ordinary operating liabilities remain inside cash conversion and are not deducted again."},
            "model_trace": {"forecast_years": FORECAST_YEARS, "states": traces},
            "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False},
        },
        "warning": policy.warning,
        "baseline": baseline.as_private_dict(),
    }


@dataclass(frozen=True)
class EquityPolicy:
    method: str
    period: str
    years: tuple[int, ...]
    annual_concept: str
    beginning_equity: float
    ending_equity: float
    weighted_shares: float
    current_shares: float
    current_start: str
    prior_start: str
    current_earnings: float
    prior_earnings: float
    current_dividends: float
    cost_of_equity: tuple[float, float, float]
    terminal_roe: tuple[float, float, float]
    terminal_growth: tuple[float, float, float]
    warning: str
    invalidation: str


EQUITY = {
    "GE": EquityPolicy("mixed_aerospace_runoff_insurance_residual_income_equity_earnings", "2026-06-30", (2023, 2024, 2025), "IncomeLossFromContinuingOperationsIncludingPortionAttributableToNoncontrollingInterest", 18_677_000_000.0, 17_640_000_000.0, 1_050_000_000.0, 1_037_562_513.0, "2026-01-01", "2025-01-01", 4_338_000_000.0, 3_975_000_000.0, 873_000_000.0, (.12, .10, .085), (.15, .25, .35), (.01, .02, .025), "Conditional Low mixed GE Aerospace/run-off-insurance residual-income baseline. Retrospectively presented continuing earnings and parent equity avoid treating insurance securities as surplus industrial cash, while insurance capital, legacy liabilities, and short post-separation history remain material.", "Invalidate if aerospace earnings, run-off insurance capital or liabilities, separation scope, common equity, payout, claims, or diluted shares changes materially."),
    "PCAR": EquityPolicy("mixed_truck_captive_finance_residual_income_equity_earnings", "2026-06-30", (2021, 2022, 2023, 2024, 2025), "NetIncomeLoss", 19_264_000_000.0, 20_321_300_000.0, 527_500_000.0, 526_364_953.0, "2026-01-01", "2025-01-01", 1_357_300_000.0, 1_228_900_000.0, 1_093_700_000.0, (.12, .10, .085), (.12, .20, .28), (.01, .02, .025), "Conditional Low mixed truck/captive-finance residual-income baseline. Common equity and earnings avoid double-counting Financial Services receivables and debt; truck cycle, credit losses, funding, and capital allocation remain material.", "Invalidate if truck-cycle earnings, finance receivables or credit losses, common equity, payout, funding, or diluted shares changes materially."),
    "DE": EquityPolicy("mixed_agriculture_captive_finance_residual_income_equity_earnings", "2026-05-03", (2021, 2022, 2023, 2024, 2025), "NetIncomeLoss", 25_950_000_000.0, 27_404_267_000.0, 270_900_000.0, 269_937_425.0, "2025-11-03", "2024-10-28", 2_429_000_000.0, 2_673_000_000.0, 878_000_000.0, (.12, .10, .085), (.12, .20, .28), (.01, .02, .025), "Conditional Low mixed agriculture/captive-finance residual-income baseline. Common equity and earnings avoid double-counting John Deere Financial debt; the cutoff equity bridge deducts the bounded July note issuance cost once.", "Invalidate if equipment-cycle earnings, finance receivables or credit losses, common equity, payout, funding, note terms, or diluted shares changes materially."),
}


def _equity_result(ticker: str, filing: dict[str, Any], structural: dict[str, Any], facts: dict[str, Any], event_root: Path) -> dict[str, Any]:
    policy = EQUITY[ticker]
    gaap = facts["facts"]["us-gaap"]
    annual = annual_facts(gaap, concepts=(policy.annual_concept,), unit="USD", valuation_date=BATCH_19_VALUATION_DATE)
    nci_annual = annual_facts(gaap, concepts=("NetIncomeLossAttributableToNoncontrollingInterest",), unit="USD", valuation_date=BATCH_19_VALUATION_DATE) if ticker == "GE" else {}
    observations = []
    for year in policy.years:
        fact = annual[year]
        nci = nci_annual.get(year)
        value = float(fact.value) - (float(nci.value) if nci else 0.0)
        sources = (_history_source(fact),) + ((_history_source(nci),) if nci else ())
        observations.append(HistoryObservation("annual", fact.period_end, fact.fiscal_year, value, "USD", "reported parent-attributable earnings", sources))
    latest_annual = observations[-1].value
    ttm = latest_annual + policy.current_earnings - policy.prior_earnings
    current_fact_name = policy.annual_concept if ticker == "GE" else "NetIncomeLoss"
    current_row = _structural_flow(structural, name=current_fact_name, start=policy.current_start, end=policy.period, expected=policy.current_earnings + (3_000_000.0 if ticker == "GE" else 0.0))
    prior_row = _structural_flow(structural, name=current_fact_name, start=policy.prior_start, end={"GE": "2025-06-30", "PCAR": "2025-06-30", "DE": "2025-04-27"}[ticker], expected=policy.prior_earnings + (-13_000_000.0 if ticker == "GE" else 0.0))
    ttm_sources = (observations[-1].sources[0], current_row, prior_row)
    observations.append(HistoryObservation("operating_ttm", policy.period, None, ttm, "USD", "latest FY + current comparable period - prior comparable period", ttm_sources))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "mixed_industrial_finance_residual_income", BATCH_19_VALUATION_DATE, tuple(row.period_end for row in observations if row.period_role == "annual"), (metric,), True, "reported_and_company_history")
    shares = _shares(policy.weighted_shares, policy.current_shares)
    earnings = (metric.low, metric.base, metric.high)
    average_equity = (policy.beginning_equity + policy.ending_equity) / 2.0
    payout = min(1.0, policy.current_dividends * 2.0 / ttm)
    rows = []
    traces = {}
    multiples = []
    for index, name in enumerate(("bear", "base", "bull")):
        trace = residual_income_valuation(
            book_value_per_share=policy.ending_equity / shares[index],
            current_roe=earnings[index] / average_equity,
            cost_of_equity=policy.cost_of_equity[index],
            current_payout_ratio=payout,
            terminal_roe=policy.terminal_roe[index],
            terminal_growth=policy.terminal_growth[index],
            years=5,
        )
        raw = float(trace["intrinsic_value"])
        multiple = raw * shares[index] / earnings[index]
        rows.append({"name": name, "conditional_value_per_share": raw, "raw_value_per_share": raw, "normalized_common_earnings": earnings[index], "book_value_per_share": policy.ending_equity / shares[index], "current_roe": earnings[index] / average_equity, "current_payout_ratio": payout, "cost_of_equity": policy.cost_of_equity[index], "terminal_roe": policy.terminal_roe[index], "terminal_growth": policy.terminal_growth[index], "earnings_multiple": multiple, "shares": shares[index], "limited_liability_floor_applied": False})
        traces[name] = trace
        multiples.append(multiple)
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0.0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid equity range")
    reasons = ("CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    assumptions = {**profile.public_metadata(), "normalization_basis": "reported_common_equity_and_history_residual_income", "assumption_source_mix": "reported_common_equity_earnings_dividends_and_finsight_policy", "normalized_common_earnings": earnings, "earnings_multiples": tuple(multiples), "shares": shares, "book_equity": policy.ending_equity, "average_common_equity": average_equity, "current_payout_ratio": payout, "cost_of_equity": policy.cost_of_equity, "terminal_roe": policy.terminal_roe, "terminal_growth": policy.terminal_growth, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "equity_floor_basis": "not applied", "calculator_calibration": "Calculator varies normalized earnings and the residual-income-implied multiple around the base.", "invalidation": policy.invalidation}
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_19_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported common equity", policy.ending_equity, AssumptionClassification.REPORTED, "Current parent equity anchors residual income."), BaselineAssumption("company earnings history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Parent earnings history supplies the ROE range.")), warnings=(policy.warning, policy.invalidation), confidence_reasons=reasons, calculator_link=f"/api/us-valuations/{ticker}/calculator")
    context = [
        _point(structural, name="StockholdersEquity", expected={"GE": 17_640_000_000.0, "PCAR": 20_321_300_000.0, "DE": 27_406_000_000.0}[ticker], period_end=policy.period),
        _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=policy.weighted_shares, period_start=policy.current_start, period_end=policy.period),
        _share_point(structural, expected=policy.current_shares, end={"GE": "2026-06-30", "PCAR": "2026-07-24", "DE": "2026-05-03"}[ticker]),
        _no_preferred_excluding_redeemable_nci(structural, policy.period) if ticker == "DE" else _no_preferred(structural, policy.period),
    ]
    dividend_name = {"GE": "PaymentsOfOrdinaryDividends", "PCAR": "PaymentsOfDividends", "DE": "PaymentsOfDividendsCommonStock"}[ticker]
    context.append(_structural_flow(structural, name=dividend_name, start=policy.current_start, end=policy.period, expected=policy.current_dividends))
    if ticker == "GE":
        context.append(_point(structural, name="MinorityInterest", expected=227_000_000.0, period_end=policy.period))
    if ticker == "DE":
        context.extend((_point(structural, name="MinorityInterest", expected=7_000_000.0, period_end=policy.period), _point(structural, name="RedeemableNoncontrollingInterestEquityCarryingAmount", expected=47_000_000.0, period_end=policy.period)))
    events = [{"source_kind": "controlling_filing_narrative", "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "matter": {"GE": "GE Aerospace and run-off insurance continuing-company economics", "PCAR": "truck manufacturing and Financial Services economics", "DE": "equipment operations and John Deere Financial economics"}[ticker], "reported_vs_estimated": "reported_narrative"}, *_event_sources(event_root, ticker)]
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_19_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_common_earnings": ttm, "beginning_common_equity": policy.beginning_equity, "ending_common_equity": policy.ending_equity, "current_period_common_dividends": policy.current_dividends}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "company_history_profile": profile.as_private_dict(), "equity_model_context": context, "event_sources": events, "residual_income_trace": {"states": traces}, "bridge_treatment": "Equity-level model; finance/insurance assets, liabilities, funding, industrial debt, and NCI remain inside parent earnings/equity and are not EV-bridged. Parent-attributable earnings already exclude NCI.", "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": policy.warning, "baseline": baseline.as_private_dict()}


def build_batch_19_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_19_TICKERS:
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
    return _operating(ticker, filing, structural, submissions, facts, event_root)


if set(P) | set(EQUITY) != set(BATCH_19_TICKERS):
    raise RuntimeError("Batch 19 denominator mismatch")
