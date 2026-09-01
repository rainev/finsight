"""History-backed practical baselines for controlled Universe Reset Batch 22."""
from __future__ import annotations

import copy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling, _duration, _point
from .batch_05_launch_first import _source_proven_no_debt
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_11_history import _no_preferred
from .batch_16_history import _share_point
from .batch_22 import BATCH_22_TICKERS, BATCH_22_VALUATION_DATE
from .history import build_cash_fcff_history_profile
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability
from .xbrl import load_concept_config


BATCH_22_HISTORY_VERSION = "BATCH-22-INDUSTRIALS-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset({"WM", "IEX", "ODFL", "CPRT", "LMT", "ROK", "FIX"})
CONDITIONAL_TICKERS = frozenset({"HON", "JCI", "WAB"})
WITHHELD_TICKERS = frozenset()


def _shares(weighted: float, current: float) -> tuple[float, float, float]:
    high, low = max(weighted, current), min(weighted, current)
    return high, (high + low) / 2.0, low


@dataclass(frozen=True)
class Policy:
    method: str
    period: str
    cash: float
    debt: float
    claims: float
    weighted_shares: float
    current_shares: float
    current_share_end: str
    growth: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal: tuple[float, float, float]
    warning: str
    invalidation: str
    claim_formula: str

    @property
    def shares(self) -> tuple[float, float, float]:
        return _shares(self.weighted_shares, self.current_shares)


