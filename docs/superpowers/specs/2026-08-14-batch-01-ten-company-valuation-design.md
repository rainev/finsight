# FinSight Batch 01: Ten-Company Valuation Design

Date: 2026-08-14
Status: User-approved direction; written design awaiting user review

## Objective

Run the evidence-aware valuation pipeline for exactly ten named companies, verify each result through the prepared artifact and local API, report the outcome as an exact count out of ten, and stop. Batch 02 must not begin until the user explicitly requests it.

This batch is the first controlled step toward the separate 500/500 objective. It proves a small, mixed-model slice of the production-shaped pipeline; it does not claim that the full company universe is complete.

## Fixed Batch 01 manifest

The manifest is fixed before seeing new pipeline results. A failing company must not be replaced with an easier one.

| Ticker | Company | Governed valuation lane |
| --- | --- | --- |
| AAPL | Apple Inc. | FCFF/DCF with EPV cross-check |
| MSFT | Microsoft Corporation | FCFF/DCF with EPV cross-check |
| CRM | Salesforce, Inc. | FCFF/DCF with EPV cross-check |
| ANET | Arista Networks, Inc. | FCFF/DCF with EPV cross-check |
| WDC | Western Digital Corporation | FCFF/DCF with EPV cross-check |
| DELL | Dell Technologies Inc. | FCFF/DCF with EPV cross-check |
| JPM | JPMorgan Chase & Co. | Residual income |
| BAC | Bank of America Corporation | Residual income |
| NEE | NextEra Energy, Inc. | Dividend discount model |
| O | Realty Income Corporation | Governed REIT/FFO route |

The first six test the ordinary operating-company path. JPM and BAC test the bank path. NEE tests the utility path. O tests the current specialist REIT path. The REIT lane remains model-capped at `Low` reliability unless the implementation supplies evidence that satisfies an already-approved stronger model contract; the batch must not silently relax that cap.

## Verified starting baseline

At branch commit `edbb049`, all ten tickers have stored baseline artifacts, but the old output is only 5 of 10 numeric:

- AAPL, JPM, BAC, NEE, and O have finite stored scenario ranges with `review_required` status.
- MSFT, CRM, ANET, WDC, and DELL are `withheld` and have no stored scenario range.

This is the before-state, not a Batch 01 result. None of the ten counts as complete until it is regenerated and verified under the new evidence, reliability, artifact, and API gates below.

## Point-in-time boundary

The batch valuation date is `2026-08-14`. Evidence is allowed only when it was publicly available on or before that date. Every accepted source must retain its filing or effective date, period, accession or equivalent source identifier, and provenance. Later information must not be used to improve an earlier value.

## Pipeline boundary

```text
Immutable 10-company manifest
        |
SEC submissions and Companyfacts evidence
        |
Arelle structural extraction when the fast path is insufficient
        |
Source and provenance validation
        |
Approved fallback ladder
        |
Governed company-specific valuation lane
        |
Low / base / high intrinsic values
        |
High / Medium / Low reliability
        |
Private evidence + safe public artifact
        |
Local list and detail API verification
```

Arelle remains an offline ingestion tool. It must not be imported into the FastAPI process. The API reads prepared JSON artifacts only.

The shared evidence-aware reliability work already under development is a prerequisite. Its independent review, public reliability schema, real-data regeneration, and local API verification must be completed before Batch 01 can pass.

## Evidence and fallback rules

For every material valuation input, use the highest trustworthy level available:

1. current directly reported company fact;
2. current Arelle-extracted fact with source evidence;
3. trustworthy reported aggregate that replaces unavailable detail without double counting;
4. trustworthy older company fact;
5. conservative range based on that company's history; or
6. conservative sector estimate as the final fallback.

A trustworthy annual value no more than 365 days old is `carried_forward`, not missing. Age alone does not create a harsh reliability penalty. Its possible economic change is reflected in the accounting uncertainty range.

The pipeline must never:

- substitute zero for unavailable data;
- accept unresolved source, period, unit, currency, or share-denominator conflicts;
- hide rejected conflicts;
- switch a company to an economically unrelated model because extraction is difficult; or
- change the approved 5%, 20%, and 40% thresholds to make this batch pass.

If the replay suggests a threshold is unfair, report the affected companies and evidence to the user. Do not tune the threshold during this batch without a separate approval.

## Generation and promotion

Initial Batch 01 results are generated under the non-serving directory `output/batch-01-ten-company/`. This prevents a partial run from changing what the local API serves.

Only after all ten companies satisfy the per-company gates may exactly ten safe public artifacts be promoted to the feature branch's serving data. Promotion does not merge, deploy, or alter `main`. The untracked replay evidence remains outside commits unless a later plan names a specific report for version control.

## Per-company completion gate

A company counts as complete only when all of the following are verified:

1. ticker, issuer, and CIK identity match the fixed manifest;
2. accepted inputs are linked to dated source evidence and rejected conflicts are recorded;
3. the governed model lane is correct for the company;
4. low, base, and high intrinsic values are finite, ordered, and denominated per share in the declared currency;
5. reliability is exactly `High`, `Medium`, or `Low`, with its caps and reason codes recorded privately;
6. the public artifact contains no unsafe private evidence or prohibited output;
7. local API list and detail responses agree with the promoted artifact; and
8. regeneration is deterministic from the recorded inputs and policy versions.

An existing numeric artifact does not automatically pass these gates. It is baseline evidence only until regenerated and checked through the new pipeline.

## Batch completion gate

Batch 01 is ready for user confirmation only when:

- exactly the ten fixed companies were attempted;
- all 10 of 10 have finite low, base, and high values;
- all 10 of 10 have a valid reliability label;
- all 10 of 10 use the governed model lane;
- no company was dropped, swapped, or silently skipped;
- the feature-branch API returns all ten identities and matching values;
- focused tests and the full backend suite pass;
- the report separates verified facts from unverified claims; and
- the user reviews the evidence and confirms the batch.

If one company cannot satisfy a gate, the result is honestly reported as partial, such as `9/10`. The failing member is debugged or reported with its exact blocker; it is not replaced.

## Verification evidence

The implementation report must include:

- the immutable manifest and valuation date;
- source accession, period, unit, currency, and share-denominator checks;
- accepted fallback level and rejected conflict reasons for each company;
- model lane and low/base/high value for each company;
- accounting-impact ratio, scenario-movement ratio, final reliability, and caps;
- focused and full test command outputs;
- regeneration command and exact `X/10` outcome;
- local API list/detail checks for all ten; and
- the branch and commit containing any promoted artifacts.

## Explicit exclusions

Batch 01 does not include:

- Batch 02 or any automatic continuation beyond these ten companies;
- the remaining 490-company manifest or full-universe replay;
- a frontend or user-interface change;
- current market price or under/over-value comparison;
- production deployment or a merge into `main`;
- a complete historical backtest; or
- silent reliability-threshold changes.

These exclusions keep the first batch focused on whether FinSight can reliably turn source-linked accounts into production-shaped intrinsic values across its existing model lanes.

## Stop condition

After reporting Batch 01 evidence, the agent stops and asks the user to confirm the result. No work on the next ten companies begins without a new explicit instruction from the user.
