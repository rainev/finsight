"""Cutoff-safe, history-backed residual-income models for Batch 38 insurers.

The four issuers in this module are valued on parent/common equity.  The
companyfacts packet supplies the annual and current-period earnings history;
the controlling structural filing supplies the equity, claims, and current
share count.  This module deliberately does not fetch or hash files: the
Batch 38 runner owns packet/structural/event receipts and appends those
artifacts to the private source ledger.
"""
from __future__ import annotations

from datetime import date
from statistics import median
from typing import Any, Iterable

from app.valuation.bank import residual_income_valuation

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_35_history import _equity, _instant, _period_flow, _rows, _share, _source
from .batch_38 import BATCH_38_VALUATION_DATE
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, summarize_history_metric
from .reliability import assess_reliability


BATCH_38_INSURER_VERSION = "BATCH-38-INSURER-HISTORY-1.0"
FORECAST_YEARS = 5
INSURER_TICKERS = ("EG", "PFG", "PRU", "AIZ")
PASS_TICKERS = frozenset()
CONDITIONAL_TICKERS = frozenset(INSURER_TICKERS)
WITHHELD_TICKERS = frozenset()


EARNINGS: dict[str, tuple[str, ...]] = {
    "EG": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
    "PFG": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
    "PRU": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
    "AIZ": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
}


POLICY: dict[str, dict[str, Any]] = {
    "EG": {
        "method": "reinsurance_residual_income_equity_earnings",
        "roe": (.06, .09, .12),
        "payout": (.20, .30, .40),
        "coe": (.115, .10, .09),
        "warning": "Conditional Low reinsurance residual-income baseline. Catastrophe losses, reserve development, retrocession, investment marks, preferred/NCI claims and regulatory capital remain material.",
    },
    "PFG": {
        "method": "retirement_life_insurance_residual_income_equity_earnings",
        "roe": (.06, .09, .12),
        "payout": (.25, .35, .45),
        "coe": (.115, .10, .09),
        "warning": "Conditional Low retirement/life-insurance residual-income baseline. Separate-account economics, market-risk benefits, investment marks, redeemable NCI and regulatory capital remain material.",
    },
    "PRU": {
        "method": "life_insurance_residual_income_equity_earnings",
        "roe": (.05, .08, .11),
        "payout": (.25, .35, .45),
        "coe": (.115, .10, .09),
        "warning": "Conditional Low life-insurance residual-income baseline. Policy reserves, closed-block obligations, market-risk benefits, investment marks, redeemable NCI and regulatory capital remain material.",
    },
    "AIZ": {
        "method": "multiline_insurance_residual_income_equity_earnings",
        "roe": (.08, .11, .14),
        "payout": (.20, .30, .40),
        "coe": (.11, .095, .085),
        "warning": "Conditional Low multiline-insurance residual-income baseline. Catastrophe losses, reserve development, specialty mix, investment marks and regulatory capital remain material.",
    },
}


def _structural_rows(
    structural: dict[str, Any],
    names: Iterable[str],
    *,
    period_start: str | None,
    period_end: str,
    unit: str | None = None,
    dimensions: bool = False,
) -> list[dict[str, Any]]:
    names = tuple(names)
    for name in names:
        rows = [
            row
            for row in structural.get("facts", [])
            if row.get("local_name") == name
            and row.get("period_start") == period_start
            and row.get("period_end") == period_end
            and (dimensions or not row.get("dimensions"))
            and isinstance(row.get("value"), (int, float))
            and not isinstance(row.get("value"), bool)
            and (unit is None or row.get("unit") == unit)
        ]
        if rows:
            return rows
    return []


def _structural_source(structural: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_kind": "structural_xbrl",
        "accession": structural.get("source_accession"),
        "filed": structural.get("filed_date"),
        "form": structural.get("form"),
        "period_start": row.get("period_start"),
        "period_end": row.get("period_end"),
        "concept": row.get("qname"),
        "unit": row.get("unit"),
        "value": float(row["value"]),
        "dimensions": row.get("dimensions"),
        "reported_vs_estimated": "reported",
    }


