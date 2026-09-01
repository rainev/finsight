# FinSight Universe Reset — Reusable Batch Processing Handoff

Status: **canonical operating handoff for future Universe Reset batch chats**.

Last verified checkpoint: **Batch 27 was user-confirmed on 2026-08-31 at Pass 6 / Conditional 4 /
Withheld 0; numeric 10/10**.

This file explains the process that produced the reliable Batch 11–27 results in the
`whole-universe-greenlight` worktree. It is intentionally detailed so that a fresh chat can follow
the same gates without relying on the conversation that created it.

This handoff does **not** authorize a new batch by itself. The current next signal is
`Start Universe Reset Batch 28`.

## 1. How the user should use this handoff

Attach or point the new chat to this file, then use the paste-ready prompt near the end. Replace
`NN` with the desired batch number.

The new chat must read this file completely before acting. It must also verify current repository
state because the checkpoint section will naturally become stale as later batches finish.

The short interaction pattern is:

1. User: `Start Universe Reset Batch NN.`
2. Agent processes exactly ten frozen companies, presents `Pass / Conditional / Withheld`, and
   stops.
3. User: `y` to confirm the initial result.
4. If any companies are Withheld, the agent reminds the user of the separate recovery signal.
5. User: `Attempt recovery for Batch NN withheld companies.`
6. Agent makes one efficient recovery attempt, presents the final recovery result, and stops.
7. User: `y` to confirm recovery/bookkeeping.
8. The agent gives—but does not execute—the next-batch signal.

If the initial batch has zero Withheld companies, there is no recovery phase. Confirmation adds
the direct Conditional companies to the Recovery Learning Watchlist with
`recovery_outcome: not_applicable`.

## 2. The non-negotiable operating rules

### Preserve the workspace

- Preserve every tracked and untracked change already present.
- Do not reset, discard, overwrite, clean, or silently stash current work.
- Do not use destructive Git commands.
- Do not alter the dirty root checkout.
- Continue in the existing dedicated worktree when it exists:
  `/Users/carlosconda/Desktop/Investing Application/.worktrees/whole-universe-greenlight`.
- Run `git worktree list`, `git status --short`, `git branch --show-current`, and `git remote -v`
  before editing. Do not assume the checkpoint below is still current.
- Generated source packets, parsed evidence, candidate artifacts, catalogs, and API receipts stay
  under untracked `output/`.
- Never overwrite an immutable evidence directory. Create a new candidate suffix such as
  `candidate-b`, `final-c`, or `challenged-a`.

### Preserve scope

- Process exactly the ten issuers in the frozen `batch_NN.json` manifest.
- Never replace, silently skip, or add a company.
- Use valuation date `2026-08-14` for this controlled reset unless the frozen manifest changes by
  an explicitly authorized new universe.
- Do not start the next batch before a new explicit user signal.
- Do not automatically attempt recovery merely because a company is Withheld.
- Do not promote or activate a tracked serving catalog, merge, push, modify `main`, or deploy
  without separate explicit authorization.
- A request to process a batch is not authorization to push it.
- If pushing is later authorized, verify the destination. The user previously corrected the
  destination to `rainev/finsight`; the current `origin` points there. Never push batch work to a
  different remote merely because it exists.

### Preserve the public/private boundary

- Private evidence may contain accessions, exact facts, arithmetic, assumptions, fallbacks,
  scenario traces, warnings, and reason codes.
- Public artifacts may contain the value range, publication state, model description, safe
  assumptions, warning, and High/Medium/Low reliability.
- Public artifacts must not contain raw source ledgers, reported-input dictionaries, model traces,
  acquisition schedules, private evidence, market-price fitting, or recommendations.
- The real API must sanitize again at the serving boundary.
- Arelle remains an offline extraction dependency. It must never be imported into or run inside the
  serving process.

## 3. Sources of truth to read at the beginning of every batch

Read only the smallest relevant files first, but read all load-bearing instructions completely.

1. `AGENTS.md`
2. This handoff
3. `.codex/goodbehavior/profiles/finsight-us-valuation.md`
4. `docs/learnings/INDEX.md`, followed by the directly relevant learnings
5. `docs/plans/ROADMAP.md`
6. `docs/audit/00-index.md`
7. The most recent confirmed batch audit and, if applicable, its recovery audit
8. `backend/app/us_valuation/config/reset_batches_2026_08_14/partition_receipt.json`
9. `backend/app/us_valuation/config/reset_batches_2026_08_14/batch_NN.json`
10. `backend/app/us_valuation/config/universe_reset_recovery_learning_watchlist.json`
11. `backend/app/us_valuation/config/universe_reset_withheld.json`
12. `backend/app/data/us_valuation_catalogs/active.json`

The frozen partition is:

