import hashlib
from importlib.resources import files

from app.us_valuation.batch_19 import (
    BATCH_19_MANIFEST,
    BATCH_19_TICKERS,
    BATCH_19_VALUATION_DATE,
)


def test_batch_19_contract_is_exact_and_frozen() -> None:
    assert BATCH_19_VALUATION_DATE == "2026-08-14"
    assert BATCH_19_TICKERS == ("GE", "HUBB", "ITW", "J", "MAS", "MMM", "NDSN", "PCAR", "PH", "DE")
    assert len(BATCH_19_MANIFEST) == 10
    assert len({row.cik for row in BATCH_19_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_19_MANIFEST) == 8
    assert [(row.ticker, row.role) for row in BATCH_19_MANIFEST if row.role == "boundary"] == [
        ("MMM", "boundary"),
        ("DE", "boundary"),
    ]
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_19_MANIFEST)


def test_batch_19_manifest_hash_matches_partition_receipt() -> None:
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_19.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "0350deebae8c9fef54ba37afd4e51e7221708eceb3ed40115b1398f815c6c1f6"