P = {
    "HON": Policy("pre_separation_conglomerate_faded_fcff", "2026-06-30", 9_296_000_000., 33_988_000_000., 320_000_000., 319_000_000., 316_940_010., "2026-06-30", (-.03, .03, .06), (.11, .095, .085), (.005, .015, .025), "Conditional Low pre-separation Honeywell baseline. The full 10-Q supports current operations and the amendment confirms shares, while separation funding and portfolio boundaries can still change continuing-company economics materially.", "Invalidate if the separation perimeter, pre-separation funding, continuing cash conversion, debt, securities, NCI, or diluted shares changes materially.", "$31.510B reported long-term debt plus $2.478B short-term borrowings; $320M NCI. $545M available-for-sale debt securities are included once with cash."),
    "WM": Policy("post_stericycle_environmental_services_faded_fcff", "2026-06-30", 557_000_000., 23_356_000_000., 1_000_000., 403_300_000., 399_715_184., "2026-07-24", (0., .04, .07), (.105, .09, .08), (.005, .015, .025), "Source-bounded post-Stericycle environmental-services baseline. Current operations, a complete combined fiscal year, debt/capital leases, NCI, shares, and five-year cash history reconcile.", "Invalidate if route pricing, landfill economics, Stericycle integration, cash conversion, debt/leases, NCI, or diluted shares changes materially.", "$23.356B reported debt and capital-lease obligations plus $1M NCI; restricted cash is excluded from surplus cash."),
    "IEX": Policy("diversified_industrial_faded_fcff", "2026-06-30", 621_300_000., 1_866_900_000., 0., 74_300_000., 73_719_896., "2026-07-24", (0., .04, .07), (.105, .09, .08), (.005, .015, .025), "Source-bounded diversified-industrial baseline. Five-year cash history and the current cash, debt, preferred-equity, NCI, and share bridge reconcile.", "Invalidate if industrial demand, acquisition integration, cash conversion, debt, claims, or diluted shares changes materially.", "$1.8669B reported long-term debt. Negative reported NCI is not credited to common equity; preferred equity is zero."),
    "JCI": Policy("building_systems_transition_faded_fcff", "2026-06-30", 641_000_000., 9_475_000_000., 33_000_000., 612_000_000., 605_741_470., "2026-06-30", (-.03, .02, .05), (.11, .095, .085), (.005, .015, .025), "Conditional Low building-systems baseline. Current cash and claims reconcile, but only two comparable annual cash periods plus restructuring and impairment activity make the historical normalization provisional.", "Invalidate if the portfolio perimeter, restructuring, cash conversion, debt/borrowings, supplier finance, NCI, or diluted shares changes materially.", "$8.299B noncurrent debt/capital leases plus $311M current maturities and $865M short-term borrowings; $33M NCI."),
    "ODFL": Policy("less_than_truckload_cycle_faded_fcff", "2026-06-30", 283_939_000., 19_997_000., 0., 209_014_000., 207_356_622., "2026-07-31", (-.05, .01, .04), (.11, .095, .085), (.005, .015, .025), "Source-bounded less-than-truckload cycle baseline. Five-year cash history, current cash, minimal debt, shares, and direct interest-expense lineage reconcile.", "Invalidate if freight demand, pricing, network utilization, capex, debt, claims, or diluted shares changes materially.", "$19.997M current debt and zero noncurrent debt. No nonzero preferred or NCI claim is reported."),
    "CPRT": Policy("vehicle_auction_network_faded_fcff", "2026-04-30", 3_354_142_000., 0., 17_181_000., 965_215_000., 925_811_482., "2026-05-27", (.02, .08, .12), (.105, .09, .08), (.005, .015, .025), "Source-bounded vehicle-auction network baseline. Four-year cash history, total cash/restricted cash, debt absence, redeemable NCI, preferred equity, and share sensitivity reconcile.", "Invalidate if auction volumes, international expansion, restricted-cash ownership, capex, debt absence, redeemable NCI, or diluted shares changes materially.", "No interest-bearing debt is reported. $17.181M redeemable NCI is deducted; preferred equity is zero."),
    "LMT": Policy("defense_program_normalized_faded_fcff", "2026-06-28", 3_791_000_000., 21_700_000_000., 0., 231_100_000., 230_790_753., "2026-07-20", (-.02, .03, .06), (.105, .09, .08), (.005, .015, .025), "Source-bounded defense-program baseline. Five-year history includes prior program losses rather than erasing them; current program-loss fact is zero and the cash, debt, and share bridge reconcile.", "Invalidate if program charges, contract cash timing, pension funding, debt, claims, or diluted shares changes materially.", "$21.7B reported debt carrying amount. No nonzero preferred or NCI claim is bridge-deducted."),
    "WAB": Policy("post_acquisition_rail_equipment_faded_fcff", "2026-06-30", 670_000_000., 6_571_000_000., 30_000_000., 170_100_000., 168_910_851., "2026-07-17", (-.02, .04, .07), (.11, .095, .085), (.005, .015, .025), "Conditional Low post-acquisition rail-equipment baseline. Current debt includes acquisition funding, but $1.062B of first-half business purchases and partial-period acquired cash conversion make the history only a broad guide.", "Invalidate if acquired revenue/cash conversion, purchase accounting, debt, supplier finance, NCI, or diluted shares changes materially.", "$6.571B total long-term debt plus $30M NCI. The acquisition payment is not deducted again from enterprise value."),
    "ROK": Policy("industrial_automation_cycle_faded_fcff", "2026-06-30", 479_000_000., 3_258_000_000., 2_000_000., 112_300_000., 111_048_676., "2026-06-30", (-.03, .03, .06), (.105, .09, .08), (.005, .015, .025), "Source-bounded industrial-automation baseline. Five-year cash history and current cash, borrowings, debt, NCI, and shares reconcile.", "Invalidate if automation demand, order conversion, software reinvestment, debt/borrowings, NCI, or diluted shares changes materially.", "$686M short-term borrowings plus $2M current and $2.570B noncurrent debt; $2M NCI."),
    "FIX": Policy("mechanical_construction_backlog_faded_fcff", "2026-06-30", 1_854_794_000., 54_064_000., 0., 35_255_000., 35_194_329., "2026-07-17", (.01, .06, .10), (.11, .095, .085), (.005, .015, .025), "Source-bounded mechanical-construction baseline. Five-year cash history and current cash, debt, zero preferred shares, and diluted shares reconcile.", "Invalidate if backlog conversion, project mix, working capital, acquisitions, debt, claims, or diluted shares changes materially.", "$54.064M total long-term debt. No preferred shares are outstanding and no nonzero NCI claim is reported."),
}


