# Structural bridge-account resolvers — in-progress handoff

Date: 2026-08-11 (Asia/Manila)

Status: in progress. Tasks 1–4 are implemented, independently reviewed, and committed. Task 5 is being implemented but is not yet reviewed or committed. Task 6 and the final broad review remain.

## Resume instruction

Use FinSight Efficiency Mode, GoodBehavior, and subagent-driven development. Resume the approved plan at Task 5; do not redo Tasks 1–4.

Plan:

`docs/superpowers/plans/2026-08-11-structural-bridge-account-resolvers.md`

Design:

`docs/superpowers/specs/2026-08-11-structural-bridge-account-resolvers-design.md`

Worktree:

`/Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution`

Branch:

`feat/structural-xbrl-resolution`

Verified checkpoint before active Task 5 edits:

`70013ec fix: reject preferred stock share counts`

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

Latest verified focused result at Task 4 close:

```text
pytest -q tests/test_concept_resolver.py tests/test_structural_xbrl_schema.py
193 passed
```

## Active Task 5 — not yet approved

Goal: expose all governed bridge fields through the shadow runner and hermetic Arelle integration while retaining `publication_effect: none_shadow_only`.

Task brief:

`.superpowers/sdd/2026-08-11-structural-bridge-account-resolvers/task-5-brief.md`

Active implementer at handoff creation:

- Agent `019ff087-8777-75a3-b96f-b8e7a0fb68fa` (Sartre)
- Model: Terra Medium

The following Task 5 files are currently modified and must be treated as unverified until the implementer reports, the controller reruns tests, the changes are committed, and a fresh reviewer returns clean:

- `backend/app/us_valuation/structural_shadow.py`
- `scripts/run_structural_xbrl_shadow.py`
- `backend/tests/test_structural_shadow.py`
- `backend/tests/test_structural_xbrl_integration.py`
- `backend/tests/fixtures/us/structural-xbrl/fsi-20251231.htm`
- `backend/tests/fixtures/us/structural-xbrl/fsi-2025_pre.xml`
- `backend/tests/fixtures/us/structural-xbrl/fsi-2025_lab.xml`
- `backend/tests/fixtures/us/structural-xbrl/us-gaap-2025.xsd`

Do not stage or commit these active files merely because they exist. First collect the Task 5 report and run the focused structural suite.

## Remaining sequence

1. Finish Task 5 RED→GREEN implementation.
2. Independently inspect and test the Task 5 delta.
3. Commit only after tests pass; run a fresh scoped review and fix/re-review if needed.
4. Execute Task 6 using Sol High locally: full backend tests and offline replay of cached ANET, CRM, DELL, FTNT, and WDC filings.
5. Record `docs/plans/EVIDENCE.md` and update the main structural-XBRL handoff.
6. Run a broad final review from design commit `1d7de4f` through HEAD.
7. End with GoodBehavior status `verified — your confirmation needed`; do not claim production publication approval.

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
