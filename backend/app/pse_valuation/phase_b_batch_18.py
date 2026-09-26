"""Reviewed Batch 18 bank, holding-company and operating-service screens."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_18.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B18-1.0"
FROZEN_BATCH_TICKERS = ("PBC", "PTC", "V", "BKR", "APC", "IPM", "SGI", "CTS", "REG", "ECP")
ROUTES = {"residual_income", "sotp", "fcff_dcf"}


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-18.0" or tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 18 schema or confirmed frozen set mismatch")
    issuers = config.get("issuers", {})
    if set(issuers) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 18 must contain exactly the confirmed ten issuers")
    for ticker, issuer in issuers.items():
        source = issuer["source"]
        policy = config["policies"].get(issuer.get("policy"))
        kind = issuer.get("metric_kind")
        if issuer.get("primary_model") not in ROUTES or kind not in {"reported_bvps", "derived_parent_bvps"} or policy is None or policy.get("metric") != "price_to_book":
            raise ValueError(f"{ticker}: unsupported route, metric or policy")
        if source["currency"] != "PHP" or date.fromisoformat(source["period_end"]) > date.fromisoformat(config["valuation_date"]):
            raise ValueError(f"{ticker}: source currency or period mismatch")
        if kind == "reported_bvps":
            fact = issuer["reported_bvps"]
            if source["units"] != "per_share" or fact["period_end"] != source["period_end"] or fact["period_type"] != "interim":
                raise ValueError(f"{ticker}: reported BVPS source or period mismatch")
            expected = float(fact["value"])
        else:
            parent = issuer["reported_parent_equity"]
            shares = issuer["reported_shares"]
            total_bvps = issuer["reported_total_bvps"]
            if (parent["period_end"] != source["period_end"] or parent["period_type"] != "interim"
                    or parent["unit_scale"] not in {"pesos", "thousands"}
                    or total_bvps["period_end"] != source["period_end"] or total_bvps["period_type"] != "interim"
                    or shares["security_type"] != "ordinary_common" or float(shares["value"]) <= 0
                    or date.fromisoformat(shares["as_of"]) > date.fromisoformat(config["valuation_date"])):
                raise ValueError(f"{ticker}: parent capital or common-share period mismatch")
            scale = 1000.0 if parent["unit_scale"] == "thousands" else 1.0
            expected = float(parent["value"]) * scale / float(shares["value"])
            if expected >= float(total_bvps["value"]):
                raise ValueError(f"{ticker}: reviewed parent BVPS no longer differs from total BVPS")
        if expected <= 0 or abs(float(issuer["metric_value_per_share"]) - expected) > 1e-9 or abs(float(issuer["normalization"]["normalized_value"]) - expected) > 1e-9:
            raise ValueError(f"{ticker}: reported and normalized per-share values do not reconcile")
        if issuer["normalization"]["original_currency"] != "PHP" or issuer["normalization"]["normalized_currency"] != "PHP":
            raise ValueError(f"{ticker}: original currency was lost")
    return config


def source_receipt(ticker: str, config: dict) -> tuple[list[dict], bytes]:
    issuer = config["issuers"][ticker]
    source = issuer["source"]
    supporting = issuer.get("supporting_sources", [])
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0", "batch_version": config["batch_version"],
        "review_status": config["review_status"], "retrieval_date": config["valuation_date"],
        "ticker": ticker, "issuer_name": issuer["issuer_name"], "source": source,
        "supporting_sources": supporting,
        "facts": {"reported_bvps": issuer.get("reported_bvps"), "reported_total_bvps": issuer.get("reported_total_bvps"), "reported_parent_equity": issuer.get("reported_parent_equity"), "reported_shares": issuer.get("reported_shares"), "metric_value_per_share": issuer["metric_value_per_share"], "metric_label": issuer["metric_label"], "normalization": issuer["normalization"], "intrinsic_blocker": issuer["intrinsic_blocker"]},
        "note": "This receipt binds manually reviewed public facts and links; it is not a copy of the remote filing or summary page.",
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    references = [{"document_id": digest[:16], "label": source["label"], "form": source["form"], "period_end": source["period_end"], "published_at": None, "url": source["url"], "source_page": None, "sha256": digest}]
    for index, extra in enumerate(supporting, start=1):
        references.append({"document_id": f"{digest[:16]}-support-{index}", "label": extra["label"], "form": extra["form"], "period_end": extra.get("period_end"), "published_at": None, "url": extra["url"], "source_page": None, "sha256": digest})
    return references, raw


def build_batch_artifacts(config: dict | None = None) -> dict[str, PseValuationArtifact]:
    config = config or load_batch_config()
    output = {}
    for ticker in FROZEN_BATCH_TICKERS:
        issuer = config["issuers"][ticker]
        policy = config["policies"][issuer["policy"]]
        sources, _ = source_receipt(ticker, config)
        relative = market_relative_range(metric="price_to_book", metric_value_per_share=float(issuer["metric_value_per_share"]), assumptions=policy["assumptions"], relation="multiple")
        relative["estimates"] = {key: round(value, 9) for key, value in relative["estimates"].items()}
        relative.update({"policy_version": policy["version"], "metric_label": issuer["metric_label"], "source_status": "reviewed_public_fact", "source_document_sha256": sources[0]["sha256"], "source_page": None, "note": "Finite analyst screening band; no peer study or complete intrinsic valuation has been completed."})
        estimates = relative["estimates"]
        warnings = ["Screening-grade market-relative result, not intrinsic value or a peer-calibrated target.", "Common-equity claims, normalized earnings and asset or cash-flow economics are not fully reconciled."]
        if issuer.get("source_warning"):
            warnings.append(issuer["source_warning"])
        output[ticker] = PseValuationArtifact(
            model_version=MODEL_VERSION, ticker=ticker,
            issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
            security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
            subsector=issuer["subsector"], primary_model=issuer["primary_model"],
            valuation_date=date.fromisoformat(config["valuation_date"]), filing_period=issuer["source"]["period_end"],
            availability_type="market_relative_only", publication_state="provisional",
            scenarios={"bear": None, "base": None, "bull": None},
            numerical_range={"low": min(estimates.values()), "high": max(estimates.values())}, market_relative=relative,
            public_assumptions={"route_reason": issuer["route_reason"], "intrinsic_blocker": issuer["intrinsic_blocker"], "metric_basis": issuer["normalization"]["formula"], "policy_rationale": policy["rationale"], "reliability": "Low"},
            sources=sources, warnings=warnings, blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object({"ticker": ticker, "issuer": issuer, "policy": policy, "source": sources[0]["sha256"], "model_version": MODEL_VERSION}),
        ).with_artifact_hash()
    return output
