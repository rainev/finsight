"""Deterministic structural resolver for marketable-securities XBRL facts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .structural_xbrl import ResolutionDecision, ResolutionRequest, StructuralFact


_CONFIG_DIR = Path(__file__).with_name("config")
_RULES_PATH = _CONFIG_DIR / "structural_concept_rules.json"
_ALIASES_PATH = _CONFIG_DIR / "concept_aliases.json"
_RESOLVER_VERSION = "US-XBRL-RESOLVER-1.0"


@dataclass(frozen=True)
class _Candidate:
    fact: StructuralFact
    status: str
    confidence: float
    mapping_method: str
    reason_codes: tuple[str, ...]


def load_structural_rules() -> dict[str, Any]:
    """Load the checked-in accounting rules used by the resolver."""

    with _RULES_PATH.open(encoding="utf-8") as handle:
        rules = json.load(handle)
    if not isinstance(rules, dict) or rules.get("version") != _RESOLVER_VERSION:
        raise ValueError("structural concept rules have an unsupported version")
    return rules


def _load_aliases() -> dict[str, Any]:
    with _ALIASES_PATH.open(encoding="utf-8") as handle:
        aliases = json.load(handle)
    if not isinstance(aliases, dict) or not isinstance(aliases.get("fields"), dict):
        raise ValueError("concept aliases must contain fields")
    return aliases


def _metric_rules(rules: Mapping[str, Any], concept: str) -> Mapping[str, Any] | None:
    value = rules.get(concept)
    return value if isinstance(value, Mapping) else None


def _concepts_for_metric(aliases: Mapping[str, Any], concept: str) -> tuple[str, ...]:
    fields = aliases.get("fields", {})
    field = fields.get(concept, {}) if isinstance(fields, Mapping) else {}
    concepts = field.get("concepts", ()) if isinstance(field, Mapping) else ()
    if not isinstance(concepts, list) or not all(isinstance(item, str) for item in concepts):
        raise ValueError(f"concept aliases for {concept} must be a list of strings")
    return tuple(concepts)


def _standard_alias_rank(fact: StructuralFact, concepts: tuple[str, ...]) -> int | None:
    for index, concept in enumerate(concepts):
        if fact.qname == concept or fact.qname == f"us-gaap:{concept}":
            return index
        if fact.namespace.casefold().find("us-gaap") >= 0 and fact.local_name == concept:
            return index
    return None


def _standard_metric_for_fact(
    fact: StructuralFact, aliases: Mapping[str, Any]
) -> str | None:
    for concept in ("marketable_securities_current", "marketable_securities_noncurrent"):
        if _standard_alias_rank(fact, _concepts_for_metric(aliases, concept)) is not None:
            return concept
    return None


def _normalized_text(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def _fact_text(fact: StructuralFact) -> str:
    parts = [fact.qname, fact.local_name, fact.documentation or ""]
    parts.extend(label for _, label in fact.labels)
    return _normalized_text(" ".join(parts))


def _contains_phrase(text: str, phrase: str) -> bool:
    return _normalized_text(phrase) in text


def _excluded_reason(
    fact: StructuralFact, rules: Mapping[str, Any]
) -> str | None:
    text = _fact_text(fact)
    phrases = rules.get("excluded_economic_phrases", ())
    if isinstance(phrases, list) and any(
        isinstance(phrase, str) and _contains_phrase(text, phrase) for phrase in phrases
    ):
        return "EXCLUDED_ECONOMIC_CLASS"
    return None


def _orientation(
    fact: StructuralFact,
    metric_rules: Mapping[str, Any],
    aliases: Mapping[str, Any],
) -> str | None:
    standard_metric = _standard_metric_for_fact(fact, aliases)
    if standard_metric is not None:
        return "current" if standard_metric.endswith("_current") else "noncurrent"

    current_parents = set(metric_rules.get("known_current_parents", ()))
    noncurrent_parents = set(metric_rules.get("known_noncurrent_parents", ()))
    parents = set(fact.presentation_parents) | set(fact.calculation_parents)
    if parents & noncurrent_parents:
        return "noncurrent"
    if parents & current_parents:
        return "current"

    text = _fact_text(fact)
    if any(token in text for token in ("noncurrent", "non current", "long term")):
        return "noncurrent"
    if any(token in text for token in ("current", "short term")):
        return "current"
    return None


def _hard_gate_reason(
    request: ResolutionRequest,
    fact: StructuralFact,
    metric_rules: Mapping[str, Any],
    rules: Mapping[str, Any],
    aliases: Mapping[str, Any],
) -> str | None:
    if fact.source_accession != request.source_accession:
        return "ACCESSION_MISMATCH"
    if fact.period_end != request.period_end:
        return "PERIOD_MISMATCH"
    if fact.unit != request.unit or fact.unit != metric_rules.get("unit"):
        return "UNIT_MISMATCH"
    if request.statement_role != metric_rules.get("statement_role"):
        return "STATEMENT_ROLE_MISMATCH"
    if request.statement_role not in fact.statement_roles:
        return "STATEMENT_ROLE_MISMATCH"
    if fact.dimensions:
        return "DIMENSIONED_NONCONSOLIDATED_FACT"

    orientation = _orientation(fact, metric_rules, aliases)
    expected = "current" if request.normalized_concept.endswith("_current") else "noncurrent"
    if orientation is not None and orientation != expected:
        return "CURRENT_NONCURRENT_CONFLICT"

    return _excluded_reason(fact, rules)


def _is_plausible_extension(fact: StructuralFact) -> bool:
    text = _fact_text(fact)
    return any(
        _contains_phrase(text, phrase)
        for phrase in (
            "marketable",
            "investment",
            "securities",
            "available for sale",
            "debt securities",
        )
    )


def _structural_signals(
    fact: StructuralFact, metric_rules: Mapping[str, Any], expected: str
) -> tuple[bool, bool, tuple[str, ...]]:
    parent_key = f"known_{expected}_parents"
    known_parents = set(metric_rules.get(parent_key, ()))
    presentation = bool(set(fact.presentation_parents) & known_parents)
    calculation = bool(set(fact.calculation_parents) & known_parents)
    reasons: list[str] = []
    if presentation:
        reasons.append(f"{expected.upper()}_ASSET_PRESENTATION_PARENT")
    if calculation:
        reasons.append(f"{expected.upper()}_ASSET_CALCULATION_PARENT")
    return presentation, calculation, tuple(reasons)


def _definition_signal(fact: StructuralFact, metric_rules: Mapping[str, Any]) -> bool:
    documentation = _normalized_text(fact.documentation or "")
    phrases = metric_rules.get("required_definition_phrases", ())
    return isinstance(phrases, list) and any(
        isinstance(phrase, str) and _contains_phrase(documentation, phrase)
        for phrase in phrases
    )


def _classify_candidate(
    fact: StructuralFact,
    request: ResolutionRequest,
    metric_rules: Mapping[str, Any],
    aliases: Mapping[str, Any],
) -> _Candidate | None:
    concepts = _concepts_for_metric(aliases, request.normalized_concept)
    alias_rank = _standard_alias_rank(fact, concepts)
    if alias_rank is not None:
        if alias_rank == 0:
            return _Candidate(
                fact,
                "accepted",
                1.00,
                "exact_configured_concept",
                ("EXACT_CONFIGURED_CONCEPT",),
            )
        return _Candidate(
            fact,
            "accepted",
            0.98,
            "known_taxonomy_alias",
            ("KNOWN_TAXONOMY_ALIAS",),
        )

    if not _is_plausible_extension(fact):
        return None

    expected = "current" if request.normalized_concept.endswith("_current") else "noncurrent"
    presentation, calculation, signal_reasons = _structural_signals(
        fact, metric_rules, expected
    )
    definition = _definition_signal(fact, metric_rules)
    if definition and presentation and calculation:
        return _Candidate(
            fact,
            "accepted",
            0.96,
            "extension_structural_match",
            signal_reasons + ("DEFINITION_IDENTIFIES_MARKETABLE_SECURITIES",),
        )
    return _Candidate(
        fact,
        "review",
        0.75,
        "insufficient_structural_support",
        ("INSUFFICIENT_STRUCTURAL_SUPPORT",),
    )


def _decision(
    request: ResolutionRequest,
    *,
    fact: StructuralFact | None,
    status: str,
    confidence: float,
    mapping_method: str,
    reason_codes: tuple[str, ...],
    value: float | None = None,
) -> ResolutionDecision:
    return ResolutionDecision(
        status=status,  # type: ignore[arg-type]
        normalized_concept=request.normalized_concept,
        source_concept=fact.qname if fact is not None else None,
        value=value if status in {"accepted", "review"} else None,
        unit=fact.unit if fact is not None else None,
        period=fact.period_end if fact is not None else request.period_end,
        source_accession=fact.source_accession if fact is not None else request.source_accession,
        confidence=confidence,
        mapping_method=mapping_method,
        reason_codes=reason_codes,
        mapping_version=_RESOLVER_VERSION,
    )


def resolve_concept(
    request: ResolutionRequest, facts: Iterable[StructuralFact]
) -> ResolutionDecision:
    """Resolve one normalized marketable-securities metric without semantic scoring."""

    rules = load_structural_rules()
    aliases = _load_aliases()
    metric_rules = _metric_rules(rules, request.normalized_concept)
    if metric_rules is None:
        return _decision(
            request,
            fact=None,
            status="unresolved",
            confidence=0.0,
            mapping_method="no_candidate",
            reason_codes=("NO_CANDIDATE",),
        )

    candidates: list[_Candidate] = []
    gate_failures: list[tuple[StructuralFact, str]] = []
    material_facts = tuple(facts)
    for fact in material_facts:
        candidate = _classify_candidate(fact, request, metric_rules, aliases)
        if candidate is None:
            continue
        gate_reason = _hard_gate_reason(request, fact, metric_rules, rules, aliases)
        if gate_reason is not None:
            gate_failures.append((fact, gate_reason))
        else:
            candidates.append(candidate)

    if not candidates:
        if gate_failures:
            fact, reason = sorted(
                gate_failures,
                key=lambda item: (item[0].qname, item[0].source_accession),
            )[0]
            return _decision(
                request,
                fact=fact,
                status="rejected",
                confidence=0.0,
                mapping_method="hard_gate_rejection",
                reason_codes=(reason,),
            )
        return _decision(
            request,
            fact=None,
            status="unresolved",
            confidence=0.0,
            mapping_method="no_candidate",
            reason_codes=("NO_CANDIDATE",),
        )

    ordered = sorted(candidates, key=lambda item: (item.fact.qname, item.fact.source_accession))
    if len(ordered) > 1:
        first = ordered[0].fact
        return _decision(
            request,
            fact=first,
            status="rejected",
            confidence=0.0,
            mapping_method="hard_gate_rejection",
            reason_codes=("AMBIGUOUS_FACTS",),
        )
    selected = ordered[0]

    return _decision(
        request,
        fact=selected.fact,
        status=selected.status,
        confidence=selected.confidence,
        mapping_method=selected.mapping_method,
        reason_codes=selected.reason_codes,
        value=selected.fact.value,
    )
