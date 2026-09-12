"""Versioned customer-fund and settlement-balance scopes.

The policies identify who owns cash before it reaches a valuation bridge.  They
contain semantic selectors and approved scenario rules, never filing amounts,
dates, or accessions.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from math import isclose, isfinite
import re
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA = "FINSIGHT-CUSTOMER-FUNDS-1"
VERSION = "FINSIGHT-CUSTOMER-FUNDS-WG8-1"
_GAAP = re.compile(r"^https?://(?:fasb\.org|xbrl\.us-gaap)/us-gaap/20\d{2}$")


RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "DASH": MappingProxyType({
        "schema_version": SCHEMA, "version": VERSION, "ticker": "DASH", "cik": "0001792789",
        "mode": "customer_cash_reserve",
        "cash_qname": "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "current_security_qname": "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent",
        "noncurrent_security_qname": "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
        "cash_flow_total_qname": "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "restricted_current_qname": "us-gaap:RestrictedCashCurrent",
        "restricted_noncurrent_qname": "us-gaap:RestrictedCashAndInvestmentsNoncurrent",
        "customer_liability_qname": "us-gaap:ContractWithCustomerLiability",
        "customer_liability_current_qname": "us-gaap:ContractWithCustomerLiabilityCurrent",
        "prepayment_local_name": "ContractWithCustomerLiabilityUnearnedPrepaymentsReceived",
        "processor_funds_local_name": "FundsHeldAtPaymentProcessors",
        "merchant_payable_local_name": "DasherAndMerchantPayableCurrent",
        "temporary_equity_qname": "us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
        "reserve_fractions": (1.0, 0.5, 0.0),
        "issuer_namespace_pattern": r"https?://(?:www\.)?doordash\.com/\d{8}",
        "treatment": "reserve full, half and zero of the current customer contract liability from issuer cash across bear, base and bull; processor-held funds, merchant payables and restricted cash remain separate operating or restricted balances",
    }),
    "ICE": MappingProxyType({
        "schema_version": SCHEMA, "version": VERSION, "ticker": "ICE", "cik": "0001571949",
        "mode": "matched_clearing_funds",
        "cash_qname": "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "cash_flow_total_qname": "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "restricted_current_qname": "us-gaap:RestrictedCashAndCashEquivalentsAtCarryingValue",
        "restricted_noncurrent_qname": "us-gaap:RestrictedCashAndCashEquivalentsNoncurrent",
        "margin_asset_local_name": "MarginDepositsAndGuarantyFundsCurrent",
        "margin_liability_local_name": "MarginDepositsAndGuarantyFundsLiabilityCurrent",
        "clearing_assets_local_name": "MarginDepositsAndGuarantyFundsAssetsCurrent",
        "settlement_receivable_local_name": "InvestedDepositsDeliveryContractsReceivableAndUnsettledVariationMarginCurrent",
        "settlement_payable_local_name": "InvestedDepositsDeliveryContractsPayableAndUnsettledVariationMarginCurrent",
        "cash_deposits_local_name": "CashDeposits",
        "guaranty_fund_asset_local_name": "GuarantyFundAsset",
        "guaranty_contribution_local_name": "GuarantyFundContribution",
        "gross_pledged_local_name": "MarginDepositsAndGuarantyFundsAssetsReceivedOrPledged",
        "issuer_namespace_pattern": r"https?://(?:www\.)?theice\.com/\d{8}",
        "treatment": "exclude matched clearing-member margin and guaranty funds plus restricted cash from issuer surplus cash; matched settlement receivable/payable and gross pledged collateral are operating diagnostics, not additive claims",
    }),
})


def customer_funds_policy(ticker: str) -> dict[str, Any]:
    rule = RULES.get(ticker)
    if rule is None:
        raise ValueError(f"no customer-funds rule for {ticker!r}")
    return deepcopy(dict(rule))


def _same_policy(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return json.dumps(dict(actual), sort_keys=True, separators=(",", ":")) == json.dumps(
        dict(expected), sort_keys=True, separators=(",", ":")
    )


def _context(policy, structural, controlling, cik, cutoff):
    expected = RULES.get(policy.get("ticker"))
    if expected is None or not _same_policy(policy, expected) or str(cik).zfill(10) != expected["cik"]:
        raise RuntimeError("customer-funds policy identity/version mismatch")
    accession = controlling.get("accessionNumber") or controlling.get("accession")
    period = controlling.get("reportDate") or controlling.get("period_end")
    filed = controlling.get("filingDate") or structural.get("filed_date")
    if structural.get("source_accession") != accession or not isinstance(period, str) or not isinstance(filed, str):
        raise ValueError("customer-funds source identity is incomplete")
    if not period <= filed <= cutoff:
        raise ValueError("customer-funds source is outside cutoff")
    date.fromisoformat(period); date.fromisoformat(filed); date.fromisoformat(cutoff)
    facts = structural.get("facts")
    if not isinstance(facts, list):
        raise ValueError("customer-funds structural facts are missing")
    return expected, str(accession), period, facts


def _valid(row, *, policy, accession, period, issuer=False):
    if (row.get("source_accession") != accession or row.get("period_end") != period
        or row.get("period_start") is not None or row.get("unit") != "USD"
        or str(row.get("entity_identifier", "")).zfill(10) != policy["cik"]
        or row.get("entity_scheme") != "http://www.sec.gov/CIK"
        or isinstance(row.get("value"), bool) or not isinstance(row.get("value"), (int, float))
        or not isfinite(float(row["value"])) or float(row["value"]) < 0):
        raise ValueError("customer-funds fact identity, period, unit or sign is invalid")
    namespace = str(row.get("namespace", ""))
    if issuer:
        if not re.fullmatch(str(policy["issuer_namespace_pattern"]), namespace):
            raise ValueError("customer-funds issuer namespace mismatch")
    elif not _GAAP.fullmatch(namespace):
        raise ValueError("customer-funds GAAP namespace mismatch")


def _one(facts, *, policy, accession, period, qname=None, local_name=None, issuer=False,
         undimensioned=True):
    rows = []
    for row in facts:
        if qname is not None and row.get("qname") != qname:
            continue
        if local_name is not None and row.get("local_name") != local_name:
            continue
        if row.get("period_end") != period or row.get("period_start") is not None:
            continue
        if undimensioned and row.get("dimensions") not in (None, []):
            continue
        _valid(row, policy=policy, accession=accession, period=period, issuer=issuer)
        rows.append(row)
    if not rows:
        raise ValueError(f"required customer-funds fact is missing: {qname or local_name}")
    values = {float(row["value"]) for row in rows}
    if len(values) != 1:
        raise ValueError(f"required customer-funds fact conflicts: {qname or local_name}")
    return dict(rows[0]), values.pop()


def select_customer_funds(policy: Mapping[str, Any], structural: Mapping[str, Any],
                          controlling: Mapping[str, Any], cik: str, cutoff: str) -> dict[str, Any]:
    policy, accession, period, facts = _context(policy, structural, controlling, cik, cutoff)
    source_rows: list[dict[str, Any]] = []
    excluded_rows: list[dict[str, Any]] = []
    components: dict[str, float] = {}

    def gaap(key):
        return _one(facts, policy=policy, accession=accession, period=period, qname=policy[key])

    def issuer(key):
        return _one(facts, policy=policy, accession=accession, period=period,
                    local_name=policy[key], issuer=True)

    if policy["mode"] == "customer_cash_reserve":
        cash_row, cash = gaap("cash_qname")
        current_security_row, current_security = gaap("current_security_qname")
        noncurrent_security_row, noncurrent_security = gaap("noncurrent_security_qname")
        cash_flow_row, cash_flow_total = gaap("cash_flow_total_qname")
        restricted_current_row, restricted_current = gaap("restricted_current_qname")
        restricted_noncurrent_row, restricted_noncurrent = gaap("restricted_noncurrent_qname")
        customer_row, customer_liability = gaap("customer_liability_qname")
        current_customer_row, current_customer = gaap("customer_liability_current_qname")
        prepayment_row, prepayment = issuer("prepayment_local_name")
        processor_row, processor_funds = issuer("processor_funds_local_name")
        merchant_row, merchant_payable = issuer("merchant_payable_local_name")
        temporary_row, temporary_equity = gaap("temporary_equity_qname")
        if not isclose(customer_liability, current_customer, rel_tol=1e-12, abs_tol=0.01):
            raise ValueError("current customer liability does not reconcile to reported total")
        if prepayment > customer_liability:
            raise ValueError("customer prepayment component exceeds total contract liability")
        if not isclose(cash_flow_total, cash + restricted_current + restricted_noncurrent,
                       rel_tol=1e-12, abs_tol=0.01):
            raise ValueError("cash-flow total does not reconcile to issuer and restricted cash")
        total_cash_and_investments = cash + current_security + noncurrent_security
        bear_fraction, base_fraction, bull_fraction = policy["reserve_fractions"]
        reserve = {
            "bear_cash_reserve": customer_liability * bear_fraction,
            "base_cash_reserve": customer_liability * base_fraction,
            "bull_cash_reserve": customer_liability * bull_fraction,
        }
        source_rows = [cash_row, current_security_row, noncurrent_security_row,
                       customer_row, current_customer_row]
        excluded_rows = [cash_flow_row, restricted_current_row, restricted_noncurrent_row,
                         prepayment_row, processor_row, merchant_row, temporary_row]
        components = {
            "issuer_cash": cash,
            "current_marketable_securities": current_security,
            "noncurrent_marketable_securities": noncurrent_security,
            "unreserved_cash_and_investments": total_cash_and_investments,
            "restricted_cash_current": restricted_current,
            "restricted_cash_noncurrent": restricted_noncurrent,
            "customer_contract_liability": customer_liability,
            "customer_unearned_prepayments_component": prepayment,
            "processor_held_funds_operating": processor_funds,
            "merchant_payable_operating": merchant_payable,
            "temporary_equity_separate_claim": temporary_equity,
            **reserve,
        }
        formula = "current issuer cash and AFS securities less full/half/zero current customer-liability reserve; restricted and processor-held cash remain excluded"
        return {
            "status": "source_bound", "claim_adjustment": 0.0, **reserve,
            "review_reasons": [], "policy": dict(policy), "source_rows": source_rows,
            "excluded_rows": excluded_rows, "components": components,
            "period_end": period, "controlling_accession": accession, "formula": formula,
        }

    if policy["mode"] == "matched_clearing_funds":
        cash_row, cash = gaap("cash_qname")
        cash_flow_row, cash_flow_total = gaap("cash_flow_total_qname")
        restricted_current_row, restricted_current = gaap("restricted_current_qname")
        restricted_noncurrent_row, restricted_noncurrent = gaap("restricted_noncurrent_qname")
        margin_asset_row, margin_asset = issuer("margin_asset_local_name")
        margin_liability_row, margin_liability = issuer("margin_liability_local_name")
        clearing_assets_row, clearing_assets = issuer("clearing_assets_local_name")
        receivable_row, settlement_receivable = issuer("settlement_receivable_local_name")
        payable_row, settlement_payable = issuer("settlement_payable_local_name")
        cash_deposits_row, cash_deposits = issuer("cash_deposits_local_name")
        guaranty_asset_row, guaranty_asset = issuer("guaranty_fund_asset_local_name")
        guaranty_contribution_row, guaranty_contribution = issuer("guaranty_contribution_local_name")
        gross_pledged_row, gross_pledged = issuer("gross_pledged_local_name")
        if not isclose(margin_asset, margin_liability, rel_tol=1e-12, abs_tol=0.01):
            raise ValueError("clearing-member margin asset and liability do not match")
        if not isclose(cash_deposits, margin_asset, rel_tol=1e-12, abs_tol=0.01):
            raise ValueError("cash-deposit presentation does not match member margin funds")
        if not isclose(settlement_receivable, settlement_payable, rel_tol=1e-12, abs_tol=0.01):
            raise ValueError("settlement receivable and payable do not match")
        if not isclose(clearing_assets, margin_asset + settlement_receivable,
                       rel_tol=1e-12, abs_tol=0.01):
            raise ValueError("clearing assets do not reconcile to margin and settlement components")
        if not isclose(cash_flow_total, cash + restricted_current + restricted_noncurrent + margin_asset,
                       rel_tol=1e-12, abs_tol=0.01):
            raise ValueError("cash-flow total does not reconcile to issuer, restricted and member funds")
        source_rows = [cash_row, margin_asset_row, margin_liability_row,
                       receivable_row, payable_row]
        excluded_rows = [cash_flow_row, restricted_current_row, restricted_noncurrent_row,
                         clearing_assets_row, cash_deposits_row, guaranty_asset_row,
                         guaranty_contribution_row, gross_pledged_row]
        components = {
            "issuer_cash": cash,
            "restricted_cash_current": restricted_current,
            "restricted_cash_noncurrent": restricted_noncurrent,
            "matched_member_margin_asset": margin_asset,
            "matched_member_margin_liability": margin_liability,
            "matched_settlement_receivable": settlement_receivable,
            "matched_settlement_payable": settlement_payable,
            "clearing_assets_total": clearing_assets,
            "cash_deposits_duplicate": cash_deposits,
            "guaranty_fund_asset_diagnostic": guaranty_asset,
            "guaranty_fund_contribution_diagnostic": guaranty_contribution,
            "gross_pledged_collateral_not_additive": gross_pledged,
            "net_customer_fund_claim": 0.0,
        }
        return {
            "status": "source_bound", "claim_adjustment": 0.0,
            "review_reasons": [], "policy": dict(policy), "source_rows": source_rows,
            "excluded_rows": excluded_rows, "components": components,
            "period_end": period, "controlling_accession": accession,
            "formula": "issuer cash only; matched member margin and settlement balances net to zero and restricted/gross pledged collateral remain excluded",
        }

    raise RuntimeError("unsupported customer-funds mode")


__all__ = ["RULES", "SCHEMA", "VERSION", "customer_funds_policy", "select_customer_funds"]
