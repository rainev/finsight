"""Transparent, Low-only conditional values for the six Batch 02 holdouts.

These are deliberately not source-bounded intrinsic values. Reported filing facts and
governed hypothetical assumptions are kept separate so the estimates remain auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping


CONDITIONAL_VERSION = "BATCH-02-CONDITIONAL-ESTIMATE-1.0"
CONDITIONAL_TICKERS = ("OMC", "TTWO", "CHTR", "CMCSA", "META", "WBD")
COMMON_WARNING = (
    "Conditional Low-reliability estimate. Uses reported facts plus hypothetical "
    "future-event assumptions; actual value may fall materially outside this range. "
    "Not a reported fact or recommendation."
)


@dataclass(frozen=True)
class ConditionalRange:
    low: float
    base: float
    high: float

    def __post_init__(self) -> None:
        values = (self.low, self.base, self.high)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("conditional values must be finite")
        if (
            self.low < 0
            or not self.low <= self.base <= self.high
            or (self.base == 0 and self.high <= 0)
        ):
            raise ValueError("conditional range must be nonnegative, ordered, and contain positive upside")

    def as_dict(self) -> dict[str, float]:
        return {"low": self.low, "base": self.base, "high": self.high}


def multiple_equity_value(
    *,
    revenue: float,
    cash_margin: float,
    multiple: float,
    cash_and_investments: float,
    debt: float,
    other_claims: float,
    shares: float,
) -> dict[str, float]:
    if min(revenue, cash_margin, multiple, cash_and_investments, debt, other_claims, shares) < 0:
        raise ValueError("conditional multiple inputs must be nonnegative")
    if revenue <= 0 or cash_margin <= 0 or multiple <= 0 or shares <= 0:
        raise ValueError("conditional multiple operating inputs must be positive")
    owner_cash = revenue * cash_margin
    equity = owner_cash * multiple + cash_and_investments - debt - other_claims
    return {
        "owner_cash": owner_cash,
        "enterprise_or_cash_value": owner_cash * multiple,
        "equity_value": equity,
        "value_per_share": equity / shares,
    }


def five_year_fcff_dcf(
    *,
    revenue: float,
    fcff_margin: float,
    growth: float,
    wacc: float,
    terminal_growth: float,
    cash_and_investments: float,
    debt: float,
    noncontrolling_interests: float,
    shares: float,
) -> dict[str, float]:
    values = (
        revenue,
        fcff_margin,
        growth,
        wacc,
        terminal_growth,
        cash_and_investments,
        debt,
        noncontrolling_interests,
        shares,
    )
    if any(not math.isfinite(value) for value in values):
        raise ValueError("conditional DCF inputs must be finite")
    if min(revenue, fcff_margin, wacc, cash_and_investments, debt, noncontrolling_interests, shares) < 0:
        raise ValueError("conditional DCF levels must be nonnegative")
    if revenue <= 0 or fcff_margin <= 0 or shares <= 0 or wacc <= terminal_growth:
        raise ValueError("conditional DCF requires positive scale and WACC above terminal growth")
    fcff = revenue * fcff_margin
    explicit_pv = 0.0
    for year in range(1, 6):
        fcff *= 1 + growth
        explicit_pv += fcff / (1 + wacc) ** year
    terminal_value = fcff * (1 + terminal_growth) / (wacc - terminal_growth)
    terminal_pv = terminal_value / (1 + wacc) ** 5
    enterprise = explicit_pv + terminal_pv
    equity = enterprise + cash_and_investments - debt - noncontrolling_interests
    return {
        "explicit_pv": explicit_pv,
        "terminal_pv": terminal_pv,
        "enterprise_value": enterprise,
        "equity_value": equity,
        "value_per_share": equity / shares,
    }


def _source(
    *, ticker: str, accession: str, filed: str, period_end: str, url: str
) -> dict[str, str]:
    return {
        "ticker": ticker,
        "accession": accession,
        "filed_date": filed,
        "period_end": period_end,
        "unit": "USD",
        "source_url": url,
        "reported_vs_estimated": "reported",
    }


SOURCES = {
    "OMC": _source(
        ticker="OMC", accession="0000029989-26-000019", filed="2026-07-29",
        period_end="2026-06-30",
        url="https://www.sec.gov/Archives/edgar/data/29989/000002998926000019/omc-20260630.htm",
    ),
    "TTWO": _source(
        ticker="TTWO", accession="0001628280-26-054870", filed="2026-08-07",
        period_end="2026-06-30",
        url="https://www.sec.gov/Archives/edgar/data/946581/000162828026054870/ttwo-20260630.htm",
    ),
    "CHTR": _source(
        ticker="CHTR", accession="0001091667-26-000052", filed="2026-07-24",
        period_end="2026-06-30",
        url="https://www.sec.gov/Archives/edgar/data/1091667/000109166726000052/chtr-20260630.htm",
    ),
    "CMCSA": _source(
        ticker="CMCSA", accession="0001628280-26-049360", filed="2026-07-23",
        period_end="2026-06-30",
        url="https://www.sec.gov/Archives/edgar/data/1166691/000162828026049360/cmcsa-20260630.htm",
    ),
    "META": _source(
        ticker="META", accession="0001628280-26-050705", filed="2026-07-30",
        period_end="2026-06-30",
        url="https://www.sec.gov/Archives/edgar/data/1326801/000162828026050705/meta-20260630.htm",
    ),
    "WBD": _source(
        ticker="WBD", accession="0001437107-26-000075", filed="2026-08-06",
        period_end="2026-06-30",
        url="https://www.sec.gov/Archives/edgar/data/1437107/000143710726000075/wbd-20260630.htm",
    ),
}

ANNUAL_SOURCES = {
    "CHTR": _source(
        ticker="CHTR", accession="0001091667-26-000017", filed="2026-01-30",
        period_end="2025-12-31",
        url="https://www.sec.gov/Archives/edgar/data/1091667/000109166726000017/chtr-20251231.htm",
    ),
    "CMCSA": _source(
        ticker="CMCSA", accession="0001628280-26-004994", filed="2026-02-03",
        period_end="2025-12-31",
        url="https://www.sec.gov/Archives/edgar/data/1166691/000162828026004994/cmcsa-20251231.htm",
    ),
    "WBD": _source(
        ticker="WBD", accession="0001437107-26-000020", filed="2026-02-27",
        period_end="2025-12-31",
        url="https://www.sec.gov/Archives/edgar/data/1437107/000143710726000020/wbd-20251231.htm",
    ),
}


def _omc() -> dict[str, Any]:
    reported = {
        "h1_operating_income": 1_568_700_000.0,
        "h1_depreciation_amortization": 333_200_000.0,
        "h1_capex": 115_100_000.0,
        "cash": 3_336_200_000.0,
        "debt": 10_002_000_000.0,
        "noncontrolling_interests": 610_400_000.0,
        "h1_diluted_weighted_shares": 290_200_000.0,
    }
    tax = 0.24
    normalized_fcff = (
        reported["h1_operating_income"] * 2 * (1 - tax)
        + reported["h1_depreciation_amortization"] * 2
        - reported["h1_capex"] * 2
    )
    leases = (119_269_104.35497124, 104_500_000.0, 89_730_895.64502876)
    multiples = (7.0, 10.0, 13.0)
    shares = (304_710_000.0, 297_455_000.0, 290_200_000.0)
    rows = []
    for name, multiple, lease, share_count in zip(
        ("bear", "base", "bull"), multiples, leases, shares
    ):
        row = multiple_equity_value(
            revenue=normalized_fcff,
            cash_margin=1.0,
            multiple=multiple,
            cash_and_investments=reported["cash"],
            debt=reported["debt"],
            other_claims=reported["noncontrolling_interests"] + lease,
            shares=share_count,
        )
        rows.append({"name": name, "multiple": multiple, "lease_reserve": lease, "shares": share_count, **row})
    return _result(
        ticker="OMC", method="post_combination_normalized_fcff_multiple",
        rows=rows, reported=reported,
        assumptions={
            "normalized_tax_rate": tax,
            "normalized_fcff": normalized_fcff,
            "multiples": multiples,
            "share_sensitivity": shares,
            "assumption_governance": (
                "The 7x/10x/13x cash-value band and 24% tax rate are governed hypothetical "
                "normalization states, deliberately broad because combined history is short. "
                "Invalidate after a full comparable combined year or material purchase-accounting revision."
            ),
        },
        source_ledger={
            "h1_operating_inputs": SOURCES["OMC"],
            "bridge": SOURCES["OMC"],
            "h1_diluted_weighted_shares": {
                **SOURCES["OMC"],
                "period_start": "2026-01-01",
                "period_end": "2026-06-30",
                "period_role": "duration_weighted_average",
            },
        },
        warning="Conditional estimate. OMC's recent combination changes comparability, so normalized cash flow and valuation multiples are assumptions. Actual value may differ materially.",
    )


def _ttwo() -> dict[str, Any]:
    reported = {
        "quarter_revenue": 1_533_900_000.0,
        "quarter_operating_cash_flow": -168_800_000.0,
        "quarter_capex": 25_000_000.0,
        "cash_and_investments": 1_826_600_000.0,
        "debt": 2_519_700_000.0,
        "shares": 186_980_443.0,
        "total_assets": 9_064_200_000.0,
    }
    annualized_revenue = reported["quarter_revenue"] * 4
    margins = (0.05, 0.15, 0.25)
    multiples = (12.0, 18.0, 24.0)
    shares = (
        reported["shares"] * 1.10,
        reported["shares"] * 1.05,
        reported["shares"],
    )
    unresolved_claims = (
        reported["total_assets"] * 0.05,
        reported["total_assets"] * 0.025,
        0.0,
    )
    rows = []
    for name, margin, multiple, share_count, claims in zip(
        ("bear", "base", "bull"), margins, multiples, shares, unresolved_claims
    ):
        rows.append({
            "name": name,
            "assumed_fcfe_margin": margin,
            "multiple": multiple,
            "shares": share_count,
            "unresolved_claims_reserve": claims,
            **multiple_equity_value(
                revenue=annualized_revenue,
                cash_margin=margin,
                multiple=multiple,
                cash_and_investments=reported["cash_and_investments"],
                debt=reported["debt"],
                other_claims=claims,
                shares=share_count,
            ),
        })
    return _result(
        ticker="TTWO", method="major_release_outcome_equity_cash_multiple",
        rows=rows, reported=reported,
        assumptions={
            "annualized_revenue": annualized_revenue,
            "assumed_fcfe_margins": margins,
            "multiples": multiples,
            "share_sensitivity": shares,
            "unresolved_claims_reserve": unresolved_claims,
            "current_cash_anchor": "Current quarterly operating cash flow less capex is negative; every positive owner-cash state is hypothetical.",
            "assumption_governance": (
                "The 5%/15%/25% owner-cash margins and 12x/18x/24x multiples are weak/normal/strong "
                "major-release states, not issuer guidance. Invalidate or recalibrate after the first post-release cash filing."
            ),
        },
        source_ledger={
            "quarter_flows_bridge_and_assets": SOURCES["TTWO"],
            "common_shares_outstanding": {
                **SOURCES["TTWO"],
                "as_of_date": "2026-07-27",
                "period_role": "instant",
            },
        },
        warning="Conditional estimate. TTWO's value is highly sensitive to the timing, reception, and profitability of major game releases, especially GTA VI. This range is scenario-based, not a forecast.",
    )


def _chtr() -> dict[str, Any]:
    reported = {
        "fy2025_revenue": 54_774_000_000.0,
        "cash": 509_000_000.0,
        "debt": 93_959_000_000.0,
        "noncontrolling_interests": 4_949_000_000.0,
        "diluted_shares": 123_969_262.0,
        "h1_revenue": 27_123_000_000.0,
        "h1_operating_cash_flow": 8_229_000_000.0,
        "h1_capex": 5_726_000_000.0,
    }
    dcf_inputs = (
        ("bear", 0.10, -0.02, 0.10, 0.00),
        ("base", 0.128, 0.00, 0.095, 0.01),
        ("bull", 0.15, 0.02, 0.085, 0.02),
    )
    current_rows = []
    for name, margin, growth, wacc, terminal in dcf_inputs:
        current_rows.append({
            "name": name, "fcff_margin": margin, "growth": growth,
            "wacc": wacc, "terminal_growth": terminal,
            **five_year_fcff_dcf(
                revenue=reported["fy2025_revenue"], fcff_margin=margin,
                growth=growth, wacc=wacc, terminal_growth=terminal,
                cash_and_investments=reported["cash"], debt=reported["debt"],
                noncontrolling_interests=reported["noncontrolling_interests"],
                shares=reported["diluted_shares"],
            ),
        })
    rows = [
        {"name": "standalone_bear", "value_per_share": 0.0, "basis": "limited_liability_floor_after_negative_bear_residual"},
        {"name": "standalone_base", "value_per_share": 0.0, "basis": "limited_liability_floor_after_negative_base_residual"},
        {"name": "standalone_bull", "value_per_share": current_rows[2]["value_per_share"], "basis": "positive_current_company_bull_residual"},
    ]
    return _result(
        ticker="CHTR", method="equity_at_risk_event_envelope",
        rows=rows, reported=reported,
        assumptions={
            "current_company_dcf_states": current_rows,
            "current_h1_cash_after_capex_margin": (
                reported["h1_operating_cash_flow"] - reported["h1_capex"]
            ) / reported["h1_revenue"],
            "assumption_governance": (
                "The standalone 10%/12.8%/15% FCFF-margin states are governed normalized scenarios "
                "starting slightly above the reported H1 cash-after-capex margin of about 9.2%. "
                "Pending Cox/Liberty terms are excluded until final filed pro forma economics exist."
            ),
        },
        source_ledger={
            "fy2025_revenue": ANNUAL_SOURCES["CHTR"],
            "current_bridge_and_diluted_shares": SOURCES["CHTR"],
        },
        warning="Conditional standalone equity-at-risk estimate. Bear and base residual equity are negative, so $0 is a limited-liability floor—not a forecast of zero operating value. Pending Cox/Liberty terms are excluded.",
    )


def _cmcsa() -> dict[str, Any]:
    reported = {
        "fy2025_revenue": 123_707_000_000.0,
        "cash_and_securities": 15_506_000_000.0,
        "debt": 90_381_000_000.0,
        "noncontrolling_interests": 7_000_000.0,
        "diluted_shares": 3_593_000_000.0,
        "h1_revenue": 61_396_000_000.0,
        "h1_operating_cash_flow": 14_983_000_000.0,
        "h1_capex": 5_253_000_000.0,
    }
    inputs = (
        ("bear", 0.07, -0.02, 0.10, 0.00),
        ("base", 0.10, 0.00, 0.081, 0.015),
        ("bull", 0.12, 0.02, 0.075, 0.02),
    )
    rows = []
    for name, margin, growth, wacc, terminal in inputs:
        rows.append({
            "name": name, "fcff_margin": margin, "growth": growth,
            "wacc": wacc, "terminal_growth": terminal,
            **five_year_fcff_dcf(
                revenue=reported["fy2025_revenue"], fcff_margin=margin,
                growth=growth, wacc=wacc, terminal_growth=terminal,
                cash_and_investments=reported["cash_and_securities"],
                debt=reported["debt"],
                noncontrolling_interests=reported["noncontrolling_interests"],
                shares=reported["diluted_shares"],
            ),
        })
    return _result(
        ticker="CMCSA", method="current_consolidated_conditional_fcff_dcf",
        rows=rows, reported=reported,
        assumptions={
            "dcf_states": inputs,
            "post_separation_value_claimed": False,
            "current_h1_cash_after_capex_margin": (
                reported["h1_operating_cash_flow"] - reported["h1_capex"]
            ) / reported["h1_revenue"],
            "assumption_governance": (
                "The 7%/10%/12% FCFF-margin states are conservative normalized FCFF scenarios below "
                "the reported H1 cash-after-capex margin of about 15.9%; growth, WACC, and terminal "
                "ranges are governed mature-media states. Invalidate after filed separation allocations."
            ),
        },
        source_ledger={
            "fy2025_revenue": ANNUAL_SOURCES["CMCSA"],
            "current_bridge_and_diluted_shares": SOURCES["CMCSA"],
        },
        warning="Conditional estimate of today's consolidated Comcast. It is not a post-separation value because future debt, cash, and corporate-cost allocations are not filed.",
    )


def _meta() -> dict[str, Any]:
    reported = {
        "h1_revenue": 117_111_000_000.0,
        "h1_operating_cash_flow": 64_088_000_000.0,
        "h1_capex": 49_113_000_000.0,
        "cash_and_securities": 90_260_000_000.0,
        "debt": 83_664_000_000.0,
        "shares": 2_548_000_000.0,
        "diluted_weighted_shares": 2_566_000_000.0,
        "total_assets": 449_956_000_000.0,
        "uncommenced_commitments": 278_990_000_000.0,
    }
    annualized_revenue = reported["h1_revenue"] * 2
    margins = (0.13, 0.25, 0.35)
    multiples = (14.0, 18.0, 22.0)
    leases = (1_977_229_901.2693937, 1_184_000_000.0, 390_770_098.73060656)
    shares = (2_592_000_000.0, 2_566_000_000.0, 2_548_000_000.0)
    unresolved_claims = (
        reported["total_assets"] * 0.01,
        reported["total_assets"] * 0.005,
        0.0,
    )
    rows = []
    for name, margin, multiple, lease, share_count, claims in zip(
        ("bear", "base", "bull"), margins, multiples, leases, shares, unresolved_claims
    ):
        rows.append({
            "name": name, "assumed_cash_conversion_margin": margin, "multiple": multiple,
            "lease_reserve": lease, "unresolved_equity_claims_reserve": claims,
            "shares": share_count,
            **multiple_equity_value(
                revenue=annualized_revenue, cash_margin=margin, multiple=multiple,
                cash_and_investments=reported["cash_and_securities"],
                debt=reported["debt"], other_claims=lease + claims, shares=share_count,
            ),
        })
    return _result(
        ticker="META", method="ai_capex_cash_conversion_equity_multiple",
        rows=rows, reported=reported,
        assumptions={
            "annualized_revenue": annualized_revenue,
            "assumed_cash_conversion_margins": margins,
            "multiples": multiples,
            "share_sensitivity": shares,
            "unresolved_equity_claims_reserve": unresolved_claims,
            "commitments_handling": "captured_in_cash_conversion_scenarios_not_deducted_again",
            "current_cash_anchor": "H1 operating cash flow less capex equals 14.975bn, or about 12.8% of H1 revenue.",
            "assumption_governance": (
                "The 13% bear margin anchors to current H1 post-capex cash conversion; 25%/35% and 14x/18x/22x "
                "are governed recovery/return states. Invalidate if commitment cash is not captured in future cash conversion."
            ),
        },
        source_ledger={"h1_flows_bridge_commitments_and_dilution": SOURCES["META"]},
        warning="Conditional estimate. META's value depends heavily on AI infrastructure spending, future cash conversion, and large uncommenced commitments; the obligations are not deducted twice.",
    )


def _wbd() -> dict[str, Any]:
    reported = {
        "fy2025_revenue": 37_296_000_000.0,
        "cash": 3_369_000_000.0,
        "debt": 33_516_000_000.0,
        "noncontrolling_interests": 1_157_000_000.0,
        "diluted_shares": 2_501_000_000.0,
        "merger_cash_per_share": 31.0,
        "ticking_cash_per_day": 0.00277778,
        "h1_revenue": 17_610_000_000.0,
        "h1_operating_cash_flow": 640_000_000.0,
        "h1_capex": 544_000_000.0,
    }
    inputs = (
        ("bear", 0.04, -0.05, 0.12, 0.00),
        ("base", 0.08, 0.00, 0.10, 0.01),
        ("bull", 0.12, 0.03, 0.09, 0.02),
    )
    standalone = []
    for name, margin, growth, wacc, terminal in inputs:
        standalone.append({
            "name": name, "fcff_margin": margin, "growth": growth,
            "wacc": wacc, "terminal_growth": terminal,
            **five_year_fcff_dcf(
                revenue=reported["fy2025_revenue"], fcff_margin=margin,
                growth=growth, wacc=wacc, terminal_growth=terminal,
                cash_and_investments=reported["cash"], debt=reported["debt"],
                noncontrolling_interests=reported["noncontrolling_interests"],
                shares=reported["diluted_shares"],
            ),
        })
    contract_high = 31.0 + 247 * reported["ticking_cash_per_day"]
    rows = [
        {"name": "standalone_downside", "value_per_share": 0.0, "basis": "limited_liability_floor_after_negative_bear_residual"},
        {"name": "standalone_base", "value_per_share": standalone[1]["value_per_share"], "basis": "normalized_standalone_fcff_estimate"},
        {"name": "standalone_bull", "value_per_share": standalone[2]["value_per_share"], "basis": "normalized_standalone_bull_estimate"},
    ]
    return _result(
        ticker="WBD", method="standalone_plus_separate_contract_event_envelope",
        rows=rows, reported=reported,
        assumptions={
            "standalone_dcf_states": standalone,
            "merger_consideration_is_intrinsic_value": False,
            "probability_weighted": False,
            "contract_cash_if_closed_by_2026_09_30": 31.0,
            "contract_calendar_illustration_2027_06_04": contract_high,
            "current_h1_cash_after_capex_margin": (
                reported["h1_operating_cash_flow"] - reported["h1_capex"]
            ) / reported["h1_revenue"],
            "assumption_governance": (
                "The 4%/8%/12% FCFF-margin states are governed normalized recovery scenarios above "
                "the unusually weak reported H1 cash-after-capex margin of about 0.5%. "
                "The contract amount is a separate filed event term and is never mixed into standalone value or probability-weighted."
            ),
        },
        source_ledger={
            "fy2025_revenue": ANNUAL_SOURCES["WBD"],
            "current_bridge_and_diluted_shares": SOURCES["WBD"],
            "contractual_consideration": {
                **SOURCES["WBD"],
                "as_of_date": "2026-02-27",
                "period_role": "merger_agreement_term",
            },
        },
        warning="Conditional standalone estimate. The low endpoint is a limited-liability floor, not a forecast of zero operating value. Filed $31-plus ticking merger cash is shown separately and is not probability-weighted intrinsic value.",
    )


def _result(
    *, ticker: str, method: str, rows: list[dict[str, Any]],
    reported: Mapping[str, float], assumptions: Mapping[str, Any],
    source_ledger: Mapping[str, Any], warning: str,
) -> dict[str, Any]:
    values = [float(row["value_per_share"]) for row in rows]
    value_range = ConditionalRange(values[0], values[1], values[2])
    return {
        "ticker": ticker,
        "model": "conditional_estimate",
        "output_type": "conditional_value_per_share",
        "model_version": CONDITIONAL_VERSION,
        "method": method,
        "publication_state": "review_required",
        "reliability": "Low",
        "warning": warning,
        "source": SOURCES[ticker],
        "input_source_ledger": dict(source_ledger),
        "reported_inputs": dict(reported),
        "governed_assumptions": dict(assumptions),
        "scenario_rows": rows,
        "scenario_range": value_range.as_dict(),
        "reason_codes": ["CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"],
    }


def build_conditional_estimates() -> dict[str, dict[str, Any]]:
    results = {row["ticker"]: row for row in (_omc(), _ttwo(), _chtr(), _cmcsa(), _meta(), _wbd())}
    if tuple(results) != CONDITIONAL_TICKERS:
        raise ValueError("conditional estimate denominator mismatch")
    return results
