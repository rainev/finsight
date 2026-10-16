"""Disjoint stage-only source bindings. No catalog or public-policy overrides.

Table roles are required in addition to XBRL names: a common-component axis is
not itself proof that a number is physically outstanding. Unknown legal claims
are deliberately outside the reported common-GAAP accounting object.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import importlib.util
import json
from math import isfinite
from pathlib import Path
import re
from statistics import median

from . import expansion_initial_common as shared
from .calculation_recipe import evaluate_recipe

VERSION = "US-WITHHELD-EXPANSION-LATE-SOURCE-BINDING-1"
TICKERS = tuple("AAON ACHC ATKR CCK COLM EHC GFF HALO HNI MSA OLN OMCL SANM VMI".split())
CUTOFF = "2026-10-08"


def require(ok, reason):
    if not ok:
        raise shared.InitialInputGap(reason)


def fact_ref(fact):
    return {k: deepcopy(fact.get(k)) for k in (
        "qname", "namespace", "value", "unit", "period_start", "period_end",
        "dimensions", "context_id", "decimals", "source_accession", "form",
        "filed_date", "document_sha256", "source_url", "DOM_element_index", "table_index")}


def eligible(fact, *, accession, end, unit):
    return (fact.get("source_accession") == accession and fact.get("period_end") == end
            and fact.get("period_start") is None and fact.get("unit") == unit
            and fact.get("filed_date", "9999") <= CUTOFF
            and re.fullmatch(r"https?://fasb.org/us-gaap/20\d{2}", fact.get("namespace") or "") is not None
            and isinstance(fact.get("value"), (int, float))
            and not isinstance(fact.get("value"), bool) and isfinite(fact["value"]))


def table_text(table):
    return " ".join(" ".join(row) for row in table["rows"])


def qualified_outstanding(facts, tables, *, accession, end):
    """Permit a common-component axis only with an explicit outstanding column.

    Issued shares, treasury shares, weighted averages and later cover dates are
    not substitutes. A separate treasury-share column in the same table requires
    further reconciliation and is rejected by this narrow source primitive.
    """
    by_index = {t["table_index"]: t for t in tables}
    hits = []
    for f in facts:
        if not eligible(f, accession=accession, end=end, unit="shares"):
            continue
        if f["qname"] != "us-gaap:CommonStockSharesOutstanding":
            continue
        dims = f.get("dimensions") or []
        if dims not in ([], [["us-gaap:StatementEquityComponentsAxis", "us-gaap:CommonStockMember"]]):
            continue
        table = by_index.get(f.get("table_index"))
        if table is None:
            continue
        if (table.get("document_sha256") != f.get("document_sha256")
                or table.get("filing", {}).get("accessionNumber") != accession):
            continue
        text = table_text(table)
        if re.search(r"Treasury Shares|Number of Treasury", text, re.I):
            continue
        if re.search(r"Number of Common Shares Outstanding|issued and outstanding|Common shares outstanding", text, re.I):
            hits.append(f)
    require(hits, "no exact balance-date outstanding common-share table binding")
    f = shared.unique(hits, "table-bound balance-date outstanding common shares")
    require(f["value"] > 0, "nonpositive physical common shares")
    return {"value": f["value"], "mode": "complete_primary_table_common_outstanding_column",
            "operands": [fact_ref(f)], "table_index": f["table_index"],
            "fully_diluted": False, "later_cover_or_weighted_average_used": False}


def aaon_common_bridge(document):
    """Bind a wholly owned issuer's complete reported common capital schedule.

    No missing NCI/preferred fact is assigned zero. The preferred no-issuance
    statement and all operating subsidiaries' ownership statement are explicit
    source observations. Unrecorded legal preferences remain unknown.
    """
    receipt = document["receipt"]
    filing = receipt["filing"]
    end, acc = filing["reportDate"], filing["accessionNumber"]
    require(filing["filingDate"] <= CUTOFF and end <= CUTOFF, "source after cutoff")
    matches = [t for t in document["tables"] if re.search(
        r"Preferred stock.*no shares issued.*Common stock.*issued and outstanding.*Additional paid.in capital.*Retained earnings.*Total stockholders",
        table_text(t), re.I)]
    require(len(matches) == 1, "complete preferred/common balance table is ambiguous or absent")
    table = matches[0]
    ownership = [s for s in document["risk_snippets"] if re.search(
        r"operating subsidiaries, all of which are wholly.owned", s["text"], re.I)]
    require(ownership, "explicit wholly-owned operating subsidiary scope is missing")
    require(not re.search(r"noncontrolling", table_text(table), re.I),
            "outside-owner row requires an explicit allocation")
    facts = [f for f in document["facts"] if eligible(f, accession=acc, end=end, unit="USD")]
    members = ("CommonStockMember", "AdditionalPaidInCapitalMember", "RetainedEarningsMember")
    components = []
    for member in members:
        hits = [f for f in facts if f.get("dimensions") == [["us-gaap:StatementEquityComponentsAxis", "us-gaap:"+member]]
                and f["qname"] == "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
        components.append(fact_ref(shared.unique(hits, member)))
    totals = [f for f in facts if not f.get("dimensions") and f["table_index"] == table["table_index"]
              and f["qname"] == "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
    total = fact_ref(shared.unique(totals, "complete balance table total"))
    require(sum(Decimal(str(f["value"])) for f in components) == Decimal(str(total["value"])),
            "complete common-component sum does not equal reported equity")
    share = qualified_outstanding(document["facts"], document["tables"], accession=acc, end=end)
    return {"schema_version": VERSION, "reported_common_book": total["value"],
            "reported_total": total, "common_components": components,
            "complete_balance_table": table, "ownership_statement": ownership,
            "shares": share, "legal_absence_of_other_claims": "unknown",
            "new_repair": "Complete primary balance/equity tables and explicit subsidiary/no-preferred-issuance statements bind the previously inclusive equity tag to reported parent common capital; no new numerical assumptions.",
            "Arelle_validated": False}


def new_binding_candidate(prior_artifact, prior_recipe, prior_result, bridge):
    """Preserve economics and add a newly evidenced source gate, not authority."""
    recipe = deepcopy(prior_recipe)
    artifact = deepcopy(prior_artifact)
    replay = evaluate_recipe(recipe)
    require(replay["range"] == prior_result["range"], "prior private recipe no longer replays exactly")
    for s in recipe["scenarios"].values():
        require(s["inputs"]["book_value_per_share"] == bridge["reported_common_book"] / bridge["shares"]["value"],
                "new common source binding does not reconcile to preserved recipe")
    artifact["recovery_candidate"] = {"version": VERSION, "new_repair": bridge["new_repair"],
        "stage_only": True, "new_economic_estimate": False,
        "new_source_binding": True, "publication_authorized": False,
        "integration_verified": False, "legal_claims": "unknown beyond reported carrying allocation"}
    artifact["private_review_only"] = True
    return artifact, recipe, replay


def rebind_explicit_common_continuing_income(ledger, recipe, facts, receipts):
    """Use the reported basic-common continuing role, without subtracting it again."""
    revised, updated = deepcopy(ledger), deepcopy(recipe)
    names = ("NetIncomeLossFromContinuingOperationsAvailableToCommonShareholdersBasic",)
    annual = [shared.flow(facts, names, f["period_end"], receipts,
                          "explicit_basic_common_continuing_income", annual=True,
                          start=f["period_start"]) for f in ledger["annual_common_income"]]
    prior_ttm = ledger["current_income_ttm"]
    operands = [annual[-1]] + [shared.flow(facts, names, f["period_end"], receipts,
                "explicit_basic_common_continuing_income", acc=f["source_accession"],
                start=f["period_start"]) for f in prior_ttm["operands"][1:]]
    ttm = operands[0]["value"] + operands[1]["value"] - operands[2]["value"]
    roes = [f["value"] / ((book["opening"]["value"] + book["closing"]["value"]) / 2)
            for f, book in zip(annual, ledger["annual_reported_parent_book"])]
    book = ledger["current_common_capital"]["reported_parent_common_book"]["value"]
    anchor = min(ttm / book, median(roes))
    require(anchor > 0, "explicit common continuing return is nonpositive")
    revised["annual_common_income"] = annual
    revised["current_income_ttm"] = {**deepcopy(prior_ttm), "value": ttm, "operands": operands,
        "income_scope": "basic_common_continuing_after_participating_security_allocation"}
    revised["annual_reported_ROE"], revised["normalized_ROE"] = roes, anchor
    policy = revised["assumptions"]
    distributions = revised["reported_common_distributions"]
    if distributions.get("status") == "reported_and_fiscal_TTM":
        ratio = sum(f["value"] for f in distributions["annual"]) / sum(f["value"] for f in annual)
        distributions["five_year_cash_dividend_to_common_income"] = ratio
        distributions["raw_TTM_cash_dividend_to_common_income"] = distributions["current_TTM"]["value"] / ttm
        if policy.get("future_payout_basis", "").startswith("future assumption using observed"):
            require(0 <= ratio <= 1, "revised observed payout is outside supported funding bounds")
            policy["corrected_observed_five_year_ratio"] = ratio
            policy["future_payout_basis"] = "Fixed prior forecast payout retained by explicit user instruction; no longer described as the exact corrected five-year observed ratio."
    for i, name in enumerate(("bear", "base", "bull")):
        terminal = anchor * policy["terminal_ROE_fractions"][i]
        updated["scenarios"][name]["inputs"].update(
            current_roe=anchor * policy["initial_ROE_multipliers"][i],
            terminal_roe=terminal,
            terminal_growth=min(policy["terminal_growth_caps"][i], terminal * policy["terminal_retention_fractions"][i]),
            current_payout_ratio=policy["future_payout_ratio"])
    updated.pop("baseline_version", None)
    revised["scenario_arguments"] = deepcopy(updated["scenarios"])
    revised["new_income_source_binding"] = "Direct basic-common continuing numerator replaces common net income minus differently allocated discontinued parent income. No extra discontinued subtraction."
    return revised, updated


def contract_metadata(artifact, recipe, submissions, classification, source, binding_sha):
    """Repair factual metadata while retaining the private acceptance boundary."""
    a, r = deepcopy(artifact), deepcopy(recipe)
    require(str(submissions["cik"]).zfill(10) == a["issuer"]["cik"], "submission issuer mismatch")
    a["issuer"] = deepcopy(classification)
    for key in ("valuation_policy", "verified_zero_bridge_fields", "governed_bridge_fields", "requires_segment_forecast"):
        a["issuer"].pop(key, None)
    a["source_financial_statement"] = {
        "form": source["form"], "period_end": source["period_end"], "filed_date": source["filed_date"],
        "accession": source["accession_number"], "url": source["source_url"],
        "note": "Frozen financial statement used; not a claim of latest disclosure completeness."}
    old = "NetIncomeLoss follows the primary FASB parent-attribution tag semantics; ProfitLoss is not used as a common-owner fallback and no NCI is subtracted again."
    new = "Income is bound to explicit parent/common statement roles; consolidated all-owner profit is not substituted and NCI is not subtracted twice."
    require(old in a["review"]["warnings"], "expected historical owner warning missing")
    a["review"]["warnings"] = [new if w == old else w for w in a["review"]["warnings"]]
    r["warnings"] = [new if w == old else w for w in r["warnings"]]
    extras = [
        "This inactive source-bound candidate uses ordinary public-contract metadata; publication, activation and automatic refresh remain unauthorized.",
        "Native classifier scores describe routing metadata, not valuation confidence. An unrated manual description has no invented numerical confidence.",
        "Accounting adjustment uncertainty is unquantified. No zero accounting-impact ratio or High accounting label is asserted; source and model remain Low.",
    ]
    a["review"]["warnings"] += extras
    r["warnings"] += extras
    a["model_version"] = VERSION
    a["model_policy"] = {"primary": "residual_income", "supporting": [],
        "reason": "Source-bound reported common-GAAP equity scenario under explicit analyst assumptions; distinct from native SIC default FCFF policy and not a bank or sustainable cash valuation."}
    a["public_assumptions"] = {"forecast_policy_version": VERSION, "forecast_mode": "residual_income_exact",
        "source_policy_binding_sha256": binding_sha, "forecast_years": r["scenarios"]["base"]["inputs"]["years"],
        "normalization_basis": "source-bound common-GAAP accounting scope; legal claims beyond that scope remain unknown",
        "discount_calibration_type": "analyst_assumptions_not_market_calibrated"}
    values = evaluate_recipe(r)["range"]
    a["scenario_range"].update(values)
    a["models"]["residual_income"]["intrinsic_value_per_share"] = values["base"]
    for n, k in (("bear", "low"), ("base", "base"), ("bull", "high")):
        a["scenarios"][n]["residual_income"]["intrinsic_value_per_share"] = values[k]
    a["reliability"] = {"label": "Low", "model_cap": "Low", "source_cap": "Low",
        "accounting_impact_ratio": None, "accounting_label": None,
        "reasons": ["ACCOUNTING_ADJUSTMENT_UNQUANTIFIED", "PUBLIC_CONTRACT_NOT_ACCEPTED"]}
    a["private_review_only"] = True
    a["review"]["publication_state"] = "withheld"
    return a, r, {"old_warning": old, "new_warning": new, "semantic_change": False,
        "basis": "Both versions expressly prohibit consolidated profit substitution and duplicate NCI subtraction. Original warning retained in immutable draft/provenance.",
        "no_special_model_version_or_profile": True}


SOURCE_ADAPTER = "expansion_late_source_binding"
BINDING_VERSION = "US-WITHHELD-EXPANSION-LATE-REPLAY-2"
_WT = Path(__file__).resolve().parents[3]
_ROOT = _WT.parents[1]
_BATCH = _ROOT / "output/us-expansion-batches-06-10-20261008"
_IDENTITIES = {"AAON": "0000824142", "EHC": "0000785161"}
_AXIS = "us-gaap:StatementEquityComponentsAxis"
_EQUITY = "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pinned(path, expected):
    p = Path(path)
    require(p.is_absolute() and ".." not in p.parts, "source path must be absolute and canonical")
    require(not any(x.is_symlink() for x in (p, *p.parents)), "source path has a symlink")
    require(p.is_file() and isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected),
            "missing source file or mandatory SHA256")
    require(_digest(p) == expected, "source SHA256 mismatch: " + str(p))
    return p


def _json(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda v: require(False, "nonfinite JSON: " + v))


def _candidate_file(candidate, name):
    require(name + "_path" in candidate and name + "_sha256" in candidate,
            "missing mandatory candidate path/hash: " + name)
    p = _pinned(candidate[name + "_path"], candidate[name + "_sha256"])
    require(p.suffix == ".json", "candidate metadata must be JSON, never source code")
    return _json(p)


def _primary_extractor():
    # Fixed implementation, never an executable path supplied by a candidate.
    path = _ROOT / "scripts/us_b0610_frozen_primary_facts.py"
    spec = importlib.util.spec_from_file_location("_late_frozen_primary", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _primary_document(receipt, cik, extractor):
    from lxml import html
    parsed = extractor.extract(receipt, cik)
    tree = html.fromstring(Path(receipt["path"]).read_bytes())
    nodes = list(tree.iter())
    header = {n.get("name"): re.sub(r"\s+", " ", n.text_content()).strip() for n in nodes
              if n.get("name") in {"dei:EntityCentralIndexKey", "dei:DocumentType", "dei:DocumentPeriodEndDate"}}
    reported = header.get("dei:DocumentPeriodEndDate", "")
    report_date = None
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%m/%d/%Y"):
        try:
            report_date = datetime.strptime(reported, fmt).date()
            break
        except ValueError:
            continue
    require(report_date is not None, "unsupported primary report date format")
    require(header.get("dei:EntityCentralIndexKey", "").zfill(10) == cik
            and header.get("dei:DocumentType") == receipt["filing"]["form"]
            and report_date.isoformat() == receipt["filing"]["reportDate"], "primary document header identity/form/report date mismatch")
    table_nodes = tree.xpath("//table")
    indexes = {node: i for i, node in enumerate(table_nodes)}
    bad_contexts = {n.get("id") for n in nodes if extractor.local(n.tag) == "context"
                    and any(extractor.local(d.tag) == "typedmember" for d in n.iter())}
    facts = []
    for f in parsed["facts"]:
        if f["context_id"] in bad_contexts:
            continue
        node = nodes[f["DOM_element_index"]]
        ancestors = node.xpath("ancestor::table")
        f["table_index"] = indexes.get(ancestors[-1]) if ancestors else None
        facts.append(f)
    for n in nodes:
        if extractor.local(n.tag) in {"hidden", "header", "context", "unit", "script", "style"} and n.getparent() is not None:
            n.getparent().remove(n)
    text = re.sub(r"[\s\u200b]+", " ", tree.text_content())
    return {"receipt": receipt, "facts": facts, "tables": extractor.tables(receipt, cik),
            "text": text, "risk_snippets": [{"text": text}]}


def _leaves(value):
    if isinstance(value, dict):
        if value.get("qname", "").startswith("us-gaap:"):
            yield value
        for child in value.values():
            yield from _leaves(child)
    elif isinstance(value, list):
        for child in value:
            yield from _leaves(child)


def _match_fact(ref, facts, cik):
    fields = ("qname", "value", "unit", "period_start", "period_end", "dimensions",
              "context_id", "source_accession", "form", "filed_date", "document_sha256", "source_url")
    require(all(k in ref for k in fields), "source leaf lacks mandatory identity/period/unit metadata")
    require(isinstance(ref["value"], (int, float)) and not isinstance(ref["value"], bool)
            and isfinite(ref["value"]), "source leaf value is not finite")
    hits = [f for f in facts if all(f.get(k) == ref[k] for k in fields)]
    require(hits, "primary fact mismatch: " + str({k: ref[k] for k in fields if k != "source_url"}))
    f = hits[0]
    require(f["entity_identifier"] == cik and f["entity_scheme"] == "http://www.sec.gov/CIK"
            and re.fullmatch(r"https?://fasb.org/us-gaap/20\d{2}", f["namespace"] or ""),
            "source entity or taxonomy mismatch")
    for saved, actual in (("reported_decimals", "decimals"), ("decimals", "decimals"),
                          ("primary_DOM_element_index", "DOM_element_index"),
                          ("DOM_element_index", "DOM_element_index"), ("namespace", "namespace"),
                          ("table_index", "table_index")):
        if saved in ref:
            require(any(h[actual] == ref[saved] for h in hits), "source precision/location mismatch: " + saved)
    start, end = f["period_start"], f["period_end"]
    require(date.fromisoformat(end) <= date.fromisoformat(CUTOFF), "fact period after cutoff")
    if start:
        require(date.fromisoformat(start) <= date.fromisoformat(end), "reversed fact period")
    if "duration_days" in ref:
        require(ref["duration_days"] == (shared.days(start, end) if start else None), "fact duration mismatch")
    return f


def _explicit_aoci_dash(document, common):
    """Bind an untagged reported dash by physical column spans, never absence."""
    from lxml import html
    tree = html.fromstring(Path(document["receipt"]["path"]).read_bytes())
    node = list(tree.iter())[common["DOM_element_index"]]
    table = node.xpath("ancestor::table")[-1]
    row = node.xpath("ancestor::tr")[-1]
    def cells(tr):
        offset = 0
        result = []
        for cell in tr.xpath("./td|./th"):
            width = int(cell.get("colspan", "1"))
            result.append((offset, offset + width, re.sub(r"\s+", " ", cell.text_content()).strip()))
            offset += width
        return result
    columns = [(lo, hi) for tr in table.xpath("./tr|./tbody/tr|./thead/tr") for lo, hi, text in cells(tr)
               if re.fullmatch(r"Accumulated Other Comprehensive (?:Income|Loss|Income \(Loss\))", text, re.I)]
    require(len(columns) == 1, "ambiguous historical OCI physical column")
    lo, hi = columns[0]
    displayed = "".join(text for left, right, text in cells(row) if left < hi and right > lo).replace("$", "").strip()
    require(displayed in {"—", "–", "-", "0", "0.0"}, "historical OCI is not an explicit reported zero/dash")


def _book_from_primary(record, end, ticker, facts, documents, cik):
    refs = list(_leaves(record))
    require(refs, "common book has no primary operands")
    matched = [_match_fact(r, facts, cik) for r in refs]
    acc = matched[0]["source_accession"]
    require(all(f["unit"] == "USD" and f["period_start"] is None and f["period_end"] == end
                and f["source_accession"] == acc for f in matched), "common book period/unit/accession mismatch")
    eligible_rows = [f for f in facts if eligible(f, accession=acc, end=end, unit="USD")]
    if ticker == "AAON":
        require(len(matched) == 1 and matched[0]["qname"] == _EQUITY and not matched[0]["dimensions"],
                "AAON common book must bind inclusive total plus complete common schedule")
        require(re.search(r"Preferred stock.*no shares issued", documents[acc]["text"], re.I),
                "AAON explicit preferred no-issuance statement missing")
        require(not any(f["dimensions"] == [[_AXIS, "us-gaap:NoncontrollingInterestMember"]]
                        for f in eligible_rows), "AAON outside-owner capital requires a new allocation")
        value = matched[0]["value"]
        members = ("CommonStockMember", "AdditionalPaidInCapitalMember", "RetainedEarningsMember")
    else:
        direct = len(matched) == 1 and matched[0]["qname"] == "us-gaap:StockholdersEquity" and not matched[0]["dimensions"]
        if direct:
            value = matched[0]["value"]
        else:
            require(len(matched) == 2 and matched[0]["qname"] == _EQUITY and not matched[0]["dimensions"]
                    and matched[1]["qname"] == _EQUITY
                    and matched[1]["dimensions"] == [[_AXIS, "us-gaap:NoncontrollingInterestMember"]],
                    "EHC book must be explicit parent or inclusive total less explicit same-scope NCI")
            value = matched[0]["value"] - matched[1]["value"]
        members = ("CommonStockMember", "AdditionalPaidInCapitalMember", "RetainedEarningsMember", "TreasuryStockCommonMember")
        common = shared.unique([f for f in eligible_rows if f["qname"] == _EQUITY
                               and f["dimensions"] == [[_AXIS, "us-gaap:CommonStockMember"]]], "common stock column")
        table = next(t for t in documents[acc]["tables"] if t["table_index"] == common["table_index"])
        require(re.search(r"Encompass Health\s*Common Shareholders", table_text(table), re.I), "EHC complete common-owner table missing")
        aoci = [f for f in eligible_rows if f["qname"] == _EQUITY
                and f["dimensions"] == [[_AXIS, "us-gaap:AccumulatedOtherComprehensiveIncomeMember"]]]
        if aoci:
            members += ("AccumulatedOtherComprehensiveIncomeMember",)
        elif re.search(r"comprehensive", table_text(table), re.I):
            _explicit_aoci_dash(documents[acc], common)
    components = [shared.unique([f for f in eligible_rows if f["qname"] == _EQUITY
                  and f["dimensions"] == [[_AXIS, "us-gaap:" + member]]], "complete common component " + member)
                  for member in members]
    total = sum(Decimal(str(f["value"])) for f in components)
    def radius(f):
        return Decimal(0) if f["decimals"] == "INF" else Decimal("0.5") * Decimal(10) ** -int(f["decimals"])
    tolerance = sum(radius(f) for f in components + matched)
    require(abs(total - Decimal(str(value))) <= tolerance, "primary common components do not reconcile at reported precision")
    require(record["value"] == value and value > 0, "derived common book differs from source allocation")
    return value


def _replay_scenarios(ledger, recipe, ticker, facts, documents, cik):
    receipts = {acc: doc["receipt"] for acc, doc in documents.items()}
    filing = max(receipts.values(), key=lambda r: r["filing"]["filingDate"])["filing"]
    end, acc = filing["reportDate"], filing["accessionNumber"]
    require(end == "2026-06-30" and filing["form"] == "10-Q", "frozen financial reference changed")
    names = (("NetIncomeLoss",) if ticker == "AAON" else
             ("NetIncomeLossFromContinuingOperationsAvailableToCommonShareholdersBasic",))
    annual = [shared.flow(facts, names, f"{year}-12-31", receipts, "common continuing income",
                         annual=True, start=f"{year}-01-01") for year in range(2021, 2026)]
    require(len(ledger["annual_common_income"]) == len(ledger["annual_reported_parent_book"]) == 5,
            "five source annual observations required")
    for saved, actual in zip(ledger["annual_common_income"], annual):
        require(_match_fact(saved, facts, cik) == _match_fact(actual, facts, cik), "annual common income selector mismatch")
    current = shared.flow(facts, names, end, receipts, "current common income", acc=acc, start="2026-01-01")
    prior = shared.flow(facts, names, "2025-06-30", receipts, "prior common income", acc=acc, start="2025-01-01")
    ttm = annual[-1]["value"] + current["value"] - prior["value"]
    stored = ledger["current_income_ttm"]
    require(stored["value"] == ttm and stored["duration_days"] == 365 and len(stored["operands"]) == 3,
            "TTM arithmetic or fiscal period mismatch")
    for saved, actual in zip(stored["operands"], (annual[-1], current, prior)):
        require(_match_fact(saved, facts, cik) == _match_fact(actual, facts, cik), "TTM owner/period operand mismatch")
    book = _book_from_primary(ledger["current_common_capital"]["reported_parent_common_book"], end, ticker, facts, documents, cik)
    share = qualified_outstanding(documents[acc]["facts"], documents[acc]["tables"], accession=acc, end=end)
    require(ledger["balance_point_common_shares"]["value"] == share["value"], "physical share denominator mismatch")
    if ticker == "AAON":
        bridge = aaon_common_bridge(documents[acc])
        require(bridge["reported_common_book"] == book, "AAON current common ownership bridge mismatch")
    else:
        require(share["operands"][0]["decimals"] == "-5", "EHC share precision must remain 0.1M")
    roes = []
    for income, capital in zip(annual, ledger["annual_reported_parent_book"]):
        start = (date.fromisoformat(income["period_start"]) - timedelta(days=1)).isoformat()
        opening = _book_from_primary(capital["opening"], start, ticker, facts, documents, cik)
        closing = _book_from_primary(capital["closing"], income["period_end"], ticker, facts, documents, cik)
        roes.append(income["value"] / ((opening + closing) / 2))
    anchor = min(ttm / book, median(roes))
    require(ledger["annual_reported_ROE"] == roes and ledger["normalized_ROE"] == anchor,
            "annual ROE or selected current/history anchor mismatch")
    policy = ledger["assumptions"]
    distributions = ledger["reported_common_distributions"]
    dividend_annual = [shared.flow(facts, shared.DIV, f"{year}-12-31", receipts, "common cash dividends",
                       annual=True, start=f"{year}-01-01") for year in range(2021, 2026)]
    dividend_current = shared.flow(facts, shared.DIV, end, receipts, "current common dividends", acc=acc, start="2026-01-01")
    dividend_prior = shared.flow(facts, shared.DIV, "2025-06-30", receipts, "prior common dividends", acc=acc, start="2025-01-01")
    require(distributions["status"] == "reported_and_fiscal_TTM" and len(distributions["annual"]) == 5,
            "common distribution history missing")
    for saved, actual in zip(distributions["annual"], dividend_annual):
        require(_match_fact(saved, facts, cik) == _match_fact(actual, facts, cik), "annual dividend operand mismatch")
    dividend_ttm = dividend_annual[-1]["value"] + dividend_current["value"] - dividend_prior["value"]
    require(distributions["current_TTM"]["value"] == dividend_ttm and distributions["current_TTM"]["duration_days"] == 365,
            "common dividend TTM mismatch")
    require(len(distributions["current_TTM"]["operands"]) == 3, "dividend TTM operand count mismatch")
    for saved, actual in zip(distributions["current_TTM"]["operands"], (dividend_annual[-1], dividend_current, dividend_prior)):
        require(_match_fact(saved, facts, cik) == _match_fact(actual, facts, cik), "dividend TTM period/owner mismatch")
    observed = sum(f["value"] for f in dividend_annual) / sum(f["value"] for f in annual)
    require(distributions["five_year_cash_dividend_to_common_income"] == observed
            and distributions["raw_TTM_cash_dividend_to_common_income"] == dividend_ttm / ttm,
            "reported dividend/common income ratio mismatch")
    if ticker == "AAON":
        require(policy["future_payout_ratio"] == observed, "AAON retained observed payout mismatch")
    else:
        require("Fixed prior forecast payout" in policy["future_payout_basis"], "EHC payout must be labeled a fixed assumption")
    scenarios = {}
    for i, name in enumerate(("bear", "base", "bull")):
        terminal = anchor * policy["terminal_ROE_fractions"][i]
        scenarios[name] = {"engine": "residual_income", "inputs": {
            "book_value_per_share": book / share["value"],
            "current_roe": anchor * policy["initial_ROE_multipliers"][i],
            "cost_of_equity": policy["cost_of_equity"][i], "current_payout_ratio": policy["future_payout_ratio"],
            "terminal_roe": terminal, "terminal_growth": min(policy["terminal_growth_caps"][i], terminal * policy["terminal_retention_fractions"][i]),
            "years": policy["years"]}}
    require(recipe["scenarios"] == ledger["scenario_arguments"] == scenarios, "scenario operands do not replay from sources and pinned policy")
    return {"common_book_USD": book, "balance_common_shares": share["value"], "shares_fully_diluted": False,
            "share_decimals": share["operands"][0]["decimals"], "common_continuing_TTM_USD": ttm,
            "TTM_days": 365, "annual_ROE": roes, "selected_ROE": anchor, "scenarios": scenarios,
            "current_accession": acc, "financial_reference_date": end, "filing_date": filing["filingDate"]}


def required_disclosure_patterns(ticker):
    """Fixed source roles; callers cannot weaken this to a candidate-supplied regex."""
    if ticker == "AAON":
        return {"AAON-tax-SBC": r"Excess tax benefits related to share.based.{0,240}12,394.{0,80}9,020",
                "AAON-state-credit": r"State tax credits.{0,100}2,227",
                "AAON-reported-rate": r"Effective tax rate.{0,130}16\.1\s*%",
                "AAON-ex-discrete-rate": r"estimated annual 2026 effective tax rate, excluding discrete events, is approximately 25\.0\s*%",
                "AAON-operating-owner": r"operating subsidiaries, all of which are wholly.owned",
                "AAON-VIE": r"eight variable interest entities",
                "AAON-NMTC": r"Short.term obligations of NMTC.{0,20}7,535.*New markets tax credit obligations.{0,20}21,331"}
    require(ticker == "EHC", "unsupported disclosure issuer")
    return {"EHC-Gamma-Knife": r"50%.{0,160}Gamma Knife.{0,500}January 1, 2026.{0,250}17\.5 million pre.tax gain.{0,280}17\.9 million proceeds",
            "EHC-healthcare": r"inpatient rehabilitation hospitals",
            "EHC-outside-owners": r"Redeemable noncontrolling interests.{0,100}57\.9.*Encompass Health shareholders.{0,60}2,597\.7"}


def verify_candidate_sources(candidate: dict, artifact: dict, recipe: dict, cutoff: str) -> dict:
    """Read-only, fail-closed AAON/EHC source proof; does not approve publication.

    Main confines artifact/recipe/binding/source_ledger paths to its run. All four
    paths and their SHA256 values are mandatory. No candidate-selected Python is
    imported. Source pins are checked before extraction and immediately before
    returning. Raises InitialInputGap (ValueError) on failed proof.
    """
    require(cutoff == CUTOFF and candidate.get("source_adapter") == SOURCE_ADAPTER, "unsupported source adapter/cutoff")
    saved_artifact = _candidate_file(candidate, "artifact")
    saved_recipe = _candidate_file(candidate, "recipe")
    binding = _candidate_file(candidate, "binding")
    ledger = _candidate_file(candidate, "source_ledger")
    require(saved_artifact == artifact and saved_recipe == recipe, "passed candidate objects differ from pinned files")
    ticker = recipe["ticker"]
    require(ticker in _IDENTITIES and binding["ticker"] == ledger["ticker"] == artifact["issuer"]["ticker"] == ticker,
            "source binding ticker mismatch")
    cik = _IDENTITIES[ticker]
    require(binding["schema_version"] == BINDING_VERSION and binding["cik"] == artifact["issuer"]["cik"] == cik,
            "source binding issuer/schema mismatch")
    require(binding["cutoff"] == ledger["cutoff"] == recipe["evidence_cutoff"] == recipe["valuation_date"]
            == artifact["valuation_date"] == artifact["assumption_date"] == cutoff, "source/assumption cutoff mismatch")
    pins = binding["source_pins"]
    require(isinstance(pins, dict) and pins, "source pin manifest missing")
    for path, digest in pins.items():
        _pinned(path, digest)
    def metadata(name):
        path = binding[name + "_path"]
        require(path in pins and Path(path).suffix == ".json", "metadata path is not pinned JSON: " + name)
        return _json(path)
    coverage = metadata("coverage")
    submissions = metadata("submissions")
    sub_meta = metadata("submissions_meta")
    require(sub_meta["sha256"] == pins[binding["submissions_path"]], "submission receipt mismatch")
    require(str(coverage["cik"]).zfill(10) == str(submissions["cik"]).zfill(10) == cik
            and ticker in submissions["tickers"], "primary coverage/submissions issuer mismatch")
    predecessor = metadata("prior_recipe")
    require(recipe["scenarios"] == predecessor["scenarios"] and recipe.get("editable") == {},
            "frozen economics or locked calculator contract changed")
    require(candidate["source_ledger_path"] == binding["source_ledger_path"]
            and candidate["source_ledger_sha256"] == binding["source_ledger_sha256"], "candidate ledger binding mismatch")
    for receipt in ledger["assumptions"].get("event_context", {}).get("receipts", []):
        require(pins.get(receipt["path"]) == receipt["sha256"] and receipt["filing"]["filingDate"] <= cutoff,
                "unreviewed event context file is not pinned or is post-cutoff")
    if ledger.get("supplemental_file_sha256"):
        supplemental = str(_BATCH / f"private-recovery-pass/supplemental-facts/{ticker}.json.gz")
        require(pins.get(supplemental) == ledger["supplemental_file_sha256"], "legacy supplemental source pin missing")
    from .classification import classify_issuer
    config = metadata("classification_config")
    if ticker == "AAON":
        classification = classify_issuer(submissions, config)
        for key in ("valuation_policy", "verified_zero_bridge_fields", "governed_bridge_fields", "requires_segment_forecast"):
            classification.pop(key, None)
        require(artifact["issuer"] == classification, "AAON native classification metadata mismatch")
    else:
        require(str(submissions["sic"]) == "8060" and artifact["issuer"]["finsight_sector"] == "Healthcare"
                and artifact["issuer"]["primary_archetype"] == "healthcare_provider_common_equity"
                and "classification_confidence" not in artifact["issuer"], "EHC classification is unsupported or confidence invented")
    extractor = _primary_extractor()
    documents = {}
    for receipt in coverage["documents"]:
        receipt = deepcopy(receipt)
        p = Path(receipt["path"])
        p = p if p.is_absolute() else _ROOT / p
        require(str(p) in pins and receipt["sha256"] == pins[str(p)] and p.is_relative_to(_BATCH), "primary receipt pin/scope mismatch")
        receipt["path"] = str(p)
        filing = receipt["filing"]
        acc = filing["accessionNumber"]
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{filing['primaryDocument']}"
        require(receipt["source_url"] == url and receipt["status"] == "captured"
                and filing["form"] in {"10-K", "10-Q"}
                and date.fromisoformat(filing["reportDate"]) <= date.fromisoformat(filing["filingDate"]) <= date.fromisoformat(cutoff),
                "source URL/form/filing date/report date mismatch")
        require(acc not in documents, "duplicate primary accession")
        documents[acc] = _primary_document(receipt, cik, extractor)
    require(len(documents) == 6, "frozen six-primary-file coverage changed")
    facts = [f for d in documents.values() for f in d["facts"]]
    leaves = list(_leaves(ledger))
    require(leaves, "ledger has no source facts")
    for ref in leaves:
        _match_fact(ref, facts, cik)
    proof = _replay_scenarios(ledger, recipe, ticker, facts, documents, cik)
    source = artifact["source_financial_statement"]
    receipt = documents[proof["current_accession"]]["receipt"]
    require(source["accession"] == proof["current_accession"] and source["period_end"] == proof["financial_reference_date"]
            and source["filed_date"] == proof["filing_date"] and source["form"] == "10-Q"
            and source["url"] == receipt["source_url"], "artifact financial source metadata mismatch")
    disclosures = binding["issuer_specific_disclosures"]
    require(disclosures and ledger["assumptions"]["issuer_specific_disclosures"] == disclosures
            and all(d in artifact["review"]["warnings"] and d in recipe["warnings"] for d in disclosures),
            "required consumer disclosures missing")
    require({s["id"]: s["pattern"] for s in binding["disclosure_spans"]} == required_disclosure_patterns(ticker),
            "mandatory primary disclosure roles changed")
    for span in binding["disclosure_spans"]:
        require(span["accession"] == proof["current_accession"], "disclosure must use frozen current statement")
        doc = documents[span["accession"]]
        require(re.search(span["pattern"], doc["text"], re.I), "required primary disclosure missing: " + span["id"])
    ranges = evaluate_recipe(recipe)["range"]
    require({k: artifact["scenario_range"][k] for k in ranges} == ranges, "artifact and source-replayed range differ")
    require(artifact["private_review_only"] is True and artifact["review"]["publication_state"] == "withheld"
            and artifact["reliability"]["label"] == "Low", "source proof cannot grant public acceptance")
    for name in ("artifact", "recipe", "binding", "source_ledger"):
        _candidate_file(candidate, name)
    for path, digest in pins.items():
        _pinned(path, digest)
    return {"source_adapter": SOURCE_ADAPTER, "verified": True, "ticker": ticker, "cik": cik,
            "cutoff": cutoff, "primary_files_reextracted": len(documents), "source_leaf_checks": len(leaves),
            "pinned_files_rechecked": len(pins), "source_pins": deepcopy(pins), "operands": proof,
            "range": ranges, "economics_preserved": True, "Arelle_validated": False,
            "public_contract_accepted": False, "publication_authorized": False,
            "limits": ["Reported common-GAAP accounting scope; no sustainable-income or market calibration claim.",
                       "Legal claims and separate after-tax one-off adjustments remain unquantified.",
                       "Main owns combined HTTP/store verification; this is the source operand gate only."]}
