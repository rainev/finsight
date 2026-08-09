# U.S. Valuation Bridge and Routing Repair Design

**Status:** Approved for implementation by the project owner on 2026-08-09.

## Goal

Repair the current U.S. valuation pipeline's enterprise-to-equity bridge, remove inappropriate legacy fallback valuations, and make company-specific model routing explicit and fail-closed, using the existing fixtures and pipeline before any full-universe rebuild.

## Context and evidence

The Obsidian/Graphify notes connect `classify_issuer()` to `model_eligibility()`, `build_us_valuation()`, the bridge tests, and the valuation artifact/publication path. Repository validation must remain authoritative when notes and code disagree.

The current normalizer selects instant facts with an `at_or_before` rule. That can allow stale historical facts to satisfy a current bridge. Fixture inspection showed examples requiring repair:

- WDC currently resolves marketable securities and preferred equity from old historical facts while marking the bridge complete.
- CRM currently resolves noncurrent securities, finance leases, and noncontrolling interest from periods earlier than its controlling filing.
- WDC temporary-equity treatment and CRM commercial-paper treatment require filing-level economic reconciliation rather than assuming the prior generated zero overrides are correct.
- Focused tests could not collect in the current shell because the `google.auth` dependency is unavailable; this is an environment limitation, not an application behavior to work around.

## Scope

In scope:

- Existing `backend/tests/fixtures/us` fixtures and the current U.S. valuation pipeline.
- Fresh extraction and reconciliation of bridge fields: cash, marketable securities, commercial paper, current/noncurrent debt, finance leases, preferred equity, NCI, and share counts.
- WDC and CRM targeted investigation using available fixture evidence and, only if necessary, targeted filing evidence.
- Fail-closed removal of inappropriate FCFF-to-equity fallback paths and stale generated fallback outputs.
- Governed archetype-to-model routing and regression tests for software, semiconductors, banks, insurers, REITs, utilities, and cyclicals.

Out of scope for this phase:

- Full-universe SEC harvesting or rebuild.
- Historical point-in-time backtesting.
- Changes to intentional equity-level models for banks, insurers, utilities, securities firms, credit companies, and REITs unless routing/data eligibility exposes a concrete defect.
- Unrelated frontend, PSE, or product work.

## Design

### 1. Freshness-aware bridge resolution

The bridge will identify the controlling filing period and accession for the normalized TTM anchor. For each instant field:

1. Prefer a reported fact from the controlling period and filing evidence.
2. Accept an explicit governed filing value only when its controlled period, accession, value, and review cutoff match the current run.
3. Accept a verified zero only under the same matching controls.
4. Treat older facts as stale evidence, not as current reported values.
5. Leave unresolved fields missing and expose their state and provenance to the publication gate.

Concept selection will preserve economic distinctions:

- Commercial paper must not be silently double-counted when a broader current-debt concept already includes it.
- Finance leases are financing liabilities and must be included only from current split or aggregate evidence.
- Operating leases remain outside the debt bridge.
- Temporary/redeemable equity must be investigated separately from nonredeemable preferred equity and must not be forced into the preferred-equity field without evidence.
- Common shares, weighted-average diluted shares, and incremental dilution must carry explicit proxy states and must not layer dilution twice.

The output contract will retain per-field value, state, source concept, period, accession, and the reason for any proxy or governed override.

### 2. Repair before withholding

Missing bridge fields will first go through deterministic re-extraction across all configured concepts, units, periods, forms, accessions, and relevant dimensions available in the fixture. For WDC and CRM, the result will be compared with the controlling filing evidence when Companyfacts alone cannot distinguish a real absence from an extraction gap.

The system will withhold only after the repair attempt leaves a field unavailable or economically ambiguous. It will not trust prior Claude-generated zero overrides merely because they exist in configuration.

### 3. Fail-closed model eligibility and fallback removal

The governed archetype registry remains the source of truth for primary models. Intentional equity-level routes remain valid for financial-business archetypes. An FCFF issuer with an incomplete bridge or an ineligible configured model must produce a withheld artifact with a repair reason; it must not silently switch to residual income or DDM.

Existing stored artifacts that encode an inappropriate fallback will be inventoried and regenerated or withheld. They will not be deleted as part of this phase.

### 4. Explicit company-specific routing

Classification and eligibility will be tested as a contract:

- Every supported archetype has exactly one governed primary model.
- SIC routes and issuer overrides produce a recognized archetype and matching model.
- Ambiguous or unsupported classifications fail closed.
- Routing tests cover enterprise software/cloud, semiconductors/components, banks, insurers, REITs, utilities, and cyclical/industrial archetypes.

Routing policy changes will be evidence-based. Heterogeneous archetypes already marked candidate or review-required will not be broadened merely to increase coverage.

## Verification strategy

Use test-first regression cases for:

- stale instant facts not clearing a current bridge;
- current filing facts taking precedence over old zero values;
- WDC temporary-equity classification;
- CRM commercial-paper/current-debt non-double-counting;
- current finance lease split/aggregate behavior;
- preferred equity and NCI freshness;
- share-count proxy and dilution behavior;
- FCFF ineligible or incomplete cases withholding without fallback;
- governed archetype/model pairs and unknown/malformed routes.

Run the focused U.S. valuation tests, then the full backend test suite once the missing test dependency is available. Report any environment limitation separately from application failures.

## Alternatives considered

1. **Issuer-by-issuer override patches:** fast but brittle and likely to repeat the extraction error across the universe.
2. **Shared freshness-aware bridge and routing contracts:** recommended because it repairs the observed WDC/CRM failures and prevents stale facts from passing future companies.
3. **Full ingestion rewrite:** disproportionate risk before the point-in-time backtest.

## Expected outcome

The current pipeline either produces a valuation from current, traceable bridge inputs and an eligible model, or withholds it with a specific repair reason. It will not publish stale bridge values or hide unsupported FCFF cases behind legacy residual-income/DDM fallbacks.
