"""History-backed practical baselines for controlled Universe Reset Batch 17."""
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
from .batch_17 import BATCH_17_TICKERS, BATCH_17_VALUATION_DATE
from .equity_fact_selection import annual_facts
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, build_cash_fcff_history_profile, summarize_history_metric
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability
from .xbrl import load_concept_config


BATCH_17_HISTORY_VERSION = "BATCH-17-HEALTH-CARE-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset({"ZTS", "STE"})
CONDITIONAL_TICKERS = frozenset({"ABBV", "MDT", "MRNA", "CI", "VTRS", "GEHC", "KVUE", "SOLV"})
WITHHELD_TICKERS = frozenset()
EQUITY_EARNINGS_TICKERS = frozenset({"CI"})


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


def _shares(weighted: float, current: float) -> tuple[float, float, float]:
    high_count, low_count = max(weighted, current), min(weighted, current)
    return high_count, (high_count + low_count) / 2.0, low_count


P = {
    "ABBV": Policy("biopharma_reported_operations_faded_fcff", "2026-06-30", 6_835_000_000.0, 70_822_000_000.0, (1_747_000_000.0,) * 3, _shares(1_773_000_000.0, 1_767_117_285.0), (0.0, 0.04, 0.07), (0.105, 0.09, 0.08), (0.005, 0.015, 0.02), "Conditional Low current standalone pre-Apogee biopharma baseline. Five-year after-payment cash history and current debt, cash, litigation reserve, NCI, and shares reconcile; the signed $10B note offering expected to close after the cutoff is not treated as issued debt or cash.", "Invalidate if the Apogee acquisition or financing closes, terminates, or changes; or if product concentration, patent timing, acquired pipeline cash, contingent consideration, litigation, debt, or shares changes materially.", "$1.7B reported litigation reserve plus $47M NCI. The $27.495B contingent-consideration liability is recorded as a diagnostic and not deducted again because ongoing payments remain in reported after-payment cash history; material changes invalidate the baseline."),
    "ZTS": Policy("animal_health_faded_fcff", "2026-06-30", 1_676_000_000.0, 9_150_000_000.0, (0.0,) * 3, _shares(420_100_000.0, 413_223_602.0), (0.01, 0.05, 0.07), (0.105, 0.09, 0.08), (0.01, 0.02, 0.025), "Source-bounded animal-health cash baseline. Five-year cash conversion, current cash/investments, debt, no NCI, and diluted shares reconcile; management does not expect current legal matters to be materially adverse to financial position.", "Invalidate if animal-health demand, product safety, cash conversion, debt, investments, claims, or shares changes materially.", "No NCI or preferred claim. Restricted cash is not treated as surplus cash."),
    "MDT": Policy("current_consolidated_medtech_faded_fcff", "2026-04-24", 9_220_000_000.0, 28_131_000_000.0, (972_000_000.0,) * 3, _shares(1_288_100_000.0, 1_280_045_190.0), (0.0, 0.035, 0.06), (0.105, 0.09, 0.08), (0.005, 0.015, 0.02), "Conditional Low current-consolidated medtech baseline. MiniMed completed an IPO but remains approximately 90.03%-owned and consolidated; future separation can change the economic object.", "Invalidate if MiniMed ownership/separation, cash investments, debt, NCI, contingent consideration, claims, or shares changes materially.", "$609M NCI plus $163M contingent consideration plus $200M loss-contingency accrual. Current cash and short-term investments are counted once."),
    "STE": Policy("sterilization_medtech_faded_fcff", "2026-06-30", 482_300_000.0, 1_893_700_000.0, (57_700_000.0,) * 3, _shares(97_900_000.0, 97_500_110.0), (0.02, 0.07, 0.10), (0.105, 0.09, 0.08), (0.01, 0.02, 0.025), "Source-bounded sterilization and medtech baseline. Five-year cash history, current cash, combined debt, litigation reserve, NCI, shares, and small current acquisitions reconcile.", "Invalidate if procedure demand, cash conversion, acquisitions, debt, litigation, NCI, or shares changes materially.", "$43.2M litigation reserve plus $14.5M NCI; reported operating cash already includes ordinary restructuring and acquisition costs."),
    "VTRS": Policy("declining_portfolio_pharma_faded_fcff", "2026-06-30", 886_500_000.0, 13_351_300_000.0, (766_600_000.0,) * 3, _shares(1_173_800_000.0, 1_148_590_864.0), (-0.08, -0.04, 0.01), (0.12, 0.105, 0.095), (-0.01, 0.005, 0.015), "Conditional Low declining-portfolio pharmaceutical baseline. Five-year cash history, current debt, contingent consideration, and recorded litigation reconcile; divestitures, restructuring, patent outcomes, and the Pfizer opioid dispute remain material.", "Invalidate if portfolio scope, restructuring, patent cash, opioid indemnification, contingent consideration, debt, claims, or shares changes materially.", "$463.6M contingent consideration plus the complete $303M legal/professional accrual. The separately tagged $60M matter is inside that $303M balance and is not added again; possible excess loss remains outside the range and is not zero."),
    "GEHC": Policy("post_spin_health_equipment_faded_fcff", "2026-06-30", 2_441_000_000.0, 10_217_000_000.0, (243_000_000.0,) * 3, _shares(456_000_000.0, 451_686_252.0), (0.01, 0.04, 0.07), (0.11, 0.095, 0.085), (0.005, 0.015, 0.02), "Conditional Low post-spin health-equipment baseline. Current interest is source repaired, but short independent history, acquisitions, tariffs, and a significant unquantified legal matter remain material.", "Invalidate if tariff mitigation, legal exposure, acquisition cash, debt/leases, NCI, post-spin cash conversion, or shares changes materially.", "$14M NCI plus $229M redeemable NCI. Debt uses the reported carrying aggregate plus the separately reported $54M noncurrent finance lease; unquantified legal loss remains None."),
    "KVUE": Policy("pre_kimberly_clark_consumer_health_faded_fcff", "2026-06-28", 1_110_000_000.0, 8_483_000_000.0, (149_000_000.0,) * 3, _shares(1_922_000_000.0, 1_920_773_467.0), (-0.03, 0.0, 0.03), (0.11, 0.095, 0.085), (0.0, 0.01, 0.02), "Conditional Low pre-Kimberly-Clark consumer-health baseline. Current standalone cash history and debt reconcile, while the pending merger, separation indemnities, and acetaminophen/talc litigation remain material.", "Invalidate if the Kimberly-Clark transaction closes, terminates, or changes; or if litigation, indemnities, debt, cash conversion, or shares changes materially.", "$149M current/noncurrent tax-indemnification liability. Other litigation beyond recorded liabilities remains outside the range and is not assigned zero."),
    "SOLV": Policy("post_spin_health_technology_faded_fcff", "2026-06-30", 403_000_000.0, 5_292_000_000.0, (235_000_000.0,) * 3, _shares(174_400_000.0, 170_223_729.0), (-0.03, 0.0, 0.03), (0.12, 0.105, 0.095), (0.0, 0.01, 0.015), "Conditional Low post-spin health-technology baseline. Current cash conversion is stressed after Acera and restructuring; Bair Hugger indemnification and short independent history remain material.", "Invalidate if post-spin cash conversion, Acera integration, restructuring, Bair Hugger/PFAS exposure, debt/leases, claims, or shares changes materially.", "$235M reported loss-contingency accrual. Debt carrying amount plus separately reported finance leases are counted once; unquantified indemnified loss remains outside the range."),
}


