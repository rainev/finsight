"""Source-bound non-debt claim policies for specialist refresh families.

This module owns the ADP client-funds/legal-claim overlay only.  It does not
assert that ADP's full FCFF refresh is ready: debt/finance-lease completeness
and the operating bridge remain outside this policy.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import re
from typing import Any, Mapping

from .xbrl import load_concept_config
from .calculation_recipe import number


SCHEMA = "FINSIGHT-REFRESH-CLAIM-POLICY-1"
ADP_CIK = "0000008670"
_ADP_CUSTOM_NAMESPACE = re.compile(r"^https?://www\.adp\.com/[0-9]{8}$")
_GAAP_NAMESPACE = re.compile(r"^https?://(?:fasb\.org|xbrl\.us-gaap)/us-gaap/[0-9]{4}$")


def capex_alias_spec() -> dict[str, Any]:
    """Return ADP's approved capex alias without copying a frozen amount."""
    config = load_concept_config()
    field = deepcopy(config.get("fields", {}).get("capital_expenditures", {}))
    concepts = list(field.get("concepts", ()))
    # batch_18_history._config('ADP') adds this reported ADP filing concept
    # because the generic aliases do not cover the issuer's exact cash-flow
    # tag.  The value is selected from the current filing at refresh time.
    if "PaymentsToAcquireOtherPropertyPlantAndEquipment" not in concepts:
        concepts.append("PaymentsToAcquireOtherPropertyPlantAndEquipment")
    field["concepts"] = concepts
    return {
        "field": "capital_expenditures",
        "unit": field.get("unit"),
        "kind": field.get("kind"),
        "concepts": concepts,
        "source_rule": "batch_18_history._config('ADP')",
        "config_version": config.get("version"),
        "amount_fit_forbidden": True,
    }


def build_adp_claim_policy() -> dict[str, Any]:
    """Compile the reusable ADP claim selector contract.

    No filing date, source amount, or source accession is embedded here.
    Those are supplied by the controlling filing and structural packet.
    """
    return {
        "schema_version": SCHEMA,
        "version": f"{SCHEMA}-ADP",
        "ticker": "ADP",
        "cik": ADP_CIK,
        "status": "source_validation_pending",
        "claim_fields": {
            "funds_held": {"local_name": "FundsHeldClients", "kind": "instant", "unit": "USD", "issuer_namespace": True},
            "client_obligations": {"local_name": "ClientFundsObligations", "kind": "instant", "unit": "USD", "issuer_namespace": True},
            "legal_accrual": {"local_name": "LossContingencyAccrualAtCarryingValue", "kind": "instant", "unit": "USD", "issuer_namespace": False},
            "legal_receivable": {"local_name": "LossContingencyReceivable", "kind": "instant", "unit": "USD", "issuer_namespace": False},
            "reported_preferred": {"local_name": "PreferredStockValue", "kind": "instant", "unit": "USD", "issuer_namespace": False},
        },
        "issuer_namespace_rule": {
            "uri_pattern": r"^https?://www\.adp\.com/[0-9]{8}$",
            "namespace_date_is_taxonomy_version_not_financial_period": True,
            "qname_prefix_is_ignored": True,
            "required_custom_local_names": ["FundsHeldClients", "ClientFundsObligations"],
        },
        "scope_requirements": {
            "funds_held_not_issuer_surplus_cash": True,
            "obligation_shortfall_is_claim_once": True,
            "legal_receivable_netted_only_against_scoped_accrual": True,
            "ordinary_operating_liabilities_not_repeated": True,
        },
        "scope_narrative": "Client funds are not issuer-owned surplus cash; only the reported client-obligation shortfall is reserved once. The legal receivable nets only the scoped legal accrual, and ordinary operating liabilities remain in operating cash conversion.",
        "formula": {
            "client_funds_shortfall": {"subtract": ["client_obligations", "funds_held"]},
            "net_legal_claim": {"subtract": ["legal_accrual", "legal_receivable"]},
            "preferred_equity_adjustment": {"add": ["client_funds_shortfall", "net_legal_claim"]},
        },
        "capex_alias": capex_alias_spec(),
        "review_rules": [
            "negative client-funds shortfall requires review; never clamp to zero",
            "negative net legal claim requires review; never clamp to zero",
            "missing or ambiguous source facts block binding; no missing-tag zero",
        ],
    }


ADP_CLAIM_POLICY = build_adp_claim_policy()


def _number(value: Any, label: str) -> float:
    return number(value, f'ADP {label}')


def _identity_row(row: Mapping[str, Any], *, name: str, unit: str, period_end: str, accession: str, cik: str, issuer_namespace: bool) -> bool:
    if row.get("local_name") != name or row.get("unit") != unit or row.get("period_end") != period_end:
        return False
    if str(row.get('qname','')).split(':')[-1] != name:
        return False
    if row.get("period_start") is not None or row.get("source_accession") != accession:
        return False
    if str(row.get("entity_identifier", "")).zfill(10) != cik or row.get("entity_scheme") != "http://www.sec.gov/CIK":
        return False
    if row.get("dimensions") not in ([], None):
        return False
    namespace = str(row.get("namespace", ""))
    if issuer_namespace:
        if not _ADP_CUSTOM_NAMESPACE.fullmatch(namespace):
            return False
        stamp = namespace.rsplit('/',1)[-1]
        try: date.fromisoformat(f'{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}')
        except ValueError: return False
    elif not _GAAP_NAMESPACE.fullmatch(namespace):
        return False
    return True


