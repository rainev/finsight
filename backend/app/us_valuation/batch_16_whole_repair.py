"""Exceptional whole-Batch-16 baseline-first repair."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .batch_04_launch_first import _controlling
from .batch_16 import BATCH_16_TICKERS
from .batch_16_history import (
    P,
    _cash_result,
    _elv_result,
    build_batch_16_history_result,
)
from .legal_tail_policy import apply_unquantified_legal_tail_policy
from .xbrl import load_concept_config


BATCH_16_WHOLE_REPAIR_VERSION = "BATCH-16-WHOLE-BASELINE-REPAIR-1.0"
REPAIRED_PASS_TICKERS = frozenset({"PODD", "VEEV", "IQV"})
REPAIRED_CONDITIONAL_TICKERS = frozenset({"A", "DXCM", "EW", "CRL", "ZBH", "COR", "ELV"})
REPAIRED_WITHHELD_TICKERS = frozenset()
LEGAL_TAIL_TICKERS = frozenset({"DXCM", "EW", "CRL", "ZBH", "COR", "ELV"})


LEGAL_DETAILS = {
    "DXCM": {
        "matter": "Securities, derivative, and G6/G7 consumer class claims",
        "recorded": P["DXCM"].claim_formula,
        "invalidation": "Invalidate if a settlement, judgment, injunction, recall, insurance recovery, or new filing makes the legal or device operating effect finite or changes the going-concern operating state.",
    },
    "EW": {
        "matter": "PASCAL, Valtech, appeal, and tax exposure beyond recorded amounts",
        "recorded": P["EW"].claim_formula,
        "invalidation": "Invalidate if PASCAL relief, remaining Valtech obligations, appeals, tax exposure, insurance, or acquired-device cash becomes finite or changes materially.",
    },
    "CRL": {
        "matter": "Revived securities-fraud and related derivative claims",
        "recorded": P["CRL"].claim_formula,
        "invalidation": "Invalidate if a reserve, settlement, judgment, D&O recovery, or operating response to the securities and derivative claims changes materially.",
    },
    "ZBH": {
        "matter": "China distributor claims and IRS or foreign-tax exposure beyond recorded amounts",
        "recorded": P["ZBH"].claim_formula,
        "invalidation": "Invalidate if China distributor claims, tax adjustments, recorded litigation, contingent consideration, debt, or operating cash changes materially.",
    },
    "COR": {
        "matter": "Opioid and controlled-substance claims, penalties, verdicts, and injunctions outside the recorded settlement schedule",
        "recorded": P["COR"].claim_formula,
        "invalidation": "Invalidate if the opioid schedule, DOJ or private matters, distribution licenses, debt, NCI, or normalized distribution cash changes materially.",
    },
    "ELV": {
        "matter": "The DOJ Medicare risk-adjustment False Claims Act suit and provider follow-on cases",
        "recorded": "The $593M remaining CMS accrual is already reflected in common equity and earnings; the disclosed $320M CMS adjustment range widens reliability and is not deducted twice.",
        "invalidation": "Invalidate if DOJ or provider claims become finite, Medicare participation or regulated capital changes, or common equity, earnings, claims reserves, or shares changes materially.",
    },
}


def _zbh_concept_config() -> dict[str, Any]:
    """Add ZBH's current net-interest concept without changing global precedence."""

    config = deepcopy(load_concept_config())
    concepts = config["fields"]["interest_expense"]["concepts"]
    if "InterestIncomeExpenseNet" not in concepts:
        concepts.append("InterestIncomeExpenseNet")
    return config


