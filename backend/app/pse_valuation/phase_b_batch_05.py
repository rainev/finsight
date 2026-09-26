"""Config-driven artifact builder for frozen PSE V2 Phase B Batch 5."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from .contract import PseValuationArtifact, ScenarioValue, canonical_json, sha256_object
from .models.comparables import market_relative_range
from .models.residual_income import residual_income_valuation


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_05.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B05-1.0"
FROZEN_BATCH_TICKERS = ("PNB", "RCB", "UBP", "AUB", "PBB", "PSB", "COL", "PSE", "NRCP", "MFIN")
INTRINSIC_TICKERS = ("PNB", "RCB", "UBP", "AUB", "PBB", "PSB", "COL", "NRCP")
RELATIVE_TICKERS = ("PSE", "MFIN")


def load_batch_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "PSE-V2-PHASE-B-BATCH-5.0":
        raise ValueError("unsupported Phase B Batch 5 configuration")
    if tuple(payload.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Phase B Batch 5 issuer set differs from the confirmed frozen set")
    issuers = payload.get("issuers")
    if not isinstance(issuers, dict) or set(issuers) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Phase B Batch 5 must contain exactly the frozen ten issuers")
    for ticker, issuer in issuers.items():
        expected = "intrinsic_valuation" if ticker in INTRINSIC_TICKERS else "market_relative_only"
        if issuer.get("availability") != expected:
            raise ValueError(f"{ticker}: Batch 5 route classification drift")
    return payload


def source_receipt(ticker: str, config: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    issuer = config["issuers"][ticker]
    receipt = {"schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0", "batch_version": config["batch_version"], "review_status": config["review_status"], "retrieval_date": config["valuation_date"], "ticker": ticker, "issuer_name": issuer["issuer_name"], "source": issuer["source"], "facts": issuer["facts"], "note": "This deterministic receipt binds reviewed public facts and the official source link. It is not a redistributed copy of the remote filing."}
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    source = issuer["source"]
    return ({"document_id": digest[:16], "label": source["label"], "form": source.get("form"), "period_end": source.get("period_end"), "published_at": source.get("published_at"), "url": source["url"], "source_page": source.get("source_page"), "sha256": digest}, raw)


def _intrinsic_artifact(ticker: str, config: dict[str, Any]) -> PseValuationArtifact:
    issuer = config["issuers"][ticker]
    facts = issuer["facts"]
    policy = config["residual_policies"][issuer["policy"]]
    source, _receipt = source_receipt(ticker, config)
    current_equity = float(facts["parent_common_equity_php_millions"])
    prior_equity = float(facts["prior_parent_common_equity_php_millions"])
    net_income = float(facts["net_income_to_parent_php_millions"])
    book_value_per_share = float(facts["book_value_per_share"])
    if min(current_equity, prior_equity, net_income, book_value_per_share) <= 0:
        raise ValueError(f"{ticker}: residual-income facts must be positive")
    shares = current_equity / book_value_per_share
    normalized_roe = net_income / ((current_equity + prior_equity) / 2)
    scenarios: dict[str, ScenarioValue] = {}
    scenario_assumptions: dict[str, dict[str, float]] = {}
    for name in ("bear", "base", "bull"):
        raw = policy["scenarios"][name]
        assumptions = {
            "current_roe": normalized_roe * float(raw["current_roe_factor"]),
            "terminal_roe": min(float(raw["terminal_roe_cap"]), max(float(raw["terminal_roe_floor"]), normalized_roe * float(raw["terminal_roe_factor"]))),
            "cost_of_equity": float(raw["cost_of_equity"]),
            "payout_ratio": float(raw["payout_ratio"]),
            "terminal_growth": float(raw["terminal_growth"]),
        }
        valued = residual_income_valuation(opening_common_equity=current_equity, shares_outstanding=shares, forecast_years=int(policy["forecast_years"]), **assumptions)
        if valued["value_per_share"] <= 0:
            raise ValueError(f"{ticker} {name}: non-positive residual-income value")
        scenarios[name] = ScenarioValue(value_per_share=valued["value_per_share"], common_equity_value=valued["common_equity_value"])
        scenario_assumptions[name] = assumptions
    values = [row.value_per_share for row in scenarios.values()]
    input_snapshot = {"ticker": ticker, "facts": facts, "policy": policy, "normalized_roe": normalized_roe, "shares_millions": shares, "source_receipt_sha256": source["sha256"], "model_version": MODEL_VERSION}
    return PseValuationArtifact(
        model_version=MODEL_VERSION, ticker=ticker, issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]}, security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"}, subsector=issuer["subsector"], primary_model="residual_income", valuation_date=date.fromisoformat(config["valuation_date"]), filing_period="FY 2025", availability_type="intrinsic_valuation", publication_state="provisional", scenarios=scenarios, numerical_range={"low": min(values), "high": max(values)},
        public_assumptions={"forecast_years": int(policy["forecast_years"]), "book_value_per_share": book_value_per_share, "normalized_roe": normalized_roe, "scenario_assumptions": scenario_assumptions, "macro_snapshot_version": config["macro_snapshot_version"], "policy_version": policy["version"], "route_reason": issuer["route_reason"], "reliability": "Low"},
        sensitivities=[{"type": "scenario_range", "drivers": ["current_roe", "terminal_roe", "cost_of_equity", "payout_ratio", "terminal_growth"]}], sources=[source], warnings=["Provisional residual-income estimate based on reviewed FY2025 public filing facts and a versioned shared financial policy.", "Capital quality, asset quality, underwriting quality, and market multiples remain challenge checks rather than direct model inputs.", "The source hash binds the reviewed fact receipt; the remote filing is referenced but not redistributed."], blocking_reasons=[], input_hash=sha256_object(input_snapshot)
    ).with_artifact_hash()


def _relative_artifact(ticker: str, config: dict[str, Any]) -> PseValuationArtifact:
    issuer = config["issuers"][ticker]
    facts = issuer["facts"]
    policy = config["relative_policies"][issuer["policy"]]
    source, _receipt = source_receipt(ticker, config)
    metric_value = float(facts[policy["metric_value_key"]])
    result = market_relative_range(metric=policy["metric"], metric_value_per_share=metric_value, assumptions=policy["assumptions"], relation=policy["relation"])
    result.update({"policy_version": policy["policy_version"], "metric_label": policy["metric_label"], "source_status": "reviewed_public_fact", "source_document_sha256": source["sha256"], "source_page": source["source_page"], "note": "Transparent market-relative screen while refreshed residual-income normalization remains incomplete."})
    estimates = result["estimates"]
    input_snapshot = {"ticker": ticker, "facts": facts, "policy": policy, "source_receipt_sha256": source["sha256"], "model_version": MODEL_VERSION}
    public = {"route_reason": issuer["route_reason"], "reported_equity_php_millions": facts["reported_equity_php_millions"], "intrinsic_blocker": facts["intrinsic_blocker"], "policy_rationale": policy["rationale"], "reliability": "Low"}
    if "latest_interim_net_loss_php_millions" in facts:
        public["latest_interim_net_loss_php_millions"] = facts["latest_interim_net_loss_php_millions"]
    return PseValuationArtifact(model_version=MODEL_VERSION, ticker=ticker, issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]}, security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"}, subsector=issuer["subsector"], primary_model=issuer["primary_model"], valuation_date=date.fromisoformat(config["valuation_date"]), filing_period="FY 2025 and latest review", availability_type="market_relative_only", publication_state="provisional", scenarios={"bear": None, "base": None, "bull": None}, numerical_range={"low": min(estimates.values()), "high": max(estimates.values())}, market_relative=result, public_assumptions=public, sources=[source], warnings=["Screening-grade market-relative estimate; this is not the unresolved residual-income valuation.", "The disclosed bridge limitation is preserved rather than replaced with a fabricated intrinsic input."], blocking_reasons=[facts["intrinsic_blocker"]], input_hash=sha256_object(input_snapshot)).with_artifact_hash()


def build_batch_artifacts(config: dict[str, Any] | None = None) -> dict[str, PseValuationArtifact]:
    payload = config or load_batch_config()
    artifacts = {ticker: (_intrinsic_artifact(ticker, payload) if ticker in INTRINSIC_TICKERS else _relative_artifact(ticker, payload)) for ticker in FROZEN_BATCH_TICKERS}
    if tuple(artifacts) != FROZEN_BATCH_TICKERS:
        raise ValueError("Phase B Batch 5 artifact set does not match the frozen issuer set")
    return artifacts
