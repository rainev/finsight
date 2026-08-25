"""Parsers for normalized FR Y-9C parent data and FFIEC subsidiary corroboration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .specialist_evidence import (
    IdentityBridge,
    RegulatedEntityIdentity,
    SpecialistFact,
    SpecialistPacket,
)


REQUIRED_BANK_FIELDS = frozenset(
    {
        "common_equity", "preferred_equity", "cet1_capital",
        "total_regulatory_capital", "risk_weighted_assets", "cet1_ratio",
        "loan_loss_allowance",
    }
)
Y9C_RECORD_IDS = {
    "common_equity": "DERIVED(BHCK3210-BHCK3283)",
    "preferred_equity": "BHCK3283",
    "cet1_capital": "BHCAP859|BHCWP859",
    "total_regulatory_capital": "BHCA3792|BHCW3792",
    "risk_weighted_assets": "BHCAA223|BHCWA223",
    "cet1_ratio": "BHCAP793|BHCWP793",
    "loan_loss_allowance": "BHCK3123",
}


def load_bank_parent_crosswalk() -> dict[str, RegulatedEntityIdentity]:
    path = Path(__file__).with_name("config") / "bank_parent_crosswalk.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "FINSIGHT-BANK-IDENTITY-1":
        raise ValueError("unsupported bank identity crosswalk")
    result: dict[str, RegulatedEntityIdentity] = {}
    rssds: set[str] = set()
    leis: set[str] = set()
    for row in payload.get("entities", []):
        ticker = str(row.get("ticker") or "")
        identity = RegulatedEntityIdentity(
            cik=row.get("cik"), rssd=row.get("rssd"), lei=row.get("lei"),
            legal_name=row.get("legal_name"), entity_kind=row.get("entity_kind"),
        )
        if not ticker or ticker in result or identity.rssd in rssds or identity.lei in leis:
            raise ValueError("bank identity crosswalk is not unique")
        sources = row.get("sources")
        if not isinstance(sources, Mapping) or set(sources) != {"sec", "rssd", "lei"}:
            raise ValueError("bank identity crosswalk needs SEC, RSSD, and LEI sources")
        result[ticker] = identity
        rssds.add(str(identity.rssd))
        leis.add(str(identity.lei))
    return result


def _packet(
    rows: Sequence[Mapping[str, Any]],
    *,
    rssd: str,
    period_end: str,
    filed_date: str,
    source_kind: str,
    source_url: str,
    authority: str,
    parent_promotable: bool,
    valuation_date: str,
    source_payload_sha256: str | None,
) -> SpecialistPacket:
    selected: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if str(row.get("rssd")) != rssd:
            raise ValueError("bank source RSSD identity mismatch")
        field = str(row.get("field") or "")
        if field in selected:
            raise ValueError(f"duplicate bank regulatory field {field}")
        selected[field] = row
        supplied_id = row.get("source_record_id")
        if source_kind == "fr_y9c" and supplied_id is not None and supplied_id != Y9C_RECORD_IDS.get(field):
            raise ValueError(f"unexpected FR Y-9C record ID for {field}")
    missing = REQUIRED_BANK_FIELDS - set(selected)
    if missing:
        raise ValueError(f"bank regulatory packet missing fields: {sorted(missing)}")
    facts = tuple(
        SpecialistFact(
            field=field,
            value=row["value"],
            unit=str(row.get("unit") or ""),
            period_end=period_end,
            filed_date=filed_date,
            source_url=source_url,
            source_record_id=str(row.get("source_record_id") or Y9C_RECORD_IDS[field]),
            extraction_method=("fr_y9c_caret_bulk" if source_kind == "fr_y9c" else "ffiec_call_report_bulk"),
        )
        for field, row in sorted(selected.items())
        if field in REQUIRED_BANK_FIELDS
    )
    identity = RegulatedEntityIdentity(
        cik=None,
        rssd=rssd,
        lei=None,
        legal_name=str(next((row.get("legal_name") for row in rows if row.get("legal_name")), f"RSSD {rssd}")),
        entity_kind=("holding_company" if source_kind == "fr_y9c" else "bank_subsidiary"),
    )
    bridge = IdentityBridge(
        public_parent=identity,
        regulated_entity=identity,
        relationship=("parent_reporting_entity" if source_kind == "fr_y9c" else "subsidiary_packet_unallocated"),
        consolidation_proven=True,
        evidence_url=source_url,
        evidence_accession=f"{source_kind.upper()}-{period_end}",
    )
    source_bytes = json.dumps(list(rows), sort_keys=True, separators=(",", ":")).encode()
    normalized_sha = hashlib.sha256(source_bytes).hexdigest()
    return SpecialistPacket(
        source_kind=source_kind,
        identity_bridge=bridge,
        facts=facts,
        valuation_date=valuation_date,
        source_sha256=source_payload_sha256 or normalized_sha,
        authority=authority,
        parent_promotable=parent_promotable and source_payload_sha256 is not None,
        normalized_sha256=normalized_sha,
    )


def parse_y9c_rows(
    rows: Sequence[Mapping[str, Any]], *, rssd: str, period_end: str,
    filed_date: str, valuation_date: str, source_payload_sha256: str | None = None,
) -> SpecialistPacket:
    return _packet(
        rows,
        rssd=rssd,
        period_end=period_end,
        filed_date=filed_date,
        source_kind="fr_y9c",
        source_url="https://www.federalreserve.gov/apps/reportingforms/Report/Index/FR_Y-9C",
        authority="parent_primary",
        parent_promotable=True,
        valuation_date=valuation_date,
        source_payload_sha256=source_payload_sha256,
    )


def parse_call_report_rows(
    rows: Sequence[Mapping[str, Any]], *, rssd: str, period_end: str,
    filed_date: str, valuation_date: str, source_payload_sha256: str | None = None,
) -> SpecialistPacket:
    return _packet(
        rows,
        rssd=rssd,
        period_end=period_end,
        filed_date=filed_date,
        source_kind="ffiec_call_report",
        source_url="https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx",
        authority="subsidiary_corroboration",
        parent_promotable=False,
        valuation_date=valuation_date,
        source_payload_sha256=source_payload_sha256,
    )