def _select_one(structural: Mapping[str, Any], spec: Mapping[str, Any], *, period_end: str, accession: str, cik: str) -> dict[str, Any]:
    facts = structural.get("facts")
    if not isinstance(facts, list):
        raise ValueError("ADP structural packet has no fact rows")
    matches = [
        row for row in facts
        if isinstance(row, Mapping)
        and _identity_row(
            row,
            name=str(spec["local_name"]),
            unit=str(spec["unit"]),
            period_end=period_end,
            accession=accession,
            cik=cik,
            issuer_namespace=bool(spec.get("issuer_namespace")),
        )
    ]
    if not matches:
        raise ValueError(f"ADP required source fact missing: {spec['local_name']}")
    unique: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for row in matches:
        key = (row.get("value"), row.get("context_id"), row.get("namespace"), row.get("qname"), str(row.get("presentation_ancestry")))
        unique[key] = row
    if len(unique) != 1:
        raise ValueError(f"ADP required source fact is ambiguous: {spec['local_name']}")
    row = deepcopy(next(iter(unique.values())))
    return row


def _check_scope(rows: Mapping[str, Mapping[str, Any]], policy: Mapping[str, Any]) -> None:
    contexts = {row.get("context_id") for row in rows.values()}
    if len(contexts) != 1 or None in contexts:
        raise ValueError("ADP claim facts do not share one controlling context")
    held = rows["funds_held"]
    obligations = rows["client_obligations"]
    held_ancestry = set(held.get("presentation_ancestry") or [])
    obligation_ancestry = set(obligations.get("presentation_ancestry") or [])
    common = held_ancestry & obligation_ancestry
    if not any("CorporateInvestmentsAndFundsHeldForClientsAbstract" in item for item in common):
        raise ValueError("ADP client-funds facts lack shared client-funds scope")
    if not any("Assets" in item for item in held_ancestry):
        raise ValueError("ADP funds-held fact is not in an asset presentation scope")
    if not any("Liabilities" in item for item in obligation_ancestry):
        raise ValueError("ADP client-obligation fact is not in a liability presentation scope")
    for name in ("legal_accrual", "legal_receivable"):
        ancestry = set(rows[name].get("presentation_ancestry") or [])
        if not any("CommitmentsAndContingenciesDisclosureAbstract" in item for item in ancestry):
            raise ValueError(f"ADP {name} lacks scoped legal disclosure ancestry")
    required_scope = policy.get("scope_requirements", {})
    if not all(required_scope.get(key) is True for key in ("funds_held_not_issuer_surplus_cash", "obligation_shortfall_is_claim_once", "legal_receivable_netted_only_against_scoped_accrual")):
        raise ValueError("ADP claim policy scope is incomplete")


