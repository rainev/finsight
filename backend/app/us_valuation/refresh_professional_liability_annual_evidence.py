"""Hash-bound annual professional-liability cash evidence and overlap decision."""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
from pathlib import Path
import json
import re

from .arelle_worker import _QNameCanonicalizer
from .catalog import canonical_json_bytes, sha256_bytes
from .refresh_narrative_evidence import _VisibleText, _source_document


VERSION = "FINSIGHT-PROFESSIONAL-LIABILITY-ANNUAL-EVIDENCE-WG35-2"
RULES = {
    "HCA": {
        "version": VERSION,
        "ticker": "HCA",
        "cik": "0000860730",
        "issuer_namespace_pattern": r"https?://hcahealthcare\.com/\d{8}",
        "gross_reserve_local": "ProfessionalLiabilityRisksReserves",
        "current_reserve_local": "CurrentProfessionalLiabilityRisks",
        "noncurrent_reserve_local": "ProfessionalLiabilityRisks",
        "reinsurance_current_local": "ReinsuranceContractsReceivableAmountRecordedInOtherCurrentAssets",
        "reinsurance_noncurrent_local": "ReinsuranceContractsReceivableAmountRecordedInOtherAssets",
        "claim_payments_local": "ProfessionalAndGeneralLiabilityClaimsPaymentsNet",
        "provision_local": "ProvisionsForLossesRelatedToProfessionalLiabilityRisks",
        "total_investment_qname": "us-gaap:InvestmentOwnedAtFairValue",
        "current_investment_qname": "us-gaap:InvestmentsFairValueDisclosure",
        "noncurrent_investment_qname": "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
        "operating_cash_flow_qname": "us-gaap:NetCashProvidedByUsedInOperatingActivities",
        "ordinary_nci_qname": "us-gaap:MinorityInterest",
        "nci_income_qname": "us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
        "nci_distributions_qname": "us-gaap:PaymentsToMinorityShareholders",
        "history_payment_rule": "current_expected_within_observed_annual_range",
    }
}


def professional_liability_annual_policy(ticker: str) -> dict:
    return deepcopy(RULES[ticker])


def _path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError("annual professional-liability relative locator required")
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("annual professional-liability source outside root or missing")
    return path


def _amount(value: str) -> float:
    token = value.replace("$", "").replace(",", "").strip()
    negative = token.startswith("(") and token.endswith(")")
    token = token.strip("() ")
    number = float(token) * 1_000_000
    return -number if negative else number


def _rollforward(section: str) -> dict[str, dict[str, float]]:
    pattern = (
        r"Changes in our professional liability reserves, net of reinsurance recoverable, for the years ended December 31, are summarized in the following table \(dollars in millions\): "
        r"(?P<y1>20\d{2}) (?P<y2>20\d{2}) (?P<y3>20\d{2}) "
        r"Net reserves for professional liability claims, January 1 \$ (?P<open1>[0-9,]+) \$ (?P<open2>[0-9,]+) \$ (?P<open3>[0-9,]+) "
        r"Provision for current year claims (?P<curprov1>\(?[0-9,]+ ?\)?) (?P<curprov2>\(?[0-9,]+ ?\)?) (?P<curprov3>\(?[0-9,]+ ?\)?) "
        r"(?:Unfavorable|Unfavorable \(favorable\)) development related to prior years[’'] claims (?P<dev1>\(?[0-9,]+ ?\)?) (?P<dev2>\(?[0-9,]+ ?\)?) (?P<dev3>\(?[0-9,]+ ?\)?) "
        r"Total provision (?P<prov1>\(?[0-9,]+ ?\)?) (?P<prov2>\(?[0-9,]+ ?\)?) (?P<prov3>\(?[0-9,]+ ?\)?) "
        r"Payments for current year claims (?P<curpay1>[0-9,]+) (?P<curpay2>[0-9,]+) (?P<curpay3>[0-9,]+) "
        r"Payments for prior years[’'] claims (?P<priorpay1>[0-9,]+) (?P<priorpay2>[0-9,]+) (?P<priorpay3>[0-9,]+) "
        r"Total claim payments (?P<pay1>[0-9,]+) (?P<pay2>[0-9,]+) (?P<pay3>[0-9,]+) "
        r"Effect of new retroactive reinsurance contracts (?P<retro1>\(?[0-9,]+ ?\)?) (?P<retro2>\(?[0-9,]+ ?\)?) (?P<retro3>\(?[0-9,]+ ?\)?) "
        r"Net reserves for professional liability claims, December 31 \$ (?P<end1>[0-9,]+) \$ (?P<end2>[0-9,]+) \$ (?P<end3>[0-9,]+)"
    )
    matches = list(re.finditer(pattern, section, re.IGNORECASE))
    if len(matches) != 1:
        raise ValueError("annual professional-liability rollforward missing or ambiguous")
    match = matches[0]
    result = {}
    for index in (1, 2, 3):
        year = match[f"y{index}"]
        row = {
            "opening_net_reserve": _amount(match[f"open{index}"]),
            "current_year_provision": _amount(match[f"curprov{index}"]),
            "prior_year_development": _amount(match[f"dev{index}"]),
            "total_provision": _amount(match[f"prov{index}"]),
            "current_year_claim_payments": _amount(match[f"curpay{index}"]),
            "prior_year_claim_payments": _amount(match[f"priorpay{index}"]),
            "total_claim_payments": _amount(match[f"pay{index}"]),
            "retroactive_reinsurance_effect": _amount(match[f"retro{index}"]),
            "ending_net_reserve": _amount(match[f"end{index}"]),
        }
        if row["total_provision"] != row["current_year_provision"] + row["prior_year_development"]:
            raise ValueError("annual professional-liability provision rollforward does not add")
        if row["total_claim_payments"] != row["current_year_claim_payments"] + row["prior_year_claim_payments"]:
            raise ValueError("annual professional-liability payment rollforward does not add")
        if row["ending_net_reserve"] != row["opening_net_reserve"] + row["total_provision"] - row["total_claim_payments"] + row["retroactive_reinsurance_effect"]:
            raise ValueError("annual professional-liability reserve rollforward does not close")
        result[year] = row
    return result


