"""Offline contract tests for controlled Batch 01 source packets."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.us_valuation.batch_01 import BATCH_01_MANIFEST

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from capture_batch_01_sources import capture_sources


class FakeSecClient:
    def submissions(self, cik: str, *, refresh: bool = False) -> dict:
        issuer = next(item for item in BATCH_01_MANIFEST if item.cik == cik)
        return {
            "cik": cik,
            "name": issuer.issuer_name,
            "tickers": [issuer.ticker],
            "filings": {
                "recent": {
                    "accessionNumber": ["0000000000-26-000001", "0000000000-26-000002"],
                    "filingDate": ["2026-08-14", "2026-08-15"],
                    "form": ["10-K", "8-K"],
                    "primaryDocument": ["annual.htm", "later.htm"],
                }
            },
        }

    def companyfacts(self, cik: str, *, refresh: bool = False) -> dict:
        issuer = next(item for item in BATCH_01_MANIFEST if item.cik == cik)
        return {"cik": cik, "entityName": issuer.issuer_name, "facts": {}}


def test_capture_builds_exact_immutable_packets_without_serving_writes(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "batch-01"
    serving_root = tmp_path / "serving"
    serving_root.mkdir()
    (serving_root / "sentinel.json").write_text('{"unchanged":true}', encoding="utf-8")
    before = hashlib.sha256((serving_root / "sentinel.json").read_bytes()).hexdigest()

    summary = capture_sources(
        output_root=output_root,
        client=FakeSecClient(),
        protected_serving_roots=(serving_root,),
    )

    assert summary["manifest_count"] == 10
    assert summary["source_packet_count"] == 10
    assert summary["serving_artifacts_changed"] is False
    assert {path.name for path in output_root.iterdir()} == {
        issuer.ticker for issuer in BATCH_01_MANIFEST
    }
    assert hashlib.sha256((serving_root / "sentinel.json").read_bytes()).hexdigest() == before

    packet = output_root / "AAPL"
    assert {path.name for path in packet.iterdir()} == {
        "submissions.json",
        "submissions.meta.json",
        "companyfacts.json",
        "companyfacts.meta.json",
        "source-manifest.json",
    }
    manifest = json.loads((packet / "source-manifest.json").read_text(encoding="utf-8"))
    assert manifest["issuer"] == {
        "ticker": "AAPL",
        "cik": "0000320193",
        "issuer_name": "Apple Inc.",
    }
    assert manifest["files"]["submissions.json"]["sha256"] == hashlib.sha256(
        (packet / "submissions.json").read_bytes()
    ).hexdigest()
    assert len(manifest["eligible_filings"]) == 1
    assert len(manifest["future_filings"]) == 1
    assert manifest["evidence"] == {
        "accepted": [], "rejected": [], "missing": [], "conflicting": []
    }
    assert set(manifest["packet_payload_sha256"]) == {
        "submissions.json", "submissions.meta.json", "companyfacts.json", "companyfacts.meta.json"
    }
    assert manifest["files"]["submissions.json"]["fetch_metadata"]["provenance_status"] == "unavailable_from_client"

    first_bytes = {
        path.relative_to(output_root): path.read_bytes()
        for path in output_root.rglob("*") if path.is_file()
    }
    repeated = capture_sources(
        output_root=output_root,
        client=FakeSecClient(),
        protected_serving_roots=(serving_root,),
    )
    assert repeated["source_packet_count"] == 10
    assert first_bytes == {
        path.relative_to(output_root): path.read_bytes()
        for path in output_root.rglob("*") if path.is_file()
    }


def test_capture_refuses_serving_roots_identity_mismatch_and_overwrite(
    tmp_path: Path,
) -> None:
    class BadIdentityClient(FakeSecClient):
        def submissions(self, cik: str, *, refresh: bool = False) -> dict:
            result = super().submissions(cik, refresh=refresh)
            result["tickers"] = ["WRONG"]
            return result

    with pytest.raises(ValueError, match="protected serving root"):
        capture_sources(
            output_root=tmp_path / "backend/app/data/us_valuations",
            client=FakeSecClient(),
            protected_serving_roots=(tmp_path / "backend/app/data/us_valuations",),
        )
    with pytest.raises(ValueError, match="ticker"):
        capture_sources(output_root=tmp_path / "bad", client=BadIdentityClient())

    output_root = tmp_path / "immutable"
    capture_sources(output_root=output_root, client=FakeSecClient())
    (output_root / "AAPL" / "submissions.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        capture_sources(output_root=output_root, client=FakeSecClient())


def test_capture_rejects_malformed_dates_and_uneven_filing_ledgers(tmp_path: Path) -> None:
    class UnevenClient(FakeSecClient):
        def submissions(self, cik: str, *, refresh: bool = False) -> dict:
            result = super().submissions(cik, refresh=refresh)
            result["filings"]["recent"]["form"] = ["10-K"]
            return result

    class BadDateClient(FakeSecClient):
        def submissions(self, cik: str, *, refresh: bool = False) -> dict:
            result = super().submissions(cik, refresh=refresh)
            result["filings"]["recent"]["filingDate"][0] = "not-a-date"
            return result

    with pytest.raises(ValueError, match="uneven lengths"):
        capture_sources(output_root=tmp_path / "uneven", client=UnevenClient())
    capture_sources(output_root=tmp_path / "bad-date", client=BadDateClient())
    manifest = json.loads((tmp_path / "bad-date" / "AAPL" / "source-manifest.json").read_text())
    assert manifest["ineligible_filings"][0]["reason"] == "invalid_filing_date"


def test_direct_help_works_without_pythonpath_or_arelle_import() -> None:
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/capture_batch_01_sources.py", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--output-root" in result.stdout
    source = (project_root / "scripts/capture_batch_01_sources.py").read_text()
    assert "arelle" not in source.casefold()
