# FinSight — Current Handoff for Claude

_Updated: 2026-08-14 (Asia/Manila)_

## Read this first

The honest state is: the reliability pipeline is partly built, but the first ten-company valuation batch has **not**
started and the 500-company universe has **not** been processed or published.

This handoff is for the worktree:

```text
/Users/carlosconda/Desktop/Investing Application/.worktrees/whole-universe-greenlight
```

The intended handoff branch is:

```text
claude-handoff-2026-08-14
```

The branch is intended to preserve the current paused implementation changes. Generated `output/` evidence must stay
untracked and must not be staged, committed, deleted, or cleaned.

## Original objective

FinSight should eventually publish an intrinsic value for the whole company universe (roughly 500 companies), similar
in purpose to AlphaSpread or GuruFocus, while clearly showing that some valuations are more reliable than others.

The immediate approved path is:

1. Make the pipeline less strict about small, non-material missing details.
2. Keep genuinely unsafe, conflicting, malformed, or non-finite data withheld.
3. Give usable valuations `High`, `Medium`, or `Low` reliability instead of treating everything as pass/fail.
4. Replay the difficult existing corpus and measure the real effect.
5. Process exactly the first ten approved companies.
6. Repeat ten-company batches until the whole universe is covered.

The first ten are: `AAPL`, `MSFT`, `CRM`, `ANET`, `WDC`, `DELL`, `JPM`, `BAC`, `NEE`, and `O`.

## Current Git state

Verified before this handoff was written:

- Previous branch: `feat/whole-universe-greenlight`
- HEAD: `7c3e607` (`docs: plan first ten-company valuation batch`)
- Remote used for the project branch: `origin` → `https://github.com/rainev/halaga.git`
- Previous status: branch was ahead of `origin/feat/whole-universe-greenlight` by 91 commits.
- The working tree contained the eight modified tracked files listed below and untracked `output/`.

Modified tracked files that must be preserved:

```text
backend/app/routers/us_valuations.py
backend/app/us_valuation/artifacts.py
backend/app/us_valuation/automated_review.py
backend/tests/test_api.py
backend/tests/test_automated_review.py
backend/tests/test_bridge_policy_artifacts.py
backend/tests/test_us_valuation.py
docs/superpowers/plans/2026-08-14-evidence-aware-reliability-pipeline.md
```

These are paused Task 5 review fixes and related plan/test changes. They are **not yet verified after the latest edits**.

## Verified progress

The phase ledger is the authoritative progress record:

[`progress.md`](../.superpowers/sdd/2026-08-14-evidence-aware-reliability-pipeline/progress.md)

- Tasks 1–4 of the evidence-aware reliability phase are recorded as complete.
- Historical full-suite evidence reached `898 passed, 3 skipped, 1 existing warning` after Task 4.
- The initial Task 5 implementation was committed as `6f53364`.
- Historical Task 5 checks reported `187 focused passed` and `931 full-backend passed`, but an independent review later
  required changes. Therefore Task 5 must not be treated as complete.
- The existing replay input shape is recorded as 106 immediate candidates: 104 valid private artifacts plus 2 known
  invalid public-shaped cases (`ADBE` and `SNPS`). This is an input denominator, not a pass count or publication count.
- The Batch 01 design and plan exist, but source capture, valuation generation, API verification, and promotion have not
  run.

## Unverified or blocked claims

Do not present these as completed:

- Task 5 after the current uncommitted fix round: not yet rerun.
- Task 6 difficult-corpus replay: not started.
- Task 7 live API verification: not completed for this phase.
- Any of the ten Batch 01 companies: not yet generated, verified, or promoted by this paused work.
- Whole-universe coverage: not run.
- Number of publishable companies after the revised policy: unknown until replay evidence exists.

There is a stale status conflict: `task-5-report.md` says `VERIFIED`, while the newer phase ledger records the
independent review as `CHANGES_REQUIRED`. Trust the newer ledger and the current diff. Tests alone do not close the
phase.

## Decisions already approved

