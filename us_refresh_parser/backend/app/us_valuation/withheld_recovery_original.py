"""Private, opt-in recovery workpapers; this module changes no runtime policy."""
from __future__ import annotations

from datetime import date
from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re

from bs4 import BeautifulSoup
from .catalog import canonical_json_bytes
from .calculation_recipe import evaluate_recipe
from .reviewed_recovery import CONCEPTS, SCHEMA as REVIEW_SCHEMA
from .refresh_bindings import bind_current_recipe
from .xbrl import CompanyFactsNormalizer, load_concept_config


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return canonical_json_bytes(value)


def checked_receipt(path: Path, ticker: str, cik: str, cutoff: str) -> dict:
    receipt = json.loads(path.read_bytes())
    packet = receipt["packet"]
    if sha256(canonical(packet)).hexdigest() != receipt["packet_sha256"]:
        raise ValueError("source packet hash mismatch")
    if receipt["ticker"] != ticker or str(packet["issuer"]["cik"]).zfill(10) != cik:
        raise ValueError("source identity mismatch")
    filing = packet["controlling_filing"]
    if date.fromisoformat(filing["filingDate"]) > date.fromisoformat(cutoff):
        raise ValueError("filing is beyond the evidence cutoff")
    structure = packet["structural_filing"]
    if structure["source_accession"] != filing["accessionNumber"]:
        raise ValueError("structural accession mismatch")
    return packet


def text_document(path: Path) -> str:
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for node in soup(["script", "style", "ix:header"]):
        node.decompose()
    return re.sub(r"\s+", " ", " ".join(soup.stripped_strings))


def fact_inventory(packet: dict) -> list[dict]:
    """Record actual fact periods and ownership; never use wrapper period_end."""
    filing = packet["controlling_filing"]
    wanted = re.compile(r"(Revenue|StockholdersEquity|MinorityInterest|PreferredStock|NetIncome|IncomeLossFromContinuing|NetCashProvidedByUsedInOperating|PaymentsToAcquireProperty|WeightedAverageNumberOfDiluted|GainLossOnDeconsolidation|ProceedsFromIssuanceOfLongTermDebt|RepaymentsOfLongTermDebt|LongTermDebtCurrent|LongTermDebtNoncurrent)")
    result = []
    for row in packet["structural_filing"]["facts"]:
        if not wanted.search(row.get("local_name", "")) or row.get("period_end") != filing["reportDate"]:
            continue
        if row.get("source_accession") != filing["accessionNumber"]:
            continue
        if str(row.get("entity_identifier", "")).zfill(10) != str(packet["issuer"]["cik"]).zfill(10):
            continue
        if row.get("dimensions") and "ContinuingOperationsMember" not in str(row["dimensions"]):
            continue
        value = row.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            continue
        result.append({key: row.get(key) for key in (
            "qname", "value", "unit", "decimals", "period_start", "period_end", "dimensions",
            "entity_identifier", "context_id", "source_accession", "filed_date", "filing_form", "statement_roles")})
    return result


def selected_fact(structural, concept, *, cik, start, end):
    """Choose the most precise compatible fact, rejecting conflicting duplicates."""
    expected_unit = "xbrli:shares" if "SharesOutstanding" in concept else "USD"
    rows = [r for r in structural["facts"] if r.get("local_name") == concept
            and r.get("period_start") == start and r.get("period_end") == end
            and not r.get("dimensions") and r.get("source_accession") == structural["source_accession"]
            and str(r.get("entity_identifier", "")).zfill(10) == cik
            and r.get("entity_scheme") == "http://www.sec.gov/CIK"]
    if not rows:
        raise ValueError("missing selected fact: " + concept)
    def radius(row):
        return 0.0 if str(row["decimals"]) == "INF" else .5 * 10 ** -int(row["decimals"])
    if any(r.get("unit") != expected_unit or isinstance(r.get("value"), bool)
           or not isinstance(r.get("value"), (float, int)) or not isfinite(r["value"]) for r in rows):
        raise ValueError("invalid selected fact unit/value: " + concept)
    if max(r["value"] - radius(r) for r in rows) > min(r["value"] + radius(r) for r in rows):
        raise ValueError("conflicting selected facts: " + concept)
    row = min(rows, key=lambda r: (radius(r), r["context_id"]))
    return {k: row.get(k) for k in ("qname", "namespace", "period_start", "period_end", "context_id", "unit", "decimals", "value")}


