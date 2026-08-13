---
name: public-bridge-range-binds-to-fcff
description: Public bridge absolutes must agree with the canonical FCFF per-share output, not merely be internally consistent.
metadata: { type: gotcha }
---
A mathematically valid `bridge_quality` range can still be forged independently
of the valuation it claims to qualify.

**Why:** Shape, ordering, and spread checks prove only internal consistency. They
do not prove that the midpoint belongs to the artifact's canonical FCFF result,
so unrelated or raw statement amounts can otherwise be laundered through an
allowlisted public path.

**How to detect / apply:** Whenever bridge absolutes are present, require a finite
`models.fcff_dcf.intrinsic_value_per_share` and bind the bridge midpoint to it at
the public sanitizer boundary. Fail the bridge closed when the model is missing,
non-finite, or mismatched. Keep a regression using a large plausible raw amount.

