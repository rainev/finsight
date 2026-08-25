"""Frozen Batch 03 denominator and role contract."""

import pytest

from app.us_valuation.batch_03 import (
    BATCH_03_MANIFEST,
    BATCH_03_TICKERS,
    BATCH_03_VALUATION_DATE,
    batch_03_issuer,
)


def test_batch_03_exact_denominator_and_partition_contract() -> None:
    assert BATCH_03_VALUATION_DATE == "2026-08-14"
    assert tuple(row.ticker for row in BATCH_03_MANIFEST) == BATCH_03_TICKERS
    assert len(BATCH_03_MANIFEST) == 10
    assert len({row.cik for row in BATCH_03_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_03_MANIFEST) == 8
    assert tuple(row.ticker for row in BATCH_03_MANIFEST if row.role == "boundary") == (
        "NWSA", "FOXA"
    )
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_03_MANIFEST)


def test_batch_03_lookup_is_exact_and_contract_is_frozen() -> None:
    assert batch_03_issuer("googl").cik == "0001652044"
    with pytest.raises(KeyError):
        batch_03_issuer("GOOG")
    with pytest.raises(Exception):
        BATCH_03_MANIFEST[0].ticker = "OTHER"

