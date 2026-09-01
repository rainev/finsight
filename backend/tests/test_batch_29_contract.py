import hashlib
from importlib.resources import files

from app.us_valuation.batch_29 import (
    BATCH_29_MANIFEST,
    BATCH_29_TICKERS,
    BATCH_29_VALUATION_DATE,
)


def test_batch_29_contract() -> None:
    assert BATCH_29_VALUATION_DATE == "2026-08-14"
    assert BATCH_29_TICKERS == (
        "TRMB",
        "ROP",
        "SNPS",
        "INTU",
        "CIEN",
        "NTAP",
        "VRSN",
        "NVDA",
        "FFIV",
        "AKAM",
    )
    assert len(BATCH_29_MANIFEST) == 10
    assert len({row.cik for row in BATCH_29_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_29_MANIFEST) == 8
    assert [
        (row.ticker, row.role) for row in BATCH_29_MANIFEST if row.role == "boundary"
    ] == [("VRSN", "boundary"), ("AKAM", "boundary")]
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_29_MANIFEST)


def test_batch_29_manifest_hash() -> None:
    path = files("app.us_valuation").joinpath(
        "config/reset_batches_2026_08_14/batch_29.json"
    )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "5177bc1a997f7c7c06fecf173597734c725c8c52c1e90a896d34672baeafb306"
    )
