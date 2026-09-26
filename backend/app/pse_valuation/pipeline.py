"""Deterministic Phase A artifact builder over reviewed local evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from . import MODEL_VERSION
from .contract import PseValuationArtifact, ScenarioValue, blocked_artifact, sha256_object
from .models import fcff_valuation
from .models.comparables import market_relative_range
from .routing import route_for


PILOT_TICKERS = ("AC", "ACR", "ALI", "AP", "AREIT", "BDO", "PERC", "SCC")
VALUATION_DATE = date(2026, 9, 21)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _document_source(document: dict[str, Any]) -> dict[str, Any]:
    raw_path = str(document.get("path") or "")
    label = Path(raw_path).name or "Reviewed PSE filing"
    return {
        "document_id": str(document["sha256"])[:16],
        "label": label,
        "form": "17-A" if "17-A" in label or "17A" in label else "17-Q" if "17-Q" in label or "17Q" in label else None,
        "period_end": None,
        "published_at": None,
        "url": None,
        "source_page": None,
        "sha256": document["sha256"],
    }


def _corpus_sources(ticker: str, root: Path) -> list[dict[str, Any]]:
    if ticker == "BDO":
        manifest_path = root / "archive/local-audit/pse/fs-testing/bdo/corpora/BDO/manifest.json"
    else:
        manifest_path = root / "archive/local-audit/pse/archetype-testing/corpora" / ticker / "manifest.json"
    manifest = _read_json(manifest_path)
    return [_document_source(document) for document in manifest.get("documents", [])]


def _file_source(path: Path, *, label: str, source_page: int | None = None) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "document_id": hashlib.sha256(raw).hexdigest()[:16],
        "label": label,
        "form": "17-A",
        "period_end": "2025-12-31",
        "published_at": None,
        "url": None,
        "source_page": source_page,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _ap_artifact(root: Path) -> PseValuationArtifact:
    seed = _read_json(root / "backend/app/seed/financials_data.json")
    company = next(row for row in seed["companies"] if row["symbol"] == "AP")
    financials = company["financials"]
    valuation = company["valuation"]
    route = route_for("AP")
    macro = _read_json(Path(__file__).with_name("config") / "macro_snapshot.json")

    normalized_fcff = float(valuation["normalizedFcf"]) / 1_000_000
    cash = float(financials["cash"]) / 1_000_000
    debt = float(financials["debt"]) / 1_000_000
    shares = float(financials["shares"]) / 1_000_000
    scenarios = {
        "bear": {"growth_rate": 0.02, "roic": 0.10, "wacc": 0.125, "terminal_growth": 0.025, "terminal_roic": 0.095},
        "base": {"growth_rate": 0.035, "roic": 0.12, "wacc": 0.115, "terminal_growth": 0.03, "terminal_roic": 0.11},
        "bull": {"growth_rate": 0.05, "roic": 0.14, "wacc": 0.105, "terminal_growth": 0.035, "terminal_roic": 0.125},
    }
    results: dict[str, ScenarioValue] = {}
    for name, assumptions in scenarios.items():
        starting_nopat_proxy = normalized_fcff / (
            1 - assumptions["growth_rate"] / assumptions["roic"]
        )
        valued = fcff_valuation(
            starting_nopat=starting_nopat_proxy,
            growth_rate=assumptions["growth_rate"],
            roic=assumptions["roic"],
            wacc=assumptions["wacc"],
            terminal_growth=assumptions["terminal_growth"],
            terminal_roic=assumptions["terminal_roic"],
            cash=cash,
            debt=debt,
            shares_outstanding=shares,
        )
        if valued["common_equity_value"] <= 0 or valued["value_per_share"] <= 0:
            raise ValueError(f"AP {name} scenario produced non-positive common equity value")
        results[name] = ScenarioValue(
            value_per_share=valued["value_per_share"],
            common_equity_value=valued["common_equity_value"],
            enterprise_value=valued["enterprise_value"],
        )

    values = [result.value_per_share for result in results.values()]
    input_snapshot = {
        "ticker": "AP",
        "normalized_fcff_php_millions": normalized_fcff,
        "cash_php_millions": cash,
        "debt_php_millions": debt,
        "shares_millions": shares,
        "scenarios": scenarios,
        "macro_snapshot_version": macro["snapshot_version"],
        "model_version": MODEL_VERSION,
    }
    return PseValuationArtifact(
        ticker="AP",
        issuer={"issuer_id": "PSE:AP", "name": route["issuer_name"]},
        security={"security_id": "PSE:AP:COMMON", "type": "ordinary_common"},
        subsector=route["subsector"],
        primary_model=route["primary_model"],
        valuation_date=VALUATION_DATE,
        filing_period="FY 2025",
        filing_published_at="2026-04-15",
        availability_type="intrinsic_valuation",
        publication_state="provisional",
        scenarios=results,
        numerical_range={"low": min(values), "high": max(values)},
        public_assumptions={
            "forecast_years": 5,
            "normalized_fcff_proxy_php_millions": normalized_fcff,
            "macro_snapshot_version": macro["snapshot_version"],
            "risk_free_rate": macro["risk_free_rate"],
            "scenario_assumptions": scenarios,
            "route_reason": route["reason"],
        },
        sensitivities=[],
        sources=_corpus_sources("AP", root),
        warnings=[
            "Provisional Phase A estimate: normalized FCFF is a reviewed analyst proxy, not a fully rebuilt segment forecast.",
            "The dated benchmark observation is not represented as a current market rate.",
            "Segment revenue and segment capex remain incomplete in the automated corpus review.",
        ],
        blocking_reasons=[],
        input_hash=sha256_object(input_snapshot),
    ).with_artifact_hash()


def _blocked_from_corpus(ticker: str, root: Path) -> PseValuationArtifact:
    route = route_for(ticker)
    validation_path = root / "archive/local-audit/pse/archetype-testing/corpora" / ticker / "validation.json"
    validation = _read_json(validation_path)
    failed = [check["message"] for check in validation.get("checks", []) if check.get("status") != "pass"]
    reasons = failed or ["Required specialist-model inputs have not completed human review."]
    snapshot = {
        "ticker": ticker,
        "route": route,
        "validation_summary": validation.get("summary"),
        "blocking_reasons": reasons,
    }
    return blocked_artifact(
        ticker=ticker,
        issuer_name=route["issuer_name"],
        subsector=route["subsector"],
        primary_model=route["primary_model"],
        valuation_date=VALUATION_DATE,
        sources=_corpus_sources(ticker, root),
        blocking_reasons=reasons,
        input_snapshot=snapshot,
    )


def _blocked_legacy_source(ticker: str, root: Path) -> PseValuationArtifact:
    route = route_for(ticker)
    if ticker == "ACR":
        path = root / "archive/local-data/pse/company-universe/Industrial/Alsons Financial Statements/2026-04-15 ACR 17A_2025_Final_compressed.pdf"
        page = 63
    elif ticker == "PERC":
        path = root / "archive/local-data/pse/company-universe/Industrial/PetroEnergy Financial Statements/PERC SEC 17-A 2025.pdf"
        page = 30
    else:
        raise ValueError(ticker)
    source = _file_source(path, label=path.name, source_page=page)
    reasons = [
        "The consolidated filing is captured, but attributable SOTP component values and ownership-scoped claims have not been reviewed.",
        "The legacy single-company estimate is not promoted into the specialist V2 route.",
    ]
    return blocked_artifact(
        ticker=ticker,
        issuer_name=route["issuer_name"],
        subsector=route["subsector"],
        primary_model=route["primary_model"],
        valuation_date=VALUATION_DATE,
        sources=[source],
        blocking_reasons=reasons,
        input_snapshot={"ticker": ticker, "route": route, "source_sha256": source["sha256"]},
    )


def _market_relative_artifact(
    ticker: str,
    specialist_artifact: PseValuationArtifact,
) -> PseValuationArtifact:
    config = _read_json(Path(__file__).with_name("config") / "market_relative_fallbacks.json")
    if config.get("schema_version") != "PSE-V2-MARKET-RELATIVE-1.0":
        raise ValueError("unsupported market-relative fallback configuration")
    policy = config["fallbacks"][ticker]
    result = market_relative_range(
        metric=policy["metric"],
        metric_value_per_share=policy["metric_value_per_share"],
        assumptions=policy["assumptions"],
        relation=policy["relation"],
    )
    result.update(
        {
            "policy_version": config["policy_version"],
            "metric_label": policy["metric_label"],
            "source_status": policy["source_status"],
            "source_document_sha256": (
                specialist_artifact.sources[0].sha256
                if policy["source_document_sha256"] == "SOURCE_FROM_EXISTING_ARTIFACT"
                else policy["source_document_sha256"]
            ),
            "source_page": policy["source_page"],
            "note": config["note"],
        }
    )
    if result["source_document_sha256"] not in {
        source.sha256 for source in specialist_artifact.sources
    }:
        raise ValueError(f"{ticker}: market-relative source is not in the artifact evidence set")
    payload = specialist_artifact.model_dump(mode="json")
    payload.update(
        {
            "model_version": MODEL_VERSION,
            "filing_period": policy["filing_period"],
            "availability_type": "market_relative_only",
            "publication_state": "provisional",
            "market_relative": result,
            "numerical_range": {
                "low": result["estimates"]["low"],
                "high": result["estimates"]["high"],
            },
            "warnings": [
                "Screening-grade market-relative estimate; this is not the specialist intrinsic valuation.",
                "Policy bands are initial conventions and are not presented as empirically validated issuer peer sets.",
                *(
                    ["The selected per-share metric is a source candidate that still requires human review."]
                    if policy["source_status"] == "review_candidate"
                    else []
                ),
            ],
            "input_hash": sha256_object(
                {
                    "specialist_input_hash": specialist_artifact.input_hash,
                    "fallback_policy": policy,
                    "policy_version": config["policy_version"],
                    "model_version": MODEL_VERSION,
                }
            ),
            "artifact_hash": None,
        }
    )
    return PseValuationArtifact.model_validate(payload).with_artifact_hash()


def build_pilot_artifacts(root: Path | None = None) -> dict[str, PseValuationArtifact]:
    repo = (root or _repo_root()).resolve()
    artifacts = {"AP": _ap_artifact(repo)}
    for ticker in ("SCC", "BDO", "AREIT", "ALI", "AC"):
        artifacts[ticker] = _market_relative_artifact(
            ticker, _blocked_from_corpus(ticker, repo)
        )
    for ticker in ("ACR", "PERC"):
        artifacts[ticker] = _market_relative_artifact(
            ticker, _blocked_legacy_source(ticker, repo)
        )
    if tuple(sorted(artifacts)) != PILOT_TICKERS:
        raise ValueError("Phase A artifact set does not match the frozen pilot")
    return {ticker: artifacts[ticker] for ticker in PILOT_TICKERS}