- Universe: `US-SP500-ISSUERS-2026-08-14-1.0`
- Partition: `US-RESET-PARTITION-2026-08-14-2.0`
- Valuation date: `2026-08-14`
- Exact cover: 500 unique issuers, 50 batches, 10 issuers per batch
- Partition-root SHA-256:
  `fd49977122da8bdbaad1d336efeb5bf8480a21a3c63d03b57c0b961cb65908a4`

Do not select companies from memory, market capitalization, alphabetical order, or a live S&P 500
list. The frozen batch manifest is the only denominator authority.

## 4. What “done” means

A batch is not done merely because code was written or tests passed.

The initial processing phase may be described as **verified — user confirmation required** only
after all of the following are true:

- the exact ten-company denominator is proven;
- cutoff-safe source packets and controlling filings are proven;
- source identities, dates, periods, units, currency, and shares are checked;
- every numeric model is economically suitable;
- low/base/high arithmetic and sensitivity directions are recomputed;
- an independent challenge has no unresolved Critical or Important finding;
- two complete regenerations are byte-identical;
- focused and full backend tests pass;
- the frontend production build passes when public contracts or shared behavior are in scope;
- an isolated cumulative catalog is exercised through the real local FastAPI list, detail, and
  calculator routes;
- public/private leakage checks pass;
- tracked serving artifacts and premature bookkeeping remain unchanged;
- the evidence is presented to the user.

The batch becomes **done** only after the user confirms it. Recovery, if needed, is a separate
authorized phase with its own verification and confirmation.

## 5. Outcome definitions

Every batch report must show all three counts explicitly, even when a count is zero.

### Pass

Use Pass when:

- issuer, source, period, unit, currency, and shares are trustworthy;
- the current economic object is coherent;
- the selected model is appropriate for the business;
- cash, debt, leases, preferred equity, NCI, and other material claims reconcile;
- source-linked history is comparable enough to anchor the assumptions;
- no named unresolved event, claim, separation, specialist-model gap, or accounting distortion can
  materially change the baseline object;
- the range is finite, ordered, and positive at the base;
- public output is safe.

Pass does not mean the future is predictable. A Pass may still have a wide range or Low internal
reliability. It means the ordinary source-bounded baseline is complete enough without a material
special disclaimer.

### Conditional

Use Conditional when:

- a useful finite low/base/high range exists;
- the missing or uncertain information is bounded without pretending it is known;
- but a named material acquisition, transaction, patent cliff, legal claim, capital allocation,
  separation, product launch, underwriting condition, cycle assumption, equity-floor convention,
  or specialist-model dependency remains load-bearing.

Material provisional assumptions normally cap reliability at Low. Conditional is a useful
baseline, not a failed valuation.

### Withheld

Withhold only for hard failures:

- wrong or unreliable issuer, source, period, unit, or currency;
- unreliable share denominator;
- materially contradictory evidence;
- no coherent current economic object;
- no economically suitable model;
- material financing or claims that cannot be separated or bounded;
- a major event with no defensible current or event-conditioned state;
- every reasonable base state is nonfinite or nonpositive;
- public-safety failure.

Do not withhold merely because the future is uncertain, perfect segment detail is missing, a
specialist disclosure is incomplete, or the company is difficult. FinSight estimates where the road
goes and drives slowly.

Never replace missing information with zero. A public zero is allowed only as an explicitly
governed limited-liability floor after retaining the raw negative bear residual privately. Never use
zero as a fabricated base input.

## 6. Decision framework — how to reason about each company

This section documents the repeatable decision method, not hidden internal deliberation.

For every company, answer these questions in order.

### Question 1: What exactly is being valued?

Name the economic object before choosing a formula:

- current consolidated operating company;
- post-spin continuing company;
- pre-transaction standalone company;
- transaction-conditioned residual equity;
- bank or insurer parent common equity;
- regulated utility common equity;
- REIT operations or property/NAV equity;
- industrial operations plus captive-finance sum-of-parts.

Do not mix two states. A current standalone intrinsic value, signed transaction consideration, and
post-close value are different surfaces.

### Question 2: Which inputs are facts, calculations, and assumptions?

Keep three layers separate:

- **Reported:** directly sourced facts with accession, filed date, period, unit, dimensions, and
  value.
- **Historically derived:** TTM reconstructions, annual medians, percentiles, normalized margins,
  average equity, or comparable-period calculations.
- **FinSight assumptions:** growth fades, WACC/cost of equity, terminal growth/ROE, claim recovery,
  capex ranges, dilution ranges, or bounded event states.

A warning is not enough. Every material assumption must change actual arithmetic or be clearly
identified as an unmodeled invalidation risk.

### Question 3: Is the current evidence comparable?

Check for:

