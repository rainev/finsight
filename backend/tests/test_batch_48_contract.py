from app.us_valuation.batch_48 import BATCH_48_MANIFEST, BATCH_48_TICKERS, BATCH_48_VALUATION_DATE


def test_batch_48_frozen_contract() -> None:
    assert BATCH_48_VALUATION_DATE == "2026-08-14"
    assert BATCH_48_TICKERS == ("FRT", "UDR", "WY", "VTR", "DOC", "WELL", "KIM", "EQR", "CPT", "IRM")
    assert tuple(row.ticker for row in BATCH_48_MANIFEST) == BATCH_48_TICKERS
    assert len({row.cik for row in BATCH_48_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_48_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_48_MANIFEST) == 2
    assert {row.partition_family_id for row in BATCH_48_MANIFEST} == {"reit_affo"}
