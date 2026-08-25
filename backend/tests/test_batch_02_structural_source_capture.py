"""Offline contract for frozen Batch 02 structural source capture."""

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.us_valuation.batch_02 import BATCH_02_MANIFEST

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/capture_batch_02_structural_sources.py"
SPEC = importlib.util.spec_from_file_location("capture_batch_02_structural_sources", SCRIPT)
assert SPEC and SPEC.loader
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)


def _source_packets(root: Path) -> None:
    for issuer in BATCH_02_MANIFEST:
        packet = root / issuer.ticker; packet.mkdir(parents=True)
        submissions = {"cik": issuer.cik, "tickers": [issuer.ticker], "filings": {"recent": {"accessionNumber": [f"{issuer.cik}-26-000001", f"{issuer.cik}-26-000002"], "filingDate": ["2026-08-13", "2026-08-15"], "form": ["10-Q", "10-K"], "primaryDocument": ["quarter.htm", "later.htm"]}}}
        (packet / "submissions.json").write_text(json.dumps(submissions))
        declared = {"submissions.json": hashlib.sha256((packet / "submissions.json").read_bytes()).hexdigest()}
        manifest = {"schema_version": "FINSIGHT-BATCH-02-SOURCE-1", "valuation_date": "2026-08-14", "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "eligible_filings": [{"accession": f"{issuer.cik}-26-000001", "filed": "2026-08-13", "form": "10-Q", "primary_document": "quarter.htm"}], "packet_payload_sha256": declared}
        (packet / "source-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def _package(_client, *, cik, accession, primary_document, form, output_dir, refresh=False):
    root = output_dir / f"CIK{cik}-{accession.replace('-', '')}" / "generation"; root.mkdir(parents=True, exist_ok=True)
    (root / primary_document).write_text("filing")
    (root / "package-manifest.json").write_text(json.dumps({"generation": "fixed", "accession": accession, "cik": cik, "form": form}))
    return root / primary_document


def _parse(_entrypoint, *, accession, form):
    return SimpleNamespace(as_dict=lambda: {"source_accession": accession, "form": form, "facts": [{"value": "1"}]})


def test_capture_uses_pre_cutoff_filing_and_is_immutable_and_serving_safe(tmp_path: Path) -> None:
    source, output, cache_root, serving = (tmp_path / value for value in ("sources", "out", "cache", "serving"))
    _source_packets(source); serving.mkdir(); (serving / "sentinel").write_text("same")
    summary = capture.capture_structural_sources(source_root=source, output_root=output, cache_root=cache_root, client=object(), package_capture=_package, parse=_parse, protected_serving_roots=(serving,))
    assert summary["attempted"] == summary["parsed"] == 10 and summary["serving_artifacts_changed"] is False
    assert all(case["accession"].endswith("000001") for case in summary["cases"])
    assert sorted(path.name for path in (output / "OMC").iterdir()) == ["package-manifest.json", "source-receipt.json", "structural-filing.json"]
    first = (output / "summary.json").read_bytes()
    capture.capture_structural_sources(source_root=source, output_root=output, cache_root=cache_root, client=object(), package_capture=_package, parse=_parse, protected_serving_roots=(serving,))
    assert (output / "summary.json").read_bytes() == first and (serving / "sentinel").read_text() == "same"


def test_capture_rejects_serving_output_and_tampered_packet(tmp_path: Path) -> None:
    source = tmp_path / "sources"; _source_packets(source)
    with pytest.raises(ValueError, match="serving"):
        capture.capture_structural_sources(source_root=source, output_root=tmp_path / "serving", cache_root=tmp_path / "cache", client=object(), package_capture=_package, parse=_parse, protected_serving_roots=(tmp_path / "serving",))
    (source / "OMC" / "submissions.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        capture.capture_structural_sources(source_root=source, output_root=tmp_path / "out", cache_root=tmp_path / "cache", client=object(), package_capture=_package, parse=_parse, protected_serving_roots=())
