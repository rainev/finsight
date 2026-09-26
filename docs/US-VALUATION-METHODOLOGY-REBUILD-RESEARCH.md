# FinSight U.S. Valuation Methodology Rebuild

**Date:** 2026-08-08  
**Scope:** U.S. equities  
**Status:** Research recommendation; no valuation code changed by this report

## Executive conclusion

FinSight should keep its SEC ingestion, filing normalization, provenance, and public-safety infrastructure. The valuation-policy layer should be rebuilt as **Valuation Engine V2**.

The dominant problem is not that every FinSight valuation is too optimistic. It is that the engine is inconsistent. Many companies are marked overvalued because their intrinsic values are too low, while a smaller FCFF group contains assumptions that can overstate value.

The most serious design flaw is the automatic replacement of FCFF with residual income or DDM when an enterprise-to-equity bridge is incomplete. A missing data field should trigger data repair or a withheld result—not an economically unrelated valuation model.

## Evidence from the current repository

The current generated universe contains 206 U.S. valuation artifacts:

| Primary model | Count | Main concern |
|---|---:|---|
| Residual income | 111 | Used for many nonfinancial companies through fallback logic |
| DDM | 69 | Used for many companies simply because a dividend is available |
| FCFF DCF | 14 | Intended model for most operating companies, but rarely reached |
| FFO | 12 | Useful first pass for REITs, but only a basic approximation |

There are 107 FCFF fallbacks. The fallback route is implemented in [pipeline.py](</Users/carlosconda/Desktop/Investing Application/backend/app/us_valuation/pipeline.py:401>) and selects generic residual-income or DDM policies in [equity_models.py](</Users/carlosconda/Desktop/Investing Application/backend/app/us_valuation/equity_models.py:343>).

The project handoff itself recognizes that these fallbacks can undervalue low-payout growth companies: [US-VALUATION-HANDOFF.md](</Users/carlosconda/Desktop/Investing Application/docs/US-VALUATION-HANDOFF.md:42>).

External valuation websites may be used as informal diagnostics, but they are not FinSight validation targets. Differences in assumptions, data vintages, and model design make exact matching inappropriate.

Amazon is the clearest routing failure: FinSight uses residual income after an incomplete FCFF bridge, despite Amazon being a large operating company whose economics are better represented by an operating DCF.

## Confirmed methodology weaknesses

### 1. Economically unrelated fallbacks

Residual income is appropriate for banks, insurers, brokers, and other businesses where equity capital is the operating resource. DDM is appropriate when dividends represent a stable and meaningful portion of distributable cash flow.

They are not universal substitutes for FCFF.

Current examples include ordinary software, retail, industrial, and technology companies being valued with book value, ROE, or dividend assumptions. This can produce materially understated values for companies that retain cash and reinvest it.

### 2. Terminal ROIC is structurally optimistic in FCFF

The current policy floors initial marginal ROIC at `WACC + 3%` and sets terminal marginal ROIC to `WACC + terminal_roic_premium`: [assumptions.py](</Users/carlosconda/Desktop/Investing Application/backend/app/us_valuation/assumptions.py:728>).

The terminal premiums range from approximately 2% to 5%. Because terminal reinvestment is calculated as growth divided by terminal ROIC, a higher terminal ROIC reduces required reinvestment and increases terminal cash flow: [models.py](</Users/carlosconda/Desktop/Investing Application/backend/app/us_valuation/models.py:198>).

For mature companies, terminal ROIC should generally converge toward WACC unless durable excess returns are supported by company-specific evidence.

### 3. Reinvestment is capped

The model calculates reinvestment as growth divided by marginal ROIC but caps it at 95%: [models.py](</Users/carlosconda/Desktop/Investing Application/backend/app/us_valuation/models.py:171>).

This prevents the model from showing genuinely negative FCFF when a high-growth company requires more investment than its current operating profit can fund. Valuation V2 should allow negative FCFF during investment-heavy growth periods.

