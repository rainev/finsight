# FinSight Whole-Universe Greenlight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task by task. Use FinSight Efficiency Mode and GoodBehavior for every phase.

**Goal:** Give all 500 companies an honest FinSight decision and publish a defensible intrinsic value for at least 450 of them.

**Architecture:** FinSight will freeze one dated company universe, turn SEC filings into source-linked accounting facts, route each company to the correct valuation model, test the major models on old data, and publish a value only when the evidence is good enough. Arelle stays in the offline ingestion path; the live app reads normalized JSON and never imports Arelle.

**Tech stack:** Python, FastAPI, React/TypeScript, SEC Companyfacts and filing packages, Arelle, pytest, public historical-price sources, immutable JSON evidence artifacts.

## Global constraints

- Work in a clean worktree. Do not implement this plan in the dirty root checkout.
- Preserve the existing `output/` evidence. Never stage generated runtime output.
- Use test-driven development: observe RED before writing production code.
- Never treat a missing, stale, conflicting, or vague accounting fact as zero.
- Never use an unrelated valuation model just to produce a number.
- Keep raw accounting evidence and detailed review notes private.
- The public product remains simple: intrinsic value, reliability, range, and sliders.
- Do not compare FinSight with AlphaSpread or GuruFocus.
- Use crawled public prices only as a baseline benchmark. Do not buy market data for this phase.
- A task is complete only after focused tests, the full relevant suite, and a real-data replay pass.

---

## Definition of greenlight

The first whole-universe release requires:

- Exactly 500 companies in one dated and versioned manifest.
- Exactly one decision for every company.
- At least 450 companies with a defensible numeric intrinsic value.
- Any unsafe company shown as `Unavailable`; no hidden value may leak publicly.
- Every published value assigned one reliability level:
  - `very_high`: 90–100
  - `high`: 80–89
  - `moderate`: 65–79
  - `limited`: 50–64
  - `very_limited`: 35–49
- Scores below 35, or any hard blocker, produce `Unavailable`.
- Major model lanes must pass the baseline point-in-time backtest before release.
- Small specialist lanes may publish only as `Limited` or lower until they have enough backtest evidence.

## Starting evidence

- The repository currently contains 206 public valuation artifacts: 81 `review_required` values and 125 withheld cases.
- The wider working universe has previously been described as 500 companies, with 477 having full data, but there is no canonical 500-company manifest in this repository.
- The Arelle/structural resolver parsed the supported 104-company shadow corpus without parser failures.
- Parsing alone did not clear publication gates: all 104 cases stayed withheld.
- The evidence-aware bridge work is on `feat/evidence-aware-bridge-policy` at `e1cd1e2`.
- The 2024 XUSSS rules were tested and rejected for current 2025/2026 filings. Do not integrate them.

---

### Task 1: Create a clean integration baseline

**Files:**

- Read: `docs/plans/EVIDENCE.md`
- Read: `docs/audit/02-evidence-aware-bridge-replay.md`
- Create: `docs/audit/03-whole-universe-baseline.md`

**Work:**

- [ ] Create `feat/whole-universe-greenlight` in a new ignored worktree from `finsight/latest-origin-main`.
- [ ] Record the starting branch, commit, worktree path, and dirty-root status.
- [ ] Integrate `feat/evidence-aware-bridge-policy` without copying untracked `output/` files.
- [ ] Review the branch diff for accidental public-data or frontend artifact changes.
- [ ] Install only the existing pinned dependencies, including the separate XBRL requirements.
- [ ] Run the focused structural-XBRL and bridge-policy suites.
- [ ] Run the full backend suite and record the exact result.
- [ ] Replay the existing cached 104-company structural corpus in shadow mode.
- [ ] Confirm that serving artifacts do not change during the replay.
- [ ] Write the evidence and any real blockers to `docs/audit/03-whole-universe-baseline.md`.

**Gate:** The integrated branch must have passing tests, reproducible shadow output, and no unexplained serving-data changes before Task 2.

---

### Task 2: Freeze the 500-company universe

**Files:**

- Create: `backend/app/us_valuation/config/universe-2026-08-13.json`
- Create: `backend/app/us_valuation/universe.py`
- Create: `scripts/reconcile_us_universe.py`
- Create: `backend/tests/test_us_universe.py`

**Manifest fields:**