def verify_pins(pins):
    if not pins:
        raise ValueError("missing source byte pins")
    for pin in pins:
        if digest(Path(pin["path"])) != pin["sha256"]:
            raise ValueError("source bytes changed: " + pin["path"])


def load_binding_packet(bundle):
    """Authenticate the real files before handing their facts to the existing binder."""
    verify_pins(bundle["source_evidence"])
    paths = bundle["packet_paths"]
    pins = {row["path"]: row["sha256"] for row in bundle["source_evidence"]}
    if set(paths) != {"structural_filing", "companyfacts", "submissions"} or any(p not in pins for p in paths.values()):
        raise ValueError("packet file is not authenticated by the review")
    packet = {key: json.loads(Path(path).read_bytes()) for key, path in paths.items()}
    policy = bundle["policy"]
    finance = policy["review"]["financing_review"]
    if pins.get(finance.get("source_path")) != finance.get("source_sha256"):
        raise ValueError("financing review does not bind the authenticated bytes")
    for event in bundle.get("events", []):
        for source in event["document_sources"]:
            if not any(Path(path).name == source["name"] and h == source["sha256"] for path, h in pins.items()):
                raise ValueError("event review does not bind the authenticated bytes")
    packet["structural_receipts"] = [{"accession": policy["review"]["accession"],
                                      "structural_sha256": digest(Path(paths["structural_filing"]))}]
    packet["events"] = deepcopy(bundle.get("events", []))
    return packet


