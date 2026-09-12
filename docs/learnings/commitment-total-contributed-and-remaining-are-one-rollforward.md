---
name: commitment-total-contributed-and-remaining-are-one-rollforward
description: Aggregate commitment, contributed-to-date and remaining balance must reconcile and must never be summed.
metadata: { type: gotcha }
---
NXPI reports a $1.2B infrastructure commitment, $1.098B contributed, and $102M
remaining. The old model deducted the full aggregate as if it remained unpaid.

**Why:** Adding or carrying the total after contributions counts sunk cash again.

**How to detect / apply:** Require total = contributed-to-date + remaining under
one scope. Only the remaining balance can enter current/future claim analysis;
separate investee commitments still require their own timing and overlap proof.
