"""Config-driven artifact builder for frozen PSE V2 Phase B Batch 2."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from statistics import median
from typing import Any

from .contract import PseValuationArtifact, ScenarioValue, canonical_json, sha256_object
from .models.comparables import market_relative_range
from .models.fcff import fcff_valuation


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_02.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B02-1.0"
FROZEN_BATCH_TICKERS = ("URC", "CNPF", "MONDE", "JFC", "DNL", "PGOLD", "RRHI", "WLCON", "SEVN", "SSI")
INTRINSIC_TICKERS = ("URC", "CNPF", "MONDE", "JFC", "PGOLD", "RRHI", "WLCON", "SEVN")
RELATIVE_TICKERS = ("DNL", "SSI")


def load_batch_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "PSE-V2-PHASE-B-BATCH-2.0":
        raise ValueError("unsupported Phase B Batch 2 configuration")
    if tuple(payload.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Phase B Batch 2 issuer set differs from the confirmed frozen set")
    issuers = payload.get("issuers")
    if not isinstance(issuers, dict) or set(issuers) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Phase B Batch 2 must contain exactly the frozen ten issuers")
    for ticker in INTRINSIC_TICKERS:
        if issuers[ticker].get("availability") != "intrinsic_valuation":
            raise ValueError(f"{ticker}: intrinsic route classification drift")
    for ticker in RELATIVE_TICKERS:
        if issuers[ticker].get("availability") != "market_relative_only":
            raise ValueError(f"{ticker}: fallback route classification drift")
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
        "facts": issuer["facts"],
        "note": (
            "This deterministic receipt binds reviewed public facts, derivations, and the official source link. "
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
        "source_page": issuer["source"].get("source_page"),
        "sha256": digest,
    }
    return reference, raw


def _validate_intrinsic_facts(ticker: str, facts: dict[str, Any]) -> None:
    required = {
        "operating_cash_flow_php_millions",
        "capital_expenditures_php_millions",
        "normalized_fcff_proxy_php_millions",
        "cash_php_millions",
        "debt_php_millions",
        "shares_millions",
        "debt_includes_lease_liabilities",
    }
    missing = sorted(required - set(facts))
    if missing:
        raise ValueError(f"{ticker}: missing intrinsic facts: {', '.join(missing)}")
    if facts["debt_includes_lease_liabilities"] is not True:
        raise ValueError(f"{ticker}: debt bridge must explicitly include lease liabilities")
    periods = ("2023", "2024", "2025")
    owner_cash = [
        float(facts["operating_cash_flow_php_millions"][year])
        - float(facts["capital_expenditures_php_millions"][year])
        for year in periods
    ]
    normalized = float(facts["normalized_fcff_proxy_php_millions"])
    if abs(normalized - median(owner_cash)) > 1e-6:
        raise ValueError(f"{ticker}: normalized FCFF does not reconcile to the stated median policy")
    if normalized <= 0 or min(float(facts[key]) for key in ("cash_php_millions", "shares_millions")) <= 0:
        raise ValueError(f"{ticker}: FCFF, cash, and shares must be positive")
    if float(facts["debt_php_millions"]) < 0:
        raise ValueError(f"{ticker}: debt must not be negative")


def _intrinsic_artifact(ticker: str, config: dict[str, Any]) -> PseValuationArtifact:
    issuer = config["issuers"][ticker]
    facts = issuer["facts"]
    _validate_intrinsic_facts(ticker, facts)
    policy = config["fcff_policies"][issuer["policy"]]
    source, _receipt = source_receipt(ticker, config)
    normalized_fcff = float(facts["normalized_fcff_proxy_php_millions"])
    bridge = {
        "cash_php_millions": float(facts["cash_php_millions"]),
        "debt_php_millions": float(facts["debt_php_millions"]),
        "shares_millions": float(facts["shares_millions"]),
        "minority_value_php_millions": float(facts.get("minority_value_php_millions", 0.0)),
        "preferred_claims_php_millions": float(facts.get("preferred_claims_php_millions", 0.0)),
        "other_claims_php_millions": float(facts.get("other_claims_php_millions", 0.0)),
        "nonoperating_assets_php_millions": float(facts.get("nonoperating_assets_php_millions", 0.0)),
        "debt_includes_lease_liabilities": True,
    }
    scenarios: dict[str, ScenarioValue] = {}
    scenario_assumptions: dict[str, dict[str, float]] = {}

    for name in ("bear", "base", "bull"):
        assumptions = {key: float(value) for key, value in policy["scenarios"][name].items()}
        starting_nopat = normalized_fcff / (1 - assumptions["growth_rate"] / assumptions["roic"])
        valued = fcff_valuation(
            starting_nopat=starting_nopat,
            forecast_years=int(policy["forecast_years"]),
            cash=bridge["cash_php_millions"],
            nonoperating_assets=bridge["nonoperating_assets_php_millions"],
            debt=bridge["debt_php_millions"],
            preferred_claims=bridge["preferred_claims_php_millions"],
            minority_value=bridge["minority_value_php_millions"],
            other_claims=bridge["other_claims_php_millions"],
            shares_outstanding=bridge["shares_millions"],
            **assumptions,
        )
        if valued["common_equity_value"] <= 0 or valued["value_per_share"] <= 0:
            raise ValueError(f"{ticker} {name}: non-positive FCFF common-equity value")
        scenarios[name] = ScenarioValue(
            value_per_share=valued["value_per_share"],
            common_equity_value=valued["common_equity_value"],
            enterprise_value=valued["enterprise_value"],
        )
        scenario_assumptions[name] = assumptions

    values = [row.value_per_share for row in scenarios.values()]
    input_snapshot = {
        "ticker": ticker,
        "facts": facts,
        "policy": policy,
        "bridge": bridge,
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
        scenarios=scenarios,
        numerical_range={"low": min(values), "high": max(values)},
        public_assumptions={
            "forecast_years": int(policy["forecast_years"]),
            "normalized_fcff_proxy_php_millions": normalized_fcff,
            "normalization_method": facts["normalization_method"],
            "capital_bridge": bridge,
            "scenario_assumptions": scenario_assumptions,
            "macro_snapshot_version": config["macro_snapshot_version"],
            "policy_version": policy["version"],
            "route_reason": issuer["route_reason"],
            "reliability": "Low",
        },
        sensitivities=[
            {"type": "scenario_range", "drivers": ["normalized_fcff", "growth_rate", "roic", "wacc", "terminal_growth", "terminal_roic", "capital_bridge"]}
        ],
        sources=[source],
        warnings=[
            "Provisional Phase B estimate using a three-year median owner-cash proxy rather than a full issuer forecast.",
            "Lease liabilities are included in debt; lease principal is not separately deducted from the owner-cash proxy.",
            "Policy bands and terminal economics remain Low-reliability analyst assumptions pending a real filing refresh.",
            "The source hash binds the reviewed fact receipt; the remote filing is referenced but not redistributed in the candidate catalog.",
        ],
        blocking_reasons=[],
        input_hash=sha256_object(input_snapshot),
    ).with_artifact_hash()


def _relative_artifact(ticker: str, config: dict[str, Any]) -> PseValuationArtifact:
    issuer = config["issuers"][ticker]
    facts = issuer["facts"]
    policy = config["relative_policies"][ticker]
    source, _receipt = source_receipt(ticker, config)
    result = market_relative_range(
        metric=policy["metric"],
        metric_value_per_share=float(policy["metric_value_per_share"]),
        assumptions=policy["assumptions"],
        relation=policy["relation"],
    )
    result.update(
        {
            "policy_version": policy["policy_version"],
            "metric_label": policy["metric_label"],
            "source_status": "reviewed_public_fact",
            "source_document_sha256": source["sha256"],
            "source_page": source["source_page"],
            "note": "Transparent screening fallback while the specialist FCFF bridge remains unavailable.",
        }
    )
    estimates = result["estimates"]
    input_snapshot = {
        "ticker": ticker,
        "facts": facts,
        "policy": policy,
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
        availability_type="market_relative_only",
        publication_state="provisional",
        scenarios={"bear": None, "base": None, "bull": None},
        numerical_range={"low": min(estimates.values()), "high": max(estimates.values())},
        market_relative=result,
        public_assumptions={
            "route_reason": issuer["route_reason"],
            "intrinsic_blocker": facts["intrinsic_blocker"],
            "reliability": "Low",
        },
        sources=[source],
        warnings=[
            "Screening-grade market-relative estimate; this is not the unavailable specialist intrinsic valuation.",
            "The source-supported FCFF and lease-adjusted capital bridge remain unresolved.",
            "Policy bands are initial conventions and are not presented as an empirically validated issuer peer study.",
        ],
        blocking_reasons=[facts["intrinsic_blocker"]],
        input_hash=sha256_object(input_snapshot),
    ).with_artifact_hash()


def build_batch_artifacts(config: dict[str, Any] | None = None) -> dict[str, PseValuationArtifact]:
    payload = config or load_batch_config()
    artifacts: dict[str, PseValuationArtifact] = {}
    for ticker in FROZEN_BATCH_TICKERS:
        artifacts[ticker] = (
            _intrinsic_artifact(ticker, payload)
            if ticker in INTRINSIC_TICKERS
            else _relative_artifact(ticker, payload)
        )
    if tuple(artifacts) != FROZEN_BATCH_TICKERS:
        raise ValueError("Phase B Batch 2 artifact set does not match the frozen issuer set")
    return artifacts
