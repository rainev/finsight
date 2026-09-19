import gzip
import importlib.util
import json
from pathlib import Path

import pytest

from app.us_valuation.catalog import canonical_json_bytes, sha256_bytes
from app.us_valuation.refresh_source_ingestion import SourceCaptureError


spec=importlib.util.spec_from_file_location('latest_verifier',Path(__file__).resolve().parents[2]/'scripts/verify_us_refresh_sources.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def receipt(root, compressed):
    discovery=canonical_json_bytes({'rows':[]})
    (root/'discovery-report.json').write_bytes(discovery)
    descriptor={'cutoff':'2026-09-19','discovery_sha256':sha256_bytes(discovery),
                'retrieval_snapshot_timestamp':'2026-09-18T20:21:38+00:00'}
    (root/'capture-input.json').write_bytes(canonical_json_bytes(descriptor))
    packet={'submissions':{'cik':1,'filings':{'recent':{'accessionNumber':[]}}},'companyfacts':{'facts':{}}}
    wrapper={**descriptor,'ticker':'TEST','cik':'0000000001','packet':packet,
             'packet_sha256':sha256_bytes(canonical_json_bytes(packet))}
    (root/'captures').mkdir()
    path=root/'captures'/('TEST.json.gz' if compressed else 'TEST.json')
    raw=canonical_json_bytes(wrapper)
    path.write_bytes(gzip.compress(raw,mtime=0) if compressed else raw)
    return path,wrapper


@pytest.mark.parametrize('compressed',[False,True])
def test_capture_loader_validates_both_checkpoint_encodings(tmp_path,compressed):
    receipt(tmp_path,compressed)
    packet,provenance=module.latest_captured_packet(tmp_path,{'ticker':'TEST','cik':'1'},'2026-09-19')
    assert packet['submissions']['cik']==1
    assert provenance['network_accessed'] is False


def test_capture_loader_rejects_payload_drift(tmp_path):
    path,wrapper=receipt(tmp_path,False)
    wrapper['packet']['submissions']['cik']=2
    path.write_bytes(canonical_json_bytes(wrapper))
    with pytest.raises(SourceCaptureError,match='packet hash mismatch'):
        module.latest_captured_packet(tmp_path,{'ticker':'TEST','cik':'1'},'2026-09-19')


def test_capture_loader_rejects_discovery_drift(tmp_path):
    receipt(tmp_path,True)
    (tmp_path/'discovery-report.json').write_text('{}')
    with pytest.raises(SourceCaptureError,match='discovery hash mismatch'):
        module.latest_captured_packet(tmp_path,{'ticker':'TEST','cik':'1'},'2026-09-19')
