# Structural XBRL resolution handoff

## Resume location

- Branch: `feat/structural-xbrl-resolution`
- Worktree: `/Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution`
- Final implementation commits:
  - `5f80961 fix: harden structural XBRL evidence pipeline`
  - `ad319a1 fix: close structural XBRL review gaps`
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

## Real-data limitation

The last bounded offline corpus run discovered 118 withheld artifacts but had
0 eligible structural cases because sanitized serving artifacts omit private
bridge fields and controlling-filing metadata. Runtime was 0.09 seconds and the
cache remained empty (0 files / 0 KiB). This is not evidence that Arelle can
recover the formerly missing accounts from real filings.

Keep the feature shadow-only until a real filing pilot is reconciled manually.

## Five-company pilot selected

Use the existing filing-specific evidence as the truth set for:

- ANET — marketable securities, debt, and finance-lease zero/inference cases;
- CRM — marketable securities, commercial-paper classification, and finance
  lease total/split;
- DELL — debt, zero current marketable securities, and NCI;
- FTNT — `ShortTermInvestments` as current marketable securities, debt, and NCI;
- WDC — debt and temporary/preferred-equity interpretation.

Evidence lives in `/Users/carlosconda/Desktop/Investing Application/output/evidence-recovery/`.
The first pilot can deterministically resolve only current/noncurrent marketable
securities; the other accounts must be inspected as raw structural evidence
until governed resolvers are added. Do not describe those accounts as recovered
merely because Arelle emits a semantically similar fact.

## Exact next step

1. Supply a compliant SEC User-Agent with a monitored contact.
2. Download complete bounded packages for the five selected filings into a
   non-serving cache.
3. Run Arelle offline on all five packages.
4. Run the deterministic marketable-securities resolver where eligible.
5. Reconcile selected facts, units, periods, contexts, and values against the
   filing-specific evidence artifacts.
6. Record accepted, review, rejected, unresolved, and parser-failure counts.
7. Keep the path shadow-only and request user confirmation before any promotion.