```json
{
  "universe_version": "US-500-2026-08-13",
  "as_of_date": "2026-08-13",
  "ticker": "MSFT",
  "issuer_name": "Microsoft Corporation",
  "cik": "0000789019",
  "filing_regime": "us_gaap_10k_10q",
  "membership_source": "documented source URL or recovered source artifact",
  "issuer_status": "active",
  "share_class_policy": "primary_listed_class",
  "included": true
}
```

**Work:**

- [ ] Write failing tests for exact count, unique CIK/ticker rules, required fields, stable sorting, and version validation.
- [ ] Recover the old 500-company working list if its original artifact can be found and proven.
- [ ] If the old list cannot be proven, freeze the current S&P 500 issuer list from a documented public source and cross-check CIKs against the SEC ticker-to-CIK file.
- [ ] Treat the universe as issuer-level: one entry per CIK. If an issuer has several listed classes, keep its primary listed class and record the rule.
- [ ] Never silently drop a company because its filing or model is unsupported.
- [ ] Reconcile the old 500, 477, and 206 denominators into one report.
- [ ] Emit one baseline lane and blocker for every company.

**Gate:** The reconciler must report exactly 500 included issuers, no duplicate CIKs, and one explicit status per issuer.

---

### Task 3: Promote the accounting evidence layer safely

**Files:**

- Modify: `backend/app/us_valuation/field_availability.py`
- Modify: `backend/app/us_valuation/bridge_policy.py`
- Modify: `backend/app/us_valuation/structural_shadow.py`
- Test: existing structural, field-availability, bridge-policy, pipeline, and artifact suites

**Field states:**

- `reported`
- `explicit_zero`
- `evidence_backed_zero`
- `not_applicable`
- `proxy`
- `bounded_unresolved`
- `not_disclosed`
- `unresolved`
- `stale`
- `conflict`

**Work:**

- [ ] Keep Companyfacts as the standard fast path.
- [ ] Keep Arelle as the structural parser for controlling filing packages and company extensions.
- [ ] Keep Arelle out of the live FastAPI serving process.
- [ ] Promote a structural mapping only when its deterministic rule has source-level tests, real-filing reconciliation, and zero unsafe promotions in its review corpus.
- [ ] Evaluate the bridge as economic groups, not ten equally mandatory tags:
  - cash and eligible investments;
  - total interest-bearing debt;
  - finance leases;
  - preferred claims;
  - noncontrolling interests;
  - diluted shares.
- [ ] Allow a proven aggregate to replace unavailable detail when double counting is impossible.
- [ ] Keep stale and conflicting facts visible but unusable.
- [ ] Emit source concept, accession, period, unit, mapping method, reason code, authority, and confidence for every accepted fact.
- [ ] Continue rejecting label-only semantic matches, payment schedules used as carrying values, share counts used as equity amounts, and unrelated dimensional members.

**Bounded uncertainty:**

- Up to 1% intrinsic-value spread: no special grade cap.
- More than 1% and up to 5%: subtract 3 reliability points.
- More than 5% and up to 10%: subtract 8 points and cap the result at `very_limited`.
- More than 10%, or no defensible upper bound: hard blocker and `Unavailable`.

**Gate:** Real difficult filings—including ANET, CRM, DELL, FTNT, and WDC—must reconcile to their source filing without an unsafe promotion.

---

### Task 4: Give every issuer the correct model lane

**Files:**

- Modify: `backend/app/us_valuation/config/archetypes.json`
- Modify: `backend/app/us_valuation/eligibility.py`
- Modify or split: `backend/app/us_valuation/equity_models.py`
- Create: `backend/app/us_valuation/model_lane_registry.py`
- Test: `backend/tests/test_us_valuation_v2_routing.py` and new lane-registry tests

**Required lanes:**

1. Ordinary operating companies: FCFF/DCF with EPV cross-check.
2. Banks, insurers, securities firms, and credit companies: residual income.
3. Regulated utilities: DDM.
4. REITs: AFFO/NAV-ready route, using FFO only as an explicitly limited interim input.
5. Energy, mining, and commodity companies: cycle/reserve-aware model.
6. Autos with captive finance: industrial business plus finance-arm separation.
7. Digital assets and special situations: dedicated model, not generic FCFF.
8. IFRS/20-F issuers: separate IFRS normalization feeding the appropriate economic model.
9. Short-history or pre-profit companies: governed steady-state/scenario route or `Unavailable`.

**Work:**

