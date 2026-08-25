---
name: input-range-zero-endpoint-is-not-zero-substitution
description: A source-bounded missing claim may have a zero low endpoint, but its estimated base cannot silently be zero; intrinsic-value ranges remain strictly positive.
metadata: { type: gotcha }
---
Practical bridge uncertainty needs ranges such as `$0` to a same-filing reported maximum. The
zero endpoint means the claim may genuinely be absent; it does not assert that the missing base
value is zero. Using the same strictly-positive contract for both valuation outputs and input
bounds prevented this honest representation.

**Why:** Forcing every input endpoint above zero invents a minimum claim, while allowing an
estimated zero base silently recreates the missing-to-zero bug. Valuation outputs and uncertain
inputs therefore need different contracts.

**How to detect / apply:** Keep intrinsic low/base/high strictly positive. Allow nonnegative
input endpoints, but reject an estimated range whose base is zero. A fully reported explicit
zero may remain zero. Preserve the source-derived upper bound, basis, and Low reliability cap.

