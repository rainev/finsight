---
name: baseline-decision-is-not-market-prediction
description: FinSight should provide a transparent baseline estimate under uncertainty rather than withhold because markets are inherently unpredictable.
metadata: { type: feedback }
---

FinSight's product goal is to give users a useful baseline decision range, not to prove that it can
predict or beat the market. After identity, source, period, unit, currency, share, and public-safety
checks pass, ordinary uncertainty should produce a usable range—not automatic withholding.
Ordinary forecast estimation can still be a normal Pass; reserve Conditional for a named material
dependency that remains load-bearing.

**Why:** No valuation provider can eliminate uncertainty. AlphaSpread- and GuruFocus-style coverage
comes from using historical behavior, industry assumptions, and default forecast inputs, then
warning users about predictability. FinSight should do the same while making assumptions more
visible and preserving conditional cases for later learning.

**How to detect / apply:** If a company is withheld only because future cash flow, transaction
effects, commitments, or model refinements require judgment, build coherent bear/base/bull states.
Classify the result as Pass when the inputs are source-bounded and the remaining estimation is
ordinary; classify it Conditional and add it to the Recovery Learning Watchlist only when a named
material dependency remains load-bearing. Fully withhold only for hard safety failures, no
economically coherent model, or no finite/nonnegative decision range. Related:
[[public-competitor-methods-are-constraints-not-formulas]],
[[conditional-values-need-economic-object-identity]], and
[[not-fully-recovered-is-broader-than-withheld]].