def _section(text: str) -> tuple[str, int, int]:
    anchors = list(re.finditer(r"Professional Liability (?:Reserves|Claims) We, along with virtually all health care providers", text))
    candidates = []
    for anchor in anchors:
        end = text.find("Income Taxes We calculate", anchor.end())
        if end >= 0:
            candidates.append((text[anchor.start():end], anchor.start(), end))
    if len(candidates) != 1:
        raise ValueError("annual professional-liability section missing or ambiguous")
    return candidates[0]


def extract_annual_professional_liability_evidence(ticker: str, sources: list[dict], *, source_root: Path, cutoff: str) -> dict:
    root = Path(source_root).resolve()
    policy = RULES[ticker]
    if not sources or len({row.get("structural_path") for row in sources}) != len(sources):
        raise ValueError("unique annual professional-liability sources required")
    canonical = _QNameCanonicalizer()
    observations = []
    bound_sources = []
    order = []
    overlap_rollforwards: dict[str, dict] = {}
    overlap_instants: dict[tuple[str, str], float] = {}
    overlap_flows: dict[tuple[str, str], float] = {}
    for source in sources:
        manifest_path = _path(root, source["package_manifest_path"])
        structural_path = _path(root, source["structural_path"])
        manifest_raw = manifest_path.read_bytes(); manifest = json.loads(manifest_raw)
        structural_raw = structural_path.read_bytes(); structural = json.loads(structural_raw)
        document, resource, filing = _source_document(manifest, manifest_path)
        if (str(manifest.get("cik", "")).zfill(10) != policy["cik"] or filing["form"] not in {"10-K", "10-K/A"}
            or not filing["report_date"] <= filing["filed_date"] <= cutoff
            or structural.get("source_accession") != filing["accession"] or structural.get("form") != filing["form"]
            or structural.get("report_date") != filing["report_date"] or structural.get("filed_date") != filing["filed_date"]):
            raise ValueError("annual professional-liability filing identity/cutoff mismatch")
        order.append((filing["filed_date"], filing["accession"]))
        primary = (manifest_path.parent / document).resolve()
        if not primary.is_relative_to(manifest_path.parent) or not primary.is_file():
            raise ValueError("annual professional-liability primary document missing or unsafe")
        document_raw = primary.read_bytes()
        if sha256_bytes(document_raw) != resource["sha256"]:
            raise ValueError("annual professional-liability document hash mismatch")
        if (not isinstance(manifest.get("files"), list) or manifest.get("resource_count") != len(manifest["files"])
            or len({row["local_path"] for row in manifest["files"]}) != len(manifest["files"])
            or manifest.get("total_bytes") != sum(row["byte_count"] for row in manifest["files"])):
            raise ValueError("annual professional-liability package inventory invalid")
        package_files = []
        for row in manifest["files"]:
            path = (manifest_path.parent / row["local_path"]).resolve()
            if (not path.is_relative_to(manifest_path.parent) or not path.is_file() or path.stat().st_size != row["byte_count"]
                or sha256_bytes(path.read_bytes()) != row["sha256"]):
                raise ValueError("annual professional-liability package resource mismatch")
            package_files.append({"path": path.relative_to(root).as_posix(), "sha256": row["sha256"]})
        parser = _VisibleText(); parser.feed(document_raw.decode("utf-8")); parser.close(); text = parser.text
        section, start, end = _section(text)
        rollforward = _rollforward(section)
        for year, row in rollforward.items():
            if year in overlap_rollforwards and overlap_rollforwards[year] != row:
                raise ValueError("annual professional-liability overlapping rollforward conflicts")
            overlap_rollforwards[year] = row
        if len(re.findall(r"average time period between the occurrence and final resolution .*? approximately five years", section, re.IGNORECASE)) != 1:
            raise ValueError("annual professional-liability resolution period missing")
        if len(re.findall(r"estimation of the timing of payments beyond a year can vary significantly", section, re.IGNORECASE)) != 1:
            raise ValueError("annual professional-liability timing limitation missing")
        facts = structural.get("facts")
        if not isinstance(facts, list):
            raise ValueError("annual professional-liability structural facts missing")

        def selected(local: str, *, instant: bool, qname: str | None = None, period: str | None = None) -> list[dict]:
            rows = [row for row in facts if (row.get("qname") == qname if qname else row.get("local_name") == local)
                    and (row.get("period_start") is None if instant else isinstance(row.get("period_start"), str))
                    and not row.get("dimensions") and (period is None or row.get("period_end") == period)]
            for row in rows:
                namespace = str(row.get("namespace", ""))
                if (row.get("unit") != "USD" or row.get("source_accession") != filing["accession"]
                    or row.get("entity_scheme") != "http://www.sec.gov/CIK" or str(row.get("entity_identifier", "")).zfill(10) != policy["cik"]
                    or isinstance(row.get("value"), bool) or not isinstance(row.get("value"), (int, float)) or not isfinite(row["value"]) or row["value"] < 0
                    or row.get("qname") != canonical.prefix(namespace) + ":" + str(row.get("local_name"))
                    or (qname and not re.fullmatch(r"https?://fasb\.org/us-gaap/20\d{2}", namespace))
                    or (not qname and not re.fullmatch(policy["issuer_namespace_pattern"], namespace))):
                    raise ValueError("annual professional-liability fact identity/value invalid")
            keyed = {}
            for row in rows:
                key = (row.get("period_start"), row.get("period_end"))
                if key in keyed and keyed[key]["value"] != row["value"]:
                    raise ValueError("annual professional-liability fact conflicts")
                keyed[key] = row
            return list(keyed.values())

        instant_specs = {
            "gross_reserve": (policy["gross_reserve_local"], None),
            "current_reserve": (policy["current_reserve_local"], None),
            "noncurrent_reserve": (policy["noncurrent_reserve_local"], None),
            "reinsurance_current_receivable": (policy["reinsurance_current_local"], None),
            "reinsurance_noncurrent_receivable": (policy["reinsurance_noncurrent_local"], None),
            "insurance_investments_total": ("", policy["total_investment_qname"]),
            "insurance_investments_current": ("", policy["current_investment_qname"]),
            "insurance_investments_noncurrent": ("", policy["noncurrent_investment_qname"]),
            "ordinary_nci": ("", policy["ordinary_nci_qname"]),
        }
        instants: dict[str, dict[str, dict]] = {}
        for name, (local, qname) in instant_specs.items():
            rows = selected(local, instant=True, qname=qname)
            if not rows:
                raise ValueError(f"annual professional-liability instant missing: {name}")
            instants[name] = {row["period_end"]: row for row in rows}
            for period, row in instants[name].items():
                key = (name, period)
                if key in overlap_instants and overlap_instants[key] != row["value"]:
                    raise ValueError("annual professional-liability overlapping instant conflicts")
                overlap_instants[key] = row["value"]
        periods = set.intersection(*(set(rows) for rows in instants.values()))
        if filing["report_date"] not in periods:
            raise ValueError("annual professional-liability current instant set incomplete")
        reconciliations = {}
        for period in sorted(periods):
            values = {name: rows[period]["value"] for name, rows in instants.items()}
            if values["gross_reserve"] != values["current_reserve"] + values["noncurrent_reserve"]:
                raise ValueError("annual professional-liability current/noncurrent reserve does not reconcile")
            if values["insurance_investments_total"] != values["insurance_investments_current"] + values["insurance_investments_noncurrent"]:
                raise ValueError("annual professional-liability investments do not reconcile")
            values["recognized_reinsurance_receivable"] = values["reinsurance_current_receivable"] + values["reinsurance_noncurrent_receivable"]
            values["net_reserve"] = values["gross_reserve"] - values["recognized_reinsurance_receivable"]
            year = period[:4]
            if year in rollforward and values["net_reserve"] != rollforward[year]["ending_net_reserve"]:
                raise ValueError("annual professional-liability net reserve disagrees with rollforward")
            reconciliations[period] = values
        flows = {}
        for name, local in (("claim_payments", policy["claim_payments_local"]), ("provision", policy["provision_local"])):
            rows = selected(local, instant=False)
            if not rows:
                raise ValueError(f"annual professional-liability flow missing: {name}")
            flows[name] = {row["period_end"][:4]: row for row in rows if row["period_start"].endswith("-01-01")}
            for year, row in flows[name].items():
                key = (name, year)
                if key in overlap_flows and overlap_flows[key] != row["value"]:
                    raise ValueError("annual professional-liability overlapping flow conflicts")
                overlap_flows[key] = row["value"]
                if year in rollforward and row["value"] != rollforward[year]["total_" + name]:
                    raise ValueError("annual professional-liability flow disagrees with rollforward")
        ocf_rows = selected("", instant=False, qname=policy["operating_cash_flow_qname"])
        operating_cash_flow = {row["period_end"][:4]: row for row in ocf_rows if row["period_start"].endswith("-01-01")}
        ownership_flows = {}
        for name, qname in (("nci_income", policy["nci_income_qname"]), ("nci_distributions", policy["nci_distributions_qname"])):
            rows = selected("", instant=False, qname=qname)
            if not rows:
                raise ValueError(f"annual ordinary-NCI flow missing: {name}")
            ownership_flows[name] = {row["period_end"][:4]: row for row in rows if row["period_start"].endswith("-01-01")}
        for year in rollforward:
            if year not in operating_cash_flow or any(year not in rows for rows in ownership_flows.values()):
                raise ValueError("annual professional-liability rollforward lacks same-period operating cash flow")
        observations.append({
            "filing": filing,
            "reconciled_balance_periods": reconciliations,
            "rollforward": rollforward,
            "flows": flows,
            "operating_cash_flow": operating_cash_flow,
            "ordinary_nci_owner_flows_nonadditive": ownership_flows,
            "timing": {"average_resolution_years": 5, "payments_beyond_one_year": "varies_significantly_no_exact_schedule"},
            "professional_liability_premiums": None,
            "section": {"name": "Professional Liability", "normalized_text_start": start, "normalized_text_end": end},
        })
        bound_sources.append({**source, "package_manifest_sha256": sha256_bytes(manifest_raw), "structural_sha256": sha256_bytes(structural_raw),
            "document_path": primary.relative_to(root).as_posix(), "document_sha256": sha256_bytes(document_raw),
            "normalized_text_sha256": sha256_bytes(text.encode()), "package_files": package_files})
    if order != sorted(order, reverse=True):
        raise ValueError("annual professional-liability sources must be latest first")
    result = {
        "version": VERSION,
        "ticker": ticker,
        "cutoff": cutoff,
        "sources": bound_sources,
        "observations": observations,
        "status": "annual_reserve_rollforward_claim_cash_and_reinsurance_verified",
        "professional_liability_premiums": None,
        "payment_timing_beyond_one_year": None,
        "claim_adjustment": None,
        "numeric_successor_issued": False,
        "review_reasons": ["professional_liability_premiums_not_separately_disclosed", "payments_beyond_one_year_have_no_exact_schedule", "current_quarter_split_and_complete_common_bridge_require_separate_reconciliation"],
    }
    result["receipt_sha256"] = sha256_bytes(canonical_json_bytes(result))
    return result


