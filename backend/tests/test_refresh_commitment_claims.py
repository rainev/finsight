from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.us_valuation.refresh_commitment_claims import commitment_claim_policy,select_commitment_claim

ROOT=Path(__file__).resolve().parents[2]
SOURCES={'MU':'output/batch-27-structural-sources-20260831/MU/structural-filing.json','KLAC':'output/batch-27-structural-sources-20260831/KLAC/structural-filing.json','NXPI':'output/batch-31-structural-sources-20260902/NXPI/structural-filing.json','AVGO':'output/batch-32-structural-sources-20260903/AVGO/structural-filing.json','SNDK':'output/batch-32-structural-sources-20260903/SNDK/structural-filing.json'}
def result(t):
 s=json.loads((ROOT/SOURCES[t]).read_text());f={'accessionNumber':s['source_accession'],'reportDate':s['report_date'],'filingDate':s['filed_date'],'form':s['form']};p=commitment_claim_policy(t)
 return select_commitment_claim(p,s,f,p['cik'],'2026-08-14')
def test_mu_current_payable_and_paid_capex_are_not_added():
 r=result('MU');assert r['status']=='source_bound' and r['claim_adjustment']==6_914_000_000
 assert r['components']=={'current_payable':6_914_000_000,'paid_capex':19_602_000_000}
def test_klac_total_has_no_invented_equal_year_pv():
 r=result('KLAC');assert r['status']=='review_required' and r['claim_adjustment'] is None
 assert r['components']['reported_total']==5_970_000_000 and r['review_reasons']==['source_timing_and_economic_scope_incomplete']
def test_nxpi_paid_and_remaining_reconcile_but_other_timing_blocks():
 r=result('NXPI');assert r['status']=='review_required' and r['claim_adjustment'] is None
 assert r['current_carrying_claim']==102_000_000
 assert r['components']=={'aggregate':1_200_000_000,'contributed_to_date':1_098_000_000,'remaining':102_000_000,'separate_investee_commitments':1_032_000_000}
def test_avgo_maximum_is_not_current_claim():
 r=result('AVGO');assert r['status']=='review_required' and r['components']['maximum_exposure']==29_000_000_000
 assert r['review_reasons']==['maximum_exposure_is_not_current_liability']
def test_sndk_mixed_schedule_and_tax_claim_stay_separate():
 r=result('SNDK');assert r['status']=='review_required'
 assert r['components']=={'mixed_commitment_total':7_107_000_000,'current_tax_indemnification':131_000_000}
@pytest.mark.parametrize('ticker',SOURCES)
def test_policies_have_no_filing_constants_and_reject_tamper(ticker):
 p=commitment_claim_policy(ticker);assert not {'accession','period_end','filed_date','amount'}&set(p)
 s=json.loads((ROOT/SOURCES[ticker]).read_text());f={'accessionNumber':s['source_accession'],'reportDate':s['report_date'],'filingDate':s['filed_date']};p['version']='bad'
 with pytest.raises(RuntimeError,match='identity/version mismatch'):select_commitment_claim(p,s,f,p['cik'],'2026-08-14')
def test_mu_reclassification_preserves_prior_value():
 from app.us_valuation.calculation_recipe import evaluate_recipe
 recipe=json.loads((ROOT/'output/us-refresh-runtime/recipes/MU.json').read_text());mapped=deepcopy(recipe)
 for spec in mapped['scenarios'].values():
  assert spec['inputs']['preferred_equity']==6_914_000_000
  spec['inputs']['preferred_equity']=0.;spec['inputs']['nonoperating_adjustment']=-6_914_000_000
 assert evaluate_recipe(mapped)['range']==evaluate_recipe(recipe)['range']
