"""Reviewed, source-bounded Batch 12 property screens and merger block."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_12.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B12-1.0"
FROZEN_BATCH_TICKERS = ("CPG", "ROCK", "SHNG", "DD", "ALLHC", "CDC", "ARA", "PHES", "RLT", "BRN")
BLOCKED_TICKERS = ("CDC",)


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-12.0":
        raise ValueError("Batch 12 schema mismatch")
    if tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 12 confirmed frozen set mismatch")
    issuers = config.get("issuers", {})
    if set(issuers) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 12 must contain the exact ten issuers")
    for ticker, issuer in issuers.items():
        if issuer.get("primary_model") != "sotp":
            raise ValueError(f"{ticker}: property SOTP route is required")
        expected = "not_available" if ticker in BLOCKED_TICKERS else "market_relative_only"
        if issuer.get("availability") != expected:
            raise ValueError(f"{ticker}: availability classification drift")
        if issuer.get("policy") not in config["policies"]:
            raise ValueError(f"{ticker}: unknown policy")
        if issuer["source"].get("period_end") != "2026-06-30" or issuer["source"].get("currency") != "PHP":
            raise ValueError(f"{ticker}: source period or currency drift")
        if float(issuer["metric_value_per_share"]) <= 0:
            raise ValueError(f"{ticker}: non-positive reported book value")
    return config


def source_receipt(ticker: str, config: dict) -> tuple[list[dict], bytes]:
    issuer = config["issuers"][ticker]
    source = issuer["source"]
    supporting = issuer.get("supporting_source")
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0",
        "batch_version": config["batch_version"],
        "review_status": config["review_status"],
        "retrieval_date": config["valuation_date"],
        "ticker": ticker,
        "issuer_name": issuer["issuer_name"],
        "source": source,
        "supporting_source": supporting,
        "facts": {
            "metric_value_per_share": issuer["metric_value_per_share"],
            "metric_label": issuer["metric_label"],
            "normalization": issuer["normalization"],
            "intrinsic_blocker": issuer["intrinsic_blocker"],
        },
        "note": "This receipt binds manually reviewed public facts and links. It is not a copy of the remote filing or summary page.",
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    references = [
        {
            "document_id": digest[:16],
            "label": source["label"],
            "form": source.get("form"),
            "period_end": source.get("period_end"),
            "published_at": source.get("published_at"),
            "url": source["url"],
            "source_page": None,
            "sha256": digest,
        }
    ]
    if supporting:
        references.append(
            {
                "document_id": f"{digest[:16]}-support",
                "label": supporting["label"],
                "form": supporting.get("form"),
                "period_end": supporting.get("period_end"),
                "published_at": supporting.get("published_at"),
                "url": supporting["url"],
                "source_page": None,
                "sha256": digest,
            }
        )
    return references, raw


def build_batch_artifacts(config: dict | None = None) -> dict[str, PseValuationArtifact]:
    config = config or load_batch_config()
    output = {}
    for ticker in FROZEN_BATCH_TICKERS:
        issuer = config["issuers"][ticker]
        policy = config["policies"][issuer["policy"]]
        sources, _ = source_receipt(ticker, config)
        warnings = [issuer["source_warning"]] if issuer.get("source_warning") else []
        input_hash = sha256_object(
            {"ticker": ticker, "issuer": issuer, "policy": policy, "source": sources[0]["sha256"], "model_version": MODEL_VERSION}
        )
        common = {
            "model_version": MODEL_VERSION,
            "ticker": ticker,
            "issuer": {"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
            "security": {"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
            "subsector": issuer["subsector"],
            "primary_model": "sotp",
            "valuation_date": date.fromisoformat(config["valuation_date"]),
            "filing_period": issuer["source"]["period_end"],
            "scenarios": {"bear": None, "base": None, "bull": None},
            "sources": sources,
            "warnings": warnings,
            "blocking_reasons": [issuer["intrinsic_blocker"]],
            "input_hash": input_hash,
        }
        if ticker in BLOCKED_TICKERS:
            output[ticker] = PseValuationArtifact(
                **common,
                availability_type="not_available",
                publication_state="blocked",
                numerical_range={"low": None, "high": None},
                public_assumptions={
                    "route_reason": issuer["route_reason"],
                    "metric_basis": issuer["normalization"]["formula"],
                    "reliability": "Unavailable",
                },
            ).with_artifact_hash()
            continue
        relative = market_relative_range(
            metric=policy["metric"],
            metric_value_per_share=float(issuer["metric_value_per_share"]),
            assumptions=policy["assumptions"],
            relation=policy["relation"],
        )
        relative.update(
            {
                "policy_version": policy["version"],
                "metric_label": issuer["metric_label"],
                "source_status": "reviewed_public_fact",
                "source_document_sha256": sources[0]["sha256"],
                "source_page": None,
                "note": "Analyst screening band; no peer study or property-level RNAV has been completed.",
            }
        )
        estimates = relative["estimates"]
        output[ticker] = PseValuationArtifact(
            **common,
            availability_type="market_relative_only",
            publication_state="provisional",
            numerical_range={"low": min(estimates.values()), "high": max(estimates.values())},
            market_relative=relative,
            public_assumptions={
                "route_reason": issuer["route_reason"],
                "intrinsic_blocker": issuer["intrinsic_blocker"],
                "metric_basis": issuer["normalization"]["formula"],
                "policy_rationale": policy["rationale"],
                "reliability": "Low",
            },
        ).with_artifact_hash()
    return output
