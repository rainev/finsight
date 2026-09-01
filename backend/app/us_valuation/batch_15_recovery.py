"""One source-exhaustive recovery attempt for Batch 15 withheld issuers."""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_02_practical_inputs import _normalizer
from .batch_04_launch_first import _point
from .batch_11_history import _dimension_fact
from .batch_15 import BATCH_15_VALUATION_DATE
from .batch_15_history import build_batch_15_history_result


BATCH_15_RECOVERY_VERSION = "BATCH-15-WITHHELD-RECOVERY-1.0"
BATCH_15_RECOVERY_TICKERS = ("LH", "ISRG", "ALGN")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _doj_source(root: Path) -> dict[str, Any]:
    packet = Path(root) / "LH"
    receipt_path = packet / "source-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    announcement = packet / "doj-announcement.html"
    agreement = packet / "doj-settlement-agreement.pdf"
    if (
        receipt.get("schema_version") != "FINSIGHT-BATCH-15-RECOVERY-SOURCE-1"
        or receipt.get("valuation_date") != BATCH_15_VALUATION_DATE
        or receipt.get("ticker") != "LH"
        or _sha(announcement) != receipt["announcement"]["sha256"]
        or _sha(agreement) != receipt["agreement"]["sha256"]
    ):
        raise ValueError("LH DOJ recovery source is invalid")
    terms = receipt["reported_terms"]
    if terms != {
        "principal_usd": 14_500_000,
        "annual_interest_rate": 0.045,
        "interest_start": "2025-05-14",
        "restitution_usd": 8_286_000,
        "payment_due_days_after_effective_date": 30,
    }:
        raise ValueError("LH DOJ reported terms changed")
    elapsed = (date.fromisoformat(BATCH_15_VALUATION_DATE) - date.fromisoformat(terms["interest_start"])).days
    interest = terms["principal_usd"] * terms["annual_interest_rate"] * elapsed / 365.
    return {
        "source_kind": "official_doj_announcement_and_settlement_agreement",
        "receipt_sha256": _sha(receipt_path),
        "announcement": receipt["announcement"],
        "agreement": receipt["agreement"],
        "reported_terms": terms,
        "cutoff_elapsed_interest_days": elapsed,
        "cutoff_interest_usd": interest,
        "cutoff_principal_plus_interest_usd": terms["principal_usd"] + interest,
        "reported_vs_estimated": "reported principal/rate/start; simple-interest cutoff arithmetic",
    }


def _baseline(ticker: str, method: str, warning: str, release: str) -> dict[str, Any]:
    return BaselineValuation(
        ticker=ticker,
        method=method,
        method_version=BATCH_15_RECOVERY_VERSION,
        low=None,
        base=None,
        high=None,
        confidence=None,
        availability_type=AvailabilityType.NOT_AVAILABLE,
        warnings=(warning, release),
    ).as_private_dict()


def _lh_recovery(initial: dict[str, Any], structural: dict[str, Any], recovery_source_root: Path) -> dict[str, Any]:
    doj = _doj_source(recovery_source_root)
    awards = [
        _dimension_fact(structural, name="LossContingencyDamagesAwardedValue", expected=272_000_000., start="2022-09-22", end="2022-09-22", member="InitialDamagesMember"),
        _dimension_fact(structural, name="LossContingencyDamagesAwardedValue", expected=100_000_000., start="2023-05-12", end="2023-05-12", member="EnhancedDamagesMember"),
        _dimension_fact(structural, name="LossContingencyDamagesAwardedValue", expected=2_600_000., start="2025-01-23", end="2025-01-23", member="SupplementalDamagesMember"),
        _dimension_fact(structural, name="LossContingencyDamagesAwardedValue", expected=100., start="2025-01-23", end="2025-01-23", member="RoyaltyDamagesMember"),
    ]
    warning = "Withheld after recovery. The $14.5M DOJ settlement is bounded, but Ravgen interest and future $100-per-test royalties plus two undisclosed class-settlement amounts leave total current legal claims materially unbounded."
    release = "Revalue only after Ravgen royalty/test-volume/interest and the AMCA and Meta Pixel settlement amounts or finite upper bounds are filed."
    result = dict(initial)
    result.update({"method": "unavailable_unbounded_total_legal_claims", "model_version": BATCH_15_RECOVERY_VERSION, "warning": warning, "baseline": _baseline("LH", "unavailable_unbounded_total_legal_claims", warning, release)})
    result["governed_assumptions"] = {**initial["governed_assumptions"], "normalization_basis": "source_exhausted_total_legal_claims_unbounded", "invalidation": release}
    result["source_ledger"] = {**initial["source_ledger"], "recovery_source_exhaustion": {"doj_subclaim": doj, "ravgen_award_sources": awards, "ravgen_unbounded_components": ("pre- and post-judgment interest without a filed cutoff balance", "$100 per future test through patent life without test volume or expiry cash schedule", "attorney fees and other relief"), "class_settlements_without_amounts": ({"matter": "AMCA multidistrict class settlement", "agreement_date": "2026-03-02", "status": "subject to court approval", "amount_or_range": None}, {"matter": "Meta Pixel class settlement", "agreement_date": "2026-04-02", "status": "subject to court approval", "amount_or_range": None}), "additional_unbounded_current_matters": ({"matter": "Davis/Vargas certified ADA class action", "relief": "statutory damages, injunction, fees, and costs", "amount_or_range": None}, {"matter": "Raymond Eugenio AMCA shareholder-derivative action", "relief": "damages, disclosures, and governance changes", "amount_or_range": None}), "management_assessed_other_matters": {"scope": "other employment, professional-liability, and commercial proceedings", "assessment": "remote and not expected to be material individually or in aggregate", "used_to_bound_specifically_described_matters": False}, "release_condition": release, "recovery_outcome": "withheld"}}
    return result


