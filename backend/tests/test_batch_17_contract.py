import hashlib
from importlib.resources import files

from app.us_valuation.batch_17 import BATCH_17_MANIFEST, BATCH_17_TICKERS, BATCH_17_VALUATION_DATE


def test_batch_17_contract_is_exact_and_frozen() -> None:
    assert BATCH_17_VALUATION_DATE == "2026-08-14"
    assert BATCH_17_TICKERS == ("ABBV", "ZTS", "MDT", "MRNA", "CI", "STE", "VTRS", "GEHC", "KVUE", "SOLV")
    assert len(BATCH_17_MANIFEST) == 10 and len({row.cik for row in BATCH_17_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_17_MANIFEST) == 8
    assert [(row.ticker, row.role) for row in BATCH_17_MANIFEST if row.role == "boundary"] == [("KVUE", "boundary"), ("SOLV", "boundary")]
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_17_MANIFEST)


def test_batch_17_manifest_hash_matches_partition_receipt() -> None:
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_17.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "ae4220d7346e650cce3a513166e5c2cde4a2f549e13a50194ef3f0c8e04fe444"
