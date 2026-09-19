"""Capture latest-universe evidence with immutable per-company checkpoints."""
import argparse
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime
import hashlib
import gzip
import json
import shutil
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.us_valuation.refresh_source_ingestion import capture_company_source
from app.us_valuation.refresh_source_index import load_source_index
from app.us_valuation.refresh_job import configured_sec_user_agent,atomic,writer
from app.us_valuation.catalog import canonical_json_bytes
from verify_us_refresh_sources import structural_candidate_rank
from app.us_valuation.sec_client import SecClient
from app.us_valuation.refresh_snapshot_cutoff import freeze_submissions


def reusable_packet(prior_root,row,root,stamp,client):
    """Reuse immutable filing bodies only after fresh discovery proves selection."""
    if prior_root.resolve()==root.resolve():return None
    path=prior_root/'captures'/f'{row["ticker"]}.json.gz'
    if not path.exists():path=path.with_suffix('')
    if not path.exists():return None
    raw=path.read_bytes()
    old=json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)
    packet=old['packet']
    if old['ticker']!=row['ticker'] or old['cik']!=row['cik']:raise ValueError('prior capture identity drift')
    if hashlib.sha256(canonical_json_bytes(packet)).hexdigest()!=old['packet_sha256']:raise ValueError('prior capture hash drift')
    for key,selected in [('controlling_filing','latest_regular'),('latest_annual_filing','latest_annual')]:
        filing=packet.get(key,{})
        if any(filing.get(k)!=row[selected].get(k) for k in ('accessionNumber','form','reportDate','primaryDocument')):return None
    prior_events={(e['accession'],e['form'],e['primary_document']) for e in packet.get('events',[]) if e.get('filed_date','')>='2026-08-14'}
    latest_events={(e['accessionNumber'],e['form'],e['primaryDocument']) for e in row['event_filings']}
    if prior_events!=latest_events or packet.get('amendment_acquisition_failures'):return None
    # Refresh machine facts while retaining earlier immutable filing bodies.
    packet['companyfacts']=client.companyfacts(row['cik'],refresh=False)
    if str(packet['companyfacts']['cik']).zfill(10)!=row['cik']:raise ValueError('fresh Companyfacts identity mismatch')
    raw_submissions=root/'sec-cache'/f'CIK{row["cik"]}-submissions.json'
    packet['submissions']=freeze_submissions(json.loads(raw_submissions.read_bytes()),stamp)
    packet['raw_hashes']={name:{'algorithm':'sha256','digest':hashlib.sha256((root/'sec-cache'/name).read_bytes()).hexdigest(),'basis':'sec_client_cache_raw_bytes'}
        for name in (f'CIK{row["cik"]}-submissions.json',f'CIK{row["cik"]}-companyfacts.json')}
    packet['prior_capture_reuse']={'path':str(path),'wrapper_sha256':hashlib.sha256(raw).hexdigest(),
        'packet_sha256':old['packet_sha256'],'selection_rechecked_against_fresh_discovery':True}
    return packet

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT/'output/latest-universe-20260919');p.add_argument('--ticker',action='append')
    p.add_argument('--workers',type=int,choices=(1,2),default=1)
    p.add_argument('--parser-timeout',type=int,default=300)
    a=p.parse_args()
    if not 1<=a.parser_timeout<=600:raise ValueError('parser timeout must be between 1 and 600 seconds')
    root=a.root.resolve(); discovery=json.loads((root/'discovery-report.json').read_bytes())
    if not discovery.get('complete') or len(discovery.get('rows',[]))!=500:
        raise ValueError('complete frozen 500-company discovery is required before capture')
    index=load_source_index(ROOT/'output/us-refresh-runtime/source-indexes/d5be9454237ce017d88950e2923206e539c063b805348b2173baa9f00ad32bfb.json',allowed_output_root=ROOT/'output')
    cutoff=discovery['cutoff']; stamp=discovery.get('snapshot_timestamp') or max(r['retrieved_at'] for r in discovery['rows'])
    descriptor={'schema_version':'FINSIGHT-LATEST-500-CAPTURE-1','cutoff':cutoff,'retrieval_snapshot_timestamp':stamp,'discovery_sha256':hashlib.sha256((root/'discovery-report.json').read_bytes()).hexdigest(),'expected_count':500}
    atomic(root/'capture-input.json',canonical_json_bytes(descriptor))
    ua=configured_sec_user_agent(ROOT/'output/us-refresh-runtime')
    client=SecClient(user_agent=ua,cache_dir=root/'sec-cache',requests_per_second=2,max_retries=2,timeout_seconds=30)
    wanted=set(a.ticker or []); known={r['ticker'] for r in discovery['rows']}
    if wanted-known:raise ValueError('ticker outside frozen universe')
    items=[r for r in discovery['rows'] if not wanted or r['ticker'] in wanted]
    priority={'BIIB','HON','INTC','JBL','MCK','LHX','GILD','INCY'}
    items.sort(key=lambda r:(r['ticker'] not in priority,not r.get('changed_regular',False),r['ticker']))
    def capture(row):
        t=row['ticker'];dest=root/'captures'/f'{t}.json.gz'
        existing=dest if dest.exists() else dest.with_suffix('')
        if existing.exists():
            data=existing.read_bytes()
            old=json.loads(gzip.decompress(data) if existing.suffix=='.gz' else data)
            if old.get('discovery_sha256')!=descriptor['discovery_sha256']:raise ValueError('checkpoint discovery drift')
            if hashlib.sha256(canonical_json_bytes(old['packet'])).hexdigest()!=old['packet_sha256']:raise ValueError('checkpoint packet hash mismatch')
            return {'ticker':t,'status':'captured','receipt_path':str(existing),'receipt_sha256':hashlib.sha256(data).hexdigest(),'reused':True}
        try:
            if shutil.disk_usage(root).free < 5*1024**3:raise ValueError('disk_capacity_guard: less than 5 GiB free; capture not attempted')
            if not row.get('latest_regular') or not row.get('latest_annual'):raise ValueError('historical submissions resolution required')
            selected={f['accessionNumber']:f for f in (row['latest_regular'],row['latest_annual'])}
            structural={}
            cache_selection=[]
            for acc,filing in selected.items():
                accepted=filing.get('acceptanceDateTime')
                if accepted and datetime.fromisoformat(accepted.replace('Z','+00:00'))>datetime.fromisoformat(stamp):raise ValueError('filing accepted after frozen retrieval timestamp')
                matches=[e for e in index.entries if e.get('kind')=='structural' and e.get('cik')==row['cik'] and e.get('accession')==acc and not e.get('validation_errors') and e.get('fact_identity_complete') is True]
                if matches:
                    ranked=[(structural_candidate_rank(e,identified=e.get('fact_identity_complete') is True),e) for e in matches]
                    best=max(rank for rank,e in ranked)
                    matches=[e for rank,e in ranked if rank==best]
                    hashes={e['files']['structural-filing.json']['sha256'] for e in matches if 'structural-filing.json' in e.get('files',{})}
                    if len(hashes)>1:
                        for candidate in matches:index.read(candidate)
                        cache_selection.append({'accession':acc,'decision':'reparse_official_package',
                            'reason':'equal-ranked cached derivations differ; no cached derivation selected',
                            'candidate_sha256':sorted(hashes)})
                        continue
                    chosen=sorted(matches,key=lambda e:e['path'])[0];index.read(chosen)
                    structural[acc]=ROOT/'output'/chosen['path']
            packet=reusable_packet(ROOT/'output/latest-universe-20260919',row,root,stamp,client)
            if packet is None:
                packet=capture_company_source(ticker=t,cik=row['cik'],cutoff=cutoff,cache_dir=root/'sec-cache',user_agent=ua,refresh=False,event_since='2026-08-13',require_structural=True,structural_paths=structural or None,structural_output_dir=root/'filings',parsed_cache_dir=root/'parsed',capture_event_relationships=True,arelle_timeout_seconds=a.parser_timeout,compress_parsed_cache=True,acceptance_cutoff=stamp,resource_store=root/'resource-store')
            primary=(packet.get('controlling_filing') or {}).get('accessionNumber')
            if primary!=row['latest_regular']['accessionNumber']:raise ValueError('captured controlling filing differs from frozen discovery')
            if cache_selection:packet['cache_selection']=cache_selection
            receipt={**descriptor,'ticker':t,'cik':row['cik'],'packet':packet,'packet_sha256':hashlib.sha256(canonical_json_bytes(packet)).hexdigest(),'valuation_refreshed':False}
            atomic(dest,gzip.compress(canonical_json_bytes(receipt),mtime=0))
            return {'ticker':t,'status':'captured','receipt_path':str(dest),'receipt_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'reused':False}
        except Exception as exc:
            return {'ticker':t,'status':'capture_failed','error':str(exc),'cause':str(exc.__cause__) if exc.__cause__ else None,'valuation_refreshed':False}
    with writer(root/'capture-lock'):
        rows=[]
        report_path=root/'capture-report.json'
        previous=json.loads(report_path.read_bytes()) if report_path.is_file() else {}
        if previous and any(previous.get(key)!=value for key,value in descriptor.items()):raise ValueError('capture report snapshot drift')
        accumulated={row['ticker']:row for row in previous.get('rows',[])}
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            remaining=iter(items)
            tasks={pool.submit(capture,r) for r in [next(remaining,None) for _ in range(a.workers)] if r is not None}
            while tasks:
                completed,_=wait(tasks,return_when=FIRST_COMPLETED)
                task=next(iter(completed));tasks.remove(task)
                result=task.result();rows.append(result)
                accumulated[result['ticker']]=result
                all_rows=sorted(accumulated.values(),key=lambda r:r['ticker'])
                report={**descriptor,'requested':len(items),'processed_this_invocation':len(rows),'processed':len(all_rows),'captured':sum(r['status']=='captured' for r in all_rows),'failed':sum(r['status']!='captured' for r in all_rows),'rows':all_rows,'valuation_refreshed_count':0}
                atomic(root/'capture-report.json',canonical_json_bytes(report),immutable=False)
                print(json.dumps({'ticker':result['ticker'],'status':result['status'],'processed':len(rows),'captured':report['captured'],'error':result.get('error')}),flush=True)
                row=next(remaining,None)
                if row is not None:tasks.add(pool.submit(capture,row))

if __name__=='__main__':main()