POINT_SPECS = {
    "ABBV": (("CashAndCashEquivalentsAtCarryingValue", 6_569_000_000.0), ("LongTermInvestments", 266_000_000.0), ("LongTermDebtAndCapitalLeaseObligations", 62_481_000_000.0), ("LongTermDebtAndCapitalLeaseObligationsCurrent", 8_341_000_000.0), ("LitigationReserve", 1_700_000_000.0), ("MinorityInterest", 47_000_000.0)),
    "ZTS": (("CashAndCashEquivalentsAtCarryingValue", 1_476_000_000.0), ("ShortTermInvestments", 200_000_000.0), ("DebtInstrumentCarryingAmount", 9_150_000_000.0), ("MinorityInterest", 0.0)),
    "MDT": (("CashAndCashEquivalentsAtCarryingValue", 1_949_000_000.0), ("ShortTermInvestments", 7_271_000_000.0), ("DebtInstrumentCarryingAmount", 28_131_000_000.0), ("MinorityInterest", 609_000_000.0), ("BusinessCombinationContingentConsiderationLiability", 163_000_000.0), ("LossContingencyAccrualAtCarryingValue", 200_000_000.0)),
    "STE": (("CashAndCashEquivalentsAtCarryingValue", 482_300_000.0), ("DebtLongtermAndShorttermCombinedAmount", 1_893_700_000.0), ("LitigationReserve", 43_200_000.0), ("MinorityInterest", 14_500_000.0)),
    "VTRS": (("CashAndCashEquivalentsAtCarryingValue", 886_500_000.0), ("LongTermDebtCurrent", 1_738_900_000.0), ("LongTermDebtNoncurrent", 11_612_400_000.0), ("BusinessCombinationContingentConsiderationLiability", 463_600_000.0), ("LitigationReserveCurrent", 303_000_000.0), ("LossContingencyAccrualAtCarryingValue", 60_000_000.0)),
    "GEHC": (("CashAndCashEquivalentsAtCarryingValue", 2_079_000_000.0), ("LongTermInvestments", 362_000_000.0), ("DebtInstrumentCarryingAmount", 10_163_000_000.0), ("FinanceLeaseLiabilityNoncurrent", 54_000_000.0), ("MinorityInterest", 14_000_000.0), ("RedeemableNoncontrollingInterestEquityCarryingAmount", 229_000_000.0)),
    "KVUE": (("CashAndCashEquivalentsAtCarryingValue", 1_110_000_000.0), ("DebtLongtermAndShorttermCombinedAmount", 8_480_000_000.0), ("OtherShortTermBorrowings", 3_000_000.0), ("PreferredStockValue", 0.0)),
    "SOLV": (("CashAndCashEquivalentsAtCarryingValue", 403_000_000.0), ("DebtInstrumentCarryingAmount", 5_083_000_000.0), ("FinanceLeaseLiability", 209_000_000.0), ("LossContingencyAccrualAtCarryingValue", 235_000_000.0)),
}


