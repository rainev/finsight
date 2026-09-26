"""Read back Batch 26 reviewed receipts, facts, run states and MinIO objects."""

from decimal import Decimal

from app.db import pool, query
from app.pse_valuation.phase_b_batch_26 import FROZEN_BATCH_TICKERS, MODEL_VERSION, build_batch_artifacts, load_batch_config, source_receipt
from app.storage import BUCKET, s3


def main() -> None:
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    expected_docs = {f"PSE:{t}": source_receipt(t, config)[0][0]["sha256"] for t in FROZEN_BATCH_TICKERS}
    expected_runs = {f"PSE:{t}:COMMON": artifacts[t].input_hash for t in FROZEN_BATCH_TICKERS}
    expected_facts = {}
    for ticker, issuer in config["issuers"].items():
        expected_facts[(ticker, f"reported_{issuer['equity_basis']}_equity")] = (issuer["equity_value"], "PHP", issuer["equity_unit_scale"], issuer["period_end"])
        expected_facts[(ticker, "reported_book_value_per_share")] = (issuer["reported_bvps"], "PHP", "per_share", issuer["period_end"])
        for row in issuer["share_classes"]:
            metric = "reported_common_shares_" + row["class"].lower().replace(" ", "_").replace("/", "_")
            expected_facts[(ticker, metric)] = (row["shares"], "N/A", "shares", row["as_of"])
    placeholders = ", ".join(["%s"] * len(FROZEN_BATCH_TICKERS))
    pool.open()
    try:
        documents = query(f"SELECT id, issuer_id, sha256, object_key FROM pse_documents WHERE issuer_id IN ({placeholders})", list(expected_docs))
        current = [row for row in documents if row["sha256"] == expected_docs[row["issuer_id"]]]
        if len(current) != 10:
            raise AssertionError("expected ten current reviewed receipts")
        facts = query(f"SELECT d.issuer_id, f.metric, f.value, f.currency, f.unit_scale, f.period_end FROM pse_reported_facts f JOIN pse_documents d ON d.id=f.document_id WHERE f.document_id IN ({placeholders})", [row["id"] for row in current])
        if len(facts) != len(expected_facts):
            raise AssertionError(("fact count", len(facts), len(expected_facts)))
        for row in facts:
            ticker = row["issuer_id"].split(":", 1)[1]
            value, currency, units, period = expected_facts.pop((ticker, row["metric"]))
            if (row["currency"], row["unit_scale"], row["period_end"].isoformat()) != (currency, units, period) or Decimal(str(row["value"])) != Decimal(str(value)):
                raise AssertionError(f"{ticker}: value, period, currency or unit drift")
        if expected_facts:
            raise AssertionError(("missing facts", sorted(expected_facts)))
        bridges = query(f"SELECT scope, value FROM pse_assumptions WHERE version=%s AND metric=%s AND scope IN ({placeholders})", ["PSE-V2-COMMON-DENOMINATOR-B26-1.0", "reviewed_ordinary_common_denominator", *FROZEN_BATCH_TICKERS])
        expected_bridge = {ticker for ticker, issuer in config["issuers"].items() if issuer["share_bridge_type"] == "single_class"}
        if {row["scope"] for row in bridges} != expected_bridge:
            raise AssertionError("reviewed common denominators drift")
        for row in bridges:
            if int(row["value"]) != config["issuers"][row["scope"]]["shares_outstanding"]:
                raise AssertionError(f"{row['scope']}: common-share denominator drift")
        multiples = query(f"SELECT COUNT(*) count FROM pse_assumptions WHERE version=%s AND metric=%s AND scope IN ({placeholders})", ["PSE-V2-PB-HISTORICAL-B26-1.0", "price_to_book", *FROZEN_BATCH_TICKERS])[0]["count"]
        runs = query("SELECT security_id, input_hash, availability_type, publication_state FROM pse_valuation_runs WHERE model_version=%s", [MODEL_VERSION])
        current_runs = [row for row in runs if row["input_hash"] == expected_runs.get(row["security_id"])]
        if len(current_runs) != 10 or int(multiples) != 3:
            raise AssertionError(("runs/multiples", len(current_runs), multiples))
        for row in current_runs:
            ticker = row["security_id"].split(":")[1]
            expected = ("market_relative_only", "provisional") if ticker == "MM" else ("not_available", "blocked")
            if (row["availability_type"], row["publication_state"]) != expected:
                raise AssertionError(f"{ticker}: run status drift")
        securities = query(f"SELECT ticker, listing_status FROM pse_securities WHERE ticker IN ({placeholders})", list(FROZEN_BATCH_TICKERS))
        if len(securities) != 10 or any(row["listing_status"] != "suspended" for row in securities):
            raise AssertionError("suspended common-security status drift")
        for document in current:
            s3.head_object(Bucket=BUCKET, Key=document["object_key"])
        print({"current_documents": 10, "reported_facts": len(facts), "reviewed_denominators": len(bridges), "multiple_assumptions": 3, "current_runs": 10, "objects": 10})
    finally:
        pool.close()


if __name__ == "__main__":
    main()
