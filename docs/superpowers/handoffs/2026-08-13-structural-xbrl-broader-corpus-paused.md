# Structural XBRL broader-corpus pause handoff

Date: 2026-08-13 (Asia/Manila)

Status: **paused by user during Task 1 — no Task 1 implementation code was completed**.

## Resume location

- Worktree: `/Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution`
- Branch: `feat/structural-xbrl-resolution`
- Plan: `docs/superpowers/plans/2026-08-13-structural-xbrl-broader-corpus.md`
- SDD ledger: `.superpowers/sdd/2026-08-13-structural-xbrl-broader-corpus/progress.md`
- Task 1 brief: `.superpowers/sdd/2026-08-13-structural-xbrl-broader-corpus/task-1-brief.md`
- Plan commits: `bc0d149`, `62ec4b2`

Use FinSight Efficiency Mode, GoodBehavior, and subagent-driven development. Do not redo the five-company pilot or the completed 20-company baseline replay.

## Completed in this continuation

The representative corpus was staged from compatible private recovery artifacts and run through the real SEC package cache, offline Arelle parser, shared resolver, and immutable shadow reporter.

Runtime evidence:

`output/structural-xbrl-broad-corpus/results-baseline/`

Verified baseline:

- 20 discovered, 20 eligible, 20 parsed, 0 parser failures, 0 skipped.
- 97 governed field requests: 0 accepted, 9 review, 86 rejected, 2 unresolved.
- Initial input state: 58 `missing`, 40 `verification_stale`; one unsupported `cash` gap was not a governed request.
- Publication effect remained `none_shadow_only` for every company.
- All 13 supported FCFF archetypes were represented.
- No production valuation input or serving artifact changed.

Representative corpus:

`A, ABBV, AMZN, APD, BA, CAT, CCL, CRDO, CSCO, DXCM, FDX, KDP, MCD, META, NVDA, ORCL, PLTR, SBUX, TMUS, UAL`

## Verified findings that drive Task 1

1. `_is_plausible_extension()` currently lets `excluded_economic_phrases` and `review_only_phrases` create candidates by themselves. This contaminates diagnostics with unrelated receivables, operating leases, fair-value disclosures, and other negative evidence. These phrases may classify an already positive candidate but must not admit one.
2. Ambiguity currently depends on whether equal-ranked candidates have different numeric values. Numeric equality must not establish semantic equivalence. After exact fact-identity deduplication, multiple distinct highest-ranked candidates must remain ambiguous.
3. NVIDIA supplies the standard, current-period, USD balance-sheet fact `us-gaap:PreferredStockValueOutstanding = 0`. The plan allows adding only this deterministic preferred-equity alias and its stable carrying-amount reason code.
4. Do not promote `NonMarketableSecurities`, common-stock concepts, generic debt totals, `ShortTermBorrowings` as commercial paper, or combined debt-and-lease concepts without further evidence.

## Full-corpus boundary

The current public flagged count is 125. Of those, 104 have compatible private US-GAAP recovery artifacts with at least one supported structural bridge gap:

- 104/104 are model-route eligible.
- 100 use 10-Q and 4 use 10-K.
- The remaining 21 are outside this resolver replay because they lack a compatible private artifact or lack a supported structural bridge gap. They must be reported separately, not treated as parser failures or silently dropped.

## Exact paused state

- Task 1 task brief was generated.
- A Luna High accounting reviewer and a Luna High Task 1 implementer were both still running when the user paused; both were explicitly shut down.
- Neither agent produced a durable report or implementation commit.
- No source-code files were modified after the plan commits.
- `output/` remains intentionally untracked and must never be staged.

## Exact next action

1. Resume at Task 1 from the existing task brief; do not rerun baseline acquisition.
2. Dispatch a fresh Luna High implementer with strict TDD and the existing report path.
3. Run the Task 1 spec/quality review loop before starting Task 2.
4. Complete Task 2 case-level shadow eligibility.
5. Re-run the cached 20-company corpus into a new immutable output directory.
6. Expand to the 104-company supported corpus only after the 20-company gate is verified.

## Copy-paste continuation prompt

```text
Resume FinSight structural XBRL work from the paused broader-corpus handoff.

Worktree: /Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution
Branch: feat/structural-xbrl-resolution
Handoff: docs/superpowers/handoffs/2026-08-13-structural-xbrl-broader-corpus-paused.md
Plan: docs/superpowers/plans/2026-08-13-structural-xbrl-broader-corpus.md

Use FinSight Efficiency Mode, GoodBehavior, and subagent-driven development. Do not redo the five-company pilot or the completed 20-company baseline. Resume at Task 1 from its existing SDD task brief. The prior Task 1 implementer and accounting reviewer were interrupted before producing reports or code, so dispatch fresh agents. Preserve none_shadow_only behavior, never infer absence as zero, never use numeric equality as semantic evidence, and never stage output/ or .superpowers/.
```