- acquisition or disposal accounting;
- discontinued operations;
- partial-period ownership;
- noncash IPR&D or impairment addbacks inside operating cash flow;
- unusually large working-capital movements;
- customer or member funds;
- settlement payments or legal reserves;
- post-period cash, debt, share, or operating events;
- stale aliases or mismatched concepts across years.

If a current TTM observation is mechanically correct but economically distorted, keep it in the
private reported ledger and exclude or stress it transparently in normalization. Never silently
delete it and never let a noncash acquisition charge become recurring cash generation.

### Question 4: Which model matches the economics?

Use the simplest suitable existing route.

- Ordinary operating issuer: history-backed faded cash-FCFF DCF.
- Bank or managed-care/insurance equity: residual income using common equity, normalized
  parent-attributable earnings/ROE, payout, and cost of equity. Do not apply an industrial EV debt
  bridge to deposits, member funds, or medical claims.
- Mixed industrial/captive finance: sum-of-parts if separable; otherwise an explicitly Conditional
  consolidated equity model that avoids double-counting finance debt.
- Utility: regulated/development sum-of-parts when possible; bounded FCFE/DDM fallback when the
  mixed-business effect is finite.
- REIT: reported AFFO/FFO and NAV/cap-rate evidence; use conservative maintenance-capex and cap-rate
  ranges when property detail is incomplete.
- Cyclical issuer: through-cycle revenue and margin normalization using company history plus a
  source-verified industry range.
- Event-driven issuer: current standalone value first; separate transaction consideration or event
  overlay. Do not probability-weight a deal without evidence.

Reuse shared pipeline components. Do not create a new model merely to force coverage.

### Question 5: Does the bridge count every item exactly once?

Reconcile:

`Enterprise value − interest-bearing debt − preferred equity − NCI − other common-equity claims + issuer-owned excess cash/investments = common equity value`

Then divide by a trustworthy diluted-share range.

Important distinctions:

- Current plus noncurrent debt must reconcile to a statement total or an explained gross-principal
  alternative.
- Finance leases are financing only if not already inside the chosen debt total.
- Operating leases usually remain post-rent operating items; do not subtract them again when rent is
  already in cash conversion.
- Supplier finance generally remains accounts payable/operating cash unless the filing proves a
  separate financing treatment.
- Legal reserves, contingent consideration, NCI, preferred equity, and acquisition payables must be
  treated once.
- Historical settlement totals are evidence, not automatically current claims.
- Insurance receivables offset the related gross reserve only when scope and collectability are
  source-bounded.
- Sale proceeds already inside period-end cash must not be added again.
- Acquisition consideration exchanged for acquired net assets is not automatically an equity loss.
- Parent-attributable earnings already exclude NCI; do not deduct NCI twice in an equity-level
  earnings model.

### Question 6: Are the scenarios coherent?

Build bear, base, and bull states with transparent inputs.

- Bear should use weaker cash conversion/growth, higher discount rate, higher claims, and more
  dilution.
- Bull should use stronger—but still defensible—cash conversion/growth, lower discount rate, lower
  bounded claims, and less dilution.
- Terminal growth must remain below WACC or cost of equity with the model's required safety spread.
- Higher cash, margin, growth, terminal growth, or normalized earnings must not lower value.
- Higher capex, WACC/cost of equity, debt, claims, or shares must not raise value.
- Preserve raw negative residuals privately. Apply a public bear-only zero floor only when the base
  remains positive and the limited-liability rule is explicit.
- A nonpositive base is a hard stop unless the product has an explicitly authorized
  equity-at-risk surface that does not pretend it is a normal positive price target.

Do not use current stock prices, analyst targets, competitor displayed values, or desired market
alignment to calibrate the intrinsic range.

### Question 7: What would make the value invalid?

Every Conditional result needs a short public warning and a precise private invalidation rule.
Examples include a transaction closing on different terms, an IRS judgment, a material claim
settlement, a spin allocation, a debt refinancing, or a share count outside the governed range.

## 7. End-to-end batch state machine

### Gate A — explicit start authorization

Accept a clear signal such as `Start Universe Reset Batch NN`.

Do not treat questions like “what is Batch NN?” or “are we ready?” as authorization.

Create a short working plan. Mark only one step in progress at a time. Do not ask the user to
approve routine internal steps once the batch start is authorized.

### Gate B — workspace and predecessor audit

1. Inspect worktrees, branch, remotes, and dirty state.
2. Read the previous confirmed audit and recovery audit.
3. Confirm the previous batch is actually user-confirmed.
4. Recompute current watchlist and withheld-register counts from their loaders.
5. Hash the tracked serving roots and cumulative bookkeeping before processing.
6. Confirm the next batch number and stop if it does not match the user's signal.

Protected roots normally include:

