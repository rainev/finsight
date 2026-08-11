"""Deterministic, policy-driven structural resolver for XBRL facts."""

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
_RESOLVER_VERSION = "US-XBRL-RESOLVER-1.1"
_CAMEL_BOUNDARY = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
)
_GATE_PRIORITY = {
    "INELIGIBLE_FILING_FORM": 5,
    "FILING_FORM_MISMATCH": 6,
    "ACCESSION_MISMATCH": 10,
    "PERIOD_MISMATCH": 20,
    "UNIT_MISMATCH": 30,
    "EXCLUDED_ECONOMIC_CLASS": 35,
    "STATEMENT_ROLE_MISMATCH": 40,
    "DIMENSIONED_NONCONSOLIDATED_FACT": 50,
    "MISSING_NUMERIC_VALUE": 60,
    "CURRENT_NONCURRENT_CONFLICT": 70,
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


def _normalized_text(value: str) -> str:
    value = _CAMEL_BOUNDARY.sub(" ", value).replace("_", " ")
    return " ".join(
        re.sub(r"[^\w]+", " ", value.casefold().replace("-", " ")).split()
    )


def _fact_text(fact: StructuralFact) -> str:
    parts = [fact.qname, fact.local_name, fact.documentation or ""]
    parts.extend(label for _, label in fact.labels)
    parts.extend(
        value
        for pair in fact.dimensions
        for value in pair
    )
    parts.extend(fact.presentation_parents)
    parts.extend(fact.calculation_parents)
    parts.extend(fact.presentation_ancestry)
    return _normalized_text(" ".join(parts))


def _rule_strings(metric_rules: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = metric_rules.get(key, ())
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _concept_matches(fact: StructuralFact, concept: str) -> bool:
    return fact.qname == concept or fact.local_name == concept


def _configured_concept_value(
    fact: StructuralFact, metric_rules: Mapping[str, Any], key: str
) -> bool:
    return any(
        _concept_matches(fact, concept)
        for concept in _rule_strings(metric_rules, key)
    )


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
    fact: StructuralFact, metric_rules: Mapping[str, Any]
) -> str | None:
    text = _fact_text(fact)
    if any(_contains_phrase(text, phrase) for phrase in _rule_strings(metric_rules, "excluded_economic_phrases")):
        return "EXCLUDED_ECONOMIC_CLASS"
    return None


def _statement_supported(
    request: ResolutionRequest,
    fact: StructuralFact,
    metric_rules: Mapping[str, Any],
) -> bool:
    if request.statement_role != metric_rules.get("statement_role"):
        return False
    if request.statement_role in fact.statement_roles:
        return True
    if fact.statement_roles:
        return False

    parent_values = (
        set(fact.presentation_parents)
        | set(fact.calculation_parents)
        | set(fact.presentation_ancestry)
    )
    if _configured_concept_value(fact, metric_rules, "direct_statement_concepts"):
        return bool(
            parent_values
            & set(_rule_strings(metric_rules, "direct_statement_parents"))
        )
    return bool(
        parent_values & set(_rule_strings(metric_rules, "statement_support_parents"))
    )


def _dimensions_allowed(
    fact: StructuralFact, metric_rules: Mapping[str, Any]
) -> bool:
    allowed = metric_rules.get("allowed_dimensions", {})
    if not isinstance(allowed, Mapping):
        return not fact.dimensions
    combinations = allowed.get(fact.qname, allowed.get(fact.local_name, ()))
    if not isinstance(combinations, (list, tuple)):
        return not fact.dimensions
    if not fact.dimensions:
        return not (
            _configured_concept_value(fact, metric_rules, "contextual_concepts")
            and combinations
        )
    actual = tuple(sorted(fact.dimensions))
    if all(
        isinstance(pair, (list, tuple))
        and len(pair) == 2
        and all(isinstance(value, str) for value in pair)
        for pair in combinations
    ):
        return actual == tuple(sorted(tuple(pair) for pair in combinations))
    return False


def _contextual_concept_match(
    fact: StructuralFact, metric_rules: Mapping[str, Any]
) -> bool:
    return _configured_concept_value(fact, metric_rules, "contextual_concepts")


def _orientation(
    fact: StructuralFact, metric_rules: Mapping[str, Any]
) -> str | None:
    configured = metric_rules.get("orientation")
    if configured not in {"current", "noncurrent"}:
        return None

    parents = set(fact.presentation_parents) | set(fact.calculation_parents)
    parent_text = _normalized_text(" ".join(parents))
    orientations: set[str] = set()
    orientation_parts = [fact.qname, fact.local_name, fact.documentation or ""]
    orientation_parts.extend(label for _, label in fact.labels)
    orientation_parts.extend(value for pair in fact.dimensions for value in pair)
    orientation_parts.extend(fact.presentation_parents)
    orientation_parts.extend(fact.calculation_parents)
    text = _normalized_text(" ".join(orientation_parts) + " " + parent_text)

    concept_text = _normalized_text(f"{fact.qname} {fact.local_name}")
    explicit_noncurrent_concept = bool(
        re.search(r"(?:^|\s)non ?current$", concept_text)
    )
    explicit_current_concept = not explicit_noncurrent_concept and bool(
        re.search(r"(?:^|\s)current$", concept_text)
        or _contains_phrase(concept_text, "current portion")
        or _contains_phrase(concept_text, "current maturities")
    )

    noncurrent_phrases = ("noncurrent", "non current")
    if any(_contains_phrase(text, token) for token in noncurrent_phrases):
        orientations.add("noncurrent")
    elif not explicit_current_concept and _contains_phrase(text, "long term"):
        orientations.add("noncurrent")

    if explicit_noncurrent_concept:
        orientations.add("noncurrent")
    if explicit_current_concept:
        orientations.add("current")

    standalone_current_text = _remove_phrases(text, noncurrent_phrases + ("long term",))
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
    excluded_reason = _excluded_reason(fact, metric_rules)
    if excluded_reason is not None:
        return excluded_reason
    if not _statement_supported(request, fact, metric_rules):
        return "STATEMENT_ROLE_MISMATCH"
    if not _dimensions_allowed(fact, metric_rules):
        return "DIMENSIONED_NONCONSOLIDATED_FACT"
    if fact.value is None:
        return "MISSING_NUMERIC_VALUE"

    orientation = _orientation(fact, metric_rules)
    expected = metric_rules.get("orientation")
    if orientation == "conflict" or (
        expected in {"current", "noncurrent"}
        and orientation is not None
        and orientation != expected
    ):
        return "CURRENT_NONCURRENT_CONFLICT"

    return None


def _is_plausible_extension(
    fact: StructuralFact, metric_rules: Mapping[str, Any]
) -> bool:
    text = _fact_text(fact)
    extension_terms = _rule_strings(metric_rules, "extension_terms")
    term_tokens = tuple(
        token
        for phrase in extension_terms
        for token in _normalized_text(phrase).split()
        if token not in {"and", "for", "of", "the", "to"}
    )
    return _contextual_concept_match(fact, metric_rules) or any(
        _contains_phrase(text, phrase)
        for phrase in extension_terms + term_tokens
    )


def _structural_signals(
    fact: StructuralFact, metric_rules: Mapping[str, Any], expected: str
) -> tuple[bool, bool, tuple[str, ...]]:
    known_parents = set(_rule_strings(metric_rules, "structural_parents"))
    presentation = bool(set(fact.presentation_parents) & known_parents)
    calculation = bool(set(fact.calculation_parents) & known_parents)
    reason_prefix = metric_rules.get("structural_reason_prefix", "ASSET")
    if not isinstance(reason_prefix, str) or not reason_prefix:
        reason_prefix = "STRUCTURAL"
    reasons: list[str] = []
    if presentation:
        reasons.append(f"{expected.upper()}_{reason_prefix}_PRESENTATION_PARENT")
    if calculation:
        reasons.append(f"{expected.upper()}_{reason_prefix}_CALCULATION_PARENT")
    return presentation, calculation, tuple(reasons)


def _definition_signal(fact: StructuralFact, metric_rules: Mapping[str, Any]) -> bool:
    text = _fact_text(fact)
    return any(
        _contains_phrase(text, phrase)
        for phrase in _rule_strings(metric_rules, "required_definition_phrases")
    )


def _concept_reason_code(
    fact: StructuralFact, metric_rules: Mapping[str, Any]
) -> str | None:
    configured = metric_rules.get("concept_reason_codes", {})
    if not isinstance(configured, Mapping):
        return None
    for concept, reason in configured.items():
        if isinstance(concept, str) and isinstance(reason, str) and _concept_matches(fact, concept):
            return reason
    return None


def _statement_reason_code(
    request: ResolutionRequest,
    fact: StructuralFact,
    metric_rules: Mapping[str, Any],
) -> str | None:
    if request.statement_role in fact.statement_roles:
        return None
    if _statement_supported(request, fact, metric_rules):
        return "STRUCTURAL_STATEMENT_SUPPORT"
    return None


def _classify_candidate(
    fact: StructuralFact,
    request: ResolutionRequest,
    metric_rules: Mapping[str, Any],
    aliases: Mapping[str, Any],
    official_namespaces: frozenset[str],
) -> _Candidate | None:
    concepts = _concepts_for_metric(aliases, request.normalized_concept)
    alias_rank = _standard_alias_rank(fact, concepts, official_namespaces)
    component_only = _configured_concept_value(
        fact, metric_rules, "component_only_concepts"
    )
    review_only = any(
        _contains_phrase(_fact_text(fact), phrase)
        for phrase in _rule_strings(metric_rules, "review_only_phrases")
    )

    def candidate(
        *,
        status: str,
        confidence: float,
        mapping_method: str,
        reason_codes: tuple[str, ...],
    ) -> _Candidate:
        reasons = list(reason_codes)
        statement_reason = _statement_reason_code(request, fact, metric_rules)
        if statement_reason is not None:
            reasons.append(statement_reason)
        concept_reason = _concept_reason_code(fact, metric_rules)
        if concept_reason is not None:
            reasons.append(concept_reason)
        return _Candidate(
            fact,
            status,
            confidence,
            mapping_method,
            tuple(dict.fromkeys(reasons)),
        )

    if alias_rank is not None:
        if component_only:
            return candidate(
                status="review",
                confidence=0.75,
                mapping_method="component_only_concept",
                reason_codes=("COMPONENT_ONLY_CONCEPT",),
            )
        if review_only:
            return candidate(
                status="review",
                confidence=0.75,
                mapping_method="review_only_accounting_context",
                reason_codes=("REVIEW_ONLY_ACCOUNTING_CONTEXT",),
            )
        if alias_rank == 0:
            return candidate(
                status="accepted",
                confidence=1.00,
                mapping_method="exact_configured_concept",
                reason_codes=("EXACT_CONFIGURED_CONCEPT",),
            )
        return candidate(
            status="accepted",
            confidence=0.98,
            mapping_method="known_taxonomy_alias",
            reason_codes=("KNOWN_TAXONOMY_ALIAS",),
        )

    if not _is_plausible_extension(fact, metric_rules):
        return None

    if _contextual_concept_match(fact, metric_rules):
        if review_only:
            return candidate(
                status="review",
                confidence=0.75,
                mapping_method="review_only_accounting_context",
                reason_codes=("REVIEW_ONLY_ACCOUNTING_CONTEXT",),
            )
        return candidate(
            status="accepted",
            confidence=0.96,
            mapping_method="taxonomy_and_context",
            reason_codes=("GOVERNED_DIMENSIONAL_CONTEXT",),
        )

    expected = metric_rules.get("orientation", "none")
    presentation, calculation, signal_reasons = _structural_signals(
        fact, metric_rules, expected
    )
    definition = _definition_signal(fact, metric_rules)
    if definition and presentation and calculation:
        if review_only:
            return candidate(
                status="review",
                confidence=0.75,
                mapping_method="review_only_accounting_context",
                reason_codes=("REVIEW_ONLY_ACCOUNTING_CONTEXT",),
            )
        return candidate(
            status="accepted",
            confidence=0.96,
            mapping_method="extension_structural_match",
            reason_codes=signal_reasons + ("DEFINITION_IDENTIFIES_MARKETABLE_SECURITIES",),
        )
    return candidate(
        status="review",
        confidence=0.75,
        mapping_method="insufficient_structural_support",
        reason_codes=("INSUFFICIENT_STRUCTURAL_SUPPORT",),
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
        gate_reason = _hard_gate_reason(request, fact, metric_rules)
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
    if len({candidate.fact.value for candidate in highest_rank}) > 1:
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
