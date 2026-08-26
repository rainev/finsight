from app.us_valuation.batch_09 import BATCH_09_MANIFEST,BATCH_09_TICKERS,BATCH_09_VALUATION_DATE
def test_batch_09_contract_is_exact_and_frozen():
 assert BATCH_09_VALUATION_DATE=='2026-08-14'
 assert BATCH_09_TICKERS==('ADM','BF.B','STZ','CLX','KO','CL','TAP','TGT','DG','GIS')
 assert len(BATCH_09_MANIFEST)==10 and len({row.cik for row in BATCH_09_MANIFEST})==10
 assert sum(row.role=='core' for row in BATCH_09_MANIFEST)==8
 assert [(row.ticker,row.role) for row in BATCH_09_MANIFEST if row.role=='boundary']==[('ADM','boundary'),('TAP','boundary')]
 assert all(row.partition_family_id=='operating_fcff' for row in BATCH_09_MANIFEST)
