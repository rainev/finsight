"""Source-bounded practical REIT baselines for controlled Universe Reset Batch 49."""
from __future__ import annotations

import hashlib
import json
from html import unescape
from pathlib import Path
import re
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_04_launch_first import _controlling
from .batch_49 import BATCH_49_TICKERS, BATCH_49_VALUATION_DATE
from .batch_49_sources import verify_source_bundle
from .practical_models import two_stage_cash_flow_value
from .reliability import assess_reliability

BATCH_49_HISTORY_VERSION = "BATCH-49-REIT-AFFO-1.0"
PERIOD = "2026-06-30"
PASS_TICKERS = frozenset()
WITHHELD_TICKERS = frozenset({"AVB"})
CONDITIONAL_TICKERS = frozenset(set(BATCH_49_TICKERS) - WITHHELD_TICKERS)

INPUTS: dict[str, dict[str, Any]] = {
    "REG": {"accession": "0001193125-26-323784", "document": "reg-ex99_1.htm", "metric": "2026 Core Operating Earnings per diluted share", "metric_pattern": r"core operating earnings per diluted share.{0,500}4\.62.{0,100}4\.66", "flow": (4.62, 4.64, 4.66), "cost": (0.13, 1 - 382.874 / 434.253, 0.105), "basis": "H1 reported AFFO 382.874m divided by H1 Core Operating Earnings 434.253m; timing is bounded.", "cost_source": {"reported_affo": 382_874_000.0, "reported_core_operating_earnings": 434_253_000.0, "formula": "1 - H1 AFFO / H1 Core Operating Earnings", "unit": "ratio"}},
    "MAA": {"accession": "0001193125-26-323756", "document": "maa-ex99_2.htm", "metric": "2026 Core AFFO per diluted share", "metric_pattern": r"core affo per share.{0,300}7\.38.{0,100}7\.62", "flow": (7.38, 7.50, 7.62), "cost": (0.0, 0.0, 0.0), "basis": "Issuer-reported Core AFFO already deducts recurring capital; no second deduction.", "cost_source": {"guidance_recurring_capital_per_share": 1.03, "treatment": "Already deducted in reported Core AFFO guidance", "unit": "USD/share"}},
    "ESS": {"accession": "0001140361-26-030060", "document": "ef20078746_ex99-1.htm", "metric": "2026 Core FFO per diluted share", "metric_pattern": r"core ffo per diluted share.{0,500}16\.03.{0,100}16\.25", "flow": (16.03, 16.14, 16.25), "cost": (0.12, (111.904 / 66.575) / 16.14, 0.09), "basis": "Trailing-four-quarter non-revenue-generating capital 111.904m divided by 66.575m diluted shares and 2026 Core FFO midpoint.", "cost_source": {"trailing_four_quarter_nonrevenue_capital": 111_904_000.0, "diluted_shares": 66_575_000.0, "core_ffo_guidance_midpoint": 16.14, "formula": "capital / shares / Core FFO midpoint", "unit": "ratio"}},
    "SBAC": {"accession": "0001193125-26-330639", "document": "d154311dex991.htm", "metric": "2026 AFFO attributable to SBA per diluted share", "metric_pattern": r"affo attributable to sba communications corporation.{0,500}11\.91.{0,100}12\.36", "flow": (11.91, 12.135, 12.36), "cost": (0.0, 0.0, 0.0), "basis": "Issuer-reported parent-attributable AFFO already includes non-discretionary capital; no second deduction.", "cost_source": {"non_discretionary_capital_guidance": (65_000_000.0, 75_000_000.0), "treatment": "Already deducted in reported AFFO guidance", "unit": "USD"}},
    "ARE": {"accession": "0001035443-26-000067", "document": "a2q26ex991supp.htm", "metric": "2026 FFO as adjusted per diluted share", "metric_pattern": r"funds from operations per share.{0,100}adjusted.{0,500}6\.35.{0,100}6\.45", "flow": (6.35, 6.40, 6.45), "cost": (0.13, 0.11, 0.09), "basis": "Five-quarter non-revenue-enhancing capital evidence supports the Batch 48 governed 9-13% recurring-cost range.", "cost_source": {"building_improvements_quarterly_millions": (4.600, 3.357, 4.372, 3.948, 4.622), "tenant_improvements_and_leasing_quarterly_millions": (28.042, 22.811, 26.494, 16.707, 23.971), "treatment": "Governed 9-13% range around reported non-revenue-enhancing capital", "unit": "USD millions"}},
    "BXP": {"accession": "0001037540-26-000031", "document": "q22026supplemental.htm", "metric": "2026 projected FFO per diluted share", "metric_pattern": r"projected ffo per share.{0,500}6\.99.{0,100}7\.05", "flow": (6.99, 7.02, 7.05), "cost": (0.34, (153.008 + 14.617) / 535.798, 0.28), "basis": "H1 BXP-share second-generation tenant improvements/leasing commissions plus maintenance capital divided by BXP Inc. diluted FFO attributable to common.", "cost_source": {"h1_second_generation_ti_and_leasing": 153_008_000.0, "h1_maintenance_capital": 14_617_000.0, "h1_bxp_diluted_ffo": 535_798_000.0, "h1_bxp_diluted_ffo_components": (283_506_000.0, 252_292_000.0), "formula": "(BXP-share TI and leasing + maintenance capital) / BXP Inc. diluted FFO", "unit": "ratio"}},
    "PLD": {"accession": "0001193125-26-305416", "document": "pld-ex99_1.htm", "metric": "2026 Core FFO per diluted share", "metric_pattern": r"core ffo attributable to common stockholders/unitholders.{0,500}6\.22.{0,100}6\.30", "flow": (6.22, 6.26, 6.30), "cost": (0.08, 1 - 2_794.860 / 2_999.620, 0.055), "basis": "H1 reported AFFO divided by H1 Core FFO; development/property-sale gains remain separately identified.", "cost_source": {"h1_affo": 2_794_860_000.0, "h1_core_ffo": 2_999_620_000.0, "formula": "1 - H1 AFFO / H1 Core FFO", "unit": "ratio"}},
    "CCI": {"accession": "0001051470-26-000069", "document": "q22026earningsrelease.htm", "metric": "2026 continuing-operations AFFO per diluted share", "metric_pattern": r"affo per share.{0,500}4\.53.{0,100}4\.65", "flow": (4.53, 4.59, 4.65), "cost": (0.0, 0.0, 0.0), "basis": "Issuer-reported pure-play tower AFFO after the completed Fiber/Small Cell sale; no second sustaining-capex deduction.", "cost_source": {"sustaining_capital_guidance": (25_000_000.0, 45_000_000.0), "treatment": "Already deducted in continuing-operations AFFO", "unit": "USD"}},
    "EQIX": {"accession": "0001101239-26-000145", "document": "a991eqix-q226xpr.htm", "metric": "2026 AFFO per diluted share", "metric_pattern": r"affo per share.{0,500}42\.69.{0,100}43\.29", "flow": (42.69, 42.99, 43.29), "cost": (0.0, 0.0, 0.0), "basis": "Issuer-reported AFFO already deducts recurring capital; non-recurring data-center expansion capex remains a warning.", "cost_source": {"recurring_capital_guidance": (290_000_000.0, 310_000_000.0), "nonrecurring_capital_guidance": (4_710_000_000.0, 5_690_000_000.0), "treatment": "Recurring capital already deducted in AFFO; expansion capital stays outside as a specialist warning", "unit": "USD"}},
}

