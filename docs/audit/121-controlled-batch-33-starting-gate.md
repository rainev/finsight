# Controlled Universe Reset Batch 33 Starting Gate

Date: 2026-09-03
Status: **firsthand audited; implementation authorized and in progress**

## Exact denominator

The user explicitly authorized `Start Universe Reset Batch 33`. The denominator authority is
`backend/app/us_valuation/config/reset_batches_2026_08_14/batch_33.json`, SHA-256
`cb67922607c31bc19c21b31f0b59c5351680a455d4cac95c50de287eb02ffcfd`. It contains exactly ten
unique issuers in this order:

AXP, AFL, AIG, WRB, CINF, FITB, MTB, BEN, HBAN, MRSH.

There are eight Financials core issuers and two rare-subindustry boundary issuers: AXP (consumer
finance) and AIG (multi-line insurance). All ten are frozen in the financial-equity family at
valuation date 2026-08-14. The partition root remains
`fd49977122da8bdbaad1d336efeb5bf8480a21a3c63d03b57c0b961cb65908a4`.

## Predecessor and protected state

- Batch 32 is user-confirmed in Audit 120.
- Confirmed cumulative state through Batch 32: 320 issuers, 114 Pass / 196 Conditional / 10
  Withheld; 310 numeric.
- Recovery Learning Watchlist: 206 entries — 196 Conditional / 10 Withheld.
- Append-only automatic-withheld history: 20 entries.
- Tracked active serving catalog remains Batch 01–10 only.
- Protected tree hashes:
  - backend catalog root: `ea5e778fb6e4da2ea47bacf90cb813eca24654d1fe8fd62dec9cc3cb102bfe62`
  - frontend public data: `5157530c9c4baf3e9d5e6b0455a54579c94a5ead79c07145d9f4d35aef0e7017`
  - generated frontend research: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

## Reuse check

No validated Batch 33 packet/package set is present in the controlled output cache. Capture all ten
cutoff-safe SEC packets and controlling filing packages into new untracked output roots. The dirty
tracked/untracked worktree remains the preservation baseline and must not be reset or stashed.

## Gap register

- **P0 Contract:** bind the exact order, identities, roles, financial-equity family, and manifest hash.
- **P0 Sources:** capture all ten SEC packets/packages and scan later cutoff-safe 8-K events.
- **P0 Equity facts:** reconcile common equity, preferred equity, NCI, diluted shares, dividends,
  and parent/common earnings without EV debt bridges.
- **P0 Economics:** distinguish consumer finance, life/P&C/multi-line insurance, regional banks,
  asset management, and insurance brokerage; do not treat deposits, policy reserves, or client
  assets as ordinary corporate debt/cash.
- **P0 Capital:** incorporate regulatory-capital and insurance-capital evidence when available;
  otherwise use transparent bounded Low ranges.
- **P0 Verification:** challenge the exact candidate, replay twice, run full suites/build, and
  exercise the isolated 330-company API.
- **P1 Bookkeeping:** preserve watchlist/withheld data until confirmation and any separately
  authorized recovery.

## Gate

Proceed through the Batch 33 initial pass and stop after presenting Pass / Conditional / Withheld
for confirmation. Do not start recovery, Batch 34, serving promotion, merge, push, or deployment.