SHARE_STARTS = {"ABBV": "2026-01-01", "ZTS": "2026-01-01", "MDT": "2025-04-26", "STE": "2026-04-01", "VTRS": "2026-01-01", "GEHC": "2026-01-01", "KVUE": "2025-12-29", "SOLV": "2026-01-01"}
SHARE_ENDS = {"ABBV": "2026-07-27", "ZTS": "2026-07-31", "MDT": "2026-06-12", "STE": "2026-08-04", "VTRS": "2026-08-03", "GEHC": "2026-07-22", "KVUE": "2026-07-31", "SOLV": "2026-07-31"}


EVENTS = {
    "ABBV": {"matter": "patent, acquisition, IPR&D, contingent-consideration, and product-liability state", "reported_terms": {"h1_acquired_iprd_and_milestones_usd": 1_035_000_000.0, "litigation_reserve_usd": 1_700_000_000.0}},
    "ZTS": {"matter": "ordinary legal contingencies", "reported_terms": {"management_assessment": "not expected to have a material adverse effect on financial position"}},
    "MDT": {"matter": "MiniMed IPO and continuing control", "reported_terms": {"ipo_completed": "2026-03-09", "ownership_ratio": 0.9003, "accounting_state": "consolidated"}},
    "STE": {"matter": "small current acquisitions and ordinary claims", "reported_terms": {"current_quarter_business_acquisition_cash_usd": 16_000_000.0, "management_assessment": "pending lawsuits and claims not expected to be materially adverse as a whole"}},
    "VTRS": {"matter": "portfolio restructuring, divestitures, and opioid indemnification dispute", "reported_terms": {"pfizer_share_of_covered_opioid_losses_ratio": 0.57, "payment_disputed": True}},
    "GEHC": {"matter": "post-spin acquisitions, tariffs, and legal exposure", "reported_terms": {"h1_tariff_operating_income_impact_usd": 156_000_000.0, "unquantified_legal_matter_could_be_material": True}},
    "KVUE": {"matter": "pending Kimberly-Clark transaction and legacy consumer-health claims", "reported_terms": {"merger_agreement_date": "2025-11-02", "valuation_state": "current_pre_transaction_standalone"}},
    "SOLV": {"matter": "post-spin Acera integration and Bair Hugger indemnification", "reported_terms": {"spin_date": "2024-04-01", "acera_acquired": "2025-12", "bair_hugger_uninsured_liability_indemnified_to_3m": True}},
}