- Accounting-impact thresholds remain `5%` and `20%`.
- Scenario-movement thresholds remain `20%` and `40%`.
- Annual data no more than 365 days old may be carried forward and should not receive a harsh missing-data penalty.
- Quarterly data may back up annual data when the period and provenance rules are satisfied.
- Arelle is an offline/source-ingestion helper. It is not the FastAPI serving parser or production authority.
- Public artifacts must use the canonical safe serializer and must not expose raw financial evidence or private fields.
- Reliability must agree with the actual artifact values and scenario ranges.
- Genuine source-integrity failures, conflicts, wrong periods/units/currencies, non-finite values, hard warnings, and
  invalid model lanes remain fail-closed.
- Do not stage or delete `output/` evidence.
- Batch 01 must generate only staged artifacts, verify list/detail API behavior for all ten, and promote exactly ten only
  after a 10/10 gate passes.

## Why Task 5 is still open

The independent review found these concrete problems:

1. Equity serialization could leak injected private top-level or nested fields.
2. Reliability could say `High` while the actual scenario range required a lower grade.
3. Serving trusted stale `automated_review` metadata instead of freshly validating the current artifact.
4. Model-local errors and hard-warning markers were not always blocking.
5. List and detail endpoints did not share all object/identity validation.

Tests and production fixes for these findings were started in the current diff, then paused. Do not discard the new
tests; finish the RED → GREEN cycle and rerun them.

## Exact next actions

1. On the handoff branch, inspect `git status -sb` and the complete diff. Leave `output/` untracked.
2. Finish the Task 5 fixes already started in the eight modified files.
3. Run the focused Task 5 tests, then the full backend suite. Record exact outputs.
4. Run an independent review of Task 5 and resolve all Important/Critical findings.
5. Implement and run Task 6 difficult-corpus replay. Produce the required audit with explicit denominators,
   fallback counts, reliability buckets, source-integrity failures, unsafe promotions, and before/after serving hashes.
6. Run the required real HTTP list/detail API verification and confirm Arelle is absent from FastAPI imports.
7. Only after the reliability phase gates pass, execute the Batch 01 plan:
   [`2026-08-14-batch-01-ten-company-valuation.md`](../superpowers/plans/2026-08-14-batch-01-ten-company-valuation.md)
8. Stop after Batch 01. Do not begin Batch 02 unless the user explicitly asks.

## Resume commands

```bash
cd "/Users/carlosconda/Desktop/Investing Application/.worktrees/whole-universe-greenlight"
git status -sb
git log -8 --oneline --decorate
git diff --check
git diff --stat
```

After finishing Task 5 fixes:

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_api.py \
  backend/tests/test_automated_review.py \
  backend/tests/test_bridge_policy_artifacts.py \
  backend/tests/test_us_valuation.py

PYTHONPATH=backend pytest -q backend/tests
```

Use the exact commands in the phase plan for the replay and API gates. Before claiming completion, exercise the real
consumer path and record evidence; do not infer production readiness from unit tests alone.

## Important files

- [`evidence-aware-reliability-pipeline.md`](../superpowers/plans/2026-08-14-evidence-aware-reliability-pipeline.md) —
  phase plan and gates.
- [`2026-08-14-batch-01-ten-company-valuation.md`](../superpowers/plans/2026-08-14-batch-01-ten-company-valuation.md) —
  exact first-batch contract.
- [`task-5-report.md`](../.superpowers/sdd/2026-08-14-evidence-aware-reliability-pipeline/task-5-report.md) —
  historical Task 5 report; reconcile it against the newer ledger and current diff.
- [`backend/app/us_valuation/artifacts.py`](../backend/app/us_valuation/artifacts.py) — public artifact serialization.
- [`backend/app/us_valuation/automated_review.py`](../backend/app/us_valuation/automated_review.py) — automated review
  and blocking logic.
- [`backend/app/routers/us_valuations.py`](../backend/app/routers/us_valuations.py) — serving endpoints.

## Reporting rule for Claude

Always separate:

- **Verified:** directly observed command output or a reviewed file.
- **Unverified:** planned, inferred, or not rerun after the latest change.
- **Blocked:** cannot proceed without resolving a concrete failure or receiving user direction.

Explain valuation problems in simple language. In particular, `104 passed`, `104 withheld`, and `0 published` are not
interchangeable numbers; always state the denominator and meaning.
