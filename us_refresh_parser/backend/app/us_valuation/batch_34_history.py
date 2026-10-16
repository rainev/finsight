"""History-backed, practical residual-income baselines for Batch 34.

Banks, insurers, custodians and financial-data businesses are valued at the
common-equity level.  This is deliberate: deposits, policy reserves,
reinsurance and client assets are operating claims of these businesses, not
surplus enterprise cash.  The private result keeps the exact source rows and
the public runner exposes only the range and caveat.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from app.valuation.bank import residual_income_valuation

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_04_launch_first import _controlling, _duration, _point
from .batch_16_history import _share_point
from .batch_30_history import _point_unit
from .batch_34 import BATCH_34_TICKERS, BATCH_34_VALUATION_DATE
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, summarize_history_metric
from .reliability import assess_reliability


BATCH_34_HISTORY_VERSION = "BATCH-34-FINANCIAL-EQUITY-HISTORY-1.0"
FORECAST_YEARS = 5
PASS_TICKERS = frozenset()
CONDITIONAL_TICKERS = frozenset(BATCH_34_TICKERS)
WITHHELD_TICKERS = frozenset()


@dataclass(frozen=True)
class Policy:
    method: str
    roe: tuple[float, float, float]
    payout: tuple[float, float, float]
    cost_of_equity: tuple[float, float, float]
    terminal_roe: tuple[float, float, float]
    terminal_growth: tuple[float, float, float]
    warning: str
    invalidation: str


def _policy(method: str, roe=(.06, .09, .12), payout=(.30, .40, .50), coe=(.115, .10, .09), *, warning: str, invalidation: str) -> Policy:
    return Policy(method, roe, payout, coe, (.085, .105, .115), (.01, .02, .025), warning, invalidation)


P = {
    "USB": _policy("diversified_bank_residual_income_equity_earnings", warning="Conditional Low diversified-bank residual-income baseline. Credit losses, deposit/funding mix, regulatory capital and the large preferred-equity stack remain material.", invalidation="Invalidate if credit losses, deposits/funding, capital, preferred claims, common equity or shares leave the bounded range."),
    "L": _policy("multi_line_insurance_residual_income_equity_earnings", roe=(.05, .09, .13), payout=(.20, .30, .40), coe=(.115, .10, .09), warning="Conditional Low holding-company/insurance residual-income baseline. Insurance subsidiaries, investment income, catastrophe/reserve development and parent liquidity remain material.", invalidation="Invalidate if reserve, catastrophe, investment, subsidiary-dividend or common-equity evidence changes materially."),
    "SPGI": _policy("financial_data_exchange_residual_income_equity_earnings", roe=(.10, .14, .18), payout=(.25, .30, .35), coe=(.105, .09, .08), warning="Conditional Low financial-data residual-income baseline. Ratings/data cycles, acquisition integration, regulatory matters and recurring investment in content/software remain material.", invalidation="Invalidate if ratings/data retention, acquisitions, regulatory matters, common equity or shares leave the stated range."),
    "NTRS": _policy("custody_bank_residual_income_equity_earnings", roe=(.08, .11, .14), payout=(.30, .40, .50), warning="Conditional Low custody-bank residual-income baseline. Fee markets, securities marks, capital, preferred dividends and trust/client-asset economics remain material.", invalidation="Invalidate if fee revenue, securities, capital, preferred claims, common equity or shares changes materially."),
    "BRO": _policy("insurance_broker_residual_income_equity_earnings", roe=(.12, .16, .20), payout=(.20, .28, .35), coe=(.105, .09, .08), warning="Source-bounded Low insurance-broker residual-income baseline. Commission growth, acquisition integration, retention and current common equity remain the principal uncertainty.", invalidation="Invalidate if renewal/commission growth, acquisitions, retention, common equity or shares leaves the bounded range."),
    "PGR": _policy("property_casualty_insurance_residual_income_equity_earnings", roe=(.10, .16, .22), payout=(.20, .28, .36), coe=(.11, .095, .085), warning="Conditional Low P&C-insurance residual-income baseline. Pricing, claims severity, catastrophe losses, reserve development and investment marks remain material.", invalidation="Invalidate if pricing, claims, catastrophe/reserves, investments, common equity or shares changes materially."),
    "TRV": _policy("property_casualty_insurance_residual_income_equity_earnings", roe=(.08, .13, .18), payout=(.20, .28, .36), coe=(.11, .095, .085), warning="Conditional Low P&C-insurance residual-income baseline. Catastrophe losses, reserve development, investment income and underwriting pricing remain material.", invalidation="Invalidate if underwriting, catastrophe/reserve, investment, common-equity or share evidence changes materially."),
    "KEY": _policy("regional_bank_residual_income_equity_earnings", warning="Conditional Low regional-bank residual-income baseline. Credit costs, deposit pricing, securities marks, capital and preferred claims remain material.", invalidation="Invalidate if credit/deposit mix, securities, capital, preferred claims, common equity or shares changes materially."),
    "TFC": _policy("diversified_bank_residual_income_equity_earnings", roe=(.055, .085, .115), warning="Conditional Low diversified-bank residual-income baseline. Credit normalization, deposit/funding costs, capital, preferred claims and execution remain material.", invalidation="Invalidate if credit costs, deposits/funding, capital, preferred claims, common equity or shares changes materially."),
    "STT": _policy("custody_bank_residual_income_equity_earnings", roe=(.08, .11, .14), payout=(.30, .40, .50), warning="Conditional Low custody-bank residual-income baseline. Fee markets, securities marks, capital, preferred dividends and client-asset economics remain material.", invalidation="Invalidate if fee revenue, securities, capital, preferred claims, common equity or shares changes materially."),
}


EARNINGS = {
    "USB": "NetIncomeLossAvailableToCommonStockholdersBasic", "L": "NetIncomeLoss", "SPGI": "NetIncomeLoss",
    "NTRS": "NetIncomeLossAvailableToCommonStockholdersBasic", "BRO": "NetIncomeLossAvailableToCommonStockholdersBasic",
    "PGR": "NetIncomeLoss", "TRV": "NetIncomeLossAvailableToCommonStockholdersBasic", "KEY": "NetIncomeLossAvailableToCommonStockholdersBasic",
    "TFC": "NetIncomeLossAvailableToCommonStockholdersBasic", "STT": "NetIncomeLossAvailableToCommonStockholdersBasic",
}
NCI_EARNINGS = {
    "L": "NetIncomeLossAttributableToNoncontrollingInterest",
    "SPGI": "IncomeLossFromContinuingOperationsAttributableToNoncontrollingEntity",
}
REPORT_END = {ticker: "2026-06-30" for ticker in BATCH_34_TICKERS}


def _rows(facts: dict[str, Any], concept: str, unit: str = "USD") -> list[dict[str, Any]]:
    node = facts.get("facts", {}).get("us-gaap", {}).get(concept)
    if not node:
        return []
    return [row for row in node.get("units", {}).get(unit, []) if isinstance(row.get("val"), (int, float))]


def _annual_common(facts: dict[str, Any], concept: str) -> tuple[dict[str, Any], ...]:
    selected: dict[str, dict[str, Any]] = {}
    from datetime import date
    for row in _rows(facts, concept):
        if row.get("form") not in {"10-K", "10-K/A"} or row.get("filed", "") > BATCH_34_VALUATION_DATE or not row.get("start") or not row.get("end"):
            continue
        span = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
        if not 300 <= span <= 380:
            continue
        old = selected.get(row["end"])
        if old is None or (row.get("filed", ""), row.get("accn", "")) > (old.get("filed", ""), old.get("accn", "")):
            selected[row["end"]] = row
    if len(selected) < 5:
        raise ValueError(f"{concept}: fewer than five exact annual periods")
    return tuple({"period_end": end, "value": float(selected[end]["val"]), "source": _companyfacts_source(selected[end], concept)} for end in sorted(selected)[-5:])


def _annual_parent(facts: dict[str, Any], ticker: str) -> tuple[dict[str, Any], ...]:
    concept = EARNINGS[ticker]
    annual = list(_annual_common(facts, concept))
    nci_concept = NCI_EARNINGS.get(ticker)
    if not nci_concept:
        return tuple(annual)
    nci = {row["period_end"]: row for row in _annual_common(facts, nci_concept)}
    if any(row["period_end"] not in nci for row in annual):
        raise ValueError(f"{ticker}: parent earnings NCI history incomplete")
    return tuple({"period_end": row["period_end"], "value": row["value"] - nci[row["period_end"]]["value"], "source": {"source_kind": "derived_parent_earnings", "formula": "consolidated earnings less NCI earnings", "value": row["value"] - nci[row["period_end"]]["value"], "unit": "USD", "period_end": row["period_end"], "components": [row["source"], nci[row["period_end"]]["source"]], "reported_vs_estimated": "reported_components_with_derived_attribution"}} for row in annual)


def _companyfacts_source(row: dict[str, Any], concept: str) -> dict[str, Any]:
    return {"source_kind": "companyfacts", "concept": f"us-gaap:{concept}", "value": float(row["val"]), "unit": "USD", "period_start": row.get("start"), "period_end": row.get("end"), "filed": row.get("filed"), "accession": row.get("accn"), "form": row.get("form"), "reported_vs_estimated": "reported"}


def _structural_row(structural: dict[str, Any], names: Iterable[str], *, start: str | None = None, end: str, unit: str | None = None, prefer_value: float | None = None) -> dict[str, Any]:
    names = tuple(names)
    # Respect the caller's concept priority.  Filing order is not a
    # semantic priority: a consolidated NetIncomeLoss row often precedes a
    # NetIncomeLossAvailableToCommonStockholdersBasic row.
    matches = []
    for name in names:
        matches = [row for row in structural.get("facts", []) if row.get("local_name") == name and row.get("period_end") == end and row.get("period_start") == start and not row.get("dimensions") and isinstance(row.get("value"), (int, float)) and (unit is None or row.get("unit") == unit)]
        if prefer_value is not None:
            matches = [row for row in matches if float(row["value"]) == float(prefer_value)]
        if matches:
            break
    if not matches:
        raise ValueError(f"structural fact {names} {start}/{end} absent")
    row = matches[0]
    return {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "filed": structural.get("filed_date"), "form": structural.get("form"), "period_start": start, "period_end": end, "concept": row.get("qname"), "unit": row.get("unit"), "value": float(row["value"]), "reported_vs_estimated": "reported"}


def _flow(structural: dict[str, Any], names: Iterable[str], start: str, end: str) -> dict[str, Any]:
    return _structural_row(structural, names, start=start, end=end, unit="USD")


def _parent_flow(structural: dict[str, Any], ticker: str, start: str, end: str) -> dict[str, Any]:
    raw = _flow(structural, (EARNINGS[ticker],), start, end)
    nci_concept = NCI_EARNINGS.get(ticker)
    if not nci_concept:
        return raw
    nci = _flow(structural, (nci_concept,), start, end)
    return {"field": "parent_attributable_earnings", "value": raw["value"] - nci["value"], "unit": "USD", "period_start": start, "period_end": end, "filed": raw.get("filed"), "accession": raw.get("accession"), "form": raw.get("form"), "method": "consolidated_earnings_less_reported_nci", "sources": [raw, nci], "reported_vs_estimated": "reported_components_with_derived_attribution"}


def _instant(structural: dict[str, Any], names: Iterable[str], end: str, *, unit: str = "USD") -> dict[str, Any]:
    return _structural_row(structural, names, start=None, end=end, unit=unit)


def _common_equity_point(structural: dict[str, Any], end: str) -> dict[str, Any]:
    try:
        return _instant(structural, ("StockholdersEquity",), end)
    except ValueError:
        total = _instant(structural, ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",), end)
        nci = _instant(structural, ("MinorityInterest", "NoncontrollingInterestInConsolidatedEntity"), end)
        return {"field": "parent_common_equity", "value": total["value"] - nci["value"], "period_end": end, "method": "consolidated_equity_less_reported_nci", "sources": [total, nci], "reported_vs_estimated": "reported_components_with_derived_attribution"}


def _companyfacts_instant(facts: dict[str, Any], concept: str, period_end: str) -> dict[str, Any]:
    rows = [row for row in _rows(facts, concept) if row.get("end") == period_end and not row.get("start") and row.get("filed", "") <= BATCH_34_VALUATION_DATE]
    if not rows:
        raise ValueError(f"companyfacts instant {concept}/{period_end} absent")
    row = sorted(rows, key=lambda r: (r.get("filed", ""), r.get("accn", "")))[-1]
    return _companyfacts_source(row, concept)


def _share(structural: dict[str, Any], facts: dict[str, Any], end: str) -> dict[str, Any]:
    names = ("EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding")
    try:
        return _instant(structural, names, end, unit="xbrli:shares")
    except ValueError:
        # DEI shares are often reported at a date shortly after the quarter
        # end.  Use the latest cutoff-safe instant, never the parser wrapper
        # period_end and never a future filing.
        candidates = [row for row in structural.get("facts", []) if row.get("local_name") in names and row.get("period_start") is None and row.get("unit") == "xbrli:shares" and not row.get("dimensions") and isinstance(row.get("value"), (int, float)) and end <= str(row.get("period_end", "")) <= BATCH_34_VALUATION_DATE]
        if candidates:
            row = sorted(candidates, key=lambda r: str(r.get("period_end")))[-1]
            return {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "filed": structural.get("filed_date"), "period_end": row["period_end"], "concept": row.get("qname"), "unit": row.get("unit"), "value": float(row["value"]), "reported_vs_estimated": "reported", "selection_note": "latest cutoff-safe DEI instant after controlling report date"}
        rows = []
        for concept in names:
            rows.extend([r for r in facts.get("facts", {}).get("dei", {}).get(concept, {}).get("units", {}).get("shares", []) if r.get("end") == end and isinstance(r.get("val"), (int, float))])
        if not rows:
            raise
        row = sorted(rows, key=lambda r: (r.get("filed", ""), r.get("accn", "")))[-1]
        return {**_companyfacts_source(row, concept), "unit": "shares"}


def _event_rows(ticker: str, event_root: Path | None) -> list[dict[str, Any]]:
    if event_root is None:
        return []
    root = Path(event_root) / ticker
    receipt_path = root / "source-receipt.json"
    if not receipt_path.exists():
        return []
    receipt = json.loads(receipt_path.read_text())
    document = root / receipt["document"]
    if receipt.get("schema_version") != "FINSIGHT-BATCH-34-EVENT-SOURCE-1" or receipt.get("filed", "") > BATCH_34_VALUATION_DATE or not document.exists() or hashlib.sha256(document.read_bytes()).hexdigest() != receipt.get("document_sha256"):
        raise ValueError(f"{ticker}: invalid event source")
    return [{"source_kind": "sec_event_filing", "accession": receipt["accession"], "filed": receipt["filed"], "period_end": receipt.get("report_date"), "form": receipt["form"], "source_url": receipt["url"], "document_sha256": receipt["document_sha256"], "reported_terms": receipt["reported_terms"], "treatment": receipt["treatment"], "reported_vs_estimated": "reported"}]


def _preferred_context(ticker: str, structural: dict[str, Any], end: str, event_rows: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]], str, tuple[float, float, float]]:
    # Values are claims, not investment-schedule preferred securities.  If a
    # filing only reports preferred dividends, retain that evidence and cap
    # reliability rather than quietly making the claim zero.
    value_names = ("PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount", "PreferredStockValue", "PreferredStockLiquidationPreferenceValue")
    for name in value_names:
        try:
            row = _instant(structural, (name,), end)
            value = float(row["value"])
            return value, [row], "reported_preferred_claim", (value, value, value)
        except ValueError:
            continue
    evidence = []
    try:
        evidence.append(_flow(structural, ("PreferredStockDividends", "PreferredStockDividendsIncomeStatementImpact", "PaymentsOfDividendsPreferredStockAndPreferenceStock"), "2026-01-01", end))
    except ValueError:
        pass
    if evidence:
        # Convert a reported six-month preferred-dividend stream into a
        # governed claim estimate.  The yield is an explicit 5%-7% policy
        # range (6% base), rather than pretending the unavailable carrying
        # value is zero.  The estimate remains Low reliability.
        six_month_dividend = float(evidence[0]["value"])
        annual_dividend = six_month_dividend * 2.0
        base = annual_dividend / 0.06
        claim_range = (annual_dividend / 0.07, base, annual_dividend / 0.05)
        if ticker == "STT":
            event_item = next((item for item in event_rows if item.get("accession") == "0001193125-26-346938"), None)
            event_claim = float(event_item.get("reported_terms", {}).get("liquidation_preference_total", 0.)) if event_item else 0.
            base += event_claim
            claim_range = tuple(value + event_claim for value in claim_range)
            if event_item:
                evidence.append(event_item)
        return base, evidence, "preferred_claim_estimated_from_reported_dividend_yield_sensitivity", claim_range
    # No preferred fact is a proven absence only when the filing explicitly
    # carries a zero PreferredStockValue row; otherwise reject the shortcut.
    try:
        row = _instant(structural, ("PreferredStockValue",), end)
        if float(row["value"]) == 0:
            return 0., [row], "reported_preferred_absence"
    except ValueError:
        pass
    # No preferred value/dividend/outstanding row was reported by the
    # controlling filing.  This is a source-bounded absence, not a missing
    # input converted to zero; retain the reason in the private ledger and
    # keep the result Low.
    # Keep a finite, conservative sensitivity rather than silently treating
    # an unreported claim as zero.  The lower bound is the no-claim case; the
    # midpoint/high cases reserve 1%/3% of reported equity for an omitted
    # preferred layer.  This is explicitly a FinSight uncertainty range.
    absence = {"source_kind": "structural_xbrl_absence_check", "accession": structural["source_accession"], "filed": structural.get("filed_date"), "period_end": end, "searched_concepts": list(value_names) + ["PreferredStockSharesOutstanding"], "reported_vs_estimated": "source_bounded_absence_check"}
    return 0., [absence], "preferred_claim_bounded_from_no_reported_claim_row", (0., 0., 0.)


def _preferred_period_range(
    *,
    structural: dict[str, Any],
    period_end: str,
    status: str,
    current_range: tuple[float, float, float],
    equity: float,
    event_rows: list[dict[str, Any]],
) -> tuple[float, float, float]:
    """Return the preferred claim range anchored to a specific balance-sheet date.

    Beginning book value must not inherit a current-period issuance or current
    equity-based placeholder.  Exact carrying-value rows are preferred; the
    governed claim estimate is retained only when the filing does not expose a
    period-specific claim.  A cutoff event is removed from the beginning range
    because it did not exist at the earlier balance-sheet date.
    """
    if status == "reported_preferred_absence":
        return (0.0, 0.0, 0.0)
    if status == "reported_preferred_claim":
        for name in (
            "PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount",
            "PreferredStockValue",
            "PreferredStockLiquidationPreferenceValue",
        ):
            try:
                row = _instant(structural, (name,), period_end)
                value = float(row["value"])
                return (value, value, value)
            except ValueError:
                continue
    if status == "preferred_claim_bounded_from_no_reported_claim_row":
        return (0.0, equity * 0.01, equity * 0.03)

    # Dividend-derived estimates have no reliable historical carrying value.
    # Keep their governed range, but remove any separately reported event claim
    # from the earlier period so a post-quarter issuance is not backdated.
    event_claim = sum(
        float(row.get("reported_terms", {}).get("liquidation_preference_total", 0.0))
        for row in event_rows
    )
    return tuple(max(0.0, float(value) - event_claim) for value in current_range)


def _preferred_period_context(structural: dict[str, Any], period_end: str, expected: float) -> list[dict[str, Any]]:
    """Retain the exact period source row when a preferred claim is reported."""
    for name in (
        "PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount",
        "PreferredStockValue",
        "PreferredStockLiquidationPreferenceValue",
    ):
        try:
            row = _instant(structural, (name,), period_end)
        except ValueError:
            continue
        if float(row["value"]) == float(expected):
            return [row]
    return []


def _equity_result(ticker: str, facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], package: dict[str, Any], receipt: dict[str, Any], event_root: Path | None) -> dict[str, Any]:
    policy = P[ticker]
    period = REPORT_END[ticker]
    concept = EARNINGS[ticker]
    annual = _annual_parent(facts, ticker)
    latest = annual[-1]
    current = _parent_flow(structural, ticker, "2026-01-01", period)
    prior = _parent_flow(structural, ticker, "2025-01-01", "2025-06-30")
    ttm = latest["value"] + current["value"] - prior["value"]
    current_equity = _common_equity_point(structural, period)
    try:
        prior_equity = _common_equity_point(structural, "2025-12-31")
    except ValueError:
        prior_equity = _companyfacts_instant(facts, "StockholdersEquity", "2025-12-31")
    event_rows = _event_rows(ticker, event_root)
    preferred, preferred_context, preferred_status, preferred_range = _preferred_context(ticker, structural, period, event_rows)
    if preferred_status == "preferred_claim_bounded_from_no_reported_claim_row":
        preferred_range = (0.0, float(current_equity["value"]) * .01, float(current_equity["value"]) * .03)
        preferred = preferred_range[1]
    beginning_preferred_range = _preferred_period_range(
        structural=structural,
        period_end="2025-12-31",
        status=preferred_status,
        current_range=preferred_range,
        equity=float(prior_equity["value"]),
        event_rows=event_rows,
    )
    beginning_preferred_context = _preferred_period_context(
        structural, "2025-12-31", beginning_preferred_range[1]
    )
    begin_common = float(prior_equity["value"]) - beginning_preferred_range[1]
    end_common = float(current_equity["value"]) - preferred
    if begin_common <= 0 or end_common <= 0 or ttm <= 0:
        raise ValueError(f"{ticker}: nonpositive common equity/earnings")
    share_row = _share(structural, facts, period)
    current_shares = float(share_row["value"])
    if current_shares <= 0:
        raise ValueError(f"{ticker}: nonpositive shares")
    shares = (current_shares * 1.015, current_shares, current_shares * .985)
    observations = [HistoryObservation("annual", row["period_end"], int(row["period_end"][:4]), row["value"], "USD", "reported annual common/parent earnings", (row["source"],)) for row in annual]
    observations.append(HistoryObservation("operating_ttm", period, None, ttm, "USD", "latest FY + current YTD - prior YTD common/parent earnings", (latest["source"], current, prior)))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "financial_equity_residual_income", BATCH_34_VALUATION_DATE, tuple(row["period_end"] for row in annual), (metric,), True, "reported_and_company_history")
    # Keep the policy conservative when it would outrun the observed
    # history.  The high bound includes the current TTM anchor; the middle
    # bound is the reported-history midpoint, and the low bound is the
    # reported-history low.  This makes the ROE bridge an actual constraint,
    # not merely a label attached to hard-coded rates.
    history_low_roe = max(.02, min(metric.low, ttm) / max(end_common, 1.))
    history_high_roe = max(history_low_roe, max(metric.high, ttm) / max(end_common, 1.))
    history_mid_roe = max(history_low_roe, min(history_high_roe, metric.base / max(end_common, 1.)))
    modeled_roe = tuple(min(value, history_high_roe) for value in policy.roe)
    if not history_low_roe <= modeled_roe[0] <= modeled_roe[1] <= modeled_roe[2] <= history_high_roe or modeled_roe[0] == modeled_roe[2]:
        modeled_roe = (history_low_roe, (history_low_roe + history_high_roe) / 2., history_high_roe)
    rows, traces, multiples = [], {}, []
    for idx, name in enumerate(("bear", "base", "bull")):
        scenario_preferred = preferred_range[idx]
        scenario_end_common = float(current_equity["value"]) - scenario_preferred
        scenario_begin_common = float(prior_equity["value"]) - beginning_preferred_range[idx]
        trace = residual_income_valuation(book_value_per_share=scenario_end_common / shares[idx], current_roe=modeled_roe[idx], cost_of_equity=policy.cost_of_equity[idx], current_payout_ratio=policy.payout[idx], terminal_roe=policy.terminal_roe[idx], terminal_growth=policy.terminal_growth[idx], years=FORECAST_YEARS)
        raw = float(trace["intrinsic_value"])
        multiple = raw * shares[idx] / ttm
        rows.append({"name": name, "conditional_value_per_share": raw, "raw_value_per_share": raw, "book_value_per_share": scenario_end_common / shares[idx], "current_roe": modeled_roe[idx], "current_payout_ratio": policy.payout[idx], "cost_of_equity": policy.cost_of_equity[idx], "terminal_roe": policy.terminal_roe[idx], "terminal_growth": policy.terminal_growth[idx], "shares": shares[idx], "normalized_common_earnings": scenario_end_common * modeled_roe[idx], "earnings_multiple": multiple, "preferred_claim": scenario_preferred, "beginning_common_equity": scenario_begin_common, "ending_common_equity": scenario_end_common, "limited_liability_floor_applied": False})
        traces[name] = trace
        multiples.append(multiple)
    scenario = {"low": rows[0]["raw_value_per_share"], "base": rows[1]["raw_value_per_share"], "high": rows[2]["raw_value_per_share"]}
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid residual-income range")
    reasons = ("PROVISIONAL_BANK_CAPITAL_RANGE", "SPECIALIST_MODEL_UNCERTAINTY") if ticker in {"USB", "NTRS", "KEY", "TFC", "STT"} else ("SPECIALIST_MODEL_UNCERTAINTY",)
    cap = "Low"
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap=cap, source_cap="High", reasons=reasons)
    dividend_bound = None
    if preferred_status == "preferred_claim_estimated_from_reported_dividend_yield_sensitivity":
        annual_dividend = float(preferred_context[0]["value"]) * 2.0
        dividend_bound = preferred_range
    warning = policy.warning + (" Preferred carrying value is unavailable; reported preferred dividends are converted to a governed 5%-7% yield claim range." if dividend_bound else "")
    if ticker == "STT" and any(item.get("accession") == "0001193125-26-346938" for item in event_rows):
        warning += " The cutoff-safe Series L $500M preferred issuance is included separately."
    assumptions = {**profile.public_metadata(), "forecast_years": FORECAST_YEARS, "normalization_basis": "reported_common_equity_with_governed_history_bounded_roe", "assumption_source_mix": "reported_equity_earnings_and_company_history_plus_finsight_policy", "equity_floor_basis": "not applied", "earnings_multiples": tuple(multiples), "calculator_calibration": "Calculator varies normalized common earnings and the residual-income-implied multiple around the exact base.", "roe_scenario_bridge": {"reported_ttm_common_earnings": ttm, "reported_ttm_roe": ttm / ((begin_common + end_common) / 2), "reported_history_annual_plus_ttm_range": (metric.low, metric.base, metric.high), "reported_history_roe_range": (history_low_roe, history_mid_roe, history_high_roe), "policy_roe_target": policy.roe, "modeled_roe": modeled_roe, "classification": "finsight_assumption_bounded_by_reported_history_and_current_equity", "normalization_reason": "Policy ROE targets are capped by the maximum of five exact annual observations and the current TTM anchor; if the policy collapses, the observed low/mid/high history is used."}, "current_roe": modeled_roe, "current_payout_ratio": policy.payout, "cost_of_equity": policy.cost_of_equity, "terminal_roe": policy.terminal_roe, "terminal_growth": policy.terminal_growth, "shares": shares, "share_sensitivity_basis": "latest cutoff-safe common shares with governed +/-1.5% stress; weighted diluted shares remain in private source context", "beginning_common_equity": begin_common, "ending_common_equity": end_common, "preferred_claim_status": preferred_status, "preferred_claim_range": preferred_range, "beginning_preferred_claim_range": beginning_preferred_range, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "bridge_formula": "Common equity is current reported equity less separately identified preferred claims; operating funding/reserves/client assets are not EV-bridged.", "invalidation": policy.invalidation}
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_34_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported common equity", end_common, AssumptionClassification.REPORTED, "Current equity less separately identified preferred claims."), BaselineAssumption("five-year earnings history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Five exact annual periods plus current TTM anchor the governed ROE range.")), warnings=(warning, policy.invalidation), confidence_reasons=reasons, calculator_link=f"/api/us-valuations/{ticker}/calculator")
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_34_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_common_earnings": ttm, "beginning_total_equity": float(prior_equity["value"]), "ending_total_equity": float(current_equity["value"]), "preferred_equity": preferred, "beginning_preferred_equity": beginning_preferred_range[1], "beginning_common_equity": begin_common, "ending_common_equity": end_common}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "common_earnings_reconstruction": {"latest_fy": latest, "current_ytd": current, "prior_ytd": prior, "ttm": ttm}, "company_history_profile": profile.as_private_dict(), "equity_model_context": [current_equity, prior_equity, *beginning_preferred_context, *preferred_context, share_row], "beginning_preferred_context": beginning_preferred_context, "preferred_context": preferred_context, "event_sources": event_rows, "residual_income_trace": {"states": traces, "clean_surplus_ddm_is_reconciliation_not_independent_evidence": True}, "bridge_treatment": "Equity-level model: deposits, card funding, policy/claim reserves, reinsurance balances, investments, client assets and debt remain inside common earnings/equity and are never EV-bridged.", "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False, "selection_basis": "source receipt report date plus exact fact periods"}}, "warning": warning, "baseline": baseline.as_private_dict()}


def build_batch_34_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path | None = None) -> dict[str, Any]:
    if ticker not in BATCH_34_TICKERS:
        raise ValueError(ticker)
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    package = json.loads((Path(structural_root) / ticker / "package-manifest.json").read_text())
    receipt = json.loads((Path(structural_root) / ticker / "source-receipt.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural.get("source_accession") != filing["accession"] or structural.get("report_date") != filing["period_end"]:
        raise ValueError(f"{ticker}: controlling source mismatch")
    return _equity_result(ticker, facts, structural, filing, package, receipt, event_root)


if set(P) != set(BATCH_34_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_34_TICKERS):
    raise RuntimeError("Batch 34 policy mismatch")
