from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.us_valuation.refresh_post_filing_events import post_filing_event_policy,select_post_filing_event
ROOT=Path(__file__).resolve().parents[2]
def source():
 s=json.loads((ROOT/'output/batch-13-structural-sources-20260829/MRK/structural-filing.json').read_text());f={'accessionNumber':s['source_accession'],'reportDate':s['report_date'],'filingDate':s['filed_date'],'form':s['form']};return s,f
def test_mrk_current_claims_and_completed_post_period_cash_count_once():
 s,f=source();r=select_post_filing_event(post_filing_event_policy(),s,f,'0000310158','2026-08-14')
 assert r['status']=='review_required' and r['claim_adjustment'] is None
 assert r['current_carrying_claim']==425_000_000
 assert r['components']=={'current_contingent_claim':150_000_000,'current_litigation_reserve':275_000_000,'post_period_completed_acquisition_cash':650_000_000}
def test_event_policy_has_no_filing_constants_and_rejects_tamper():
 p=post_filing_event_policy();assert not {'accession','period_end','filed_date','amount'}&set(p);p['version']='bad';s,f=source()
 with pytest.raises(RuntimeError,match='identity/version mismatch'):select_post_filing_event(p,s,f,'0000310158','2026-08-14')
def test_post_period_transaction_price_is_not_applied_to_intrinsic_value():
 s,f=source();r=select_post_filing_event(post_filing_event_policy(),s,f,'0000310158','2026-08-14')
 assert r['excluded_rows'][0]['value']==650_000_000
 assert r['review_reasons']==['completed_event_lacks_post_event_cash_debt_share_rollforward_and_event_receipt']
