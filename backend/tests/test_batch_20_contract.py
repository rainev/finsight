import hashlib
from importlib.resources import files

from app.us_valuation.batch_20 import BATCH_20_MANIFEST, BATCH_20_TICKERS, BATCH_20_VALUATION_DATE


def test_batch_20_contract_is_exact_and_frozen() -> None:
    assert BATCH_20_VALUATION_DATE == "2026-08-14"
    assert BATCH_20_TICKERS == ("PNR", "ROL", "AOS", "SNA", "LUV", "SWK", "UAL", "UNP", "CTAS", "PAYX")
    assert len(BATCH_20_MANIFEST) == 10 and len({row.cik for row in BATCH_20_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_20_MANIFEST) == 8
    assert [(row.ticker, row.role) for row in BATCH_20_MANIFEST if row.role == "boundary"] == [("CTAS", "boundary"), ("PAYX", "boundary")]
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_20_MANIFEST)


def test_batch_20_manifest_hash_matches_partition_receipt() -> None:
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_20.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "a6da41ca5e593099973619dae32ac1eca1321c322161a9ea64274b5f35986301"
