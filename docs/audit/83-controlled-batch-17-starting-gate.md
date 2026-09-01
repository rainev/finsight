# Controlled Universe Reset Batch 17 Starting Gate

Status: **firsthand starting audit complete; implementation and verification recorded in
[Audit 84](84-controlled-batch-17-result.md)**. No watchlist entry, withheld-history entry, serving
artifact, Batch 18, merge, push, or deployment is authorized before the initial result is confirmed.

## Reference and predecessor

- User signal: `Start Universe Reset Batch 17`
- Previous checkpoint: [Audit 82](82-batch-16-whole-repair-result.md), user-confirmed on
  2026-08-30 at Pass 3 / Conditional 7 / Withheld 0
- Frozen universe: `US-SP500-ISSUERS-2026-08-14-1.0`
- Frozen partition: `US-RESET-PARTITION-2026-08-14-2.0`
- Valuation date: `2026-08-14`
- Partition-root SHA-256:
  `fd49977122da8bdbaad1d336efeb5bf8480a21a3c63d03b57c0b961cb65908a4`

The dedicated worktree remains intentionally dirty on `codex/universe-reset-batch-10`. The root
checkout and all tracked/untracked work are preserved. `origin` remains
`https://github.com/rainev/finsight.git`; no push is authorized.

## Exact denominator

Frozen manifest SHA-256:
`ae4220d7346e650cce3a513166e5c2cde4a2f549e13a50194ef3f0c8e04fe444`

| Order | Ticker | CIK | Role | Economic lane |
| ---: | --- | --- | --- | --- |
| 1 | ABBV | 0001551152 | Core | Health Care / Biotechnology |
| 2 | ZTS | 0001555280 | Core | Health Care / Pharmaceuticals |
| 3 | MDT | 0001613103 | Core | Health Care / Equipment |
| 4 | MRNA | 0001682852 | Core | Health Care / Biotechnology |
| 5 | CI | 0001739940 | Core | Health Care / Services |
| 6 | STE | 0001757898 | Core | Health Care / Equipment |
| 7 | VTRS | 0001792044 | Core | Health Care / Pharmaceuticals |
| 8 | GEHC | 0001932393 | Core | Health Care / Equipment |
| 9 | KVUE | 0001944048 | Boundary | Consumer health products |
| 10 | SOLV | 0001964738 | Boundary | Health Care technology / recent spin |

✔ Exactly ten unique tickers and ten unique CIKs; eight core and two predeclared boundary issuers.
No company was selected from memory, market value, or a live index.

## Starting evidence and protected state

- Recovery Learning Watchlist: 103 — 94 current Conditional / 9 post-recovery Withheld
- Cumulative automatic-withheld history: 19
- Tracked active catalog remains Batch 01–10 only
- Canonical protected-tree hashes at start:
  - tracked valuation catalogs:
    `ea5e778fb6e4da2ea47bacf90cb813eca24654d1fe8fd62dec9cc3cb102bfe62`
  - frontend public data:
    `5157530c9c4baf3e9d5e6b0455a54579c94a5ead79c07145d9f4d35aef0e7017`
  - generated research surface:
    `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Watchlist SHA-256:
  `6d685d784ba4c051891ead366a01f5c356b53e84e3234e8adc64bca2d57254e7`
- Withheld-history SHA-256:
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`

Cache preflight:

- ✔ Complete cutoff-safe SEC packets exist for ABBV and KVUE.
- ✔ ABBV and KVUE have current parsed packages in the prior official-evidence cache. ABBV uses the
  2026-06-30 10-Q accession `0001551152-26-000026`; KVUE uses accession
  `0001944048-26-000142`, filed 2026-08-06 for the 2026-06-28 period.
- ✔ Eight SEC packets and eight current structural wrappers remain to capture.

## Gap register

| ID | Severity | Finding | Evidence | Required closure |
| --- | --- | --- | --- | --- |
| B17-01 | P0 | No typed Batch 17 contract or contract test exists | ✔ repository audit | Bind exact manifest/hash/order and fail fast on drift |
| B17-02 | P0 | Eight source packets and eight current structural wrappers are missing | ✔ cache inventory corrected against all official-evidence roots | Cache-first SEC capture, Python 3.11 structural parsing, protected-root proof |
| B17-03 | P0 | No source-linked Batch 17 history/model layer exists | ✔ repository audit | Build comparable annual/current history; route CI through managed-care equity economics and ordinary issuers through suitable cash models |
| B17-04 | P0 | Current acquisition, disposal, patent, claim, debt, share, and spin facts are not yet bound | ✔ repository audit | Reconcile each load-bearing event/bridge item exactly once; preserve unknowns as unknown |
| B17-05 | P0 | No exact-candidate challenge, deterministic replay, full suite/build, or 170-company API proof exists | ✔ repository/output audit | Separate source and economic challenge lenses; repair all Important/Critical findings; replay and real HTTP parity |
| B17-06 | P0 | No Batch 17 result or confirmation gate exists | ✔ audit index | Record exact Pass/Conditional/Withheld values and stop before confirmation/recovery/Batch 18 |

## Reuse and execution rule

Reuse the Batch 16 contract/capture/history/public/catalog/API patterns and shared historical,
legal-tail, and specialist equity models. Do not copy Batch 16 classifications or constants. MRNA,
VTRS, GEHC, KVUE, and SOLV require explicit comparability review; CI requires an equity-level
managed-care route rather than an industrial debt bridge. Unknown facts are never zero, and no
assumption may be calibrated to market prices or competitor displayed values.
