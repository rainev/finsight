---
name: reliability-thresholds-are-provisional
description: The approved FinSight reliability bands are V1 thresholds that must be replay-tested and escalated if they grade companies unfairly.
metadata: { type: project }
---
FinSight's approved V1 reliability thresholds are:

- Accounting-data impact: `0%–5%` creates no automatic reliability cap; `>5%–20%` caps reliability at `Medium`; `>20%` makes reliability `Low`.
- Total valuation movement from base: up to `20%` can support `High`; `>20%–40%` is `Medium`; `>40%` is `Low`.
- Trustworthy annual company data no more than 12 months old is `carried_forward`, not missing. It receives no automatic age penalty. Grade the possible change in the account and its effect on intrinsic value.

These bands are source-informed FinSight policy, not universal industry rules. They remain provisional until exercised on the 104-company replay, the complete 500-company universe, and a point-in-time backtest.

**Why:** The user wants consistent reliability grades without FinSight withholding or downgrading valuations over economically unimportant accounting details.

**How to detect / apply:** During each replay, report the rating distribution, fallback sources, near-boundary cases, and examples where the grade appears harsher or looser than the economic risk. If a threshold appears unfair, identify it as the suspected cause and bring the evidence to the user before changing it. Do not silently tune the policy.