POINT_SPECS = {
    "HON": (("CashAndCashEquivalentsAtCarryingValue", 8_751_000_000.), ("AvailableForSaleSecuritiesDebtSecurities", 545_000_000.), ("LongTermDebt", 31_510_000_000.), ("ShortTermBorrowings", 2_478_000_000.), ("MinorityInterest", 320_000_000.)),
    "WM": (("CashAndCashEquivalentsAtCarryingValue", 557_000_000.), ("DebtAndCapitalLeaseObligations", 23_356_000_000.), ("MinorityInterest", 1_000_000.)),
    "IEX": (("CashAndCashEquivalentsAtCarryingValue", 621_300_000.), ("LongTermDebt", 1_866_900_000.), ("MinorityInterest", -1_400_000.), ("PreferredStockValue", 0.)),
    "JCI": (("CashAndCashEquivalentsAtCarryingValue", 641_000_000.), ("LongTermDebtAndCapitalLeaseObligations", 8_299_000_000.), ("LongTermDebtAndCapitalLeaseObligationsCurrent", 311_000_000.), ("ShortTermBorrowings", 865_000_000.), ("MinorityInterest", 33_000_000.), ("PreferredStockValue", 0.)),
    "ODFL": (("CashAndCashEquivalentsAtCarryingValue", 283_939_000.), ("LongTermDebtCurrent", 19_997_000.), ("LongTermDebtNoncurrent", 0.)),
    "CPRT": (("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", 3_354_142_000.), ("RedeemableNoncontrollingInterestEquityCarryingAmount", 17_181_000.), ("PreferredStockValue", 0.)),
    "LMT": (("CashAndCashEquivalentsAtCarryingValue", 3_791_000_000.), ("DebtInstrumentCarryingAmount", 21_700_000_000.), ("LongTermDebtCurrent", 0.)),
    "WAB": (("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", 670_000_000.), ("LongTermDebt", 6_571_000_000.), ("MinorityInterest", 30_000_000.)),
    "ROK": (("CashAndCashEquivalentsAtCarryingValue", 479_000_000.), ("ShortTermBorrowings", 686_000_000.), ("LongTermDebtCurrent", 2_000_000.), ("LongTermDebtNoncurrent", 2_570_000_000.), ("MinorityInterest", 2_000_000.)),
    "FIX": (("CashAndCashEquivalentsAtCarryingValue", 1_854_794_000.), ("LongTermDebt", 54_064_000.)),
}

SHARE_STARTS = {"HON":"2026-01-01", "WM":"2026-01-01", "IEX":"2026-01-01", "JCI":"2025-10-01", "ODFL":"2026-01-01", "CPRT":"2025-08-01", "LMT":"2026-01-01", "WAB":"2026-01-01", "ROK":"2025-10-01", "FIX":"2026-01-01"}


def _controlling_full(ticker: str, manifest: dict[str, Any], submissions: dict[str, Any]) -> dict[str, str]:
    if ticker != "HON":
        return _controlling(manifest, submissions)
    candidates = [row for row in manifest["eligible_filings"] if row["form"] == "10-Q"]
    filing = max(candidates, key=lambda row: (row["filed"], row["accession"]))
    index = submissions["filings"]["recent"]["accessionNumber"].index(filing["accession"])
    return {**filing, "period_end": submissions["filings"]["recent"]["reportDate"][index]}


def _issuer_normalizer(ticker: str, submissions: dict[str, Any], facts: dict[str, Any]):
    if ticker not in {"HON", "ODFL"}:
        return _normalizer(submissions, facts)
    config = copy.deepcopy(load_concept_config())
    config["fields"]["interest_expense"]["concepts"].append("InterestAndDebtExpense")
    return _normalizer(submissions, facts, concept_config=config)


def _bridge(ticker: str, structural: dict[str, Any], policy: Policy) -> list[dict[str, Any]]:
    rows = [_point(structural, name=name, expected=value, period_end=policy.period) for name, value in POINT_SPECS[ticker]]
    rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=policy.weighted_shares, period_start=SHARE_STARTS[ticker], period_end=policy.period))
    rows.append(_share_point(structural, expected=policy.current_shares, end=policy.current_share_end))
    rows.append(_no_preferred(structural, policy.period))
    if ticker == "CPRT":
        rows.append(_source_proven_no_debt(structural, period_end=policy.period))
    return rows


