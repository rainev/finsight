---
name: conditional-values-need-economic-object-identity
description: A disclaimer cannot make standalone value, transaction consideration, and event payoffs one coherent valuation range.
metadata: { type: gotcha }
---

A conditional value needs its own model/output identity and one coherent economic object per
range. Standalone DCF, transaction-conditioned residual equity, and contractual merger cash must
not be mixed into low/base/high merely because a warning calls the result conditional. Contract
consideration belongs on a separate event surface, and a negative residual-equity state may use an
explicit limited-liability floor only when that convention is visible.

**Why:** In Batch 02, CHTR initially mixed transaction and standalone claim states, while WBD mixed
standalone DCF with contractual merger cash. The arithmetic was correct but the public meaning was
not. In Batch 10, KMB became recoverable only after selecting the exact post-IFP, pre-Kenvue state:
continuing operations plus completed IFP cash/stake value, with pending Kenvue consideration and
dilution excluded. The legacy `intrinsic_value_per_share` field also contradicted the conditional
disclaimer.

**How to detect / apply:** Check that all range endpoints use the same model, claims, dilution, and
event state. Use `conditional_value_per_share`, keep reliability Low, state when $0 is an equity
floor, and publish contractual consideration separately without probability weighting. Related:
[[conditional-deal-consideration-is-not-intrinsic-value]] and
[[public-assumptions-must-match-practical-base-state]].
