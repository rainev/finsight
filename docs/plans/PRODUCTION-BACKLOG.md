# FinSight whole-universe production backlog

Only work that does not belong on the approved 500/500 critical path is parked here. Full-universe coverage, specialist model lanes, price comparison, and backtesting are scheduled roadmap work, not deferred aspirations.

## Deferred until the critical path is verified

- **B1 · General documentation cleanup.** Large folder reorganization does not change valuation behavior. Revisit after the reliability pipeline and canonical universe are stable.
- **B2 · Retiring old generated frontend modules.** The active U.S. valuation page reads the API. Remove unused generated modules only after the API/UI contract is finalized and imports are rechecked.
- **B3 · Production deployment.** Feature-branch implementation and local/staging verification do not authorize merging or deploying. Unblocks after all roadmap gates, branch review, and explicit user approval.
- **B4 · Paid institutional market-data integration.** The first governed current-price comparison should use an approved public source. Paid data remains unnecessary unless public-source quality fails the release gate.

## Log-new-tangent rule

If a defect is discovered while executing a phase and it does not block that phase's consumer-visible behavior, record it here with the exact evidence, why it is deferred, and what would move it back to the roadmap. Do not interrupt the current phase for unrelated cleanup.
