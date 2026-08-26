import json,sys
from pathlib import Path
from app.us_valuation.batch_10 import BATCH_10_MANIFEST,BATCH_10_TICKERS,BATCH_10_VALUATION_DATE
def test_batch_10_contract_is_exact_and_frozen():
 assert BATCH_10_VALUATION_DATE=='2026-08-14'
 assert BATCH_10_TICKERS==('HSY','HRL','KMB','KR','MKC','PEP','PG','SJM','TSN','WMT')
 assert len(BATCH_10_MANIFEST)==10 and len({row.cik for row in BATCH_10_MANIFEST})==10
 assert sum(row.role=='core' for row in BATCH_10_MANIFEST)==8
 assert [(row.ticker,row.role) for row in BATCH_10_MANIFEST if row.role=='boundary']==[('KR','boundary'),('PG','boundary')]
 assert all(row.partition_family_id=='operating_fcff' for row in BATCH_10_MANIFEST)
def test_batch_10_packet_reuse_preserves_inner_fetch_metadata(tmp_path):
 sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
 from capture_batch_10_sources import _reuse
 root=tmp_path/'reuse'/'HSY';root.mkdir(parents=True);payload={'ok':True};meta={'fetch_metadata':{'provenance_status':'network_fetch_recorded','fetched_at_epoch':123.}}
 for name,value in (('submissions.json',payload),('companyfacts.json',payload),('submissions.meta.json',meta),('companyfacts.meta.json',meta)):(root/name).write_text(json.dumps(value))
 _,_,sub_meta,fact_meta=_reuse(tmp_path/'reuse','HSY')
 assert sub_meta==fact_meta==meta['fetch_metadata']
