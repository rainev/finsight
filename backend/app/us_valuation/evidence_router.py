"""Model-route guard for specialist official evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any


_ALLOWED = {
    "bank_residual_income": {"residual_income"},
    "regulated_utility": {"ddm", "regulated_utility_sotp"},
    "reit": {"ffo", "affo", "reit_nav"},
}
_SOURCE_FAMILIES = {
    "fr_y9c": {"bank_residual_income"},
    "ffiec_call_report": {"bank_residual_income"},
    "ferc_form_1": {"regulated_utility"},
    "ferc_form_3q": {"regulated_utility"},
    "sec_filed_exhibit_99_2": {"reit"},
}


@dataclass(frozen=True)
class EvidenceModelRoute:
    family: str
    model: str
    source_kind: str


def route_evidence_model(
    route: Mapping[str, Any], *, source_kind: str
) -> EvidenceModelRoute:
    family = route.get("family")
    model = route.get("model")
    if not isinstance(family, str) or not isinstance(model, str):
        raise ValueError("evidence model route needs family and model")
    if family not in _SOURCE_FAMILIES.get(source_kind, set()):
        raise ValueError("specialist source is incompatible with the declared model family")
    if model not in _ALLOWED.get(family, set()):
        raise ValueError("specialist evidence cannot authorize an unsuitable model")
    return EvidenceModelRoute(family=family, model=model, source_kind=source_kind)
