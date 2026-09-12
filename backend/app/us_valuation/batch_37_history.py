"""History-backed practical baselines for controlled Universe Reset Batch 37."""
from __future__ import annotations

import copy
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from app.valuation.bank import residual_income_valuation

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling
from .batch_08_history import _annual_cash_with_losses
from .batch_35_history import _equity, _instant, _period_flow, _rows, _share, _source
from .batch_36_history import _structural_rows
from .batch_37 import BATCH_37_MANIFEST, BATCH_37_TICKERS, BATCH_37_VALUATION_DATE
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, build_cash_fcff_history_profile, summarize_history_metric
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability
from .xbrl import load_concept_config


BATCH_37_HISTORY_VERSION = "BATCH-37-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset()
CONDITIONAL_TICKERS = frozenset(BATCH_37_TICKERS)
WITHHELD_TICKERS = frozenset()
OPERATING_TICKERS = frozenset({"FDS", "MCO"})
FINANCIAL_TICKERS = tuple(ticker for ticker in BATCH_37_TICKERS if ticker not in {"OKE", *OPERATING_TICKERS})


EARNINGS: dict[str, tuple[str, ...]] = {
    "IVZ": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "ERIE": ("NetIncomeLoss",),
    "ACGL": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "FDS": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
    "MCO": ("NetIncomeLoss",),
    "BRK.B": ("NetIncomeLoss",),
    "MET": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "TROW": ("NetIncomeLossAvailableToCommonStockholdersBasic",),
    "NDAQ": ("NetIncomeLoss",),
}


POLICY: dict[str, dict[str, Any]] = {
    "IVZ": {"method": "asset_manager_residual_income_equity_earnings", "roe": (.08, .11, .14), "payout": (.25, .35, .45), "coe": (.11, .095, .085), "warning": "Conditional Low asset-manager residual-income baseline. Client AUM is not issuer cash; the 2025 intangible impairment, preferred claim, NCI, fee mix and market levels remain material."},
    "ERIE": {"method": "reciprocal_insurance_manager_residual_income_equity_earnings", "roe": (.12, .16, .20), "payout": (.20, .28, .36), "coe": (.105, .09, .08), "warning": "Conditional Low reciprocal-insurance manager residual-income baseline. The 25% management-fee relationship is modeled at the parent; policyholder premiums, reserves and Exchange float are not parent cash."},
    "ACGL": {"method": "property_casualty_reinsurance_residual_income_equity_earnings", "roe": (.08, .12, .16), "payout": (.20, .30, .40), "coe": (.11, .095, .085), "warning": "Conditional Low P&C/reinsurance residual-income baseline. Catastrophe, reserve, reinsurance, investment marks, preferred claims and capital remain material."},
    "BRK.B": {"method": "holding_company_insurance_residual_income_equity_earnings", "roe": (.07, .09, .11), "payout": (0., 0., 0.), "coe": (.10, .09, .08), "warning": "Conditional Low holding-company/insurance residual-income baseline. Insurance float and operating subsidiaries remain inside equity economics; investment gains, acquisitions, NCI and Class A/B conversion remain material."},
    "MET": {"method": "life_insurance_residual_income_equity_earnings", "roe": (.07, .10, .13), "payout": (.25, .35, .45), "coe": (.11, .095, .085), "warning": "Conditional Low life-insurance residual-income baseline. Policy reserves, investment marks, capital, redeemable NCI and the economic preferred claim remain material."},
    "TROW": {"method": "asset_manager_residual_income_equity_earnings", "roe": (.09, .12, .15), "payout": (.35, .45, .55), "coe": (.105, .09, .08), "warning": "Conditional Low asset-manager residual-income baseline. Client AUM and sponsored portfolios are not issuer cash; market levels, flows and redeemable NCI remain material."},
    "NDAQ": {"method": "financial_exchange_data_residual_income_equity_earnings", "roe": (.09, .13, .17), "payout": (.25, .30, .35), "coe": (.105, .09, .08), "warning": "Conditional Low exchange/data residual-income baseline. Acquisition integration, debt, recurring reinvestment, sale/discontinued gains and transaction volumes remain material."},
}


NORMALIZATION = {
    "IVZ": {"concept": "ImpairmentOfIntangibleAssetsIndefinitelivedExcludingGoodwill", "value": 1_794_900_000., "multiplier": .79, "direction": 1., "label": "2025 indefinite-lived intangible impairment after a governed 21% tax effect"},
    "MCO": {"concept": "GainLossOnSaleOfBusiness", "value": 181_000_000., "multiplier": .79, "direction": -1., "label": "H1 2026 business-sale gain after a governed 21% tax effect"},
    "NDAQ": {"concept": "GainLossOnSaleOfBusiness", "value": 89_000_000., "multiplier": .79, "direction": -1., "label": "H1 2026 business-sale gain after a governed 21% tax effect"},
}


