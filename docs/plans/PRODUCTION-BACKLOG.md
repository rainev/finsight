# FinSight whole-universe production backlog

Only work that does not belong on the approved 500/500 critical path is parked here. Full-universe coverage, specialist model lanes, price comparison, and backtesting are scheduled roadmap work, not deferred aspirations.

## Deferred until the critical path is verified

- **B1 · General documentation cleanup.** Large folder reorganization does not change valuation behavior. Revisit after the reliability pipeline and canonical universe are stable.
- **B2 · Retiring old generated frontend modules.** The active U.S. valuation page reads the API. Remove unused generated modules only after the API/UI contract is finalized and imports are rechecked.
- **B3 · Production deployment.** Feature-branch implementation and local/staging verification do not authorize merging or deploying. Unblocks after all roadmap gates, branch review, and explicit user approval.
- **B4 · Paid institutional market-data integration.** The first governed current-price comparison should use an approved public source. Paid data remains unnecessary unless public-source quality fails the release gate.

## Log-new-tangent rule

If a defect is discovered while executing a phase and it does not block that phase's consumer-visible behavior, record it here with the exact evidence, why it is deferred, and what would move it back to the roadmap. Do not interrupt the current phase for unrelated cleanup.

## Deferred — quality caveats to revisit (not blockers, but carry review flags)

- **B5 · Conservative fallbacks undervalue growth names.** Residual-income / DDM fallbacks (HD $155, MCD $121, WMT $42)
  are systematically conservative for low-payout / high-growth companies. Fine as `review_required` floors; revisit if
  they're surfaced as headline values.
- **B6 · Candidate archetype cohort contamination.** `specialty_chemicals` mixes industrial chem + household/personal
  care; `internet_digital_services` is META/GOOGL-heavy (n=5); `transportation` mixes rail/airline; `retail` mixes
  discount/franchise. Split + recalibrate before promoting to `pass`.
- **B7 · `sales_to_capital` and dividend-growth are governed policy, not per-issuer.** Documented; refine with
  per-issuer evidence before final publish.
- **B8 · Preserve contradiction-trigger evidence in structural rejection reports.** HPE is safely rejected when its
  displayed preferred-stock zero conflicts with same-filing preferred-instrument evidence, but the corrected report
  row currently has `evidence: null`. Retain the triggering companion fact, context, period, and accession directly in
  future rejection artifacts before relying on those artifacts for analyst-facing audit trails.
- **B9 · Reject clearly liability-like preferred-equity review noise.** The corrected DE candidate remains safely
  review-grade and withheld, but its documentation and `LiabilitiesAbstract` parent identify a liability rather than
  genuine preferred-equity ambiguity. Add a deterministic economic-class rejection after broader regression coverage.

- **B10 · Historical BP4 bounded-review baseline (superseded by Phase 1).**
  *Why retained:* the pre-Phase-1 replay had 104 legacy private artifacts, zero bounded candidates, and five requested
  current private artifacts absent. This is historical evidence of the fail-closed baseline, not a current publication
  rule or reliability threshold.
  *Revisit when:* the Phase 1 policy is replayed on current source-linked artifacts; do not treat the old 1% spread
  criterion as a live acceptance rule.

- **B11 · Recover stale bridge-shadow writer locks automatically.**
  *Why deferred:* an abrupt process termination can leave `.bridge-policy-shadow.lock`; this fails safely and requires
  an operator to verify no writer is active before removing the lock. It does not risk serving writes or overwrite
  immutable output.
  *Reconsider when:* the replay CLI becomes scheduled or routinely concurrent and needs PID-aware stale-lock recovery.

- **B12 · Retire or rewrite the older Batch 01 all-or-nothing implementation plan.**
  *Why deferred:* `docs/superpowers/plans/2026-08-14-batch-01-ten-company-valuation.md`
  remains useful implementation research, but its branch assumptions and requirement that all
  ten pass before any promotion conflict with the user-approved controlled reset. The active
  roadmap and controlled-reset rules govern; the old file must not silently drive promotion.
  *Reconsider when:* Batch 01 is reported and the historical plan can be annotated or archived
  without losing useful design evidence.

- **B13 · Canonical 500-universe proof.**
  **Resolved 2026-08-24 by explicit user authorization.** Exhaustive local/Git review found no
  original historical 500-row artifact, so the workflow stopped before selection. The user then
  authorized a replacement S&P 500 issuer universe effective 2026-08-14. A pinned public table,
  official S&P cutoff-change evidence, and captured SEC mapping reconcile 503 securities to 500
  CIKs; the canonical manifest and all Batches 02–50 are frozen and independently challenged.

- **B14 · Batch 01 SEC acquisition lacks a monitored contact.**
  **Resolved 2026-08-20.** The user supplied a monitored contact, the capture completed 10/10,
  and a cached rerun reproduced the same immutable packets without serving changes. Retained as
  history because future fresh acquisition still requires an explicit monitored contact; never
  invent one or bypass this provenance gate.