def validate_annual_professional_liability_evidence(receipt: dict, *, source_root: Path, cutoff: str) -> dict:
    if receipt.get("version") != VERSION or receipt.get("cutoff") != cutoff:
        raise ValueError("annual professional-liability version/cutoff mismatch")
    sources = [{key: row[key] for key in ("package_manifest_path", "structural_path")} for row in receipt["sources"]]
    rebuilt = extract_annual_professional_liability_evidence(receipt["ticker"], sources, source_root=source_root, cutoff=cutoff)
    if canonical_json_bytes(receipt) != canonical_json_bytes(rebuilt):
        raise ValueError("annual professional-liability source/receipt drift")
    return rebuilt


def bind_annual_professional_liability_cash(policy: dict, annual_receipt: dict, current_scope: dict, recipe: dict, *, source_root: Path, cutoff: str) -> dict:
    if policy != RULES.get(policy.get("ticker")):
        raise ValueError("annual professional-liability policy identity/version mismatch")
    annual = validate_annual_professional_liability_evidence(annual_receipt, source_root=source_root, cutoff=cutoff)
    if current_scope.get("ticker") != policy["ticker"] or current_scope.get("numeric_successor_issued") is not False:
        raise ValueError("annual/current professional-liability scope mismatch")
    latest = annual["observations"][0]
    latest_period = latest["filing"]["report_date"]
    balances = latest["reconciled_balance_periods"][latest_period]
    current_comparative = current_scope["comparative_balance_sheet_professional_liability"]
    if current_comparative["period_end"] != latest_period or current_comparative["value"] != balances["noncurrent_reserve"]:
        raise ValueError("annual/current noncurrent professional-liability balance conflicts")
    comparative_investments = current_scope["insurance_investments"]["comparative"]
    for key, annual_key in (("total", "insurance_investments_total"), ("current", "insurance_investments_current"), ("noncurrent", "insurance_investments_noncurrent")):
        if comparative_investments[key]["value"] != balances[annual_key]:
            raise ValueError("annual/current insurance investment balance conflicts")
    annual_ocf = {str(row["end"][:4]): row["value"] for row in current_scope["annual_reported_operating_cash_flow_inventory"]}
    rollforward = latest["rollforward"]
    for year in rollforward:
        if annual_ocf.get(year) != latest["operating_cash_flow"][year]["value"]:
            raise ValueError("annual/current operating cash-flow history conflicts")
    observed_payments = [rollforward[year]["total_claim_payments"] for year in sorted(rollforward)]
    expected = current_scope["claim_payment_schedule"]["next_12_month_aggregate"]
    if policy["history_payment_rule"] != "current_expected_within_observed_annual_range" or not min(observed_payments) <= expected <= max(observed_payments):
        raise ValueError("current professional-liability payment expectation is outside governed history")
    ownership = current_scope["ownership_carrying_proof"]["source_total"]
    diagnostics = {}
    for name, scenario in recipe["scenarios"].items():
        prior = current_scope["scenario_diagnostics_not_candidate"][name]
        old = scenario["inputs"]
        old_claim = old["preferred_equity"] + old["noncontrolling_interests"] - old.get("nonoperating_adjustment", 0.0)
        if prior["legacy_claim"] != old_claim or prior["approved_ownership_claim"] != ownership:
            raise ValueError("annual professional-liability predecessor scenario drift")
        diagnostics[name] = {"old_value": prior["old_value"], "retained_value": prior["reclassified_value"], "value_change": 0.0,
            "retained_noncurrent_reserve_sensitivity": prior["noncurrent_reserve_sensitivity"], "ownership_claim_retained": ownership}
    return {
        "status": "annual_claim_cash_history_verified_forward_reserve_runoff_review",
        "version": VERSION,
        "ticker": policy["ticker"],
        "annual_receipt_sha256": annual["receipt_sha256"],
        "claim_adjustment": None,
        "reserve_claim_treatment": "recurring net claim payments remain in reported cash conversion history; retain bounded noncurrent reserve sensitivity until current multi-year runoff overlap is source-reconciled",
        "historical_net_claim_payments": observed_payments,
        "current_next_12_month_expected_net_payments": expected,
        "current_net_reserve": current_scope["total_narrative_professional_reserves"],
        "latest_annual_net_reserve": balances["net_reserve"],
        "latest_annual_gross_reserve": balances["gross_reserve"],
        "latest_annual_current_reserve": balances["current_reserve"],
        "latest_annual_noncurrent_reserve": balances["noncurrent_reserve"],
        "latest_annual_recognized_reinsurance_receivable": balances["recognized_reinsurance_receivable"],
        "latest_annual_ordinary_nci": balances["ordinary_nci"],
        "current_ordinary_nci": ownership,
        "scenario_diagnostics": diagnostics,
        "professional_liability_premiums": None,
        "exact_payment_timing_beyond_one_year": None,
        "candidate_eligible_for_remaining_bridge_checks": False,
        "numeric_successor_issued": False,
        "review_reasons": ["professional_liability_premiums_not_separately_disclosed", "exact_multi_year_reserve_runoff_schedule_unavailable", "normalized_forward_ocf_does_not_explicitly_reconcile_noncurrent_reserve_runoff", "current_quarter_current_reserve_and_reinsurance_split_not_separately_tagged", "complete_cash_debt_preferred_common_bridge_still_required"],
    }
