# Controlled Universe Reset Batch 28 Starting Gate

Date: 2026-08-31  
Status: **firsthand audited; implementation authorized and in progress**

## Exact denominator

The user explicitly authorized `Start Universe Reset Batch 28`. The denominator authority is
`backend/app/us_valuation/config/reset_batches_2026_08_14/batch_28.json`, SHA-256
`6d12a7011210d098790f3c0756dbe5fccd042e4cda32a26d5d97236738190350`. It contains exactly ten
unique issuers in this order:

QCOM, CDNS, FICO, MCHP, GEN, PTC, CSCO, TYL, ZBRA, JBL.

There are eight Information Technology core issuers and two boundary issuers: ZBRA (electronic
equipment/instruments) and JBL (electronic manufacturing services). All ten are frozen in the
operating-FCFF family at valuation date 2026-08-14. The partition root remains
`fd49977122da8bdbaad1d336efeb5bf8480a21a3c63d03b57c0b961cb65908a4`.

## Predecessor and protected state

- Batch 27 is user-confirmed in Audit 109 at Pass 6 / Conditional 4 / Withheld 0.
- Confirmed cumulative state through Batch 27: 270 issuers, 104 Pass / 157 Conditional / 9
  Withheld; 261 numeric.
- Recovery Learning Watchlist: 166 entries — 157 Conditional / 9 Withheld.
- Append-only automatic-withheld history: 19 entries.
- Tracked active serving catalog remains Batch 01–10 only.
- Protected tree hashes under `run_batch_07_history._tree`:
  - backend catalog root: `ea5e778fb6e4da2ea47bacf90cb813eca24654d1fe8fd62dec9cc3cb102bfe62`
  - frontend public data: `5157530c9c4baf3e9d5e6b0455a54579c94a5ead79c07145d9f4d35aef0e7017`
  - generated frontend research: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

## Reuse check

Validated difficult-106 packet/package/parsed evidence exists for CDNS, MCHP, CSCO, and JBL.
QCOM, FICO, GEN, PTC, TYL, and ZBRA need new cutoff-safe packets and controlling packages. Reuse
the Batch 27 capture pipeline.

## Gap register

- **P0 ✔ Contract:** no typed Batch 28 module or exact-order/hash test exists.
- **P0 ✔ Sources:** six SEC packets/packages are missing; four cached issuers need identity-checked
  rewrapping.
- **P0 ✔ Histories:** no Batch 28 annual/TTM history, bridge, shares, or event ledger exists.
- **P0 ✔ Economic routes:** semiconductor/licensing economics, SaaS/SBC, leverage/negative equity,
  post-acquisition integration, cybersecurity/software mix, and EMS/device working capital must be
  source-bounded and reflected in arithmetic.
- **P0 ✔ Classification:** ordinary market/cycle uncertainty stays inside scenarios; only named
  material dependencies may force Conditional or Withheld.
- **P0 ✔ Verification:** no exact candidate, challenge, deterministic replay, full suite, 280-company
  catalog, or real API evidence exists.
- **P1 ✔ Bookkeeping:** watchlist and withheld registers must remain unchanged before confirmation
  and any separate recovery authorization.

## Gate

Proceed through the Batch 28 initial pass and stop after presenting Pass / Conditional / Withheld
for confirmation. Generated evidence remains untracked. Do not start recovery, Batch 29, serving
promotion, merge, push, or deployment.