def _gehc_config() -> dict[str, Any]:
    config = deepcopy(load_concept_config())
    concepts = config["fields"]["interest_expense"]["concepts"]
    if "InterestAndDebtExpense" not in concepts:
        concepts.append("InterestAndDebtExpense")
    return config


def _bridge(ticker: str, structural: dict[str, Any], policy: Policy) -> list[dict[str, Any]]:
    rows = [_point(structural, name=name, expected=value, period_end=policy.period) for name, value in POINT_SPECS[ticker]]
    rows.extend((_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=max(policy.shares), period_start=SHARE_STARTS[ticker], period_end=policy.period), _share_point(structural, expected=min(policy.shares), end=SHARE_ENDS[ticker]), _no_preferred(structural, policy.period)))
    if ticker == "ABBV":
        contingent = _dimension_fact(structural, name="BusinessCombinationContingentConsiderationLiability", expected=27_495_000_000.0, start=None, end=policy.period, member="FairValueInputsLevel3Member")
        contingent["treatment"] = "Recorded as a load-bearing operating-claim diagnostic but not bridge-deducted again because ongoing contingent payments remain in the reported after-payment cash history and normalized FCFF."
        rows.append(contingent)
    return rows


def _abbv_financing_event(event_root: Path) -> dict[str, Any]:
    packet = Path(event_root) / "ABBV"
    receipt = json.loads((packet / "source-receipt.json").read_text())
    document = packet / receipt["primary_document"]
    if receipt.get("schema_version") != "FINSIGHT-BATCH-17-EVENT-SOURCE-1" or receipt.get("valuation_date") != BATCH_17_VALUATION_DATE or receipt.get("accession") != "0001104659-26-091269" or receipt.get("filed") > BATCH_17_VALUATION_DATE or hashlib.sha256(document.read_bytes()).hexdigest() != receipt.get("document_sha256"):
        raise ValueError("ABBV financing-event source invalid")
    terms = receipt["reported_terms"]
    if terms.get("aggregate_principal_usd") != 10_000_000_000.0 or terms.get("expected_net_proceeds_usd") != 9_930_000_000.0 or terms.get("expected_close_date") != "2026-08-18" or terms.get("cutoff_status") != "signed_not_closed_not_issued":
        raise ValueError("ABBV financing-event terms changed")
    return {"source_kind": "sec_current_report", "accession": receipt["accession"], "filed": receipt["filed"], "form": receipt["form"], "period_end": receipt["report_date"], "url": receipt["url"], "document_sha256": receipt["document_sha256"], "reported_terms": terms, "treatment": receipt["treatment"], "reported_vs_estimated": "reported"}


