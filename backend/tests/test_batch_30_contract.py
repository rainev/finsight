import hashlib
from importlib.resources import files

from app.us_valuation.batch_30 import BATCH_30_MANIFEST, BATCH_30_TICKERS, BATCH_30_VALUATION_DATE


def test_batch_30_contract() -> None:
    assert BATCH_30_VALUATION_DATE == "2026-08-14"
    assert BATCH_30_TICKERS == ("CTSH", "TDY", "ON", "STX", "FTNT", "FSLR", "MPWR", "PLTR", "BR", "TEL")
    assert len(BATCH_30_MANIFEST) == 10 and len({row.cik for row in BATCH_30_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_30_MANIFEST) == 8
    assert [(row.ticker, row.role) for row in BATCH_30_MANIFEST if row.role == "boundary"] == [("BR", "boundary"), ("TEL", "boundary")]
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_30_MANIFEST)


def test_batch_30_manifest_hash() -> None:
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_30.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "a84c4b3eb4dc978e0ce5fc1de3d4cc67623e99d38b2367a482b712e8f84ca63f"
