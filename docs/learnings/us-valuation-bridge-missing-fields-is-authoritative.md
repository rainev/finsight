---
name: us-valuation-bridge-missing-fields-is-authoritative
description: Use the nested balance-sheet bridge fields, not top-level review or raw field states, when auditing US valuation completeness.
metadata: { type: gotcha }
---
US valuation private artifacts store bridge status under `financials.balance_sheet.bridge_complete` and the authoritative blocking set under `financials.balance_sheet.bridge_missing_fields`. The top-level `review` object stores publication/errors, while `field_states` also contains stale and governed states that do not necessarily equal the blocking set.

**Why:** Counting the wrong layer can make the bridge look more or less incomplete than it is. Also, in `jq`, `false // "fallback"` evaluates to the fallback, so use an explicit boolean test when counting `bridge_complete`.

**How to detect / apply:** Inspect the artifact keys first; count `bridge_missing_fields` for blocker frequencies, test `bridge_complete` with `if ... == false`, and reconcile the result to `review.errors` before drawing conclusions.