WARNINGS = {
    "REG": "Conditional Low retail-REIT AFFO proxy. The reported H1 AFFO/Core Operating Earnings conversion is applied to current guidance; preferred stock, development, acquisitions and partnership scope remain material.",
    "MAA": "Conditional Low multifamily-REIT Core AFFO baseline. Reported guidance includes recurring capital, but development, lease-up, dispositions, Series I preferred economics, the $300M third-quarter bond maturity/refinancing and Sunbelt operating conditions remain material.",
    "AVB": "Withheld: AvalonBay shareholders approved the EQR merger on August 12 with closing expected August 17. Only standalone operating guidance remained, while no cutoff-safe combined AFFO or final closing bridge existed on August 14.",
    "ESS": "Conditional Low multifamily-REIT AFFO proxy. Core FFO is reduced by trailing non-revenue capital; West Coast rents, insurance, development, concessions and dispositions remain material.",
    "SBAC": "Conditional Low tower-REIT AFFO baseline. Parent-attributable guidance is used after the Canada sale; tenant churn, foreign operations, refinancing, discretionary capex and repurchases remain material.",
    "ARE": "Conditional Low life-science/office REIT AFFO proxy. FFO as adjusted is reduced by bounded non-revenue capital; lab leasing, vacancy, construction, dispositions and the August junior-subordinated notes remain material.",
    "BXP": "Conditional Low office-REIT AFFO proxy. FFO is reduced by source-linked second-generation leasing and maintenance capital; occupancy, concessions, development, refinancing and JV scope remain material.",
    "PLD": "Conditional Low industrial-REIT AFFO proxy. H1 reported AFFO/Core FFO conversion is applied to guidance; strategic capital, development, land gains, turnover costs and co-investment ownership remain material.",
    "CCI": "Conditional Low pure-play tower AFFO baseline. Current guidance follows the completed Fiber and Small Cell sale; DISH/Sprint churn, sustaining capex, leverage and post-sale cash deployment remain material.",
    "EQIX": "Conditional Low data-center REIT AFFO baseline. Reported AFFO includes recurring capital, but large expansion capex, power/interconnection commitments, leases, foreign/JV scope and August debt issuance remain material.",
}

