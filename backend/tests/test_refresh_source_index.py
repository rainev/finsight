import hashlib
import json
from pathlib import Path
import shutil

import pytest

from app.us_valuation.catalog import canonical_json_bytes
from app.us_valuation.refresh_source_index import (
    SourceIndexIdentityError,
    SourceIndexIntegrityError,
    build_source_index,
    load_source_index,
    persist_source_index,
)


def _write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _packet(root: Path, *, ticker="TEST", cik="0000123456", filings=None):
    packet = root / "batch-01" / ticker
    submissions = {"cik": cik, "name": "Test Corporation", "tickers": [ticker]}
    facts = {"cik": int(cik), "entityName": "Test Corporation", "facts": {}}
    submissions_raw = canonical_json_bytes(submissions)
    facts_raw = canonical_json_bytes(facts)
    manifest = {
        "issuer": {"ticker": ticker, "cik": cik, "issuer_name": "Test Corporation"},
        "files": {
            "submissions.json": {"sha256": hashlib.sha256(submissions_raw).hexdigest()},
            "companyfacts.json": {"sha256": hashlib.sha256(facts_raw).hexdigest()},
        },
        "packet_payload_sha256": {
            "submissions.json": hashlib.sha256(submissions_raw).hexdigest(),
            "companyfacts.json": hashlib.sha256(facts_raw).hexdigest(),
        },
        "eligible_filings": filings or [
            {"accession": "0000123456-26-000001", "form": "10-Q", "filed": "2026-08-01", "report_date": "2026-06-30"},
            {"accession": "0000123456-26-000002", "form": "10-K", "filed": "2026-08-02", "report_date": "2025-12-31"},
        ],
    }
    _write(packet / "submissions.json", submissions)
    _write(packet / "companyfacts.json", facts)
    _write(packet / "source-manifest.json", manifest)
    return packet


def _structural(root: Path, *, ticker="TEST", cik="0000123456"):
    directory = root / "batch-01-structural" / ticker
    structural = {
        "source_accession": "0000123456-26-000001",
        "form": "10-Q",
        "filed_date": "2026-08-01",
        "report_date": "2026-06-30",
        "facts": [{"entity_identifier": cik, "concept": "Revenue"}],
    }
    package = {
        "cik": cik,
        "accession": "0000123456-26-000001",
        "form": "10-Q",
        "filed_date": "2026-08-01",
        "report_date": "2026-06-30",
        "files": [{"local_path": "test.xsd", "sha256": "a" * 64}],
    }
    receipt = {"ticker": ticker, "cik": cik, "parser_definition_sha256": "b" * 64}
    _write(directory / "structural-filing.json", structural)
    _write(directory / "package-manifest.json", package)
    _write(directory / "source-receipt.json", receipt)
    return directory / "structural-filing.json"


def test_index_is_deterministic_and_preserves_ambiguity(tmp_path):
    _packet(tmp_path)
    _structural(tmp_path)
    first = build_source_index(tmp_path, created_at_epoch=100.0)
    second = build_source_index(tmp_path, created_at_epoch=100.0)
    assert first["input_fingerprint_sha256"] == second["input_fingerprint_sha256"]
    assert first["entries"] == second["entries"]
    packets=[e for e in first['entries'] if e['kind']=='packet'];assert len(packets)==1
    assert {e["accession"] for e in packets[0]['filings']} == {
        "0000123456-26-000001", "0000123456-26-000002"
    }


def test_lookup_reads_real_cached_fixture_without_rescan(tmp_path):
    packet = _packet(tmp_path)
    index_path = tmp_path / "source-index.json"
    build_source_index(tmp_path, index_path, created_at_epoch=100.0)
    index = load_source_index(index_path)
    rows = index.lookup(ticker="TEST", accession="0000123456-26-000001", kind="packet")
    assert len(rows) == 1
    result = index.read(rows[0])
    assert result["submissions"]["cik"] == "0000123456"
    assert Path(result["path"]) == packet


def test_legacy_packet_without_manifest_remains_indexable(tmp_path):
    packet=_packet(tmp_path)
    (packet/'source-manifest.json').unlink()
    payload=build_source_index(tmp_path,created_at_epoch=100.0)
    entries=[row for row in payload['entries'] if row['kind']=='packet']
    assert len(entries)==1 and entries[0]['filings'] == []
    target=tmp_path/'indexes'/f"{payload['input_fingerprint_sha256']}.json"
    persist_source_index(payload,target,output_root=tmp_path)
    value=load_source_index(target).read(entries[0])
    assert value['manifest'] is None and value['ticker']=='TEST'


def test_selected_read_rejects_source_drift(tmp_path):
    packet = _packet(tmp_path)
    index_path = tmp_path / "source-index.json"
    build_source_index(tmp_path, index_path, created_at_epoch=100.0)
    index = load_source_index(index_path)
    row = index.lookup(ticker="TEST", kind="packet")[0]
    (packet / "companyfacts.json").write_bytes(b'{"cik": 9999999}')
    with pytest.raises(SourceIndexIntegrityError, match="drifted|declared packet hash"):
        index.read(row)