- `backend/app/data/us_valuation_catalogs`
- `frontend/public/data`
- `frontend/src/research/generated`

Use the same tree-hash algorithm for before/after comparisons. Do not compare hashes produced by
different algorithms.

### Gate C — freeze and validate the exact denominator

Read `batch_NN.json` and verify:

- batch number;
- valuation date;
- exactly ten unique tickers and ten unique CIKs;
- core/boundary counts and order;
- lane/family fields;
- consistency with `partition_receipt.json`.

Create or update the typed contract module:

- `backend/app/us_valuation/batch_NN.py`
- `backend/tests/test_batch_NN_contract.py`

The typed module must fail fast if the manifest changes or the ten-company order differs.

### Gate D — cache-first SEC source capture

Create batch-specific capture tooling by reusing the latest proven capture helpers:

- `scripts/capture_batch_NN_sources.py`
- `scripts/capture_batch_NN_structural_sources.py`

Order of operations:

1. Search complete existing `output/` caches by CIK/ticker/accession.
2. Validate cached identity and hashes.
3. Fetch only missing SEC submissions/companyfacts packets.
4. Select the latest cutoff-eligible 10-K/10-Q by filing date and accession.
5. Capture the exact filing package.
6. Parse it structurally with Arelle.
7. Write immutable packet/package/structural receipts under a new untracked output root.
8. Prove protected roots did not change.

Never hardcode a personal email into the repository. Use the configured `SEC_USER_AGENT` when a
network fetch is required.

The default Python environment may lack Arelle. Before structural parsing, check the pinned
runtime. In this workspace the proven structural runtime is `python3.11` with `arelle-release`.
If the wrong interpreter captures a complete package but fails during parsing, preserve and reuse
the package rather than fetching again.

If a run is interrupted after writing some immutable issuer receipts, do not retry into the same
output root: a valid `capture_mode` change from `captured` to `reused` changes receipt bytes. Resume
into a fresh immutable root and include the partial wrapper/package cache as a reuse source.

### Gate E — source and cutoff audit

For all ten companies, privately record:

- ticker, CIK, legal/display issuer identity;
- accession, form, filing date, report date, primary document;
- source packet, package, and structural hashes;
- unit and currency;
- share facts and periods;
- controlling filing selection reason;
- important acquisition, disposal, litigation, debt, lease, NCI, preferred, or subsequent-event
  facts.

Do not trust the structural wrapper's top-level `period_end` blindly. Several real wrappers contain
malformed diagnostic dates. Use the bound source receipt's filing/report dates and each fact's own
period. Record `used_for_selection: false` for a malformed diagnostic.

### Gate F — build source-linked history

Prefer three to five comparable annual periods plus the current TTM object.

For flows, reconstruct TTM as:

`latest fiscal year + current comparable YTD − prior-year comparable YTD`

Current and prior YTD durations must align. A point-in-time balance is not a flow and must not be
inserted into this formula.

For each history observation, retain concept, value, unit, accession, form, filed date, start/end
dates, fiscal year, and formula. Reject stale aliases that do not connect to current economics.

When current history is not comparable because of a spin, acquisition, disposal, or accounting
event, use one of these transparent paths:

- continuing-operation history;
- filed pro-forma scale;
- source-bounded current/comparative period;
- annual-history normalization that explicitly excludes the distorted TTM observation;
- Conditional fallback with a named release condition;
- Withheld if no finite coherent object remains.

### Gate G — implement the practical model

Typical batch files are:

- `backend/app/us_valuation/batch_NN_history.py`
- `scripts/run_batch_NN_history.py`
- `backend/tests/test_batch_NN_history.py`

Use shared `history.py`, `practical_models.py`, specialist adapters, baseline/public contracts, and
calculator logic. Keep issuer-specific constants and source bindings together and traceable.

Every private numeric result must contain:

- economic archetype and model version;
- why the model was selected;
- controlling source identity;
- reported inputs;
- historically derived inputs;
- FinSight assumptions;
- low/base/high scenario rows;
- exact bridge and claims formulas;
- model trace;
- fallback level and reason codes;
- reliability cap and reasons;
- missing details and how they were bounded;
- warning and invalidation rule.

Every public artifact must agree exactly on ticker, value range, availability, reliability, method,
and safe assumptions while excluding the private ledger.

### Gate H — classify without gaming the result

Attempt an ordinary Pass first. Do not automatically label every difficult company Conditional.

Then ask:

- Does a named material dependency remain?
- Is that dependency greater than ordinary forecast uncertainty?
- Does it change the economic object or determine whether value is positive?

If no, Pass. If yes but bounded, Conditional. If materially unbounded, Withheld.

Never set a quota for Pass, Conditional, numeric coverage, or 10/10 success. The exact result is an
output of the evidence, not a target.

### Gate I — independent challenge

