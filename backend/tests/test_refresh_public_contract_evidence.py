from copy import deepcopy
import json
from pathlib import Path
import subprocess,sys,pytest
from app.us_valuation.refresh_public_contract_evidence import validate_public_contract_evidence,extract_public_contract_evidence
ROOT=Path(__file__).resolve().parents[2];RECEIPT=ROOT/'output/us-refresh-runtime/public-contract-evidence/MCK.json'
def receipt():return json.loads(RECEIPT.read_bytes())
def bind(r=None):return validate_public_contract_evidence(r or receipt(),source_root=ROOT/'output')
def test_real_official_sources_prove_floor_and_event_descriptor_not_claim():
 r=bind();assert len(r['sources'])==6 and not r['executed_agreements_captured']
 assert r['core_put']['floor_percent']==75 and r['core_put']['initial_core_fair_value']==700_000_000
 assert r['core_put']['source_arithmetic_floor']==525_000_000 and r['core_put']['first_exercise_date'] is None
 t=r['apollo_announcement']['terms'][0]['value'];assert t=={'investment':1_250_000_000,'subsidiary_interest_percent':13,'transaction_enterprise_valuation':13_000_000_000}
 assert r['claim_adjustment'] is None and not r['numeric_successor_issued']
 assert r['historical_component_evidence']['current_per_instrument_reconciliation'] is None
def test_two_real_put_vintages_agree_but_later_omission_is_not_revocation():
 r=bind();assert len(r['core_put']['vintages'])==2
 assert r['core_put']['latest_annual_and_current_omission']=='not_source_proven_revocation'
 assert r['historical_component_evidence']['annual_fair_value_adjustment'][0]['value']==87_000_000
 assert r['historical_component_evidence']['annual_core_redemption_adjustment'][0]['value']==122_000_000
@pytest.mark.parametrize('field,value',[('claim_adjustment',525_000_000),('executed_agreements_captured',True),('numeric_successor_issued',True)])
def test_receipt_cannot_promote_floor_or_transaction_descriptor(field,value):
 r=receipt();r[field]=value
 with pytest.raises(ValueError):bind(r)
def test_tampered_source_fails(tmp_path,monkeypatch):
 r=receipt();target=(ROOT/'output'/r['sources'][0]['document_path']).resolve();original=Path.read_bytes
 monkeypatch.setattr(Path,'read_bytes',lambda p:b'tampered' if p.resolve()==target else original(p))
 with pytest.raises(ValueError,match='hash/size'):bind(r)
def test_capture_cannot_substitute_another_official_url(monkeypatch):
 r=receipt();target=(ROOT/'output'/r['capture_report_path']).resolve();original=Path.read_bytes;cap=json.loads(original(target));cap['rows'][0]['url']='https://www.sec.gov/Archives/edgar/data/927653/other.htm';cap['rows'][0]['final_url']=cap['rows'][0]['url']
 monkeypatch.setattr(Path,'read_bytes',lambda p:json.dumps(cap).encode() if p.resolve()==target else original(p))
 with pytest.raises(ValueError,match='identity/date/type'):extract_public_contract_evidence(target,source_root=ROOT/'output')
def test_real_frozen_workers_execute_public_source_receipt_without_numeric_bypass():
 p=subprocess.run([sys.executable,str(ROOT/'scripts/verify_us_refresh_group.py'),'--ticker','MCK','--ticker','LHX','--max-workers','2',
  '--source-index',str(ROOT/'output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json')],cwd=ROOT,check=True,capture_output=True,text=True)
 summary=json.loads(p.stdout.strip().splitlines()[-1]);report=json.loads(Path(summary['report_path']).read_bytes())
 mck=next(r for r in report['rows'] if r['ticker']=='MCK')
 assert mck['status']=='implementation_gap'
 assert mck['partial_public_contract_evidence']['core_put']['source_arithmetic_floor']==525_000_000
 assert mck['partial_public_contract_evidence']['claim_adjustment'] is None
 assert not mck['partial_public_contract_evidence']['numeric_successor_issued']
 assert 'partial_public_contract_evidence' not in next(r for r in report['rows'] if r['ticker']=='LHX')