### 4. Discount rates are policy-based rather than issuer-specific

Current WACC calculations use archetype betas, target capital structures, and default debt spreads. The code explicitly describes these as governed policy inputs rather than observed company-specific inputs.

This can overvalue risky or cyclical companies and undervalue stable companies. V2 should use company-specific leverage, beta ranges, debt spreads, and a transparent sensitivity band.

### 5. Growth and margin forecasts can preserve recent peaks

Generic growth blends:

- 37.5% recent TTM growth
- 37.5% annual history
- 25% archetype anchor

This is bounded but can still preserve unusually strong recent growth. Margins are also blended with archetype targets. Cyclical companies and companies experiencing temporary demand spikes require longer-cycle normalization.

### 6. Residual income uses fragile single-period inputs

The residual-income path relies heavily on current ROE, current book value, policy payout, and policy terminal ROE. Current ROE can be distorted by buybacks, goodwill, acquisitions, impairments, or temporary earnings.

V2 should use multi-year normalized ROE, book-value roll-forwards, payout sustainability, capital requirements, and clean-surplus checks.

### 7. REIT valuation is incomplete

Current FFO is a filing-derived approximation and does not fully capture AFFO, recurring maintenance capital expenditure, lease obligations, or property NAV. The project documentation already identifies this limitation: [US-VALUATION-HANDOFF.md](</Users/carlosconda/Desktop/Investing Application/docs/US-VALUATION-HANDOFF.md:51>).

V2 should use AFFO plus NAV/capitalization-rate analysis and require an issuer-level property-owner test. Real-estate services companies should not automatically receive an equity-REIT model based only on broad SIC ranges.

### 8. Warnings do not always stop publication

Large DCF/EPV disagreement, high terminal-value dependence, uncertain dilution, and weak bridge evidence currently produce warnings or `review_required` states rather than consistently withholding the result.

V2 should use eligibility gates. A valuation with unresolved critical inputs should not receive a green-light status merely because a mathematical output exists.

## Recommended model-selection framework

| Economic type | Primary model | Required supporting checks |
|---|---|---|
| Mature nonfinancial business | FCFF DCF and owner earnings | Historical margins, maintenance capex, working capital, relative multiples |
| Software/platform/high growth | Segment DCF | Capitalized R&D, unit economics, reinvestment, reverse DCF |
| Banks and lenders | Residual income or excess returns | Regulatory capital, normalized ROE, credit losses, P/B |
| Insurance | Excess returns plus underwriting analysis | Combined ratio, reserves, float, investment income |
| Regulated utilities | DDM plus rate-base model | Dividend coverage, allowed ROE, capex, regulatory plan |
| Equity REITs | AFFO plus NAV | Recurring capex, occupancy, rent growth, leverage, property values |
| Cyclicals | Mid-cycle normalized DCF | Full-cycle margins, utilization, normalized working capital |
| Commodity producers | Reserve/NAV plus normalized earnings | Commodity price deck, reserves, depletion, sustaining capex |
| Conglomerates/holdings | Sum-of-the-parts | Segment-level values, holding-company discount, net debt |
| Distressed or unprofitable companies | Probability-weighted scenarios | Liquidity, runway, restructuring, liquidation or option value |

The model choice should be based on economic structure and cash-flow behavior, not simply the presence of dividends or the inability to fill one bridge field.

## Principles for Valuation Engine V2

### Owner economics first

For understandable operating businesses, calculate normalized owner earnings:

```text
normalized operating cash earnings
- maintenance capital expenditure
- normalized working-capital investment
- recurring stock-based compensation dilution
= owner earnings available to owners
```

