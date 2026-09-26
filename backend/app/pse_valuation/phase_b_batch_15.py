"""Reviewed Batch 15 property screens and the delisted HOUSE block."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_15.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B15-1.0"
FROZEN_BATCH_TICKERS = ("ALCO", "ALHI", "APVI", "CEI", "ELI", "GERI", "HOUSE", "KPPI", "PRMX", "SLI")
BLOCKED_TICKERS = ("HOUSE",)
SOURCE_PERIODS = {"ALCO": "2026-03-31", "HOUSE": "2025-06-30"}


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-15.0" or tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 15 schema or confirmed frozen set mismatch")
    issuers = config.get("issuers", {})
    if set(issuers) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 15 must contain exactly the confirmed ten issuers")
    policy = config["policy"]
    if policy.get("metric") != "price_to_book" or policy.get("relation") != "multiple" or policy.get("assumptions") != {"low": 0.30, "base": 0.45, "high": 0.60}:
        raise ValueError("Batch 15 property policy differs from reviewed band")
    for ticker, issuer in issuers.items():
        if issuer.get("primary_model") != "sotp" or issuer.get("availability") != ("not_available" if ticker in BLOCKED_TICKERS else "market_relative_only"):
            raise ValueError(f"{ticker}: route or availability differs from frozen review")
        source = issuer["source"]
        period = SOURCE_PERIODS.get(ticker, "2026-06-30")
        fact = issuer["reported_bvps"]
        if source.get("period_end") != period or fact.get("period_end") != period or source.get("currency") != "PHP" or source.get("units") != "per share":
            raise ValueError(f"{ticker}: source period, currency or units differ")
        if fact.get("period_type") != ("historical_interim" if ticker in BLOCKED_TICKERS else "interim") or float(fact.get("value", 0)) <= 0 or abs(float(issuer["metric_value_per_share"]) - float(fact["value"])) > 1e-9:
            raise ValueError(f"{ticker}: original reported BVPS does not reconcile")
    house = issuers["HOUSE"]["supporting_source"]
    if house.get("period_end") != "2025-10-31" or house.get("url") != "https://edge.pse.com.ph/downloadHtml.do?file_id=1827603":
        raise ValueError("HOUSE delisting evidence differs from reviewed notice")
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
        "facts": {"reported_bvps": issuer["reported_bvps"], "metric_value_per_share": issuer["metric_value_per_share"], "metric_label": issuer["metric_label"], "intrinsic_blocker": issuer["intrinsic_blocker"]},
        "note": "This receipt binds manually reviewed public facts and links; it is not a copy of a remote filing or summary page.",
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    references = [{"document_id": digest[:16], "label": source["label"], "form": source["form"], "period_end": source["period_end"], "published_at": None, "url": source["url"], "source_page": None, "sha256": digest}]
    if supporting:
        references.append({"document_id": f"{digest[:16]}-support", "label": supporting["label"], "form": supporting["form"], "period_end": supporting["period_end"], "published_at": None, "url": supporting["url"], "source_page": None, "sha256": digest})
    return references, raw


def build_batch_artifacts(config: dict | None = None) -> dict[str, PseValuationArtifact]:
    config = config or load_batch_config()
    policy = config["policy"]
    output = {}
    for ticker in FROZEN_BATCH_TICKERS:
        issuer = config["issuers"][ticker]
        sources, _ = source_receipt(ticker, config)
        warnings = ["Reported book value is not a completed property RNAV or peer-calibrated target."]
        if issuer.get("source_warning"):
            warnings.append(issuer["source_warning"])
        common = dict(
            model_version=MODEL_VERSION, ticker=ticker,
            issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
            security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
            subsector=issuer["subsector"], primary_model="sotp",
            valuation_date=date.fromisoformat(config["valuation_date"]), filing_period=issuer["source"]["period_end"],
            scenarios={"bear": None, "base": None, "bull": None}, sources=sources, warnings=warnings,
            blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object({"ticker": ticker, "issuer": issuer, "policy": policy if ticker not in BLOCKED_TICKERS else None, "source": sources[0]["sha256"], "model_version": MODEL_VERSION}),
        )
        if ticker in BLOCKED_TICKERS:
            output[ticker] = PseValuationArtifact(
                **common, availability_type="not_available", publication_state="blocked",
                numerical_range={"low": None, "high": None},
                public_assumptions={"route_reason": issuer["route_reason"], "metric_basis": "Historical pre-delisting reported BVPS, not a current per-share estimate", "listing_status": "delisted", "reliability": "Unavailable"},
            ).with_artifact_hash()
            continue
        relative = market_relative_range(metric=policy["metric"], metric_value_per_share=float(issuer["metric_value_per_share"]), assumptions=policy["assumptions"], relation=policy["relation"])
        relative["estimates"] = {key: round(value, 9) for key, value in relative["estimates"].items()}
        relative.update({"policy_version": policy["version"], "metric_label": issuer["metric_label"], "source_status": "reviewed_public_fact", "source_document_sha256": sources[0]["sha256"], "source_page": None, "note": "Finite analyst screening band; no peer study or property-level RNAV has been completed."})
        estimates = relative["estimates"]
        output[ticker] = PseValuationArtifact(
            **common, availability_type="market_relative_only", publication_state="provisional",
            numerical_range={"low": min(estimates.values()), "high": max(estimates.values())}, market_relative=relative,
            public_assumptions={"route_reason": issuer["route_reason"], "intrinsic_blocker": issuer["intrinsic_blocker"], "metric_basis": "PSE-reported PHP book value per share; no property fair-value adjustment", "policy_rationale": policy["rationale"], "reliability": "Low"},
        ).with_artifact_hash()
    return output
