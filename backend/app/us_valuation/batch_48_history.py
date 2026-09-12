"""Source-bounded practical REIT baselines for controlled Universe Reset Batch 48."""
from __future__ import annotations

import hashlib
import json
from html import unescape
from pathlib import Path
import re
from statistics import median
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_04_launch_first import _controlling
from .batch_35_history import _instant
from .batch_40_history import _latest_shares
from .batch_46_history import _annual_fact, _combine, _structural_flow
from .batch_48 import BATCH_48_MANIFEST, BATCH_48_TICKERS, BATCH_48_VALUATION_DATE
from .batch_48_sources import verify_source_bundle
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf, two_stage_cash_flow_value
from .reliability import assess_reliability

BATCH_48_HISTORY_VERSION = "BATCH-48-REIT-AFFO-CYCLE-1.0"
PERIOD = "2026-06-30"
PASS_TICKERS = frozenset()
WITHHELD_TICKERS = frozenset({"WY", "EQR"})
CONDITIONAL_TICKERS = frozenset(set(BATCH_48_TICKERS) - WITHHELD_TICKERS)

# Reported issuer measures are copied from the named cutoff-safe SEC-filed
# earnings exhibits. Recurring-cost ratios are either issuer-derived or a
# transparent Batch 48 peer range, never a missing-value zero.
REIT_INPUTS: dict[str, dict[str, Any]] = {
    "FRT": {"accession": "0000034903-26-000040", "document": "frt-6302026xex991.htm", "flow_name": "2026 Core FFO per diluted share", "flow": (7.48, 7.52, 7.56), "cost": (0.185, 53.590 / 325.348, 0.145), "cost_basis": "H1 maintenance capital plus tenant improvements/incentives divided by H1 Core FFO; bounded for timing.", "cost_source": {"reported_numerator": 53_590_000.0, "reported_denominator": 325_348_000.0, "formula": "(H1 maintenance capital 10.495m + tenant improvements/incentives 43.095m) / H1 Core FFO 325.348m", "accession": "0000034903-26-000040", "document": "frt-6302026xex991.htm", "unit": "ratio"}, "event_burden_per_share": (16.1 / 86.733, 14.0 / 86.733, 0.0), "event_dilution_factor": (1 + 3.901260 / 86.733, 1 + 1.950630 / 86.733, 1.0), "event_burden_source": {"accession": "0001193125-26-344547", "filed": "2026-08-11", "principal": 460_000_000.0, "coupon": 0.035, "initial_maximum_exchange_shares": 3_901_260.0, "h1_diluted_shares": 86_733_000.0, "treatment": "Bear assumes maximum exchange dilution and full $16.1m annual coupon burden; base assumes half maximum dilution and $14m base-principal coupon; bull assumes debt repayment and capped calls offset incremental burden. No refinancing benefit is added.", "reported_vs_estimated": "reported_terms_with_governed_bounded_treatment"}},
    "UDR": {"accession": "0000074208-26-000070", "document": "udr-20260727xex99d1.htm", "flow_name": "2026 FFOA per diluted share", "flow": (2.49, 2.53, 2.57), "cost": (0.13, 1 - 1.11 / 1.25, 0.095), "cost_basis": "H1 reported AFFO $1.11 divided by H1 FFOA $1.25, with a bounded recurring-cost range.", "cost_source": {"reported_affo_per_share": 1.11, "reported_ffoa_per_share": 1.25, "formula": "1 - H1 AFFO per share / H1 FFOA per share", "accession": "0000074208-26-000070", "document": "udr-20260727xex99d2.htm", "unit": "ratio"}},
    "VTR": {"accession": "0000740260-26-000022", "document": "q22026earningsrelease.htm", "flow_name": "2026 Normalized FFO per diluted share", "flow": (3.85, 3.875, 3.90), "cost": (0.13, 0.11, 0.09), "cost_basis": "Batch 48 issuer-reported recurring-capital ratios bound missing exact SHOP/triple-net AFFO detail."},
    "DOC": {"accession": "0001628280-26-052608", "document": "ex99106302026.htm", "flow_name": "2026 FFO as Adjusted per diluted share", "flow": (1.73, 1.75, 1.77), "cost": (0.12, 66.061 / 633.381, 0.09), "cost_basis": "H1 AFFO capital expenditures divided by H1 FFO as Adjusted, with a bounded timing range.", "cost_source": {"reported_numerator": 66_061_000.0, "reported_denominator": 633_381_000.0, "formula": "H1 AFFO capital expenditures / H1 FFO as Adjusted", "accession": "0001628280-26-052608", "document": "ex99106302026.htm", "unit": "ratio"}},
    "WELL": {"accession": "0000766704-26-000026", "document": "a2q26earningsrelease991.htm", "flow_name": "2026 Normalized FFO per diluted share", "flow": (6.36, 6.40, 6.44), "cost": (0.11, 465 / 4_743, 0.09), "cost_basis": "Current outlook recurring capex, tenant improvements and lease commissions divided by Normalized FFO.", "cost_source": {"reported_numerator": 465_000_000.0, "reported_denominator": 4_743_000_000.0, "formula": "2026 recurring capex/TI/lease commissions / midpoint Normalized FFO", "accession": "0000766704-26-000026", "document": "a2q26earningsrelease991.htm", "unit": "ratio"}},
    "KIM": {"accession": "0001193125-26-331498", "document": "kim-ex99_1.htm", "flow_name": "2026 FFO per diluted share", "flow": (1.83, 1.835, 1.84), "cost": (0.13, 0.11, 0.09), "cost_basis": "Batch 48 issuer-reported recurring-capital ratios bound missing exact current AFFO; diluted FFO includes convertible preferred treatment."},
    "CPT": {"accession": "0001628280-26-051083", "document": "exhibit992supplement2q26.htm", "flow_name": "2026 Core FFO per diluted share", "flow": (6.68, 6.75, 6.82), "cost": (0.15, 1 - 2.95 / 3.39, 0.11), "cost_basis": "H1 reported Core AFFO $2.95 divided by Core FFO $3.39, with timing sensitivity.", "cost_source": {"reported_affo_per_share": 2.95, "reported_ffo_per_share": 3.39, "formula": "1 - H1 Core AFFO per share / H1 Core FFO per share", "accession": "0001628280-26-051083", "document": "exhibit992supplement2q26.htm", "unit": "ratio"}, "value_adjustment_per_share": -53_000_000 / 105_218_000, "value_adjustment_source": {"accession": "0001628280-26-051083", "filed": "2026-07-30", "claim": 53_000_000.0, "share_denominator": 105_218_000.0, "formula": "July litigation settlement / H1 diluted FFO shares", "treatment": "Deduct once from equity value because issuer Core FFO/Core AFFO excludes the cash settlement.", "reported_vs_estimated": "reported_claim_and_share_denominator"}},
    "IRM": {"accession": "0001020569-26-000068", "document": "final-q22026earningspres.htm", "flow_name": "2026 AFFO per diluted share", "flow": (5.87, 5.90, 5.93), "cost": (0.0, 0.0, 0.0), "cost_basis": "Issuer-reported AFFO already deducts recurring capital; no second recurring-capital deduction.", "cost_source": {"reported_affo_range": (5.87, 5.90, 5.93), "formula": "No second deduction from issuer-defined AFFO", "accession": "0001020569-26-000068", "document": "final-q22026earningspres.htm", "unit": "USD/share"}},
}

