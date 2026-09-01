from app.us_valuation.batch_13 import BATCH_13_MANIFEST,BATCH_13_TICKERS,BATCH_13_VALUATION_DATE
def test_batch_13_contract_is_exact_and_frozen():
 assert BATCH_13_VALUATION_DATE=='2026-08-14'
 assert BATCH_13_TICKERS==('PFE','TMO','JNJ','MRK','SYK','DHR','AMGN','COO','CAH','UNH')
 assert len(BATCH_13_MANIFEST)==10 and len({r.cik for r in BATCH_13_MANIFEST})==10
 assert sum(r.role=='core' for r in BATCH_13_MANIFEST)==8
 assert [(r.ticker,r.role) for r in BATCH_13_MANIFEST if r.role=='boundary']==[('COO','boundary'),('CAH','boundary')]
 assert all(r.partition_family_id=='operating_fcff' for r in BATCH_13_MANIFEST)
