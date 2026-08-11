# Structural bridge-account resolvers — in-progress handoff

Date: 2026-08-11 (Asia/Manila)

Status: in progress. Tasks 1–5 are implemented, independently reviewed, and committed. Task 6 and the final broad review remain.

## Resume instruction

Use FinSight Efficiency Mode, GoodBehavior, and subagent-driven development. Resume the approved plan at Task 6; do not redo Tasks 1–5.

Plan:

`docs/superpowers/plans/2026-08-11-structural-bridge-account-resolvers.md`

Design:

`docs/superpowers/specs/2026-08-11-structural-bridge-account-resolvers-design.md`

Worktree:

`/Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution`

Branch:

`feat/structural-xbrl-resolution`

Latest independently reviewed implementation checkpoint:

`ecb183d feat: evaluate bridge accounts in structural shadow`

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

## Remaining sequence

1. Execute Task 6 using Sol High locally: full backend tests and offline replay of cached ANET, CRM, DELL, FTNT, and WDC filings.
2. Record `docs/plans/EVIDENCE.md` and update the main structural-XBRL handoff.
3. Run a broad final review from design commit `1d7de4f` through HEAD.
4. End with GoodBehavior status `verified — your confirmation needed`; do not claim production publication approval.

## Copy-paste continuation prompt

```text
Resume FinSight structural XBRL work from the saved handoff on branch `feat/structural-xbrl-resolution`.

Repository: `/Users/carlosconda/Desktop/Investing Application`
Worktree: `/Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution`
Handoff: `docs/superpowers/handoffs/2026-08-11-structural-bridge-resolvers-in-progress-handoff.md`
Plan: `docs/superpowers/plans/2026-08-11-structural-bridge-account-resolvers.md`
Reviewed implementation checkpoint: `ecb183d`

Use FinSight Efficiency Mode, GoodBehavior, and subagent-driven development. Read the handoff and inspect the branch first. Do not redo Tasks 1–5; they are committed and independently reviewed. Resume at Task 6: run the full backend regression suite and replay the cached ANET, CRM, DELL, FTNT, and WDC filings offline against the approved accounting baseline. Record durable evidence, update the main handoff, and run the broad final review. Keep `publication_effect: none_shadow_only`; do not change production valuation inputs. Never stage `output/` or `.superpowers/`. Use `pytest` directly. End with `verified — your confirmation needed`, not production approval.
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
