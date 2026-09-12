from app.us_valuation.batch_37 import BATCH_37_MANIFEST, BATCH_37_TICKERS, BATCH_37_VALUATION_DATE


def test_batch_37_contract_is_exact_and_frozen():
    assert BATCH_37_VALUATION_DATE == "2026-08-14"
    assert tuple(row.ticker for row in BATCH_37_MANIFEST) == BATCH_37_TICKERS
    assert len(BATCH_37_MANIFEST) == 10
    assert len({row.cik for row in BATCH_37_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_37_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_37_MANIFEST) == 2
    assert {row.ticker for row in BATCH_37_MANIFEST if row.role == "boundary"} == {"OKE", "BRK.B"}