EVENT_TREATMENTS = {
    "REG": "July guidance follows reported acquisitions/development; August dividend declarations and governance events add no separate value.",
    "MAA": "July corrected operating guidance and August capital-markets update are context; the $300M third-quarter bond maturity remains a refinancing warning, and no future development value or unissued financing is added.",
    "AVB": "August 12 approval and 2.793 exchange ratio remain a hard economic-object gate; no post-cutoff Vivmark state is substituted.",
    "ESS": "July earnings and updated guidance define the cutoff operating state; future development and dispositions are not capitalized.",
    "SBAC": "July refinancing and Canada-sale effects are consumed through parent-attributable AFFO guidance; no debt proceeds or nonrecurring tax benefit is added twice.",
    "ARE": "August $1bn junior-subordinated note pricing is recorded as post-guidance financing context; no proceeds or refinancing benefit is added to AFFO value.",
    "BXP": "July earnings and leasing-capital evidence define the current office baseline; no unclosed development or disposition value is added.",
    "PLD": "July guidance and August financing/governance filings are recorded; development gains and co-investment values are not added outside AFFO.",
    "CCI": "The May 1 Fiber/Small Cell sale is reflected in July continuing-operations AFFO guidance; sale proceeds are not added as surplus value.",
    "EQIX": "August note issuance/refinancing is recorded; proceeds and debt are not separately bridged into the equity-level AFFO value.",
}


def _events(ticker: str, root: Path, manifest_sha: str) -> dict[str, Any]:
    inventory = root / ticker / "inventory.json"
    rows = json.loads(inventory.read_text())
    if not rows or any(row.get("filed", "") > BATCH_49_VALUATION_DATE for row in rows):
        raise ValueError(f"{ticker}: invalid event inventory")
    documents = []
    for row in rows:
        for document in row.get("documents", []):
            path = Path(document["path"])
            if not path.is_absolute():
                path = root.parent.parent / path
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != document.get("sha256"):
                raise ValueError(f"{ticker}: event hash mismatch")
            documents.append({**document, "accession": row["accession"], "filed": row["filed"], "form": row["form"]})
    return {"source_kind": "sec_event_screening", "screened_filings": rows, "documents": documents, "inventory_sha256": hashlib.sha256(inventory.read_bytes()).hexdigest(), "source_manifest_sha256": manifest_sha, "treatment": EVENT_TREATMENTS[ticker], "reported_vs_estimated": "reported_and_screened"}


def _specialist_source(ticker: str, event: dict[str, Any], event_root: Path) -> dict[str, Any]:
    spec = INPUTS[ticker]
    matches = [row for row in event["documents"] if row["accession"] == spec["accession"] and Path(row["path"]).name == spec["document"]]
    if len(matches) != 1:
        raise ValueError(f"{ticker}: specialist exhibit unresolved")
    row = matches[0]
    path = Path(row["path"])
    if not path.is_absolute():
        path = event_root.parent.parent / path
    text = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", path.read_text(errors="ignore")))).casefold()
    if re.search(spec["metric_pattern"], text, flags=re.IGNORECASE) is None:
        raise ValueError(f"{ticker}: specialist metric row/period values not found in filed exhibit")
    return {"source_kind": "sec_filed_earnings_exhibit", "accession": spec["accession"], "filed": row["filed"], "period_end": PERIOD, "document": spec["document"], "sha256": row["sha256"], "metric": spec["metric"], "reported_low_base_high_per_share": spec["flow"], "unit": "USD/share", "reported_vs_estimated": "issuer_reported_guidance"}


