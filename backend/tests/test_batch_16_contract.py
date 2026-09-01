from app.us_valuation.batch_16 import BATCH_16_MANIFEST, BATCH_16_TICKERS, BATCH_16_VALUATION_DATE


def test_batch_16_contract_is_exact_and_frozen():
    assert BATCH_16_VALUATION_DATE == "2026-08-14"
    assert BATCH_16_TICKERS == ("A", "DXCM", "EW", "CRL", "ZBH", "COR", "PODD", "ELV", "VEEV", "IQV")
    assert len(BATCH_16_MANIFEST) == 10 and len({row.cik for row in BATCH_16_MANIFEST}) == 10
    assert sum(row.role == "core" for row in BATCH_16_MANIFEST) == 8
    assert [(row.ticker, row.role) for row in BATCH_16_MANIFEST if row.role == "boundary"] == [("COR", "boundary"), ("VEEV", "boundary")]
    assert all(row.partition_family_id == "operating_fcff" for row in BATCH_16_MANIFEST)
