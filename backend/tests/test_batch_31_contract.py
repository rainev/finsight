import hashlib
from importlib.resources import files

from app.us_valuation.batch_31 import BATCH_31_MANIFEST, BATCH_31_TICKERS, BATCH_31_VALUATION_DATE


def test_batch_31_contract() -> None:
    assert BATCH_31_VALUATION_DATE == "2026-08-14"
    assert BATCH_31_TICKERS == ("PANW", "WDAY", "ORCL", "NOW", "SMCI", "CDW", "NXPI", "VRSK", "ACN", "CRWD")
    assert len(BATCH_31_MANIFEST) == 10 and len({row.cik for row in BATCH_31_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_31_MANIFEST) == 8
    assert [(row.ticker, row.role, row.boundary_reason) for row in BATCH_31_MANIFEST if row.role == "boundary"] == [("CDW", "boundary", "same_cohort_rare_subindustry_boundary"), ("VRSK", "boundary", "data_and_analytics_platform_boundary")]
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_31_MANIFEST)


def test_batch_31_manifest_hash() -> None:
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_31.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "3e3db7e7a94a61d654df22e9a29778da7a18a205e8c0e821e83c6928db300894"
