from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_09.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B09-1.0"
FROZEN_BATCH_TICKERS = ("FB", "EMI", "GSMI", "RFM", "MAXS", "PIZZA", "DELM", "VITA", "ANI", "CAT")


def load_batch_config(path: Path = CONFIG_PATH):
    payload = json.loads(path.read_text())
    if payload.get("schema_version") != "PSE-V2-PHASE-B-BATCH-9.0":
        raise ValueError("Batch 9 schema mismatch")
    if tuple(payload.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 9 confirmed frozen set mismatch")
    if set(payload.get("issuers", {})) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 9 must contain exact ten")
    return payload


def source_receipt(ticker, config):
    issuer = config["issuers"][ticker]
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0",
        "batch_version": config["batch_version"],
        "review_status": config["review_status"],
        "retrieval_date": config["valuation_date"],
        "ticker": ticker,
        "issuer_name": issuer["issuer_name"],
        "source": issuer["source"],
        "facts": {"metric_value_per_share": issuer["metric_value_per_share"], "metric_label": issuer["metric_label"], "normalization": issuer["normalization"], "intrinsic_blocker": issuer["intrinsic_blocker"]},
        "note": "This deterministic receipt binds reviewed public facts, normalization, and official source links. It is not a redistributed filing copy.",
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    source = issuer["source"]
    return ({"document_id": digest[:16], "label": source["label"], "form": source.get("form"), "period_end": source.get("period_end"), "published_at": source.get("published_at"), "url": source["url"], "source_page": None, "sha256": digest}, raw)


def build_batch_artifacts(config=None):
    config = config or load_batch_config()
    output = {}
    for ticker in FROZEN_BATCH_TICKERS:
        issuer = config["issuers"][ticker]
        policy = config["policies"][issuer["policy"]]
        source, _ = source_receipt(ticker, config)
        relative = market_relative_range(metric=policy["metric"], metric_value_per_share=float(issuer["metric_value_per_share"]), assumptions=policy["assumptions"], relation=policy["relation"])
        relative.update({"policy_version": policy["version"], "metric_label": issuer["metric_label"], "source_status": "reviewed_public_fact", "source_document_sha256": source["sha256"], "source_page": None, "note": "Transparent screening fallback while the specialist intrinsic bridge remains incomplete."})
        estimates = relative["estimates"]
        warnings = ["Screening-grade market-relative estimate; this is not the unresolved specialist intrinsic valuation.", "Input costs, consumer demand, margins, working capital, and capital claims can materially change value and are not replaced by this screening band."]
        if issuer.get("source_warning"):
            warnings.append(issuer["source_warning"])
        output[ticker] = PseValuationArtifact(
            model_version=MODEL_VERSION,
            ticker=ticker,
            issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
            security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
            subsector=issuer["subsector"],
            primary_model=issuer["primary_model"],
            valuation_date=date.fromisoformat(config["valuation_date"]),
            filing_period=source["period_end"],
            availability_type="market_relative_only",
            publication_state="provisional",
            scenarios={"bear": None, "base": None, "bull": None},
            numerical_range={"low": min(estimates.values()), "high": max(estimates.values())},
            market_relative=relative,
            public_assumptions={"route_reason": issuer["route_reason"], "intrinsic_blocker": issuer["intrinsic_blocker"], "metric_basis": issuer["normalization"]["formula"], "reliability": "Low"},
            sources=[source],
            warnings=warnings,
            blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object({"ticker": ticker, "issuer": issuer, "policy": policy, "source": source["sha256"], "model_version": MODEL_VERSION}),
        ).with_artifact_hash()
    return output
