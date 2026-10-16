#!/usr/bin/env python3
"""Offline worker/real child smoke test with explicitly synthetic metadata.

This proves retention, identity and recipe preservation, NOT source acquisition
or new-filing recalculation. No DB job, network request or live pointer is used.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def verify(private,output):
    receipt=json.loads((ROOT/'docs/handoff/us700-receipt.json').read_bytes())
    catalog=private/'catalogs'/receipt['catalog_version']
    manifest=json.loads((catalog/'manifest.json').read_bytes())
    # Production explicitly forbids offline fixtures. This test-only permission
    # does not alter production guards; HTTP verification uses production mode.
    os.environ.update(APP_ENV='test',US_REFRESH_CODE_ROOT=str(ROOT),
        US_REFRESH_CODE_WT=str(ROOT/'us_refresh_parser'),PYTHONDONTWRITEBYTECODE='1')
    sys.path.insert(0,str(ROOT/'backend'))
    from app.us_valuation.us_refresh_worker import run_once
    with tempfile.TemporaryDirectory(prefix='us700-offline-partner-') as tmp:
        temp=Path(tmp);cats=temp/'catalogs';cats.mkdir();(cats/'snapshot').symlink_to(catalog,target_is_directory=True)
        pointer=json.dumps({'schema_version':'FINSIGHT-US-VALUATION-ACTIVE-1.0','catalog_version':receipt['catalog_version'],
            'catalog_path':'snapshot','manifest_sha256':receipt['manifest_sha256']}).encode()
        (cats/'active.json').write_bytes(pointer)
        source=temp/'synthetic-sources';cache=source/'sec-cache';cache.mkdir(parents=True)
        for row in manifest['entries']:
            artifact=json.loads((catalog/'artifacts'/f"{row['ticker']}.json").read_bytes())
            filing=artifact['source_financial_statement']
            recent={'accessionNumber':[filing['accession']],'form':[filing['form']],
                'filingDate':[filing['filed_date']],'reportDate':[filing['period_end']],
                'primaryDocument':['synthetic-offline-metadata.htm']}
            (cache/f"CIK{row['cik']}-submissions.json").write_text(json.dumps({'cik':row['cik'],'filings':{'recent':recent}}))
        os.environ['US_REFRESH_OFFLINE_SOURCE_ROOT']=str(source)
        # run_once launches the separately shipped parser as a real subprocess.
        report=run_once(catalogs_root=cats,runtime_root=private/'runtime',private_root=temp/'worker',
            cutoff='2026-10-13',runner=ROOT/'us_refresh_parser/scripts/run_us_500_stage_cycle.py')
        assert report['catalog_count']==report['selected_count']==700
        assert len(report['rows'])==700 and len({row['ticker'] for row in report['rows']})==700
        assert report['active_changed'] is False and (cats/'active.json').read_bytes()==pointer
        assert report['counts'].get('source_bound',0)==0
        candidate=report.get('candidate')
        if candidate:
            child=json.loads((Path(candidate['path'])/'manifest.json').read_bytes())
            assert child['entries']==manifest['entries']
            assert child['private_recipe_sha256']==manifest['private_recipe_sha256']
        proof={'synthetic_metadata':True,'real_worker_and_parser_subprocess':True,
            'catalog_count':700,'selected_count':700,'outcomes':report['counts'],
            'candidate_created':bool(candidate),'all_values_and_recipe_hashes_preserved':True,
            'live_SEC_check_or_recalculation_proved':False,'active_changed':False,'DB_job_started':False}
        output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();verify(a.private_root.resolve(),a.output.resolve())
