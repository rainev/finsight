---
name: whole-batch-recovery-needs-explicit-attempt-semantics
description: Recovering initial Conditional issuers requires an explicit one-attempt contract distinct from older direct-Conditional not-applicable bookkeeping.
metadata: { type: gotcha }
---
The original Recovery Learning Watchlist schema assumed only initially Withheld issuers consume a
recovery attempt; direct Conditional issuers always used `recovery_outcome: not_applicable`. A
user-authorized whole-batch recovery intentionally attempts the Conditional values too, so those
issuers need `recovery_outcome: conditional_numeric_low` while still consuming exactly one attempt.

**Why:** broadening the loader globally would silently change historical semantics, while leaving
the old rule unchanged makes honest whole-batch recovery impossible to record.

**How to detect / apply:** pin the recovery denominator and approved initial artifact by hash,
record one receipt per ticker, derive final counts from generated cases, and scope the direct-
Conditional recovery exception to the explicitly authorized batch or a future explicit attempt
marker. Afterward, add all remaining Conditional/Withheld issuers to the watchlist and only
still-Withheld issuers to the cumulative register. Related:
[[universe-reset-one-recovery-then-register]] and [[not-fully-recovered-is-broader-than-withheld]].
