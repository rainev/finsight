"""One authorized ORCL recovery attempt with an explicit infrastructure schedule."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

from .baseline import AvailabilityType, BaselineValuation
from .batch_31 import BATCH_31_TICKERS
from .batch_31_history import build_batch_31_history_result, _fact


BATCH_31_RECOVERY_VERSION = "BATCH-31-ORCL-INFRASTRUCTURE-RECOVERY-1.0"
FORECAST_YEARS = 10
RECOVERED_PASS_TICKERS = frozenset({"CDW", "VRSK"})
RECOVERED_CONDITIONAL_TICKERS = frozenset({"PANW", "WDAY", "NOW", "SMCI", "NXPI", "ACN", "CRWD"})
RECOVERED_WITHHELD_TICKERS = frozenset({"ORCL"})

_B = 1_000_000_000.
_START_REVENUE = 67.357 * _B
_START_CAPEX_RATIO = 55.663 / 67.357
_CASH = 31.894 * _B
_DEBT_AND_FINANCE_LEASES = 137.242 * _B
_PREFERRED_CLAIM = 4.954 * _B
_NCI = .548 * _B
_PURCHASE_SCHEDULE = (1_841_000_000., 1_034_000_000., 1_053_000_000., 952_000_000., 896_000_000., 0., 0., 0., 0., 0.)


@dataclass(frozen=True)
class InfrastructureScenario:
    name: str
    annual_growth: float
    pre_capex_cash_margin: float
    terminal_capex_ratio: float
    new_lease_term_years: int
    lease_commencement: str
    wacc: float
    terminal_growth: float
    shares: float


SCENARIOS = (
    InfrastructureScenario("bear", .060195379749369504, .28176989326107443, .36960574226031810, 15, "all_fiscal_2027", .12, 0., 2_914_000_000.),
    InfrastructureScenario("base", .12864242718068264, .41173129481915050, .15185135124828427, 17, "equal_thirds_fiscal_2027_to_2029", .105, .01, 2_897_235_500.),
    InfrastructureScenario("bull", .17348734298506940, .46622881537591104, .10629123468426013, 19, "equal_thirds_fiscal_2027_to_2029", .095, .02, 2_880_471_000.),
)


def _lease_cohorts(scenario: InfrastructureScenario) -> tuple[tuple[int, float, int], ...]:
    if scenario.lease_commencement == "all_fiscal_2027":
        return ((1, 260. * _B, scenario.new_lease_term_years),)
    return tuple((start, 260. * _B / 3, scenario.new_lease_term_years) for start in (1, 2, 3))


def _lease_cash(scenario: InfrastructureScenario, year: int) -> float:
    return sum(amount / term for start, amount, term in _lease_cohorts(scenario) if start <= year < start + term)


def _lease_residual_pv(scenario: InfrastructureScenario) -> float:
    return sum((amount / term) / (1 + scenario.wacc) ** year for start, amount, term in _lease_cohorts(scenario) for year in range(11, start + term))


def value_oracle_infrastructure_scenario(scenario: InfrastructureScenario) -> dict:
    revenue = _START_REVENUE
    explicit_pv = 0.
    forecast_rows = []
    for year in range(1, FORECAST_YEARS + 1):
        revenue *= 1 + scenario.annual_growth
        capex_ratio = _START_CAPEX_RATIO + (scenario.terminal_capex_ratio - _START_CAPEX_RATIO) * year / FORECAST_YEARS
        pre_capex_cash = revenue * scenario.pre_capex_cash_margin
        capex = revenue * capex_ratio
        lease_cash = _lease_cash(scenario, year)
        purchase_cash = _PURCHASE_SCHEDULE[year - 1]
        fcff = pre_capex_cash - capex - lease_cash - purchase_cash
        present_value = fcff / (1 + scenario.wacc) ** year
        explicit_pv += present_value
        forecast_rows.append({"year": year, "revenue": revenue, "growth": scenario.annual_growth, "pre_capex_cash_margin": scenario.pre_capex_cash_margin, "pre_capex_cash": pre_capex_cash, "capex_ratio": capex_ratio, "capex": capex, "new_lease_cash": lease_cash, "purchase_obligation_cash": purchase_cash, "fcff": fcff, "present_value": present_value})
    terminal_revenue = revenue * (1 + scenario.terminal_growth)
    terminal_fcff = terminal_revenue * (scenario.pre_capex_cash_margin - scenario.terminal_capex_ratio)
    terminal_value = terminal_fcff / (scenario.wacc - scenario.terminal_growth)
    terminal_pv = terminal_value / (1 + scenario.wacc) ** FORECAST_YEARS
    lease_residual_pv = _lease_residual_pv(scenario)
    enterprise_value = explicit_pv + terminal_pv - lease_residual_pv
    equity_value = enterprise_value + _CASH - _DEBT_AND_FINANCE_LEASES - _PREFERRED_CLAIM - _NCI
    raw_value = equity_value / scenario.shares
    conversion_rate = {"bear": 624.7657, "base": (499.8126 + 624.7657) / 2, "bull": 499.8126}[scenario.name]
    conversion_shares = 50_000. * conversion_rate
    conversion_alternative = (enterprise_value + _CASH - _DEBT_AND_FINANCE_LEASES - _NCI) / (scenario.shares + conversion_shares)
    return {"name": scenario.name, "raw_value_per_share": raw_value, "preferred_conversion_alternative_per_share": conversion_alternative, "explicit_fcff_present_value": explicit_pv, "terminal_present_value": terminal_pv, "post_year_ten_lease_residual_present_value": lease_residual_pv, "enterprise_value": enterprise_value, "equity_value": equity_value, "shares": scenario.shares, "forecast_rows": tuple(forecast_rows), "terminal_revenue": terminal_revenue, "terminal_fcff": terminal_fcff, "annual_growth": scenario.annual_growth, "pre_capex_cash_margin": scenario.pre_capex_cash_margin, "starting_capex_ratio": _START_CAPEX_RATIO, "terminal_capex_ratio": scenario.terminal_capex_ratio, "new_lease_term_years": scenario.new_lease_term_years, "lease_commencement": scenario.lease_commencement, "wacc": scenario.wacc, "terminal_growth": scenario.terminal_growth, "preferred_conversion_rate": conversion_rate, "preferred_conversion_shares": conversion_shares}


def _versioned(result: dict) -> dict:
    value = deepcopy(result)
    value["model_version"] = BATCH_31_RECOVERY_VERSION
    value["baseline"] = {**value["baseline"], "method_version": BATCH_31_RECOVERY_VERSION}
    return value


def _provenance(structural_root: Path) -> dict:
    package = json.loads((Path(structural_root) / "ORCL" / "package-manifest.json").read_text())
    primary = next(item for item in package["files"] if item.get("local_path") == package.get("primary_document"))
    return {"source_kind": "controlling_filing_reported_terms", "accession": "0001193125-26-277521", "filed": "2026-06-22", "form": "10-K", "period_end": "2026-05-31", "primary_document": primary["local_path"], "source_url": primary["source_url"], "document_sha256": primary["sha256"], "reported_vs_estimated": "reported_terms_with_governed_timing"}


def _oracle_attempt(initial: dict, structural_root: Path) -> dict:
    structural = json.loads((Path(structural_root) / "ORCL" / "structural-filing.json").read_text())
    traces = tuple(value_oracle_infrastructure_scenario(scenario) for scenario in SCENARIOS)
    reason = "Recovery attempted; Oracle remains withheld. A history-bounded ten-year infrastructure stress replay produces negative bear and base common-equity values even before fully charging the $7.533B thereafter power bucket and the subsequent $19B infrastructure commitment. A positive base still requires unsupported infrastructure economics."
    invalidation = "Revalue after issuer-supported capex commissioning/depreciation, lease payment starts, infrastructure revenue and cash conversion, purchase-obligation timing, refinancing, and preferred-conversion evidence supports a finite positive base."
    baseline = BaselineValuation(ticker="ORCL", method="unavailable_cloud_infrastructure_commitment_model", method_version=BATCH_31_RECOVERY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(reason, invalidation))
    structural_sources = (
        _fact(structural, "CloudRevenues", 33_989_000_000., "2025-06-01", "2026-05-31"),
        _fact(structural, "ConstructionInProgressGross", 39_973_000_000., None, "2026-05-31"),
        _fact(structural, "IncreaseDecreaseInDeferredRevenuesFromCustomerPrepaymentsWithSignificantFinancingComponent", 4_592_000_000., "2025-06-01", "2026-05-31"),
        _fact(structural, "RevenueRemainingPerformanceObligation", 638_000_000_000., None, "2026-05-31"),
        _fact(structural, "LesseeOperatingLeaseLeaseNotYetCommencedLeaseCommitments", 260_000_000_000., None, "2026-05-31"),
        _fact(structural, "UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", 13_309_000_000., None, "2026-05-31"),
        _fact(structural, "UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", 19_000_000_000., None, "2026-06-22", True),
        _fact(structural, "PreferredStockSharesOutstanding", 50_000., None, "2026-05-31", True),
    )
    reported_terms = {**_provenance(structural_root), "source_locator": "MD&A Liquidity and Capital Resources; Notes 1, 6, 9, and 10", "reported_terms": {"rpo_total": 638_000_000_000., "rpo_recognition_percentages": {"next_12_months": .12, "months_13_to_36": .34, "months_37_to_60": .34, "thereafter": .20}, "new_lease_commitments": 260_000_000_000., "lease_commencement_window": "fiscal_2027_through_fiscal_2029", "lease_term_years": [15, 19], "purchase_obligation_schedule": {"fiscal_2027": 1_841_000_000., "fiscal_2028": 1_034_000_000., "fiscal_2029": 1_053_000_000., "fiscal_2030": 952_000_000., "fiscal_2031": 896_000_000., "thereafter": 7_533_000_000.}, "post_balance_infrastructure_commitment": 19_000_000_000., "post_balance_commitment_term_years": 5, "preferred_carrying_value": _PREFERRED_CLAIM, "preferred_conversion_date": "2029-01-15", "preferred_conversion_rate_range": [499.8126, 624.7657]}}
    assumptions = {"history_policy_version": initial["governed_assumptions"]["history_policy_version"], "history_years_used": initial["governed_assumptions"]["history_years_used"], "forecast_years": FORECAST_YEARS, "normalization_basis": "history_bounded_infrastructure_recovery_attempt", "assumption_source_mix": "reported_filing_terms_and_finsight_policy", "assumption_classification": {"reported_terms": "reported", "annual_growth": "historically_derived_finsight_assumption", "pre_capex_cash_margin": "historically_derived_finsight_assumption", "capex_fade": "historically_derived_finsight_assumption", "lease_commencement_cohorts": "optimistic_finsight_assumption_within_reported_window", "wacc_and_terminal_growth": "finsight_assumption"}, "scenario_parameters": {scenario.name: {"annual_growth": scenario.annual_growth, "pre_capex_cash_margin": scenario.pre_capex_cash_margin, "starting_capex_ratio": _START_CAPEX_RATIO, "terminal_capex_ratio": scenario.terminal_capex_ratio, "new_lease_term_years": scenario.new_lease_term_years, "lease_commencement": scenario.lease_commencement, "wacc": scenario.wacc, "terminal_growth": scenario.terminal_growth, "shares": scenario.shares, "reported_vs_estimated": "finsight_assumption"} for scenario in SCENARIOS}, "lease_schedule_treatment": {"reported_total": 260_000_000_000., "reported_commencement_window": "fiscal_2027_through_fiscal_2029", "reported_term_range_years": [15, 19], "estimated_cohort_timing": {"bear": "all fiscal 2027", "base": "equal thirds fiscal 2027-2029", "bull": "equal thirds fiscal 2027-2029"}, "reported_vs_estimated": "reported_bounds_with_optimistic_finsight_timing"}, "excluded_optimistic_costs": {"purchase_obligations_after_year_five": 7_533_000_000., "post_balance_infrastructure_commitment": 19_000_000_000., "reason": "Timing is not fully disclosed; excluding them makes the failed positive-base test deliberately optimistic."}, "double_count_controls": {"existing_operating_lease_expense": "inside reported OCF", "uncommenced_lease_cash": "modeled incrementally", "finance_lease_liability": "deducted once in bridge", "debt_maturities": "not deducted again from FCFF", "preferred": "carrying claim deducted once; corrected conversion alternative is diagnostic only", "rpo": "not cash or an asset"}, "reason_codes": ["MODEL_UNSUPPORTED", "NONFINITE_OR_NONPOSITIVE_VALUE", "CAPEX_CASH_CONVERSION_SENSITIVITY"], "invalidation": invalidation}
    value = deepcopy(initial)
    value.update({"model_version": BATCH_31_RECOVERY_VERSION, "warning": reason, "baseline": baseline.as_private_dict(), "governed_assumptions": assumptions})
    value["source_ledger"] = {**initial["source_ledger"], "infrastructure_recovery_attempt": {"structural_sources": list(structural_sources), "reported_terms": reported_terms, "scenario_traces": list(traces), "formula": "PV[revenue × pre-capex cash margin − revenue × linearly faded capex ratio − incremental uncommenced-lease cash − disclosed first-five-year power obligations] + PV[terminal revenue × (cash margin − capex floor)] − PV[post-year-10 lease residual] + cash − debt/finance leases − preferred claim − NCI", "purchase_obligations_after_year_five_included": False, "post_balance_19b_included": False, "rpo_added_as_cash": False, "conclusion": "base common-equity value remains negative under an optimistic source-bounded replay"}, "recovery_attempt": {"attempted": True, "initial_availability_type": "not_available", "final_availability_type": "not_available", "market_price_used": False, "analyst_target_used": False, "competitor_value_used": False}}
    return value


def build_batch_31_recovery_result(*, ticker: str, source_root: Path, structural_root: Path) -> dict:
    if ticker not in BATCH_31_TICKERS:
        raise ValueError(ticker)
    initial = build_batch_31_history_result(ticker=ticker, source_root=source_root, structural_root=structural_root)
    return _oracle_attempt(initial, structural_root) if ticker == "ORCL" else _versioned(initial)


if RECOVERED_PASS_TICKERS | RECOVERED_CONDITIONAL_TICKERS | RECOVERED_WITHHELD_TICKERS != set(BATCH_31_TICKERS):
    raise RuntimeError("Batch 31 recovery classification mismatch")
