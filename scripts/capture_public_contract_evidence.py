#!/usr/bin/env python3
"""Capture an explicit list of official public documents immutably and hash them."""
from __future__ import annotations
import argparse,hashlib,json,os,tempfile,time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError

ALLOWED_HOSTS={'www.sec.gov','sec.gov','investor.mckesson.com','investors.biogen.com'}
SCHEMA='FINSIGHT-PUBLIC-CONTRACT-EVIDENCE-CAPTURE-1'
MAX_BYTES=20*1024*1024

class Redirects(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        target=_url(newurl)
        if target.hostname.removeprefix('www.')!=urlparse(req.full_url).hostname.removeprefix('www.'):
            raise ValueError('cross-host redirect requires a separately reviewed source URL')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def _url(value):
    parsed=urlparse(value)
    if parsed.scheme!='https' or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password:
        raise ValueError('source URL must use an approved official HTTPS host')
    return parsed

def _sha(raw):return hashlib.sha256(raw).hexdigest()
def _json(value):return (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
def _immutable(path,raw):
    if path.exists():
        if path.read_bytes()!=raw:raise FileExistsError('immutable evidence differs: '+str(path))
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as handle:handle.write(raw);handle.flush();os.fsync(handle.fileno())
        Path(name).replace(path)
    finally:
        Path(name).unlink(missing_ok=True)
def _fetch(url,user_agent):
    last=None;opener=build_opener(Redirects())
    # The configured contact is authorized for SEC retrieval, not third parties.
    request_agent=user_agent if urlparse(url).hostname in {'www.sec.gov','sec.gov'} else 'FinSight/1.0 official-evidence-review'
    for attempt in range(3):
        try:
            with opener.open(Request(url,headers={'User-Agent':request_agent,'Accept':'*/*'}),timeout=30) as response:
                final=response.geturl();_url(final);raw=response.read(MAX_BYTES+1)
                if len(raw)>MAX_BYTES:raise ValueError('public source exceeds size limit')
                return raw,final,response.headers.get_content_type()
        except (HTTPError,URLError,TimeoutError) as exc:
            last=exc
            if attempt<2:time.sleep(1+attempt)
    raise RuntimeError('public source request failed after bounded retries') from last

def capture(*,output_root,source_specs,cutoff,user_agent):
    output_root=Path(output_root).resolve();date.fromisoformat(cutoff)
    if any(urlparse(spec.split('|',2)[-1]).hostname in {'www.sec.gov','sec.gov'} for spec in source_specs):
        if not user_agent or '@' not in user_agent:raise ValueError('monitored SEC user agent required')
    labels=set();rows=[]
    for spec in source_specs:
        try:label,source_date,url=spec.split('|',2)
        except ValueError as exc:raise ValueError('source format is LABEL|YYYY-MM-DD|URL') from exc
        if not label.replace('-','').replace('_','').isalnum() or label in labels:raise ValueError('unique safe source label required')
        labels.add(label);date.fromisoformat(source_date)
        if source_date>cutoff:raise ValueError('public source exceeds frozen cutoff')
        parsed=_url(url);name=Path(parsed.path).name
        if not name or name in {'.','..'}:name=label+'.html'
        target=output_root/label/name;receipt_path=output_root/label/'source-receipt.json'
        if receipt_path.is_file() and target.is_file():
            receipt=json.loads(receipt_path.read_bytes())
            if receipt.get('url')!=url or receipt.get('sha256')!=_sha(target.read_bytes()):raise ValueError('cached public receipt/source mismatch')
            rows.append(receipt);continue
        raw,final,content_type=_fetch(url,user_agent)
        _immutable(target,raw)
        receipt={'schema_version':SCHEMA,'label':label,'source_date':source_date,'cutoff':cutoff,
            'url':url,'final_url':final,'host':urlparse(final).hostname,'document_name':name,
            'document_path':target.relative_to(output_root.parent).as_posix(),'content_type':content_type,
            'byte_count':len(raw),'sha256':_sha(raw)}
        _immutable(receipt_path,_json(receipt));rows.append(receipt)
    report={'schema_version':SCHEMA,'cutoff':cutoff,'attempted':len(source_specs),'captured':len(rows),
        'rows':rows,'economic_validation':False}
    _immutable(output_root/'capture-report.json',_json(report));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--source',action='append',dest='source_specs',required=True);p.add_argument('--cutoff',required=True)
    p.add_argument('--user-agent',default=os.environ.get('SEC_USER_AGENT'))
    print(json.dumps(capture(**vars(p.parse_args())),sort_keys=True))
