# Audit 25 — FOD2 governed semantics and validation result

Status: **verified — FOD3 may proceed; package-complete disclosure remains source-dependent**

Reference: `docs/audit/20-evidence-semantics-and-validation.md` and PLAN Phase 2.

## Implemented

- A versioned governed field registry merges standard aliases with explicit custom aliases, statement/disclosure roles, exact dimensions, parent consolidation, units/period roles, valid aggregate coverage, double-count exclusions, accounting meaning, and economic class. Alias collisions and bad coverage fail loading.
- Structural official-evidence decisions now require both resolver acceptance and exact registry/CIK/context policy. After the registry gate, Batch 01 retained 15 selected facts and Batch 02 retained 9; nonconforming dimensional/semantic candidates remained rejected.
- A generic date-aware table parser preserves title/scope text, row label, column label, date, raw unit/scale, excerpt, locator, searched resources/tables, and scope hash. It rejects ambiguous duplicates, maturity/commitment roles, unknown scale, and broad row-label false positives.
- `not_disclosed` is possible only with complete governed package scope. Current frozen packages predate attachment-scope receipts, so their primary-only no-matches remain `unresolved` instead of false not-disclosures.
- A point-in-time value-change ledger selects only cutoff-eligible facts and preserves form/report/amendment/dimension-known state. Only same-context amendments can become confirmed restatements; Companyfacts dimension-unknown changes remain unresolved.
- Official DQC v29.0.6 2025/2026 rulesets and Xule 30052 run outside FastAPI. Exact ruleset hashes and primary US-GAAP namespace are required. Missing log/plugin/rules or zero execution becomes unavailable; DQC can never create a value.

## Deterministic real evidence

### Governed structural decisions

- Batch 01 A/B receipt hash: `c8a53cea…`; 100 decisions = 12 reported, 3 explicit zero, 85 unresolved; 15 selected, 3 retained rejected candidates.
- Batch 02 A/B receipt hash: `306f5243…`; 100 decisions = 8 reported, 1 explicit zero, 91 unresolved; 9 selected, 8 retained rejected candidates.

### Filing tables

- Batch 01 A/B hash: `89cbf36d…`; 61 applicable searches, 10 strict dated observations, 51 unresolved, 15 package-unavailable requests. Reported rows are source-scaled `USD millions` observations for AAPL, ANET, CRM, and DELL.
- Batch 02 A/B hash: `2c1966b3…`; 76 applicable searches, 8 strict dated observations, 68 unresolved. Reported rows are for META, OMC, TTWO, and WBD.
- Every current package is honestly `primary_document_only`; zero no-match rows are labeled `not_disclosed`. Protected serving hashes are unchanged.

### Restatement/value-change ledger

- Batch 01 A/B hash: `d75f95a1…`; 96,098 eligible Companyfacts observations, 1,744 value-change links, zero confirmed restatements because dimensions are unknown.
- Batch 02 A/B hash: `c2f927a4…`; 103,210 observations, 1,270 value-change links, zero confirmed restatements for the same reason.
- All 3,014 links are classified `unresolved_dimension_context`; none can rewrite a point-in-time selection silently.

### DQC

- Ten Batch 02 controller packages used the exact 2026 ruleset SHA-256 `ec87e8ec…` through Xule 30052.
- Final A/B DQC tree hash: `7c8c0427e64b600249f4bf3450dcb6ee9599ff2b204e9c26c2a562809d2cd698`.
- Twenty canonical rule executions were recorded across ten filings (`DQC.US.0139.9860`, `DQC.US.0226.10791`); all assertions were skipped as not applicable, so each outcome is `pass_no_applicable_rules`, not an unqualified pass. Diagnostics/errors: 0. `can_create_value=false` for all ten.

## Automated verification

`315 passed in 4.40s` across evidence outcomes, ingestion, registry, custom/dimensional resolver, table, restatement, DQC, filing evidence, structural schema, Arelle adapter, and real Arelle integration. `git diff --check` passed.

## Limitations carried forward

- Current packages lack governed attachment inventories, so real `not_disclosed` outcomes remain unavailable until FOD3 captures supplements/official packets with complete scope.
- Companyfacts cannot prove dimensions; confirmed restatements require exact filing-context candidates.
- The 2026 DQC v29 ruleset produced two rule entries per filing and no applicable assertions. This is execution evidence, not evidence that every DQC rule applied.
- Table observations are private diagnostics until FOD4 source ordering and arithmetic integration validate normalized values and prevent double counting.

Conclusion: semantic decisions, table extraction, restatement classification, and DQC execution fail closed and reproduce byte-identically. No value was synthesized from DQC, no unsafe table observation entered valuation, and no later filing rewrote an earlier cutoff result.