Use the FinSight efficiency workflow when available. Sol remains the synthesizer and verifier.
Use at most three disjoint agents; fewer is better.

Recommended split:

- **Source inventory:** `gpt-5.6-luna`, High reasoning. Check identity, cutoff, accessions, periods,
  units, shares, cache reuse, and missing evidence.
- **Economic/model challenge:** `gpt-5.6-luna`, xhigh reasoning. Recompute arithmetic, challenge
  model choice, claims, acquisitions, scenario calibration, classification, and public calculator
  routing.
- Optional third agent only for a genuinely separate specialist scope.

Agents are reviewers, not decision makers. Sol must inspect their evidence, repair every Critical or
Important finding, rerun the candidate, and request a final concise recheck. Report which agents,
model/effort, and evidence were used.

Challenge the exact final candidate—not merely preliminary policy ideas.

### Gate J — deterministic replay

Perform two independent cache-only replays:

1. SEC packet replay A/B: all ten reused, zero network fetches.
2. Structural replay A/B: all ten reused, zero reparsing/fetch when complete wrappers exist.
3. Candidate generation A/B from the separate replay roots.
4. Compare full trees, generated-private trees, and staged-public trees byte-for-byte.

Keep hashes and the hashing contract in the audit. A deterministic valuation run does not excuse a
bad model; model challenge and determinism are separate gates.

### Gate K — tests and consumer-path verification

Run focused tests first:

```sh
PYTHONPATH=backend:. pytest -q \
  backend/tests/test_batch_NN_contract.py \
  backend/tests/test_batch_NN_history.py
```

Focused tests should prove:

- exact denominator and order;
- exact expected classifications;
- finite ordered ranges;
- base greater than zero for numeric results;
- missing values never become zero;
- sensitivity directions;
- exact material claim formulas;
- specialist model identity;
- public/private boundary;
- public calculator model family and default parity;
- serving/watchlist/withheld immutability during initial processing.

Then run the full backend suite:

```sh
PYTHONPATH=backend:. pytest -q
```

Run the frontend production build when shared public behavior, schemas, catalog behavior, or UI
contracts are in the batch scope:

```sh
cd frontend
npm run build
```

Build an **isolated untracked cumulative catalog** from the last confirmed catalog plus the new
staged batch. Never activate it. Verify its expected count and availability/publication totals with
`scripts/build_us_valuation_catalog.py`.

Start the real local FastAPI test harness against the isolated catalog. If sandbox policy prevents
binding or localhost connections, request the narrow permission needed for the local port. Do not
claim API verification from an in-process unit test.

The cumulative API verifier must check:

- list HTTP 200 and exact cumulative count;
- exact ticker set;
- detail HTTP 200 and byte-equivalent catalog parity for every ticker;
- exact staged parity for all ten new tickers;
- calculator GET HTTP 200 for every ticker;
- calculator default POST with `save=false` reproduces low/base/high for every numeric ticker;
- Withheld calculator POST fails closed with HTTP 400;
- calculator model family matches the private economic route;
- zero private-key leaks.

UI/browser verification is required only when user-facing behavior changes. Do not spend usage on a
browser pass for a data-only batch whose frontend contract is unchanged.

### Gate L — write the evidence report

Determine the next unused audit number; do not guess. Create:

- `docs/audit/<number>-controlled-batch-NN-result.md`

Update:

- `docs/audit/00-index.md`
- `docs/plans/ROADMAP.md`

The audit must include:

- exact Pass/Conditional/Withheld counts out of ten;
- exact ticker lists;
- low/base/high values and reliability;
- controlling filing/accession/period;
- simple company-by-company reason;
- source capture and cache results;
- independent challenge findings and repairs;
- deterministic hashes;
- focused/full test results;
- frontend result;
- real API counts and receipt hash;
- protected-root and bookkeeping state;
- explicit confirmation gate and prohibited next actions.

Record a durable learning only for a genuinely non-obvious trap or user correction. Update an
existing learning on the same topic instead of creating duplicates.

### Gate M — present the initial result and stop

Lead with:

```text
Pass: X/10
Conditional: Y/10
Withheld: Z/10
```

Then show one concise table:

```text
Ticker | Outcome | Low | Base | High | Reliability | Short reason
```

Explain the result in plain language. Do not bury Withheld companies inside technical details.
State that values are baseline decision ranges, not predictions or recommendations.

Report cumulative processed and numeric coverage, but do not change the denominator.

End with:

`To confirm Batch NN, reply: y.`

Do not start recovery, mutate the watchlist/register, promote, push, deploy, or start the next batch
before confirmation.

### Gate N — confirmation bookkeeping

After the user replies `y`:

