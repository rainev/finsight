"""Source-bounded practical operating valuations for controlled Batch 03."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
from statistics import median
from typing import Any, Mapping

from .batch_02_practical_inputs import (
    _annual_cash_fcff,
    _normalizer,
    _normalized_tax_rate,
    cash_fcff_from_reported,
)
from .batch_03 import BATCH_03_MANIFEST, BATCH_03_VALUATION_DATE
from .practical_models import (
    EnterpriseCashFlowState,
    enterprise_cash_flow_dcf,
    practical_cash_fcff_range,
)
from .reliability import relative_movement


BATCH_03_POLICY_VERSION = "BATCH-03-PRACTICAL-CASH-FCFF-1.0"
BATCH_03_NUMERIC_TICKERS = ("NWSA", "TTD", "DIS")

WITHHELD_DECISIONS: dict[str, dict[str, Any]] = {
    "LYV": {
        "model": "live_events_operating_fcff",
        "archetype": "live_events_ticketing",
        "reason": "Live-events seasonality, event-related cash and deferred revenue, redeemable NCI, leases, and convertible dilution require a specialist route before the current positive cash flow can support publication.",
        "hard_blockers": ["MODEL_UNSUPPORTED", "CLAIMS_UNBOUNDED"],
    },
    "ECHO": {
        "model": "deconsolidation_adjusted_telecom_fcff",
        "archetype": "telecom_spectrum_transition",
        "reason": "The DISH/EchoStar deconsolidation and disposal state, spectrum economics, debt, and NCI cannot be separated into a source-bounded continuing-company range.",
        "hard_blockers": ["MAJOR_EVENT_UNBOUNDED", "CLAIMS_UNBOUNDED"],
    },
    "TKO": {
        "model": "sports_rights_operating_fcff",
        "archetype": "sports_live_entertainment",
        "reason": "The controlling evidence lacks a complete capital-spending and rights-commitment cash series, while material NCI and share contexts remain model-load-bearing.",
        "hard_blockers": ["MODEL_UNSUPPORTED", "CLAIMS_UNBOUNDED"],
    },
    "GOOGL": {
        "model": "ai_commitment_adjusted_cash_fcff",
        "archetype": "internet_cloud_ai_infrastructure",
        "reason": "Current preferred and NCI claims are repaired, but the controlling filing reports $707bn of long-term purchase commitments without a mutually exclusive timing and cash-conversion schedule. The source-bounded cash range does not cover that exposure.",
        "hard_blockers": ["CLAIMS_UNBOUNDED", "MODEL_UNSUPPORTED"],
    },
    "APP": {
        "model": "post_disposal_operating_fcff",
        "archetype": "advertising_technology",
        "reason": "The controlling 2026 filing has no current capex fact; combining 2026 operating cash flow with a 2024 capex observation would violate the period gate.",
        "hard_blockers": ["PERIOD_INVALID", "MODEL_UNSUPPORTED"],
    },
    "FOXA": {
        "model": "broadcasting_rights_operating_fcff",
        "archetype": "broadcasting_media_rights",
        "reason": "The controlling filing reports $6.461bn of contractual obligations plus $715m of other commitments due within twelve months, which the current bear cash state cannot cover without a specialist rights schedule.",
        "hard_blockers": ["CLAIMS_UNBOUNDED", "MODEL_UNSUPPORTED"],
    },
    "PSKY": {
        "model": "successor_media_fcff",
        "archetype": "successor_media",
        "reason": "Paramount Skydance has a predecessor-to-successor history break and material share, debt, and ownership conversion. A comparable source-bounded terminal state is not yet available.",
        "hard_blockers": ["MAJOR_EVENT_UNBOUNDED", "MODEL_UNSUPPORTED"],
    },
}

_CONFIG = {
    "NWSA": {"wacc": 0.085, "growth": "mature", "confidence": 0.80, "diluted_shares": 558_400_000.0},
    "TTD": {"wacc": 0.091, "growth": "growth", "confidence": 0.90, "diluted_shares": 473_397_000.0},
    "DIS": {"wacc": 0.085, "growth": "mature", "confidence": 0.75, "diluted_shares": 1_769_000_000.0},
}


def _controlling(
    source_manifest: Mapping[str, Any], submissions: Mapping[str, Any]
) -> dict[str, str]:
    filing = max(
        source_manifest["eligible_filings"],
        key=lambda row: (row["filed"], row["accession"]),
    )
    accessions = submissions["filings"]["recent"]["accessionNumber"]
    index = accessions.index(filing["accession"])
    return {
        **filing,
        "period_end": submissions["filings"]["recent"]["reportDate"][index],
    }


def _fact(
    structural: Mapping[str, Any],
    *,
    period_end: str,
    local_name: str,
    expected: float,
    unit: str = "USD",
) -> dict[str, Any]:
    rows = [
        row for row in structural["facts"]
        if row.get("period_start") is None
        and row.get("period_end") == period_end
        and row.get("local_name") == local_name
        and not row.get("dimensions")
        and row.get("unit") in {unit, f"xbrli:{unit}"}
        and isinstance(row.get("value"), (int, float))
        and not isinstance(row.get("value"), bool)
    ]
    values = {float(row["value"]) for row in rows}
    if expected not in values:
        raise ValueError(
            f"{local_name}: expected {expected} in {sorted(values)} for {period_end}"
        )
    row = next(item for item in rows if float(item["value"]) == expected)
    return {
        "source_kind": "structural_xbrl",
        "accession": structural["source_accession"],
        "period_end": period_end,
        "concept": row.get("qname"),
        "unit": unit,
        "value": expected,
        "reported_vs_estimated": "reported",
    }


def _zero(
    structural: Mapping[str, Any],
    *,
    period_end: str,
    field: str,
    local_names: tuple[str, ...],
) -> dict[str, Any]:
    nonzero = [
        row for row in structural["facts"]
        if row.get("period_start") is None
        and row.get("period_end") == period_end
        and row.get("local_name") in local_names
        and not row.get("dimensions")
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) != 0
    ]
    if nonzero:
        raise ValueError(f"{field}: controlling filing contains a nonzero claim")
    return {
        "source_kind": "structural_complete_extraction",
        "accession": structural["source_accession"],
        "period_end": period_end,
        "field": field,
        "unit": "USD",
        "value": 0.0,
        "reported_vs_estimated": "absence_proven_zero",
        "basis": "No nonzero matching ownership or financing claim is presented in the fully parsed controlling filing.",
    }


def _diluted_share_fact(
    structural: Mapping[str, Any], *, period_end: str, expected: float
) -> dict[str, Any]:
    rows = [
        row for row in structural["facts"]
        if row.get("period_end") == period_end
        and row.get("local_name") == "WeightedAverageNumberOfDilutedSharesOutstanding"
        and not row.get("dimensions")
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) == expected
    ]
    if not rows:
        raise ValueError(f"diluted shares {expected} are absent for {period_end}")
    row = max(rows, key=lambda item: item.get("period_start") or "")
    return {
        "source_kind": "structural_xbrl",
        "accession": structural["source_accession"],
        "period_start": row.get("period_start"),
        "period_end": period_end,
        "concept": row.get("qname"),
        "unit": "shares",
        "value": expected,
        "reported_vs_estimated": "reported",
    }


def _bridge(
    ticker: str,
    structural: Mapping[str, Any],
    period_end: str,
    diluted_shares: float,
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []

    def reported(name: str, value: float, unit: str = "USD") -> float:
        sources.append(
            _fact(
                structural,
                period_end=period_end,
                local_name=name,
                expected=value,
                unit=unit,
            )
        )
        return value

    if ticker == "NWSA":
        cash = reported("CashAndCashEquivalentsAtCarryingValue", 2_095_000_000.0)
        debt = reported("LongTermDebtNoncurrent", 1_989_000_000.0)
        nci = reported("MinorityInterest", 710_000_000.0)
        preferred = 0.0
        sources.append(_zero(structural, period_end=period_end, field="preferred_equity", local_names=("PreferredStockValue", "ConvertiblePreferredStockNonredeemableOrRedeemableIssuerOptionValue", "TemporaryEquityCarryingAmount")))
        shares = (diluted_shares * 1.05, diluted_shares * 1.025, diluted_shares)
    elif ticker == "GOOGL":
        cash = reported("CashCashEquivalentsAndShortTermInvestments", 242_474_000_000.0)
        debt = (
            reported("LongTermDebtCurrent", 1_999_000_000.0)
            + reported("LongTermDebtNoncurrent", 98_165_000_000.0)
            + reported("FinanceLeaseLiability", 2_590_000_000.0)
        )
        preferred = reported("ConvertiblePreferredStockNonredeemableOrRedeemableIssuerOptionValue", 18_023_000_000.0)
        nci = (
            reported("NoncontrollingInterestInVariableInterestEntity", 7_100_000_000.0)
            + reported("RedeemableNoncontrollingInterestInVariableInterestEntity", 824_000_000.0)
        )
        shares = (12_400_000_000.0, 12_300_000_000.0, diluted_shares)
    elif ticker == "TTD":
        cash = reported("CashCashEquivalentsAndShortTermInvestments", 1_485_333_000.0)
        debt = preferred = nci = 0.0
        sources.extend((
            _zero(structural, period_end=period_end, field="interest_bearing_debt", local_names=("LongTermDebtCurrent", "LongTermDebtNoncurrent", "ShortTermBorrowings", "CommercialPaper")),
            _zero(structural, period_end=period_end, field="noncontrolling_interests", local_names=("MinorityInterest", "NoncontrollingInterestInConsolidatedEntity", "RedeemableNoncontrollingInterestEquityCarryingAmount")),
        ))
        reported("PreferredStockValue", 0.0)
        shares = (diluted_shares * 1.05, diluted_shares * 1.025, diluted_shares)
    elif ticker == "DIS":
        cash = reported("CashAndCashEquivalentsAtCarryingValue", 5_185_000_000.0)
        excluded_investment = reported("LongTermInvestments", 7_627_000_000.0)
        debt = (
            reported("LongTermDebtCurrent", 8_627_000_000.0)
            + reported("LongTermDebtNoncurrent", 37_414_000_000.0)
        )
        preferred = reported("PreferredStockValue", 0.0)
        nci = reported("MinorityInterest", 6_810_000_000.0)
        shares = (diluted_shares * 1.05, diluted_shares * 1.025, diluted_shares)
    elif ticker == "APP":
        cash = reported("CashAndCashEquivalentsAtCarryingValue", 3_053_306_000.0)
        debt = reported("LongTermDebtNoncurrent", 3_515_072_000.0)
        preferred = reported("PreferredStockValue", 0.0)
        nci = 0.0
        sources.extend((
            _zero(structural, period_end=period_end, field="current_debt", local_names=("LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings", "CommercialPaper")),
            _zero(structural, period_end=period_end, field="noncontrolling_interests", local_names=("MinorityInterest", "NoncontrollingInterestInConsolidatedEntity", "RedeemableNoncontrollingInterestEquityCarryingAmount")),
            _zero(structural, period_end=period_end, field="nonoperating_securities", local_names=("MarketableSecuritiesCurrent", "MarketableSecuritiesNoncurrent", "ShortTermInvestments")),
        ))
        shares = (diluted_shares * 1.05, diluted_shares * 1.025, diluted_shares)
    elif ticker == "FOXA":
        cash = reported("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", 4_205_000_000.0)
        debt = reported("DebtInstrumentCarryingAmount", 6_650_000_000.0)
        preferred = 0.0
        sources.append(_zero(structural, period_end=period_end, field="preferred_equity", local_names=("PreferredStockValue", "ConvertiblePreferredStockNonredeemableOrRedeemableIssuerOptionValue", "TemporaryEquityCarryingAmount")))
        nci = (
            reported("MinorityInterest", 100_000_000.0)
            + reported("RedeemableNoncontrollingInterestEquityCarryingAmount", 86_000_000.0)
        )
        shares = (diluted_shares * 1.05, diluted_shares * 1.025, diluted_shares)
    else:
        raise ValueError(f"{ticker}: no Batch 03 source-bounded bridge")
    result = {
        "cash_and_investments": (cash, cash, cash),
        "debt": debt,
        "preferred_equity": preferred,
        "noncontrolling_interests": nci,
        "shares": shares,
        "sources": sources,
    }
    if ticker == "DIS":
        result["excluded_nonliquid_or_unclassified_investments"] = excluded_investment
    return result


def _no_material_commitment_schedule(
    structural: Mapping[str, Any], *, period_end: str
) -> dict[str, Any]:
    names = {
        "ContractualObligation",
        "ContractualObligationDueInNextTwelveMonths",
        "OtherCommitment",
        "OtherCommitmentDueInNextTwelveMonths",
        "PurchaseObligation",
        "PaymentsForPurchaseObligations",
    }


def _ttd_table_commitments(
    structural_root: Path, *, accession: str, period_end: str
) -> dict[str, Any]:
    package_manifest_path = Path(structural_root) / "TTD" / "package-manifest.json"
    package_manifest = json.loads(package_manifest_path.read_text())
    if package_manifest.get("accession") != accession:
        raise ValueError("TTD commitment table package accession mismatch")
    primary = next(
        (
            row for row in package_manifest.get("files", [])
            if row.get("local_path") == "ttd-20260630.htm"
        ),
        None,
    )
    expected_sha = "deedc998e97ad90b544a2659cff1e2991bbb3c48c62f80c267b1cd453a35eec5"
    if not isinstance(primary, dict) or primary.get("sha256") != expected_sha:
        raise ValueError("TTD controlling HTML hash mismatch")
    return {
        "source_kind": "filing_table_manual_review",
        "accession": accession,
        "period_end": period_end,
        "form": "10-Q",
        "filed_date": "2026-08-06",
        "table": "Note 11 - Contractual Obligations",
        "primary_document": "ttd-20260630.htm",
        "primary_document_sha256": expected_sha,
        "source_url": primary["logical_url"],
        "operating_lease_commitments": 762_231_000.0,
        "other_contractual_commitments": 176_893_000.0,
        "total_commitments": 939_124_000.0,
        "remainder_2026": 97_937_000.0,
        "year_2027_and_thereafter": 841_187_000.0,
        "reported_vs_estimated": "reported_table",
    }
    rows = [
        row for row in structural["facts"]
        if row.get("period_end") == period_end
        and row.get("local_name") in names
        and not row.get("dimensions")
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) != 0
    ]
    if rows:
        raise ValueError("material commitment schedule is present and must be modeled")
    return {
        "source_kind": "structural_complete_extraction",
        "accession": structural["source_accession"],
        "period_end": period_end,
        "status": "no_material_commitment_schedule_found",
        "reported_vs_estimated": "absence_proven",
    }


def build_batch_03_practical_result(
    *, ticker: str, source_root: Path, structural_root: Path
) -> dict[str, Any]:
    if ticker not in BATCH_03_NUMERIC_TICKERS:
        raise ValueError(f"{ticker}: not approved for the Batch 03 initial numeric set")
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    companyfacts = json.loads((packet / "companyfacts.json").read_text())
    source_manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    filing = _controlling(source_manifest, submissions)
    if structural.get("source_accession") != filing["accession"]:
        raise ValueError(f"{ticker}: structural accession mismatch")
    normalizer = _normalizer(submissions, companyfacts)
    flows = {
        field: normalizer.ttm_flow(field)
        for field in (
            "revenue", "operating_cash_flow", "capital_expenditures",
            "interest_expense",
        )
    }
    tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    current_cash = cash_fcff_from_reported(
        operating_cash_flow=float(flows["operating_cash_flow"]["value"]),
        capital_expenditures=float(flows["capital_expenditures"]["value"]),
        spectrum_investment=0.0,
        interest_expense=abs(float(flows["interest_expense"]["value"])),
        tax_rate=tax_rate,
    )
    annual_cash, annual_revenue, annual_sources = _annual_cash_fcff(
        normalizer,
        spectrum_required=False,
        spectrum_floor=0.0,
        spectrum_source={},
        scope_adjustment=0.0,
    )
    if current_cash <= 0 or len(annual_cash) < 3 or len(annual_revenue) < 3:
        raise ValueError(f"{ticker}: insufficient positive comparable cash history")
    recent_cash = tuple(annual_cash[-2:])
    cash_range = (
        min((current_cash, *recent_cash)) * 0.85,
        float(median((current_cash, *recent_cash))),
        max((current_cash, *recent_cash)) * 1.15,
    )
    recent_revenue = tuple(annual_revenue[-3:])
    cagr = (recent_revenue[-1] / recent_revenue[0]) ** 0.5 - 1
    config = _CONFIG[ticker]
    growth_base = (
        min(0.12, max(0.02, cagr))
        if config["growth"] == "growth"
        else min(0.05, max(-0.02, cagr))
    )
    growth = (growth_base - 0.02, growth_base, growth_base + 0.015)
    diluted_shares = float(config["diluted_shares"])
    bridge = _bridge(ticker, structural, filing["period_end"], diluted_shares)
    bridge["sources"].append(
        _diluted_share_fact(
            structural,
            period_end=filing["period_end"],
            expected=diluted_shares,
        )
    )
    forward_commitment_evidence: dict[str, Any]
    if ticker == "NWSA":
        next_twelve = _fact(
            structural,
            period_end=filing["period_end"],
            local_name="ContractualObligationDueInNextTwelveMonths",
            expected=573_000_000.0,
        )
        stressed_low = max(1.0, cash_range[1] - next_twelve["value"])
        cash_range = (min(cash_range[0], stressed_low), cash_range[1], cash_range[2])
        excluded_investment = _fact(
            structural,
            period_end=filing["period_end"],
            local_name="LongTermInvestments",
            expected=1_002_000_000.0,
        )
        forward_commitment_evidence = {
            "total_contractual_obligations": _fact(
                structural,
                period_end=filing["period_end"],
                local_name="ContractualObligation",
                expected=4_732_000_000.0,
            ),
            "next_twelve_months": next_twelve,
            "bear_cash_reduction": cash_range[1] - cash_range[0],
            "bear_covers_next_twelve_months": cash_range[1] - cash_range[0] >= next_twelve["value"],
            "excluded_nonliquid_long_term_investment": excluded_investment,
        }
    elif ticker == "DIS":
        content_current = _fact(
            structural,
            period_end=filing["period_end"],
            local_name="ProducedAndLicensedContentTotal",
            expected=32_127_000_000.0,
        )
        content_prior = _fact(
            structural,
            period_end="2025-09-27",
            local_name="ProducedAndLicensedContentTotal",
            expected=33_390_000_000.0,
        )
        forward_commitment_evidence = {
            "content_balance_current": content_current,
            "content_balance_prior": content_prior,
            "content_balance_change": content_current["value"] - content_prior["value"],
            "cash_flow_already_includes_content_spending": True,
            "remaining_performance_obligation_is_customer_revenue_not_cash_debt": _fact(
                structural,
                period_end=filing["period_end"],
                local_name="RevenueRemainingPerformanceObligation",
                expected=16_000_000_000.0,
            ),
            "excluded_nonliquid_or_unclassified_investments": bridge[
                "excluded_nonliquid_or_unclassified_investments"
            ],
        }
    elif ticker == "TTD":
        table = _ttd_table_commitments(
            Path(structural_root),
            accession=filing["accession"],
            period_end=filing["period_end"],
        )
        governed_first_year_stress = (
            table["remainder_2026"]
            + table["year_2027_and_thereafter"] / 5.0
        )
        stressed_low = max(1.0, cash_range[1] - governed_first_year_stress)
        cash_range = (min(cash_range[0], stressed_low), cash_range[1], cash_range[2])
        forward_commitment_evidence = {
            **table,
            "governed_first_year_stress": governed_first_year_stress,
            "stress_policy": "remainder of 2026 plus one-fifth of the 2027-and-thereafter balance",
            "bear_cash_reduction": cash_range[1] - cash_range[0],
            "bear_covers_governed_first_year_stress": cash_range[1] - cash_range[0] >= governed_first_year_stress,
            "commitments_are_operating_cash_items_not_bridge_debt": True,
        }
    else:
        forward_commitment_evidence = _no_material_commitment_schedule(
            structural, period_end=filing["period_end"]
        )
    states = {}
    for index, name in enumerate(("bear", "base", "bull")):
        states[name] = EnterpriseCashFlowState(
            cash_fcff=cash_range[index],
            initial_growth=growth[index],
            terminal_growth=(0.015, 0.02, 0.025)[index],
            wacc=float(config["wacc"]) + (0.01, 0.0, -0.005)[index],
            cash_and_investments=bridge["cash_and_investments"][index],
            interest_bearing_debt=bridge["debt"],
            preferred_equity=bridge["preferred_equity"],
            noncontrolling_interests=bridge["noncontrolling_interests"],
            diluted_shares=bridge["shares"][index],
        )
    value_range, scenarios = practical_cash_fcff_range(states)
    movement = relative_movement(
        low=value_range.low, base=value_range.base, high=value_range.high
    )
    base_state = states["base"]
    sensitivities = []
    for delta in (-0.01, 0.0, 0.01):
        model = enterprise_cash_flow_dcf(replace(base_state, wacc=base_state.wacc + delta))
        sensitivities.append({
            "field": "wacc",
            "delta": delta,
            "intrinsic_value_per_share": model["intrinsic_value_per_share"],
            "publication_state": "review_required",
        })
    issuer = next(row for row in BATCH_03_MANIFEST if row.ticker == ticker)
    reason_codes = ["SPECIALIST_MODEL_UNCERTAINTY"]
    if ticker in {"NWSA", "DIS", "FOXA"}:
        reason_codes.insert(0, "CONSOLIDATED_MODEL_FALLBACK")
    if ticker in {"GOOGL", "APP"}:
        reason_codes.insert(0, "CAPEX_CASH_CONVERSION_SENSITIVITY")
    source_url = (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{int(issuer.cik)}/{filing['accession'].replace('-', '')}/"
        f"{filing['primary_document']}"
    )
    warning = (
        "Low-reliability source-bounded estimate. Business-model, cash-conversion, "
        "and scenario uncertainty may materially affect the range."
    )
    return {
        "ticker": ticker,
        "model_version": BATCH_03_POLICY_VERSION,
        "model_selection_reason": (
            "Practical consolidated operating cash-FCFF uses current and recent annual "
            "issuer cash conversion with a fully reconciled current claims bridge."
        ),
        "source_financial_statement": {
            "form": filing["form"],
            "period_end": filing["period_end"],
            "filed_date": filing["filed"],
            "accession": filing["accession"],
            "url": source_url,
            "note": "Controlling cutoff-eligible SEC filing anchors the Batch 03 source-bounded estimate.",
        },
        "scenario_range": {
            **value_range.as_dict(),
            "label": "assumption range, not a statistical confidence interval",
        },
        "models": {"fcff_dcf": scenarios["base"]},
        "scenarios": {
            name: {"fcff_dcf": model} for name, model in scenarios.items()
        },
        "sensitivities": sensitivities,
        "public_assumptions": {
            "forecast_policy_version": BATCH_03_POLICY_VERSION,
            "forecast_years": 8,
            "forecast_mode": "company_history_cash_conversion",
            "initial_revenue_growth": growth_base,
            "terminal_growth": 0.02,
            "policy_wacc": float(config["wacc"]),
            "diluted_shares": bridge["shares"][1],
            "diluted_shares_low": bridge["shares"][2],
            "diluted_shares_high": bridge["shares"][0],
            "source_policy": "SEC facts filed on or before 2026-08-14; no stock price or analyst target.",
        },
        "forecast_quality": {
            "policy_version": BATCH_03_POLICY_VERSION,
            "status": "review_required",
            "errors": [],
            "warnings": [warning],
            "checks": {},
        },
        "review": {
            "publication_state": "review_required",
            "confidence_grade": "conditional_low",
            "errors": [],
            "warnings": [warning],
            "price_dependent_inputs_used": False,
            "prohibited_output_check": {
                "buy_hold_sell": False,
                "current_price": False,
                "trading_multiples": False,
                "upside_downside": False,
            },
        },
        "reliability": {
            "label": "Low",
            "accounting_label": "High",
            "scenario_label": "Low",
            "model_cap": "Low",
            "source_cap": "Low",
            "accounting_impact_ratio": 0.0,
            "scenario_movement_ratio": movement,
            "reasons": reason_codes,
        },
        "private_inputs": {
            "current_cash_fcff": current_cash,
            "cash_fcff_range": cash_range,
            "annual_cash_fcff": annual_cash,
            "annual_revenue": annual_revenue,
            "growth_range": growth,
            "tax_rate": tax_rate,
            "bridge": bridge,
            "scenario_states": {
                name: asdict(state) for name, state in states.items()
            },
            "flow_sources": flows,
            "tax_sources": tax_sources,
            "annual_sources": annual_sources,
            "forward_commitment_evidence": forward_commitment_evidence,
        },
    }
