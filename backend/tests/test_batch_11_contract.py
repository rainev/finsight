import hashlib
import json
from pathlib import Path

from app.us_valuation.batch_11 import (
    BATCH_11_MANIFEST,
    BATCH_11_TICKERS,
    BATCH_11_VALUATION_DATE,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "backend/app/us_valuation/config/reset_batches_2026_08_14/batch_11.json"
RECEIPT = ROOT / "backend/app/us_valuation/config/reset_batches_2026_08_14/partition_receipt.json"


def test_batch_11_contract_is_exact_and_frozen():
    assert BATCH_11_VALUATION_DATE == "2026-08-14"
    assert BATCH_11_TICKERS == (
        "SYY",
        "CHD",
        "MO",
        "MNST",
        "COST",
        "DLTR",
        "MDLZ",
        "PM",
        "KHC",
        "BG",
    )
    assert len(BATCH_11_MANIFEST) == 10
    assert len({row.cik for row in BATCH_11_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_11_MANIFEST) == 8
    assert [
        (row.ticker, row.role) for row in BATCH_11_MANIFEST if row.role == "boundary"
    ] == [("SYY", "boundary"), ("BG", "boundary")]
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_11_MANIFEST)


def test_batch_11_manifest_matches_frozen_partition_receipt():
    expected = json.loads(RECEIPT.read_text())["batch_sha256"]["batch_11.json"]
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == expected
