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
