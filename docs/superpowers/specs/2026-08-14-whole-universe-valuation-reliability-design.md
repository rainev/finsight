# FinSight Whole-Universe Valuation Reliability Design

Date: 2026-08-14
Status: User-approved design; implementation and real-data validation have not started

## Objective

FinSight will publish a numeric intrinsic value for every company in one frozen 500-company universe. Every company will have the same public features:

- intrinsic value;
- percentage under or over intrinsic value;
- valuation range; and
- `High`, `Medium`, or `Low` reliability.

Reliability describes uncertainty. It does not hide the valuation or remove features. A low-reliability value is still shown, but its wider uncertainty must be clear.

## Why the current behavior must change

The current bridge policy often withholds a complete valuation when one accounting detail is unavailable. It checks whether every requested detail is present before checking whether that detail materially changes intrinsic value.

That order is too strict for the 500/500 product goal. A missing small detail should not have the same effect as a wrong currency, a wrong share count, or an unsuitable valuation model.

The new order is:

1. find the best trustworthy evidence;
2. use an economically valid fallback when needed;
3. measure how much uncertainty changes intrinsic value;
4. assign reliability; and
5. publish the numeric value and range.

## End-to-end pipeline

```text
Frozen 500-company manifest
        |
SEC filing and company evidence
        |
Companyfacts fast path + Arelle structural extraction
        |
Source-linked field candidates
        |
FinSight meaning, reconciliation, and fallback policy
        |
Correct company-specific valuation lane
        |
Low / base / high valuation scenarios
        |
Reliability decision
        |
Prepared JSON artifact -> API -> identical public features for all 500
```

Arelle remains an offline filing parser. It is not imported into the live API. The live application reads prepared, validated artifacts.

Arelle does not make the final accounting or publication decision. It exposes filing facts, including custom company tags. FinSight decides what those facts mean, whether they can be combined safely, and how much uncertainty they create.

## Accounting fallback ladder

For each required economic input, FinSight uses the highest available trustworthy level:

1. current, directly reported company number;
2. current Arelle-extracted number with source evidence;
3. trustworthy reported aggregate replacing unavailable details, when double counting is impossible;
4. trustworthy older company number;
5. conservative range based on that company's history; or
6. conservative sector estimate as the final fallback.

The provenance level is saved with the field and remains traceable internally.

### Annual backup rule

A trustworthy annual number no more than 12 months old is `carried_forward`, not missing. It receives no automatic age penalty.

FinSight estimates whether the account may have changed since the annual filing. A major acquisition, disposal, refinancing, capital raise, or other relevant event can widen the range. Stable businesses and economically small carried-forward accounts can still support `High` reliability.

Annual revenue or annual cash flow cannot simply replace current operating performance. Flow measures must be updated to a current trailing-twelve-month period or estimated as a range.

### Unsafe evidence

FinSight never treats unavailable data as zero. A candidate with an unresolved period, unit, currency, source, or share-denominator conflict is rejected and the pipeline moves to the next fallback. The conflicting value does not enter the valuation.

## Correct valuation model

Each company receives one governed economic model lane before its missing inputs are resolved. Existing supported lanes remain the starting point:

- ordinary operating companies: FCFF/DCF with EPV cross-check;
- banks, insurers, securities firms, and credit companies: residual income;
- regulated utilities: DDM; and
- REITs: the governed real-estate lane, using FFO only when its limitations are explicit.

Specialist companies such as commodity producers, companies with captive finance arms, pre-profit companies, digital-asset businesses, and IFRS filers must remain in an economically suitable specialist lane. FinSight must not switch an operating company to residual income or DDM merely because an FCFF account is difficult to extract.

An unproven specialist lane still produces a conservative numeric range for the 500/500 contract, but its reliability is `Low` until the model earns stronger evidence. A wrong model is never used.

## Reliability thresholds

FinSight separates accounting-data uncertainty from normal forecasting uncertainty.

### Accounting-data impact

Hold the business assumptions constant. Change only the uncertain accounting inputs and measure the largest movement from the base value:

```text
accounting impact = max(abs(low - base), abs(high - base)) / abs(base)
```

| Impact on intrinsic value | Reliability effect |
| --- | --- |
| 0% to 5% | No automatic reliability cap |
| More than 5% to 20% | Reliability cannot exceed `Medium` |
| More than 20% | Reliability is `Low` |

### Total valuation movement

Measure the largest movement from the base value across governed low, base, and high business scenarios:

