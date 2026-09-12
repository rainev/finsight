---
name: transaction-price-is-not-a-post-event-cash-state
description: A completed acquisition price cannot update intrinsic value without source-bound post-event cash, debt, shares and operating scope.
metadata: { type: gotcha }
---
MRK's 10-Q reports the $650M TARGAN acquisition as a subsequent event, but no
separate event receipt or post-event balance rollforward is captured.

**Why:** Subtracting the transaction price from the June bridge would look like a
cash update while carrying June debt, shares and operating scope forward.

**How to detect / apply:** Keep the transaction as context until cash, financing,
shares and acquired operating scope reconcile together. Never use consideration
as intrinsic value or a standalone bridge deduction.

A pending fixed price may remain a clearly labeled private scenario sensitivity,
but it is not a current carrying liability. Add any separately reported current
contingent-consideration liability in every scenario, exclude cash already paid,
and never use the pending sensitivity as evidence that closing occurred.
