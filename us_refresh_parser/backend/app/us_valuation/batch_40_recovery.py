"""One controlled recovery attempt for Batch 40 COIN."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import hashlib
import json
from typing import Any

from app.valuation.bank import residual_income_valuation

from .baseline import AvailabilityType, BaselineValuation
from .batch_35_history import _instant
from .batch_40 import BATCH_40_TICKERS
from .batch_40_history import build_batch_40_history_result
from .history import CompanyHistoryProfile, HISTORY_POLICY_VERSION, HistoryObservation, summarize_history_metric


BATCH_40_RECOVERY_VERSION = "BATCH-40-COIN-RECOVERY-1.0"
PERIOD = "2026-06-30"
VALUATION_DATE = "2026-08-14"
RECOVERED_PASS_TICKERS = frozenset()
RECOVERED_CONDITIONAL_TICKERS = frozenset(set(BATCH_40_TICKERS) - {"COIN"})
RECOVERED_WITHHELD_TICKERS = frozenset({"COIN"})


def _recovery_source(root: Path) -> dict[str, Any]:
    receipt_path = Path(root) / "COIN/recovery-source-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    document = receipt["document"]
    path = Path(root) / "COIN" / receipt["accession"] / document["filename"]
    if not str(document["path"]).endswith(str(Path("COIN") / receipt["accession"] / document["filename"])):
        raise ValueError("COIN recovery exhibit path mismatch")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != document["sha256"]:
        raise ValueError("COIN recovery exhibit hash mismatch")
    text = raw.decode(errors="ignore")
    required = (
        "Total revenue $1.2B",
        "Adjusted EBITDA1 $208M",
        "Subscription &amp; services revenue $555M",
        "Net (loss) income $(359)M",
    )
    if any(value not in text for value in required):
        raise ValueError("COIN recovery exhibit metrics changed")
    return {
        **receipt,
        "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "verified": True,
        "reported_metrics": {
            "q2_total_revenue": 1_220_068_000.0,
            "q2_adjusted_ebitda_non_gaap": 207_800_000.0,
            "q2_subscription_and_services_revenue": 555_145_000.0,
            "q2_net_loss": -359_000_000.0,
            "used_as_valuation_input": False,
            "treatment": "The earnings deck completes the event package but its non-GAAP EBITDA does not replace common earnings or bound legal and regulatory claims.",
        },
    }


def _primary_filing(structural_cache_root: Path, expected_sha256: str) -> tuple[Path, str]:
    candidates = list(
        (Path(structural_cache_root) / "filings/COIN/CIK0001679788-000167978826000088").glob("*/coin-20260630.htm")
    )
    if len(candidates) != 1:
        raise ValueError("COIN controlling primary filing is unresolved")
    path = candidates[0]
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise ValueError("COIN controlling primary filing hash mismatch")
    text = raw.decode(errors="ignore")
    required = (
        "unable to determine an estimate of the possible loss or range of loss beyond amounts already accrued",
        "additional accruals or resolution in excess of established accruals",
    )
    if any(value not in text for value in required):
        raise ValueError("COIN legal or tax loss-range disclosure changed")
    return path, digest


def _dimensional_instant(structural: dict[str, Any], name: str, member: str) -> dict[str, Any]:
    rows = [
        row
        for row in structural.get("facts", [])
        if row.get("local_name") == name
        and row.get("period_start") is None
        and row.get("period_end") == PERIOD
        and row.get("unit") == "xbrli:shares"
        and isinstance(row.get("value"), (int, float))
        and any(member in dimension_member for _, dimension_member in row.get("dimensions", []))
    ]
    if len(rows) != 1:
        raise ValueError(f"COIN {name} {member} is unresolved")
    row = rows[0]
    return {
        "source_kind": "structural_xbrl",
        "accession": structural.get("source_accession"),
        "filed": structural.get("filed_date"),
        "form": structural.get("form"),
        "period_start": None,
        "period_end": PERIOD,
        "concept": row.get("qname"),
        "unit": row.get("unit"),
        "value": float(row["value"]),
        "dimensions": row.get("dimensions"),
        "reported_vs_estimated": "reported",
    }


def _coin_attempt(
    initial: dict[str, Any],
    structural: dict[str, Any],
    structural_cache_root: Path,
    recovery_source_root: Path,
) -> dict[str, Any]:
    value = deepcopy(initial)
    earnings = initial["source_ledger"]["common_earnings_reconstruction"]
    annual = earnings["annual_history"]
    ttm = float(earnings["ttm"])
    equity = initial["source_ledger"]["equity"]
    share = initial["source_ledger"]["share_count"]
    if ttm >= 0 or equity["value"] <= 0 or share["value"] <= 0:
        raise ValueError("COIN recovery gate changed")

    observations = [
        HistoryObservation(
            "annual",
            row["period_end"],
            int(row["period_end"][:4]),
            row["value"],
            "USD",
            "reported annual parent/common earnings",
            (row["source"],),
        )
        for row in annual
    ]
    observations.append(
        HistoryObservation(
            "operating_ttm",
            PERIOD,
            None,
            ttm,
            "USD",
            "latest FY plus current H1 less prior H1",
            (annual[-1]["source"], earnings["current_h1"], earnings["prior_h1"]),
        )
    )
    metric = summarize_history_metric("normalized_common_earnings", observations)
    if metric is None or metric.low >= 0 or metric.base <= 0:
        raise ValueError("COIN through-cycle earnings gate changed")
    profile = CompanyHistoryProfile(
        HISTORY_POLICY_VERSION,
        "crypto_platform_parent_equity_residual_income",
        VALUATION_DATE,
        tuple(row["period_end"] for row in annual),
        (metric,),
        True,
        "reported_and_company_history",
    )

    recovery_source = _recovery_source(recovery_source_root)
    primary_path, primary_sha = _primary_filing(
        structural_cache_root,
        initial["source_ledger"]["runtime_source_verification"]["primary_document_sha256"],
    )

    corporate_cash = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), PERIOD)
    restricted_cash = _instant(structural, ("RestrictedCashAndCashEquivalentsAtCarryingValue",), PERIOD)
    aggregate_cash = _instant(structural, ("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",), PERIOD)
    safeguarding_asset = _instant(structural, ("SafeguardingAssetOffBalanceSheet",), PERIOD)
    safeguarding_liability = _instant(structural, ("SafeguardingLiabilityOffBalanceSheet",), PERIOD)
    client_cash = initial["source_ledger"]["customer_boundary"]["client_custodial_cash"]
    client_funds = initial["source_ledger"]["customer_boundary"]["client_custodial_funds"]
    client_liability = initial["source_ledger"]["customer_boundary"]["custodial_cash_liability"]
    if aggregate_cash["value"] != corporate_cash["value"] + restricted_cash["value"] + client_cash["value"]:
        raise ValueError("COIN cash scope no longer reconciles")
    if client_funds["value"] != client_liability["value"] or safeguarding_asset["value"] != safeguarding_liability["value"]:
        raise ValueError("COIN customer safeguarding scope no longer matches")

    collateral = _instant(structural, ("CryptoAssetFairValueHeldAsCollateral",), PERIOD)
    collateral_obligation = _instant(structural, ("ObligationToReturnCollateral",), PERIOD)
    loan_fiat = _instant(structural, ("FiatAndPaymentStablecoinFinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss",), PERIOD)
    loan_crypto = _instant(structural, ("CryptoAssetLoansFinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss",), PERIOD)
    owned_crypto = _instant(structural, ("CryptoAssetFairValueNoncurrent",), PERIOD)
    borrowed_crypto = _instant(structural, ("CryptoAssetFairValueBorrowed",), PERIOD)
    temporary_equity = _instant(structural, ("TemporaryEquityCarryingAmountAttributableToParent",), PERIOD)
    option_shares = _instant(structural, ("ShareBasedCompensationArrangementByShareBasedPaymentAwardOptionsOutstandingNumber",), PERIOD, unit="xbrli:shares")
    rsu_shares = _dimensional_instant(structural, "ShareBasedCompensationArrangementByShareBasedPaymentAwardEquityInstrumentsOtherThanOptionsNonvestedNumber", "RestrictedStockUnitsRSUMember")
    prsu_shares = _dimensional_instant(structural, "ShareBasedCompensationArrangementByShareBasedPaymentAwardEquityInstrumentsOtherThanOptionsNonvestedNumber", "PerformanceRestrictedStockUnitsPRSUsMember")

    book = equity["value"] / share["value"]
    base_roe = metric.base / equity["value"]
    bull_roe = min(metric.high / equity["value"], 0.12)
    diagnostics: list[dict[str, Any]] = []
    for name, roe, payout, cost, terminal_roe, terminal_growth in (
        ("forced_positive_bear", 0.01, 0.0, 0.14, 0.04, 0.0),
        ("history_median_base", base_roe, 0.25, 0.105, 0.09, 0.015),
        ("history_capped_bull", bull_roe, 0.40, 0.09, 0.12, 0.025),
    ):
        trace = residual_income_valuation(
            book_value_per_share=book,
            current_roe=roe,
            cost_of_equity=cost,
            current_payout_ratio=payout,
            terminal_roe=terminal_roe,
            terminal_growth=terminal_growth,
            years=5,
        )
        diagnostics.append(
            {
                "name": name,
                "value_per_share": float(trace["intrinsic_value"]),
                "book_value_per_share": book,
                "current_roe": roe,
                "current_payout_ratio": payout,
                "cost_of_equity": cost,
                "terminal_roe": terminal_roe,
                "terminal_growth": terminal_growth,
                "shares": share["value"],
                "publication_allowed": False,
                "rejection_reason": "The forced bear floor is not source-backed; positive diagnostics do not bound the disclosed tax, legal and regulatory tail.",
                "trace": trace,
            }
        )

    reason = (
        "Recovery attempted; COIN remains withheld. Five annual common-earnings periods and the missing Q2 earnings exhibit were recovered and reviewed, but the history-backed bear earnings state remains negative and the controlling filing says some tax loss ranges cannot be estimated beyond recorded accruals. "
        "Customer custodial cash, stablecoin balances, safeguarding assets, crypto collateral, lending balances and borrowed crypto are not issuer cash. A positive bear floor or legal reserve would require invention."
    )
    release = (
        "Revalue after source-bounded tax, legal and regulatory claim ranges and a specialist crypto/customer-funding schedule establish a finite through-cycle bear/base/bull range without treating customer or collateral balances as issuer cash."
    )
    baseline = BaselineValuation(
        ticker="COIN",
        method="crypto_platform_parent_equity_residual_income",
        method_version=BATCH_40_RECOVERY_VERSION,
        low=None,
        base=None,
        high=None,
        confidence=None,
        availability_type=AvailabilityType.NOT_AVAILABLE,
        warnings=(reason, release),
    )
    value.update(
        {
            "model_version": BATCH_40_RECOVERY_VERSION,
            "warning": reason,
            "baseline": baseline.as_private_dict(),
        }
    )
    value["governed_assumptions"] = {
        **profile.public_metadata(),
        "forecast_years": 5,
        "normalization_basis": "five_annual_common_earnings_periods_plus_current_ttm_with_negative_bear_preserved",
        "assumption_source_mix": "reported_parent_equity_earnings_and_completed_q2_event_package",
        "reported_history_earnings_range": (metric.low, metric.base, metric.high),
        "reported_history_roe_range_on_current_equity": (
            metric.low / equity["value"],
            metric.base / equity["value"],
            metric.high / equity["value"],
        ),
        "customer_cash_used_as_free_cash": False,
        "route_is_equity_level": True,
        "ev_debt_bridge_applied": False,
        "equity_floor_basis": "not applied; a positive bear floor was tested privately and rejected as unsupported",
        "reason_codes": [
            "NEGATIVE_THROUGH_CYCLE_BEAR",
            "UNBOUNDED_TAX_REGULATORY_CLAIMS",
            "SPECIALIST_MODEL_REQUIRED",
            "VALUATION_WITHHELD",
        ],
        "invalidation": release,
    }
    value["source_ledger"] = {
        **initial["source_ledger"],
        "company_history_profile": profile.as_private_dict(),
        "completed_earnings_exhibit": recovery_source,
        "tax_legal_regulatory_claim_boundary": {
            "source_kind": "controlling_filing_narrative",
            "accession": initial["source_ledger"]["controlling_filing"]["accession"],
            "primary_document": primary_path.name,
            "primary_document_sha256": primary_sha,
            "table_locator": "Note 20 Commitments and Contingencies - legal and regulatory matters; tax regulation",
            "possible_loss_range": None,
            "loss_range_estimable": False,
            "established_accruals_complete_bound": False,
            "treatment": "No reserve is invented. The source says existing investigations are not expected to impair overall financial condition, but period effects and tax exposure can be material and the additional loss range is not estimable.",
            "reported_vs_estimated": "reported_narrative_and_unresolved_range",
        },
        "customer_crypto_funding_reconciliation": {
            "aggregate_cash_reconciliation": {
                "aggregate_cash_and_restricted": aggregate_cash,
                "corporate_cash": corporate_cash,
                "restricted_cash": restricted_cash,
                "client_custodial_cash": client_cash,
                "formula": "aggregate cash and restricted = corporate cash + restricted cash + client custodial cash",
                "difference": aggregate_cash["value"] - corporate_cash["value"] - restricted_cash["value"] - client_cash["value"],
            },
            "client_custodial_funds": client_funds,
            "custodial_cash_liability": client_liability,
            "safeguarding_asset_off_balance_sheet": safeguarding_asset,
            "safeguarding_liability_off_balance_sheet": safeguarding_liability,
            "crypto_collateral": collateral,
            "obligation_to_return_collateral": collateral_obligation,
            "fiat_and_stablecoin_loan_receivables": loan_fiat,
            "crypto_loan_receivables": loan_crypto,
            "owned_crypto_investment": owned_crypto,
            "borrowed_crypto": borrowed_crypto,
            "all_customer_or_financing_balances_used_as_issuer_cash": False,
        },
        "capital_and_dilution_context": {
            "temporary_equity": temporary_equity,
            "current_class_a_plus_b_shares": share,
            "option_shares_outstanding": option_shares,
            "nonvested_rsu_shares": rsu_shares,
            "nonvested_prsu_shares": prsu_shares,
            "undiscounted_full_share_stress": share["value"] + option_shares["value"] + rsu_shares["value"] + prsu_shares["value"],
            "treatment": "Dilution is source-bounded privately but cannot cure the unbounded claim and negative-bear gates.",
        },
        "rejected_through_cycle_diagnostic": {
            "reported_earnings_percentiles": {"low": metric.low, "base": metric.base, "high": metric.high},
            "reported_bear_roe": metric.low / equity["value"],
            "scenario_rows": diagnostics,
            "publication_allowed": False,
            "why_rejected": "The history-backed bear is a loss. Replacing it with the tested 1% positive ROE floor would manufacture support, while the tax and regulatory claim range remains unbounded.",
        },
        "recovery_attempt": {
            "attempted": True,
            "initial_availability_type": "not_available",
            "final_availability_type": "not_available",
            "missing_earnings_exhibit_recovered": True,
            "positive_finite_base_diagnostic_found": True,
            "history_bear_gate_closed": False,
            "claim_range_gate_closed": False,
            "customer_funding_fcff_gate_closed": False,
            "market_price_used": False,
            "analyst_target_used": False,
            "competitor_value_used": False,
        },
    }
    return value


def build_batch_40_recovery_result(
    *,
    ticker: str,
    source_root: Path,
    structural_root: Path,
    event_root: Path,
    recovery_source_root: Path,
    structural_cache_root: Path | None = None,
) -> dict[str, Any]:
    if ticker not in BATCH_40_TICKERS:
        raise ValueError(ticker)
    initial = build_batch_40_history_result(
        ticker=ticker,
        source_root=source_root,
        structural_root=structural_root,
        event_root=event_root,
        structural_cache_root=structural_cache_root,
    )
    if ticker != "COIN":
        value = deepcopy(initial)
        value["model_version"] = BATCH_40_RECOVERY_VERSION
        value["baseline"] = {**value["baseline"], "method_version": BATCH_40_RECOVERY_VERSION}
        return value
    structural = json.loads((Path(structural_root) / "COIN/structural-filing.json").read_text())
    return _coin_attempt(initial, structural, Path(structural_cache_root), Path(recovery_source_root))


if RECOVERED_PASS_TICKERS | RECOVERED_CONDITIONAL_TICKERS | RECOVERED_WITHHELD_TICKERS != set(BATCH_40_TICKERS):
    raise RuntimeError("Batch 40 recovery classification mismatch")