This is consistent with Berkshire Hathaway’s owner-oriented approach: intrinsic value is an estimate of the discounted cash that can be taken out of a business over its remaining life. [Berkshire Hathaway Owner’s Manual](https://www.berkshirehathaway.com/owners.html).

### No automatic model substitution

When a model is ineligible:

1. Repair the missing input from the filing.
2. Use a documented filing-specific zero only when justified.
3. Run an explicitly eligible alternative model.
4. Otherwise withhold the valuation.

### Independent relative-value check

FinSight should add historical and peer multiples as a cross-check. It should not blindly average every model. Relative value should be weighted according to peer quality, accounting comparability, growth, profitability, leverage, and business type.

### Reverse DCF

Every operating-company valuation should show what revenue growth, margin, reinvestment, and terminal assumptions the current market price implies. This is a diagnostic—not a recommendation.

### Explicit uncertainty

The output should be a range with:

- bear, base, and bull cases;
- terminal-value percentage;
- model-eligibility grade;
- source/provenance grade;
- assumption-confidence grade;
- dilution and bridge-quality flags;
- historical calibration error by model and archetype.

## Point-in-time realized-outcome backtest

FinSight should validate its intrinsic values against subsequent market outcomes, not against another website’s estimate.

For each historical valuation date:

1. Freeze the exact information set available on each historical filing date.
2. Calculate the intrinsic-value range using only information available at that date.
3. Record the market price on the valuation date.
4. Compare the intrinsic value and scenarios with the actual stock price after a defined horizon, such as 6, 12, and 24 months.
5. Include companies that later failed, delisted, or were removed from major indexes.
6. Prevent later restatements and future classifications from entering earlier observations.
7. Measure forecast error for revenue, margins, reinvestment, cash flow, ROE, dividends, AFFO, and NAV—not only share-price return.
8. Track signed error, absolute error, optimistic error, scenario coverage, rank correlation, and forward returns.
9. Report results by economic archetype and model type.
10. Keep a later period fully out-of-sample.

## Implementation sequence

### Phase 0 — Quarantine V1

- Keep all existing outputs available for comparison.
- Label every current result as experimental/candidate.
- Prevent fallback-generated values from receiving a green-light status.

### Phase 1 — Repair routing and data coverage

- Remove generic FCFF-to-RI/DDM substitution.
- Repair enterprise-to-equity bridge fields.
- Improve fully diluted shares, operating leases, working capital, and noncontrolling interests.
- Split broad SIC categories using issuer-level economic tests.

### Phase 2 — Build model-specific V2 engines

- FCFF and owner earnings for operating companies.
- Segment DCF and capitalized R&D for high-growth companies.
- Excess-return models for financial institutions.
- AFFO/NAV for REITs.
- Rate-base/DDM for utilities.
- Mid-cycle and reserve/NAV models for cyclicals and commodities.
- Sum-of-the-parts for holding companies.

### Phase 3 — Add market reality checks

- Historical peer multiples.
- Company-specific discount rates.
- Reverse DCF.
- Model disagreement and terminal-value diagnostics.

### Phase 4 — Validate and promote automatically

Automatic promotion should require:

- correct model eligibility;
- complete or documented source bridge;
- sufficient classification confidence;
- acceptable dilution quality;
- bounded terminal-value dependence;
- acceptable sensitivity range;
- satisfactory out-of-sample calibration for that archetype.

If those conditions are not met, the system should explain why the company is withheld instead of forcing a valuation.

## Final decision

**Keep the FinSight data foundation. Rebuild the valuation layer.**

The immediate priority is eliminating inappropriate fallbacks. The next priority is replacing blanket growth, ROIC, payout, and discount-rate assumptions with company-specific, archetype-appropriate inputs, then validating them through point-in-time realized-outcome backtests.

The goal is not to make every company receive a favorable valuation. The goal is to make every published valuation economically appropriate, explainable, and calibrated to what the business can actually return to its owners.

## Unresolved questions

- The current repository does not yet contain a complete point-in-time realized-outcome backtest for the 206-issuer universe.
- The size and direction of each bias must be measured by archetype; the fallback problem is confirmed, but its valuation impact is not identical for every company.
