"""Acquisition transaction tests; cached SEC bytes are real, transport is offline."""
import json
from pathlib import Path
import pytest
from app.us_valuation import refresh_job

ROOT = Path(__file__).resolve().parents[2]


def test_interrupted_real_packet_capture_resumes_without_refetching_success(tmp_path, monkeypatch):
    source = ROOT / 'output/batch-01-controlled/sources'
    registry = {'entries': [{'ticker':'AAPL','cik':'0000320193'}, {'ticker':'JPM','cik':'0000019617'}]}
    lookup = {row['cik']: row['ticker'] for row in registry['entries']}
    calls = []
    interrupted = [False]
    class OfflineTransport:
        def __init__(self, **kwargs): pass
        def submissions(self, cik, **kwargs):
            calls.append(cik)
            if cik == '0000019617' and not interrupted[0]:
                interrupted[0] = True
                raise KeyboardInterrupt('test interruption')
            return json.loads((source / lookup[cik] / 'submissions.json').read_text())
        def companyfacts(self, cik, **kwargs):
            return json.loads((source / lookup[cik] / 'companyfacts.json').read_text())
    monkeypatch.setattr(refresh_job, 'SecClient', OfflineTransport)
    with pytest.raises(KeyboardInterrupt):
        refresh_job.capture(tmp_path, registry, '2026-08-14', 'offline@example.invalid')
    status = json.loads((tmp_path / 'acquisition-status.json').read_text())
    frozen = refresh_job.capture(tmp_path, registry, '2026-08-14', 'offline@example.invalid', acquisition_id=status['acquisition_id'])
    assert calls.count('0000320193') == 1
    assert calls.count('0000019617') == 2
    assert frozen['packets']['AAPL']['companyfacts'] == json.loads((source/'AAPL/companyfacts.json').read_text())
    assert frozen['packets']['JPM']['submissions'] == json.loads((source/'JPM/submissions.json').read_text())
    calls.clear()
    assert refresh_job.capture(tmp_path, registry, '2026-08-14', 'offline@example.invalid', acquisition_id=status['acquisition_id']) == frozen
    assert calls == []
    with pytest.raises(ValueError, match='preserve acquisition cutoff'):
        refresh_job.capture(tmp_path, registry, '2026-08-15', 'offline@example.invalid', acquisition_id=status['acquisition_id'])
    with pytest.raises(ValueError, match='preserve predecessor'):
        refresh_job.capture(tmp_path, registry, '2026-08-14', 'offline@example.invalid', acquisition_id=status['acquisition_id'], context_fingerprint='changed-policy')
    packet_path = tmp_path/'acquisitions'/status['acquisition_id']/'packets/AAPL.json'
    damaged = json.loads(packet_path.read_text())
    damaged['packet']['companyfacts']['cik'] = 1
    packet_path.write_text(json.dumps(damaged))
    with pytest.raises(ValueError, match='checkpoint identity or hash'):
        refresh_job.capture(tmp_path, registry, '2026-08-14', 'offline@example.invalid', acquisition_id=status['acquisition_id'])


def test_checkpoint_write_failure_is_global_not_financial_invalidity(tmp_path, monkeypatch):
    class Transport:
        def __init__(self, **kwargs): pass
        def submissions(self, *args, **kwargs): return {'cik':1}
        def companyfacts(self, *args, **kwargs): return {'cik':1}
    real_atomic = refresh_job.atomic
    def fail_disk(path, payload, **kwargs):
        if path.parent.name == 'packets': raise OSError('disk full')
        return real_atomic(path, payload, **kwargs)
    monkeypatch.setattr(refresh_job, 'SecClient', Transport)
    monkeypatch.setattr(refresh_job, 'atomic', fail_disk)
    with pytest.raises(OSError, match='disk full'):
        refresh_job.capture(tmp_path, {'entries':[{'ticker':'A','cik':'0000000001'}]}, '2026-08-14', 'offline@example.invalid')


def test_offline_snapshot_excludes_unknown_issuers_and_contains_source_faults():
    registry = {'entries':[{'ticker':'A','cik':'0000000001'}]}
    invalid = {'cutoff':'2026-08-14','packets':{'A':{'submissions':{'cik':2},'companyfacts':{'cik':1}}}}
    result = refresh_job.checked_snapshot(invalid, registry, '2026-08-14')
    assert result['packets']['A']['acquisition_failed'] == 'source_identity_or_shape_invalid'
    assert 'rejected_payload_sha256' in result['packets']['A']
    invalid['packets']['B'] = {}
    with pytest.raises(ValueError, match='outside the frozen registry'):
        refresh_job.checked_snapshot(invalid, registry, '2026-08-14')