def _fact(structural: dict[str, Any], names: Iterable[str], *, period_start: str | None, period_end: str, unit: str) -> dict[str, Any]:
    rows = _structural_rows(structural, names, period_start=period_start, period_end=period_end, unit=unit)
    if not rows:
        raise ValueError(f"structural fact {tuple(names)} {period_start}/{period_end} absent")
    return _structural_source(structural, rows[0])


def _period_flow(structural: dict[str, Any], names: Iterable[str], end: str, *, target_days: int | None = None) -> dict[str, Any]:
    candidates: list[tuple[int, dict[str, Any]]] = []
    for name in names:
        for row in structural.get("facts", []):
            if (
                row.get("local_name") != name
                or row.get("period_end") != end
                or row.get("period_start") is None
                or row.get("unit") != "USD"
                or row.get("dimensions")
                or not isinstance(row.get("value"), (int, float))
                or isinstance(row.get("value"), bool)
            ):
                continue
            try:
                days = (date.fromisoformat(end) - date.fromisoformat(row["period_start"])).days
            except (KeyError, TypeError, ValueError):
                continue
            if days >= 45:
                candidates.append((days, row))
        if candidates:
            break
    if not candidates:
        raise ValueError(f"period flow {tuple(names)} ending {end} absent")
    wanted = target_days if target_days is not None else max(days for days, _ in candidates)
    _, row = min(candidates, key=lambda item: (abs(item[0] - wanted), -item[0]))
    return _structural_source(structural, row)


def _annual(facts: dict[str, Any], ticker: str) -> tuple[dict[str, Any], ...]:
    selected: dict[str, tuple[dict[str, Any], str]] = {}
    for concept in EARNINGS[ticker]:
        for row in _rows(facts, concept):
            if row.get("form") not in {"10-K", "10-K/A"} or row.get("filed", "") > BATCH_38_VALUATION_DATE:
                continue
            if not row.get("start") or not row.get("end"):
                continue
            try:
                span = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
            except (KeyError, TypeError, ValueError):
                continue
            if not 300 <= span <= 380:
                continue
            old = selected.get(row["end"])
            if old is None or (row.get("filed", ""), row.get("accn", "")) > (old[0].get("filed", ""), old[0].get("accn", "")):
                selected[row["end"]] = (row, concept)
        if len(selected) >= 5:
            break
    if len(selected) < 5:
        raise ValueError(f"{ticker}: fewer than five exact annual common-earnings periods")
    return tuple(
        {"period_end": end, "value": float(selected[end][0]["val"]), "source": _source(selected[end][0], selected[end][1])}
        for end in sorted(selected)[-5:]
    )


def _share_exact(structural: dict[str, Any], facts: dict[str, Any], period_end: str) -> dict[str, Any]:
    """Use the latest cover-page DEI count in the controlling filing.

    The balance-sheet common-stock tag can be stale, pre-split, or a class
    total.  DEI is the filing's explicit current entity count and may be dated
    a few weeks after the balance-sheet date while still belonging to the same
    controlling filing.
    """
    rows = [
        row
        for row in structural.get("facts", [])
        if row.get("local_name") == "EntityCommonStockSharesOutstanding"
        and row.get("period_start") is None
        and row.get("unit") == "xbrli:shares"
        and not row.get("dimensions")
        and isinstance(row.get("value"), (int, float))
        and period_end <= str(row.get("period_end", "")) <= BATCH_38_VALUATION_DATE
    ]
    if rows:
        return {**_structural_source(structural, max(rows, key=lambda row: row["period_end"])), "source_kind": "structural_dei_current_share_count", "selection": "latest controlling-filing DEI count"}
    rows = [
        row
        for row in structural.get("facts", [])
        if row.get("local_name") == "CommonStockSharesOutstanding"
        and row.get("period_start") is None
        and row.get("unit") == "xbrli:shares"
        and not row.get("dimensions")
        and isinstance(row.get("value"), (int, float))
        and row.get("period_end") == period_end
    ]
    if rows:
        return {**_structural_source(structural, rows[-1]), "source_kind": "structural_common_share_count", "selection": "controlling-period common shares"}
    # Keep the fallback cutoff-safe and source-linked if a parser omitted DEI.
    return {**_share(structural, facts, period_end), "selection": "shared cutoff-safe share selector"}


