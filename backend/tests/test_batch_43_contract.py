from importlib.resources import files
import hashlib

from app.us_valuation.batch_43 import BATCH_43_MANIFEST, BATCH_43_TICKERS, BATCH_43_VALUATION_DATE


def test_batch_43_manifest_is_exact_and_frozen():
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_43.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "b48b4146ce632b5efd7a9363cb5ada91ff50e183cc02332eaacd74b938eba18b"
    assert BATCH_43_VALUATION_DATE == "2026-08-14"
    assert BATCH_43_TICKERS == ("MLM", "STLD", "DVN", "COP", "NEM", "MOS", "CF", "VMC", "LYB", "LIN")
    assert len(BATCH_43_MANIFEST) == 10
    assert sum(row.role == "core" for row in BATCH_43_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_43_MANIFEST) == 2
    assert {row.ticker for row in BATCH_43_MANIFEST if row.role == "boundary"} == {"NEM", "LIN"}
    assert {row.partition_family_id for row in BATCH_43_MANIFEST} == {"resource_cycle_fcff"}
    assert len({row.cik for row in BATCH_43_MANIFEST}) == 10
