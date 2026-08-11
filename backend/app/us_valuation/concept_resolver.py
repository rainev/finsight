"""Deterministic structural resolver for marketable-securities XBRL facts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .structural_xbrl import (
    ELIGIBLE_FILING_FORMS,
    ResolutionDecision,
    ResolutionEvidence,
    ResolutionRequest,
    StructuralFact,
)


_CONFIG_DIR = Path(__file__).with_name("config")
_RULES_PATH = _CONFIG_DIR / "structural_concept_rules.json"
_ALIASES_PATH = _CONFIG_DIR / "concept_aliases.json"
_RESOLVER_VERSION = "US-XBRL-RESOLVER-1.0"
_CAMEL_BOUNDARY = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
)
_GATE_PRIORITY = {
    "INELIGIBLE_FILING_FORM": 5,
    "FILING_FORM_MISMATCH": 6,
    "ACCESSION_MISMATCH": 10,
    "PERIOD_MISMATCH": 20,
    "UNIT_MISMATCH": 30,
    "STATEMENT_ROLE_MISMATCH": 40,
    "DIMENSIONED_NONCONSOLIDATED_FACT": 50,
    "MISSING_NUMERIC_VALUE": 60,
    "CURRENT_NONCURRENT_CONFLICT": 70,
    "EXCLUDED_ECONOMIC_CLASS": 80,
}


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
    namespaces = rules.get("official_us_gaap_namespaces")
    if (
        not isinstance(namespaces, list)
        or not namespaces
        or any(not isinstance(namespace, str) or not namespace for namespace in namespaces)
        or len(namespaces) != len(set(namespaces))
    ):
        raise ValueError("structural concept rules must contain a unique namespace allowlist")
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


def _standard_alias_rank(
    fact: StructuralFact,
    concepts: tuple[str, ...],
    official_namespaces: frozenset[str],
) -> int | None:
    if fact.namespace not in official_namespaces:
        return None
    for index, concept in enumerate(concepts):
        if fact.qname == f"us-gaap:{concept}" and fact.local_name == concept:
            return index
    return None


def _standard_metric_for_fact(
    fact: StructuralFact,
    aliases: Mapping[str, Any],
    official_namespaces: frozenset[str],
) -> str | None:
    for concept in ("marketable_securities_current", "marketable_securities_noncurrent"):
        if (
            _standard_alias_rank(
                fact,
                _concepts_for_metric(aliases, concept),
                official_namespaces,
            )
            is not None
        ):
            return concept
    return None


def _normalized_text(value: str) -> str:
    value = _CAMEL_BOUNDARY.sub(" ", value).replace("_", " ")
    return " ".join(
        re.sub(r"[^\w]+", " ", value.casefold().replace("-", " ")).split()
    )


def _fact_text(fact: StructuralFact) -> str:
    parts = [fact.qname, fact.local_name, fact.documentation or ""]
    parts.extend(label for _, label in fact.labels)
    return _normalized_text(" ".join(parts))


def _phrase_pattern(phrase: str) -> str:
    normalized_phrase = _normalized_text(phrase)
    suffix = "s?" if len(normalized_phrase.split()) == 1 else ""
    return rf"(?<!\w){re.escape(normalized_phrase)}{suffix}(?!\w)"


def _contains_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(_phrase_pattern(phrase), text))


def _remove_phrases(text: str, phrases: tuple[str, ...]) -> str:
    for phrase in phrases:
        text = re.sub(_phrase_pattern(phrase), " ", text)
    return text


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
    rules: Mapping[str, Any],
    aliases: Mapping[str, Any],
) -> str | None:
    current_rules = rules.get("marketable_securities_current", {})
    noncurrent_rules = rules.get("marketable_securities_noncurrent", {})
    current_parents = set(
        current_rules.get("known_current_parents", ())
        if isinstance(current_rules, Mapping)
        else ()
    )
    noncurrent_parents = set(
        noncurrent_rules.get("known_noncurrent_parents", ())
        if isinstance(noncurrent_rules, Mapping)
        else ()
    )
    parents = set(fact.presentation_parents) | set(fact.calculation_parents)
    orientations: set[str] = set()
    if parents & current_parents:
        orientations.add("current")
    if parents & noncurrent_parents:
        orientations.add("noncurrent")

    official_namespaces = frozenset(rules["official_us_gaap_namespaces"])
    standard_metric = _standard_metric_for_fact(fact, aliases, official_namespaces)
    if standard_metric is not None:
        orientations.add("current" if standard_metric.endswith("_current") else "noncurrent")

    text = _fact_text(fact)
    noncurrent_phrases = ("noncurrent", "non current", "long term")
    if any(_contains_phrase(text, token) for token in noncurrent_phrases):
        orientations.add("noncurrent")
    standalone_current_text = _remove_phrases(text, noncurrent_phrases)
    if any(
        _contains_phrase(standalone_current_text, token)
        for token in ("current", "short term")
    ):
        orientations.add("current")
    if len(orientations) > 1:
        return "conflict"
    if orientations:
        return next(iter(orientations))
    return None


def _hard_gate_reason(
    request: ResolutionRequest,
    fact: StructuralFact,
    metric_rules: Mapping[str, Any],
    rules: Mapping[str, Any],
    aliases: Mapping[str, Any],
) -> str | None:
    if fact.filing_form not in ELIGIBLE_FILING_FORMS:
        return "INELIGIBLE_FILING_FORM"
    if fact.filing_form != request.form:
        return "FILING_FORM_MISMATCH"
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
    if fact.value is None:
        return "MISSING_NUMERIC_VALUE"

    orientation = _orientation(fact, rules, aliases)
    expected = "current" if request.normalized_concept.endswith("_current") else "noncurrent"
    if orientation == "conflict" or (
        orientation is not None and orientation != expected
    ):
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
    official_namespaces: frozenset[str],
) -> _Candidate | None:
    concepts = _concepts_for_metric(aliases, request.normalized_concept)
    alias_rank = _standard_alias_rank(fact, concepts, official_namespaces)
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
    evidence = None
    if fact is not None and status in {"accepted", "review"}:
        evidence = ResolutionEvidence.from_fact(
            fact,
            mapping_version=_RESOLVER_VERSION,
            confidence=confidence,
            reason_codes=reason_codes,
        )
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
        form=request.form,
        evidence=evidence,
        mapping_version=_RESOLVER_VERSION,
    )


def _gate_failure_sort_key(
    failure: tuple[StructuralFact, str],
) -> tuple[int, str, str, str, str, str]:
    fact, reason = failure
    return (
        _GATE_PRIORITY.get(reason, 999),
        fact.qname,
        fact.source_accession,
        fact.period_end,
        fact.unit,
        fact.context_id,
    )


def _component_total_conflict(left: StructuralFact, right: StructuralFact) -> bool:
    return bool(
        right.qname in left.calculation_children
        or left.qname in right.calculation_children
        or right.qname in left.calculation_parents
        or left.qname in right.calculation_parents
    )


def _fact_identity(fact: StructuralFact) -> tuple[object, ...]:
    """Identity used to collapse exact duplicate XBRL facts before ambiguity."""

    return (
        fact.qname,
        fact.context_id,
        fact.unit,
        fact.period_start,
        fact.period_end,
        fact.value,
    )


def _candidate_sort_key(candidate: _Candidate) -> tuple[float, str, str, str]:
    return (
        -candidate.confidence,
        candidate.fact.qname,
        candidate.fact.context_id,
        candidate.fact.source_accession,
    )


def resolve_concept(
    request: ResolutionRequest, facts: Iterable[StructuralFact]
) -> ResolutionDecision:
    """Resolve one normalized marketable-securities metric without semantic scoring."""

    rules = load_structural_rules()
    aliases = _load_aliases()
    if request.form not in ELIGIBLE_FILING_FORMS:
        return _decision(
            request,
            fact=None,
            status="unresolved",
            confidence=0.0,
            mapping_method="ineligible_filing_form",
            reason_codes=("INELIGIBLE_FILING_FORM",),
        )
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
    official_namespaces = frozenset(rules["official_us_gaap_namespaces"])
    material_facts = tuple(facts)
    for fact in material_facts:
        candidate = _classify_candidate(
            fact,
            request,
            metric_rules,
            aliases,
            official_namespaces,
        )
        if candidate is None:
            continue
        gate_reason = _hard_gate_reason(request, fact, metric_rules, rules, aliases)
        if gate_reason is not None:
            gate_failures.append((fact, gate_reason))
        else:
            candidates.append(candidate)

    if not candidates:
        if gate_failures:
            fact, reason = sorted(gate_failures, key=_gate_failure_sort_key)[0]
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

    deduplicated: dict[tuple[object, ...], _Candidate] = {}
    for candidate in sorted(candidates, key=_candidate_sort_key):
        deduplicated.setdefault(_fact_identity(candidate.fact), candidate)
    ordered = sorted(deduplicated.values(), key=_candidate_sort_key)
    if any(
        _component_total_conflict(left.fact, right.fact)
        for index, left in enumerate(ordered)
        for right in ordered[index + 1 :]
    ):
        first = ordered[0].fact
        return _decision(
            request,
            fact=first,
            status="rejected",
            confidence=0.0,
            mapping_method="hard_gate_rejection",
            reason_codes=("COMPONENT_TOTAL_CONFLICT",),
        )
    highest_confidence = ordered[0].confidence
    highest_rank = tuple(
        candidate for candidate in ordered if candidate.confidence == highest_confidence
    )
    if len(highest_rank) > 1:
        return _decision(
            request,
            fact=highest_rank[0].fact,
            status="rejected",
            confidence=0.0,
            mapping_method="hard_gate_rejection",
            reason_codes=("AMBIGUOUS_FACTS",),
        )
    selected = highest_rank[0]

    return _decision(
        request,
        fact=selected.fact,
        status=selected.status,
        confidence=selected.confidence,
        mapping_method=selected.mapping_method,
        reason_codes=selected.reason_codes,
        value=selected.fact.value,
    )
