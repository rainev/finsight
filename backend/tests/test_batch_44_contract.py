from app.us_valuation.batch_44 import BATCH_44_MANIFEST, BATCH_44_TICKERS, BATCH_44_VALUATION_DATE


def test_batch_44_manifest_is_exact_and_frozen():
    assert BATCH_44_VALUATION_DATE == "2026-08-14"
    assert BATCH_44_TICKERS == ("MPC", "PSX", "FANG", "BKR", "AMCR", "DOW", "CTVA", "APA", "SW", "XOM")
    assert len(BATCH_44_MANIFEST) == 10
    assert len({row.cik for row in BATCH_44_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_44_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_44_MANIFEST) == 2
    assert {row.partition_family_id for row in BATCH_44_MANIFEST} == {"resource_cycle_fcff"}