PEER_COST_EVIDENCE = {
    "method": "bounded range across Batch 48 issuer-reported recurring-capital conversions",
    "ratios": {"UDR": 1 - 1.11 / 1.25, "DOC": 66.061 / 633.381, "WELL": 465 / 4_743, "CPT": 1 - 2.95 / 3.39},
    "selected_range": (0.13, 0.11, 0.09),
    "reported_vs_estimated": "derived_reported_peer_components_and_governed_bounds",
}

EVENT_MODEL_TREATMENTS = {
    "FRT": "The August 11 notes are quantified through a coupon and maximum-exchange dilution sensitivity; debt-repayment or capped-call benefit is not added.",
    "UDR": "The July earnings outlook is the selected forward operating input; no unclosed development or disposition value is added.",
    "VTR": "The July earnings outlook includes announced/closed investment activity; incomplete SHOP/triple-net recurring capital remains in the Low cap.",
    "DOC": "The August guidance and H1 AFFO-capex evidence use the current Healthpeak economic scope; merger/JV integration remains a Low-cap warning.",
    "WELL": "The July 27 release reports the C$1.15B note issuance and states that guidance includes announced or closed acquisitions and no unannounced capital activity; no second overlay is added.",
    "KIM": "The August 4 raised outlook follows the $600M exchangeable-note issue and related common/preferred repurchases. The selected FFO numerator and diluted denominator use the issuer's as-converted preferred treatment, so the $553.196M liquidation preference is not deducted again.",
    "CPT": "The July 30 guidance reflects the July 29 California sale and excludes its gain; $0.9B intended debt repayment is not treated as surplus value. The excluded $53M settlement is deducted once per diluted share.",
    "IRM": "The August 5 AFFO guidance follows the July leasing update; reported AFFO already deducts recurring capital and no second deduction is made.",
}

