---
name: opaque typed claim contexts force Conditional
description: Conservatively summing distinct typed XBRL contexts can bound value, but cannot support Pass until overlap is disproven.
metadata: { type: gotcha }
---
Two XBRL facts can have different context IDs while exposing the same opaque typed dimension in
the normalized structural output. Their separate IDs prove separate presentations, not separate
economic claims. If both amounts may be material, sum them conservatively to keep the valuation
finite, retain the context IDs and raw residual privately, and classify the result Conditional
until the filing proves the facts do not overlap.

**Why:** Batch 30 initially treated STX's `$45M` and `$75M` loss-contingency facts as two fully
reconciled claims and labeled the result Pass. Both facts used typed statement-of-financial-position
contexts (`c-303` and `c-304`) whose economic members were opaque after parsing. The `$120M`
conservative deduction bounded downside, but did not prove claim-set completeness or non-overlap.

**How to detect / apply:** when two material facts share concept, instant, unit, and an opaque typed
dimension, inspect the controlling filing and context definitions. If economic members remain
unresolved, do not silently choose one or call the sum fully reconciled. Record both values and
context IDs, use a conservative bounded treatment if suitable, add an invalidation trigger, and
cap the outcome at Conditional Low. See also [[specialist-facts-require-filed-lineage]].
