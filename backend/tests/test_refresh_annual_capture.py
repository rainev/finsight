"""Selected annual acquisition integrity; doubles are unit tests, not source acceptance."""
import json
import hashlib
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from capture_us_annual_evidence import run


def inputs(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    submission = {'cik': '202058', 'tickers': ['LHX'], 'filings': {'recent': {
        'accessionNumber': ['new', 'old', 'quarter'], 'form': ['10-K', '10-K', '10-Q'],
        'filingDate': ['2026-02-12', '2025-02-14', '2026-07-30'],
        'reportDate': ['2026-01-02', '2025-01-03', '2026-07-03'],
        'primaryDocument': ['new.htm', 'old.htm', 'quarter.htm']}}}
    (source / 'submissions.json').write_text(json.dumps(submission))
    (source / 'source-manifest.json').write_text(json.dumps({
        'valuation_date':'2026-08-14','issuer':{'ticker':'LHX','cik':'202058'},'packet_payload_sha256':{
            'submissions.json':hashlib.sha256((source/'submissions.json').read_bytes()).hexdigest()}}))
    return dict(source_root=source, output_root=tmp_path/'out', cache_root=tmp_path/'cache',
                ticker='LHX', accessions=['new', 'old'], user_agent=None, client=object())


@pytest.mark.parametrize('accessions', [['old','new'], ['new','new'], ['missing'], ['quarter']])
def test_reject_unapproved_selection_shape_before_any_fetch(tmp_path,accessions):
    args=inputs(tmp_path); args['accessions']=accessions
    def forbidden(*args,**kwargs): raise AssertionError('must not fetch')
    with pytest.raises(ValueError): run(**args,package_capture=forbidden,parse=forbidden)


def test_failed_acquisition_records_transport_cause_without_economic_invalidity(tmp_path):
    args=inputs(tmp_path); calls=[]
    def fail(client,**kwargs):
        calls.append(kwargs['accession'])
        try: raise ConnectionError('transport unavailable')
        except ConnectionError as cause: raise RuntimeError('bounded request failed') from cause
    report=run(**args,package_capture=fail,parse=lambda *a,**k: None)
    assert calls==['new','old'] and report['parsed']==0
    assert not report['economic_validation']
    assert all(r['causes'][0]['error_type']=='ConnectionError' for r in report['cases'])
    assert report['serving_hash_before']==report['serving_hash_after']


def test_parsed_wrong_filing_date_not_accepted(tmp_path):
    args=inputs(tmp_path)
    def capture(client,**kwargs):
        target=tmp_path/kwargs['accession'];target.mkdir()
        (target/'package-manifest.json').write_text(json.dumps({'cik':'202058','accession':kwargs['accession']}))
        return target/'entry.htm'
    def parse(entry,**kwargs):
        return {'source_accession':kwargs['accession'],'report_date':'2026-01-02',
                'filed_date':'wrong','form':'10-K'}
    report=run(**args,package_capture=capture,parse=parse)
    assert report['parsed']==0
    assert all(r['status']=='acquisition_or_parse_failed' for r in report['cases'])

def test_corrupt_submissions_rejected_before_fetch(tmp_path):
    args=inputs(tmp_path);(args['source_root']/'submissions.json').write_text('{"cik":"1"}')
    def forbidden(*args,**kwargs):raise AssertionError('must not fetch')
    with pytest.raises(ValueError,match='hash mismatch'):run(**args,package_capture=forbidden,parse=forbidden)

def test_annual_after_cutoff_rejected_before_fetch(tmp_path):
    args=inputs(tmp_path);args['cutoff']='2026-01-01'
    def forbidden(*args,**kwargs):raise AssertionError('must not fetch')
    with pytest.raises(ValueError,match='cutoff'):run(**args,package_capture=forbidden,parse=forbidden)
