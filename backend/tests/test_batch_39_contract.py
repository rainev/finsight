from importlib.resources import files
import hashlib

from app.us_valuation.batch_39 import BATCH_39_MANIFEST, BATCH_39_TICKERS, BATCH_39_VALUATION_DATE


def test_batch_39_manifest_is_exact_and_frozen():
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_39.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "5b6639290bf9ed81293e1eb31952c508947e39a2e77e2280493c74ed670d00c8"
    assert BATCH_39_VALUATION_DATE == "2026-08-14"
    assert BATCH_39_TICKERS == ("ARES", "RF", "CBOE", "IBKR", "TRGP", "BNY", "BX", "V", "KKR", "KMI")
    assert len(BATCH_39_MANIFEST) == 10
    assert sum(row.role == "core" for row in BATCH_39_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_39_MANIFEST) == 2
    assert {row.ticker for row in BATCH_39_MANIFEST if row.partition_family_id == "resource_cycle_fcff"} == {"TRGP", "KMI"}
    assert len({row.cik for row in BATCH_39_MANIFEST}) == 10