- **B15 · Representative browser UAT for controlled Batch 01.**
  *Why deferred:* the worktree has no installed frontend runtime (`vite: command not found`) and
  the U.S. valuation route is authentication-protected. No UI code changed in this phase, and a
  faked login would not be real consumer evidence. The real staged FastAPI path is verified.
  *Reconsider when:* frontend dependencies and a local authenticated test user/database are
  available; then exercise the 10-item selector and withheld detail state in the browser.

- **B16 · NEE specialist FPL/NEER sum-of-parts.**
  *Why deferred:* direct Q2 extraction fixed the period defect, but the approved consolidated
  FCFE fallback produces nonpositive bear/base common cash flow once commercial paper and parent/
  NCI allocation are complete. A dividend-only value would conceal the mixed-business problem.
  *Reconsider when:* source-linked FPL regulated equity/rate-base economics, Energy Resources
  project cash flow, parent claims, and segment financing can be reconciled into a provisional
  specialist SOTP and independently challenged.

- **B17 · Batch 02 real localhost HTTP acceptance.**
  **Resolved 2026-08-24 after explicit user approval.** Uvicorn served the exact staged ten on
  `127.0.0.1:8765`; list count was 10, all 10 details returned HTTP 200 with exact range/state/
  reliability parity, no private fields leaked, zero Arelle modules loaded in the serving import,
  and the process shut down cleanly.

- **B18 · Reconstruct the exact difficult-corpus official-package denominator.**
  **Denominator resolved by FOD5.** The retained period-aware report proves exactly 106 candidates. Combined with Batch 01/02 and the withheld subset, the de-duplicated manifest has 121 unique issuers and 133 cohort memberships.

- **B19 · Capture unified official-evidence packets for the remaining difficult 101.**
  **Resolved after the user supplied a monitored SEC contact.** All 106 source packets and 205 unique controller/annual packages were frozen, the initial 11 XBRL-ZIP package failures were repaired safely, and the complete evidence/consumer/API replay passed twice without serving changes.

- **B20 · Obtain promotable specialist source payloads.**
  *Why blocked:* FR Y-9C bulk access returned HTTP 403, FERC CID/payload/allocation is unresolved, and the SEC-filed Realty Income supplement is link-verified but not frozen locally with a complete AFFO reconciliation.
  *Unblocks when:* immutable official payloads, parent identity/allocation, cutoff, units, and reconciliations pass the specialist contracts.

- **B21 · Supply approved private U.S. EOD and peer records.**
  *Why blocked:* the worktree contains no private vendor EOD dataset, peer cohort, or provider
  client/credentials. The launch-first implementation can validate and consume provider-neutral
  private records, but it must not fabricate prices or silently substitute an unapproved source.
  *Unblocks when:* approved records include canonical security/listing, USD currency,
  split-adjusted close, price date, provider, and payload hash under the private contract.

- **B22 · Batch 04 promotion resolved; merge, push, and deployment remain separate.**
  *Current state:* the user explicitly confirmed and promoted the exact Batch 04 history-backed
  candidate on 2026-08-26. Ten default backend serving artifacts and the real API are verified.
  *Why still blocked:* promotion did not authorize merge, push, staging deployment, production
  deployment, Batch 05/06 retry, or Batch 07 processing. Main pushes auto-deploy staging.
  *Unblocks when:* the user separately authorizes the specific outward-facing or next-batch action.

- **B23 · Real Postgres U.S. saved-run migration and persistence acceptance.**
  *Why blocked:* this machine has no Docker command or reachable local Postgres. Nullable U.S.
  columns, migration SQL, `save_us`, API scoping, safe payload tests, and the browser save response
  pass, but no real row was inserted/read back.
  *Unblocks when:* a staging/local database is available; run migrations, save a custom U.S. result,
  read it through `/api/valuations`, verify user scoping and fields, then delete the test row.

- **B24 · Normalize `filed_date` into inherited structural flow rows.**
  *Why deferred:* Batch 12 recovery retains the controlling accession and receipt-level filed date,
  so `filed: null` on selected structural rows is a display/provenance-shape issue rather than a
  valuation or cutoff failure. Changing the shared Batch 07 helper would alter many historical
  private traces during a value-recovery phase.
  *Unblocks when:* a cross-batch provenance-schema migration can regenerate and compare every
  affected private artifact without changing public values.

- **B25 · Make calculator controls display each artifact's actual base assumptions.**
  *Why deferred:* cumulative default POSTs reproduce every published range, but the shared
  calculator view still displays generic cash-conversion, growth, discount-rate, and terminal-growth
  defaults. Correcting this safely changes the public contract across all confirmed historical
  catalogs, not only Batch 27.
  *Unblocks when:* a dedicated cross-batch migration can map each operating/equity model's exact
  base assumptions into calculator controls, rebuild every catalog, and reverify saved-run and API
  compatibility without changing confirmed values.
