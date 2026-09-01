# Controlled Universe Reset Batch 26 Starting Gate

Date: 2026-08-31  
Status: **firsthand audited; implementation authorized and in progress**

## Reference and exact denominator

The user explicitly authorized `Start Universe Reset Batch 26`. The only denominator authority is
`backend/app/us_valuation/config/reset_batches_2026_08_14/batch_26.json`, SHA-256
`0c767cc411938e49e1e2d731470c158c76de6e16ff0cd8c518293c482651964a`. It matches the frozen
partition receipt and contains exactly ten unique issuers in this order:

1. AMD — Advanced Micro Devices
2. SWKS — Skyworks Solutions
3. ADI — Analog Devices
4. AMAT — Applied Materials
5. GLW — Corning
6. HPQ — HP Inc.
7. INTC — Intel
8. IBM — IBM
9. MSI — Motorola Solutions
10. APH — Amphenol

There are eight Information Technology core issuers and two electronic-component boundary issuers
(GLW and APH), all routed to the operating-FCFF family by the frozen partition. The valuation date
is 2026-08-14. The partition root remains
`fd49977122da8bdbaad1d336efeb5bf8480a21a3c63d03b57c0b961cb65908a4` and proves an exact
500-issuer, 50-batch cover.

## Predecessor and protected state

- Batch 25 recovery is user-confirmed in Audit 105 at Pass 2 / Conditional 8 / Withheld 0.
- Confirmed isolated cumulative state through Batch 25: 250 issuers, 92 available / 149
  conditional / 9 unavailable.
- Recovery Learning Watchlist: 158 entries — 149 Conditional / 9 Withheld.
- Append-only automatic-withheld history: 19 entries.
- Tracked serving catalog remains Batch 01–10 only.
- Protected tree hashes under the shared `_tree` contract:
  - backend catalog root: `ea5e778fb6e4da2ea47bacf90cb813eca24654d1fe8fd62dec9cc3cb102bfe62`
  - frontend public data: `5157530c9c4baf3e9d5e6b0455a54579c94a5ead79c07145d9f4d35aef0e7017`
  - generated frontend research: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

## Reuse check and current source readiness

The current difficult-106 cache already contains complete cutoff packets for AMD and APH at
`output/difficult-106-sec-source-packets-20260824`. It also contains current parsed/package
evidence for AMD accession 0000002488-26-000123 and APH accession 0001104659-26-089194 under
`output/official-evidence-difficult-106-part-1`. No complete Batch-style packet or structural
wrapper was found for the other eight issuers. Cache-first tooling from Batch 25 can be reused; no
parallel source pipeline is needed.

## Gap register

- **P0 ✔ Denominator contract:** no Batch 26 typed contract or exact-order test exists yet.
- **P0 ✔ Source packets:** SWKS, ADI, AMAT, GLW, HPQ, INTC, IBM, and MSI need cutoff-safe SEC
  packets; AMD and APH must be rewrapped from validated cache without refetching.
- **P0 ✔ Structural evidence:** eight controlling filings require package capture/offline Arelle
  parsing; AMD/APH current parses require identity-checked reuse.
- **P0 ✔ History and bridges:** no Batch 26 TTM/annual history, cash/debt/claims/share bridge, or
  acquisition/subsequent-event ledger exists.
- **P0 ✔ Economic suitability:** semiconductor cycle, AI/data-center R&D and capex, fab/foundry
  reinvestment, acquisition integration, restricted investments, negative equity, and large
  portfolio events must affect actual arithmetic or an explicit Conditional release condition.
- **P0 ✔ Classification:** each issuer must receive an ordinary Pass attempt before Conditional or
  Withheld; no quota is permitted.
- **P0 ✔ Verification:** no exact candidate, independent challenge, deterministic replay, focused
  and full suite, cumulative 260-company catalog, or real API evidence exists yet.
- **P1 ✔ Bookkeeping boundary:** watchlist and withheld registers must remain unchanged until user
  confirmation and any separately authorized recovery.

## Gate

Proceed through one controlled Batch 26 initial pass. Generated evidence remains untracked. Stop
after presenting Pass / Conditional / Withheld for user confirmation. Do not start recovery, Batch
27, serving promotion, merge, push, or deployment.