- mark the audit and roadmap as user-confirmed;
- add every direct Conditional company to the Recovery Learning Watchlist with:
  - `initial_outcome: conditional_numeric_low`
  - `recovery_outcome: not_applicable`
  - `current_status: conditional_numeric_low` or the explicit equity-at-risk variant;
- do not add a Pass;
- do not add an initial Withheld company to the cumulative withheld register yet, because it has not
  received its one recovery attempt;
- run the watchlist and withheld-register loaders/tests;
- state the exact updated counts and hashes;
- if no companies are Withheld, say no recovery is needed and provide the next-batch signal;
- if companies are Withheld, remind the user of the separate recovery signal below.

## 8. One-attempt recovery workflow

Recovery requires the explicit signal:

`Attempt recovery for Batch NN withheld companies.`

Do not recover Pass or direct Conditional companies unless the user explicitly authorizes a wider
whole-batch review. Batch 12's whole-batch recovery was a special user-authorized exception and is
not the default precedent.

### Efficient recovery method

For each Withheld company:

1. Re-read the exact release condition and blocker from the initial private ledger.
2. Reuse all existing source packets and structural evidence.
3. Search only for the missing event, specialist, pro-forma, claim, or history evidence.
4. Prefer a narrow extraction/model repair over a parallel pipeline.
5. Use public research when the user authorized it, but compare only transparent public practices.
   Do not copy AlphaSpread, GuruFocus, or another provider's proprietary formula or displayed value.
6. Try the simplest economically honest workaround:
   - current standalone state;
   - post-event state;
   - consolidated fallback;
   - source-bounded normalized history;
   - residual-income/FCFE/AFFO specialist route;
   - broad Conditional Low range.
7. Keep Withheld if a finite positive base still requires invention.
8. Independently challenge every newly numeric recovery.
9. Replay twice, run focused/full tests, and exercise the real cumulative API.

### Recovery bookkeeping

After recovery confirmation:

- recovered to Pass: do not add to the watchlist; remove an older watchlist entry only when the
  evidence and user confirmation support full recovery;
- recovered to Conditional: add/update the watchlist with
  `recovery_outcome: conditional_numeric_low`;
- still Withheld: add/update the watchlist with `withheld_after_recovery` and append it to the
  cumulative withheld register with one consumed attempt;
- never give a second ordinary recovery attempt during the 50-batch reset;
- report both the batch-final current Withheld count and the append-only cumulative register count;
  they are not always identical.

The recovery report must show initial versus final outcomes company by company and explain every
newly numeric value.

## 9. Common traps discovered during Batches 01–14

These are the mistakes most likely to make a fresh chat look productive while producing the wrong
result.

### Mechanical traps

- Treating a wrapper's malformed top-level period as the controlling report date.
- Using a current point balance in a TTM flow formula.
- Mixing annual interest expense with YTD net interest income without aligning signs.
- Accepting stale historical aliases because the number exists.
- Using entity shares, weighted-average diluted shares, and post-repurchase shares interchangeably.
- Treating a tag name as proof that debt includes or excludes current maturities or leases.
- Counting finance leases twice.
- Subtracting operating leases, supplier finance, or other working-capital liabilities again after
  their cash cost is already in operating cash flow.
- Treating missing preferred/NCI evidence as zero without a structural absence proof.

### Economic traps

- Letting acquisition IPR&D addbacks inflate recurring operating cash while ignoring acquisition
  cash outflows.
- Adding acquisition consideration as a loss even though consideration was exchanged for acquired
  net assets, or failing to reserve the cash when the forecast excludes the acquired business.
- Adding sale proceeds again when they are already in period-end cash.
- Projecting dividends from a disposed equity-method investment.
- Treating historical settlement payments as a current liability.
- Subtracting NCI twice from parent-attributable earnings.
- Applying industrial FCFF to a bank, insurer, managed-care company, or captive-finance-heavy
  object.
- Combining standalone intrinsic value and merger consideration.
- Manufacturing a positive cycle midpoint from one unusually good year.
- Price-fitting assumptions to current market prices or competitor outputs.

### Product and verification traps

- Calling correct arithmetic proof that the model is calibrated appropriately.
- Passing default calculator parity while exposing the wrong calculator model family and controls.
- Allowing public assumptions to differ from the actual private base state.
- Reporting tests as proof of the real API.
- Verifying ten staged files but not the cumulative catalog.
- Comparing hashes produced by different algorithms.
- Overwriting earlier candidate evidence instead of creating a new immutable output root.
- Adding direct Conditional companies to the watchlist before user confirmation.
- Registering initial Withheld companies before their one recovery attempt.
- Starting the next batch automatically after confirmation.
- Pushing to the wrong remote or treating a push as implicit batch authorization.

## 10. File pattern for a normal new batch

A typical batch adds or updates:

