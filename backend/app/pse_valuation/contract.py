"""Public PSE V2 artifact contract and fail-closed semantic validation."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from . import MODEL_VERSION, SCHEMA_VERSION


AvailabilityType = Literal["intrinsic_valuation", "market_relative_only", "not_available"]
PublicationState = Literal["approved", "provisional", "blocked"]
ScenarioName = Literal["bear", "base", "bull"]


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


class ScenarioValue(BaseModel):
    value_per_share: float
    common_equity_value: float
    enterprise_value: float | None = None


class SourceReference(BaseModel):
    document_id: str
    label: str
    form: str | None = None
    period_end: str | None = None
    published_at: str | None = None
    url: str | None = None
    source_page: int | None = None
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PseValuationArtifact(BaseModel):
    schema_version: str = SCHEMA_VERSION
    model_version: str = MODEL_VERSION
    market: Literal["PH"] = "PH"
    currency: str = "PHP"
    ticker: str
    issuer: dict[str, Any]
    security: dict[str, Any]
    subsector: str
    primary_model: str
    valuation_date: date
    filing_period: str | None = None
    filing_published_at: str | None = None
    price: dict[str, Any] | None = None
    availability_type: AvailabilityType
    publication_state: PublicationState
    scenarios: dict[ScenarioName, ScenarioValue | None]
    numerical_range: dict[str, float | None]
    market_relative: dict[str, Any] | None = None
    public_assumptions: dict[str, Any] = Field(default_factory=dict)
    sensitivities: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[SourceReference]
    warnings: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    data_boundary: dict[str, Any] = Field(
        default_factory=lambda: {
            "reported_facts_public": False,
            "source_references_public": True,
            "derived_outputs_public": True,
        }
    )

    @model_validator(mode="after")
    def validate_publication_semantics(self) -> "PseValuationArtifact":
        names = {"bear", "base", "bull"}
        if set(self.scenarios) != names:
            raise ValueError("scenarios must contain bear, base, and bull exactly")
        values = [row.value_per_share for row in self.scenarios.values() if row is not None]
        low = self.numerical_range.get("low")
        high = self.numerical_range.get("high")

        if self.publication_state == "blocked":
            if self.availability_type != "not_available":
                raise ValueError("blocked artifacts must be not_available")
            if values or low is not None or high is not None:
                raise ValueError("blocked artifacts must expose null valuation values")
            if not self.blocking_reasons:
                raise ValueError("blocked artifacts require blocking reasons")
        elif self.availability_type == "intrinsic_valuation":
            if len(values) != 3:
                raise ValueError("intrinsic valuations require all three scenario values")
            if low != min(values) or high != max(values):
                raise ValueError("numerical range must be derived from scenario values")
        elif self.availability_type == "market_relative_only":
            if values:
                raise ValueError("market-relative artifacts must not expose intrinsic scenarios")
            if not self.market_relative:
                raise ValueError("market-relative artifacts require a separate estimate")
            estimates = self.market_relative.get("estimates")
            if not isinstance(estimates, dict) or set(estimates) != {"low", "base", "high"}:
                raise ValueError("market-relative artifacts require low/base/high estimates")
            relative_values = [estimates[name] for name in ("low", "base", "high")]
            if any(not isinstance(value, (int, float)) for value in relative_values):
                raise ValueError("market-relative estimates must be numeric")
            if low != min(relative_values) or high != max(relative_values):
                raise ValueError("numerical range must be derived from market-relative estimates")
        return self

    def with_artifact_hash(self) -> "PseValuationArtifact":
        payload = self.model_dump(mode="json")
        payload["artifact_hash"] = None
        return self.model_copy(update={"artifact_hash": sha256_object(payload)})

    def verify_artifact_hash(self) -> bool:
        if not self.artifact_hash:
            return False
        payload = self.model_dump(mode="json")
        expected = payload.pop("artifact_hash")
        payload["artifact_hash"] = None
        return sha256_object(payload) == expected


def blocked_artifact(
    *,
    ticker: str,
    issuer_name: str,
    subsector: str,
    primary_model: str,
    valuation_date: date,
    sources: list[dict[str, Any]],
    blocking_reasons: list[str],
    input_snapshot: dict[str, Any],
) -> PseValuationArtifact:
    return PseValuationArtifact(
        ticker=ticker,
        issuer={"issuer_id": ticker, "name": issuer_name},
        security={"security_id": f"PSE:{ticker}:COMMON", "type": "ordinary_common"},
        subsector=subsector,
        primary_model=primary_model,
        valuation_date=valuation_date,
        availability_type="not_available",
        publication_state="blocked",
        scenarios={"bear": None, "base": None, "bull": None},
        numerical_range={"low": None, "high": None},
        sources=sources,
        blocking_reasons=blocking_reasons,
        input_hash=sha256_object(input_snapshot),
    ).with_artifact_hash()