def _operating_result(*, ticker: str, filing: dict[str, Any], structural: dict[str, Any], submissions: dict[str, Any], facts: dict[str, Any], event_root: Path) -> dict[str, Any]:
    policy = P[ticker]
    normalizer = _normalizer(submissions, facts, concept_config=_gehc_config() if ticker == "GEHC" else None)
    flows = {name: normalizer.ttm_flow(name) for name in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    try:
        tax_rate, tax_rows = _normalized_tax_rate(normalizer)
    except ValueError:
        tax_rate, tax_rows = 0.21, ()
    if tax_rate < 0.05:
        tax_rate = 0.21
    current_cash = cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]), capital_expenditures=float(flows["capital_expenditures"]["value"]), spectrum_investment=0.0, interest_expense=abs(float(flows["interest_expense"]["value"])), tax_rate=tax_rate)
    annual = _annual_cash_with_losses(normalizer)[2]
    sources = [dict(row) for flow in flows.values() for row in flow.get("sources", []) if isinstance(row, dict)]
    revenue = float(flows["revenue"]["value"])
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=revenue, ttm_cash_fcff=current_cash, ttm_period_end=policy.period, ttm_sources=sources, valuation_date=BATCH_17_VALUATION_DATE)
    cash_metric, growth_metric = profile.metric("cash_conversion_margin"), profile.metric("revenue_growth")
    if not profile.full_history or cash_metric is None or growth_metric is None:
        raise ValueError(f"{ticker}: comparable history unavailable")
    margins = tuple(max(0.001, value) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    growth = (max(-0.10, min(policy.growth[0], growth_metric.low)), max(-0.08, min(policy.growth[1], growth_metric.base)), max(0.0, min(policy.growth[2], growth_metric.high)))
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(cash_fcff=revenue * margins[index], initial_growth=growth[index], terminal_growth=policy.terminal[index], wacc=policy.wacc[index], cash_and_investments=policy.cash, interest_bearing_debt=policy.debt, preferred_equity=0.0, noncontrolling_interests=policy.claims[index], diluted_shares=policy.shares[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "conditional_value_per_share": max(0.0, raw), "raw_value_per_share": raw, "starting_cash_fcff": state.cash_fcff, "cash_conversion_margin": margins[index], "growth": growth[index], "wacc": policy.wacc[index], "terminal_growth": policy.terminal[index], "cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims[index], "shares": policy.shares[index], "limited_liability_floor_applied": raw < 0.0})
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0.0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0.0:
        raise ValueError(f"{ticker}: invalid operating range")
    is_pass = ticker in PASS_TICKERS
    reasons = () if is_pass else ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="High" if is_pass else "Low", source_cap="High", reasons=reasons)
    public_history = profile.public_metadata()
    if not is_pass:
        public_history.update({"normalization_basis": "company_history_with_named_material_dependency", "assumption_source_mix": "reported_history_and_finsight_policy"})
    assumptions = {**public_history, "forecast_years": FORECAST_YEARS, "cash_conversion_margin": margins, "growth": growth, "wacc": policy.wacc, "terminal_growth": policy.terminal, "shares": policy.shares, "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0.0 else "not applied", "unquantified_legal_loss_amount": None if ticker in {"ABBV", "VTRS", "GEHC", "KVUE", "SOLV"} else "not_applicable", "unquantified_legal_loss_assumed_zero": False, "calculator_calibration": "Calculator is calibrated to the exact faded-cash base; private bridge and event schedules remain fixed.", "invalidation": policy.invalidation}
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_17_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked annual and current cash conversion anchors the scenarios."), BaselineAssumption("faded operating states", str({"growth": growth, "wacc": policy.wacc, "terminal": policy.terminal}), AssumptionClassification.FINSIGHT_ASSUMPTION, "Growth fades over eight years to a governed terminal state.")), warnings=(policy.warning, policy.invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link=f"/api/us-valuations/{ticker}/calculator")
    event = {"source_kind": "controlling_filing_narrative", "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "reported_vs_estimated": "reported_narrative", **EVENTS[ticker]}
    event_sources = [event, *([_abbv_financing_event(event_root)] if ticker == "ABBV" else [])]
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_17_HISTORY_VERSION, "availability_type": "available" if is_pass else "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": revenue, "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": flows["interest_expense"]["value"], "ttm_cash_fcff": current_cash}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "tax_rate_sources": list(tax_rows), "company_history_profile": profile.as_private_dict(), "bridge_sources": _bridge(ticker, structural, policy), "event_sources": event_sources, "bridge_reconciliation": {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims, "other_equity_claim_formula": policy.claim_formula, "shares": policy.shares, "operating_liability_treatment": "Ordinary operating liabilities remain inside cash conversion and are not deducted again.", "contingent_consideration_treatment": "ABBV only: $27.495B current liability is not bridge-deducted because historical/TTM normalized FCFF remains after ongoing contingent cash payments; material changes invalidate the baseline." if ticker == "ABBV" else "not_applicable"}, "model_trace": {"forecast_years": FORECAST_YEARS, "states": traces}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": policy.warning, "baseline": baseline.as_private_dict()}


def _mrna_result(filing: dict[str, Any], structural: dict[str, Any], submissions: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    normalizer = _normalizer(submissions, facts)
    revenue, operating, capex = (normalizer.ttm_flow(field) for field in ("revenue", "operating_cash_flow", "capital_expenditures"))
    annual_burn = []
    observations = []
    for year in (2023, 2024, 2025):
        end = f"{year}-12-31"
        ocf, reinvestment = normalizer.annual_at_end("operating_cash_flow", end), normalizer.annual_at_end("capital_expenditures", end)
        if ocf is None or reinvestment is None:
            raise ValueError("MRNA burn history incomplete")
        burn = max(0.0, -(float(ocf.value) - float(reinvestment.value)))
        annual_burn.append(burn)
        observations.append(HistoryObservation("annual", end, year, burn, "USD", "max(0, -(operating cash flow - capex))", (ocf.as_dict(), reinvestment.as_dict())))
    ttm_burn = max(0.0, -(float(operating["value"]) - float(capex["value"])))
    observations.append(HistoryObservation("operating_ttm", "2026-06-30", None, ttm_burn, "USD", "max(0, -(TTM operating cash flow - TTM capex))", tuple(dict(row) for flow in (operating, capex) for row in flow["sources"])))
    metric = summarize_history_metric("cash_burn", observations)
    if metric is None:
        raise ValueError("MRNA burn metric unavailable")
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "pipeline_cash_runway_equity", BATCH_17_VALUATION_DATE, ("2023-12-31", "2024-12-31", "2025-12-31"), (metric,), True, "reported_and_company_history")
    liquid_assets, debt_and_leases = 6_910_000_000.0, 628_000_000.0
    shares = _shares(396_000_000.0, 399_235_889.0)
    median_recent_burn = sorted(annual_burn)[1]
    burn_reserve = (median_recent_burn * 3.0, ttm_burn * 2.0, ttm_burn)
    rows = []
    for index, name in enumerate(("bear", "base", "bull")):
        raw_equity = liquid_assets - debt_and_leases - burn_reserve[index]
        raw = raw_equity / shares[index]
        rows.append({"name": name, "conditional_value_per_share": max(0.0, raw), "raw_value_per_share": raw, "liquid_assets": liquid_assets, "debt_and_finance_leases": debt_and_leases, "cash_burn_reserve": burn_reserve[index], "shares": shares[index], "pipeline_terminal_value": 0.0, "limited_liability_floor_applied": raw < 0.0})
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0.0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0.0:
        raise ValueError("MRNA runway range invalid")
    reasons = ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    warning = "Conditional Low pipeline cash-runway baseline. It values current liquid assets after debt and governed cash-burn reserves; it assigns no invented pipeline terminal value and can materially understate successful products or overstate value if burn persists."
    invalidation = "Invalidate if product revenue, pipeline approvals, annual cash burn, investments, commitments, debt/leases, or shares changes materially."
    assumptions = {**profile.public_metadata(), "normalization_basis": "liquid_assets_less_debt_and_governed_cash_burn", "assumption_source_mix": "reported_liquid_assets_debt_burn_history_and_finsight_policy", "cash_burn_reserve": burn_reserve, "shares": shares, "pipeline_terminal_value": 0.0, "pipeline_terminal_value_status": "not_modeled_not_missing_value_substitution", "equity_floor_basis": "limited-liability bear floor with raw negative retained", "calculator_calibration": "Calculator uses operating-style sensitivity around the published runway baseline; liquid assets, debt, and private burn schedule remain fixed.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker="MRNA", method="pipeline_cash_runway_equity_baseline", method_version=BATCH_17_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported liquid assets", liquid_assets, AssumptionClassification.REPORTED, "Cash and current/noncurrent AFS securities at June 30, 2026."), BaselineAssumption("cash-burn reserve", str(burn_reserve), AssumptionClassification.FINSIGHT_ASSUMPTION, "Recent reported burn and current TTM burn set the runway reserve; no pipeline success is invented.")), warnings=(warning, invalidation), confidence_reasons=reasons, calculator_link="/api/us-valuations/MRNA/calculator")
    bridge = [_point(structural, name="CashAndCashEquivalentsAtCarryingValue", expected=1_723_000_000.0, period_end="2026-06-30"), _point(structural, name="AvailableForSaleSecuritiesDebtSecuritiesCurrent", expected=3_415_000_000.0, period_end="2026-06-30"), _point(structural, name="AvailableForSaleSecuritiesDebtSecuritiesNoncurrent", expected=1_772_000_000.0, period_end="2026-06-30"), _point(structural, name="LongTermDebtNoncurrent", expected=591_000_000.0, period_end="2026-06-30"), _point(structural, name="FinanceLeaseLiability", expected=37_000_000.0, period_end="2026-06-30"), _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=396_000_000.0, period_start="2026-01-01", period_end="2026-06-30"), _share_point(structural, expected=399_235_889.0, end="2026-07-24"), _point(structural, name="PreferredStockValue", expected=0.0, period_end="2026-06-30")]
    return {"ticker": "MRNA", "method": baseline.method, "model_version": BATCH_17_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": revenue["value"], "ttm_operating_cash_flow": operating["value"], "ttm_reinvestment": capex["value"], "ttm_cash_burn": ttm_burn, "liquid_assets": liquid_assets, "debt_and_finance_leases": debt_and_leases}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": {"revenue": revenue, "operating_cash_flow": operating, "capital_expenditures": capex}, "company_history_profile": profile.as_private_dict(), "bridge_sources": bridge, "event_sources": [{"source_kind": "controlling_filing_narrative", "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "matter": "pipeline products and current cash runway", "reported_terms": {"liquid_assets_usd": liquid_assets, "h1_liquid_asset_decline_usd": 1_200_000_000.0, "pending_legal_matters_expected_material": False}, "reported_vs_estimated": "reported_narrative"}], "bridge_reconciliation": {"liquid_assets": liquid_assets, "debt_and_finance_leases": debt_and_leases, "cash_burn_reserve": burn_reserve, "pipeline_terminal_value": 0.0, "pipeline_value_treatment": "No value assigned; this is an explicit model scope, not substitution for a missing reported value.", "shares": shares}, "model_trace": {"states": rows}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def _ci_result(filing: dict[str, Any], structural: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    gaap = facts["facts"]["us-gaap"]
    common = annual_facts(gaap, concepts=("NetIncomeLossAvailableToCommonStockholdersBasic",), unit="USD", valuation_date=BATCH_17_VALUATION_DATE)
    parent = annual_facts(gaap, concepts=("NetIncomeLoss",), unit="USD", valuation_date=BATCH_17_VALUATION_DATE)
    observations = []
    for year in (2021, 2022, 2023, 2024):
        fact = common[year]
        observations.append(HistoryObservation("annual", fact.period_end, year, fact.value, "USD", "reported common-stockholder earnings", (_history_source(fact),)))
    fact_2025 = parent[2025]
    observations.append(HistoryObservation("annual", fact_2025.period_end, 2025, fact_2025.value, "USD", "reported parent-attributable earnings", (_history_source(fact_2025),)))
    current = _structural_flow(structural, name="NetIncomeLoss", start="2026-01-01", end="2026-06-30", expected=3_314_000_000.0)
    prior = _structural_flow(structural, name="NetIncomeLoss", start="2025-01-01", end="2025-06-30", expected=2_855_000_000.0)
    ttm = fact_2025.value + current["value"] - prior["value"]
    observations.append(HistoryObservation("operating_ttm", "2026-06-30", None, ttm, "USD", "latest FY + current H1 - prior H1 parent earnings", (_history_source(fact_2025), current, prior)))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    if metric is None:
        raise ValueError("CI earnings history unavailable")
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "managed_care_residual_income", BATCH_17_VALUATION_DATE, tuple(row.period_end for row in observations if row.period_role == "annual"), (metric,), True, "reported_and_company_history")
    beginning_equity, ending_equity = 41_713_000_000.0, 42_620_000_000.0
    average_equity = (beginning_equity + ending_equity) / 2.0
    shares = _shares(263_990_000.0, 264_240_486.0)
    earnings = (metric.low, metric.base, metric.high)
    dividends = 824_000_000.0
    payout = min(1.0, dividends * 2.0 / ttm)
    cost_of_equity, terminal_roe, terminal_growth = (0.12, 0.10, 0.085), (0.07, 0.11, 0.15), (0.01, 0.02, 0.025)
    rows, traces, multiples = [], {}, []
    for index, name in enumerate(("bear", "base", "bull")):
        trace = residual_income_valuation(book_value_per_share=ending_equity / shares[index], current_roe=earnings[index] / average_equity, cost_of_equity=cost_of_equity[index], current_payout_ratio=payout, terminal_roe=terminal_roe[index], terminal_growth=terminal_growth[index], years=5)
        raw = float(trace["intrinsic_value"])
        multiple = raw * shares[index] / earnings[index]
        rows.append({"name": name, "conditional_value_per_share": raw, "raw_value_per_share": raw, "normalized_common_earnings": earnings[index], "book_value_per_share": ending_equity / shares[index], "current_roe": earnings[index] / average_equity, "current_payout_ratio": payout, "cost_of_equity": cost_of_equity[index], "terminal_roe": terminal_roe[index], "terminal_growth": terminal_growth[index], "earnings_multiple": multiple, "shares": shares[index], "limited_liability_floor_applied": False})
        traces[name], multiples = trace, [*multiples, multiple]
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0.0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError("CI range invalid")
    reasons = ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    warning = "Conditional Low managed-care and pharmacy-services residual-income baseline. Common equity and parent earnings are source linked, while medical claims, regulated capital, Evernorth mix, and the planned Individual and Family Plans exit remain material."
    invalidation = "Invalidate if common equity/earnings, medical claims, regulated capital, Evernorth economics, IFP exit, payout, or shares changes materially."
    assumptions = {**profile.public_metadata(), "normalization_basis": "reported_common_equity_and_history_residual_income", "assumption_source_mix": "reported_common_equity_earnings_dividends_and_finsight_policy", "normalized_common_earnings": earnings, "earnings_multiples": tuple(multiples), "shares": shares, "book_equity": ending_equity, "average_common_equity": average_equity, "current_payout_ratio": payout, "cost_of_equity": cost_of_equity, "terminal_roe": terminal_roe, "terminal_growth": terminal_growth, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "equity_floor_basis": "not applied", "calculator_calibration": "Calculator varies normalized common earnings and the residual-income-implied multiple around the published base.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker="CI", method="managed_care_pharmacy_residual_income_equity_earnings", method_version=BATCH_17_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported common equity", ending_equity, AssumptionClassification.REPORTED, "Current parent equity supplies the residual-income anchor."), BaselineAssumption("company earnings history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Parent/common earnings history supplies the ROE range.")), warnings=(warning, invalidation), confidence_reasons=reasons, calculator_link="/api/us-valuations/CI/calculator")
    context = [_point(structural, name="StockholdersEquity", expected=beginning_equity, period_end="2025-12-31"), _point(structural, name="StockholdersEquity", expected=ending_equity, period_end="2026-06-30"), _point(structural, name="InsuranceAndContractholderLiabilities", expected=16_322_000_000.0, period_end="2026-06-30"), _point(structural, name="MinorityInterest", expected=290_000_000.0, period_end="2026-06-30"), _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=263_990_000.0, period_start="2026-01-01", period_end="2026-06-30"), _share_point(structural, expected=264_240_486.0, end="2026-07-24"), _structural_flow(structural, name="DividendsCommonStockCash", start="2026-01-01", end="2026-06-30", expected=dividends), _no_preferred(structural, "2026-06-30")]
    return {"ticker": "CI", "method": baseline.method, "model_version": BATCH_17_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_common_earnings": ttm, "beginning_common_equity": beginning_equity, "ending_common_equity": ending_equity, "h1_common_dividends": dividends}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "company_history_profile": profile.as_private_dict(), "equity_model_context": context, "event_sources": [{"source_kind": "controlling_filing_narrative", "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "matter": "managed-care/pharmacy mix and planned IFP exit", "reported_terms": {"ifp_exit_effective": "2027-01-01", "h1_medical_care_ratio": 0.822}, "reported_vs_estimated": "reported_narrative"}], "residual_income_trace": {"states": traces}, "bridge_treatment": "Equity-level managed-care model; insurance liabilities, medical claims, investments, debt, regulated capital, and NCI remain inside parent earnings/common equity and are not EV-bridged.", "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def build_batch_17_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_17_TICKERS:
        raise ValueError(f"unexpected Batch 17 ticker {ticker}")
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural["source_accession"] != filing["accession"]:
        raise ValueError(f"{ticker}: controlling source mismatch")
    if ticker == "MRNA":
        return _mrna_result(filing, structural, submissions, facts)
    if ticker == "CI":
        return _ci_result(filing, structural, facts)
    if filing["period_end"] != P[ticker].period:
        raise ValueError(f"{ticker}: period mismatch")
    return _operating_result(ticker=ticker, filing=filing, structural=structural, submissions=submissions, facts=facts, event_root=event_root)


if set(P) | {"MRNA", "CI"} != set(BATCH_17_TICKERS):
    raise RuntimeError("Batch 17 denominator mismatch")