def _event_sources(ticker: str, filing: dict[str, Any], structural: dict[str, Any]) -> list[dict[str, Any]]:
    base = {"source_kind":"controlling_filing_narrative", "accession":filing["accession"], "filed":filing["filed"], "period_end":filing["period_end"], "reported_vs_estimated":"reported_narrative"}
    events: dict[str, dict[str, Any]] = {
        "HON": {"matter":"business separations and pre-separation funding", "reported_terms":{"pre_separation_funding_usd":15_835_000_000.}},
        "WM": {"matter":"post-Stericycle environmental-services operations", "reported_terms":{"complete_combined_fiscal_year_used":True}},
        "IEX": {"matter":"ordinary diversified-industrial operations", "reported_terms":{}},
        "JCI": {"matter":"portfolio restructuring and limited comparable history", "reported_terms":{"current_ytd_restructuring_usd":224_000_000., "current_ytd_impairment_usd":160_000_000.}},
        "ODFL": {"matter":"less-than-truckload cycle", "reported_terms":{}},
        "CPRT": {"matter":"ordinary vehicle-auction network expansion", "reported_terms":{}},
        "LMT": {"matter":"defense-program execution", "reported_terms":{"current_h1_program_losses_usd":0., "prior_h1_program_losses_usd":1_615_000_000.}},
        "WAB": {"matter":"current-year business acquisition", "reported_terms":{"h1_acquisition_cash_usd":1_062_000_000.}},
        "ROK": {"matter":"industrial-automation cycle", "reported_terms":{}},
        "FIX": {"matter":"mechanical-construction backlog conversion", "reported_terms":{}},
    }
    rows = [{**base, **events[ticker]}]
    if ticker == "HON":
        rows.append(_structural_flow(structural, name="PreSeparationFunding", start="2026-01-01", end=policy_period(ticker), expected=15_835_000_000.))
    elif ticker == "JCI":
        rows.extend((_structural_flow(structural, name="RestructuringCostsAndAssetImpairmentCharges", start="2025-10-01", end=policy_period(ticker), expected=224_000_000.), _structural_flow(structural, name="AssetImpairmentCharges", start="2025-10-01", end=policy_period(ticker), expected=160_000_000.)))
    elif ticker == "LMT":
        rows.extend((_structural_flow(structural, name="ProgramGainsLosses", start="2026-01-01", end=policy_period(ticker), expected=0.), _structural_flow(structural, name="ProgramGainsLosses", start="2025-01-01", end="2025-06-29", expected=1_615_000_000.)))
    elif ticker == "WAB":
        rows.append(_structural_flow(structural, name="PaymentsToAcquireBusinessesNetOfCashAcquired", start="2026-01-01", end=policy_period(ticker), expected=1_062_000_000.))
    return rows


def policy_period(ticker: str) -> str:
    return P[ticker].period


