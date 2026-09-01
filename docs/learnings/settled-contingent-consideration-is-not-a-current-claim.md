---
name: settled-contingent-consideration-is-not-a-current-claim
description: Preserve settled acquisition consideration in the event ledger without deducting it again as a current claim.
metadata: { type: gotcha }
---
Historical contingent consideration may remain essential to understanding an acquisition even when
the current filing says the contingency has been fully settled. Record the original amount and its
role in total purchase consideration, then separately record the settlement evidence and current
claim state.

**Why:** AMD's ZT Systems consideration included $361M of contingent consideration. The current
10-Q states that it was fully settled in October 2025. Omitting it made the acquisition trace
incomplete, while subtracting it again from the current equity bridge would double-count a claim
that no longer exists.

**How to detect / apply:** reconcile the acquisition-date consideration facts to the latest
cutoff-eligible narrative. Preserve historical consideration in the event ledger. Use a current
zero claim only when the filing explicitly proves settlement, label it
`source_proven_settled_not_missing_zero`, and never infer settlement from the absence of a current
XBRL liability. See also [[cutoff-bridge-includes-post-balance-financing]].
