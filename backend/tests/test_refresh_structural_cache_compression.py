from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_source_ingestion import SourceCaptureError, capture_company_source


ROOT = Path(__file__).resolve().parents[2]
DDOG_PACKET = ROOT / "output/batch-32-sec-source-packets-20260903/DDOG"
DDOG_STRUCTURAL = ROOT / "output/batch-32-structural-replay-a-20260903/DDOG/structural-filing.json"
DDOG_ACCESSION = "0001628280-26-054458"


def _capture(parsed_cache_dir: Path, *, compressed: bool) -> dict:
    return capture_company_source(
        ticker="DDOG",
        cik="0001561550",
        cutoff="2026-08-14",
        offline_packet_dir=DDOG_PACKET,
        structural_paths={DDOG_ACCESSION: DDOG_STRUCTURAL},
        require_structural=False,
        parsed_cache_dir=parsed_cache_dir,
        compress_parsed_cache=compressed,
    )


def test_compressed_structural_cache_is_deterministic_and_identity_preserving(tmp_path: Path) -> None:
    first = _capture(tmp_path / "parsed", compressed=True)
    cache_files = list((tmp_path / "parsed").rglob("*.json.gz"))
    assert len(cache_files) == 1
    cache_bytes = cache_files[0].read_bytes()
    with gzip.open(cache_files[0], "rt", encoding="utf-8") as handle:
        envelope = json.load(handle)
    assert envelope["source_package_sha256"] == first["structural_receipts"][0]["source_package_sha256"]
    assert envelope["parsed_sha256"]
    assert cache_bytes[4:8] == b"\x00\x00\x00\x00"

    second = _capture(tmp_path / "parsed", compressed=True)
    assert cache_files[0].read_bytes() == cache_bytes
    assert second["structural_sha256"] == first["structural_sha256"]
    assert second["structural_receipts"][0]["parsed_cache_reused"] is True


def test_plain_reader_reuses_compressed_structural_cache(tmp_path: Path) -> None:
    compressed = _capture(tmp_path / "parsed", compressed=True)
    replayed = _capture(tmp_path / "parsed", compressed=False)

    assert replayed["structural_sha256"] == compressed["structural_sha256"]
    assert replayed["structural_receipts"][0]["parsed_cache_reused"] is True


def test_corrupt_compressed_structural_cache_fails_closed(tmp_path: Path) -> None:
    parsed = tmp_path / "parsed"
    _capture(parsed, compressed=True)
    cache_path = next(parsed.rglob("*.json.gz"))
    cache_path.write_bytes(b"not-gzip")

    with pytest.raises(SourceCaptureError, match="parsed structural cache is invalid"):
        _capture(parsed, compressed=True)
