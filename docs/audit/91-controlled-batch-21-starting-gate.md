# Controlled Universe Reset Batch 21 Starting Gate

Status: **firsthand starting audit complete; implementation and verification recorded in
[Audit 92](92-controlled-batch-21-result.md)**. No outward action is authorized before confirmation.

## Reference and predecessor

- Previous checkpoint: [Audit 90](90-controlled-batch-20-result.md), user-confirmed on
  2026-08-30 at Pass 3 / Conditional 7 / Withheld 0
- Cumulative confirmed state: 71 Pass / 120 Conditional / 9 Withheld; numeric 191/200
- Frozen universe/partition: `US-SP500-ISSUERS-2026-08-14-1.0` /
  `US-RESET-PARTITION-2026-08-14-2.0`
- Valuation date: `2026-08-14`
- Partition-root SHA-256:
  `fd49977122da8bdbaad1d336efeb5bf8480a21a3c63d03b57c0b961cb65908a4`

The intentionally dirty `codex/universe-reset-batch-10` worktree is preserved. `origin` remains
`https://github.com/rainev/finsight.git`; no push is authorized.

## Exact denominator

Frozen manifest SHA-256:
`b4cd7b3c64c5de53dce64017108a2cdfe12faf63865044088d89df231b9a3a5b`

| Order | Ticker | CIK | Role | Economic lane |
| ---: | --- | --- | --- | --- |
| 1 | RTX | 0000101829 | Core | Aerospace & Defense |
| 2 | EME | 0000105634 | Core | Construction & Engineering |
| 3 | LHX | 0000202058 | Core | Aerospace & Defense |
| 4 | TXT | 0000217346 | Core | Aerospace & Defense |
| 5 | GWW | 0000277135 | Core | Industrial Distribution |
| 6 | CSX | 0000277948 | Core | Rail Transportation |
| 7 | NSC | 0000702165 | Core | Rail Transportation |
| 8 | JBHT | 0000728535 | Boundary | Cargo Ground Transportation |
| 9 | EXPD | 0000746515 | Core | Air Freight & Logistics |
| 10 | FAST | 0000815556 | Boundary | Trading Companies & Distributors |

✔ Exactly ten unique tickers and CIKs; eight core and two predeclared boundary issuers, all in the
frozen `operating_fcff` family.

## Starting evidence and protected state

- Recovery Learning Watchlist: 129 — 120 Conditional / 9 post-recovery Withheld
- Cumulative automatic-withheld history: 19
- Tracked active catalog remains Batch 01–10 only
- Capture-guard hashes: catalogs `38efe664dc981e9d2383ece43b66e9ae326b4b9a7cc2443f2463498432ef66a8`;
  frontend data `353a14bc672002e88d248811f98d23d4c1fb47cf28e526d969f463f256260274`;
  generated research `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Watchlist SHA-256: `723b31bac31da7918a71fda0919901f8a0efbb8572cfba66d90360d29bc402b2`
- Withheld-history SHA-256: `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`

Cache preflight: RTX, CSX, NSC, and FAST are reusable; EME, LHX, TXT, GWW, JBHT, and EXPD require
current packets/wrappers. Expected split: four reused / six captured.

## Gap register

| ID | Severity | Finding | Required closure |
| --- | --- | --- | --- |
| B21-01 | P0 | No typed Batch 21 contract/test | Bind exact manifest/hash/order |
| B21-02 | P0 | Six current source/structural packages missing | Cache-first capture and protected-root proof |
| B21-03 | P0 | No Batch 21 histories/models | Build comparable source-linked history and suitable routes |
| B21-04 | P0 | Engine claims, acquisitions, finance, rail transaction, debt/leases, shares unbound | Reconcile each once; preserve unknowns |
| B21-05 | P0 | No final challenge/replay/full-suite/210-API proof | Repair all Important/Critical findings and verify real HTTP |
| B21-06 | P0 | No result/confirmation gate | Report exact three-way outcomes and stop before Batch 22 |

Reuse Batch 20's proven pipeline. RTX engine-program exposure, NSC's pending transaction, and any
material portfolio/finance dependencies require explicit treatment. No market price or competitor
displayed value may calibrate the ranges.
