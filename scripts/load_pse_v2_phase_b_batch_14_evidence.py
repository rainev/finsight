#!/usr/bin/env python3
"""Persist Batch 14 reviewed receipts, original-period facts, policies and runs."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.db import pool
from app.db_migrate import run_migrations
from app.pse_valuation.persistence import capture_document, store_assumption, store_reported_fact, store_valuation_run, upsert_security
from app.pse_valuation.phase_b_batch_14 import FROZEN_BATCH_TICKERS, load_batch_config, source_receipt
from app.services import company_service


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-14-candidate-a"


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
            if ticker == "MEDIC":
                facts = [("reported_book_value_per_share", issuer["reported_bvps"], "stock", "PSE_reported_BVPS_parent_basis_unreconciled")]
            else:
                facts = [(f"reported_basic_eps_{role}", fact, "flow", "PSE_reported_basic_EPS_common_attribution_unreconciled") for role, fact in issuer["reported_eps"].items()]
            for metric, fact, measurement, scope in facts:
                store_reported_fact(documents[ticker]["id"], {"metric": metric, "value": fact["value"], "currency": "PHP", "unit_scale": "per_share", "period_end": date.fromisoformat(fact["period_end"]), "period_type": fact["period_type"], "measurement_type": measurement, "consolidation_scope": scope, "source_page": None})
            for scenario, value in policy["assumptions"].items():
                store_assumption({"version": policy["version"], "scope": ticker, "metric": policy["metric"], "scenario": scenario, "value": value, "unit": "multiple", "effective_date": date.fromisoformat(config["valuation_date"]), "source_or_rationale": policy["rationale"], "reviewer": "Phase B Batch 14 reviewed screening policy"})
        for ticker in FROZEN_BATCH_TICKERS:
            artifact = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
            store_valuation_run(artifact, {"artifact_hash": artifact["artifact_hash"], "receipt_sha256": documents[ticker]["sha256"]})
        print({"batch": config["batch_version"], "securities": 10, "documents": 10, "reported_facts": 26, "assumptions": 30, "runs": 10})
    finally:
        pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    args = parser.parse_args()
    main(args.candidate_root)
