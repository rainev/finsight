# Controlled Universe Reset Batch 20 Starting Gate

Status: **firsthand starting audit complete; implementation and verification recorded in
[Audit 90](90-controlled-batch-20-result.md)**. The user explicitly authorized
`Start Universe Reset Batch 20`. No recovery, watchlist/withheld-history mutation, tracked serving
promotion, Batch 21, merge, push, or deployment is authorized before confirmation.

## Reference and predecessor

- Previous checkpoint: [Audit 88](88-controlled-batch-19-result.md), user-confirmed on
  2026-08-30 at Pass 4 / Conditional 6 / Withheld 0
- Cumulative confirmed state: 68 Pass / 113 Conditional / 9 Withheld; numeric 181/190
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
`a6da41ca5e593099973619dae32ac1eca1321c322161a9ea64274b5f35986301`

| Order | Ticker | CIK | Role | Economic lane |
| ---: | --- | --- | --- | --- |
| 1 | PNR | 0000077360 | Core | Industrial Machinery |
| 2 | ROL | 0000084839 | Core | Environmental & Facilities Services |
| 3 | AOS | 0000091142 | Core | Building Products |
| 4 | SNA | 0000091440 | Core | Industrial Machinery |
| 5 | LUV | 0000092380 | Core | Passenger Airlines |
| 6 | SWK | 0000093556 | Core | Industrial Machinery |
| 7 | UAL | 0000100517 | Core | Passenger Airlines |
| 8 | UNP | 0000100885 | Core | Rail Transportation |
| 9 | CTAS | 0000723254 | Boundary | Diversified Support Services |
| 10 | PAYX | 0000723531 | Boundary | Human Resource & Employment Services |

✔ Exactly ten unique tickers and CIKs; eight core and two predeclared boundary issuers. All use
the frozen `operating_fcff` partition family, but Snap-on's finance business and Paychex client
funds require issuer-specific economic treatment rather than blind industrial bridges.

## Starting evidence and protected state

- Recovery Learning Watchlist: 122 — 113 current Conditional / 9 post-recovery Withheld
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
  `fcc02bdb2cd279bf424937ebec2492c64c0818f09f3e7ba9ee0a533f1d84cbaa`
- Withheld-history SHA-256:
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`

Cache preflight:

- ✔ Complete cutoff-safe SEC packets and current parsed packages exist for UAL and UNP in the
  difficult-106 evidence cache.
- ✔ PNR, ROL, AOS, SNA, LUV, SWK, CTAS, and PAYX require current SEC packets and structural
  packages.
- ✔ Expected cache-first work: two packet/wrapper reuses and eight captures.

The hash values above use the capture guard's raw-byte tree algorithm. They are compared only with
later hashes produced by that same algorithm.

## Gap register

| ID | Severity | Finding | Evidence | Required closure |
| --- | --- | --- | --- | --- |
| B20-01 | P0 | No typed Batch 20 contract or contract test exists | ✔ repository audit | Bind exact manifest/hash/order and fail fast on drift |
| B20-02 | P0 | Eight source packets and eight current structural wrappers are missing | ✔ cache inventory | Cache-first SEC capture, Python 3.11 structural parsing, protected-root proof |
| B20-03 | P0 | No Batch 20 source-linked histories or models exist | ✔ repository audit | Build comparable history and suitable operating or equity-level routes |
| B20-04 | P0 | Current finance/client funds, fleet commitments, transaction states, debt/leases, claims, and shares are unbound | ✔ repository audit | Reconcile each item once and preserve unavailable amounts as unknown |
| B20-05 | P0 | No exact-candidate source/economic challenge, deterministic replay, full suite/build, or 200-company API proof exists | ✔ repository/output audit | Repair all Important/Critical findings; replay and real HTTP parity |
| B20-06 | P0 | No Batch 20 result or confirmation gate exists | ✔ audit index | Record exact Pass/Conditional/Withheld values and stop before confirmation/recovery/Batch 21 |

## Reuse and execution rule

Reuse Batch 19's contract/capture/history/public/catalog/API patterns and the shared historical,
cutoff-event, client-funds, airline-cycle, and mixed-finance controls. Do not copy Batch 19
classifications or constants. Snap-on finance receivables and debt must not be double counted;
Paychex client funds cannot become surplus cash; LUV/UAL fleet obligations need coherent cash
coverage; Union Pacific's cutoff transaction state must remain distinct from standalone value. No
market price, analyst target, or competitor displayed value may calibrate the ranges.
