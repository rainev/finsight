#!/usr/bin/env python3
"""Persist reviewed Phase B Batch 3 receipts, facts, assumptions, and runs."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.db import pool
from app.db_migrate import run_migrations
from app.pse_valuation.persistence import (
    capture_document,
    store_assumption,
    store_reported_fact,
    store_valuation_run,
    upsert_security,
)
from app.pse_valuation.phase_b_batch_03 import (
    FROZEN_BATCH_TICKERS,
    INTRINSIC_TICKERS,
    load_batch_config,
    source_receipt,
)
from app.services import company_service


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-03-candidate-a"


def main(candidate_root: Path = DEFAULT_CANDIDATE_ROOT) -> None:
    config = load_batch_config()
    catalog_root = candidate_root / config["catalog_version"]
    if not (catalog_root / "manifest.json").is_file():
        raise RuntimeError("build the Phase B Batch 3 candidate before loading evidence")
    pool.open()
    try:
        run_migrations()
        retrieved_at = datetime.now(timezone.utc)
        documents: dict[str, dict] = {}
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
            company_service.upsert(
                ticker=ticker,
                name=issuer["issuer_name"],
                sector=issuer["subsector"],
                currency="PHP",
                market="PH",
                exchange="PSE",
            )
            reference, raw = source_receipt(ticker, config)
            documents[ticker] = capture_document(
                issuer_id=f"PSE:{ticker}",
                security_id=security_id,
                source_url=reference["url"],
                published_at=(
                    datetime.fromisoformat(reference["published_at"] + "T00:00:00+00:00")
                    if reference.get("published_at")
                    else None
                ),
                retrieved_at=retrieved_at,
                filename=f"{ticker}-reviewed-fact-receipt.json",
                raw=raw,
                content_type="application/json",
            )

        period_end = date(2025, 12, 31)
        effective_date = date.fromisoformat(config["valuation_date"])
        for ticker in FROZEN_BATCH_TICKERS:
            issuer = config["issuers"][ticker]
            facts = issuer["facts"]
            document_id = documents[ticker]["id"]
            facts_to_store = [
                ("book_value_per_share", facts["book_value_per_share"], "per_share"),
                ("parent_common_equity", facts["parent_equity_php_millions"], "millions"),
            ]
            if ticker in INTRINSIC_TICKERS:
                facts_to_store.extend(
                    [
                        ("investment_property_carrying_value", facts["investment_property_carrying_value_php_millions"], "millions"),
                        ("investment_property_fair_value", facts["investment_property_fair_value_php_millions"], "millions"),
                        ("preferred_claims", facts["preferred_claims_php_millions"], "millions"),
                        ("shares_outstanding", facts["shares_millions"], "millions"),
                    ]
                )
            for metric, value, unit_scale in facts_to_store:
                store_reported_fact(
                    document_id,
                    {
                        "metric": metric,
                        "value": value,
                        "currency": "PHP",
                        "unit_scale": unit_scale,
                        "period_end": period_end,
                        "period_type": "instant",
                        "measurement_type": "stock",
                        "consolidation_scope": "parent_common",
                        "source_page": issuer["source"]["source_page"],
                    },
                )
            if ticker in INTRINSIC_TICKERS:
                policy = config["nav_policies"][issuer["policy"]]
                for scenario, values in policy["scenarios"].items():
                    for metric, value in values.items():
                        store_assumption(
                            {
                                "version": policy["version"],
                                "scope": ticker,
                                "metric": metric,
                                "scenario": scenario,
                                "value": value,
                                "unit": "decimal",
                                "effective_date": effective_date,
                                "source_or_rationale": policy["rationale"],
                                "reviewer": "Phase B Batch 3 reviewed policy",
                            }
                        )
            else:
                policy = config["relative_policies"][issuer["policy"]]
                for scenario, value in policy["assumptions"].items():
                    store_assumption(
                        {
                            "version": policy["policy_version"],
                            "scope": ticker,
                            "metric": policy["metric"],
                            "scenario": scenario,
                            "value": value,
                            "unit": "multiple",
                            "effective_date": effective_date,
                            "source_or_rationale": policy["rationale"],
                            "reviewer": "Phase B Batch 3 reviewed policy",
                        }
                    )

        for ticker in FROZEN_BATCH_TICKERS:
            artifact = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
            store_valuation_run(
                artifact,
                {
                    "artifact_hash": artifact["artifact_hash"],
                    "reviewed_fact_receipt_sha256": documents[ticker]["sha256"],
                },
            )
        print(
            {
                "batch": config["batch_version"],
                "securities": len(FROZEN_BATCH_TICKERS),
                "documents": len(documents),
                "reported_facts": len(FROZEN_BATCH_TICKERS) * 2 + len(INTRINSIC_TICKERS) * 4,
                "assumptions": (len(FROZEN_BATCH_TICKERS) - len(INTRINSIC_TICKERS)) * 3 + len(INTRINSIC_TICKERS) * 6,
                "runs": len(FROZEN_BATCH_TICKERS),
            }
        )
    finally:
        pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    args = parser.parse_args()
    main(args.candidate_root.resolve())
