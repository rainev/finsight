# Structural XBRL resolution handoff

## Resume location

- Branch: `feat/structural-xbrl-resolution`
- Worktree: `/Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution`
- Final implementation commits:
  - `5f80961 fix: harden structural XBRL evidence pipeline`
  - `ad319a1 fix: close structural XBRL review gaps`
  - `a1b69d7 feat: enable SEC transforms in structural XBRL pilot`
- Design: `docs/superpowers/specs/2026-08-10-structural-xbrl-concept-resolution-design.md`
- Plan: `docs/superpowers/plans/2026-08-10-structural-xbrl-concept-resolution.md`
- SDD ledger: `.superpowers/sdd/2026-08-10-structural-xbrl-concept-resolution/progress.md`

## Completed implementation

Tasks 1–6 remain complete and independently approved. Final-review findings were
addressed in `5f80961` and the scoped re-review fixes in `ad319a1`:

- recursively bounded SEC/taxonomy dependency acquisition with governed HTTPS
  domains, redirect validation, hashes, source/local URL mappings, taxonomy
  version provenance, and fail-closed closure verification;
- immutable, atomically published filing-package generations;
- offline Arelle URL remapping against the verified local package;
- protected cache/output path validation, including resolved symlink aliases;
- filing-form gating for 10-K, 10-K/A, 10-Q, and 10-Q/A;
- fuller immutable fact/relationship/mapping evidence;
- exact fact deduplication and evidence-class ambiguity handling;
- a hermetic package-builder → offline Arelle → resolver → shadow-report test.
- taxonomy redirects are rejected before urllib follows an ungoverned target;
- filing-directory indexes are streamed under a 2 MiB bound;
- equal-ranked candidates are ambiguous only when their values conflict.

Company Facts remains the production authority. Structural results remain
shadow-only and cannot alter or clear publication gates. No LLM, embedding,
fuzzy, or semantic-value acceptance path was added.

## Verification at implementation commit

- Focused structural suite after scoped re-review fixes: `193 passed in 3.99s`.
- Hermetic real-boundary integration: `1 passed in 0.27s`.
- Targeted filing/valuation regressions from repository root:
  `84 passed, 3 skipped, 1 pre-existing failure`.
- Full backend suite after scoped re-review fixes:
  `336 passed, 3 skipped, 1 pre-existing failure`.
- The sole failure remains
  `test_microsoft_public_artifact_contains_no_raw_financial_amounts`, which
  expects the unrelated, uncommitted `automated_review` integration from the
  user's main worktree (`KeyError: 'automated_review'`).
- The plan-prescribed `backend/tests/test_bridge_recovery.py` is still absent
  from this isolated branch and was not copied from unrelated main-worktree
  changes.
- `git diff --check` passed.
- No files under `backend/app/data/us_valuations/` or
  `frontend/public/data/` changed.
- Generated `output/` remains untracked and was excluded from commits.

## Real filing pilot (2026-08-11)

The selected ANET, CRM, DELL, FTNT, and WDC filings were downloaded into the
non-serving structural cache and parsed offline. Final pilot run 5 produced:

- 5/5 filings parsed and 0 parser failures;
- 4,421 bounded numeric structural facts: ANET 576, CRM 772, DELL 1,040,
  FTNT 1,043, and WDC 990;
- accepted current marketable securities for ANET (`$9,563.7m`) and CRM
  (`$2,902m`) through the governed `AvailableForSaleSecuritiesDebtSecuritiesCurrent`
  taxonomy alias;
- review-grade, value-matched current short-term investments for FTNT
  (`$1,134.7m`) through `OtherShortTermInvestments`; the resolver did not
  auto-accept it because the current rules require stronger governed support;
- rejected false candidates for ANET noncurrent marketable securities and DELL
  current marketable securities rather than inferring zeros from unrelated
  zero-valued facts.

The earlier run-4 candidate scan ranked facts partly by whether they matched the
known truth-set value. Independent review correctly identified that method as
circular and prone to elevating unrelated zero-valued facts. Run 5 supersedes
it: candidate discovery now uses only field terms, period, unit, dimensions,
and statement placement. Expected values do not affect discovery or ranking.
At run 5, all non-marketable candidate lists were observations only. Tasks 2–4
subsequently added account-specific governed resolvers, and run 24 now verifies the
accepted/non-accepted bridge baseline recorded in `docs/plans/EVIDENCE.md`. The enduring
rule remains that zero/absence cannot be accepted merely because an unrelated fact has
value zero.

The first real run exposed two integration gaps that now have regression tests:

- legacy allowlisted XBRL taxonomy identifiers using `http://` are upgraded to
  governed `https://` retrieval URLs;
- relative filing-package paths are resolved before the worker changes its
  working directory.

Plain `arelle-release==2.44.0` excludes the SEC EDGAR transform plugin. The
runtime-only official `Arelle/EDGAR/transform` plugin is therefore vendored at
commit `72033f579e89ab47e882437b5d4ceed9c7656ed5`, loaded inside the isolated
worker, and covered by a representative SEC transform fixture. No parser
errors are ignored or downgraded.

Raw pilot evidence is intentionally untracked under
`output/structural-xbrl-pilot/results-run5/`. Publication effect remains
`none_shadow_only`; no serving valuation artifact changed.

## Pilot verification

- Focused structural suite: `200 passed in 5.97s`.
- Full backend suite from repository root: `343 passed, 3 skipped, 1
  pre-existing failure`.
- The sole failure is still the unrelated missing `automated_review` field in
  `test_microsoft_public_artifact_contains_no_raw_financial_amounts`.
- Real run-5 assertions confirmed 5/5 parsed, governed marketable values matched
  the truth set, candidate ranking contains no expected-value signal, and the
  publication effect is shadow-only.
- `git diff --check` passed and no serving valuation path changed.

## Five-company pilot selected

Use the existing filing-specific evidence as the truth set for:

- ANET — marketable securities, debt, and finance-lease zero/inference cases;
- CRM — marketable securities, commercial-paper classification, and finance
  lease total/split;
- DELL — debt, zero current marketable securities, and NCI;
- FTNT — `ShortTermInvestments` as current marketable securities, debt, and NCI;
- WDC — debt and temporary/preferred-equity interpretation.

Evidence lives in `/Users/carlosconda/Desktop/Investing Application/output/evidence-recovery/`.
The first pilot resolved only current/noncurrent marketable securities. The final run 24
also exercises governed debt, lease, preferred/temporary-equity, commercial-paper, and
NCI policies. Only accepted decisions may be described as recovered; review and rejected
decisions remain non-publishable evidence.

## Exact next step

Task 6 is complete at commits `1544335`, `432e9db`, and `8155326`. The final offline replay is
`output/structural-xbrl-pilot/results-run24/`; all five filings parsed and the approved
debt, lease, preferred/temporary-equity, commercial-paper, and NCI baseline passed.

Full evidence is recorded in `docs/plans/EVIDENCE.md`. Status is **verified — your
confirmation needed**, not production-approved.

1. Obtain user confirmation of the five-company result.
2. Run a broader representative company corpus in `none_shadow_only` mode.
3. Keep `OtherShortTermInvestments` review-grade until cross-company evidence supports
   promotion.
4. Address the unrelated `automated_review` public-artifact test in its own scope.
5. Consider production integration only after broader shadow evidence is reviewed.