```text
backend/app/us_valuation/batch_NN.py
backend/app/us_valuation/batch_NN_history.py
backend/tests/test_batch_NN_contract.py
backend/tests/test_batch_NN_history.py
scripts/capture_batch_NN_sources.py
scripts/capture_batch_NN_structural_sources.py
scripts/run_batch_NN_history.py
docs/audit/<next>-controlled-batch-NN-result.md
docs/audit/00-index.md
docs/plans/ROADMAP.md
```

Only after confirmation:

```text
backend/app/us_valuation/config/universe_reset_recovery_learning_watchlist.json
backend/tests/test_universe_reset_recovery_learning_watchlist.py
```

Only after a confirmed one-attempt recovery leaves a company Withheld:

```text
backend/app/us_valuation/config/universe_reset_withheld.json
backend/tests/test_universe_reset_withheld.py
```

Recovery usually adds:

```text
backend/app/us_valuation/batch_NN_recovery.py
backend/tests/test_batch_NN_recovery.py
scripts/run_batch_NN_recovery.py
docs/audit/<next>-batch-NN-recovery-result.md
```

Do not mechanically copy constants or classifications from the previous batch. Reuse structure and
helpers, then bind the new batch's own sources and economics.

## 11. Reporting style expected by the user

- Explain the outcome first.
- Use plain, non-technical language for company blockers and uncertainty.
- Use `Pass / Conditional / Withheld`, not vague “publishable” totals alone.
- Explain why a zero bear value is a limited-liability floor when it appears.
- Say what facts make a result Conditional; do not call all estimates “speculation.”
- Be concise in the chat, while preserving detailed evidence in the audit.
- Never imply certainty or market-beating ability.
- Never say “done” before real consumer-path verification and user confirmation.
- If something is not verified, label it clearly and do not let it drive promotion.

Suggested initial-result response:

```text
Batch NN is verified, but not yet user-confirmed.

Pass: X/10
Conditional: Y/10
Withheld: Z/10

[Company table]

Verification: source capture, independent challenge, deterministic replay, focused/full tests,
frontend build, cumulative API parity, and private-leak check.

Serving artifacts and bookkeeping remain unchanged. Batch NN+1 was not started.

To confirm Batch NN, reply: y.
```

Suggested post-confirmation response:

```text
Batch NN is confirmed and recorded.

- Pass: X/10
- Conditional: Y/10
- Withheld: Z/10
- Recovery Learning Watchlist: <exact current count>
- Cumulative withheld register: <exact count and whether it changed>
- Serving catalog unchanged
- Batch NN+1 not started

If recovery is needed, reply: Attempt recovery for Batch NN withheld companies.
Otherwise, the next signal is: Start Universe Reset Batch NN+1.
```

## 12. Current verified checkpoint — update this after each confirmed batch

As of 2026-08-31:

- Batches processed and user-confirmed: **01–27**
- Exact issuers processed: **270/500**
- Current verified classification through Batch 27:
  - Pass: **104/270**
  - Conditional: **157/270**
  - Withheld: **9/270**
  - Numeric: **261/270**
- Recovery Learning Watchlist: **166 entries**
  - Conditional current status: **157**
  - Withheld current status: **9**
- Cumulative automatic-withheld history: **19 preserved entries**
- Tracked active serving catalog: **Batches 01–10 only**
  - Catalog: `US-RESET-2026-08-14-B01-B10-1.0`
  - 100 issuers: 45 available / 51 conditional / 4 unavailable
- Batches 11–27 are implemented and verified in the dirty worktree but are not activated in the
  tracked serving catalog.
- Latest full backend proof: `1,645 passed, 3 skipped, 1 warning`
- Latest frontend proof: production build passed, `1,694` modules transformed
- Latest cumulative isolated API proof: Batch 27 catalog with 104 available / 157 conditional /
  9 unavailable; 270/270 detail and calculator GET parity; 261 numeric POSTs HTTP 200; 9 unavailable
  POSTs HTTP 400; zero private leaks
- Current dedicated worktree:
  `/Users/carlosconda/Desktop/Investing Application/.worktrees/whole-universe-greenlight`
- Current worktree branch at this checkpoint: `codex/universe-reset-batch-10`
- Current worktree HEAD at this checkpoint: `6d6814daf98afe75770d3ca4cd22f57f95323817`
- Current tracked remote destination for user-authorized pushes: `origin` →
  `https://github.com/rainev/finsight.git`
- The worktree is intentionally dirty with preserved Batch 11–27 and earlier work.
- No promotion, merge, push, deployment, or Batch 28 start is authorized by this handoff.

Latest evidence:

