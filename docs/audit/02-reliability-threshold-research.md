# Audit 02 — Reliability-threshold research

Date: 2026-08-14
Status: **user-approved V1 design — source-verified, not yet replay-validated**

## Question

What percentage thresholds should FinSight use when uncertain accounting inputs or valuation assumptions change a company's intrinsic value?

## Essential distinction

FinSight has two different kinds of uncertainty:

1. **Accounting-data uncertainty:** the value changes because a reported input is missing, old, aggregated, or estimated.
2. **Total valuation uncertainty:** the value changes because the future is uncertain—for example growth, margins, reinvestment, or discount rates.

The first is avoidable process uncertainty and should use tighter bands. The second is normal in intrinsic valuation and needs wider bands.

## Source findings

### ✔ SEC materiality guidance

SEC Staff Accounting Bulletin No. 99 recognizes 5% as a possible preliminary numerical screen, but expressly rejects using any percentage by itself. Qualitative circumstances must also be considered. This supports 5% as FinSight's first accounting-impact boundary, not as an automatic safe-harbor rule.

Source: [SEC Staff Accounting Bulletin No. 99](https://www.sec.gov/interps/account/sab99.htm).

### ✔ International Valuation Standards Council

IVSC guidance treats valuation uncertainty as normal and distinguishes it from errors or weak process. It identifies data limitations, model constraints, and assumption sensitivity as separate sources. IVSC defines materiality by whether an input or assumption could influence a user's economic decision; it does not prescribe one universal percentage.

Sources: [IVSC value-uncertainty paper](https://ivsc.org/managing-and-communicating-value-uncertainty/) and [IVSC standards glossary](https://ivsc.org/standards-glossary/).

### ✔ CFA Institute

CFA's equity-valuation process requires a model appropriate for the business and available data, followed by sensitivity analysis. It does not provide universal percentage bands. This supports a separate model-fit check instead of allowing a narrow numerical range to excuse the wrong valuation model.

Source: [CFA Institute Equity Valuation: Applications and Processes](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-applications-and-processes).

### ✔ Morningstar equity-research methodology

Morningstar's published equity methodology explicitly links uncertainty to the dispersion of possible intrinsic values. Its uncertainty-dependent buy margins are approximately 20%, 30%, 40%, 50%, and 75% from Low through Extreme uncertainty. Morningstar says its cutoffs combine empirical performance and option-pricing theory, with analyst judgment for business-specific risks.

This is not a direct template for FinSight's accounting bridge. It is useful evidence that normal whole-company fair-value uncertainty is materially wider than 5% or 15%.

Sources: [Morningstar Equity Research Methodology](https://www.morningstar.com/content/dam/marketing/shared/research/methodology/705988Morningstar_Equity_Research_Methodology.pdf) and [Morningstar uncertainty methodology explanation](https://www.morningstar.com/stocks/an-introduction-morningstar-uncertainty-rating).

### ✔ Empirical reasonableness check

Published research on analyst target prices reports large errors, in some samples reaching roughly 46%. Target prices are not the same as intrinsic-value estimates, so this cannot set FinSight's thresholds. It does show that treating a 10%–15% total fair-value range as universally adequate would create false precision.

Source: [Bonini et al., Target Price Accuracy in Equity Research](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=676327).

## Recommended V1 thresholds

### 1. Accounting-data impact

Measure the largest movement away from the base value caused only by uncertain accounting inputs:

```text
accounting impact = max(|low - base|, |high - base|) / |base|
```

| Impact on intrinsic value | Internal data judgment | Public effect |
| --- | --- | --- |
| 0%–5% | Small | No automatic reliability cap |
| More than 5%–20% | Meaningful | Reliability cannot exceed Medium |
| More than 20% | Large | Reliability is Low |

Why these boundaries:

- 5% has a recognized role as a preliminary materiality screen, with qualitative overrides.
- 20% is where the uncertainty becomes comparable with the margin demanded even for a low-uncertainty equity valuation in a major published research methodology.
- A 15% boundary has no comparably strong external anchor; 20% is better supported and easier to explain.

### 2. Total valuation range

Measure the largest movement from the base value across governed bear/base/bull scenarios:

| Largest movement from base | Scenario judgment | Public reliability ceiling |
| --- | --- | --- |
| Up to 20% | Relatively narrow | High is possible |
| More than 20%–40% | Meaningful uncertainty | Medium |
| More than 40% | Wide uncertainty | Low |

These bands are an explicit FinSight inference from Morningstar's published 20%/30%/40% uncertainty-dependent margins, IVSC's materiality principle, and empirical evidence that equity forecasts often miss by substantially more than 15%. They are not claimed as a universal valuation standard.

## Qualitative overrides

Percentages cannot be the only rule.

- Data no more than 12 months old receives no automatic reliability cap. Its impact range and any major intervening company event determine the penalty.
- A wrong or unproven model lane caps reliability at Low even if its numerical range looks narrow.
- A sector estimate as the final data fallback caps reliability at Low.
- A source conflict, unit/currency ambiguity, or share-denominator ambiguity cannot be hidden by a small calculated range; it remains Low and visible internally.
- A documented current aggregate may replace missing detail when double counting is impossible.
- Every company still receives a numeric value under the agreed 500/500 product contract.

## Overall label

The public `High` / `Medium` / `Low` label is the lowest justified result from:

1. accounting-data impact;
2. total valuation range;
3. model fit; and
4. source-integrity overrides.

This is intentionally simple for users while preserving the detailed reasons internally.

## Rejected threshold choices

- **Current 1% maximum spread:** too strict for the 500/500 coverage goal and materially narrower than published valuation-uncertainty practice.
- **One 5%/15% rule for everything:** mixes data-quality risk with normal forecast risk and gives 15% no clear external anchor.
- **No numerical bands:** too subjective and difficult to apply consistently across 500 companies.
- **Percentages with no override:** conflicts with SEC and IVSC principles that context and decision impact matter.

## Verification boundary

The cited methodology claims and the current FinSight 1% implementation are verified. The recommended 5%/20% accounting bands and 20%/40% scenario bands are a source-informed FinSight policy inference. They have not yet been exercised on the 104-company replay, the canonical 500-company universe, or the point-in-time backtest. Those real-data checks remain required before implementation is called complete.

## Approval and future-testing rule

The user approved these thresholds as FinSight's V1 design on 2026-08-14. Approval does not make them permanent. During the 104-company replay, 500-company rollout, and point-in-time backtest, FinSight must check whether the bands systematically underrate or overrate companies.

If evidence suggests that a threshold is producing unfair grades, do not silently tune it. Report the affected company count, examples near the boundary, the valuation impact, and the proposed adjustment to the user before changing the policy.

A trustworthy annual value no more than 12 months old is `carried_forward`, not missing. Age alone creates no automatic penalty; the possible change in the account and its effect on intrinsic value are what enter the accounting-impact thresholds.
