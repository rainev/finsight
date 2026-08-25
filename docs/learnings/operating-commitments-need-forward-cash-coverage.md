---
name: operating-commitments-need-forward-cash-coverage
description: Keep operating commitments out of the debt bridge, but require their schedule or growth to be covered by forward cash scenarios.
metadata: { type: gotcha }
---
Contractual content, cloud, data-center, and uncommenced lease commitments are not automatically
debt claims. When their cash costs already run through operating cash flow, subtracting the full
obligation again double counts them. They still cannot be ignored in the forecast.

**Why:** NFLX's current OCF already contains content cash payments, and its bear cash reduction can
be tested against the filed growth in content additions and obligation schedule. META, by contrast,
reported very large uncommenced leases and contractual commitments whose timing and overlap with
future capex were not reconciled; a simple plus/minus capex percentage did not bound them.

**How to detect / apply:** Preserve the total, unrecorded amount, near-term schedule, and historical
cash conversion. Publish Low only when the bear cash state covers the source-observed commitment
growth without bridge subtraction. Withhold when timing/overlap is material and unresolved. See
[[public-assumptions-must-match-practical-base-state]].
