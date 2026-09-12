from importlib.resources import files
import hashlib

from app.us_valuation.batch_41 import BATCH_41_MANIFEST, BATCH_41_TICKERS, BATCH_41_VALUATION_DATE


def test_batch_41_manifest_is_exact_and_frozen():
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_41.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "8029d2b9a03ba54d119876aa61ad48b15df8f4c954947337fe1993cb79f393af"
    assert BATCH_41_VALUATION_DATE == "2026-08-14"
    assert BATCH_41_TICKERS == ("APD", "AVY", "BALL", "ECL", "EQT", "HAL", "IFF", "IP", "NUE", "PKG")
    assert len(BATCH_41_MANIFEST) == 10
    assert sum(row.role == "core" for row in BATCH_41_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_41_MANIFEST) == 2
    assert {row.ticker for row in BATCH_41_MANIFEST if row.role == "boundary"} == {"APD", "BALL"}
    assert {row.partition_family_id for row in BATCH_41_MANIFEST} == {"resource_cycle_fcff"}
    assert len({row.cik for row in BATCH_41_MANIFEST}) == 10
