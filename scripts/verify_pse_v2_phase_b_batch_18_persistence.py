"""Read back Batch 18 reviewed facts, policies, runs and MinIO receipts."""

from app.db import pool, query
from app.pse_valuation.phase_b_batch_18 import FROZEN_BATCH_TICKERS, MODEL_VERSION, build_batch_artifacts, load_batch_config, source_receipt
from app.storage import BUCKET, s3


def main() -> None:
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    expected_docs = {f"PSE:{ticker}": source_receipt(ticker, config)[0][0]["sha256"] for ticker in FROZEN_BATCH_TICKERS}
    expected_runs = {f"PSE:{ticker}:COMMON": artifacts[ticker].input_hash for ticker in FROZEN_BATCH_TICKERS}
    placeholders = ", ".join(["%s"] * 10)
    expected_facts = {}
    for ticker, issuer in config["issuers"].items():
        if issuer["metric_kind"] == "reported_bvps":
            expected_facts[(ticker, "reported_book_value_per_share")] = (issuer["reported_bvps"], "PHP", "per_share")
        else:
            expected_facts[(ticker, "reported_total_book_value_per_share")] = (issuer["reported_total_bvps"], "PHP", "per_share")
            parent = issuer["reported_parent_equity"]
            expected_facts[(ticker, "reported_parent_equity")] = (parent, "PHP", parent["unit_scale"])
            shares = issuer["reported_shares"]
            expected_facts[(ticker, "reported_common_shares_outstanding")] = ({"value": shares["value"], "period_end": shares["as_of"], "period_type": "point_in_time"}, "N/A", "shares")
    pool.open()
    try:
        documents = query(f"SELECT id, issuer_id, sha256, object_key FROM pse_documents WHERE issuer_id IN ({placeholders})", list(expected_docs))
        current = [row for row in documents if row["sha256"] == expected_docs[row["issuer_id"]]]
        if len(current) != 10:
            raise AssertionError("expected ten current reviewed receipts")
        facts = query(f"SELECT d.issuer_id, f.metric, f.value, f.currency, f.unit_scale, f.period_end, f.period_type FROM pse_reported_facts f JOIN pse_documents d ON d.id=f.document_id WHERE f.document_id IN ({placeholders})", [row["id"] for row in current])
        if len(facts) != 16 or len(expected_facts) != 16:
            raise AssertionError("expected 16 original-period facts")
        for row in facts:
            ticker = row["issuer_id"].split(":", 1)[1]
            fact, currency, units = expected_facts.pop((ticker, row["metric"]))
            if row["currency"] != currency or row["unit_scale"] != units or row["period_end"].isoformat() != fact["period_end"] or row["period_type"] != fact["period_type"] or abs(float(row["value"]) - float(fact["value"])) > 1e-9:
                raise AssertionError(f"{ticker}: original fact value, period, currency or units drift")
        if expected_facts:
            raise AssertionError("missing original-period facts")
        assumptions = query(f"SELECT COUNT(*) count FROM pse_assumptions WHERE version LIKE %s AND scope IN ({placeholders})", ["%B18%", *FROZEN_BATCH_TICKERS])[0]["count"]
        runs = query("SELECT security_id, input_hash FROM pse_valuation_runs WHERE model_version=%s", [MODEL_VERSION])
        current_runs = [row for row in runs if row["input_hash"] == expected_runs.get(row["security_id"])]
        securities = query(f"SELECT ticker, listing_status FROM pse_securities WHERE ticker IN ({placeholders})", list(FROZEN_BATCH_TICKERS))
        if len(securities) != 10 or any(row["listing_status"] != "listed" for row in securities):
            raise AssertionError("Batch 18 ordinary-common listing status drift")
        for document in current:
            s3.head_object(Bucket=BUCKET, Key=document["object_key"])
        if (int(assumptions), len(current_runs)) != (30, 10):
            raise AssertionError((assumptions, len(current_runs)))
        print({"current_documents": 10, "original_period_facts": 16, "multiple_assumptions": 30, "current_runs": 10, "current_objects": 10, "parent_common_bridges": 3})
    finally:
        pool.close()


if __name__ == "__main__":
    main()
