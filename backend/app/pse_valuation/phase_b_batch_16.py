"""Reviewed Batch 16 mixed operating, bank and holding-company screens."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_16.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B16-1.0"
FROZEN_BATCH_TICKERS = ("AXLM", "BALAI", "FCG", "FOOD", "SFI", "BCOR", "BNCOM", "BSC", "PMPC", "PPC")
ROUTES = {"fcff_dcf", "residual_income", "sotp"}
METRIC_KINDS = {"ttm_eps", "reported_bvps", "ttm_revenue_per_share"}


def _aligned_flow(facts: dict, source_period: str) -> float:
    if set(facts) != {"fy", "current_ytd", "prior_ytd"}:
        raise ValueError("TTM bridge requires annual, current YTD and prior YTD facts")
    fy, current, prior = (facts[key] for key in ("fy", "current_ytd", "prior_ytd"))
    current_date = date.fromisoformat(current["period_end"])
    prior_date = date.fromisoformat(prior["period_end"])
    fiscal_date = date.fromisoformat(fy["period_end"])
    if (current["period_end"] != source_period or current["period_type"] != prior["period_type"]
            or current["period_type"] not in {"half_year_ytd", "nine_month_ytd"}
            or current_date.year - prior_date.year != 1
            or current_date.strftime("%m-%d") != prior_date.strftime("%m-%d")
            or fiscal_date.year != prior_date.year or fy["period_type"] != "annual"):
        raise ValueError("annual/YTD periods are not aligned to the reviewed source")
    if any(float(fact["value"]) < 0 for fact in facts.values()):
        raise ValueError("screening flow components must not be negative")
    return float(fy["value"]) + float(current["value"]) - float(prior["value"])


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-16.0" or tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise ValueError("Batch 16 schema or confirmed frozen set mismatch")
    issuers = config.get("issuers", {})
    if set(issuers) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 16 must contain exactly the confirmed ten issuers")
    fx = config["fx_snapshot"]
    if (fx.get("pair") != "USD/PHP" or fx.get("observed_at") != "2026-09-23"
            or float(fx.get("rate_php_per_usd", 0)) != 62.698
            or fx.get("source_url") != "https://www.bsp.gov.ph/Statistics/sdds/sdds.aspx"):
        raise ValueError("Batch 16 reviewed USD/PHP observation differs")
    for ticker, issuer in issuers.items():
        source = issuer["source"]
        kind = issuer.get("metric_kind")
        policy = config["policies"].get(issuer.get("policy"))
        if issuer.get("primary_model") not in ROUTES or kind not in METRIC_KINDS or policy is None:
            raise ValueError(f"{ticker}: unsupported route, metric or policy")
        if date.fromisoformat(source["period_end"]) > date.fromisoformat(config["valuation_date"]):
            raise ValueError(f"{ticker}: source period is in the future")
        if kind == "ttm_eps":
            if source["currency"] != "PHP" or source["units"] != "per_share" or policy["metric"] != "price_to_earnings":
                raise ValueError(f"{ticker}: earnings source or policy mismatch")
            expected = _aligned_flow(issuer["reported_eps"], source["period_end"])
        elif kind == "reported_bvps":
            fact = issuer["reported_bvps"]
            if source["currency"] != "PHP" or source["units"] != "per_share" or policy["metric"] != "price_to_book" or fact["period_end"] != source["period_end"] or fact["period_type"] != "interim":
                raise ValueError(f"{ticker}: book-value source or policy mismatch")
            expected = float(fact["value"])
        else:
            if policy["metric"] != "price_to_sales" or source["units"] not in {"dollars", "thousands"}:
                raise ValueError(f"{ticker}: sales source or policy mismatch")
            revenue = _aligned_flow(issuer["reported_revenue"], source["period_end"])
            shares = issuer["reported_shares"]
            if shares["security_type"] != "ordinary_common" or float(shares["value"]) <= 0:
                raise ValueError(f"{ticker}: common share count is missing")
            scale = 1000.0 if source["units"] == "thousands" else 1.0
            if source["currency"] not in {"PHP", "USD"} or (source["currency"] == "USD" and source["units"] != "dollars"):
                raise ValueError(f"{ticker}: original revenue currency or units are unsupported")
            conversion = float(fx["rate_php_per_usd"]) if source["currency"] == "USD" else 1.0
            expected = revenue * scale * conversion / float(shares["value"])
        if expected <= 0 or abs(float(issuer["metric_value_per_share"]) - expected) > 1e-9 or abs(float(issuer["normalization"]["normalized_value"]) - expected) > 1e-9:
            raise ValueError(f"{ticker}: reported and normalized per-share values do not reconcile")
        if issuer["normalization"]["original_currency"] != source["currency"] or issuer["normalization"]["normalized_currency"] != "PHP":
            raise ValueError(f"{ticker}: original currency was lost")
    return config


def source_receipt(ticker: str, config: dict) -> tuple[list[dict], bytes]:
    issuer = config["issuers"][ticker]
    source = issuer["source"]
    supporting = issuer.get("supporting_sources", [])
    fx = config["fx_snapshot"] if source["currency"] == "USD" else None
    receipt = {
        "schema_version": "PSE-V2-REVIEWED-FACT-RECEIPT-1.0", "batch_version": config["batch_version"],
        "review_status": config["review_status"], "retrieval_date": config["valuation_date"],
        "ticker": ticker, "issuer_name": issuer["issuer_name"], "source": source,
        "supporting_sources": supporting, "fx_snapshot": fx,
        "facts": {"reported_eps": issuer.get("reported_eps"), "reported_bvps": issuer.get("reported_bvps"), "reported_revenue": issuer.get("reported_revenue"), "reported_shares": issuer.get("reported_shares"), "metric_value_per_share": issuer["metric_value_per_share"], "metric_label": issuer["metric_label"], "normalization": issuer["normalization"], "intrinsic_blocker": issuer["intrinsic_blocker"]},
        "note": "This receipt binds manually reviewed public facts and links; it is not a copy of the remote filing or summary page.",
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    references = [{"document_id": digest[:16], "label": source["label"], "form": source["form"], "period_end": source["period_end"], "published_at": None, "url": source["url"], "source_page": None, "sha256": digest}]
    for index, extra in enumerate(supporting, start=1):
        references.append({"document_id": f"{digest[:16]}-support-{index}", "label": extra["label"], "form": extra["form"], "period_end": extra.get("period_end"), "published_at": None, "url": extra["url"], "source_page": None, "sha256": digest})
    if fx:
        references.append({"document_id": f"{digest[:16]}-fx", "label": fx["source_label"], "form": "BSP exchange-rate observation", "period_end": fx["observed_at"], "published_at": None, "url": fx["source_url"], "source_page": None, "sha256": digest})
    return references, raw


def build_batch_artifacts(config: dict | None = None) -> dict[str, PseValuationArtifact]:
    config = config or load_batch_config()
    output = {}
    for ticker in FROZEN_BATCH_TICKERS:
        issuer = config["issuers"][ticker]
        policy = config["policies"][issuer["policy"]]
        sources, _ = source_receipt(ticker, config)
        relative = market_relative_range(metric=policy["metric"], metric_value_per_share=float(issuer["metric_value_per_share"]), assumptions=policy["assumptions"], relation=policy["relation"])
        relative["estimates"] = {key: round(value, 9) for key, value in relative["estimates"].items()}
        relative.update({"policy_version": policy["version"], "metric_label": issuer["metric_label"], "source_status": "reviewed_public_fact", "source_document_sha256": sources[0]["sha256"], "source_page": None, "note": "Finite analyst screening band; no peer study or complete intrinsic FCFF, residual-income or SOTP valuation has been completed."})
        estimates = relative["estimates"]
        fx_assumptions = {"fx_rate_php_per_usd": config["fx_snapshot"]["rate_php_per_usd"], "fx_observed_at": config["fx_snapshot"]["observed_at"]} if issuer["source"]["currency"] == "USD" else {}
        warnings = ["Screening-grade market-relative result, not intrinsic value or a peer-calibrated target.", "Operating cash flows, capital efficiency and common-equity claims have not been fully reconciled."]
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
            public_assumptions={"route_reason": issuer["route_reason"], "intrinsic_blocker": issuer["intrinsic_blocker"], "metric_basis": issuer["normalization"]["formula"], "policy_rationale": policy["rationale"], "reliability": "Low", **fx_assumptions},
            sources=sources, warnings=warnings, blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object({"ticker": ticker, "issuer": issuer, "policy": policy, "fx_snapshot": config["fx_snapshot"] if issuer["source"]["currency"] == "USD" else None, "source": sources[0]["sha256"], "model_version": MODEL_VERSION}),
        ).with_artifact_hash()
    return output
