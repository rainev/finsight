# Controlled Universe Reset Batch 18 Starting Gate

Status: **firsthand starting audit complete; implementation and verification recorded in
[Audit 86](86-controlled-batch-18-result.md)**. No watchlist/withheld-history mutation, tracked
serving artifact, Batch 19, merge, push, or deployment is authorized before confirmation.

## Reference and predecessor

- User signal: `Start Universe Reset Batch 18`
- Previous checkpoint: [Audit 84](84-controlled-batch-17-result.md), user-confirmed on
  2026-08-30 at Pass 2 / Conditional 8 / Withheld 0
- Frozen universe: `US-SP500-ISSUERS-2026-08-14-1.0`
- Frozen partition: `US-RESET-PARTITION-2026-08-14-2.0`
- Valuation date: `2026-08-14`
- Partition-root SHA-256:
  `fd49977122da8bdbaad1d336efeb5bf8480a21a3c63d03b57c0b961cb65908a4`

The dedicated worktree remains intentionally dirty on `codex/universe-reset-batch-10`; all existing
tracked and untracked work is preserved. `origin` remains `https://github.com/rainev/finsight.git`.
No push is authorized.

## Exact denominator

Frozen manifest SHA-256:
`c2574b73d31c4581d84087b6f4ee5d624831adc9daf59a3fb26b5fb07b413a38`

| Order | Ticker | CIK | Role | Economic lane |
| ---: | --- | --- | --- | --- |
| 1 | HWM | 0000004281 | Core | Aerospace & Defense |
| 2 | ADP | 0000008670 | Boundary | Human Resource & Employment Services |
| 3 | BA | 0000012927 | Core | Aerospace & Defense |
| 4 | CAT | 0000018230 | Core | Construction/Heavy Equipment |
| 5 | CMI | 0000026172 | Core | Construction/Heavy Equipment |
| 6 | DAL | 0000027904 | Core | Passenger Airlines |
| 7 | DOV | 0000029905 | Core | Industrial Machinery |
| 8 | EMR | 0000032604 | Core | Electrical Components & Equipment |
| 9 | EFX | 0000033185 | Boundary | Research & Consulting Services |
| 10 | GD | 0000040533 | Core | Aerospace & Defense |

✔ Exactly ten unique tickers and CIKs; eight core and two predeclared boundary issuers. All use the
frozen `operating_fcff` partition family, but CAT's captive finance and ADP's client funds require
issuer-specific economic treatment rather than blind industrial bridges.

## Starting evidence and protected state

- Recovery Learning Watchlist: 111 — 102 current Conditional / 9 post-recovery Withheld
- Cumulative automatic-withheld history: 19
- Tracked active catalog remains Batch 01–10 only
- Canonical protected-tree hashes:
  - tracked valuation catalogs:
    `ea5e778fb6e4da2ea47bacf90cb813eca24654d1fe8fd62dec9cc3cb102bfe62`
  - frontend public data:
    `5157530c9c4baf3e9d5e6b0455a54579c94a5ead79c07145d9f4d35aef0e7017`
  - generated research surface:
    `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Watchlist SHA-256:
  `4e240453662d70a282797e85b1ef66c668adb68ca15d7e90492a3ea8d185a137`
- Withheld-history SHA-256:
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`

Cache preflight:

- ✔ Complete cutoff-safe SEC packets and current parsed packages exist for BA, CAT, CMI, DAL,
  and GD in the difficult-106 cache.
- ✔ HWM, ADP, DOV, EMR, and EFX require current SEC packets and structural packages.
- ✔ Expected cache-first work: five packet/wrapper reuses and five captures.

## Gap register

| ID | Severity | Finding | Evidence | Required closure |
| --- | --- | --- | --- | --- |
| B18-01 | P0 | No typed Batch 18 contract or contract test exists | ✔ repository audit | Bind exact manifest/hash/order and fail fast on drift |
| B18-02 | P0 | Five source packets and five current structural wrappers are missing | ✔ cache inventory | Cache-first SEC capture, Python 3.11 structural parsing, protected-root proof |
| B18-03 | P0 | No Batch 18 source-linked histories or models exist | ✔ repository audit | Build comparable history; use suitable operating, mixed-finance, client-funds, cyclical, or equity-at-risk routes |
| B18-04 | P0 | Current events, debt/leases, client funds, finance claims, legal reserves, and shares are unbound | ✔ repository audit | Reconcile each item once and preserve unknown values as unknown |
| B18-05 | P0 | No exact-candidate challenge, deterministic replay, full suite/build, or 180-company API proof exists | ✔ repository/output audit | Separate source and economic review; repair all Important/Critical findings; replay and real HTTP parity |
| B18-06 | P0 | No Batch 18 result or confirmation gate exists | ✔ audit index | Record exact Pass/Conditional/Withheld values and stop before confirmation/recovery/Batch 19 |

## Reuse and execution rule

Reuse Batch 17's contract/capture/history/public/catalog/API patterns and the shared historical,
asset-runway, legal-tail, and mixed-finance controls. Do not copy Batch 17 classifications or
constants. Boeing, Caterpillar, Cummins, Delta, and Emerson require explicit cycle/event review;
ADP client funds must never be treated as ordinary surplus cash; CAT finance receivables/debt must
not be double counted. No market price, analyst target, or competitor displayed value may calibrate
the ranges.
