"""Fresh, resumable SEC submissions discovery for the frozen 500-company universe.

This does not claim full filing acquisition, economic validation or publication.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.us_valuation.sec_client import SecClient
from app.us_valuation.refresh_job import configured_sec_user_agent,atomic
from app.us_valuation.catalog import canonical_json_bytes

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cutoff',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--snapshot-at',help='Exact UTC-aware acceptance cutoff; retrieve metadata after freezing this instant')
    args=parser.parse_args()
    manifest_path=ROOT/'output/batch-50-api-runtime-a/catalogs/US-RESET-2026-08-14-B01-B50-INITIAL-1.0/manifest.json'
    raw=manifest_path.read_bytes(); manifest=json.loads(raw)
    assert len(manifest['entries'])==500
    out=args.output; out.mkdir(parents=True,exist_ok=True)
    identity={'cutoff':args.cutoff,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'expected_count':500}
    snapshot=None
    if args.snapshot_at:
        snapshot=datetime.fromisoformat(args.snapshot_at.replace('Z','+00:00'))
        if snapshot.tzinfo is None or snapshot>datetime.now(timezone.utc):raise ValueError('snapshot must be an elapsed timezone-aware instant')
        identity['snapshot_timestamp']=snapshot.isoformat()
    atomic(out/'input.json',canonical_json_bytes(identity))
    client=SecClient(user_agent=configured_sec_user_agent(ROOT/'output/us-refresh-runtime'),cache_dir=out/'sec-cache',requests_per_second=2,max_retries=2,timeout_seconds=30)
    rows=[]; failures=0
    for entry in manifest['entries']:
        ticker=entry['ticker']; cik=str(entry['cik']).zfill(10); receipt=out/'companies'/f'{ticker}.json'
        if receipt.exists():
            row=json.loads(receipt.read_bytes())
            if row['cutoff']!=args.cutoff or row['cik']!=cik or row.get('snapshot_timestamp')!=identity.get('snapshot_timestamp'):raise ValueError('checkpoint identity mismatch')
            cached=out/'sec-cache'/f'CIK{cik}-submissions.json'
            if hashlib.sha256(cached.read_bytes()).hexdigest()!=row['submissions_sha256']:raise ValueError('checkpoint source drift')
        else:
            try:
                s=client.submissions(cik,refresh=True)
                if str(s['cik']).zfill(10)!=cik:raise ValueError('SEC CIK mismatch')
                recent=s['filings']['recent']; filings=[]
                for i,acc in enumerate(recent['accessionNumber']):
                    f={key:values[i] for key,values in recent.items() if isinstance(values,list) and i<len(values)}
                    eligible=f.get('filingDate','')<=args.cutoff
                    if eligible and snapshot is not None:
                        accepted=f.get('acceptanceDateTime')
                        if not accepted:eligible=False
                        else:
                            instant=datetime.fromisoformat(accepted.replace('Z','+00:00'))
                            if instant.tzinfo is None:raise ValueError('SEC acceptance timestamp has no timezone')
                            eligible=instant<=snapshot
                    if eligible:filings.append(f)
                annual=[f for f in filings if f['form'] in ('10-K','20-F','40-F')]
                regular=[f for f in filings if f['form'] in ('10-K','10-Q','20-F','40-F')]
                sort=lambda fs:sorted(fs,key=lambda f:(f.get('filingDate',''),f.get('acceptanceDateTime','')),reverse=True)
                latest=sort(regular)[0] if regular else None
                baseline=json.loads((manifest_path.parent/'artifacts'/f'{ticker}.json').read_bytes())['source_financial_statement']
                events=sort([f for f in filings if f['form'] in ('8-K','8-K/A','6-K','10-Q/A','10-K/A','20-F/A') and f['filingDate']>=manifest['valuation_date']])
                source=out/'sec-cache'/f'CIK{cik}-submissions.json'
                row={**identity,'ticker':ticker,'cik':cik,'sec_name':s.get('name'),'sec_tickers':s.get('tickers'),'retrieved_at':datetime.now(timezone.utc).isoformat(),'submissions_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'latest_regular':latest,'latest_annual':sort(annual)[0] if annual else None,'baseline_accession':baseline.get('accession'),'changed_regular':latest is not None and latest['accessionNumber']!=baseline.get('accession'),'event_filings':events,'older_submission_files':s['filings'].get('files',[]),'status':'discovered' if latest else 'historical_submissions_search_required','valuation_refreshed':False}
                atomic(receipt,canonical_json_bytes(row)); failures=0
            except Exception as exc:
                failures+=1
                cause=exc.__cause__
                row={**identity,'ticker':ticker,'cik':cik,'status':'retrieval_failed','error':str(exc),'cause':str(cause) if cause else None,'valuation_refreshed':False}
        rows.append(row)
        report={**identity,'attempted':len(rows),'captured':sum(r['status']!='retrieval_failed' for r in rows),'changed_regular':sum(r.get('changed_regular',False) for r in rows),'companies_with_events':sum(bool(r.get('event_filings')) for r in rows),'rows':rows,'complete':len(rows)==500,'valuation_refreshed_count':0}
        atomic(out/'discovery-report.json',canonical_json_bytes(report),immutable=False)
        if len(rows)%25==0 or row['status']=='retrieval_failed':print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)
        if failures>=3:raise RuntimeError('Three consecutive retrieval failures; resume after source access recovery')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)

if __name__=='__main__':main()
