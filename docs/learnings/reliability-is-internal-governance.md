---
name: reliability-is-internal-governance
description: Keep High/Medium/Low reliability in audit data, but do not present it as a headline verdict on intrinsic value.
metadata: { type: feedback }
---
The user confirmed that intrinsic values are baseline decision aids, not market predictions. A prominent
`Confidence: Low` card makes users question whether any value is usable and confuses model uncertainty
with a claim that the estimate is untrustworthy. Preserve reliability labels, reasons, and caps in the
artifact/API for governance, review, and future calibration, but keep them out of the primary valuation UI.

**Why:** every valuation depends on assumptions and markets are not perfectly predictable. The product
should communicate the range and assumptions directly instead of turning internal model diagnostics into
a simple user-facing verdict.

**How to detect / apply:** review valuation pages for visible `Confidence`, `High/Medium/Low`,
`review_required`, `CANDIDATE`, or reliability-cap language. Keep source-specific caveats in Key
assumptions, while retaining the machine-readable reliability payload privately/publicly for audit.
Related: [[baseline-decision-is-not-market-prediction]] and [[reporting-honesty]].
