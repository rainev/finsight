"""Batch 21 reviewed property/holding screens with explicit equity scope."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_21.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B21-1.0"
FROZEN_BATCH_TICKERS = ("IDC", "JOH", "KEP", "LPC", "DWC", "OM", "MHC", "PHA", "SPM", "SRDC")


def equity_per_share(issuer: dict) -> float:
    scale = 1000 if issuer["equity_unit_scale"] == "thousands" else 1
    return float(issuer["equity_value"]) * scale / float(issuer["shares_outstanding"])


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-21.0" or tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 21 schema or confirmed issuer set mismatch")
    if set(config.get("issuers", {})) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 21 must contain exactly the confirmed ten issuers")
    valuation_date = date.fromisoformat(config["valuation_date"])
    for ticker, issuer in config["issuers"].items():
        if issuer.get("availability") != "market_relative_only" or issuer.get("primary_model") != "sotp":
            raise ValueError(f"{ticker}: unreviewed status or primary route")
        if issuer["equity_basis"] not in {"parent", "total"} or issuer["equity_unit_scale"] not in {"pesos", "thousands"}:
            raise ValueError(f"{ticker}: equity scope or units invalid")
        if float(issuer["shares_outstanding"]) <= 0 or equity_per_share(issuer) <= 0 or float(issuer["reported_bvps"]) <= 0:
            raise ValueError(f"{ticker}: positive common-equity bridge unsupported")
        if date.fromisoformat(issuer["share_as_of"]) > valuation_date or date.fromisoformat(issuer["period_end"]) > valuation_date:
            raise ValueError(f"{ticker}: dated facts exceed valuation date")
        policy = config["policies"].get(issuer.get("policy"))
        if policy is None or policy["metric"] != "price_to_book":
            raise ValueError(f"{ticker}: unreviewed P/B policy")
        assumptions = policy["assumptions"]
        if set(assumptions) != {"low", "base", "high"} or not 0 < assumptions["low"] < assumptions["base"] < assumptions["high"]:
            raise ValueError(f"{ticker}: invalid finite screening band")
        if int(issuer["company_id"]) <= 0 or not issuer.get("intrinsic_blocker") or not issuer.get("source_warning"):
            raise ValueError(f"{ticker}: source identity or review reasons missing")
    return config


def source_receipt(ticker: str, config: dict) -> tuple[list[dict], bytes]:
    issuer = config["issuers"][ticker]
    company_id = issuer["company_id"]
    source = {
        "label": f"{ticker} FY2025 and latest PSE financial summary",
        "form": "PSE financial summary", "period_end": issuer["period_end"],
        "currency": "PHP", "units": issuer["equity_unit_scale"],
        "url": f"https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id={company_id}",
    }
    stock = {
        "label": f"{ticker} open ordinary-common stock data",
        "form": "PSE common-stock data", "period_end": issuer["share_as_of"],
        "url": issuer.get("stock_url") or f"https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id={company_id}",
    }
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0",
        "batch_version": config["batch_version"], "review_status": config["review_status"],
        "retrieval_date": config["valuation_date"], "ticker": ticker,
        "issuer_name": issuer["issuer_name"], "source": source, "supporting_sources": [stock],
        "facts": {
            "reported_equity": {"value": issuer["equity_value"], "basis": issuer["equity_basis"], "unit_scale": issuer["equity_unit_scale"], "period_end": issuer["period_end"], "period_type": "interim"},
            "reported_common_shares_outstanding": {"value": issuer["shares_outstanding"], "as_of": issuer["share_as_of"], "security_type": "ordinary_common"},
            "reported_bvps": {"value": issuer["reported_bvps"], "period_end": issuer["period_end"], "unit_scale": "per_share"},
            "derived_equity_per_share": equity_per_share(issuer),
            "intrinsic_blocker": issuer["intrinsic_blocker"],
        },
        "note": "Manually reviewed public-fact receipt, not an original PSE filing or its content hash. Blank or zero parent fields are not replaced by economic zero. Source publication dates and filing page references were not established.",
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    references = []
    for index, item in enumerate((source, stock)):
        references.append({
            "document_id": digest[:16] if index == 0 else f"{digest[:16]}-support-{index}",
            "label": item["label"], "form": item["form"], "period_end": item["period_end"],
            "published_at": None, "url": item["url"], "source_page": None, "sha256": digest,
        })
    return references, raw


def build_batch_artifacts(config: dict | None = None) -> dict[str, PseValuationArtifact]:
    config = config or load_batch_config()
    output = {}
    for ticker in FROZEN_BATCH_TICKERS:
        issuer = config["issuers"][ticker]
        policy = config["policies"][issuer["policy"]]
        sources, _ = source_receipt(ticker, config)
        relative = market_relative_range(
            metric="price_to_book", metric_value_per_share=equity_per_share(issuer),
            assumptions=policy["assumptions"], relation="multiple",
        )
        relative["estimates"] = {name: round(value, 9) for name, value in relative["estimates"].items()}
        relative.update({
            "policy_version": policy["version"],
            "metric_label": f"{issuer['period_end']} {issuer['equity_basis']} equity per outstanding ordinary common share",
            "source_status": "reviewed_public_summary_receipt", "source_document_sha256": sources[0]["sha256"],
            "source_page": None, "note": "Finite analyst book-value screen; total-equity bases are tentative common-share proxies. No peer calibration or completed intrinsic valuation.",
        })
        estimates = relative["estimates"]
        output[ticker] = PseValuationArtifact(
            model_version=MODEL_VERSION, ticker=ticker,
            issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
            security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
            subsector=issuer["subsector"], primary_model="sotp",
            valuation_date=date.fromisoformat(config["valuation_date"]), filing_period=issuer["period_end"],
            availability_type="market_relative_only", publication_state="provisional",
            scenarios={"bear": None, "base": None, "bull": None},
            numerical_range={"low": min(estimates.values()), "high": max(estimates.values())},
            market_relative=relative,
            public_assumptions={
                "route_reason": issuer["route_reason"], "intrinsic_blocker": issuer["intrinsic_blocker"],
                "metric_basis": f"PHP {issuer['equity_basis']} equity ({issuer['equity_unit_scale']}) / {issuer['shares_outstanding']:,} dated outstanding common shares",
                "policy_rationale": policy["rationale"], "reliability": "Low",
            },
            sources=sources,
            warnings=["Reviewed public-summary receipt only; original filing and publication date were not captured.", issuer["source_warning"]],
            blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object({"ticker": ticker, "issuer": issuer, "policy": policy, "receipt_sha256": sources[0]["sha256"], "model_version": MODEL_VERSION}),
        ).with_artifact_hash()
    return output
