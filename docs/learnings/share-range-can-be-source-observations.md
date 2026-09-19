---
name: share-range-can-be-source-observations
description: Symmetric scenario shares may encode two reported denominators and their midpoint, not a reusable percentage sensitivity.
metadata: { type: gotcha }
---

GILD and INCY used reported fiscal-YTD weighted diluted shares for the bear
denominator, reported cover shares for the bull denominator, and their arithmetic
midpoint for base. The symmetric-looking factors around base were therefore a
presentation of two source observations, not a governed percentage range. Freezing
those factors across filings would carry stale source evidence forward.

BBY is different: its private ledger has one reported YTD denominator, while its
governed assumptions explicitly apply ±2.5% scenario factors. That relative
sensitivity can be carried to the newly selected reported base share.

**Why:** identical arithmetic shapes can have different economic provenance.
Output symmetry is not evidence of assumption symmetry.

**How to detect / apply:** inspect the SHA-pinned private source ledger before
compiling a refresh rule. If both endpoints map to distinct reported facts, reselect
those facts and rebuild the midpoint. Use fixed relative factors only when one
reported base observation and separately governed scenario assumptions are proven.
