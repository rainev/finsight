"""One source-exhaustive recovery attempt for Batch 16 withheld issuers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_04_launch_first import _point
from .batch_11_history import _dimension_fact
from .batch_16_history import BATCH_16_HISTORY_VERSION, build_batch_16_history_result


BATCH_16_RECOVERY_VERSION = "BATCH-16-WITHHELD-RECOVERY-1.0"
BATCH_16_RECOVERY_TICKERS = ("DXCM", "EW", "CRL", "ZBH", "COR", "ELV")


DETAILS = {
    "DXCM": {
        "method": "unavailable_unbounded_securities_and_device_class_claims",
        "warning": "Withheld after recovery. Securities, derivative, and G6/G7 consumer class actions remain active, and no damages reserve, total loss range, or current insurance ceiling is disclosed.",
        "release": "Revalue after all current securities/derivative and G6/G7 class claims have source-supported finite ranges or are resolved.",
        "matters": ("two securities class-action groups", "federal and Delaware derivative actions", "six overlapping G6/G7 consumer class actions"),
    },
    "EW": {
        "method": "unavailable_unbounded_patent_milestone_and_tax_claims",
        "warning": "Withheld after recovery. The $56.9M reserve and historical Valtech milestone cap do not bound PASCAL damages/injunction, remaining Valtech relief, appeals, or tax exposure beyond accruals.",
        "release": "Revalue after PASCAL, remaining Valtech, appeal, and tax exposure beyond recorded reserves has one finite source-backed range.",
        "matters": ("PASCAL patent damages and permanent injunction", "Valtech accelerated milestone payments and ancillary relief", "Aortic/securities/derivative appeals", "tax exposure beyond uncertain-tax accruals"),
    },
    "CRL": {
        "method": "unavailable_unbounded_securities_class_claims",
        "warning": "Withheld after recovery. The revived securities-fraud claims and two stayed derivative actions have no disclosed maximum exposure, loss range, settlement, reserve, or current D&O insurance ceiling.",
        "release": "Revalue after the securities and derivative claim set has a source-supported finite net loss range or is resolved.",
        "matters": ("revived securities-fraud class claims", "two related stayed derivative actions"),
    },
    "ZBH": {
        "method": "unavailable_unbounded_china_distributor_and_tax_claims",
        "warning": "Withheld after recovery. The $137.9M litigation estimate does not bound China distributor claims beyond accruals, potential additional claims, or material IRS/foreign tax adjustments.",
        "release": "Revalue after the China distributor and tax-audit excess exposures have finite source-backed ranges.",
        "matters": ("China distributor lawsuits and possible additional claims", "IRS proposed adjustments", "foreign tax disputes"),
    },
    "COR": {
        "method": "unavailable_unbounded_opioid_claims",
        "warning": "Withheld after recovery. The $4.2B settled-opioid schedule is finite, but additional opioid and controlled-substance claims, penalties, private verdicts, and injunctions remain outside that accrual without a range.",
        "release": "Revalue after all material opioid/controlled-substance matters outside the recorded settlement schedule have finite source-backed ranges.",
        "matters": ("unsettled opioid lawsuits outside accrual", "DOJ controlled-substance civil penalties", "private verdict and injunction exposure"),
    },
    "ELV": {
        "method": "unavailable_unbounded_medicare_risk_adjustment_litigation",
        "warning": "Withheld after recovery. The CMS administrative notice is closed and bounded, but the separate DOJ False Claims Act suit and provider follow-on cases allege unspecified payments and remain unranged.",
        "release": "Revalue after the DOJ Medicare risk-adjustment and material provider follow-on claims have finite source-supported ranges or are resolved.",
        "matters": ("DOJ Medicare risk-adjustment False Claims Act lawsuit", "BCBSA provider follow-on cases", "other government actions with potential material sanctions"),
    },
}


def _baseline(ticker: str, detail: dict[str, Any]) -> dict[str, Any]:
    return BaselineValuation(ticker=ticker, method=detail["method"], method_version=BATCH_16_RECOVERY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(detail["warning"], detail["release"])).as_private_dict()


def _evidence(ticker: str, structural: dict[str, Any]) -> dict[str, Any]:
    detail = DETAILS[ticker]
    result: dict[str, Any] = {"unbounded_current_matters": detail["matters"], "allocated_total_claim_range": None, "release_condition": detail["release"], "recovery_outcome": "withheld"}
    if ticker == "DXCM":
        result.update({"professional_fee_accrual_not_damages_reserve": _point(structural, name="AccruedTaxAuditAndLegalFees", expected=33_500_000., period_end="2026-06-30"), "current_claim_insurance_limit": None, "insurance_receivable": None})
    elif ticker == "EW":
        result.update({"litigation_reserve": _point(structural, name="LitigationReserve", expected=56_900_000., period_end="2026-06-30"), "combined_litigation_and_insurance_reserve": _point(structural, name="AccruedLitigationAndInsuranceReserves", expected=72_400_000., period_end="2026-06-30"), "reserve_overlap_treatment": "Combined category cannot be added to the litigation reserve without scope proof.", "historical_valtech_total_milestone_cap_usd": 350_000_000., "remaining_valtech_balance": None, "applicable_insurance_limit": None})
    elif ticker == "CRL":
        result.update({"maximum_securities_exposure": None, "damages_reserve": None, "settlement_amount": None, "current_d_and_o_insurance_limit": None, "official_appeal_source": "https://www.ca1.uscourts.gov/sites/ca1/files/opnfiles/24-1705P-01A.pdf"})
    elif ticker == "ZBH":
        result.update({"recorded_litigation_estimate": _point(structural, name="LitigationReserve", expected=137_900_000., period_end="2026-06-30"), "china_excess_loss_range": None, "current_irs_proposed_adjustment_range": None, "foreign_tax_excess_range": None})
    elif ticker == "COR":
        result.update({"total_recorded_opioid_accrual": _dimension_fact(structural, name="LossContingencyAccrualAtCarryingValue", expected=4_200_000_000., start=None, end="2026-06-30", member="OpioidLawsuitsandInvestigationsMember"), "current_recorded_opioid_accrual": _dimension_fact(structural, name="LossContingencyAccrualCarryingValueCurrent", expected=396_200_000., start=None, end="2026-06-30", member="OpioidLawsuitsandInvestigationsMember"), "payment_horizon_years": 13, "loss_range_outside_accrual": None})
    else:
        result.update({"cms_original_accrual_usd": 935_000_000., "cms_payment_usd": 342_000_000., "cms_remaining_accrual": _dimension_fact(structural, name="LossContingencyEstimateOfPossibleLoss", expected=593_000_000., start=None, end="2026-06-30", member="CMSNoticeOfPossibleSanctionMember"), "cms_adjustment_range_plus_minus_usd": 320_000_000., "cms_enforcement_status": "closed_without_sanctions", "doj_alleged_payments": "unspecified", "doj_total_loss_range": None, "official_doj_source": "https://www.justice.gov/usao-sdny/pr/manhattan-us-attorney-files-civil-fraud-suit-against-anthem-inc-falsely-certifying"})
    return result


def build_batch_16_recovery_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_16_RECOVERY_TICKERS:
        raise ValueError(f"unexpected Batch 16 recovery ticker {ticker}")
    initial = build_batch_16_history_result(ticker=ticker, source_root=source_root, structural_root=structural_root, event_root=event_root)
    if initial["availability_type"] != "not_available" or initial["scenario_range"] != {"low": None, "base": None, "high": None}:
        raise ValueError(f"{ticker}: recovery must start from confirmed Withheld result")
    structural = __import__("json").loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    detail = DETAILS[ticker]
    result = dict(initial)
    result.update({"model_version": BATCH_16_RECOVERY_VERSION, "warning": detail["warning"], "baseline": _baseline(ticker, detail)})
    result["governed_assumptions"] = {**initial["governed_assumptions"], "normalization_basis": "source_exhausted_material_claims_unbounded", "invalidation": detail["release"]}
    result["source_ledger"] = {**initial["source_ledger"], "recovery_source_exhaustion": _evidence(ticker, structural)}
    return result