WARNINGS = {
    "FRT": "Conditional Low retail-REIT AFFO proxy. The base normalized cash flow deducts the August notes' $14M annual coupon and half the maximum exchange dilution; full-effect and no-effect cases remain private input sensitivities, while the public range varies only the discount rate.",
    "UDR": "Conditional Low multifamily-REIT AFFO baseline. The current AFFO-to-FFOA conversion is applied to 2026 guidance; development, concessions, dispositions and JV debt can change the result.",
    "WY": "Withheld: current timber-cycle cash conversion produces a negative bear equity residual, while land and standing-timber value, harvest normalization, reforestation/environmental obligations and preferred/NCI scope are not sufficiently source-bounded for a public baseline.",
    "VTR": "Conditional Low healthcare-REIT cash baseline. Reported Normalized FFO is reduced by an evidence-bounded recurring-capital range because SHOP and triple-net maintenance detail is incomplete.",
    "DOC": "Conditional Low healthcare-REIT AFFO proxy. Reported FFO as Adjusted is reduced by reported AFFO capital expenditure; merger integration, JV scope and asset sales remain material.",
    "WELL": "Conditional Low healthcare-REIT AFFO proxy. Reported Normalized FFO is reduced by disclosed recurring capex, tenant improvements and lease commissions; financing, acquisitions and dispositions remain material.",
    "KIM": "Conditional Low retail-REIT AFFO proxy. Reported FFO is reduced by a peer-bounded recurring-capital range and uses the issuer's as-converted preferred numerator and diluted denominator, so preferred liquidation is not deducted again; exchangeable notes, redevelopment and JV scope remain material.",
    "EQR": "Withheld: the AvalonBay merger was shareholder-approved on August 12 and expected to close August 17. Standalone EQR guidance was withdrawn, while the combined Vivmark economic object was not yet closed at the August 14 valuation cutoff.",
    "CPT": "Conditional Low multifamily-REIT AFFO baseline. Reported Core AFFO conversion is applied to 2026 Core FFO guidance; the July California sale, debt repayment and litigation settlement remain material.",
    "IRM": "Conditional Low specialized-REIT AFFO baseline. Reported AFFO supports a finite value, but data-center growth capex, records-storage economics, leases, debt and negative common book equity remain material.",
}


def _events(ticker: str, root: Path, manifest_sha: str) -> dict[str, Any]:
    inventory_path = root / ticker / "inventory.json"
    rows = json.loads(inventory_path.read_text())
    if not rows or any(row.get("filed", "") > BATCH_48_VALUATION_DATE for row in rows):
        raise ValueError(f"{ticker}: invalid event inventory")
    documents = []
    for row in rows:
        for document in row.get("documents", []):
            path = Path(document["path"])
            if not path.is_absolute():
                path = root.parent.parent / path
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != document.get("sha256"):
                raise ValueError(f"{ticker}: event hash mismatch")
            documents.append({**document, "accession": row["accession"], "filed": row["filed"], "form": row["form"]})
    return {"source_kind": "sec_event_screening", "screened_filings": rows, "documents": documents, "inventory_sha256": hashlib.sha256(inventory_path.read_bytes()).hexdigest(), "source_manifest_sha256": manifest_sha, "reported_vs_estimated": "reported_and_screened"}


