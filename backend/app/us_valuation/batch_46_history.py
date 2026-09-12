"""History-backed utility equity baselines for controlled Universe Reset Batch 46."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any

from app.valuation.bank import residual_income_valuation
from .baseline import AvailabilityType, BaselineValuation
from .batch_04_launch_first import _controlling
from .batch_35_history import _instant
from .batch_40_history import _latest_shares
from .batch_46 import BATCH_46_MANIFEST, BATCH_46_TICKERS, BATCH_46_VALUATION_DATE
from .batch_46_sources import verify_source_bundle
from .practical_models import EquityCashFlowState, mixed_utility_fcfe, practical_equity_cash_flow_range
from .reliability import assess_reliability

BATCH_46_HISTORY_VERSION = "BATCH-46-UTILITY-EQUITY-1.0"
PERIOD = "2026-06-30"
PASS_TICKERS = frozenset()
WITHHELD_TICKERS = frozenset({"EIX", "AES", "PCG", "SRE"})
CONDITIONAL_TICKERS = frozenset(set(BATCH_46_TICKERS) - WITHHELD_TICKERS)
FCFE_ELIGIBLE = frozenset({"ATO", "PPL", "FE"})
INCOME = {ticker: ("NetIncomeLossAvailableToCommonStockholdersBasic",) for ticker in BATCH_46_TICKERS}
INCOME["FE"] = ("NetIncomeLoss",)

WARNINGS = {
    "ATO": "Conditional Low regulated-gas-utility residual-income baseline. Fiscal-year seasonality, safety/reliability capex, securitized debt, rate recovery and ongoing equity funding remain material.",
    "CMS": "Conditional Low regulated-utility residual-income baseline. NorthStar scope, preferred stock, NCI, environmental obligations, capital spending and rate recovery remain material.",
    "EIX": "Withheld: Edison/SCE wildfire liabilities, insurance and Wildfire Fund recoveries, regulatory recovery, preferred/NCI claims and parent-versus-subsidiary funding are not finitely reconciled.",
    "AES": "Withheld: consolidated cash flow mixes parent recourse funding with nonrecourse project debt, large NCI and redeemable interests; a source-bounded project/parent allocation is unavailable.",
    "PPL": "Conditional Low utility FCFE baseline. Rhode Island integration, special items, rate recovery, construction spending and debt funding remain material.",
    "DTE": "Conditional Low regulated-utility residual-income baseline. Data-center commitments, pending approvals, future equity issuance, project capex and rate recovery remain material.",
    "AEE": "Conditional Low regulated-utility residual-income baseline. Nuclear fuel, rate recovery, money-pool/debt funding, NCI and prospective ATM dilution remain material.",
    "PCG": "Withheld: wildfire claims and recoveries, preferred/NCI claims, regulatory disallowance risk, current share dilution and debt issuance are not source-bounded as one common-equity state.",
    "FE": "Conditional Low regulated-utility residual-income baseline. NCI attribution, storm/environmental costs, Energize365 capex, debt funding and regulatory approvals remain material.",
    "SRE": "Withheld: regulated utilities, LNG/infrastructure and merchant activities cannot be separated from pending KKR/Ecogas transactions, temporary equity, NCI and project funding with current evidence.",
}
EVENT_TREATMENTS = {
    "ATO": "The earnings release and management retirement are recorded; capex/rate guidance is context and is not added to intrinsic value.",
    "CMS": "The NorthStar strategy and parent-funding reduction are context only; no forecast benefit is added without a filed cash bridge.",
    "EIX": "Wildfire, recovery, preferred and financing disclosures remain an unresolved hard gate; expected recoveries are not treated as surplus value.",
    "AES": "Credit-facility amendments do not supply the missing parent/project allocation; recourse and nonrecourse funding are never combined as owner cash.",
    "PPL": "Integration and ISO-NE special items remain comparability warnings and are not adjusted twice; financing is consumed only through reported cash-flow facts.",
    "DTE": "Data-center agreements, battery plans and future equity issuance are context; unsigned or unapproved projects are not capitalized as value.",
    "AEE": "The ATM/forward program is a dilution trigger, not current cash or shares until issued; the full capacity is not added to value.",
    "PCG": "Wildfire reform, claims/recoveries and mortgage-bond financing remain unresolved; unreceived recoveries are not added to value.",
    "FE": "Energize365 and data-center plans remain rate/capex context; projected spend and load are not added as assets.",
    "SRE": "The pending KKR infrastructure sale and Ecogas disposal are not closed-state value; proceeds, taxes, NCI and retained economics need a filed bridge.",
}
WITHHELD_RELEASE = {
    "EIX": "Revalue only after a source-bounded Edison/SCE wildfire liability, recovery, preferred/NCI and parent-funding reconciliation.",
    "AES": "Revalue only after parent cash, recourse/nonrecourse project debt, NCI/redeemable claims and project cash flows are allocated without overlap.",
    "PCG": "Revalue only after wildfire liabilities/recoveries, preferred/NCI, current diluted shares and debt issuance reconcile to one cutoff-safe common-equity state.",
    "SRE": "Revalue only after a segment or SOTP bridge allocates KKR/Ecogas effects, temporary equity, NCI and project funding across the current economic object.",
}
DIRECT_RESIDUAL_REASONS = {
    "CMS": "Comparable annual PP&E cash capex is absent from the current Companyfacts concept and NorthStar changes the operating scope; residual income avoids inventing cash reinvestment.",
    "DTE": "The current productive-asset cash-flow line includes business acquisitions net of acquired cash, so it is not a clean recurring utility-capex input for FCFE.",
    "AEE": "The annual and current long-term-debt repayment concepts change lineage while a prospective ATM/forward program can alter dilution; residual income keeps the current common-equity object explicit.",
}


def _annual_span(ticker: str, year: int) -> tuple[str, str]:
    return (f"{year - 1}-10-01", f"{year}-09-30") if ticker == "ATO" else (f"{year}-01-01", f"{year}-12-31")


def _source(row: dict[str, Any], concept: str) -> dict[str, Any]:
    return {"source_kind": "companyfacts", "concept": f"us-gaap:{concept}", "value": float(row["val"]), "unit": "USD", "period_start": row.get("start"), "period_end": row.get("end"), "filed": row.get("filed"), "accession": row.get("accn"), "form": row.get("form"), "reported_vs_estimated": "reported"}


def _annual_fact(facts: dict[str, Any], ticker: str, concepts: tuple[str, ...], year: int) -> dict[str, Any]:
    start, end = _annual_span(ticker, year)
    for concept in concepts:
        rows = facts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get("USD", [])
        candidates = [row for row in rows if row.get("form") in {"10-K", "10-K/A"} and row.get("start") == start and row.get("end") == end and row.get("filed", "") <= BATCH_46_VALUATION_DATE and isinstance(row.get("val"), (int, float)) and not isinstance(row.get("val"), bool)]
        if candidates:
            return _source(max(candidates, key=lambda row: (row.get("filed", ""), row.get("accn", ""))), concept)
    raise ValueError(f"{ticker}: annual {concepts}/{year} absent")


def _annual_instant(facts: dict[str, Any], ticker: str, concepts: tuple[str, ...], year: int) -> dict[str, Any]:
    period_end = _annual_span(ticker, year)[1]
    for concept in concepts:
        rows = facts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get("USD", [])
        candidates = [row for row in rows if row.get("start") is None and row.get("end") == period_end and row.get("form") in {"10-K", "10-K/A", "10-Q"} and row.get("filed", "") <= BATCH_46_VALUATION_DATE and isinstance(row.get("val"), (int, float)) and not isinstance(row.get("val"), bool)]
        if candidates:
            return _source(max(candidates, key=lambda row: (row.get("filed", ""), row.get("accn", ""))), concept)
    raise ValueError(f"{ticker}: annual instant {concepts}/{year} absent")


def _annual_common_equity(ticker: str, facts: dict[str, Any], year: int) -> dict[str, Any]:
    concept = "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest" if ticker == "PPL" else "StockholdersEquity"
    parent = _annual_instant(facts, ticker, (concept,), year)
    if ticker == "CMS":
        preferred = _annual_instant(facts, ticker, ("PreferredStockValue",), year)
        return _combine("StockholdersEquity-PreferredStockValue", [(parent, 1), (preferred, -1)])
    if ticker == "EIX":
        preferred = _annual_instant(facts, ticker, ("PreferredStockValueOutstanding",), year)
        return _combine("StockholdersEquity-PreferredStockValueOutstanding", [(parent, 1), (preferred, -1)])
    if ticker == "PCG":
        preferred = _annual_instant(facts, ticker, ("PreferredStockValue", "PreferredStockCarryingValue"), year)
        return _combine("StockholdersEquity-PreferredStock", [(parent, 1), (preferred, -1)])
    return parent


def _structural_flow(structural: dict[str, Any], concepts: tuple[str, ...], start: str, end: str) -> dict[str, Any]:
    for concept in concepts:
        rows = [row for row in structural.get("facts", []) if row.get("local_name") == concept and not row.get("dimensions") and row.get("period_start") == start and row.get("period_end") == end and isinstance(row.get("value"), (int, float)) and not isinstance(row.get("value"), bool)]
        values = {float(row["value"]) for row in rows}
        if len(values) == 1:
            row = rows[-1]
            return {"source_kind": "structural_xbrl", "concept": row.get("qname"), "value": values.pop(), "unit": row.get("unit"), "period_start": start, "period_end": end, "filed": structural.get("filed_date"), "accession": structural.get("source_accession"), "form": structural.get("form"), "reported_vs_estimated": "reported"}
    raise ValueError(f"structural flow {concepts}/{start}/{end} absent")


def _combine(label: str, components: list[tuple[dict[str, Any], int]]) -> dict[str, Any]:
    first = components[0][0]
    return {"source_kind": "derived_reported_components", "concept": label, "value": sum(source["value"] * sign for source, sign in components), "unit": "USD", "period_start": first.get("period_start"), "period_end": first.get("period_end"), "components": [{**source, "sign": sign} for source, sign in components], "reported_vs_estimated": "derived_reported_components"}


def _common_income_annual(ticker: str, facts: dict[str, Any], year: int) -> dict[str, Any]:
    income = _annual_fact(facts, ticker, INCOME[ticker], year)
    if ticker != "FE":
        return income
    nci = _annual_fact(facts, ticker, ("NetIncomeLossAttributableToNoncontrollingInterest",), year)
    return _combine("NetIncomeLoss-NetIncomeLossAttributableToNoncontrollingInterest", [(income, 1), (nci, -1)])


def _current_spans(ticker: str) -> tuple[tuple[str, str], tuple[str, str]]:
    return (("2025-10-01", PERIOD), ("2024-10-01", "2025-06-30")) if ticker == "ATO" else (("2026-01-01", PERIOD), ("2025-01-01", "2025-06-30"))


def _common_income_ttm(ticker: str, facts: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    latest = _annual_fact(facts, ticker, INCOME[ticker], 2025) if ticker == "FE" else _common_income_annual(ticker, facts, 2025)
    current_span, prior_span = _current_spans(ticker)
    current = _structural_flow(structural, INCOME[ticker], *current_span)
    prior = _structural_flow(structural, INCOME[ticker], *prior_span)
    components = [(latest, 1), (current, 1), (prior, -1)]
    if ticker == "FE":
        current_nci = _structural_flow(structural, ("NetIncomeLossAttributableToNoncontrollingInterest",), *current_span)
        prior_nci = _structural_flow(structural, ("NetIncomeLossAttributableToNoncontrollingInterest",), *prior_span)
        annual_nci = _annual_fact(facts, ticker, ("NetIncomeLossAttributableToNoncontrollingInterest",), 2025)
        components = [(latest, 1), (current, 1), (prior, -1), (annual_nci, -1), (current_nci, -1), (prior_nci, 1)]
    value = _combine("latest_fy_plus_current_ytd_minus_prior_ytd_common_income", components)
    value["period_end"] = PERIOD
    value["method"] = "latest_fy_plus_current_ytd_minus_prior_comparable_ytd"
    return value


def _maybe_instant(structural: dict[str, Any], names: tuple[str, ...], period: str) -> dict[str, Any] | None:
    try:
        return _instant(structural, names, period)
    except ValueError:
        return None


def _equity(structural: dict[str, Any], ticker: str, period: str) -> dict[str, Any]:
    preferred = _maybe_instant(structural, ("PreferredStockValueOutstanding", "PreferredStockValue"), period)
    nci = _maybe_instant(structural, ("MinorityInterest", "OtherMinorityInterests"), period)
    temporary = _maybe_instant(structural, ("TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests", "TemporaryEquityCarryingAmount"), period)
    if ticker == "CMS":
        parent_total = _instant(structural, ("StockholdersEquity",), period)
        preferred = _instant(structural, ("PreferredStockValue",), period)
        parent = _combine("StockholdersEquity-PreferredStockValue", [(parent_total, 1), (preferred, -1)])
        total = _instant(structural, ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",), period)
    elif ticker == "PPL":
        total = _instant(structural, ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",), period)
        parent = {**total, "source_kind": "source_bounded_parent_equity_after_claim_search", "claim_absence_check": {"searched_concepts": ["MinorityInterest", "PreferredStockValue", "TemporaryEquityCarryingAmount"], "result": "No parent-level NCI, preferred or temporary-equity balance was reported for the selected period.", "reported_vs_estimated": "source_bounded_absence"}}
        preferred = nci = temporary = None
    elif ticker in {"EIX", "PCG"}:
        parent_total = _instant(structural, ("StockholdersEquity",), period)
        parent = _combine("StockholdersEquity-PreferredStock", [(parent_total, 1), (preferred, -1)]) if preferred else parent_total
        total = _instant(structural, ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",), period)
    else:
        parent = _instant(structural, ("StockholdersEquity",), period)
        total = _maybe_instant(structural, ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",), period) or parent
    denominator = total["value"] + (temporary["value"] if temporary else 0.0)
    share = parent["value"] / denominator
    if not 0 < share <= 1:
        raise ValueError(f"{ticker}: parent equity share invalid")
    return {"parent_common_equity": parent, "total_equity": total, "preferred_equity": preferred, "noncontrolling_interest": nci, "temporary_or_redeemable_equity": temporary, "parent_cash_flow_share": share}


def _events(ticker: str, root: Path, source_manifest_sha256: str) -> dict[str, Any]:
    path = root / ticker / "inventory.json"
    rows = json.loads(path.read_text())
    if not rows or any(row.get("filed", "") > BATCH_46_VALUATION_DATE for row in rows):
        raise ValueError(f"{ticker}: invalid event inventory")
    documents = []
    for row in rows:
        for document in row.get("documents", []):
            document_path = Path(document["path"])
            if not document_path.is_absolute():
                document_path = root.parent.parent / document_path
            if not document_path.exists() or hashlib.sha256(document_path.read_bytes()).hexdigest() != document["sha256"]:
                raise ValueError(f"{ticker}: event hash mismatch")
            documents.append(document)
    return {"source_kind": "sec_event_screening", "screened_filings": rows, "documents": documents, "inventory_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "source_manifest_sha256": source_manifest_sha256, "treatment": EVENT_TREATMENTS[ticker], "reported_vs_estimated": "reported_and_screened"}


def _common_history(ticker: str, facts: dict[str, Any], structural: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    annual = []
    for year in (2024, 2025):
        income = _common_income_annual(ticker, facts, year)
        equity = _annual_common_equity(ticker, facts, year)
        annual.append({"period_end": _annual_span(ticker, year)[1], "common_net_income": income, "common_equity": equity, "roe_on_ending_equity": income["value"] / equity["value"]})
    ttm = _common_income_ttm(ticker, facts, structural)
    prior = _equity(structural, ticker, _annual_span(ticker, 2025)[1])
    current = _equity(structural, ticker, PERIOD)
    ttm_roe = ttm["value"] / ((prior["parent_common_equity"]["value"] + current["parent_common_equity"]["value"]) / 2)
    return annual, {"period_end": PERIOD, "common_net_income": ttm, "beginning_common_equity": prior["parent_common_equity"], "ending_common_equity": current["parent_common_equity"], "roe_on_average_equity": ttm_roe}


def _fcfe_history(ticker: str, facts: dict[str, Any], structural: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    specs = {
        "ATO": {"capex": ("PaymentsToAcquireProductiveAssets",), "issued": ("ProceedsFromIssuanceOfLongTermDebt",), "repaid": ("RepaymentsOfLongTermDebt",), "short": ()},
        "PPL": {"capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "issued": ("ProceedsFromIssuanceOfLongTermDebt",), "repaid": ("RepaymentsOfLongTermDebt",), "short": ("ProceedsFromRepaymentsOfShortTermDebtMaturingInThreeMonthsOrLess",)},
        "FE": {"capex": ("PaymentsToAcquireProductiveAssets",), "issued": ("ProceedsFromIssuanceOfLongTermDebt",), "repaid": ("RepaymentsOfLongTermDebt",), "short": ()},
    }
    spec = specs[ticker]
    annual = []
    for year in (2024, 2025):
        cfo = _annual_fact(facts, ticker, ("NetCashProvidedByUsedInOperatingActivities",), year)
        capex = _annual_fact(facts, ticker, spec["capex"], year)
        income = _common_income_annual(ticker, facts, year)
        issued = _annual_fact(facts, ticker, spec["issued"], year)
        repaid = _annual_fact(facts, ticker, spec["repaid"], year)
        short = _annual_fact(facts, ticker, spec["short"], year) if spec["short"] else None
        reinvestment = capex["value"] + income["value"] - cfo["value"]
        net = issued["value"] - repaid["value"] + (short["value"] if short else 0.0)
        annual.append({"period_end": _annual_span(ticker, year)[1], "operating_cash_flow": cfo, "capital_expenditures": capex, "common_net_income": income, "debt_issued": issued, "debt_repaid": repaid, "short_term_net": short, "reinvestment": reinvestment, "net_borrowing": net, "raw_debt_funding_share": net / reinvestment})
    current_span, prior_span = _current_spans(ticker)
    current = {}
    for field, annual_key, concepts in (("operating_cash_flow", "operating_cash_flow", ("NetCashProvidedByUsedInOperatingActivities",)), ("capital_expenditures", "capital_expenditures", spec["capex"]), ("common_net_income", "common_net_income", INCOME[ticker]), ("debt_issued", "debt_issued", spec["issued"]), ("debt_repaid", "debt_repaid", spec["repaid"]), ("short_term_net", "short_term_net", spec["short"])):
        if not concepts:
            current[field] = None
            continue
        latest = annual[-1][annual_key]
        now = _structural_flow(structural, concepts, *current_span)
        prior = _structural_flow(structural, concepts, *prior_span)
        current[field] = {"value": latest["value"] + now["value"] - prior["value"], "period_end": PERIOD, "method": "latest_fy_plus_current_ytd_minus_prior_ytd", "sources": [latest, now, prior]}
    reinvestment = current["capital_expenditures"]["value"] + current["common_net_income"]["value"] - current["operating_cash_flow"]["value"]
    net = current["debt_issued"]["value"] - current["debt_repaid"]["value"] + (current["short_term_net"]["value"] if current["short_term_net"] else 0.0)
    current.update({"reinvestment": reinvestment, "net_borrowing": net, "raw_debt_funding_share": net / reinvestment})
    return annual, current


def _residual_result(ticker: str, *, filing, common_history, current, equity, shares, event, verification, structural, fcfe_rejection: dict[str, Any]) -> dict[str, Any]:
    observed_roes = tuple(row["roe_on_ending_equity"] for row in common_history) + (current["roe_on_average_equity"],)
    sustainable_roe = median(observed_roes)
    end = current["ending_common_equity"]["value"]
    coe = (0.095, 0.085, 0.075)
    terminal_roe = min(0.105, max(0.075, sustainable_roe))
    rows, traces = [], {}
    for name, cost in zip(("bear", "base", "bull"), coe):
        trace = residual_income_valuation(book_value_per_share=end / shares["value"], current_roe=sustainable_roe, cost_of_equity=cost, current_payout_ratio=0.65, terminal_roe=terminal_roe, terminal_growth=0.02, years=5)
        rows.append({"name": name, "raw_value_per_share": trace["intrinsic_value"], "conditional_value_per_share": trace["intrinsic_value"], "book_value_per_share": end / shares["value"], "current_roe": sustainable_roe, "current_payout_ratio": 0.65, "cost_of_equity": cost, "terminal_roe": terminal_roe, "terminal_growth": 0.02, "shares": shares["value"]})
        traces[name] = trace
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: residual range invalid")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("CONSOLIDATED_MIXED_UTILITY_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"))
    invalidation = "Revalue if common equity, sustainable ROE, payout, regulatory recovery, parent/NCI attribution, shares or cutoff events leave the recorded range."
    baseline = BaselineValuation(ticker=ticker, method="regulated_utility_residual_income", method_version=BATCH_46_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(WARNINGS[ticker], invalidation))
    assumptions = {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 3, "forecast_years": 5, "normalization_basis": "median FY2024, FY2025 and current-TTM common ROE on source-linked common equity", "assumption_source_mix": "reported_common_equity_and_earnings_plus_governed_cost_of_equity_range", "observed_common_roe": observed_roes, "current_roe": (sustainable_roe,) * 3, "current_payout_ratio": (0.65,) * 3, "cost_of_equity": coe, "terminal_roe": (terminal_roe,) * 3, "terminal_growth": (0.02,) * 3, "shares": (shares["value"],) * 3, "scenario_calibration": "cost_of_equity_only; history-normalized ROE, payout, terminal ROE, growth and shares held fixed", "route_is_equity_level": True, "ev_debt_bridge_applied": False, "equity_floor_basis": "not applied", "calculator_calibration": "Exact residual-income assumptions replay through the public calculator.", "invalidation": invalidation}
    return {"ticker": ticker, "method": "regulated_utility_residual_income", "model_version": BATCH_46_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_common_earnings": current["common_net_income"]["value"], "beginning_common_equity": current["beginning_common_equity"]["value"], "ending_common_equity": end, "share_count": shares["value"]}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "annual_common_equity_history": common_history, "ttm_common_equity_state": current, "equity_allocation": equity, "share_source": shares, "event_sources": event, "residual_income_trace": {"states": traces}, "fcfe_route_rejected": fcfe_rejection, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS[ticker], "baseline": baseline.as_private_dict()}


def _fcfe_result(ticker: str, *, filing, common_history, common_current, cash_history, cash_current, equity, shares, event, verification, structural) -> dict[str, Any]:
    raw = tuple(row["raw_debt_funding_share"] for row in (*cash_history, cash_current))
    bounded = sorted(max(0.0, min(1.0, value)) for value in raw)
    funding = ((bounded[0] + bounded[1]) / 2, bounded[1], (bounded[1] + bounded[2]) / 2)
    model_income = cash_current["common_net_income"]["value"] / equity["parent_cash_flow_share"]
    cash = tuple(mixed_utility_fcfe(operating_cash_flow=cash_current["operating_cash_flow"]["value"], capital_expenditures=cash_current["capital_expenditures"]["value"], net_income=model_income, debt_funding_share=value, parent_cash_flow_share=equity["parent_cash_flow_share"]) for value in funding)
    if min(cash) <= 0:
        raise ValueError(f"{ticker}: utility FCFE route not positive")
    states = {name: EquityCashFlowState(cash[index], 0.02, 0.02, 0.085) for index, name in enumerate(("bear", "base", "bull"))}
    value_range, traces = practical_equity_cash_flow_range(states=states, diluted_shares=shares["value"], forecast_years=10, maximum_terminal_share=0.90)
    scenario = value_range.as_dict()
    if abs(scenario["high"] - scenario["base"]) < 1e-12:
        raise ValueError(f"{ticker}: utility FCFE route degenerate")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("CAPEX_CASH_CONVERSION_SENSITIVITY", "SPECIALIST_MODEL_UNCERTAINTY"))
    invalidation = "Revalue if capex, debt funding, parent/common allocation, shares, rate recovery or cutoff events leave the recorded range."
    baseline = BaselineValuation(ticker=ticker, method="regulated_utility_fcfe", method_version=BATCH_46_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(WARNINGS[ticker], invalidation))
    rows = [{"name": name, "value_per_share": scenario[key], "cash_flow": cash[index], "debt_funding_share": funding[index], "growth_rate": 0.02, "terminal_growth": 0.02, "cost_of_equity": 0.085, "shares": shares["value"]} for index, (name, key) in enumerate(zip(("bear", "base", "bull"), ("low", "base", "high")))]
    assumptions = {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 3, "forecast_years": 10, "normalization_basis": "reported FY2024, FY2025 and TTM debt-funded utility reinvestment with bounded funding", "assumption_source_mix": "reported_utility_cash_equity_and_financing_history_plus_governed_clipping", "debt_funding_share": funding, "raw_debt_funding_share": raw, "growth_rate": 0.02, "terminal_growth": 0.02, "cost_of_equity": 0.085, "shares": (shares["value"],) * 3, "equity_floor_basis": "not applied", "route_is_equity_level": True, "ev_debt_bridge_applied": False, "calculator_calibration": "Exact utility FCFE funding range replays through the public calculator.", "funding_clipping_policy": "Raw funding is retained privately; ratios outside 0%-100% are capped only for the sustainable funding range.", "invalidation": invalidation}
    return {"ticker": ticker, "method": "regulated_utility_fcfe", "model_version": BATCH_46_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_operating_cash_flow": cash_current["operating_cash_flow"]["value"], "ttm_capital_expenditures": cash_current["capital_expenditures"]["value"], "ttm_common_net_income": cash_current["common_net_income"]["value"], "model_income_before_parent_allocation": model_income, "parent_cash_flow_share": equity["parent_cash_flow_share"], "share_count": shares["value"]}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "annual_common_equity_history": common_history, "ttm_common_equity_state": common_current, "annual_utility_cash_history": cash_history, "ttm_utility_cash_state": cash_current, "equity_allocation": equity, "share_source": shares, "event_sources": event, "model_trace": {"states": traces}, "funding_clipping": {"raw": raw, "bounded": tuple(max(0.0, min(1.0, value)) for value in raw), "treatment": "Excess financing is not added to recurring owner cash."}, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS[ticker], "baseline": baseline.as_private_dict()}


def _withheld_result(ticker: str, *, filing, common_history, current, equity, shares, event, verification, structural) -> dict[str, Any]:
    intended = "regulated_utility_residual_income" if ticker in {"EIX", "PCG"} else "utility_project_finance_sotp" if ticker == "AES" else "mixed_utility_infrastructure_sotp"
    baseline = BaselineValuation(ticker=ticker, method=intended, method_version=BATCH_46_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(WARNINGS[ticker], WITHHELD_RELEASE[ticker]))
    return {"ticker": ticker, "method": intended, "model_version": BATCH_46_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {"ttm_common_earnings_diagnostic": current["common_net_income"]["value"], "ending_common_equity_diagnostic": current["ending_common_equity"]["value"], "share_count": shares["value"]}, "governed_assumptions": {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 3, "forecast_years": 5, "normalization_basis": "source-linked common-equity history retained as diagnostic only; specialist event/scope gate failed", "assumption_source_mix": "reported_history_and_unresolved_specialist_scope", "equity_floor_basis": "not applied", "availability_separate_from_model_identity": True, "invalidation": WITHHELD_RELEASE[ticker]}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "annual_common_equity_history": common_history, "ttm_common_equity_state": current, "equity_allocation": equity, "share_source": shares, "event_sources": event, "runtime_source_verification": verification, "specialist_gate": {"passed": False, "reason": WARNINGS[ticker], "release_condition": WITHHELD_RELEASE[ticker]}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS[ticker], "baseline": baseline.as_private_dict()}


def build_batch_46_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_46_TICKERS:
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
    common_history, current = _common_history(ticker, facts, structural)
    equity, shares = _equity(structural, ticker, PERIOD), _latest_shares(ticker, structural)
    event = _events(ticker, Path(event_root), verification["source_manifest_sha256"])
    if ticker in WITHHELD_TICKERS:
        return _withheld_result(ticker, filing=filing, common_history=common_history, current=current, equity=equity, shares=shares, event=event, verification=verification, structural=structural)
    rejection: dict[str, Any] = {"executed": False, "reason": DIRECT_RESIDUAL_REASONS.get(ticker, "Complete comparable debt-funded FCFE history is unavailable; regulated common-equity residual income is used without inventing missing cash-flow inputs.")}
    if ticker in FCFE_ELIGIBLE:
        cash_history, cash_current = _fcfe_history(ticker, facts, structural)
        try:
            return _fcfe_result(ticker, filing=filing, common_history=common_history, common_current=current, cash_history=cash_history, cash_current=cash_current, equity=equity, shares=shares, event=event, verification=verification, structural=structural)
        except ValueError as error:
            if "utility FCFE route" not in str(error):
                raise
            rejection = {"executed": True, "observed_error": str(error), "annual_utility_cash_history": cash_history, "ttm_utility_cash_state": cash_current, "reason": "The complete source-derived FCFE route failed the positive/non-degenerate gate; residual income is used without an EV debt bridge."}
    return _residual_result(ticker, filing=filing, common_history=common_history, current=current, equity=equity, shares=shares, event=event, verification=verification, structural=structural, fcfe_rejection=rejection)


if PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_46_TICKERS):
    raise RuntimeError("Batch 46 classification mismatch")
