"""Config-driven artifact builder for frozen PSE V2 Phase B Batch 3."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from .contract import PseValuationArtifact, ScenarioValue, canonical_json, sha256_object
from .models.comparables import market_relative_range
from .models.sotp import sotp_valuation


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_03.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B03-1.0"
FROZEN_BATCH_TICKERS = ("SM", "AEV", "JGS", "GTCAP", "DMC", "SMPH", "RLC", "MEG", "FLI", "CLI")
INTRINSIC_TICKERS = ("SMPH", "RLC", "FLI")
RELATIVE_TICKERS = ("SM", "AEV", "JGS", "GTCAP", "DMC", "MEG", "CLI")


def load_batch_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "PSE-V2-PHASE-B-BATCH-3.0":
        raise ValueError("unsupported Phase B Batch 3 configuration")
    if tuple(payload.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Phase B Batch 3 issuer set differs from the confirmed frozen set")
    issuers = payload.get("issuers")
    if not isinstance(issuers, dict) or set(issuers) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Phase B Batch 3 must contain exactly the frozen ten issuers")
    relative_policies = payload.get("relative_policies", {})
    nav_policies = payload.get("nav_policies", {})
    for ticker, issuer in issuers.items():
        if issuer.get("primary_model") != "sotp":
            raise ValueError(f"{ticker}: SOTP/NAV must remain the primary intrinsic route")
        expected = "intrinsic_valuation" if ticker in INTRINSIC_TICKERS else "market_relative_only"
        if issuer.get("availability") != expected:
            raise ValueError(f"{ticker}: Batch 3 route classification drift")
        policies = nav_policies if ticker in INTRINSIC_TICKERS else relative_policies
        if issuer.get("policy") not in policies:
            raise ValueError(f"{ticker}: unknown relative policy")
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
    source = issuer["source"]
    return (
        {
            "document_id": digest[:16],
            "label": source["label"],
            "form": source.get("form"),
            "period_end": source.get("period_end"),
            "published_at": source.get("published_at"),
            "url": source["url"],
            "source_page": source.get("source_page"),
            "sha256": digest,
        },
        raw,
    )


def _intrinsic_artifact(ticker: str, config: dict[str, Any]) -> PseValuationArtifact:
    issuer = config["issuers"][ticker]
    facts = issuer["facts"]
    required = {
        "parent_equity_php_millions",
        "investment_property_carrying_value_php_millions",
        "investment_property_fair_value_php_millions",
        "preferred_claims_php_millions",
        "shares_millions",
    }
    missing = sorted(required - set(facts))
    if missing:
        raise ValueError(f"{ticker}: missing RNAV facts: {', '.join(missing)}")
    parent_equity = float(facts["parent_equity_php_millions"])
    carrying_value = float(facts["investment_property_carrying_value_php_millions"])
    fair_value = float(facts["investment_property_fair_value_php_millions"])
    preferred_claims = float(facts["preferred_claims_php_millions"])
    shares = float(facts["shares_millions"])
    if min(parent_equity, carrying_value, fair_value, shares) <= 0 or preferred_claims < 0:
        raise ValueError(f"{ticker}: RNAV bridge values are invalid")
    if fair_value <= carrying_value:
        raise ValueError(f"{ticker}: investment-property fair value must exceed carrying value")
    source, _receipt = source_receipt(ticker, config)
    policy = config["nav_policies"][issuer["policy"]]
    raw_uplift = fair_value - carrying_value
    scenarios: dict[str, ScenarioValue] = {}
    scenario_assumptions: dict[str, dict[str, float]] = {}
    for name in ("bear", "base", "bull"):
        assumptions = {key: float(value) for key, value in policy["scenarios"][name].items()}
        adjusted_uplift = raw_uplift * assumptions["uplift_realization"] * (1 - assumptions["tax_leakage"])
        valued = sotp_valuation(
            components=[
                {"name": "reported_parent_equity", "equity_value": parent_equity, "ownership": 1.0},
                {"name": "after_tax_property_fair_value_uplift", "equity_value": adjusted_uplift, "ownership": 1.0},
            ],
            shares_outstanding=shares,
            other_parent_claims=preferred_claims,
        )
        scenarios[name] = ScenarioValue(
            value_per_share=valued["value_per_share"],
            common_equity_value=valued["common_equity_value"],
            enterprise_value=None,
        )
        scenario_assumptions[name] = assumptions
    values = [row.value_per_share for row in scenarios.values()]
    nav_bridge = {
        "parent_equity_php_millions": parent_equity,
        "investment_property_carrying_value_php_millions": carrying_value,
        "investment_property_fair_value_php_millions": fair_value,
        "preferred_claims_php_millions": preferred_claims,
        "shares_millions": shares,
    }
    input_snapshot = {
        "ticker": ticker,
        "facts": facts,
        "policy": policy,
        "nav_bridge": nav_bridge,
        "source_receipt_sha256": source["sha256"],
        "model_version": MODEL_VERSION,
    }
    return PseValuationArtifact(
        model_version=MODEL_VERSION,
        ticker=ticker,
        issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
        security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
        subsector=issuer["subsector"],
        primary_model="sotp",
        valuation_date=date.fromisoformat(config["valuation_date"]),
        filing_period="FY 2025",
        availability_type="intrinsic_valuation",
        publication_state="provisional",
        scenarios=scenarios,
        numerical_range={"low": min(values), "high": max(values)},
        public_assumptions={
            "nav_bridge": nav_bridge,
            "scenario_assumptions": scenario_assumptions,
            "policy_version": policy["version"],
            "policy_rationale": policy["rationale"],
            "route_reason": issuer["route_reason"],
            "reliability": "Low",
        },
        sensitivities=[
            {"type": "scenario_range", "drivers": ["investment_property_fair_value", "uplift_realization", "tax_leakage", "preferred_claims"]}
        ],
        sources=[source],
        warnings=[
            "Provisional property RNAV using reported parent equity plus a risk-adjusted investment-property fair-value uplift.",
            "The fair-value uplift is Level 3 or otherwise appraisal-dependent and may not be realized at the reported amount.",
            "The model does not separately revalue development inventory, associates, or assets outside the disclosed investment-property portfolio.",
            "The source hash binds the reviewed fact receipt; the remote filing is referenced but not redistributed in the candidate catalog.",
        ],
        blocking_reasons=[],
        input_hash=sha256_object(input_snapshot),
    ).with_artifact_hash()


def _relative_artifact(ticker: str, config: dict[str, Any]) -> PseValuationArtifact:
    issuer = config["issuers"][ticker]
    facts = issuer["facts"]
    book_value = float(facts["book_value_per_share"])
    parent_equity = float(facts["parent_equity_php_millions"])
    if book_value <= 0 or parent_equity <= 0:
        raise ValueError(f"{ticker}: reported book value and parent equity must be positive")
    policy = config["relative_policies"][issuer["policy"]]
    source, _receipt = source_receipt(ticker, config)
    result = market_relative_range(
        metric=policy["metric"],
        metric_value_per_share=book_value,
        assumptions=policy["assumptions"],
        relation=policy["relation"],
    )
    result.update(
        {
            "policy_version": policy["policy_version"],
            "metric_label": "FY2025 reported parent book value per common share",
            "source_status": "reviewed_public_fact",
            "source_document_sha256": source["sha256"],
            "source_page": source["source_page"],
            "note": "Transparent P/B-to-reported-NAV screen while the component-level SOTP or property RNAV remains incomplete.",
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
            "reported_parent_equity_php_millions": parent_equity,
            "intrinsic_blocker": facts["intrinsic_blocker"],
            "policy_rationale": policy["rationale"],
            "reliability": "Low",
        },
        sources=[source],
        warnings=[
            "Screening-grade market-relative estimate; this is not the unresolved component SOTP or property RNAV.",
            "Reported book value is an accounting measure and may differ materially from current asset fair value.",
            "The policy band is a transparent initial convention, not a completed issuer peer study.",
            "The source hash binds the reviewed fact receipt; the remote filing is referenced but not redistributed in the candidate catalog.",
        ],
        blocking_reasons=[facts["intrinsic_blocker"]],
        input_hash=sha256_object(input_snapshot),
    ).with_artifact_hash()


def build_batch_artifacts(config: dict[str, Any] | None = None) -> dict[str, PseValuationArtifact]:
    payload = config or load_batch_config()
    artifacts = {
        ticker: (
            _intrinsic_artifact(ticker, payload)
            if ticker in INTRINSIC_TICKERS
            else _relative_artifact(ticker, payload)
        )
        for ticker in FROZEN_BATCH_TICKERS
    }
    if tuple(artifacts) != FROZEN_BATCH_TICKERS:
        raise ValueError("Phase B Batch 3 artifact set does not match the frozen issuer set")
    return artifacts
