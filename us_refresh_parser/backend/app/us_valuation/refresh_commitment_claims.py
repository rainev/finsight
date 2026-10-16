"""Versioned current-payable and timed-commitment scopes."""
from __future__ import annotations
from copy import deepcopy
from datetime import date
import json,re
from math import isfinite
from types import MappingProxyType
from typing import Any,Mapping

SCHEMA="FINSIGHT-COMMITMENT-CLAIM-1";VERSION="FINSIGHT-COMMITMENT-CLAIM-WG4-1";WG20_VERSION="FINSIGHT-COMMITMENT-CLAIM-WG20-1"
RULES: Mapping[str,Mapping[str,Any]]=MappingProxyType({
 "JBL":MappingProxyType({"schema_version":SCHEMA,"version":"FINSIGHT-COMMITMENT-CLAIM-WG23-1",
   "ticker":"JBL","cik":"0000898293","mode":"new_finance_lease_payment_schedule_review",
   "total_qname":"us-gaap:FinanceLeaseLiabilityPaymentsDue",
   "schedule_qnames":("us-gaap:FinanceLeaseLiabilityPaymentsDueInNextRollingTwelveMonths",
     "us-gaap:FinanceLeaseLiabilityPaymentsDueInRollingAfterYearFive"),
   "schedule_local_names":("FinanceLeaseLiabilityPaymentsDueInNextRollingYearOneThroughThree",
     "FinanceLeaseLiabilityPaymentsDueInNextRollingYearFourThroughFive"),
   "namespace_pattern":r"https?://(?:www\.)?jabil\.com/\d{8}",
   "treatment":"new-lease future payment total is not a full current finance-lease carrying claim; retain legacy deduction until carrying scope, timing and debt overlap are source-bound"}),
 "CRWD":MappingProxyType({"schema_version":SCHEMA,"version":WG20_VERSION,"ticker":"CRWD","cik":"0001535527","mode":"operating_purchase_schedule",
   "total_qname":"us-gaap:RecordedUnconditionalPurchaseObligation",
   "schedule_qnames":("us-gaap:RecordedUnconditionalPurchaseObligationDueInRemainderOfFiscalYear",
     "us-gaap:RecordedUnconditionalPurchaseObligationDueWithinOneYear",
     "us-gaap:RecordedUnconditionalPurchaseObligationDueInSecondYear",
     "us-gaap:RecordedUnconditionalPurchaseObligationDueInThirdYear",
     "us-gaap:RecordedUnconditionalPurchaseObligationDueInFourthYear"),
   "after_year_four_local_name":"RecordedUnconditionalPurchaseObligationToBePaidAfterYearFour",
   "unrecorded_qname":"us-gaap:UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount",
   "subsequent_event_axis":"us-gaap:SubsequentEventTypeAxis","subsequent_event_member":"us-gaap:SubsequentEventMember",
   "namespace_pattern":r"https?://(?:www\.)?crowdstrike\.com/\d{8}",
   "treatment":"reconcile the exact recorded purchase-obligation schedule to its total and retain both recorded and unrecorded purchase commitments in operating cash conversion; do not relabel them financing debt"}),
 "MU":MappingProxyType({"schema_version":SCHEMA,"version":VERSION,"ticker":"MU","cik":"0000723125","mode":"current_payable",
   "local_name":"PropertyPlantAndEquipmentPayableCurrent","namespace_pattern":r"https?://(?:www\.)?micron\.com/\d{8}",
   "paid_qname":"us-gaap:PaymentsToAcquirePropertyPlantAndEquipment","treatment":"current PP&E payable deducted once; paid capex and undated future purchase obligations remain separate"}),
 "KLAC":MappingProxyType({"schema_version":SCHEMA,"version":VERSION,"ticker":"KLAC","cik":"0000319201","mode":"timing_incomplete_total",
   "qname":"us-gaap:PurchaseCommitmentRemainingMinimumAmountCommitted","treatment":"mixed purchase commitment retained for review; equal-year timing is not source evidence"}),
 "NXPI":MappingProxyType({"schema_version":SCHEMA,"version":VERSION,"ticker":"NXPI","cik":"0001413447","mode":"aggregate_remaining_review",
   "local_name":"EquityMethodInvestmentsAdditionalInfrastructureInvestmentObligations",
   "contributed_local_name":"EquityMethodInvestmentsAdditionalInfrastructureInvestmentObligationsContributed",
   "remaining_local_name":"EquityMethodInvestmentsAdditionalInfrastructureInvestmentObligationsRemaining",
   "component_local_name":"EquityMethodInvestmentAdditionalInvestmentCommitmentObligation",
   "namespace_pattern":r"https?://(?:www\.)?nxp\.com/\d{8}","treatment":"aggregate less contributed-to-date reconciles to remaining carrying obligation; separate investee commitments need source timing before PV"}),
 "AVGO":MappingProxyType({"schema_version":SCHEMA,"version":VERSION,"ticker":"AVGO","cik":"0001730168","mode":"maximum_exposure_review",
   "qname":"us-gaap:GuaranteeObligationsMaximumExposure","treatment":"subsequent-event guarantee maximum is not a current liability or deterministic timed payment"}),
 "SNDK":MappingProxyType({"schema_version":SCHEMA,"version":VERSION,"ticker":"SNDK","cik":"0002023554","mode":"mixed_schedule_review",
   "total_qname":"us-gaap:PurchaseObligation","namespace_pattern":r"https?://(?:www\.)?sandisk\.com/\d{8}",
   "tax_local_name":"TaxLiabilityIndemnification","treatment":"mixed commitments, guarantees, paid investment and authorization remain separate; broad buckets are not evenly split"}),
})