def test_identity_mismatch_is_retained_but_not_read(tmp_path):
    _packet(tmp_path, cik="0000123456")
    facts_path = tmp_path / "batch-01" / "TEST" / "companyfacts.json"
    _write(facts_path, {"cik": 9999999, "entityName": "Wrong", "facts": {}})
    payload = build_source_index(tmp_path, created_at_epoch=100.0)
    rows = [entry for entry in payload["entries"] if entry["kind"] == "packet"]
    assert rows and rows[0]["validation_errors"]
    index_path = tmp_path / "source-index.json"
    build_source_index(tmp_path, index_path, created_at_epoch=100.0)
    index = load_source_index(index_path)
    with pytest.raises(SourceIndexIntegrityError):
        index.read(index.lookup(kind="packet")[0])


def test_invalid_filing_date_is_recorded_as_blocker(tmp_path):
    _packet(tmp_path, filings=[{
        "accession": "0000123456-26-000003", "form": "10-Q",
        "filed": "not-a-date", "report_date": "2026-06-30",
    }])
    payload = build_source_index(tmp_path, created_at_epoch=100.0)
    row = next(entry for entry in payload["entries"] if entry["kind"] == "packet")
    assert row["filed_date"] is None
    assert any("filed_date" in error for error in row["validation_errors"])


def test_path_escape_is_rejected(tmp_path):
    outside = tmp_path.parent / "outside-source.json"
    outside.write_text("{}")
    link = tmp_path / "batch" / "TEST" / "structural-filing.json"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    with pytest.raises(SourceIndexIntegrityError, match="escapes allowed output root"):
        build_source_index(tmp_path)


def test_in_root_symlink_is_resolved_and_retained(tmp_path):
    packet = _packet(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(packet, target_is_directory=True)
    payload = build_source_index(tmp_path, created_at_epoch=100.0)
    packet_rows = [entry for entry in payload["entries"] if entry["kind"] == "packet"]
    assert packet_rows
    assert all(not entry["path"].startswith("alias/") for entry in packet_rows)


def test_real_cached_source_is_indexable_when_workspace_output_exists():
    output = Path(__file__).resolve().parents[2] / "output"
    packet_manifest = next(output.rglob("source-manifest.json"), None)
    if packet_manifest is None:
        pytest.skip("cached SEC output is not present")
    packet = packet_manifest.parent
    manifest = json.loads(packet_manifest.read_text())
    assert manifest["issuer"]["ticker"]
    # A bounded real-source check copies only one cached packet, avoiding a
    # recursive scan of the full multi-gigabyte workspace fixture.
    import tempfile
    with tempfile.TemporaryDirectory() as destination:
        root = Path(destination) / "cached"
        root.mkdir()
        local_packet = root / packet.name
        local_packet.mkdir()
        for name in ("source-manifest.json", "submissions.json", "companyfacts.json"):
            shutil.copy2(packet / name, local_packet / name)
        payload = build_source_index(root, created_at_epoch=100.0)
    matches = [entry for entry in payload["entries"] if entry["path"] == packet.name]
    assert matches
    assert matches[0]["files"]["submissions.json"]["sha256"]


def test_structural_read_does_not_require_copied_raw_entrypoint(tmp_path):
    path=_structural(tmp_path)
    package=json.loads((path.parent/'package-manifest.json').read_text());package['entrypoint_local_path']='not-copied.htm';_write(path.parent/'package-manifest.json',package)
    payload=build_source_index(tmp_path,created_at_epoch=100.0);target=tmp_path/'index.json';persist_source_index(payload,target,output_root=tmp_path)
    index=load_source_index(target);result=index.read(index.lookup(ticker='TEST',kind='structural')[0])
    assert result['package_entrypoint_rehashed'] is False


def test_structural_in_verification_named_folder_keeps_cik_without_fake_ticker(tmp_path):
    path=_structural(tmp_path);target=tmp_path/'verification-output'/'structural-filing.json';target.parent.mkdir();target.write_bytes(path.read_bytes())
    payload=build_source_index(tmp_path,created_at_epoch=100.0)
    row=next(item for item in payload['entries'] if item['path']=='verification-output/structural-filing.json')
    assert row['ticker'] is None and row['cik']=='0000123456' and not row['validation_errors']
    assert row['fact_identity_complete'] is True


def test_wrapper_cik_does_not_claim_complete_fact_identity(tmp_path):
    path=_structural(tmp_path);value=json.loads(path.read_text());value['facts'][0].pop('entity_identifier');_write(path,value)
    payload=build_source_index(tmp_path,created_at_epoch=100.0)
    row=next(item for item in payload['entries'] if item['kind']=='structural')
    assert row['cik']=='0000123456' and row['fact_identity_complete'] is False
