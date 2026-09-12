# Automated U.S. valuation

Checked against the code 2026-09-09: migration retains 419/419 exact numeric recipes. Current compilation reports **231 executable-shaped contracts and 188 implementation gaps**, not 231 certified refreshes. The new deterministic work register separates these from current source proof: **4 current-version source-bound**, **0 explicit successive-period verified**, 11 current NCI-group financial reviews, and 425 older results needing version recheck. Eleven clean NCI-only rules and their history-growth policies produced the compilation increase; all eleven still stop on named cash/debt/lease/investment/preferred bridge evidence. The stage command remains blocked with `activated:false`. Full automatic refresh/publication remains unverified and gated.

Efficiency path: `refresh_us_valuations.py --work-status`, immutable compact source index, and two frozen cached workers are implemented. Current 15-company report `output/us-refresh-group-verification/5a2829b8226cfd5449dd4856d1037cd11fbe42e133cd0ca5cf8d33710b528445/report.json` accounts for 4 bound + 11 financial reviews. Cold wall time 30.83s; identical hash-validated reuse 0.59s. Timings are kept outside deterministic report content.

Current-code UI/API/PostgreSQL regression: Adobe base-only discount edit, manual-price comparison, save/readback, reset and dated history passed in the redesigned 4178 frontend with the isolated 4179 API restarted. Saved UAT rows 11/12 are retained; direct model math and user-scoping checks passed. See `output/us-refresh-ui-20260909/persistence.json`. This validates the existing preview calculator/persistence path, not blocked successor financial values.

Current verified operational evidence: `output/us-refresh-operational-uat-20260908T190247Z-635274b0/uat-report.json` exercises real FastAPI activation/reload/rollback and an injected unavailable state followed by recovery from captured Microsoft evidence. The unavailable API record clears numeric surfaces and labels the old filing historical. This is an isolated operational UAT, not a full-universe financial refresh or production approval. Production serving artifacts remain untouched.

Reference: approved plan in this task. Scope fixed to the confirmed Batch 01–44 catalog: 440 issuers, 419 numeric. Batch 45 work is preserved outside this scope.

| Phase | Work | Source gap | Evidence gate | Status |
|---|---|---|---|---|
| A | GoodBehavior reconciliation, exact baseline and recipe inventory | AR1–AR4 | source hashes, all 440 records and active-catalog protection | 419/419 numeric recipes replay; all 440 historical records preserved; user acceptance pending |
| B NOW | Registry, immutable refresh/replay/checkpoint flow | AR1 | changed quarter without edits, failure/resume and exact replay | acquisition resume, lazy structural parsing/cache, source hashes, event relationship capture and source-check CLI built; complete issuer coverage remains open |
| C | Sustainable-input normalization | AR2 | real input reconciliation and adjustments | shared balance-only normalizer, annual cash profile, common-equity reconciliation and AAPL/APTV dispatch exercised; special claim/commitment migration remains open |
| D | Exact scenario calculator and dated comparison | AR3 | independent calculations, stale version, API/browser | Current main-checkout redesign now integrated and locally verified with staged API, per-case edits, reset, history and DB save/readback; user acceptance pending |
| E | Forecast evaluation, guarded automatic activation/history | AR4 | actual vintages, atomic publication/rollback, real DB | forecast coordinator wired with frozen prior evidence; synthetic later-actual tests are not a historical track record; complete successor flow remains open |

Default command stages. Initial acceptance is required before routine auto-publication. New economic failures show unavailable; transient fetch failures retain explicitly stale prior results. No schedule, new paid source, AI runtime, auto tuning or deployment.

Preserve existing AGENTS.md, profiles, hooks and docs/learnings. Upstream GoodBehavior updated 601e9740 -> 75b3697f (seven skills; no conflicts). Do not reorganize unrelated historical roadmap material during this initiative.

Current evidence and remaining gates: [implementation evidence](../audit/automated-implementation-evidence.md). The CLI currently refuses staging/publication; it is not a functioning unattended update release yet. The SEC contact has been supplied and seven live issuer captures verified. The existing 100-company serving catalog is unchanged; the separate 440-company preview is UAT only.

Current UI acceptance reference and evidence: [redesigned UI integration](../audit/redesigned-ui-pipeline-integration.md). Earlier worktree-only browser evidence is not acceptance of the newer UI; the new checks use the main-checkout redesign as requested by the user.