def commitment_claim_policy(ticker):
 rule=RULES.get(ticker)
 if rule is None: raise ValueError(f"no commitment rule for {ticker!r}")
 return deepcopy(dict(rule))

def _same(a,b):return json.dumps(dict(a),sort_keys=True,separators=(",",":"))==json.dumps(dict(b),sort_keys=True,separators=(",",":"))
def _member(row,name):return any(isinstance(p,(list,tuple)) and len(p)==2 and str(p[1]).rsplit(":",1)[-1]==name for p in row.get("dimensions") or [])
def _context(policy,structural,controlling,cik,cutoff):
 expected=RULES.get(policy.get("ticker"))
 if expected is None or not _same(policy,expected) or str(cik).zfill(10)!=expected["cik"]:raise RuntimeError("commitment policy identity/version mismatch")
 acc,period,filed=controlling["accessionNumber"],controlling["reportDate"],controlling["filingDate"]
 if structural.get("source_accession")!=acc or (structural.get("report_date") or structural.get("period_end"))!=period or not period<=filed<=cutoff:raise ValueError("commitment source identity/period/cutoff mismatch")
 date.fromisoformat(period);date.fromisoformat(filed);date.fromisoformat(cutoff)
 return expected,acc,period,structural.get("facts",[])
def _valid(row,p,acc,period,instant=True,issuer=False):
 if row.get("source_accession")!=acc or row.get("unit")!="USD" or str(row.get("entity_identifier","")).zfill(10)!=p["cik"] or row.get("entity_scheme")!="http://www.sec.gov/CIK" or row.get("period_end")!=period or (instant and row.get("period_start") is not None) or isinstance(row.get("value"),bool) or not isinstance(row.get("value"),(int,float)) or not isfinite(row["value"]):raise ValueError("commitment fact identity/unit/amount invalid")
 ns=str(row.get("namespace",""))
 if issuer and not re.fullmatch(p["namespace_pattern"],ns):raise ValueError("commitment issuer namespace mismatch")
 if not issuer and not re.fullmatch(r"https?://(?:fasb\.org|xbrl\.us-gaap)/us-gaap/20\d{2}",ns):raise ValueError("commitment GAAP namespace mismatch")
def _one(rows,label):
 if not rows:raise ValueError(f"{label} missing; absence is not zero")
 vals={float(r["value"]) for r in rows}
 if len(vals)!=1:raise ValueError(f"{label} conflicts")
 return rows[0],vals.pop()

