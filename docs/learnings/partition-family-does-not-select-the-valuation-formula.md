---
name: partition-family-does-not-select-the-valuation-formula
description: Universe partition metadata can group economic neighbors without making them share one valuation formula.
metadata: { type: gotcha }
---
The universe-reset partition can place non-REIT real-estate service companies in a `reit_affo` family for deterministic
batch selection. That label is not evidence that FFO/AFFO is economically appropriate. Batch 50 placed CSGP and CBRE
beside property REITs, but both required operating enterprise FCFF.

**Why:** Treating cohort metadata as model identity would create a reproducible but economically invalid valuation.

**How to detect / apply:** Compare the issuer's legal/economic business and filed performance measures with the proposed
formula before building. Persist an explicit route override and assert private method, public model identity, forecast
mode and calculator family all agree.
