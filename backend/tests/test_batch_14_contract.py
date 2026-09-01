from app.us_valuation.batch_14 import BATCH_14_MANIFEST,BATCH_14_TICKERS,BATCH_14_VALUATION_DATE
def test_batch_14_contract_is_exact_and_frozen():
 assert BATCH_14_VALUATION_DATE=='2026-08-14'
 assert BATCH_14_TICKERS==('TECH','HCA','REGN','IDXX','BIIB','VRTX','INCY','GILD','BSX','MCK')
 assert len(BATCH_14_MANIFEST)==10 and len({r.cik for r in BATCH_14_MANIFEST})==10
 assert sum(r.role=='core' for r in BATCH_14_MANIFEST)==8
 assert [(r.ticker,r.role) for r in BATCH_14_MANIFEST if r.role=='boundary']==[('HCA','boundary'),('MCK','boundary')]
 assert all(r.partition_family_id=='operating_fcff' for r in BATCH_14_MANIFEST)