def _preferred(structural: dict[str, Any], period_end: str) -> tuple[float, str, list[dict[str, Any]]]:
    names = ("PreferredStockLiquidationPreferenceValue", "PreferredStockCarryingValue", "PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount", "PreferredStockValue")
    rows: list[dict[str, Any]] = []
    for name in names:
        rows = _structural_rows(structural, (name,), period_start=None, period_end=period_end, unit="USD")
        if rows:
            row = rows[0]
            if float(row["value"]) > 0:
                return float(row["value"]), "reported_preferred_claim", [_structural_source(structural, row)]
            break
    issued = _structural_rows(structural, ("PreferredStockSharesIssued",), period_start=None, period_end=period_end, unit="xbrli:shares")
    outstanding = _structural_rows(structural, ("PreferredStockSharesOutstanding",), period_start=None, period_end=period_end, unit="xbrli:shares")
    preferred_flows = [
        row for row in structural.get("facts", [])
        if "Preferred" in str(row.get("local_name", ""))
        and row.get("period_start") is not None
        and row.get("period_end") == period_end
        and row.get("unit") == "USD"
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) != 0
        and not row.get("dimensions")
    ]
    if issued and outstanding and all(float(row["value"]) == 0 for row in issued + outstanding) and not preferred_flows:
        status = "reported_preferred_absence"
    elif rows and float(rows[0]["value"]) == 0 and not preferred_flows and (not issued or all(float(row["value"]) == 0 for row in issued)):
        status = "reported_preferred_absence"
    elif not rows and not preferred_flows and not issued and not outstanding:
        status = "statement_proven_preferred_absence"
    else:
        raise ValueError("economic preferred claim is not source-bounded")
    source = {
        "source_kind": "structural_statement_absence_check",
        "accession": structural.get("source_accession"),
        "filed": structural.get("filed_date"),
        "form": structural.get("form"),
        "period_end": period_end,
        "searched_concepts": list(names) + ["PreferredStockSharesIssued", "PreferredStockSharesOutstanding"],
        "treatment": "Preferred claim is treated as absent only after the controlling filing shows no preferred shares/dividends or an explicit zero preferred class; blank source scope is not silently converted to zero.",
        "reported_vs_estimated": "source_bounded_absence_check",
    }
    return 0.0, status, [source]


def _nci_claims(structural: dict[str, Any], period_end: str) -> tuple[dict[str, Any], dict[str, Any]]:
    def point(names: tuple[str, ...]) -> dict[str, Any]:
        for name in names:
            rows = _structural_rows(structural, (name,), period_start=None, period_end=period_end, unit="USD")
            if rows:
                return _structural_source(structural, rows[0])
        return {
            "source_kind": "structural_statement_absence_check",
            "accession": structural.get("source_accession"),
            "filed": structural.get("filed_date"),
            "period_end": period_end,
            "searched_concepts": list(names),
            "value": 0.0,
            "unit": "USD",
            "treatment": "No nonzero NCI point fact in the controlling equity statement; parent equity remains the model anchor.",
            "reported_vs_estimated": "source_bounded_absence_check",
        }

    return point(("MinorityInterest", "NoncontrollingInterestInConsolidatedEntity")), point(("RedeemableNoncontrollingInterestEquityCarryingAmount", "TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests"))


