---
name: reit-sale-gains-missing-is-not-zero
description: A missing REIT property-sale-gain fact cannot be silently converted to zero in FFO or AFFO arithmetic.
metadata: { type: gotcha }
---
The interim REIT FFO route historically used zero when no property-sale-gain fact was selected.
That converts missing evidence into a favorable accounting assumption and can produce a numeric
FFO result without proving that sale gains were actually zero.

**Why:** FFO is defined by reconciling net income for depreciation and property-sale gains. A
missing adjustment can materially overstate or understate normalized earnings and violates the
project's explicit zero-versus-missing rule.

**How to detect / apply:** Require a reported gain, an explicit zero, or source-backed complete-
search/not-disclosed evidence before completing the FFO reconciliation. Otherwise return a
withheld outcome with the exact missing adjustment. Keep the interim REIT model capped at Low
until a governed AFFO/NAV lane is validated.

