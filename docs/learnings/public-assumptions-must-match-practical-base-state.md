---
name: public-assumptions-must-match-practical-base-state
description: Public assumptions and calculator routing must reproduce the exact private base model, not a generic or stale model family.
metadata: { type: gotcha }
---
The practical FCFF runner recalibrated `sales_to_capital` from reported capex/revenue history,
but initially left `forecast_assumptions.sales_to_capital` at the generic archetype value. The
private base scenario and valuation used the calibrated value while the public API would have
displayed the old one.

**Why:** A safe public artifact can still be misleading if its disclosed assumptions do not
reproduce its base value. Public/private field allowlists do not detect semantic staleness.

**How to detect / apply:** After every practical base-state transformation, copy the exact base
growth, margin, capital-efficiency, discount, terminal, share, and model inputs into the
canonical private fields used by the public serializer. Assert public assumptions equal the
base scenario inputs and independently recalculate the base value.

Batch 13 exposed the same semantic trap at the model-family level. UNH's private result correctly
used managed-care residual income, but the public `forecast_mode="residual_income"` was not a
recognized calculator route while `model_policy.primary` remained `conditional_estimate`. The API
therefore exposed operating-FCFF controls even though default range parity still appeared valid.

**How to detect / apply:** For every staged artifact, call the real calculator view and assert its
`model_family` and editable fields match the private method—not merely that the default numeric
range agrees. Then exercise a meaningful override in the consumer path. A correct private schedule
plus default API parity does not prove that users are editing the intended model.

Batch 19 exposed the same trap inside a Conditional acquisition fallback. Hubbell's warning and
private evidence cited filed pro-forma acquisition revenue, while the first candidate still valued
only reported TTM revenue containing a few weeks of the acquired business—despite carrying the full
acquisition debt. The statements were true, but the pro-forma scale had no effect on arithmetic.

**How to detect / apply:** For every named fallback, event overlay, or pro-forma assumption, assert
that the cited source value flows into the exact forecast input. Reconcile reported scale to
valuation scale explicitly, and challenge the asymmetric case where a full transaction claim is
bridged against only partial acquired operations.
