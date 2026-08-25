"""Practical Batch 01 model application over frozen, point-in-time evidence."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import date
from statistics import median
from typing import Any, Mapping, Sequence

from .practical_models import (
    BankPracticalInputs,
    CyclicalOperatingState,
    EquityCashFlowState,
    captive_finance_owner_cash_flow,
    mixed_utility_fcfe,
    practical_bank_residual_income_range,
    practical_cyclical_fcff_range,
    practical_fcff_scenarios,
    practical_equity_cash_flow_range,
    practical_fcff_one_way_sensitivities,
    practical_reit_range,
    research_profitability_sensitivity,
)
from .batch_01_recovery_inputs import (
    companyfacts_annual_rows,
    structural_fact,
    ttm_from_structural,
)
from .bridge_policy import BridgeRange, BridgeResolution, assess_bridge_materiality
from .practical_policy import (
    BoundedAssumption,
    HardSafetyInput,
    InputRange,
    PracticalOutcome,
    SourceTrace,
    ValueRange,
    decide_practical_outcome,
)
from .reliability import assess_reliability, relative_movement


PRACTICAL_POLICY_VERSION = "BATCH-01-PRACTICAL-1.1"
OPERATING_TICKERS = frozenset({"AAPL", "MSFT", "CRM", "ANET"})
BANK_TICKERS = frozenset({"JPM", "BAC"})


def _rows(
    companyfacts: Mapping[str, Any],
    *,
    concept: str,
    unit: str,
    namespace: str = "us-gaap",
) -> list[dict[str, Any]]:
    return list(
        companyfacts.get("facts", {})
        .get(namespace, {})
        .get(concept, {})
        .get("units", {})
        .get(unit, [])
    )


def _exact(
    companyfacts: Mapping[str, Any],
    *,
    concept: str,
    unit: str,
    accession: str,
    period_end: str,
    period_start: str | None = None,
    namespace: str = "us-gaap",
) -> float:
    matches = []
    for row in _rows(
        companyfacts, concept=concept, unit=unit, namespace=namespace
    ):
        if (
            row.get("accn") == accession
            and row.get("end") == period_end
            and (period_start is None or row.get("start") == period_start)
            and row.get("filed", "") <= "2026-08-14"
            and row.get("form") in {"10-K", "10-K/A", "10-Q", "10-Q/A"}
            and isinstance(row.get("val"), (int, float))
            and not isinstance(row.get("val"), bool)
        ):
            matches.append(float(row["val"]))
    values = set(matches)
    if len(values) != 1:
        raise ValueError(
            f"{concept} requires one exact point-in-time value for {period_end}"
        )
    return values.pop()


def _annual_series(
    companyfacts: Mapping[str, Any],
    *,
    concept: str,
    unit: str = "USD",
) -> tuple[list[float], list[tuple[str, str]]]:
    selected: dict[str, dict[str, Any]] = {}
    for row in _rows(companyfacts, concept=concept, unit=unit):
        start = row.get("start")
        end = row.get("end")
        if (
            not isinstance(start, str)
            or not isinstance(end, str)
            or row.get("fp") != "FY"
            or row.get("form") not in {"10-K", "10-K/A"}
            or row.get("filed", "") > "2026-08-14"
            or not isinstance(row.get("val"), (int, float))
            or isinstance(row.get("val"), bool)
        ):
            continue
        duration = (date.fromisoformat(end) - date.fromisoformat(start)).days
        if not 300 <= duration <= 380:
            continue
        prior = selected.get(end)
        if prior is None or (row["filed"], row["accn"]) > (
            prior["filed"],
            prior["accn"],
        ):
            selected[end] = row
    ordered = [selected[end] for end in sorted(selected, reverse=True)]
    return (
        [float(row["val"]) for row in ordered],
        [(row["accn"], row["end"]) for row in ordered],
    )


def _trace(
    accession: str,
    period_end: str,
    *,
    unit: str,
    estimated: bool,
) -> SourceTrace:
    return SourceTrace(
        source_kind="filing_evidence",
        accession=accession,
        policy_reference=None,
        period_end=period_end,
        unit=unit,
        reported_vs_estimated="estimated" if estimated else "reported",
    )


def _policy_trace(reference: str, *, unit: str) -> SourceTrace:
    return SourceTrace(
        source_kind="governed_policy",
        accession=None,
        policy_reference=reference,
        period_end="2026-08-14",
        unit=unit,
        reported_vs_estimated="estimated",
    )


def _outcome_dict(outcome: PracticalOutcome) -> dict[str, Any]:
    return asdict(outcome)


def _accounting_range(diagnostic: Mapping[str, Any], base: float) -> tuple[float, float, float]:
    bridge = (
        diagnostic.get("financials", {})
        .get("balance_sheet", {})
        .get("bridge_uncertainty", {})
        .get("intrinsic_value_range")
    )
    if isinstance(bridge, Mapping) and all(
        isinstance(bridge.get(key), (int, float))
        for key in ("low", "midpoint", "high")
    ):
        return float(bridge["low"]), float(bridge["midpoint"]), float(bridge["high"])
    return base, base, base


def _operating_result(
    *,
    ticker: str,
    diagnostic: dict[str, Any],
    companyfacts: Mapping[str, Any],
) -> tuple[dict[str, Any], PracticalOutcome]:
    financials = diagnostic["financials"]
    current_revenue = float(financials["ttm"]["values"]["revenue"])
    current_capex = float(financials["ttm"]["values"]["capital_expenditures"])
    if current_revenue <= 0 or current_capex <= 0:
        raise ValueError("current revenue and capex must be positive")
    historical_capex_ratios = [
        float(row["values"]["capital_expenditures"])
        / float(row["values"]["revenue"])
        for row in financials["annual"]
        if isinstance(row["values"].get("capital_expenditures"), (int, float))
        and isinstance(row["values"].get("revenue"), (int, float))
        and row["values"]["capital_expenditures"] > 0
        and row["values"]["revenue"] > 0
    ]
    if len(historical_capex_ratios) < 3:
        raise ValueError("at least three annual capex/revenue observations are required")
    current_capex_ratio = current_capex / current_revenue
    historical_capex_ratio = float(median(historical_capex_ratios[-5:]))
    base_capital_multiplier = min(
        1.25,
        max(0.50, historical_capex_ratio / current_capex_ratio),
    )
    capital_multipliers = {
        "bear": max(0.35, base_capital_multiplier * 0.75),
        "base": base_capital_multiplier,
        "bull": min(1.25, base_capital_multiplier * 1.10),
    }
    scenarios = practical_fcff_scenarios(
        assumptions=diagnostic["forecast_assumptions"],
        discount_rate=diagnostic["discount_rate"],
        financials=diagnostic["financials"],
        capital_efficiency_multipliers=capital_multipliers,
    )
    for row in scenarios.values():
        row["fcff_dcf"]["publication_state"] = "review_required"
        warning = "Practical bounded-uncertainty scenario; reliability capped at Low."
        if warning not in row["fcff_dcf"].setdefault("warnings", []):
            row["fcff_dcf"]["warnings"].append(warning)
    bridge_assessment = diagnostic["financials"]["balance_sheet"].get(
        "bridge_uncertainty", {}
    )
    bridge_range = bridge_assessment.get("intrinsic_value_range")
    if isinstance(bridge_range, Mapping):
        bridge_midpoint = float(bridge_range["midpoint"])
        for scenario_name, bridge_key in (("bear", "low"), ("bull", "high")):
            model = scenarios[scenario_name]["fcff_dcf"]
            delta = float(bridge_range[bridge_key]) - bridge_midpoint
            model["intrinsic_value_per_share"] += delta
            if isinstance(model.get("equity_value"), (int, float)):
                shares = diagnostic["financials"]["balance_sheet"][
                    "fully_diluted_shares_proxy"
                ]
                model["equity_value"] += delta * shares
            model.setdefault("detail", {})[
                "practical_bridge_delta_per_share"
            ] = delta
    crm_share_range = None
    if ticker == "CRM":
        strict_shares = float(
            diagnostic["financials"]["balance_sheet"][
                "fully_diluted_shares_proxy"
            ]
        )
        reported_diluted = _exact(
            companyfacts,
            concept="WeightedAverageNumberOfDilutedSharesOutstanding",
            unit="shares",
            accession="0001108524-26-000127",
            period_start="2026-02-01",
            period_end="2026-04-30",
        )
        future_diluted = reported_diluted * 1.05
        scenario_shares = {
            "bear": future_diluted,
            "base": reported_diluted,
            "bull": strict_shares,
        }
        for name, shares in scenario_shares.items():
            model = scenarios[name]["fcff_dcf"]
            model["intrinsic_value_per_share"] = model["equity_value"] / shares
            model.setdefault("detail", {})["shares_proxy"] = shares
            model["detail"]["practical_diluted_shares"] = shares
        crm_share_range = InputRange(
            strict_shares,
            reported_diluted,
            future_diluted,
        )
    values = {
        name: row["fcff_dcf"]["intrinsic_value_per_share"]
        for name, row in scenarios.items()
    }
    value_range = ValueRange(values["bear"], values["base"], values["bull"])
    resolution = BridgeResolution.from_dict(
        diagnostic["financials"]["balance_sheet"]["bridge_precheck"]
    )
    if crm_share_range is not None:
        resolution = replace(
            resolution,
            fully_diluted_shares=crm_share_range.base,
        )
    practical_bridge_assessment = assess_bridge_materiality(
        resolution,
        enterprise_value=scenarios["base"]["fcff_dcf"]["enterprise_value"],
    )
    controlling = diagnostic["financials"]["ttm"]["controlling_filing"]
    accession = controlling["accession"]
    period = diagnostic["financial_period_end"]
    rd_values, rd_sources = _annual_series(
        companyfacts,
        concept="ResearchAndDevelopmentExpense",
    )
    available_lives = tuple(life for life in (3, 5, 7) if len(rd_values) >= life + 1)
    if len(available_lives) < 2:
        raise ValueError(f"{ticker} lacks enough annual R&D history for sensitivity")
    latest_annual_ebit, _ = _annual_series(
        companyfacts,
        concept="OperatingIncomeLoss",
    )
    research = research_profitability_sensitivity(
        rd_history_newest_first=rd_values,
        reported_ebit=latest_annual_ebit[0],
        reported_operating_capital=diagnostic["financials"]["balance_sheet"][
            "values"
        ]["total_assets"],
        reported_fcff=diagnostic["financials"]["ttm"]["values"]["reported_fcff"],
        lives=available_lives,
    )
    accounting_impact = float(
        practical_bridge_assessment.accounting_impact_ratio or 0.0
    )
    scenario_impact = relative_movement(
        low=value_range.low,
        base=value_range.base,
        high=value_range.high,
    )
    sales_to_capital = float(diagnostic["forecast_assumptions"]["sales_to_capital"])
    assumptions_list = [
        BoundedAssumption(
            name="consolidated operating model",
            value_range=InputRange(
                diagnostic["forecast_assumptions"]["starting_revenue"],
                diagnostic["forecast_assumptions"]["starting_revenue"],
                diagnostic["forecast_assumptions"]["starting_revenue"],
            ),
            sources=(_trace(accession, period, unit="USD", estimated=False),),
            fallback_level="consolidated_companyfacts",
            basis="Current consolidated TTM revenue and operating economics.",
            accounting_impact_ratio=accounting_impact,
            scenario_impact_ratio=scenario_impact,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="R&D capitalization life",
            value_range=InputRange(
                float(min(available_lives)),
                float(median(available_lives)),
                float(max(available_lives)),
            ),
            sources=tuple(
                _trace(accn, end, unit="USD", estimated=False)
                for accn, end in rd_sources[: max(available_lives) + 1]
            )
            + (_policy_trace(f"{PRACTICAL_POLICY_VERSION}:rd-life", unit="years"),),
            fallback_level="governed_sensitivity",
            basis=research["basis"],
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=0.0,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="capital intensity and cash conversion",
            value_range=InputRange(
                sales_to_capital * capital_multipliers["bear"],
                sales_to_capital * capital_multipliers["base"],
                sales_to_capital * capital_multipliers["bull"],
            ),
            sources=(
                _trace(accession, period, unit="USD", estimated=False),
                _policy_trace(
                    f"{PRACTICAL_POLICY_VERSION}:capital-intensity",
                    unit="ratio",
                ),
            ),
            fallback_level="coupled_bear_base_bull",
            basis=(
                f"Current capex/revenue is {current_capex_ratio:.6f}; the recent "
                f"annual median is {historical_capex_ratio:.6f}. Lower "
                "sales-to-capital in the bear case represents higher capex and "
                "weaker cash conversion without unsupported extra revenue."
            ),
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=scenario_impact,
            material_provisional=True,
        ),
    ]
    if crm_share_range is not None:
        assumptions_list.append(
            BoundedAssumption(
                name="SBC and diluted-share denominator",
                value_range=crm_share_range,
                sources=(
                    _trace(
                        "0001108524-26-000127",
                        "2026-04-30",
                        unit="shares",
                        estimated=False,
                    ),
                    _policy_trace(
                        f"{PRACTICAL_POLICY_VERSION}:future-dilution",
                        unit="shares",
                    ),
                ),
                fallback_level="reported_and_governed_dilution_range",
                basis=(
                    "Current cover-plus-incremental shares, reported diluted "
                    "weighted-average shares, and a 5% governed future-dilution "
                    "stress. SBC remains an operating expense and is not subtracted again."
                ),
                accounting_impact_ratio=relative_movement(
                    low=crm_share_range.low,
                    base=crm_share_range.base,
                    high=crm_share_range.high,
                ),
                scenario_impact_ratio=scenario_impact,
                material_provisional=True,
            )
        )
    assumptions = tuple(assumptions_list)
    reasons = ["CONSOLIDATED_MODEL_FALLBACK", "RD_LIFE_SENSITIVITY"]
    if ticker in {"MSFT", "CRM", "ANET"}:
        reasons.append("CAPEX_CASH_CONVERSION_SENSITIVITY")
    reasons.append("SPECIALIST_MODEL_UNCERTAINTY")
    outcome = decide_practical_outcome(
        value_range=value_range,
        model_version="PRACTICAL-CONSOLIDATED-FCFF-1.0",
        model_selection_reason=(
            "Source-linked consolidated FCFF is economically suitable; missing "
            "advanced detail is represented by coupled finite scenarios."
        ),
        assumptions=assumptions,
        reason_codes=reasons,
        safety=HardSafetyInput(),
        reliability="Low",
    )
    result = deepcopy(diagnostic)
    result["forecast_assumptions"]["sales_to_capital"] = scenarios["base"][
        "assumptions"
    ]["sales_to_capital"]
    result["forecast_assumptions"]["initial_marginal_roic"] = scenarios["base"][
        "fcff_dcf"
    ]["detail"]["initial_marginal_roic"]
    result["models"]["fcff_dcf"] = scenarios["base"]["fcff_dcf"]
    result["scenarios"] = {
        name: {"fcff_dcf": row["fcff_dcf"]} for name, row in scenarios.items()
    }
    result["scenario_range"] = {
        **value_range.as_dict(),
        "label": "coupled practical bear/base/bull range",
    }
    result["sensitivities"] = practical_fcff_one_way_sensitivities(
        assumptions=diagnostic["forecast_assumptions"],
        discount_rate=diagnostic["discount_rate"],
        financials=diagnostic["financials"],
        base_capital_efficiency_multiplier=capital_multipliers["base"],
        share_range=(
            (
                crm_share_range.low,
                crm_share_range.base,
                crm_share_range.high,
            )
            if crm_share_range is not None
            else None
        ),
    )
    result["review"]["publication_state"] = "review_required"
    result["review"]["errors"] = []
    result["review"]["warnings"] = list(
        dict.fromkeys(
            [
                *result["review"].get("warnings", []),
                "Practical consolidated model uses material bounded assumptions and is capped at Low.",
            ]
        )
    )
    serialized_assessment = practical_bridge_assessment.as_dict()
    serialized_assessment.pop("accounting_impact_ratio")
    serialized_assessment.pop("reliability_cap")
    result_balance = result["financials"]["balance_sheet"]
    result_balance["bridge_uncertainty"] = serialized_assessment
    result_balance["bridge_usable"] = practical_bridge_assessment.usable
    result_balance["bridge_decision"] = practical_bridge_assessment.decision
    accounting_low, accounting_base, accounting_high = _accounting_range(
        result, value_range.base
    )
    result["reliability"] = assess_reliability(
        accounting_low=accounting_low,
        accounting_base=accounting_base,
        accounting_high=accounting_high,
        scenario_low=value_range.low,
        scenario_base=value_range.base,
        scenario_high=value_range.high,
        model_cap="Low",
        source_cap="Low" if accounting_impact > 0.20 else "High",
        reasons=tuple(reasons),
    ).as_dict()
    result["practical_policy"] = {
        "version": PRACTICAL_POLICY_VERSION,
        "outcome": _outcome_dict(outcome),
        "scenario_inputs": {
            name: row["assumptions"] for name, row in scenarios.items()
        },
        "research_sensitivity": research,
    }
    return result, outcome


def _bank_inputs(
    *,
    ticker: str,
    companyfacts: Mapping[str, Any],
) -> tuple[BankPracticalInputs, dict[str, Any]]:
    if ticker == "JPM":
        accession = "0001628280-26-054343"
        begin = "2025-12-31"
        end = "2026-06-30"
        begin_total = _exact(companyfacts, concept="StockholdersEquity", unit="USD", accession=accession, period_end=begin)
        end_total = _exact(companyfacts, concept="StockholdersEquity", unit="USD", accession=accession, period_end=end)
        begin_pref = _exact(companyfacts, concept="PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount", unit="USD", accession=accession, period_end=begin)
        end_pref = _exact(companyfacts, concept="PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount", unit="USD", accession=accession, period_end=end)
        issued = _exact(companyfacts, concept="CommonStockSharesIssued", unit="shares", accession=accession, period_end=end)
        treasury = _exact(companyfacts, concept="TreasuryStockCommonShares", unit="shares", accession=accession, period_end=end)
        shares = issued - treasury
        ttm_income = (
            _exact(companyfacts, concept="NetIncomeLossAvailableToCommonStockholdersBasic", unit="USD", accession="0001628280-26-008131", period_start="2025-01-01", period_end="2025-12-31")
            + _exact(companyfacts, concept="NetIncomeLossAvailableToCommonStockholdersBasic", unit="USD", accession=accession, period_start="2026-01-01", period_end=end)
            - _exact(companyfacts, concept="NetIncomeLossAvailableToCommonStockholdersBasic", unit="USD", accession=accession, period_start="2025-01-01", period_end="2025-06-30")
        )
        inputs = BankPracticalInputs(begin_total, end_total, begin_pref, begin_pref, end_pref, end_pref, ttm_income, shares, 0.095, 0.03, 5, 0.12)
        return inputs, {"accession": accession, "period_end": end, "shares": shares, "ttm_common_net_income": ttm_income}
    if ticker == "BAC":
        accession = "0000070858-26-000394"
        begin = "2025-12-31"
        end = "2026-06-30"
        begin_total = _exact(companyfacts, concept="StockholdersEquity", unit="USD", accession=accession, period_end=begin)
        end_total = _exact(companyfacts, concept="StockholdersEquity", unit="USD", accession=accession, period_end=end)
        annual_pref = _exact(companyfacts, concept="PreferredStockIncludingAdditionalPaidInCapital", unit="USD", accession="0000070858-26-000157", period_end=begin)
        shares = _exact(companyfacts, concept="CommonStockSharesOutstanding", unit="shares", accession=accession, period_end=end)
        ttm_income = (
            _exact(companyfacts, concept="NetIncomeLossAvailableToCommonStockholdersBasic", unit="USD", accession="0000070858-26-000157", period_start="2025-01-01", period_end="2025-12-31")
            + _exact(companyfacts, concept="NetIncomeLossAvailableToCommonStockholdersBasic", unit="USD", accession=accession, period_start="2026-01-01", period_end=end)
            - _exact(companyfacts, concept="NetIncomeLossAvailableToCommonStockholdersBasic", unit="USD", accession=accession, period_start="2025-01-01", period_end="2025-06-30")
        )
        inputs = BankPracticalInputs(begin_total, end_total, annual_pref, annual_pref, annual_pref * 0.90, annual_pref * 1.10, ttm_income, shares, 0.105, 0.03, 5, 0.115)
        return inputs, {"accession": accession, "period_end": end, "shares": shares, "ttm_common_net_income": ttm_income, "annual_preferred": annual_pref}
    raise ValueError("unsupported practical bank ticker")


def _bank_result(
    *,
    ticker: str,
    diagnostic: dict[str, Any],
    companyfacts: Mapping[str, Any],
) -> tuple[dict[str, Any], PracticalOutcome]:
    inputs, provenance = _bank_inputs(ticker=ticker, companyfacts=companyfacts)
    governed = diagnostic["public_assumptions"]
    inputs = replace(
        inputs,
        cost_of_equity=float(governed["cost_of_equity"]),
        terminal_growth=float(governed["terminal_growth"]),
        terminal_roe=float(governed["terminal_roe"]),
    )
    value_range, scenarios = practical_bank_residual_income_range(inputs)
    accession = provenance["accession"]
    period = provenance["period_end"]
    assumptions = (
        BoundedAssumption(
            name="preferred equity and common book",
            value_range=InputRange(
                inputs.ending_preferred_low,
                (inputs.ending_preferred_low + inputs.ending_preferred_high) / 2,
                inputs.ending_preferred_high,
            ),
            sources=(
                _trace(
                    "0000070858-26-000157" if ticker == "BAC" else accession,
                    "2025-12-31" if ticker == "BAC" else period,
                    unit="USD",
                    estimated=False,
                ),
                *(
                    (
                        _policy_trace(
                            f"{PRACTICAL_POLICY_VERSION}:annual-preferred-carry",
                            unit="USD",
                        ),
                    )
                    if ticker == "BAC"
                    else ()
                ),
            ),
            fallback_level="current_or_carried_preferred_equity",
            basis="Common equity is total equity less separately ranged preferred equity.",
            accounting_impact_ratio=relative_movement(low=value_range.low, base=value_range.base, high=value_range.high),
            scenario_impact_ratio=relative_movement(low=value_range.low, base=value_range.base, high=value_range.high),
            material_provisional=True,
        ),
        BoundedAssumption(
            name="regulatory capital constrained payout",
            value_range=InputRange(0.20, 0.30, 0.40),
            sources=(
                _trace(accession, period, unit="USD", estimated=False),
                _policy_trace(
                    f"{PRACTICAL_POLICY_VERSION}:bank-capital-sensitivity",
                    unit="ratio",
                ),
            ),
            fallback_level="provisional_bank_capital_range",
            basis="Missing current CET1/RWA refinement is represented by a conservative payout range.",
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=relative_movement(low=value_range.low, base=value_range.base, high=value_range.high),
            material_provisional=True,
        ),
    )
    reasons = ("PROVISIONAL_BANK_CAPITAL_RANGE", "SPECIALIST_MODEL_UNCERTAINTY")
    outcome = decide_practical_outcome(
        value_range=value_range,
        model_version="PRACTICAL-BANK-RI-1.0",
        model_selection_reason="Deposits are operating funding; common-equity residual income is the suitable practical model.",
        assumptions=assumptions,
        reason_codes=reasons,
        safety=HardSafetyInput(),
        reliability="Low",
    )
    result = deepcopy(diagnostic)
    result["financial_period_end"] = period
    result["models"] = {
        "residual_income": {
            "model": "residual_income",
            "output_type": "intrinsic_value_per_share",
            "currency": "USD",
            "intrinsic_value_per_share": value_range.base,
            "publication_state": "review_required",
            "errors": [],
            "warnings": ["Provisional common-equity and regulatory-capital range; reliability capped at Low."],
        }
    }
    result["scenarios"] = {
        name: {
            "residual_income": {
                "intrinsic_value_per_share": value,
                "publication_state": "review_required",
            }
        }
        for name, value in (("bear", value_range.low), ("base", value_range.base), ("bull", value_range.high))
    }
    result["scenario_range"] = {**value_range.as_dict(), "label": "provisional bank-capital range"}
    result["public_assumptions"] = {
        "cost_of_equity": inputs.cost_of_equity,
        "terminal_growth": inputs.terminal_growth,
        "terminal_roe": inputs.terminal_roe,
        "ttm_common_net_income": inputs.ttm_common_net_income,
        "ending_common_shares": inputs.ending_common_shares,
    }
    result["input_provenance"] = provenance
    result["review"]["publication_state"] = "review_required"
    result["review"]["errors"] = []
    result["review"]["warnings"] = result["models"]["residual_income"]["warnings"]
    result["reliability"] = assess_reliability(
        accounting_low=value_range.base,
        accounting_base=value_range.base,
        accounting_high=value_range.base,
        scenario_low=value_range.low,
        scenario_base=value_range.base,
        scenario_high=value_range.high,
        model_cap="Low",
        source_cap="Low",
        reasons=reasons,
    ).as_dict()
    result["practical_policy"] = {"version": PRACTICAL_POLICY_VERSION, "outcome": _outcome_dict(outcome), "scenario_inputs": scenarios, "source_trace": provenance}
    return result, outcome


def _reit_result(
    *,
    diagnostic: dict[str, Any],
    companyfacts: Mapping[str, Any],
) -> tuple[dict[str, Any], PracticalOutcome]:
    annual = "0000726728-26-000011"
    current = "0000726728-26-000048"
    def ttm(concept: str) -> float:
        return (
            _exact(companyfacts, concept=concept, unit="USD", accession=annual, period_start="2025-01-01", period_end="2025-12-31")
            + _exact(companyfacts, concept=concept, unit="USD", accession=current, period_start="2026-01-01", period_end="2026-06-30")
            - _exact(companyfacts, concept=concept, unit="USD", accession=current, period_start="2025-01-01", period_end="2025-06-30")
        )
    ffo = (
        ttm("NetIncomeLossAvailableToCommonStockholdersBasic")
        + ttm("DepreciationDepletionAndAmortization")
        - ttm("GainLossOnSaleOfProperties")
    )
    straight_line = _exact(companyfacts, concept="StraightLineRent", unit="USD", accession=current, period_start="2026-01-01", period_end="2026-06-30") * 2
    maintenance = ValueRange(130_102_000.0, 523_956_000.0, 531_159_000.0)
    lease_income_annual = _exact(companyfacts, concept="LeaseIncome", unit="USD", accession=annual, period_start="2025-01-01", period_end="2025-12-31")
    lease_income = ttm("LeaseIncome")
    property_cost = _exact(companyfacts, concept="RealEstateInvestmentPropertyAtCost", unit="USD", accession=annual, period_end="2025-12-31")
    historical_rates = []
    for year, income, cost in ((2023, 3_958_150_000.0, 49_586_404_000.0), (2024, 5_043_748_000.0, 58_295_055_000.0), (2025, lease_income_annual, property_cost)):
        historical_rates.append(income / cost)
    cap_rates = ValueRange(min(historical_rates), median(historical_rates), max(historical_rates))
    shares = _exact(companyfacts, concept="WeightedAverageNumberOfDilutedSharesOutstanding", unit="shares", accession=current, period_start="2026-01-01", period_end="2026-06-30")
    cash = _exact(companyfacts, concept="CashAndCashEquivalentsAtCarryingValue", unit="USD", accession=current, period_end="2026-06-30")
    debt = _exact(companyfacts, concept="NotesPayable", unit="USD", accession=current, period_end="2026-06-30")
    nci = (
        _exact(companyfacts, concept="StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", unit="USD", accession=current, period_end="2026-06-30")
        - _exact(companyfacts, concept="StockholdersEquity", unit="USD", accession=current, period_end="2026-06-30")
    )
    preferred_upper = 167_394_000.0
    value_range, scenarios = practical_reit_range(
        ffo=ffo,
        straight_line_rent=straight_line,
        maintenance_capex_range=maintenance,
        diluted_shares=shares,
        annualized_lease_income=lease_income,
        cap_rate_range=cap_rates,
        cash=cash,
        debt=debt,
        preferred_equity=preferred_upper,
        noncontrolling_interests=nci,
    )
    impact = relative_movement(low=value_range.low, base=value_range.base, high=value_range.high)
    assumptions = (
        BoundedAssumption(
            name="annualized straight-line rent adjustment",
            value_range=InputRange(straight_line, straight_line, straight_line),
            sources=(
                _trace(current, "2026-06-30", unit="USD", estimated=False),
                _policy_trace(
                    f"{PRACTICAL_POLICY_VERSION}:annualize-current-h1",
                    unit="USD",
                ),
            ),
            fallback_level="annualized_current_h1_estimate",
            basis="No annual 2025 straight-line-rent fact is available; current H1 2026 is doubled and capped at Low.",
            accounting_impact_ratio=impact,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="recurring maintenance capital",
            value_range=InputRange(maintenance.low, maintenance.base, maintenance.high),
            sources=(_trace(annual, "2025-12-31", unit="USD", estimated=True),),
            fallback_level="reported_schedule_iii_improvement_range",
            basis="Range uses reported real-estate improvement and subsequent-capitalization categories; acquisitions are excluded.",
            accounting_impact_ratio=impact,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="gross lease capitalization diagnostic rate",
            value_range=InputRange(cap_rates.low, cap_rates.base, cap_rates.high),
            sources=(_trace(annual, "2025-12-31", unit="ratio", estimated=True),),
            fallback_level="private_historical_gross_lease_yield_diagnostic",
            basis="Private diagnostic uses the issuer's 2023-2025 reported lease-income-to-gross-property yields; it is not represented as NOI or NAV.",
            accounting_impact_ratio=impact,
            scenario_impact_ratio=0.0,
            material_provisional=True,
        ),
    )
    reasons = ("REPORTED_AFFO_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY")
    outcome = decide_practical_outcome(value_range=value_range, model_version="PRACTICAL-REIT-AFFO-DCF-1.0", model_selection_reason="Source-linked TTM FFO adjusted by straight-line rent and recurring-capital ranges provides a practical equity-REIT cash-flow model; gross-lease capitalization remains diagnostic only.", assumptions=assumptions, reason_codes=reasons, safety=HardSafetyInput(), reliability="Low")
    result = deepcopy(diagnostic)
    result["financial_period_end"] = "2026-06-30"
    result["source_financial_statement"] = {"form": "10-Q", "period_end": "2026-06-30", "filed_date": "2026-08-06", "accession": current, "url": "https://www.sec.gov/Archives/edgar/data/726728/000072672826000048/o-20260630.htm"}
    result["models"] = {"ffo": {"model": "ffo", "output_type": "intrinsic_value_per_share", "currency": "USD", "intrinsic_value_per_share": value_range.base, "publication_state": "review_required", "errors": [], "warnings": ["TTM AFFO uses annualized current-H1 straight-line rent and source-derived recurring-capital ranges; private gross-lease diagnostic is non-primary. Reliability capped at Low."]}}
    result["scenarios"] = {name: {"ffo": {"intrinsic_value_per_share": value, "publication_state": "review_required"}} for name, value in (("bear", value_range.low), ("base", value_range.base), ("bull", value_range.high))}
    result["scenario_range"] = {**value_range.as_dict(), "label": "practical TTM AFFO DCF range"}
    result["public_assumptions"] = {"maintenance_capex_low": maintenance.low, "maintenance_capex_base": maintenance.base, "maintenance_capex_high": maintenance.high, "gross_lease_diagnostic_yield_low": cap_rates.low, "gross_lease_diagnostic_yield_base": cap_rates.base, "gross_lease_diagnostic_yield_high": cap_rates.high}
    result["review"]["publication_state"] = "review_required"; result["review"]["errors"] = []; result["review"]["warnings"] = result["models"]["ffo"]["warnings"]
    result["reliability"] = assess_reliability(accounting_low=value_range.base, accounting_base=value_range.base, accounting_high=value_range.base, scenario_low=value_range.low, scenario_base=value_range.base, scenario_high=value_range.high, model_cap="Low", source_cap="Low", reasons=reasons).as_dict()
    result["input_provenance"] = {"annual_accession": annual, "current_accession": current, "ffo": ffo, "straight_line_rent": straight_line, "shares": shares, "cash": cash, "debt": debt, "nci": nci, "preferred_upper": preferred_upper}
    result["practical_policy"] = {"version": PRACTICAL_POLICY_VERSION, "outcome": _outcome_dict(outcome), "scenario_inputs": scenarios}
    return result, outcome


def _recovery_source_trace(
    accession: str,
    period_end: str,
    *,
    unit: str = "USD",
    estimated: bool = False,
) -> SourceTrace:
    return SourceTrace(
        source_kind="filing_evidence",
        accession=accession,
        policy_reference=None,
        period_end=period_end,
        unit=unit,
        reported_vs_estimated="estimated" if estimated else "reported",
    )


def _nee_recovery_result(
    *, diagnostic: dict[str, Any], recovery: Mapping[str, Any]
) -> tuple[dict[str, Any], PracticalOutcome]:
    annual = recovery["NEE-FY2025"]
    interim = recovery["NEE-Q2"]
    annual_accession = "0000753308-26-000015"
    current_accession = "0000753308-26-000060"

    def annual_value(concept: str, year: int) -> float:
        return structural_fact(
            annual,
            local_name=concept,
            period_start=f"{year}-01-01",
            period_end=f"{year}-12-31",
        )

    def ttm(concept: str) -> float:
        return ttm_from_structural(
            annual=annual,
            interim=interim,
            local_name=concept,
            annual_start="2025-01-01",
            annual_end="2025-12-31",
            current_start="2026-01-01",
            current_end="2026-06-30",
            prior_start="2025-01-01",
            prior_end="2025-06-30",
        )

    concepts = {
        "cfo": "NetCashProvidedByUsedInOperatingActivities",
        "capex": "CapitalExpendituresIndependentPowerInvestmentsAndNuclearFuelPurchases",
        "net_income": "NetIncomeLoss",
        "debt_issued": "ProceedsFromIssuanceOfLongTermDebt",
        "debt_repaid": "RepaymentsOfLongTermDebt",
        "commercial_paper_net": "ProceedsFromRepaymentsOfCommercialPaper",
    }
    current = {name: ttm(concept) for name, concept in concepts.items()}
    history = []
    for year in (2024, 2025):
        row = {name: annual_value(concept, year) for name, concept in concepts.items()}
        reinvestment = row["capex"] + row["net_income"] - row["cfo"]
        row["net_borrowing"] = (
            row["debt_issued"]
            - row["debt_repaid"]
            + row["commercial_paper_net"]
        )
        row["debt_funding_share"] = row["net_borrowing"] / reinvestment
        row["year"] = year
        history.append(row)
    current_reinvestment = current["capex"] + current["net_income"] - current["cfo"]
    current["net_borrowing"] = (
        current["debt_issued"]
        - current["debt_repaid"]
        + current["commercial_paper_net"]
    )
    current["debt_funding_share"] = current["net_borrowing"] / current_reinvestment
    funding = sorted(
        [history[0]["debt_funding_share"], history[1]["debt_funding_share"], current["debt_funding_share"]]
    )
    if not all(0 <= value <= 1 for value in funding):
        raise ValueError("NEE debt funding share must remain within 0% to 100%")
    shares = structural_fact(
        interim,
        local_name="WeightedAverageNumberOfDilutedSharesOutstanding",
        period_start="2026-01-01",
        period_end="2026-06-30",
        unit="xbrli:shares",
    )
    parent_equity = structural_fact(
        interim,
        local_name="StockholdersEquity",
        period_end="2026-06-30",
    )
    total_equity = structural_fact(
        interim,
        local_name="StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        period_end="2026-06-30",
    )
    temporary_equity = structural_fact(
        interim,
        local_name="TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
        period_end="2026-06-30",
    )
    parent_cash_flow_share = parent_equity / (total_equity + temporary_equity)
    if not 0 < parent_cash_flow_share <= 1:
        raise ValueError("NEE parent cash-flow share must be within zero and one")
    cash_flows = [
        mixed_utility_fcfe(
            operating_cash_flow=current["cfo"],
            capital_expenditures=current["capex"],
            net_income=current["net_income"],
            debt_funding_share=share,
            parent_cash_flow_share=parent_cash_flow_share,
        )
        for share in funding
    ]
    if cash_flows[1] <= 0:
        assumptions = (
            BoundedAssumption(
                name="total interest-bearing funding share of consolidated reinvestment",
                value_range=InputRange(funding[0], funding[1], funding[2]),
                sources=(
                    _recovery_source_trace(
                        annual_accession,
                        "2025-12-31",
                        unit="ratio",
                        estimated=True,
                    ),
                    _recovery_source_trace(
                        current_accession,
                        "2026-06-30",
                        unit="ratio",
                        estimated=True,
                    ),
                ),
                fallback_level="direct_q2_mixed_utility_fcfe",
                basis="Long-term debt and net commercial-paper borrowing are both included. The resulting bear and base parent FCFE are nonpositive, so the fallback cannot publish.",
                accounting_impact_ratio=0.0,
                scenario_impact_ratio=0.0,
                material_provisional=True,
            ),
        )
        reasons = (
            "CONSOLIDATED_MIXED_UTILITY_FALLBACK",
            "CAPEX_CASH_CONVERSION_SENSITIVITY",
            "SPECIALIST_MODEL_UNCERTAINTY",
        )
        outcome = decide_practical_outcome(
            value_range=None,
            model_version="PRACTICAL-MIXED-UTILITY-FCFE-1.1",
            model_selection_reason="Direct Q2 consolidated FCFE remains economically unsuitable because complete interest-bearing funding produces nonpositive bear and base common cash flow.",
            assumptions=assumptions,
            reason_codes=reasons,
            safety=HardSafetyInput(),
        )
        result = deepcopy(diagnostic)
        result["financial_period_end"] = "2026-06-30"
        result["source_financial_statement"] = {
            "form": "10-Q",
            "period_end": "2026-06-30",
            "filed_date": "2026-07-24",
            "accession": current_accession,
            "url": "https://www.sec.gov/Archives/edgar/data/753308/000075330826000060/nee-20260630.htm",
        }
        result["model_policy"] = {
            "primary": "fcfe_dcf",
            "supporting": [],
            "blend_models": False,
            "reason": "Provisional consolidated mixed-utility FCFE failed the positive-value gate.",
        }
        result["models"] = {
            "fcfe_dcf": {
                "model": "fcfe_dcf",
                "output_type": "intrinsic_value_per_share",
                "currency": "USD",
                "intrinsic_value_per_share": None,
                "publication_state": "withheld",
                "errors": ["Complete interest-bearing funding produces nonpositive bear and base common FCFE."],
                "warnings": [],
            }
        }
        result["scenarios"] = {
            name: {
                "fcfe_dcf": {
                    "model": "fcfe_dcf",
                    "intrinsic_value_per_share": None,
                    "publication_state": "withheld",
                }
            }
            for name in ("bear", "base", "bull")
        }
        result["scenario_range"] = {
            "low": None,
            "base": None,
            "high": None,
            "label": "provisional mixed-utility FCFE withheld",
        }
        result["review"]["publication_state"] = "withheld"
        result["review"]["errors"] = [
            "Complete interest-bearing funding produces nonpositive bear and base common FCFE."
        ]
        result["review"]["warnings"] = []
        result["practical_policy"] = {
            "version": PRACTICAL_POLICY_VERSION,
            "outcome": _outcome_dict(outcome),
            "recovery_diagnostic": {
                "annual_accession": annual_accession,
                "current_accession": current_accession,
                "ttm": current,
                "funding_history": history,
                "funding_range": {
                    "low": funding[0],
                    "base": funding[1],
                    "high": funding[2],
                },
                "parent_cash_flow_share": parent_cash_flow_share,
                "candidate_cash_flows": cash_flows,
            },
        }
        return result, outcome
    states = {
        "bear": EquityCashFlowState(cash_flows[0], 0.01, 0.01, 0.095),
        "base": EquityCashFlowState(cash_flows[1], 0.03, 0.02, 0.085),
        "bull": EquityCashFlowState(cash_flows[2], 0.04, 0.025, 0.078),
    }
    value_range, scenarios = practical_equity_cash_flow_range(
        states=states,
        diluted_shares=shares,
    )
    impact = relative_movement(
        low=value_range.low, base=value_range.base, high=value_range.high
    )
    assumptions = (
        BoundedAssumption(
            name="sustainable debt funding share of consolidated reinvestment",
            value_range=InputRange(funding[0], funding[1], funding[2]),
            sources=(
                _recovery_source_trace(annual_accession, "2025-12-31", unit="ratio", estimated=True),
                _recovery_source_trace(current_accession, "2026-06-30", unit="ratio", estimated=True),
            ),
            fallback_level="direct_q2_mixed_utility_fcfe",
            basis="Range is the ordered 2024, 2025, and TTM debt-funded share of filing-derived reinvestment; every endpoint remains between zero and one.",
            accounting_impact_ratio=impact,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="parent common-equity share of consolidated cash flow",
            value_range=InputRange(
                parent_cash_flow_share,
                parent_cash_flow_share,
                parent_cash_flow_share,
            ),
            sources=(
                _recovery_source_trace(
                    current_accession,
                    "2026-06-30",
                    unit="ratio",
                    estimated=True,
                ),
            ),
            fallback_level="reported_parent_nci_equity_allocation",
            basis="Consolidated equity cash flow is allocated to NEE common using reported parent equity divided by total permanent plus temporary equity, preventing the NCI claim from being valued as common equity.",
            accounting_impact_ratio=impact,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="mixed-utility FCFE growth and cost of equity",
            value_range=InputRange(0.078, 0.085, 0.095),
            sources=(
                _policy_trace(f"{PRACTICAL_POLICY_VERSION}:mixed-utility-fcfe-risk", unit="ratio"),
            ),
            fallback_level="governed_mixed_utility_sensitivity",
            basis="Coupled growth/risk states retain a minimum 2.5 percentage-point cost-of-equity spread over terminal growth.",
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
    )
    reasons = (
        "CONSOLIDATED_MIXED_UTILITY_FALLBACK",
        "CAPEX_CASH_CONVERSION_SENSITIVITY",
        "SPECIALIST_MODEL_UNCERTAINTY",
    )
    outcome = decide_practical_outcome(
        value_range=value_range,
        model_version="PRACTICAL-MIXED-UTILITY-FCFE-1.1",
        model_selection_reason="Direct Q2 consolidated cash flow and filing-derived debt funding provide a bounded equity-level mixed-utility fallback without an EV debt bridge.",
        assumptions=assumptions,
        reason_codes=reasons,
        safety=HardSafetyInput(),
        reliability="Low",
    )
    result = deepcopy(diagnostic)
    result["financial_period_end"] = "2026-06-30"
    result["source_financial_statement"] = {
        "form": "10-Q",
        "period_end": "2026-06-30",
        "filed_date": "2026-07-24",
        "accession": current_accession,
        "url": "https://www.sec.gov/Archives/edgar/data/753308/000075330826000060/nee-20260630.htm",
    }
    result["model_policy"] = {
        "primary": "fcfe_dcf",
        "supporting": [],
        "blend_models": False,
        "reason": "Provisional consolidated FCFE for a mixed regulated/development utility; reliability capped at Low.",
    }
    result["models"] = {
        "fcfe_dcf": {
            "model": "fcfe_dcf",
            "output_type": "intrinsic_value_per_share",
            "currency": "USD",
            "intrinsic_value_per_share": value_range.base,
            "publication_state": "review_required",
            "errors": [],
            "warnings": ["Mixed-utility financing, NCI allocation, and capital intensity are bounded through provisional source-linked scenarios; the older DDM remains private diagnostic only. Reliability capped at Low."],
        }
    }
    result["scenarios"] = {
        name: {"fcfe_dcf": {"intrinsic_value_per_share": value, "publication_state": "review_required"}}
        for name, value in (("bear", value_range.low), ("base", value_range.base), ("bull", value_range.high))
    }
    result["scenario_range"] = {**value_range.as_dict(), "label": "provisional mixed-utility FCFE range"}
    result["public_assumptions"] = {
        "debt_funding_share_low": funding[0],
        "debt_funding_share_base": funding[1],
        "debt_funding_share_high": funding[2],
        "cost_of_equity_base": states["base"].cost_of_equity,
        "terminal_growth_base": states["base"].terminal_growth,
    }
    result["review"]["publication_state"] = "review_required"
    result["review"]["errors"] = []
    result["review"]["warnings"] = result["models"]["fcfe_dcf"]["warnings"]
    result["reliability"] = assess_reliability(
        accounting_low=value_range.base,
        accounting_base=value_range.base,
        accounting_high=value_range.base,
        scenario_low=value_range.low,
        scenario_base=value_range.base,
        scenario_high=value_range.high,
        model_cap="Low",
        source_cap="Low",
        reasons=reasons,
    ).as_dict()
    result["input_provenance"] = {
        "annual_accession": annual_accession,
        "current_accession": current_accession,
        "ttm": current,
        "funding_history": history,
        "diluted_shares": shares,
        "parent_equity": parent_equity,
        "total_equity_including_nci": total_equity,
        "temporary_equity": temporary_equity,
        "parent_cash_flow_share": parent_cash_flow_share,
    }
    result["practical_policy"] = {
        "version": PRACTICAL_POLICY_VERSION,
        "outcome": _outcome_dict(outcome),
        "scenario_inputs": scenarios,
        "ddm_diagnostic_not_blended": diagnostic.get("scenario_range"),
    }
    return result, outcome


def _structural_fact_with_member(
    filing: Mapping[str, Any],
    *,
    local_name: str,
    period_end: str,
    member_text: str,
    unit: str = "USD",
) -> float:
    matches = []
    for fact in filing.get("facts", []):
        if (
            fact.get("local_name") == local_name
            and fact.get("period_end") == period_end
            and fact.get("unit") == unit
            and member_text in str(fact.get("dimensions") or [])
            and isinstance(fact.get("value"), (int, float))
            and not isinstance(fact.get("value"), bool)
        ):
            matches.append(float(fact["value"]))
    if len(set(matches)) != 1:
        raise ValueError(f"{local_name} requires one exact member-scoped value")
    return matches[0]


def _dell_recovery_result(
    *, diagnostic: dict[str, Any], recovery: Mapping[str, Any]
) -> tuple[dict[str, Any], PracticalOutcome]:
    annual = recovery["DELL-FY2026"]
    current = recovery["DELL-Q1"]
    annual_accession = "0001571996-26-000008"
    current_accession = "0001571996-26-000030"
    annual_adjusted_fcf = ValueRange(3_097_000_000.0, 5_607_000_000.0, 11_508_000_000.0)
    ttm_adjusted_fcf = 11_508_000_000.0 + 3_165_000_000.0 - 2_232_000_000.0
    annual_assets = (
        structural_fact(annual, local_name="NotesReceivableNet", period_end="2025-01-31")
        + structural_fact(annual, local_name="PropertySubjectToOrAvailableForOperatingLeaseNet", period_end="2025-01-31")
    )
    latest_assets = (
        structural_fact(annual, local_name="NotesReceivableNet", period_end="2026-01-30")
        + structural_fact(annual, local_name="PropertySubjectToOrAvailableForOperatingLeaseNet", period_end="2026-01-30")
    )
    current_assets = (
        structural_fact(current, local_name="NotesReceivableNet", period_end="2026-05-01")
        + structural_fact(current, local_name="PropertySubjectToOrAvailableForOperatingLeaseNet", period_end="2026-05-01")
    )
    annual_structured_debt = _structural_fact_with_member(
        annual,
        local_name="DebtInstrumentCarryingAmount",
        period_end="2026-01-30",
        member_text="StructuredFinancingDebtMember",
    )
    current_structured_debt = _structural_fact_with_member(
        current,
        local_name="DebtInstrumentCarryingAmount",
        period_end="2026-05-01",
        member_text="StructuredFinancingDebtMember",
    )
    annual_growth = latest_assets - annual_assets
    annualized_current_growth = max(0.0, (current_assets - latest_assets) * 4)
    asset_growth = InputRange(
        annualized_current_growth,
        (annualized_current_growth + annual_growth) / 2,
        annual_growth,
    )
    leverage = 7.0
    cash_flows = {
        "bear": captive_finance_owner_cash_flow(
            adjusted_free_cash_flow=annual_adjusted_fcf.low,
            finance_asset_growth=asset_growth.high,
            debt_to_equity=leverage,
        ),
        "base": captive_finance_owner_cash_flow(
            adjusted_free_cash_flow=annual_adjusted_fcf.base,
            finance_asset_growth=asset_growth.base,
            debt_to_equity=leverage,
        ),
        "bull": captive_finance_owner_cash_flow(
            adjusted_free_cash_flow=annual_adjusted_fcf.high,
            finance_asset_growth=asset_growth.low,
            debt_to_equity=leverage,
        ),
    }
    shares = structural_fact(
        current,
        local_name="WeightedAverageNumberOfDilutedSharesOutstanding",
        period_start="2026-01-31",
        period_end="2026-05-01",
        unit="xbrli:shares",
    )
    states = {
        "bear": EquityCashFlowState(cash_flows["bear"], 0.01, 0.01, 0.12),
        "base": EquityCashFlowState(cash_flows["base"], 0.03, 0.02, 0.105),
        "bull": EquityCashFlowState(cash_flows["bull"], 0.04, 0.025, 0.095),
    }
    value_range, scenarios = practical_equity_cash_flow_range(states=states, diluted_shares=shares)
    impact = relative_movement(low=value_range.low, base=value_range.base, high=value_range.high)
    assumptions = (
        BoundedAssumption(
            name="reported adjusted free cash flow",
            value_range=InputRange(annual_adjusted_fcf.low, annual_adjusted_fcf.base, annual_adjusted_fcf.high),
            sources=(_recovery_source_trace(annual_accession, "2026-01-30", estimated=False),),
            fallback_level="reported_adjusted_fcf_history",
            basis="Dell's filing reconciles FY2024-FY2026 adjusted free cash flow to operating cash flow and removes financing-receivable and operating-lease-equipment effects. TTM adjusted FCF is retained as a diagnostic and does not raise the conservative high endpoint above the reported annual maximum.",
            accounting_impact_ratio=impact,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="DFS equity-funded asset growth",
            value_range=InputRange(asset_growth.low, asset_growth.base, asset_growth.high),
            sources=(
                _recovery_source_trace(annual_accession, "2026-01-30", estimated=True),
                _recovery_source_trace(current_accession, "2026-05-01", estimated=True),
                _policy_trace(f"{PRACTICAL_POLICY_VERSION}:dell-dfs-seven-to-one", unit="ratio"),
            ),
            fallback_level="dfs_asset_growth_equity_share",
            basis="Only one-eighth of source-derived DFS-owned-asset growth is charged to common equity under Dell's disclosed 7:1 debt-to-equity approximation.",
            accounting_impact_ratio=impact,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
    )
    reasons = (
        "CONSOLIDATED_MODEL_FALLBACK",
        "CAPEX_CASH_CONVERSION_SENSITIVITY",
        "SPECIALIST_MODEL_UNCERTAINTY",
    )
    outcome = decide_practical_outcome(
        value_range=value_range,
        model_version="PRACTICAL-CAPTIVE-FINANCE-FCFE-1.0",
        model_selection_reason="Dell-reported adjusted free cash flow plus the equity-funded share of DFS asset growth supports an equity-level valuation without subtracting DFS debt twice.",
        assumptions=assumptions,
        reason_codes=reasons,
        safety=HardSafetyInput(),
        reliability="Low",
    )
    result = deepcopy(diagnostic)
    result["financial_period_end"] = "2026-05-01"
    result["source_financial_statement"] = {
        "form": "10-Q", "period_end": "2026-05-01", "filed_date": "2026-06-09",
        "accession": current_accession,
        "url": "https://www.sec.gov/Archives/edgar/data/1571996/000157199626000030/dell-20260501.htm",
    }
    result["model_policy"] = {
        "primary": "fcfe_dcf", "supporting": [], "blend_models": False,
        "reason": "Provisional consolidated FCFE with explicit captive-finance equity funding; reliability capped at Low.",
    }
    result["models"] = {
        "fcfe_dcf": {
            "model": "fcfe_dcf", "output_type": "intrinsic_value_per_share", "currency": "USD",
            "intrinsic_value_per_share": value_range.base, "publication_state": "review_required", "errors": [],
            "warnings": ["DFS asset growth and funding are bounded at the equity level; no cash/debt bridge is applied. Reliability capped at Low."],
        }
    }
    result["scenarios"] = {
        name: {"fcfe_dcf": {"intrinsic_value_per_share": value, "publication_state": "review_required"}}
        for name, value in (("bear", value_range.low), ("base", value_range.base), ("bull", value_range.high))
    }
    result["scenario_range"] = {**value_range.as_dict(), "label": "provisional captive-finance FCFE range"}
    result["public_assumptions"] = {
        "adjusted_fcf_low": annual_adjusted_fcf.low, "adjusted_fcf_base": annual_adjusted_fcf.base,
        "adjusted_fcf_high": annual_adjusted_fcf.high, "dfs_debt_to_equity": leverage,
        "cost_of_equity": states["base"].cost_of_equity,
    }
    result["review"]["publication_state"] = "review_required"; result["review"]["errors"] = []
    result["review"]["warnings"] = result["models"]["fcfe_dcf"]["warnings"]
    result["forecast_quality"] = {
        "policy_version": "US-FORECAST-QUALITY-1.0",
        "status": "review_required",
        "checks": {
            "captive_finance_fcfe_reconciliation": {
                "status": "review_required"
            }
        },
        "errors": [],
        "warnings": result["models"]["fcfe_dcf"]["warnings"],
    }
    result["reliability"] = assess_reliability(
        accounting_low=value_range.base, accounting_base=value_range.base, accounting_high=value_range.base,
        scenario_low=value_range.low, scenario_base=value_range.base, scenario_high=value_range.high,
        model_cap="Low", source_cap="Low", reasons=reasons,
    ).as_dict()
    result["input_provenance"] = {
        "annual_accession": annual_accession, "current_accession": current_accession,
        "adjusted_fcf": annual_adjusted_fcf.as_dict(), "dfs_owned_assets": {
            "2025-01-31": annual_assets, "2026-01-30": latest_assets, "2026-05-01": current_assets,
        }, "asset_growth": asset_growth.as_dict(), "shares": shares,
        "ttm_adjusted_fcf": ttm_adjusted_fcf,
        "dfs_funding_reconciliation": {
            "target_debt": latest_assets * leverage / (1 + leverage),
            "annual_structured_debt": annual_structured_debt,
            "annual_core_debt_allocated_to_dfs": latest_assets * leverage / (1 + leverage) - annual_structured_debt,
            "current_structured_debt": current_structured_debt,
        },
    }
    result["practical_policy"] = {
        "version": PRACTICAL_POLICY_VERSION, "outcome": _outcome_dict(outcome), "scenario_inputs": scenarios,
    }
    return result, outcome


def _wdc_discontinued_fact(
    filing: Mapping[str, Any],
    *,
    local_name: str,
    period_start: str,
    period_end: str,
) -> float:
    matches = []
    for fact in filing.get("facts", []):
        dimensions = fact.get("dimensions") or []
        if (
            fact.get("local_name") == local_name
            and fact.get("period_start") == period_start
            and fact.get("period_end") == period_end
            and fact.get("unit") == "USD"
            and any("Sandisk" in str(member) for _, member in dimensions)
            and isinstance(fact.get("value"), (int, float))
            and not isinstance(fact.get("value"), bool)
        ):
            matches.append(float(fact["value"]))
    if len(set(matches)) != 1:
        raise ValueError(f"{local_name} requires one exact discontinued-Flash fact")
    return matches[0]


def _wdc_recovery_result(
    *, diagnostic: dict[str, Any], recovery: Mapping[str, Any]
) -> tuple[dict[str, Any], PracticalOutcome]:
    filing = recovery["WDC-FY2026"]
    financials = diagnostic["financials"]
    rows = {
        int(row["fiscal_year"]): row
        for row in financials["annual"]
        if int(row["fiscal_year"]) in {2024, 2025, 2026}
    }
    if set(rows) != {2024, 2025, 2026}:
        raise ValueError("WDC requires all three restated continuing-operation years")
    discontinued_da = {
        2024: _wdc_discontinued_fact(
            filing,
            local_name="DepreciationAndAmortizationDiscontinuedOperations",
            period_start="2023-07-01",
            period_end="2024-06-28",
        ),
        2025: _wdc_discontinued_fact(
            filing,
            local_name="DepreciationAndAmortizationDiscontinuedOperations",
            period_start="2024-06-29",
            period_end="2025-06-27",
        ),
    }
    discontinued_capex = {
        2024: _wdc_discontinued_fact(
            filing,
            local_name="PaymentsToAcquirePropertyPlantAndEquipment",
            period_start="2023-07-01",
            period_end="2024-06-28",
        ),
        2025: _wdc_discontinued_fact(
            filing,
            local_name="PaymentsToAcquirePropertyPlantAndEquipment",
            period_start="2024-06-29",
            period_end="2025-06-27",
        ),
    }
    wdc_states = []
    for year in (2024, 2025, 2026):
        values = rows[year]["values"]
        revenue = float(values["revenue"])
        da = float(values["depreciation_amortization"]) - discontinued_da.get(year, 0.0)
        capex = float(values["capital_expenditures"]) - discontinued_capex.get(year, 0.0)
        if min(revenue, da, capex) <= 0:
            raise ValueError("WDC continuing revenue, D&A, and capex must be positive")
        wdc_states.append(
            CyclicalOperatingState(
                issuer="WDC",
                period_end=rows[year]["period_end"],
                revenue=revenue,
                operating_margin=float(values["operating_income"]) / revenue,
                depreciation_ratio=da / revenue,
                capex_ratio=capex / revenue,
            )
        )

    peer = recovery["STX-companyfacts"]
    concepts = {
        "revenue": "RevenueFromContractWithCustomerExcludingAssessedTax",
        "ebit": "OperatingIncomeLoss",
        "da": "DepreciationDepletionAndAmortization",
        "capex": "PaymentsToAcquirePropertyPlantAndEquipment",
    }
    peer_rows = {
        name: {
            row["end"]: row
            for row in companyfacts_annual_rows(peer, concept=concept)
        }
        for name, concept in concepts.items()
    }
    peer_ends = sorted(
        set.intersection(*(set(rows_by_end) for rows_by_end in peer_rows.values()))
    )
    peer_ends = [
        end for end in peer_ends if "2017-01-01" <= end <= "2026-12-31"
    ][-10:]
    if len(peer_ends) != 10:
        raise ValueError("STX must provide ten complete annual paired cycle states")
    stx_states = []
    for end in peer_ends:
        paired_accessions = {
            peer_rows[name][end]["accn"] for name in concepts
        }
        if len(paired_accessions) != 1:
            raise ValueError("STX cycle metrics must share one filing accession")
        revenue = float(peer_rows["revenue"][end]["val"])
        stx_states.append(
            CyclicalOperatingState(
                issuer="STX",
                period_end=end,
                revenue=revenue,
                operating_margin=float(peer_rows["ebit"][end]["val"]) / revenue,
                depreciation_ratio=float(peer_rows["da"][end]["val"]) / revenue,
                capex_ratio=float(peer_rows["capex"][end]["val"]) / revenue,
            )
        )
    current = wdc_states[-1]
    nwc_sources = financials["ttm"]["nwc_sources"]
    operating_nwc_investment = float(nwc_sources["current"]["value"]) - float(
        nwc_sources["prior"]["value"]
    )
    operating_nwc_ratio = operating_nwc_investment / current.revenue
    cash = structural_fact(
        filing,
        local_name="CashAndCashEquivalentsAtCarryingValue",
        period_end="2026-07-03",
    )
    debt = structural_fact(
        filing, local_name="LongTermDebt", period_end="2026-07-03"
    )
    other_claims = InputRange(0.0, 0.0, 0.0)
    cover_shares = structural_fact(
        filing,
        local_name="EntityCommonStockSharesOutstanding",
        period_end="2026-08-07",
        unit="xbrli:shares",
    )
    nonvested_awards = _structural_fact_with_member(
        filing,
        local_name="ShareBasedCompensationArrangementByShareBasedPaymentAwardEquityInstrumentsOtherThanOptionsNonvestedNumber",
        period_end="2026-07-03",
        member_text="RestrictedStockUnitsAndPerformanceShareUnitsMember",
        unit="xbrli:shares",
    )
    annual_diluted_shares = structural_fact(
        filing,
        local_name="WeightedAverageNumberOfDilutedSharesOutstanding",
        period_start="2025-06-28",
        period_end="2026-07-03",
        unit="xbrli:shares",
    )
    annual_incremental_shares = structural_fact(
        filing,
        local_name="IncrementalCommonSharesAttributableToShareBasedPaymentArrangements",
        period_start="2025-06-28",
        period_end="2026-07-03",
        unit="xbrli:shares",
    )
    share_range = InputRange(
        cover_shares + nonvested_awards,
        annual_diluted_shares,
        cover_shares + annual_incremental_shares,
    )
    shares = share_range.base
    normalized_tax = 0.21
    wacc = float(diagnostic["discount_rate"]["wacc"])
    def run_cycle(
        tax_rate: float, share_count: float
    ) -> tuple[ValueRange, dict[str, Any]]:
        return practical_cyclical_fcff_range(
            current_state=current,
            observed_states=(*wdc_states, *stx_states),
            operating_nwc_ratio=operating_nwc_ratio,
            normalized_tax_rate=tax_rate,
            wacc=wacc,
            cash=cash,
            debt=debt,
            other_claims=other_claims,
            diluted_shares=share_count,
        )

    base_cycle_range, cycle = run_cycle(normalized_tax, share_range.base)
    high_tax_range, _ = run_cycle(0.25, share_range.high)
    low_tax_range, _ = run_cycle(0.16, share_range.low)
    value_range = ValueRange(
        high_tax_range.low,
        base_cycle_range.base,
        low_tax_range.high,
    )
    cycle["tax_sensitivity"] = {
        "low_value_at_25_percent_tax": high_tax_range.low,
        "base_value_at_21_percent_tax": base_cycle_range.base,
        "high_value_at_16_percent_tax": low_tax_range.high,
    }
    terminal_state = cycle["terminal_state"]
    epv_fcff = (
        terminal_state["revenue"]
        * terminal_state["operating_margin"]
        * (1 - normalized_tax)
    )
    cycle["epv_diagnostic"] = {
        "no_growth_fcff": epv_fcff,
        "enterprise_value": epv_fcff / wacc,
        "equity_value_per_share": (epv_fcff / wacc + cash - debt) / shares,
        "is_primary": False,
        "is_blended": False,
    }
    impact = relative_movement(
        low=value_range.low, base=value_range.base, high=value_range.high
    )
    assumptions = (
        BoundedAssumption(
            name="issuer-balanced complete storage-cycle states",
            value_range=InputRange(
                value_range.low, value_range.base, value_range.high
            ),
            sources=(
                _recovery_source_trace(
                    "0001628280-26-057139",
                    "2026-07-03",
                    unit="USD/shares",
                    estimated=True,
                ),
                _recovery_source_trace(
                    "0001137789-26-000159",
                    "2026-07-03",
                    unit="USD/shares",
                    estimated=True,
                ),
            ),
            fallback_level="issuer_balanced_storage_cycle",
            basis="WDC FY2024-FY2026 and Seagate FY2017-FY2026 paired states each receive 50% issuer weight; WDC D&A and capex exclude reported discontinued Flash amounts.",
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="post-transaction diluted share denominator",
            value_range=share_range,
            sources=(
                _recovery_source_trace(
                    "0001628280-26-057139",
                    "2026-08-07",
                    unit="shares",
                    estimated=True,
                ),
            ),
            fallback_level="post_transaction_share_range",
            basis="Low-share endpoint adds current nonvested awards to the post-conversion cover count; base uses reported annual diluted shares; high adds the full annual incremental amount as a conservative ceiling.",
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="normalized operating tax rate",
            value_range=InputRange(0.16, normalized_tax, 0.25),
            sources=(
                _recovery_source_trace(
                    "0001628280-26-057139",
                    "2026-07-03",
                    unit="ratio",
                    estimated=True,
                ),
                _policy_trace(
                    f"{PRACTICAL_POLICY_VERSION}:wdc-spin-normalized-tax",
                    unit="ratio",
                ),
            ),
            fallback_level="spin_adjusted_operating_tax",
            basis="The 21% base is the U.S. statutory anchor; 16%-25% brackets the filing reconciliation after excluding the tax-free Sandisk retained-interest gain and separation-specific items.",
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=0.0,
            material_provisional=True,
        ),
    )
    reasons = ("NORMALIZED_CYCLICAL_RANGE", "SPECIALIST_MODEL_UNCERTAINTY")
    outcome = decide_practical_outcome(
        value_range=value_range,
        model_version="PRACTICAL-CYCLICAL-FCFF-1.1",
        model_selection_reason="Issuer-balanced paired WDC/Seagate cycle states normalize the post-spin HDD business with a complete current filing bridge.",
        assumptions=assumptions,
        reason_codes=reasons,
        safety=HardSafetyInput(),
        reliability="Low",
    )
    result = deepcopy(diagnostic)
    result["forecast_assumptions"]["forecast_mode_override"] = "normalized_cycle"
    result["forecast_assumptions"]["forecast_policy_version"] = (
        PRACTICAL_POLICY_VERSION
    )
    result["forecast_assumptions"]["forecast_years"] = 10
    result["forecast_assumptions"]["terminal_growth"] = 0.0
    result["model_policy"] = {
        "primary": "fcff_dcf",
        "supporting": [],
        "blend_models": False,
        "reason": "Provisional issuer-balanced normalized-cycle FCFF; reliability capped at Low.",
    }
    warning = "Post-spin continuing operations are normalized through issuer-balanced WDC/Seagate paired states; reliability capped at Low."
    result["models"] = {
        "fcff_dcf": {
            "model": "fcff_dcf",
            "output_type": "intrinsic_value_per_share",
            "currency": "USD",
            "intrinsic_value_per_share": value_range.base,
            "publication_state": "review_required",
            "errors": [],
            "warnings": [warning],
        }
    }
    result["scenarios"] = {
        name: {
            "fcff_dcf": {
                "model": "fcff_dcf",
                "output_type": "intrinsic_value_per_share",
                "currency": "USD",
                "intrinsic_value_per_share": value,
                "publication_state": "review_required",
                "errors": [],
                "warnings": [warning],
            }
        }
        for name, value in (
            ("bear", value_range.low),
            ("base", value_range.base),
            ("bull", value_range.high),
        )
    }
    result["scenario_range"] = {
        **value_range.as_dict(),
        "label": "issuer-balanced normalized storage-cycle range",
    }
    result["review"]["publication_state"] = "review_required"
    result["review"]["errors"] = []
    result["review"]["warnings"] = [warning]
    result["public_assumptions"] = {
        "cycle_wdc_weight": 0.5,
        "cycle_stx_weight": 0.5,
        "normalized_tax_rate": normalized_tax,
        "operating_nwc_ratio": operating_nwc_ratio,
        "diluted_shares": shares,
        "diluted_shares_low": share_range.low,
        "diluted_shares_high": share_range.high,
        "bridge_claims_basis": "reported total debt; complete filing extraction found zero current investments, preferred/temporary equity, finance-lease debt, and NCI",
    }
    base_ev = value_range.base * shares - cash + debt + other_claims.base
    resolution = BridgeResolution(
        complete=True,
        can_value=True,
        missing_fields=(),
        blocking_fields=(),
        bounded_fields=(),
        cash_and_investments=BridgeRange(cash, cash, cash),
        total_debt=BridgeRange(debt, debt, debt),
        preferred_equity=BridgeRange(0.0, 0.0, 0.0),
        noncontrolling_interests=BridgeRange(
            other_claims.low, other_claims.base, other_claims.high
        ),
        bridge_adjustment=BridgeRange(
            cash - debt - other_claims.high,
            cash - debt - other_claims.base,
            cash - debt - other_claims.low,
        ),
        fully_diluted_shares=shares,
        reason_codes=(
            "NOT_DISCLOSED_COMPLETE_EXTRACTION",
            "REPORTED_AGGREGATE_REPLACEMENT",
        ),
    )
    assessment = assess_bridge_materiality(resolution, enterprise_value=base_ev)
    serialized_assessment = assessment.as_dict()
    serialized_assessment.pop("accounting_impact_ratio")
    serialized_assessment.pop("reliability_cap")
    result_balance = result["financials"]["balance_sheet"]
    result_balance.update(resolution.as_balance_sheet_fields())
    result_balance["bridge_uncertainty"] = serialized_assessment
    result_balance["bridge_usable"] = assessment.usable
    result_balance["bridge_decision"] = assessment.decision
    result["forecast_quality"] = {
        "policy_version": "US-FORECAST-QUALITY-1.0",
        "status": "review_required",
        "checks": {
            "normalized_cycle_evidence": {
                "status": "review_required",
                "wdc_state_count": len(wdc_states),
                "stx_state_count": len(stx_states),
                "issuer_balanced": True,
            }
        },
        "errors": [],
        "warnings": [warning],
    }
    result["reliability"] = assess_reliability(
        accounting_low=assessment.intrinsic_value_range.low,
        accounting_base=assessment.intrinsic_value_range.midpoint,
        accounting_high=assessment.intrinsic_value_range.high,
        scenario_low=value_range.low,
        scenario_base=value_range.base,
        scenario_high=value_range.high,
        model_cap="Low",
        source_cap="Low",
        reasons=reasons,
    ).as_dict()
    result["input_provenance"] = {
        "wdc_accession": "0001628280-26-057139",
        "stx_cutoff": "2026-08-14",
        "discontinued_flash_da": discontinued_da,
        "discontinued_flash_capex": discontinued_capex,
        "share_range": share_range.as_dict(),
        "current_bridge": {
            "cash": cash,
            "total_debt": debt,
            "equity_securities": structural_fact(
                filing,
                local_name="EquitySecuritiesFvNi",
                period_end="2026-07-03",
            ),
            "temporary_equity": structural_fact(
                filing,
                local_name="TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
                period_end="2026-07-03",
            ),
            "operating_lease_liability_not_capitalized": structural_fact(
                filing,
                local_name="OperatingLeaseLiability",
                period_end="2026-07-03",
            ),
        },
        "cycle": cycle,
    }
    result["practical_policy"] = {
        "version": PRACTICAL_POLICY_VERSION,
        "outcome": _outcome_dict(outcome),
        "scenario_inputs": cycle,
    }
    return result, outcome


def build_practical_result(
    *,
    ticker: str,
    diagnostic: dict[str, Any],
    companyfacts: Mapping[str, Any],
    recovery_evidence: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], PracticalOutcome]:
    if ticker in OPERATING_TICKERS:
        return _operating_result(ticker=ticker, diagnostic=diagnostic, companyfacts=companyfacts)
    if ticker in BANK_TICKERS:
        return _bank_result(ticker=ticker, diagnostic=diagnostic, companyfacts=companyfacts)
    if ticker == "O":
        return _reit_result(diagnostic=diagnostic, companyfacts=companyfacts)
    if recovery_evidence is not None and ticker == "NEE":
        return _nee_recovery_result(
            diagnostic=diagnostic,
            recovery=recovery_evidence,
        )
    if recovery_evidence is not None and ticker == "DELL":
        return _dell_recovery_result(
            diagnostic=diagnostic,
            recovery=recovery_evidence,
        )
    if recovery_evidence is not None and ticker == "WDC":
        return _wdc_recovery_result(
            diagnostic=diagnostic,
            recovery=recovery_evidence,
        )
    reason = {
        "WDC": ("NORMALIZED_CYCLICAL_RANGE", HardSafetyInput(claims_bounded=False)),
        "DELL": ("SPECIALIST_MODEL_UNCERTAINTY", HardSafetyInput(claims_bounded=False)),
        "NEE": ("CONSOLIDATED_MIXED_UTILITY_FALLBACK", HardSafetyInput(period_valid=False)),
    }[ticker]
    outcome = decide_practical_outcome(
        value_range=None,
        model_version={"WDC": "PRACTICAL-CYCLICAL-FCFF-1.0", "DELL": "PRACTICAL-CAPTIVE-FINANCE-SOTP-1.0", "NEE": "PRACTICAL-MIXED-UTILITY-FCFE-1.0"}[ticker],
        model_selection_reason={"WDC": "A normalized cyclical FCFF model requires a defensible complete-cycle range.", "DELL": "Captive-finance claims must be separated from industrial operations.", "NEE": "The latest filed quarter must support a mixed-utility or consolidated FCFE range."}[ticker],
        assumptions=(),
        reason_codes=(reason[0],),
        safety=reason[1],
    )
    result = deepcopy(diagnostic)
    result["practical_policy"] = {"version": PRACTICAL_POLICY_VERSION, "outcome": _outcome_dict(outcome)}
    return result, outcome
