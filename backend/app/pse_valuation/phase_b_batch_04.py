"""Config-driven artifact builder for frozen PSE V2 Phase B Batch 4."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from .contract import PseValuationArtifact, ScenarioValue, canonical_json, sha256_object
from .models.comparables import market_relative_range
from .models.distributions import distribution_valuation


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_04.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B04-1.0"
FROZEN_BATCH_TICKERS = ("MER", "FGEN", "ACEN", "MWC", "SPC", "CREC", "ALTER", "ASLAG", "SPNEC", "MYNLD")
INTRINSIC_TICKERS = ("MER", "MWC", "SPC", "MYNLD")
RELATIVE_TICKERS = ("FGEN", "ACEN", "CREC", "ALTER", "ASLAG", "SPNEC")


def load_batch_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "PSE-V2-PHASE-B-BATCH-4.0":
        raise ValueError("unsupported Phase B Batch 4 configuration")
    if tuple(payload.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Phase B Batch 4 issuer set differs from the confirmed frozen set")
    issuers = payload.get("issuers")
    if not isinstance(issuers, dict) or set(issuers) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Phase B Batch 4 must contain exactly the frozen ten issuers")
    for ticker, issuer in issuers.items():
        expected = "intrinsic_valuation" if ticker in INTRINSIC_TICKERS else "market_relative_only"
        if issuer.get("availability") != expected:
            raise ValueError(f"{ticker}: Batch 4 route classification drift")
        policies = payload["distribution_policies"] if ticker in INTRINSIC_TICKERS else payload["relative_policies"]
        if issuer.get("policy") not in policies:
            raise ValueError(f"{ticker}: unknown Batch 4 policy")
        if not isinstance(issuer.get("sources"), list) or not issuer["sources"]:
            raise ValueError(f"{ticker}: at least one source is required")
    return payload


def source_receipts(ticker: str, config: dict[str, Any]) -> list[tuple[dict[str, Any], bytes]]:
    issuer = config["issuers"][ticker]
    receipts: list[tuple[dict[str, Any], bytes]] = []
    for index, source in enumerate(issuer["sources"], start=1):
        receipt = {
            "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0",
            "batch_version": config["batch_version"],
            "review_status": config["review_status"],
            "retrieval_date": config["valuation_date"],
            "ticker": ticker,
            "issuer_name": issuer["issuer_name"],
            "source_index": index,
            "source": source,
            "facts": issuer["facts"],
            "note": (
                "This deterministic receipt binds reviewed public facts, derivations, and the official source link. "
                "It is not a redistributed copy of the remote filing."
            ),
        }
        raw = canonical_json(receipt) + b"\n"
        digest = hashlib.sha256(raw).hexdigest()
        receipts.append(
            (
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
        )
    return receipts


def _intrinsic_artifact(ticker: str, config: dict[str, Any]) -> PseValuationArtifact:
    issuer = config["issuers"][ticker]
    facts = issuer["facts"]
    required = {"current_distribution_per_share", "shares_millions", "book_value_per_share", "reported_equity_php_millions"}
    missing = sorted(required - set(facts))
    if missing:
        raise ValueError(f"{ticker}: missing distribution facts: {', '.join(missing)}")
    distribution = float(facts["current_distribution_per_share"])
    shares = float(facts["shares_millions"])
    if distribution <= 0 or shares <= 0:
        raise ValueError(f"{ticker}: distribution and shares must be positive")
    policy = config["distribution_policies"][issuer["policy"]]
    finite_life = facts.get("finite_life_years")
    forecast_years = int(finite_life if finite_life is not None else policy["forecast_years"])
    sources = [reference for reference, _raw in source_receipts(ticker, config)]
    scenarios: dict[str, ScenarioValue] = {}
    scenario_assumptions: dict[str, dict[str, float]] = {}
    for name in ("bear", "base", "bull"):
        assumptions = {key: float(value) for key, value in policy["scenarios"][name].items()}
        valued = distribution_valuation(
            current_distribution_per_share=distribution,
            forecast_years=forecast_years,
            finite_life_years=forecast_years if finite_life is not None else None,
            **assumptions,
        )
        equity_value = valued["value_per_share"] * shares
        scenarios[name] = ScenarioValue(
            value_per_share=valued["value_per_share"],
            common_equity_value=equity_value,
            enterprise_value=None,
        )
        scenario_assumptions[name] = assumptions
    values = [row.value_per_share for row in scenarios.values()]
    input_snapshot = {
        "ticker": ticker,
        "facts": facts,
        "policy": policy,
        "source_receipt_sha256": [source["sha256"] for source in sources],
        "model_version": MODEL_VERSION,
    }
    warnings = [
        "Provisional common-distribution valuation; it is not a substitute for the unresolved asset-level or regulated FCFF model.",
        "The current payout and growth policy remain Low-reliability analyst assumptions pending a real filing refresh.",
        "The source hashes bind reviewed fact receipts; remote filings are referenced but not redistributed in the candidate catalog.",
    ]
    if finite_life is not None:
        warnings.append("No terminal value is assigned beyond the documented franchise or concession expiry.")
    return PseValuationArtifact(
        model_version=MODEL_VERSION,
        ticker=ticker,
        issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
        security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
        subsector=issuer["subsector"],
        primary_model="sustainable_distributions",
        valuation_date=date.fromisoformat(config["valuation_date"]),
        filing_period="FY 2025",
        availability_type="intrinsic_valuation",
        publication_state="provisional",
        scenarios=scenarios,
        numerical_range={"low": min(values), "high": max(values)},
        public_assumptions={
            "current_distribution_per_share": distribution,
            "distribution_derivation": facts["distribution_derivation"],
            "forecast_years": forecast_years,
            "finite_life_years": int(finite_life) if finite_life is not None else None,
            "expiry_date": facts.get("expiry_date"),
            "scenario_assumptions": scenario_assumptions,
            "policy_version": policy["version"],
            "policy_rationale": policy["rationale"],
            "route_reason": issuer["route_reason"],
            "reliability": "Low",
        },
        sensitivities=[{"type": "scenario_range", "drivers": ["current_distribution_per_share", "explicit_growth", "cost_of_equity", "documented_expiry"]}],
        sources=sources,
        warnings=warnings,
        blocking_reasons=[],
        input_hash=sha256_object(input_snapshot),
    ).with_artifact_hash()


def _relative_artifact(ticker: str, config: dict[str, Any]) -> PseValuationArtifact:
    issuer = config["issuers"][ticker]
    facts = issuer["facts"]
    book_value = float(facts["book_value_per_share"])
    equity = float(facts["reported_equity_php_millions"])
    if book_value <= 0 or equity <= 0:
        raise ValueError(f"{ticker}: reported book value and equity must be positive")
    policy = config["relative_policies"][issuer["policy"]]
    sources = [reference for reference, _raw in source_receipts(ticker, config)]
    result = market_relative_range(
        metric=policy["metric"],
        metric_value_per_share=book_value,
        assumptions=policy["assumptions"],
        relation=policy["relation"],
    )
    result.update(
        {
            "policy_version": policy["policy_version"],
            "metric_label": "FY2025 reported book value per common share",
            "source_status": "reviewed_public_fact",
            "source_document_sha256": sources[0]["sha256"],
            "source_page": sources[0]["source_page"],
            "note": "Transparent P/B screen while the asset-level FCFF or SOTP bridge remains incomplete.",
        }
    )
    estimates = result["estimates"]
    input_snapshot = {
        "ticker": ticker,
        "facts": facts,
        "policy": policy,
        "source_receipt_sha256": [source["sha256"] for source in sources],
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
            "reported_equity_php_millions": equity,
            "intrinsic_blocker": facts["intrinsic_blocker"],
            "policy_rationale": policy["rationale"],
            "source_currency": facts["source_currency"],
            "reliability": "Low",
        },
        sources=sources,
        warnings=[
            "Screening-grade market-relative estimate; this is not the unresolved asset-level intrinsic valuation.",
            "Reported book value is an accounting measure and may differ materially from project fair value.",
            "The policy band is a transparent initial convention, not a completed issuer peer study.",
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
        raise ValueError("Phase B Batch 4 artifact set does not match the frozen issuer set")
    return artifacts
