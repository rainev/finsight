"""Check Batch 11 Postgres rows and object storage receipts."""

from app.db import pool, query
from app.pse_valuation.phase_b_batch_11 import (
    FROZEN_BATCH_TICKERS,
    MODEL_VERSION,
    build_batch_artifacts,
    load_batch_config,
    source_receipt,
)
from app.storage import BUCKET, s3


def main() -> None:
    issuer_ids = [f"PSE:{ticker}" for ticker in FROZEN_BATCH_TICKERS]
    placeholders = ", ".join(["%s"] * 10)
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    expected_documents = {f"PSE:{ticker}": source_receipt(ticker, config)[0]["sha256"] for ticker in FROZEN_BATCH_TICKERS}
    expected_runs = {f"PSE:{ticker}:COMMON": artifacts[ticker].input_hash for ticker in FROZEN_BATCH_TICKERS}
    pool.open()
    try:
        documents = query(f"SELECT id, issuer_id, sha256, object_key FROM pse_documents WHERE issuer_id IN ({placeholders})", issuer_ids)
        current_documents = [row for row in documents if row["sha256"] == expected_documents[row["issuer_id"]]]
        if len(current_documents) != 10:
            raise AssertionError("expected one current source receipt per issuer")
        current_ids = [row["id"] for row in current_documents]
        facts = query(
            f"SELECT COUNT(*) count FROM pse_reported_facts WHERE document_id IN ({placeholders})",
            current_ids,
        )[0]["count"]
        assumptions = query(
            f"SELECT COUNT(*) count FROM pse_assumptions WHERE version LIKE %s AND scope IN ({placeholders})",
            ["%B11%", *FROZEN_BATCH_TICKERS],
        )[0]["count"]
        runs = query("SELECT security_id, input_hash FROM pse_valuation_runs WHERE model_version=%s", [MODEL_VERSION])
        current_runs = [row for row in runs if row["input_hash"] == expected_runs.get(row["security_id"])]
        for document in current_documents:
            s3.head_object(Bucket=BUCKET, Key=document["object_key"])
        actual = (len(current_documents), int(facts), int(assumptions), len(current_runs))
        if actual != (10, 10, 30, 10):
            raise AssertionError(actual)
        print({"current_documents": 10, "current_facts": 10, "assumptions": 30, "current_runs": 10, "current_objects": 10, "superseded_receipts": len(documents) - 10})
    finally:
        pool.close()


if __name__ == "__main__":
    main()
