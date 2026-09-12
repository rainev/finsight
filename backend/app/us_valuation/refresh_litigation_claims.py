"""Versioned litigation/insurance claim scopes; no filing constants or fitted zeros."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from math import isfinite
import re
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA = "FINSIGHT-LITIGATION-CLAIM-1"
VERSION = "FINSIGHT-LITIGATION-CLAIM-WG3-1"
WG15_VERSION = "FINSIGHT-LITIGATION-CLAIM-WG15-1"
_GAAP = re.compile(r"^https?://(?:fasb\.org|xbrl\.us-gaap)/us-gaap/20\d{2}$")


RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "ABT": MappingProxyType({
        "schema_version":SCHEMA,"version":WG15_VERSION,"ticker":"ABT","cik":"0000001800",
        "mode":"scoped_current_accrual","reserve_qname":"us-gaap:LossContingencyAccrualAtCarryingValue",
        "reserve_axis":"us-gaap:LossContingenciesByNatureOfContingencyAxis",
        "reserve_member":"LegalProceedingsAndEnvironmentalExposuresMember",
        "possible_loss_qname":"us-gaap:LossContingencyEstimateOfPossibleLoss",
        "range_axis_local_name":"RangeAxis",
        "range_member_local_names":("MinimumMember","MaximumMember"),
        "environmental_maximum_local_names":(
            "LossContingencyRangeOfPossibleLossMaximumAggregateSites",
            "LossContingencyRangeOfPossibleLossMaximumIndividualSite",
        ),
        "damages_qname":"us-gaap:LossContingencyDamagesAwardedValue",
        "case_axis_local_name":"LitigationCaseAxis",
        "case_member_local_name":"NecrotizingEnterocolitisNECMember",
        "zero_reserve_qname":"us-gaap:LitigationReserve",
        "issuer_namespace_pattern":r"https?://(?:www\.)?abbott\.com/\d{8}",
        "treatment":"deduct the current recorded legal/environmental accrual once; possible-loss ranges, site maxima, damages and zero case reserves remain non-additive diagnostics",
    }),
    "ABBV": MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"ABBV","cik":"0001551152",
        "mode":"direct_reserve","reserve_qname":"us-gaap:LitigationReserve",
        "overlap_local_name":"NonCashLitigationReserveAdjustmentsNetOfCashPayments",
        "issuer_namespace_pattern":r"https?://(?:www\.)?abbvie\.com/\d{8}",
        "treatment":"deduct the recorded litigation reserve once; keep the noncash reserve/cash-payment flow as overlap evidence",
    }),
    "STE": MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"STE","cik":"0001757898",
        "mode":"direct_reserve","reserve_qname":"us-gaap:LitigationReserve",
        "excluded_qnames":("us-gaap:SelfInsuranceReserveCurrent","us-gaap:SelfInsuranceReserveNoncurrent"),
        "treatment":"deduct the current litigation reserve once; self-insurance reserves are separate operating liabilities",
    }),
    "CAH": MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"CAH","cik":"0000721371",
        "mode":"scoped_reserves_post_period_review",
        "reserve_qname":"us-gaap:LitigationReserve","reserve_member":"TotalOpioidLitigationMember",
        "current_reserve_qname":"us-gaap:LitigationReserveCurrent",
        "other_accrual_qname":"us-gaap:LossContingencyAccrualAtCarryingValue",
        "other_accrual_member":"ProductLiabilityLawsuitsMember",
        "possible_loss_qname":"us-gaap:LossContingencyEstimateOfPossibleLoss",
        "post_period_payment_qname":"us-gaap:PaymentsForLegalSettlements",
        "treatment":"sum distinct current reserves once; current portions and historical possible-loss facts are not additive; post-period cash needs a claim/cash rollforward",
    }),
    "COO": MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"COO","cik":"0000711404",
        "mode":"recognized_receivable_net","reserve_qname":"us-gaap:LitigationReserveCurrent",
        "receivable_qname":"us-gaap:LossContingencyReceivable",
        "treatment":"deduct the current litigation reserve less only the separately recognized same-matter receivable; do not assume unrecognized insurance recovery",
    }),
    "DASH": MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"DASH","cik":"0001792789",
        "mode":"direct_reserve","reserve_qname":"us-gaap:LitigationReserveCurrent",
        "treatment":"deduct the recorded current litigation reserve once; customer, merchant, processor and contract balances remain separate operating items",
    }),
    "FIS": MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"FIS","cik":"0001136893",
        "mode":"operating_settlement_not_litigation",
        "settlement_asset_qname":"us-gaap:SettlementAssetsCurrent",
        "settlement_liability_qname":"us-gaap:SettlementLiabilitiesCurrent",
        "deposit_local_name":"SettlementDepositsCurrent","receivable_local_name":"SettlementReceivablesCurrent",
        "issuer_namespace_pattern":r"https?://(?:www\.)?fisglobal\.com/\d{8}",
        "treatment":"payment-settlement assets and liabilities remain operating; insurer-funded legal event has no recognized numeric recovery/claim scope",
    }),
    "V": MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"V","cik":"0001403161",
        "mode":"scoped_recovery_operating_overlap_review",
        "issuer_namespace_pattern":r"https?://(?:w{3,4}\.)?visa\.com/\d{8}",
        "reserve_qname":"us-gaap:LitigationReserveCurrent",
        "escrow_local_name":"RestrictedCashAndCashEquivalentsU.S.LitigationEscrow",
        "settlement_payable_local_name":"SettlementPayable","settlement_receivable_local_name":"SettlementReceivable",
        "customer_collateral_asset_local_name":"CustomerCollateralAssets",
        "customer_collateral_liability_local_name":"CustomerCollateralLiabilities",
        "treatment":"net escrow only against the same litigation scope; keep operating settlement balances and matched customer collateral separate",
    }),
})


def litigation_claim_policy(ticker: str) -> dict[str, Any]:
    rule=RULES.get(ticker)
    if rule is None: raise ValueError(f"no litigation claim rule for {ticker!r}")
    return deepcopy(dict(rule))


def _same_policy(actual: Mapping[str,Any],expected: Mapping[str,Any]) -> bool:
    return json.dumps(dict(actual),sort_keys=True,separators=(",",":"))==json.dumps(dict(expected),sort_keys=True,separators=(",",":"))


def _context(policy,structural,controlling,cik,cutoff):
    expected=RULES.get(policy.get("ticker"))
    if expected is None or not _same_policy(policy,expected) or str(cik).zfill(10)!=expected["cik"]:
        raise RuntimeError("litigation claim policy identity/version mismatch")
    accession,period=controlling["accessionNumber"],controlling["reportDate"]
    filed=controlling["filingDate"]
    if (structural.get("source_accession")!=accession
        or (structural.get("report_date") or structural.get("period_end"))!=period
        or not period<=filed<=cutoff):
        raise ValueError("litigation source period/accession/cutoff mismatch")
    date.fromisoformat(period);date.fromisoformat(filed);date.fromisoformat(cutoff)
    facts=structural.get("facts")
    if not isinstance(facts,list): raise ValueError("litigation structural facts are missing")
    return expected,accession,period,facts


def _valid(row,*,policy,accession,period,instant=True,issuer=False):
    if (row.get("source_accession")!=accession or row.get("unit")!="USD"
        or str(row.get("entity_identifier","")).zfill(10)!=policy["cik"]
        or row.get("entity_scheme")!="http://www.sec.gov/CIK"
        or row.get("period_end")!=period or (instant and row.get("period_start") is not None)
        or (not instant and not isinstance(row.get("period_start"),str))
        or isinstance(row.get("value"),bool) or not isinstance(row.get("value"),(int,float))
        or not isfinite(row["value"])):
        raise ValueError("litigation claim identity, period, unit or amount invalid")
    namespace=str(row.get("namespace",""))
    if issuer:
        if not re.fullmatch(str(policy["issuer_namespace_pattern"]),namespace):
            raise ValueError("litigation issuer namespace mismatch")
    elif not _GAAP.fullmatch(namespace):
        raise ValueError("litigation GAAP namespace mismatch")


def _member(row,local_name):
    return any(isinstance(pair,(list,tuple)) and len(pair)==2 and str(pair[1]).rsplit(":",1)[-1]==local_name
               for pair in (row.get("dimensions") or []))


def _one(rows,label):
    if not rows: raise ValueError(f"{label} is missing; absence is not zero")
    values={float(row["value"]) for row in rows}
    if len(values)!=1: raise ValueError(f"{label} conflicts")
    return rows[0],values.pop()


def select_litigation_claim(policy: Mapping[str,Any],structural: Mapping[str,Any],
                            controlling: Mapping[str,Any],cik: str,cutoff: str) -> dict[str,Any]:
    policy,accession,period,facts=_context(policy,structural,controlling,cik,cutoff)
    mode=policy["mode"];sources=[];excluded=[];review=[];claim=None;components={}
    if mode=="scoped_current_accrual":
        reserve_rows=[row for row in facts if row.get("qname")==policy["reserve_qname"]
                      and row.get("period_end")==period and row.get("period_start") is None
                      and dict(row.get("dimensions") or {}).keys()=={policy["reserve_axis"]}
                      and str(dict(row.get("dimensions") or {})[policy["reserve_axis"]]).rsplit(":",1)[-1]==policy["reserve_member"]]
        for row in reserve_rows:_valid(row,policy=policy,accession=accession,period=period)
        reserve_row,reserve=_one(reserve_rows,"current scoped legal/environmental accrual")
        if reserve<0: raise ValueError("current scoped legal/environmental accrual cannot be negative")
        possible=[row for row in facts if row.get("qname")==policy["possible_loss_qname"]
                  and row.get("period_end")==period and row.get("period_start") is None
                  and len(row.get("dimensions") or [])==2
                  and {str(axis).rsplit(":",1)[-1] for axis,_ in row.get("dimensions") or []}
                      =={policy["range_axis_local_name"],policy["reserve_axis"].rsplit(":",1)[-1]}
                  and _member(row,policy["reserve_member"])
                  and any(str(member).rsplit(":",1)[-1] in policy["range_member_local_names"]
                          for _,member in row.get("dimensions") or [])]
        for row in possible:_valid(row,policy=policy,accession=accession,period=period)
        range_members={str(member).rsplit(":",1)[-1] for row in possible for _,member in row.get("dimensions") or []
                       if str(member).rsplit(":",1)[-1] in policy["range_member_local_names"]}
        if len(possible)!=2 or range_members!=set(policy["range_member_local_names"]):
            raise ValueError("current possible-loss range is incomplete")
        environmental=[]
        for local_name in policy["environmental_maximum_local_names"]:
            rows=[row for row in facts if row.get("local_name")==local_name
                  and row.get("period_end")==period and row.get("period_start") is None]
            for row in rows:_valid(row,policy=policy,accession=accession,period=period,issuer=True)
            if not rows: raise ValueError(f"current environmental diagnostic is missing: {local_name}")
            environmental.extend(rows)
        damages=[row for row in facts if row.get("qname")==policy["damages_qname"]
                 and row.get("period_end")==period and isinstance(row.get("period_start"),str)
                 and len(row.get("dimensions") or [])==1
                 and str((row.get("dimensions") or [])[0][0]).rsplit(":",1)[-1]==policy["case_axis_local_name"]
                 and str((row.get("dimensions") or [])[0][1]).rsplit(":",1)[-1]==policy["case_member_local_name"]]
        for row in damages:_valid(row,policy=policy,accession=accession,period=period,instant=False)
        if not damages: raise ValueError("current legal damages flow is missing")
        zeros=[row for row in facts if row.get("qname")==policy["zero_reserve_qname"]
               and row.get("period_end")==period and row.get("period_start") is None
               and len(row.get("dimensions") or [])==1
               and str((row.get("dimensions") or [])[0][0]).rsplit(":",1)[-1]==policy["case_axis_local_name"]
               and str((row.get("dimensions") or [])[0][1]).rsplit(":",1)[-1]==policy["case_member_local_name"]]
        for row in zeros:_valid(row,policy=policy,accession=accession,period=period)
        if not zeros or any(float(row["value"])!=0 for row in zeros):
            raise ValueError("case-level litigation reserve diagnostic is missing or nonzero")
        related={policy["reserve_qname"],policy["possible_loss_qname"],policy["damages_qname"],policy["zero_reserve_qname"]}
        accepted_ids={id(row) for row in (*reserve_rows,*possible,*damages,*zeros)}
        unexpected=[row for row in facts if row.get("qname") in related and row.get("period_end")==period
                    and row.get("source_accession")==accession and id(row) not in accepted_ids
                    and isinstance(row.get("value"),(int,float)) and not isinstance(row.get("value"),bool)
                    and float(row["value"])!=0]
        if unexpected:
            raise ValueError("unexpected positive current litigation/accrual scope requires review")
        sources=[reserve_row];excluded=[*possible,*environmental,*damages,*zeros]
        components={"legal_environmental_accrual":reserve,
            "possible_loss_range":[min(float(row["value"]) for row in possible),max(float(row["value"]) for row in possible)],
            "site_maxima":[float(row["value"]) for row in environmental],
            "damages_awarded_flow":[float(row["value"]) for row in damages]}
        claim=reserve
        formula="current scoped carrying accrual deducted once; possible-loss ranges, maxima, damages flows and case-level zero reserves excluded"
    elif mode=="direct_reserve":
        rows=[row for row in facts if row.get("qname")==policy["reserve_qname"]
              and row.get("period_end")==period and row.get("period_start") is None and not row.get("dimensions")]
        for row in rows:_valid(row,policy=policy,accession=accession,period=period)
        reserve_row,reserve=_one(rows,"current litigation reserve")
        if reserve<0: raise ValueError("litigation reserve cannot be negative")
        sources=[reserve_row];components["litigation_reserve"]=reserve;claim=reserve
        if policy.get("overlap_local_name"):
            overlap=[row for row in facts if row.get("local_name")==policy["overlap_local_name"] and row.get("period_end")==period]
            for row in overlap:_valid(row,policy=policy,accession=accession,period=period,instant=False,issuer=True)
            if not overlap: raise ValueError("litigation cash/noncash overlap evidence is missing")
            excluded.extend(overlap)
        for qname in policy.get("excluded_qnames",()):
            rows=[row for row in facts if row.get("qname")==qname and row.get("period_end")==period and row.get("period_start") is None]
            for row in rows:_valid(row,policy=policy,accession=accession,period=period)
            excluded.extend(rows)
        formula="current recorded litigation reserve deducted once; cash/noncash flows and unrelated insurance reserves remain diagnostics"
    elif mode=="recognized_receivable_net":
        def gaap(qname,label):
            rows=[row for row in facts if row.get("qname")==qname and row.get("period_end")==period
                  and row.get("period_start") is None and not row.get("dimensions")]
            for row in rows:_valid(row,policy=policy,accession=accession,period=period)
            return _one(rows,label)
        reserve_row,reserve=gaap(policy["reserve_qname"],"current litigation reserve")
        receivable_row,receivable=gaap(policy["receivable_qname"],"recognized litigation receivable")
        if min(reserve,receivable)<0 or receivable>reserve:
            raise ValueError("recognized recovery exceeds its scoped litigation reserve")
        claim=reserve-receivable;sources=[reserve_row,receivable_row]
        components={"litigation_reserve":reserve,"recognized_recovery_receivable":receivable,
            "net_litigation_claim":claim}
        formula="current litigation reserve less separately recognized same-scope receivable"
    elif mode=="scoped_reserves_post_period_review":
        total_rows=[row for row in facts if row.get("qname")==policy["reserve_qname"] and row.get("period_end")==period
                    and row.get("period_start") is None and _member(row,policy["reserve_member"])]
        current_rows=[row for row in facts if row.get("qname")==policy["current_reserve_qname"] and row.get("period_end")==period
                      and row.get("period_start") is None and _member(row,policy["reserve_member"])]
        accrual_rows=[row for row in facts if row.get("qname")==policy["other_accrual_qname"] and row.get("period_end")==period
                      and row.get("period_start") is None and _member(row,policy["other_accrual_member"])]
        for row in (*total_rows,*current_rows,*accrual_rows):_valid(row,policy=policy,accession=accession,period=period)
        total_row,total=_one(total_rows,"scoped opioid reserve");current_row,current=_one(current_rows,"current opioid reserve")
        accrual_row,other=_one(accrual_rows,"other current litigation accrual")
        if min(total,current,other)<0 or current>total: raise ValueError("litigation reserve scope is invalid")
        possible=[row for row in facts if row.get("qname")==policy["possible_loss_qname"] and row.get("period_end")==period]
        for row in possible:_valid(row,policy=policy,accession=accession,period=period)
        post=[row for row in facts if row.get("qname")==policy["post_period_payment_qname"] and row.get("period_end","")>period]
        if not post: raise ValueError("post-period legal cash evidence is missing")
        sources=[total_row,accrual_row];excluded=[current_row,*possible,*post]
        components={"opioid_total_reserve":total,"other_current_accrual":other,"opioid_current_portion":current}
        claim=total+other;review.append("post_period_legal_cash_requires_claim_and_cash_rollforward")
        formula="distinct carrying reserves summed once; current portion and historical possible-loss/settlement facts excluded"
    elif mode=="operating_settlement_not_litigation":
        def gaap(qname):
            rows=[row for row in facts if row.get("qname")==qname and row.get("period_end")==period and row.get("period_start") is None and not row.get("dimensions")]
            for row in rows:_valid(row,policy=policy,accession=accession,period=period)
            return _one(rows,qname)
        def custom(local):
            rows=[row for row in facts if row.get("local_name")==local and row.get("period_end")==period and row.get("period_start") is None and not row.get("dimensions")]
            for row in rows:_valid(row,policy=policy,accession=accession,period=period,issuer=True)
            return _one(rows,local)
        asset_row,assets=gaap(policy["settlement_asset_qname"]);liability_row,liabilities=gaap(policy["settlement_liability_qname"])
        deposit_row,deposits=custom(policy["deposit_local_name"]);receivable_row,receivables=custom(policy["receivable_local_name"])
        if assets!=deposits+receivables: raise ValueError("operating settlement assets do not reconcile")
        excluded=[asset_row,liability_row,deposit_row,receivable_row]
        components={"operating_settlement_assets":assets,"operating_settlement_liabilities":liabilities}
        review.append("insurance_funded_legal_event_has_no_recognized_numeric_claim_or_recovery")
        formula="operating payment-settlement balances excluded from litigation; unquantified insured legal event retained for review"
    elif mode=="scoped_recovery_operating_overlap_review":
        def custom(local):
            rows=[row for row in facts if row.get("local_name")==local and row.get("period_end")==period and row.get("period_start") is None and not row.get("dimensions")]
            for row in rows:_valid(row,policy=policy,accession=accession,period=period,issuer=True)
            return _one(rows,local)
        reserve_rows=[row for row in facts if row.get("qname")==policy["reserve_qname"] and row.get("period_end")==period
                      and row.get("period_start") is None and not row.get("dimensions")]
        for row in reserve_rows:_valid(row,policy=policy,accession=accession,period=period)
        reserve_row,reserve=_one(reserve_rows,"current litigation reserve")
        escrow_row,escrow=custom(policy["escrow_local_name"]);payable_row,payable=custom(policy["settlement_payable_local_name"])
        receivable_row,receivable=custom(policy["settlement_receivable_local_name"])
        collateral_asset_row,collateral_asset=custom(policy["customer_collateral_asset_local_name"])
        collateral_liability_row,collateral_liability=custom(policy["customer_collateral_liability_local_name"])
        if collateral_asset!=collateral_liability: raise ValueError("customer collateral asset/liability mismatch")
        reserve_net=reserve-escrow;settlement_net=payable-receivable
        if min(reserve_net,settlement_net)<0: raise ValueError("recovery exceeds its scoped claim")
        claim=reserve_net
        components={"litigation_reserve":reserve,"restricted_litigation_escrow":escrow,
            "net_litigation_reserve":reserve_net,"operating_settlement_payable":payable,
            "operating_settlement_receivable":receivable,"operating_settlement_net":settlement_net,
            "matched_customer_collateral":collateral_asset}
        sources=[reserve_row,escrow_row];excluded=[payable_row,receivable_row,collateral_asset_row,collateral_liability_row]
        review.append("litigation_recovery_and_preferred_conversion_overlap_requires_review")
        formula="litigation reserve less same-scope restricted escrow; operating settlement and customer collateral excluded"
    else: raise RuntimeError("unsupported litigation claim mode")
    return {"status":"review_required" if review else "source_bound","claim_adjustment":None if review else claim,
        "current_carrying_claim":claim,"review_reasons":review,"policy":dict(policy),"source_rows":sources,
        "excluded_rows":excluded,"components":components,"period_end":period,"formula":formula,"treatment":policy["treatment"]}


__all__=["RULES","SCHEMA","VERSION","litigation_claim_policy","select_litigation_claim"]