def _earnings_attribution(structural: dict[str, Any], parent: dict[str, Any], period: str, target_days: int) -> dict[str, Any]:
    try:
        consolidated = _period_flow(structural, ("ProfitLoss",), period, target_days=target_days)
    except ValueError:
        return {"period": period, "parent_attributable": parent, "treatment": "Selected common-earnings concept is already parent/common attributable; no NCI subtraction applied."}
    nci_names = ("NetIncomeLossAttributableToNoncontrollingInterest", "NetIncomeLossAttributableToNoncontrollingInterestAndRedeemableNoncontrollingInterest")
    try:
        nci = _period_flow(structural, nci_names, period, target_days=target_days)
    except ValueError:
        return {"period": period, "parent_attributable": parent, "consolidated": consolidated, "treatment": "Consolidated line retained as diagnostic; common-earnings selector is parent attributable and no NCI subtraction applied."}
    if abs(consolidated["value"] - nci["value"] - parent["value"]) < 0.5:
        return {"period": period, "parent_attributable": parent, "consolidated": consolidated, "nci": nci, "formula": "consolidated earnings - NCI earnings = parent/common earnings; selected parent line is not reduced again"}
    allocation = _period_flow(structural, ('UndistributedEarningsLossAllocatedToParticipatingSecuritiesBasic',), period, target_days=target_days)
    if abs(consolidated['value']-nci['value']-allocation['value']-parent['value'])<.5:
        return {'period':period,'parent_attributable':parent,'consolidated':consolidated,'nci':nci,'participating_earnings':allocation,'formula':'consolidated - NCI - participating earnings = common earnings; no second deduction'}
    raise ValueError('Parent/common attribution does not reconcile')


