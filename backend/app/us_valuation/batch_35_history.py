"""History-backed practical baselines for controlled Universe Reset Batch 35.

The financial issuers use a common-equity residual-income model.  WMB is the
single resource/asset-backed boundary and uses an operating cash-flow DCF.
The selectors below deliberately use exact filing periods and source facts;
they never use the structural parser's wrapper period as a valuation period.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from app.valuation.bank import residual_income_valuation

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling, _duration, _point
from .batch_08_history import _annual_cash_with_losses
from .batch_16_history import _share_point
from .batch_30_history import _point_unit
from .batch_35 import BATCH_35_MANIFEST, BATCH_35_TICKERS, BATCH_35_VALUATION_DATE
from .history import CompanyHistoryProfile, HistoryObservation, build_cash_fcff_history_profile, summarize_history_metric, HISTORY_POLICY_VERSION
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_35_HISTORY_VERSION = "BATCH-35-SOL-AUDIT-REPAIR-1.2"
FORECAST_YEARS = 8
EVENT_INTEREST_TAX_RATE = .21
EVENT_PROCEEDS_INCOME_OFFSET = (0., .5, 1.)
PASS_TICKERS = frozenset()
CONDITIONAL_TICKERS = frozenset(BATCH_35_TICKERS)
WITHHELD_TICKERS = frozenset()


EQUITY_TICKERS = tuple(ticker for ticker in BATCH_35_TICKERS if ticker != "WMB")
EARNINGS_CANDIDATES: dict[str, tuple[str, ...]] = {
    "WFC": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
    "AON": ("NetIncomeLoss", "ProfitLoss"),
    "SCHW": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
    "GL": ("NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"),
    "AJG": ("NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"),
    "PNC": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
    "RJF": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
    "CFG": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
    "JKHY": ("NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"),
}


POLICY: dict[str, dict[str, Any]] = {
    "WFC": {"method": "diversified_bank_residual_income_equity_earnings", "roe": (.06, .09, .12), "payout": (.30, .40, .50), "coe": (.115, .10, .09), "warning": "Conditional Low diversified-bank residual-income baseline. Credit losses, deposit/funding mix, regulatory capital, preferred claims and net interest margins remain material.", "invalidation": "Invalidate if credit losses, deposits/funding, capital, preferred claims, common equity or shares leave the bounded range."},
    "AON": {"method": "insurance_broker_residual_income_equity_earnings", "roe": (.10, .14, .18), "payout": (.22, .30, .38), "coe": (.105, .09, .08), "warning": "Conditional Low insurance-broker residual-income baseline. Retention, commission growth, acquisition integration, debt and current common equity remain material.", "invalidation": "Invalidate if renewal/commission growth, acquisitions, debt, common equity or shares leave the bounded range."},
    "SCHW": {"method": "broker_dealer_residual_income_equity_earnings", "roe": (.06, .09, .12), "payout": (.35, .45, .55), "coe": (.11, .095, .085), "warning": "Conditional Low broker-dealer residual-income baseline. Client cash economics, net interest margins, market levels, capital and preferred claims remain material.", "invalidation": "Invalidate if client cash, margins, capital, preferred claims, common equity or shares change materially."},
    "GL": {"method": "life_insurance_residual_income_equity_earnings", "roe": (.08, .12, .16), "payout": (.20, .30, .40), "coe": (.115, .10, .09), "warning": "Conditional Low life-insurance residual-income baseline. Mortality, reserve development, policy persistency, investment marks and regulatory capital remain material.", "invalidation": "Invalidate if mortality, reserves, persistency, investment marks, capital, common equity or shares change materially."},
    "AJG": {"method": "insurance_broker_residual_income_equity_earnings", "roe": (.10, .14, .18), "payout": (.20, .28, .36), "coe": (.105, .09, .08), "warning": "Conditional Low insurance-broker residual-income baseline. Acquisition integration, retention, commission growth, debt and dilution remain material.", "invalidation": "Invalidate if acquisitions, renewal/commission growth, debt, common equity or shares change materially."},
    "PNC": {"method": "diversified_bank_residual_income_equity_earnings", "roe": (.06, .09, .12), "payout": (.30, .40, .50), "coe": (.115, .10, .09), "warning": "Conditional Low diversified-bank residual-income baseline. Credit costs, deposit pricing, securities marks, regulatory capital and preferred claims remain material.", "invalidation": "Invalidate if credit/deposit mix, securities, capital, preferred claims, common equity or shares changes materially."},
    "RJF": {"method": "broker_dealer_residual_income_equity_earnings", "roe": (.08, .11, .14), "payout": (.30, .40, .50), "coe": (.11, .095, .085), "warning": "Conditional Low broker-dealer residual-income baseline. Market levels, client assets, recruiting, capital and acquisition activity remain material.", "invalidation": "Invalidate if client assets, market conditions, capital, acquisitions, common equity or shares change materially."},
    "CFG": {"method": "regional_bank_residual_income_equity_earnings", "roe": (.05, .08, .11), "payout": (.25, .35, .45), "coe": (.12, .105, .095), "warning": "Conditional Low regional-bank residual-income baseline. Credit normalization, deposit costs, securities marks, capital and preferred claims remain material.", "invalidation": "Invalidate if credit/deposit mix, securities, capital, preferred claims, common equity or shares changes materially."},
    "JKHY": {"method": "financial_software_residual_income_equity_earnings", "roe": (.10, .14, .18), "payout": (.35, .45, .55), "coe": (.105, .09, .08), "warning": "Conditional Low financial-software residual-income baseline. Recurring retention, implementation timing, acquisition integration, cash conversion and common equity remain material.", "invalidation": "Invalidate if recurring revenue, implementation timing, acquisitions, cash conversion, common equity or shares change materially."},
}


def _rows(facts: dict[str, Any], concept: str, unit: str = "USD") -> list[dict[str, Any]]:
    node = facts.get("facts", {}).get("us-gaap", {}).get(concept, {})
    return [row for row in node.get("units", {}).get(unit, []) if isinstance(row.get("val"), (int, float)) and not isinstance(row.get("val"), bool)]


def _source(row: dict[str, Any], concept: str) -> dict[str, Any]:
    return {"source_kind": "companyfacts", "concept": f"us-gaap:{concept}", "value": float(row["val"]), "unit": "USD", "period_start": row.get("start"), "period_end": row.get("end"), "filed": row.get("filed"), "accession": row.get("accn"), "form": row.get("form"), "reported_vs_estimated": "reported"}


def _annual(facts: dict[str, Any], ticker: str) -> tuple[dict[str, Any], ...]:
    selected: dict[str, tuple[dict[str, Any], str]] = {}
    for concept in EARNINGS_CANDIDATES[ticker]:
        for row in _rows(facts, concept):
            if row.get("form") not in {"10-K", "10-K/A"} or row.get("filed", "") > BATCH_35_VALUATION_DATE or not row.get("start") or not row.get("end"):
                continue
            try:
                span = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
            except (KeyError, ValueError):
                continue
            if not 300 <= span <= 380:
                continue
            old = selected.get(row["end"])
            if old is None or (row.get("filed", ""), row.get("accn", "")) > (old[0].get("filed", ""), old[0].get("accn", "")):
                selected[row["end"]] = (row, concept)
        if len(selected) >= 5:
            break
    if len(selected) < 5:
        raise ValueError(f"{ticker}: fewer than five exact annual earnings periods")
    return tuple({"period_end": end, "value": float(selected[end][0]["val"]), "source": _source(selected[end][0], selected[end][1])} for end in sorted(selected)[-5:])


def _structural_rows(structural: dict[str, Any], names: Iterable[str], *, period_start: str | None, period_end: str, unit: str | None = None, dimensions: bool = False) -> list[dict[str, Any]]:
    names = tuple(names)
    for name in names:
        matches = [row for row in structural.get("facts", []) if row.get("local_name") == name and row.get("period_start") == period_start and row.get("period_end") == period_end and (dimensions or not row.get("dimensions")) and isinstance(row.get("value"), (int, float)) and (unit is None or row.get("unit") == unit)]
        if matches:
            return matches
    return []


def _structural_fact(structural: dict[str, Any], names: Iterable[str], *, period_start: str | None, period_end: str, unit: str | None = None, dimensions: bool = False) -> dict[str, Any]:
    rows = _structural_rows(structural, names, period_start=period_start, period_end=period_end, unit=unit, dimensions=dimensions)
    if not rows:
        raise ValueError(f"structural fact {tuple(names)} {period_start}/{period_end} absent")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural.get("source_accession"), "filed": structural.get("filed_date"), "form": structural.get("form"), "period_start": period_start, "period_end": period_end, "concept": row.get("qname"), "unit": row.get("unit"), "value": float(row["value"]), "reported_vs_estimated": "reported"}


def _instant(structural: dict[str, Any], names: Iterable[str], period_end: str, unit: str = "USD") -> dict[str, Any]:
    return _structural_fact(structural, names, period_start=None, period_end=period_end, unit=unit)


def _flow(structural: dict[str, Any], names: Iterable[str], period_start: str, period_end: str) -> dict[str, Any]:
    return _structural_fact(structural, names, period_start=period_start, period_end=period_end, unit="USD")


def _period_flow(structural: dict[str, Any], names: Iterable[str], end: str, *, target_days: int | None = None) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for name in names:
        for row in structural.get("facts", []):
            if row.get("local_name") != name or row.get("period_end") != end or row.get("period_start") is None or row.get("unit") != "USD" or row.get("dimensions") or not isinstance(row.get("value"), (int, float)):
                continue
            try:
                days = (date.fromisoformat(end) - date.fromisoformat(row["period_start"])).days
            except (KeyError, ValueError):
                continue
            if days >= 45:
                candidates.append((days, row))
        if candidates:
            break
    if not candidates:
        raise ValueError(f"period flow {tuple(names)} ending {end} absent")
    if target_days is None:
        target_days = max(days for days, _ in candidates)
    _, row = min(candidates, key=lambda item: (abs(item[0] - target_days), -item[0]))
    return {"source_kind": "structural_xbrl", "accession": structural.get("source_accession"), "filed": structural.get("filed_date"), "form": structural.get("form"), "period_start": row.get("period_start"), "period_end": end, "concept": row.get("qname"), "unit": row.get("unit"), "value": float(row["value"]), "reported_vs_estimated": "reported"}


def _share(structural: dict[str, Any], facts: dict[str, Any], period_end: str) -> dict[str, Any]:
    names = ("EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding")
    candidates = [row for row in structural.get("facts", []) if row.get("local_name") in names and row.get("period_start") is None and row.get("unit") == "xbrli:shares" and not row.get("dimensions") and isinstance(row.get("value"), (int, float)) and period_end <= str(row.get("period_end", "")) <= BATCH_35_VALUATION_DATE]
    if candidates:
        row = sorted(candidates, key=lambda value: str(value.get("period_end")))[-1]
        return {"source_kind": "structural_xbrl", "accession": structural.get("source_accession"), "filed": structural.get("filed_date"), "period_end": row.get("period_end"), "concept": row.get("qname"), "unit": row.get("unit"), "value": float(row["value"]), "reported_vs_estimated": "reported"}
    for concept in names:
        rows = [row for row in facts.get("facts", {}).get("dei", {}).get(concept, {}).get("units", {}).get("shares", []) if row.get("end") == period_end and isinstance(row.get("val"), (int, float))]
        if rows:
            row = max(rows, key=lambda value: (value.get("filed", ""), value.get("accn", "")))
            return {**_source(row, concept), "unit": "shares"}
    raise ValueError(f"{period_end}: common shares absent")


def _companyfacts_instant(facts: dict[str, Any], names: Iterable[str], period_end: str) -> dict[str, Any]:
    for name in names:
        rows = [row for row in _rows(facts, name) if row.get("end") == period_end and not row.get("start") and row.get("filed", "") <= BATCH_35_VALUATION_DATE]
        if rows:
            row = max(rows, key=lambda value: (value.get("filed", ""), value.get("accn", "")))
            return _source(row, name)
    raise ValueError(f"companyfacts instant {tuple(names)}/{period_end} absent")


def _equity(structural: dict[str, Any], period_end: str, facts: dict[str, Any] | None = None) -> dict[str, Any]:
    direct = ("StockholdersEquityAttributableToParent", "StockholdersEquityAttributableToParentEntity", "StockholdersEquity")
    try:
        return _instant(structural, direct, period_end)
    except ValueError:
        try:
            total = _instant(structural, ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",), period_end)
            nci = _instant(structural, ("MinorityInterest", "NoncontrollingInterestInConsolidatedEntity"), period_end)
        except ValueError:
            if facts is None:
                raise
            # Some issuers do not repeat the prior-year balance sheet in the
            # current structural packet.  A cutoff-safe companyfacts instant
            # is acceptable for the prior anchor and remains fully traced.
            return _companyfacts_instant(facts, ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"), period_end)
        return {"source_kind": "derived_structural_xbrl", "accession": structural.get("source_accession"), "period_end": period_end, "unit": "USD", "value": total["value"] - nci["value"], "method": "consolidated_equity_less_nci", "sources": [total, nci], "reported_vs_estimated": "reported_components_with_derived_attribution"}


def _pnc_preferred_claim(structural: dict[str, Any], period_end: str) -> tuple[float, str, list[dict[str, Any]], tuple[float, float, float]] | None:
    """Recover PNC's economic preferred claim from its regulatory-capital table.

    PNC's balance-sheet ``PreferredStockValue`` is par value and rounds to
    zero; it is not evidence that the preferred economic claim is absent.
    The same filing reports $5.879B of preferred stock plus related surplus
    and a $119M preferred issuance in the FirstBank acquisition.
    """
    if structural.get("source_accession") != "0001628280-26-053170":
        return None
    filing_source = {
        "source_kind": "sec_filing_table",
        "accession": structural.get("source_accession"),
        "filed": structural.get("filed_date"),
        "form": structural.get("form"),
        "period_end": "2026-06-30",
        "concept": "Basel III capital — preferred stock plus related surplus",
        "unit": "USD",
        "value": 5_879_000_000.,
        "table_locator": "Table 30: Basel III Capital — Additional tier 1 capital",
        "source_url": "https://www.sec.gov/Archives/edgar/data/713676/000162828026053170/pnc-20260630.htm",
        "document_sha256": "83eaaaefcbefccd03ad03b4ba7ef2288d0a375e548837fc777cb3523a5d33824",
        "package_manifest_sha256": "297cf4f9ecf4e3d276b73b10d3aeeae3c24ec1bb60af2c2ca8e0997d0f9c8ea1",
        "reported_vs_estimated": "reported",
    }
    if period_end == "2026-06-30":
        return 5_879_000_000., "reported_regulatory_capital_preferred_claim", [filing_source], (5_879_000_000.,) * 3
    if period_end == "2025-12-31":
        issuance_rows = _structural_rows(
            structural,
            ("StockIssuedDuringPeriodValueAcquisitions", "BusinessCombinationConsiderationTransferredEquityInterestsIssuedAndIssuable"),
            period_start="2026-01-01",
            period_end="2026-06-30",
            unit="USD",
            dimensions=True,
        )
        preferred_rows = [
            row for row in issuance_rows
            if float(row.get("value", 0.)) == 119_000_000.
            and any("PreferredStockMember" in member for dimension in row.get("dimensions", []) for member in dimension)
        ]
        if not preferred_rows:
            raise ValueError("PNC: reported FirstBank preferred issuance missing")
        issuance_source = {
            "source_kind": "structural_xbrl",
            "accession": structural.get("source_accession"),
            "filed": structural.get("filed_date"),
            "form": structural.get("form"),
            "period_start": preferred_rows[0].get("period_start"),
            "period_end": preferred_rows[0].get("period_end"),
            "concept": preferred_rows[0].get("qname"),
            "unit": preferred_rows[0].get("unit"),
            "value": 119_000_000.,
            "dimensions": preferred_rows[0].get("dimensions"),
            "reported_vs_estimated": "reported",
        }
        prior = 5_760_000_000.
        derived = {
            "source_kind": "derived_reported_components",
            "period_end": period_end,
            "unit": "USD",
            "value": prior,
            "method": "current preferred stock plus related surplus less FirstBank preferred issuance",
            "sources": [filing_source, issuance_source],
            "reported_vs_estimated": "reported_components_with_derived_prior",
        }
        return prior, "derived_period_specific_preferred_claim", [derived], (prior,) * 3
    return None


def _preferred(ticker: str, structural: dict[str, Any], period_end: str) -> tuple[float, str, list[dict[str, Any]], tuple[float, float, float]]:
    if ticker == "PNC":
        pnc_claim = _pnc_preferred_claim(structural, period_end)
        if pnc_claim is not None:
            return pnc_claim
    names = ("PreferredStockLiquidationPreferenceValue", "PreferredStockValue", "PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount")
    zero_row: dict[str, Any] | None = None
    for name in names:
        try:
            row = _instant(structural, (name,), period_end)
            value = float(row["value"])
            if value > 0:
                return value, "reported_preferred_claim", [row], (value, value, value)
            zero_row = row
        except ValueError:
            continue
    try:
        row = _instant(structural, ("PreferredStockSharesOutstanding",), period_end, unit="xbrli:shares")
        # A zero share count plus a zero carrying-value row is affirmative
        # evidence of absence.  Positive shares alone are evidence of a claim,
        # but never convert shares to currency by silently assuming zero.
        if float(row["value"]) == 0. and zero_row is not None:
            return 0., "reported_preferred_absence", [zero_row, row], (0., 0., 0.)
        if float(row["value"]) > 0:
            return 0., "preferred_shares_only_governed_claim", [row] + ([zero_row] if zero_row else []), (0., 0., 0.)
    except ValueError:
        pass
    if zero_row is not None:
        return 0., "reported_preferred_absence", [zero_row], (0., 0., 0.)
    absence = {"source_kind": "structural_xbrl_absence_check", "accession": structural.get("source_accession"), "period_end": period_end, "searched_concepts": list(names) + ["PreferredStockSharesOutstanding"], "reported_vs_estimated": "source_bounded_absence_check"}
    return 0., "preferred_claim_bounded_from_no_reported_claim_row", [absence], (0., 0., 0.)


def _event_rows(ticker: str, event_root: Path | None, source_manifest_sha256: str) -> list[dict[str, Any]]:
    if event_root is None:
        raise ValueError(f"{ticker}: complete cutoff-event ledger is required")
    packet = Path(event_root) / ticker
    receipt_path = packet / "source-receipt.json"
    if not receipt_path.exists():
        raise ValueError(f"{ticker}: cutoff-event screening receipt is missing")
    receipt = json.loads(receipt_path.read_text())
    screened = receipt.get("screened_filing") or {}
    if (
        receipt.get("schema_version") != "FINSIGHT-BATCH-35-EVENT-LEDGER-1"
        or receipt.get("ticker") != ticker
        or receipt.get("valuation_date") != BATCH_35_VALUATION_DATE
        or receipt.get("source_manifest_sha256") != source_manifest_sha256
        or screened.get("filed", "") > BATCH_35_VALUATION_DATE
        or receipt.get("decision") not in {"accepted", "rejected"}
    ):
        raise ValueError(f"{ticker}: invalid event source")
    documents = []
    for document in receipt.get("documents", []):
        path = packet / document["document"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if digest != document.get("sha256"):
            raise ValueError(f"{ticker}: event document hash mismatch")
        documents.append(document)
    return [{"source_kind": "sec_event_screening", "decision": receipt["decision"], "accession": screened.get("accession"), "filed": screened.get("filed"), "period_end": screened.get("report_date"), "form": screened.get("form"), "items": screened.get("items"), "documents": documents, "source_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(), "reported_terms": receipt.get("reported_terms", {}), "treatment": receipt.get("treatment"), "reported_vs_estimated": "reported" if receipt["decision"] == "accepted" else "screened_and_rejected"}]


def _verify_source_bundle(
    *,
    ticker: str,
    packet: Path,
    structural_packet: Path,
    structural_cache_root: Path,
    filing: dict[str, Any],
) -> dict[str, Any]:
    """Bind every load-bearing local input to its immutable capture receipt."""
    issuer = next(row for row in BATCH_35_MANIFEST if row.ticker == ticker)
    source_manifest_path = packet / "source-manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text())
    if source_manifest.get("issuer", {}).get("ticker") != ticker or source_manifest.get("issuer", {}).get("cik") != issuer.cik:
        raise ValueError(f"{ticker}: source packet identity mismatch")
    verified_packet_hashes: dict[str, str] = {}
    for name, expected in source_manifest.get("packet_payload_sha256", {}).items():
        path = packet / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if actual != expected:
            raise ValueError(f"{ticker}: source packet hash mismatch for {name}")
        verified_packet_hashes[name] = actual

    receipt_path = structural_packet / "source-receipt.json"
    structural_path = structural_packet / "structural-filing.json"
    package_path = structural_packet / "package-manifest.json"
    receipt = json.loads(receipt_path.read_text())
    package = json.loads(package_path.read_text())
    expected_filing = {
        "accession": filing["accession"],
        "filed": filing["filed"],
        "form": filing["form"],
        "report_date": filing["period_end"],
    }
    actual_filing = receipt.get("filing") or {}
    if (
        receipt.get("schema_version") != "FINSIGHT-BATCH-35-STRUCTURAL-SOURCE-1"
        or receipt.get("ticker") != ticker
        or receipt.get("cik") != issuer.cik
        or receipt.get("valuation_date") != BATCH_35_VALUATION_DATE
        or any(actual_filing.get(key) != value for key, value in expected_filing.items())
    ):
        raise ValueError(f"{ticker}: structural receipt identity mismatch")
    structural_hash = hashlib.sha256(structural_path.read_bytes()).hexdigest()
    package_hash = hashlib.sha256(package_path.read_bytes()).hexdigest()
    if structural_hash != receipt.get("structural_filing_sha256") or package_hash != receipt.get("package_manifest_sha256"):
        raise ValueError(f"{ticker}: structural source hash mismatch")
    entrypoint = package.get("entrypoint_local_path")
    package_entry = next((row for row in package.get("files", []) if row.get("local_path") == entrypoint), None)
    search_root = Path(structural_cache_root) / "filings" / ticker
    html_path = next(search_root.glob(f"**/{entrypoint}"), None) if entrypoint else None
    if package_entry is None or html_path is None:
        raise ValueError(f"{ticker}: primary filing document unavailable")
    document_hash = hashlib.sha256(html_path.read_bytes()).hexdigest()
    if document_hash != package_entry.get("sha256"):
        raise ValueError(f"{ticker}: primary filing document hash mismatch")
    return {
        "source_kind": "runtime_verified_source_bundle",
        "ticker": ticker,
        "cik": issuer.cik,
        "source_manifest": str(source_manifest_path),
        "source_manifest_sha256": hashlib.sha256(source_manifest_path.read_bytes()).hexdigest(),
        "packet_payload_sha256": verified_packet_hashes,
        "structural_receipt": str(receipt_path),
        "structural_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "structural_filing_sha256": structural_hash,
        "package_manifest_sha256": package_hash,
        "primary_document": entrypoint,
        "primary_document_sha256": document_hash,
        "accession": filing["accession"],
        "filed": filing["filed"],
        "period_end": filing["period_end"],
        "verified": True,
    }


def _financial_result(ticker: str, facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], event_root: Path | None, source_manifest_sha256: str) -> dict[str, Any]:
    policy = POLICY[ticker]
    event_rows = _event_rows(ticker, event_root, source_manifest_sha256)
    accepted_event = event_rows[0] if event_rows[0]["decision"] == "accepted" else None
    event_terms = accepted_event["reported_terms"] if accepted_event else {}
    period = filing["period_end"]
    annual = _annual(facts, ticker)
    # Select the longest current filing flow (usually six months; nine months
    # for issuers with a non-calendar fiscal year), then match its duration in
    # the prior year.  This avoids assuming every Q2 issuer is calendar-year.
    current_raw = _period_flow(structural, EARNINGS_CANDIDATES[ticker], period)
    current_start = current_raw["period_start"]
    duration_days = (date.fromisoformat(period) - date.fromisoformat(current_start)).days
    prior_end = f"{int(period[:4]) - 1}{period[4:]}"
    prior_raw = _period_flow(structural, EARNINGS_CANDIDATES[ticker], prior_end, target_days=duration_days)
    current = dict(current_raw)
    prior = dict(prior_raw)
    ttm = float(annual[-1]["value"]) + float(current["value"]) - float(prior["value"])
    end_equity = _equity(structural, period, facts)
    # The latest audited annual end is the proper opening equity anchor.  It
    # also handles non-calendar issuers such as RJF (September) and JKHY (June).
    prior_equity_period = annual[-1]["period_end"]
    prior_equity = _equity(structural, prior_equity_period, facts)
    preferred, preferred_status, preferred_context, preferred_range = _preferred(ticker, structural, period)
    prior_preferred, prior_preferred_status, prior_preferred_context, prior_preferred_range = _preferred(ticker, structural, prior_equity_period)
    if preferred_status in {"preferred_claim_bounded_from_no_reported_claim_row", "preferred_shares_only_governed_claim"}:
        preferred_range = (0., float(end_equity["value"]) * .01, float(end_equity["value"]) * .03)
        preferred = preferred_range[1]
    if prior_preferred_status in {"preferred_claim_bounded_from_no_reported_claim_row", "preferred_shares_only_governed_claim"}:
        prior_preferred_range = (0., float(prior_equity["value"]) * .01, float(prior_equity["value"]) * .03)
        prior_preferred = prior_preferred_range[1]
    event_equity_proceeds = float(event_terms.get("preferred_claim", 0.)) if ticker == "CFG" else 0.
    event_preferred_claim = event_equity_proceeds
    if event_preferred_claim:
        preferred_range = tuple(value + event_preferred_claim for value in preferred_range)
        preferred += event_preferred_claim
        preferred_status = "reported_preferred_claim_plus_cutoff_issuance"
    begin_common = float(prior_equity["value"]) - prior_preferred
    post_event_total_equity = float(end_equity["value"]) + event_equity_proceeds
    end_common = post_event_total_equity - preferred
    share_row = _share(structural, facts, period)
    current_shares = float(share_row["value"])
    if min(ttm, begin_common, end_common, current_shares) <= 0:
        raise ValueError(f"{ticker}: nonpositive common equity, earnings, or shares")
    shares = (current_shares * 1.015, current_shares, current_shares * .985)
    observations = [HistoryObservation("annual", row["period_end"], int(row["period_end"][:4]), row["value"], "USD", "reported annual earnings", (row["source"],)) for row in annual]
    observations.append(HistoryObservation("operating_ttm", period, None, ttm, "USD", "latest FY + current filing YTD - prior comparable YTD", (annual[-1]["source"], current, prior)))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "financial_equity_residual_income", BATCH_35_VALUATION_DATE, tuple(row["period_end"] for row in annual), (metric,), True, "reported_and_company_history")
    history_low = max(.02, min(metric.low, ttm) / max(end_common, 1.))
    history_high = max(history_low, max(metric.high, ttm) / max(end_common, 1.))
    history_mid = max(history_low, min(history_high, metric.base / max(end_common, 1.)))
    modeled_roe = tuple(min(value, history_high) for value in policy["roe"])
    if not history_low <= modeled_roe[0] <= modeled_roe[1] <= modeled_roe[2] <= history_high or modeled_roe[0] == modeled_roe[2]:
        modeled_roe = (history_low, (history_low + history_high) / 2., history_high)
    if ticker in {"PNC", "SCHW"}:
        annualized_interest = float(event_terms["annualized_gross_interest"])
        illustrative_after_tax = annualized_interest * (1 - EVENT_INTEREST_TAX_RATE)
        event_earnings_drag = tuple(illustrative_after_tax * (1 - offset) for offset in EVENT_PROCEEDS_INCOME_OFFSET)
        event_interest_tax_rate: float | None = EVENT_INTEREST_TAX_RATE
        event_proceeds_income_offset = EVENT_PROCEEDS_INCOME_OFFSET
    elif ticker == "CFG":
        annual_preferred_dividend = float(event_terms["annual_preferred_dividend"])
        event_earnings_drag = (annual_preferred_dividend,) * 3
        event_interest_tax_rate = None
        event_proceeds_income_offset = (0., 0., 0.)
    else:
        event_earnings_drag = (0., 0., 0.)
        event_interest_tax_rate = None
        event_proceeds_income_offset = (0., 0., 0.)
    pre_event_modeled_roe = modeled_roe
    scenario_preferred_claims = (preferred_range[2], preferred_range[1], preferred_range[0])
    scenario_roes = tuple(
        max(.01, modeled_roe[idx] - event_earnings_drag[idx] / max(post_event_total_equity - scenario_preferred_claims[idx], 1.))
        for idx in range(3)
    )
    rows, traces = [], {}
    for idx, name in enumerate(("bear", "base", "bull")):
        scenario_end = post_event_total_equity - scenario_preferred_claims[idx]
        trace = residual_income_valuation(book_value_per_share=scenario_end / shares[idx], current_roe=scenario_roes[idx], cost_of_equity=policy["coe"][idx], current_payout_ratio=policy["payout"][idx], terminal_roe=(.085, .105, .115)[idx], terminal_growth=(.01, .02, .025)[idx], years=5)
        raw = float(trace["intrinsic_value"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": raw, "book_value_per_share": scenario_end / shares[idx], "current_roe": scenario_roes[idx], "pre_event_current_roe": pre_event_modeled_roe[idx], "event_forward_common_earnings_drag": event_earnings_drag[idx], "event_proceeds_income_offset": event_proceeds_income_offset[idx], "current_payout_ratio": policy["payout"][idx], "cost_of_equity": policy["coe"][idx], "terminal_roe": (.085, .105, .115)[idx], "terminal_growth": (.01, .02, .025)[idx], "shares": shares[idx], "preferred_claim": scenario_preferred_claims[idx], "ending_common_equity": scenario_end, "limited_liability_floor_applied": False})
        traces[name] = trace
    scenario = {"low": rows[0]["raw_value_per_share"], "base": rows[1]["raw_value_per_share"], "high": rows[2]["raw_value_per_share"]}
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid residual-income range")
    reasons = ("SPECIALIST_MODEL_UNCERTAINTY", "PROVISIONAL_BANK_CAPITAL_RANGE") if ticker in {"WFC", "SCHW", "PNC", "CFG", "RJF"} else ("SPECIALIST_MODEL_UNCERTAINTY",)
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    warning = policy["warning"] + (f" Preferred carrying value is unavailable; the explicit governed common-equity claim sensitivity is bear ${preferred_range[2] / 1_000_000:.1f}M (3%), base ${preferred_range[1] / 1_000_000:.1f}M (1%), and bull $0 (0%), rather than a missing-value zero." if preferred_status in {"preferred_claim_bounded_from_no_reported_claim_row", "preferred_shares_only_governed_claim"} else "")
    if ticker == "PNC":
        warning += " The pre-cutoff $2.0B note issuance implies $102.94M annual gross interest; using a governed 21% tax rate and 0%/50%/100% proceeds-income offset, an $81.32M/$40.66M/$0 earnings drag is applied for bear/base/bull."
    elif ticker == "SCHW":
        warning += " The pre-cutoff $2.6B note issuance implies $140.19M annual gross interest; using a governed 21% tax rate and 0%/50%/100% proceeds-income offset, a $110.75M/$55.38M/$0 earnings drag is applied for bear/base/bull."
    elif ticker == "CFG":
        warning += " The pre-cutoff $400M Series J proceeds and preferred claim offset in common book equity; its $27M annual preferred dividend is deducted from forward common earnings."
    elif ticker == "JKHY":
        warning += " The August 11 cutoff filing reports $9.3M Q4 and $42.8M FY2026 deconversion revenue; it is disclosed but excluded from normalized recurring earnings because the issuer identifies it as non-recurring and does not report FY GAAP earnings in that filing."
    assumptions = {**profile.public_metadata(), "forecast_years": 5, "normalization_basis": "reported_common_equity_with_history_bounded_roe", "assumption_source_mix": "reported_equity_earnings_and_company_history_plus_finsight_policy", "equity_floor_basis": "not applied", "earnings_multiples": tuple(row["raw_value_per_share"] * row["shares"] / ttm for row in rows), "calculator_calibration": "Calculator replays the exact residual-income base assumptions and varies ROE, payout, cost of equity, terminal ROE, terminal growth, and forecast years.", "roe_scenario_bridge": {"reported_ttm_common_earnings": ttm, "reported_ttm_roe": ttm / max((begin_common + end_common) / 2., 1.), "reported_history_annual_plus_ttm_range": (metric.low, metric.base, metric.high), "reported_history_roe_range": (history_low, history_mid, history_high), "policy_roe_target": policy["roe"], "pre_event_modeled_roe": pre_event_modeled_roe, "event_forward_common_earnings_drag": event_earnings_drag, "event_interest_tax_rate": event_interest_tax_rate, "event_proceeds_income_offset": event_proceeds_income_offset, "modeled_roe": scenario_roes, "classification": "finsight_assumption_bounded_by_reported_history_current_equity_and_cutoff_events"}, "current_roe": scenario_roes, "current_payout_ratio": policy["payout"], "cost_of_equity": policy["coe"], "terminal_roe": (.085, .105, .115), "terminal_growth": (.01, .02, .025), "shares": shares, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "preferred_claim_status": preferred_status, "preferred_claim_range": preferred_range, "preferred_claim_scenario_values": scenario_preferred_claims, "event_equity_proceeds": event_equity_proceeds, "event_preferred_claim": event_preferred_claim, "event_forward_common_earnings_drag": event_earnings_drag, "event_interest_tax_rate": event_interest_tax_rate, "event_proceeds_income_offset": event_proceeds_income_offset, "preferred_book_and_earnings_reconciliation": "Preferred stock plus related surplus is removed once from total shareholders' equity to obtain common book equity. Preferred dividends are separately removed once in reported common earnings; the stock claim and period earnings attribution are complementary, not duplicate deductions." if ticker == "PNC" else "Period-specific preferred claims are removed once from total shareholders' equity; common earnings use the issuer's common-attributable line where reported.", "invalidation": policy["invalidation"]}
    baseline = BaselineValuation(ticker=ticker, method=policy["method"], method_version=BATCH_35_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported common equity", end_common, AssumptionClassification.REPORTED, "Current equity less separately identified preferred claims."), BaselineAssumption("five exact annual periods", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Annual history bounds the ROE scenarios.")), warnings=(warning, policy["invalidation"]), confidence_reasons=reasons, calculator_link=f"/api/us-valuations/{ticker}/calculator")
    availability = "available" if ticker in PASS_TICKERS else "conditional_estimate"
    return {"ticker": ticker, "method": policy["method"], "model_version": BATCH_35_HISTORY_VERSION, "availability_type": availability, "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_common_earnings": ttm, "beginning_total_equity": float(prior_equity["value"]), "ending_total_equity": float(end_equity["value"]), "post_event_total_equity": post_event_total_equity, "beginning_preferred_equity": prior_preferred, "preferred_equity": preferred, "beginning_common_equity": begin_common, "ending_common_equity": end_common}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "common_earnings_reconstruction": {"latest_fy": annual[-1], "current_ytd": current, "prior_ytd": prior, "ttm": ttm}, "company_history_profile": profile.as_private_dict(), "equity_model_context": [end_equity, prior_equity, *preferred_context, *prior_preferred_context, share_row], "preferred_context": {"current": preferred_context, "prior": prior_preferred_context, "current_status": preferred_status, "prior_status": prior_preferred_status, "prior_equity_period": prior_equity_period}, "event_sources": event_rows, "bridge_treatment": "Equity-level model: deposits, policy reserves, client assets, investments and operating funding remain inside common earnings/equity and are not EV-bridged. Cutoff financing proceeds and matching claims offset in current common book equity; explicit forward common-earnings effects are scenario-adjusted.", "residual_income_trace": {"states": traces, "clean_surplus_ddm_is_reconciliation_not_independent_evidence": True}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False, "selection_basis": "source receipt report date plus exact fact periods"}}, "warning": warning, "baseline": baseline.as_private_dict()}


def _wmb_result(submissions: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any], filing: dict[str, Any], event_root: Path | None, source_manifest_sha256: str) -> dict[str, Any]:
    ticker = "WMB"
    event_rows = _event_rows(ticker, event_root, source_manifest_sha256)
    normalizer = _normalizer(submissions, facts)
    # Use the filing packet's reported statement periods, while retaining the
    # normalizer's companyfacts lineage for annual history and tax evidence.
    flows = {field: normalizer.ttm_flow(field) for field in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    try:
        tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    except ValueError:
        tax_rate, tax_sources = .21, ()
    tax_rate = tax_rate if .05 <= tax_rate <= .30 else .21
    cash_fcff = cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]), capital_expenditures=float(flows["capital_expenditures"]["value"]), spectrum_investment=0., interest_expense=abs(float(flows["interest_expense"]["value"])), tax_rate=tax_rate)
    annual = _annual_cash_with_losses(normalizer)[2]
    sources = [source for flow in flows.values() for source in flow.get("sources", [])]
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=float(flows["revenue"]["value"]), ttm_cash_fcff=cash_fcff, ttm_period_end=filing["period_end"], ttm_sources=sources, valuation_date=BATCH_35_VALUATION_DATE)
    cash_metric = profile.metric("cash_conversion_margin")
    growth_metric = profile.metric("revenue_growth")
    if cash_metric is None or growth_metric is None or not profile.full_history:
        raise ValueError("WMB: cash history unavailable")
    margins = tuple(max(.001, float(value)) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    growth = (max(-.08, min(0., growth_metric.low)), max(-.05, min(.03, growth_metric.base)), max(0., min(.06, growth_metric.high)))
    cash_row = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"), filing["period_end"])
    debt_row = _instant(structural, ("LongTermDebtAndCapitalLeaseObligations", "LongTermDebt"), filing["period_end"])
    current_debt_row = _instant(structural, ("LongTermDebtAndCapitalLeaseObligationsCurrent", "LongTermDebtCurrent"), filing["period_end"])
    commercial_paper_row = _instant(structural, ("CommercialPaper",), filing["period_end"])
    nci_row = _instant(structural, ("MinorityInterest", "NoncontrollingInterestInConsolidatedEntity"), filing["period_end"])
    preferred_row = _instant(structural, ("PreferredStockValue",), filing["period_end"])
    cash = float(cash_row["value"])
    debt = float(debt_row["value"]) + float(current_debt_row["value"]) + float(commercial_paper_row["value"])
    nci = float(nci_row["value"])
    preferred = float(preferred_row["value"])
    claims = nci + preferred
    # Only an aggregate cash-plus-restricted-cash fact is reported.  Bound its
    # common-equity availability instead of treating all of it as surplus.
    cash_values = (0., cash / 2., cash)
    investment_absence = {
        "source_kind": "structural_xbrl_absence_check",
        "accession": structural.get("source_accession"),
        "period_end": filing["period_end"],
        "searched_concepts": ["ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
        "treatment": "No separate investment asset is included; this is exclusion, not a zero-valued estimate.",
        "reported_vs_estimated": "source_bounded_exclusion",
    }
    shares = _share(structural, facts, filing["period_end"])
    share_value = float(shares["value"])
    rows, traces = [], {}
    for idx, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(float(flows["revenue"]["value"]) * margins[idx], growth[idx], (.01, .02, .025)[idx], (.105, .095, .085)[idx], cash_values[idx], debt, 0., claims, share_value * (1.015, 1., .985)[idx])
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": max(0., raw), "starting_cash_fcff": state.cash_fcff, "cash_conversion_margin": margins[idx], "growth": growth[idx], "wacc": state.wacc, "terminal_growth": state.terminal_growth, "cash_and_investments": state.cash_and_investments, "debt_and_finance_leases": state.interest_bearing_debt, "other_equity_claims": state.noncontrolling_interests, "shares": state.diluted_shares, "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError("WMB: invalid FCFF range")
    reasons = ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    bridge_low = scenario["base"] - cash_values[1] / share_value
    bridge_high = scenario["base"] + cash_values[1] / share_value
    reliability = assess_reliability(accounting_low=bridge_low, accounting_base=scenario["base"], accounting_high=bridge_high, scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=reasons)
    warning = "Conditional Low resource-cycle FCFF baseline. Pipeline volumes, commodity/contract timing, leverage, investment claims and energy-transition spending remain material. Noncurrent debt, current maturities, and commercial paper are included; the reported $203M cash-plus-restricted-cash aggregate is conservatively ranged from $0 to $203M. The signed Power Innovation JV commits $5.34B of partner capital for a 49% NCI, including $4.4B expected growth-capex funding and about $0.9B additional consideration; it remains an event-conditioned warning until closing and project cash economics are filed."
    assumptions = {**profile.public_metadata(), "forecast_years": FORECAST_YEARS, "cash_conversion_margin": margins, "growth": growth, "wacc": (.105, .095, .085), "terminal_growth": (.01, .02, .025), "cash_and_investments": cash_values, "cash_bridge_range": {"low": bridge_low, "midpoint": scenario["base"], "high": bridge_high, "spread_ratio": (bridge_high - bridge_low) / scenario["base"]}, "debt_and_finance_leases": (debt,) * 3, "other_equity_claims": (claims,) * 3, "shares": (share_value * 1.015, share_value, share_value * .985), "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0 else "not applied", "calculator_calibration": "Calculator replays the exact faded-cash base, including the reported claims bridge and bounded aggregate-cash midpoint.", "assumption_classification": {"cash_conversion_margin": "historically_derived", "growth": "history_bounded_finsight_assumption", "wacc": "finsight_assumption", "bridge": "reported_structural_aggregates", "cash_availability": "reported_aggregate_governed_zero_to_full_range", "unreported_investments": "excluded_not_zero_imputed"}, "invalidation": "Invalidate if pipeline/cash conversion, debt, claims or shares leave the stated range."}
    baseline = BaselineValuation(ticker=ticker, method="resource_cycle_fcff", method_version=BATCH_35_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("cash conversion history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Reported annual and TTM cash conversion anchors the range."),), warnings=(warning, "Invalidate if pipeline/cash conversion, debt, claims or shares leave the stated range."), confidence_reasons=reasons, calculator_link="/api/us-valuations/WMB/calculator")
    return {"ticker": ticker, "method": "resource_cycle_fcff", "model_version": BATCH_35_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": float(flows["revenue"]["value"]), "ttm_operating_cash_flow": float(flows["operating_cash_flow"]["value"]), "ttm_reinvestment": float(flows["capital_expenditures"]["value"]), "ttm_interest": float(flows["interest_expense"]["value"]), "tax_rate": tax_rate, "ttm_cash_fcff": cash_fcff}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": list(annual), "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_sources": [cash_row, debt_row, current_debt_row, commercial_paper_row, nci_row, preferred_row, investment_absence, shares], "event_sources": event_rows, "model_trace": {"forecast_years": FORECAST_YEARS, "states": traces}, "bridge_reconciliation": {"reported_cash_and_restricted_cash": cash, "cash_availability_range": cash_values, "noncurrent_debt_and_finance_leases": float(debt_row["value"]), "current_debt": float(current_debt_row["value"]), "commercial_paper": float(commercial_paper_row["value"]), "debt_and_finance_leases": debt, "noncontrolling_interest": nci, "preferred_equity": preferred, "other_equity_claims": claims, "shares": share_value, "treatment": "Reported consolidated aggregates; noncurrent debt, current maturities, and commercial paper are summed once; the inseparable cash-plus-restricted-cash aggregate is ranged from zero to full availability; no unreported investment asset is imputed; preferred equity is deducted separately from common value."}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False, "selection_basis": "source receipt report date plus exact fact periods"}}, "warning": warning, "baseline": baseline.as_private_dict()}


def build_batch_35_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path | None = None, structural_cache_root: Path | None = None) -> dict[str, Any]:
    if ticker not in BATCH_35_TICKERS:
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
    cache_root = Path(structural_cache_root) if structural_cache_root is not None else Path(structural_root).parent / "batch-35-structural-cache-20260904"
    verification = _verify_source_bundle(ticker=ticker, packet=packet, structural_packet=structural_packet, structural_cache_root=cache_root, filing=filing)
    result = _wmb_result(submissions, facts, structural, filing, event_root, verification["source_manifest_sha256"]) if ticker == "WMB" else _financial_result(ticker, facts, structural, filing, event_root, verification["source_manifest_sha256"])
    if ticker == "PNC":
        pnc_sources = result["source_ledger"]["preferred_context"]["current"]
        table_source = next(row for row in pnc_sources if row.get("source_kind") == "sec_filing_table")
        if table_source.get("document_sha256") != verification["primary_document_sha256"]:
            raise ValueError("PNC: preferred table source is not the runtime-verified filing")
    result["source_ledger"]["runtime_source_verification"] = verification
    return result


if set(POLICY) != set(EQUITY_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_35_TICKERS):
    raise RuntimeError("Batch 35 policy mismatch")
