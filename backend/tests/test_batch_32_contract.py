import hashlib
from importlib.resources import files

from app.us_valuation.batch_32 import BATCH_32_MANIFEST, BATCH_32_TICKERS, BATCH_32_VALUATION_DATE


def test_batch_32_contract() -> None:
    assert BATCH_32_VALUATION_DATE == "2026-08-14"
    assert BATCH_32_TICKERS == ("DDOG", "KEYS", "GDDY", "LITE", "HPE", "VRT", "AVGO", "MRVL", "SNDK", "Q")
    assert len(BATCH_32_MANIFEST) == 10 and len({row.cik for row in BATCH_32_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_32_MANIFEST) == 8
    assert [(row.ticker, row.boundary_reason) for row in BATCH_32_MANIFEST if row.role == "boundary"] == [("GDDY", "same_cohort_rare_subindustry_boundary"), ("VRT", "data_center_infrastructure_boundary")]
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_32_MANIFEST)


def test_batch_32_manifest_hash() -> None:
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_32.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "ec9a82dcf24fc1638fc4c88fd015425ce431cbd4e1c9fd49524e2185072aa80e"
