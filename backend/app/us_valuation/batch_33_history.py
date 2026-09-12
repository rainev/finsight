"""History-backed financial-equity baselines for Universe Reset Batch 33."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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
from .batch_16_history import _share_point
from .batch_30_history import _fact, _point_unit
from .batch_33 import BATCH_33_TICKERS, BATCH_33_VALUATION_DATE
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, build_cash_fcff_history_profile, summarize_history_metric
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_33_HISTORY_VERSION = "BATCH-33-FINANCIAL-EQUITY-HISTORY-1.0"
FORECAST_YEARS = 5
PASS_TICKERS = frozenset({"MRSH"})
CONDITIONAL_TICKERS = frozenset(set(BATCH_33_TICKERS) - PASS_TICKERS)
WITHHELD_TICKERS = frozenset()


@dataclass(frozen=True)
class EquityPolicy:
    method: str
    period: str
    begin_period: str
    total_equity: tuple[float, float]
    preferred: tuple[float, float]
    shares: tuple[float, float, float]
    current_roe: tuple[float, float, float]
    payout: tuple[float, float, float]
    cost_of_equity: tuple[float, float, float]
    terminal_roe: tuple[float, float, float]
    terminal_growth: tuple[float, float, float]
    warning: str
    invalidation: str


RI = {
    "AXP": EquityPolicy("consumer_finance_residual_income_equity_earnings", "2026-06-30", "2025-12-31", (33_474_000_000., 34_280_000_000.), (1_600_000_000., 1_600_000_000.), (682_000_000., 678_500_000., 675_309_833.), (.20, .28, .34), (.25, .30, .35), (.11, .095, .085), (.09, .11, .12), (.01, .02, .025), "Conditional Low consumer-finance residual-income baseline. Credit losses, card funding/deposits, regulatory capital, and the cutoff Series E issuance/Series D redemption sequence remain material.", "Invalidate if credit loss, card receivables, deposits/funding, regulatory capital, preferred redemption, common equity, or shares changes materially."),
    "AFL": EquityPolicy("life_health_insurance_residual_income_equity_earnings", "2026-06-30", "2025-12-31", (29_490_000_000., 30_312_000_000.), (0., 0.), (510_150_000., 505_750_000., 501_343_298.), (.10, .15, .20), (.20, .22, .25), (.105, .09, .08), (.085, .10, .11), (.01, .02, .025), "Conditional Low life/health-insurance residual-income baseline. Policy liabilities, Japan/US mix, FX, claims, reinsurance, and current risk-based capital remain material.", "Invalidate if claims/reserves, reinsurance, Japan/US mix, FX, capital, common equity, or shares changes materially."),
    "AIG": EquityPolicy("multiline_insurance_residual_income_equity_earnings", "2026-06-30", "2025-12-31", (41_139_000_000., 40_606_000_000.), (0., 0.), (537_846_532., 530_000_000., 522_893_169.), (.03, .07, .11), (.25, .32, .40), (.115, .10, .09), (.07, .09, .11), (.01, .02, .025), "Conditional Low multi-line-insurance residual-income baseline. Negative and positive earnings years are retained; reserve development, reinsurance recoverability, runoff exposure, catastrophe loss, and capital remain material.", "Invalidate if reserve development, reinsurance recovery, catastrophe/runoff exposure, capital, common equity, or shares changes materially."),
    "WRB": EquityPolicy("property_casualty_insurance_residual_income_equity_earnings", "2026-06-30", "2025-12-31", (9_700_818_000., 9_833_239_000.), (0., 0.), (393_316_000., 382_200_000., 371_227_529.), (.12, .18, .22), (.30, .36, .40), (.11, .095, .085), (.09, .10, .11), (.01, .02, .025), "Conditional Low P&C-insurance residual-income baseline. Underwriting/catastrophe cycles, reserve development, reinsurance, investment income, and current capital remain material.", "Invalidate if underwriting, catastrophe losses, reserves/reinsurance, investments, capital, common equity, or shares changes materially."),
    "CINF": EquityPolicy("property_casualty_insurance_investment_residual_income_equity_earnings", "2026-06-30", "2025-12-31", (15_911_000_000., 16_671_000_000.), (0., 0.), (156_300_000., 154_900_000., 153_478_045.), (.06, .15, .20), (.20, .25, .30), (.11, .095, .085), (.09, .10, .11), (.01, .02, .025), "Conditional Low P&C-insurance/investment residual-income baseline. The negative 2022 year remains in history; catastrophe, reserve development, equity-market income, and current capital remain material.", "Invalidate if underwriting/catastrophe losses, reserves, investment values, capital, common equity, or shares changes materially."),
    "FITB": EquityPolicy("post_comerica_regional_bank_residual_income_equity_earnings", "2026-06-30", "2025-12-31", (21_724_000_000., 34_482_000_000.), (1_770_000_000., 2_182_000_000.), (915_959_377., 911_400_000., 906_892_564.), (.06, .09, .12), (.30, .45, .55), (.115, .10, .09), (.08, .10, .11), (.01, .02, .025), "Conditional Low post-Comerica regional-bank residual-income baseline. The enlarged equity/share state is current, while combined annual earnings, credit costs, integration, and regulatory-capital refinement remain material.", "Invalidate if combined earnings, integration, credit losses, deposits/funding, preferred equity, regulatory capital, common equity, or shares changes materially."),
    "MTB": EquityPolicy("regional_bank_residual_income_equity_earnings", "2026-06-30", "2025-12-31", (29_177_000_000., 27_946_000_000.), (2_834_000_000., 2_434_000_000.), (148_424_000., 146_400_000., 144_416_262.), (.08, .105, .125), (.25, .32, .40), (.115, .10, .09), (.09, .105, .115), (.01, .02, .025), "Conditional Low regional-bank residual-income baseline. Preferred redemption, credit/deposit mix, securities marks, funding, and current regulatory-capital refinement remain material.", "Invalidate if credit/deposit mix, securities, funding, preferred equity, regulatory capital, common equity, or shares changes materially."),
    "BEN": EquityPolicy("asset_manager_residual_income_equity_earnings_fallback", "2026-06-30", "2025-09-30", (12_077_800_000., 11_738_200_000.), (0., 0.), (517_500_000., 512_800_000., 508_076_910.), (.04, .065, .09), (.65, .75, .85), (.12, .105, .095), (.06, .075, .09), (.01, .02, .025), "Conditional Low asset-manager equity-earnings baseline. AUM/flows, fee compression, client-asset segregation, NCI/temporary equity, debt refinancing, and high historical payout remain material.", "Invalidate if AUM/flows, fees, client-asset segregation, NCI/temporary equity, refinancing, common equity, or shares changes materially."),
    "HBAN": EquityPolicy("post_veritex_cadence_regional_bank_residual_income_equity_earnings", "2026-06-30", "2025-12-31", (24_342_000_000., 32_624_000_000.), (2_731_000_000., 2_881_000_000.), (2_048_311_000., 2_034_000_000., 2_020_414_826.), (.06, .09, .115), (.35, .45, .55), (.115, .10, .09), (.085, .105, .115), (.01, .02, .025), "Conditional Low post-Veritex/Cadence regional-bank residual-income baseline. Current Q2 structural facts repair stale Companyfacts; combined annual earnings, credit/deposits, NCI, preferred equity, and capital remain material.", "Invalidate if combined earnings, credit/deposits, integration, NCI/preferred equity, regulatory capital, common equity, or shares changes materially."),
}


EARNINGS = {
    "AXP": ("NetIncomeLossAvailableToCommonStockholdersBasic", "2026-01-01", 6_014_000_000., "2025-01-01", 5_404_000_000.),
    "AFL": ("NetIncomeLoss", "2026-01-01", 1_844_000_000., "2025-01-01", 628_000_000.),
    "AIG": ("NetIncomeLossAvailableToCommonStockholdersBasic", "2026-01-01", 1_711_000_000., "2025-01-01", 1_842_000_000.),
    "WRB": ("NetIncomeLoss", "2026-01-01", 967_478_000., "2025-01-01", 818_860_000.),
    "CINF": ("NetIncomeLoss", "2026-01-01", 1_529_000_000., "2025-01-01", 595_000_000.),
    "FITB": ("NetIncomeLossAvailableToCommonStockholdersBasic", "2026-01-01", 891_000_000., "2025-01-01", 1_069_000_000.),
    "MTB": ("NetIncomeLossAvailableToCommonStockholdersBasic", "2026-01-01", 1_401_000_000., "2025-01-01", 1_226_000_000.),
    "BEN": ("NetIncomeLossAvailableToCommonStockholdersBasic", "2025-10-01", 651_900_000., "2024-10-01", 364_400_000.),
    "HBAN": ("NetIncomeLossAvailableToCommonStockholdersBasic", "2026-01-01", 1_168_000_000., "2025-01-01", 1_009_000_000.),
}


DIVIDENDS = {"AXP": ("DividendsCommonStockCash", 1_297_000_000., "2026-01-01"), "AFL": ("PaymentsOfDividends", 603_000_000., "2026-01-01"), "AIG": ("PaymentsOfDividendsCommonStock", 504_000_000., "2026-01-01"), "WRB": ("PaymentsOfDividendsCommonStock", 33_704_000., "2026-01-01"), "CINF": ("PaymentsOfDividendsCommonStock", 276_000_000., "2026-01-01"), "FITB": ("DividendsCommonStockCash", 734_000_000., "2026-01-01"), "MTB": ("PaymentsOfDividendsCommonStock", 445_000_000., "2026-01-01"), "BEN": ("PaymentsOfDividendsCommonStock", 522_800_000., "2025-10-01"), "HBAN": ("PaymentsOfDividendsCommonStock", 564_000_000., "2026-01-01")}


def _history_source(row: dict[str, Any], concept: str) -> dict[str, Any]:
    return {"source_kind": "companyfacts", "concept": f"us-gaap:{concept}", "value": float(row["val"]), "unit": "USD", "period_start": row["start"], "period_end": row["end"], "filed": row["filed"], "accession": row["accn"], "form": row["form"], "reported_vs_estimated": "reported"}


def _annual_common(facts: dict[str, Any], concept: str) -> tuple[dict[str, Any], ...]:
    rows = facts["facts"]["us-gaap"][concept]["units"]["USD"]
    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("form") not in {"10-K", "10-K/A"} or row.get("filed", "") > BATCH_33_VALUATION_DATE or not row.get("start") or not row.get("end") or not isinstance(row.get("val"), (int, float)):
            continue
        span = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
        if not 300 <= span <= 380:
            continue
        prior = selected.get(row["end"])
        if prior is None or (row.get("filed", ""), row.get("accn", "")) > (prior.get("filed", ""), prior.get("accn", "")):
            selected[row["end"]] = row
    result = tuple({"period_end": end, "value": float(selected[end]["val"]), "source": _history_source(selected[end], concept)} for end in sorted(selected)[-5:])
    if len(result) != 5:
        raise ValueError(f"{concept}: five annual periods required")
    return result


def _event_rows(ticker: str, event_root: Path) -> list[dict[str, Any]]:
    if ticker not in {"AXP", "FITB", "MTB", "BEN"}:
        return []
    root = Path(event_root) / ticker
    receipt = json.loads((root / "source-receipt.json").read_text())
    document = root / receipt["document"]
    if receipt.get("schema_version") != "FINSIGHT-BATCH-33-EVENT-SOURCE-1" or receipt.get("filed", "") > BATCH_33_VALUATION_DATE or hashlib.sha256(document.read_bytes()).hexdigest() != receipt.get("document_sha256"):
        raise ValueError(f"{ticker}: invalid event source")
    return [{"source_kind": "sec_event_filing", "accession": receipt["accession"], "filed": receipt["filed"], "period_end": receipt["report_date"], "form": receipt["form"], "source_url": receipt["url"], "document_sha256": receipt["document_sha256"], "reported_terms": receipt["reported_terms"], "treatment": receipt["treatment"], "reported_vs_estimated": "reported"}]


def _flow(structural: dict[str, Any], *, name: str, start: str, end: str, expected: float) -> dict[str, Any]:
    row = _structural_flow(structural, name=name, start=start, end=end, expected=expected)
    if row.get("filed") is None:
        row["filed"] = structural.get("filed_date")
    return row


def _transaction_narrative(ticker: str, filing: dict[str, Any], package: dict[str, Any], receipt: dict[str, Any]) -> list[dict[str, Any]]:
    terms = {
        "FITB": {"transactions": [{"acquiree": "Comerica", "close_date": "2026-02-01", "total_consideration": 12_676_000_000., "common_shares_issued_approx": 240_000_000., "common_equity_consideration": 12_056_000_000., "preferred_equity_consideration": 412_000_000.}], "h1_integration_cost": 849_000_000., "current_common_equity": 32_300_000_000., "history_scope": "partial_combination"},
        "HBAN": {"transactions": [{"acquiree": "Veritex", "close_date": "2025-10-20", "total_consideration": 1_700_000_000., "common_shares_issued": 107_000_000., "converted_award_shares": 1_000_000.}, {"acquiree": "Cadence", "close_date": "2026-02-01", "total_consideration": 8_335_000_000., "common_shares_issued": 462_000_000.}], "h1_acquisition_cost": 473_000_000., "current_common_equity": 29_743_000_000., "history_scope": "partial_combination"},
    }.get(ticker)
    if terms is None:
        return []
    primary_name = package.get("primary_document")
    primary = next((item for item in package.get("files", []) if item.get("local_path") == primary_name), None)
    if not isinstance(primary, dict) or not primary.get("sha256") or not primary.get("source_url"):
        raise ValueError(f"{ticker}: transaction narrative provenance unavailable")
    return [{"source_kind": "controlling_filing_reported_terms", "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "source_url": primary["source_url"], "document_sha256": primary["sha256"], "package_manifest_sha256": receipt["package_manifest_sha256"], "reported_terms": terms, "treatment": "The current balance sheet and share count anchor the combined object; historical earnings are diagnostic and the modeled ROE is explicitly a partial-combination FinSight scenario.", "reported_vs_estimated": "reported_terms_with_governed_treatment"}]


def _equity_context(ticker: str, structural: dict[str, Any], policy: EquityPolicy) -> list[dict[str, Any]]:
    rows = [_point(structural, name="StockholdersEquity", expected=policy.total_equity[0], period_end=policy.begin_period), _point(structural, name="StockholdersEquity", expected=policy.total_equity[1], period_end=policy.period)]
    if policy.preferred[0] or policy.preferred[1]:
        if ticker == "AXP":
            rows.extend((_point_unit(structural, "PreferredStockSharesOutstanding", 1_600., policy.begin_period), _point_unit(structural, "PreferredStockSharesOutstanding", 1_600., policy.period), _point(structural, name="PreferredStockValue", expected=0., period_end=policy.period)))
        else:
            rows.extend((_point(structural, name="PreferredStockValue", expected=policy.preferred[0], period_end=policy.begin_period), _point(structural, name="PreferredStockValue", expected=policy.preferred[1], period_end=policy.period)))
    concept, current_start, current_value, prior_start, prior_value = EARNINGS[ticker]
    rows.extend((_flow(structural, name=concept, start=current_start, end=policy.period, expected=current_value), _flow(structural, name=concept, start=prior_start, end="2025-06-30", expected=prior_value)))
    dividend_concept, dividend_value, dividend_start = DIVIDENDS[ticker]
    rows.append(_flow(structural, name=dividend_concept, start=dividend_start, end=policy.period, expected=dividend_value))
    weighted = policy.shares[0]
    weighted_start = current_start
    if ticker in {"FITB", "HBAN"}:
        weighted_start = "2026-04-01"
    rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=weighted, period_start=weighted_start, period_end=policy.period))
    current_share_dates = {"AXP": "2026-07-14", "AFL": "2026-07-28", "AIG": "2026-07-31", "WRB": "2026-07-27", "CINF": "2026-07-22", "FITB": "2026-07-31", "MTB": "2026-07-31", "BEN": "2026-07-22", "HBAN": "2026-06-30"}
    rows.append(_share_point(structural, expected=policy.shares[2], end=current_share_dates[ticker]))
    claim_specs = {"AFL": (("LiabilityForUnpaidClaimsAndClaimsAdjustmentExpenseNet", 553_000_000.),), "AIG": (("LiabilityForClaimsAndClaimsAdjustmentExpense", 69_852_000_000.), ("LiabilityForUnpaidClaimsAndClaimsAdjustmentExpenseNet", 41_994_000_000.)), "WRB": (("LiabilityForClaimsAndClaimsAdjustmentExpense", 23_182_240_000.), ("LiabilityForUnpaidClaimsAndClaimsAdjustmentExpenseNet", 19_745_833_000.)), "CINF": (("LiabilityForClaimsAndClaimsAdjustmentExpense", 12_479_000_000.),)}
    rows.extend(_point(structural, name=name, expected=value, period_end=policy.period) for name, value in claim_specs.get(ticker, ()))
    if ticker == "BEN":
        rows.extend((_point(structural, name="MinorityInterest", expected=1_181_700_000., period_end=policy.period), _point(structural, name="TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests", expected=1_480_800_000., period_end=policy.period), _point(structural, name="PreferredStockValue", expected=0., period_end=policy.period)))
    if ticker == "HBAN":
        rows.append(_point(structural, name="MinorityInterest", expected=41_000_000., period_end=policy.period))
    transaction_specs = {"FITB": (("BusinessCombinationConsiderationTransferred1", 12_676_000_000., "2026-02-01", "2026-02-01", True), ("BusinessCombinationConsiderationTransferredEquityInterestsIssuedAndIssuable", 12_056_000_000., "2026-02-01", "2026-02-01", True), ("BusinessCombinationIntegrationRelatedCosts", 849_000_000., "2026-01-01", "2026-06-30", True)), "HBAN": (("BusinessCombinationConsiderationTransferred1", 1_700_000_000., "2025-10-20", "2025-10-20", True), ("BusinessCombinationConsiderationTransferred1", 8_335_000_000., "2026-02-01", "2026-02-01", True), ("StockIssuedDuringPeriodSharesAcquisitions", 462_000_000., "2026-02-01", "2026-02-01", True), ("BusinessCombinationAcquisitionRelatedCosts", 473_000_000., "2026-01-01", "2026-06-30", True))}
    rows.extend(_fact(structural, *spec) for spec in transaction_specs.get(ticker, ()))
    return rows


def _ri_result(ticker: str, policy: EquityPolicy, facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], package: dict[str, Any], receipt: dict[str, Any], event_root: Path) -> dict[str, Any]:
    concept, current_start, current_value, prior_start, prior_value = EARNINGS[ticker]
    annual = _annual_common(facts, concept)
    latest = annual[-1]
    current_source = _flow(structural, name=concept, start=current_start, end=policy.period, expected=current_value)
    prior_source = _flow(structural, name=concept, start=prior_start, end="2025-06-30", expected=prior_value)
    ttm = latest["value"] + current_value - prior_value
    observations = [HistoryObservation("annual", row["period_end"], int(row["period_end"][:4]), row["value"], "USD", "reported annual common/parent earnings", (row["source"],)) for row in annual]
    observations.append(HistoryObservation("operating_ttm", policy.period, None, ttm, "USD", "latest FY + current YTD - prior YTD common/parent earnings", (latest["source"], current_source, prior_source)))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "financial_equity_residual_income", BATCH_33_VALUATION_DATE, tuple(row["period_end"] for row in annual), (metric,), True, "reported_and_company_history")
    begin_common = policy.total_equity[0] - policy.preferred[0]
    end_common = policy.total_equity[1] - policy.preferred[1]
    average_common = end_common if ticker in {"FITB", "HBAN"} else (begin_common + end_common) / 2
    rows, traces, multiples = [], {}, []
    for index, name in enumerate(("bear", "base", "bull")):
        trace = residual_income_valuation(book_value_per_share=end_common / policy.shares[index], current_roe=policy.current_roe[index], cost_of_equity=policy.cost_of_equity[index], current_payout_ratio=policy.payout[index], terminal_roe=policy.terminal_roe[index], terminal_growth=policy.terminal_growth[index], years=FORECAST_YEARS)
        raw = float(trace["intrinsic_value"])
        multiple = raw * policy.shares[index] / ttm
        rows.append({"name": name, "conditional_value_per_share": raw, "raw_value_per_share": raw, "normalized_common_earnings": policy.current_roe[index] * average_common, "book_value_per_share": end_common / policy.shares[index], "current_roe": policy.current_roe[index], "current_payout_ratio": policy.payout[index], "cost_of_equity": policy.cost_of_equity[index], "terminal_roe": policy.terminal_roe[index], "terminal_growth": policy.terminal_growth[index], "earnings_multiple": multiple, "shares": policy.shares[index], "limited_liability_floor_applied": False})
        traces[name] = trace
        multiples.append(multiple)
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid residual-income range")
    reasons = ("PROVISIONAL_BANK_CAPITAL_RANGE", "SPECIALIST_MODEL_UNCERTAINTY") if ticker in {"AXP", "FITB", "MTB", "HBAN"} else ("CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    normalization_reason = {"AXP": "Credit-cycle and card-network durability stress reported TTM ROE.", "AFL": "Japan/US mix, FX, and claims normalize reported TTM ROE.", "AIG": "The bear ROE explicitly preserves the effect of the reported negative 2024 earnings year and reserve/runoff volatility.", "WRB": "Underwriting/catastrophe cycle and reserve development normalize reported TTM ROE.", "CINF": "The bear ROE explicitly preserves the effect of the reported negative 2022 catastrophe/investment year.", "FITB": "Post-Comerica current equity anchors a partial-combination ROE; pre-close history is diagnostic only.", "MTB": "Credit/deposit mix and securities marks normalize reported TTM ROE.", "BEN": "AUM/flow and fee compression normalize reported TTM ROE.", "HBAN": "Post-Veritex/Cadence current equity anchors a partial-combination ROE; legacy history is diagnostic only."}[ticker]
    assumptions = {**profile.public_metadata(), "forecast_years": FORECAST_YEARS, "normalization_basis": "reported_common_equity_with_governed_history_bounded_roe", "assumption_source_mix": "reported_common_equity_earnings_dividends_and_finsight_policy", "normalized_common_earnings": tuple(row["normalized_common_earnings"] for row in rows), "earnings_multiples": tuple(multiples), "shares": policy.shares, "beginning_common_equity": begin_common, "ending_common_equity": end_common, "average_common_equity": average_common, "equity_anchor_method": "current_post_close_common_equity" if ticker in {"FITB", "HBAN"} else "beginning_ending_average_common_equity", "current_roe": policy.current_roe, "current_payout_ratio": policy.payout, "cost_of_equity": policy.cost_of_equity, "terminal_roe": policy.terminal_roe, "terminal_growth": policy.terminal_growth, "roe_scenario_bridge": {"reported_ttm_common_earnings": ttm, "reported_ttm_roe": ttm / average_common, "reported_history_annual_plus_ttm_range": (metric.low, metric.base, metric.high), "modeled_roe": policy.current_roe, "classification": "finsight_assumption_bounded_by_reported_history_and_current_equity", "normalization_reason": normalization_reason}, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "equity_floor_basis": "not applied", "regulatory_capital_treatment": "Current exact capital refinement is not in structural XBRL; the result is capped at Conditional Low rather than substituting zero.", "calculator_calibration": "Calculator varies normalized common earnings and the residual-income-implied multiple around the exact base.", "invalidation": policy.invalidation}
    if ticker == "AXP":
        assumptions["preferred_event_treatment"] = {"series_d_quarter_end_claim": 1_600_000_000., "series_e_cutoff_issuance": 1_600_000_000., "series_d_redemption_completed_at_cutoff": False, "common_equity_effect": 0., "treatment": "New cash and preferred equity offset; both Series D and E remain claims at cutoff, while reported common equity stays total equity less the pre-existing Series D claim."}
    if ticker == "FITB":
        assumptions["note_exchange_treatment"] = {"principal": 1_272_791_000., "new_principal_created": False, "treatment": "Equal-principal registration exchange is not a second debt claim."}
        assumptions["combination_treatment"] = {"acquiree": "Comerica", "close_date": "2026-02-01", "total_consideration": 12_676_000_000., "common_shares_issued_approx": 240_000_000., "h1_integration_cost": 849_000_000., "history_scope": "partial_combination", "release_condition": "Requires complete post-Comerica annual earnings and regulatory-capital history before Pass."}
    if ticker == "MTB":
        assumptions["preferred_event_treatment"] = {"quarter_end_total_equity": 27_946_000_000., "quarter_end_preferred_equity": 2_434_000_000., "series_l_cutoff_issuance": 600_000_000., "cutoff_total_equity": 28_546_000_000., "cutoff_preferred_equity": 3_034_000_000., "ending_common_equity": 25_512_000_000., "annual_preferred_dividend": 39_750_000., "treatment": "New cash and preferred equity offset, so common book is unchanged; future common earnings remain sensitive to the added preferred dividend."}
    if ticker == "BEN":
        assumptions["client_and_refinancing_treatment"] = {"client_assets_as_issuer_cash": False, "temporary_equity": 1_480_800_000., "nci": 1_181_700_000., "new_notes": 750_000_000., "revolver_repayment": 700_000_000.}
    if ticker == "HBAN":
        assumptions["combination_treatment"] = {"transactions": (("Veritex", "2025-10-20", 1_700_000_000., 108_000_000.), ("Cadence", "2026-02-01", 8_335_000_000., 462_000_000.)), "h1_acquisition_cost": 473_000_000., "history_scope": "partial_combination", "release_condition": "Requires complete post-Veritex/Cadence annual earnings and regulatory-capital history before Pass."}
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_33_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported common equity", end_common, AssumptionClassification.REPORTED, "Current total equity less separately modeled preferred equity supplies the opening anchor."), BaselineAssumption("company earnings history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Five aligned annual periods plus current TTM anchor the ROE range.")), warnings=(policy.warning, policy.invalidation), confidence_reasons=reasons, calculator_link=f"/api/us-valuations/{ticker}/calculator")
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_33_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_common_earnings": ttm, "beginning_total_equity": policy.total_equity[0], "ending_total_equity": policy.total_equity[1], "beginning_preferred_equity": policy.preferred[0], "ending_preferred_equity": policy.preferred[1], "beginning_common_equity": begin_common, "ending_common_equity": end_common}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "common_earnings_reconstruction": {"latest_fy": latest, "current_ytd": current_source, "prior_ytd": prior_source, "ttm": ttm}, "company_history_profile": profile.as_private_dict(), "equity_model_context": _equity_context(ticker, structural, policy), "event_sources": [*_event_rows(ticker, event_root), *_transaction_narrative(ticker, filing, package, receipt)], "residual_income_trace": {"states": traces, "clean_surplus_ddm_is_reconciliation_not_independent_evidence": True}, "bridge_treatment": "Equity-level model: deposits, card funding, policy/claim reserves, reinsurance balances, investments, client assets, and debt remain inside common earnings/equity and are never EV-bridged.", "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False, "selection_basis": "source receipt report date plus exact fact periods"}}, "warning": policy.warning, "baseline": baseline.as_private_dict()}


def _mrsh_result(submissions: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any]) -> dict[str, Any]:
    normalizer = _normalizer(submissions, facts)
    flows = {name: normalizer.ttm_flow(name) for name in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    current_cash = cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]), capital_expenditures=float(flows["capital_expenditures"]["value"]), spectrum_investment=0., interest_expense=abs(float(flows["interest_expense"]["value"])), tax_rate=tax_rate)
    annual = _annual_cash_with_losses(normalizer)[2]
    sources = [dict(source) for flow in flows.values() for source in flow.get("sources", [])]
    revenue = float(flows["revenue"]["value"])
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=revenue, ttm_cash_fcff=current_cash, ttm_period_end="2026-06-30", ttm_sources=sources, valuation_date=BATCH_33_VALUATION_DATE)
    cash_metric = profile.metric("cash_conversion_margin")
    margins = (cash_metric.low, cash_metric.base, cash_metric.high)
    growth, wacc, terminal = (.03, .05, .07), (.105, .09, .08), (.01, .02, .025)
    shares = (484_000_000., 480_600_000., 477_211_268.)
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(revenue * margins[index], growth[index], terminal[index], wacc[index], 1_700_000_000., 20_561_000_000., 0., 250_000_000., shares[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "conditional_value_per_share": raw, "raw_value_per_share": raw, "starting_cash_fcff": state.cash_fcff, "cash_conversion_margin": margins[index], "growth": growth[index], "wacc": wacc[index], "terminal_growth": terminal[index], "cash_and_investments": 1_700_000_000., "debt_and_finance_leases": 20_561_000_000., "other_equity_claims": 250_000_000., "shares": shares[index], "limited_liability_floor_applied": False})
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="High", source_cap="High", reasons=())
    warning = "Source-bounded Low insurance-broker operating baseline. Five-year owner-cash history, issuer cash, complete current/noncurrent debt, NCI, client-fund exclusion, ordinary acquisitions, and shares reconcile."
    invalidation = "Invalidate if organic/renewal cash conversion, acquisitions, debt, client-fund segregation, NCI, or diluted shares changes materially."
    assumptions = {**profile.public_metadata(), "forecast_years": 8, "cash_conversion_margin": margins, "growth": growth, "wacc": wacc, "terminal_growth": terminal, "shares": shares, "equity_floor_basis": "not applied", "calculator_calibration": "Exact faded-cash base.", "invalidation": invalidation, "client_funds_treatment": {"reported_restricted_cash": 12_203_000_000., "included_as_issuer_cash": False, "treatment": "Fiduciary/client restricted cash is excluded from surplus cash."}, "acquisition_treatment": {"h1_acquisition_cash": 129_000_000., "treatment": "Ordinary-sized completed acquisitions are consolidated; no future acquisition growth is invented."}}
    baseline = BaselineValuation(ticker="MRSH", method="insurance_broker_cash_faded_fcff", method_version=BATCH_33_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE, key_assumptions=(BaselineAssumption("company cash history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Five annual periods plus current TTM anchor cash conversion."),), warnings=(warning, invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link="/api/us-valuations/MRSH/calculator")
    context = [_point(structural, name="CashAndCashEquivalentsAtCarryingValue", expected=1_700_000_000., period_end="2026-06-30"), _point(structural, name="DebtCurrent", expected=1_670_000_000., period_end="2026-06-30"), _point(structural, name="LongTermDebtNoncurrent", expected=18_891_000_000., period_end="2026-06-30"), _point(structural, name="LongTermDebt", expected=19_537_000_000., period_end="2026-06-30"), _point(structural, name="MinorityInterest", expected=250_000_000., period_end="2026-06-30"), _point(structural, name="RestrictedCashAndCashEquivalentsAtCarryingValue", expected=12_203_000_000., period_end="2026-06-30"), _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=484_000_000., period_start="2026-01-01", period_end="2026-06-30"), _share_point(structural, expected=477_211_268., end="2026-07-16"), _point(structural, name="PreferredStockValue", expected=0., period_end="2026-06-30"), _flow(structural, name="PaymentsToAcquireBusinessesNetOfCashAcquired", start="2026-01-01", end="2026-06-30", expected=129_000_000.)]
    context[3]["used_in_arithmetic"] = False
    context[3]["coverage_role"] = "diagnostic_overlap_total_excludes_short_term_borrowings"
    context[5]["used_in_arithmetic"] = False
    context[5]["coverage_role"] = "excluded_fiduciary_client_cash"
    return {"ticker": "MRSH", "method": baseline.method, "model_version": BATCH_33_HISTORY_VERSION, "availability_type": "available", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": revenue, "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": flows["interest_expense"]["value"], "tax_rate": tax_rate, "ttm_cash_fcff": current_cash}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": list(annual), "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_sources": context, "bridge_reconciliation": {"cash_and_investments": (1_700_000_000.,) * 3, "debt_and_finance_leases": 20_561_000_000., "debt_formula": "$1.670B current debt plus $18.891B noncurrent debt; the $19.537B long-term total overlaps and excludes $1.024B short-term borrowings.", "other_equity_claims": (250_000_000.,) * 3, "shares": shares}, "model_trace": {"forecast_years": 8, "states": traces}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def build_batch_33_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_33_TICKERS:
        raise ValueError(ticker)
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    package = json.loads((Path(structural_root) / ticker / "package-manifest.json").read_text())
    receipt = json.loads((Path(structural_root) / ticker / "source-receipt.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural["source_accession"] != filing["accession"] or structural["report_date"] != filing["period_end"]:
        raise ValueError(f"{ticker}: controlling source mismatch")
    return _mrsh_result(submissions, facts, structural, filing) if ticker == "MRSH" else _ri_result(ticker, RI[ticker], facts, structural, filing, package, receipt, event_root)


if set(RI) | {"MRSH"} != set(BATCH_33_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_33_TICKERS):
    raise RuntimeError("Batch 33 policy mismatch")
