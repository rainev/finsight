from app.us_valuation.batch_15 import BATCH_15_MANIFEST,BATCH_15_TICKERS,BATCH_15_VALUATION_DATE
def test_batch_15_contract_is_exact_and_frozen():
 assert BATCH_15_VALUATION_DATE=='2026-08-14'
 assert BATCH_15_TICKERS==('LH','DVA','RMD','HSIC','WAT','DGX','ISRG','MTD','CNC','ALGN')
 assert len(BATCH_15_MANIFEST)==10 and len({r.cik for r in BATCH_15_MANIFEST})==10
 assert sum(r.role=='core' for r in BATCH_15_MANIFEST)==8
 assert [(r.ticker,r.role) for r in BATCH_15_MANIFEST if r.role=='boundary']==[('HSIC','boundary'),('ALGN','boundary')]
 assert next(r for r in BATCH_15_MANIFEST if r.ticker=='RMD').issuer_name=='ResMed|'
 assert all(r.partition_family_id=='operating_fcff' for r in BATCH_15_MANIFEST)
