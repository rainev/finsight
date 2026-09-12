"""Versioned acquisition and financing claim scopes for WG9.

The mappings contain semantic source selectors and approved scenario rules, not
filing dates, accessions, or amounts.  Paid cash, recognized liabilities,
ownership claims, supplier financing, and pending events remain disjoint.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from math import isclose, isfinite
import re
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA="FINSIGHT-ACQUISITION-FINANCING-CLAIMS-1"
VERSION="FINSIGHT-ACQUISITION-FINANCING-WG9-1"
_GAAP=re.compile(r"^https?://(?:fasb\.org|xbrl\.us-gaap)/us-gaap/20\d{2}$")


RULES: Mapping[str,Mapping[str,Any]]=MappingProxyType({
    "KDP":MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"KDP","cik":"0001418135",
        "mode":"complex_financing_review",
        "nci_qname":"us-gaap:MinorityInterest",
        "temporary_carrying_qname":"us-gaap:TemporaryEquityCarryingAmountAttributableToParent",
        "temporary_liquidation_qname":"us-gaap:TemporaryEquityLiquidationPreference",
        "preferred_zero_qname":"us-gaap:PreferredStockValue",
        "mandatory_redemption_qname":"us-gaap:SharesSubjectToMandatoryRedemptionSettlementTermsAmountNoncurrent",
        "supplier_total_qname":"us-gaap:SupplierFinanceProgramObligationCurrent",
        "supplier_location_axis":"us-gaap:StatementOfFinancialPositionLocationBalanceAxis",
        "supplier_typed_domain":"us-gaap:QName.domain",
        "supplier_operating_member":"us-gaap:AccountsPayableCurrent",
        "supplier_financing_member_local_name":"StructuredPayablesCurrent",
        "structured_payables_local_name":"StructuredPayablesCurrent",
        "deferred_consideration_local_name":"AccruedConsiderationToUntenderedShareholdersInTheJDEPeetsAcquisition",
        "acquisition_cash_qname":"us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired",
        "inventory_stepup_local_name":"AmortizationOfInventoryStepUp",
        "preferred_proceeds_qname":"us-gaap:ProceedsFromIssuanceOfConvertiblePreferredStock",
        "preferred_dividend_qname":"us-gaap:PaymentsOfDividendsPreferredStockAndPreferenceStock",
        "restricted_cash_qname":"us-gaap:RestrictedCashAndCashEquivalentsAtCarryingValue",
        "integration_range_qname":"us-gaap:RestructuringAndRelatedCostExpectedCost1",
        "integration_plan_member_local_name":"IntegrationOfJDEPeetsMember",
        "integration_minimum_member_local_name":"MinimumMember",
        "integration_maximum_member_local_name":"MaximumMember",
        "pro_forma_revenue_qname":"us-gaap:BusinessAcquisitionsProFormaRevenue",
        "pro_forma_acquisition_member_local_name":"JDEPeetsAcquisitionMember",
        "pro_forma_annualization_factor":2.0,
        "issuer_namespace_pattern":r"https?://(?:www\.)?keurigdrpepper\.com/\d{8}",
        "preferred_treatment":"deduct carrying/liquidation claim under the retained scenario policy; do not also add as-converted shares",
        "treatment":"keep NCI, temporary equity, mandatory redemption, supplier-finance locations, deferred acquisition consideration, integration stress, paid cash and inventory step-up separate; typed supplier locations require preserved semantic members before binding",
    }),
    "MSCI":MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"MSCI","cik":"0001408198",
        "mode":"recognized_claim_pending_event",
        "contingent_total_qname":"us-gaap:BusinessCombinationContingentConsiderationLiability",
        "contingent_current_qname":"us-gaap:BusinessCombinationContingentConsiderationLiabilityCurrent",
        "contingent_noncurrent_qname":"us-gaap:BusinessCombinationContingentConsiderationLiabilityNoncurrent",
        "paid_cash_qname":"us-gaap:PaymentForContingentConsiderationLiabilityFinancingActivities",
        "pending_price_qname":"us-gaap:PaymentsToAcquireBusinessesGross",
        "pending_member_local_name":"FirstStreetTechnologyIncMember",
        "restricted_cash_qname":"us-gaap:RestrictedCashCurrent",
        "pending_price_fractions":(1.0,0.5,0.0),
        "treatment":"deduct the reported current contingent-consideration liability once; exclude historical paid cash; keep pending First Street closing cash as full/half/zero private event sensitivity and leave unquantified contingent payments unresolved",
    }),
})


def acquisition_financing_policy(ticker:str)->dict[str,Any]:
    rule=RULES.get(ticker)
    if rule is None:raise ValueError(f"no acquisition-financing rule for {ticker!r}")
    return deepcopy(dict(rule))


def _same(actual,expected):
    return json.dumps(dict(actual),sort_keys=True,separators=(",",":"))==json.dumps(dict(expected),sort_keys=True,separators=(",",":"))


def _context(policy,structural,controlling,cik,cutoff):
    expected=RULES.get(policy.get("ticker"))
    if expected is None or not _same(policy,expected) or str(cik).zfill(10)!=expected["cik"]:
        raise RuntimeError("acquisition-financing policy identity/version mismatch")
    accession=controlling.get("accessionNumber") or controlling.get("accession")
    period=controlling.get("reportDate") or controlling.get("period_end")
    filed=controlling.get("filingDate") or structural.get("filed_date")
    if structural.get("source_accession")!=accession or not isinstance(period,str) or not isinstance(filed,str) or not period<=filed<=cutoff:
        raise ValueError("acquisition-financing source period/accession/cutoff mismatch")
    date.fromisoformat(period);date.fromisoformat(filed);date.fromisoformat(cutoff)
    facts=structural.get("facts")
    if not isinstance(facts,list):raise ValueError("acquisition-financing structural facts are missing")
    return expected,str(accession),period,facts


def _valid(row,*,policy,accession,unit="USD",issuer=False):
    if (row.get("source_accession")!=accession or row.get("unit")!=unit
        or str(row.get("entity_identifier","")).zfill(10)!=policy["cik"]
        or row.get("entity_scheme")!="http://www.sec.gov/CIK"
        or isinstance(row.get("value"),bool) or not isinstance(row.get("value"),(int,float))
        or not isfinite(float(row["value"]))):
        raise ValueError("acquisition-financing fact identity, unit or amount invalid")
    namespace=str(row.get("namespace",""))
    if issuer:
        if not re.fullmatch(str(policy["issuer_namespace_pattern"]),namespace):raise ValueError("acquisition-financing issuer namespace mismatch")
    elif not _GAAP.fullmatch(namespace):raise ValueError("acquisition-financing GAAP namespace mismatch")


def _one(facts,*,policy,accession,period,qname=None,local_name=None,instant=True,
         issuer=False,undimensioned=True,member_local=None):
    rows=[]
    for row in facts:
        if qname is not None and row.get("qname")!=qname:continue
        if local_name is not None and row.get("local_name")!=local_name:continue
        if instant:
            if row.get("period_end")!=period or row.get("period_start") is not None:continue
        else:
            if row.get("period_end")!=period or not isinstance(row.get("period_start"),str):continue
        dims=row.get("dimensions") or []
        if undimensioned and dims:continue
        if member_local is not None and not any(isinstance(pair,(list,tuple)) and len(pair)==2
            and str(pair[1]).rsplit(":",1)[-1]==member_local for pair in dims):continue
        _valid(row,policy=policy,accession=accession,issuer=issuer)
        rows.append(row)
    if not rows:raise ValueError(f"required acquisition-financing fact missing: {qname or local_name}")
    if not instant:
        start=min(str(row["period_start"]) for row in rows);rows=[row for row in rows if row["period_start"]==start]
    values={float(row["value"]) for row in rows}
    if len(values)!=1:raise ValueError(f"required acquisition-financing fact conflicts: {qname or local_name}")
    return dict(rows[0]),values.pop()


def _event_price(facts,*,policy,accession,period):
    rows=[]
    for row in facts:
        if row.get("qname")!=policy["pending_price_qname"] or row.get("unit")!="USD":continue
        if row.get("period_start")!=row.get("period_end") or not isinstance(row.get("period_end"),str) or row["period_end"]>period:continue
        if not any(isinstance(pair,(list,tuple)) and len(pair)==2 and str(pair[1]).rsplit(":",1)[-1]==policy["pending_member_local_name"] for pair in (row.get("dimensions") or [])):continue
        _valid(row,policy=policy,accession=accession);rows.append(row)
    if not rows or len({float(row["value"]) for row in rows})!=1:raise ValueError("pending acquisition price event missing or conflicting")
    return dict(rows[0]),float(rows[0]["value"])


def select_acquisition_financing_claim(policy:Mapping[str,Any],structural:Mapping[str,Any],
                                       controlling:Mapping[str,Any],cik:str,cutoff:str)->dict[str,Any]:
    policy,accession,period,facts=_context(policy,structural,controlling,cik,cutoff)
    def gaap(key,**kwargs):return _one(facts,policy=policy,accession=accession,period=period,qname=policy[key],**kwargs)
    def issuer(key,**kwargs):return _one(facts,policy=policy,accession=accession,period=period,local_name=policy[key],issuer=True,**kwargs)
    if policy["mode"]=="complex_financing_review":
        nci_row,nci=gaap("nci_qname");carrying_row,carrying=gaap("temporary_carrying_qname")
        liquidation_row,liquidation=gaap("temporary_liquidation_qname")
        preferred_row,preferred=gaap("preferred_zero_qname")
        mandatory_row,mandatory=gaap("mandatory_redemption_qname")
        supplier_total_row,supplier_total=gaap("supplier_total_qname")
        supplier_locations=[]
        for row in facts:
            if row.get("qname")==policy["supplier_total_qname"] and row.get("period_end")==period and row.get("period_start") is None and row.get("dimensions"):
                _valid(row,policy=policy,accession=accession);supplier_locations.append(dict(row))
        location_values=sorted({float(row["value"]) for row in supplier_locations})
        if len(location_values)!=2 or not isclose(sum(location_values),supplier_total,rel_tol=1e-12,abs_tol=.01):
            raise ValueError("supplier-finance locations do not reconcile to total")
        typed_by_member={}
        for row in supplier_locations:
            evidence=row.get("typed_dimensions")
            if not isinstance(evidence,list):continue
            for triple in evidence:
                if (not isinstance(triple,(list,tuple)) or len(triple)!=3
                    or triple[0]!=policy["supplier_location_axis"]
                    or triple[1]!=policy["supplier_typed_domain"]):continue
                member=str(triple[2]);local=member.rsplit(":",1)[-1]
                if member==policy["supplier_operating_member"]:
                    typed_by_member["operating_accounts_payable"]=(float(row["value"]),row)
                elif local==policy["supplier_financing_member_local_name"] and member.startswith("ns_"):
                    typed_by_member["structured_financing"]=(float(row["value"]),row)
        structured_row,structured_total=issuer("structured_payables_local_name")
        deferred_row,deferred=issuer("deferred_consideration_local_name")
        paid_row,paid=gaap("acquisition_cash_qname",instant=False)
        stepup_row,stepup=issuer("inventory_stepup_local_name",instant=False)
        proceeds_row,proceeds=gaap("preferred_proceeds_qname",instant=False)
        dividend_row,dividend=gaap("preferred_dividend_qname",instant=False)
        restricted_row,restricted=gaap("restricted_cash_qname")
        integration=[]
        for row in facts:
            if (row.get("qname")!=policy["integration_range_qname"] or row.get("period_end")!=period
                or row.get("period_start") is not None or row.get("unit")!="USD"):continue
            dims=row.get("dimensions") or []
            members={str(pair[1]).rsplit(":",1)[-1] for pair in dims if isinstance(pair,(list,tuple)) and len(pair)==2}
            if policy["integration_plan_member_local_name"] not in members:continue
            _valid(row,policy=policy,accession=accession);integration.append(dict(row))
        minimum=[row for row in integration if policy["integration_minimum_member_local_name"] in {str(pair[1]).rsplit(":",1)[-1] for pair in row.get("dimensions",[])}]
        maximum=[row for row in integration if policy["integration_maximum_member_local_name"] in {str(pair[1]).rsplit(":",1)[-1] for pair in row.get("dimensions",[])}]
        if len(minimum)!=1 or len(maximum)!=1:raise ValueError("JDE integration range is missing or ambiguous")
        integration_min,integration_max=float(minimum[0]["value"]),float(maximum[0]["value"])
        if not 0<=integration_min<=integration_max:raise ValueError("JDE integration range is invalid")
        pro_forma_row,pro_forma_h1=_one(
            facts,policy=policy,accession=accession,period=period,
            qname=policy["pro_forma_revenue_qname"],instant=False,undimensioned=False,
            member_local=policy["pro_forma_acquisition_member_local_name"])
        annualized_revenue=pro_forma_h1*float(policy["pro_forma_annualization_factor"])
        if pro_forma_h1<=0 or annualized_revenue<=0:raise ValueError("KDP pro-forma revenue anchor is nonpositive")
        if min(nci,carrying,liquidation,preferred,mandatory,supplier_total,structured_total,
               deferred,paid,stepup,proceeds,dividend,restricted)<0:raise ValueError("KDP claim sign requires review")
        if preferred!=0:raise ValueError("reported preferred value is nonzero and may overlap temporary equity")
        review=[]
        if set(typed_by_member)!={"operating_accounts_payable","structured_financing"}:
            review.append("typed_supplier_finance_location_members_not_preserved")
        operating_supplier=typed_by_member.get("operating_accounts_payable",(None,None))[0]
        financing_supplier=typed_by_member.get("structured_financing",(None,None))[0]
        if not review and not isclose(operating_supplier+financing_supplier,supplier_total,rel_tol=1e-12,abs_tol=.01):
            raise ValueError("typed supplier-finance members do not reconcile to total")
        fixed_claim=mandatory+deferred+(financing_supplier or 0.0)
        scenario_adjustments=None
        if not review:
            scenario_adjustments={
                "bear_adjustment":liquidation+integration_max+fixed_claim,
                "base_adjustment":carrying+integration_min+fixed_claim,
                "bull_adjustment":carrying+fixed_claim,
            }
        return {"status":"review_required" if review else "source_bound",
            "claim_adjustment":None if review else scenario_adjustments["base_adjustment"],
            **(scenario_adjustments or {}),"annualized_revenue":annualized_revenue,"review_reasons":review,
            "policy":dict(policy),"period_end":period,"controlling_accession":accession,
            "components":{"nci":nci,"temporary_equity_carrying":carrying,
                "temporary_equity_liquidation_preference":liquidation,
                "mandatory_redemption_liability":mandatory,"supplier_finance_total":supplier_total,
                "supplier_finance_unlabeled_location_values":location_values,
                "supplier_finance_operating_accounts_payable":operating_supplier,
                "supplier_finance_structured_financing":financing_supplier,
                "structured_payables_total":structured_total,"deferred_acquisition_consideration":deferred,
                "acquisition_cash_already_paid":paid,"inventory_stepup_in_ocf":stepup,
                "preferred_proceeds_already_in_cash":proceeds,"preferred_dividend_paid":dividend,
                "restricted_cash_excluded":restricted,"integration_cost_minimum":integration_min,
                "integration_cost_maximum":integration_max,
                "reported_pro_forma_h1_revenue":pro_forma_h1,
                "annualized_pro_forma_revenue":annualized_revenue,
                "preferred_treatment":"current claim under retained scenario basis; no as-converted shares added",
                **(scenario_adjustments or {})},
            "source_rows":[nci_row,carrying_row,liquidation_row,mandatory_row,supplier_total_row,*supplier_locations,deferred_row,*integration,pro_forma_row],
            "excluded_rows":[preferred_row,structured_row,paid_row,stepup_row,proceeds_row,dividend_row,restricted_row],
            "formula":"NCI remains separate; temporary-equity carrying/liquidation claim plus mandatory redemption, typed structured financing, deferred consideration and max/min/zero integration stress; no conversion dilution added"}
    if policy["mode"]=="recognized_claim_pending_event":
        total_row,total=gaap("contingent_total_qname",undimensioned=False)
        current_row,current=gaap("contingent_current_qname",undimensioned=False)
        noncurrent_row,noncurrent=gaap("contingent_noncurrent_qname",undimensioned=False)
        if not isclose(total,current+noncurrent,rel_tol=1e-12,abs_tol=.01):raise ValueError("contingent total does not reconcile to current and noncurrent components")
        paid_row,paid=gaap("paid_cash_qname",instant=False)
        pending_row,pending=_event_price(facts,policy=policy,accession=accession,period=period)
        restricted_row,restricted=gaap("restricted_cash_qname")
        if min(total,current,noncurrent,paid,pending,restricted)<0:raise ValueError("MSCI claim sign requires review")
        bear,base,bull=policy["pending_price_fractions"]
        adjustments={"bear_adjustment":total+pending*bear,"base_adjustment":total+pending*base,
                     "bull_adjustment":total+pending*bull}
        return {"status":"source_bound","claim_adjustment":total,**adjustments,
            "restricted_cash_adjustment":restricted,"review_reasons":[],"policy":dict(policy),
            "period_end":period,"controlling_accession":accession,
            "components":{"recognized_contingent_consideration":total,"current_component":current,
                "noncurrent_component":noncurrent,"paid_cash_not_repeated":paid,
                "pending_fixed_price_event":pending,"pending_unquantified_contingent_payments":None,
                "restricted_cash_excluded":restricted,**adjustments},
            "source_rows":[total_row,current_row,noncurrent_row],
            "excluded_rows":[paid_row,pending_row,restricted_row],
            "formula":"recognized current liability plus full/half/zero pending fixed-price sensitivity; paid cash and unquantified future consideration excluded"}
    raise RuntimeError("unsupported acquisition-financing mode")


__all__=["RULES","SCHEMA","VERSION","acquisition_financing_policy","select_acquisition_financing_claim"]