def _versioned(result: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(result)
    value["model_version"] = BATCH_16_WHOLE_REPAIR_VERSION
    value["baseline"] = {**value["baseline"], "method_version": BATCH_16_WHOLE_REPAIR_VERSION}
    value["source_ledger"] = {
        **value["source_ledger"],
        "whole_batch_repair": {
            "repair_scope": "exceptional_user_authorized_whole_batch_revisit",
            "automatic_recovery_attempt_reset": False,
            "prior_recovery_evidence_preserved": True,
            "market_price_used": False,
            "analyst_target_used": False,
        },
    }
    return value


def _podd_pass(result: dict[str, Any]) -> dict[str, Any]:
    value = _versioned(result)
    warning = (
        "Source-bounded insulin-delivery baseline. The filing says current legal proceedings are "
        "not expected to be materially adverse and the Hu loss is not probable; its reported zero "
        "accrual is not treated as an estimated zero ultimate loss."
    )
    invalidation = (
        "Invalidate if Omnipod growth, cash conversion, manufacturing capex, debt/leases, shares, "
        "or the Hu/other legal assessment changes materially."
    )
    value.update({"availability_type": "available", "warning": warning})
    value["history_reliability"] = {
        **value["history_reliability"],
        "model_cap": "High",
        "reasons": [],
    }
    value["governed_assumptions"] = {
        **value["governed_assumptions"],
        "normalization_basis": "company_history_with_reported_nonprobable_nonmaterial_claim_assessment",
        "assumption_source_mix": "reported_history_and_reported_legal_assessment",
        "unquantified_legal_loss_amount": None,
        "unquantified_legal_loss_assumed_zero": False,
        "invalidation": invalidation,
    }
    value["source_ledger"] = {
        **value["source_ledger"],
        "claim_publication_assessment": {
            "matter": "Hu securities class action",
            "reported_loss_probability": "not probable",
            "reported_accrual_usd": 0.0,
            "reported_aggregate_materiality_assessment": "not expected to have a material adverse effect on results of operations",
            "ultimate_loss_estimate": None,
            "zero_substitution_used": False,
            "treatment": "Pass classification uses the issuer's current probability and aggregate materiality assessment; it does not claim ultimate loss is zero.",
            "invalidation": invalidation,
        },
    }
    value["baseline"] = {
        **value["baseline"],
        "availability_type": "available",
        "confidence_reasons": [],
        "warnings": [warning, invalidation],
    }
    return value


def _repair_ew_trace(result: dict[str, Any]) -> dict[str, Any]:
    """Label EW's annual interest carry and governed claim midpoint honestly."""

    value = deepcopy(result)
    annual_interest = value["reported_inputs"]["ttm_interest"]
    if annual_interest != 20_400_000.0:
        raise ValueError("EW annual interest fallback changed")
    value["reported_inputs"].update(
        {
            "ttm_interest": None,
            "interest_expense_used": annual_interest,
            "interest_period_status": "latest_fiscal_year_carried_as_estimate",
        }
    )
    value["governed_assumptions"].update(
        {
            "interest_period_treatment": "FY2025 reported interest expense is carried as a conservative TTM estimate because the current filing reports net investment/interest income rather than a comparable interest-expense duration.",
            "autus_contingent_consideration_range": (132_500_000.0, 70_000_000.0, 7_500_000.0),
            "autus_contingent_consideration_base_status": "finsight_arithmetic_midpoint_estimate",
        }
    )
    value["source_ledger"]["ew_repair_trace"] = {
        "interest_expense_used_usd": annual_interest,
        "interest_period_status": "latest_fiscal_year_carried_as_estimate",
        "interest_source": value["source_ledger"]["flow_sources"]["interest_expense"],
        "autus_contingent_consideration_high_reported_usd": 132_500_000.0,
        "current_contingent_consideration_liability_reported_usd": 7_500_000.0,
        "base_midpoint_estimated_usd": 70_000_000.0,
        "base_midpoint_formula": "(132.5M reported maximum + 7.5M reported current liability) / 2",
        "medical_device_company_equity_issued_usd": 70_000_000.0,
        "medical_device_company_equity_used_as_autus_fact": False,
    }
    return value


def build_batch_16_whole_repair_result(
    *,
    ticker: str,
    source_root: Path,
    structural_root: Path,
    event_root: Path,
) -> dict[str, Any]:
    if ticker not in BATCH_16_TICKERS:
        raise ValueError(f"unexpected Batch 16 whole-repair ticker {ticker}")
    source_root, structural_root, event_root = map(Path, (source_root, structural_root, event_root))
    initial = build_batch_16_history_result(
        ticker=ticker,
        source_root=source_root,
        structural_root=structural_root,
        event_root=event_root,
    )
    if ticker not in LEGAL_TAIL_TICKERS:
        return _podd_pass(initial) if ticker == "PODD" else _versioned(initial)

    packet = source_root / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((structural_root / ticker / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural.get("source_accession") != filing["accession"]:
        raise ValueError(f"{ticker}: whole-repair controlling source mismatch")
    candidate = (
        _elv_result(filing, structural, facts)
        if ticker == "ELV"
        else _cash_result(
            ticker=ticker,
            filing=filing,
            structural=structural,
            submissions=submissions,
            facts=facts,
            event_root=event_root,
            concept_config=_zbh_concept_config() if ticker == "ZBH" else None,
        )
    )
    detail = LEGAL_DETAILS[ticker]
    candidate = apply_unquantified_legal_tail_policy(
        candidate,
        model_version=BATCH_16_WHOLE_REPAIR_VERSION,
        matter_summary=detail["matter"],
        recorded_claim_treatment=detail["recorded"],
        invalidation=detail["invalidation"],
    )
    if ticker == "EW":
        candidate = _repair_ew_trace(candidate)
    candidate["source_ledger"] = {
        **candidate["source_ledger"],
        "whole_batch_repair": {
            "repair_scope": "exceptional_user_authorized_whole_batch_revisit",
            "initial_availability_type": initial["availability_type"],
            "automatic_recovery_attempt_reset": False,
            "prior_recovery_evidence_preserved": True,
            "market_price_used": False,
            "analyst_target_used": False,
        },
    }
    return candidate


if REPAIRED_PASS_TICKERS | REPAIRED_CONDITIONAL_TICKERS | REPAIRED_WITHHELD_TICKERS != set(BATCH_16_TICKERS):
    raise RuntimeError("Batch 16 whole-repair denominator mismatch")
