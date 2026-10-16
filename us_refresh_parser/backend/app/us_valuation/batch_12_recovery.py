"""One source-bounded whole-batch recovery attempt for Universe Reset Batch 12."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from app.valuation.bank import residual_income_valuation

from .baseline import (
    AssumptionClassification,
    AvailabilityType,
    BaselineAssumption,
    BaselineValuation,
)
from .batch_02_practical_inputs import (
    _normalizer,
    _normalized_tax_rate,
    cash_fcff_from_reported,
)
from .batch_04_launch_first import _point
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_11_history import _dimension_fact
from .batch_12 import BATCH_12_TICKERS, BATCH_12_VALUATION_DATE
from .batch_12_history import P, build_batch_12_history_result
from .history import HISTORY_POLICY_VERSION, build_cash_fcff_history_profile
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_12_RECOVERY_VERSION = "BATCH-12-WHOLE-RECOVERY-1.0"
FORECAST_YEARS = 8
OPERATING_TICKERS = frozenset({"ABT", "BAX", "BDX", "BMY", "RVTY", "LLY", "WST"})
EQUITY_TICKERS = frozenset({"HUM", "CVS"})
WITHHELD_TICKERS = frozenset({"UHS"})


OPERATING_POLICY: dict[str, dict[str, Any]] = {
    "ABT": {
        "method": "post_exact_pro_forma_faded_cash_fcff",
        "growth": (0.02, 24.5 / 23.0 - 1.0, 0.09),
        "wacc": (0.115, 0.10, 0.09),
        "terminal": (0.01, 0.02, 0.025),
        "warning": "Conditional Low post-Exact recovery. Filed pro-forma combined scale closes the partial-revenue/full-debt mismatch, but integration, diagnostics cash conversion, R&D, debt, claims, and dilution remain material.",
        "invalidation": "Invalidate if filed post-Exact revenue/cash, acquisition accounting, debt, claims, R&D, capex, or diluted shares leaves the recorded range.",
    },
    "BAX": {
        "method": "post_disposition_claim_adjusted_faded_cash_fcff",
        "growth": (0.00, 0.03, 0.05),
        "wacc": (0.115, 0.10, 0.09),
        "terminal": (0.01, 0.02, 0.025),
        "warning": "Conditional Low post-disposition recovery. Continuing cash is retained, while all reported contingent/separation claims, uneven history, and the governed 21% tax policy remain explicit.",
        "invalidation": "Invalidate if continuing-operation scope, retained separation claims, tax normalization, debt/leases, cash conversion, or shares changes.",
    },
    "BDX": {
        "method": "post_spin_continuing_faded_cash_fcff",
        "growth": (0.02, 0.04, 0.06),
        "wacc": (0.12, 0.105, 0.095),
        "terminal": (0.01, 0.02, 0.025),
        "warning": "Conditional Low post-spin recovery. Continuing cash is source-linked and the spin distribution is not added twice; separation costs, impairment, R&D, and shorter post-spin history remain material.",
        "invalidation": "Invalidate if continuing cash scope, spin accounting, impairment, debt, capex, R&D, or shares changes.",
    },
    "BMY": {
        "method": "patent_pipeline_faded_cash_fcff",
        "growth": (-0.03, 0.00, 0.03),
        "wacc": (0.115, 0.10, 0.09),
        "terminal": (0.01, 0.02, 0.025),
        "warning": "Conditional Low pharmaceutical recovery. The faded cash model includes an explicit patent-loss downside and the CVR claim, while pipeline probability, pricing, litigation, R&D, and leverage remain material.",
        "invalidation": "Invalidate if patent/pipeline cash, pricing, litigation, R&D, debt, CVRs, capex, or shares changes.",
    },
    "RVTY": {
        "method": "acquisition_restructuring_faded_cash_fcff",
        "growth": (-0.03, 0.01, 0.04),
        "wacc": (0.115, 0.10, 0.09),
        "terminal": (0.01, 0.02, 0.025),
        "warning": "Conditional Low life-sciences recovery. The faded model retains gross debt, ACD cash/contingent consideration, and restructuring evidence without bridge-double-counting the operating reserve.",
        "invalidation": "Invalidate if acquisition integration, restructuring, diagnostics/life-sciences cash, debt, claims, capex, or shares changes.",
    },
    "LLY": {
        "method": "pipeline_high_growth_faded_cash_fcff",
        "growth": (0.10, 0.18, 0.25),
        "wacc": (0.115, 0.10, 0.09),
        "terminal": (0.01, 0.02, 0.025),
        "warning": "Conditional Low high-growth pharmaceutical recovery. Explicit growth is materially below current and historical rates and fades to a governed terminal state; pipeline, patent/pricing, manufacturing capex, R&D, debt, and claims remain material.",
        "invalidation": "Invalidate if product/pipeline growth, patent or pricing cash, manufacturing capex, acquired obligations, debt, or shares leaves the recorded range.",
    },
    "WST": {
        "method": "post_smartdose_faded_cash_fcff",
        "growth": (0.00, 0.025, 0.05),
        "wacc": (0.115, 0.10, 0.09),
        "terminal": (0.01, 0.02, 0.025),
        "warning": "Conditional Low post-SmartDose recovery. Sale cash is included once, but pre-sale history still contains the disposed product and no invented continuing-cash adjustment is used.",
        "invalidation": "Invalidate if SmartDose closing adjustments, continuing cash, quality/regulatory events, capacity capex, debt/leases, claims, or shares changes.",
    },
}


RECOVERY_BRIDGE_TREATMENT = {
    "ABT": "$5.603B cash/investments and $32.608B debt are bridged once. Claims are $652M NCI + $263M acquisition contingent consideration + $510M recorded legal/environmental accrual = $1.425B.",
    "BAX": "$2.151B cash and $9.459B debt/leases are bridged once. Claims are $10M contingent consideration + $43M separation indemnification + $52M Vantive capex reimbursement = $105M; the $28M retained guarantees are Carlyle-indemnified and not added.",
    "BDX": "$708M cash and $16.808B debt are bridged once. The $1.6B recorded product-liability/legal accrual is a separate claim; $181M supplier finance remains in AP/OCF and is not debt.",
    "BMY": "$11.464B cash/investments and $43.888B debt are bridged once. Claims are $607M CVR + $950M fixed Hengrui payments = $1.557B; the $14.3B contingent maximum is not probability-weighted.",
    "RVTY": "$1.022943B cash and $3.2222B gross-principal debt are bridged once with the $8M ACD claim. The $32.818M restructuring reserve remains operating in OCF/history.",
    "LLY": "$8.950B cash and $54.908B debt are bridged once. Claims are $2.518B reported contingent consideration + $2.0B July cash paid = $4.518B; pending $2.8B AtaiBeckley is outside intrinsic value.",
    "WST": "$571.8M cash including SmartDose proceeds, $207.3M debt/finance leases, and $3.3M contingent consideration are bridged once; no disposed-business cash adjustment is invented.",
}


EQUITY_POLICY: dict[str, dict[str, Any]] = {
    "HUM": {
        "method": "managed_care_residual_income_normalized_equity_earnings",
        "ending_equity": 19_213_000_000.0,
        "beginning_equity": 17_657_000_000.0,
        "h1_dividends": 214_000_000.0,
        "cost_of_equity": (0.12, 0.10, 0.085),
        "terminal_roe": (0.07, 0.10, 0.12),
        "terminal_growth": (0.01, 0.02, 0.025),
        "warning": "Conditional Low managed-care residual-income recovery. Reported common equity, payout, and parent-attributable earnings anchor value; claims, regulated capital, member funds, acquisitions, and underwriting normalization remain material.",
        "invalidation": "Invalidate if common equity, parent earnings, payout, medical claims, regulated capital, member funds, acquisitions, or shares changes.",
    },
    "CVS": {
        "method": "mixed_health_services_residual_income_normalized_equity_earnings",
        "ending_equity": 79_702_000_000.0,
        "beginning_equity": 75_214_000_000.0,
        "h1_dividends": 1_725_000_000.0,
        "cost_of_equity": (0.12, 0.10, 0.085),
        "terminal_roe": (0.06, 0.075, 0.095),
        "terminal_growth": (0.01, 0.02, 0.025),
        "warning": "Conditional Low mixed-health residual-income recovery. Reported common equity, payout, and common earnings replace an unanchored fixed multiple; insurance/PBM/retail mix, claims, reimbursement, capital, and debt remain material.",
        "invalidation": "Invalidate if common equity, earnings, payout, insurance/PBM/retail mix, claims, reimbursement, capital requirements, debt, or shares changes.",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metric(profile: dict[str, Any], name: str) -> dict[str, Any]:
    for row in profile.get("metrics", []):
        if row.get("name") == name:
            return row
    raise ValueError(f"history metric {name} is missing")


def _load(
    ticker: str, source_root: Path, structural_root: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    packet = Path(source_root) / ticker
    structural_dir = Path(structural_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    structural = json.loads((structural_dir / "structural-filing.json").read_text())
    receipt = json.loads((structural_dir / "source-receipt.json").read_text())
    initial = build_batch_12_history_result(
        ticker=ticker, source_root=source_root, structural_root=structural_root
    )
    filing = initial["source_ledger"]["controlling_filing"]
    if (
        structural.get("source_accession") != filing["accession"]
        or receipt.get("filing", {}).get("accession") != filing["accession"]
        or receipt.get("valuation_date") != BATCH_12_VALUATION_DATE
    ):
        raise ValueError(f"{ticker}: recovery source identity mismatch")
    return initial, submissions, facts, structural, receipt


def _attempt_receipt(
    *,
    ticker: str,
    initial: dict[str, Any],
    method: str,
    source_root: Path,
    structural_root: Path,
) -> dict[str, Any]:
    packet = Path(source_root) / ticker
    structural_dir = Path(structural_root) / ticker
    return {
        "attempt_number": 1,
        "attempt_scope": "whole_batch_value_recovery",
        "initial_availability_type": initial["availability_type"],
        "initial_scenario_range": dict(initial["scenario_range"]),
        "candidate_method": method,
        "outcome": "conditional_numeric_low",
        "source_packet_manifest_sha256": _sha256(packet / "source-manifest.json"),
        "package_manifest_sha256": _sha256(structural_dir / "package-manifest.json"),
        "source_receipt_sha256": _sha256(structural_dir / "source-receipt.json"),
        "structural_filing_sha256": _sha256(structural_dir / "structural-filing.json"),
        "market_price_used": False,
        "analyst_target_used": False,
    }


def _operating_result(
    *,
    ticker: str,
    initial: dict[str, Any],
    submissions: dict[str, Any],
    facts: dict[str, Any],
    structural: dict[str, Any],
    source_root: Path,
    structural_root: Path,
) -> dict[str, Any]:
    policy = OPERATING_POLICY[ticker]
    source_ledger = deepcopy(initial["source_ledger"])
    reported = dict(initial["reported_inputs"])
    profile = source_ledger["company_history_profile"]
    cash_metric = _metric(profile, "cash_conversion_margin")
    margins = (cash_metric["low"], cash_metric["base"], cash_metric["high"])
    pro_forma_h1_revenue = 24_500_000_000.0 if ticker == "ABT" else None
    revenue = pro_forma_h1_revenue * 2.0 if pro_forma_h1_revenue else float(reported["ttm_revenue"])
    bridge_policy = P[ticker]
    cash = (bridge_policy.cash,) * 3
    debt = (bridge_policy.debt,) * 3
    claims = (bridge_policy.claims,) * 3
    shares = bridge_policy.shares
    if ticker == "BAX":
        claims = (105_000_000.0,) * 3
        source_ledger.setdefault("recovery_event_sources", []).extend(
            [
                _point(
                    structural,
                    name="BusinessSeparationIndemnificationLiability",
                    expected=43_000_000.0,
                    period_end="2026-06-30",
                ),
                _dimension_fact(
                    structural,
                    name="DisposalGroupIncludingDiscontinuedOperationsContingentLiability",
                    expected=52_000_000.0,
                    start=None,
                    end="2026-06-30",
                    member="IndemnificationGuaranteeMember",
                ),
            ]
        )
    if ticker == "ABT":
        claims = (1_425_000_000.0,) * 3
        source_ledger.setdefault("recovery_event_sources", []).extend(
            [
                _dimension_fact(
                    structural,
                    name="BusinessAcquisitionsProFormaRevenue",
                    expected=24_500_000_000.0,
                    start="2026-01-01",
                    end="2026-06-30",
                    member="ExactSciencesCorporationMember",
                ),
                _dimension_fact(
                    structural,
                    name="BusinessAcquisitionsProFormaIncomeLossFromContinuingOperationsBeforeChangesInAccountingAndExtraordinaryItemsNetOfTax",
                    expected=2_900_000_000.0,
                    start="2026-01-01",
                    end="2026-06-30",
                    member="ExactSciencesCorporationMember",
                ),
                _dimension_fact(
                    structural,
                    name="LossContingencyAccrualAtCarryingValue",
                    expected=510_000_000.0,
                    start=None,
                    end="2026-06-30",
                    member="LegalProceedingsAndEnvironmentalExposuresMember",
                ),
            ]
        )
    if ticker == "BDX":
        claims = (1_600_000_000.0,) * 3
        source_ledger.setdefault("recovery_event_sources", []).append(
            _point(
                structural,
                name="LossContingencyAccrualAtCarryingValue",
                expected=1_600_000_000.0,
                period_end="2026-06-30",
            )
        )
    if ticker == "BMY":
        claims = (1_557_000_000.0,) * 3
        source_ledger.setdefault("recovery_event_sources", []).extend(
            [
                _dimension_fact(
                    structural,
                    name="LicenseAndOtherArrangementsUpfrontPayments",
                    expected=600_000_000.0,
                    start="2026-07-01",
                    end="2026-09-30",
                    member="HengruiLicenseAgreementsMember",
                ),
                _dimension_fact(
                    structural,
                    name="LicenseAndOtherArrangementsAnniversaryPayments",
                    expected=175_000_000.0,
                    start="2027-01-01",
                    end="2027-12-31",
                    member="HengruiLicenseAgreementsMember",
                ),
                _dimension_fact(
                    structural,
                    name="LicenseAndOtherArrangementsAnniversaryPayments",
                    expected=175_000_000.0,
                    start="2028-01-01",
                    end="2028-12-31",
                    member="HengruiLicenseAgreementsMember",
                ),
                _dimension_fact(
                    structural,
                    name="ContingentAndRegulatoryMilestonePaymentsMaximumAggregate",
                    expected=14_300_000_000.0,
                    start="2028-01-01",
                    end="2028-12-31",
                    member="HengruiLicenseAgreementsMember",
                ),
                {
                    "source_kind": "governed_event_treatment",
                    "field": "hengrui_fixed_and_contingent_payments",
                    "fixed_claim_included": 950_000_000.0,
                    "contingent_maximum_not_probability_weighted": 14_300_000_000.0,
                    "unit": "USD",
                    "basis": "Only the reported fixed upfront and anniversary payments are reserved. The milestone maximum remains a separate contingent event surface.",
                },
            ]
        )
    if ticker == "LLY":
        claims = (4_518_000_000.0,) * 3
        source_ledger.setdefault("recovery_event_sources", []).extend(
            [
                _dimension_fact(
                    structural,
                    name="BusinessCombinationPriceOfAcquisitionExpected",
                    expected=3_900_000_000.0,
                    start="2026-07-01",
                    end="2026-07-31",
                    member="ThreeAcquiredCompaniesMember",
                ),
                _dimension_fact(
                    structural,
                    name="NumberOfBusinessesAcquired",
                    expected=3.0,
                    start="2026-07-01",
                    end="2026-07-31",
                    member="ThreeAcquiredCompaniesMember",
                ),
                {
                    "source_kind": "controlling_filing_text_and_governed_event_reserve",
                    "accession": structural["source_accession"],
                    "event_period": "2026-07",
                    "field": "three_completed_infectious_disease_acquisitions",
                    "reported_cash_paid": 2_000_000_000.0,
                    "reported_maximum_consideration": 3_900_000_000.0,
                    "unit": "USD",
                    "valuation_treatment": "reported_cash_paid_reserved_once; no acquired earnings added",
                },
                {
                    "source_kind": "controlling_filing_text_pending_event",
                    "accession": structural["source_accession"],
                    "field": "pending_ataibeckley_consideration",
                    "reported_value": 2_800_000_000.0,
                    "unit": "USD",
                    "valuation_treatment": "separate_pending_transaction_surface_not_in_intrinsic_value",
                },
            ]
        )
    rows = []
    traces = {}
    for index, state_name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(
            cash_fcff=revenue * margins[index],
            initial_growth=policy["growth"][index],
            terminal_growth=policy["terminal"][index],
            wacc=policy["wacc"][index],
            cash_and_investments=cash[index],
            interest_bearing_debt=debt[index],
            preferred_equity=0.0,
            noncontrolling_interests=claims[index],
            diluted_shares=shares[index],
        )
        trace = enterprise_cash_flow_dcf(
            state,
            forecast_years=FORECAST_YEARS,
            allow_nonpositive_equity_trace=True,
        )
        raw_value = float(trace["intrinsic_value_per_share"])
        value = max(0.0, raw_value)
        rows.append(
            {
                "name": state_name,
                "conditional_value_per_share": value,
                "raw_value_per_share": raw_value,
                "starting_cash_fcff": state.cash_fcff,
                "cash_conversion_margin": margins[index],
                "growth": policy["growth"][index],
                "wacc": policy["wacc"][index],
                "terminal_growth": policy["terminal"][index],
                "cash_and_investments": cash[index],
                "debt_and_finance_leases": debt[index],
                "other_equity_claims": claims[index],
                "shares": shares[index],
                "limited_liability_floor_applied": raw_value < 0.0,
            }
        )
        traces[state_name] = trace
    scenario = {
        "low": rows[0]["conditional_value_per_share"],
        "base": rows[1]["conditional_value_per_share"],
        "high": rows[2]["conditional_value_per_share"],
    }
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError(f"{ticker}: recovery range is invalid")
    reliability = assess_reliability(
        accounting_low=scenario["base"],
        accounting_base=scenario["base"],
        accounting_high=scenario["base"],
        scenario_low=scenario["low"],
        scenario_base=scenario["base"],
        scenario_high=scenario["high"],
        model_cap="Low",
        source_cap="High",
        reasons=("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"),
    )
    assumptions = {
        "history_policy_version": HISTORY_POLICY_VERSION,
        "history_years_used": len(set(profile["annual_periods"])),
        "normalization_basis": "source_normalized_cash_with_eight_year_growth_fade",
        "assumption_source_mix": "reported_history_current_events_and_finsight_recovery_policy",
        "forecast_years": FORECAST_YEARS,
        "cash_conversion_margin": margins,
        "growth": policy["growth"],
        "wacc": policy["wacc"],
        "terminal_growth": policy["terminal"],
        "cash_and_investments": cash,
        "debt_and_finance_leases": debt,
        "other_equity_claims": claims,
        "shares": shares,
        "equity_floor_basis": "limited-liability floor after negative residual" if scenario["low"] == 0 else "not applied",
        "calculator_calibration": "Calculator defaults reproduce the published faded-cash recovery base; source facts and private schedule remain locked.",
        "invalidation": policy["invalidation"],
    }
    baseline = BaselineValuation(
        ticker=ticker,
        method=policy["method"],
        method_version=BATCH_12_RECOVERY_VERSION,
        low=scenario["low"],
        base=scenario["base"],
        high=scenario["high"],
        confidence=reliability.label,
        availability_type=AvailabilityType.CONDITIONAL,
        key_assumptions=(
            BaselineAssumption(
                "source-linked company history",
                assumptions["history_years_used"],
                AssumptionClassification.HISTORICALLY_DERIVED,
                "Reported annual and current cash conversion supplies the starting cash states.",
            ),
            BaselineAssumption(
                "faded recovery states",
                str({"growth": policy["growth"], "wacc": policy["wacc"], "terminal": policy["terminal"]}),
                AssumptionClassification.FINSIGHT_ASSUMPTION,
                "Explicit growth fades over eight years to a terminal rate no higher than 2.5%.",
            ),
        ),
        warnings=(policy["warning"], policy["invalidation"]),
        confidence_reasons=tuple(reliability.reasons),
        calculator_link=f"/api/us-valuations/{ticker}/calculator",
    )
    source_ledger["recovery_model_trace"] = {
        "forecast_years": FORECAST_YEARS,
        "starting_revenue": revenue,
        "starting_revenue_formula": "2 × filed $24.5B pro-forma combined H1 revenue" if ticker == "ABT" else "reported TTM revenue",
        "states": traces,
    }
    source_ledger["bridge_reconciliation"] = {
        **source_ledger.get("bridge_reconciliation", {}),
        "recovery_cash_and_investments": cash,
        "recovery_debt_and_finance_leases": debt,
        "recovery_other_equity_claims": claims,
        "recovery_shares": shares,
        "treatment": RECOVERY_BRIDGE_TREATMENT[ticker],
    }
    source_ledger["recovery_attempt"] = _attempt_receipt(
        ticker=ticker,
        initial=initial,
        method=policy["method"],
        source_root=source_root,
        structural_root=structural_root,
    )
    return {
        "ticker": ticker,
        "method": policy["method"],
        "model_version": BATCH_12_RECOVERY_VERSION,
        "availability_type": "conditional_estimate",
        "scenario_rows": rows,
        "scenario_range": scenario,
        "reported_inputs": {**reported, "recovery_starting_revenue": revenue},
        "governed_assumptions": assumptions,
        "history_reliability": reliability.as_dict(),
        "source_ledger": source_ledger,
        "warning": policy["warning"],
        "baseline": baseline.as_private_dict(),
    }


def _withheld_uhs_recovery(
    *,
    initial: dict[str, Any],
    structural: dict[str, Any],
    source_root: Path,
    structural_root: Path,
) -> dict[str, Any]:
    reason = "Withheld after one recovery attempt. A finite Ireland purchase reserve does not reconstruct UHS's post-period operating state: the filing also reports Provo Canyon license revocations and patient discharges, a new CMG operating responsibility, and pending debt-financed Talkspace."
    invalidation = "Revalue after a filed post-Ireland/Provo/CMG operating and cash/debt state plus final Talkspace closing or termination."
    source_ledger = deepcopy(initial["source_ledger"])
    source_ledger["recovery_event_sources"] = [
        _dimension_fact(
            structural,
            name="AssetAcquisitionConsiderationTransferred",
            expected=188_000_000.0,
            start="2026-07-01",
            end="2026-07-31",
            member="SubsequentEventMember",
        ),
        _point(
            structural,
            name="LineOfCreditFacilityMaximumBorrowingCapacity",
            expected=1_272_000_000.0,
            period_end="2026-06-30",
        ),
        {
            "source_kind": "controlling_filing_text_subsequent_operating_event",
            "accession": structural["source_accession"],
            "event_dates": ["2026-07-06", "2026-07-17"],
            "field": "provo_canyon_license_revocations",
            "reported_effect": "remaining patients required to be discharged by early to mid-August 2026; appeals and future operations unresolved",
            "valuation_treatment": "hard_stop_post_period_operating_state",
        },
        {
            "source_kind": "controlling_filing_text_subsequent_operating_event",
            "accession": structural["source_accession"],
            "event_date": "2026-08-01",
            "field": "capital_medical_group_operating_responsibility",
            "reported_effect": "UHS subsidiary became sole member and assumed management and financial responsibility while OAG review remained open",
            "valuation_treatment": "hard_stop_post_period_operating_state",
        },
        {
            "source_kind": "recovery_exhaustion",
            "field": "ireland_financing_reserve_test",
            "reported_purchase_price": 188_000_000.0,
            "unit": "USD",
            "result": "finite reserve does not clear operating-state blockers",
        },
    ]
    attempt = _attempt_receipt(
        ticker="UHS",
        initial=initial,
        method="unavailable_post_period_multi_event_state",
        source_root=source_root,
        structural_root=structural_root,
    )
    attempt.update(
        {
            "outcome": "withheld",
            "hard_blockers": [
                "POST_PERIOD_CASH_DEBT_STATE_UNAVAILABLE",
                "POST_PERIOD_OPERATING_STATE_CHANGED",
                "PENDING_TRANSACTION_FINANCING_UNRESOLVED",
            ],
        }
    )
    source_ledger["recovery_attempt"] = attempt
    source_ledger["release_condition"] = invalidation
    baseline = BaselineValuation(
        ticker="UHS",
        method="unavailable_post_period_multi_event_state",
        method_version=BATCH_12_RECOVERY_VERSION,
        low=None,
        base=None,
        high=None,
        confidence=None,
        availability_type=AvailabilityType.NOT_AVAILABLE,
        warnings=(reason, invalidation),
    )
    return {
        "ticker": "UHS",
        "method": "unavailable_post_period_multi_event_state",
        "model_version": BATCH_12_RECOVERY_VERSION,
        "availability_type": "not_available",
        "scenario_rows": [],
        "scenario_range": {"low": None, "base": None, "high": None},
        "reported_inputs": {},
        "governed_assumptions": {
            "history_policy_version": HISTORY_POLICY_VERSION,
            "history_years_used": 0,
            "normalization_basis": "post_period_multi_event_state_unavailable_after_recovery",
            "assumption_source_mix": "reported_pre_event_state_subsequent_events_and_exhaustion",
            "recovery_attempts": 1,
            "invalidation": invalidation,
        },
        "history_reliability": None,
        "source_ledger": source_ledger,
        "warning": reason,
        "baseline": baseline.as_private_dict(),
    }


def _equity_result(
    *,
    ticker: str,
    initial: dict[str, Any],
    structural: dict[str, Any],
    source_root: Path,
    structural_root: Path,
) -> dict[str, Any]:
    policy = EQUITY_POLICY[ticker]
    profile = initial["source_ledger"]["company_history_profile"]
    earnings_metric = _metric(profile, "normalized_common_earnings")
    earnings = (earnings_metric["low"], earnings_metric["base"], earnings_metric["high"])
    shares = initial["governed_assumptions"]["shares"]
    average_equity = (policy["beginning_equity"] + policy["ending_equity"]) / 2.0
    ttm_earnings = float(initial["reported_inputs"]["ttm_common_earnings"])
    payout = min(1.0, policy["h1_dividends"] * 2.0 / ttm_earnings)
    rows = []
    traces = {}
    implied_multiples = []
    for index, state_name in enumerate(("bear", "base", "bull")):
        book_value_per_share = policy["ending_equity"] / shares[index]
        current_roe = earnings[index] / average_equity
        trace = residual_income_valuation(
            book_value_per_share=book_value_per_share,
            current_roe=current_roe,
            cost_of_equity=policy["cost_of_equity"][index],
            current_payout_ratio=payout,
            terminal_roe=policy["terminal_roe"][index],
            terminal_growth=policy["terminal_growth"][index],
            years=5,
        )
        value = float(trace["intrinsic_value"])
        multiple = value * shares[index] / earnings[index]
        implied_multiples.append(multiple)
        rows.append(
            {
                "name": state_name,
                "conditional_value_per_share": value,
                "raw_value_per_share": value,
                "normalized_consolidated_earnings": earnings[index],
                "book_value_per_share": book_value_per_share,
                "current_roe": current_roe,
                "current_payout_ratio": payout,
                "cost_of_equity": policy["cost_of_equity"][index],
                "terminal_roe": policy["terminal_roe"][index],
                "terminal_growth": policy["terminal_growth"][index],
                "earnings_multiple": multiple,
                "shares": shares[index],
                "limited_liability_floor_applied": False,
            }
        )
        traces[state_name] = trace
    scenario = {
        "low": rows[0]["conditional_value_per_share"],
        "base": rows[1]["conditional_value_per_share"],
        "high": rows[2]["conditional_value_per_share"],
    }
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: residual-income recovery range is invalid")
    reliability = assess_reliability(
        accounting_low=scenario["base"],
        accounting_base=scenario["base"],
        accounting_high=scenario["base"],
        scenario_low=scenario["low"],
        scenario_base=scenario["base"],
        scenario_high=scenario["high"],
        model_cap="Low",
        source_cap="High",
        reasons=("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"),
    )
    assumptions = {
        "history_policy_version": HISTORY_POLICY_VERSION,
        "history_years_used": len(set(profile["annual_periods"])),
        "normalization_basis": "reported_common_equity_and_history_residual_income",
        "assumption_source_mix": "reported_common_equity_earnings_payout_and_finsight_policy",
        "normalized_consolidated_earnings": earnings,
        "earnings_multiples": tuple(implied_multiples),
        "shares": shares,
        "book_equity": policy["ending_equity"],
        "average_common_equity": average_equity,
        "current_payout_ratio": payout,
        "cost_of_equity": policy["cost_of_equity"],
        "terminal_roe": policy["terminal_roe"],
        "terminal_growth": policy["terminal_growth"],
        "ev_debt_bridge_applied": False,
        "route_is_equity_level": True,
        "equity_floor_basis": "not applied",
        "calculator_calibration": "Calculator varies normalized earnings and the residual-income-implied multiple around the published base; private book/ROE schedules remain locked.",
        "invalidation": policy["invalidation"],
    }
    baseline = BaselineValuation(
        ticker=ticker,
        method=policy["method"],
        method_version=BATCH_12_RECOVERY_VERSION,
        low=scenario["low"],
        base=scenario["base"],
        high=scenario["high"],
        confidence=reliability.label,
        availability_type=AvailabilityType.CONDITIONAL,
        key_assumptions=(
            BaselineAssumption(
                "reported common equity",
                policy["ending_equity"],
                AssumptionClassification.REPORTED,
                "Current parent equity supplies the residual-income opening anchor.",
            ),
            BaselineAssumption(
                "source-linked common earnings",
                earnings,
                AssumptionClassification.HISTORICALLY_DERIVED,
                "Parent/common earnings history supplies the ROE states.",
            ),
            BaselineAssumption(
                "residual-income policy",
                str({"cost_of_equity": policy["cost_of_equity"], "terminal_roe": policy["terminal_roe"]}),
                AssumptionClassification.FINSIGHT_ASSUMPTION,
                "Required return and terminal ROE remain transparent policy assumptions.",
            ),
        ),
        warnings=(policy["warning"], policy["invalidation"]),
        confidence_reasons=tuple(reliability.reasons),
        calculator_link=f"/api/us-valuations/{ticker}/calculator",
    )
    dividend_name = "PaymentsOfDividends"
    sources = {
        "beginning_parent_equity": _point(
            structural,
            name="StockholdersEquity",
            expected=policy["beginning_equity"],
            period_end="2025-12-31",
        ),
        "ending_parent_equity": _point(
            structural,
            name="StockholdersEquity",
            expected=policy["ending_equity"],
            period_end="2026-06-30",
        ),
        "current_h1_dividends": _structural_flow(
            structural,
            name=dividend_name,
            start="2026-01-01",
            end="2026-06-30",
            expected=policy["h1_dividends"],
        ),
    }
    source_ledger = deepcopy(initial["source_ledger"])
    source_ledger["residual_income_sources"] = sources
    source_ledger["recovery_model_trace"] = {
        "states": traces,
        "clean_surplus_ddm_is_reconciliation_not_independent_evidence": True,
    }
    source_ledger["recovery_attempt"] = _attempt_receipt(
        ticker=ticker,
        initial=initial,
        method=policy["method"],
        source_root=source_root,
        structural_root=structural_root,
    )
    return {
        "ticker": ticker,
        "method": policy["method"],
        "model_version": BATCH_12_RECOVERY_VERSION,
        "availability_type": "conditional_estimate",
        "scenario_rows": rows,
        "scenario_range": scenario,
        "reported_inputs": {
            **initial["reported_inputs"],
            "ending_parent_equity": policy["ending_equity"],
            "beginning_parent_equity": policy["beginning_equity"],
            "annualized_current_dividends": policy["h1_dividends"] * 2.0,
        },
        "governed_assumptions": assumptions,
        "history_reliability": reliability.as_dict(),
        "source_ledger": source_ledger,
        "warning": policy["warning"],
        "baseline": baseline.as_private_dict(),
    }


def build_batch_12_recovery_result(
    *, ticker: str, source_root: Path, structural_root: Path
) -> dict[str, Any]:
    if ticker not in BATCH_12_TICKERS:
        raise ValueError(f"{ticker}: not in frozen Batch 12")
    initial, submissions, facts, structural, _receipt = _load(
        ticker, Path(source_root), Path(structural_root)
    )
    if ticker in OPERATING_TICKERS:
        return _operating_result(
            ticker=ticker,
            initial=initial,
            submissions=submissions,
            facts=facts,
            structural=structural,
            source_root=Path(source_root),
            structural_root=Path(structural_root),
        )
    if ticker in EQUITY_TICKERS:
        return _equity_result(
            ticker=ticker,
            initial=initial,
            structural=structural,
            source_root=Path(source_root),
            structural_root=Path(structural_root),
        )
    return _withheld_uhs_recovery(
        initial=initial,
        structural=structural,
        source_root=Path(source_root),
        structural_root=Path(structural_root),
    )


if OPERATING_TICKERS | EQUITY_TICKERS | WITHHELD_TICKERS != set(BATCH_12_TICKERS):
    raise RuntimeError("Batch 12 recovery denominator mismatch")
