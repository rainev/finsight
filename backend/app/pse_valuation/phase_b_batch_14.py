"""Reviewed, source-bounded Batch 14 market-relative screens."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .contract import PseValuationArtifact, canonical_json, sha256_object
from .models.comparables import market_relative_range


CONFIG_PATH = Path(__file__).with_name("config") / "phase_b_batch_14.json"
MODEL_VERSION = "PSE-V2-PHASE-B-B14-1.0"
FROZEN_BATCH_TICKERS = ("STI", "CEU", "FEU", "IPO", "MEDIC", "EURO", "MRSGI", "UPSON", "FRUIT", "KEEPR")
NON_DECEMBER_PERIODS = {"STI": "2026-03-31", "CEU": "2026-02-28", "FEU": "2026-05-31"}


def load_batch_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "PSE-V2-PHASE-B-BATCH-14.0":
        raise ValueError("Batch 14 schema mismatch")
    if tuple(config.get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS or set(config.get("issuers", {})) != set(FROZEN_BATCH_TICKERS):
        raise ValueError("Batch 14 confirmed frozen set mismatch")
    for ticker, issuer in config["issuers"].items():
        policy = config["policies"].get(issuer.get("policy"))
        if issuer.get("primary_model") not in {"fcff_dcf", "sotp"} or policy is None:
            raise ValueError(f"{ticker}: unsupported route or policy")
        source = issuer["source"]
        if source.get("currency") != "PHP" or source.get("units") != "per share":
            raise ValueError(f"{ticker}: original currency or unit differs")
        if source.get("period_end") != NON_DECEMBER_PERIODS.get(ticker, "2026-06-30"):
            raise ValueError(f"{ticker}: reporting period differs from reviewed source")
        facts = issuer.get("reported_eps")
        if ticker == "MEDIC":
            if facts or policy["metric"] != "price_to_book":
                raise ValueError("MEDIC: expected book-value-only screen")
            bvps = issuer["reported_bvps"]
            if bvps["period_end"] != source["period_end"] or bvps["period_type"] != "interim":
                raise ValueError("MEDIC: book-value period mismatch")
            expected = float(bvps["value"])
        else:
            if policy["metric"] != "price_to_earnings" or set(facts) not in ({"fy"}, {"fy", "current_ytd", "prior_ytd"}):
                raise ValueError(f"{ticker}: expected aligned earnings bridge")
            if any(float(fact["value"]) <= 0 for fact in facts.values()):
                raise ValueError(f"{ticker}: earnings fact must be positive")
            if set(facts) == {"fy"}:
                if ticker != "FEU" or facts["fy"]["period_end"] != source["period_end"] or facts["fy"]["period_type"] != "annual":
                    raise ValueError(f"{ticker}: annual period mismatch")
                expected = float(facts["fy"]["value"])
            else:
                if facts["current_ytd"]["period_end"] != source["period_end"] or facts["current_ytd"]["period_type"] != facts["prior_ytd"]["period_type"]:
                    raise ValueError(f"{ticker}: YTD period mismatch")
                current_date = date.fromisoformat(facts["current_ytd"]["period_end"])
                prior_date = date.fromisoformat(facts["prior_ytd"]["period_end"])
                fiscal_date = date.fromisoformat(facts["fy"]["period_end"])
                if current_date.year - prior_date.year != 1 or current_date.strftime("%m-%d") != prior_date.strftime("%m-%d") or fiscal_date.year != prior_date.year or facts["fy"]["period_type"] != "annual":
                    raise ValueError(f"{ticker}: EPS bridge is not annual plus aligned YTD")
                expected = float(facts["fy"]["value"]) + float(facts["current_ytd"]["value"]) - float(facts["prior_ytd"]["value"])
        if expected <= 0 or abs(float(issuer["metric_value_per_share"]) - expected) > 1e-9 or abs(float(issuer["normalization"]["normalized_value"]) - expected) > 1e-9:
            raise ValueError(f"{ticker}: reported and normalized per-share values do not reconcile")
        if issuer["normalization"]["original_currency"] != "PHP" or issuer["normalization"]["normalized_currency"] != "PHP":
            raise ValueError(f"{ticker}: currency normalization mismatch")
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
        "facts": {
            "reported_eps": issuer.get("reported_eps"),
            "reported_bvps": issuer.get("reported_bvps"),
            "metric_value_per_share": issuer["metric_value_per_share"],
            "metric_label": issuer["metric_label"],
            "normalization": issuer["normalization"],
            "intrinsic_blocker": issuer["intrinsic_blocker"],
        },
        "note": "This receipt binds manually reviewed public facts and links; it is not a copy of the remote filing or summary page.",
    }
    raw = canonical_json(receipt) + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    references = [{"document_id": digest[:16], "label": source["label"], "form": source["form"], "period_end": source["period_end"], "published_at": None, "url": source["url"], "source_page": None, "sha256": digest}]
    if supporting:
        references.append({"document_id": f"{digest[:16]}-support", "label": supporting["label"], "form": supporting["form"], "period_end": supporting["period_end"], "published_at": None, "url": supporting["url"], "source_page": None, "sha256": digest})
    return references, raw


def build_batch_artifacts(config: dict | None = None) -> dict[str, PseValuationArtifact]:
    config = config or load_batch_config()
    output = {}
    for ticker in FROZEN_BATCH_TICKERS:
        issuer = config["issuers"][ticker]
        policy = config["policies"][issuer["policy"]]
        sources, _ = source_receipt(ticker, config)
        relative = market_relative_range(metric=policy["metric"], metric_value_per_share=float(issuer["metric_value_per_share"]), assumptions=policy["assumptions"], relation=policy.get("relation", "multiple"))
        relative["estimates"] = {key: round(value, 9) for key, value in relative["estimates"].items()}
        relative.update({"policy_version": policy["version"], "metric_label": issuer["metric_label"], "source_status": "reviewed_public_fact", "source_document_sha256": sources[0]["sha256"], "source_page": None, "note": "Analyst screening band; no peer study or complete intrinsic FCFF/SOTP has been completed."})
        estimates = relative["estimates"]
        warnings = ["Screening-grade market-relative result, not intrinsic value or a peer-calibrated target.", "Operating cash flows, reinvestment and common-equity claims have not been reconciled."]
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
            filing_period=issuer["source"]["period_end"],
            availability_type="market_relative_only", publication_state="provisional",
            scenarios={"bear": None, "base": None, "bull": None},
            numerical_range={"low": min(estimates.values()), "high": max(estimates.values())},
            market_relative=relative,
            public_assumptions={"route_reason": issuer["route_reason"], "intrinsic_blocker": issuer["intrinsic_blocker"], "metric_basis": issuer["normalization"]["formula"], "policy_rationale": policy["rationale"], "reliability": "Low"},
            sources=sources, warnings=warnings, blocking_reasons=[issuer["intrinsic_blocker"]],
            input_hash=sha256_object({"ticker": ticker, "issuer": issuer, "policy": policy, "source": sources[0]["sha256"], "model_version": MODEL_VERSION}),
        ).with_artifact_hash()
    return output
