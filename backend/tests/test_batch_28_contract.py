import hashlib
from importlib.resources import files
from app.us_valuation.batch_28 import BATCH_28_MANIFEST,BATCH_28_TICKERS,BATCH_28_VALUATION_DATE
def test_batch_28_contract():
 assert BATCH_28_VALUATION_DATE=='2026-08-14' and BATCH_28_TICKERS==('QCOM','CDNS','FICO','MCHP','GEN','PTC','CSCO','TYL','ZBRA','JBL');assert len(BATCH_28_MANIFEST)==10 and len({r.cik for r in BATCH_28_MANIFEST})==10 and sum(r.role=='core' for r in BATCH_28_MANIFEST)==8;assert [(r.ticker,r.role) for r in BATCH_28_MANIFEST if r.role=='boundary']==[('ZBRA','boundary'),('JBL','boundary')];assert all(r.partition_family_id=='operating_fcff' for r in BATCH_28_MANIFEST)
def test_batch_28_hash():
 p=files('app.us_valuation').joinpath('config/reset_batches_2026_08_14/batch_28.json');assert hashlib.sha256(p.read_bytes()).hexdigest()=='6d12a7011210d098790f3c0756dbe5fccd042e4cda32a26d5d97236738190350'