- [ ] Create a registry that gives every issuer one lane, model version, eligibility state, and reason.
- [ ] Remove all silent FCFF-to-residual-income/DDM fallbacks.
- [ ] Keep unsupported lanes explicit until their real model exists.
- [ ] Build lanes in this order: existing FCFF/equity lanes, REITs, energy/cyclicals, autos/special situations, IFRS, short-history.
- [ ] Stop expanding new lanes once at least 450 companies have defensible values; keep honest `Unavailable` decisions for the rest.

**Gate:** All 500 companies must have exactly one model-lane decision. No company may receive an economically unrelated fallback.

---

### Task 5: Build the baseline point-in-time backtest

**Files:**

- Create: `backend/app/us_valuation/backtest/contracts.py`
- Create: `backend/app/us_valuation/backtest/point_in_time.py`
- Create: `backend/app/us_valuation/backtest/prices.py`
- Create: `backend/app/us_valuation/backtest/metrics.py`
- Create: `scripts/run_us_valuation_backtest.py`
- Create: focused backtest tests under `backend/tests/`

**Sample:**

- Target 100 companies; require at least 75 usable companies.
- About 80 current-universe companies, stratified by model lane and sector.
- About 20 removed, delisted, distressed, or historically poor performers.
- Use a fixed random seed and save the selected sample before computing results.
- Never remove a company because its valuation performed badly.

**Historical valuation dates:**

- `2019-12-31`
- `2020-06-30`
- `2021-12-31`
- `2022-06-30`
- `2023-12-31`
- `2024-06-30`

**Price baseline:**

- Crawl Yahoo's public chart data as the primary source and Stooq daily data as the cross-check.
- Cache every raw response with retrieval time and source URL.
- Rate-limit requests and do not bypass access controls.
- Use split-adjusted closing prices and exclude dividends.
- Use the nearest trading day within five calendar days of the target date.
- Mark missing or conflicting histories unusable; never invent or interpolate them.
- This is a baseline benchmark, not institutional-grade market data.

**Point-in-time rules:**

- Use only filings available by the valuation date.
- Keep original filing date, period end, accession, and taxonomy/model version.
- Reject later filings, later restatements, and later-created assumptions.
- Use the historical 10-year Treasury rate from a public historical source.
- Use a versioned FinSight ERP policy table available as of each valuation date.
- Compare intrinsic value with prices after 6, 12, and 24 months.
- Compare performance with an unchanged starting-price baseline.

**Major-lane pass gate:**

- At least 15 issuers and 60 issuer-date observations.
- No look-ahead violations.
- Twelve-month directional accuracy of at least 55%.
- Twelve-month scenario coverage between 60% and 90%.
- Twelve-month median absolute valuation error no worse than 40%.
- No material systematic overvaluation or undervaluation.
- Beat the unchanged-price baseline, or be no more than 10% worse while giving better directional or scenario coverage.

**Small lanes:**

- The sample is directional evidence only.
- A small lane cannot receive a grade above `limited` until it has enough observations to pass the major-lane gate.

**Gate:** The report must reproduce from frozen inputs and show every exclusion, observation count, formula, and look-ahead check.

---

### Task 6: Add the reliability score and approval contract

**Files:**

- Create: `backend/app/us_valuation/reliability.py`
- Modify: `backend/app/us_valuation/pipeline.py`
- Modify: `backend/app/us_valuation/artifacts.py`
- Create: `backend/tests/test_us_valuation_reliability.py`

**Hard blockers:**

- Look-ahead leakage.
- Wrong period, accession, unit, currency, or share denominator.
- Unbounded, stale, or conflicting material accounting exposure.
- Ineligible or unimplemented model.
- Major model lane has not passed its backtest.
- Non-finite output or non-positive output when the selected model does not apply.

**Score:**

| Component | Points | Initial rule |
|---|---:|---|
| Accounting data and provenance | 35 | Core flows 10, bridge 10, shares/dilution 10, period/unit/source integrity 5 |
| Model suitability | 25 | Approved route 10, history 5, model-specific inputs 5, classification quality 5 |
| Lane backtest evidence | 25 | Lane pass 10, direction 5, error 5, scenario coverage 5 |
| Scenario and assumption stability | 15 | Scenario width 7, cross-check dispersion 4, finite/monotonic sensitivities 4 |

**Work:**