| Largest movement from base | Reliability effect |
| --- | --- |
| Up to 20% | `High` remains possible |
| More than 20% to 40% | Reliability cannot exceed `Medium` |
| More than 40% | Reliability is `Low` |

The final public label is the lowest result justified by:

1. accounting-data impact;
2. total valuation movement;
3. model suitability; and
4. source-integrity overrides.

Sector estimates and unproven specialist model lanes cap reliability at `Low`. A narrow numeric range cannot hide a source, unit, currency, period, or share-denominator problem; the bad candidate is discarded and a valid fallback is used.

These are source-informed FinSight V1 thresholds, not universal industry rules. The research basis and limitations are recorded in `docs/audit/02-reliability-threshold-research.md`.

## Public and private output

Every public company record contains the same simple output:

- base intrinsic value;
- low and high intrinsic values;
- current-price difference in amount and percentage; and
- `High`, `Medium`, or `Low` reliability.

The public label does not disable sliders, comparisons, or other valuation features.

Private evidence records contain the details needed for audit and debugging:

- model lane and model version;
- source concepts, filing accession, period, unit, and currency;
- fallback level for each material input;
- accounting-impact calculation;
- scenario-width calculation;
- reliability caps and reason codes; and
- any conflicts that were rejected.

## Failure handling

- If Companyfacts lacks an account, try Arelle.
- If Arelle cannot establish the account, move down the fallback ladder.
- If a detailed account is unavailable but a trustworthy aggregate is sufficient, use the aggregate without double counting.
- If current detail is unavailable but trustworthy annual data is no more than 12 months old, carry it forward and test its possible impact.
- If company-specific evidence is still insufficient, use a company-history range and then a conservative sector estimate.
- If a parser or source fails, preserve the failure reason internally and continue through valid fallbacks.
- Never substitute zero, corrupted evidence, or an unrelated valuation model.
- Never silently alter reliability thresholds because results are inconvenient.

## Testing and fairness review

### Automated boundary tests

Tests must cover values exactly at and immediately around 5%, 20%, and 40%; annual data at and immediately beyond 12 months; aggregate replacement; double-count protection; rejected unit/currency/share conflicts; and correct model-lane routing.

### 104-company replay

Replay the same 104-company Arelle corpus and report:

- companies receiving a numeric value before and after the new policy;
- `High`, `Medium`, and `Low` counts;
- fallback use by level;
- accounting-impact distribution;
- companies near each threshold; and
- any unsafe promotion or wrong-model case.

### Complete-universe replay

Freeze one canonical issuer-level manifest containing exactly 500 companies. Produce exactly one valuation decision and one numeric valuation for every company. Report all exclusions from any intermediate stage; no company may disappear from the denominator.

### Point-in-time backtest

Run historical valuations using only information available on each historical valuation date. Evaluate model lanes, valuation ranges, directional results, systematic overvaluation or undervaluation, and whether reliability labels separate stronger from weaker outcomes.

### Threshold fairness escalation

The V1 thresholds are provisional until these replays are complete. If they appear to grade companies unfairly, FinSight must report to the user before changing them. The report must include:

- the suspected threshold;
- the number of affected companies out of the tested population;
- representative companies near the boundary;
- how their values and labels would change under a proposed adjustment; and
- whether the problem comes from the threshold, fallback assumptions, extraction, or the valuation model.

Thresholds must not be silently tuned to produce a preferred rating distribution.

## Acceptance criteria

The implementation is ready for user confirmation only when:

1. the frozen universe contains exactly 500 issuers;
2. all 500 receive a finite numeric base value and range;
3. all 500 receive `High`, `Medium`, or `Low` reliability;
4. every valuation uses the correct economic model lane;
5. no unresolved bad source, unit, currency, period, or share count enters a valuation;
6. annual backup within 12 months is treated as carried forward rather than automatically missing;
7. the 104-company and 500-company replay reports are reproducible;
8. the point-in-time backtest is reproducible and contains no look-ahead data;
9. any suspected unfair threshold is raised to the user with evidence; and
10. the real API and user interface show the same valuation features for all companies, with the user confirming the result.

## Superseded plan rules

Any earlier plan rule that conflicts with this approved design must be rewritten before implementation. In particular, this design supersedes:

- a target of only 450 published values;
- `Unavailable` as the normal outcome for unresolved but estimable companies;
- five public reliability levels; and
- the older 1%/5%/10% uncertainty policy.

The approved target is 500/500 numeric values with three public reliability levels and the V1 thresholds defined above.
