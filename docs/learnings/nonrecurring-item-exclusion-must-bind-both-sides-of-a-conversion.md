---
name: nonrecurring-item-exclusion-must-bind-both-sides-of-a-conversion
description: A normalized ratio must remove the same nonrecurring item from both numerator and denominator scopes.
metadata: { type: gotcha }
---
When a guidance anchor excludes a nonrecurring item, the historical cash-conversion numerator must exclude it too.
Batch 50 initially divided DLR AFFO containing $187.871m of promote income by Core FFO excluding promote, producing a
ratio above 100%. The correct exact-dollar conversion was `(1,563.339 - 187.871) / 1,483.956`.

**Why:** Mixed scopes silently transfer a one-time gain into recurring owner cash and overstate every DCF scenario.

**How to detect / apply:** Reconcile numerator and denominator adjustment ledgers before calculating a conversion ratio.
Prefer exact reported dollar totals over rounded per-share figures, retain excluded amounts in private evidence, and
test that the public warning names any material one-time amount deliberately retained as sensitivity.