- [ ] Score only after all hard blockers pass.
- [ ] Store score, grade, component scores, deductions, grade caps, hard blockers, model version, and backtest version privately.
- [ ] Apply the bounded-uncertainty deductions from Task 3.
- [ ] Cap small unproven lanes at `limited`.
- [ ] Cap 5–10% accounting uncertainty at `very_limited`.
- [ ] Auto-approve clean companies after their lane passes.
- [ ] Require manual review for every `very_limited` result, every promoted company-extension mapping, every withheld-to-publishable change, and at least 10% of each lane with a minimum of three companies.
- [ ] Preserve public scrubbing when a hard gate fails.

**Gate:** Unit tests must cover every score boundary, deduction, cap, hard blocker, and public-scrubbing path.

---

### Task 7: Run the lane-by-lane release train

**Release order:**

1. Standard US-GAAP FCFF cohorts.
2. Banks, insurance, securities, credit, and utilities.
3. REITs.
4. Energy and cyclicals.
5. Autos and special situations.
6. IFRS/20-F and short-history companies.

**For each lane:**

- [ ] Confirm extraction coverage and source lineage.
- [ ] Confirm model eligibility and formulas.
- [ ] Pass the lane backtest or apply the small-lane reliability cap.
- [ ] Run shadow valuation for every company in the lane.
- [ ] Reconcile all publication-state changes.
- [ ] Complete the required manual sample.
- [ ] Verify that no withheld value leaks publicly.
- [ ] Publish a lane evidence report with counts, metrics, failures, and approved model/config versions.
- [ ] Release a 10% canary before enabling the full lane.

**Gate:** A lane does not advance on parser success alone. It advances only when accounting, valuation, backtest, and review gates pass.

---

### Task 8: Keep the public product simple

**Files:**

- Modify: `backend/app/routers/us_valuations.py`
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/pages/UsValuations.tsx`
- Add focused backend and frontend tests

**Public display:**

- Headline intrinsic value per share.
- Five-level reliability badge.
- Low/base/high range as secondary detail.
- Existing assumption sliders.
- One short explanation for `limited` or `very_limited` results.
- `Unavailable` with no exposed value when a hard gate fails.

**Private-only detail:**

- Raw accounting facts.
- XBRL concept and relationship evidence.
- Manual-review notes.
- Full scoring breakdown and internal reason codes.
- Backtest observation-level records.

**Gate:** Exercise the real page through the backend and frontend. Confirm that values, reliability labels, ranges, sliders, and unavailable states render correctly.

---

### Task 9: Rebuild and operate the full universe

**Work:**

- [ ] Run the complete 500-company pipeline in shadow mode.
- [ ] Reconcile exactly 500 decisions.
- [ ] Require at least 450 numeric intrinsic values.
- [ ] Confirm zero unsafe field promotions.
- [ ] Confirm zero look-ahead violations in the benchmark.
- [ ] Confirm zero leaked unavailable/withheld values.
- [ ] Confirm every output records filing accession, source period, universe version, model version, reliability version, and backtest version.
- [ ] Rebuild a company after each new 10-Q, 10-K, or 20-F, using a daily filing check.
- [ ] Keep prior output versions for rollback and comparison.
- [ ] Monitor extraction failures, stale filings, reliability-grade changes, backtest drift, refresh failures, and lane coverage.
- [ ] Roll back by universe/model version; never repair a production release by hand-editing individual JSON files.

**Final gate:** FinSight is not “whole-universe greenlit” until the real 500-company replay, public-safety check, UI check, and user review all pass.

---

## Final verification commands

The exact focused commands may grow as files are added, but the final gate must include:

```bash
pytest -q backend/tests/test_structural_xbrl_schema.py \
  backend/tests/test_concept_resolver.py \
  backend/tests/test_arelle_adapter.py \
  backend/tests/test_structural_shadow.py \
  backend/tests/test_field_availability.py \
  backend/tests/test_bridge_policy.py

pytest -q backend

cd frontend && npm run build
```

Also run the real universe reconciler, backtest CLI, 500-company shadow rebuild, API safety checks, and browser acceptance test. Save their exact commands and results in the lane and final audit reports.

## Plain-language summary

1. Make one clean list of 500 companies.
2. Make sure FinSight reads each filing correctly.
3. Give each kind of company the right math model.
4. Test the big models using old information and later stock prices.
5. Give safe values a reliability label.
6. Hide values that are still too risky.
7. Release one company group at a time.
8. Do not call the whole universe finished until at least 450 values are safe enough to show.
