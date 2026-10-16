"""History-backed resource-cycle baselines for controlled Universe Reset Batch 42."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling
from .batch_08_history import _annual_cash_with_losses
from .batch_35_history import _instant, _period_flow
from .batch_40_history import _latest_shares
from .batch_42 import BATCH_42_MANIFEST, BATCH_42_TICKERS, BATCH_42_VALUATION_DATE
from .batch_42_sources import verify_source_bundle
from .history import HISTORY_POLICY_VERSION, build_cash_fcff_history_profile
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability
from .xbrl import load_concept_config


BATCH_42_HISTORY_VERSION = "BATCH-42-HISTORY-1.0"
PERIOD = "2026-06-30"
PASS_TICKERS = frozenset()
WITHHELD_TICKERS = frozenset({"EXE", "ALB"})
CONDITIONAL_TICKERS = frozenset(set(BATCH_42_TICKERS) - WITHHELD_TICKERS)

FLOW_SPEC = {
    "PPG": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestPaidNet",)},
    "SLB": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestExpense",)},
    "SHW": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("PaymentsToAcquireProductiveAssets",), "interest": ("InterestPaidNet",)},
    "CVX": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("PaymentsToAcquireProductiveAssets",), "interest": ("InterestPaidNet",)},
    "OXY": {"revenue": ("Revenues",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestPaidNet",)},
    "EOG": {"revenue": ("Revenues",), "capex": ("PaymentsToAcquireOilAndGasPropertyAndEquipment", "PaymentsToAcquireOtherPropertyPlantAndEquipment"), "interest": ("InterestExpense",)},
    "FCX": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("SegmentExpenditureAdditionToLongLivedAssets",), "annual_capex": ("PaymentsToAcquireProductiveAssets",), "interest": ("InterestIncomeExpenseNet",)},
    "CRH": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("PaymentsToAcquireProductiveAssets",), "interest": ("InterestExpenseNonoperating",), "use_default_annual": True},
    "EXE": {"revenue": ("Revenues",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestExpenseNonoperating",)},
    "ALB": {"revenue": ("Revenues",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestAndDebtExpense",)},
}

POLICY = {
    "PPG": {"growth": (-.03, .02, .045), "wacc": (.11, .095, .085), "terminal": (-.005, .01, .018), "warning": "Conditional Low coatings/materials-cycle FCFF baseline. Price/volume, acquisitions, raw materials, pensions, environmental claims and working-capital timing remain material."},
    "SLB": {"growth": (-.05, .01, .045), "wacc": (.115, .095, .085), "terminal": (-.005, .01, .018), "warning": "Conditional Low oilfield-services cycle FCFF baseline. ChampionX comparability, international activity, pricing, capex, NCI and contract execution remain material."},
    "SHW": {"growth": (-.025, .02, .045), "wacc": (.105, .09, .08), "terminal": (0., .015, .02), "warning": "Conditional Low coatings/distribution FCFF baseline. Suvinil integration, housing and industrial demand, raw materials, debt, leases and environmental claims remain material."},
    "CVX": {"growth": (-.07, 0., .04), "wacc": (.115, .095, .085), "terminal": (-.015, .005, .015), "warning": "Conditional Low integrated-energy cycle FCFF baseline. Commodity prices, Hess integration, production, capex, NCI, pensions, restricted cash and asset-sale timing remain material."},
    "OXY": {"growth": (-.08, -.005, .04), "wacc": (.125, .105, .09), "terminal": (-.02, .0025, .0125), "warning": "Conditional Low levered E&P cycle FCFF baseline. Commodity prices, CrownRock scope, preferred stock, debt, ARO, environmental claims and discontinued-operation effects remain material."},
    "EOG": {"growth": (-.07, 0., .04), "wacc": (.115, .095, .085), "terminal": (-.015, .005, .015), "warning": "Conditional Low E&P cycle FCFF baseline. Commodity prices, decline, production, oil-and-gas plus other capex, derivatives and ARO remain material."},
    "FCX": {"growth": (-.08, 0., .04), "wacc": (.12, .10, .085), "terminal": (-.02, .005, .015), "warning": "Conditional Low copper/mining cycle FCFF baseline. Copper/gold/molybdenum prices, major-project capex, NCI, closure/environmental obligations and restoration work remain material."},
    "CRH": {"growth": (-.04, .015, .045), "wacc": (.11, .095, .085), "terminal": (-.005, .01, .018), "warning": "Conditional Low construction-materials cycle FCFF baseline. Price/volume, acquisitions, debt/leases, NCI, pensions and the pending Arcosa transaction remain material."},
    "EXE": {"growth": (-.08, -.01, .04), "wacc": (.13, .11, .095), "terminal": (-.02, 0., .0125), "warning": "Conditional Low post-combination gas-producer FCFF baseline. Only current combined-company cash evidence governs the range; gas prices, hedges, decline, gathering commitments and the pending Twin Eagle deal remain material."},
}

EVENT_TREATMENTS = {
    "PPG": "The July earnings release is source context; reported acquisitions and financing are already reflected in the controlling filing and no future insurance recovery is added.",
    "SLB": "ChampionX is part of the current company and its short history keeps the model Conditional. The quarter's Tachyus acquisition is retained as context; no unreported value is added.",
    "SHW": "Suvinil is already included in current operations. Valspar amortization and restructuring remain in reported cash history; no acquisition price is added to value.",
    "CVX": "The July earnings release is reconciled to the controlling filing. Hess integration and asset-sale effects remain current-scope uncertainty; no projected synergy or future sale proceeds are added.",
    "OXY": "The two earnings filings are reconciled to the controlling 10-Q. Discontinued-operation gains are not treated as recurring FCFF; preferred and environmental claims remain explicit.",
    "EOG": "Reported derivative settlements and the future Brent-linked gas contract remain operating scenario context, not bridge assets or guaranteed future cash.",
    "FCX": "The earnings release supplies project and operating context. Current capex, Cerro Verde ownership, NCI and restoration charges are consumed once; no reserve or project NAV is added.",
    "CRH": "Arcosa and its bridge/term-loan commitments are pending at the cutoff. No purchase price, acquisition cash flow or financing is added to the current-company baseline.",
    "EXE": "Twin Eagle is signed but unclosed. The $62.5M deposit is excluded from available cash; purchase price, projected EBITDA, synergies and future financing are not added.",
    "ALB": "Ketjen's controlling-stake sale is in current statements. Talison dividend and working-capital timing are not extrapolated; the mandatory convertible is handled through diluted shares rather than a second claim deduction.",
}


def _events(ticker: str, root: Path, source_manifest_sha256: str) -> dict[str, Any]:
    path = root / ticker / "inventory.json"
    rows = json.loads(path.read_text())
    if not rows or any(row.get("filed", "") > BATCH_42_VALUATION_DATE for row in rows):
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
    return {"source_kind": "sec_event_screening", "decision": "accepted_context", "screened_filings": rows, "documents": documents, "inventory_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "source_manifest_sha256": source_manifest_sha256, "treatment": EVENT_TREATMENTS[ticker], "reported_vs_estimated": "reported_and_screened"}


def _config(ticker: str) -> dict[str, Any]:
    config = deepcopy(load_concept_config())
    spec = FLOW_SPEC[ticker]
    if not spec.get("use_default_annual"):
        config["fields"]["revenue"]["concepts"] = list(spec["revenue"])
        config["fields"]["interest_expense"]["concepts"] = list(spec["interest"])
        if ticker == "EOG":
            config["fields"]["capital_expenditures"]["concepts"] = []
            config["fields"]["capital_expenditures"]["derivations"] = [{"op": "sum", "components": [["PaymentsToAcquireOilAndGasPropertyAndEquipment"], ["PaymentsToAcquireOtherPropertyPlantAndEquipment"]]}]
        else:
            config["fields"]["capital_expenditures"]["concepts"] = list(spec.get("annual_capex", spec["capex"]))
    return config


def _flow(structural: dict[str, Any], names: tuple[str, ...], end: str) -> dict[str, Any]:
    if len(names) == 1:
        return _period_flow(structural, names, end, target_days=180)
    components = [_period_flow(structural, (name,), end, target_days=180) for name in names]
    return {"source_kind": "structural_component_sum", "accession": structural.get("source_accession"), "filed": structural.get("filed_date"), "form": structural.get("form"), "period_start": components[0]["period_start"], "period_end": end, "concept": "+".join(names), "unit": "USD", "value": sum(row["value"] for row in components), "components": components, "reported_vs_estimated": "reported_components"}


def _ttm_flows(ticker: str, normalizer, structural: dict[str, Any], tax_rate: float) -> dict[str, Any]:
    spec = FLOW_SPEC[ticker]
    fields = {}
    for field, names in (("revenue", spec["revenue"]), ("operating_cash_flow", ("NetCashProvidedByUsedInOperatingActivities",)), ("capital_expenditures", spec["capex"]), ("interest_expense", spec["interest"])):
        annual = normalizer.annual_series(field, 1)
        if not annual:
            raise ValueError(f"{ticker}: annual {field} unavailable")
        current = _flow(structural, names, PERIOD)
        prior = _flow(structural, names, "2025-06-30")
        latest = annual[-1].as_dict()
        fields[field] = {"value": annual[-1].value + current["value"] - prior["value"], "period_end": PERIOD, "method": "latest_fy_plus_current_h1_minus_prior_h1", "sources": [latest, current, prior], "latest_fy": latest, "current_h1": current, "prior_h1": prior}
    fcff = cash_fcff_from_reported(operating_cash_flow=fields["operating_cash_flow"]["value"], capital_expenditures=fields["capital_expenditures"]["value"], spectrum_investment=0., interest_expense=abs(fields["interest_expense"]["value"]), tax_rate=tax_rate)
    fields["cash_fcff"] = fcff
    return fields


def _point(structural: dict[str, Any], names: tuple[str, ...], period: str = PERIOD) -> dict[str, Any]:
    return _instant(structural, names, period)


def _latest_diluted_shares(structural: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in structural.get("facts", []) if row.get("local_name") == "WeightedAverageNumberOfDilutedSharesOutstanding" and row.get("period_start") == "2026-01-01" and row.get("period_end") == PERIOD and row.get("unit") == "xbrli:shares" and not row.get("dimensions") and isinstance(row.get("value"), (int, float))]
    values = {float(row["value"]) for row in rows}
    if len(values) != 1:
        raise ValueError("diluted share fact unresolved")
    row = rows[-1]
    return {"source_kind": "structural_xbrl", "accession": structural.get("source_accession"), "filed": structural.get("filed_date"), "form": structural.get("form"), "period_start": row["period_start"], "period_end": row["period_end"], "concept": row.get("qname"), "unit": row["unit"], "value": float(row["value"]), "reported_vs_estimated": "reported"}


def _bridge(ticker: str, structural: dict[str, Any]) -> dict[str, Any]:
    latest = _latest_shares(ticker, structural)
    diluted = _latest_diluted_shares(structural)
    share_value = latest["value"]
    claims = [0., 0., 0.]
    excluded: dict[str, Any] = {}
    if ticker == "PPG":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",)); short_investments = _point(structural, ("ShortTermInvestments",)); cash = {**cash, "value": cash["value"] + short_investments["value"], "formula": "cash plus reported short-term investments"}; debt = _point(structural, ("DebtCurrent",))["value"] + _point(structural, ("LongTermDebtNoncurrent",))["value"] + _point(structural, ("FinanceLeaseLiability",))["value"]
        nci = _point(structural, ("MinorityInterest",))["value"]; operating_stress = _point(structural, ("DefinedBenefitPensionPlanLiabilitiesNoncurrent",))["value"] + _point(structural, ("AccrualForEnvironmentalLossContingencies",))["value"]; claims = [nci + operating_stress, nci, nci]
        excluded["long_term_investments"] = _point(structural, ("LongTermInvestments",))["value"]
        excluded["operating_claim_stress"] = (operating_stress, 0., 0.)
    elif ticker == "SLB":
        cash = _point(structural, ("Cash",)); cash = {**cash, "value": cash["value"] + _point(structural, ("ShortTermInvestments",))["value"], "formula": "cash plus short-term investments"}; debt = _point(structural, ("ShortTermBorrowingsAndLongTermDebtCurrent",))["value"] + _point(structural, ("LongTermDebtNoncurrent",))["value"]
        nci = _point(structural, ("MinorityInterest",))["value"]; operating_stress = _point(structural, ("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",))["value"]; claims = [nci + operating_stress, nci, nci]; excluded["operating_claim_stress"] = (operating_stress, 0., 0.)
    elif ticker == "SHW":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",)); debt = _point(structural, ("DebtLongtermAndShorttermCombinedAmount",))["value"]
        accrued = _point(structural, ("AccruedEnvironmentalLossContingenciesCurrent",))["value"] + _point(structural, ("AccruedEnvironmentalLossContingenciesNoncurrent",))["value"]; claims = [accrued + 73_900_000., 0., 0.]; excluded["operating_claim_stress"] = (accrued + 73_900_000., 0., 0.)
    elif ticker == "CVX":
        cash = _point(structural, ("CashAndCashEquivalentsExcludingTimeDeposits",)); debt = _point(structural, ("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",))["value"]
        nci = _point(structural, ("MinorityInterest",))["value"]; operating_stress = _point(structural, ("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",))["value"]; claims = [nci + operating_stress, nci, nci]; excluded["operating_claim_stress"] = (operating_stress, 0., 0.)
        excluded["restricted_cash"] = _point(structural, ("RestrictedCashCurrent",))["value"] + _point(structural, ("RestrictedCashNoncurrent",))["value"]
    elif ticker == "OXY":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",)); debt = _point(structural, ("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",))["value"]
        fixed_claim = _point(structural, ("MinorityInterest",))["value"] + _point(structural, ("PreferredStockValue",))["value"]; operating_stress = _point(structural, ("AssetRetirementObligationCurrent",))["value"] + _point(structural, ("AssetRetirementObligationsNoncurrent",))["value"] + _point(structural, ("AccrualForEnvironmentalLossContingencies",))["value"] + _point(structural, ("EnvironmentalRemediationPossibleAdditionalLossBeyondAccruals",))["value"]; claims = [fixed_claim + operating_stress, fixed_claim, fixed_claim]; excluded["operating_claim_stress"] = (operating_stress, 0., 0.)
    elif ticker == "EOG":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",)); debt = _point(structural, ("LongTermDebtCurrent",))["value"] + _point(structural, ("LongTermDebtNoncurrent",))["value"]; operating_stress = _point(structural, ("AssetRetirementObligation",))["value"]; claims = [operating_stress, 0., 0.]; excluded["operating_claim_stress"] = (operating_stress, 0., 0.)
    elif ticker == "FCX":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",)); debt = _point(structural, ("LongTermDebt",))["value"]
        nci = _point(structural, ("MinorityInterest",))["value"]; closure = _point(structural, ("EnvironmentalAndAssetRetirementObligationsCurrent",))["value"] + _point(structural, ("EnvironmentalAndAssetRetirementObligationsNoncurrent",))["value"]; claims = [nci + closure, nci, nci]
        excluded["restricted_cash"] = _point(structural, ("RestrictedCashAndCashEquivalentsAtCarryingValue",))["value"] + _point(structural, ("RestrictedCashAndCashEquivalentsNoncurrent",))["value"]
        excluded["closure_obligation_sensitivity"] = (closure, 0., 0.)
    elif ticker == "CRH":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",)); debt = _point(structural, ("DebtCurrent",))["value"] + _point(structural, ("LongTermDebtNoncurrent",))["value"] + _point(structural, ("FinanceLeaseLiabilityCurrent",))["value"] + _point(structural, ("FinanceLeaseLiabilityNoncurrent",))["value"]
        fixed_claim = _point(structural, ("MinorityInterest",))["value"] + _point(structural, ("RedeemableNoncontrollingInterestEquityCarryingAmount",))["value"]; operating_stress = _point(structural, ("DefinedBenefitPensionPlanLiabilitiesNoncurrent",))["value"] + _point(structural, ("AssetRetirementObligationsNoncurrent",))["value"]; claims = [fixed_claim + operating_stress, fixed_claim, fixed_claim]; excluded["operating_claim_stress"] = (operating_stress, 0., 0.)
        excluded["restricted_cash"] = _point(structural, ("RestrictedCashCurrent",))["value"]
    elif ticker == "EXE":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",)); cash = {**cash, "value": cash["value"] - 62_500_000., "formula": "reported cash less paid Twin Eagle deposit"}; debt = _point(structural, ("LongTermDebtNoncurrent",))["value"]; operating_stress = _point(structural, ("AssetRetirementObligationsNoncurrent",))["value"]; claims = [operating_stress, 0., 0.]; excluded["operating_claim_stress"] = (operating_stress, 0., 0.)
        excluded["restricted_cash"] = _point(structural, ("RestrictedCashCurrent",))["value"]
    elif ticker == "ALB":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",)); debt = _point(structural, ("LongTermDebt",))["value"] + _point(structural, ("FinanceLeaseLiability",))["value"]
        nci = _point(structural, ("MinorityInterest",))["value"]; operating_stress = _point(structural, ("DefinedBenefitPensionPlanLiabilitiesNoncurrent",))["value"] + _point(structural, ("AccrualForEnvironmentalLossContingencies",))["value"]; claims = [nci + operating_stress, nci, nci]; excluded["operating_claim_stress"] = (operating_stress, 0., 0.)
        excluded["long_term_investments"] = _point(structural, ("LongTermInvestments",))["value"]
        excluded["preferred_stock_requires_conversion_reconciliation"] = _point(structural, ("PreferredStockValue",))["value"]
    else:
        raise ValueError(ticker)
    return {"cash": float(cash["value"]), "debt": float(debt), "claims": tuple(float(value) for value in claims), "latest_common_shares": latest, "h1_diluted_shares_diagnostic": diluted, "base_share_count": float(share_value), "cash_source": cash, "excluded_or_separately_treated": {**excluded, "operating_claim_policy": "Pension, environmental and ARO cash effects remain in reported OCF. Their closing balances are applied only as a bear stress to avoid a full base/bull double deduction; NCI and preferred claims remain bridge deductions in every scenario."}, "reported_vs_estimated": "reported_bridge_with_named_event_adjustments"}


def _withheld_alb(*, filing: dict[str, Any], flows: dict[str, Any], annual: tuple[dict[str, Any], ...], profile, bridge: dict[str, Any], event: dict[str, Any], verification: dict[str, Any], structural: dict[str, Any], tax_rate: float, tax_sources) -> dict[str, Any]:
    annual_margins = tuple(row["cash_fcff"] / row["revenue"]["value"] for row in annual)
    if median(annual_margins) >= 0:
        raise ValueError("ALB: annual cycle median withholding gate changed")
    reason = "Withheld: Albemarle's five-year reported cash-FCFF median remains negative. Current TTM cash is positive but is materially helped by Talison dividend and working-capital timing, while the Ketjen scope change and mandatory convertible prevent treating that one period as a through-cycle base."
    invalidation = "Revalue after a positive comparable post-Ketjen cash history separates lithium, specialties, Talison distributions, working capital, capex and mandatory-convertible dilution."
    baseline = BaselineValuation(ticker="ALB", method="lithium_specialty_resource_cycle_fcff", method_version=BATCH_42_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(reason, invalidation))
    return {"ticker": "ALB", "method": baseline.method, "model_version": BATCH_42_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {"ttm_revenue": flows["revenue"]["value"], "ttm_cash_fcff": flows["cash_fcff"]}, "governed_assumptions": {**profile.public_metadata(), "forecast_years": 8, "normalization_basis": "negative_five_year_cash_fcff_median_and_event_distorted_current_ttm", "assumption_source_mix": "reported_history_current_ttm_and_event_context", "cash_conversion_margin": annual_margins, "equity_floor_basis": "not applied", "invalidation": invalidation}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": annual, "tax_rate": tax_rate, "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_context": bridge, "event_sources": event, "runtime_source_verification": verification, "current_ttm_is_diagnostic_only": True, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": reason, "baseline": baseline.as_private_dict()}


def _withheld_exe(*, filing: dict[str, Any], flows: dict[str, Any], annual: tuple[dict[str, Any], ...], profile, bridge: dict[str, Any], event: dict[str, Any], verification: dict[str, Any], structural: dict[str, Any], tax_rate: float, tax_sources) -> dict[str, Any]:
    if profile.history_years_used != 1:
        raise ValueError("EXE: comparable-history withholding gate changed")
    reason = "Withheld: Expand Energy has only one complete annual period for the current combined company. The corrected June TTM is positive, but using it with one annual observation cannot define a defensible gas-cycle range, and the signed Twin Eagle transaction remains unclosed."
    invalidation = "Revalue after at least three comparable combined-company annual periods or an issuer-filed pro-forma cash history, with Twin Eagle closing, funding, hedges, gathering commitments and ARO reconciled."
    baseline = BaselineValuation(ticker="EXE", method="post_combination_gas_resource_cycle_fcff", method_version=BATCH_42_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(reason, invalidation))
    return {"ticker": "EXE", "method": baseline.method, "model_version": BATCH_42_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {"ttm_revenue": flows["revenue"]["value"], "ttm_cash_fcff": flows["cash_fcff"]}, "governed_assumptions": {**profile.public_metadata(), "forecast_years": 8, "normalization_basis": "one_comparable_post_combination_annual_period_is_insufficient", "assumption_source_mix": "reported_current_combined_history_and_event_context", "equity_floor_basis": "not applied", "invalidation": invalidation}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": annual, "tax_rate": tax_rate, "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_context": bridge, "event_sources": event, "runtime_source_verification": verification, "current_ttm_is_diagnostic_only": True, "twin_eagle_purchase_price_included": False, "projected_ebitda_or_synergies_included": False, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": reason, "baseline": baseline.as_private_dict()}


def build_batch_42_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_42_TICKERS:
        raise ValueError(ticker)
    packet = Path(source_root) / ticker
    structural_packet = Path(structural_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((structural_packet / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural.get("source_accession") != filing["accession"] or structural.get("report_date") != PERIOD:
        raise ValueError(f"{ticker}: controlling mismatch")
    verification = verify_source_bundle(ticker=ticker, packet=packet, structural_packet=structural_packet, structural_cache_root=Path(structural_cache_root), filing=filing)
    event = _events(ticker, Path(event_root), verification["source_manifest_sha256"])
    normalizer = _normalizer(submissions, facts, concept_config=_config(ticker))
    tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    flows = _ttm_flows(ticker, normalizer, structural, tax_rate)
    _, _, annual_all = _annual_cash_with_losses(normalizer)
    annual = tuple(row for row in annual_all if ticker != "EXE" or row["period_end"] >= "2025-01-01")
    ttm_sources = [source for field in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense") for source in flows[field]["sources"]]
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=flows["revenue"]["value"], ttm_cash_fcff=flows["cash_fcff"], ttm_period_end=PERIOD, ttm_sources=ttm_sources, valuation_date=BATCH_42_VALUATION_DATE)
    metric = profile.metric("cash_conversion_margin")
    if metric is None:
        raise ValueError(f"{ticker}: cash history unavailable")
    bridge = _bridge(ticker, structural)
    if ticker == "EXE":
        return _withheld_exe(filing=filing, flows=flows, annual=annual, profile=profile, bridge=bridge, event=event, verification=verification, structural=structural, tax_rate=tax_rate, tax_sources=tax_sources)
    if ticker == "ALB":
        return _withheld_alb(filing=filing, flows=flows, annual=annual_all, profile=profile, bridge=bridge, event=event, verification=verification, structural=structural, tax_rate=tax_rate, tax_sources=tax_sources)
    policy = POLICY[ticker]
    margins = (metric.low, metric.base, metric.high)
    if ticker == "EXE":
        margins = (max(.04, metric.low * .5), metric.low, min(.20, metric.high))
    share_base = bridge["base_share_count"]
    shares = (share_base * 1.015, share_base, share_base * .985)
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        starting = flows["revenue"]["value"] * margins[index]
        state = EnterpriseCashFlowState(starting, policy["growth"][index], policy["terminal"][index], policy["wacc"][index], bridge["cash"], bridge["debt"], 0., bridge["claims"][index], shares[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": max(0., raw), "starting_cash_fcff": starting, "cash_conversion_margin": margins[index], "growth": policy["growth"][index], "wacc": policy["wacc"][index], "terminal_growth": policy["terminal"][index], "cash_and_investments": bridge["cash"], "debt_and_finance_leases": bridge["debt"], "other_equity_claims": bridge["claims"][index], "shares": shares[index], "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError(f"{ticker}: nonpositive or unordered scenario")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("NORMALIZED_CYCLICAL_RANGE", "SPECIALIST_MODEL_UNCERTAINTY"))
    invalidation = "Revalue if current-company scope, commodity/input prices, cash conversion, capex, debt/leases, preferred/NCI, environmental/closure obligations, shares or cutoff events leave the recorded range."
    assumptions = {**profile.public_metadata(), "forecast_years": 8, "normalization_basis": "source-linked comparable cash-FCFF history with issuer-specific cycle treatment", "assumption_source_mix": "reported_history_and_governed_cycle_scenarios", "cash_conversion_margin": margins, "growth": policy["growth"], "wacc": policy["wacc"], "terminal_growth": policy["terminal"], "shares": shares, "share_sensitivity_basis": "latest cutoff-safe common shares are the base; H1 weighted diluted shares are diagnostic only; governed +/-1.5% stress represents unresolved dilution", "equity_floor_basis": "bear-only limited-liability floor; raw residual retained privately", "calculator_calibration": "Exact enterprise cash-FCFF default replay.", "invalidation": invalidation}
    if ticker == "EXE":
        assumptions["post_combination_history_treatment"] = "FY2025 and current June-2026 TTM only; bear is half the lower observed margin, base uses the lower observed margin, and bull is capped at 20%."
    baseline = BaselineValuation(ticker=ticker, method="resource_cycle_enterprise_fcff", method_version=BATCH_42_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(policy["warning"], invalidation))
    return {"ticker": ticker, "method": baseline.method, "model_version": BATCH_42_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": flows["revenue"]["value"], "ttm_cash_fcff": flows["cash_fcff"], "share_count": share_base}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": annual, "tax_rate": tax_rate, "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_context": bridge, "event_sources": event, "model_trace": {"states": traces}, "raw_scenario_rows": rows, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": policy["warning"], "baseline": baseline.as_private_dict()}


if PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_42_TICKERS):
    raise RuntimeError("Batch 42 policy mismatch")
