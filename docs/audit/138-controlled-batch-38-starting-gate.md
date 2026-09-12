# Controlled Universe Reset Batch 38 Starting Gate

Date: 2026-09-07
Status: **firsthand audited; implementation in progress**

## Frozen denominator

The deterministic Batch 38 manifest is exactly:

`EG, GPN, PFG, FIS, PRU, WTW, MA, CME, CPAY, AIZ`

All ten are in the frozen Financials cohort. EG and AIZ are rare-subindustry boundaries. The
valuation date remains **2026-08-14**.

Manifest SHA-256:
`876a53798385ea4afc09ae57ff95abe7afe09dff542fe9759f700920df0e8bb2`.

## Confirmed predecessor

Batch 37 is user-confirmed. The isolated predecessor contains exactly **370 companies**:

- Pass **116**
- Conditional **243**
- Withheld **11**
- Numeric **359**

Predecessor catalog tree:
`39d43452805ada42dd319ea075ba2a9a227440b702bac7b96e3e11a64134d1b8`.
Predecessor manifest SHA-256:
`484533ce5a2c83c9ce8bc7bafed366f38dc4d1485be420c7d286a30dcd4ca8d3`.

The Recovery Learning Watchlist remains **254** — 243 Conditional and 11 Withheld — SHA-256
`a476c3503379e52326b3fb393ae9189d83fddf1764c015f5013c3b94b6141f34`.
The cumulative withheld register remains **21 entries**, SHA-256
`22fb28e93e84996d6b2fe1bd836d0cee3df746f3536aec26b57dfc1215751bb6`.

## Required model gates

- EG, PFG, PRU, and AIZ require parent/common-equity insurance models with catastrophe/mortality,
  reserve, reinsurance, investment-mark, preferred/NCI, and regulatory-capital controls.
- GPN, FIS, MA, and CPAY are economically operating payment processors. They require settlement,
  customer/merchant-funds, captive-finance, acquisition, debt, and recurring-reinvestment separation
  before operating FCFF can be used.
- WTW requires an insurance-broker model with acquisition/retention, pension, debt, and recurring
  commission/cash conversion evidence.
- CME requires a financial-exchange/data model that keeps clearing/member collateral and client
  assets out of issuer cash while preserving transaction-volume and market-cycle history.

Every issuer must use the controlling cutoff-safe filing, exact annual periods plus current TTM,
complete accepted/rejected event receipts, source-hash verification, private reported/estimated
lineage, public-safe ranges, and exact calculator/model identity.

## Boundary

This gate authorizes Batch 38 initial processing only. Do not perform recovery, watchlist/withheld
bookkeeping, Batch 39, tracked serving promotion, merge, push, or deployment. Stop after presenting
Pass/Conditional/Withheld results for user confirmation.
