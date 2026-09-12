---
name: public-sanitizer-scrubbed-replay-context
description: Null valuation ranges are valid only when every public value sink proves the artifact was already scrubbed.
metadata: { type: gotcha }
---
An all-null `bridge_quality.intrinsic_value_range` is ambiguous: it can be the
safe result of an earlier top-level withholding pass, or a forged initial DTO
trying to avoid range arithmetic and canonical-value checks.

**Why:** Treating both cases alike either accepts an unverified initial bridge or
breaks sanitizer idempotency by replacing truthful bridge metadata on replay.

**How to detect / apply:** At the public boundary, accept a scrubbed complete or
bounded range only when the raw input is already withheld and every model,
scenario, sensitivity, and aggregate range sink is withheld/null. A top-level
`withheld` label by itself is insufficient. Test the malicious initial shape and
the twice-sanitized control separately.

The FCFF public sanitizer also validates the private
`financials.balance_sheet.bridge_uncertainty` object against an exact legacy key
set before constructing `bridge_quality`. Until the dedicated public-sanitizer
schema task changes that allowlist, new private reliability fields belong in the
result's top-level `reliability` object; the stored bridge projection must retain
its legacy shape. `BridgeAssessment.from_dict()` must continue deriving the new
impact/cap fields when it reads that projection or historical artifacts.

**Why:** Adding `accounting_impact_ratio` and `reliability_cap` directly to the
stored bridge projection caused otherwise-valid complete and bounded artifacts
to fail closed as `BRIDGE_QUALITY_INVALID_OR_MISSING`, even though the private
valuation itself was correct.

Explicit availability is also part of the already-scrubbed public contract. A
second sanitizer pass must preserve it for every exact forecast mode, including
`reit_affo_exact` and `timber_distribution_exact`. Omitting those modes caused 26
stored Conditional REIT/timber artifacts to become `available` when FastAPI
sanitized them again.

**How to detect / apply:** Assert `sanitize_public_artifact(public) == public`
for every generated public artifact family, and run one raw stored-versus-live
availability comparison across the active catalog. Do not infer availability
from model identity when an allowlisted exact mode already carries an explicit
validated availability classification.
