"""Batch 19 reviewed common-share facts and deliberately limited screens."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_19.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B19-1.0"
FROZEN_BATCH_TICKERS = ("TBGI", "IS", "PHC", "LODE", "CPM", "APL", "ABA", "PAX", "LMG", "PRIM")
BLOCKED_TICKERS = frozenset({"IS", "PAX", "PRIM"})


def _equity_per_share(issuer: dict) -> float:
    scale = 1000 if issuer["equity_unit_scale"] == "thousands" else 1
    return float(issuer["equity_value"]) * scale / float(issuer["shares_outstanding"])


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-19.0" or tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 19 schema or frozen issuer set mismatch")
    if set(config.get("issuers", {})) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 19 must contain exactly the confirmed ten")
    valuation_date = date.fromisoformat(config["valuation_date"])
    for ticker, issuer in config["issuers"].items():
        if issuer["availability"] != ("not_available" if ticker in BLOCKED_TICKERS else "market_relative_only"):
            raise ValueError(f"{ticker}: availability does not match the reviewed gate")
        if issuer["primary_model"] not in {"fcff_dcf", "sotp"}:
            raise ValueError(f"{ticker}: unsupported primary route")
        if issuer["equity_basis"] not in {"parent", "total"} or issuer["equity_unit_scale"] not in {"pesos", "thousands"}:
            raise ValueError(f"{ticker}: equity scope or units invalid")
        if float(issuer["shares_outstanding"]) <= 0 or date.fromisoformat(issuer["share_as_of"]) > valuation_date or date.fromisoformat(issuer["period_end"]) > valuation_date:
            raise ValueError(f"{ticker}: shares or period invalid")
        if ticker in BLOCKED_TICKERS:
            if issuer.get("policy") is not None:
                raise ValueError(f"{ticker}: blocked security cannot have a valuation policy")
        else:
            policy = config["policies"].get(issuer.get("policy"))
            if policy is None or policy["metric"] != "price_to_book" or _equity_per_share(issuer) <= 0:
                raise ValueError(f"{ticker}: positive book screen unsupported")
            assumptions = policy["assumptions"]
            if set(assumptions) != {"low", "base", "high"} or not 0 < assumptions["low"] < assumptions["base"] < assumptions["high"]:
                raise ValueError(f"{ticker}: screening band invalid")
    return config


def source_receipt(ticker: str, config: dict) -> tuple[list[dict], bytes]:
    issuer = config["issuers"][ticker]
    company_id = issuer["company_id"]
    source = {
        "label": f"{ticker} FY2025 and latest PSE financial summary",
        "form": "PSE financial summary",
        "period_end": issuer["period_end"],
        "currency": "PHP",
        "units": issuer["equity_unit_scale"],
        "url": f"https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id={company_id}",
    }
    stock = {
        "label": f"{ticker} ordinary-common stock data",
        "form": "PSE common-stock data",
        "period_end": issuer["share_as_of"],
        "url": f"https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id={company_id}",
    }
    supporting = [stock, *issuer.get("extra_sources", [])]
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0",
        "batch_version": config["batch_version"],
        "review_status": config["review_status"],
        "retrieval_date": config["valuation_date"],
        "ticker": ticker,
        "issuer_name": issuer["issuer_name"],
        "source": source,
        "supporting_sources": supporting,
        "facts": {
            "reported_equity": {"value": issuer["equity_value"], "basis": issuer["equity_basis"], "unit_scale": issuer["equity_unit_scale"], "period_end": issuer["period_end"], "period_type": "interim"},
            "reported_common_shares_outstanding": {"value": issuer["shares_outstanding"], "as_of": issuer["share_as_of"], "security_type": "ordinary_common"},
            "reported_bvps": {"value": issuer["reported_bvps"], "period_end": issuer["period_end"], "unit_scale": "per_share"},
            "derived_equity_per_share": _equity_per_share(issuer),
            "intrinsic_blocker": issuer["intrinsic_blocker"],
        },
        "note": "Manually reviewed public-fact receipt, not a copy or content hash of a PSE filing. Source publication dates and original filing page references were not established.",
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    references = []
    for index, item in enumerate([source, *supporting]):
        references.append({
            "document_id": digest[:16] if index == 0 else f"{digest[:16]}-support-{index}",
            "label": item["label"], "form": item["form"], "period_end": item.get("period_end"),
            "published_at": None, "url": item["url"], "source_page": None, "sha256": digest,
        })
    return references, raw


def build_batch_artifacts(config: dict | None = None) -> dict[str, PseValuationArtifact]:
    config = config or load_batch_config()
    output = {}
    for ticker in FROZEN_BATCH_TICKERS:
        issuer = config["issuers"][ticker]
        sources, _ = source_receipt(ticker, config)
        policy = config["policies"].get(issuer["policy"]) if issuer["policy"] else None
        common = dict(
            model_version=MODEL_VERSION, ticker=ticker,
            issuer={"issuer_id": f"PSE:{ticker}", "name": issuer["issuer_name"]},
            security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
            subsector=issuer["subsector"], primary_model=issuer["primary_model"],
            valuation_date=date.fromisoformat(config["valuation_date"]), filing_period=issuer["period_end"],
            scenarios={"bear": None, "base": None, "bull": None}, sources=sources,
            warnings=["Reviewed public-summary receipt only; original filing and source publication date were not captured.", issuer["source_warning"]],
            blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object({"ticker": ticker, "issuer": issuer, "policy": policy, "receipt_sha256": sources[0]["sha256"], "model_version": MODEL_VERSION}),
        )
        if issuer["availability"] == "not_available":
            output[ticker] = PseValuationArtifact(
                **common, availability_type="not_available", publication_state="blocked",
                numerical_range={"low": None, "high": None},
                public_assumptions={"route_reason": issuer["route_reason"], "reliability": "Unavailable", "metric_basis": "No defensible present ordinary-common per-share screen"},
            ).with_artifact_hash()
            continue
        relative = market_relative_range(
            metric="price_to_book", metric_value_per_share=_equity_per_share(issuer),
            assumptions=policy["assumptions"], relation="multiple",
        )
        relative["estimates"] = {name: round(value, 9) for name, value in relative["estimates"].items()}
        relative.update({
            "policy_version": policy["version"], "metric_label": f"{issuer['period_end']} {issuer['equity_basis']} equity per outstanding common share",
            "source_status": "reviewed_public_summary_receipt", "source_document_sha256": sources[0]["sha256"],
            "source_page": None, "note": "Finite analyst book-value screen; no peer calibration or complete intrinsic valuation.",
        })
        estimates = relative["estimates"]
        output[ticker] = PseValuationArtifact(
            **common, availability_type="market_relative_only", publication_state="provisional",
            numerical_range={"low": min(estimates.values()), "high": max(estimates.values())}, market_relative=relative,
            public_assumptions={
                "route_reason": issuer["route_reason"], "intrinsic_blocker": issuer["intrinsic_blocker"],
                "metric_basis": f"PHP {issuer['equity_basis']} equity ({issuer['equity_unit_scale']}) / {issuer['shares_outstanding']:,} outstanding common shares",
                "policy_rationale": policy["rationale"], "reliability": "Low",
            },
        ).with_artifact_hash()
    return output