def _numeric(ticker: str, *, filing, verification, event, specialist, structural):
    spec = INPUTS[ticker]
    sensitivity = tuple(flow * (1 - cost) for flow, cost in zip(spec["flow"], spec["cost"]))
    owner_cash = sensitivity[1]
    discounts = (0.0975, 0.0925, 0.0875)
    rows = []
    for name, discount in zip(("bear", "base", "bull"), discounts):
        value = two_stage_cash_flow_value(cash_flow_per_share=owner_cash, growth_rate=0.02, growth_years=8, terminal_growth=0.02, discount_rate=discount)
        rows.append({"name": name, "reported_ffo_or_affo_per_share": spec["flow"][1], "locked_recurring_cost_ratio": spec["cost"][1], "normalized_affo_per_share": owner_cash, "growth_rate": 0.02, "forecast_years": 8, "terminal_growth": 0.02, "discount_rate": discount, "raw_value_per_share": value, "conditional_value_per_share": value})
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid REIT range")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("REPORTED_AFFO_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"))
    invalidation = "Revalue if reported FFO/AFFO, recurring capital, property/segment/JV scope, preferred/NCI, dilution, financing or cutoff events leave the recorded bounds."
    assumptions = {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 1, "forecast_years": 8, "normalization_basis": "cutoff-safe issuer guidance reduced by issuer-reported or governed recurring capital", "assumption_source_mix": "SEC-filed specialist guidance plus transparent recurring-capital and discount assumptions", "reported_flow_per_share": spec["flow"], "recurring_cost_ratio": spec["cost"], "input_normalized_affo_sensitivity": sensitivity, "normalized_affo_per_share": (owner_cash,) * 3, "growth_rate": (0.02,) * 3, "discount_rate": discounts, "terminal_growth": (0.02,) * 3, "equity_floor_basis": "not applied", "scenario_calibration": "one-driver public range: normalized AFFO per share is fixed while cost of equity varies", "calculator_calibration": "Exact locked AFFO DCF base replay; recurring capital, horizon and terminal growth cannot be edited twice.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker=ticker, method="reit_affo_per_share_dcf", method_version=BATCH_49_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(WARNINGS[ticker], invalidation))
    return {"ticker": ticker, "method": "reit_affo_per_share_dcf", "model_version": BATCH_49_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"reported_flow_per_share": spec["flow"], "flow_metric": spec["metric"], "input_kind": "issuer_reported_guidance"}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "specialist_metric_source": specialist, "recurring_capital_basis": {"ratios": spec["cost"], "basis": spec["basis"], "direct_source": {**spec["cost_source"], "accession": spec["accession"], "document": spec["document"], "reported_vs_estimated": "reported_or_governed_bounded_components"}, "reported_vs_estimated": "reported_or_governed_bounded_range", "missing_values_zero_imputed": False}, "event_sources": event, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS[ticker], "baseline": baseline.as_private_dict()}


def _avb_withheld(*, filing, verification, event, structural):
    approval = next((row for row in event["screened_filings"] if row["accession"] == "0001104659-26-094930"), None)
    if approval is None:
        raise ValueError("AVB: merger approval event absent")
    release = "Revalue after a cutoff-safe closed-company combined AFFO/capital filing, or after explicit authorization of a standalone pre-close-only policy that expires at closing."
    baseline = BaselineValuation(ticker="AVB", method="reit_affo_per_share_dcf", method_version=BATCH_49_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(WARNINGS["AVB"], release))
    return {"ticker": "AVB", "method": "reit_affo_per_share_dcf", "model_version": BATCH_49_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {"standalone_h1_core_ffo_per_share_diagnostic": 5.69}, "governed_assumptions": {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 1, "forecast_years": 8, "normalization_basis": "pending major corporate-event gate", "assumption_source_mix": "reported standalone diagnostics; no published value", "equity_floor_basis": "not applied", "availability_separate_from_model_identity": True, "invalidation": release}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "cutoff_identity": {"ticker": "AVB", "cik": "0000915912", "name": "AvalonBay Communities", "status": "standalone legal issuer at 2026-08-14"}, "merger_approval_event": approval, "event_sources": event, "specialist_gate": {"passed": False, "reason": WARNINGS["AVB"], "release_condition": release}, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS["AVB"], "baseline": baseline.as_private_dict()}


def build_batch_49_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_49_TICKERS:
        raise ValueError(ticker)
    packet, structural_packet = Path(source_root) / ticker, Path(structural_root) / ticker
    submissions, manifest = json.loads((packet / "submissions.json").read_text()), json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((structural_packet / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural.get("source_accession") != filing["accession"] or structural.get("report_date") != PERIOD:
        raise ValueError(f"{ticker}: controlling mismatch")
    verification = verify_source_bundle(ticker=ticker, packet=packet, structural_packet=structural_packet, structural_cache_root=Path(structural_cache_root), filing=filing)
    event = _events(ticker, Path(event_root), verification["source_manifest_sha256"])
    if ticker == "AVB":
        return _avb_withheld(filing=filing, verification=verification, event=event, structural=structural)
    specialist = _specialist_source(ticker, event, Path(event_root))
    return _numeric(ticker, filing=filing, verification=verification, event=event, specialist=specialist, structural=structural)


if PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_49_TICKERS):
    raise RuntimeError("Batch 49 classification mismatch")
