#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.db import pool
from app.db_migrate import run_migrations
from app.pse_valuation.persistence import capture_document, store_assumption, store_reported_fact, store_valuation_run, upsert_security
from app.pse_valuation.phase_b_batch_07 import FROZEN_BATCH_TICKERS, load_batch_config, source_receipt
from app.services import company_service


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-07-candidate-a"


def main(candidate_root=DEFAULT_CANDIDATE_ROOT):
    config = load_batch_config()
    catalog_root = Path(candidate_root) / config["catalog_version"]
    pool.open()
    try:
        run_migrations()
        documents = {}
        retrieved_at = datetime.now(timezone.utc)
        for ticker in FROZEN_BATCH_TICKERS:
            issuer = config["issuers"][ticker]
            security_id = f"PSE:{ticker}:COMMON"
            upsert_security(
                security_id=security_id,
                issuer_id=f"PSE:{ticker}",
                ticker=ticker,
                issuer_name=issuer["issuer_name"],
                subsector=issuer["subsector"],
                source_as_of=date.fromisoformat(config["valuation_date"]),
            )
            company_service.upsert(ticker=ticker, name=issuer["issuer_name"], sector=issuer["subsector"], currency="PHP", market="PH", exchange="PSE")
            reference, raw = source_receipt(ticker, config)
            documents[ticker] = capture_document(
                issuer_id=f"PSE:{ticker}",
                security_id=security_id,
                source_url=reference["url"],
                published_at=None,
                retrieved_at=retrieved_at,
                filename=f"{ticker}-receipt.json",
                raw=raw,
                content_type="application/json",
            )
            policy = config["policies"][issuer["policy"]]
            store_reported_fact(
                documents[ticker]["id"],
                {
                    "metric": "screening_metric_per_share",
                    "value": issuer["metric_value_per_share"],
                    "currency": "PHP",
                    "unit_scale": "per_share",
                    "period_end": date.fromisoformat(issuer["source"]["period_end"]),
                    "period_type": "annual" if ticker == "LSC" else "interim_or_ttm",
                    "measurement_type": "flow" if policy["metric"] in {"price_to_earnings", "price_to_sales"} else "stock",
                    "consolidation_scope": "consolidated_common",
                    "source_page": None,
                },
            )
            for scenario, value in policy["assumptions"].items():
                store_assumption(
                    {
                        "version": policy["version"],
                        "scope": ticker,
                        "metric": policy["metric"],
                        "scenario": scenario,
                        "value": value,
                        "unit": "multiple",
                        "effective_date": date.fromisoformat(config["valuation_date"]),
                        "source_or_rationale": issuer["route_reason"],
                        "reviewer": "Phase B Batch 7 reviewed policy",
                    }
                )
        for ticker in FROZEN_BATCH_TICKERS:
            artifact = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
            store_valuation_run(artifact, {"artifact_hash": artifact["artifact_hash"], "receipt_sha256": documents[ticker]["sha256"]})
        print({"batch": config["batch_version"], "securities": 10, "documents": 10, "reported_facts": 10, "assumptions": 30, "runs": 10})
    finally:
        pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    args = parser.parse_args()
    main(args.candidate_root)