def build_batch_22_history_result(*, ticker: str, source_root: Path, structural_root: Path) -> dict[str, Any]:
    policy = P[ticker]
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    filing = _controlling_full(ticker, manifest, submissions)
    if structural["source_accession"] != filing["accession"]:
        raise ValueError(f"{ticker}: structural/control accession mismatch")
    normalizer = _issuer_normalizer(ticker, submissions, facts)
    flows = {name: normalizer.ttm_flow(name) for name in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    try:
        tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    except ValueError:
        tax_rate, tax_sources = .21, ()
    if not .05 <= tax_rate <= .30:
        tax_rate = .21
    current = cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]), capital_expenditures=float(flows["capital_expenditures"]["value"]), spectrum_investment=0., interest_expense=abs(float(flows["interest_expense"]["value"])), tax_rate=tax_rate)
    annual = _annual_cash_with_losses(normalizer)[2]
    sources = [dict(row) for flow in flows.values() for row in flow.get("sources", [])]
    revenue = float(flows["revenue"]["value"])
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=revenue, ttm_cash_fcff=current, ttm_period_end=policy.period, ttm_sources=sources, valuation_date=BATCH_22_VALUATION_DATE)
    cash_metric, growth_metric = profile.metric("cash_conversion_margin"), profile.metric("revenue_growth")
    if cash_metric is None or growth_metric is None or (not profile.full_history and ticker != "JCI"):
        raise ValueError(f"{ticker}: insufficient history")
    margins = tuple(max(.001, float(value)) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    growth = (max(-.10, min(policy.growth[0], growth_metric.low)), max(-.08, min(policy.growth[1], growth_metric.base)), max(0., min(policy.growth[2], growth_metric.high)))
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(revenue * margins[index], growth[index], policy.terminal[index], policy.wacc[index], policy.cash, policy.debt, 0., policy.claims, policy.shares[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name":name, "conditional_value_per_share":max(0., raw), "raw_value_per_share":raw, "starting_cash_fcff":state.cash_fcff, "cash_conversion_margin":margins[index], "growth":growth[index], "wacc":policy.wacc[index], "terminal_growth":policy.terminal[index], "cash_and_investments":policy.cash, "debt_and_finance_leases":policy.debt, "other_equity_claims":policy.claims, "shares":policy.shares[index], "limited_liability_floor_applied":raw < 0.})
        traces[name] = trace
    scenario = {"low":rows[0]["conditional_value_per_share"], "base":rows[1]["conditional_value_per_share"], "high":rows[2]["conditional_value_per_share"]}
    if not 0. <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0.:
        raise ValueError(f"{ticker}: invalid range")
    is_pass = ticker in PASS_TICKERS
    reasons = () if is_pass else ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="High" if is_pass else "Low", source_cap="High", reasons=reasons)
    public_history = profile.public_metadata()
    if not is_pass:
        public_history.update({"normalization_basis":"company_history_with_named_material_transition", "assumption_source_mix":"reported_history_and_finsight_policy"})
    assumptions = {**public_history, "forecast_years":FORECAST_YEARS, "cash_conversion_margin":margins, "growth":growth, "wacc":policy.wacc, "terminal_growth":policy.terminal, "shares":policy.shares, "equity_floor_basis":"limited-liability bear floor with raw residual retained" if scenario["low"] == 0. else "not applied", "calculator_calibration":"Exact faded-cash base.", "interest_alias_policy":"Issuer-specific direct InterestAndDebtExpense lineage" if ticker in {"HON", "ODFL"} else "shared governed aliases", "invalidation":policy.invalidation}
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_22_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked annual and current cash conversion anchors the range."), BaselineAssumption("faded operating states", str({"growth":growth, "wacc":policy.wacc, "terminal":policy.terminal}), AssumptionClassification.FINSIGHT_ASSUMPTION, "Growth fades over eight years to a governed terminal state.")), warnings=(policy.warning, policy.invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link=f"/api/us-valuations/{ticker}/calculator")
    return {"ticker":ticker, "method":policy.method, "model_version":BATCH_22_HISTORY_VERSION, "availability_type":"available" if is_pass else "conditional_estimate", "scenario_rows":rows, "scenario_range":scenario, "reported_inputs":{"ttm_revenue":revenue, "ttm_operating_cash_flow":flows["operating_cash_flow"]["value"], "ttm_reinvestment":flows["capital_expenditures"]["value"], "ttm_interest":flows["interest_expense"]["value"], "tax_rate":tax_rate, "ttm_cash_fcff":current}, "governed_assumptions":assumptions, "history_reliability":reliability.as_dict(), "source_ledger":{"controlling_filing":filing, "flow_sources":flows, "annual_cash_sources":list(annual), "tax_rate_sources":list(tax_sources), "company_history_profile":profile.as_private_dict(), "bridge_sources":_bridge(ticker, structural, policy), "event_sources":_event_sources(ticker, filing, structural), "bridge_reconciliation":{"cash_and_investments":policy.cash, "debt_and_finance_leases":policy.debt, "other_equity_claims":policy.claims, "other_equity_claim_formula":policy.claim_formula, "shares":policy.shares, "operating_liability_treatment":"Operating leases, supplier finance, and ordinary working-capital obligations remain in cash conversion and are not deducted twice."}, "model_trace":{"forecast_years":FORECAST_YEARS, "states":traces}, "structural_top_level_period_diagnostic":{"value":structural.get("period_end"), "used_for_selection":False}}, "warning":policy.warning, "baseline":baseline.as_private_dict()}


if set(P) != set(BATCH_22_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_22_TICKERS):
    raise RuntimeError("Batch 22 policy/manifest mismatch")
