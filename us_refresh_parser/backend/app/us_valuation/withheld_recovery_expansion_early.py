"""Disjoint, offline recovery workpapers. Never writes or authorizes a catalog.

Reuse the existing source selectors and residual-income recipe evaluator. A
reported common-owner after-tax benefit may be removed from the matching income
window once; gross cash, a tax-rate reconciliation, and future inventory savings
are not interchangeable with that benefit.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import hashlib
from math import isclose, isfinite
from pathlib import Path
import re
from statistics import median

from lxml import html

from .calculation_recipe import evaluate_recipe


VERSION = "US-WITHHELD-EXPANSION-EARLY-1"
CUTOFF = "2026-10-08"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified_document(record, root, cutoff=CUTOFF):
    path = Path(record["path"])
    path = path if path.is_absolute() else Path(root) / path
    actual = file_sha(path)
    require(actual == record["sha256"], "primary byte hash mismatch: " + str(path))
    filing = record["filing"]
    filed, period = filing["filingDate"], filing["reportDate"]
    require(date.fromisoformat(filed) <= date.fromisoformat(cutoff), "post-cutoff filing")
    require(not period or date.fromisoformat(period) <= date.fromisoformat(cutoff), "post-cutoff period")
    return {
        "path": str(path.resolve()), "sha256": actual,
        "accession": filing["accessionNumber"], "form": filing["form"],
        "filed_date": filed, "periods": {"filing_report_date": period},
        "source_url": record.get("source_url"), "verification": "verified_actual_bytes_and_receipt",
    }


def visible_text(path):
    doc = html.fromstring(Path(path).read_bytes())
    # lxml HTML parsing retains XML prefixes; local-name alone is insufficient.
    for node in list(doc.iter()):
        local = str(node.tag).split(":")[-1].lower()
        if local in {"script", "style", "hidden", "header", "context", "unit"}:
            if node.getparent() is not None:
                node.getparent().remove(node)
    return re.sub(r"[\s\u200b]+", " ", doc.text_content()).strip()


def proof_span(text, phrase):
    start = text.find(phrase)
    require(start >= 0, "required primary disclosure missing: " + phrase)
    return {"phrase": phrase, "start": start, "end": start + len(phrase)}


def extract_gic_net_refund_proof(record, root):
    """Narrow parser binding the explicit net EPS benefit to common owners."""
    evidence = verified_document(record, root)
    text = visible_text(evidence["path"])
    match = re.search(
        r"Year to date 2026 net income per diluted share results include an after tax benefit "
        r"of approximately \$([0-9.]+) million, or \$([0-9.]+) per diluted share, related to the IEEPA tariff refunds", text)
    require(match is not None, "explicit year-to-date net common-owner refund benefit is missing")
    gross = re.search(r"Approximately \$([0-9.]+) million of this refund was recorded as a benefit to cost of sales, "
                      r"\$([0-9.]+) million was recorded to interest income and \$([0-9.]+) million was recorded to inventory", text)
    require(gross is not None, "refund income/interest/inventory separation is missing")
    after_tax = float(Decimal(match.group(1)) * Decimal(1_000_000))
    cogs, interest, inventory = [float(Decimal(x) * Decimal(1_000_000)) for x in gross.groups()]
    require(0 < after_tax <= cogs + interest and inventory >= 0, "invalid disclosed benefit components")
    return {
        "source": evidence, "unit": "USD", "scope": "issuer_after_tax_benefit_basic_common_allocation_unresolved",
        "period_start": "2026-01-01", "period_end": "2026-06-30",
        "after_tax_benefit": after_tax, "reported_precision": "approximately_USD_0.1_million",
        "cogs_benefit": cogs, "interest_benefit": interest,
        "inventory_not_yet_in_income": inventory,
        "primary_spans": [proof_span(text, match.group(0)), proof_span(text, gross.group(0)),
            proof_span(text, "The Company expects that the amount remaining in inventory will sell through during the remainder of 2026.")],
        "ownership_basis": "The issuer reports an approximate net benefit and rounded diluted EPS effect. This does not prove the allocation to the basic two-class common numerator.",
        "same_basic_common_owner_allocation_verified": False,
    }


def remove_net_benefit(ledger, benefit):
    """Reject a gross, wrong-owner, outside-period or already-removed benefit."""
    require(benefit.get("scope") == "parent_common_after_tax_continuing_income", "not an after-tax common-owner benefit")
    require(benefit.get("same_basic_common_owner_allocation_verified") is True, "same basic-common participation allocation is unproved")
    require(benefit.get("unit") == "USD", "benefit must be USD")
    ttm = ledger["current_income_ttm"]
    require(ttm["period_start"] <= benefit["period_start"] <= benefit["period_end"] <= ttm["period_end"], "benefit outside income window")
    require(not ledger.get("removed_net_benefits"), "benefit already removed")
    value = benefit["after_tax_benefit"]
    require(isinstance(value, (float, int)) and not isinstance(value, bool) and isfinite(value) and value > 0, "invalid net benefit")
    sources = {x.get("source_accession") for x in ttm.get("operands", [])}
    require(benefit["source"]["accession"] in sources, "benefit source is not a controlling income operand")
    adjusted = ttm["value"] - value
    require(adjusted > 0, "no positive residual income anchor; do not invent a turnaround")
    result = deepcopy(ledger)
    result["removed_net_benefits"] = [deepcopy(benefit)]
    result["adjusted_income_for_forecast_anchor"] = {
        "value": adjusted, "unit": "USD", "period_start": ttm["period_start"],
        "period_end": ttm["period_end"], "formula": "reported_continuing_common_TTM_minus_disclosed_net_benefit_once",
        "operands": [deepcopy(ttm), deepcopy(benefit)],
        "not_a_complete_normalization_of_all_items": True,
    }
    book = ledger["current_common_capital"]["reported_parent_common_book"]["value"]
    anchor = min(adjusted / book, median(ledger["annual_reported_ROE"]))
    require(anchor > 0, "nonpositive source-derived return")
    result["repaired_ROE_anchor"] = anchor
    return result


def repaired_recipe(original, ledger, benefit):
    require(original.get("ticker") != "GIC", "GIC candidate withdrawn: common-continuing roles, fiscal weeks and refund participation allocation require independent re-review")
    revised = remove_net_benefit(ledger, benefit)
    recipe = deepcopy(original)
    policy = ledger["assumptions"]
    recipe.update(recipe_version=VERSION, evidence_review_date=CUTOFF,
                  private_only=True, staged_recovery_only=True, publication_authorized=False)
    recipe.pop("baseline_version", None)
    anchor = revised["repaired_ROE_anchor"]
    for i, name in enumerate(("bear", "base", "bull")):
        spec = recipe["scenarios"][name]
        require(spec["engine"] == "residual_income" and "equity_floor" not in spec, "unexpected source model/floor")
        expected_book = ledger["current_common_capital"]["reported_parent_common_book"]["value"] / ledger["balance_point_common_shares"]["value"]
        require(isclose(spec["inputs"]["book_value_per_share"], expected_book, abs_tol=1e-12), "common capital/share binding mismatch")
        terminal = anchor * policy["terminal_ROE_fractions"][i]
        spec["inputs"].update(current_roe=anchor * policy["initial_ROE_multipliers"][i],
            terminal_roe=terminal,
            terminal_growth=min(policy["terminal_growth_caps"][i], terminal * policy["terminal_retention_fractions"][i]))
    warnings = [
        "New staged scenario: subtract only the issuer-disclosed approximate after-tax continuing refund benefit from the matching common-income window once.",
        "The remaining reported inventory refund component is retained in evidence. No additional inventory windfall is capitalized in future ROE; its later tax/realization amount is not asserted to be zero or a reported fact.",
        "Forward returns deliberately exclude additional one-time refund gains. Reported book is unchanged; no second refund-cash addition or book deduction.",
        "Eight-year ROE fade, payout, clean surplus and funded terminal growth remain explicit forecast assumptions. This is not a fully normalized sustainable-income or market-calibrated valuation.",
        "Financial reference remains the captured June 30 2026 balance sheet; the October 8 review is not a new financial period or verification of uncaptured later filings.",
        "Independent cohort reconciliation and consumer integration remain required. No admission, automatic refresh authority, activation or publication.",
    ]
    recipe["warnings"] = list(original["warnings"]) + warnings
    recipe["repair_policy"] = {"name": "exclude_disclosed_net_one_off_from_forward_common_return",
        "inventory_runoff": "No incremental future refund windfall capitalized; known amount remains disclosed, not zero-filled",
        "book_adjustment": "none; retain reported common book", "benefit_source": benefit["source"],
        "no_market_prices_or_targets": True}
    revised["scenario_arguments"] = deepcopy(recipe["scenarios"])
    revised["new_repair_policy"] = recipe["repair_policy"]
    return recipe, revised, evaluate_recipe(recipe)


def equal_class_rights(record, root):
    evidence = verified_document(record, root)
    text = visible_text(evidence["path"])
    phrases = ["The Class A common stock and Class B common stock have equal dividend and liquidation rights.",
        "Shares of Class B common stock are convertible into shares of Class A common stock on a one-to-one basis at the option of the holder."]
    return {"source": evidence, "spans": [proof_span(text, x) for x in phrases],
        "resolved_gap": "source proof of common economic rights; voting rights differ",
        "does_not_close_other_claims": True}


def gic_withdrawal_evidence(coverage, root):
    """Recheck the challenge from primary EPS roles; produce no valuation."""
    records = {r["filing"]["accessionNumber"]:r for r in coverage["documents"]}
    annual = records["0001628280-26-012945"]
    quarter = records["0001628280-26-052687"]
    observations = []
    for record, table_index, qname, context_id, start, end in [
        (annual,44,"us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic","c-1","2025-01-01","2025-12-31"),
        (quarter,23,"us-gaap:NetIncomeLossFromContinuingOperationsAvailableToCommonShareholdersBasic","c-1","2026-01-01","2026-06-30"),
        (quarter,23,"us-gaap:NetIncomeLossFromContinuingOperationsAvailableToCommonShareholdersBasic","c-7","2025-01-01","2025-06-30")]:
        source = verified_document(record, root)
        doc = html.fromstring(Path(source["path"]).read_bytes())
        table = doc.xpath("//table")[table_index]
        nodes = list(doc.iter())
        local = lambda n: str(n.tag).split(":")[-1].lower()
        context = next(n for n in nodes if local(n)=="context" and n.get("id")==context_id)
        details = {local(n):(n.text or "").strip() for n in context.iter() if local(n) in {"identifier","startdate","enddate"}}
        require(details == {"identifier":"0000945114","startdate":start,"enddate":end}, "common-income identity/period context mismatch")
        require(not any(local(n)=="explicitmember" for n in context.iter()), "dimensioned common income is not consolidated")
        before_discontinued = True
        hits = []
        for tr in table.xpath("./tr|./tbody/tr"):
            row_text = re.sub(r"\s+", " ", tr.text_content())
            if "Net income from discontinued operations" in row_text:
                before_discontinued = False
            for node in tr.iter():
                if local(node)=="nonfraction" and node.get("name")==qname and node.get("contextref")==context_id:
                    require(before_discontinued and "available to common shareholders" in row_text, "common numerator not bound to continuing EPS section")
                    unit = next(n for n in nodes if local(n)=="unit" and n.get("id")==node.get("unitref"))
                    require(unit.text_content().strip()=="iso4217:USD", "common income unit is not USD")
                    value = Decimal(node.text_content().replace(",", "").strip()) * Decimal(10)**int(node.get("scale","0"))
                    if node.get("sign")=="-": value = -value
                    hits.append({"value":float(value),"unit":"USD","qname":qname,"context_id":context_id,
                        "period_start":start,"period_end":end,"scope":"basic_common_continuing_income",
                        "table_index_zero_based":table_index,"source":source,"source_row":row_text,
                        "continuing_section_before_discontinued_verified":True})
        require(len(hits)==1,"ambiguous primary common continuing numerator")
        observations.extend(hits)
    annual_text = visible_text(verified_document(annual,root)["path"])
    quarter_text = visible_text(verified_document(quarter,root)["path"])
    require("2025 included 53 weeks" in annual_text and "first six months of both 2026 and 2025 included 26 weeks" in quarter_text,"fiscal-week proof absent")
    require("January 3, 2026" in annual_text and "July 4, 2026 and June 28, 2025" in quarter_text,"actual fiscal dates absent")
    benefit = extract_gic_net_refund_proof(quarter,root)
    total = Decimal(str(observations[0]["value"])) + Decimal(str(observations[1]["value"])) - Decimal(str(observations[2]["value"]))
    return {"decision":"withdraw_repaired_candidate","claim_status":"verified_primary_role_and_fiscal_basis",
        "common_income_operands":observations,"reported_common_continuing_bridge_USD":float(total),
        "fiscal_weeks":53,"fiscal_duration_days":371,"XBRL_calendar_labels_are_presentation_dates":True,
        "fiscal_week_formula":"53 + 26 - 26 = 53",
        "actual_fiscal_ends":{"annual":"2026-01-03","current_YTD":"2026-07-04","prior_YTD":"2025-06-28"},
        "refund_proof":benefit,"same_basic_common_refund_allocation_proven":False,
        "adjusted_common_income":None,"replacement_range":None,
        "reason":"The corrected 84.7M basic-common fiscal bridge is sourceable. The 16.4M approximate refund benefit is not separately allocated to that two-class common numerator; no allocation or normalized return is invented.",
        "shared_change_proposal":"Before any future shared owner_income use, bind the selected numerator's actual table role as total versus continuing and its common versus pre-participation scope. Subtract discontinued amounts only from a proven total numerator of identical owner scope; preserve stated fiscal-week duration. No shared module edited."}
