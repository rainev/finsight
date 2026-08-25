from app.us_valuation.batch_04 import BATCH_04_MANIFEST, BATCH_04_TICKERS, BATCH_04_VALUATION_DATE


def test_batch_04_exact_frozen_contract() -> None:
    assert BATCH_04_VALUATION_DATE == "2026-08-14"
    assert tuple(row.ticker for row in BATCH_04_MANIFEST) == BATCH_04_TICKERS
    assert len(BATCH_04_MANIFEST) == 10
    assert len({row.cik for row in BATCH_04_MANIFEST}) == 10
    assert tuple(row.ticker for row in BATCH_04_MANIFEST if row.role == "boundary") == ("GPC", "HAS")
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_04_MANIFEST)
