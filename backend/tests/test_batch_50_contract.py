from app.us_valuation.batch_50 import BATCH_50_MANIFEST, BATCH_50_TICKERS, BATCH_50_VALUATION_DATE


def test_batch_50_frozen_contract() -> None:
    assert BATCH_50_VALUATION_DATE == "2026-08-14"
    assert BATCH_50_TICKERS == ("AMT", "CSGP", "SPG", "HST", "CBRE", "EXR", "DLR", "PSA", "INVH", "VICI")
    assert tuple(row.ticker for row in BATCH_50_MANIFEST) == BATCH_50_TICKERS
    assert len({row.cik for row in BATCH_50_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_50_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_50_MANIFEST) == 2
    assert {row.partition_family_id for row in BATCH_50_MANIFEST} == {"reit_affo"}
