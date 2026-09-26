"""Source-bounded Batch 13 manufacturing and industrial-supply screens."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_13.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B13-1.0"
FROZEN_BATCH_TICKERS = ("IMI", "TECH", "ION", "CIC", "MVC", "CROWN", "STN", "LFM", "VMC", "SBS")
USD_TICKERS = ("IMI", "TECH", "ION")


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-13.0":
        raise ValueError("Batch 13 schema mismatch")
    if tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 13 confirmed frozen set mismatch")
    issuers = config.get("issuers", {})
    if set(issuers) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 13 must contain the exact ten issuers")
    fx = config["fx_snapshot"]
    if fx.get("pair") != "USD/PHP" or fx.get("observed_at") != config["valuation_date"] or float(fx.get("rate_php_per_usd", 0)) <= 0:
        raise ValueError("Batch 13 USD/PHP snapshot is missing or mismatched")
    for ticker, issuer in issuers.items():
        if issuer.get("primary_model") not in {"fcff_dcf", "sotp"} or issuer.get("policy") not in config["policies"]:
            raise ValueError(f"{ticker}: route or policy is unsupported")
        source = issuer["source"]
        if source.get("currency") != ("USD" if ticker in USD_TICKERS else "PHP"):
            raise ValueError(f"{ticker}: reported currency differs from the source review")
        if source.get("period_end") != ("2026-05-31" if ticker == "VMC" else "2026-06-30"):
            raise ValueError(f"{ticker}: reporting period differs from the reviewed source")
        normalization = issuer["normalization"]
        original = float(normalization["original_value"])
        working = float(issuer["metric_value_per_share"])
        expected = original * float(fx["rate_php_per_usd"]) if ticker in USD_TICKERS else original
        if original <= 0 or abs(working - expected) > 1e-9 or abs(float(normalization["normalized_value"]) - expected) > 1e-9:
            raise ValueError(f"{ticker}: original and PHP per-share values do not reconcile")
        if ticker in USD_TICKERS and (
            float(normalization.get("fx_rate", 0)) != float(fx["rate_php_per_usd"])
            or normalization.get("fx_rate_date") != fx["observed_at"]
        ):
            raise ValueError(f"{ticker}: source FX observation differs from the reviewed snapshot")
    return config


def source_receipt(ticker: str, config: dict) -> tuple[list[dict], bytes]:
    issuer = config["issuers"][ticker]
    source = issuer["source"]
    supporting = issuer.get("supporting_source")
    fx = config["fx_snapshot"] if ticker in USD_TICKERS else None
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0",
        "batch_version": config["batch_version"],
        "review_status": config["review_status"],
        "retrieval_date": config["valuation_date"],
        "ticker": ticker,
        "issuer_name": issuer["issuer_name"],
        "source": source,
        "supporting_source": supporting,
        "fx_snapshot": fx,
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
    if fx:
        references.append(
            {
                "document_id": f"{digest[:16]}-fx",
                "label": fx["source_label"],
                "form": "BSP exchange-rate observation",
                "period_end": fx["observed_at"],
                "published_at": None,
                "url": fx["source_url"],
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
                "note": "Analyst screening band; no peer study or complete intrinsic FCFF/SOTP has been completed.",
            }
        )
        estimates = relative["estimates"]
        warnings = [
            "Screening-grade market-relative P/B; the operating FCFF or attributable SOTP remains unresolved.",
            "Reported book value per share does not establish a common-equity claim bridge or a peer-calibrated multiple.",
        ]
        if issuer.get("source_warning"):
            warnings.append(issuer["source_warning"])
        fx_assumptions = (
            {"fx_rate_php_per_usd": config["fx_snapshot"]["rate_php_per_usd"], "fx_observed_at": config["fx_snapshot"]["observed_at"]}
            if ticker in USD_TICKERS else {}
        )
        output[ticker] = PseValuationArtifact(
            model_version=MODEL_VERSION,
            ticker=ticker,
            issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
            security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
            subsector=issuer["subsector"],
            primary_model=issuer["primary_model"],
            valuation_date=date.fromisoformat(config["valuation_date"]),
            filing_period=issuer["source"]["period_end"],
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
                **fx_assumptions,
            },
            sources=sources,
            warnings=warnings,
            blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object(
                {
                    "ticker": ticker,
                    "issuer": issuer,
                    "policy": policy,
                    "fx_snapshot": config["fx_snapshot"] if ticker in USD_TICKERS else None,
                    "source": sources[0]["sha256"],
                    "model_version": MODEL_VERSION,
                }
            ),
        ).with_artifact_hash()
    return output
