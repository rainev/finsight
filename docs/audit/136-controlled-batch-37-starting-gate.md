# Controlled Universe Reset Batch 37 Starting Gate

Date: 2026-09-06
Status: **firsthand audited; implementation in progress**

## Frozen denominator

The deterministic Batch 37 manifest is exactly:

`IVZ, ERIE, ACGL, FDS, OKE, MCO, BRK.B, MET, TROW, NDAQ`

Eight issuers are Financials core companies. OKE is the asset-backed energy boundary and BRK.B is
the rare multi-sector holding-company boundary. The valuation date remains **2026-08-14**.

Manifest SHA-256:
`2e768f125d982c4a2f2769e5ec4ccb3ed55077717abe94146c6f7e4734be640b`.

## Confirmed predecessor

Batch 36 and its one VLO recovery attempt are user-confirmed. The isolated predecessor contains
exactly **360 companies**:

- Pass **116**
- Conditional **233**
- Withheld **11**
- Numeric **349**

Predecessor catalog tree:
`eb7e73ccaa8ec9b8c8d6e0d1aeeab26f269c0254af1ca90a9d9fc0128b8fa5d1`.
Predecessor manifest SHA-256:
`060a0cf1e5aada4b469edc0b33f43d4234232376553186e96bd18c38bb9fc572`.

The Recovery Learning Watchlist remains **244** — 233 Conditional and 11 Withheld — SHA-256
`7027181b9bd2262e6c7e0d707a44ba3d4748d2ae44d50b7ed83ddafcaaa10b93`.
The cumulative withheld register contains **21 entries**, SHA-256
`22fb28e93e84996d6b2fe1bd836d0cee3df746f3536aec26b57dfc1215751bb6`.

## Required model gates

- IVZ/TROW require asset-manager equity models that keep client AUM separate from issuer cash and
  preserve fee/market-cycle history.
- ERIE requires a management-fee/reciprocal-insurance treatment that does not mistake policyholder
  economics for ordinary parent cash.
- ACGL/MET require insurer residual-income models with parent-attributable earnings, period-specific
  preferred/NCI claims, catastrophe/reserve history, and regulatory-capital warnings.
- FDS/MCO/NDAQ require financial-data/exchange models with acquisition, subscription, transaction,
  debt, and recurring reinvestment evidence separated.
- BRK.B requires a holding-company/insurance model that keeps insurance float and operating
  subsidiaries inside equity economics while treating noncontrolling interests and share classes
  exactly once.
- OKE requires a resource-cycle cash-FCFF model with complete debt/lease/NCI/preferred bridge,
  project/acquisition events, and bounded pipeline cash conversion.

Every issuer must use the controlling cutoff-safe filing, exact annual periods plus current TTM,
complete accepted/rejected event receipts, source-hash verification, private reported/estimated
lineage, public-safe ranges, and exact calculator/model identity.

## Boundary

This gate authorizes Batch 37 initial processing only. Do not perform recovery, watchlist/withheld
bookkeeping, Batch 38, tracked serving promotion, merge, push, or deployment. Stop after presenting
Pass/Conditional/Withheld results for user confirmation.
