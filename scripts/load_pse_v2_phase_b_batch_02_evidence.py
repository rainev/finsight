#!/usr/bin/env python3
"""Persist reviewed Phase B Batch 2 receipts, reported facts, assumptions, and runs."""

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
from app.pse_valuation.phase_b_batch_02 import (
    FROZEN_BATCH_TICKERS,
    INTRINSIC_TICKERS,
    load_batch_config,
    source_receipt,
)
from app.services import company_service


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-02-candidate-a"


def _reported_fact(
    *, metric: str, value: float, period_end: date, period_type: str, measurement_type: str, unit_scale: str
) -> dict:
    return {
        "metric": metric,
        "value": value,
        "currency": "PHP",
        "unit_scale": unit_scale,
        "period_end": period_end,
        "period_type": period_type,
        "measurement_type": measurement_type,
        "consolidation_scope": "consolidated_common",
        "source_page": None,
    }


def main(candidate_root: Path = DEFAULT_CANDIDATE_ROOT) -> None:
    config = load_batch_config()
    catalog_root = candidate_root / config["catalog_version"]
    if not (catalog_root / "manifest.json").is_file():
        raise RuntimeError("build the Phase B Batch 2 candidate before loading evidence")
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
                published_at=None,
                retrieved_at=retrieved_at,
                filename=f"{ticker}-reviewed-fact-receipt.json",
                raw=raw,
                content_type="application/json",
            )

        for ticker in FROZEN_BATCH_TICKERS:
            facts = config["issuers"][ticker]["facts"]
            document_id = documents[ticker]["id"]
            rows: list[dict] = []
            if ticker in INTRINSIC_TICKERS:
                for year in ("2023", "2024", "2025"):
                    period_end = date(int(year), 12, 31)
                    rows.extend(
                        [
                            _reported_fact(
                                metric="operating_cash_flow",
                                value=facts["operating_cash_flow_php_millions"][year],
                                period_end=period_end,
                                period_type="annual",
                                measurement_type="flow",
                                unit_scale="millions",
                            ),
                            _reported_fact(
                                metric="capital_expenditures",
                                value=facts["capital_expenditures_php_millions"][year],
                                period_end=period_end,
                                period_type="annual",
                                measurement_type="flow",
                                unit_scale="millions",
                            ),
                        ]
                    )
                for metric, key, unit in (
                    ("cash_and_eligible_investments", "cash_php_millions", "millions"),
                    ("interest_bearing_debt_including_leases", "debt_php_millions", "millions"),
                    ("shares_outstanding", "shares_millions", "millions"),
                ):
                    rows.append(
                        _reported_fact(
                            metric=metric,
                            value=facts[key],
                            period_end=date(2025, 12, 31),
                            period_type="instant",
                            measurement_type="stock",
                            unit_scale=unit,
                        )
                    )
                for metric, key in (
                    ("minority_value", "minority_value_php_millions"),
                    ("preferred_claims", "preferred_claims_php_millions"),
                ):
                    if float(facts.get(key, 0.0)) > 0:
                        rows.append(
                            _reported_fact(
                                metric=metric,
                                value=facts[key],
                                period_end=date(2025, 12, 31),
                                period_type="instant",
                                measurement_type="stock",
                                unit_scale="millions",
                            )
                        )
            else:
                rows.append(
                    _reported_fact(
                        metric="eps_basic",
                        value=facts["eps_basic"],
                        period_end=date(2025, 12, 31),
                        period_type="annual",
                        measurement_type="flow",
                        unit_scale="per_share",
                    )
                )
            for row in rows:
                store_reported_fact(document_id, row)

        effective_date = date.fromisoformat(config["valuation_date"])
        for ticker in INTRINSIC_TICKERS:
            issuer = config["issuers"][ticker]
            policy = config["fcff_policies"][issuer["policy"]]
            store_assumption(
                {
                    "version": policy["version"],
                    "scope": ticker,
                    "metric": "normalized_fcff_proxy",
                    "scenario": "all",
                    "value": issuer["facts"]["normalized_fcff_proxy_php_millions"],
                    "unit": "PHP millions",
                    "effective_date": effective_date,
                    "source_or_rationale": issuer["facts"]["normalization_method"],
                    "reviewer": "Phase B Batch 2 reviewed policy",
                }
            )
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
                            "reviewer": "Phase B Batch 2 reviewed policy",
                        }
                    )
        for ticker, policy in config["relative_policies"].items():
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
                        "source_or_rationale": "Screening fallback while the specialist FCFF bridge remains unresolved.",
                        "reviewer": "Phase B Batch 2 reviewed policy",
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
