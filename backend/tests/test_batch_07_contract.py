from app.us_valuation.batch_07 import BATCH_07_MANIFEST,BATCH_07_TICKERS,BATCH_07_VALUATION_DATE
def test_batch_07_contract_is_exact():
 assert BATCH_07_VALUATION_DATE=="2026-08-14"
 assert BATCH_07_TICKERS==("EL","EBAY","BKNG","TPR","GRMN","WYNN","DPZ","LVS","TSLA","EXPE")
 assert tuple(row.ticker for row in BATCH_07_MANIFEST)==BATCH_07_TICKERS
 assert len({row.cik for row in BATCH_07_MANIFEST})==10
 assert sum(row.role=="core" for row in BATCH_07_MANIFEST)==8
 assert sum(row.role=="boundary" for row in BATCH_07_MANIFEST)==2
 assert all(row.partition_family_id=="operating_fcff" for row in BATCH_07_MANIFEST)
