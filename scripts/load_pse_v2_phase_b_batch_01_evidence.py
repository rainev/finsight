#!/usr/bin/env python3
"""Persist reviewed Phase B Batch 1 fact receipts, assumptions, and runs."""

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
from app.pse_valuation.phase_b_batch_01 import (
    BANK_TICKERS,
    FROZEN_BATCH_TICKERS,
    load_batch_config,
    source_receipt,
)
from app.services import company_service


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-01"


def _fact(
    *,
    metric: str,
    value: float,
    period_end: date,
    period_type: str,
    measurement_type: str,
    unit_scale: str,
) -> dict:
    return {
        "metric": metric,
        "value": value,
        "currency": "PHP",
        "unit_scale": unit_scale,
        "period_end": period_end,
        "period_type": period_type,
        "measurement_type": measurement_type,
        "consolidation_scope": "parent_common",
        "source_page": None,
    }


def main(candidate_root: Path = DEFAULT_CANDIDATE_ROOT) -> None:
    config = load_batch_config()
    catalog_root = candidate_root / config["catalog_version"]
    if not (catalog_root / "manifest.json").is_file():
        raise RuntimeError("build the Phase B Batch 1 candidate before loading evidence")

    pool.open()
    try:
        run_migrations()
        documents: dict[str, dict] = {}
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
                published_at=None,
                retrieved_at=retrieved_at,
                filename=f"{ticker}-reviewed-fact-receipt.json",
                raw=raw,
                content_type="application/json",
            )

        for ticker in FROZEN_BATCH_TICKERS:
            facts = config["issuers"][ticker]["facts"]
            document_id = documents[ticker]["id"]
            if ticker in BANK_TICKERS:
                rows = (
                    _fact(
                        metric="parent_common_equity",
                        value=facts["prior_parent_common_equity_php_millions"],
                        period_end=date(2024, 12, 31),
                        period_type="instant",
                        measurement_type="stock",
                        unit_scale="millions",
                    ),
                    _fact(
                        metric="parent_common_equity",
                        value=facts["parent_common_equity_php_millions"],
                        period_end=date(2025, 12, 31),
                        period_type="instant",
                        measurement_type="stock",
                        unit_scale="millions",
                    ),
                    _fact(
                        metric="net_income_to_parent",
                        value=facts["net_income_to_parent_php_millions"],
                        period_end=date(2025, 12, 31),
                        period_type="annual",
                        measurement_type="flow",
                        unit_scale="millions",
                    ),
                    _fact(
                        metric="book_value_per_share",
                        value=facts["book_value_per_share"],
                        period_end=date(2025, 12, 31),
                        period_type="instant",
                        measurement_type="stock",
                        unit_scale="per_share",
                    ),
                    _fact(
                        metric="eps_basic",
                        value=facts["basic_eps"],
                        period_end=date(2025, 12, 31),
                        period_type="annual",
                        measurement_type="flow",
                        unit_scale="per_share",
                    ),
                )
            else:
                rows = (
                    _fact(
                        metric="distribution_per_share",
                        value=facts["distribution_per_share"],
                        period_end=date(2025, 12, 31),
                        period_type="annual",
                        measurement_type="flow",
                        unit_scale="per_share",
                    ),
                    _fact(
                        metric="book_value_per_share",
                        value=facts["book_value_per_share"],
                        period_end=date(2025, 12, 31),
                        period_type="instant",
                        measurement_type="stock",
                        unit_scale="per_share",
                    ),
                    _fact(
                        metric="shares_outstanding",
                        value=facts["shares_millions"],
                        period_end=date(2025, 12, 31),
                        period_type="instant",
                        measurement_type="stock",
                        unit_scale="millions",
                    ),
                )
            for row in rows:
                store_reported_fact(document_id, row)

        bank_policy = config["bank_policy"]
        for ticker in BANK_TICKERS:
            for scenario, values in bank_policy["scenarios"].items():
                for metric, value in values.items():
                    store_assumption(
                        {
                            "version": bank_policy["version"],
                            "scope": ticker,
                            "metric": metric,
                            "scenario": scenario,
                            "value": value,
                            "unit": "decimal",
                            "effective_date": date.fromisoformat(config["valuation_date"]),
                            "source_or_rationale": bank_policy["rationale"],
                            "reviewer": "Phase B Batch 1 reviewed policy",
                        }
                    )
        for ticker in set(FROZEN_BATCH_TICKERS) - set(BANK_TICKERS):
            policy = config["reit_policies"][config["issuers"][ticker]["policy"]]
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
                            "effective_date": date.fromisoformat(config["valuation_date"]),
                            "source_or_rationale": policy["rationale"],
                            "reviewer": "Phase B Batch 1 reviewed policy",
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
