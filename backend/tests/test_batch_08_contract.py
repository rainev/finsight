from app.us_valuation.batch_08 import BATCH_08_MANIFEST, BATCH_08_TICKERS, BATCH_08_VALUATION_DATE


def test_batch_08_contract_is_exact_and_frozen() -> None:
    assert BATCH_08_VALUATION_DATE == "2026-08-14"
    assert BATCH_08_TICKERS == ("LULU", "ULTA", "KDP", "GM", "NCLH", "APTV", "ABNB", "HLT", "CVNA", "DASH")
    assert len(BATCH_08_MANIFEST) == 10
    assert len({row.cik for row in BATCH_08_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_08_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_08_MANIFEST) == 2
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_08_MANIFEST)
    assert [(row.ticker, row.role) for row in BATCH_08_MANIFEST if row.role == "boundary"] == [("KDP", "boundary"), ("APTV", "boundary")]
