---
name: pse-concession-distributions-must-end-at-expiry
description: Distribution valuations for finite franchises or concessions must stop at the sourced expiry and carry no automatic perpetuity.
metadata: { type: gotcha }
---

A sustainable-distribution route normally adds a Gordon-growth terminal value. That is unsafe when the issuer's legal
right to operate ends on a documented franchise or concession date.

**Why:** A calculator can reproduce a plausible dividend value while assigning most of it to cash flows after the
economic right expires. The error is especially easy to miss because the current payout and discount-rate controls
still behave normally.

**How to detect / apply:** Every distribution artifact for a finite franchise or concession must publish
`finite_life_years` and `expiry_date`. The engine and calculator must use the same explicit horizon, return zero terminal
value, and omit the terminal-growth control. A continuing distribution case may retain terminal growth only when the
operating life is not source-limited. Recheck `backend/app/pse_valuation/models/distributions.py` and
`backend/app/pse_valuation/calculator.py` before relying on this learning.
