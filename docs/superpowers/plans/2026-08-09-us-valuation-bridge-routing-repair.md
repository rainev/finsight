# U.S. Valuation Bridge and Routing Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair current-period U.S. bridge extraction, eliminate inappropriate FCFF fallbacks, and enforce company-specific model routing using controlled fixtures before any full-universe rebuild.

**Architecture:** Keep the current `CompanyFactsNormalizer` and fail-closed pipeline contracts, but add a current-filing bridge resolution boundary that cannot satisfy a bridge with stale instant facts. Keep intentional equity-level models for financial-business archetypes and make legacy fallback artifacts withhold at the serving boundary until regenerated.

**Tech Stack:** Python 3.11, pytest, SEC Companyfacts/submissions JSON fixtures, FastAPI artifact loader, JSON configuration.

## Global Constraints

- Preserve all existing user changes in the dirty worktree; stage only files belonging to this plan.
- Use existing `backend/tests/fixtures/us` first; do not run full-universe harvesting or rebuild in this phase.
- Treat prior Claude-generated zero overrides as hypotheses that require current filing period/accession validation.
- A bridge field is current only when its source period/accession is controlled for the normalized valuation period, or when a governed value explicitly matches that period/accession and cutoff.
- Missing fields must be re-extracted across configured concepts before they cause withholding.
- FCFF issuers may not silently fall back to residual income or DDM; intentional equity-level archetypes remain eligible.
- Every production change follows red-green-refactor: write a failing regression test, run it, implement the minimum change, then rerun focused and broader verification.
- Do not claim completion without fresh verification output.

---

### Task 1: Add current-filing bridge resolution tests

**Files:**
- Modify: `backend/tests/test_us_valuation.py`
- Modify: `backend/tests/test_us_valuation_v2_routing.py` only if a shared fixture helper is required

**Interfaces:**
- Consumes: `CompanyFactsNormalizer`, `classify_issuer`, and the WDC/CRM controlled fixtures.
- Produces: regression tests proving stale instant facts do not clear the current bridge and current facts/governed evidence do clear it.

- [ ] **Step 1: Write failing WDC regression tests.** Load WDC submissions and Companyfacts, normalize with classified WDC evidence, and assert marketable securities and preferred equity cannot be accepted from old periods as current reported bridge values; assert `bridge_complete` reflects unresolved fields.
- [ ] **Step 2: Run the WDC tests.** Run `PYTHONPATH=backend pytest -q backend/tests/test_us_valuation.py -k 'wdc and bridge'`. Expected: FAIL because the current `instant(..., at_or_before=...)` rule accepts old facts.
- [ ] **Step 3: Write failing CRM regression tests.** Assert CRM noncurrent securities, NCI, and lease facts from earlier periods cannot satisfy the current bridge. Assert commercial paper is not counted from stale/ambiguous evidence or double-counted with current debt.
- [ ] **Step 4: Run the CRM tests.** Run `PYTHONPATH=backend pytest -q backend/tests/test_us_valuation.py -k 'crm and bridge'`. Expected: FAIL against the current behavior.
- [ ] **Step 5: Commit red tests.** Run `git add backend/tests/test_us_valuation.py && git commit -m "test: expose stale US bridge facts"`.

### Task 2: Implement freshness-aware bridge extraction

**Files:**
- Modify: `backend/app/us_valuation/xbrl.py`
- Modify: `backend/app/us_valuation/config/concept_aliases.json` only when a verified missing concept is identified
- Modify: `backend/app/us_valuation/config/archetypes.json` only for corrected WDC/CRM evidence records
- Test: `backend/tests/test_us_valuation.py`

**Interfaces:**
- Consumes: `self.filing_records`, `self.as_of_date`, bridge evidence mappings, and Task 1 tests.
- Produces: bridge field states/provenance distinguishing current, governed-zero, stale, missing, and proxy values.

