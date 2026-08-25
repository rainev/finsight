"""Launch-first conditional baselines for five Batch 03 holdouts.

The estimates value the current consolidated/legal-state economic object. Reported
anchors and governed assumptions remain separate. ECHO and PSKY deliberately remain
unavailable because their economic/share objects are not bounded by the frozen packet.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from statistics import median
from typing import Any, Mapping

from .baseline import (
    AssumptionClassification,
    AvailabilityType,
    BaselineAssumption,
    BaselineValuation,
    FallbackRejected,
    FallbackStage,
    run_fallback_ladder,
)
from .batch_02_conditional_estimates import ConditionalRange, five_year_fcff_dcf
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate
from .batch_03 import BATCH_03_VALUATION_DATE
from .sec_client import normalize_cik


LAUNCH_FIRST_BATCH_03_VERSION = "BATCH-03-LAUNCH-FIRST-1.1"
LAUNCH_FIRST_CONDITIONAL_TICKERS = ("LYV", "GOOGL", "APP", "FOXA", "TKO")
LAUNCH_FIRST_HARD_FAILURES = {
    "ECHO": (
        "Current negative owner cash flow cannot be separated from the DISH/deconsolidation and spectrum transition.",
        "Debt, disposal assets, spectrum economics, and conversion shares are not bounded to one continuing-company object.",
    ),
    "PSKY": (
        "The current-successor bear and base residual equity are nonpositive after debt and NCI.",
        "A positive value depends on an unproven recovery state before a complete comparable successor fiscal year exists.",
    ),
}


@dataclass(frozen=True)
class ConditionalPolicy:
    method: str
    growth: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal_growth: tuple[float, float, float]
    shares: tuple[float, float, float]
    expected_revenue: float
    expected_operating_cash_flow: float
    expected_capex: float | None
    warning: str
    invalidation: str
    assumption_basis: str


_POLICIES = {
    "LYV": ConditionalPolicy(
        method="event_normalized_cash_fcff",
        growth=(-0.02, 0.02, 0.05),
        wacc=(0.115, 0.105, 0.095),
        terminal_growth=(0.0, 0.015, 0.02),
        shares=(244_000_000.0, 235_633_860.0, 232_621_161.0),
        expected_revenue=26_272_535_000.0,
        expected_operating_cash_flow=2_608_702_000.0,
        expected_capex=1_226_000_000.0,
        warning=(
            "Conditional Low-reliability estimate. Event timing, client cash, deferred revenue, "
            "leases, NCI, and convertible dilution can move value materially."
        ),
        invalidation="Invalidate when a complete fiscal year falls outside the governed cash-margin range or current claims/share conversion changes materially.",
        assumption_basis="Three-to-five-year company cash conversion, current TTM results, and explicit event/claims stress.",
    ),
    "GOOGL": ConditionalPolicy(
        method="ai_commitment_adjusted_cash_fcff",
        growth=(0.04, 0.08, 0.12),
        wacc=(0.105, 0.09, 0.08),
        terminal_growth=(0.015, 0.02, 0.025),
        shares=(12_400_000_000.0, 12_300_000_000.0, 12_230_000_000.0),
        expected_revenue=445_866_000_000.0,
        expected_operating_cash_flow=185_675_000_000.0,
        expected_capex=132_402_000_000.0,
        warning=(
            "Conditional Low-reliability estimate. The $707bn purchase-commitment burden is "
            "captured inside broad cash-conversion states and is not deducted again as debt."
        ),
        invalidation="Invalidate when the commitment timing, capex program, preferred/VIE claims, or AI-cloud cash conversion leaves the governed range.",
        assumption_basis="Current TTM cash conversion and company history, widened for AI infrastructure commitments and financing claims.",
    ),
    "APP": ConditionalPolicy(
        method="normalized_cash_fcff",
        growth=(0.05, 0.10, 0.15),
        wacc=(0.12, 0.10, 0.09),
        terminal_growth=(0.01, 0.02, 0.025),
        shares=(352_000_000.0, 335_291_000.0, 325_000_000.0),
        expected_revenue=6_829_124_000.0,
        expected_operating_cash_flow=4_527_589_000.0,
        expected_capex=None,
        warning=(
            "Conditional Low-reliability estimate. Current capex is not reported; cash margins "
            "use company-history bounds and do not copy the stale 2024 capex amount into 2026. "
            "Unresolved NCI is reserved at 5%/2.5%/0% of assets across bear/base/bull."
        ),
        invalidation="Invalidate when a current capex disclosure or a complete post-disposal year falls outside the governed cash-margin range.",
        assumption_basis="Current TTM operating cash flow with explicitly assumed, history-bounded asset-light reinvestment and post-disposal growth.",
    ),
    "FOXA": ConditionalPolicy(
        method="rights_adjusted_broadcast_cash_fcff",
        growth=(-0.02, 0.0, 0.03),
        wacc=(0.115, 0.10, 0.09),
        terminal_growth=(0.0, 0.015, 0.02),
        shares=(461_000_000.0, 439_000_000.0, 420_000_000.0),
        expected_revenue=17_126_000_000.0,
        expected_operating_cash_flow=1_970_000_000.0,
        expected_capex=502_000_000.0,
        warning=(
            "Conditional Low-reliability estimate. Programming and sports-rights obligations "
            "are captured through stressed cash margins and are not deducted twice as bridge debt."
        ),
        invalidation="Invalidate when the rights schedule, near-term obligations, or reported cash conversion leaves the governed range.",
        assumption_basis="Five annual cash periods plus explicit next-twelve-month contractual and program-rights obligations.",
    ),
    "TKO": ConditionalPolicy(
        method="sports_rights_normalized_cash_fcff",
        growth=(0.0, 0.04, 0.07),
        wacc=(0.13, 0.11, 0.10),
        terminal_growth=(0.0, 0.01, 0.02),
        shares=(203_000_000.0, 193_323_374.0, 189_269_713.0),
        expected_revenue=5_301_863_000.0,
        expected_operating_cash_flow=1_795_136_000.0,
        expected_capex=None,
        warning=(
            "Conditional Low-reliability estimate. Capex and rights reinvestment are explicit "
            "FinSight assumptions; the bear case reaches the limited-liability equity floor."
        ),
        invalidation="Invalidate when filed capex/rights cash, OpCo conversion, NCI, or the diluted share denominator leaves the governed range.",
        assumption_basis="Current TTM cash generation with 30%/20%/15% of revenue reserved for capex and rights reinvestment because no complete capex series is filed.",
    ),
}


def _point(
    structural: Mapping[str, Any],
    *,
    name: str,
    expected: float,
    period_end: str = "2026-06-30",
    unit: str = "USD",
    allow_dimensions: bool = False,
) -> dict[str, Any]:
    rows = [
        row
        for row in structural["facts"]
        if row.get("local_name") == name
        and row.get("period_start") is None
        and row.get("period_end") == period_end
        and row.get("unit") in {unit, f"xbrli:{unit}"}
        and (allow_dimensions or not row.get("dimensions"))
        and isinstance(row.get("value"), (int, float))
        and not isinstance(row.get("value"), bool)
        and float(row["value"]) == expected
    ]
    if not rows:
        raise ValueError(f"{name}: expected source value {expected} is absent")
    row = rows[0]
    return {
        "source_kind": "structural_xbrl",
        "accession": structural["source_accession"],
        "period_end": period_end,
        "concept": row.get("qname"),
        "unit": unit,
        "value": expected,
        "reported_vs_estimated": "reported",
    }


def _duration(
    structural: Mapping[str, Any],
    *,
    name: str,
    expected: float,
    period_start: str = "2026-01-01",
    period_end: str = "2026-06-30",
    unit: str = "shares",
) -> dict[str, Any]:
    rows = [
        row
        for row in structural["facts"]
        if row.get("local_name") == name
        and row.get("period_start") == period_start
        and row.get("period_end") == period_end
        and row.get("unit") in {unit, f"xbrli:{unit}"}
        and not row.get("dimensions")
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) == expected
    ]
    if not rows:
        raise ValueError(f"{name}: expected duration source value {expected} is absent")
    row = rows[0]
    return {
        "source_kind": "structural_xbrl",
        "accession": structural["source_accession"],
        "period_start": period_start,
        "period_end": period_end,
        "concept": row.get("qname"),
        "unit": unit,
        "value": expected,
        "reported_vs_estimated": "reported",
    }


def _point_member(
    structural: Mapping[str, Any],
    *,
    name: str,
    expected: float,
    member: str,
    unit: str,
) -> dict[str, Any]:
    rows = [
        row
        for row in structural["facts"]
        if row.get("local_name") == name
        and row.get("period_start") is None
        and row.get("period_end") == "2026-06-30"
        and row.get("unit") in {unit, f"xbrli:{unit}"}
        and any(member in str(value) for _, value in (row.get("dimensions") or []))
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) == expected
    ]
    if not rows:
        raise ValueError(f"{name}/{member}: expected member value {expected} is absent")
    row = rows[0]
    return {
        "source_kind": "structural_xbrl",
        "accession": structural["source_accession"],
        "period_end": "2026-06-30",
        "concept": row.get("qname"),
        "member": member,
        "unit": unit,
        "value": expected,
        "reported_vs_estimated": "reported",
    }


def _bridge(ticker: str, structural: Mapping[str, Any]) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []

    def point(name: str, expected: float, **kwargs: Any) -> float:
        sources.append(_point(structural, name=name, expected=expected, **kwargs))
        return expected

    if ticker == "LYV":
        cash = point("CashAndCashEquivalentsAtCarryingValue", 9_071_949_000.0)
        client_cash = point("ClientCollectedCashAndCashEquivalentsAtCarryingValue", 1_900_000_000.0)
        debt = point("DebtInstrumentCarryingAmount", 9_282_337_000.0)
        claims = point("MinorityInterest", 673_233_000.0) + point(
            "RedeemableNoncontrollingInterestEquityCarryingAmount", 1_063_602_000.0
        )
        sources.append(
            _duration(
                structural,
                name="WeightedAverageNumberOfDilutedSharesOutstanding",
                expected=232_621_161.0,
            )
        )
        return {
            "cash_and_investments": (cash - client_cash,) * 3,
            "debt": debt,
            "other_claims": (claims,) * 3,
            "sources": sources,
            "special_treatment": "Client-collected cash is excluded from available cash.",
        }
    if ticker == "GOOGL":
        cash = point("CashCashEquivalentsAndShortTermInvestments", 242_474_000_000.0)
        debt = (
            point("LongTermDebtCurrent", 1_999_000_000.0)
            + point("LongTermDebtNoncurrent", 98_165_000_000.0)
            + point("FinanceLeaseLiability", 2_590_000_000.0)
        )
        claims = (
            point("ConvertiblePreferredStockNonredeemableOrRedeemableIssuerOptionValue", 18_023_000_000.0)
            + point("NoncontrollingInterestInVariableInterestEntity", 7_100_000_000.0)
            + point("RedeemableNoncontrollingInterestInVariableInterestEntity", 824_000_000.0)
        )
        sources.append(
            _duration(
                structural,
                name="LongTermPurchaseCommitmentAmount",
                expected=707_000_000_000.0,
                unit="USD",
            )
        )
        return {
            "cash_and_investments": (cash,) * 3,
            "debt": debt,
            "other_claims": (claims,) * 3,
            "sources": sources,
            "special_treatment": "Purchase commitments are captured through cash margins and not deducted again.",
            "commitment_inputs": {
                "total_purchase_commitments": 707_000_000_000.0,
                "cash_realization_horizons_years": (5.0, 8.0, 12.0),
            },
        }
    if ticker == "APP":
        cash = point("CashAndCashEquivalentsAtCarryingValue", 3_053_306_000.0)
        debt = point("LongTermDebtNoncurrent", 3_515_072_000.0)
        point("PreferredStockValue", 0.0)
        assets = point("Assets", 8_269_131_000.0)
        return {
            "cash_and_investments": (cash,) * 3,
            "debt": debt,
            "other_claims": (assets * 0.05, assets * 0.025, 0.0),
            "sources": sources,
            "special_treatment": "Current capex is estimated from company history; unresolved NCI is reserved at 5%/2.5%/0% of assets rather than treated as zero.",
        }
    if ticker == "FOXA":
        cash = point("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", 4_205_000_000.0)
        debt = point("DebtInstrumentCarryingAmount", 6_650_000_000.0)
        claims = point("MinorityInterest", 100_000_000.0) + point(
            "RedeemableNoncontrollingInterestEquityCarryingAmount", 86_000_000.0
        )
        point("ContractualObligationDueInNextTwelveMonths", 6_461_000_000.0)
        point("OtherCommitmentDueInNextTwelveMonths", 715_000_000.0)
        point("ProgramRightsObligationsCurrent", 801_000_000.0)
        sources.append(
            _duration(
                structural,
                name="WeightedAverageNumberOfDilutedSharesOutstanding",
                expected=439_000_000.0,
                period_start="2025-07-01",
            )
        )
        return {
            "cash_and_investments": (0.0, cash * 0.5, cash),
            "debt": debt,
            "other_claims": (claims,) * 3,
            "sources": sources,
            "special_treatment": "Restricted-cash availability is ranged at 0%/50%/100%; rights and obligations reduce scenario cash and are not bridge debt.",
            "commitment_inputs": {
                "next_twelve_month_contractual_other_and_program_rights": 7_977_000_000.0,
                "incremental_cash_reserve_fractions": (0.10, 0.05, 0.0),
            },
        }
    if ticker == "TKO":
        cash = point("CashAndCashEquivalentsAtCarryingValue", 592_485_000.0)
        debt = (
            point("DebtInstrumentCarryingAmount", 4_659_049_000.0)
            + point("FinanceLeaseLiabilityCurrent", 25_501_000.0)
            + point("FinanceLeaseLiabilityNoncurrent", 238_311_000.0)
        )
        redeemable_nci = point("RedeemableNoncontrollingInterestEquityCarryingAmount", 34_412_000.0)
        point("NonredeemableNoncontrollingInterest", 4_934_964_000.0)
        point("RevenueRemainingPerformanceObligation", 15_969_998_000.0)
        diluted_source = _duration(
            structural,
            name="WeightedAverageNumberOfDilutedSharesOutstanding",
            expected=193_323_374.0,
        )
        basic_source = _duration(
            structural,
            name="WeightedAverageNumberOfSharesOutstandingBasic",
            expected=76_054_642.0,
        )
        class_b_source = _point_member(
            structural,
            name="CommonStockSharesOutstanding",
            expected=116_158_615.0,
            member="CommonClassBMember",
            unit="shares",
        )
        conversion_source = _point_member(
            structural,
            name="CommonUnitsConvertibleConversionRatio",
            expected=1.0,
            member="TKOOpCoMember",
            unit="pure",
        )
        sources.extend((diluted_source, basic_source, class_b_source, conversion_source))
        incremental_dilution = 193_323_374.0 - 76_054_642.0 - 116_158_615.0
        if incremental_dilution < 0:
            raise ValueError("TKO: diluted shares do not cover Class B conversion units")
        return {
            "cash_and_investments": (cash,) * 3,
            "debt": debt,
            "other_claims": (redeemable_nci,) * 3,
            "sources": sources,
            "special_treatment": "Nonredeemable OpCo NCI is represented by convertible Class B units in diluted shares; customer performance obligations are revenue, not cash debt.",
            "reinvestment_rates": (0.30, 0.20, 0.15),
            "nci_share_reconciliation": {
                "h1_basic_shares": 76_054_642.0,
                "class_b_conversion_units": 116_158_615.0,
                "conversion_ratio": 1.0,
                "incremental_dilution": incremental_dilution,
                "h1_diluted_shares": 193_323_374.0,
                "difference": 76_054_642.0 + 116_158_615.0 + incremental_dilution - 193_323_374.0,
                "nci_deducted_separately": False,
                "redeemable_nci_deducted": redeemable_nci,
            },
        }
    raise ValueError(f"{ticker}: no launch-first bridge")


def _annual_context(normalizer: Any) -> dict[str, list[dict[str, Any]]]:
    return {
        field: [row.as_dict() for row in normalizer.annual_series(field, 5)]
        for field in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")
    }


def _derived_cash_margins(
    *,
    ticker: str,
    policy: ConditionalPolicy,
    normalizer: Any,
    bridge: Mapping[str, Any],
    capex: Mapping[str, Any] | None,
) -> tuple[tuple[float, float, float], dict[str, Any]]:
    interest = normalizer.ttm_flow("interest_expense")
    tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    tax_rate = min(0.30, max(0.15, float(tax_rate)))
    after_tax_interest = abs(float(interest["value"])) * (1 - tax_rate)
    revenue = policy.expected_revenue
    pre_capex_cash = policy.expected_operating_cash_flow + after_tax_interest
    context = _annual_context(normalizer)
    by_field = {
        field: {row["end"]: float(row["value"]) for row in rows}
        for field, rows in context.items()
    }
    common = sorted(
        set(by_field["revenue"])
        & set(by_field["operating_cash_flow"])
        & set(by_field["capital_expenditures"])
        & set(by_field["interest_expense"])
    )
    historical_margins = [
        (
            by_field["operating_cash_flow"][end]
            - by_field["capital_expenditures"][end]
            + abs(by_field["interest_expense"][end]) * (1 - tax_rate)
        )
        / by_field["revenue"][end]
        for end in common
        if by_field["revenue"][end] > 0
    ]
    if ticker == "TKO":
        rates = bridge["reinvestment_rates"]
        margins = tuple(pre_capex_cash / revenue - rate for rate in rates)
        calculation = {
            "method": "gross TTM owner cash less explicit FinSight capex/rights reinvestment reserve",
            "reinvestment_rates": rates,
        }
    elif ticker == "APP":
        capex_periods = sorted(set(by_field["capital_expenditures"]) & set(by_field["revenue"]))
        capex_ratios = [
            by_field["capital_expenditures"][end] / by_field["revenue"][end]
            for end in capex_periods
            if by_field["revenue"][end] > 0
        ]
        if len(capex_ratios) < 3 or len(historical_margins) < 2:
            raise ValueError("APP: capex and cash history do not bound a conditional range")
        current = (
            pre_capex_cash / revenue - max(capex_ratios),
            pre_capex_cash / revenue - median(capex_ratios),
            pre_capex_cash / revenue - min(capex_ratios),
        )
        pool = historical_margins[-3:] + list(current)
        margins = (
            max(0.01, min(pool) * 0.80),
            median(pool),
            max(pool) * 1.05,
        )
        calculation = {
            "method": "TTM pre-capex cash less historical capex/revenue range, bounded by annual owner-cash margins",
            "historical_capex_ratios": capex_ratios,
        }
    else:
        if capex is None or len(historical_margins) < 2:
            raise ValueError(f"{ticker}: reported cash history is insufficient")
        current_margin = (
            pre_capex_cash - float(capex["value"])
        ) / revenue
        pool = historical_margins[-3:] + [current_margin]
        if ticker == "GOOGL":
            commitment = bridge["commitment_inputs"]["total_purchase_commitments"]
            horizons = bridge["commitment_inputs"]["cash_realization_horizons_years"]
            effective_capex = tuple(
                max(float(capex["value"]), commitment / horizon)
                for horizon in horizons
            )
            commitment_margins = tuple(
                (pre_capex_cash - amount) / revenue for amount in effective_capex
            )
            margins = (
                max(0.01, min((*pool, commitment_margins[0])) * 0.90),
                median((commitment_margins[1], *historical_margins[-2:])),
                max((*pool, commitment_margins[2])) * 1.05,
            )
            calculation = {
                "method": "reported capex versus annualized purchase-commitment burden without double counting",
                "commitment_horizons_years": horizons,
                "effective_reinvestment": effective_capex,
            }
        elif ticker == "FOXA":
            commitment = bridge["commitment_inputs"]["next_twelve_month_contractual_other_and_program_rights"]
            fractions = bridge["commitment_inputs"]["incremental_cash_reserve_fractions"]
            anchors = (min(pool), median(pool), max(pool))
            margins = tuple(
                max(0.005, anchor - commitment * fraction / revenue)
                for anchor, fraction in zip(anchors, fractions)
            )
            calculation = {
                "method": "historical/current owner-cash margins less explicit incremental rights reserve",
                "incremental_reserve_fractions": fractions,
                "incremental_reserve_amounts": tuple(commitment * fraction for fraction in fractions),
            }
        else:
            margins = (
                max(0.005, min(pool) * 0.75),
                median(pool),
                max(pool) * 1.25,
            )
            calculation = {"method": "current and three recent annual owner-cash margins"}
    if not 0 < margins[0] <= margins[1] <= margins[2] < 1:
        raise ValueError(f"{ticker}: derived cash margins are invalid")
    return margins, {
        **calculation,
        "normalized_tax_rate": tax_rate,
        "tax_sources": tax_sources,
        "ttm_interest_expense": interest,
        "historical_cash_margins": historical_margins,
        "annual_context": context,
        "derived_cash_margins": margins,
    }


def build_batch_03_launch_first_result(
    *,
    ticker: str,
    source_root: Path,
    structural_root: Path,
    primary_rejection_reasons: tuple[str, ...],
) -> dict[str, Any]:
    ticker = ticker.strip().upper()
    if ticker not in LAUNCH_FIRST_CONDITIONAL_TICKERS:
        raise ValueError(f"{ticker}: no approved launch-first conditional route")
    policy = _POLICIES[ticker]
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    companyfacts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    if (
        manifest.get("valuation_date") != BATCH_03_VALUATION_DATE
        or manifest.get("issuer", {}).get("ticker") != ticker
        or normalize_cik(manifest.get("issuer", {}).get("cik"))
        != normalize_cik(submissions.get("cik"))
        or normalize_cik(manifest.get("issuer", {}).get("cik"))
        != normalize_cik(companyfacts.get("cik"))
        or not primary_rejection_reasons
    ):
        raise ValueError(f"{ticker}: launch-first source identity or rejection receipt is invalid")
    filing = max(manifest["eligible_filings"], key=lambda row: (row["filed"], row["accession"]))
    if (
        filing["filed"] > BATCH_03_VALUATION_DATE
        or filing["form"] not in {"10-K", "10-K/A", "10-Q", "10-Q/A"}
        or structural.get("source_accession") != filing["accession"]
    ):
        raise ValueError(f"{ticker}: source and structural filing identity disagree")
    normalizer = _normalizer(submissions, companyfacts)
    revenue = normalizer.ttm_flow("revenue")
    operating_cash_flow = normalizer.ttm_flow("operating_cash_flow")
    if float(revenue["value"]) != policy.expected_revenue:
        raise ValueError(f"{ticker}: TTM revenue changed")
    if float(operating_cash_flow["value"]) != policy.expected_operating_cash_flow:
        raise ValueError(f"{ticker}: TTM operating cash flow changed")
    capex = None
    if policy.expected_capex is not None:
        capex = normalizer.ttm_flow("capital_expenditures")
        if float(capex["value"]) != policy.expected_capex:
            raise ValueError(f"{ticker}: TTM capex changed")
    bridge = _bridge(ticker, structural)
    margins, margin_evidence = _derived_cash_margins(
        ticker=ticker,
        policy=policy,
        normalizer=normalizer,
        bridge=bridge,
        capex=capex,
    )
    rows = []
    values = []
    raw_values = []
    for index, name in enumerate(("bear", "base", "bull")):
        model = five_year_fcff_dcf(
            revenue=policy.expected_revenue,
            fcff_margin=margins[index],
            growth=policy.growth[index],
            wacc=policy.wacc[index],
            terminal_growth=policy.terminal_growth[index],
            cash_and_investments=bridge["cash_and_investments"][index],
            debt=bridge["debt"],
            noncontrolling_interests=bridge["other_claims"][index],
            shares=policy.shares[index],
        )
        raw_value = model["value_per_share"]
        raw_values.append(raw_value)
        floor_applied = raw_value < 0
        if floor_applied and name != "bear":
            raise ValueError(f"{ticker}: nonpositive base/bull residual equity is unavailable")
        value = 0.0 if floor_applied else raw_value
        values.append(value)
        rows.append(
            {
                "name": name,
                "cash_conversion_margin": margins[index],
                "growth": policy.growth[index],
                "wacc": policy.wacc[index],
                "terminal_growth": policy.terminal_growth[index],
                "shares": policy.shares[index],
                **model,
                "raw_residual_value_per_share": raw_value,
                "conditional_value_per_share": value,
                "limited_liability_floor_applied": floor_applied,
            }
        )
    value_range = ConditionalRange(*values)
    floor_applied = any(row["limited_liability_floor_applied"] for row in rows)
    floor_basis = (
        "The bear scenario reaches a limited-liability common-equity floor of zero; "
        "its negative raw residual is retained privately and is not used as an ordinary value."
    )
    public_warning = f"{policy.warning} {floor_basis}" if floor_applied else policy.warning
    assumptions = (
        BaselineAssumption("ttm_revenue", policy.expected_revenue, AssumptionClassification.REPORTED, "Cutoff-eligible SEC filing reconstruction."),
        BaselineAssumption("cash_conversion_margin", margins[1], AssumptionClassification.HISTORICALLY_DERIVED, str(margin_evidence["method"])),
        BaselineAssumption("discount_rate", policy.wacc[1], AssumptionClassification.FINSIGHT_ASSUMPTION, "Governed scenario discount rate."),
        BaselineAssumption("initial_growth", policy.growth[1], AssumptionClassification.FINSIGHT_ASSUMPTION, "Governed company/archetype scenario."),
        BaselineAssumption("terminal_growth", policy.terminal_growth[1], AssumptionClassification.FINSIGHT_ASSUMPTION, "Governed long-run scenario below the discount rate."),
        BaselineAssumption("diluted_shares", policy.shares[1], AssumptionClassification.FINSIGHT_ASSUMPTION, "Reported share evidence with explicit dilution/conversion stress."),
        BaselineAssumption("claims_and_commitment_treatment", bridge["special_treatment"], AssumptionClassification.FINSIGHT_ASSUMPTION, policy.assumption_basis),
    )

    def reject_primary() -> BaselineValuation:
        raise FallbackRejected("; ".join(primary_rejection_reasons))

    def conditional() -> BaselineValuation:
        return BaselineValuation(
            ticker=ticker,
            method=policy.method,
            method_version=LAUNCH_FIRST_BATCH_03_VERSION,
            low=value_range.low,
            base=value_range.base,
            high=value_range.high,
            confidence="Low",
            availability_type=AvailabilityType.CONDITIONAL,
            key_assumptions=assumptions,
            warnings=(public_warning, policy.invalidation),
            confidence_reasons=("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"),
            calculator_link=f"/api/us-valuations/{ticker}/calculator",
        )

    baseline = run_fallback_ladder(
        ticker=ticker,
        strategies=(
            (FallbackStage.PRIMARY_INTRINSIC, "fcff_dcf", reject_primary),
            (FallbackStage.CONDITIONAL, policy.method, conditional),
        ),
    )
    return {
        "ticker": ticker,
        "model_version": LAUNCH_FIRST_BATCH_03_VERSION,
        "method": policy.method,
        "availability_type": AvailabilityType.CONDITIONAL.value,
        "scenario_range": value_range.as_dict(),
        "scenario_rows": rows,
        "reported_inputs": {
            "ttm_revenue": policy.expected_revenue,
            "ttm_operating_cash_flow": policy.expected_operating_cash_flow,
            "ttm_capex": policy.expected_capex,
        },
        "governed_assumptions": {
            "forecast_years": 5,
            "cash_conversion_margin": margins,
            "initial_growth": policy.growth,
            "wacc": policy.wacc,
            "terminal_growth": policy.terminal_growth,
            "shares": policy.shares,
            "limited_liability_floor": {
                "applied": floor_applied,
                "basis": floor_basis,
            },
            "assumption_basis": policy.assumption_basis,
            "invalidation": policy.invalidation,
        },
        "source_ledger": {
            "revenue": revenue,
            "operating_cash_flow": operating_cash_flow,
            "capital_expenditures": capex,
            "margin_derivation": margin_evidence,
            "bridge": bridge,
            "primary_rejection_reasons": list(primary_rejection_reasons),
        },
        "raw_scenario_values": raw_values,
        "warning": public_warning,
        "baseline": baseline.as_private_dict(),
    }


def _psky_rejected_conditional_replay(
    *, source_root: Path, structural_root: Path
) -> dict[str, Any]:
    packet = Path(source_root) / "PSKY"
    submissions = json.loads((packet / "submissions.json").read_text())
    companyfacts = json.loads((packet / "companyfacts.json").read_text())
    structural = json.loads((Path(structural_root) / "PSKY" / "structural-filing.json").read_text())
    normalizer = _normalizer(submissions, companyfacts)
    revenue = normalizer.ttm_flow("revenue")
    if float(revenue["value"]) != 29_432_000_000.0:
        raise ValueError("PSKY: rejected replay revenue changed")
    sources = [
        _point(structural, name="CashAndCashEquivalentsAtCarryingValue", expected=1_627_000_000.0),
        _point(structural, name="DebtAndCapitalLeaseObligations", expected=15_156_000_000.0),
        _point(structural, name="MinorityInterest", expected=1_039_000_000.0),
        _duration(
            structural,
            name="WeightedAverageNumberOfDilutedSharesOutstanding",
            expected=1_119_000_000.0,
        ),
    ]
    margins = (0.01, 0.03, 0.06)
    growth = (-0.03, 0.0, 0.03)
    wacc = (0.12, 0.105, 0.095)
    terminal_growth = (-0.01, 0.01, 0.02)
    shares = (1_180_000_000.0, 1_121_000_000.0, 1_070_000_000.0)
    rows = []
    for index, name in enumerate(("bear", "base", "bull")):
        model = five_year_fcff_dcf(
            revenue=29_432_000_000.0,
            fcff_margin=margins[index],
            growth=growth[index],
            wacc=wacc[index],
            terminal_growth=terminal_growth[index],
            cash_and_investments=1_627_000_000.0,
            debt=15_156_000_000.0,
            noncontrolling_interests=1_039_000_000.0,
            shares=shares[index],
        )
        rows.append({"name": name, **model})
    return {
        "valuation_object": "current-successor-only",
        "reported_revenue": revenue,
        "source_ledger": sources,
        "assumptions": {
            "cash_conversion_margin": margins,
            "growth": growth,
            "wacc": wacc,
            "terminal_growth": terminal_growth,
            "shares": shares,
        },
        "rows": rows,
        "raw_range": {
            "low": rows[0]["value_per_share"],
            "base": rows[1]["value_per_share"],
            "high": rows[2]["value_per_share"],
        },
        "decision": "rejected_nonpositive_base_without_comparable_successor_history",
    }


def build_batch_03_launch_first_hard_failure(
    ticker: str,
    *,
    source_root: Path | None = None,
    structural_root: Path | None = None,
) -> dict[str, Any]:
    ticker = ticker.strip().upper()
    reasons = LAUNCH_FIRST_HARD_FAILURES.get(ticker)
    if reasons is None:
        raise ValueError(f"{ticker}: no approved launch-first hard failure")
    baseline = run_fallback_ladder(ticker=ticker, strategies=(), hard_failures=reasons)
    result = {
        "ticker": ticker,
        "model_version": LAUNCH_FIRST_BATCH_03_VERSION,
        "availability_type": AvailabilityType.NOT_AVAILABLE.value,
        "hard_failures": list(reasons),
        "baseline": baseline.as_private_dict(),
    }
    if ticker == "PSKY":
        if source_root is None or structural_root is None:
            raise ValueError("PSKY: rejected conditional replay roots are required")
        result["rejected_conditional_replay"] = _psky_rejected_conditional_replay(
            source_root=source_root,
            structural_root=structural_root,
        )
    return result
