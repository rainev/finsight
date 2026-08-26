from app.us_valuation.batch_06 import (
    BATCH_06_MANIFEST,
    BATCH_06_TICKERS,
    BATCH_06_VALUATION_DATE,
)


def test_batch_06_contract_is_exact_and_frozen() -> None:
    assert BATCH_06_VALUATION_DATE == "2026-08-14"
    assert BATCH_06_TICKERS == (
        "BBY", "DECK", "TSCO", "LEN", "DRI", "AMZN", "RL", "YUM", "MAR", "CMG",
    )
    assert tuple(row.ticker for row in BATCH_06_MANIFEST) == BATCH_06_TICKERS
    assert len(BATCH_06_MANIFEST) == 10
    assert len({row.cik for row in BATCH_06_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_06_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_06_MANIFEST) == 2
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_06_MANIFEST)


def test_batch_06_boundary_reasons_are_explicit() -> None:
    boundary = [row for row in BATCH_06_MANIFEST if row.role == "boundary"]
    assert [row.ticker for row in boundary] == ["BBY", "DECK"]
    assert all(row.boundary_reason for row in boundary)
    assert all(row.boundary_reason is None for row in BATCH_06_MANIFEST if row.role == "core")
