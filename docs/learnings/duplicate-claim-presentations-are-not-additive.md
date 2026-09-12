---
name: duplicate-claim-presentations-are-not-additive
description: Aggregate, Level-3 and acquisition-member views can report the same contingent liability and must be reconciled by scope rather than summed.
metadata: { type: gotcha }
---
CTSH and VRT report contingent consideration through multiple dimensional views.
CTSH's current aggregate and Level-3 rows are the same $25M liability. VRT's
issuer current total is independently corroborated by aggregate and Level-3
derivative views, while acquisition-specific GAAP rows are narrower slices.

**Why:** Summing every nonzero fact double-counts one claim and can also invent a
residual when a consolidated total and acquisition slices use different scopes.

**How to detect / apply:** Prefer a current issuer total only when another
authoritative presentation corroborates it. Require matching period, accession,
dimensions and positive totals; accept Level-1/2 zeros as diagnostics. Retain
acquisition-member rows, maxima and noncash changes separately and reject
conflicts.