def _specialist_source(ticker: str, event: dict[str, Any], event_root: Path) -> dict[str, Any]:
    spec = REIT_INPUTS[ticker]
    matches = [row for row in event["documents"] if row["accession"] == spec["accession"] and Path(row["path"]).name == spec["document"]]
    if len(matches) != 1:
        raise ValueError(f"{ticker}: specialist exhibit unresolved")
    row = matches[0]
    path = Path(row["path"])
    if not path.is_absolute():
        path = event_root.parent.parent / path
    text = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", path.read_text(errors="ignore")))).casefold()
    required = [str(value).casefold() for value in spec["flow"] if value != spec["flow"][1]]
    if not all(token in text for token in required):
        raise ValueError(f"{ticker}: specialist values not found in filed exhibit")
    return {"source_kind": "sec_filed_earnings_exhibit", "accession": spec["accession"], "filed": row["filed"], "period_end": PERIOD, "document": spec["document"], "sha256": row["sha256"], "metric": spec["flow_name"], "reported_low_base_high_per_share": spec["flow"], "unit": "USD/share", "reported_vs_estimated": "issuer_reported_guidance"}


def _reit_result(ticker: str, *, filing: dict[str, Any], verification: dict[str, Any], event: dict[str, Any], specialist: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    spec = REIT_INPUTS[ticker]
    event_burden = spec.get("event_burden_per_share", (0.0, 0.0, 0.0))
    dilution_factor = spec.get("event_dilution_factor", (1.0, 1.0, 1.0))
    input_cash_range = tuple((flow * (1 - cost) - burden) / dilution for flow, cost, burden, dilution in zip(spec["flow"], spec["cost"], event_burden, dilution_factor))
    cash = (input_cash_range[1],) * 3
    discounts = (0.0975, 0.0925, 0.0875)
    value_adjustment = float(spec.get("value_adjustment_per_share", 0.0))
    rows = []
    for name, owner_cash, discount in zip(("bear", "base", "bull"), cash, discounts):
        dcf_value = two_stage_cash_flow_value(cash_flow_per_share=owner_cash, growth_rate=0.02, growth_years=8, terminal_growth=0.02, discount_rate=discount)
        value = dcf_value + value_adjustment
        rows.append({"name": name, "reported_ffo_or_affo_per_share": spec["flow"][1], "recurring_cost_ratio": spec["cost"][1], "locked_base_event_interest_burden_per_share": event_burden[1], "locked_base_event_dilution_factor": dilution_factor[1], "normalized_affo_per_share": owner_cash, "growth_rate": 0.02, "forecast_years": 8, "terminal_growth": 0.02, "discount_rate": discount, "nonrecurring_value_adjustment_per_share": value_adjustment, "dcf_value_per_share_before_adjustment": dcf_value, "conditional_value_per_share": value, "raw_value_per_share": value})
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid REIT range")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("REPORTED_AFFO_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"))
    invalidation = "Revalue if reported FFO/AFFO, recurring-capital treatment, property/JV scope, preferred/NCI, dilution, leverage or cutoff events leave the bounded range."
    assumptions = {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 1, "forecast_years": 8, "normalization_basis": "cutoff-safe issuer guidance or current run-rate reduced by source-linked or peer-bounded recurring capital", "assumption_source_mix": "issuer-reported SEC-filed guidance plus transparent recurring-capital, cutoff-event and discount-rate ranges", "reported_flow_per_share": spec["flow"], "recurring_cost_ratio": spec["cost"], "event_interest_burden_per_share": event_burden, "event_dilution_factor": dilution_factor, "input_normalized_affo_sensitivity": input_cash_range, "normalized_affo_per_share": cash, "growth_rate": (0.02, 0.02, 0.02), "discount_rate": discounts, "terminal_growth": (0.02, 0.02, 0.02), "nonrecurring_value_adjustment_per_share": (value_adjustment,) * 3, "equity_floor_basis": "not applied", "scenario_calibration": "one-driver public range: base normalized AFFO per share and any one-time claim deduction are held fixed while discount rate changes; input uncertainty remains a private diagnostic and no property NAV is blended into primary value", "calculator_calibration": "Public calculator independently replays the exact base AFFO DCF from locked normalized AFFO per share and value adjustment plus editable growth and discount assumptions.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker=ticker, method="reit_affo_per_share_dcf", method_version=BATCH_48_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(WARNINGS[ticker], invalidation))
    event_reconciliation = None if ticker != "FRT" else {"unadjusted_base_affo_per_share": spec["flow"][1] * (1 - spec["cost"][1]), "coupon_burden_per_share": event_burden[1], "dilution_factor": dilution_factor[1], "event_adjusted_base_affo_per_share": cash[1], "formula": "(base FFO/share x (1 - recurring-cost ratio) - $14m coupon / 86.733m H1 diluted shares) / (1 + half of 3.901260m maximum exchange shares / 86.733m H1 diluted shares)", "arithmetic_bound_to_public_base": True}
    return {"ticker": ticker, "method": "reit_affo_per_share_dcf", "model_version": BATCH_48_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"reported_flow_per_share": spec["flow"], "flow_metric": spec["flow_name"], "input_kind": "issuer_reported_guidance"}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "specialist_metric_source": specialist, "recurring_capital_basis": {"ratios": spec["cost"], "basis": spec["cost_basis"], "direct_source": spec.get("cost_source"), "peer_evidence": PEER_COST_EVIDENCE if ticker in {"VTR", "KIM"} else None, "reported_vs_estimated": "reported_or_governed_bounded_range", "missing_values_zero_imputed": False}, "cutoff_event_burden": spec.get("event_burden_source"), "event_adjustment_reconciliation": event_reconciliation, "nonrecurring_value_adjustment_source": spec.get("value_adjustment_source"), "event_model_treatment": EVENT_MODEL_TREATMENTS[ticker], "event_sources": event, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS[ticker], "baseline": baseline.as_private_dict()}


def _wy_result(*, facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], verification: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    annual = []
    for year in range(2021, 2026):
        ocf = _annual_fact(facts, "WY", ("NetCashProvidedByUsedInOperatingActivities",), year)
        capex = _annual_fact(facts, "WY", ("PropertyPlantAndEquipmentAdditions",), year)
        interest = _annual_fact(facts, "WY", ("InterestPaidNet",), year)
        fcff = ocf["value"] - capex["value"] + interest["value"] * 0.79
        annual.append({"period_end": f"{year}-12-31", "operating_cash_flow": ocf, "capital_expenditures": capex, "interest_paid": interest, "cash_fcff": fcff, "formula": "OCF - PP&E additions + 79% of interest paid"})
    current = {name: _structural_flow(structural, concepts, "2026-01-01", PERIOD) for name, concepts in {"ocf": ("NetCashProvidedByUsedInOperatingActivities",), "capex": ("PropertyPlantAndEquipmentAdditions",), "interest": ("InterestPaidNet",)}.items()}
    prior = {name: _structural_flow(structural, concepts, "2025-01-01", "2025-06-30") for name, concepts in {"ocf": ("NetCashProvidedByUsedInOperatingActivities",), "capex": ("PropertyPlantAndEquipmentAdditions",), "interest": ("InterestPaidNet",)}.items()}
    ttm = {name: annual[-1][{"ocf": "operating_cash_flow", "capex": "capital_expenditures", "interest": "interest_paid"}[name]]["value"] + current[name]["value"] - prior[name]["value"] for name in current}
    ttm_fcff = ttm["ocf"] - ttm["capex"] + ttm["interest"] * 0.79
    starting = (ttm_fcff, median(row["cash_fcff"] for row in annual[-3:]), median(row["cash_fcff"] for row in annual))
    cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), PERIOD)
    current_debt = _instant(structural, ("LongTermDebtExcludingLinesOfCreditCurrent",), PERIOD)
    noncurrent_debt = _instant(structural, ("LongTermDebtNoncurrent",), PERIOD)
    debt = _combine("current_plus_noncurrent_debt", [(current_debt, 1), (noncurrent_debt, 1)])
    shares = _latest_shares("WY", structural)
    share_states = (shares["value"] * 1.015, shares["value"], shares["value"] * 0.985)
    growth, wacc, terminal = (-0.02, 0.0, 0.02), (0.11, 0.10, 0.09), (0.0, 0.01, 0.015)
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(starting[index], growth[index], terminal[index], wacc[index], cash["value"], debt["value"], 0.0, 0.0, share_states[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "starting_cash_fcff": starting[index], "growth_rate": growth[index], "wacc": wacc[index], "terminal_growth": terminal[index], "cash": cash["value"], "debt": debt["value"], "preferred_and_nci": 0.0, "shares": share_states[index], "raw_value_per_share": raw, "conditional_value_per_share": max(0.0, raw), "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError("WY: invalid timber-cycle range")
    release = "Revalue only after timber/land economics, reforestation and environmental obligations, and preferred/NCI scope support a positive finite bear/base/bull range without a display floor."
    assumptions = {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 6, "forecast_years": 8, "normalization_basis": "TTM trough, median of latest three annual cash-FCFF states, and five-year annual median retained as private diagnostics", "assumption_source_mix": "reported cash-flow history and governed timber-cycle diagnostics", "starting_cash_fcff_diagnostic": starting, "growth_rate_diagnostic": growth, "wacc_diagnostic": wacc, "terminal_growth_diagnostic": terminal, "shares_diagnostic": share_states, "governed_tax_rate": 0.21, "tax_rate_basis": "governed federal-rate proxy used only in the private cash-FCFF diagnostic; not sufficient for publication", "equity_floor_basis": "not published; negative raw bear residual retained privately", "preferred_nci_status": "statement-scope search found no numeric claim, but absence is not sufficient for publication", "availability_separate_from_model_identity": True, "calculator_calibration": "Calculator unavailable while the timber specialist gate is open.", "invalidation": release}
    baseline = BaselineValuation(ticker="WY", method="timber_cycle_fcff", method_version=BATCH_48_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(WARNINGS["WY"], release))
    return {"ticker": "WY", "method": "timber_cycle_fcff", "model_version": BATCH_48_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {"ttm_operating_cash_flow": ttm["ocf"], "ttm_capital_expenditures": ttm["capex"], "ttm_interest_paid": ttm["interest"], "ttm_cash_fcff_diagnostic": ttm_fcff, "cash": cash["value"], "debt": debt["value"], "share_count": shares["value"]}, "governed_assumptions": assumptions, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "annual_cash_history": annual, "ttm_cash_reconstruction": {"latest_fy": annual[-1], "current_h1": current, "prior_h1": prior, "values": ttm, "cash_fcff_diagnostic": ttm_fcff}, "bridge_sources": {"cash": cash, "debt": debt, "preferred_and_nci_scope": assumptions["preferred_nci_status"], "shares": shares}, "event_sources": event, "private_pre_publication_diagnostic": {"scenario_range": scenario, "scenario_rows": rows, "model_trace": traces, "published": False}, "specialist_gate": {"passed": False, "reason": WARNINGS["WY"], "release_condition": release}, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS["WY"], "baseline": baseline.as_private_dict()}


def _eqr_withheld(*, filing: dict[str, Any], verification: dict[str, Any], event: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    merger = next((row for row in event["screened_filings"] if row["accession"] == "0001140361-26-032504"), None)
    if merger is None:
        raise ValueError("EQR: merger approval event absent")
    release = "Revalue only after a cutoff-safe closed-company filing or an approved explicit pre-close standalone policy reconciles the 2.793 exchange ratio, combined shares, pro forma earnings, debt and closing adjustments."
    baseline = BaselineValuation(ticker="EQR", method="reit_affo_per_share_dcf", method_version=BATCH_48_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(WARNINGS["EQR"], release))
    return {"ticker": "EQR", "method": "reit_affo_per_share_dcf", "model_version": BATCH_48_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {"standalone_h1_normalized_ffo_per_share_diagnostic": 2.01, "standalone_h1_recurring_capital_expenditures": 94_566_000.0}, "governed_assumptions": {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 1, "forecast_years": 8, "normalization_basis": "pending major corporate-event gate", "assumption_source_mix": "reported standalone and pro forma diagnostics; no published value", "equity_floor_basis": "not applied", "availability_separate_from_model_identity": True, "invalidation": release}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "cutoff_identity": {"ticker": "EQR", "cik": "0000906107", "name": "Equity Residential", "status": "standalone legal issuer at 2026-08-14"}, "merger_event": merger, "event_sources": event, "specialist_gate": {"passed": False, "reason": WARNINGS["EQR"], "release_condition": release}, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS["EQR"], "baseline": baseline.as_private_dict()}


def build_batch_48_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_48_TICKERS:
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
    event = _events(ticker, Path(event_root), verification["source_manifest_sha256"])
    if ticker == "EQR":
        return _eqr_withheld(filing=filing, verification=verification, event=event, structural=structural)
    if ticker == "WY":
        return _wy_result(facts=facts, structural=structural, filing=filing, verification=verification, event=event)
    specialist = _specialist_source(ticker, event, Path(event_root))
    return _reit_result(ticker, filing=filing, verification=verification, event=event, specialist=specialist, structural=structural)


if PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_48_TICKERS):
    raise RuntimeError("Batch 48 classification mismatch")