def select_commitment_claim(policy:Mapping[str,Any],structural:Mapping[str,Any],controlling:Mapping[str,Any],cik:str,cutoff:str)->dict[str,Any]:
 p,acc,period,facts=_context(policy,structural,controlling,cik,cutoff);mode=p["mode"];src=[];excluded=[];review=[];claim=None;components={}
 if mode=="current_payable":
  rows=[r for r in facts if r.get("local_name")==p["local_name"] and r.get("period_end")==period and r.get("period_start") is None and not r.get("dimensions")]
  for r in rows:_valid(r,p,acc,period,issuer=True)
  row,claim=_one(rows,"current PP&E payable");src=[row]
  paid=[r for r in facts if r.get("qname")==p["paid_qname"] and r.get("period_end")==period and r.get("period_start")]
  for r in paid:_valid(r,p,acc,period,instant=False)
  if not paid:raise ValueError("paid capex evidence missing")
  excluded=paid;components={"current_payable":claim,"paid_capex":float(paid[0]["value"])}
 elif mode=="aggregate_remaining_review":
  totals=[r for r in facts if r.get("local_name")==p["local_name"] and r.get("period_end")==period and r.get("period_start") is None and not r.get("dimensions")]
  remaining=[r for r in facts if r.get("local_name")==p["remaining_local_name"] and r.get("period_end")==period and r.get("period_start") is None]
  contributed=[r for r in facts if r.get("local_name")==p["contributed_local_name"] and r.get("period_start") and r.get("period_end")<period]
  parts=[r for r in facts if r.get("local_name")==p["component_local_name"] and r.get("period_end")==period and r.get("period_start") is None]
  for r in (*totals,*remaining,*parts):_valid(r,p,acc,period,issuer=True)
  for r in contributed:_valid(r,p,acc,r["period_end"],instant=False,issuer=True)
  row,total=_one(totals,"infrastructure obligation aggregate");remaining_row,claim=_one(remaining,"remaining infrastructure obligation")
  contributed_values={float(r["value"]) for r in contributed}
  matches=[value for value in contributed_values if value+claim==total]
  if len(matches)!=1:raise ValueError("contributed and remaining infrastructure obligation do not reconcile to aggregate")
  if not parts:raise ValueError("separate investee commitments missing")
  src=[row,remaining_row];excluded=[*contributed,*parts];components={"aggregate":total,"contributed_to_date":matches[0],"remaining":claim,"separate_investee_commitments":sum({float(r["value"]) for r in parts})}
  review=["separate_investee_commitments_lack_exact_payment_timing"]
 elif mode=="timing_incomplete_total":
  rows=[r for r in facts if r.get("qname")==p["qname"] and r.get("period_end")==period and r.get("period_start") is None and not r.get("dimensions")]
  for r in rows:_valid(r,p,acc,period)
  row,total=_one(rows,"purchase commitment total");src=[row];components={"reported_total":total};review=["source_timing_and_economic_scope_incomplete"]
 elif mode=="new_finance_lease_payment_schedule_review":
  def select(name,issuer=False):
   key='local_name' if issuer else 'qname'
   rows=[r for r in facts if r.get(key)==name and r.get('period_end')==period
         and r.get('period_start') is None and not r.get('dimensions')]
   for r in rows:_valid(r,p,acc,period,issuer=issuer)
   return _one(rows,name)
  row,total=select(p['total_qname']);parts=[select(q) for q in p['schedule_qnames']]
  parts.extend(select(n,True) for n in p['schedule_local_names'])
  if total<0 or any(value<0 for _,value in parts) or sum(value for _,value in parts)!=total:
   raise ValueError('new finance-lease payment schedule does not reconcile')
  src=[row,*[r for r,_ in parts]]
  components={'new_finance_lease_future_payments':total,
    'reported_nonannual_payment_buckets':{r['local_name']:value for r,value in parts},
    'current_total_carrying_finance_lease_claim':None}
  review=['new_lease_payment_schedule_lacks_full_current_carrying_scope_and_debt_overlap',
          'multiyear_payment_buckets_do_not_supply_exact_annual_timing']
 elif mode=="maximum_exposure_review":
  rows=[r for r in facts if r.get("qname")==p["qname"] and r.get("period_end","")>period and _member(r,"SubsequentEventMember")]
  for r in rows:_valid(r,p,acc,r["period_end"])
  row,total=_one(rows,"subsequent guarantee maximum");src=[row];components={"maximum_exposure":total};review=["maximum_exposure_is_not_current_liability"]
 elif mode=="mixed_schedule_review":
  totals=[r for r in facts if r.get("qname")==p["total_qname"] and r.get("period_end")==period and r.get("period_start") is None and not r.get("dimensions")]
  for r in totals:_valid(r,p,acc,period)
  row,total=_one(totals,"purchase obligation total")
  tax=[r for r in facts if r.get("local_name")==p["tax_local_name"] and r.get("period_end")==period and r.get("period_start") is None and not r.get("dimensions")]
  for r in tax:_valid(r,p,acc,period,issuer=True)
  taxrow,taxvalue=_one(tax,"tax indemnification")
  src=[row,taxrow];components={"mixed_commitment_total":total,"current_tax_indemnification":taxvalue};review=["mixed_commitment_schedules_and_post_period_payment_require_reconciliation"]
 elif mode=="operating_purchase_schedule":
  totals=[r for r in facts if r.get("qname")==p["total_qname"] and r.get("period_end")==period and r.get("period_start") is None and not r.get("dimensions")]
  for r in totals:_valid(r,p,acc,period)
  row,total=_one(totals,"recorded purchase-obligation total")
  schedule=[]
  for qname in p["schedule_qnames"]:
   rows=[r for r in facts if r.get("qname")==qname and r.get("period_end")==period and r.get("period_start") is None and not r.get("dimensions")]
   for r in rows:_valid(r,p,acc,period)
   selected,value=_one(rows,f"purchase-obligation schedule component {qname}");schedule.append((selected,value))
  after=[r for r in facts if r.get("local_name")==p["after_year_four_local_name"] and r.get("period_end")==period and r.get("period_start") is None and not r.get("dimensions")]
  for r in after:_valid(r,p,acc,period,issuer=True)
  after_row,after_value=_one(after,"purchase obligations after year four")
  schedule_total=sum(value for _,value in schedule)+after_value
  if schedule_total!=total:raise ValueError("purchase-obligation schedule does not reconcile to recorded total")
  unrecorded=[r for r in facts if r.get("qname")==p["unrecorded_qname"] and r.get("period_end")==period and r.get("period_start") is None and not r.get("dimensions")]
  for r in unrecorded:_valid(r,p,acc,period)
  unrecorded_row,unrecorded_value=_one(unrecorded,"unrecorded purchase obligation")
  post=[r for r in facts if r.get("qname")==p["total_qname"] and period<r.get("period_end","")<=cutoff
        and r.get("period_start") is None and dict(r.get("dimensions") or {})=={
         p["subsequent_event_axis"]:p["subsequent_event_member"]}]
  for r in post:_valid(r,p,acc,r["period_end"])
  post_row,post_value=_one(post,"post-period purchase obligation")
  if min(total,unrecorded_value,*[value for _,value in schedule],after_value)<0:raise ValueError("purchase-obligation schedule sign requires review")
  claim=0.;src=[];excluded=[row,*[item for item,_ in schedule],after_row,unrecorded_row,post_row]
  components={"recorded_operating_purchase_obligations":total,
   "recorded_payment_schedule":[value for _,value in schedule]+[after_value],
   "unrecorded_operating_purchase_obligations":unrecorded_value,
   "post_period_operating_purchase_obligation":post_value,
   "additional_equity_bridge_claim":0.0}
 else:raise RuntimeError("unsupported commitment mode")
 return {"status":"review_required" if review else "source_bound","claim_adjustment":None if review else claim,"current_carrying_claim":claim,"review_reasons":review,"policy":dict(p),"source_rows":src,"excluded_rows":excluded,"components":components,"period_end":period,"treatment":p["treatment"]}

__all__=["RULES","SCHEMA","VERSION","commitment_claim_policy","select_commitment_claim"]
