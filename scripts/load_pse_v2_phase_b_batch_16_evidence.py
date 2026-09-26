#!/usr/bin/env python3
"""Persist Batch 16 original-period facts, source receipts, policies, FX and runs."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.db import pool
from app.db_migrate import run_migrations
from app.pse_valuation.persistence import capture_document, store_assumption, store_reported_fact, store_valuation_run, upsert_security
from app.pse_valuation.phase_b_batch_16 import FROZEN_BATCH_TICKERS, load_batch_config, source_receipt
from app.services import company_service


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-16-candidate-a"


def _fact(document_id: int, *, metric: str, value: float, currency: str | None, unit_scale: str, period_end: str, period_type: str, measurement_type: str, scope: str) -> None:
    store_reported_fact(document_id, {"metric": metric, "value": value, "currency": currency, "unit_scale": unit_scale, "period_end": date.fromisoformat(period_end), "period_type": period_type, "measurement_type": measurement_type, "consolidation_scope": scope, "source_page": None})


def main(candidate_root: Path = DEFAULT_CANDIDATE_ROOT) -> None:
    config = load_batch_config()
    catalog_root = Path(candidate_root) / config["catalog_version"]
    pool.open()
    try:
        run_migrations()
        documents = {}
        for ticker in FROZEN_BATCH_TICKERS:
            issuer = config["issuers"][ticker]
            policy = config["policies"][issuer["policy"]]
            security_id = f"PSE:{ticker}:COMMON"
            upsert_security(security_id=security_id, issuer_id=f"PSE:{ticker}", ticker=ticker, issuer_name=issuer["issuer_name"], subsector=issuer["subsector"], source_as_of=date.fromisoformat(config["valuation_date"]))
            company_service.upsert(ticker=ticker, name=issuer["issuer_name"], sector=issuer["subsector"], currency="PHP", market="PH", exchange="PSE")
            references, raw = source_receipt(ticker, config)
            documents[ticker] = capture_document(issuer_id=f"PSE:{ticker}", security_id=security_id, source_url=references[0]["url"], published_at=None, retrieved_at=datetime.now(timezone.utc), filename=f"{ticker}-receipt.json", raw=raw, content_type="application/json")
            document_id = documents[ticker]["id"]
            kind = issuer["metric_kind"]
            if kind == "ttm_eps":
                for role, fact in issuer["reported_eps"].items():
                    _fact(document_id, metric=f"reported_basic_eps_{role}", value=fact["value"], currency="PHP", unit_scale="per_share", period_end=fact["period_end"], period_type=fact["period_type"], measurement_type="flow", scope="PSE_reported_basic_EPS_common_attribution_unreconciled")
            elif kind == "reported_bvps":
                fact = issuer["reported_bvps"]
                _fact(document_id, metric="reported_book_value_per_share", value=fact["value"], currency="PHP", unit_scale="per_share", period_end=fact["period_end"], period_type=fact["period_type"], measurement_type="stock", scope="PSE_reported_BVPS_common_basis_unreconciled")
            else:
                for role, fact in issuer["reported_revenue"].items():
                    _fact(document_id, metric=f"reported_revenue_{role}", value=fact["value"], currency=issuer["source"]["currency"], unit_scale=issuer["source"]["units"], period_end=fact["period_end"], period_type=fact["period_type"], measurement_type="flow", scope="PSE_reported_consolidated_revenue")
                shares = issuer["reported_shares"]
                _fact(document_id, metric="reported_common_shares_outstanding", value=shares["value"], currency="N/A", unit_scale="shares", period_end=shares["as_of"], period_type="point_in_time", measurement_type="stock", scope="PSE_listed_ordinary_common")
            for scenario, value in policy["assumptions"].items():
                store_assumption({"version": policy["version"], "scope": ticker, "metric": policy["metric"], "scenario": scenario, "value": value, "unit": "multiple", "effective_date": date.fromisoformat(config["valuation_date"]), "source_or_rationale": policy["rationale"], "reviewer": "Phase B Batch 16 reviewed screening policy"})
        fx = config["fx_snapshot"]
        store_assumption({"version": fx["version"], "scope": fx["pair"], "metric": "fx_rate_php_per_usd", "scenario": "all", "value": fx["rate_php_per_usd"], "unit": "PHP per USD", "effective_date": date.fromisoformat(fx["observed_at"]), "source_or_rationale": fx["source_url"], "reviewer": "Phase B Batch 16 reviewed carry-forward of Batch 13 BSP observation"})
        for ticker in FROZEN_BATCH_TICKERS:
            artifact = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
            store_valuation_run(artifact, {"artifact_hash": artifact["artifact_hash"], "receipt_sha256": documents[ticker]["sha256"]})
        print({"batch": config["batch_version"], "securities": 10, "documents": 10, "original_period_facts": 22, "multiple_assumptions": 30, "fx_assumptions": 1, "runs": 10})
    finally:
        pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    args = parser.parse_args()
    main(args.candidate_root)
