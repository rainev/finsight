"""Real-source structural cash lookup; combined restricted balances stay gated."""
import json
from pathlib import Path

from app.us_valuation.official_evidence import EvidenceRequest
from app.us_valuation.official_filing_ingestion import _structural_evidence_decisions

ROOT = Path(__file__).parents[2]/'output/us-refresh-runtime/acquisitions'


def decision(acquisition,ticker):
    packet = json.loads((ROOT/acquisition/'packets'/f'{ticker}.json').read_text())['packet']
    structural = packet['structural_filing']
    record = packet['controlling_filing']
    filing = {'accession':structural['source_accession'],'form':structural['form'],
        'filed':structural['filed_date'],'report_date':structural['report_date'],
        'primary_document':record['primary_document'] if 'primary_document' in record else record['primaryDocument']}
    rows,_ = _structural_evidence_decisions([EvidenceRequest('cash','fcff_dcf','balance_sheet_snapshot','material',
        valuation_date='2026-08-14',expected_unit='USD')],parsed=structural,filing=filing,
        cik=str(packet['companyfacts']['cik']).zfill(10),valuation_date='2026-08-14',
        proof=(packet['structural_receipts'][0]['structural_sha256'],))
    return rows[0]


def test_standard_cash_concept_is_available_to_structural_lookup():
    row = decision('46b4aef07dddcaef6c42a278c4942007d5154e3dd16d9327f6be2f36f1866752','MSFT')
    assert row['status'] == 'reported'


def test_combined_restricted_cash_is_not_accepted_as_unrestricted_cash():
    row = decision('506c1ecff5edd36238a72e9a6ebe30be11e2679946d4c9342e329b811cd466bc','CSX')
    assert row['status'] not in {'reported','explicit_zero'}
    assert 'FIELD_NOT_IN_GOVERNED_EVIDENCE_REGISTRY' not in row['reason_codes']
