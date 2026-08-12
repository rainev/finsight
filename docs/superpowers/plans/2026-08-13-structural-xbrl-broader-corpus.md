# Structural XBRL Broader Corpus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the structural XBRL resolver on a representative 20-company corpus, correct recurring deterministic mapping/reporting gaps, classify each company’s valuation data eligibility in shadow mode, and then replay the resolver over the full supported withheld corpus.

**Architecture:** Keep Arelle and the existing deterministic resolver unchanged as the parser and per-field decision boundary. Tighten candidate admission so negative accounting phrases cannot create unrelated candidates, add only evidence-supported taxonomy aliases, and aggregate existing per-field decisions into a separate shadow-only case disposition. Production valuation inputs and publication states remain untouched.

**Tech Stack:** Python 3, Arelle, pytest, immutable JSON shadow reports, cached SEC filing packages.

## Global Constraints

- Publication effect remains exactly `none_shadow_only`; no production valuation input or serving artifact may change.
- Company Facts remains the production authority during this phase.
- Absence is not zero; rejected, unresolved, and review decisions never populate valuation fields.
- Use deterministic taxonomy and accounting structure only; no LLM, embedding, fuzzy, expected-value, or market-price acceptance path.
- Preserve source concept, accession, period, unit, form, confidence, mapping method, reason codes, and structural evidence for accepted/review decisions.
- Model-route eligibility and data-quality eligibility are separate outputs.
- A parser failure, unsupported required field, rejected decision, unresolved decision, or required review decision produces a shadow `withhold` disposition.
- A case can be a shadow `publish_candidate` only when every requested supported field is accepted. Accepted structural/extension mappings below 0.98 produce `lower_confidence_candidate`; otherwise the case is `publish_candidate`.
- `data_quality_score` is the minimum accepted resolver confidence when all requested fields are accepted; otherwise it is `null`. Classification confidence remains separate.
- Keep `OtherShortTermInvestments` review-grade.
- Never stage `output/` or `.superpowers/`.

---

### Task 1: Tighten candidate admission and add verified preferred-equity alias

**Files:**
- Modify: `backend/app/us_valuation/concept_resolver.py`
- Modify: `backend/app/us_valuation/config/concept_aliases.json`
- Modify: `backend/app/us_valuation/config/structural_concept_rules.json`
- Modify: `backend/tests/test_concept_resolver.py`

**Interfaces:**
- Consumes: `resolve_concept(request, facts) -> ResolutionDecision` and mapping version `US-XBRL-RESOLVER-1.1`.
- Produces: deterministic positive candidate admission; `PreferredStockValueOutstanding` as a governed preferred-equity alias only when all existing hard gates pass.

- [ ] **Step 1: Write failing tests for positive candidate admission**

Add tests proving an unrelated fact that matches only `excluded_economic_phrases` or only `review_only_phrases` yields `NO_CANDIDATE`, while a finance-lease payment fact with an actual finance-lease phrase remains review-grade and an investment fact with an actual commercial-paper member remains rejected.

- [ ] **Step 2: Run the targeted tests and verify RED**

Run:

```bash
pytest -q backend/tests/test_concept_resolver.py -k 'negative_phrase or review_phrase or finance_lease_payment or commercial_paper'
```

Expected: the new unrelated-fact tests fail because negative/review phrases currently admit candidates by themselves.

- [ ] **Step 3: Require a positive accounting signal before classification**

In `_is_plausible_extension`, candidate admission may use `extension_terms`, `required_definition_phrases`, contextual concepts, and configured component-only concepts. `review_only_phrases` and `excluded_economic_phrases` may classify or reject an already plausible candidate, but may not create one.

- [ ] **Step 4: Write the failing structural-ambiguity test**

Add two distinct, equally ranked candidate facts with different QNames or contexts but the same numeric value. Assert `AMBIGUOUS_FACTS`; numeric equality must not establish semantic equivalence.

- [ ] **Step 5: Run the ambiguity test and verify RED**

Run:

```bash
pytest -q backend/tests/test_concept_resolver.py -k 'same_value_distinct_candidates'
```

Expected: accepted status because ambiguity currently depends on differing numeric values.

- [ ] **Step 6: Make ambiguity structural rather than value-based**

After exact fact-identity deduplication, reject whenever more than one distinct candidate remains at the highest confidence. Do not compare candidate values to decide semantic equivalence.

- [ ] **Step 7: Write the failing NVIDIA preferred-equity test**

Add a standard US-GAAP `PreferredStockValueOutstanding` fact with value zero, USD unit, current period, no dimensions, and direct balance-sheet equity support. Assert accepted status and `PREFERRED_EQUITY_CARRYING_AMOUNT`.

- [ ] **Step 8: Run the preferred-equity test and verify RED**

Run:

```bash
pytest -q backend/tests/test_concept_resolver.py -k 'preferred_stock_value_outstanding'
```

Expected: review status because the concept is not yet a configured alias.

- [ ] **Step 9: Add the exact deterministic alias**

Add `PreferredStockValueOutstanding` to `fields.preferred_equity.concepts` and its stable reason code to the preferred-equity policy. Do not add common-stock concepts, `NonMarketableSecurities`, generic debt totals, or combined debt-and-lease concepts.

- [ ] **Step 10: Run resolver regression tests**

Run:

```bash
pytest -q backend/tests/test_concept_resolver.py backend/tests/test_structural_xbrl_schema.py
```

- [ ] **Step 11: Commit**

```bash
git add backend/app/us_valuation/concept_resolver.py backend/app/us_valuation/config/concept_aliases.json backend/app/us_valuation/config/structural_concept_rules.json backend/tests/test_concept_resolver.py
git commit -m "fix: tighten structural candidate admission"
```

