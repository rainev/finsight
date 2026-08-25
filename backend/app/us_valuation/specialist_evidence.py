"""Private identity-safe packet contracts for official specialist sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from math import isfinite
from numbers import Real
import re
from typing import Any, Mapping
from urllib.parse import urlparse


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty text")
    return value.strip()


def _iso(value: object, field: str) -> str:
    text = _text(value, field)
    try:
        date.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO date") from error
    return text


def _source(value: object) -> str:
    text = _text(value, "source_url")
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("source_url must be HTTPS")
    return text


@dataclass(frozen=True)
class RegulatedEntityIdentity:
    cik: str | None
    rssd: str | None
    lei: str | None
    legal_name: str
    entity_kind: str
    ferc_cid: str | None = None

    def __post_init__(self) -> None:
        if self.cik is not None and not re.fullmatch(r"\d{10}", self.cik):
            raise ValueError("CIK must be ten digits")
        if self.rssd is not None and not re.fullmatch(r"\d{4,12}", self.rssd):
            raise ValueError("RSSD must be numeric")
        if self.lei is not None and not re.fullmatch(r"[A-Z0-9]{20}", self.lei):
            raise ValueError("LEI must be exactly 20 alphanumeric characters")
        _text(self.legal_name, "legal_name")
        _text(self.entity_kind, "entity_kind")
        if self.ferc_cid is not None:
            _text(self.ferc_cid, "ferc_cid")

    def as_dict(self) -> dict[str, Any]:
        return {
            "cik": self.cik, "rssd": self.rssd, "lei": self.lei,
            "legal_name": self.legal_name, "entity_kind": self.entity_kind,
            "ferc_cid": self.ferc_cid,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RegulatedEntityIdentity:
        return cls(**{key: value.get(key) for key in ("cik", "rssd", "lei", "legal_name", "entity_kind", "ferc_cid")})


@dataclass(frozen=True)
class IdentityBridge:
    public_parent: RegulatedEntityIdentity
    regulated_entity: RegulatedEntityIdentity
    relationship: str
    consolidation_proven: bool
    evidence_url: str
    evidence_accession: str
    ownership_percent: float | None = None
    allocation_method: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.public_parent, RegulatedEntityIdentity) or not isinstance(self.regulated_entity, RegulatedEntityIdentity):
            raise ValueError("identity bridge requires governed identities")
        _text(self.relationship, "relationship")
        _source(self.evidence_url)
        _text(self.evidence_accession, "evidence_accession")
        subsidiary = self.regulated_entity != self.public_parent
        if subsidiary and (
            not self.consolidation_proven
            or self.ownership_percent is None
            or self.allocation_method is None
        ):
            raise ValueError("subsidiary evidence requires proven consolidation and allocation")
        if not subsidiary and not self.consolidation_proven:
            raise ValueError("parent reporting identity requires proven consolidation")
        if self.ownership_percent is not None and not 0 < self.ownership_percent <= 1:
            raise ValueError("ownership_percent must be in (0, 1]")
        if self.allocation_method is not None:
            _text(self.allocation_method, "allocation_method")

    def as_dict(self) -> dict[str, Any]:
        return {
            "public_parent": self.public_parent.as_dict(),
            "regulated_entity": self.regulated_entity.as_dict(),
            "relationship": self.relationship,
            "consolidation_proven": self.consolidation_proven,
            "evidence_url": self.evidence_url,
            "evidence_accession": self.evidence_accession,
            "ownership_percent": self.ownership_percent,
            "allocation_method": self.allocation_method,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> IdentityBridge:
        return cls(
            public_parent=RegulatedEntityIdentity.from_dict(value["public_parent"]),
            regulated_entity=RegulatedEntityIdentity.from_dict(value["regulated_entity"]),
            relationship=value["relationship"],
            consolidation_proven=value["consolidation_proven"],
            evidence_url=value["evidence_url"],
            evidence_accession=value["evidence_accession"],
            ownership_percent=value.get("ownership_percent"),
            allocation_method=value.get("allocation_method"),
        )


@dataclass(frozen=True)
class SpecialistFact:
    field: str
    value: float
    unit: str
    period_end: str
    filed_date: str
    source_url: str
    source_record_id: str
    extraction_method: str

    def __post_init__(self) -> None:
        _text(self.field, "field")
        if isinstance(self.value, bool) or not isinstance(self.value, Real) or not isfinite(float(self.value)):
            raise ValueError("specialist value must be finite")
        _text(self.unit, "unit")
        _iso(self.period_end, "period_end")
        _iso(self.filed_date, "filed_date")
        _source(self.source_url)
        _text(self.source_record_id, "source_record_id")
        _text(self.extraction_method, "extraction_method")

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> SpecialistFact:
        return cls(**{key: value[key] for key in ("field", "value", "unit", "period_end", "filed_date", "source_url", "source_record_id", "extraction_method")})


_FIELD_UNITS = {
    "cet1_ratio": {"ratio"}, "allowed_return": {"ratio"},
    "ownership_interest": {"ratio"}, "occupancy": {"ratio"},
}
_NONNEGATIVE_FIELDS = {
    "common_equity", "preferred_equity", "cet1_capital",
    "total_regulatory_capital", "risk_weighted_assets", "loan_loss_allowance",
    "rate_base", "utility_debt",
}
_RATIO_FIELDS = {"cet1_ratio", "allowed_return", "ownership_interest", "occupancy"}


@dataclass(frozen=True)
class SpecialistPacket:
    source_kind: str
    identity_bridge: IdentityBridge
    facts: tuple[SpecialistFact, ...]
    valuation_date: str
    source_sha256: str
    authority: str = "parent_primary"
    parent_promotable: bool = True
    normalized_sha256: str | None = None
    parser_version: str = "FINSIGHT-SPECIALIST-PARSER-1"

    def __post_init__(self) -> None:
        _text(self.source_kind, "source_kind")
        if not isinstance(self.identity_bridge, IdentityBridge):
            raise ValueError("identity_bridge is required")
        if not self.identity_bridge.consolidation_proven:
            raise ValueError("specialist packet consolidation is unproven")
        cutoff = _iso(self.valuation_date, "valuation_date")
        if not isinstance(self.facts, tuple) or not self.facts or any(not isinstance(fact, SpecialistFact) for fact in self.facts):
            raise ValueError("specialist packet requires facts")
        for fact in self.facts:
            if fact.filed_date > cutoff:
                raise ValueError("specialist fact was filed after cutoff")
            if fact.period_end > cutoff:
                raise ValueError("specialist fact period ends after cutoff")
            allowed = _FIELD_UNITS.get(fact.field, {"USD", "USD millions", "shares"})
            if fact.unit not in allowed:
                raise ValueError(f"specialist fact unit is invalid for {fact.field}")
            if fact.field in _NONNEGATIVE_FIELDS and fact.value < 0:
                raise ValueError(f"specialist fact must be nonnegative for {fact.field}")
            if fact.field in _RATIO_FIELDS and not 0 <= fact.value <= 1:
                raise ValueError(f"specialist ratio must be in [0, 1] for {fact.field}")
        if not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256):
            raise ValueError("source_sha256 must be lowercase SHA-256")
        _text(self.authority, "authority")
        if self.authority == "subsidiary_corroboration" and self.parent_promotable:
            raise ValueError("subsidiary corroboration cannot be parent promotable")
        if self.normalized_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", self.normalized_sha256):
            raise ValueError("normalized_sha256 must be lowercase SHA-256")
        _text(self.parser_version, "parser_version")

    @property
    def receipt_sha256(self) -> str:
        encoded = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_kind": self.source_kind,
            "identity_bridge": self.identity_bridge.as_dict(),
            "facts": [fact.as_dict() for fact in self.facts],
            "valuation_date": self.valuation_date,
            "source_sha256": self.source_sha256,
            "authority": self.authority,
            "parent_promotable": self.parent_promotable,
            "normalized_sha256": self.normalized_sha256,
            "parser_version": self.parser_version,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> SpecialistPacket:
        return cls(
            source_kind=value["source_kind"],
            identity_bridge=IdentityBridge.from_dict(value["identity_bridge"]),
            facts=tuple(SpecialistFact.from_dict(item) for item in value["facts"]),
            valuation_date=value["valuation_date"],
            source_sha256=value["source_sha256"],
            authority=value.get("authority", "parent_primary"),
            parent_promotable=value.get("parent_promotable", True),
            normalized_sha256=value.get("normalized_sha256"),
            parser_version=value.get("parser_version", "FINSIGHT-SPECIALIST-PARSER-1"),
        )
