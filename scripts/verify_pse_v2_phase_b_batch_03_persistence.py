#!/usr/bin/env python3
"""Verify persisted Batch 3 evidence in the real Postgres and MinIO services."""

from __future__ import annotations

from app.db import pool, query
from app.pse_valuation.phase_b_batch_03 import FROZEN_BATCH_TICKERS, MODEL_VERSION
from app.storage import BUCKET, s3


def main() -> None:
    issuer_ids = [f"PSE:{ticker}" for ticker in FROZEN_BATCH_TICKERS]
    placeholders = ", ".join(["%s"] * len(FROZEN_BATCH_TICKERS))
    pool.open()
    try:
        securities = query(
            f"SELECT ticker FROM pse_securities WHERE ticker IN ({placeholders}) ORDER BY ticker",
            list(FROZEN_BATCH_TICKERS),
        )
        documents = query(
            f"SELECT id, issuer_id, object_key FROM pse_documents WHERE issuer_id IN ({placeholders}) ORDER BY issuer_id",
            issuer_ids,
        )
        facts = query(
            f"""
            SELECT COUNT(*) AS count
            FROM pse_reported_facts f
            JOIN pse_documents d ON d.id = f.document_id
            WHERE d.issuer_id IN ({placeholders})
            """,
            issuer_ids,
        )[0]["count"]
        assumptions = query(
            "SELECT COUNT(*) AS count FROM pse_assumptions WHERE version LIKE %s",
            ["%B03%"],
        )[0]["count"]
        runs = query(
            "SELECT COUNT(*) AS count FROM pse_valuation_runs WHERE model_version = %s",
            [MODEL_VERSION],
        )[0]["count"]
        verified_objects = 0
        for document in documents:
            s3.head_object(Bucket=BUCKET, Key=document["object_key"])
            verified_objects += 1
        expected = {
            "securities": len(FROZEN_BATCH_TICKERS),
            "documents": len(FROZEN_BATCH_TICKERS),
            "reported_facts": 32,
            "assumptions": 39,
            "runs": len(FROZEN_BATCH_TICKERS),
            "minio_objects": len(FROZEN_BATCH_TICKERS),
        }
        actual = {
            "securities": len(securities),
            "documents": len(documents),
            "reported_facts": int(facts),
            "assumptions": int(assumptions),
            "runs": int(runs),
            "minio_objects": verified_objects,
        }
        if actual != expected:
            raise RuntimeError(f"Batch 3 persistence mismatch: expected {expected}, got {actual}")
        print({"batch": MODEL_VERSION, **actual})
    finally:
        pool.close()


if __name__ == "__main__":
    main()
