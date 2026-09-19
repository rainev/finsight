import hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from capture_selected_sec_filings import run

def sha(raw):return hashlib.sha256(raw).hexdigest()

class Client:
    def filing_index(self,cik,accession,refresh=False):
        primary='first.htm' if accession.endswith('084') else 'second.htm'
        return {'directory':{'item':[{'name':primary,'type':'text.gif'},
            {'name':'exhibit21.htm','type':'text.gif'},{'name':'unlinked-exhibit99.htm','type':'text.gif'}]}}
    def filing_attachment(self,cik,accession,filename,refresh=False,max_bytes=None):
        if filename in {'first.htm','second.htm'}:return b'<html><a href="exhibit21.htm">Exhibit 2.1</a></html>'
        return b'<html>agreement</html>'

def test_exact_filings_follow_direct_exhibit_links_and_replay(tmp_path):
    source=tmp_path/'source';source.mkdir();submissions={'cik':'773840','tickers':['HON'],'filings':{'recent':{
        'accessionNumber':['0000773840-26-000084','0000773840-26-000120'],'filingDate':['2026-06-29','2026-07-23'],
        'reportDate':['2026-06-25','2026-07-23'],'form':['8-K','8-K'],'items':['1.01,9.01','2.02,9.01'],
        'primaryDocument':['first.htm','second.htm']}}}
    raw=json.dumps(submissions).encode();(source/'submissions.json').write_bytes(raw)
    manifest={'issuer':{'ticker':'HON','cik':'0000773840'},'packet_payload_sha256':{'submissions.json':sha(raw)}}
    (source/'source-manifest.json').write_text(json.dumps(manifest))
    kwargs=dict(source_root=source,output_root=tmp_path/'out',cache_root=tmp_path/'cache',ticker='HON',
        accessions=['0000773840-26-000084','0000773840-26-000120'],cutoff='2026-08-14',user_agent='test@example.com',client=Client())
    first=run(**kwargs);second=run(**kwargs)
    assert first==second and first['captured']==2 and not first['economic_validation']
    for case in first['cases']:
        names={row['name'] for row in case['documents']}
        assert case['filing']['primary_document'] in names and 'exhibit21.htm' in names and 'unlinked-exhibit99.htm' not in names
        assert all(row['directly_linked_from_primary'] for row in case['documents'])
