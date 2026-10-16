"""Source-bound post-period event state transitions."""
from copy import deepcopy
from datetime import date
import json,re
from math import isfinite
SCHEMA='FINSIGHT-POST-FILING-EVENT-1';VERSION=SCHEMA+'-MRK-1'
RULE={'schema_version':SCHEMA,'version':VERSION,'ticker':'MRK','cik':'0000310158',
 'current_claim_qnames':('us-gaap:AssetAcquisitionContingentConsiderationLiabilityCurrent','us-gaap:AssetAcquisitionContingentConsiderationLiabilityNoncurrent'),
 'current_claim_member':'PelotonTherapeuticsInc.Member','litigation_qname':'us-gaap:LitigationReserve','litigation_member':'LegalDefenseCostsMember',
 'event_qname':'us-gaap:BusinessCombinationConsiderationTransferred1','event_member':'TARGANMember','event_state_member':'SubsequentEventMember',
 'treatment':'current claims remain at period end; completed post-period acquisition cash reduces value once without adding transaction price as intrinsic value'}
def post_filing_event_policy():return deepcopy(RULE)
def _member(row,name):return any(isinstance(p,(list,tuple)) and len(p)==2 and str(p[1]).rsplit(':',1)[-1]==name for p in row.get('dimensions') or [])
def _valid(row,acc,cik):
 if row.get('source_accession')!=acc or row.get('unit')!='USD' or str(row.get('entity_identifier','')).zfill(10)!=cik or row.get('entity_scheme')!='http://www.sec.gov/CIK' or not re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',str(row.get('namespace',''))) or isinstance(row.get('value'),bool) or not isinstance(row.get('value'),(int,float)) or not isfinite(row['value']) or row['value']<0:raise ValueError('post-filing event fact identity/unit/amount invalid')
def _one(rows,label):
 if not rows:raise ValueError(label+' missing')
 vals={float(r['value']) for r in rows}
 if len(vals)!=1:raise ValueError(label+' conflicts')
 return rows[0],vals.pop()
def select_post_filing_event(policy,structural,controlling,cik,cutoff):
 if json.dumps(policy,sort_keys=True)!=json.dumps(RULE,sort_keys=True) or str(cik).zfill(10)!=RULE['cik']:raise RuntimeError('post-filing event policy identity/version mismatch')
 acc,period,filed=controlling['accessionNumber'],controlling['reportDate'],controlling['filingDate']
 if structural.get('source_accession')!=acc or (structural.get('report_date') or structural.get('period_end'))!=period or not period<=filed<=cutoff:raise ValueError('post-filing event source identity/period/cutoff mismatch')
 facts=structural.get('facts',[]);sources=[];current=0.
 for q in RULE['current_claim_qnames']:
  rows=[r for r in facts if r.get('qname')==q and r.get('period_end')==period and r.get('period_start') is None and _member(r,RULE['current_claim_member'])]
  for r in rows:_valid(r,acc,RULE['cik'])
  row,value=_one(rows,q);sources.append(row);current+=value
 rows=[r for r in facts if r.get('qname')==RULE['litigation_qname'] and r.get('period_end')==period and r.get('period_start') is None and _member(r,RULE['litigation_member'])]
 for r in rows:_valid(r,acc,RULE['cik'])
 row,litigation=_one(rows,'litigation reserve');sources.append(row)
 events=[r for r in facts if r.get('qname')==RULE['event_qname'] and r.get('period_start') and r.get('period_start')>period and r.get('period_end')<=filed and r.get('period_end')<=cutoff and _member(r,RULE['event_member']) and _member(r,RULE['event_state_member'])]
 for r in events:_valid(r,acc,RULE['cik'])
 event,event_cash=_one(events,'completed post-period acquisition cash')
 return {'status':'review_required','claim_adjustment':None,'current_carrying_claim':current+litigation,
  'review_reasons':['completed_event_lacks_post_event_cash_debt_share_rollforward_and_event_receipt'],'policy':policy,'source_rows':sources,'excluded_rows':[event],
  'components':{'current_contingent_claim':current,'current_litigation_reserve':litigation,'post_period_completed_acquisition_cash':event_cash},
  'period_end':period,'formula':'current claims remain period-end liabilities; completed transaction is context until post-event cash/debt/share state is source-bound','treatment':RULE['treatment']}
__all__=['SCHEMA','VERSION','post_filing_event_policy','select_post_filing_event']
