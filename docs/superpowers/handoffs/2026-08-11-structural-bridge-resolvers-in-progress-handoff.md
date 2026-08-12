# Structural bridge-account resolvers — in-progress handoff

Date: 2026-08-11 (Asia/Manila)

Status: Task 6 verified — user confirmation needed. Tasks 1–6 are implemented, reviewed,
and committed; production promotion has not been approved.

## Resume instruction

Use FinSight Efficiency Mode, GoodBehavior, and subagent-driven development. Do not redo
Tasks 1–6. Read `docs/plans/EVIDENCE.md`, then continue with a broader shadow-only corpus
after user confirmation.

Plan:

`docs/superpowers/plans/2026-08-11-structural-bridge-account-resolvers.md`

Design:

`docs/superpowers/specs/2026-08-11-structural-bridge-account-resolvers-design.md`

Worktree:

`/Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution`

Branch:

`feat/structural-xbrl-resolution`

Latest independently reviewed implementation checkpoints:

- `1544335 fix: harden structural bridge resolution`
- `432e9db fix: classify structural relationship roles safely`
- `8155326 fix: preserve fail-closed relationship roles`

## Completed work

### Task 1 — common resolver contract

- Policy-driven structural resolver contract.
- Exact configured dimensions are required for contextual concepts.
- Final committed range: `fe2d1a6..04177e9`.
- Independent review: clean.

### Task 2 — debt and commercial paper

- Governed current debt, noncurrent debt, and commercial paper.
- Maturity schedules and component-only facts cannot become aggregate balances.
- CRM's investment-style commercial paper is excluded from borrowing.
- Evidence reason codes are policy-specific and truthful.
- Final committed range: `04177e9..3fd34d8`.
- Independent review: clean.

### Task 3 — finance leases

- Governed current, noncurrent, and total finance-lease carrying values.
- CRM's $664 million net liability is the intended accepted total.
- Gross payments and current/noncurrent payment schedules cannot satisfy carrying-value requests.
- Current and noncurrent aliases have accounting-context gate coverage.
- Final committed range: `3fd34d8..5f7a67e`.
- Independent review: clean.

### Task 4 — preferred/temporary equity and NCI

- ANET preferred-stock carrying value zero and WDC temporary-equity carrying value zero are governed values.
- Liquidation preference, redemption amounts, proceeds, EPS, and preferred share counts are non-accepted review evidence.
- DELL NCI zero requires the exact `StatementEquityComponentsAxis/NoncontrollingInterestMember` dimensions and the equity roll-forward parent.
- Legacy unsegmented NCI aliases cannot bypass the governed contextual mapping.
- Added optional `required_statement_support_parents`; policies without it retain prior behavior.
- Final committed range: `5f7a67e..70013ec`.
- Independent review: clean.

### Task 5 — structural shadow runner and hermetic Arelle integration

- Exposes all ten governed bridge fields through public `SUPPORTED_STRUCTURAL_FIELDS`.
- Every supported gap creates one USD balance-sheet request; unknown gaps remain skipped.
- The CLI retains lazy Arelle imports and `publication_effect: none_shadow_only`.
- The hermetic fixture now includes `DebtCurrent=125,000,000` with schema, labels, and presentation support.
- Offline integration proves two accepted decisions—current marketable securities and current debt—without network access or source mutation.
- Final implementation commit: `ecb183d`.
- Independent review: clean.

Latest verified focused result at Task 5 close:

```text
pytest -q tests/test_structural_xbrl_schema.py tests/test_concept_resolver.py tests/test_arelle_adapter.py tests/test_filing_package.py tests/test_structural_shadow.py tests/test_structural_xbrl_integration.py
290 passed
```

## Task 6 result

- Final focused structural suite: `316 passed`.
- Final full backend suite: `459 passed, 3 skipped, 1 pre-existing unrelated failure`.
- Offline Arelle replay: 5/5 parsed, zero parser failures, 4,421 facts.
- Governed decisions: 13 accepted, 2 review, 11 rejected, 0 unresolved.
- Final runtime evidence: `output/structural-xbrl-pilot/results-run24/`.
- Durable evidence: `docs/plans/EVIDENCE.md`.
- Publication effect remained `none_shadow_only`; no serving valuation artifact changed.
- Final independent re-review after closing the role-name fallback bypass: clean.

The sole full-suite failure remains the unrelated missing `automated_review` public field.

## Copy-paste continuation prompt

```text
Resume FinSight structural XBRL work from the saved handoff on branch `feat/structural-xbrl-resolution`.

Repository: `/Users/carlosconda/Desktop/Investing Application`
Worktree: `/Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution`
Handoff: `docs/superpowers/handoffs/2026-08-11-structural-bridge-resolvers-in-progress-handoff.md`
Plan: `docs/superpowers/plans/2026-08-11-structural-bridge-account-resolvers.md`
Reviewed implementation checkpoints: `1544335`, `432e9db`, `8155326`

Use FinSight Efficiency Mode, GoodBehavior, and subagent-driven development. Read this handoff and `docs/plans/EVIDENCE.md` first. Do not redo Tasks 1–6. The five-company structural bridge pilot is verified but not production-approved. The next safe step is a broader representative-company replay in `none_shadow_only` mode, followed by user review. Keep `OtherShortTermInvestments` review-grade, do not change production valuation inputs, and never stage `output/` or `.superpowers/`.
```

If the branch is checked out in a fresh clone rather than this machine, create a normal worktree or work directly on the branch and supply the cached `output/structural-xbrl-pilot` evidence separately because `output/` is intentionally untracked.

## Safety and workspace notes

- Keep Arelle as the parser; no new XBRL dependency is planned.
- Preserve deterministic policy/accounting logic; no LLM primary mapping.
- Absence is not zero.
- Production valuation inputs must remain unchanged during this phase.
- `output/` is intentionally untracked and contains pilot cache/evidence; never stage it.
- `.superpowers/` is local SDD scratch evidence; do not stage it.
- Use `pytest` directly. The shell's `python -m pytest` path may not contain pytest.
- Subagents cannot reliably write the shared Git index; the controller stages and commits only verified files.

## Accounting baseline for real-file replay

Accepted USD millions:

- Current debt: DELL 7,550; FTNT 0; WDC 1,581.
- Noncurrent debt: CRM 39,280; DELL 23,611; FTNT 496.9; WDC 0.
- Finance-lease total: CRM 664.
- Preferred equity: ANET 0; WDC 0 carrying amount.
- NCI: DELL 0 only with the governed NCI member dimension.

Must remain non-accepted:

- Absence-based debt/lease zeros.
- CRM commercial-paper investment component of 94.
- CRM lease payment-schedule components and gross payments of 718.
- DELL preferred share-count zero.
- FTNT narrative-only NCI zero.
- WDC temporary-equity liquidation preference of 265.