def _annual(facts: dict[str, Any], ticker: str) -> tuple[dict[str, Any], ...]:
    required = 3 if ticker == "IVZ" else 5
    selected: dict[str, tuple[dict[str, Any], str]] = {}
    for concept in EARNINGS[ticker]:
        for row in _rows(facts, concept):
            if row.get("form") not in {"10-K", "10-K/A"} or row.get("filed", "") > BATCH_37_VALUATION_DATE or not row.get("start") or not row.get("end"):
                continue
            try:
                span = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
            except ValueError:
                continue
            if not 300 <= span <= 380:
                continue
            old = selected.get(row["end"])
            if old is None or (row.get("filed", ""), row.get("accn", "")) > (old[0].get("filed", ""), old[0].get("accn", "")):
                selected[row["end"]] = (row, concept)
        if len(selected) >= required:
            break
    recent = [end for end in sorted(selected) if end >= "2020-01-01"]
    if len(recent) < required:
        raise ValueError(f"{ticker}: fewer than {required} current annual earnings periods")
    return tuple({"period_end": end, "value": float(selected[end][0]["val"]), "source": _source(selected[end][0], selected[end][1])} for end in recent[-required:])


def _dimensional_source(structural: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {"source_kind": "structural_xbrl", "accession": structural.get("source_accession"), "filed": structural.get("filed_date"), "form": structural.get("form"), "period_start": row.get("period_start"), "period_end": row.get("period_end"), "concept": row.get("qname"), "unit": row.get("unit"), "value": float(row["value"]), "dimensions": row.get("dimensions"), "reported_vs_estimated": "reported"}


def _shares(ticker: str, structural: dict[str, Any], facts: dict[str, Any], period: str) -> dict[str, Any]:
    if ticker == "ERIE":
        rows = [row for row in structural.get("facts", []) if row.get("local_name") == "WeightedAverageNumberOfDilutedSharesOutstanding" and row.get("period_start") == "2026-01-01" and row.get("period_end") == period and row.get("unit") == "xbrli:shares" and any("CommonClassAMember" in member for dim in row.get("dimensions", []) for member in dim)]
        if not rows:
            raise ValueError("ERIE: diluted Class A-equivalent shares absent")
        source = _dimensional_source(structural, rows[0])
        return {"source_kind": "class_equivalent_share_selection", "value": source["value"], "unit": "xbrli:shares", "period_end": period, "formula": "reported diluted Class A-equivalent shares; Class B conversion is already reflected", "sources": [source], "reported_vs_estimated": "reported"}
    if ticker == "BRK.B":
        candidates = [row for row in structural.get("facts", []) if row.get("local_name") == "EntityCommonStockSharesOutstanding" and row.get("unit") == "xbrli:shares" and period <= str(row.get("period_end", "")) <= BATCH_37_VALUATION_DATE and row.get("dimensions")]
        class_a = next(row for row in candidates if any("CommonClassAMember" in member for dim in row["dimensions"] for member in dim))
        class_b = next(row for row in candidates if any("CommonClassBMember" in member for dim in row["dimensions"] for member in dim))
        value = float(class_a["value"]) * 1500. + float(class_b["value"])
        return {"source_kind": "derived_class_b_equivalent_shares", "value": value, "unit": "xbrli:shares", "period_end": class_a["period_end"], "formula": "Class A shares * 1,500 + Class B shares", "conversion_ratio": 1500., "sources": [_dimensional_source(structural, class_a), _dimensional_source(structural, class_b)], "reported_vs_estimated": "reported_components_with_derived_conversion"}
    return _share(structural, facts, period)


def _preferred(ticker: str, structural: dict[str, Any], period: str) -> tuple[float, str, list[dict[str, Any]]]:
    if ticker == "MET":
        prior = _instant(structural, ("PreferredStockLiquidationPreferenceValue",), "2025-12-31")
        if period == "2025-12-31":
            return float(prior["value"]), "reported_preferred_claim", [prior]
        dividends = _period_flow(structural, ("DividendsPreferredStock", "DividendsPreferredStockCash"), period, target_days=180)
        issued = _structural_rows(structural, ("PreferredStockSharesIssued",), period_start=None, period_end=period, unit="xbrli:shares")
        outstanding = _structural_rows(structural, ("PreferredStockSharesOutstanding",), period_start=None, period_end=period, unit="xbrli:shares")
        prior_outstanding = _structural_rows(structural, ("PreferredStockSharesOutstanding",), period_start=None, period_end="2025-12-31", unit="xbrli:shares")
        if dividends["value"] != 76_000_000. or not issued or not outstanding or not prior_outstanding or max(float(row["value"]) for row in issued) != max(float(row["value"]) for row in outstanding) or sorted(float(row["value"]) for row in outstanding) != sorted(float(row["value"]) for row in prior_outstanding):
            raise ValueError("MET: preferred series state changed")
        carry = {"source_kind": "derived_period_specific_preferred_claim", "value": prior["value"], "unit": "USD", "period_end": period, "formula": "2025-12-31 reported $2.905B liquidation preference carried to 2026-06-30 only after identical aggregate/series issued and outstanding share counts and $76M current H1 preferred dividends prove the stack persists", "sources": [prior, dividends, *[_dimensional_source(structural, row) for row in outstanding]], "reported_vs_estimated": "reported_components_with_derived_current_claim"}
        return float(prior["value"]), "derived_current_preferred_claim", [carry]
    for name in ("PreferredStockLiquidationPreferenceValue", "PreferredStockCarryingValue", "PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount", "PreferredStockValue"):
        try:
            row = _instant(structural, (name,), period)
        except ValueError:
            continue
        return float(row["value"]), "reported_preferred_claim" if row["value"] > 0 else "reported_preferred_absence", [row]
    absence = {"source_kind": "structural_statement_absence_check", "accession": structural.get("source_accession"), "period_end": period, "searched_concepts": ["PreferredStockLiquidationPreferenceValue", "PreferredStockCarryingValue", "PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount", "PreferredStockValue", "PreferredStockSharesOutstanding"], "treatment": "The controlling balance/equity facts present common equity without a preferred class or dividend; this is an explicit source-scope check, not blank-to-zero.", "reported_vs_estimated": "source_bounded_absence_check"}
    return 0., "statement_proven_preferred_absence", [absence]


def _event_rows(ticker: str, event_root: Path, source_manifest_sha256: str) -> list[dict[str, Any]]:
    packet = Path(event_root) / ticker
    receipt_path = packet / "source-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    filings = receipt.get("screened_filings") or []
    if receipt.get("schema_version") != "FINSIGHT-BATCH-37-EVENT-LEDGER-1" or receipt.get("ticker") != ticker or receipt.get("valuation_date") != BATCH_37_VALUATION_DATE or receipt.get("source_manifest_sha256") != source_manifest_sha256 or receipt.get("decision") not in {"accepted", "rejected"} or not filings or any(row.get("filed", "") > BATCH_37_VALUATION_DATE for row in filings):
        raise ValueError(f"{ticker}: invalid event source")
    documents = []
    for document in receipt.get("documents", []):
        path = packet / document["document"]
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != document.get("sha256"):
            raise ValueError(f"{ticker}: event document hash mismatch")
        documents.append(document)
    return [{"source_kind": "sec_event_screening", "decision": receipt["decision"], "screened_filings": filings, "documents": documents, "source_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(), "reported_terms": receipt.get("reported_terms", {}), "treatment": receipt.get("treatment"), "reported_vs_estimated": "reported" if receipt["decision"] == "accepted" else "screened_and_rejected"}]


def _verify_source_bundle(*, ticker: str, packet: Path, structural_packet: Path, structural_cache_root: Path, filing: dict[str, Any]) -> dict[str, Any]:
    issuer = next(row for row in BATCH_37_MANIFEST if row.ticker == ticker)
    source_manifest_path = packet / "source-manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text())
    if source_manifest.get("issuer", {}).get("ticker") != ticker or source_manifest.get("issuer", {}).get("cik") != issuer.cik:
        raise ValueError(f"{ticker}: source packet identity mismatch")
    packet_hashes = {}
    for name, expected in source_manifest.get("packet_payload_sha256", {}).items():
        path = packet / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if actual != expected:
            raise ValueError(f"{ticker}: source packet hash mismatch for {name}")
        packet_hashes[name] = actual
    receipt_path = structural_packet / "source-receipt.json"
    structural_path = structural_packet / "structural-filing.json"
    package_path = structural_packet / "package-manifest.json"
    receipt = json.loads(receipt_path.read_text())
    package = json.loads(package_path.read_text())
    expected_filing = {"accession": filing["accession"], "filed": filing["filed"], "form": filing["form"], "report_date": filing["period_end"]}
    if receipt.get("schema_version") != "FINSIGHT-BATCH-37-STRUCTURAL-SOURCE-1" or receipt.get("ticker") != ticker or receipt.get("cik") != issuer.cik or receipt.get("valuation_date") != BATCH_37_VALUATION_DATE or any((receipt.get("filing") or {}).get(key) != value for key, value in expected_filing.items()):
        raise ValueError(f"{ticker}: structural receipt identity mismatch")
    structural_hash = hashlib.sha256(structural_path.read_bytes()).hexdigest()
    package_hash = hashlib.sha256(package_path.read_bytes()).hexdigest()
    if structural_hash != receipt.get("structural_filing_sha256") or package_hash != receipt.get("package_manifest_sha256"):
        raise ValueError(f"{ticker}: structural source hash mismatch")
    entrypoint = package.get("entrypoint_local_path")
    entry = next((row for row in package.get("files", []) if row.get("local_path") == entrypoint), None)
    html_path = next((Path(structural_cache_root) / "filings" / ticker).glob(f"**/{entrypoint}"), None) if entrypoint else None
    if entry is None or html_path is None or hashlib.sha256(html_path.read_bytes()).hexdigest() != entry.get("sha256"):
        raise ValueError(f"{ticker}: primary filing document hash mismatch")
    return {"source_kind": "runtime_verified_source_bundle", "ticker": ticker, "cik": issuer.cik, "source_manifest_sha256": hashlib.sha256(source_manifest_path.read_bytes()).hexdigest(), "packet_payload_sha256": packet_hashes, "structural_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(), "structural_filing_sha256": structural_hash, "package_manifest_sha256": package_hash, "primary_document": entrypoint, "primary_document_sha256": entry["sha256"], "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "verified": True}


def _normalization_source(facts: dict[str, Any], ticker: str) -> tuple[float, dict[str, Any] | None]:
    spec = NORMALIZATION.get(ticker)
    if not spec:
        return 0., None
    rows = [row for row in _rows(facts, spec["concept"]) if row.get("form") in {"10-K", "10-Q", "10-Q/A"} and row.get("filed", "") <= BATCH_37_VALUATION_DATE and float(row["val"]) == spec["value"]]
    if not rows:
        raise ValueError(f"{ticker}: normalization source absent")
    row = max(rows, key=lambda value: (value.get("filed", ""), value.get("accn", "")))
    amount = spec["direction"] * spec["value"] * spec["multiplier"]
    return amount, {"source_kind": "reported_fact_with_governed_tax_effect", "reported_fact": _source(row, spec["concept"]), "reported_amount": spec["value"], "governed_multiplier": spec["multiplier"], "normalized_earnings_adjustment": amount, "label": spec["label"], "reported_vs_estimated": "reported_amount_with_finsight_tax_policy"}


def _financial_result(ticker: str, facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], event_root: Path, manifest_sha: str) -> dict[str, Any]:
    policy = POLICY[ticker]
    events = _event_rows(ticker, event_root, manifest_sha)
    period = filing["period_end"]
    annual = _annual(facts, ticker)
    current = _period_flow(structural, EARNINGS[ticker], period)
    duration = (date.fromisoformat(period) - date.fromisoformat(current["period_start"])).days
    prior_end = f"{int(period[:4]) - 1}{period[4:]}"
    prior = _period_flow(structural, EARNINGS[ticker], prior_end, target_days=duration)
    earnings_attribution_context: list[dict[str, Any]] = []
    if ticker == "BRK.B":
        current_consolidated = _period_flow(structural, ("ProfitLoss",), period, target_days=duration)
        current_nci = _period_flow(structural, ("NetIncomeLossAttributableToNoncontrollingInterest",), period, target_days=duration)
        prior_consolidated = _period_flow(structural, ("ProfitLoss",), prior_end, target_days=duration)
        prior_nci = _period_flow(structural, ("NetIncomeLossAttributableToNoncontrollingInterest",), prior_end, target_days=duration)
        if current_consolidated["value"] - current_nci["value"] != current["value"] or prior_consolidated["value"] - prior_nci["value"] != prior["value"]:
            raise ValueError("BRK.B: parent earnings attribution does not reconcile")
        earnings_attribution_context = [{"period": "current_h1", "parent_attributable": current, "consolidated": current_consolidated, "nci": current_nci, "formula": "ProfitLoss - NCI earnings = NetIncomeLoss attributable to Berkshire; selected parent line is not reduced again"}, {"period": "prior_h1", "parent_attributable": prior, "consolidated": prior_consolidated, "nci": prior_nci, "formula": "ProfitLoss - NCI earnings = NetIncomeLoss attributable to Berkshire; selected parent line is not reduced again"}]
    raw_ttm = float(annual[-1]["value"]) + float(current["value"]) - float(prior["value"])
    normalization, normalization_source = _normalization_source(facts, ticker)
    if ticker == "NDAQ":
        discontinued_rows = [row for row in _rows(facts, "DiscontinuedOperationAmountOfAdjustmentToPriorPeriodGainLossOnDisposalNetOfTax") if row.get("start") == "2026-01-01" and row.get("end") == "2026-06-30" and row.get("filed", "") <= BATCH_37_VALUATION_DATE and float(row["val"]) == 88_000_000.]
        if not discontinued_rows:
            raise ValueError("NDAQ: discontinued-operation adjustment absent")
        discontinued_source = _source(max(discontinued_rows, key=lambda row: (row.get("filed", ""), row.get("accn", ""))), "DiscontinuedOperationAmountOfAdjustmentToPriorPeriodGainLossOnDisposalNetOfTax")
        normalization -= 88_000_000.
        normalization_source = {"source_kind": "combined_nonrecurring_earnings_adjustment", "sources": [normalization_source, discontinued_source], "normalized_earnings_adjustment": normalization, "formula": "remove after-tax business-sale gain and reported net-of-tax discontinued-operation adjustment", "reported_vs_estimated": "reported_amounts_with_finsight_tax_policy"}
    normalized_ttm = raw_ttm + normalization
    end_total = _equity(structural, period, facts)
    prior_period = annual[-1]["period_end"]
    prior_total = _equity(structural, prior_period, facts)
    preferred, preferred_status, preferred_sources = _preferred(ticker, structural, period)
    prior_preferred, prior_status, prior_preferred_sources = _preferred(ticker, structural, prior_period)
    end_common = float(end_total["value"]) - preferred
    begin_common = float(prior_total["value"]) - prior_preferred
    share = _shares(ticker, structural, facts, period)
    current_shares = float(share["value"])
    if min(normalized_ttm, end_common, begin_common, current_shares) <= 0:
        raise ValueError(f"{ticker}: nonpositive normalized financial inputs")
    observations = [HistoryObservation("annual", row["period_end"], int(row["period_end"][:4]), row["value"], "USD", "reported annual parent/common earnings", (row["source"],)) for row in annual]
    observations.append(HistoryObservation("operating_ttm", period, None, normalized_ttm, "USD", "latest FY plus current YTD less prior comparable YTD plus explicit nonrecurring adjustment", tuple([annual[-1]["source"], current, prior] + ([normalization_source] if normalization_source else []))))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    if metric is None:
        raise ValueError(f"{ticker}: earnings history unavailable")
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "financial_equity_residual_income", BATCH_37_VALUATION_DATE, tuple(row["period_end"] for row in annual), (metric,), len(annual) >= 3, "reported_and_company_history")
    history_high = max(metric.high, normalized_ttm) / end_common
    roes = tuple(min(value, max(.03, history_high)) for value in policy["roe"])
    if roes[0] == roes[2]:
        roes = (max(.02, history_high * .5), max(.025, history_high * .75), history_high)
    shares = (current_shares * 1.015, current_shares, current_shares * .985)
    rows, traces = [], {}
    for idx, name in enumerate(("bear", "base", "bull")):
        trace = residual_income_valuation(book_value_per_share=end_common / shares[idx], current_roe=roes[idx], cost_of_equity=policy["coe"][idx], current_payout_ratio=policy["payout"][idx], terminal_roe=(.085, .105, .115)[idx], terminal_growth=(.01, .02, .025)[idx], years=5)
        raw = float(trace["intrinsic_value"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": raw, "book_value_per_share": end_common / shares[idx], "current_roe": roes[idx], "current_payout_ratio": policy["payout"][idx], "cost_of_equity": policy["coe"][idx], "terminal_roe": (.085, .105, .115)[idx], "terminal_growth": (.01, .02, .025)[idx], "shares": shares[idx], "preferred_claim": preferred, "ending_common_equity": end_common, "limited_liability_floor_applied": False})
        traces[name] = trace
    scenario = {"low": rows[0]["raw_value_per_share"], "base": rows[1]["raw_value_per_share"], "high": rows[2]["raw_value_per_share"]}
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid residual-income range")
    reasons = ("SPECIALIST_MODEL_UNCERTAINTY",)
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    warning = policy["warning"]
    if ticker == "IVZ":
        warning += f" Raw TTM common earnings are ${raw_ttm/1e6:.1f}M; the model adds back ${normalization/1e6:.1f}M after tax from the reported $1.7949B 2025 impairment, while preserving the raw loss as a diagnostic. July preliminary AUM was $2.4471T and is never treated as cash."
    elif ticker == "MCO":
        warning += " The reported $181M H1 business-sale gain is removed after a governed 21% tax effect before setting normalized TTM earnings."
    elif ticker == "NDAQ":
        warning += " The reported $89M H1 business-sale gain is removed after a governed 21% tax effect; the June 30 $1.5B revolver is capacity only and no draw is added."
    elif ticker == "MET":
        warning += " The $2.905B preferred claim is carried from the reported year-end liquidation preference only after current series share counts and preferred dividends prove the stack persists; the zero par-value tag is rejected."
    special_context: list[dict[str, Any]] = []
    if ticker == "ERIE":
        fee_rows = [row for row in structural.get("facts", []) if row.get("local_name") == "InsuranceAgencyManagementFeePercent" and row.get("period_start") == "2026-01-01" and row.get("period_end") == period and row.get("unit") == "xbrli:pure" and not row.get("dimensions") and float(row.get("value", -1)) == .25]
        proceeds = _period_flow(structural, ("ProceedsFromInsuranceAgencyManagementFeesReceived",), period, target_days=duration)
        if not fee_rows or proceeds["value"] != 1_656_098_000.:
            raise ValueError("ERIE: reciprocal management-fee evidence changed")
        special_context = [{"management_fee_rate": _dimensional_source(structural, fee_rows[0]), "management_fee_proceeds": proceeds, "treatment": "Parent residual income uses reported parent earnings/equity; reciprocal policyholder premiums, reserves, and float are excluded from any issuer-cash bridge."}]
        warning += " The filing reports a 25% management-fee rate and $1.656098B H1 fee proceeds; reciprocal policyholder economics remain outside the parent bridge."
    assumptions = {**profile.public_metadata(), "forecast_years": 5, "normalization_basis": "reported_parent_common_equity_with_history_bounded_roe", "assumption_source_mix": "reported_equity_earnings_company_history_and_finsight_policy", "earnings_multiples": tuple(row["raw_value_per_share"] * row["shares"] / normalized_ttm for row in rows), "current_roe": roes, "current_payout_ratio": policy["payout"], "cost_of_equity": policy["coe"], "terminal_roe": (.085, .105, .115), "terminal_growth": (.01, .02, .025), "shares": shares, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "preferred_claim_status": preferred_status, "equity_floor_basis": "not applied", "calculator_calibration": "Calculator replays the exact residual-income assumptions.", "invalidation": "Invalidate if parent earnings, common equity, preferred claims, class conversion, shares, capital or the named business-cycle conditions leave the bounded range."}
    baseline = BaselineValuation(ticker=ticker, method=policy["method"], method_version=BATCH_37_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported common equity", end_common, AssumptionClassification.REPORTED, "Current parent equity less separately identified preferred claims."), BaselineAssumption("history periods", profile.history_years_used, AssumptionClassification.HISTORICALLY_DERIVED, "Exact annual periods plus current TTM bound the ROE policy.")), warnings=(warning, assumptions["invalidation"]), confidence_reasons=reasons, calculator_link=f"/api/us-valuations/{ticker}/calculator")
    return {"ticker": ticker, "method": policy["method"], "model_version": BATCH_37_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"raw_ttm_common_earnings": raw_ttm, "normalized_ttm_common_earnings": normalized_ttm, "normalization_adjustment": normalization, "beginning_total_equity": prior_total["value"], "ending_total_equity": end_total["value"], "beginning_preferred_claim": prior_preferred, "preferred_claim": preferred, "beginning_common_equity": begin_common, "ending_common_equity": end_common}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "common_earnings_reconstruction": {"latest_fy": annual[-1], "current_ytd": current, "prior_ytd": prior, "raw_ttm": raw_ttm, "normalization": normalization_source, "normalized_ttm": normalized_ttm}, "earnings_attribution_context": earnings_attribution_context, "company_history_profile": profile.as_private_dict(), "equity_model_context": [end_total, prior_total, *preferred_sources, *prior_preferred_sources, share], "specialist_context": special_context, "preferred_context": {"current_status": preferred_status, "prior_status": prior_status}, "event_sources": events, "bridge_treatment": "Equity-level model: client AUM, insurance float/reserves, exchange deposits, sponsored portfolios and operating funding remain inside parent common earnings/equity; no EV bridge and no double NCI subtraction.", "residual_income_trace": {"states": traces}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def _oke_result(submissions: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], event_root: Path, manifest_sha: str) -> dict[str, Any]:
    events = _event_rows("OKE", event_root, manifest_sha)
    normalizer = _normalizer(submissions, facts)
    flows = {field: normalizer.ttm_flow(field) for field in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    cash_fcff = cash_fcff_from_reported(operating_cash_flow=flows["operating_cash_flow"]["value"], capital_expenditures=flows["capital_expenditures"]["value"], spectrum_investment=0., interest_expense=abs(flows["interest_expense"]["value"]), tax_rate=tax_rate)
    _, _, annual = _annual_cash_with_losses(normalizer)
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=flows["revenue"]["value"], ttm_cash_fcff=cash_fcff, ttm_period_end=filing["period_end"], ttm_sources=[source for flow in flows.values() for source in flow["sources"]], valuation_date=BATCH_37_VALUATION_DATE)
    cash_metric, growth_metric = profile.metric("cash_conversion_margin"), profile.metric("revenue_growth")
    if cash_metric is None or growth_metric is None or not profile.full_history:
        raise ValueError("OKE: history unavailable")
    margins = tuple(max(.001, value) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    growth = (max(-.08, min(-.05, growth_metric.low)), max(-.03, min(.02, growth_metric.base)), max(0., min(.06, growth_metric.high)))
    cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), filing["period_end"])
    debt_noncurrent = _instant(structural, ("LongTermDebtNoncurrent",), filing["period_end"])
    debt_current = _instant(structural, ("LongTermDebtCurrent",), filing["period_end"])
    short_debt = _instant(structural, ("ShortTermBorrowings",), filing["period_end"])
    nci = _instant(structural, ("MinorityInterest",), filing["period_end"])
    redeemable_nci = _instant(structural, ("RedeemableNoncontrollingInterestEquityCarryingAmount",), filing["period_end"])
    acquisition_cash = _period_flow(structural, ("PaymentsToAcquireInterestInSubsidiariesAndAffiliates",), filing["period_end"], target_days=180)
    equity_method_impairment = _period_flow(structural, ("EquityMethodInvestmentOtherThanTemporaryImpairment",), filing["period_end"], target_days=180)
    lease_absence = {"source_kind": "structural_statement_absence_check", "accession": structural.get("source_accession"), "period_end": filing["period_end"], "searched_concepts": ["FinanceLeaseLiability", "FinanceLeaseLiabilityCurrent", "FinanceLeaseLiabilityNoncurrent", "CapitalLeaseObligations", "OperatingLeaseLiability"], "treatment": "No separately reported finance/capital lease liability is added; operating lease cash remains inside OCF. This is a source-scope exclusion, not a zero estimate.", "reported_vs_estimated": "source_bounded_absence_check"}
    preferred, preferred_status, preferred_sources = _preferred("OKE", structural, filing["period_end"])
    share = _shares("OKE", structural, facts, filing["period_end"])
    debt = debt_noncurrent["value"] + debt_current["value"] + short_debt["value"]
    claims = nci["value"] + redeemable_nci["value"] + preferred
    acquisition_burden = (acquisition_cash["value"], acquisition_cash["value"] / 2., 0.)
    shares = (share["value"] * 1.015, share["value"], share["value"] * .985)
    rows, traces = [], {}
    for idx, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(flows["revenue"]["value"] * margins[idx] - acquisition_burden[idx], growth[idx], (.01, .02, .025)[idx], (.105, .095, .085)[idx], cash["value"], debt, preferred, nci["value"] + redeemable_nci["value"], shares[idx])
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": max(0., raw), "starting_cash_fcff": state.cash_fcff, "cash_conversion_margin": margins[idx], "acquisition_reinvestment_burden": acquisition_burden[idx], "growth": growth[idx], "wacc": state.wacc, "terminal_growth": state.terminal_growth, "cash_and_investments": state.cash_and_investments, "debt_and_finance_leases": state.interest_bearing_debt, "other_equity_claims": claims, "shares": state.diluted_shares, "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError("OKE: invalid FCFF range")
    reasons = ("NORMALIZED_CYCLICAL_RANGE", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    warning = "Conditional Low pipeline/resource-cycle FCFF baseline. Five-year cash history bounds margins; leverage, project/acquisition spending, commodity-volume timing and integration remain material. The reported $353M H1 acquisition cash is charged as full/half/zero bear/base/bull reinvestment and never added to value; the $60M equity-method impairment remains a noncash diagnostic. The August 3 document is an earnings/guidance release despite a conflicting SEC submissions item string, so no acquisition-close overlay is invented. The August 4 prospectus creates up to $1B of ATM capacity but reports no completed sale; no proceeds or dilution are added."
    assumptions = {**profile.public_metadata(), "forecast_years": FORECAST_YEARS, "normalization_basis": "reported_five_year_cash_fcff_cycle", "assumption_source_mix": "reported_company_history_and_finsight_policy", "cash_conversion_margin": margins, "acquisition_reinvestment_burden": acquisition_burden, "growth": growth, "wacc": (.105, .095, .085), "terminal_growth": (.01, .02, .025), "cash_and_investments": (cash["value"],) * 3, "debt_and_finance_leases": (debt,) * 3, "other_equity_claims": (claims,) * 3, "shares": shares, "cash_bridge_range": {"low": scenario["base"], "midpoint": scenario["base"], "high": scenario["base"], "spread_ratio": 0.}, "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0 else "not applied", "calculator_calibration": "Calculator replays the exact enterprise FCFF base assumptions.", "invalidation": "Invalidate if pipeline cash conversion, acquisition/project reinvestment, capex, debt, leases, NCI/redeemable NCI, preferred claims or shares leave the bounded range."}
    baseline = BaselineValuation(ticker="OKE", method="resource_cycle_fcff", method_version=BATCH_37_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("five-year cash history", profile.history_years_used, AssumptionClassification.HISTORICALLY_DERIVED, "Reported annual and TTM cash conversion anchors the range."),), warnings=(warning, assumptions["invalidation"]), confidence_reasons=reasons, calculator_link="/api/us-valuations/OKE/calculator")
    return {"ticker": "OKE", "method": "resource_cycle_fcff", "model_version": BATCH_37_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": flows["revenue"]["value"], "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": flows["interest_expense"]["value"], "tax_rate": tax_rate, "ttm_cash_fcff": cash_fcff}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": list(annual), "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_sources": [cash, debt_noncurrent, debt_current, short_debt, nci, redeemable_nci, acquisition_cash, equity_method_impairment, lease_absence, *preferred_sources, share], "event_sources": events, "specialist_reinvestment": {"acquisition_cash": acquisition_cash, "scenario_burden": acquisition_burden, "equity_method_impairment": equity_method_impairment, "impairment_treatment": "Noncash impairment remains inside the reported OCF reconciliation and is not subtracted as acquisition cash."}, "bridge_reconciliation": {"cash": cash["value"], "noncurrent_debt": debt_noncurrent["value"], "current_debt": debt_current["value"], "short_term_borrowings": short_debt["value"], "debt_and_finance_leases": debt, "lease_scope": lease_absence, "nci": nci["value"], "redeemable_nci": redeemable_nci["value"], "preferred": preferred, "other_equity_claims": claims, "shares": share["value"]}, "model_trace": {"states": traces}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def _operating_data_result(ticker: str, submissions: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], event_root: Path, manifest_sha: str) -> dict[str, Any]:
    events = _event_rows(ticker, event_root, manifest_sha)
    if ticker == "MCO":
        concept_config = copy.deepcopy(load_concept_config())
        concept_config["fields"]["interest_expense"]["concepts"] = ["InterestPaidNet"]
        normalizer = _normalizer(submissions, facts, concept_config=concept_config)
    else:
        normalizer = _normalizer(submissions, facts)
    flows = {field: normalizer.ttm_flow(field) for field in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    cash_fcff = cash_fcff_from_reported(operating_cash_flow=flows["operating_cash_flow"]["value"], capital_expenditures=flows["capital_expenditures"]["value"], spectrum_investment=0., interest_expense=abs(flows["interest_expense"]["value"]), tax_rate=tax_rate)
    _, _, annual = _annual_cash_with_losses(normalizer)
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=flows["revenue"]["value"], ttm_cash_fcff=cash_fcff, ttm_period_end=filing["period_end"], ttm_sources=[source for flow in flows.values() for source in flow["sources"]], valuation_date=BATCH_37_VALUATION_DATE)
    cash_metric, growth_metric = profile.metric("cash_conversion_margin"), profile.metric("revenue_growth")
    if cash_metric is None or growth_metric is None or not profile.full_history:
        raise ValueError(f"{ticker}: operating cash history unavailable")
    margins = tuple(max(.001, value) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    growth = (max(-.05, min(0., growth_metric.low)), max(-.03, min(.04, growth_metric.base)), max(0., min(.07, growth_metric.high)))
    cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), filing["period_end"])
    investments = _instant(structural, ("ShortTermInvestments",), filing["period_end"])
    debt_total = _instant(structural, ("LongTermDebt",), filing["period_end"])
    debt_current = _instant(structural, ("LongTermDebtCurrent",), filing["period_end"])
    debt_noncurrent = _instant(structural, ("LongTermDebtNoncurrent",), filing["period_end"])
    if debt_current["value"] + debt_noncurrent["value"] != debt_total["value"]:
        raise ValueError(f"{ticker}: debt components do not reconcile")
    preferred, preferred_status, preferred_sources = _preferred(ticker, structural, filing["period_end"])
    try:
        nci = _instant(structural, ("MinorityInterest",), filing["period_end"])
    except ValueError:
        nci = {"source_kind": "structural_statement_absence_check", "accession": structural.get("source_accession"), "period_end": filing["period_end"], "value": 0., "unit": "USD", "treatment": "No NCI line exists in the controlling balance/equity facts; exclusion is source-proven, not blank-to-zero.", "reported_vs_estimated": "source_bounded_absence_check"}
    share = _shares(ticker, structural, facts, filing["period_end"])
    shares = (share["value"] * 1.015, share["value"], share["value"] * .985)
    claims = preferred + nci["value"]
    rows, traces = [], {}
    for idx, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(flows["revenue"]["value"] * margins[idx], growth[idx], (.005, .015, .025)[idx], (.105, .09, .08)[idx], cash["value"] + investments["value"], debt_total["value"], preferred, nci["value"], shares[idx])
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": max(0., raw), "starting_cash_fcff": state.cash_fcff, "cash_conversion_margin": margins[idx], "growth": growth[idx], "wacc": state.wacc, "terminal_growth": state.terminal_growth, "cash_and_investments": state.cash_and_investments, "debt_and_finance_leases": state.interest_bearing_debt, "other_equity_claims": claims, "shares": state.diluted_shares, "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError(f"{ticker}: invalid operating FCFF range")
    reasons = ("CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    warning = ("Conditional Low financial-data subscription FCFF baseline. Fiscal periods are aligned to August 31; recurring software/content investment, debt, leases and subscription retention remain material." if ticker == "FDS" else "Conditional Low ratings/data FCFF baseline. Ratings cycles, subscription retention, debt, restructuring and business-sale effects remain material; the reported sale gain is already removed from OCF and is not adjusted twice.")
    assumptions = {**profile.public_metadata(), "forecast_years": FORECAST_YEARS, "normalization_basis": "reported_five_year_cash_fcff", "assumption_source_mix": "reported_company_history_and_finsight_policy", "cash_conversion_margin": margins, "growth": growth, "wacc": (.105, .09, .08), "terminal_growth": (.005, .015, .025), "cash_and_investments": ((cash["value"] + investments["value"]),) * 3, "debt_and_finance_leases": (debt_total["value"],) * 3, "other_equity_claims": (claims,) * 3, "shares": shares, "cash_bridge_range": {"low": scenario["base"], "midpoint": scenario["base"], "high": scenario["base"], "spread_ratio": 0.}, "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0 else "not applied", "calculator_calibration": "Calculator replays the exact enterprise FCFF base assumptions.", "invalidation": "Invalidate if recurring cash conversion, debt, investments, NCI/preferred claims, shares, ratings/subscription cycles or acquisition effects leave the bounded range."}
    method = "financial_data_subscription_fcff" if ticker == "FDS" else "financial_data_ratings_fcff"
    baseline = BaselineValuation(ticker=ticker, method=method, method_version=BATCH_37_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("five-year cash history", profile.history_years_used, AssumptionClassification.HISTORICALLY_DERIVED, "Reported annual and TTM cash conversion anchors the range."),), warnings=(warning, assumptions["invalidation"]), confidence_reasons=reasons, calculator_link=f"/api/us-valuations/{ticker}/calculator")
    return {"ticker": ticker, "method": method, "model_version": BATCH_37_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": flows["revenue"]["value"], "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": flows["interest_expense"]["value"], "tax_rate": tax_rate, "ttm_cash_fcff": cash_fcff}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": list(annual), "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_sources": [cash, investments, debt_total, debt_current, debt_noncurrent, nci, *preferred_sources, share], "event_sources": events, "bridge_reconciliation": {"cash": cash["value"], "short_term_investments": investments["value"], "debt_total": debt_total["value"], "debt_current": debt_current["value"], "debt_noncurrent": debt_noncurrent["value"], "debt_components_sum": debt_current["value"] + debt_noncurrent["value"], "nci": nci["value"], "preferred": preferred, "other_equity_claims": claims, "shares": share["value"], "treatment": "Total debt is deducted once after proving current plus noncurrent components equal the aggregate; gains reconciled out of OCF are not subtracted again."}, "model_trace": {"states": traces}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def build_batch_37_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path | None = None) -> dict[str, Any]:
    if ticker not in BATCH_37_TICKERS:
        raise ValueError(ticker)
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural_packet = Path(structural_root) / ticker
    structural = json.loads((structural_packet / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural.get("source_accession") != filing["accession"] or structural.get("report_date") != filing["period_end"]:
        raise ValueError(f"{ticker}: controlling source mismatch")
    cache_root = Path(structural_cache_root) if structural_cache_root else Path(structural_root).parent / "batch-37-structural-cache-20260906"
    verification = _verify_source_bundle(ticker=ticker, packet=packet, structural_packet=structural_packet, structural_cache_root=cache_root, filing=filing)
    if ticker == "OKE":
        result = _oke_result(submissions, facts, structural, filing, event_root, verification["source_manifest_sha256"])
    elif ticker in OPERATING_TICKERS:
        result = _operating_data_result(ticker, submissions, facts, structural, filing, event_root, verification["source_manifest_sha256"])
    else:
        result = _financial_result(ticker, facts, structural, filing, event_root, verification["source_manifest_sha256"])
    result["source_ledger"]["runtime_source_verification"] = verification
    return result


if set(POLICY) != set(FINANCIAL_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_37_TICKERS):
    raise RuntimeError("Batch 37 policy mismatch")
