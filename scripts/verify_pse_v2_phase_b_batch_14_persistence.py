"""Verify the exact current Batch 14 receipts, facts, policies, runs and objects."""

from app.db import pool, query
from app.pse_valuation.phase_b_batch_14 import FROZEN_BATCH_TICKERS, MODEL_VERSION, build_batch_artifacts, load_batch_config, source_receipt
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
            raise AssertionError("missing current source receipts")
        facts = query(f"SELECT d.issuer_id, f.metric, f.value, f.currency, f.unit_scale, f.period_end, f.period_type FROM pse_reported_facts f JOIN pse_documents d ON d.id=f.document_id WHERE f.document_id IN ({placeholders})", [row["id"] for row in current])
        expected_facts = {}
        for ticker in FROZEN_BATCH_TICKERS:
            issuer = config["issuers"][ticker]
            values = {"reported_book_value_per_share": issuer["reported_bvps"]} if ticker == "MEDIC" else {f"reported_basic_eps_{role}": fact for role, fact in issuer["reported_eps"].items()}
            for metric, fact in values.items():
                expected_facts[(f"PSE:{ticker}", metric)] = fact
        if len(facts) != 26 or len(expected_facts) != 26:
            raise AssertionError("expected exactly 26 original-period facts")
        for row in facts:
            expected = expected_facts.pop((row["issuer_id"], row["metric"]))
            if row["currency"] != "PHP" or row["unit_scale"] != "per_share" or row["period_end"].isoformat() != expected["period_end"] or row["period_type"] != expected["period_type"] or abs(float(row["value"]) - float(expected["value"])) > 1e-9:
                raise AssertionError("reported fact does not match source period, unit or value")
        if expected_facts:
            raise AssertionError("missing original-period facts")
        assumptions = query(f"SELECT COUNT(*) count FROM pse_assumptions WHERE version LIKE %s AND scope IN ({placeholders})", ["%B14%", *FROZEN_BATCH_TICKERS])[0]["count"]
        runs = query("SELECT security_id, input_hash FROM pse_valuation_runs WHERE model_version=%s", [MODEL_VERSION])
        current_runs = [row for row in runs if row["input_hash"] == expected_runs.get(row["security_id"])]
        for document in current:
            s3.head_object(Bucket=BUCKET, Key=document["object_key"])
        if (int(assumptions), len(current_runs)) != (30, 10):
            raise AssertionError((assumptions, len(current_runs)))
        print({"current_documents": 10, "original_period_facts": 26, "assumptions": 30, "current_runs": 10, "current_objects": 10, "non_december_periods_preserved": True})
    finally:
        pool.close()


if __name__ == "__main__":
    main()
