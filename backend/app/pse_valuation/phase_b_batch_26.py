"""Reviewed, source-bounded PSE Batch 26 suspension and claim screens."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_26.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B26-1.0"
FROZEN_BATCH_TICKERS = ("DHI", "HOME", "MM", "STR", "VLC", "UNH", "PNX", "ROX", "INFRA", "I")
SCALES = {"pesos": 1, "thousands": 1_000, "millions": 1_000_000}


def equity_per_share(issuer: dict) -> float:
    if issuer["currency"] != "PHP" or issuer["equity_value"] is None or issuer["shares_outstanding"] is None:
        raise ValueError("PHP common book requires reported equity and reviewed shares")
    return float(issuer["equity_value"]) * SCALES[issuer["equity_unit_scale"]] / float(issuer["shares_outstanding"])


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-26.0" or tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 26 schema or confirmed issuer set mismatch")
    if set(config.get("issuers", {})) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 26 must contain exactly the confirmed ten issuers")
    valuation_date = date.fromisoformat(config["valuation_date"])
    for ticker, issuer in config["issuers"].items():
        if issuer.get("primary_model") not in {"nav_sotp", "sotp", "fcff_dcf", "residual_income", "sustainable_distributions"}:
            raise ValueError(f"{ticker}: unsupported primary route")
        if issuer.get("availability") not in {"market_relative_only", "not_available"} or not issuer.get("source_warning") or not issuer.get("intrinsic_blocker"):
            raise ValueError(f"{ticker}: missing reviewed status or explanation")
        if issuer.get("currency") != "PHP" or issuer.get("equity_unit_scale") not in SCALES or issuer.get("equity_basis") not in {"parent", "total"}:
            raise ValueError(f"{ticker}: equity currency, units or scope invalid")
        if not issuer.get("financial_source_url", "").startswith("https://edge.pse.com.ph/") or not issuer.get("share_classes"):
            raise ValueError(f"{ticker}: source path or common-share line missing")
        if issuer.get("equity_value") is None or not 0 < issuer.get("shares_outstanding", 0):
            raise ValueError(f"{ticker}: reported equity and positive shares required")
        if date.fromisoformat(issuer["period_end"]) > valuation_date or date.fromisoformat(issuer["status_as_of"]) > valuation_date or date.fromisoformat(issuer["share_as_of"]) > valuation_date:
            raise ValueError(f"{ticker}: dated facts exceed valuation date")
        classes = issuer["share_classes"]
        if any(not 0 < row["shares"] or date.fromisoformat(row["as_of"]) > valuation_date or not row["url"].startswith("https://edge.pse.com.ph/") for row in classes):
            raise ValueError(f"{ticker}: incomplete common-share source")
        if issuer["share_bridge_type"] not in {"single_class", "unresolved_claims"}:
            raise ValueError(f"{ticker}: unreviewed common-share bridge")
        if issuer["share_bridge_type"] == "single_class" and (len(classes) != 1 or classes[0]["shares"] != issuer["shares_outstanding"]):
            raise ValueError(f"{ticker}: common-share denominator does not reconcile")
        if issuer.get("trading_status") != "suspended":
            raise ValueError(f"{ticker}: the confirmed suspension-risk batch requires a dated suspended stock snapshot")
        if issuer["availability"] == "market_relative_only":
            if issuer["share_bridge_type"] != "single_class" or issuer["equity_basis"] != "parent" or issuer["period_end"] < "2026-01-01" or not str(issuer.get("screen_time_basis", "")).startswith("historical_"):
                raise ValueError(f"{ticker}: finite suspended-line screen requires a dated historical parent/common bridge")
            if equity_per_share(issuer) <= 0:
                raise ValueError(f"{ticker}: positive PHP parent/common book required")
            policy = config["policies"].get(issuer.get("policy"))
            if not policy or policy["metric"] != "price_to_book":
                raise ValueError(f"{ticker}: historical P/B policy missing")
            band = policy["assumptions"]
            if set(band) != {"low", "base", "high"} or not 0 < band["low"] < band["base"] < band["high"]:
                raise ValueError(f"{ticker}: invalid finite screening band")
        elif issuer.get("policy") is not None:
            raise ValueError(f"{ticker}: blocked issuer cannot carry a valuation policy")
    return config


def source_receipt(ticker: str, config: dict) -> tuple[list[dict], bytes]:
    issuer = config["issuers"][ticker]
    source = {
        "label": f"{ticker} reviewed PSE financial summary", "form": "PSE financial summary",
        "period_end": issuer["period_end"], "currency": issuer["currency"], "units": issuer["equity_unit_scale"],
        "url": issuer["financial_source_url"], "published_at": None,
    }
    supporting = [
        {"label": f"{ticker} {row['class']} stock data", "form": "PSE common-stock data", "period_end": row["as_of"], "published_at": None, "url": row["url"]}
        for row in issuer["share_classes"]
    ]
    supporting.extend({"label": row["label"], "form": row["form"], "period_end": None, "published_at": row.get("published_at"), "url": row["url"]} for row in issuer.get("supporting_sources", []))
    denominator = None if issuer["share_bridge_type"] == "unresolved_claims" else {
        "value": issuer["shares_outstanding"], "bridge_type": issuer["share_bridge_type"], "as_of": issuer["share_as_of"],
    }
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0", "batch_version": config["batch_version"],
        "review_status": config["review_status"], "retrieval_date": config["valuation_date"],
        "ticker": ticker, "issuer_name": issuer["issuer_name"], "source": source, "supporting_sources": supporting,
        "facts": {
            "reported_equity": {"value": issuer["equity_value"], "basis": issuer["equity_basis"], "currency": "PHP", "unit_scale": issuer["equity_unit_scale"], "period_end": issuer["period_end"], "period_type": "interim"},
            "reported_share_classes": issuer["share_classes"], "reviewed_common_denominator": denominator,
            "reported_bvps": {"value": issuer["reported_bvps"], "period_end": issuer["period_end"], "currency": "PHP"},
            "derived_php_equity_per_common_share": equity_per_share(issuer) if issuer["availability"] == "market_relative_only" else None,
            "trading_status_snapshot": {"status": issuer["trading_status"], "as_of": issuer["status_as_of"]},
            "intrinsic_blocker": issuer["intrinsic_blocker"],
        },
        "note": "Manually reviewed public-fact receipt, not the original filing or its content hash. No licensed current price was acquired. Source summary publication dates and page references were not established; unresolved claims remain unresolved rather than zero.",
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    references = [
        {"document_id": digest[:16] if index == 0 else f"{digest[:16]}-support-{index}",
         "label": row["label"], "form": row["form"], "period_end": row["period_end"],
         "published_at": row["published_at"], "url": row["url"], "source_page": None, "sha256": digest}
        for index, row in enumerate((source, *supporting))
    ]
    return references, raw


def build_batch_artifacts(config: dict | None = None) -> dict[str, PseValuationArtifact]:
    config = config or load_batch_config()
    output = {}
    for ticker in FROZEN_BATCH_TICKERS:
        issuer = config["issuers"][ticker]
        policy = config["policies"].get(issuer["policy"])
        sources, _ = source_receipt(ticker, config)
        relative = None
        numerical_range = {"low": None, "high": None}
        if issuer["availability"] == "market_relative_only":
            relative = market_relative_range(metric="price_to_book", metric_value_per_share=equity_per_share(issuer), assumptions=policy["assumptions"], relation="multiple")
            relative["estimates"] = {name: round(value, 9) for name, value in relative["estimates"].items()}
            relative.update({
                "policy_version": policy["version"], "metric_label": f"Historical {issuer['period_end']} parent equity per reviewed ordinary-common denominator",
                "source_status": "reviewed_historical_public_summary_receipt", "source_document_sha256": sources[0]["sha256"],
                "source_page": None, "note": "Historical finite analyst P/B screen for a suspended line; no current quote or upside, no intrinsic value.",
            })
            numerical_range = {"low": min(relative["estimates"].values()), "high": max(relative["estimates"].values())}
        metric_basis = (
            f"PHP {issuer['equity_basis']} equity ({issuer['equity_unit_scale']}) / {issuer['shares_outstanding']:,} reviewed ordinary-common shares"
            if issuer["share_bridge_type"] == "single_class" else "No completed parent/common claim bridge"
        )
        output[ticker] = PseValuationArtifact(
            model_version=MODEL_VERSION, ticker=ticker,
            issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
            security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common", "quoted_line": ticker},
            subsector=issuer["subsector"], primary_model=issuer["primary_model"],
            valuation_date=date.fromisoformat(config["valuation_date"]), filing_period=issuer["period_end"],
            availability_type=issuer["availability"], publication_state="provisional" if relative else "blocked",
            scenarios={"bear": None, "base": None, "bull": None}, numerical_range=numerical_range, market_relative=relative,
            public_assumptions={
                "route_reason": issuer["route_reason"], "intrinsic_blocker": issuer["intrinsic_blocker"],
                "metric_basis": metric_basis, "share_bridge_type": issuer["share_bridge_type"],
                "trading_status_as_of": issuer["status_as_of"], "trading_status": issuer["trading_status"],
                "screen_time_basis": issuer.get("screen_time_basis"),
                "policy_rationale": policy["rationale"] if policy else None,
                "reliability": "Low" if relative else "Unavailable",
            },
            sources=sources,
            warnings=["Reviewed public-summary receipt only; original filing and summary publication date were not captured. No current market quote or upside is published for this suspended security.", issuer["source_warning"]],
            blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object({"ticker": ticker, "issuer": issuer, "policy": policy, "receipt_sha256": sources[0]["sha256"], "model_version": MODEL_VERSION}),
        ).with_artifact_hash()
    return output
