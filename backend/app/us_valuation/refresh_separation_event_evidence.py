"""Hash-bound separation agreements, pro forma financials and current guidance."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import re

from .catalog import canonical_json_bytes, sha256_bytes
from .refresh_narrative_evidence import _VisibleText

VERSION = "FINSIGHT-SEPARATION-EVENT-EVIDENCE-WG37-3"
RULES = {"HON": {"version": VERSION, "ticker": "HON", "cik": "0000773840",
    "mechanism": "separation_pro_forma_and_current_guidance",
    "required_roles": ["separation_agreement", "trademark_agreement", "pro_forma_financials", "current_earnings_release"]}}


def separation_event_policy(ticker):
    return deepcopy(RULES[ticker])


def _path(root, relative):
    if not isinstance(relative,str) or Path(relative).is_absolute():raise ValueError("separation event relative path required")
    path=(Path(root)/relative).resolve();root=Path(root).resolve()
    if not path.is_relative_to(root) or not path.is_file():raise ValueError("separation event source missing or outside root")
    return path


def _visible(path):
    raw=path.read_bytes();parser=_VisibleText();parser.feed(raw.decode("utf-8"));parser.close();return raw,parser.text


def _number(token):
    token=token.replace("$","").replace(",","").strip();negative=token.startswith("(") and token.endswith(")")
    token=token.strip("() ")
    return (-1 if negative else 1)*float(token)*1_000_000


def _row(section,label,next_label,expected):
    starts=[m for m in re.finditer(re.escape(label),section,re.I)
            if section[max(0,m.start()-3):m.start()].lower()!="of "
            and not section[m.end():m.end()+7].lower().startswith(" margin")]
    if len(starts)!=1:raise ValueError("separation event table row missing or ambiguous: "+label)
    end=len(section) if not next_label else section.find(next_label,starts[0].end())
    if end<0:raise ValueError("separation event table row boundary missing: "+label)
    excerpt=section[starts[0].end():end];excerpt=re.sub(r"\([a-z](?:\)\([a-z])?\)","",excerpt)
    tokens=re.findall(r"—|\(?[0-9][0-9,.]*\)?",excerpt)
    if len(tokens)!=expected:raise ValueError("separation event table row cardinality changed: "+label)
    return [0.0 if token=="—" else _number(token) for token in tokens]


def _section(text,start,end):
    matches=list(re.finditer(start,text,re.I));candidates=[]
    for match in matches:
        finish=text.find(end,match.end())
        if finish>=0:candidates.append((text[match.start():finish],match.start(),finish))
    if len(candidates)!=1:raise ValueError("separation event section missing or ambiguous: "+start)
    return candidates[0]


def _term(section,offset,name,pattern,value,unit,source):
    matches=list(re.finditer(pattern,section,re.I))
    if len(matches)!=1:raise ValueError("separation event term missing or ambiguous: "+name)
    match=matches[0];excerpt=section[match.start():match.end()]
    return {"name":name,"value":value,"unit":unit,"source_role":source,
        "locator":{"normalized_text_start":offset+match.start(),"normalized_text_end":offset+match.end()},
        "excerpt_sha256":sha256(excerpt.encode()).hexdigest()}


def extract_separation_event_evidence(ticker,capture_report_path,*,source_root,cutoff):
    policy=RULES[ticker];root=Path(source_root).resolve();report_path=_path(root,str(capture_report_path))
    report_raw=report_path.read_bytes();report=json.loads(report_raw);capture_root=report_path.parent
    if (report.get("schema_version")!="FINSIGHT-SELECTED-SEC-FILINGS-WG37-2" or report.get("cutoff")!=cutoff
        or report.get("attempted")!=2 or report.get("captured")!=2 or report.get("economic_validation") is not False):
        raise ValueError("separation event capture contract mismatch")
    expected_accessions={"0000773840-26-000084","0000773840-26-000120"};documents={};sources=[]
    for case in report["cases"]:
        filing=case["filing"]
        if (case.get("ticker")!=ticker or str(case.get("cik","")).zfill(10)!=policy["cik"] or case.get("status")!="captured"
            or filing.get("accession") not in expected_accessions or filing.get("form")!="8-K"
            or not filing["report_date"]<=filing["filed_date"]<=cutoff):raise ValueError("separation event filing identity/cutoff mismatch")
        for row in case["documents"]:
            if row.get("directly_linked_from_primary") is not True:raise ValueError("separation event document is not directly linked")
            path=_path(capture_root,row["path"]);raw=path.read_bytes()
            if len(raw)!=row["byte_count"] or sha256_bytes(raw)!=row["sha256"]:raise ValueError("separation event document hash/size mismatch")
            if row["name"] in documents:raise ValueError("separation event duplicate document name")
            documents[row["name"]]=(path,raw,row,filing)
            sources.append({"filing":filing,"name":row["name"],"path":path.relative_to(root).as_posix(),"sha256":row["sha256"],"byte_count":row["byte_count"]})
    if {case["filing"]["accession"] for case in report["cases"]}!=expected_accessions:raise ValueError("separation event filing set incomplete")
    def role(fragment):
        matches=[value for name,value in documents.items() if fragment in name]
        if len(matches)!=1:raise ValueError("separation event required role missing/ambiguous: "+fragment)
        path,raw,row,filing=matches[0];parser=_VisibleText();parser.feed(raw.decode("utf-8"));parser.close();return path,parser.text,filing
    _,proforma,pf_filing=role("unauditedproform");_,earnings,earn_filing=role("q22026earningsre")
    _,agreement,sep_filing=role("separationanddis");_,trademark,_=role("trademarklicens")

    balance,bs,be=_section(proforma,r"UNAUDITED PRO FORMA CONDENSED CONSOLIDATED BALANCE SHEET As of March 31, 2026 March 31, 2026","UNAUDITED PRO FORMA CONDENSED CONSOLIDATED STATEMENT OF OPERATIONS")
    balance_rows={
        "cash":_row(balance,"Cash and cash equivalents","Short-term investments",4),
        "short_investments":_row(balance,"Short-term investments","Accounts receivable",4),
        "total_assets":_row(balance,"Total assets","LIABILITIES",4),
        "short_borrowings":_row(balance,"Commercial paper and other short-term borrowings","Current maturities of long-term debt",4),
        "current_debt":_row(balance,"Current maturities of long-term debt","Accrued liabilities",4),
        "long_debt":_row(balance,"Long-term debt","Deferred income taxes",4),
        "parent_equity":_row(balance,"Total Honeywell shareowners’ equity","Noncontrolling interest",4),
        "nci":_row(balance,"Noncontrolling interest","Total shareowners' equity",4),
        "total_equity":_row(balance,"Total shareowners' equity","Total liabilities and shareowners' equity",4),
        "liabilities_and_equity":_row(balance,"Total liabilities and shareowners' equity","",4),
    }
    for name,row in balance_rows.items():
        if abs(sum(row[:3])-row[3])>.01:raise ValueError("pro forma balance row does not reconcile: "+name)
    proforma_balance={name:row[-1] for name,row in balance_rows.items()}
    if proforma_balance["total_assets"]!=proforma_balance["liabilities_and_equity"]:raise ValueError("pro forma balance sheet does not balance")
    proforma_balance["cash_and_short_investments"]=proforma_balance["cash"]+proforma_balance["short_investments"]
    proforma_balance["interest_bearing_debt"]=proforma_balance["short_borrowings"]+proforma_balance["current_debt"]+proforma_balance["long_debt"]

    headings=[("q1_2026",r"For the Three Months Ended March 31, 2026 Three months ended March 31, 2026","For the Year Ended December 31, 2025",4),
        ("fy2025",r"For the Year Ended December 31, 2025 Year ended December 31, 2025","For the Year Ended December 31, 2024",4),
        ("fy2024",r"For the Year Ended December 31, 2024 Year ended December 31, 2024","For the Year Ended December 31, 2023",3),
        ("fy2023",r"For the Year Ended December 31, 2023 Year ended December 31, 2023","NOTES TO UNAUDITED",3)]
    history={}
    for name,start,end,count in headings:
        section,_,_=_section(proforma,start,end)
        rows={"revenue":_row(section,"Net sales","Costs, expenses and other",count),
              "interest":_row(section,"Interest and other financial charges","Total costs, expenses and other",count),
              "parent_net_income":_row(section,"Net income from continuing operations attributable to Honeywell","Weighted average shares outstanding",count)}
        for field,row in rows.items():
            if abs(sum(row[:-1])-row[-1])>.01:raise ValueError("pro forma income row does not reconcile: "+name+field)
        history[name]={field:row[-1] for field,row in rows.items()}
    notes,ns,ne=_section(proforma,r"NOTES TO UNAUDITED PRO FORMA","$") if False else (proforma[proforma.index("NOTES TO UNAUDITED"):],proforma.index("NOTES TO UNAUDITED"),len(proforma))
    note_terms=[]
    note_specs=(
        ("aerospace_retained_cash",r"expectation that \$(?P<a>[0-9,.]+) billion will be retained by Aerospace",lambda m:float(m["a"])*1e9,"USD_estimate"),
        ("additional_nonrecurring_cost_accrual",r"additional estimated nonrecurring costs of \$(?P<a>[0-9,.]+) million",lambda m:float(m["a"])*1e6,"USD_estimate"),
        ("distributed_notes",r"distributed \$(?P<a>[0-9,.]+) billion of the senior unsecured notes",lambda m:float(m["a"])*1e9,"USD"),
        ("distributed_cash_proceeds",r"and \$(?P<a>[0-9,.]+) billion of cash proceeds",lambda m:float(m["a"])*1e9,"USD"),
        ("debt_repayment",r"used \$(?P<a>[0-9,.]+) billion related to such distributions to repay third-party debt",lambda m:float(m["a"])*1e9,"USD"),
        ("annual_interest_reduction",r"Interest expense was reduced by an estimated \$[0-9,.]+ million and \$(?P<a>[0-9,.]+) million .*? year ended December 31, 2025",lambda m:float(m["a"])*1e6,"USD_estimate"),
    )
    for name,pattern,convert,unit in note_specs:
        matches=list(re.finditer(pattern,notes,re.I))
        if len(matches)!=1:raise ValueError("pro forma note term missing/ambiguous: "+name)
        note_terms.append(_term(notes,ns,name,pattern,convert(matches[0]),unit,"pro_forma_notes"))

    table2,t2s,t2e=_section(earnings,r"Table 2: Summary of Honeywell Technologies Financial Results","Table 3:")
    current_quarter={"revenue":_row(table2,"Sales","Organic",3)[0],"operating_income":_row(table2,"Operating Income","Operating Income Margin",3)[0],
        "operating_cash_flow":_row(table2,"Cash Flow from Operations - Continuing Operations","Free Cash Flow",3)[0],
        "adjusted_free_cash_flow":_row(table2,"Free Cash Flow 1,4","* Results refer",3)[0]}
    cash_reconciliation,crs,cre=_section(earnings,r"Reconciliation of Cash Provided by Operating Activities to Free Cash Flow \(Unaudited\)","We define free cash flow")
    q2_patterns={"capital_expenditures":r"Capital expenditures \([0-9,.]+\) \([0-9,.]+\) \((?P<value>[0-9,.]+)\)",
        "separation_cost_payment_addback":r"Spin-off and separation-related cost payments [0-9,.]+ [0-9,.]+ (?P<value>[0-9,.]+)",
        "quantinuum_cash_addback":r"Quantinuum [0-9,.]+ — (?P<value>[0-9,.]+)"}
    for name,pattern in q2_patterns.items():
        matches=list(re.finditer(pattern,cash_reconciliation,re.I))
        if len(matches)!=1:raise ValueError("current quarter cash reconciliation missing/ambiguous: "+name)
        current_quarter[name]=float(matches[0]["value"].replace(",",""))*1e6
    table4,t4s,t4e=_section(earnings,r"Table 4: Honeywell Technologies Full-Year 2026 Guidance","2026 Outlook")
    guidance_patterns={
        "revenue_range":r"Sales \$[0-9.]+B - \$[0-9.]+B \$(?P<low>[0-9.]+)B - \$(?P<high>[0-9.]+)B",
        "operating_cash_flow":r"Operating Cash Flow ~\$[0-9.]+B ~\$(?P<value>[0-9.]+)B",
        "adjusted_free_cash_flow":r"Free Cash Flow 4 ~\$[0-9.]+B ~\$(?P<value>[0-9.]+)B",
    }
    guidance={}
    for name,pattern in guidance_patterns.items():
        matches=list(re.finditer(pattern,table4,re.I))
        if len(matches)!=1:raise ValueError("current guidance missing/ambiguous: "+name)
        m=matches[0];guidance[name]=([float(m["low"])*1e9,float(m["high"])*1e9] if "low" in m.groupdict() else float(m["value"])*1e9)
    guidance["includes_johnson_matthey_and_expected_divestitures"]=bool(re.search(r"Guidance incorporates expected results for the acquisition of Johnson Matthey.*?expected close of the .*? divestitures",earnings,re.I))
    guidance["gaap_reconciliation_complete"]=False
    cash_range=re.search(r"Cash provided by operating activities from continuing operations .*?\$(?P<low>[0-9.]+) - \$(?P<high>[0-9.]+) Capital expenditures .*?~\((?P<capex>[0-9.]+)\) Spin-off and separation-related cost payments .*?~(?P<separation>[0-9.]+) Quantinuum .*?~(?P<quantinuum>[0-9.]+) Free cash flow .*?~(?P<fcf_low>[0-9.]+) - \$(?P<fcf_high>[0-9.]+)",cash_reconciliation,re.I)
    if not cash_range:raise ValueError("current cash guidance reconciliation missing")
    guidance.update(operating_cash_flow_range=[float(cash_range["low"])*1e9,float(cash_range["high"])*1e9],
        capital_expenditures=float(cash_range["capex"])*1e9,separation_cost_payment_addback=float(cash_range["separation"])*1e9,
        quantinuum_cash_addback=float(cash_range["quantinuum"])*1e9,
        adjusted_free_cash_flow_range=[float(cash_range["fcf_low"])*1e9,float(cash_range["fcf_high"])*1e9])
    calculated=[value-guidance["capital_expenditures"]+guidance["separation_cost_payment_addback"]+guidance["quantinuum_cash_addback"] for value in guidance["operating_cash_flow_range"]]
    if calculated!=guidance["adjusted_free_cash_flow_range"]:raise ValueError("current cash guidance reconciliation does not add")
    if (current_quarter["operating_cash_flow"]-current_quarter["capital_expenditures"]
        +current_quarter["separation_cost_payment_addback"]+current_quarter["quantinuum_cash_addback"]
        !=current_quarter["adjusted_free_cash_flow"]):
        raise ValueError("current quarter continuing free cash flow reconciliation does not add")
    fcf_definition=bool(re.search(r"free cash flow adjusts for capital expenditures, spin-off and separation-related cost payments, and cash flows attributable to Quantinuum",earnings,re.I))
    if not fcf_definition or not guidance["includes_johnson_matthey_and_expected_divestitures"]:raise ValueError("current guidance economic scope incomplete")

    agreement_terms=[]
    agreement_specs=(("intergroup_accounts",r"any and all intercompany receivables, payables, loans and balances.*?shall, prior to the Effective Time, be satisfied and/or settled in full.*?or otherwise canceled and terminated or extinguished", "settled_cash_dividend_contribution_or_extinguished_amount_undisclosed"),
        ("aerospace_cash_assets",r"all Cash and Cash Equivalents, notes, interest receivables and other financial assets owned by any member of the Aerospace Group", "transferred_by_group_ownership_amount_in_schedules_not_disclosed"))
    for name,pattern,value in agreement_specs:agreement_terms.append(_term(agreement,0,name,pattern,value,"classification","separation_agreement"))
    cash_distribution_pattern=r"“ Aerospace Cash Distribution ” shall mean the cash distribution in the aggregate amount of \(i\) \$(?P<fixed>[0-9.]+) billion plus \(ii\) up to an additional \$(?P<maximum>[0-9.]+) billion .*? exact dollar amount thereof to be determined"
    cash_matches=list(re.finditer(cash_distribution_pattern,agreement,re.I))
    if len(cash_matches)!=1:raise ValueError("separation cash distribution term missing/ambiguous")
    agreement_terms.append(_term(agreement,0,"aerospace_cash_distribution",cash_distribution_pattern,
        {"fixed":float(cash_matches[0]["fixed"])*1e9,"additional_maximum":float(cash_matches[0]["maximum"])*1e9,"exact_total":None},
        "USD_contract_range_not_current_cash","separation_agreement"))
    trademark_pattern=r"license fees totaling \$1\.125 billion.*?upfront payment of \$18\.75 million.*?fifty-nine \(59\) equal consecutive monthly payments of \$18\.75 million"
    trademark_terms=[_term(trademark,0,"trademark_fixed_schedule",trademark_pattern,{"total":1.125e9,"upfront":18.75e6,"monthly_count":59,"monthly":18.75e6},"USD_schedule","trademark_agreement")]

    result={"version":VERSION,"ticker":ticker,"cutoff":cutoff,"capture_report_path":report_path.relative_to(root).as_posix(),
        "capture_report_sha256":sha256_bytes(report_raw),"sources":sources,"pro_forma_balance":proforma_balance,"pro_forma_history":history,
        "pro_forma_notes":note_terms,"current_quarter_continuing_parent":{**current_quarter,"scope":"management_continuing_parent_excluding_aerospace_with_perimeter_corporate_and_intracompany_adjustments"},"management_guidance":guidance,
        "agreement_terms":agreement_terms+trademark_terms,"status":"continuing_history_and_guidance_bound_current_bridge_review",
        "continuing_fcff":None,"post_close_cash_and_investments":None,"post_close_debt":None,"post_close_nci":None,
        "acquired_fcff":None,"divestiture_proceeds":None,"claim_adjustment":None,"numeric_successor_issued":False,
        "review_reasons":["pro_forma_balance_is_march_not_post_close_current_state","pro_forma_has_no_cash_flow_statement",
            "management_free_cash_flow_is_adjusted_and_not_enterprise_fcff","guidance_combines_acquisition_and_expected_divestitures",
            "johnson_matthey_funding_post_close_balances_and_acquired_fcff_unavailable","separation_schedules_with_numeric_asset_liability_allocations_omitted",
            "intercompany_settlement_amounts_and_eliminations_unavailable","current_trademark_receipts_tax_and_cash_overlap_unreconciled",
            "pro_forma_share_basis_not_current_split_adjusted_denominator"]}
    result["receipt_sha256"]=sha256_bytes(canonical_json_bytes(result));return result


def validate_separation_event_evidence(receipt,*,source_root,cutoff):
    if receipt.get("version")!=VERSION or receipt.get("cutoff")!=cutoff:raise ValueError("separation event receipt version/cutoff mismatch")
    rebuilt=extract_separation_event_evidence(receipt["ticker"],receipt["capture_report_path"],source_root=source_root,cutoff=cutoff)
    if canonical_json_bytes(receipt)!=canonical_json_bytes(rebuilt):raise ValueError("separation event evidence/source drift")
    return rebuilt


def bind_separation_event_evidence(policy,receipt,current_scope,recipe,*,source_root,cutoff):
    if policy!=RULES.get(policy.get("ticker")):raise ValueError("separation event policy identity/version mismatch")
    evidence=validate_separation_event_evidence(receipt,source_root=source_root,cutoff=cutoff)
    if current_scope.get("ticker")!=policy["ticker"] or current_scope.get("numeric_successor_issued") is not False or recipe.get("ticker")!=policy["ticker"]:
        raise ValueError("separation event/current scope identity mismatch")
    if current_scope["terms"]["reported_shares_already_adjusted"] is not True:raise ValueError("current share restatement scope unresolved")
    return {"version":VERSION,"ticker":policy["ticker"],"status":"pro_forma_and_guidance_verified_current_bridge_still_required",
        "event_receipt_sha256":evidence["receipt_sha256"],"pro_forma_balance":evidence["pro_forma_balance"],
        "pro_forma_history":evidence["pro_forma_history"],"current_quarter_continuing_parent":evidence["current_quarter_continuing_parent"],
        "management_guidance":evidence["management_guidance"],"continuing_fcff":None,"post_close_cash_and_investments":None,
        "post_close_debt":None,"post_close_nci":None,"acquired_fcff":None,"claim_adjustment":None,
        "historical_range_only":current_scope["historical_range_only"],"numeric_successor_issued":False,
        "review_reasons":evidence["review_reasons"]}
