"""Source-bound MSFT segment/intangible forecast builder.

This module stops at the pure operating forecast.  Cash, debt, preferred,
NCI, and finance-lease bridge resolution belongs to the main refresh binder;
no missing balance-sheet claim is replaced with zero here.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import json
import re
from pathlib import Path
from statistics import median
from typing import Any, Mapping

from .assumptions import derive_forecast_assumptions
from .calculation_recipe import number
from .models import fcff_dcf
from .practical_models import PRACTICAL_FCFF_STATES, _apply_operating_state
from .refresh_financials import _validate_ttm_alignment
from .xbrl import CompanyFactsNormalizer, load_concept_config


SUPPORTED_TICKER = "MSFT"


def compile_msft_approved_policy(recipe: Mapping[str, Any]) -> dict[str, Any]:
    """Compile date-independent MSFT assumptions from retained approval inputs."""
    if recipe.get("ticker") != SUPPORTED_TICKER:
        raise MSFTRefreshError("MSFT approved-policy compiler received another ticker")
    private_path = (recipe.get("provenance") or {}).get("source_path")
    if not isinstance(private_path, str) or not Path(private_path).is_file():
        raise MSFTRefreshError("MSFT approved private provenance file is unavailable at compile time")
    config_path = Path(__file__).with_name("config") / "issuer_forecasts.json"
    private_bytes = Path(private_path).read_bytes(); config_bytes = config_path.read_bytes()
    private = json.loads(private_bytes); config = json.loads(config_bytes)["issuers"]["0000789019"]
    forecast = private["practical_private"]["forecast_assumptions"]
    segments = forecast["segment_forecast"]["segments"]
    anchors = {key: float(value["evidence"]["archetype_growth_anchor"]) for key, value in segments.items()}
    # Use the retained approved model, never dictionary order in dated config.
    retained_weights = [value['evidence']['growth_weights'] for value in segments.values()]
    if not retained_weights or any(value != retained_weights[0] for value in retained_weights):
        raise MSFTRefreshError('MSFT retained segment growth weights require a per-segment policy')
    weights = deepcopy(retained_weights[0])
    return {
        "policy_version": config["forecast_policy_version"], "forecast_years": int(config["forecast_years"]), "growth_persistence": float(config["growth_persistence"]), "margin_persistence": float(config["margin_persistence"]),
        "growth_weights": weights, "sales_to_capital": float(private["diagnostic_private"]["forecast_assumptions"]["sales_to_capital"]), "archetype_median_growth": float(forecast["evidence"]["archetype_median_growth"]), "archetype_target_operating_margin": float(forecast["evidence"]["archetype_target_margin"]), "tax_normalization_window": "latest_three_annual_plus_current_ttm", "margin_normalization_window": "source_verified_latest_five_annual_history_median",
        "capital_intensity_rule": "BATCH-01-PRACTICAL-1.0:capital-intensity",
        "forecast_policy_version": config["forecast_policy_version"], "segment_axis_qname": "us-gaap:StatementBusinessSegmentsAxis",
        "segment_members": {"productivity_and_business_processes": "ProductivityAndBusinessProcessesMember", "intelligent_cloud": "IntelligentCloudMember", "more_personal_computing": "MorePersonalComputingMember"}, "segment_growth_anchors": anchors,
        "input_hashes": {"private_provenance_sha256": hashlib.sha256(private_bytes).hexdigest(), "issuer_forecasts_sha256": hashlib.sha256(config_bytes).hexdigest()},
    }


class MSFTRefreshError(ValueError):
    """Captured MSFT source cannot support a safe forecast build."""


def _records(submissions: Mapping[str, Any]) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    return [{key: values[i] for key, values in recent.items() if isinstance(values, list) and i < len(values)} for i in range(len(recent.get("accessionNumber", [])))]


def _source_row(row: Mapping[str, Any], accession: str) -> dict[str, Any]:
    return {"concept": row.get("qname"), "value": float(row["value"]), "unit": row.get("unit"), "period_start": row.get("period_start"), "period_end": row.get("period_end"), "accession": accession, "dimensions": row.get("dimensions", []), "filed_date": row.get("filed_date")}


def _structural_segments(structural: Mapping[str, Any], *, accession: str, period_end: str, filed_date: str, approved_policy: Mapping[str, Any]) -> dict[str, Any]:
    facts = structural.get("facts")
    if not isinstance(facts, list) or structural.get("source_accession") != accession:
        raise MSFTRefreshError("MSFT structural source identity/accession mismatch")
    relevant = [row for row in facts if isinstance(row, Mapping) and row.get("source_accession") == accession]
    if not relevant:
        raise MSFTRefreshError("MSFT structural source has no selected-accession facts")
    cik = "0000789019"
    if any(str(row.get("entity_identifier", "")).zfill(10) != cik or row.get("entity_scheme") != "http://www.sec.gov/CIK" for row in relevant):
        raise MSFTRefreshError("MSFT structural source issuer identity conflict")
    axis_qname = str(approved_policy.get("segment_axis_qname", ""))
    members = approved_policy.get("segment_members")
    if not axis_qname or not isinstance(members, Mapping) or set(members) != {"productivity_and_business_processes", "intelligent_cloud", "more_personal_computing"}:
        raise MSFTRefreshError("MSFT approved segment dimension policy is incomplete")
    annual_ends = sorted({str(row["period_end"]) for row in relevant if row.get("local_name") in {"RevenueFromContractWithCustomerExcludingAssessedTax", "OperatingIncomeLoss"} and row.get("period_start") and row.get("unit") == "USD" and 330 <= (date.fromisoformat(str(row["period_end"])) - date.fromisoformat(str(row["period_start"]))).days + 1 <= 385})[-3:]
    if len(annual_ends) != 3 or period_end not in annual_ends:
        raise MSFTRefreshError("MSFT segment source lacks three aligned annual periods")
    segments: dict[str, Any] = {}
    source_rows: list[dict[str, Any]] = []
    for key, member in members.items():
        revenue, operating = [], []
        for end in annual_ends:
            def pick(local: str) -> Mapping[str, Any]:
                rows = [row for row in relevant if row.get("local_name") == local and row.get("qname") == f"us-gaap:{local}" and row.get("period_end") == end and row.get("unit") == "USD" and any(str(pair[0]) == axis_qname and str(pair[1]).split(":")[-1] == str(member) for pair in (row.get("dimensions") or []))]
                if len(rows) != 1:
                    raise MSFTRefreshError(f"MSFT segment fact missing/ambiguous: {key} {local} {end}")
                return rows[0]
            rev, op = pick("RevenueFromContractWithCustomerExcludingAssessedTax"), pick("OperatingIncomeLoss")
            revenue.append(float(rev["value"])); operating.append(float(op["value"]))
            source_rows.extend([_source_row(rev, accession), _source_row(op, accession)])
        segments[key] = {"label": key.replace("_", " ").title(), "annual_revenue": revenue, "annual_operating_income": operating, "latest_ytd_revenue": revenue[-1], "prior_ytd_revenue": revenue[-2], "latest_ytd_operating_income": operating[-1], "prior_ytd_operating_income": operating[-2], "ttm_revenue": revenue[-1], "ttm_operating_income": operating[-1]}
    consolidated: dict[str, float] = {}
    for local, key in (("RevenueFromContractWithCustomerExcludingAssessedTax", "revenue"), ("OperatingIncomeLoss", "operating_income")):
        rows = [row for row in relevant if row.get("local_name") == local and row.get("period_end") == period_end and row.get("period_start") and not row.get("dimensions") and row.get("unit") == "USD"]
        values = {float(row["value"]) for row in rows}
        if len(values) != 1:
            raise MSFTRefreshError(f"MSFT consolidated {local} fact missing/ambiguous")
        consolidated[key] = next(iter(values))
    totals = {key: sum(segment[f"ttm_{key}"] for segment in segments.values()) for key in ("revenue", "operating_income")}
    if any(abs(totals[key] - consolidated[key]) / max(abs(consolidated[key]), 1.0) > 0.001 for key in totals):
        raise MSFTRefreshError("MSFT segment totals do not reconcile to consolidated source facts")
    rd = [_source_row(row, accession) for row in relevant if row.get("local_name") in {"ResearchAndDevelopmentExpense", "FinitelivedIntangibleAssetsAcquired1", "AcquisitionsNetOfCashAcquiredAndPurchasesOfIntangibleAndOtherAssets"} and row.get("period_end") == period_end and row.get("period_start") and not row.get("dimensions")]
    return {"status": "reconciled", "accession": accession, "period_end": period_end, "filed_date": filed_date, "annual_periods": annual_ends, "segments": segments, "consolidated_ttm": consolidated, "source_rows": source_rows, "rd_intangible_sources": rd, "rd_policy": "reported R&D/intangible rows are diagnostic; segment operating income already captures reported segment economics and no unapproved asset-life capitalization is applied", "segment_axis_qname": axis_qname, "segment_members": dict(members)}


def _financials(packet: Mapping[str, Any], *, cutoff: str, controlling: Mapping[str, Any]) -> tuple[CompanyFactsNormalizer, dict[str, Any], float]:
    submissions, companyfacts = packet["submissions"], packet["companyfacts"]
    records = _records(submissions)
    normalizer = CompanyFactsNormalizer(companyfacts, concept_config=load_concept_config(), fiscal_year_end=submissions.get("fiscalYearEnd"), as_of_date=cutoff, filing_records=records)
    fields = ("revenue", "operating_income", "capital_expenditures", "operating_cash_flow", "pretax_income", "income_tax")
    annual = {field: normalizer.annual_series(field, 5) for field in fields}
    if any(len(rows) < 3 for rows in annual.values()):
        raise MSFTRefreshError("MSFT standardized annual source history is incomplete")
    by_end = {field: {fact.end: fact for fact in rows} for field, rows in annual.items()}
    common_ends = sorted(set.intersection(*(set(values) for values in by_end.values())))[-5:]
    if len(common_ends) < 3:
        raise MSFTRefreshError("MSFT annual source fields have no aligned period intersection")
    current = {field: normalizer.ttm_flow(field) for field in fields}
    for flow in current.values():
        try:
            _validate_ttm_alignment(flow)
        except ValueError as exc:
            raise MSFTRefreshError(str(exc)) from exc
    if any(value["period_end"] != controlling["reportDate"] for value in current.values()):
        raise MSFTRefreshError("MSFT standardized current source periods are not aligned")
    pretax, tax = normalizer.ttm_flow("pretax_income"), normalizer.ttm_flow("income_tax")
    if float(pretax["value"]) <= 0 or not (0.0 <= float(tax["value"]) / float(pretax["value"]) <= 0.30):
        raise MSFTRefreshError("MSFT source tax rate is outside the approved normalized band")
    current_tax_rate = float(tax["value"]) / float(pretax["value"])
    annual_tax_rates = []
    tax_history_ends = sorted((set(by_end["pretax_income"]) & set(by_end["income_tax"])) - {str(controlling["reportDate"])})[-3:]
    for end in tax_history_ends:
        pretax_value, tax_value = float(by_end["pretax_income"][end].value), float(by_end["income_tax"][end].value)
        if pretax_value > 0:
            annual_tax_rates.append({"period_end": end, "rate": tax_value / pretax_value, "pretax": by_end["pretax_income"][end].as_dict(), "tax": by_end["income_tax"][end].as_dict()})
    if len(annual_tax_rates) < 3:
        raise MSFTRefreshError("MSFT approved tax normalization needs three annual constituents")
    from statistics import median
    tax_rate = float(median([row["rate"] for row in annual_tax_rates] + [current_tax_rate]))
    annual_rows = []
    for end in common_ends:
        row = {"fiscal_year": by_end["revenue"][end].fiscal_year, "period_end": end, "values": {}, "sources": {}}
        for field in fields:
            fact = by_end[field][end]
            row["values"][field] = fact.value
            row["sources"][field] = fact.as_dict()
        annual_rows.append(row)
    financials = {
        "annual": annual_rows,
        "ttm": {"period_end": controlling["reportDate"], "source_cutoff_date": cutoff, "controlling_filing": {"accession": controlling["accessionNumber"], "form": controlling["form"], "report_date": controlling["reportDate"], "filing_date": controlling["filingDate"]}, "values": {field: current[field]["value"] for field in fields}, "sources": current},
        "normalized": {"revenue_ttm_history": [{"period_end": row["period_end"], "value": row["values"]["revenue"]} for row in annual_rows], "tax_rate": tax_rate, "tax_rate_constituents": {"annual": annual_tax_rates, "current_ttm": {"period_end": controlling["reportDate"], "rate": current_tax_rate, "pretax": pretax, "tax": tax}}},
    }
    return normalizer, financials, tax_rate


def _structural_interim_segments(structural: Mapping[str, Any], *, accession: str, period_end: str, approved_policy: Mapping[str, Any]) -> dict[str, Any]:
    """Select current and comparable prior-YTD segment facts from a 10-Q."""
    facts = structural.get("facts")
    if not isinstance(facts, list) or structural.get("source_accession") != accession:
        raise MSFTRefreshError("MSFT interim structural source identity/accession mismatch")
    axis_qname = str(approved_policy["segment_axis_qname"]); members = approved_policy["segment_members"]
    relevant = [row for row in facts if isinstance(row, Mapping) and row.get("source_accession") == accession]
    if any(str(row.get("entity_identifier", "")).zfill(10) != "0000789019" or row.get("entity_scheme") != "http://www.sec.gov/CIK" for row in relevant):
        raise MSFTRefreshError("MSFT interim structural source issuer identity conflict")
    segments: dict[str, Any] = {}
    starts_seen: set[str] = set(); source_rows: list[dict[str, Any]] = []
    for key, member in members.items():
        def candidates(local: str) -> list[Mapping[str, Any]]:
            return [row for row in relevant if row.get("local_name") == local and row.get("qname") == f"us-gaap:{local}" and row.get("period_end") == period_end and row.get("period_start") and row.get("unit") == "USD" and any(str(pair[0]) == axis_qname and str(pair[1]).split(":")[-1] == str(member) for pair in (row.get("dimensions") or []))]
        rev_rows, op_rows = candidates("RevenueFromContractWithCustomerExcludingAssessedTax"), candidates("OperatingIncomeLoss")
        if not rev_rows or not op_rows:
            raise MSFTRefreshError(f"MSFT interim segment facts missing: {key}")
        current_start = max((str(row["period_start"]) for row in rev_rows), key=lambda start: (date.fromisoformat(period_end) - date.fromisoformat(start)).days)
        current_rev = [row for row in rev_rows if row["period_start"] == current_start]; current_op = [row for row in op_rows if row["period_start"] == current_start]
        if len(current_rev) != 1 or len(current_op) != 1:
            raise MSFTRefreshError(f"MSFT interim current segment facts ambiguous: {key}")
        current_days = (date.fromisoformat(period_end) - date.fromisoformat(current_start)).days
        prior = [row for row in relevant if row.get("local_name") in {"RevenueFromContractWithCustomerExcludingAssessedTax", "OperatingIncomeLoss"} and row.get("qname") in {"us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "us-gaap:OperatingIncomeLoss"} and row.get("period_start") and row.get("period_end") < period_end and row.get("period_end") and row.get("unit") == "USD" and abs((date.fromisoformat(str(row["period_end"])) - date.fromisoformat(str(row["period_start"]))).days - current_days) <= 8 and any(str(pair[0]) == axis_qname and str(pair[1]).split(":")[-1] == str(member) for pair in (row.get("dimensions") or []))]
        prior_rev = [row for row in prior if row.get("local_name") == "RevenueFromContractWithCustomerExcludingAssessedTax"]; prior_op = [row for row in prior if row.get("local_name") == "OperatingIncomeLoss"]
        if len(prior_rev) != 1 or len(prior_op) != 1:
            raise MSFTRefreshError(f"MSFT interim comparable segment facts missing/ambiguous: {key}")
        starts_seen.add(str(current_start))
        segments[key] = {"current_start": current_start, "current_end": period_end, "prior_start": prior_rev[0]["period_start"], "prior_end": prior_rev[0]["period_end"], "current_revenue": float(current_rev[0]["value"]), "prior_revenue": float(prior_rev[0]["value"]), "current_operating_income": float(current_op[0]["value"]), "prior_operating_income": float(prior_op[0]["value"]), "segment_member": member}
        source_rows.extend([_source_row(current_rev[0], accession), _source_row(prior_rev[0], accession), _source_row(current_op[0], accession), _source_row(prior_op[0], accession)])
    if len(starts_seen) != 1:
        raise MSFTRefreshError("MSFT interim segment durations are not aligned")
    consolidated: dict[str, float] = {}
    for local, key in (("RevenueFromContractWithCustomerExcludingAssessedTax", "revenue"), ("OperatingIncomeLoss", "operating_income")):
        rows = [row for row in relevant if row.get("local_name") == local and row.get("qname") == f"us-gaap:{local}" and row.get("period_end") == period_end and row.get("period_start") and not row.get("dimensions") and row.get("unit") == "USD"]
        if not rows: raise MSFTRefreshError(f"MSFT interim consolidated {local} fact missing")
        longest = max(rows, key=lambda row: (date.fromisoformat(period_end) - date.fromisoformat(str(row["period_start"]))).days)
        same = [row for row in rows if row.get("period_start") == longest.get("period_start")]
        values = {float(row["value"]) for row in same}
        if len(values) != 1: raise MSFTRefreshError(f"MSFT interim consolidated {local} fact ambiguous")
        consolidated[key] = next(iter(values))
    prior_end = next(iter(segments.values()))["prior_end"]; prior_start = next(iter(segments.values()))["prior_start"]
    prior_consolidated: dict[str, float] = {}
    for local, key in (("RevenueFromContractWithCustomerExcludingAssessedTax", "revenue"), ("OperatingIncomeLoss", "operating_income")):
        rows = [row for row in relevant if row.get("local_name") == local and row.get("qname") == f"us-gaap:{local}" and row.get("period_end") == prior_end and row.get("period_start") == prior_start and not row.get("dimensions") and row.get("unit") == "USD"]
        values = {float(row["value"]) for row in rows}
        if len(values) != 1: raise MSFTRefreshError(f"MSFT interim prior consolidated {local} fact missing/ambiguous")
        prior_consolidated[key] = next(iter(values))
    current_segment_totals = {key: sum(segment[f"current_{key}"] for segment in segments.values()) for key in ("revenue", "operating_income")}
    prior_segment_totals = {key: sum(segment[f"prior_{key}"] for segment in segments.values()) for key in ("revenue", "operating_income")}
    if any(abs(current_segment_totals[key] - consolidated[key]) / max(abs(consolidated[key]), 1.0) > 0.001 for key in consolidated):
        raise MSFTRefreshError("MSFT current comparable-YTD segment totals do not reconcile to consolidated facts")
    if any(abs(prior_segment_totals[key] - prior_consolidated[key]) / max(abs(prior_consolidated[key]), 1.0) > 0.001 for key in prior_consolidated):
        raise MSFTRefreshError("MSFT prior comparable-YTD segment totals do not reconcile to consolidated facts")
    return {"status": "interim_reconciled", "accession": accession, "period_end": period_end, "segments": segments, "consolidated_ytd": consolidated, "prior_consolidated": prior_consolidated, "current_segment_totals": current_segment_totals, "prior_segment_totals": prior_segment_totals, "prior_period_end": prior_end, "prior_period_start": prior_start, "source_rows": source_rows, "period_comparison_basis": "ytd", "period_start": next(iter(starts_seen))}


def _build_evidence(segments: Mapping[str, Any], *, controlling: Mapping[str, Any], approved_policy: Mapping[str, Any]) -> dict[str, Any]:
    """Build the exact provenance envelope required by derive_forecast_assumptions."""
    paths = ["consolidated_ttm.revenue", "consolidated_ttm.operating_income"]
    values = {paths[0]: segments["consolidated_ttm"]["revenue"], paths[1]: segments["consolidated_ttm"]["operating_income"]}
    for key, segment in segments["segments"].items():
        for field in ("annual_revenue", "annual_operating_income"):
            for index, value in enumerate(segment[field]):
                path = f"segments.{key}.{field}[{index}]"; paths.append(path); values[path] = value
        for field in ("latest_ytd_revenue", "prior_ytd_revenue", "latest_ytd_operating_income", "prior_ytd_operating_income", "ttm_revenue", "ttm_operating_income", "archetype_growth_anchor"):
            path = f"segments.{key}.{field}"; paths.append(path); values[path] = segment[field]
    source = {"id": "selected_controlling_filing", "accession": controlling.get("accessionNumber") or controlling.get("accession"), "form": controlling.get("form"), "period_end": controlling.get("reportDate") or controlling.get("period_end"), "filing_date": controlling.get("filingDate") or controlling.get("filing_date"), "evidence": "Extracted from selected structural filing segment table"}
    context = {"source_ids": ["selected_controlling_filing"], "fiscal_year": "policy-selected", "fiscal_period": "FY", "duration_basis": "annual", "unit": "USD", "table_line": "Reportable segment revenue/operating income", "status": "source_structural_filing", "derivation": "exact selected QName and governed segment dimension"}
    comparison_basis = segments.get("period_comparison_basis", "annual")
    return {"forecast_mode": "segment_operating_income", "period_comparison_basis": comparison_basis, "periods": {segments["period_end"]: {"evidence_period_end": segments["period_end"], "as_of_filed_date": segments["filed_date"], "segments": segments["segments"], "consolidated_ttm": segments["consolidated_ttm"], "growth_weights": deepcopy(approved_policy["growth_weights"]), "forecast_years": approved_policy["forecast_years"], "growth_persistence": approved_policy["growth_persistence"], "margin_persistence": approved_policy["margin_persistence"], "forecast_policy_version": approved_policy["forecast_policy_version"], "evidence_status": "source_structural_filing", "sources": [source], "field_provenance": {path: "selected_context" for path in paths}, "provenance_contexts": {"selected_context": context}, "field_source_values": values}}, "forecast_policy_version": approved_policy["forecast_policy_version"]}


def _select_msft_shares(structural: Mapping[str, Any], *, accession: str, period_end: str) -> Mapping[str, Any]:
    facts = structural.get("facts")
    if not isinstance(facts, list):
        raise MSFTRefreshError("MSFT share source facts are missing")
    rows = [
        row for row in facts
        if isinstance(row, Mapping)
        and row.get("local_name") == "WeightedAverageNumberOfDilutedSharesOutstanding"
        and row.get("qname") == "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"
        and re.fullmatch(r"https?://fasb\.org/us-gaap/20\d{2}", str(row.get("namespace", "")))
        and row.get("source_accession") == accession
        and row.get("entity_identifier") == "0000789019"
        and row.get("entity_scheme") == "http://www.sec.gov/CIK"
        and row.get("period_end") == period_end
        and row.get("period_start")
        and row.get("unit") == "xbrli:shares"
        and row.get("dimensions") in ([], None)
        and isinstance(row.get("value"), (int, float))
    ]
    if not rows:
        raise MSFTRefreshError("MSFT current diluted-share fact is missing or has the wrong QName/namespace")
    starts = sorted({str(row["period_start"]) for row in rows}, key=lambda start: (date.fromisoformat(period_end) - date.fromisoformat(start)).days, reverse=True)
    selected_start = starts[0]
    selected = [row for row in rows if str(row["period_start"]) == selected_start]
    unique = {(float(row["value"]), row.get("context_id"), row.get("qname")): row for row in selected}
    values = {float(row["value"]) for row in selected}
    if len(values) != 1 or not unique:
        raise MSFTRefreshError("MSFT current diluted-share facts conflict for the selected duration")
    return next(iter(unique.values()))


def build_msft_forecast(packet: Mapping[str, Any], recipe: Mapping[str, Any], *, cutoff: str, approved_policy: Mapping[str, Any]) -> dict[str, Any]:
    """Build the source-bound unbridged MSFT segment forecast and model traces."""
    if recipe.get("ticker") != SUPPORTED_TICKER:
        raise MSFTRefreshError("MSFT forecast builder received another ticker")
    controlling = packet.get("_selected_controlling_filing") or packet.get("controlling_filing")
    if not isinstance(controlling, Mapping):
        raise MSFTRefreshError("MSFT selected controlling filing is missing")
    structural = packet.get("structural_filing")
    is_interim = str(controlling.get("form", "")) in {"10-Q", "10-Q/A"}
    if is_interim:
        annual_structural = packet.get("annual_structural_filing")
        if not isinstance(annual_structural, Mapping) or not isinstance(structural, Mapping) or annual_structural.get("source_accession") == structural.get("source_accession"):
            raise MSFTRefreshError("MSFT interim binding requires a distinct captured annual structural package plus current/prior comparable-YTD structural facts")
        annual_filing = packet.get("latest_annual_filing")
        if not isinstance(annual_filing, Mapping):
            raise MSFTRefreshError("MSFT interim binding requires annual filing metadata")
        annual = _structural_segments(annual_structural, accession=str(annual_filing.get("accessionNumber") or annual_filing.get("accession")), period_end=str(annual_filing.get("reportDate") or annual_filing.get("period_end")), filed_date=str(annual_filing.get("filingDate") or annual_filing.get("filing_date")), approved_policy=approved_policy)
        interim = _structural_interim_segments(structural, accession=str(controlling.get("accessionNumber") or controlling.get("accession")), period_end=str(controlling.get("reportDate") or controlling.get("period_end")), approved_policy=approved_policy)
        segments = deepcopy(annual)
        segments["status"] = "annual_plus_comparable_ytd_reconciled"
        segments["period_comparison_basis"] = "ytd"
        segments["interim_source"] = interim
        for key, seg in segments["segments"].items():
            current = interim["segments"][key]
            if not 1 <= (date.fromisoformat(current['current_start']) - date.fromisoformat(annual['period_end'])).days <= 8:
                raise MSFTRefreshError('MSFT segment annual and current YTD are not contiguous')
            if current['prior_end'] > annual['period_end'] or not 350 <= (date.fromisoformat(current['current_start']) - date.fromisoformat(current['prior_start'])).days <= 380:
                raise MSFTRefreshError('MSFT segment comparative YTD is not the preceding fiscal year')
            seg["latest_ytd_revenue"] = current["current_revenue"]; seg["prior_ytd_revenue"] = current["prior_revenue"]
            seg["latest_ytd_operating_income"] = current["current_operating_income"]; seg["prior_ytd_operating_income"] = current["prior_operating_income"]
            seg["ttm_revenue"] = seg["annual_revenue"][-1] + current["current_revenue"] - current["prior_revenue"]
            seg["ttm_operating_income"] = seg["annual_operating_income"][-1] + current["current_operating_income"] - current["prior_operating_income"]
        segments["consolidated_ttm"] = {"revenue": annual["consolidated_ttm"]["revenue"] + interim["consolidated_ytd"]["revenue"] - interim["prior_consolidated"]["revenue"], "operating_income": annual["consolidated_ttm"]["operating_income"] + interim["consolidated_ytd"]["operating_income"] - interim["prior_consolidated"]["operating_income"]}
        segments["period_end"] = str(controlling.get("reportDate")); segments["filed_date"] = str(controlling.get("filingDate")); segments["accession"] = str(controlling.get("accessionNumber") or controlling.get("accession")); segments["source_rows"] = annual["source_rows"] + interim["source_rows"]
    else:
        segments = _structural_segments(structural, accession=str(controlling.get("accessionNumber") or controlling.get("accession")), period_end=str(controlling.get("reportDate") or controlling.get("period_end")), filed_date=str(controlling.get("filingDate") or controlling.get("filing_date")), approved_policy=approved_policy)
    normalizer, financials, tax_rate = _financials(packet, cutoff=cutoff, controlling=controlling)
    for key in segments["segments"]:
        if key not in approved_policy["segment_growth_anchors"]:
            raise MSFTRefreshError(f"MSFT approved policy lacks segment anchor: {key}")
        segments["segments"][key]["archetype_growth_anchor"] = float(approved_policy["segment_growth_anchors"][key])
    evidence = _build_evidence(segments, controlling=controlling, approved_policy=approved_policy)
    policy = {key: approved_policy[key] for key in ("forecast_years", "growth_persistence", "margin_persistence", "sales_to_capital", "archetype_median_growth", "archetype_target_operating_margin")}
    discount = {"wacc": float(recipe["scenarios"]["base"]["inputs"]["discount_rate"])}
    normalized = derive_forecast_assumptions(financials, policy=policy, discount_rate=discount, issuer_evidence=evidence)
    shares = _select_msft_shares(structural, accession=str(controlling.get("accessionNumber") or controlling.get("accession")), period_end=segments["period_end"])
    financials["balance_sheet"] = {"cash_and_nonoperating_investments": 0.0, "total_interest_bearing_debt": 0.0, "preferred_equity": 0.0, "noncontrolling_interests": 0.0, "fully_diluted_shares_proxy": float(shares["value"])}
    # Preserve the approved Batch 01 rule, not its prior source-derived result.
    annual_capex_ratios = [row["values"]["capital_expenditures"] / row["values"]["revenue"] for row in financials["annual"] if row["values"]["capital_expenditures"] > 0 and row["values"]["revenue"] > 0]
    current_revenue = financials["ttm"]["values"]["revenue"]
    current_capex = financials["ttm"]["values"]["capital_expenditures"]
    if len(annual_capex_ratios) < 3 or current_revenue <= 0 or current_capex <= 0:
        raise MSFTRefreshError("MSFT capital intensity needs positive current and three annual capex/revenue observations")
    historical_ratio = float(median(annual_capex_ratios[-5:]))
    current_ratio = current_capex / current_revenue
    base_multiplier = min(1.25, max(0.50, historical_ratio / current_ratio))
    multipliers = {"bear": max(0.35, base_multiplier * 0.75), "base": base_multiplier, "bull": min(1.25, base_multiplier * 1.10)}
    segments["capital_intensity"] = {"rule": approved_policy["capital_intensity_rule"], "unadjusted_sales_to_capital": policy["sales_to_capital"], "annual_ratios": annual_capex_ratios, "historical_median": historical_ratio, "current_ratio": current_ratio, "scenario_multipliers": multipliers}
    scenarios = {}
    for name in ("bear", "base", "bull"):
        assumptions = deepcopy(normalized)
        state = {"growth_delta": PRACTICAL_FCFF_STATES[name]["growth_delta"], "margin_delta": PRACTICAL_FCFF_STATES[name]["margin_delta"], "capital_efficiency_multiplier": multipliers[name]}
        _apply_operating_state(assumptions, **state)
        assumptions["terminal_growth"] = float(recipe["scenarios"][name]["inputs"]["terminal_growth"])
        assumptions["terminal_marginal_roic"] = float(recipe["scenarios"][name]["inputs"]["discount_rate"])
        model = fcff_dcf(assumptions=assumptions, discount_rate={"wacc": float(recipe["scenarios"][name]["inputs"]["discount_rate"])}, financials={"balance_sheet": financials["balance_sheet"]})
        if model.get("errors"):
            raise MSFTRefreshError("MSFT pure segment forecast rejected assumptions: " + "; ".join(model["errors"]))
        scenarios[name] = {"model": model, "assumptions": assumptions}
    return {"status": "forecast_bound_unbridged", "ticker": "MSFT", "source_ledger": {"controlling_filing": controlling, "segment_evidence": segments, "input_ledger": {"annual_segment_rows": segments["source_rows"], "interim_segment_rows": segments.get("interim_source", {}).get("source_rows", []), "annual_source_accession": segments["source_rows"][0]["accession"] if segments["source_rows"] else None, "interim_source_accession": segments.get("interim_source", {}).get("accession"), "reconciliation_basis": segments.get("period_comparison_basis", "annual")}, "tax_rate": tax_rate, "tax_normalization": financials["normalized"]["tax_rate_constituents"], "r_and_d_treatment": segments["rd_policy"], "share_source": _source_row(shares, str(controlling.get("accessionNumber") or controlling.get("accession")))}, "normalized_assumptions": normalized, "scenarios": scenarios, "bridge_deferred": True, "bridge_note": "Cash/debt/preferred/NCI/finance-lease bridge is intentionally excluded and must be resolved by the main binder."}


__all__ = ["MSFTRefreshError", "build_msft_forecast", "compile_msft_approved_policy"]
