import hashlib
from importlib.resources import files
from app.us_valuation.batch_22 import BATCH_22_MANIFEST,BATCH_22_TICKERS,BATCH_22_VALUATION_DATE
def test_batch_22_contract():
 assert BATCH_22_VALUATION_DATE=='2026-08-14' and BATCH_22_TICKERS==('HON','WM','IEX','JCI','ODFL','CPRT','LMT','WAB','ROK','FIX');assert len(BATCH_22_MANIFEST)==10 and len({r.cik for r in BATCH_22_MANIFEST})==10 and sum(r.role=='core' for r in BATCH_22_MANIFEST)==8;assert [(r.ticker,r.role) for r in BATCH_22_MANIFEST if r.role=='boundary']==[('ODFL','boundary'),('CPRT','boundary')]
def test_batch_22_hash():
 p=files('app.us_valuation').joinpath('config/reset_batches_2026_08_14/batch_22.json');assert hashlib.sha256(p.read_bytes()).hexdigest()=='1544cd049eaaea45e1c6472554495321dba0efbdc60353224e96595391fb27a8'