- [ ] **Step 1: Add `_controlling_filing(self, period_end: str) -> dict[str, Any] | None`.** Select the latest eligible 10-K/10-Q whose `reportDate` equals `period_end`, respects `as_of_date`, and return accession plus filing metadata.
- [ ] **Step 2: Add `_bridge_instant(self, field: str, *, period_end: str, controlling_accession: str | None, allow_cover_page_date: bool = False) -> SelectedFact | None`.** Prefer the controlling accession/current period; reject stale earlier-period facts. Allow cover-page shares from the same accession with an event date at or before the filing date, preserving proxy/source state.
- [ ] **Step 3: Run focused tests before integration.** Run `PYTHONPATH=backend pytest -q backend/tests/test_us_valuation.py -k 'wdc and bridge or crm and bridge'`. Expected: FAIL because `normalize()` still uses the generic instant selector.
- [ ] **Step 4: Route bridge fields through `_bridge_instant()`.** Use it for cash, marketable securities, commercial paper, current/noncurrent debt, finance leases, preferred equity, and NCI. Keep `operating_nwc()` on its existing proxy behavior because it is not an enterprise-to-equity bridge field.
- [ ] **Step 5: Validate governed values and zeros.** Require matching `controlled_period_end`, `source_accession`, valid nonnegative numeric values where applicable, and `reviewed_on <= as_of_date` when a cutoff exists. Preserve stale evidence as `verification_stale`.
- [ ] **Step 6: Reconcile economic categories.** Avoid double-counting commercial paper embedded in a broader debt concept. Include finance-lease totals only when current split fields are absent and a current aggregate exists. Do not map temporary/redeemable equity to `preferred_equity` without evidence identifying it as an ownership claim. Avoid layering share dilution twice.
- [ ] **Step 7: Investigate WDC and CRM evidence before editing config.** Search fixture concepts, accession records, and current source caches. If reduced fixtures cannot resolve temporary equity or commercial paper, record the gap and withhold rather than inventing a value. Only then update `archetypes.json` with traceable current evidence or a verified zero.
- [ ] **Step 8: Run normalizer regressions.** Run `PYTHONPATH=backend pytest -q backend/tests/test_us_valuation.py -k 'bridge or share or normalization'`. Expected: PASS for focused bridge behavior.
- [ ] **Step 9: Commit the bridge repair.** Run `git add backend/app/us_valuation/xbrl.py backend/app/us_valuation/config/concept_aliases.json backend/app/us_valuation/config/archetypes.json backend/tests/test_us_valuation.py && git commit -m "fix: require current evidence for US bridge fields"`.

### Task 3: Remove legacy FCFF fallback publication

**Files:**
- Modify: `backend/app/us_valuation/artifacts.py`
- Modify: `backend/app/routers/us_valuations.py` only if serving-boundary behavior needs a helper
- Modify: `backend/tests/test_us_valuation.py`
- Modify: `backend/tests/test_us_valuation_v2_routing.py`

**Interfaces:**
- Consumes: `sanitize_public_artifact()` and `load_generated_result()`.
- Produces: public artifacts that withhold legacy `fallback_from: fcff_dcf` valuations while preserving legitimate primary residual-income, DDM, and FFO artifacts.

- [ ] **Step 1: Write failing artifact tests.** Use a copy of `LOW.json` with `model_policy.fallback_from == "fcff_dcf"`, `review_required`, and a non-null DDM value. Assert sanitization withholds and scrubs values with a specific error. Add companion tests proving WFC residual income and SO utility DDM remain eligible.
- [ ] **Step 2: Run the tests.** Run `PYTHONPATH=backend pytest -q backend/tests/test_us_valuation.py backend/tests/test_us_valuation_v2_routing.py -k 'fallback or intentional or artifact'`. Expected: FAIL because publication vocabulary is validated but fallback provenance is not.
- [ ] **Step 3: Add `_legacy_fcff_fallback_reason(artifact: dict[str, Any]) -> str | None`.** Flag `model_policy.fallback_from == "fcff_dcf"` or an explicit incomplete-FCFF-to-other-model reason; do not flag intentional equity-level policies without a fallback marker.
- [ ] **Step 4: Apply the gate in `sanitize_public_artifact()`.** Reuse the existing fail-closed scrub path so all model/scenario values and ranges become unavailable while the repair reason remains visible.
- [ ] **Step 5: Run focused artifact tests.** Re-run the command from Step 2 and expect PASS for legacy and intentional cases.
- [ ] **Step 6: Commit the fallback gate.** Run `git add backend/app/us_valuation/artifacts.py backend/app/routers/us_valuations.py backend/tests/test_us_valuation.py backend/tests/test_us_valuation_v2_routing.py && git commit -m "fix: withhold legacy FCFF fallback artifacts"`.