def select_current_claims(policy: Mapping[str, Any], structural: Mapping[str, Any], controlling: Mapping[str, Any], cik: str, cutoff: str) -> dict[str, Any]:
    """Select ADP's current non-debt claim facts and calculate the overlay.

    The function returns ``status=review_required`` for negative derived
    claims, retaining raw values and formula inputs without clamping them.
    Identity, accession, period, unit, namespace, and scope failures raise.
    """
    if policy.get('schema_version') == 'FINSIGHT-ACQUISITION-CLAIM-1':
        from .refresh_acquisition_claims import select_acquisition_claim
        return select_acquisition_claim(policy, structural, controlling, cik, cutoff)
    if policy.get('schema_version') == 'FINSIGHT-LITIGATION-CLAIM-1':
        from .refresh_litigation_claims import select_litigation_claim
        return select_litigation_claim(policy,structural,controlling,cik,cutoff)
    if policy.get('schema_version') == 'FINSIGHT-COMMITMENT-CLAIM-1':
        from .refresh_commitment_claims import select_commitment_claim
        return select_commitment_claim(policy,structural,controlling,cik,cutoff)
    if policy.get('schema_version') == 'FINSIGHT-POST-FILING-EVENT-1':
        from .refresh_post_filing_events import select_post_filing_event
        return select_post_filing_event(policy,structural,controlling,cik,cutoff)
    if policy.get('schema_version') == 'FINSIGHT-OPERATING-CLAIM-1':
        from .refresh_operating_claims import select_operating_claim
        return select_operating_claim(policy,structural,controlling,cik,cutoff)
    if policy.get('schema_version') == 'FINSIGHT-CUSTOMER-FUNDS-1':
        from .refresh_customer_funds import select_customer_funds
        return select_customer_funds(policy,structural,controlling,cik,cutoff)
    if policy.get('schema_version') == 'FINSIGHT-ACQUISITION-FINANCING-CLAIMS-1':
        from .refresh_acquisition_financing_claims import select_acquisition_financing_claim
        return select_acquisition_financing_claim(policy,structural,controlling,cik,cutoff)
    if policy.get('schema_version') == 'FINSIGHT-CONVERTIBLE-CLAIM-1':
        from .refresh_convertible_claims import select_convertible_claim
        return select_convertible_claim(policy,structural,controlling,cik,cutoff)
    if policy.get('schema_version') == 'FINSIGHT-TRANSACTION-CLAIMS-1':
        from .refresh_transaction_claims import select_transaction_claim
        return select_transaction_claim(policy,structural,controlling,cik,cutoff)
    if policy.get('schema_version') == 'FINSIGHT-NCI-OWNERSHIP-CLAIM-1':
        from .refresh_nci_ownership_claims import select_nci_ownership_claim
        return select_nci_ownership_claim(policy,structural,controlling,cik,cutoff)
    if policy.get("ticker") != "ADP":
        raise ValueError("ADP claim selector received a non-ADP policy")
    expected_cik = str(policy.get("cik", cik)).zfill(10)
    normalized_cik = str(cik).zfill(10)
    if normalized_cik != expected_cik or not normalized_cik.isdigit() or len(normalized_cik) != 10:
        raise ValueError("ADP claim CIK mismatch")
    try:
        cutoff_date = date.fromisoformat(str(cutoff))
    except ValueError as exc:
        raise ValueError("ADP cutoff must be an ISO date") from exc
    accession = str(controlling.get("accession") or controlling.get("accessionNumber") or "")
    period_end = str(controlling.get("period_end") or controlling.get("reportDate") or "")
    if not accession or not period_end:
        raise ValueError("ADP controlling filing requires accession and period_end")
    try:
        date.fromisoformat(period_end)
    except ValueError as exc:
        raise ValueError("ADP controlling filing has invalid period_end") from exc
    if str(structural.get("source_accession", "")) != accession:
        raise ValueError("ADP structural source accession mismatch")
    filed_date = structural.get("filed_date")
    if not isinstance(filed_date, str) or not date.fromisoformat(period_end) <= date.fromisoformat(filed_date) <= cutoff_date:
        raise ValueError("ADP structural source is outside cutoff")
    specs = policy.get("claim_fields")
    if not isinstance(specs, Mapping):
        raise ValueError("ADP claim policy has no claim_fields")
    rows = {name: _select_one(structural, spec, period_end=period_end, accession=accession, cik=normalized_cik) for name, spec in specs.items()}
    _check_scope(rows, policy)
    funds_held = _number(rows["funds_held"]["value"], "funds held")
    client_obligations = _number(rows["client_obligations"]["value"], "client obligations")
    legal_accrual = _number(rows["legal_accrual"]["value"], "legal accrual")
    legal_receivable = _number(rows["legal_receivable"]["value"], "legal receivable")
    reported_preferred = _number(rows["reported_preferred"]["value"], "reported preferred")
    if min(funds_held,client_obligations,legal_accrual,legal_receivable,reported_preferred) < 0:
        raise ValueError('ADP reported asset/claim sign requires an explicit source rule')
    if reported_preferred != 0.0:
        raise ValueError("ADP reported preferred stock is nonzero; claim overlay cannot silently overlap it")
    client_funds_shortfall = client_obligations - funds_held
    net_legal_claim = legal_accrual - legal_receivable
    claim_adjustment = client_funds_shortfall + net_legal_claim
    review_reasons = []
    if client_funds_shortfall < 0:
        review_reasons.append("client_funds_shortfall_negative")
    if net_legal_claim < 0:
        review_reasons.append("net_legal_claim_negative")
    status = "review_required" if review_reasons else "source_bound"
    return {
        "status": status,
        "ticker": "ADP",
        "cik": normalized_cik,
        "controlling_accession": accession,
        "period_end": period_end,
        "source_filed_date": filed_date,
        "reported_preferred_equity": reported_preferred,
        "preferred_equity": None if review_reasons else claim_adjustment,
        "claim_adjustment": None if review_reasons else claim_adjustment,
        "raw_components": {
            "funds_held": funds_held,
            "client_obligations": client_obligations,
            "legal_accrual": legal_accrual,
            "legal_receivable": legal_receivable,
        },
        "derived_components": {"client_funds_shortfall": client_funds_shortfall, "net_legal_claim": net_legal_claim},
        "review_reasons": review_reasons,
        "formula": deepcopy(policy["formula"]),
        "scope": deepcopy(policy["scope_requirements"]),
        "scope_narrative": policy.get("scope_narrative"),
        "claim_sources": rows,
        "source_ledger": {
            "controlling_accession": accession,
            "period_end": period_end,
            "claim_sources": rows,
            "claim_formula": deepcopy(policy["formula"]),
        },
        "sources": rows,
        "capex_alias": deepcopy(policy.get("capex_alias", capex_alias_spec())),
    }


__all__ = ["ADP_CLAIM_POLICY", "SCHEMA", "build_adp_claim_policy", "capex_alias_spec", "select_current_claims"]