def _isrg_recovery(initial: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    current_accrued = _point(structural, name="OtherAccruedLiabilitiesCurrent", expected=445_500_000., period_end="2026-06-30")
    warning = "Withheld after recovery. Current product-liability and antitrust matters may exceed recognized accruals, while the filing discloses neither the allocated reserve nor an excess-loss range or current insurance ceiling."
    release = "Revalue only after current product-liability and antitrust excess losses or insurance-backed upper bounds are disclosed."
    result = dict(initial)
    result.update({"model_version": BATCH_15_RECOVERY_VERSION, "warning": warning, "baseline": _baseline("ISRG", initial["method"], warning, release)})
    result["governed_assumptions"] = {**initial["governed_assumptions"], "normalization_basis": "source_exhausted_product_and_antitrust_claims_unbounded", "invalidation": release}
    result["source_ledger"] = {**initial["source_ledger"], "recovery_source_exhaustion": {"aggregate_other_accrued_liabilities": current_accrued, "allocated_legal_reserve": None, "current_insurance_limit": None, "current_product_claim_count": None, "unbounded_current_matters": ("product-liability excess over recognized amount", "SIS antitrust appeal", "certified da Vinci antitrust class action", "Restore appeal"), "why_history_does_not_bound": "Historical reserves and insurance terms do not establish the current claim count, punitive-damage exposure, or 2026 coverage ceiling.", "release_condition": release, "recovery_outcome": "withheld"}}
    return result


def _algn_recovery(initial: dict[str, Any], structural: dict[str, Any], facts: dict[str, Any], submissions: dict[str, Any]) -> dict[str, Any]:
    normalizer = _normalizer(submissions, facts)
    annual = normalizer.annual_series("revenue", 5)[-1]
    if annual.end != "2025-12-31" or float(annual.value) != 4_034_964_000.:
        raise ValueError("ALGN 2025 revenue source changed")
    eu_cap = float(annual.value) * .10
    warning = "Withheld after recovery. The EU administrative fine alone has a 10%-of-turnover ceiling, but Straumann money-damage counterclaims, follow-on private litigation, patent remedies, and indemnification exposure have no total filed range."
    release = "Revalue only after the non-EU-fine legal/IP/private-damage claims have source-supported finite bounds."
    result = dict(initial)
    result.update({"model_version": BATCH_15_RECOVERY_VERSION, "warning": warning, "baseline": _baseline("ALGN", initial["method"], warning, release)})
    result["governed_assumptions"] = {**initial["governed_assumptions"], "normalization_basis": "source_exhausted_legal_ip_and_competition_claims_unbounded", "invalidation": release}
    result["source_ledger"] = {**initial["source_ledger"], "recovery_source_exhaustion": {"known_accrued_legal_settlement": _point(structural, name="AccruedLegalSettlementCosts", expected=31_800_000., period_end="2026-06-30"), "known_uk_vat_contingency": _point(structural, name="UKVATLossContingency", expected=37_514_000., period_end="2026-06-30"), "eu_investigation": {"case_identifier": "AT.40900", "opened": "2026-06-30", "official_source": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1483", "subject": "Invisalign clear aligners and iTero intraoral scanners"}, "eu_regulation_1_2003_article_23": {"fine_cap_ratio": .10, "prior_year_worldwide_turnover_usd": annual.as_dict(), "indicative_turnover_reference_usd": eu_cap, "scope": "Indicative 2025-turnover reference for the European Commission administrative fine only; not a guaranteed future total legal maximum."}, "unbounded_outside_eu_fine": ("City Smiles direct-purchaser antitrust class appeal seeking treble damages, interest, fees, and injunction", "Misty Snow indirect-purchaser antitrust class appeal seeking treble damages, interest, fees, and injunction", "Straumann antitrust and unfair-competition money damages/post-trial appeal risk", "EU follow-on private litigation", "patent/IP remedies across EU, China, and US ITC", "future indemnification maximum"), "unused_revolver_is_not_debt": True, "private_investment_upside_not_used_to_offset_claims": True, "release_condition": release, "recovery_outcome": "withheld"}}
    return result


def build_batch_15_recovery_result(*, ticker: str, source_root: Path, structural_root: Path, recovery_source_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_15_RECOVERY_TICKERS:
        raise ValueError(f"unexpected Batch 15 recovery ticker {ticker}")
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    initial = build_batch_15_history_result(ticker=ticker, source_root=source_root, structural_root=structural_root)
    if initial["availability_type"] != "not_available" or initial["scenario_range"] != {"low": None, "base": None, "high": None}:
        raise ValueError(f"{ticker}: recovery must start from the confirmed Withheld result")
    if ticker == "LH":
        return _lh_recovery(initial, structural, Path(recovery_source_root))
    if ticker == "ISRG":
        return _isrg_recovery(initial, structural)
    return _algn_recovery(initial, structural, facts, submissions)
