#!/usr/bin/env python3
"""Persist reviewed Phase B Batch 4 receipts, facts, assumptions, and runs."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.db import pool
from app.db_migrate import run_migrations
from app.pse_valuation.persistence import capture_document, store_assumption, store_reported_fact, store_valuation_run, upsert_security
from app.pse_valuation.phase_b_batch_04 import FROZEN_BATCH_TICKERS, INTRINSIC_TICKERS, load_batch_config, source_receipts
from app.services import company_service


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-04-candidate-a"


def _fact(
    metric: str,
    value: float,
    unit_scale: str,
    *,
    period_end: date,
    scope: str = "parent_common",
    period_type: str = "instant",
    measurement_type: str = "stock",
) -> dict:
    return {
        "metric": metric,
        "value": value,
        "currency": "PHP",
        "unit_scale": unit_scale,
        "period_end": period_end,
        "period_type": period_type,
        "measurement_type": measurement_type,
        "consolidation_scope": scope,
        "source_page": None,
    }


def main(candidate_root: Path = DEFAULT_CANDIDATE_ROOT) -> None:
    config = load_batch_config()
    catalog_root = candidate_root / config["catalog_version"]
    if not (catalog_root / "manifest.json").is_file():
        raise RuntimeError("build the Phase B Batch 4 candidate before loading evidence")
    pool.open()
    try:
        run_migrations()
        retrieved_at = datetime.now(timezone.utc)
        documents: dict[str, list[dict]] = {}
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
            documents[ticker] = []
            for index, (reference, raw) in enumerate(source_receipts(ticker, config), start=1):
                documents[ticker].append(
                    capture_document(
                        issuer_id=f"PSE:{ticker}",
                        security_id=security_id,
                        source_url=reference["url"],
                        published_at=date.fromisoformat(reference["published_at"]) if reference.get("published_at") else None,
                        retrieved_at=retrieved_at,
                        filename=f"{ticker}-reviewed-fact-receipt-{index:02d}.json",
                        raw=raw,
                        content_type="application/json",
                    )
                )

        effective_date = date.fromisoformat(config["valuation_date"])
        for ticker in FROZEN_BATCH_TICKERS:
            issuer = config["issuers"][ticker]
            facts = issuer["facts"]
            annual_document_id = documents[ticker][0]["id"]
            annual_period_end = date.fromisoformat(issuer["sources"][0]["period_end"])
            rows = [
                _fact("book_value_per_share", facts["book_value_per_share"], "per_share", period_end=annual_period_end),
                _fact("reported_equity", facts["reported_equity_php_millions"], "millions", period_end=annual_period_end),
            ]
            if ticker in INTRINSIC_TICKERS:
                rows.extend(
                    [
                        _fact("shares_outstanding", facts["shares_millions"], "millions", period_end=annual_period_end),
                        _fact(
                            "common_distribution_per_share",
                            facts["current_distribution_per_share"],
                            "per_share",
                            period_end=date.fromisoformat(issuer["sources"][-1]["period_end"]),
                            period_type="annual",
                            measurement_type="flow",
                        ),
                    ]
                )
            for row in rows:
                target_document_id = documents[ticker][-1]["id"] if row["metric"] == "common_distribution_per_share" else annual_document_id
                store_reported_fact(target_document_id, row)

            if ticker in INTRINSIC_TICKERS:
                policy = config["distribution_policies"][issuer["policy"]]
                for scenario, values in policy["scenarios"].items():
                    for metric, value in values.items():
                        store_assumption(
                            {"version": policy["version"], "scope": ticker, "metric": metric, "scenario": scenario, "value": value, "unit": "decimal", "effective_date": effective_date, "source_or_rationale": policy["rationale"], "reviewer": "Phase B Batch 4 reviewed policy"}
                        )
            else:
                policy = config["relative_policies"][issuer["policy"]]
                for scenario, value in policy["assumptions"].items():
                    store_assumption(
                        {"version": policy["policy_version"], "scope": ticker, "metric": policy["metric"], "scenario": scenario, "value": value, "unit": "multiple", "effective_date": effective_date, "source_or_rationale": policy["rationale"], "reviewer": "Phase B Batch 4 reviewed policy"}
                    )

        for ticker in FROZEN_BATCH_TICKERS:
            artifact = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
            store_valuation_run(artifact, {"artifact_hash": artifact["artifact_hash"], "reviewed_fact_receipt_sha256": [row["sha256"] for row in documents[ticker]]})
        print({"batch": config["batch_version"], "securities": 10, "documents": sum(len(rows) for rows in documents.values()), "reported_facts": 28, "assumptions": 45, "runs": 10})
    finally:
        pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    args = parser.parse_args()
    main(args.candidate_root.resolve())
