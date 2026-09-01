# Controlled Universe Reset Batch 19 Starting Gate

Status: **firsthand starting audit complete; implementation and verification recorded in
[Audit 88](88-controlled-batch-19-result.md)**. The user explicitly authorized
`Start Universe Reset Batch 19`. No recovery, watchlist/withheld-history mutation, tracked serving
promotion, Batch 20, merge, push, or deployment is authorized before confirmation.

## Reference and predecessor

- Previous checkpoint: [Audit 86](86-controlled-batch-18-result.md), user-confirmed on
  2026-08-30 at Pass 5 / Conditional 5 / Withheld 0
- Cumulative confirmed state: 64 Pass / 107 Conditional / 9 Withheld; numeric 171/180
- Frozen universe: `US-SP500-ISSUERS-2026-08-14-1.0`
- Frozen partition: `US-RESET-PARTITION-2026-08-14-2.0`
- Valuation date: `2026-08-14`
- Partition-root SHA-256:
  `fd49977122da8bdbaad1d336efeb5bf8480a21a3c63d03b57c0b961cb65908a4`

The dedicated worktree remains intentionally dirty on `codex/universe-reset-batch-10`; all
existing tracked and untracked work is preserved. `origin` remains
`https://github.com/rainev/finsight.git`. No push is authorized.

## Exact denominator

Frozen manifest SHA-256:
`0350deebae8c9fef54ba37afd4e51e7221708eceb3ed40115b1398f815c6c1f6`

| Order | Ticker | CIK | Role | Economic lane |
| ---: | --- | --- | --- | --- |
| 1 | GE | 0000040545 | Core | Aerospace & Defense |
| 2 | HUBB | 0000048898 | Core | Industrial Machinery |
| 3 | ITW | 0000049826 | Core | Industrial Machinery |
| 4 | J | 0000052988 | Core | Construction & Engineering |
| 5 | MAS | 0000062996 | Core | Building Products |
| 6 | MMM | 0000066740 | Boundary | Industrial Conglomerates |
| 7 | NDSN | 0000072331 | Core | Industrial Machinery |
| 8 | PCAR | 0000075362 | Core | Construction/Heavy Equipment |
| 9 | PH | 0000076334 | Core | Industrial Machinery |
| 10 | DE | 0000315189 | Boundary | Agricultural & Farm Machinery |

✔ Exactly ten unique tickers and CIKs; eight core and two predeclared boundary issuers. All use
the frozen `operating_fcff` partition family, but PCAR and Deere require captive-finance-aware
equity treatment rather than a blind industrial enterprise-value debt bridge.

## Starting evidence and protected state

- Recovery Learning Watchlist: 116 — 107 current Conditional / 9 post-recovery Withheld
- Cumulative automatic-withheld history: 19
- Tracked active catalog remains Batch 01–10 only
- Canonical capture-guard protected-tree hashes:
  - tracked valuation catalogs:
    `38efe664dc981e9d2383ece43b66e9ae326b4b9a7cc2443f2463498432ef66a8`
  - frontend public data:
    `353a14bc672002e88d248811f98d23d4c1fb47cf28e526d969f463f256260274`
  - generated research surface:
    `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Watchlist SHA-256:
  `d1db5d18e687ed8a9c615cd2456c0b43f64626b04a9a1049fb71a840f023a274`
- Withheld-history SHA-256:
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`

Cache preflight:

- ✔ Complete cutoff-safe SEC packets and current parsed packages exist for ITW, PH, and DE in the
  difficult-106 evidence cache.
- ✔ GE, HUBB, J, MAS, MMM, NDSN, and PCAR require current SEC packets and structural packages.
- ✔ Expected cache-first work: three packet/wrapper reuses and seven captures.

The hash values above use the capture guard's raw-byte tree algorithm. They are compared only with
later hashes produced by that same algorithm.

## Gap register

| ID | Severity | Finding | Evidence | Required closure |
| --- | --- | --- | --- | --- |
| B19-01 | P0 | No typed Batch 19 contract or contract test exists | ✔ repository audit | Bind exact manifest/hash/order and fail fast on drift |
| B19-02 | P0 | Seven source packets and seven current structural wrappers are missing | ✔ cache inventory | Cache-first SEC capture, Python 3.11 structural parsing, protected-root proof |
| B19-03 | P0 | No Batch 19 source-linked histories or models exist | ✔ repository audit | Build comparable history and suitable operating or equity-level routes |
| B19-04 | P0 | Current separations, finance operations, settlements, acquisitions, debt/leases, claims, and shares are unbound | ✔ repository audit | Reconcile each item once and preserve unavailable amounts as unknown |
| B19-05 | P0 | No exact-candidate source/economic challenge, deterministic replay, full suite/build, or 190-company API proof exists | ✔ repository/output audit | Repair all Important/Critical findings; replay and real HTTP parity |
| B19-06 | P0 | No Batch 19 result or confirmation gate exists | ✔ audit index | Record exact Pass/Conditional/Withheld values and stop before confirmation/recovery/Batch 20 |

## Reuse and execution rule

Reuse Batch 18's contract/capture/history/public/catalog/API patterns and the shared historical,
legal-tail, cutoff-event, and mixed-finance controls. Do not copy Batch 18 classifications or
constants. GE and Jacobs require explicit continuing-company comparability checks; 3M requires
settlement obligations and related offsets to be counted once; PCAR and Deere finance receivables,
debt, earnings, and common equity must not be double counted. No market price, analyst target, or
competitor displayed value may calibrate the ranges.
