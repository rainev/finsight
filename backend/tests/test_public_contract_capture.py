import hashlib,json
from pathlib import Path
import sys,pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import capture_public_contract_evidence as c

def test_rejects_host_cutoff_labels_and_credentials(tmp_path):
    base=dict(output_root=tmp_path/'out',cutoff='2026-08-14',user_agent='FinSight a@b.com')
    for source in ('x|2026-08-15|https://www.sec.gov/x','x|2026-01-01|http://www.sec.gov/x',
        'x|2026-01-01|https://example.com/x','../x|2026-01-01|https://www.sec.gov/x'):
        with pytest.raises(ValueError):c.capture(source_specs=[source],**base)
    with pytest.raises(ValueError):c.capture(source_specs=['x|2026-01-01|https://www.sec.gov/x'],**{**base,'user_agent':'bad'})

def test_realish_fetch_is_immutable_and_reused(tmp_path,monkeypatch):
    calls=[]
    def fetch(url,agent):calls.append(url);return b'evidence',url,'text/html'
    monkeypatch.setattr(c,'_fetch',fetch);args=dict(output_root=tmp_path/'out',source_specs=['x|2026-01-01|https://www.sec.gov/x.htm'],cutoff='2026-08-14',user_agent='FinSight a@b.com')
    first=c.capture(**args);second=c.capture(**args)
    assert first==second and calls==['https://www.sec.gov/x.htm']
    assert first['rows'][0]['sha256']==hashlib.sha256(b'evidence').hexdigest()
    (tmp_path/'out/x/x.htm').write_bytes(b'tampered')
    with pytest.raises(ValueError,match='mismatch'):c.capture(**args)
