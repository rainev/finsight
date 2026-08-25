"""Contracts for the minimal Batch 01 recovery source capture."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/capture_batch_01_recovery_sources.py"
SPEC = importlib.util.spec_from_file_location("capture_batch_01_recovery_sources", SCRIPT)
assert SPEC and SPEC.loader
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)


class FakeClient:
    def submissions(self, cik: str, *, refresh: bool = False) -> dict:
        if cik == "0001137789":
            return {"cik": 1137789, "tickers": ["STX"], "filings": {"recent": {}}}
        targets = [row for row in capture.TARGET_FILINGS if row["cik"] == cik]
        return {
            "cik": int(cik),
            "tickers": [targets[0]["ticker"]],
            "filings": {
                "recent": {
                    "accessionNumber": [row["accession"] for row in targets],
                    "form": [row["form"] for row in targets],
                    "filingDate": [row["filed"] for row in targets],
                    "reportDate": [row["period_end"] for row in targets],
                    "primaryDocument": [row["primary_document"] for row in targets],
                }
            },
        }

    def companyfacts(self, cik: str, *, refresh: bool = False) -> dict:
        return {"cik": int(cik), "entityName": "Seagate Technology Holdings plc", "facts": {}}


def fake_package(_client, *, cik, accession, primary_document, form, output_dir, refresh=False):
    root = output_dir / f"CIK{cik}-{accession.replace('-', '')}" / "generation"
    root.mkdir(parents=True, exist_ok=True)
    (root / primary_document).write_text("filing")
    (root / "package-manifest.json").write_text(json.dumps({"generation": "generation"}))
    return root / primary_document


def fake_parse(_entrypoint, *, accession, form):
    return SimpleNamespace(as_dict=lambda: {"source_accession": accession, "form": form, "facts": []})


def test_capture_is_exact_immutable_and_serving_safe(tmp_path: Path) -> None:
    output = tmp_path / "output"
    cache = tmp_path / "cache"
    summary = capture.capture_recovery_sources(
        output_root=output,
        cache_root=cache,
        client=FakeClient(),
        package_capture=fake_package,
        parse=fake_parse,
        protected_serving_roots=(),
    )
    assert summary["case_count"] == 4
    assert [row["ticker"] for row in summary["cases"]] == ["NEE", "NEE", "DELL", "STX"]
    assert sorted(path.name for path in (output / "NEE-Q2").iterdir()) == [
        "package-manifest.json",
        "source-receipt.json",
        "structural-filing.json",
    ]
    first = (output / "summary.json").read_bytes()
    capture.capture_recovery_sources(
        output_root=output,
        cache_root=cache,
        client=FakeClient(),
        package_capture=fake_package,
        parse=fake_parse,
        protected_serving_roots=(),
    )
    assert (output / "summary.json").read_bytes() == first


def test_rejects_serving_root_and_wrong_peer_identity(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="serving"):
        capture._validate_paths(capture.PROTECTED_ROOTS[0] / "bad", tmp_path / "cache")

    class WrongPeer(FakeClient):
        def submissions(self, cik: str, *, refresh: bool = False) -> dict:
            value = super().submissions(cik, refresh=refresh)
            if cik == "0001137789":
                value["tickers"] = ["WRONG"]
            return value

    with pytest.raises(ValueError, match="peer source identity"):
        capture.capture_recovery_sources(
            output_root=tmp_path / "output",
            cache_root=tmp_path / "cache",
            client=WrongPeer(),
            package_capture=fake_package,
            parse=fake_parse,
            protected_serving_roots=(),
        )
