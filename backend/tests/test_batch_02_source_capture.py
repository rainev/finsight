"""Offline contracts for frozen Batch 02 SEC source packets."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

from app.us_valuation.batch_02 import BATCH_02_MANIFEST, BATCH_02_TICKERS, BATCH_02_VALUATION_DATE

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from capture_batch_02_sources import capture_sources


class FakeSecClient:
    def submissions(self, cik: str, *, refresh: bool = False) -> dict:
        issuer = next(item for item in BATCH_02_MANIFEST if item.cik == cik)
        return {"cik": cik, "name": issuer.issuer_name, "tickers": [issuer.ticker], "filings": {"recent": {"accessionNumber": ["0000000000-26-000001", "0000000000-26-000002"], "filingDate": ["2026-08-14", "2026-08-15"], "form": ["10-K", "8-K"], "primaryDocument": ["annual.htm", "later.htm"]}}}
    def companyfacts(self, cik: str, *, refresh: bool = False) -> dict:
        issuer = next(item for item in BATCH_02_MANIFEST if item.cik == cik)
        return {"cik": cik, "entityName": issuer.issuer_name, "facts": {}}


def test_loader_and_capture_are_exact_immutable_and_serving_safe(tmp_path: Path) -> None:
    assert BATCH_02_VALUATION_DATE == "2026-08-14"
    assert BATCH_02_TICKERS == ("OMC", "VZ", "T", "TTWO", "NFLX", "CHTR", "CMCSA", "TMUS", "META", "WBD")
    output, serving = tmp_path / "batch-02", tmp_path / "serving"
    serving.mkdir(); (serving / "sentinel").write_text("same")
    before = hashlib.sha256((serving / "sentinel").read_bytes()).hexdigest()
    summary = capture_sources(output_root=output, client=FakeSecClient(), protected_serving_roots=(serving,))
    assert summary["manifest_count"] == summary["source_packet_count"] == 10
    assert summary["serving_artifacts_changed"] is False
    assert {path.name for path in output.iterdir()} == set(BATCH_02_TICKERS)
    assert hashlib.sha256((serving / "sentinel").read_bytes()).hexdigest() == before
    packet = output / "OMC"; manifest = json.loads((packet / "source-manifest.json").read_text())
    assert manifest["schema_version"] == "FINSIGHT-BATCH-02-SOURCE-1"
    assert manifest["issuer"] == {"ticker": "OMC", "cik": "0000029989", "issuer_name": "Omnicom Group"}
    assert len(manifest["eligible_filings"]) == len(manifest["future_filings"]) == 1
    assert manifest["files"]["submissions.json"]["sha256"] == hashlib.sha256((packet / "submissions.json").read_bytes()).hexdigest()
    first = {path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()}
    capture_sources(output_root=output, client=FakeSecClient(), protected_serving_roots=(serving,))
    assert first == {path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()}


def test_capture_rejects_serving_root_identity_mismatch_and_overwrite(tmp_path: Path) -> None:
    class BadIdentity(FakeSecClient):
        def submissions(self, cik: str, *, refresh: bool = False) -> dict:
            result = super().submissions(cik, refresh=refresh); result["tickers"] = ["WRONG"]; return result
    with pytest.raises(ValueError, match="protected serving root"):
        capture_sources(output_root=tmp_path / "serving", client=FakeSecClient(), protected_serving_roots=(tmp_path / "serving",))
    with pytest.raises(ValueError, match="ticker"):
        capture_sources(output_root=tmp_path / "bad", client=BadIdentity())
    output = tmp_path / "immutable"; capture_sources(output_root=output, client=FakeSecClient())
    (output / "OMC" / "submissions.json").write_text("{}")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        capture_sources(output_root=output, client=FakeSecClient())