### Task 4: Complete governed company-specific routing

**Files:**
- Modify: `backend/app/us_valuation/eligibility.py`
- Modify: `backend/app/us_valuation/classification.py` only if validation exposes a routing defect
- Modify: `backend/app/us_valuation/config/archetypes.json` only for evidence-backed model corrections
- Modify: `backend/tests/test_us_valuation_v2_routing.py`

**Interfaces:**
- Consumes: `load_archetype_config()`, `classify_issuer()`, and `model_eligibility()`.
- Produces: an explicit validated archetype/model contract and requested route coverage.

- [ ] **Step 1: Write failing routing tests.** Assert every configured archetype has a primary model represented by the governed map. Cover software/cloud → FCFF, semiconductors/components → FCFF, banks/insurers → residual income, REITs → FFO, utilities → DDM, and cyclical/industrial archetypes → their configured FCFF route. Add unknown/malformed/mismatch withholding tests.
- [ ] **Step 2: Run routing tests.** Run `PYTHONPATH=backend pytest -q backend/tests/test_us_valuation_v2_routing.py`. Expected: FAIL for uncovered policy/registry mismatches.
- [ ] **Step 3: Make eligibility validate the configured policy against one governed source of truth.** Preserve explicit rejection reasons and fail-closed behavior; do not broaden heterogeneous candidate archetypes merely to increase coverage.
- [ ] **Step 4: Run routing regressions.** Run `PYTHONPATH=backend pytest -q backend/tests/test_us_valuation_v2_routing.py backend/tests/test_us_valuation.py -k 'routing or classification or model_policy'`. Expected: PASS with no accidental FCFF fallback.
- [ ] **Step 5: Commit routing changes.** Run `git add backend/app/us_valuation/eligibility.py backend/app/us_valuation/classification.py backend/app/us_valuation/config/archetypes.json backend/tests/test_us_valuation_v2_routing.py && git commit -m "fix: enforce governed US model routing"`.

### Task 5: Inventory and verify the controlled scope

**Files:**
- Modify: `scripts/build_us_valuation_pipeline.py` only if a narrow regeneration guard is required
- Test: `backend/tests/test_us_valuation.py`, `backend/tests/test_us_valuation_v2_routing.py`, `backend/tests/test_us_valuation_v2_fcff.py`

**Interfaces:**
- Consumes: corrected bridge, artifact, and routing behavior from Tasks 1–4.
- Produces: an evidence-backed legacy-fallback inventory and fresh verification results; no full-universe rebuild.

- [ ] **Step 1: Run a read-only artifact inventory.** Scan `backend/app/data/us_valuations/*.json` for `fallback_from == "fcff_dcf"` or fallback-warning text; report legacy tickers separately from intentional equity-level models. Do not delete or rewrite the directory wholesale.
- [ ] **Step 2: Run the targeted suite.** Run `PYTHONPATH=backend pytest -q backend/tests/test_us_valuation.py backend/tests/test_us_valuation_v2_routing.py backend/tests/test_us_valuation_v2_fcff.py`. Expected: PASS once declared backend dependencies are available, otherwise report exact collection blockers.
- [ ] **Step 3: Run the complete backend suite.** Run `PYTHONPATH=backend pytest -q backend/tests` and categorize pre-existing failures versus changes from this plan.
- [ ] **Step 4: Inspect final state.** Run `git diff --check`, `git status --short`, and `git log --oneline -6`; confirm existing user changes remain untouched and only plan-owned files were staged in implementation commits.
