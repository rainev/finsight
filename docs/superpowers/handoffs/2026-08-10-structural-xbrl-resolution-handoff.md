# Structural XBRL resolution handoff

## Resume location

- Branch: `feat/structural-xbrl-resolution`
- Worktree: `/Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution`
- Clean HEAD: `60466ce fix: enforce exact XBRL integer boundary`
- Design: `docs/superpowers/specs/2026-08-10-structural-xbrl-concept-resolution-design.md`
- Plan: `docs/superpowers/plans/2026-08-10-structural-xbrl-concept-resolution.md`
- SDD ledger: `.superpowers/sdd/2026-08-10-structural-xbrl-concept-resolution/progress.md`

## Completed and independently approved

1. Parser boundary and immutable provenance schema.
   - Commits: `d373ebf`, `4f659ed`
2. Deterministic marketable-securities resolver.
   - Commits: `2fc7d1d`, `151b381`, `9ff67a0`, `512338d`, `74a9923`
   - Exact governed US-GAAP namespace registry; no fuzzy or LLM acceptance.
3. Process-isolated Arelle 2.44.0 adapter and local representative Inline XBRL package.
   - Commits: `2c10552`, `ec92866`, `76745ed`, `ec1f0b4`, `60466ce`
   - Parent application imports no Arelle code.
   - Child process is offline, time-bounded, resource-bounded on POSIX, environment-sanitized, and JSON-only.
   - Extracts contexts, units, labels, documentation, presentation, calculation, definition, and dimensional relationships.
   - Corrects Arelle's exclusive period boundaries and conservatively diagnoses values that cannot cross the numeric JSON boundary exactly.

## Verification at pause

- Task 1–3 focused suite: `127 passed`.
- Arelle adapter suite: `32 passed` in the final independent review.
- Root backend suite: `270 passed, 3 skipped, 1 pre-existing unrelated failure`.
- The pre-existing failure expects the user's uncommitted `automated_review` integration and predates this branch.
- Independent Task 3 reviewer: approved with no substantive findings.
- Worktree was clean when paused.
- `arelle-release==2.44.0` was installed from `backend/requirements-xbrl.txt` and verified importable in the current Python 3.11 environment.

## Current production impact

- None. The structural resolver is not connected to valuation publication or approval gates.
- Existing Company Facts normalization and serving artifacts are unchanged.
- This is intentional until the shadow path is measured.

## Exact next step

Resume Task 4: cache complete SEC filing packages reproducibly.

- Generated brief: `.superpowers/sdd/2026-08-10-structural-xbrl-concept-resolution/task-4-brief.md`
- Task 4 agent was stopped before creating or modifying any files.
- Implement `SecClient.filing_index`, `SecClient.filing_attachment`, and `filing_package.py` with safe names, deterministic manifests, hashes, bounded resource selection, and fail-closed incomplete-package behavior.
- Then perform a fresh independent Task 4 review before Task 5.

After Task 4:

5. Add the shadow-only structural resolution path and CLI.
6. Run regression verification, bounded shadow measurement, and documentation.
7. Run final strongest-model whole-branch review and verification.

## Suggested resume prompt

`Resume the structural XBRL resolution work from docs/superpowers/handoffs/2026-08-10-structural-xbrl-resolution-handoff.md in the existing feat/structural-xbrl-resolution worktree. Use FinSight Efficiency Mode and subagent-driven development. Start at Task 4; do not redo approved Tasks 1–3.`
