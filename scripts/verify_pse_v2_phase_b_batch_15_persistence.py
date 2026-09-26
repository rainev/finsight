"""Verify exact current Batch 15 receipts, source periods, delisting, and runs."""

from app.db import pool, query
from app.pse_valuation.phase_b_batch_15 import BLOCKED_TICKERS, FROZEN_BATCH_TICKERS, MODEL_VERSION, build_batch_artifacts, load_batch_config, source_receipt
from app.storage import BUCKET, s3


def main() -> None:
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    expected_docs = {f"PSE:{ticker}": source_receipt(ticker, config)[0][0]["sha256"] for ticker in FROZEN_BATCH_TICKERS}
    expected_runs = {f"PSE:{ticker}:COMMON": artifacts[ticker].input_hash for ticker in FROZEN_BATCH_TICKERS}
    placeholders = ", ".join(["%s"] * 10)
    pool.open()
    try:
        documents = query(f"SELECT id, issuer_id, sha256, object_key FROM pse_documents WHERE issuer_id IN ({placeholders})", list(expected_docs))
        current = [row for row in documents if row["sha256"] == expected_docs[row["issuer_id"]]]
        if len(current) != 10:
            raise AssertionError("expected ten current reviewed receipts")
        facts = query(f"SELECT d.issuer_id, f.value, f.currency, f.unit_scale, f.period_end, f.period_type, f.consolidation_scope FROM pse_reported_facts f JOIN pse_documents d ON d.id=f.document_id WHERE f.document_id IN ({placeholders})", [row["id"] for row in current])
        if len(facts) != 10:
            raise AssertionError("expected ten original-period facts")
        for row in facts:
            ticker = row["issuer_id"].split(":", 1)[1]
            fact = config["issuers"][ticker]["reported_bvps"]
            if row["currency"] != "PHP" or row["unit_scale"] != "per_share" or row["period_end"].isoformat() != fact["period_end"] or row["period_type"] != fact["period_type"] or abs(float(row["value"]) - float(fact["value"])) > 1e-9:
                raise AssertionError(f"{ticker}: original-period fact drift")
            if ticker in BLOCKED_TICKERS and row["consolidation_scope"] != "PSE_historical_pre_delisting_BVPS":
                raise AssertionError("HOUSE fact was relabeled as current")
        securities = query(f"SELECT ticker, listing_status FROM pse_securities WHERE ticker IN ({placeholders})", list(FROZEN_BATCH_TICKERS))
        if len(securities) != 10 or any(row["listing_status"] != ("delisted" if row["ticker"] in BLOCKED_TICKERS else "listed") for row in securities):
            raise AssertionError("listing status drift")
        assumptions = query(f"SELECT COUNT(*) count FROM pse_assumptions WHERE version=%s AND scope IN ({placeholders})", [config["policy"]["version"], *FROZEN_BATCH_TICKERS])[0]["count"]
        runs = query("SELECT security_id, input_hash FROM pse_valuation_runs WHERE model_version=%s", [MODEL_VERSION])
        current_runs = [row for row in runs if row["input_hash"] == expected_runs.get(row["security_id"])]
        for document in current:
            s3.head_object(Bucket=BUCKET, Key=document["object_key"])
        if (int(assumptions), len(current_runs)) != (27, 10):
            raise AssertionError((assumptions, len(current_runs)))
        print({"current_documents": 10, "original_period_facts": 10, "assumptions": 27, "current_runs": 10, "current_objects": 10, "house_listing_status": "delisted", "house_period": "2025-06-30", "alco_period": "2026-03-31"})
    finally:
        pool.close()


if __name__ == "__main__":
    main()
