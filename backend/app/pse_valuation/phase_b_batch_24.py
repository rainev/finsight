"""Batch 24 class-aware, source-bounded PSE screening records."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_24.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B24-1.0"
FROZEN_BATCH_TICKERS = ("AB", "FPI", "FAF", "BH", "GEO", "UPM", "MA", "X", "MFC", "SLF")


def equity_per_share(issuer: dict) -> float:
    if issuer["currency"] != "PHP":
        raise ValueError("a dated approved FX observation is required before PHP conversion")
    scale = 1000 if issuer["equity_unit_scale"] == "thousands" else 1
    return float(issuer["equity_value"]) * scale / float(issuer["shares_outstanding"])


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-24.0" or tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 24 schema or confirmed issuer set mismatch")
    if set(config.get("issuers", {})) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 24 must contain exactly the confirmed ten issuers")
    valuation_date = date.fromisoformat(config["valuation_date"])
    for ticker, issuer in config["issuers"].items():
        if issuer.get("primary_model") not in {"sotp", "fcff_dcf", "residual_income"} or issuer.get("availability") not in {"market_relative_only", "not_available"}:
            raise ValueError(f"{ticker}: unreviewed route or availability")
        if issuer.get("equity_basis") not in {"parent", "total"} or issuer.get("currency") not in {"PHP", "CAD"}:
            raise ValueError(f"{ticker}: equity scope or currency invalid")
        if (issuer["currency"], issuer["equity_unit_scale"]) not in {("PHP", "pesos"), ("PHP", "thousands"), ("CAD", "millions")}:
            raise ValueError(f"{ticker}: equity units invalid")
        if float(issuer["equity_value"]) == 0 or not 0 < float(issuer["shares_outstanding"]):
            raise ValueError(f"{ticker}: nonzero reported equity and positive shares required")
        if date.fromisoformat(issuer["period_end"]) > valuation_date or date.fromisoformat(issuer["share_as_of"]) > valuation_date:
            raise ValueError(f"{ticker}: dated facts exceed valuation date")
        classes = issuer.get("share_classes")
        if not classes or any(not 0 < float(row["shares"]) or date.fromisoformat(row["as_of"]) > valuation_date or not row.get("url") for row in classes):
            raise ValueError(f"{ticker}: incomplete dated common-share classes")
        bridge = issuer.get("share_bridge_type")
        if bridge not in {"single_class", "class_sum", "reported_total_declassification"}:
            raise ValueError(f"{ticker}: unreviewed class bridge")
        if bridge == "single_class" and len(classes) != 1 or bridge == "class_sum" and len(classes) != 2:
            raise ValueError(f"{ticker}: class count differs from bridge")
        if bridge != "reported_total_declassification" and sum(row["shares"] for row in classes) != issuer["shares_outstanding"]:
            raise ValueError(f"{ticker}: pooled common shares do not reconcile")
        if bridge == "reported_total_declassification" and (len(classes) != 1 or classes[0]["shares"] != issuer["shares_outstanding"] or not issuer.get("claim_source_url")):
            raise ValueError(f"{ticker}: declassification source or total missing")
        if not issuer.get("intrinsic_blocker") or not issuer.get("source_warning") or int(issuer["company_id"]) <= 0:
            raise ValueError(f"{ticker}: source or block explanation missing")
        if issuer["availability"] == "market_relative_only":
            if issuer["currency"] != "PHP" or equity_per_share(issuer) <= 0 or not issuer.get("policy"):
                raise ValueError(f"{ticker}: PHP common book bridge unsupported")
            policy = config["policies"].get(issuer["policy"])
            if not policy or policy["metric"] != "price_to_book":
                raise ValueError(f"{ticker}: P/B policy missing")
            a = policy["assumptions"]
            if set(a) != {"low", "base", "high"} or not 0 < a["low"] < a["base"] < a["high"]:
                raise ValueError(f"{ticker}: invalid finite screening band")
        elif issuer.get("policy") is not None:
            raise ValueError(f"{ticker}: blocked record cannot carry a valuation policy")
    return config


def source_receipt(ticker: str, config: dict) -> tuple[list[dict], bytes]:
    issuer = config["issuers"][ticker]
    source = {
        "label": f"{ticker} FY2025 and latest PSE financial summary", "form": "PSE financial summary",
        "period_end": issuer["period_end"], "currency": issuer["currency"], "units": issuer["equity_unit_scale"],
        "url": f"https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id={issuer['company_id']}",
    }
    supporting = [
        {"label": f"{ticker} {row['class']} common stock data", "form": "PSE common-stock data", "period_end": row["as_of"], "url": row["url"]}
        for row in issuer["share_classes"]
    ]
    if issuer.get("claim_source_url"):
        supporting.append({"label": f"{ticker} class or capital-claim disclosure", "form": "PSE issuer disclosure", "period_end": None, "url": issuer["claim_source_url"]})
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0", "batch_version": config["batch_version"],
        "review_status": config["review_status"], "retrieval_date": config["valuation_date"],
        "ticker": ticker, "issuer_name": issuer["issuer_name"], "source": source, "supporting_sources": supporting,
        "facts": {
            "reported_equity": {"value": issuer["equity_value"], "basis": issuer["equity_basis"], "currency": issuer["currency"], "unit_scale": issuer["equity_unit_scale"], "period_end": issuer["period_end"], "period_type": "interim"},
            "reported_share_classes": issuer["share_classes"],
            "reviewed_common_denominator": {"value": issuer["shares_outstanding"], "bridge_type": issuer["share_bridge_type"], "as_of": issuer["share_as_of"]},
            "reported_bvps": {"value": issuer["reported_bvps"], "period_end": issuer["period_end"], "currency": issuer["currency"], "requires_php_conversion": issuer["currency"] != "PHP"},
            "derived_php_equity_per_common_share": equity_per_share(issuer) if issuer["availability"] == "market_relative_only" else None,
            "intrinsic_blocker": issuer["intrinsic_blocker"],
        },
        "note": "Manually reviewed public-fact receipt, not an original PSE filing or its content hash. Class bridges are issuer-level screening denominators, not a substitute for completed class-rights and dilution underwriting. Source publication dates and page references were not established.",
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    references = []
    for index, item in enumerate((source, *supporting)):
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
        policy = config["policies"].get(issuer["policy"])
        sources, _ = source_receipt(ticker, config)
        relative = None
        numerical_range = {"low": None, "high": None}
        if issuer["availability"] == "market_relative_only":
            relative = market_relative_range(
                metric="price_to_book", metric_value_per_share=equity_per_share(issuer),
                assumptions=policy["assumptions"], relation="multiple",
            )
            relative["estimates"] = {name: round(value, 9) for name, value in relative["estimates"].items()}
            relative.update({
                "policy_version": policy["version"],
                "metric_label": f"{issuer['period_end']} {issuer['equity_basis']} equity per reviewed ordinary-common denominator",
                "source_status": "reviewed_public_summary_receipt", "source_document_sha256": sources[0]["sha256"],
                "source_page": None, "note": "Finite analyst book screen with explicit class/claim caveats; no peer calibration or intrinsic value.",
            })
            numerical_range = {"low": min(relative["estimates"].values()), "high": max(relative["estimates"].values())}
        output[ticker] = PseValuationArtifact(
            model_version=MODEL_VERSION, ticker=ticker,
            issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
            security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common", "quoted_line": ticker},
            subsector=issuer["subsector"], primary_model=issuer["primary_model"],
            valuation_date=date.fromisoformat(config["valuation_date"]), filing_period=issuer["period_end"],
            availability_type=issuer["availability"],
            publication_state="provisional" if relative else "blocked",
            scenarios={"bear": None, "base": None, "bull": None}, numerical_range=numerical_range,
            market_relative=relative,
            public_assumptions={
                "route_reason": issuer["route_reason"], "intrinsic_blocker": issuer["intrinsic_blocker"],
                "metric_basis": f"{issuer['currency']} {issuer['equity_basis']} equity ({issuer['equity_unit_scale']}) / {issuer['shares_outstanding']:,} reviewed ordinary-common shares",
                "share_bridge_type": issuer["share_bridge_type"],
                "policy_rationale": policy["rationale"] if policy else None,
                "reliability": "Low" if relative else "Unavailable",
            },
            sources=sources,
            warnings=["Reviewed public-summary receipt only; original filing and publication date were not captured.", issuer["source_warning"]],
            blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object({"ticker": ticker, "issuer": issuer, "policy": policy, "receipt_sha256": sources[0]["sha256"], "model_version": MODEL_VERSION}),
        ).with_artifact_hash()
    return output
