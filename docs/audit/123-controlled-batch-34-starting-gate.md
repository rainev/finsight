# Controlled Universe Reset Batch 34 Starting Gate

Date: 2026-09-03
Status: **firsthand audited; implementation in progress**

## Exact denominator

The user explicitly authorized `Start Universe Reset batch 34`. The denominator authority is
`backend/app/us_valuation/config/reset_batches_2026_08_14/batch_34.json`, SHA-256
`2a2c23e5a9b2112e49ec7c9d1882bceca46374c03bfb4319ae775e0a9bb18fe8`. It contains exactly ten
unique issuers in this order:

USB, L, SPGI, NTRS, BRO, PGR, TRV, KEY, TFC, STT.

There are eight Financials core issuers and two boundary issuers: USB (diversified banks) and L
(multi-line insurance). All ten are frozen in the financial-equity family at valuation date
2026-08-14.

## Predecessor and protected state

- Batch 33 is user-confirmed in Audit 122.
- Confirmed cumulative state through Batch 33: 330 issuers, 115 Pass / 205 Conditional / 10
  Withheld; 320 numeric.
- Recovery Learning Watchlist: 215 entries — 205 Conditional / 10 Withheld.
- Append-only automatic-withheld history: 20 entries.
- Tracked active serving catalog remains Batch 01–10 only.
- Protected hashes at the start of this batch: backend catalog
  `38efe664dc981e9d2383ece43b66e9ae326b4b9a7cc2443f2463498432ef66a8`, frontend public data
  `353a14bc672002e88d248811f98d23d4c1fb47cf28e526d969f463f256260274`, generated research
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Batch-specific gates

- Use equity-level residual-income or economically suitable financial models. Deposits, policy
  reserves, reinsurance, and client assets are not ordinary corporate debt or excess cash.
- Capture current common equity, preferred claims/dividends, NCI, shares, and five exact annual
  earnings periods. Exact accession/report dates and fact periods control; wrapper-level period
  labels remain diagnostic only.
- Check cutoff-safe preferred/debt events for USB, KEY, NTRS, TFC, TRV, and STT. Preserve event
  claims separately and never count financing twice.
- Cap material regulatory, reserve, integration, capital, and cycle uncertainty at Low. Withhold
  only for genuinely unbounded uncertainty, nonpositive base value, contradictory identity, or an
  unsupported model.

## Gate

Proceed through the Batch 34 initial pass and stop after presenting Pass / Conditional / Withheld
for confirmation. Do not start recovery, Batch 35, serving promotion, merge, push, or deployment.
