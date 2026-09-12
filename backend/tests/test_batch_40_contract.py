from importlib.resources import files
import hashlib
from app.us_valuation.batch_40 import BATCH_40_MANIFEST, BATCH_40_TICKERS, BATCH_40_VALUATION_DATE

def test_batch_40_manifest_is_exact_and_frozen():
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_40.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "42bc92fe7a7d56884fe8e1adb07879fe6aa0f21088280d321c8bc1da08903c91"
    assert BATCH_40_VALUATION_DATE == "2026-08-14"
    assert BATCH_40_TICKERS == ("MSCI", "XYZ", "ICE", "SYF", "PYPL", "COIN", "HOOD", "TPL", "APO", "BLK")
    assert len(BATCH_40_MANIFEST) == 10
    assert sum(row.role == "core" for row in BATCH_40_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_40_MANIFEST) == 2
    assert {row.ticker for row in BATCH_40_MANIFEST if row.partition_family_id == "resource_cycle_fcff"} == {"TPL"}
