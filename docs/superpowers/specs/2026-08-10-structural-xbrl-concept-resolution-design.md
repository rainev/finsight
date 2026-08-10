# Structural XBRL Concept Resolution Design

**Date:** 2026-08-10

## Decision summary

FinSight will keep its existing SEC retrieval, Companyfacts normalization, point-in-time controls, provenance, and fail-closed publication gates. It will add an isolated Arelle-backed structural XBRL adapter for controlling filings and a FinSight-owned deterministic concept resolver. The new path will run in background ingestion and initially operate in shadow mode; it will not silently change published valuations.

EdgarTools will not become the production source of truth. It may be used later as an independent comparison tool, but FinSight must own the final mapping from source concepts to normalized financial metrics.

## Problem

The current `CompanyFactsNormalizer` resolves only configured concept names. Unqualified aliases default to the `us-gaap` namespace, so an issuer extension is reachable only when its exact namespace and concept name have already been configured.

The filing-evidence fallback is intentionally conservative and reads visible filing text. It recognizes a small set of literal balance-sheet captions, but it does not use Inline XBRL concept names, labels, documentation, contexts, dimensions, statement roles, presentation relationships, or calculation relationships. Consequently, a valid value can remain unresolved when an issuer uses a different standard concept or a company extension.

This is a concept-resolution gap, not primarily a filing-download gap.

## Goals

- Resolve economically equivalent financial-statement concepts across issuers without depending on literal captions.
- Preserve deterministic handling of common US-GAAP concepts.
- Use accounting context and XBRL structure when evaluating extensions.
- Preserve the original fact, source filing, period, unit, context, and mapping rationale.
- Fail closed when evidence is insufficient or contradictory.
- Keep extraction reproducible and point-in-time safe.
- Add the capability without replacing stable parts of the valuation pipeline.

## Non-goals

- An LLM will not parse XBRL or automatically approve financial values.
- Semantic similarity alone will not qualify a concept.
- The first increment will not replace Companyfacts historical-series extraction.
- The first increment will not migrate all valuation artifacts to a new database.
- The first increment will not automatically publish valuations recovered by the new resolver.
- EdgarTools will not be introduced as a second authoritative normalization layer.

## Alternatives considered

### Expand the alias file only

This is inexpensive and should continue for known taxonomy concepts, but it cannot scale to issuer extensions and does not use XBRL structure. It remains part of the fast path, not the complete solution.

### Make EdgarTools the primary extraction layer

EdgarTools offers a convenient SEC API and standardized statement views. That is useful for development and independent comparison, but its normalization is outside FinSight's governance and can still omit extension-only lines. Replacing the current pipeline with it would exchange known limitations for less visible ones.

### Add Arelle beneath a FinSight-owned resolver

Arelle supplies the low-level XBRL and Inline-XBRL model FinSight currently lacks: taxonomy concepts, labels, documentation, contexts, units, dimensions, statement roles, presentation networks, calculation networks, and extension taxonomies. FinSight then applies its own accounting rules. This is the selected approach because it separates parsing correctness from economic classification and keeps the decision auditable.

## Architecture

```text
SEC submissions and filing package
        |
        v
Existing SecClient and immutable cache
        |
        +---------------------> SEC Companyfacts fast path
        |                               |
        v                               v
Isolated Arelle adapter          Known concept mappings
        |                               |
        +---------------+---------------+
                        v
          FinSight deterministic resolver
                        |
                        v
          Normalized fact + mapping evidence
                        |
                        v
       Existing normalizer and valuation gates
```

The Arelle adapter will run during ingestion, not inside an interactive valuation request. Each filing accession will be parsed once and cached. The valuation engine will consume bounded normalized JSON rather than an in-memory Arelle model.

## Components

### SEC filing-package acquisition

Keep `SecClient` as the governed SEC access boundary. Extend it only as needed to cache the controlling filing's primary Inline-XBRL document and referenced taxonomy/linkbase resources. Cache entries must retain source URL, accession, retrieval timestamp, and content hash. Existing SEC fair-access limits remain authoritative.

### Arelle adapter

Add a small adapter with a strict JSON output boundary. It will extract:

- concept QName and namespace;
- standard, terse, and documentation labels when available;
- numeric value, decimals, scale, sign, and unit;
- start/end or instant period;
- accession and filing metadata;
- dimensions and members;
- statement role and presentation ancestry;
- calculation parents, children, and weights;
- extension-to-standard relationships available in the discovered taxonomy set.

Arelle must be pinned as an ingestion dependency and isolated from the application-serving process. Parser failures, missing taxonomy resources, validation errors, or unsupported documents will produce structured unresolved diagnostics rather than partial accepted values.

### FinSight concept resolver

Create a resolver independent of Arelle's Python object model. It consumes normalized candidate records and emits either an accepted mapping, a review candidate, or a rejection.

Every candidate must first pass hard gates:

