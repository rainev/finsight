from app.us_valuation.batch_49 import BATCH_49_MANIFEST, BATCH_49_TICKERS, BATCH_49_VALUATION_DATE


def test_batch_49_frozen_contract() -> None:
    assert BATCH_49_VALUATION_DATE == "2026-08-14"
    assert BATCH_49_TICKERS == ("REG", "MAA", "AVB", "ESS", "SBAC", "ARE", "BXP", "PLD", "CCI", "EQIX")
    assert tuple(row.ticker for row in BATCH_49_MANIFEST) == BATCH_49_TICKERS
    assert len({row.cik for row in BATCH_49_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_49_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_49_MANIFEST) == 2
    assert {row.partition_family_id for row in BATCH_49_MANIFEST} == {"reit_affo"}
