#!/usr/bin/env python3
"""Load the reviewed Phase A source set into Postgres and MinIO.

The script makes no network calls. It verifies every local file against the
existing audit manifest before upload and stores reported AP facts separately
from the provisional valuation assumptions.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.db import pool
from app.db_migrate import run_migrations
from app.pse_valuation import CATALOG_VERSION
from app.pse_valuation.persistence import (
    capture_document,
    store_assumption,
    store_reported_fact,
    store_valuation_run,
    upsert_security,
)
from app.pse_valuation.pipeline import PILOT_TICKERS, VALUATION_DATE
from app.pse_valuation.routing import route_for
from app.services import company_service


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = ROOT / "archive/local-data/pse"
CATALOG_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs" / CATALOG_VERSION
CORPUS_ROOT = ROOT / "archive/local-audit/pse/archetype-testing/corpora"
PREFERRED_DIR = {
    "AP": "Aboitiz Power Corp",
    "SCC": "Semirara",
    "BDO": "BDO Unibank",
    "AREIT": "AREIT",
    "ALI": "Ayala Land",
    "AC": "Ayala Corp",
}


def _resolve_file(ticker: str, filename: str) -> Path:
    matches = [path for path in ARCHIVE_ROOT.rglob(filename) if path.is_file()]
    preferred = [path for path in matches if PREFERRED_DIR[ticker] in path.parts]
    candidates = preferred or matches
    if len(candidates) != 1:
        raise RuntimeError(f"{ticker}: expected one source file for {filename}, found {len(candidates)}")
    return candidates[0]


def _corpus_documents(ticker: str) -> list[tuple[Path, str]]:
    if ticker == "BDO":
        manifest_path = ROOT / "archive/local-audit/pse/fs-testing/bdo/corpora/BDO/manifest.json"
    else:
        manifest_path = CORPUS_ROOT / ticker / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    rows = []
    for document in manifest["documents"]:
        path = _resolve_file(ticker, Path(document["path"]).name)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != document["sha256"]:
            raise RuntimeError(f"{ticker}: source hash mismatch for {path.name}")
        rows.append((path, digest))
    return rows


def _legacy_document(ticker: str) -> tuple[Path, str]:
    artifact = json.loads((CATALOG_ROOT / "artifacts" / f"{ticker}.json").read_text())
    source = artifact["sources"][0]
    if ticker == "ACR":
        path = ROOT / "archive/local-data/pse/company-universe/Industrial/Alsons Financial Statements/2026-04-15 ACR 17A_2025_Final_compressed.pdf"
    else:
        path = ROOT / "archive/local-data/pse/company-universe/Industrial/PetroEnergy Financial Statements/PERC SEC 17-A 2025.pdf"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != source["sha256"]:
        raise RuntimeError(f"{ticker}: legacy source hash mismatch")
    return path, digest


def main() -> None:
    pool.open()
    try:
        run_migrations()
        captured: dict[str, list[dict]] = {}
        retrieved_at = datetime.now(timezone.utc)
        for ticker in PILOT_TICKERS:
            route = route_for(ticker)
            security_id = f"PSE:{ticker}:COMMON"
            upsert_security(
                security_id=security_id,
                issuer_id=f"PSE:{ticker}",
                ticker=ticker,
                issuer_name=route["issuer_name"],
                subsector=route["subsector"],
                source_as_of=VALUATION_DATE,
            )
            company_service.upsert(
                ticker=ticker,
                name=route["issuer_name"],
                sector=route["subsector"],
                currency="PHP",
                market="PH",
                exchange="PSE",
            )
            documents = _corpus_documents(ticker) if ticker in PREFERRED_DIR else [_legacy_document(ticker)]
            captured[ticker] = []
            for path, _digest in documents:
                captured[ticker].append(
                    capture_document(
                        issuer_id=f"PSE:{ticker}",
                        security_id=security_id,
                        source_url=None,
                        published_at=None,
                        retrieved_at=retrieved_at,
                        filename=path.name,
                        raw=path.read_bytes(),
                    )
                )

        # AP retains its reviewed Phase A fact snapshot. Phase A.1 also stores
        # the seven source-linked per-share fallback metrics without promoting
        # them into specialist intrinsic-model facts.
        seed = json.loads((ROOT / "backend/app/seed/financials_data.json").read_text())
        ap = next(row for row in seed["companies"] if row["symbol"] == "AP")
        document_id = captured["AP"][-1]["id"]
        for metric, value, measurement in (
            ("cash", ap["financials"]["cash"] / 1_000_000, "stock"),
            ("total_debt", ap["financials"]["debt"] / 1_000_000, "stock"),
            ("shares_outstanding", ap["financials"]["shares"] / 1_000_000, "stock"),
            ("operating_income", ap["financials"]["operatingIncome"] / 1_000_000, "flow"),
            ("tax_expense", ap["financials"]["taxExpense"] / 1_000_000, "flow"),
        ):
            store_reported_fact(
                document_id,
                {
                    "metric": metric,
                    "value": value,
                    "currency": "PHP",
                    "unit_scale": "millions",
                    "period_end": date(2025, 12, 31),
                    "period_type": "annual" if measurement == "flow" else "instant",
                    "measurement_type": measurement,
                    "consolidation_scope": "consolidated",
                    "source_page": None,
                },
            )

        fallback_config = json.loads(
            (ROOT / "backend/app/pse_valuation/config/market_relative_fallbacks.json").read_text()
        )
        for ticker, fallback in fallback_config["fallbacks"].items():
            artifact = json.loads((CATALOG_ROOT / "artifacts" / f"{ticker}.json").read_text())
            expected_sha = artifact["market_relative"]["source_document_sha256"]
            document = next(
                (row for row in captured[ticker] if row["sha256"] == expected_sha),
                None,
            )
            if document is None:
                raise RuntimeError(f"{ticker}: fallback source was not captured")
            store_reported_fact(
                document["id"],
                {
                    "metric": (
                        "distribution_per_share"
                        if fallback["relation"] == "yield"
                        else "eps_basic"
                    ),
                    "value": fallback["metric_value_per_share"],
                    "currency": "PHP",
                    "unit_scale": "per_share",
                    "period_end": date.fromisoformat(fallback["period_end"]),
                    "period_type": "annual" if fallback["relation"] == "multiple" else "quarter",
                    "measurement_type": "flow",
                    "consolidation_scope": "issuer_reported",
                    "source_page": fallback["source_page"],
                },
            )

        macro = json.loads((ROOT / "backend/app/pse_valuation/config/macro_snapshot.json").read_text())
        store_assumption(
            {
                "version": macro["snapshot_version"],
                "scope": "PH",
                "metric": "risk_free_rate",
                "value": macro["risk_free_rate"],
                "unit": "decimal",
                "effective_date": date.fromisoformat(macro["risk_free_observed_at"]),
                "source_or_rationale": macro["risk_free_source"]["url"],
                "reviewer": "Phase A reviewed snapshot",
            }
        )
        for ticker, fallback in fallback_config["fallbacks"].items():
            for scenario, value in fallback["assumptions"].items():
                store_assumption(
                    {
                        "version": fallback_config["policy_version"],
                        "scope": ticker,
                        "metric": fallback["metric"],
                        "scenario": scenario,
                        "value": value,
                        "unit": "multiple" if fallback["relation"] == "multiple" else "decimal_yield",
                        "effective_date": VALUATION_DATE,
                        "source_or_rationale": fallback_config["note"],
                        "reviewer": "Phase A.1 market-relative fallback policy",
                    }
                )
        for ticker in PILOT_TICKERS:
            artifact = json.loads((CATALOG_ROOT / "artifacts" / f"{ticker}.json").read_text())
            store_valuation_run(artifact, {"artifact_hash": artifact["artifact_hash"]})
        print({"securities": 8, "documents": sum(map(len, captured.values())), "runs": 8})
    finally:
        pool.close()


if __name__ == "__main__":
    main()
