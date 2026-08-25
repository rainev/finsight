---
name: public-assumptions-must-match-practical-base-state
description: After a practical sensitivity recalibrates the base state, the public assumption DTO must be updated from that exact base—not left at the generic pre-calibration policy value.
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

