"""Normalized FERC Form 1 and Form 3-Q specialist packet parser."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .specialist_evidence import (
    IdentityBridge,
    RegulatedEntityIdentity,
    SpecialistFact,
    SpecialistPacket,
)


REQUIRED_FERC_FIELDS = frozenset(
    {"rate_base", "allowed_return", "utility_debt", "ownership_interest"}
)


def parse_ferc_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    entity_id: str,
    form: str,
    period_end: str,
    filed_date: str,
    valuation_date: str,
    public_parent_cik: str | None = None,
    allocation_bridge: Mapping[str, Any] | None = None,
    source_payload_sha256: str | None = None,
) -> SpecialistPacket:
    normalized_form = form.upper()
    if normalized_form not in {"FORM1", "FORM3Q"}:
        raise ValueError("unsupported FERC form")
    selected: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if row.get("entity_id") != entity_id:
            raise ValueError("FERC entity identity mismatch")
        field = str(row.get("field") or "")
        if field in selected:
            raise ValueError(f"duplicate FERC field {field}")
        selected[field] = row
    missing = REQUIRED_FERC_FIELDS - set(selected)
    if missing:
        raise ValueError(f"FERC packet missing fields: {sorted(missing)}")
    if public_parent_cik is not None and allocation_bridge is None:
        raise ValueError("FERC subsidiary evidence needs parent ownership and allocation bridge")
    if public_parent_cik is not None and (
        not isinstance(allocation_bridge.get("allocation_method"), str)
        or not allocation_bridge["allocation_method"].strip()
        or allocation_bridge.get("reconciliation_status") != "pass"
        or source_payload_sha256 is None
    ):
        raise ValueError("FERC parent allocation requires exact payload and passing reconciliation")

    utility = RegulatedEntityIdentity(
        cik=None,
        rssd=None,
        lei=None,
        legal_name=str(next((row.get("legal_name") for row in rows if row.get("legal_name")), entity_id)),
        entity_kind="regulated_utility",
        ferc_cid=entity_id,
    )
    if public_parent_cik is None:
        parent = utility
        bridge = IdentityBridge(
            public_parent=utility,
            regulated_entity=utility,
            relationship="regulated_reporting_entity",
            consolidation_proven=True,
            evidence_url="https://www.ferc.gov/general-information-0/electric-industry-forms",
            evidence_accession=f"FERC-{normalized_form}-{period_end}",
        )
        authority, parent_promotable = "regulated_entity_only", False
    else:
        parent = RegulatedEntityIdentity(
            cik=public_parent_cik,
            rssd=None,
            lei=None,
            legal_name=str(allocation_bridge.get("public_parent_name") or f"CIK {public_parent_cik}"),
            entity_kind="public_parent",
        )
        ownership = allocation_bridge.get("ownership_percent")
        method = allocation_bridge.get("allocation_method")
        bridge = IdentityBridge(
            public_parent=parent,
            regulated_entity=utility,
            relationship="regulated_utility_subsidiary",
            consolidation_proven=allocation_bridge.get("consolidation_proven") is True,
            evidence_url=str(allocation_bridge.get("evidence_url") or "https://www.ferc.gov/general-information-0/electric-industry-forms"),
            evidence_accession=str(allocation_bridge.get("evidence_accession") or f"FERC-{normalized_form}-{period_end}"),
            ownership_percent=ownership,
            allocation_method=method,
        )
        authority, parent_promotable = "allocated_parent_evidence", True

    source_url = "https://www.ferc.gov/general-information-0/electric-industry-forms"
    facts = tuple(
        SpecialistFact(
            field=field,
            value=row["value"],
            unit=str(row.get("unit") or ""),
            period_end=period_end,
            filed_date=filed_date,
            source_url=source_url,
            source_record_id=str(row.get("source_record_id") or field),
            extraction_method="ferc_eforms_xbrl",
        )
        for field, row in sorted(selected.items())
        if field in REQUIRED_FERC_FIELDS
    )
    raw = json.dumps(list(rows), sort_keys=True, separators=(",", ":")).encode()
    normalized_sha = hashlib.sha256(raw).hexdigest()
    return SpecialistPacket(
        source_kind="ferc_form_1" if normalized_form == "FORM1" else "ferc_form_3q",
        identity_bridge=bridge,
        facts=facts,
        valuation_date=valuation_date,
        source_sha256=source_payload_sha256 or normalized_sha,
        authority=authority,
        parent_promotable=parent_promotable and source_payload_sha256 is not None,
        normalized_sha256=normalized_sha,
    )
