"""Config-driven artifact builder for frozen PSE V2 Phase B Batch 1."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from .contract import PseValuationArtifact, ScenarioValue, canonical_json, sha256_object
from .models.distributions import distribution_valuation
from .models.residual_income import residual_income_valuation


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_01.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B01-1.0"
BANK_TICKERS = ("BPI", "MBT", "SECB", "CBC", "EW")
REIT_TICKERS = ("RCR", "MREIT", "CREIT", "FILRT", "DDMPR")
FROZEN_BATCH_TICKERS = BANK_TICKERS + REIT_TICKERS


def load_batch_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "PSE-V2-PHASE-B-BATCH-1.0":
        raise ValueError("unsupported Phase B Batch 1 configuration")
    if tuple(payload.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Phase B Batch 1 issuer set differs from the confirmed frozen set")
    issuers = payload.get("issuers")
    if not isinstance(issuers, dict) or set(issuers) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Phase B Batch 1 must contain exactly the frozen ten issuers")
    return payload


def source_receipt(ticker: str, config: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    issuer = config["issuers"][ticker]
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0",
        "batch_version": config["batch_version"],
        "review_status": config["review_status"],
        "retrieval_date": config["valuation_date"],
        "ticker": ticker,
        "issuer_name": issuer["issuer_name"],
        "source": issuer["source"],
        "supporting_urls": issuer.get("distribution_sources", []),
        "facts": issuer["facts"],
        "note": (
            "This deterministic receipt binds the reviewed public facts and official source links. "
            "It is not a redistributed copy of the remote filing."
        ),
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    reference = {
        "document_id": digest[:16],
        "label": issuer["source"]["label"],
        "form": issuer["source"].get("form"),
        "period_end": issuer["source"].get("period_end"),
        "published_at": issuer["source"].get("published_at"),
        "url": issuer["source"]["url"],
        "source_page": None,
        "sha256": digest,
    }
    return reference, raw


def _bank_artifact(ticker: str, config: dict[str, Any]) -> PseValuationArtifact:
    issuer = config["issuers"][ticker]
    facts = issuer["facts"]
    policy = config["bank_policy"]
    source, _receipt = source_receipt(ticker, config)
    current_equity = float(facts["parent_common_equity_php_millions"])
    prior_equity = float(facts["prior_parent_common_equity_php_millions"])
    net_income = float(facts["net_income_to_parent_php_millions"])
    book_value_per_share = float(facts["book_value_per_share"])
    shares = current_equity / book_value_per_share
    normalized_roe = net_income / ((current_equity + prior_equity) / 2)
    scenario_values: dict[str, ScenarioValue] = {}
    scenario_assumptions: dict[str, dict[str, float]] = {}
    private_results: dict[str, Any] = {}

    for name in ("bear", "base", "bull"):
        raw = policy["scenarios"][name]
        current_roe = normalized_roe * float(raw["current_roe_factor"])
        terminal_roe = min(
            float(raw["terminal_roe_cap"]),
            max(float(raw["terminal_roe_floor"]), normalized_roe * float(raw["terminal_roe_factor"])),
        )
        assumptions = {
            "current_roe": current_roe,
            "terminal_roe": terminal_roe,
            "cost_of_equity": float(raw["cost_of_equity"]),
            "payout_ratio": float(raw["payout_ratio"]),
            "terminal_growth": float(raw["terminal_growth"]),
        }
        valued = residual_income_valuation(
            opening_common_equity=current_equity,
            shares_outstanding=shares,
            forecast_years=int(policy["forecast_years"]),
            **assumptions,
        )
        if valued["common_equity_value"] <= 0 or valued["value_per_share"] <= 0:
            raise ValueError(f"{ticker} {name}: non-positive residual-income value")
        scenario_assumptions[name] = assumptions
        private_results[name] = valued
        scenario_values[name] = ScenarioValue(
            value_per_share=valued["value_per_share"],
            common_equity_value=valued["common_equity_value"],
        )

    values = [row.value_per_share for row in scenario_values.values()]
    input_snapshot = {
        "ticker": ticker,
        "facts": facts,
        "normalized_roe": normalized_roe,
        "shares_millions": shares,
        "policy": policy,
        "macro_snapshot_version": config["macro_snapshot_version"],
        "source_receipt_sha256": source["sha256"],
        "model_version": MODEL_VERSION,
    }
    return PseValuationArtifact(
        model_version=MODEL_VERSION,
        ticker=ticker,
        issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
        security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
        subsector=issuer["subsector"],
        primary_model=issuer["primary_model"],
        valuation_date=date.fromisoformat(config["valuation_date"]),
        filing_period="FY 2025",
        availability_type="intrinsic_valuation",
        publication_state="provisional",
        scenarios=scenario_values,
        numerical_range={"low": min(values), "high": max(values)},
        public_assumptions={
            "forecast_years": int(policy["forecast_years"]),
            "book_value_per_share": book_value_per_share,
            "normalized_roe": normalized_roe,
            "scenario_assumptions": scenario_assumptions,
            "macro_snapshot_version": config["macro_snapshot_version"],
            "policy_version": policy["version"],
            "route_reason": issuer["route_reason"],
            "reliability": "Low",
        },
        sensitivities=[
            {
                "type": "scenario_range",
                "drivers": ["current_roe", "terminal_roe", "cost_of_equity", "payout_ratio", "terminal_growth"],
            }
        ],
        sources=[source],
        warnings=[
            "Provisional Phase B estimate based on reviewed FY2025 public filing facts and a versioned shared bank policy.",
            "Regulatory capital, asset quality, and current market multiples remain challenge checks rather than direct numerical model inputs.",
            "The source hash binds the reviewed fact receipt; the remote filing is referenced but not redistributed in the candidate catalog.",
        ],
        blocking_reasons=[],
        input_hash=sha256_object(input_snapshot),
    ).with_artifact_hash()


def _reit_artifact(ticker: str, config: dict[str, Any]) -> PseValuationArtifact:
    issuer = config["issuers"][ticker]
    facts = issuer["facts"]
    policy = config["reit_policies"][issuer["policy"]]
    source, _receipt = source_receipt(ticker, config)
    current_distribution = float(facts["distribution_per_share"])
    shares = float(facts["shares_millions"])
    scenario_values: dict[str, ScenarioValue] = {}
    scenario_assumptions: dict[str, dict[str, float]] = {}

    for name in ("bear", "base", "bull"):
        assumptions = {
            key: float(value) for key, value in policy["scenarios"][name].items()
        }
        valued = distribution_valuation(
            current_distribution_per_share=current_distribution,
            forecast_years=int(policy["forecast_years"]),
            **assumptions,
        )
        if valued["value_per_share"] <= 0:
            raise ValueError(f"{ticker} {name}: non-positive distribution value")
        scenario_assumptions[name] = assumptions
        scenario_values[name] = ScenarioValue(
            value_per_share=valued["value_per_share"],
            common_equity_value=valued["value_per_share"] * shares,
        )

    values = [row.value_per_share for row in scenario_values.values()]
    input_snapshot = {
        "ticker": ticker,
        "facts": facts,
        "policy": policy,
        "macro_snapshot_version": config["macro_snapshot_version"],
        "source_receipt_sha256": source["sha256"],
        "model_version": MODEL_VERSION,
    }
    return PseValuationArtifact(
        model_version=MODEL_VERSION,
        ticker=ticker,
        issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
        security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
        subsector=issuer["subsector"],
        primary_model=issuer["primary_model"],
        valuation_date=date.fromisoformat(config["valuation_date"]),
        filing_period=str(facts["distribution_period"]),
        availability_type="intrinsic_valuation",
        publication_state="provisional",
        scenarios=scenario_values,
        numerical_range={"low": min(values), "high": max(values)},
        public_assumptions={
            "forecast_years": int(policy["forecast_years"]),
            "current_distribution_per_share": current_distribution,
            "book_value_per_share_check": float(facts["book_value_per_share"]),
            "scenario_assumptions": scenario_assumptions,
            "macro_snapshot_version": config["macro_snapshot_version"],
            "policy_version": policy["version"],
            "route_reason": issuer["route_reason"],
            "reliability": "Low",
        },
        sensitivities=[
            {
                "type": "scenario_range",
                "drivers": ["current_distribution_per_share", "explicit_growth", "cost_of_equity", "terminal_growth"],
            }
        ],
        sources=[source],
        warnings=[
            "Provisional Phase B estimate based on reviewed FY2025 distributions and a versioned shared REIT policy.",
            "NAV is shown only as a reported book-value check; a property-level appraisal NAV has not been substituted or silently inferred.",
            "The source hash binds the reviewed fact receipt; the remote filing is referenced but not redistributed in the candidate catalog.",
        ],
        blocking_reasons=[],
        input_hash=sha256_object(input_snapshot),
    ).with_artifact_hash()


def build_batch_artifacts(config: dict[str, Any] | None = None) -> dict[str, PseValuationArtifact]:
    payload = config or load_batch_config()
    artifacts: dict[str, PseValuationArtifact] = {}
    for ticker in FROZEN_BATCH_TICKERS:
        artifacts[ticker] = (
            _bank_artifact(ticker, payload)
            if ticker in BANK_TICKERS
            else _reit_artifact(ticker, payload)
        )
    if tuple(artifacts) != FROZEN_BATCH_TICKERS:
        raise ValueError("Phase B Batch 1 artifact set does not match the frozen issuer set")
    return artifacts
