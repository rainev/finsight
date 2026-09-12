import json

import pytest

from app.us_valuation.catalog import canonical_json_bytes, sha256_bytes
from app.us_valuation.refresh_source_ingestion import SourceCaptureError
from scripts.verify_us_refresh_sources import acquired_packet,structural_candidate_rank


def test_structural_candidate_rank_prefers_current_parser_and_complete_filing_identity():
    from app.us_valuation.refresh_source_ingestion import _definition_hash
    old={'parser_definition_sha256':None,'filing':{'accession':'a','form':'10-Q','report_date':None,'filed_date':None}}
    current={'parser_definition_sha256':_definition_hash(),'filing':{
        'accession':'a','form':'10-Q','report_date':'2026-06-30','filed_date':'2026-08-10'}}
    assert structural_candidate_rank(current,identified=True)>structural_candidate_rank(old,identified=True)


@pytest.fixture
def captured(tmp_path):
    descriptor = {'cutoff': '2026-09-08'}
    acquisition = sha256_bytes(canonical_json_bytes(descriptor))
    root = tmp_path/'acquisitions'/acquisition
    (root/'packets').mkdir(parents=True)
    (root/'input.json').write_bytes(canonical_json_bytes(descriptor))
    packet = {'submissions': {'cik': '123'}}
    wrapper = {'ticker': 'ABC', 'cik': '0000000123', 'packet': packet,
               'packet_sha256': sha256_bytes(canonical_json_bytes(packet))}
    path = root/'packets/ABC.json'
    path.write_bytes(canonical_json_bytes(wrapper))
    return tmp_path, acquisition, {'ticker': 'ABC', 'cik': '123'}, path


def test_verified_capture_is_reused_without_network(captured):
    root, acquisition, entry, path = captured
    packet, provenance = acquired_packet(root, acquisition, entry, '2026-09-08')
    assert packet['submissions']['cik'] == '123'
    assert provenance['network_accessed'] is False
    assert provenance['wrapper_sha256'] == sha256_bytes(path.read_bytes())


@pytest.mark.parametrize('change', ['packet', 'identity', 'cutoff', 'descriptor', 'path'])
def test_capture_verification_rejects_drift(captured, change):
    root, acquisition, entry, path = captured
    cutoff = '2026-09-08'
    wrapper = json.loads(path.read_bytes())
    if change == 'packet':
        wrapper['packet']['submissions']['cik'] = '999'
    elif change == 'identity':
        wrapper['cik'] = '999'
    elif change == 'cutoff':
        cutoff = '2026-09-09'
    elif change == 'descriptor':
        (path.parent.parent/'input.json').write_text('{}')
    else:
        acquisition = '../escape'
    path.write_bytes(canonical_json_bytes(wrapper))
    with pytest.raises((SourceCaptureError, ValueError)):
        acquired_packet(root, acquisition, entry, cutoff)