def build_insurer(ticker: str, facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any]) -> dict[str, Any]:
    """Build one private Batch 38 insurer result from already-captured facts."""
    if ticker not in INSURER_TICKERS:
        raise ValueError(ticker)
    if not isinstance(filing, dict) or filing.get("period_end") is None or filing.get("accession") is None:
        raise ValueError(f"{ticker}: controlling filing identity is required")
    period = str(filing["period_end"])
    if str(structural.get("source_accession")) != str(filing["accession"]) or str(structural.get("report_date")) != period:
        raise ValueError(f"{ticker}: structural source does not match controlling filing")
    if period > BATCH_38_VALUATION_DATE or str(filing.get("filed", "")) > BATCH_38_VALUATION_DATE:
        raise ValueError(f"{ticker}: controlling filing is after valuation cutoff")

    policy = POLICY[ticker]
    annual = _annual(facts, ticker)
    current = _period_flow(structural, EARNINGS[ticker], period)
    duration = (date.fromisoformat(period) - date.fromisoformat(current["period_start"])).days
    prior_end = f"{int(period[:4]) - 1}{period[4:]}"
    prior = _period_flow(structural, EARNINGS[ticker], prior_end, target_days=duration)
    ttm = float(annual[-1]["value"]) + float(current["value"]) - float(prior["value"])

    end_total = _equity(structural, period, facts)
    prior_total = _equity(structural, annual[-1]["period_end"], facts)
    preferred, preferred_status, preferred_sources = _preferred(structural, period)
    prior_preferred, prior_preferred_status, prior_preferred_sources = _preferred(structural, annual[-1]["period_end"])
    share = _share_exact(structural, facts, period)
    end_common = float(end_total["value"]) - preferred
    begin_common = float(prior_total["value"]) - prior_preferred
    if min(ttm, end_common, begin_common, float(share["value"])) <= 0:
        raise ValueError(f"{ticker}: nonpositive parent/common inputs")

    observations = [
        HistoryObservation("annual", row["period_end"], int(row["period_end"][:4]), row["value"], "USD", "reported annual parent/common earnings", (row["source"],))
        for row in annual
    ]
    observations.append(HistoryObservation("operating_ttm", period, None, ttm, "USD", "latest FY plus current YTD less prior comparable YTD", (annual[-1]["source"], current, prior)))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    if metric is None:
        raise ValueError(f"{ticker}: common-earnings history unavailable")
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "financial_equity_residual_income", BATCH_38_VALUATION_DATE, tuple(row["period_end"] for row in annual), (metric,), True, "reported_and_company_history")

    history_high = max(metric.high, ttm) / end_common
    roes = tuple(min(float(value), max(.03, history_high)) for value in policy["roe"])
    if not 0 < roes[0] <= roes[1] <= roes[2] or roes[0] == roes[2]:
        roes = (max(.02, history_high * .50), max(.025, history_high * .75), history_high)
    japan = None
    if ticker == 'PRU':
        # The current TTM already includes the H1 impact. Cap modeled earnings
        # by the remaining 2026 cost, with no extra subtraction from equity.
        remaining = (340e6,315e6,290e6)
        ceilings = tuple((ttm-cost*.79)/end_common for cost in remaining)
        ceilings_2027 = tuple((ttm-cost*.79)/end_common for cost in (450e6,425e6,400e6))
        ceilings = tuple(min(a,b) for a,b in zip(ceilings,ceilings_2027))
        roes = tuple(min(roe,ceiling) for roe,ceiling in zip(roes,ceilings))
        japan = {'source_kind':'controlling_filing_narrative','accession':filing['accession'],'period_end':period,'locator':'MD&A International Businesses: Prudential of Japan suspension','reported_h1_pre_tax_impact':235e6,'reported_2026_pre_tax_range':[525e6,575e6],'reported_2027_pre_tax_range':[400e6,450e6],'remaining_2026_pre_tax_scenarios':remaining,'tax_rate_assumption':.21,'roe_ceilings':ceilings,'modeled_roes':roes,'formula':'cap forward earnings at TTM common earnings minus (2026 full-year impact minus reported H1 impact) times 0.79; no double deduction of H1 or book equity','unknown_reimbursement_tail':None,'reported_vs_estimated':'reported forecast bounds with governed tax and scenario mapping'}
        japan['2027_roe_ceilings']=ceilings_2027
        japan['effect']='Nonbinding: all chosen policy ROEs are already below both stressed earnings ceilings. No additional subtraction is made. Forecast levels, not a separate reserve, accommodate the disclosed earnings headwind.'
    share_value = float(share["value"])
    shares = (share_value * 1.015, share_value, share_value * .985)
    terminal_roe = (.085, .105, .115)
    terminal_growth = (.01, .02, .025)
    rows: list[dict[str, Any]] = []
    traces: dict[str, Any] = {}
    for idx, name in enumerate(("bear", "base", "bull")):
        book = end_common / shares[idx]
        trace = residual_income_valuation(book_value_per_share=book, current_roe=roes[idx], cost_of_equity=policy["coe"][idx], current_payout_ratio=policy["payout"][idx], terminal_roe=terminal_roe[idx], terminal_growth=terminal_growth[idx], years=FORECAST_YEARS)
        raw = float(trace["intrinsic_value"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": raw, "book_value_per_share": book, "current_roe": roes[idx], "current_payout_ratio": policy["payout"][idx], "cost_of_equity": policy["coe"][idx], "terminal_roe": terminal_roe[idx], "terminal_growth": terminal_growth[idx], "shares": shares[idx], "preferred_claim": preferred, "ending_common_equity": end_common, "limited_liability_floor_applied": False})
        traces[name] = trace
    scenario = {"low": rows[0]["raw_value_per_share"], "base": rows[1]["raw_value_per_share"], "high": rows[2]["raw_value_per_share"]}
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid residual-income range")

    nci, redeemable_nci = _nci_claims(structural, period)
    prior_nci, prior_redeemable_nci = _nci_claims(structural, annual[-1]["period_end"])
    attribution = [_earnings_attribution(structural, current, period, duration), _earnings_attribution(structural, prior, prior_end, duration)]
    reasons = ("SPECIALIST_MODEL_UNCERTAINTY",)
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    event_focus = {
        "EG": "The July 29 8-K earnings release is an event diagnostic only; catastrophe/reserve and reinsurance changes are not projected from the release without a bounded source schedule.",
        "PFG": "The July 20 AUM release is not issuer cash and is not added to equity; the July 27 earnings release remains a reported-operations diagnostic only.",
        "PRU": "The July 24 Prudential Life Japan reimbursement update reports 2.85B yen of reviewed/completed claims and an ongoing committee tail; the August 4 earnings and financial supplement do not provide a bounded parent-level reserve overlay, so no invented charge is applied.",
        "AIZ": "The August 4 earnings release is retained as a reported-operations diagnostic; catastrophe/reserve and specialty-mix changes are not projected without a bounded source schedule.",
    }[ticker]
    warning = policy["warning"] + " The model uses parent/common earnings and stockholders' equity. " + event_focus + " Unquantified legal and transaction outcomes can move actual value outside this reported-operations range."
    if japan:
        warning += ' The chosen earnings assumptions already sit below ceilings reflecting the reported Japan suspension impacts for 2026 and 2027; this check does not reduce the values again. The reimbursement tail is unquantified and remains outside the range.'
    assumptions = {
        **profile.public_metadata(),
        "forecast_years": FORECAST_YEARS,
        "equity_floor_basis": "not applied",
        "earnings_multiples": tuple(row['raw_value_per_share']*row['shares']/ttm for row in rows),
        "normalization_basis": "reported_five_year_parent_common_earnings_history",
        "assumption_source_mix": "reported_equity_earnings_company_history_and_finsight_policy",
        "current_roe": roes,
        "current_payout_ratio": tuple(policy["payout"]),
        "cost_of_equity": tuple(policy["coe"]),
        "terminal_roe": terminal_roe,
        "terminal_growth": terminal_growth,
        "shares": shares,
        "route_is_equity_level": True,
        "ev_debt_bridge_applied": False,
        "preferred_claim_status": preferred_status,
        "preferred_claim_range": (preferred, preferred, preferred),
        "nci_claim": nci["value"],
        "redeemable_nci_claim": redeemable_nci["value"],
        "calculator_calibration": "Calculator replays the exact residual-income assumptions.",
        "invalidation": "Invalidate if parent earnings, common equity, preferred/NCI claims, shares, catastrophe/reserve experience, investment marks or regulatory capital leave the bounded range.",
    }
    baseline = BaselineValuation(ticker=ticker, method=policy["method"], method_version=BATCH_38_INSURER_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported parent/common equity", end_common, AssumptionClassification.REPORTED, "Controlling stockholders' equity less separately identified preferred claim."), BaselineAssumption("five annual earnings periods", len(annual), AssumptionClassification.HISTORICALLY_DERIVED, "Exact 10-K periods cap the ROE range.")), warnings=(warning, assumptions["invalidation"]), confidence_reasons=reasons, calculator_link=f"/api/us-valuations/{ticker}/calculator")

    return {
        "ticker": ticker,
        "method": policy["method"],
        "model_version": BATCH_38_INSURER_VERSION,
        "availability_type": "conditional_estimate",
        "scenario_rows": rows,
        "scenario_range": scenario,
        "reported_inputs": {"raw_ttm_common_earnings": ttm, "beginning_total_equity": float(prior_total["value"]), "ending_total_equity": float(end_total["value"]), "beginning_common_equity": begin_common, "ending_common_equity": end_common, "preferred_claim": preferred, "share_count": share_value},
        "governed_assumptions": assumptions,
        "history_reliability": reliability.as_dict(),
        "source_ledger": {
            "controlling_filing": filing,
            "common_earnings_reconstruction": {"annual_history": list(annual), "latest_fy": annual[-1], "current_ytd": current, "prior_ytd": prior, "ttm": ttm, "formula": "latest FY + current YTD - prior comparable YTD"},
            "earnings_attribution_context": attribution,
            "company_history_profile": profile.as_private_dict(),
            "equity_model_context": [end_total, prior_total, *preferred_sources, *prior_preferred_sources, share],
            "preferred_context": {"current_status": preferred_status, "prior_status": prior_preferred_status, "current": preferred_sources, "prior": prior_preferred_sources},
            "nci_context": {"current_minority_interest": nci, "current_redeemable_nci": redeemable_nci, "prior_minority_interest": prior_nci, "prior_redeemable_nci": prior_redeemable_nci, "treatment": "Reported parent stockholders' equity is the model anchor; NCI claims remain a disclosed economic control and are not deducted twice."},
            "event_sources": [],
            "event_focus": event_focus,
            "japan_forward_earnings_constraint": japan,
            "event_treatment": "Cutoff event receipt is attached by the Batch 38 root; this module makes no unsupported event overlay.",
            "bridge_treatment": "Equity-level model: policy reserves, separate accounts, insurance float, investment portfolios and funding remain inside parent common earnings/equity; no EV bridge and no double NCI subtraction.",
            "residual_income_trace": {"states": traces},
            "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False, "basis": "Filing period and exact fact-row periods govern; parser wrapper period is diagnostic only."},
        },
        "warning": warning,
        "baseline": baseline.as_private_dict(),
    }


if set(POLICY) != set(INSURER_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(INSURER_TICKERS):
    raise RuntimeError("Batch 38 insurer policy mismatch")
