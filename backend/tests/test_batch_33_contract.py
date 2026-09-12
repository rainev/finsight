import hashlib
from importlib.resources import files

from app.us_valuation.batch_33 import BATCH_33_MANIFEST, BATCH_33_TICKERS, BATCH_33_VALUATION_DATE


def test_batch_33_contract() -> None:
    assert BATCH_33_VALUATION_DATE == "2026-08-14"
    assert BATCH_33_TICKERS == ("AXP", "AFL", "AIG", "WRB", "CINF", "FITB", "MTB", "BEN", "HBAN", "MRSH")
    assert len(BATCH_33_MANIFEST) == 10 and len({row.cik for row in BATCH_33_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_33_MANIFEST) == 8
    assert [(row.ticker, row.boundary_reason) for row in BATCH_33_MANIFEST if row.role == "boundary"] == [("AXP", "same_cohort_rare_subindustry_boundary"), ("AIG", "same_cohort_rare_subindustry_boundary")]
    assert all(row.partition_family_id == "financial_equity" for row in BATCH_33_MANIFEST)


def test_batch_33_manifest_hash() -> None:
    path = files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_33.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "cb67922607c31bc19c21b31f0b59c5351680a455d4cac95c50de287eb02ffcfd"
