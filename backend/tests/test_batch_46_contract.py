from app.us_valuation.batch_46 import BATCH_46_MANIFEST, BATCH_46_TICKERS, BATCH_46_VALUATION_DATE


def test_batch_46_frozen_contract() -> None:
    assert BATCH_46_VALUATION_DATE == "2026-08-14"
    assert BATCH_46_TICKERS == ("ATO", "CMS", "EIX", "AES", "PPL", "DTE", "AEE", "PCG", "FE", "SRE")
    assert tuple(row.ticker for row in BATCH_46_MANIFEST) == BATCH_46_TICKERS
    assert len({row.cik for row in BATCH_46_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_46_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_46_MANIFEST) == 2
    assert {row.partition_family_id for row in BATCH_46_MANIFEST} == {"utility_fcfe"}
