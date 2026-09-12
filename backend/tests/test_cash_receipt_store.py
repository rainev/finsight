from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.us_valuation.cash_receipt_store import attach_cf_receipts, load_receipt_history
from app.us_valuation.catalog import canonical_json_bytes, sha256_bytes
from app.us_valuation.refresh_financials import cash_history, POLICY_VERSION
from app.us_valuation.xbrl import CompanyFactsNormalizer

ROOT = Path(__file__).parents[2]
CAPTURE = ROOT/'output/us-refresh-runtime/acquisitions/a587eafaa664f46d3971d383f81d4290a6aa1a83fa14d507c405ccab5fcedab0/packets/CF.json'


def source():
    wrapper = json.loads(CAPTURE.read_bytes())
    assert wrapper['packet_sha256'] == sha256_bytes(canonical_json_bytes(wrapper['packet']))
    return wrapper['packet']


def test_real_capture_retains_immutable_receipt_when_later_disclosure_is_omitted(tmp_path):
    packet = source()
    frozen = attach_cf_receipts(packet,history_root=tmp_path,source_root=ROOT/'output')
    assert frozen['cash_receipt_evidence'][0]['event']['cash_received_date'] == '2026-04-30'
    assert frozen['cash_receipt_evidence_sha256'] == sha256_bytes(canonical_json_bytes(frozen['cash_receipt_evidence']))
    # Simulated omitted disclosure, not a claim that this is a later real filing.
    later = {**deepcopy(packet),'cutoff':'2026-09-08','structural_receipts':[],'structural_packets':{}}
    carried = attach_cf_receipts(later,history_root=tmp_path,source_root=ROOT/'output')
    assert carried['cash_receipt_evidence'] == frozen['cash_receipt_evidence']
    assert load_receipt_history(tmp_path,cutoff='2026-08-01') == []
    path = next(tmp_path.glob('*.json'))
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='history hash mismatch'):
        load_receipt_history(tmp_path,cutoff='2026-09-08')


def test_real_cf_normalization_removes_cash_receipt_once_not_from_prior_annuals():
    packet = source()
    recent = packet['submissions']['filings']['recent']
    records = [{key:values[i] for key,values in recent.items() if isinstance(values,list) and i<len(values)} for i in range(len(recent['accessionNumber']))]
    normalizer = CompanyFactsNormalizer(packet['companyfacts'],fiscal_year_end=packet['submissions']['fiscalYearEnd'],as_of_date=packet['cutoff'],filing_records=records)
    result = cash_history(normalizer,period='2026-06-30',cutoff=packet['cutoff'],rule={'normalization_version':POLICY_VERSION},cash_receipts=packet['cash_receipt_evidence'])
    assert result['cash_receipt_adjustment']['amount'] == 170000000
    assert result['cash_receipt_adjustment']['cash_fcff_before_adjustment'] - result['ttm_cash_fcff'] == pytest.approx(170000000)
    assert all(row['cash_receipt_adjustment']['amount'] == 0 for row in result['annual'])
    assert result['reported']['operating_cash_flow'] == 2977000000


def test_received_but_conflicting_disclosure_is_not_a_download_failure(tmp_path, monkeypatch):
    from app.us_valuation import refresh_job, cash_receipt_store
    from app.us_valuation.refresh_cash_receipts import CashReceiptReviewRequired
    packet = source()
    class Provider:
        def __init__(self, **kwargs): pass
        def submissions(self, *args, **kwargs): return packet['submissions']
        def companyfacts(self, *args, **kwargs): return packet['companyfacts']
    monkeypatch.setattr(refresh_job,'SecClient',Provider)
    monkeypatch.setattr(refresh_job,'capture_company_source',lambda **kwargs:deepcopy(packet))
    def conflict(*args, **kwargs):
        raise CashReceiptReviewRequired('conflicting receipt evidence')
    monkeypatch.setattr(cash_receipt_store,'attach_cf_receipts',conflict)
    registry={'entries':[{'ticker':'CF','cik':'0001324404'}]}
    result=refresh_job.capture(tmp_path,registry,'2026-08-14','offline@example.invalid',source_policies={'CF':{'cash_receipt_policy':'CF_ORICA_LITIGATION_SETTLEMENT'}})
    captured=result['packets']['CF']
    assert 'acquisition_failed' not in captured
    assert 'conflicting receipt evidence' in captured['normalization_review_required']
    checkpoint=json.loads(next((tmp_path/'acquisitions').glob('*/packets/CF.json')).read_bytes())
    assert checkpoint['packet']['normalization_review_required'] == captured['normalization_review_required']
