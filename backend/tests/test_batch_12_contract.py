import hashlib
import json
from pathlib import Path

from app.us_valuation.batch_12 import (
    BATCH_12_MANIFEST,
    BATCH_12_TICKERS,
    BATCH_12_VALUATION_DATE,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "backend/app/us_valuation/config/reset_batches_2026_08_14/batch_12.json"
RECEIPT = ROOT / "backend/app/us_valuation/config/reset_batches_2026_08_14/partition_receipt.json"


def test_batch_12_contract_is_exact_and_frozen():
    assert BATCH_12_VALUATION_DATE == "2026-08-14"
    assert BATCH_12_TICKERS == (
        "ABT", "BAX", "BDX", "BMY", "RVTY", "HUM", "LLY", "CVS", "WST", "UHS"
    )
    assert len(BATCH_12_MANIFEST) == 10
    assert len({row.cik for row in BATCH_12_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_12_MANIFEST) == 8
    assert [(row.ticker, row.role) for row in BATCH_12_MANIFEST if row.role == "boundary"] == [("WST", "boundary"), ("UHS", "boundary")]
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_12_MANIFEST)


def test_batch_12_manifest_matches_frozen_partition_receipt():
    expected = json.loads(RECEIPT.read_text())["batch_sha256"]["batch_12.json"]
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == expected
