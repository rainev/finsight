# Controlled Universe Reset Batch 35 Starting Gate

Date: 2026-09-04
Status: **firsthand audited; implementation authorized and in progress**

## Exact denominator

The user explicitly authorized `Start Universe Reset batch 35`. The denominator authority is
`backend/app/us_valuation/config/reset_batches_2026_08_14/batch_35.json`, SHA-256
`c6476d96abc4e22605b0b3454608be05de67b69d3b237245dab06788e011e35f`. It contains exactly ten
unique issuers in this order:

WFC, WMB, AON, SCHW, GL, AJG, PNC, RJF, CFG, JKHY.

Eight are Financials core issuers. WFC is a diversified-bank boundary and WMB is the asset-backed
energy boundary. The frozen model families are financial-equity for nine companies and
resource-cycle FCFF for WMB. Valuation date remains 2026-08-14.

## Predecessor and protected state

- The Batch 34 Sol repair is user-confirmed in Audit 128.
- Confirmed cumulative state through Batch 34: **340 issuers — 116 Pass / 214 Conditional / 10
  Withheld; 330 numeric**.
- Recovery Learning Watchlist: **224 entries — 214 Conditional / 10 Withheld**, SHA-256
  `ec861afc1778e7de157ad40478b9b2f90fa49e9205d2432c2d4ea344a4e581b7`.
- Append-only withheld register: 20 entries, SHA-256
  `7530586e01fdf65a61eea35feeca4b47337bc19134caeb4a87e4e8a87a016fce`.
- Tracked serving roots remain unchanged: backend catalog
  `ea5e778fb6e4da2ea47bacf90cb813eca24654d1fe8fd62dec9cc3cb102bfe62`, frontend public data
  `5157530c9c4baf3e9d5e6b0455a54579c94a5ead79c07145d9f4d35aef0e7017`, generated research
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Batch-specific gates

- Banks, brokerages, and life insurance use equity-level economics; deposits, client assets,
  policy reserves, and regulatory funding are not ordinary enterprise debt or surplus cash.
- AON and AJG must explicitly address acquisition/reinvestment intensity before Pass, applying the
  Batch 34 BRO learning rather than an acquisition-blind cash shortcut.
- WMB requires a resource-cycle operating model with debt, NCI, capex, midstream cash conversion,
  and any project/commodity dependencies bridged once.
- Every preferred claim must be period-specific. Any post-quarter issuance/redemption must add both
  proceeds and claims at the correct cutoff date.
- Public model identity must match the actual formula. Repricing must recompute reliability, ROE,
  traces, and baseline metadata. Pass evidence must be runtime-bound to source receipts and bytes.

## Gate

Proceed through the Batch 35 initial pass and stop after presenting Pass / Conditional / Withheld
for confirmation. Do not start recovery, Batch 36, tracked serving promotion, merge, push, or
deployment.