- the fact belongs to the controlling filing and eligible 10-K/10-Q family;
- the fact period matches the required balance-sheet date or permitted duration;
- the unit matches the metric definition;
- the fact is at the required consolidated context, unless the metric explicitly permits dimensions;
- current/noncurrent classification does not conflict with statement position, label, or definition;
- the statement role is compatible with the requested financial metric;
- the value does not conflict with another equally supported fact.

After hard gates, deterministic evidence classes apply:

1. Exact configured concept: accept at highest confidence.
2. Governed standard-taxonomy alias: accept at high confidence.
3. Extension with strong structural support: accept only when at least two independent structural signals agree, including a compatible presentation/calculation relationship and explicit accounting classification.
4. Plausible but incomplete extension: emit a review candidate; do not enter the valuation.
5. Weak, contradictory, or label-only match: reject.

The resolver will use explicit reason codes and evidence, not opaque fuzzy similarity. A numeric confidence score will summarize deterministic evidence but will not override hard gates.

### Mapping output

Each resolution record will preserve:

```json
{
  "normalized_concept": "marketable_securities_current",
  "source_concept": "issuer:LiquidInvestmentSecurities",
  "value": 42500000,
  "unit": "USD",
  "period": "2025-12-31",
  "source_accession": "0000000000-26-000001",
  "statement_role": "balance_sheet",
  "confidence": 0.96,
  "mapping_method": "extension_structural_match",
  "reason_codes": [
    "CURRENT_ASSET_PRESENTATION_PARENT",
    "CALCULATION_CHILD_OF_CURRENT_INVESTMENTS",
    "DEFINITION_IDENTIFIES_DEBT_SECURITIES"
  ],
  "mapping_version": "US-XBRL-RESOLVER-1.0"
}
```

The human-readable reason will be derived from stable reason codes so the same evidence produces the same explanation.

## Marketable-securities policy

The resolver will distinguish at least:

- current marketable or short-term investment securities;
- noncurrent marketable or long-term investment securities;
- cash equivalents already included in cash;
- equity-method and strategic investments;
- restricted investments;
- customer or financing receivables;
- trading assets of financial institutions;
- collateral and trust assets.

A candidate will not be accepted merely because its label contains `investment`, `security`, or `marketable`. Statement position, definition, context, dimensions, and relationships must support the same economic classification. The resolver must prevent double counting when a component is already included in cash or in another accepted investment total.

## Confidence and publication policy

- Exact configured concept: target confidence `1.00`.
- Governed standard alias with all hard gates: target confidence `0.98`.
- Structurally resolved extension: maximum confidence `0.96` and requires at least two independent structural signals.
- Review candidate: confidence below the automatic-acceptance boundary or missing required structural evidence.
- Rejected candidate: failed hard gate or contradictory evidence.

Initial rollout is shadow-only. New extension mappings will be written to diagnostic artifacts but will not clear publication gates. Automatic acceptance may be enabled only after reviewed representative cases show no material false positives and all regression tests pass.

## Error handling

- Arelle unavailable: retain current Companyfacts and governed-evidence behavior.
- Filing package incomplete: record `XBRL_PACKAGE_INCOMPLETE` and remain unresolved.
- Multiple equally supported facts: record `AMBIGUOUS_FACTS` and remain unresolved.
- Unit, period, accession, or context mismatch: reject with a specific reason code.
- Presentation/calculation contradiction: remain unresolved and preserve both evidence paths.
- Parser timeout or resource limit: terminate the ingestion job safely and preserve the existing cached result.

No failure in the new path may turn a previously withheld field into an accepted zero.

## Testing strategy

Add focused tests for:

- existing standard aliases such as `ShortTermInvestments` and `AvailableForSaleSecuritiesCurrent`;
- a representative issuer extension that is a current investment asset and is structurally connected to recognized investment concepts;
- the corresponding noncurrent extension case;
- a label-similar strategic or equity-method investment that must be rejected;
- a fact with the wrong period, accession, unit, or dimensional context;
- conflicting presentation and calculation evidence;
- duplicate totals and components that could cause double counting;
- Arelle absence or parser failure preserving current behavior;
- point-in-time runs excluding facts filed after the valuation date;
- full existing US valuation and filing-evidence regression suites.

Tests will use small, checked-in representative Inline-XBRL/taxonomy fixtures. Network access will not be required for the test suite.

## Rollout

1. Add the isolated parser boundary and representative fixtures.
2. Add the deterministic resolver and reason-code schema.
3. Run shadow extraction on the withheld universe and a control set of already reliable companies.
4. Compare candidates against controlling filings and existing accepted facts.
5. Review false positives, false negatives, double-counting risks, and runtime cost.
6. Enable automatic acceptance only for evidence classes validated by the reviewed corpus.

This rollout deliberately separates improved discovery from publication authority.

## Success criteria

- Common standard concepts retain existing results.
- Company extensions can be surfaced with structural evidence without literal keyword dependence.
- No label-only candidate is automatically accepted.
- Every accepted value is traceable to an accession, context, unit, period, source concept, mapping version, and reason code.
- Existing focused and full US valuation tests do not regress.
- Shadow evaluation reports coverage gains and false-positive findings before any publication behavior changes.
