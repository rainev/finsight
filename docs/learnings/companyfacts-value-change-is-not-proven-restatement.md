---
name: companyfacts-value-change-is-not-proven-restatement
description: Different values across eligible Companyfacts accessions are value-change candidates, not automatically restatements.
metadata: { type: gotcha }
---
Grouping Companyfacts by tag, unit, period, and issuer and linking every later value change overstates restatements. Companyfacts omits dimensional context needed to distinguish consolidated, segment, and member facts, and an ordinary later comparative disclosure is not proof of correction.

**Why:** The first Batch 01/02 ledger labeled thousands of ordinary or dimension-unknown changes as restatements.

**How to detect / apply:** Preserve form, report date, amendment status, and whether dimensions are known. Confirm only same-context amendment links; classify dimension-unknown and ordinary comparative changes as unresolved candidates. Never let them silently rewrite an earlier cutoff artifact.
