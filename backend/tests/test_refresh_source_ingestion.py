"""Regression coverage for cutoff-bound cached source capture."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from app.us_valuation.refresh_source_ingestion import SourceCaptureError, capture_company_source


ROOT = Path(__file__).resolve().parents[2]
DDOG_PACKET = ROOT / "output/batch-32-sec-source-packets-20260903/DDOG"
DDOG_STRUCTURAL = ROOT / "output/batch-32-structural-replay-a-20260903/DDOG/structural-filing.json"


def _capture(**overrides):
    kwargs = {
        "ticker": "DDOG",
        "cik": "0001561550",
        "cutoff": "2026-08-14",
        "offline_packet_dir": DDOG_PACKET,
    }
    kwargs.update(overrides)
    return capture_company_source(**kwargs)


def test_real_cached_capture_binds_identity_cutoff_and_raw_hashes() -> None:
    packet = _capture()
    assert packet["issuer"] == {"ticker": "DDOG", "cik": "0001561550"}
    assert packet["cutoff"] == "2026-08-14"
    assert packet["network_mode"] == "offline_cache"
    assert packet["raw_hashes"]["submissions.json"]["digest"]
    assert packet["controlling_filing"]["filingDate"] <= packet["cutoff"]


def test_cached_capture_replays_at_multiple_explicit_cutoffs() -> None:
    first = _capture(cutoff="2026-08-14")
    second = _capture(cutoff="2026-08-20")
    assert first["cutoff"] != second["cutoff"]
    assert first["issuer"] == second["issuer"]
    assert first["raw_hashes"] == second["raw_hashes"]


def test_cached_capture_rejects_wrong_cik_identity() -> None:
    with pytest.raises(SourceCaptureError, match="CIK"):
        _capture(cik="0000000001")


def test_cached_manifest_hash_tampering_is_rejected(tmp_path: Path) -> None:
    packet = tmp_path / "DDOG"
    shutil.copytree(DDOG_PACKET, packet)
    manifest_path = packet / "source-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["submissions.json"]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(SourceCaptureError, match="manifest hash"):
        _capture(offline_packet_dir=packet)


def test_cached_capture_requires_monitored_user_agent_on_cache_miss(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SEC_USER_AGENT"):
        capture_company_source(
            ticker="DDOG",
            cik="0001561550",
            cutoff="2026-08-14",
            cache_dir=tmp_path / "empty-cache",
        )


def test_event_screen_is_cutoff_bound_and_preserves_amendments() -> None:
    packet = _capture()
    assert all(row["filed_date"] <= packet["cutoff"] for row in packet["amendment_filings"])
    assert all(row["filed_date"] <= packet["cutoff"] for row in packet["events"])


def test_output_packet_is_immutable_for_same_cutoff(tmp_path: Path) -> None:
    first = _capture(output_dir=tmp_path)
    second = _capture(output_dir=tmp_path)
    assert first["packet_sha256"] == second["packet_sha256"]
    with pytest.raises(FileExistsError):
        _capture(output_dir=tmp_path, cutoff="2026-08-20")


def test_structural_capture_uses_real_cached_structural_payload(tmp_path: Path) -> None:
    packet = _capture(
        structural_path=DDOG_STRUCTURAL,
        require_structural=False,
        structural_paths={"0001628280-26-054458": DDOG_STRUCTURAL},
        parsed_cache_dir=tmp_path / "parsed",
    )
    assert packet["structural_filing"]["source_accession"] == packet["controlling_filing"]["accessionNumber"]
    assert packet["structural_sha256"]


def test_structural_parse_cache_is_reused_on_second_read(tmp_path: Path) -> None:
    first = _capture(require_structural=False, structural_paths={"0001628280-26-054458": DDOG_STRUCTURAL}, parsed_cache_dir=tmp_path / "parsed")
    second = _capture(require_structural=False, structural_paths={"0001628280-26-054458": DDOG_STRUCTURAL}, parsed_cache_dir=tmp_path / "parsed")
    assert first["structural_sha256"] == second["structural_sha256"]
    assert second["structural_receipts"][0]["parsed_cache_reused"] is True
    from app.us_valuation.catalog import canonical_json_bytes, sha256_bytes
    assert first['structural_sha256'] == sha256_bytes(canonical_json_bytes(first['structural_filing']))


def test_structural_parse_cache_tampering_is_rejected(tmp_path: Path) -> None:
    parsed = tmp_path / "parsed"
    _capture(require_structural=False, structural_paths={"0001628280-26-054458": DDOG_STRUCTURAL}, parsed_cache_dir=parsed)
    cache_file = next(parsed.rglob("*.json"))
    value = json.loads(cache_file.read_text())
    value["parsed_sha256"] = "0" * 64
    cache_file.write_text(json.dumps(value))
    with pytest.raises(SourceCaptureError, match="cache identity|cache is invalid|digest"):
        _capture(require_structural=False, structural_paths={"0001628280-26-054458": DDOG_STRUCTURAL}, parsed_cache_dir=parsed)


def test_required_structural_capture_without_cached_source_fails_explicitly(tmp_path: Path) -> None:
    with pytest.raises(SourceCaptureError, match="structural"):
        _capture(structural_path=tmp_path / "missing.json", require_structural=True)


def test_real_arelle_entrypoint_is_parsed_once_and_reused_at_later_cutoff(tmp_path, monkeypatch):
    import app.us_valuation.refresh_source_ingestion as ingestion
    original = ingestion.parse_structural_filing
    calls = []
    def real_parse(*args, **kwargs):
        calls.append(str(args[0]))
        return original(*args, **kwargs)
    monkeypatch.setattr(ingestion,'parse_structural_filing',real_parse)
    entrypoint = next((ROOT/'output/batch-18-structural-cache-20260830/filings/ADP').rglob('adp-20260630.htm'))
    first_hash = None
    for cutoff in ('2026-08-14','2026-08-15'):
        packet = capture_company_source(ticker='ADP',cik='0000008670',cutoff=cutoff,
            offline_packet_dir=ROOT/'output/batch-18-source-replay-a/ADP',
            structural_paths={'0000008670-26-000030':entrypoint},require_structural=True,
            event_since='2026-08-14',parsed_cache_dir=tmp_path)
        assert packet['structural_filing']['source_accession'] == '0000008670-26-000030'
        assert packet['annual_structural_sha256'] == packet['structural_sha256']
        if first_hash is None: first_hash = packet['structural_sha256']
        else: assert packet['structural_sha256'] == first_hash
    assert len(calls) == 1
    assert packet['structural_receipts'][0]['parsed_cache_reused'] is True


def test_real_successive_sndk_filings_are_selected_without_editing_code():
    source = ROOT/'output/batch-32-sec-source-packets-20260903/SNDK'
    early = capture_company_source(ticker='SNDK',cik='0002023554',cutoff='2026-07-30',offline_packet_dir=source)
    later = capture_company_source(ticker='SNDK',cik='0002023554',cutoff='2026-08-20',offline_packet_dir=source)
    assert early['controlling_filing']['accessionNumber'] == '0001628280-26-029401'
    assert early['controlling_filing']['reportDate'] == '2026-04-03'
    assert later['controlling_filing']['accessionNumber'] == '0001628280-26-057406'
    assert later['controlling_filing']['reportDate'] == '2026-07-03'


def test_future_amendment_metadata_does_not_replace_underlying_regular_source(tmp_path):
    source = ROOT/'output/batch-32-sec-source-packets-20260903/SNDK'
    submissions = json.loads((source/'submissions.json').read_text())
    recent = submissions['filings']['recent']
    amendment = {'accessionNumber':'0002023554-26-000999','form':'10-Q/A','reportDate':'2026-04-03',
                 'filingDate':'2026-07-29','primaryDocument':'cover.htm'}
    for key,values in recent.items():
        if isinstance(values,list): values.append(amendment.get(key,''))
    (tmp_path/'submissions.json').write_text(json.dumps(submissions))
    (tmp_path/'companyfacts.json').write_bytes((source/'companyfacts.json').read_bytes())
    packet = capture_company_source(ticker='SNDK',cik='0002023554',cutoff='2026-07-30',offline_packet_dir=tmp_path)
    assert packet['controlling_filing']['accessionNumber'] == '0001628280-26-029401'
    assert any(row['accessionNumber']==amendment['accessionNumber'] for row in packet['amendment_filings'])
