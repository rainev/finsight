---
name: pse-market-relative-fallback-is-a-separate-product
description: A practical PSE fallback may publish a source-linked relative range without weakening or relabeling the specialist intrinsic model.
metadata: { type: feedback }
---
When a PSE specialist intrinsic route is blocked, FinSight may still publish a provisional low/base/high screening range
from a source-linked per-share metric and a transparent policy band. The artifact must use
`availability_type: market_relative_only`, keep all intrinsic scenarios null, and retain the exact intrinsic-model
limitations. Do not call the fallback intrinsic value and do not blend it into a later intrinsic result.

**Why:** The user wants practical coverage comparable to broad valuation platforms without making the engine so strict
that every incomplete specialist route returns no number. Separating the product types preserves usefulness and honesty.

**How to detect / apply:** If EPS, book value, or a sustainable distribution candidate has source provenance and no
obvious sign/unit contradiction, a versioned provisional policy band can produce the relative range. Candidate facts
carry a review warning; reviewed legacy facts do not. Specialist evidence continues under
[[pse-v2-corpus-blockers-are-authoritative]].