def make_reviewed_policy(ticker, cik, packet, recipe, *, structural_sha256, financing_path, cutoff):
    """Materialize existing reviewed-recovery rules with actual source selections.

    No numerical targets, new stress amounts, or source-zero fallback enter this
    routine. The old recipe's explicitly disclosed scenario assumptions remain.
    """
    if ticker not in CONCEPTS or recipe["ticker"] != ticker:
        raise ValueError("unsupported reviewed recipe identity")
    structural = packet["structural_filing"]
    accession = structural["source_accession"]
    recent = packet["submissions"]["filings"]["recent"]
    index = recent["accessionNumber"].index(accession)
    end, filed = recent["reportDate"][index], recent["filingDate"][index]
    if filed > cutoff:
        raise ValueError("reviewed filing after cutoff")
    # These are the existing H1 reviewed recipes. A different period fails closed.
    if end != "2026-06-30":
        raise ValueError("new fiscal period needs a new reviewed earnings/cash basis")
    selected = {}
    for name, concept in CONCEPTS[ticker].items():
        flow = name in {"parent_earnings", "dividends", "shares"}
        selected[name] = selected_fact(structural, concept, cik=cik,
            start="2026-01-01" if flow else None,
            end="2025-12-31" if name == "opening_parent_equity" else end)
    text = text_document(financing_path)
    base = recipe["scenarios"]["base"]["inputs"]
    if ticker == "BG":
        note = re.search(r"\$([\d.,]+) million aggregate principal amount of ([\d.]+)% Senior Notes", text)
        if not note:
            raise ValueError("reviewed financing note terms are missing")
        principal, coupon = float(note[1].replace(",", "")) * 1e6, float(note[2]) / 100
        # Existing private assumption: a full-year incremental interest stress,
        # 24% tax proxy, no refinancing or interest-income offset.
        tax_proxy = .24
        interest = principal * coupon * (1 - tax_proxy)
        specialist = {"earnings_annualization_factor": 2,
            "annual_note_interest_after_tax": interest,
            "roe_multipliers": {case: spec["inputs"]["current_roe"] / base["current_roe"]
                                for case, spec in recipe["scenarios"].items()},
            "financing_review": {"source_sha256": digest(financing_path),
                "source_path": str(financing_path), "principal": principal, "coupon": coupon,
                "tax_proxy": tax_proxy, "treatment": "Retained full-year incremental interest stress; 24% tax is an assumption, with no refinancing or interest-income credit."}}
    else:
        assertion = "As of June 30, 2026, we had no outstanding borrowings under the facility"
        if assertion not in text:
            raise ValueError("explicit facility borrowing evidence is missing")
        n = CompanyFactsNormalizer(packet["companyfacts"], concept_config=load_concept_config(),
            fiscal_year_end=packet["submissions"].get("fiscalYearEnd"), as_of_date=cutoff)
        flows = {label: n.ttm_flow(field) for label, field in (
            ("operating_cash_flow_ttm", "operating_cash_flow"), ("capital_expenditures_ttm", "capital_expenditures"))}
        known_claims = selected["legal"]["value"] + selected["vat"]["value"]
        specialist = {"ttm": {k: row["value"] for k, row in flows.items()},
            "cash_multipliers": {case: spec["inputs"]["cash_fcff"] / base["cash_fcff"]
                                 for case, spec in recipe["scenarios"].items()},
            "extra_legal_loss": {case: -spec["inputs"]["nonoperating_adjustment"] - known_claims
                                 for case, spec in recipe["scenarios"].items()},
            "financing_review": {"source_sha256": digest(financing_path), "source_path": str(financing_path),
                "borrowings": 0, "assertion": assertion,
                "treatment": "Reported unused facility; parent balance reconciles without NCI; preferred is reported zero. Retained post-rent owner-cash convention; future unknown claims are not reported zero."},
            "ttm_operand_evidence": flows}
    review = {"accession": accession, "period_end": end, "filed_date": filed,
              "structural_sha256": structural_sha256, "facts": selected, **specialist}
    policy = {"schema_version": REVIEW_SCHEMA, "version": REVIEW_SCHEMA + "-ORIGINAL-20261008",
        "ticker": ticker, "cik": cik, "review": review, "stage_only": True,
        "automatic_refresh_authorized": False, "publication_authorized": False,
        "new_filing_requires_new_review": True,
        "statement_required_fields": {"parent_equity": "instant", "parent_earnings": "flow"} if ticker == "BG"
            else {"cash": "instant", "operating_cash_flow": "flow"},
        "concept_config": {"fields": {
            "parent_equity": {"concepts": ["StockholdersEquity"], "unit": "USD"},
            "parent_earnings": {"concepts": ["NetIncomeLoss"], "unit": "USD"},
            "cash": {"concepts": ["CashAndCashEquivalentsAtCarryingValue"], "unit": "USD"},
            "operating_cash_flow": {"concepts": ["NetCashProvidedByUsedInOperatingActivities"], "unit": "USD"}}},
        "source_requirements": {"structural": True, "event_exhibits": True}}
    return policy


def replay_binding(bundle, recipe, *, staged_only, cutoff):
    if staged_only is not True or bundle.get("stage_only") is not True:
        raise ValueError("this recovery is stage-only")
    if cutoff != bundle["review_date"]:
        raise ValueError("a new cutoff requires review; no automatic carry-forward")
    if sha256(canonical(recipe)).hexdigest() != bundle["prior_recipe_semantic_sha256"]:
        raise ValueError("unreviewed prior recipe mutation")
    policy = bundle["policy"]
    if policy["ticker"] != bundle["ticker"] or policy["cik"] != bundle["cik"]:
        raise ValueError("binding identity mismatch")
    packet = load_binding_packet(bundle)
    bound, ledger = bind_current_recipe({"ticker": bundle["ticker"], "cik": bundle["cik"],
        "refresh_policy": policy}, deepcopy(recipe), packet, cutoff, staged_only=True)
    if bound["scenarios"] != recipe["scenarios"]:
        raise ValueError("binding changed prior economics; separate economic review is required")
    return bound, evaluate_recipe(bound), ledger
