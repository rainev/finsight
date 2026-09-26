"""Reviewed, null-only PSE Batch 27 suspended-common records."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_27.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B27-1.0"
FROZEN_BATCH_TICKERS = ("AR", "BMM", "CYBR", "MGH", "MJIC", "PNC", "PORT", "SOC", "T", "TUBIG")
EQUITY_SCALES = {"pesos", "thousands", "millions"}


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-27.0" or tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 27 schema or confirmed issuer set mismatch")
    if set(config.get("issuers", {})) != set(FROZEN_BATCH_TICKERS) or config.get("policies") != {}:
        raise ValueError("Batch 27 requires exactly the confirmed ten null-only issuers")
    valuation_date = date.fromisoformat(config["valuation_date"])
    for ticker, issuer in config["issuers"].items():
        if issuer.get("primary_model") not in {"sotp", "nav_sotp", "fcff_dcf"}:
            raise ValueError(f"{ticker}: unsupported primary route")
        if issuer.get("availability") != "not_available" or issuer.get("policy") is not None or not issuer.get("intrinsic_blocker") or not issuer.get("source_warning"):
            raise ValueError(f"{ticker}: null-only publication boundary invalid")
        if issuer.get("currency") != "PHP" or issuer.get("trading_status") != "suspended":
            raise ValueError(f"{ticker}: currency or suspended status invalid")
        if not issuer.get("financial_source_url", "").startswith("https://edge.pse.com.ph/"):
            raise ValueError(f"{ticker}: financial source path missing")
        if date.fromisoformat(issuer["status_as_of"]) > valuation_date or date.fromisoformat(issuer["share_as_of"]) > valuation_date:
            raise ValueError(f"{ticker}: stock status or share date exceeds valuation date")
        shares = issuer.get("shares_outstanding")
        classes = issuer.get("share_classes", [])
        if not isinstance(shares, int) or shares <= 0 or len(classes) != 1:
            raise ValueError(f"{ticker}: positive sourced common-share line required")
        row = classes[0]
        if row["shares"] != shares or date.fromisoformat(row["as_of"]) > valuation_date or not row["url"].startswith("https://edge.pse.com.ph/"):
            raise ValueError(f"{ticker}: common-share line does not reconcile to stock source")
        if issuer.get("share_bridge_type") not in {"single_class", "unresolved_claims"}:
            raise ValueError(f"{ticker}: unreviewed common-share bridge")
        period = issuer.get("period_end")
        if period is None:
            if any(issuer.get(name) is not None for name in ("equity_value", "equity_unit_scale", "equity_basis", "reported_bvps", "source_currency_label")) or issuer["share_bridge_type"] != "unresolved_claims":
                raise ValueError(f"{ticker}: missing financial facts must remain null")
        else:
            if date.fromisoformat(period) > valuation_date or issuer.get("equity_value") is None or issuer.get("equity_unit_scale") not in EQUITY_SCALES or issuer.get("equity_basis") not in {"parent", "total"} or issuer.get("reported_bvps") is None or not issuer.get("source_currency_label"):
                raise ValueError(f"{ticker}: dated reported equity, unit, scope and BVPS required")
        for support in issuer.get("supporting_sources", []):
            if not support.get("url", "").startswith("https://edge.pse.com.ph/"):
                raise ValueError(f"{ticker}: supporting source path invalid")
            if support.get("published_at") and date.fromisoformat(support["published_at"]) > valuation_date:
                raise ValueError(f"{ticker}: supporting source date exceeds valuation date")
    return config


def source_receipt(ticker: str, config: dict) -> tuple[list[dict], bytes]:
    issuer = config["issuers"][ticker]
    source = {
        "label": f"{ticker} reviewed PSE financial-summary page", "form": "PSE financial summary",
        "period_end": issuer["period_end"], "currency": issuer["currency"],
        "source_currency_label": issuer["source_currency_label"], "units": issuer["equity_unit_scale"],
        "url": issuer["financial_source_url"], "published_at": None,
    }
    supporting = [
        {"label": f"{ticker} {row['class']} stock data", "form": "PSE common-stock data", "period_end": row["as_of"], "published_at": None, "url": row["url"]}
        for row in issuer["share_classes"]
    ]
    supporting.extend({"label": row["label"], "form": row["form"], "period_end": None, "published_at": row.get("published_at"), "url": row["url"]} for row in issuer.get("supporting_sources", []))
    equity = None if issuer["equity_value"] is None else {
        "value": issuer["equity_value"], "basis": issuer["equity_basis"], "currency": issuer["currency"],
        "source_currency_label": issuer["source_currency_label"], "unit_scale": issuer["equity_unit_scale"],
        "period_end": issuer["period_end"], "period_type": "interim",
    }
    denominator = None if issuer["share_bridge_type"] == "unresolved_claims" else {
        "value": issuer["shares_outstanding"], "bridge_type": issuer["share_bridge_type"], "as_of": issuer["share_as_of"],
    }
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0", "batch_version": config["batch_version"],
        "review_status": config["review_status"], "retrieval_date": config["valuation_date"],
        "ticker": ticker, "issuer_name": issuer["issuer_name"], "source": source, "supporting_sources": supporting,
        "facts": {
            "reported_equity": equity, "reported_share_classes": issuer["share_classes"],
            "reviewed_common_denominator": denominator,
            "reported_bvps": None if issuer["reported_bvps"] is None else {"value": issuer["reported_bvps"], "period_end": issuer["period_end"], "currency": "PHP"},
            "derived_php_equity_per_common_share": None,
            "trading_status_snapshot": {"status": issuer["trading_status"], "as_of": issuer["status_as_of"]},
            "intrinsic_blocker": issuer["intrinsic_blocker"],
        },
        "note": "Manually reviewed public-fact receipt, not an original filing or its content hash. Source currency labels and units are retained. Unavailable financial fields and unsettled claims remain null, not zero; no licensed current price was acquired.",
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
        sources, _ = source_receipt(ticker, config)
        output[ticker] = PseValuationArtifact(
            model_version=MODEL_VERSION, ticker=ticker,
            issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
            security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common", "quoted_line": ticker},
            subsector=issuer["subsector"], primary_model=issuer["primary_model"],
            valuation_date=date.fromisoformat(config["valuation_date"]), filing_period=issuer["period_end"],
            availability_type="not_available", publication_state="blocked",
            scenarios={"bear": None, "base": None, "bull": None}, numerical_range={"low": None, "high": None}, market_relative=None,
            public_assumptions={
                "route_reason": issuer["route_reason"], "intrinsic_blocker": issuer["intrinsic_blocker"],
                "metric_basis": "No published valuation: financial period or parent/common economic claims are unresolved",
                "share_bridge_type": issuer["share_bridge_type"],
                "trading_status_as_of": issuer["status_as_of"], "trading_status": issuer["trading_status"],
                "reliability": "Unavailable",
            },
            sources=sources,
            warnings=["Reviewed public-summary receipt only; original filing and summary publication date were not captured. Suspended stock has no current market quote or upside claim.", issuer["source_warning"]],
            blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object({"ticker": ticker, "issuer": issuer, "receipt_sha256": sources[0]["sha256"], "model_version": MODEL_VERSION}),
        ).with_artifact_hash()
    return output
