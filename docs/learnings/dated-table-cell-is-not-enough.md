---
name: dated-table-cell-is-not-enough
description: A dated numeric table cell still needs carrying-value role, scale, and complete-scope proof.
metadata: { type: gotcha }
---
A row-label plus exact date match can still select the wrong economics: par value as shares, money-market detail as cash, facility capacity as commercial paper, proceeds as cash, or maturity payments as debt carrying value.

**Why:** The first generic Batch 01/02 table replay produced each of those false positives even though the current column date was correct.

**How to detect / apply:** Require exact field-specific row semantics, reject maturity/commitment roles, derive and preserve table scale, retain the full locator/excerpt, and keep no-match outcomes unresolved unless every governed primary/attachment document was searched. A `primary_document_only` search can produce a reported observation but cannot prove `not_disclosed`.
