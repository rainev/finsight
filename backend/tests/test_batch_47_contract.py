from app.us_valuation.batch_47 import BATCH_47_MANIFEST, BATCH_47_TICKERS, BATCH_47_VALUATION_DATE


def test_batch_47_frozen_contract() -> None:
    assert BATCH_47_VALUATION_DATE == "2026-08-14"
    assert BATCH_47_TICKERS == ("NRG", "ED", "EXC", "NI", "CNP", "DUK", "AWK", "VST", "EVRG", "CEG")
    assert tuple(row.ticker for row in BATCH_47_MANIFEST) == BATCH_47_TICKERS
    assert len({row.cik for row in BATCH_47_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_47_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_47_MANIFEST) == 2
    assert {row.partition_family_id for row in BATCH_47_MANIFEST} == {"utility_fcfe"}
