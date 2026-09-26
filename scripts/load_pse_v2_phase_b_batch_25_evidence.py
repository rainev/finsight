#!/usr/bin/env python3
"""Persist reviewed Batch 25 receipts, reported facts and staged run records."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.db import pool
from app.db_migrate import run_migrations
from app.pse_valuation.persistence import capture_document, store_assumption, store_reported_fact, store_valuation_run, upsert_security
from app.pse_valuation.phase_b_batch_25 import FROZEN_BATCH_TICKERS, load_batch_config, source_receipt
from app.services import company_service


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-25-candidate-a"
BRIDGE_VERSION = "PSE-V2-COMMON-DENOMINATOR-B25-1.0"


def _fact(document_id: int, *, metric: str, value: float, currency: str, unit_scale: str, period_end: str, period_type: str, scope: str) -> None:
    store_reported_fact(document_id, {
        "metric": metric, "value": value, "currency": currency, "unit_scale": unit_scale,
        "period_end": date.fromisoformat(period_end), "period_type": period_type,
        "measurement_type": "stock", "consolidation_scope": scope, "source_page": None,
    })


def main(candidate_root: Path = DEFAULT_CANDIDATE_ROOT) -> None:
    config = load_batch_config()
    catalog_root = Path(candidate_root) / config["catalog_version"]
    pool.open()
    try:
        run_migrations()
        documents = {}
        fact_count = 0
        denominator_count = 0
        multiple_count = 0
        for ticker in FROZEN_BATCH_TICKERS:
            issuer = config["issuers"][ticker]
            security_id = f"PSE:{ticker}:COMMON"
            upsert_security(
                security_id=security_id, issuer_id=f"PSE:{ticker}", ticker=ticker,
                issuer_name=issuer["issuer_name"], subsector=issuer["subsector"],
                source_as_of=date.fromisoformat(issuer["status_as_of"]),
                listing_status="suspended" if issuer["trading_status"] == "suspended" else "listed",
            )
            company_service.upsert(ticker=ticker, name=issuer["issuer_name"], sector=issuer["subsector"], currency="PHP", market="PH", exchange="PSE")
            references, raw = source_receipt(ticker, config)
            documents[ticker] = capture_document(
                issuer_id=f"PSE:{ticker}", security_id=security_id,
                source_url=references[0]["url"], published_at=None,
                retrieved_at=datetime.now(timezone.utc), filename=f"{ticker}-receipt.json",
                raw=raw, content_type="application/json",
            )
            document_id = documents[ticker]["id"]
            if issuer["equity_value"] is not None:
                _fact(document_id, metric=f"reported_{issuer['equity_basis']}_equity", value=issuer["equity_value"], currency="PHP", unit_scale=issuer["equity_unit_scale"], period_end=issuer["period_end"], period_type="interim", scope=f"PSE_reported_{issuer['equity_basis']}_equity")
                _fact(document_id, metric="reported_book_value_per_share", value=issuer["reported_bvps"], currency="PHP", unit_scale="per_share", period_end=issuer["period_end"], period_type="interim", scope="PSE_reported_BVPS_not_automatically_parent_common")
                fact_count += 2
            for share_class in issuer["share_classes"]:
                metric = "reported_common_shares_" + share_class["class"].lower().replace(" ", "_").replace("/", "_")
                _fact(document_id, metric=metric, value=share_class["shares"], currency="N/A", unit_scale="shares", period_end=share_class["as_of"], period_type="point_in_time", scope=f"PSE_reported_{share_class['class']}_common_outstanding")
                fact_count += 1
            if issuer.get("preferred_shares_outstanding") is not None:
                _fact(document_id, metric="reported_preferred_shares_outstanding", value=issuer["preferred_shares_outstanding"], currency="N/A", unit_scale="shares", period_end=issuer["preferred_shares_as_of"], period_type="point_in_time", scope="PSE_reported_senior_preferred_shares_claim_value_unresolved")
                fact_count += 1
            if issuer["share_bridge_type"] == "single_class":
                store_assumption({
                    "version": BRIDGE_VERSION, "scope": ticker, "metric": "reviewed_ordinary_common_denominator",
                    "scenario": "all", "value": issuer["shares_outstanding"], "unit": "shares",
                    "effective_date": date.fromisoformat(config["valuation_date"]),
                    "source_or_rationale": f"single_class: {issuer['source_warning']}",
                    "reviewer": "Phase B Batch 25 reviewed common-share bridge",
                })
                denominator_count += 1
            if issuer["policy"] is not None:
                policy = config["policies"][issuer["policy"]]
                for scenario, value in policy["assumptions"].items():
                    store_assumption({
                        "version": policy["version"], "scope": ticker, "metric": policy["metric"],
                        "scenario": scenario, "value": value, "unit": "multiple",
                        "effective_date": date.fromisoformat(config["valuation_date"]),
                        "source_or_rationale": policy["rationale"],
                        "reviewer": "Phase B Batch 25 reviewed screening policy",
                    })
                    multiple_count += 1
        for ticker in FROZEN_BATCH_TICKERS:
            artifact = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
            store_valuation_run(artifact, {"artifact_hash": artifact["artifact_hash"], "receipt_sha256": documents[ticker]["sha256"]})
        print({
            "batch": config["batch_version"], "securities": 10, "receipt_objects": 10,
            "reported_facts": fact_count, "reviewed_denominators": denominator_count,
            "multiple_assumptions": multiple_count, "runs": 10,
        })
    finally:
        pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    args = parser.parse_args()
    main(args.candidate_root)
