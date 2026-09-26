"""Reviewed Batch 11 holding-company screening artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_11.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B11-1.0"
FROZEN_BATCH_TICKERS = ("SMC", "LTG", "AGI", "COSCO", "FDC", "FPH", "ANS", "LPZ", "APO", "TFHI")


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text())
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-11.0":
        raise ValueError("Batch 11 schema mismatch")
    if tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 11 confirmed frozen set mismatch")
    if set(config.get("issuers", {})) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 11 must contain the exact ten issuers")
    return config


def source_receipt(ticker: str, config: dict) -> tuple[dict, bytes]:
    issuer = config["issuers"][ticker]
    source = issuer["source"]
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0",
        "batch_version": config["batch_version"],
        "review_status": config["review_status"],
        "retrieval_date": config["valuation_date"],
        "ticker": ticker,
        "issuer_name": issuer["issuer_name"],
        "source": source,
        "relationship_source_url": issuer.get("relationship_source_url"),
        "facts": {
            "metric_value_per_share": issuer["metric_value_per_share"],
            "metric_label": issuer["metric_label"],
            "normalization": issuer["normalization"],
            "intrinsic_blocker": issuer["intrinsic_blocker"],
        },
        "note": "This receipt binds reviewed public facts and official source links. It is not a redistributed filing copy.",
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    return (
        {
            "document_id": digest[:16],
            "label": source["label"],
            "form": source.get("form"),
            "period_end": source.get("period_end"),
            "published_at": source.get("published_at"),
            "url": source["url"],
            "source_page": None,
            "sha256": digest,
        },
        raw,
    )


def build_batch_artifacts(config: dict | None = None) -> dict[str, PseValuationArtifact]:
    config = config or load_batch_config()
    output = {}
    for ticker in FROZEN_BATCH_TICKERS:
        issuer = config["issuers"][ticker]
        policy = config["policies"][issuer["policy"]]
        source, _ = source_receipt(ticker, config)
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
                "source_document_sha256": source["sha256"],
                "source_page": None,
                "note": "Analyst screening band; no peer study or attributable SOTP has been completed.",
            }
        )
        estimates = relative["estimates"]
        warnings = [
            "Screening-grade market-relative estimate; the component SOTP remains unresolved.",
            "Reported P/B does not establish attributable subsidiary value, parent-only claims, or a justified holding-company discount.",
        ]
        if issuer.get("source_warning"):
            warnings.append(issuer["source_warning"])
        output[ticker] = PseValuationArtifact(
            model_version=MODEL_VERSION,
            ticker=ticker,
            issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
            security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
            subsector=issuer["subsector"],
            primary_model="sotp",
            valuation_date=date.fromisoformat(config["valuation_date"]),
            filing_period=source["period_end"],
            availability_type="market_relative_only",
            publication_state="provisional",
            scenarios={"bear": None, "base": None, "bull": None},
            numerical_range={"low": min(estimates.values()), "high": max(estimates.values())},
            market_relative=relative,
            public_assumptions={
                "route_reason": issuer["route_reason"],
                "intrinsic_blocker": issuer["intrinsic_blocker"],
                "metric_basis": issuer["normalization"]["formula"],
                "policy_rationale": policy["rationale"],
                "reliability": "Low",
            },
            sources=[source],
            warnings=warnings,
            blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object(
                {
                    "ticker": ticker,
                    "issuer": issuer,
                    "policy": policy,
                    "source": source["sha256"],
                    "model_version": MODEL_VERSION,
                }
            ),
        ).with_artifact_hash()
    return output
