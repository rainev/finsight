"""History-backed resource-cycle baselines for controlled Universe Reset Batch 41."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .baseline import AvailabilityType, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling
from .batch_08_history import _annual_cash_with_losses
from .batch_35_history import _instant
from .batch_40_history import _latest_shares
from .batch_41 import BATCH_41_MANIFEST, BATCH_41_TICKERS, BATCH_41_VALUATION_DATE
from .batch_41_sources import verify_source_bundle
from .history import HISTORY_POLICY_VERSION, build_cash_fcff_history_profile, summarize_history_metric
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_41_HISTORY_VERSION = "BATCH-41-HISTORY-1.0"
WITHHELD_TICKERS = frozenset({"APD", "IFF", "IP"})
CONDITIONAL_TICKERS = frozenset(set(BATCH_41_TICKERS) - WITHHELD_TICKERS)
PASS_TICKERS = frozenset()
COMPARABLE_FROM = {"BALL": "2025-01-01", "IP": "2025-01-01", "PKG": "2025-01-01"}
POLICY = {
    "AVY": {"growth": (-0.02, 0.025, 0.05), "wacc": (0.105, 0.09, 0.08), "terminal": (0.0, 0.015, 0.02), "warning": "Conditional Low materials-science FCFF baseline. Restructuring, acquisition/divestiture mix, RFID adoption, input costs and policy-only share sensitivity remain material."},
    "BALL": {"growth": (-0.03, 0.015, 0.045), "wacc": (0.115, 0.10, 0.09), "terminal": (-0.005, 0.01, 0.018), "warning": "Conditional Low post-aerospace packaging FCFF baseline. Only current packaging history governs the range; contractual pass-throughs, volumes, debt and buyback execution remain material."},
    "ECL": {"growth": (-0.01, 0.03, 0.06), "wacc": (0.105, 0.09, 0.08), "terminal": (0.0, 0.015, 0.02), "warning": "Conditional Low specialty-chemicals/services FCFF baseline. CoolIT closed after the balance date; financing is already in debt and cash, while the acquired operating asset is carried at a bounded cost-based overlay until comparable cash history exists."},
    "EQT": {"growth": (-0.06, 0.0, 0.045), "wacc": (0.12, 0.10, 0.085), "terminal": (-0.01, 0.005, 0.015), "warning": "Conditional Low natural-gas resource-cycle FCFF baseline. Commodity and hedge realization, Equitrans integration, gathering economics and the cutoff Blackline acquisition remain material."},
    "HAL": {"growth": (-0.05, 0.01, 0.045), "wacc": (0.115, 0.095, 0.085), "terminal": (-0.005, 0.01, 0.018), "warning": "Conditional Low oilfield-services cycle FCFF baseline. Activity, pricing, international mix, capex, legal exposure and policy-only share sensitivity remain material."},
    "IP": {"growth": (-0.04, 0.01, 0.04), "wacc": (0.12, 0.105, 0.095), "terminal": (-0.01, 0.005, 0.015), "warning": "Conditional Low post-DS-Smith packaging FCFF baseline. Only current combined-company cash history governs the range; integration, mill actions, separation costs, debt and cycle margins remain material."},
    "NUE": {"growth": (-0.07, 0.0, 0.04), "wacc": (0.12, 0.10, 0.085), "terminal": (-0.015, 0.005, 0.015), "warning": "Conditional Low steel-cycle FCFF baseline. Through-cycle margins, working capital, major project capex, NCI and buyback execution remain material."},
    "PKG": {"growth": (-0.04, 0.015, 0.045), "wacc": (0.115, 0.10, 0.09), "terminal": (-0.005, 0.01, 0.018), "warning": "Conditional Low packaging-cycle FCFF baseline. The current object includes Greif; integration, Wallula restructuring, fiber/freight costs, debt and maintenance outages remain material. A 25-year Valdosta minimum-volume shortfall contract starts in 2028, but its annual amount is unquantified."},
}
EVENT_TREATMENTS = {
    "APD": "Accepted: the June 30 project exits create up to $925M of future cash settlements. The controlling 10-Q includes the impairment, but the unpaid cash obligation remains a valuation blocker.",
    "AVY": "The July earnings release is superseded by the controlling 10-Q. Completed first-half buybacks affect only the current reported share count; no future repurchase is assumed.",
    "BALL": "The same-day earnings release is superseded by the controlling 10-Q. The announced 2026 capital return target is not treated as executed future repurchases.",
    "ECL": "Accepted: CoolIT closed July 2 for $4.75B. June debt and cash already include its financing; post-close cash and a bounded acquired-asset overlay are modeled once.",
    "EQT": "Accepted: Blackline closed July 21 for approximately $77M funded by the revolver, after a $115M debt repayment. The at-par exchanges are recorded as base-value-neutral; purchase price is not treated as intrinsic value.",
    "HAL": "The July earnings release is superseded by the controlling 10-Q. InformatiQ and the multi-year Aramco well contracts are retained as qualitative current-object uncertainty because no source-bounded consideration or contract cash schedule is reported.",
    "IFF": "Accepted as current standalone context: Food Ingredients is classified as discontinued operations but remains pending sale. No proceeds, debt reduction or buyback is assumed before closing.",
    "IP": "The July operating release is superseded by the controlling 10-Q. Current statements include DS Smith, NORPAC and Delmarva; pending separation and mill actions remain warnings.",
    "NUE": "The July release is superseded by the controlling 10-Q. Completed buybacks are reflected only through the cutoff-safe share count; future repurchases are not assumed.",
    "PKG": "The July release is superseded by the controlling 10-Q. Greif and current restructuring charges are already in the current-company statements.",
}


def _events(ticker: str, root: Path, source_manifest_sha256: str) -> dict:
    path = root / ticker / "inventory.json"
    rows = json.loads(path.read_text())
    if not rows or any(row.get("filed", "") > BATCH_41_VALUATION_DATE for row in rows):
        raise ValueError(f"{ticker}: invalid event inventory")
    documents = []
    for row in rows:
        for document in row.get("documents", []):
            document_path = Path(document["path"])
            if not document_path.is_absolute():
                document_path = root.parent.parent / document_path
            if not document_path.exists() or hashlib.sha256(document_path.read_bytes()).hexdigest() != document.get("sha256"):
                raise ValueError(f"{ticker}: event hash mismatch")
            documents.append(document)
    return {
        "source_kind": "sec_event_screening",
        "decision": "accepted_context",
        "screened_filings": rows,
        "documents": documents,
        "inventory_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_manifest_sha256": source_manifest_sha256,
        "treatment": EVENT_TREATMENTS[ticker],
        "reported_vs_estimated": "reported_and_screened",
    }


def _point_optional(structural: dict, names: tuple[str, ...], period: str) -> dict:
    try:
        return _instant(structural, names, period)
    except ValueError:
        return {"source_kind": "statement_scope_check", "concepts_checked": names, "period_end": period, "value": 0.0, "unit": "USD", "reported_vs_estimated": "source_bounded_absence_check"}


def _sum_dimensional_points(structural: dict, name: str, period: str) -> dict:
    rows = [row for row in structural.get("facts", []) if row.get("local_name") == name and row.get("period_start") is None and row.get("period_end") == period and row.get("unit") == "USD" and isinstance(row.get("value"), (int, float))]
    if not rows:
        raise ValueError(f"{name} {period}: fact absent")
    selected = []
    seen_dimensions = set()
    for row in rows:
        dimensions = tuple(tuple(item) for item in row.get("dimensions", []))
        if dimensions in seen_dimensions:
            continue
        seen_dimensions.add(dimensions)
        selected.append(row)
    return {"source_kind": "structural_dimensional_sum", "concept": name, "period_end": period, "unit": "USD", "value": sum(float(row["value"]) for row in selected), "sources": selected, "reported_vs_estimated": "reported_components"}


def _apd_debt(structural: dict, period: str) -> dict:
    long_rows = [row for row in structural.get("facts", []) if row.get("local_name") == "LongTermDebtAndCapitalLeaseObligations" and row.get("period_start") is None and row.get("period_end") == period and row.get("unit") == "USD" and isinstance(row.get("value"), (int, float)) and any("RelatedPartyTransactionsByRelatedPartyAxis" in axis for axis, _ in row.get("dimensions", [])) and not any("ConsolidatedEntitiesAxis" in axis for axis, _ in row.get("dimensions", []))]
    if len(long_rows) != 2:
        raise ValueError("APD: related/nonrelated long-term debt scope unresolved")
    current = _instant(structural, ("LongTermDebtAndCapitalLeaseObligationsCurrent",), period)
    short = _instant(structural, ("ShortTermBorrowings",), period)
    return {"source_kind": "structural_debt_reconciliation", "period_end": period, "unit": "USD", "value": sum(float(row["value"]) for row in long_rows) + current["value"] + short["value"], "components": [*long_rows, current, short], "reported_vs_estimated": "reported_components", "treatment": "Related and nonrelated long-term balances plus current maturities and short-term borrowings; the dimensional VIE subtotal is not added again."}


def _dimensional_flow(structural: dict, name: str, start: str, end: str) -> dict:
    rows = [row for row in structural.get("facts", []) if row.get("local_name") == name and row.get("period_start") == start and row.get("period_end") == end and row.get("unit") == "USD" and isinstance(row.get("value"), (int, float)) and row.get("dimensions")]
    if len(rows) != 1:
        raise ValueError(f"{name} {start}/{end}: exact dimensional flow unresolved")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural.get("source_accession"), "filed": structural.get("filed_date"), "form": structural.get("form"), "period_start": start, "period_end": end, "concept": row.get("qname"), "unit": row.get("unit"), "value": float(row["value"]), "dimensions": row.get("dimensions"), "reported_vs_estimated": "reported"}


def _bridge(ticker: str, structural: dict, period: str) -> dict:
    cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), period)
    sources = [cash]
    investments = 0.0
    claims = 0.0
    overlay = (0.0, 0.0, 0.0)
    event_debt = 0.0
    if ticker == "AVY":
        current = _point_optional(structural, ("DebtSecuritiesAvailableForSaleExcludingAccruedInterest",), period)
        noncurrent = _point_optional(structural, ("DebtSecuritiesAvailableForSaleExcludingAccruedInterestNoncurrent",), period)
        debt_current = _instant(structural, ("DebtCurrent",), period)
        debt_long = _instant(structural, ("LongTermDebtAndCapitalLeaseObligations",), period)
        investments = current["value"] + noncurrent["value"]
        retirement = _instant(structural, ("LongTermRetirementBenefitsAndOtherLiabilities",), period)
        restructuring = _instant(structural, ("RestructuringReserve",), period)
        debt = debt_current["value"] + debt_long["value"]
        claims = restructuring["value"]
        sources += [current, noncurrent, debt_current, debt_long, retirement, restructuring]
    elif ticker == "BALL":
        debt_row = _instant(structural, ("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",), period)
        nci = _point_optional(structural, ("MinorityInterest",), period)
        pension = _instant(structural, ("DefinedBenefitPensionPlanCurrentAndNoncurrentLiabilities",), period)
        retiree = _instant(structural, ("PostemploymentBenefitsLiabilityNoncurrent",), period)
        debt, claims = debt_row["value"], nci["value"] + pension["value"] + retiree["value"]
        sources += [debt_row, nci, pension, retiree]
    elif ticker == "ECL":
        debt_row = _instant(structural, ("DebtAndCapitalLeaseObligations",), period)
        nci = _point_optional(structural, ("MinorityInterest",), period)
        purchase_price = 4_750_000_000.0
        scenario_cash = tuple(cash["value"] - purchase_price * factor for factor in (1.05, 1.0, 0.95))
        cash = {**cash, "value": scenario_cash[1], "formula": "June cash less July 2 CoolIT cash consideration", "components": [cash, {"source_kind": "controlling_filing_subsequent_event", "value": purchase_price, "unit": "USD", "period_end": "2026-07-02", "treatment": "completed cash acquisition; exact final settlement was not reported"}]}
        overlay = tuple(purchase_price * factor for factor in (0.75, 1.0, 1.25))
        pension_liability = _instant(structural, ("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",), period)
        pension_assets = _instant(structural, ("DefinedBenefitPlanAssetsForPlanBenefitsNoncurrent",), period)
        pension_deficit = max(0.0, pension_liability["value"] - pension_assets["value"])
        debt, claims = debt_row["value"], nci["value"] + pension_deficit
        sources += [debt_row, nci, pension_liability, pension_assets]
    elif ticker == "EQT":
        debt_row = _instant(structural, ("LongTermDebt",), period)
        nci = _instant(structural, ("MinorityInterest",), period)
        debt, claims = debt_row["value"], nci["value"]
        sources += [debt_row, nci]
    elif ticker == "HAL":
        debt_row = _instant(structural, ("LongTermDebt",), period)
        debt_current = _instant(structural, ("LongTermDebtCurrent",), period)
        nci = _point_optional(structural, ("MinorityInterest",), period)
        debt, claims = debt_row["value"] + debt_current["value"], nci["value"]
        sources += [debt_row, debt_current, nci]
    elif ticker == "IP":
        debt_row = _instant(structural, ("DebtAndCapitalLeaseObligations",), period)
        debt = debt_row["value"]
        sources.append(debt_row)
    elif ticker == "NUE":
        short = _instant(structural, ("ShortTermBorrowings",), period)
        current = _instant(structural, ("LongTermDebtAndCapitalLeaseObligationsCurrent",), period)
        long = _instant(structural, ("LongTermDebtAndCapitalLeaseObligations",), period)
        short_investments = _instant(structural, ("ShortTermInvestments",), period)
        nci = _instant(structural, ("MinorityInterest",), period)
        debt = short["value"] + current["value"] + long["value"]
        investments, claims = short_investments["value"], nci["value"]
        sources += [short, current, long, short_investments, nci]
    elif ticker == "PKG":
        current_investments = _instant(structural, ("AvailableForSaleSecuritiesDebtSecuritiesCurrent",), period)
        noncurrent_investments = _instant(structural, ("AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",), period)
        long = _instant(structural, ("LongTermDebtNoncurrent",), period)
        lease_current = _instant(structural, ("FinanceLeaseLiabilityCurrent",), period)
        lease_noncurrent = _instant(structural, ("FinanceLeaseLiabilityNoncurrent",), period)
        investments = current_investments["value"] + noncurrent_investments["value"]
        pension = _instant(structural, ("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",), period)
        build_to_suit = {"source_kind": "controlling_filing_note", "concept": "ValdostaBuildToSuitFinancingObligation", "period_end": period, "unit": "USD", "value": 12_500_000.0, "reported_vs_estimated": "reported", "treatment": "Debt-like financing obligation included once; the associated 25-year minimum-volume shortfall amount is unquantified and remains an invalidation warning."}
        debt = long["value"] + lease_current["value"] + lease_noncurrent["value"] + build_to_suit["value"]
        claims = pension["value"]
        sources += [current_investments, noncurrent_investments, long, lease_current, lease_noncurrent, pension, build_to_suit]
    else:
        raise ValueError(ticker)
    event_reconciliation = None
    commitment_schedule = None
    capex_coverage = None
    if ticker == "EQT":
        event_reconciliation = {"july_15_debt_repayment": 115_000_000.0, "july_21_acquisition_debt": 77_000_000.0, "july_21_acquired_asset_cost": 77_000_000.0, "gross_debt_change": -38_000_000.0, "net_debt_change": 0.0, "base_common_equity_effect": 0.0, "treatment": "Keep the verified June cash/debt anchor because the exact post-event cash balance is unavailable. The debt repayment and revolver-funded acquisition are recorded as at-par exchanges with zero net-debt and base common-equity effect; purchase price is not treated as acquired intrinsic value."}
        commitment_schedule = {"southgate_total_cost_range": (370_000_000.0, 430_000_000.0), "southgate_ownership": 0.472, "boost_total_cost_range": (400_000_000.0, 540_000_000.0), "boost_ownership": 0.532, "assumed_project_payment_years": (1, 2), "project_payment_timing_basis": "governed equal two-year timing because exact payment dates are not reported", "lng_vessel_lease_count": 2, "lng_vessel_total_payments_each": 295_000_000.0, "lng_vessel_start_year": 2, "lng_vessel_term_years": 10, "reported_vs_estimated": "reported total-cost ranges with governed payment timing", "conservatism": "Uses total estimated project cost as an upper-bound reserve because remaining cost is not disclosed; this may double count incurred spend and keeps the result Conditional Low."}
    if ticker == "NUE":
        capex_coverage = {"reported_h1_2026_capex": 1_232_000_000.0, "reported_fy2026_capex_guidance": 2_500_000_000.0, "implied_h2_2026_remaining": 1_268_000_000.0, "reported_ttm_capex_in_model": 2_841_000_000.0, "ttm_coverage_above_full_year_guidance": 341_000_000.0, "future_project_value_included": False, "treatment": "The model's current TTM cash anchor deducts more capex than full-year 2026 guidance, so the disclosed H2 program is covered rather than double-counted. No West Virginia/NTS/Berkeley project value is added; unreported 2027-2028 cash timing remains an invalidation condition."}
    overlay_basis = None
    if ticker == "ECL":
        overlay_basis = {"reported_agreement_price": 4_750_000_000.0, "final_settlement_reported": False, "cash_consideration_scenario_factors": (1.05, 1.0, 0.95), "asset_value_scenario_factors": (0.75, 1.0, 1.25), "reported_vs_estimated": "reported agreement price with private FinSight cash-settlement and valuation sensitivities", "treatment": "The acquired asset overlay is not a reported fair value or future FCFF forecast. It keeps the pre-close operating DCF and post-close financing bridge on one bounded current-company surface until comparable CoolIT cash history exists."}
    if ticker != "ECL":
        scenario_cash = (cash["value"], cash["value"], cash["value"])
    operating_obligation_treatment = None
    if ticker == "AVY":
        operating_obligation_treatment = {"retirement_and_other_liabilities": 427_900_000.0, "bridge_deducted": False, "reason": "The filed line combines retirement benefits with other operating liabilities and has no separable funded-status schedule. Periodic cash effects remain in OCF; opacity is retained as a Conditional warning instead of a duplicate bridge claim.", "restructuring_reserve": 19_400_000.0, "restructuring_bridge_deducted": True}
    elif ticker == "BALL":
        operating_obligation_treatment = {"defined_benefit_liability": 176_000_000.0, "retiree_medical_liability": 75_000_000.0, "bridge_deducted": True, "reason": "Only the reported period-end unfunded obligations are reserved; ordinary service/contribution cash remains in reported OCF and is not added again."}
    elif ticker == "PKG":
        operating_obligation_treatment = {"pension_and_postretirement_liability": 115_100_000.0, "bridge_deducted": True, "reason": "Only the reported period-end unfunded obligation is reserved; ordinary contribution cash remains in OCF and is not added again."}
    return {"cash": cash["value"], "scenario_cash": scenario_cash, "issuer_investments": investments, "debt": debt, "other_equity_claims": claims, "operating_obligation_treatment": operating_obligation_treatment, "event_debt": event_debt, "operating_asset_overlay": overlay, "operating_asset_overlay_basis": overlay_basis, "event_reconciliation": event_reconciliation, "commitment_schedule": commitment_schedule, "capex_coverage": capex_coverage, "sources": sources, "preferred_claim": 0.0, "preferred_treatment": "No economic preferred claim is reported in the controlling statement scope; missing facts are not treated as a reported zero."}


def _share_reconciliation(ticker: str, structural: dict, period: str, selected: dict) -> dict | None:
    if ticker not in {"BALL", "IP"}:
        return None
    issued = _instant(structural, ("CommonStockSharesIssued",), period, unit="xbrli:shares")
    treasury = _instant(structural, ("TreasuryStockCommonShares",), period, unit="xbrli:shares")
    calculated = issued["value"] - abs(treasury["value"])
    return {"selected_cover_dei_shares": selected, "period_end_issued_shares": issued, "period_end_treasury_shares": treasury, "calculated_period_end_outstanding": calculated, "difference_to_later_cover": selected["value"] - calculated, "treatment": "Use the later cutoff-safe DEI cover count. The statement-context gross share fact equals issued shares and does not subtract treasury shares."}


def _withheld(ticker: str, filing: dict, flows: dict, annual: list, profile: dict, event: dict, verification: dict, reason: str, extra: dict) -> dict:
    invalidation = "Revalue only when a source-bounded positive current-company cash base and complete material claim or discontinued-operation schedule are available."
    baseline = BaselineValuation(ticker=ticker, method="resource_cycle_enterprise_fcff", method_version=BATCH_41_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(reason, invalidation))
    return {
        "ticker": ticker,
        "method": baseline.method,
        "model_version": BATCH_41_HISTORY_VERSION,
        "availability_type": "not_available",
        "scenario_rows": [],
        "scenario_range": {"low": None, "base": None, "high": None},
        "reported_inputs": {},
        "governed_assumptions": {"history_policy_version": HISTORY_POLICY_VERSION, "history_years_used": len(annual), "forecast_years": 8, "normalization_basis": "withheld_current_company_cash_gate", "assumption_source_mix": "reported_current_and_history", "invalidation": invalidation},
        "history_reliability": None,
        "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": annual, "company_history_profile": profile, "event_sources": event, "runtime_source_verification": verification, **extra},
        "warning": reason,
        "baseline": baseline.as_private_dict(),
    }


def build_batch_41_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path):
    if ticker not in BATCH_41_TICKERS:
        raise ValueError(ticker)
    packet = Path(source_root) / ticker
    structural_packet = Path(structural_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    companyfacts = json.loads((packet / "companyfacts.json").read_text())
    source_manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((structural_packet / "structural-filing.json").read_text())
    filing = _controlling(source_manifest, submissions)
    if structural.get("source_accession") != filing["accession"] or structural.get("report_date") != filing["period_end"]:
        raise ValueError(f"{ticker}: controlling filing mismatch")
    verification = verify_source_bundle(ticker=ticker, packet=packet, structural_packet=structural_packet, structural_cache_root=Path(structural_cache_root), filing=filing)
    event = _events(ticker, Path(event_root), verification["source_manifest_sha256"])
    normalizer = _normalizer(submissions, companyfacts)
    flows = {field: normalizer.ttm_flow(field) for field in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    try:
        tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    except ValueError:
        tax_rate, tax_sources = 0.25, ({"source_kind": "finsight_policy", "value": 0.25, "reason": "current and annual effective-tax observations are not comparable enough for the shared median policy"},)
    ttm_fcff = cash_fcff_from_reported(operating_cash_flow=flows["operating_cash_flow"]["value"], capital_expenditures=flows["capital_expenditures"]["value"], spectrum_investment=0.0, interest_expense=abs(flows["interest_expense"]["value"]), tax_rate=tax_rate)
    if ticker == "AVY":
        from .batch_35_history import _period_flow
        current_software = _period_flow(structural, ("PurchaseOfSoftwareAndOtherDeferredCharges",), filing["period_end"], target_days=180)
        annualized_software = 2.0 * current_software["value"]
        ttm_fcff -= annualized_software
        flows["software_and_deferred_charges"] = {"value": annualized_software, "period_end": filing["period_end"], "method": "two_times_current_h1_source_bounded_run_rate", "current_h1": current_software, "sources": [current_software]}
    annual = list(_annual_cash_with_losses(normalizer)[2])
    comparable_from = COMPARABLE_FROM.get(ticker)
    if comparable_from:
        annual = [row for row in annual if row["period_end"] >= comparable_from]
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=flows["revenue"]["value"], ttm_cash_fcff=ttm_fcff, ttm_period_end=flows["revenue"]["period_end"], ttm_sources=[source for value in flows.values() for source in value["sources"]], valuation_date=BATCH_41_VALUATION_DATE)
    metric = profile.metric("cash_conversion_margin")
    if metric is None:
        raise ValueError(f"{ticker}: no cash history")
    if ticker == "EQT":
        annual_metric = summarize_history_metric("cash_conversion_margin", (observation for observation in metric.observations if observation.period_role == "annual"))
        if annual_metric is None:
            raise ValueError("EQT: annual cycle history absent")
        metric = annual_metric
    if ticker == "APD":
        reason = "Withheld: Air Products has negative current and median source-linked cash FCFF while project-exit cash settlements remain as high as $925M. A positive base would require separating unfinished-project economics, nonrecourse funding and future capex beyond the current evidence."
        return _withheld(ticker, filing, flows, annual, profile.as_private_dict(), event, verification, reason, {"ttm_cash_fcff": ttm_fcff, "cash_conversion_margin": {"low": metric.low, "base": metric.base, "high": metric.high}, "project_exit_cash_maximum": 925_000_000.0, "debt": _apd_debt(structural, filing["period_end"]), "noncontrolling_interest": _instant(structural, ("MinorityInterest",), filing["period_end"]), "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}})
    if ticker == "IFF":
        reason = "Withheld: IFF's income statement is recast to continuing operations, but the current cash-flow statement does not separately identify operating cash and reinvestment for the discontinued Food Ingredients/SCL disposal groups. A continuing-company FCFF base would mix economic objects."
        return _withheld(ticker, filing, flows, annual, profile.as_private_dict(), event, verification, reason, {"ttm_cash_fcff_diagnostic_only": ttm_fcff, "disposal_group_assets": _instant(structural, ("AssetsOfDisposalGroupIncludingDiscontinuedOperationCurrent",), filing["period_end"]), "disposal_group_liabilities": _sum_dimensional_points(structural, "LiabilitiesOfDisposalGroupIncludingDiscontinuedOperationCurrent", filing["period_end"]), "pending_sale_proceeds_included": False, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}})
    if ticker == "IP":
        reason = "Withheld: International Paper has positive total-company cash FCFF, but only one full post-DS-Smith year and no complete continuing/discontinued capex bridge after the GCF sale. The pending EMEA separation and mill actions leave no source-bounded comparable current-company cash base after $9.2B of debt."
        selected_share = _latest_shares(ticker, structural)
        return _withheld(ticker, filing, flows, annual, profile.as_private_dict(), event, verification, reason, {"ttm_cash_fcff_diagnostic_only": ttm_fcff, "cash_conversion_margin_diagnostic_only": {"low": metric.low, "base": metric.base, "high": metric.high}, "gcf_discontinued_cash": {"operating": _dimensional_flow(structural, "CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations", "2026-01-01", filing["period_end"]), "investing": _dimensional_flow(structural, "CashProvidedByUsedInInvestingActivitiesDiscontinuedOperations", "2026-01-01", filing["period_end"]), "complete_capex_line_available": False}, "debt": _instant(structural, ("DebtAndCapitalLeaseObligations",), filing["period_end"]), "share_reconciliation": _share_reconciliation(ticker, structural, filing["period_end"], selected_share), "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}})

    bridge = _bridge(ticker, structural, filing["period_end"])
    share = _latest_shares(ticker, structural)
    share_reconciliation = _share_reconciliation(ticker, structural, filing["period_end"], share)
    share_value = float(share["value"])
    shares = (share_value * 1.015, share_value, share_value * 0.985)
    policy = POLICY[ticker]
    revenue = flows["revenue"]["value"]
    starting = tuple(revenue * margin for margin in (metric.low, metric.base, metric.high))
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        bridge_assets = bridge["scenario_cash"][index] + bridge["issuer_investments"] + bridge["operating_asset_overlay"][index]
        commitment_pv = 0.0
        if ticker == "EQT":
            schedule = bridge["commitment_schedule"]
            southgate = tuple(value * schedule["southgate_ownership"] for value in schedule["southgate_total_cost_range"])
            boost = tuple(value * schedule["boost_ownership"] for value in schedule["boost_total_cost_range"])
            project_cost = (southgate[1] + boost[1], (sum(southgate) + sum(boost)) / 2.0, southgate[0] + boost[0])[index]
            project_pv = sum((project_cost / 2.0) / (1.0 + policy["wacc"][index]) ** year for year in schedule["assumed_project_payment_years"])
            annual_lease = schedule["lng_vessel_lease_count"] * schedule["lng_vessel_total_payments_each"] / schedule["lng_vessel_term_years"]
            lease_pv = sum(annual_lease / (1.0 + policy["wacc"][index]) ** year for year in range(schedule["lng_vessel_start_year"], schedule["lng_vessel_start_year"] + schedule["lng_vessel_term_years"]))
            commitment_pv = project_pv + lease_pv
        other_claims = bridge["other_equity_claims"] + commitment_pv
        state = EnterpriseCashFlowState(starting[index], policy["growth"][index], policy["terminal"][index], policy["wacc"][index], bridge_assets, bridge["debt"], bridge["preferred_claim"], other_claims, shares[index])
        if starting[index] <= 0:
            raw = (bridge_assets - bridge["debt"] - other_claims) / shares[index]
            trace = {"model": "zero_operating_value_bear_state", "enterprise_value": 0.0, "equity_value": bridge_assets - bridge["debt"] - other_claims, "intrinsic_value_per_share": raw, "reason": "reported history includes negative cash conversion; no positive operating value is invented"}
        else:
            trace = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
            raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": max(0.0, raw), "starting_cash_fcff": starting[index], "growth": policy["growth"][index], "wacc": policy["wacc"][index], "terminal_growth": policy["terminal"][index], "cash_and_investments": bridge_assets, "issuer_cash": bridge["scenario_cash"][index], "issuer_investments": bridge["issuer_investments"], "operating_asset_overlay": bridge["operating_asset_overlay"][index], "debt_and_finance_leases": bridge["debt"], "other_equity_claims": other_claims, "commitment_present_value": commitment_pv, "shares": shares[index], "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError(f"{ticker}: invalid FCFF range")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("RESOURCE_CYCLE_UNCERTAINTY",))
    invalidation = "Revalue if comparable cash conversion, cycle conditions, current-company scope, acquisition/project economics, debt/NCI, claims or shares leave the bounded range."
    assumptions = {**profile.public_metadata(), "forecast_years": 8, "normalization_basis": "source-linked comparable cash FCFF history", "assumption_source_mix": "reported_history_and_governed_cycle_scenarios", "cash_conversion_margin": (metric.low, metric.base, metric.high), "growth": policy["growth"], "wacc": policy["wacc"], "terminal_growth": policy["terminal"], "shares": shares, "share_sensitivity_basis": "policy-only +/-1.5%; completed buybacks are reflected only through the reported current share count", "equity_floor_basis": "bear-only limited-liability floor; raw residual retained privately", "calculator_calibration": "Exact enterprise cash-FCFF default replay.", "invalidation": invalidation}
    if ticker == "AVY":
        assumptions["software_and_deferred_charges_run_rate"] = {"current_h1_reported": 13_900_000.0, "annualized_amount": 27_800_000.0, "annualization_method": "two times current H1", "reported_vs_estimated": "FinSight estimate from reported current H1"}
    if ticker == "EQT":
        assumptions["cycle_normalization"] = "Five exact annual cash-conversion observations; current TTM is retained as a diagnostic and excluded from the scenario percentile set."
    baseline = BaselineValuation(ticker=ticker, method="resource_cycle_enterprise_fcff", method_version=BATCH_41_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(policy["warning"], invalidation))
    return {
        "ticker": ticker,
        "method": baseline.method,
        "model_version": BATCH_41_HISTORY_VERSION,
        "availability_type": "conditional_estimate",
        "scenario_rows": rows,
        "scenario_range": scenario,
        "reported_inputs": {"ttm_revenue": revenue, "ttm_cash_fcff": ttm_fcff, "share_count": share_value},
        "governed_assumptions": assumptions,
        "history_reliability": reliability.as_dict(),
        "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": annual, "tax_rate": tax_rate, "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_context": bridge, "share_reconciliation": share_reconciliation, "event_sources": event, "model_trace": {"states": traces}, "raw_scenario_rows": rows, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}},
        "warning": policy["warning"],
        "baseline": baseline.as_private_dict(),
    }


if PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_41_TICKERS):
    raise RuntimeError("Batch 41 policy mismatch")