---

### Task 2: Add case-level shadow data-quality eligibility

**Files:**
- Modify: `backend/app/us_valuation/structural_shadow.py`
- Modify: `scripts/run_structural_xbrl_shadow.py`
- Modify: `backend/tests/test_structural_shadow.py`

**Interfaces:**
- Produces: `shadow_case_eligibility(artifact, decisions, *, parser_failed=False) -> dict[str, Any]`.
- Report fields: `model_route_eligible`, `classification_confidence`, `data_quality_status`, `data_quality_score`, `shadow_disposition`, `blocking_fields`, and `publication_effect`.

- [ ] **Step 1: Write failing pure aggregation tests**

Cover all-accepted exact aliases, all-accepted structural extension, accepted plus review, accepted plus rejected, accepted plus unresolved, model-ineligible, no decisions, and parser failure. Assert rejected/unresolved/review cases have `data_quality_score is None` and never become zero-valued evidence.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
pytest -q backend/tests/test_structural_shadow.py -k 'eligibility or disposition'
```

Expected: import or assertion failure because the case aggregator does not exist.

- [ ] **Step 3: Implement the pure fail-closed aggregator**

Keep model eligibility separate from data quality. Derive model route status from the private artifact’s governed `issuer.model_route_eligible`; preserve `issuer.classification_confidence` separately. Use per-field decision status before reading confidence. Return `withhold` for any blocking status and `null` data-quality score; return `publish_candidate` only for all-accepted decisions at confidence at least 0.98, otherwise `lower_confidence_candidate`.

- [ ] **Step 4: Attach eligibility to successful and failed reports**

`evaluate_shadow_case` adds the aggregation without changing decisions. `_failure_report` emits the same contract with parser failure as a blocker. Keep `publication_effect: none_shadow_only`.

- [ ] **Step 5: Add case counters to the CLI summary**

Add `publish_candidate`, `lower_confidence_candidate`, and `withhold_cases` counters while preserving existing field-level counters for backwards compatibility. Count one disposition per eligible company, not one per decision.

- [ ] **Step 6: Run shadow tests**

Run:

```bash
pytest -q backend/tests/test_structural_shadow.py backend/tests/test_structural_xbrl_integration.py
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/us_valuation/structural_shadow.py scripts/run_structural_xbrl_shadow.py backend/tests/test_structural_shadow.py
git commit -m "feat: classify structural shadow eligibility"
```

---

### Task 3: Replay and validate the representative 20-company corpus

**Files:**
- Modify: `docs/plans/EVIDENCE.md`
- Modify: `docs/superpowers/handoffs/2026-08-11-structural-bridge-resolvers-in-progress-handoff.md`
- Runtime evidence only: `output/structural-xbrl-broad-corpus/`

**Interfaces:**
- Consumes: the 20 staged private artifacts and cached filing packages.
- Produces: immutable post-fix company reports, summary, reconciled candidate ledger, and case dispositions.

- [ ] **Step 1: Run the focused structural suite**

```bash
pytest -q backend/tests/test_structural_xbrl_schema.py backend/tests/test_concept_resolver.py backend/tests/test_arelle_adapter.py backend/tests/test_filing_package.py backend/tests/test_structural_shadow.py backend/tests/test_structural_xbrl_integration.py
```

- [ ] **Step 2: Run a fresh cached 20-company replay**

Run the committed shadow CLI against the staged corpus into a new immutable output directory without `--refresh`.

- [ ] **Step 3: Validate the real output**

Reconcile 20 discovered/eligible/parsed companies, zero parser failures, one case disposition per company, field decision totals, mapping methods, and publication effect. Compare the five-company regression baseline and confirm rejected/unresolved/review decisions did not become valuation inputs.

- [ ] **Step 4: Record evidence and commit**

Document exact counts, accepted mappings, non-accepted recurring patterns, limitations, and the shadow-only eligibility result. Do not stage runtime `output/`.

---

### Task 4: Expand across the full supported withheld corpus

**Files:**
- Modify: `docs/plans/EVIDENCE.md`
- Modify: `docs/superpowers/handoffs/2026-08-11-structural-bridge-resolvers-in-progress-handoff.md`
- Runtime evidence only: `output/structural-xbrl-full-corpus/`

**Interfaces:**
- Consumes: all available private US-GAAP withheld artifacts with at least one field in `SUPPORTED_STRUCTURAL_FIELDS`.
- Produces: full-corpus shadow reports and aggregate recovery/ambiguity/eligibility metrics.

- [x] **Step 1: Build an untracked, auditable input manifest**

Select only private artifacts with eligible 10-K/10-Q forms and at least one supported missing bridge field. Record ticker, CIK, archetype, filing accession/form/period, and requested fields. Exclude IFRS/20-F and unsupported-only cases.

- [x] **Step 2: Run the full cached/network replay under SEC fair-access controls**

Use the existing package cache, no production data roots, and a new immutable output directory. Preserve parser failures as withhold cases.

- [x] **Step 3: Validate aggregate and stratified results**

Reconcile input count to discovered/eligible/skipped/parser-failed totals; aggregate decisions and case dispositions by field and archetype; inspect every newly recurring review mapping; verify no rejected/unresolved decision became zero or entered a valuation.

- [x] **Step 4: Run final regression tests**

Run the focused structural suite and full backend suite. Report any pre-existing unrelated failure separately.

- [x] **Step 5: Record evidence and commit**

Update durable evidence and handoff with the exact full-corpus counts, remaining mapping gaps, and production-promotion boundary. Status remains `verified — your confirmation needed`.
