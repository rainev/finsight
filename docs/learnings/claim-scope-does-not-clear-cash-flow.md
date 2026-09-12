---
name: claim-scope-does-not-clear-cash-flow
description: A fully reconciled bridge claim does not override a non-positive current sustainable-cash scenario.
metadata: { type: gotcha }
---
BALL's NCI and benefit-liability components reconcile, but its current cash-FCFF
normalization produces a non-positive scenario that the valuation engine rejects.
**Why:** claim correctness and sustainable cash generation are independent gates.
**How to detect / apply:** report the claim mechanism as source-bound while
keeping the full company in financial review; never clamp cash FCFF positive or
count the company as a working valuation merely because the bridge is complete.
