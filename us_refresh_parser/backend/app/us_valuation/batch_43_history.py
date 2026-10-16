"""History-backed resource-cycle baselines for controlled Universe Reset Batch 43."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling
from .batch_08_history import _annual_cash_with_losses
from .batch_35_history import _instant, _period_flow
from .batch_40_history import _latest_shares
from .batch_43 import BATCH_43_MANIFEST, BATCH_43_TICKERS, BATCH_43_VALUATION_DATE
from .batch_43_sources import verify_source_bundle
from .history import build_cash_fcff_history_profile
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability
from .xbrl import load_concept_config


BATCH_43_HISTORY_VERSION = "BATCH-43-HISTORY-1.0"
PERIOD = "2026-06-30"
PASS_TICKERS = frozenset()
WITHHELD_TICKERS = frozenset({"DVN", "NEM", "LYB"})
CONDITIONAL_TICKERS = frozenset(set(BATCH_43_TICKERS) - WITHHELD_TICKERS)

FLOW_SPEC = {
    "MLM": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestExpense",)},
    "STLD": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestExpenseNonoperating",)},
    "DVN": {"revenue": ("Revenues",), "capex": ("PaymentsToAcquireProductiveAssets",), "interest": ("InterestExpenseDebt",)},
    "COP": {"revenue": ("Revenues",), "capex": ("PaymentToAcquireProductiveAssetsAndInvestments",), "interest": ("InterestAndDebtExpense",)},
    "NEM": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("PaymentsToAcquireProductiveAssets",), "interest": ("InterestIncomeExpenseNonoperatingNet",)},
    "MOS": {"revenue": ("Revenues",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestPaidNet",)},
    "CF": {"revenue": ("Revenues",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestExpense",)},
    "VMC": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestExpenseNonoperating",)},
    "LYB": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestExpenseNonoperating",)},
    "LIN": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestExpenseNonoperating",)},
}

POLICY = {
    "MLM": {"growth": (-.04, .015, .045), "wacc": (.11, .095, .085), "terminal": (-.005, .01, .018), "warning": "Conditional Low aggregates-cycle FCFF baseline. The pending Lhoist transaction, financing, housing/infrastructure demand, pricing, capex and claims can move value materially."},
    "STLD": {"growth": (-.07, 0., .04), "wacc": (.12, .10, .085), "terminal": (-.015, .005, .015), "warning": "Conditional Low steel-cycle FCFF baseline. Steel prices, utilization, construction, capex, repurchases and redeemable minority claims remain material."},
    "COP": {"growth": (-.08, 0., .04), "wacc": (.115, .095, .085), "terminal": (-.015, .005, .015), "warning": "Conditional Low integrated E&P-cycle FCFF baseline. Commodity prices, decline, capex, dispositions, pensions and retirement/environmental obligations remain material."},
    "MOS": {"growth": (-.08, -.01, .035), "wacc": (.125, .105, .09), "terminal": (-.02, 0., .0125), "warning": "Conditional Low fertilizer-cycle FCFF baseline. Current cash conversion is negative; fertilizer prices, capex, restricted securities, ARO/environmental claims and pending debt refinancing remain material."},
    "CF": {"growth": (-.07, 0., .035), "wacc": (.115, .095, .085), "terminal": (-.015, .005, .015), "warning": "Conditional Low nitrogen-cycle FCFF baseline. Fertilizer and gas prices, turnaround capex, minority claims and the nonrecurring litigation receipt remain material."},
    "VMC": {"growth": (-.04, .015, .045), "wacc": (.105, .09, .08), "terminal": (-.005, .01, .018), "warning": "Conditional Low aggregates-cycle FCFF baseline. Divestiture scope, price/volume, construction demand, acquisition integration, debt and closure/environmental claims remain material."},
    "LIN": {"growth": (-.035, .02, .045), "wacc": (.10, .085, .075), "terminal": (0., .015, .02), "warning": "Conditional Low industrial-gases FCFF baseline. Project timing, energy/input costs, capex, acquisitions, debt and minority claims remain material."},
}

EVENT_TREATMENTS = {
    "MLM": "Lhoist remains unclosed. The $5.5B August notes are added to cash and debt once and no Lhoist operations, purchase value or synergies are included; the conditional facility remains unfunded.",
    "STLD": "The current filing and earnings releases include current repurchases and the impairment. No future management change or unexecuted capital action is added.",
    "DVN": "The Coterra merger closed May 7, 2026. The controlling quarter contains only a partial combined period and no unspliced multi-year combined cash history; consideration, assumed debt and synergies are not added again.",
    "COP": "The July $1.7B disposition closed after the balance date. It is recorded as a perimeter event but neither the proceeds nor sold operations are mixed into the current-company bridge; pending Kirkuk terms are excluded.",
    "NEM": "The August NGM/Fourmile amendment includes a $1.95B payment plus project contribution and assumed-liability terms. Confidential settlement and future project economics remain unbounded and are not invented.",
    "MOS": "The $2.0B note offering and up-to-$1.4B tenders were priced but settle after the valuation cutoff. They are pending refinancing context and are not added to the June bridge.",
    "CF": "The $170M litigation receipt is removed once from normalized current cash FCFF; it is not treated as recurring operating cash. Duplicate earnings releases add no second value.",
    "VMC": "The current filing includes the small acquisition and completed divestitures. No future transaction value is added; perimeter uncertainty remains in the Low cap.",
    "LYB": "The European asset sale and refinery discontinuation materially change the continuing company, while reported OCF is consolidated. Historical disposed cash flows are not guessed or silently assigned to continuing operations.",
    "LIN": "The earnings and governance filings are screened as current context. Backlog is not an asset and the reported acquisition payment is not extrapolated as recurring capex.",
}


def _config(ticker: str) -> dict[str, Any]:
    config = deepcopy(load_concept_config())
    spec = FLOW_SPEC[ticker]
    config["fields"]["revenue"]["concepts"] = list(spec["revenue"])
    config["fields"]["capital_expenditures"]["concepts"] = list(spec["capex"])
    config["fields"]["interest_expense"]["concepts"] = list(spec["interest"])
    return config


def _flow(structural: dict[str, Any], names: tuple[str, ...], end: str) -> dict[str, Any]:
    return _period_flow(structural, names, end, target_days=180)


def _source(row: dict[str, Any], field: str, value: float) -> dict[str, Any]:
    return {"field": field, "namespace": row.get("namespace", "us-gaap"), "concept": row.get("local_name"), "unit": row.get("unit"), "value": float(value), "start": row.get("period_start"), "end": row.get("period_end"), "accession": row.get("accession"), "form": row.get("form"), "filed": row.get("filed"), "fiscal_year": int(str(row.get("period_end"))[:4]), "fiscal_period": "FY", "dimensions": row.get("dimensions", []), "taxonomy_type": "reported_structural", "value_status": "reported", "selection_reason": "Exact no-dimension annual context in the cutoff-safe controlling 10-K."}


def _annual_fact(structural: dict[str, Any], name: str, end: str) -> dict[str, Any]:
    rows = [row for row in structural.get("facts", []) if row.get("local_name") == name and row.get("period_end") == end and row.get("period_start") == f"{end[:4]}-01-01" and not row.get("dimensions") and isinstance(row.get("value"), (int, float))]
    values = {float(row["value"]) for row in rows}
    if len(values) != 1:
        raise ValueError(f"COP: unresolved annual {name} {end}")
    return rows[-1]


def _cop_annual(annual_root: Path) -> tuple[dict[str, Any], ...]:
    packet = annual_root / "COP"
    receipt = json.loads((packet / "source-receipt.json").read_text())
    structural_path = packet / "structural-filing.json"
    package_path = packet / "package-manifest.json"
    if receipt.get("filing", {}).get("accession") != "0001163165-26-000009" or hashlib.sha256(structural_path.read_bytes()).hexdigest() != receipt.get("structural_filing_sha256") or hashlib.sha256(package_path.read_bytes()).hexdigest() != receipt.get("package_manifest_sha256"):
        raise ValueError("COP: annual source receipt mismatch")
    structural = json.loads(structural_path.read_text())
    rows = []
    for end in ("2023-12-31", "2024-12-31", "2025-12-31"):
        raw = {field: _annual_fact(structural, name, end) for field, name in {"revenue": "Revenues", "operating_cash_flow": "NetCashProvidedByUsedInOperatingActivities", "capital_expenditures": "PaymentToAcquireProductiveAssetsAndInvestments", "interest_expense": "InterestAndDebtExpense", "income_tax": "IncomeTaxExpenseBenefit", "pretax_income": "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"}.items()}
        fields = {field: _source(value, field, value["value"]) for field, value in raw.items()}
        tax_rate = max(0., min(.30, fields["income_tax"]["value"] / fields["pretax_income"]["value"]))
        rows.append({"period_end": end, **fields, "cash_fcff": cash_fcff_from_reported(operating_cash_flow=fields["operating_cash_flow"]["value"], capital_expenditures=fields["capital_expenditures"]["value"], spectrum_investment=0., interest_expense=abs(fields["interest_expense"]["value"]), tax_rate=tax_rate), "formula": "OCF - capex + after-tax interest; exact structural annual lineage", "annual_source_receipt": receipt})
    return tuple(rows)


def _ttm_flows(ticker: str, normalizer, structural: dict[str, Any], tax_rate: float, annual: tuple[dict[str, Any], ...] | None = None) -> dict[str, Any]:
    spec = FLOW_SPEC[ticker]
    fields = {}
    for field, names in (("revenue", spec["revenue"]), ("operating_cash_flow", ("NetCashProvidedByUsedInOperatingActivities",)), ("capital_expenditures", spec["capex"]), ("interest_expense", spec["interest"])):
        current = _flow(structural, names, PERIOD)
        prior = _flow(structural, names, "2025-06-30")
        if ticker == "COP":
            assert annual is not None
            latest = annual[-1][field]
            annual_value = latest["value"]
        else:
            selected = normalizer.annual_series(field, 1)
            if not selected:
                raise ValueError(f"{ticker}: annual {field} unavailable")
            latest = selected[-1].as_dict()
            annual_value = selected[-1].value
        fields[field] = {"value": annual_value + current["value"] - prior["value"], "period_end": PERIOD, "method": "latest_fy_plus_current_h1_minus_prior_h1", "sources": [latest, current, prior], "latest_fy": latest, "current_h1": current, "prior_h1": prior}
    fields["cash_fcff"] = cash_fcff_from_reported(operating_cash_flow=fields["operating_cash_flow"]["value"], capital_expenditures=fields["capital_expenditures"]["value"], spectrum_investment=0., interest_expense=abs(fields["interest_expense"]["value"]), tax_rate=tax_rate)
    if ticker == "CF":
        fields["reported_cash_fcff_before_event_normalization"] = fields["cash_fcff"]
        fields["nonrecurring_litigation_receipt_removed"] = 170_000_000.
        fields["cash_fcff"] -= 170_000_000.
    return fields


def _point(structural: dict[str, Any], names: tuple[str, ...]) -> dict[str, Any]:
    return _instant(structural, names, PERIOD)


def _bridge(ticker: str, structural: dict[str, Any]) -> dict[str, Any]:
    latest = _latest_shares(ticker, structural)
    cash = debt = fixed = stress = 0.
    excluded: dict[str, Any] = {}
    if ticker == "MLM":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",))["value"] + 5_500_000_000.; debt = _point(structural, ("LongTermDebtCurrent",))["value"] + _point(structural, ("LongTermDebtNoncurrent",))["value"] + 5_500_000_000.; fixed = _point(structural, ("MinorityInterest",))["value"]; stress = 55_000_000.; excluded["restricted_cash"] = 8_000_000.; excluded["august_note_overlay"] = {"cash": 5_500_000_000., "debt": 5_500_000_000., "bear_redemption_stress": 55_000_000.}
    elif ticker == "STLD":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt = _point(structural, ("LongTermDebtCurrent",))["value"] + _point(structural, ("LongTermDebtNoncurrent",))["value"]; fixed = _point(structural, ("RedeemableNoncontrollingInterestEquityCarryingAmount",))["value"]; excluded["negative_nonredeemable_nci_not_inverted"] = _point(structural, ("MinorityInterest",))["value"]
    elif ticker == "DVN":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt = _point(structural, ("LongTermDebt",))["value"] + _point(structural, ("FinanceLeaseLiability",))["value"]; stress = _point(structural, ("AssetRetirementObligation",))["value"]; excluded["investments_not_proven_surplus"] = _point(structural, ("Investments",))["value"]
    elif ticker == "COP":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",))["value"] + _point(structural, ("ShortTermInvestments",))["value"]; debt = _point(structural, ("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",))["value"]; stress = _point(structural, ("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",))["value"] + _point(structural, ("AssetRetirementObligationsAndAccruedEnvironmentalCostNonCurrent",))["value"]; excluded["restricted_cash"] = _point(structural, ("RestrictedCashNoncurrent",))["value"]; excluded["long_term_investments"] = _point(structural, ("LongTermInvestmentsAndReceivablesNet",))["value"]
    elif ticker == "NEM":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt = _point(structural, ("LongTermDebt",))["value"] + _point(structural, ("LeaseAndOtherFinancingObligationsCurrent",))["value"] + _point(structural, ("LeaseAndOtherFinancingObligationsNoncurrent",))["value"]; fixed = _point(structural, ("MinorityInterest",))["value"] + 1_950_000_000.; stress = _point(structural, ("AssetRetirementObligationAndEnvironmentalLossContingencies",))["value"] + _point(structural, ("PensionAndOtherPostretirementDefinedBenefitPlansAndOtherEmployeeRelatedLiabilitiesNoncurrent",))["value"]; excluded["restricted_cash"] = _point(structural, ("RestrictedCash",))["value"]; excluded["long_term_investments"] = _point(structural, ("LongTermInvestments",))["value"]
    elif ticker == "MOS":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt = _point(structural, ("LongTermDebtAndCapitalLeaseObligations",))["value"] + _point(structural, ("LongTermDebtAndCapitalLeaseObligationsCurrent",))["value"] + _point(structural, ("OtherShortTermBorrowings",))["value"]; fixed = _point(structural, ("MinorityInterest",))["value"]; stress = _point(structural, ("AssetRetirementObligation",))["value"] + _point(structural, ("AccrualForEnvironmentalLossContingencies",))["value"] + _point(structural, ("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",))["value"]; excluded["restricted_securities_not_surplus_cash"] = _point(structural, ("DebtSecuritiesAvailableForSaleRestricted",))["value"]
    elif ticker == "CF":
        cash = _point(structural, ("Cash",))["value"]; debt = _point(structural, ("LongTermDebt",))["value"]; fixed = _point(structural, ("MinorityInterest",))["value"]; excluded["cash_plus_restricted_aggregate_not_surplus"] = _point(structural, ("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",))["value"]
    elif ticker == "VMC":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt = _point(structural, ("DebtLongtermAndShorttermCombinedAmount",))["value"] + _point(structural, ("FinanceLeaseLiabilityCurrent",))["value"] + _point(structural, ("FinanceLeaseLiabilityNoncurrent",))["value"]; fixed = _point(structural, ("MinorityInterest",))["value"]; stress = _point(structural, ("AssetRetirementObligation",))["value"] + _point(structural, ("AccrualForEnvironmentalLossContingencies",))["value"]; excluded["restricted_cash"] = _point(structural, ("RestrictedCashAndCashEquivalentsAtCarryingValue",))["value"]
    elif ticker == "LYB":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",))["value"] + _point(structural, ("MarketableSecuritiesCurrent",))["value"]; debt = _point(structural, ("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",))["value"] + _point(structural, ("ShortTermBorrowings",))["value"]; fixed = _point(structural, ("MinorityInterest",))["value"] + _point(structural, ("TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",))["value"]; stress = _point(structural, ("AccrualForEnvironmentalLossContingencies",))["value"]
    elif ticker == "LIN":
        cash = _point(structural, ("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt = _point(structural, ("DebtLongtermAndShorttermCombinedAmount",))["value"]; fixed = _point(structural, ("MinorityInterest",))["value"] + _point(structural, ("RedeemableNoncontrollingInterestEquityCarryingAmount",))["value"]
    else:
        raise ValueError(ticker)
    claims = (float(fixed + stress), float(fixed), float(fixed))
    return {"cash": float(cash), "debt": float(debt), "claims": claims, "latest_common_shares": latest, "base_share_count": float(latest["value"]), "excluded_or_separately_treated": {**excluded, "operating_claim_stress": (float(stress), 0., 0.), "operating_claim_policy": "Operating cash effects remain in reported OCF; closing ARO, environmental and pension balances are bear-only stresses. Fixed NCI/temporary-equity claims are deducted in every scenario."}, "reported_vs_estimated": "reported_bridge_with_named_event_adjustments"}


def _events(ticker: str, root: Path, source_manifest_sha256: str) -> dict[str, Any]:
    path = root / ticker / "inventory.json"
    rows = json.loads(path.read_text())
    if not rows or any(row.get("filed", "") > BATCH_43_VALUATION_DATE for row in rows):
        raise ValueError(f"{ticker}: invalid event inventory")
    documents = []
    for row in rows:
        for document in row.get("documents", []):
            document_path = Path(document["path"])
            if not document_path.is_absolute():
                document_path = root.parent.parent / document_path
            if not document_path.exists() or hashlib.sha256(document_path.read_bytes()).hexdigest() != document.get("sha256"):
                raise ValueError(f"{ticker}: event hash mismatch")
            documents.append(document)
    return {"source_kind": "sec_event_screening", "decision": "accepted_context", "screened_filings": rows, "documents": documents, "inventory_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "source_manifest_sha256": source_manifest_sha256, "treatment": EVENT_TREATMENTS[ticker], "reported_vs_estimated": "reported_and_screened"}


def _withheld(ticker: str, *, filing, flows, annual, profile, bridge, event, verification, structural, tax_rate, tax_sources) -> dict[str, Any]:
    reasons = {
        "DVN": ("Withheld: Devon's Coterra merger closed only seven weeks before the controlling quarter ended. Current cash flow mixes legacy Devon with a partial combined period, so a multi-year combined-company cycle cannot be bounded without inventing a pro-forma cash history.", "Revalue with issuer-filed combined pro-forma cash flows or sufficient post-close annual history, plus a complete current debt, lease, share and synergy reconciliation."),
        "NEM": ("Withheld: Newmont's pre-cutoff NGM/Fourmile agreement combines a $1.95B payment with contributed project rights, assumed liabilities and confidential settlement terms. The payment is known, but the common-equity value transferred and remaining obligations are not yet finitely bounded.", "Revalue when the transaction closes or issuer evidence quantifies the contributed assets, assumed liabilities, settlement scope and resulting NGM/Fourmile ownership economics."),
        "LYB": ("Withheld: LyondellBasell's completed European asset sale and refinery discontinuation changed the continuing company, but reported operating cash flow remains consolidated. Disposed and continuing cash flows cannot be separated from the captured filing without guessing.", "Revalue with issuer-filed continuing-company cash flow, pro-forma information or enough post-disposal history to separate refinery and sold-European cash conversion from continuing operations."),
    }
    reason, invalidation = reasons[ticker]
    baseline = BaselineValuation(ticker=ticker, method="resource_cycle_enterprise_fcff", method_version=BATCH_43_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(reason, invalidation))
    return {"ticker": ticker, "method": baseline.method, "model_version": BATCH_43_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {"ttm_revenue": flows["revenue"]["value"], "ttm_cash_fcff": flows["cash_fcff"]}, "governed_assumptions": {**profile.public_metadata(), "forecast_years": 8, "normalization_basis": "current-scope hard gate; reported history retained only as a diagnostic", "assumption_source_mix": "reported_history_current_ttm_and_event_context", "equity_floor_basis": "not applied", "invalidation": invalidation}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": annual, "tax_rate": tax_rate, "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_context": bridge, "event_sources": event, "runtime_source_verification": verification, "current_ttm_is_diagnostic_only": True, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": reason, "baseline": baseline.as_private_dict()}


def build_batch_43_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path, cop_annual_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_43_TICKERS:
        raise ValueError(ticker)
    packet = Path(source_root) / ticker
    structural_packet = Path(structural_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((structural_packet / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural.get("source_accession") != filing["accession"] or structural.get("report_date") != PERIOD:
        raise ValueError(f"{ticker}: controlling mismatch")
    verification = verify_source_bundle(ticker=ticker, packet=packet, structural_packet=structural_packet, structural_cache_root=Path(structural_cache_root), filing=filing)
    event = _events(ticker, Path(event_root), verification["source_manifest_sha256"])
    normalizer = _normalizer(submissions, facts, concept_config=_config(ticker))
    tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    cop_annual = _cop_annual(Path(cop_annual_root)) if ticker == "COP" else None
    flows = _ttm_flows(ticker, normalizer, structural, tax_rate, cop_annual)
    if cop_annual is not None:
        annual = cop_annual
    else:
        _, _, annual = _annual_cash_with_losses(normalizer)
    ttm_sources = [source for field in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense") for source in flows[field]["sources"]]
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=flows["revenue"]["value"], ttm_cash_fcff=flows["cash_fcff"], ttm_period_end=PERIOD, ttm_sources=ttm_sources, valuation_date=BATCH_43_VALUATION_DATE)
    metric = profile.metric("cash_conversion_margin")
    if metric is None:
        raise ValueError(f"{ticker}: cash history unavailable")
    bridge = _bridge(ticker, structural)
    if ticker in WITHHELD_TICKERS:
        return _withheld(ticker, filing=filing, flows=flows, annual=annual, profile=profile, bridge=bridge, event=event, verification=verification, structural=structural, tax_rate=tax_rate, tax_sources=tax_sources)
    policy = POLICY[ticker]
    margins = (metric.low, metric.base, metric.high)
    if ticker == "MOS":
        # Current TTM is negative, so the base is the conservative five-year
        # annual-cycle median rather than an interpolation through that one period.
        annual_margins = sorted(float(row["cash_fcff"]) / float(row["revenue"]["value"]) for row in annual)
        margins = (.005, annual_margins[len(annual_margins) // 2], max(.14, metric.high))
    share_base = bridge["base_share_count"]
    shares = (share_base * 1.015, share_base, share_base * .985)
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        starting = flows["revenue"]["value"] * margins[index]
        state = EnterpriseCashFlowState(starting, policy["growth"][index], policy["terminal"][index], policy["wacc"][index], bridge["cash"], bridge["debt"], 0., bridge["claims"][index], shares[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": max(0., raw), "starting_cash_fcff": starting, "cash_conversion_margin": margins[index], "growth": policy["growth"][index], "wacc": policy["wacc"][index], "terminal_growth": policy["terminal"][index], "cash_and_investments": bridge["cash"], "debt_and_finance_leases": bridge["debt"], "other_equity_claims": bridge["claims"][index], "shares": shares[index], "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError(f"{ticker}: nonpositive or unordered scenario")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("NORMALIZED_CYCLICAL_RANGE", "SPECIALIST_MODEL_UNCERTAINTY"))
    invalidation = "Revalue if current-company scope, resource/input prices, cash conversion, capex, debt/leases, NCI, operating claims, shares or cutoff events leave the recorded range."
    assumptions = {**profile.public_metadata(), "forecast_years": 8, "normalization_basis": "source-linked cash-FCFF history with issuer-specific cycle and event treatment", "assumption_source_mix": "reported_history_and_governed_cycle_scenarios", "cash_conversion_margin": margins, "growth": policy["growth"], "wacc": policy["wacc"], "terminal_growth": policy["terminal"], "shares": shares, "share_sensitivity_basis": "latest cutoff-safe common shares are the base; governed +/-1.5% stress represents unresolved dilution", "equity_floor_basis": "bear-only limited-liability floor; raw residual retained privately", "calculator_calibration": "Exact enterprise cash-FCFF default replay.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker=ticker, method="resource_cycle_enterprise_fcff", method_version=BATCH_43_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(policy["warning"], invalidation))
    return {"ticker": ticker, "method": baseline.method, "model_version": BATCH_43_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": flows["revenue"]["value"], "ttm_cash_fcff": flows["cash_fcff"], "share_count": share_base}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": annual, "tax_rate": tax_rate, "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_context": bridge, "event_sources": event, "model_trace": {"states": traces}, "raw_scenario_rows": rows, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": policy["warning"], "baseline": baseline.as_private_dict()}


if PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_43_TICKERS):
    raise RuntimeError("Batch 43 policy mismatch")
