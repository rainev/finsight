from app.us_valuation.batch_38 import BATCH_38_MANIFEST, BATCH_38_TICKERS, BATCH_38_VALUATION_DATE


def test_batch_38_contract_is_exact_and_frozen():
    assert BATCH_38_VALUATION_DATE == "2026-08-14"
    assert tuple(row.ticker for row in BATCH_38_MANIFEST) == BATCH_38_TICKERS
    assert len(BATCH_38_MANIFEST) == 10
    assert len({row.cik for row in BATCH_38_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_38_MANIFEST) == 8
    assert {row.ticker for row in BATCH_38_MANIFEST if row.role == "boundary"} == {"EG", "AIZ"}