- `docs/audit/65-controlled-batch-11-result.md`
- `docs/audit/66-batch-11-recovery-result.md`
- `docs/audit/67-controlled-batch-12-result.md`
- `docs/audit/68-batch-12-whole-recovery-gap.md`
- `docs/audit/69-batch-12-whole-recovery-result.md`
- `docs/audit/70-controlled-batch-13-result.md`
- `docs/audit/71-controlled-batch-14-result.md`
- `docs/audit/72-batch-14-pass-repair-gap.md`
- `docs/audit/73-batch-14-pass-repair-result.md`
- `docs/audit/74-controlled-batch-15-result.md`
- `docs/audit/75-batch-15-recovery-gap.md`
- `docs/audit/76-batch-15-recovery-result.md`
- `docs/audit/77-controlled-batch-16-starting-gate.md`
- `docs/audit/78-controlled-batch-16-result.md`
- `docs/audit/79-batch-16-recovery-gap.md`
- `docs/audit/80-batch-16-recovery-result.md`
- `docs/audit/81-batch-16-whole-repair-gap.md`
- `docs/audit/82-batch-16-whole-repair-result.md`
- `docs/audit/83-controlled-batch-17-starting-gate.md`
- `docs/audit/84-controlled-batch-17-result.md`
- `docs/audit/85-controlled-batch-18-starting-gate.md`
- `docs/audit/86-controlled-batch-18-result.md`
- `docs/audit/87-controlled-batch-19-starting-gate.md`
- `docs/audit/88-controlled-batch-19-result.md`
- `docs/audit/89-controlled-batch-20-starting-gate.md`
- `docs/audit/90-controlled-batch-20-result.md`
- `docs/audit/91-controlled-batch-21-starting-gate.md`
- `docs/audit/92-controlled-batch-21-result.md`
- `docs/audit/93-controlled-batch-22-starting-gate.md`
- `docs/audit/94-controlled-batch-22-result.md`
- `docs/audit/95-controlled-batch-23-starting-gate.md`
- `docs/audit/96-controlled-batch-23-result.md`
- `docs/audit/97-batch-23-whole-repair-gap.md`
- `docs/audit/98-batch-23-whole-repair-result.md`
- `docs/audit/99-controlled-batch-24-starting-gate.md`
- `docs/audit/100-controlled-batch-24-result.md`
- `docs/audit/101-batch-24-whole-repair-gap.md`
- `docs/audit/102-batch-24-whole-repair-result.md`
- `docs/audit/103-controlled-batch-25-starting-gate.md`
- `docs/audit/104-controlled-batch-25-result.md`
- `docs/audit/105-batch-25-recovery-result.md`
- `docs/audit/106-controlled-batch-26-starting-gate.md`
- `docs/audit/107-controlled-batch-26-result.md`
- `docs/audit/108-controlled-batch-27-starting-gate.md`
- `docs/audit/109-controlled-batch-27-result.md`

Batch 27 is Pass 6 / Conditional 4 / Withheld 0. KLAC, ADBE, COHR, and FLEX were added to the
watchlist; TER, TXN, LRCX, MU, IT, and ADSK were not added. No Batch 27 recovery is needed.

The next valid signal is:

`Start Universe Reset Batch 28`

## 13. Paste-ready prompt for a new chat

Use this prompt with this file attached or linked:

```text
Work in the existing FinSight whole-universe-greenlight worktree. Read AGENTS.md and
BATCH-PROCESSING-HANDOFF.md completely before acting, then verify the current repository,
worktree, batch, audit, watchlist, withheld-register, and active-catalog state instead of trusting
stale chat memory.

Follow the handoff's exact gated workflow: preserve all tracked and untracked work; process exactly
the frozen ten-company manifest; use cache-first cutoff-safe SEC/structural evidence and the
historical layer; choose the economically suitable practical model; distinguish Pass,
Conditional, and Withheld; independently challenge the exact candidate; repair all Critical and
Important findings; replay twice; run focused and full backend tests, the appropriate frontend
build, and the real isolated cumulative FastAPI list/detail/calculator verification; keep generated
evidence untracked; do not mutate tracked serving artifacts or premature bookkeeping; present the
initial result and stop for my confirmation.

Use the finsight-efficiency, gate-build-goodbehavior, verify-goodbehavior, and
learn-goodbehavior workflows when available. Explain company outcomes simply in chat while keeping
the detailed source/model evidence in the audit. Do not recover withheld companies, start the next
batch, promote, merge, push, or deploy without a separate explicit signal.

Start Universe Reset Batch NN.
```

For the current checkpoint, replace `NN` with `28`.

## 14. Final reminder to the future agent

The goal is not 10/10 Pass and not 10/10 numeric coverage. The goal is a practical conservative
baseline wherever uncertainty can be bounded, with honest refusal where it cannot.

Source correctness, model suitability, public behavior, deterministic replay, and user confirmation
are separate gates. Do not collapse them into one convenient proxy.
