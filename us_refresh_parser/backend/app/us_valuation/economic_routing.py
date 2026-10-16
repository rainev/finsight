"""Private economic-profile and valuation-model governance contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from importlib.resources import files
import re
from typing import Any, Literal, Mapping


BusinessType = Literal["operating", "financial", "regulated", "asset_based", "mixed"]
Lifecycle = Literal["mature", "growth", "pre_profit", "declining", "turnaround"]
ModelMaturity = Literal["experimental", "provisional", "validated"]
ReliabilityCap = Literal["Withhold", "Low", "Medium", "High"]
RoutingStatus = Literal["hypothesis", "selected", "rejected"]

_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_MODEL_MATURITIES = frozenset({"experimental", "provisional", "validated"})
_RELIABILITY_CAPS = frozenset({"Withhold", "Low", "Medium", "High"})
_ROUTING_STATUSES = frozenset({"hypothesis", "selected", "rejected"})


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _strings(value: object, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list or tuple")
    result = tuple(_text(item, field) for item in value)
    if not allow_empty and not result:
        raise ValueError(f"{field} must not be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{field} must not contain duplicates")
    return result


def _bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _accessions(value: object, field: str) -> tuple[str, ...]:
    result = _strings(value, field)
    if any(not _ACCESSION.fullmatch(item) for item in result):
        raise ValueError(f"{field} contains an invalid SEC accession")
    return result


@dataclass(frozen=True)
class RejectedModel:
    model_family: str
    reason: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RejectedModel":
        if not isinstance(value, Mapping):
            raise ValueError("rejected model must be an object")
        return cls(
            model_family=_text(value.get("model_family"), "model_family"),
            reason=_text(value.get("reason"), "reason"),
        )


@dataclass(frozen=True)
class EconomicProfile:
    business_type: BusinessType
    material_segments: tuple[str, ...]
    lifecycle: Lifecycle
    cyclical_exposure: bool
    commodity_exposure: bool
    regulatory_capital_dependence: bool
    captive_finance_activity: bool
    property_or_reserve_assets: bool
    primary_model_candidate: str
    secondary_model_candidates: tuple[str, ...]
    routing_explanation: str
    source_accessions: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EconomicProfile":
        if not isinstance(value, Mapping):
            raise ValueError("economic_profile must be an object")
        business_type = value.get("business_type")
        if business_type not in {"operating", "financial", "regulated", "asset_based", "mixed"}:
            raise ValueError("business_type is invalid")
        lifecycle = value.get("lifecycle")
        if lifecycle not in {"mature", "growth", "pre_profit", "declining", "turnaround"}:
            raise ValueError("lifecycle is invalid")
        primary = _text(value.get("primary_model_candidate"), "primary_model_candidate")
        secondary = _strings(
            value.get("secondary_model_candidates", []),
            "secondary_model_candidates",
            allow_empty=True,
        )
        if primary in secondary:
            raise ValueError("primary model candidate cannot also be secondary")
        return cls(
            business_type=business_type,
            material_segments=_strings(value.get("material_segments"), "material_segments"),
            lifecycle=lifecycle,
            cyclical_exposure=_bool(value.get("cyclical_exposure"), "cyclical_exposure"),
            commodity_exposure=_bool(value.get("commodity_exposure"), "commodity_exposure"),
            regulatory_capital_dependence=_bool(
                value.get("regulatory_capital_dependence"),
                "regulatory_capital_dependence",
            ),
            captive_finance_activity=_bool(
                value.get("captive_finance_activity"), "captive_finance_activity"
            ),
            property_or_reserve_assets=_bool(
                value.get("property_or_reserve_assets"), "property_or_reserve_assets"
            ),
            primary_model_candidate=primary,
            secondary_model_candidates=secondary,
            routing_explanation=_text(
                value.get("routing_explanation"), "routing_explanation"
            ),
            source_accessions=_accessions(
                value.get("source_accessions"), "source_accessions"
            ),
        )


@dataclass(frozen=True)
class ModelDecision:
    economic_lane: str
    model_family: str
    model_version: str
    required_inputs: tuple[str, ...]
    rejected_models: tuple[RejectedModel, ...]
    maturity: ModelMaturity
    reliability_cap: ReliabilityCap
    source_accessions: tuple[str, ...]
    routing_status: RoutingStatus
    decision_reason: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelDecision":
        if not isinstance(value, Mapping):
            raise ValueError("model_decision must be an object")
        maturity = value.get("maturity")
        cap = value.get("reliability_cap")
        status = value.get("routing_status")
        if maturity not in _MODEL_MATURITIES:
            raise ValueError("maturity is invalid")
        if cap not in _RELIABILITY_CAPS:
            raise ValueError("reliability_cap is invalid")
        if status not in _ROUTING_STATUSES:
            raise ValueError("routing_status is invalid")
        if maturity == "experimental" and cap != "Withhold":
            raise ValueError("experimental models must be withheld")
        if maturity == "provisional" and cap not in {"Withhold", "Low"}:
            raise ValueError("provisional models may be capped only at Low or Withhold")
        if status == "hypothesis" and cap != "Withhold":
            raise ValueError("unconfirmed routing hypotheses must be withheld")
        if status == "selected" and maturity == "experimental":
            raise ValueError("experimental models cannot be selected for publication")
        raw_rejected = value.get("rejected_models")
        if not isinstance(raw_rejected, list) or not raw_rejected:
            raise ValueError("rejected_models must be a non-empty list")
        rejected = tuple(RejectedModel.from_dict(item) for item in raw_rejected)
        model_family = _text(value.get("model_family"), "model_family")
        if any(item.model_family == model_family for item in rejected):
            raise ValueError("selected model family cannot also be rejected")
        if len({item.model_family for item in rejected}) != len(rejected):
            raise ValueError("rejected model families must be unique")
        return cls(
            economic_lane=_text(value.get("economic_lane"), "economic_lane"),
            model_family=model_family,
            model_version=_text(value.get("model_version"), "model_version"),
            required_inputs=_strings(value.get("required_inputs"), "required_inputs"),
            rejected_models=rejected,
            maturity=maturity,
            reliability_cap=cap,
            source_accessions=_accessions(
                value.get("source_accessions"), "source_accessions"
            ),
            routing_status=status,
            decision_reason=_text(value.get("decision_reason"), "decision_reason"),
        )


@dataclass(frozen=True)
class EconomicRoutingRecord:
    ticker: str
    economic_profile: EconomicProfile
    model_decision: ModelDecision

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EconomicRoutingRecord":
        if not isinstance(value, Mapping):
            raise ValueError("routing record must be an object")
        ticker = _text(value.get("ticker"), "ticker")
        profile = EconomicProfile.from_dict(value.get("economic_profile"))
        decision = ModelDecision.from_dict(value.get("model_decision"))
        if decision.model_family != profile.primary_model_candidate:
            raise ValueError("model decision must match the profile's primary candidate")
        if not set(decision.source_accessions).issubset(profile.source_accessions):
            raise ValueError("model-decision accessions must be present in the economic profile")
        return cls(ticker=ticker, economic_profile=profile, model_decision=decision)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_batch_01_routing_records() -> tuple[EconomicRoutingRecord, ...]:
    path = files(__package__).joinpath("config/batch_01_economic_routing.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("version") != "US-ECONOMIC-ROUTING-1.1":
        raise ValueError("Batch 01 routing policy version is invalid")
    records = raw.get("records")
    if not isinstance(records, list):
        raise ValueError("Batch 01 routing records must be a list")
    parsed = tuple(EconomicRoutingRecord.from_dict(item) for item in records)
    tickers = tuple(item.ticker for item in parsed)
    if len(set(tickers)) != len(tickers):
        raise ValueError("Batch 01 routing records contain duplicate tickers")
    return parsed
