"""Point-in-time cash-flow and bridge inputs for controlled Batch 02."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from numbers import Real
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

from .batch_02 import BATCH_02_VALUATION_DATE
from .xbrl import CompanyFactsNormalizer


NUMERIC_CANDIDATES = frozenset({"VZ", "T", "NFLX", "TMUS"})


def cash_fcff_from_reported(
    *,
    operating_cash_flow: float,
    capital_expenditures: float,
    spectrum_investment: float,
    interest_expense: float,
    tax_rate: float,
) -> float:
    """Reconcile cash FCFF without silently dropping spectrum investment."""

    values = (
        operating_cash_flow,
        capital_expenditures,
        spectrum_investment,
        interest_expense,
        tax_rate,
    )
    if any(
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(float(value))
        for value in values
    ):
        raise ValueError("cash-FCFF inputs must be finite")
    if min(capital_expenditures, spectrum_investment, interest_expense) < 0:
        raise ValueError("cash-FCFF reinvestment and interest must be nonnegative")
    if not 0 <= tax_rate <= 1:
        raise ValueError("cash-FCFF tax rate must be between zero and one")
    return (
        float(operating_cash_flow)
        - float(capital_expenditures)
        - float(spectrum_investment)
        + float(interest_expense) * (1 - float(tax_rate))
    )


@dataclass(frozen=True)
class BridgeInputs:
    cash_and_investments: float
    interest_bearing_debt: float
    preferred_equity: float
    noncontrolling_interests: float
    diluted_shares: float
    nonoperating_range: tuple[float, float, float]
    sources: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class CashFcffInputs:
    ticker: str
    accession: str
    filing_date: str
    form: str
    primary_document: str
    period_end: str
    source_url: str
    ttm_revenue: float
    ttm_operating_cash_flow: float
    ttm_capex: float
    ttm_spectrum_investment: float
    ttm_interest_expense: float
    normalized_tax_rate: float
    reported_cash_fcff: float
    one_time_cash_adjustment: float
    normalized_cash_fcff: float
    annual_cash_fcff: tuple[float, ...]
    annual_revenue: tuple[float, ...]
    bridge: BridgeInputs
    flow_sources: tuple[dict[str, Any], ...]
    specialist_context: dict[str, Any]


def _filing_records(submissions: Mapping[str, Any]) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    count = len(recent.get("accessionNumber", []))
    return [
        {
            key: values[index]
            for key, values in recent.items()
            if isinstance(values, list) and index < len(values)
        }
        for index in range(count)
    ]


def _controlling_filing(
    source_manifest: Mapping[str, Any],
    submissions: Mapping[str, Any],
) -> dict[str, str]:
    rows = source_manifest.get("eligible_filings", [])
    if not rows:
        raise ValueError("source packet has no cutoff-eligible filings")
    row = max(rows, key=lambda item: (item["filed"], item["accession"]))
    if row["filed"] > BATCH_02_VALUATION_DATE:
        raise ValueError("controlling filing is after the valuation cutoff")
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    if row["accession"] not in accessions:
        raise ValueError("controlling filing is absent from submissions")
    index = accessions.index(row["accession"])
    return {
        **row,
        "period_end": recent.get("reportDate", [])[index],
    }


def _normalizer(
    submissions: Mapping[str, Any], companyfacts: Mapping[str, Any]
) -> CompanyFactsNormalizer:
    return CompanyFactsNormalizer(
        dict(companyfacts),
        fiscal_year_end=submissions.get("fiscalYearEnd"),
        as_of_date=BATCH_02_VALUATION_DATE,
        filing_records=_filing_records(submissions),
    )


def _instant(
    companyfacts: Mapping[str, Any],
    *,
    concept: str,
    accession: str,
    period_end: str,
    unit: str = "USD",
) -> tuple[float, dict[str, Any]]:
    rows = (
        companyfacts.get("facts", {})
        .get("us-gaap", {})
        .get(concept, {})
        .get("units", {})
        .get(unit, [])
    )
    matches = [
        row
        for row in rows
        if row.get("accn") == accession
        and row.get("end") == period_end
        and row.get("filed", "") <= BATCH_02_VALUATION_DATE
        and row.get("form") in {"10-K", "10-K/A", "10-Q", "10-Q/A"}
        and isinstance(row.get("val"), (int, float))
        and not isinstance(row.get("val"), bool)
    ]
    values = {float(row["val"]) for row in matches}
    if len(values) != 1:
        raise ValueError(
            f"{concept} requires one same-accession value for {period_end}"
        )
    value = values.pop()
    return value, {
        "source_kind": "companyfacts",
        "concept": f"us-gaap:{concept}",
        "accession": accession,
        "period_end": period_end,
        "unit": unit,
        "value": value,
    }


def _duration(
    companyfacts: Mapping[str, Any],
    *,
    concept: str,
    accession: str,
    period_start: str,
    period_end: str,
    unit: str,
) -> tuple[float, dict[str, Any]]:
    rows = (
        companyfacts.get("facts", {})
        .get("us-gaap", {})
        .get(concept, {})
        .get("units", {})
        .get(unit, [])
    )
    matches = [
        row
        for row in rows
        if row.get("accn") == accession
        and row.get("start") == period_start
        and row.get("end") == period_end
        and row.get("filed", "") <= BATCH_02_VALUATION_DATE
        and isinstance(row.get("val"), (int, float))
        and not isinstance(row.get("val"), bool)
    ]
    values = {float(row["val"]) for row in matches}
    if len(values) != 1:
        raise ValueError(
            f"{concept} requires one same-accession duration value"
        )
    value = values.pop()
    return value, {
        "source_kind": "companyfacts",
        "concept": f"us-gaap:{concept}",
        "accession": accession,
        "period_start": period_start,
        "period_end": period_end,
        "unit": unit,
        "value": value,
    }


def _load_structural(structural_root: Path, ticker: str) -> dict[str, Any]:
    path = Path(structural_root) / ticker / "structural-filing.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("source_accession") is None or not isinstance(
        value.get("facts"), list
    ):
        raise ValueError(f"{ticker}: structural filing is invalid")
    return value


def _structural_value(
    structural: Mapping[str, Any],
    *,
    local_name: str,
    period_end: str,
    member: str | None = None,
) -> tuple[float, dict[str, Any]]:
    matches = []
    for fact in structural["facts"]:
        if (
            fact.get("local_name") != local_name
            or fact.get("period_end") != period_end
            or fact.get("period_start") is not None
            or not isinstance(fact.get("value"), (int, float))
            or isinstance(fact.get("value"), bool)
        ):
            continue
        dimensions = fact.get("dimensions") or []
        if member is not None and not any(
            member in str(dimension_member)
            for _, dimension_member in dimensions
        ):
            continue
        matches.append(fact)
    numeric_decimals = [
        int(fact["decimals"])
        for fact in matches
        if str(fact.get("decimals", "")).lstrip("-").isdigit()
    ]
    if numeric_decimals:
        most_precise = max(numeric_decimals)
        matches = [
            fact
            for fact in matches
            if str(fact.get("decimals", "")).lstrip("-").isdigit()
            and int(fact["decimals"]) == most_precise
        ]
    values = {float(fact["value"]) for fact in matches}
    if len(values) != 1:
        raise ValueError(
            f"{local_name} requires one structural value for {period_end}"
        )
    value = values.pop()
    fact = next(fact for fact in matches if float(fact["value"]) == value)
    return value, {
        "source_kind": "structural_xbrl",
        "concept": fact.get("qname"),
        "accession": structural["source_accession"],
        "period_end": period_end,
        "unit": fact.get("unit"),
        "context_id": fact.get("context_id"),
        "dimensions": fact.get("dimensions"),
        "value": value,
    }


def _structural_duration_value(
    structural: Mapping[str, Any],
    *,
    local_name: str,
    period_start: str,
    period_end: str,
    member: str | None = None,
) -> tuple[float, dict[str, Any]]:
    matches = []
    for fact in structural["facts"]:
        if (
            fact.get("local_name") != local_name
            or fact.get("period_start") != period_start
            or fact.get("period_end") != period_end
            or not isinstance(fact.get("value"), (int, float))
            or isinstance(fact.get("value"), bool)
        ):
            continue
        dimensions = fact.get("dimensions") or []
        if member is not None and not any(
            member in str(dimension_member)
            for _, dimension_member in dimensions
        ):
            continue
        matches.append(fact)
    values = {float(fact["value"]) for fact in matches}
    if len(values) != 1:
        raise ValueError(
            f"{local_name} requires one structural duration value for {period_end}"
        )
    value = values.pop()
    fact = next(fact for fact in matches if float(fact["value"]) == value)
    return value, {
        "source_kind": "structural_xbrl",
        "concept": fact.get("qname"),
        "accession": structural["source_accession"],
        "period_start": period_start,
        "period_end": period_end,
        "unit": fact.get("unit"),
        "context_id": fact.get("context_id"),
        "dimensions": fact.get("dimensions"),
        "value": value,
    }


def _complete_extraction_zero(
    structural: Mapping[str, Any],
    *,
    period_end: str,
    field: str,
    name_fragments: Sequence[str],
) -> tuple[float, dict[str, Any]]:
    possible = [
        fact
        for fact in structural["facts"]
        if fact.get("period_end") == period_end
        and fact.get("period_start") is None
        and any(
            fragment.casefold() in str(fact.get("local_name", "")).casefold()
            for fragment in name_fragments
        )
        and isinstance(fact.get("value"), (int, float))
        and float(fact["value"]) != 0
    ]
    if possible:
        raise ValueError(f"{field} is not source-proven zero")
    return 0.0, {
        "source_kind": "structural_complete_extraction",
        "field": field,
        "accession": structural["source_accession"],
        "period_end": period_end,
        "unit": "USD",
        "value": 0.0,
        "basis": (
            "The fully parsed controlling balance sheet presents no nonzero "
            f"{field} ownership claim."
        ),
    }


def _bridge_inputs(
    *,
    ticker: str,
    companyfacts: Mapping[str, Any],
    structural: Mapping[str, Any],
    accession: str,
    period_end: str,
    diluted_shares: float,
    shares_source: dict[str, Any],
) -> BridgeInputs:
    sources: list[dict[str, Any]] = [shares_source]

    def instant(concept: str) -> float:
        value, source = _instant(
            companyfacts,
            concept=concept,
            accession=accession,
            period_end=period_end,
        )
        sources.append(source)
        return value

    cash = instant("CashAndCashEquivalentsAtCarryingValue")
    adjustment = (0.0, 0.0, 0.0)
    if ticker == "VZ":
        equity_securities = instant("EquitySecuritiesFVNINoncurrent")
        affiliate_investments, affiliate_source = _structural_value(
            structural,
            local_name="InvestmentsInAffiliatesSubsidiariesAssociatesAndJointVentures",
            period_end=period_end,
        )
        sources.append(affiliate_source)
        investments = equity_securities + affiliate_investments
        debt = instant("LongTermDebtCurrent") + instant(
            "LongTermDebtAndCapitalLeaseObligations"
        )
        preferred = instant("PreferredStockValue")
        nci = instant("MinorityInterest")
    elif ticker == "T":
        investments = instant("AvailableForSaleSecuritiesDebtSecurities") + instant(
            "EquityMethodInvestments"
        )
        debt = instant("DebtCurrent") + instant(
            "LongTermDebtAndCapitalLeaseObligations"
        )
        preferred, source = _complete_extraction_zero(
            structural,
            period_end=period_end,
            field="preferred equity",
            name_fragments=("PreferredStockValue", "TemporaryEquity"),
        )
        sources.append(source)
        nci = instant("MinorityInterest") + instant(
            "RedeemableNoncontrollingInterestEquityCarryingAmount"
        )
        held_assets, held_assets_source = _structural_value(
            structural,
            local_name="AssetsOfDisposalGroupIncludingDiscontinuedOperation",
            period_end=period_end,
        )
        held_liabilities, held_liabilities_source = _structural_value(
            structural,
            local_name="LiabilitiesOfDisposalGroupIncludingDiscontinuedOperation",
            period_end=period_end,
        )
        sources.extend((held_assets_source, held_liabilities_source))
        net_held = held_assets - held_liabilities
        if net_held <= 0:
            raise ValueError("T held-for-sale net asset range must be positive")
        adjustment = (0.0, net_held / 2.0, net_held)
    elif ticker == "NFLX":
        investments = instant("ShortTermInvestments")
        debt = instant("ShortTermBorrowings") + instant("LongTermDebtNoncurrent")
        preferred, preferred_source = _complete_extraction_zero(
            structural,
            period_end=period_end,
            field="preferred equity",
            name_fragments=("PreferredStockValue", "TemporaryEquity"),
        )
        nci, nci_source = _complete_extraction_zero(
            structural,
            period_end=period_end,
            field="noncontrolling interests",
            name_fragments=("MinorityInterest", "NoncontrollingInterest"),
        )
        sources.extend((preferred_source, nci_source))
    elif ticker == "TMUS":
        investments = 0.0
        sources.append(
            {
                "source_kind": "structural_complete_extraction",
                "field": "nonoperating marketable securities",
                "accession": accession,
                "period_end": period_end,
                "unit": "USD",
                "value": 0.0,
                "basis": "No nonoperating marketable-security balance is presented in the controlling balance sheet.",
            }
        )
        total_debt, debt_source = _structural_value(
            structural,
            local_name="LongTermDebt",
            period_end=period_end,
            member="TotalDebtMember",
        )
        finance_current = instant("FinanceLeaseLiabilityCurrent")
        finance_noncurrent = instant("FinanceLeaseLiabilityNoncurrent")
        tower_obligations, tower_source = _structural_value(
            structural,
            local_name="SaleLeasebackTransactionTowerObligation",
            period_end=period_end,
        )
        debt = (
            total_debt
            + finance_current
            + finance_noncurrent
            + tower_obligations
        )
        sources.append(debt_source)
        sources.append(tower_source)
        preferred, preferred_source = _complete_extraction_zero(
            structural,
            period_end=period_end,
            field="preferred equity",
            name_fragments=("PreferredStockValue", "TemporaryEquity"),
        )
        nci, nci_source = _complete_extraction_zero(
            structural,
            period_end=period_end,
            field="noncontrolling interests",
            name_fragments=("MinorityInterest", "NoncontrollingInterest"),
        )
        sources.extend((preferred_source, nci_source))
    elif ticker == "META":
        investments = instant("MarketableSecuritiesCurrent")
        debt = instant("DebtInstrumentCarryingAmount")
        preferred, preferred_source = _complete_extraction_zero(
            structural,
            period_end=period_end,
            field="preferred equity",
            name_fragments=("PreferredStockValue", "TemporaryEquity"),
        )
        nci, nci_source = _complete_extraction_zero(
            structural,
            period_end=period_end,
            field="noncontrolling interests",
            name_fragments=("MinorityInterest", "NoncontrollingInterest"),
        )
        sources.extend((preferred_source, nci_source))
    else:
        raise ValueError(f"{ticker}: no approved Batch 02 bridge rule")
    values = (cash, investments, debt, preferred, nci, diluted_shares)
    if any(value < 0 for value in values) or diluted_shares <= 0:
        raise ValueError(f"{ticker}: bridge values must be nonnegative")
    return BridgeInputs(
        cash_and_investments=cash + investments,
        interest_bearing_debt=debt,
        preferred_equity=preferred,
        noncontrolling_interests=nci,
        diluted_shares=diluted_shares,
        nonoperating_range=adjustment,
        sources=tuple(sources),
    )


def _annual_cash_fcff(
    normalizer: CompanyFactsNormalizer,
    *,
    spectrum_required: bool,
    spectrum_floor: float,
    spectrum_source: Mapping[str, Any],
    scope_adjustment: float,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[dict[str, Any], ...]]:
    cash_rows: list[float] = []
    revenue_rows: list[float] = []
    source_rows: list[dict[str, Any]] = []
    for operating_cash in normalizer.annual_series("operating_cash_flow", 5):
        capex = normalizer.annual_at_end(
            "capital_expenditures", operating_cash.end
        )
        interest = normalizer.annual_at_end("interest_expense", operating_cash.end)
        pretax = normalizer.annual_at_end("pretax_income", operating_cash.end)
        tax = normalizer.annual_at_end("income_tax", operating_cash.end)
        revenue = normalizer.annual_at_end("revenue", operating_cash.end)
        if capex is None or interest is None or revenue is None:
            continue
        tax_rate = (
            max(0.0, min(0.30, tax.value / pretax.value))
            if pretax is not None
            and tax is not None
            and pretax.value > 0
            else 0.21
        )
        spectrum = (
            normalizer.annual_at_end(
                "intangible_asset_purchases", operating_cash.end
            )
            if spectrum_required
            else None
        )
        spectrum_value = (
            spectrum.value
            if spectrum is not None
            else spectrum_floor
            if spectrum_required
            else 0.0
        )
        cash_fcff = cash_fcff_from_reported(
            operating_cash_flow=operating_cash.value,
            capital_expenditures=capex.value,
            spectrum_investment=spectrum_value,
            interest_expense=abs(interest.value),
            tax_rate=tax_rate,
        ) - scope_adjustment
        if cash_fcff > 0 and revenue.value > 0:
            cash_rows.append(cash_fcff)
            revenue_rows.append(revenue.value)
            source_rows.append(
                {
                    "period_end": operating_cash.end,
                    "operating_cash_flow": operating_cash.as_dict(),
                    "capital_expenditures": capex.as_dict(),
                    "spectrum_investment": (
                        spectrum.as_dict()
                        if spectrum is not None
                        else {
                            "state": "not_applicable",
                            "value": 0.0,
                        }
                        if not spectrum_required
                        else {
                            **dict(spectrum_source),
                            "value": spectrum_floor,
                            "reported_vs_estimated": "estimated",
                            "basis": "Current source-backed spectrum cash is carried as a conservative annual reinvestment floor.",
                        }
                    ),
                    "scope_adjustment": scope_adjustment,
                    "interest_expense": interest.as_dict(),
                    "pretax_income": pretax.as_dict() if pretax else None,
                    "income_tax": tax.as_dict() if tax else None,
                    "revenue": revenue.as_dict(),
                    "cash_fcff": cash_fcff,
                }
            )
    return tuple(cash_rows), tuple(revenue_rows), tuple(source_rows)


def _normalized_tax_rate(
    normalizer: CompanyFactsNormalizer,
) -> tuple[float, tuple[dict[str, Any], ...]]:
    rates = []
    sources = []
    for pretax in normalizer.annual_series("pretax_income", 5):
        tax = normalizer.annual_at_end("income_tax", pretax.end)
        if tax is not None and pretax.value > 0:
            rates.append(max(0.0, min(0.30, tax.value / pretax.value)))
            sources.append(
                {
                    "period_end": pretax.end,
                    "pretax_income": pretax.as_dict(),
                    "income_tax": tax.as_dict(),
                    "effective_tax_rate": rates[-1],
                }
            )
    if len(rates) < 3:
        raise ValueError("at least three annual effective-tax observations are required")
    return float(median(rates)), tuple(sources)


def load_cash_fcff_inputs(
    *,
    ticker: str,
    source_root: Path,
    structural_root: Path,
) -> CashFcffInputs:
    """Load one approved candidate from immutable Companyfacts and Arelle packets."""

    if ticker not in NUMERIC_CANDIDATES:
        raise ValueError(f"{ticker}: no approved numeric-candidate input route")
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    companyfacts = json.loads((packet / "companyfacts.json").read_text())
    source_manifest = json.loads((packet / "source-manifest.json").read_text())
    filing = _controlling_filing(source_manifest, submissions)
    accession = filing["accession"]
    period_end = filing["period_end"]
    structural = _load_structural(structural_root, ticker)
    if structural["source_accession"] != accession:
        raise ValueError(f"{ticker}: structural accession mismatch")

    normalizer = _normalizer(submissions, companyfacts)
    flows = {
        field: normalizer.ttm_flow(field)
        for field in (
            "revenue",
            "pretax_income",
            "income_tax",
            "capital_expenditures",
            "operating_cash_flow",
            "interest_expense",
        )
    }
    if any(flow["period_end"] != period_end for flow in flows.values()):
        raise ValueError(f"{ticker}: TTM flow periods do not match controlling filing")
    tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    operating_cash = float(flows["operating_cash_flow"]["value"])
    capex = float(flows["capital_expenditures"]["value"])
    interest = abs(float(flows["interest_expense"]["value"]))
    spectrum_required = ticker in {"VZ", "T", "TMUS"}
    if ticker in {"VZ", "TMUS"}:
        spectrum_flow = normalizer.ttm_flow("intangible_asset_purchases")
        if spectrum_flow["period_end"] != period_end:
            raise ValueError(f"{ticker}: spectrum TTM does not match controlling period")
        spectrum_investment = float(spectrum_flow["value"])
        spectrum_source = {
            "field": "spectrum_investment",
            "value": spectrum_investment,
            "period_end": period_end,
            "source": spectrum_flow,
        }
    elif ticker == "T":
        spectrum_investment, spectrum_source = _structural_duration_value(
            structural,
            local_name="PaymentsToAcquireBusinessesNetOfCashAcquired",
            period_start="2026-01-01",
            period_end=period_end,
            member="LicenseMember",
        )
    else:
        spectrum_investment = 0.0
        spectrum_source = {
            "state": "not_applicable",
            "value": 0.0,
            "basis": "The content model has no spectrum-license investment.",
        }
    scope_adjustment_range = (0.0, 0.0, 0.0)
    scope_source: dict[str, Any] | None = None
    if ticker == "T":
        discontinued_capex, scope_source = _structural_value(
            structural,
            local_name="DisposalGroupIncludingDiscontinuedOperationPropertyPlantAndEquipmentNoncurrent",
            period_end=period_end,
            member="OtherCapitalizedPropertyPlantAndEquipmentMember",
        )
        scope_adjustment_range = (
            0.0,
            discontinued_capex / 2.0,
            discontinued_capex,
        )
    reported_cash_fcff = cash_fcff_from_reported(
        operating_cash_flow=operating_cash,
        capital_expenditures=capex,
        spectrum_investment=spectrum_investment,
        interest_expense=interest,
        tax_rate=tax_rate,
    )
    one_time_adjustment = 2_800_000_000.0 if ticker == "NFLX" else 0.0
    normalized_cash_fcff = (
        reported_cash_fcff
        - one_time_adjustment
        - scope_adjustment_range[1]
    )
    if normalized_cash_fcff <= 0:
        raise ValueError(f"{ticker}: normalized cash FCFF must be positive")

    diluted_shares, shares_source = _duration(
        companyfacts,
        concept="WeightedAverageNumberOfDilutedSharesOutstanding",
        accession=accession,
        period_start="2026-01-01",
        period_end=period_end,
        unit="shares",
    )
    bridge = _bridge_inputs(
        ticker=ticker,
        companyfacts=companyfacts,
        structural=structural,
        accession=accession,
        period_end=period_end,
        diluted_shares=diluted_shares,
        shares_source=shares_source,
    )
    annual_cash, annual_revenue, annual_sources = _annual_cash_fcff(
        normalizer,
        spectrum_required=spectrum_required,
        spectrum_floor=spectrum_investment,
        spectrum_source=spectrum_source,
        scope_adjustment=scope_adjustment_range[1],
    )
    if len(annual_cash) < 3 or len(annual_revenue) < 3:
        raise ValueError(f"{ticker}: fewer than three comparable annual cash states")
    source_url = (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{int(source_manifest['issuer']['cik'])}/"
        f"{accession.replace('-', '')}/{filing['primary_document']}"
    )
    current_sources = tuple(
        {
            "field": field,
            "value": flow["value"],
            "period_end": flow["period_end"],
            "source": flow,
        }
        for field, flow in flows.items()
    )
    specialist_context: dict[str, Any] = {
        "scope_adjustment_range": scope_adjustment_range,
        "scope_adjustment_source": scope_source,
    }
    if ticker == "NFLX":
        purchase_current, purchase_current_source = _structural_value(
            structural,
            local_name="PurchaseObligation",
            period_end=period_end,
        )
        purchase_prior, purchase_prior_source = _structural_value(
            structural,
            local_name="PurchaseObligation",
            period_end="2025-12-31",
        )
        unrecorded, unrecorded_source = _structural_value(
            structural,
            local_name="UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount",
            period_end=period_end,
        )
        next_twelve, next_twelve_source = _structural_value(
            structural,
            local_name="PurchaseObligationFutureMinimumPaymentsRemainderOfFiscalYear",
            period_end=period_end,
        )
        additions_current, additions_current_source = _structural_duration_value(
            structural,
            local_name="AdditionstoStreamingContentAssets",
            period_start="2026-01-01",
            period_end=period_end,
        )
        additions_prior, additions_prior_source = _structural_duration_value(
            structural,
            local_name="AdditionstoStreamingContentAssets",
            period_start="2025-01-01",
            period_end="2025-06-30",
        )
        specialist_context["content_commitments"] = {
            "total_current": purchase_current,
            "total_prior": purchase_prior,
            "unrecorded_current": unrecorded,
            "next_twelve_months": next_twelve,
            "h1_additions_current": additions_current,
            "h1_additions_prior": additions_prior,
            "h1_additions_increase": additions_current - additions_prior,
            "sources": (
                purchase_current_source,
                purchase_prior_source,
                unrecorded_source,
                next_twelve_source,
                additions_current_source,
                additions_prior_source,
            ),
        }
    flow_sources = (
        *current_sources,
        spectrum_source,
        {"annual_cash_states": annual_sources},
        {"normalized_tax_sources": tax_sources},
    )
    return CashFcffInputs(
        ticker=ticker,
        accession=accession,
        filing_date=filing["filed"],
        form=filing["form"],
        primary_document=filing["primary_document"],
        period_end=period_end,
        source_url=source_url,
        ttm_revenue=float(flows["revenue"]["value"]),
        ttm_operating_cash_flow=operating_cash,
        ttm_capex=capex,
        ttm_spectrum_investment=spectrum_investment,
        ttm_interest_expense=interest,
        normalized_tax_rate=tax_rate,
        reported_cash_fcff=reported_cash_fcff,
        one_time_cash_adjustment=one_time_adjustment,
        normalized_cash_fcff=normalized_cash_fcff,
        annual_cash_fcff=annual_cash,
        annual_revenue=annual_revenue,
        bridge=bridge,
        flow_sources=flow_sources,
        specialist_context=specialist_context,
    )
