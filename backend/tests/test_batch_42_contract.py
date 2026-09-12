from importlib.resources import files
import hashlib

from app.us_valuation.batch_42 import BATCH_42_MANIFEST, BATCH_42_TICKERS, BATCH_42_VALUATION_DATE


def test_batch_42_manifest_is_exact_and_frozen():
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_42.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "dc1ed9b01a99616ab8be40a098c3be2531c1137c0b4f068d70b0f592b3e87378"
    assert BATCH_42_VALUATION_DATE == "2026-08-14"
    assert BATCH_42_TICKERS == ("PPG", "SLB", "SHW", "CVX", "OXY", "EOG", "FCX", "CRH", "EXE", "ALB")
    assert len(BATCH_42_MANIFEST) == 10
    assert sum(row.role == "core" for row in BATCH_42_MANIFEST) == 8
    assert sum(row.role == "boundary" for row in BATCH_42_MANIFEST) == 2
    assert {row.ticker for row in BATCH_42_MANIFEST if row.role == "boundary"} == {"CVX", "FCX"}
    assert {row.partition_family_id for row in BATCH_42_MANIFEST} == {"resource_cycle_fcff"}
    assert len({row.cik for row in BATCH_42_MANIFEST}) == 10
