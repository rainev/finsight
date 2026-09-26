# Audit 14 — PSE V2 Phase B Batch 4

**Status:** implemented, live verified, and user-confirmed as a staged candidate on 2026-09-22. The user separately
authorized local activation; the cumulative 48-company catalog was activated, live verified, and user-confirmed on
2026-09-23. The 38-company Batch 3 catalog is preserved for rollback.

## Reference

- Confirmed set: `MER, FGEN, ACEN, MWC, SPC, CREC, ALTER, ASLAG, SPNEC, MYNLD`.
- Governing plan: `docs/plans/PSE-SECTOR-VALUATION-PIPELINE-V2.md`.
- Sector method: utility/project FCFF or SOTP where fully source-bounded; sustainable distributions may be used for a
  reviewed payout stream; comparables remain separately labeled market-relative results.
- Finite concessions and franchises must not receive value beyond documented expiry.

## Ours before Batch 4

- The active catalog is the confirmed 38-company Batch 3 catalog.
- The FCFF engine supports finite lives, but the shared calculator does not reproduce finite-life FCFF inputs.
- The distribution engine and calculator assume a perpetual terminal value.
- Existing Batch 3 patterns already provide immutable receipts, cumulative catalog staging outside the serving root,
  persistence, API parity, and calculator verification.

## Reuse check

- Reuse the existing FCFF, SOTP, sustainable-distribution, comparables, contract, catalog, persistence, API, and UI
  layers.
- Add no new engine, service, scheduler, or Batch-specific UI.

## Gaps

| ID | Gap | Severity | Evidence |
|---|---|---|---|
| B04-01 | Finite-life distribution cases cannot end at a documented franchise/concession expiry without a perpetuity. | P0 | ✔ `models/distributions.py` always calculates terminal value. |
| B04-02 | The calculator cannot reproduce a finite-life distribution artifact. | P0 | ✔ `calculator.py` always requires terminal growth for distribution cases. |
| B04-03 | The frozen ten have no reviewed Batch 4 config, source receipts, route classifications, or artifacts. | P0 | ✔ No Batch 4 module/config exists. |
| B04-04 | No cumulative 48-company staged builder pins and preserves the confirmed 38-company parent. | P0 | ✔ Latest builder targets Batch 3 and 38 issuers. |
| B04-05 | No Batch 4 persistence, API parity, deterministic-twin, or live UI evidence exists. | P0 | ✔ No Batch 4 verification scripts/tests exist. |
| B04-06 | Foreign-currency source facts must retain original currency and a dated normalization basis. | P1 | ✔ FGEN reports FY2025 in USD while the public artifact contract is PHP. |

All findings are firsthand against the current workspace. The build closes only this frozen batch and stops before
activation.

## Resolution

- B04-01/B04-02: closed. Sustainable distributions now support a reviewed finite horizon with zero terminal value;
  finite-life calculator views omit terminal growth and replay the same engine.
- B04-03: closed. The exact confirmed ten have reviewed config, routes, source receipts, and artifacts.
- B04-04: closed. The cumulative candidate copies the hash-pinned 38-company parent byte-for-byte and adds exactly ten.
- B04-05: closed with deterministic, persistence, API, calculator, UI, full-test, and production-build evidence below.
- B04-06: closed for this batch. FGEN's public screening fact uses the issuer's official PSE filing translated to PHP;
  no agent-generated FX conversion is used.

## Batch 4 values per share

| Ticker | Output | Bear/Low | Base | Bull/High | Status |
|---|---|---:|---:|---:|---|
| MER | Finite-life distributions | 200.61637189455172 | 298.3566172850372 | 441.9236919232287 | Provisional intrinsic · Low |
| FGEN | P/B fallback | 15.678 | 23.517 | 31.356 | Provisional market-relative · Low |
| ACEN | P/B fallback | 2.552 | 3.509 | 4.466 | Provisional market-relative · Low |
| MWC | Finite-life distributions | 12.083097841919663 | 17.025269694732497 | 23.44202931005598 | Provisional intrinsic · Low |
| SPC | Continuing distributions | 7.923421795810739 | 10.907882969149753 | 16.05410204439587 | Provisional intrinsic · Low |
| CREC | P/B fallback | 1.736 | 2.387 | 3.038 | Provisional market-relative · Low |
| ALTER | P/B fallback | 0.46 | 0.6900000000000001 | 0.92 | Provisional market-relative · Low |
| ASLAG | P/B fallback | 1.54 | 1.9800000000000002 | 2.4200000000000004 | Provisional market-relative · Low |
| SPNEC | P/B fallback | 0.97 | 1.455 | 1.94 | Provisional market-relative · Low |
| MYNLD | Finite-life distributions | 6.347356681557339 | 8.024114199072182 | 9.824019273537669 | Provisional intrinsic · Low |

## Evidence and verification

- Batch output: `4 provisional intrinsic / 6 market-relative / 0 unavailable`; all ten are Low reliability.
- MER ends at the sourced 2053 franchise expiry, MWC at January 2047, and MYNLD at the currently effective July 2037
  concession expiry. All three carry zero terminal value.
- Real persistence: 10 securities, 16 reviewed receipts, 28 reported facts, 45 versioned assumptions, and 10 valuation
  runs in Postgres; all 16 receipt objects were verified in MinIO.
- Candidate twins are byte-identical. Cumulative manifest SHA-256:
  `29673524d381211947d1518cc31720320fcbbe60d0a88f5b005040808f248588`.
- Cumulative candidate: 48 artifacts — 26 intrinsic, 22 market-relative, 0 unavailable; all 48 provisional.
- Real staged API: 48/48 details matched stored artifacts; all 10 Batch 4 calculator defaults reproduced the catalog;
  unauthenticated list access returned 401; edited MWC scenario `#10` persisted.
- Real staged UI: MWC rendered `PHP17.03` and changed to `PHP18.42` when distribution growth changed from 2.5% to 3.5%;
  ACEN rendered `PHP3.51` and changed to `PHP3.83` when P/B changed from 1.1x to 1.2x; footer reported 48 companies.
- Verification: 339 backend tests passed; the frontend production build passed with the existing chunk-size warning.
- Active preservation: active pointer SHA-256 remains
  `2c39244d615d31432e6996714a768192475e9b95949079593ba18060c083bf7b`; active Batch 3 manifest SHA-256 remains
  `fb420ec53ea1878743e3c3debd9082ecd57de867837a2080b2820d94259cc35a`.

## Gate

**Verified and user-confirmed on 2026-09-22.** Confirmation accepts the staged Batch 4 result and bookkeeping only. It
did not authorize deployment, push, recovery, Batch 5, or Phase C. Local activation was separately authorized.

## Local activation

- Active catalog: `PSE-V2-PHASE-B-B04-2026-09-22-1.0`, exactly 48 issuers.
- Active pointer SHA-256: `8deab067ac2cdb80a618f1c389ba397c472d76855c2340820d6551ebf6ee5d88`.
- Active manifest SHA-256: `29673524d381211947d1518cc31720320fcbbe60d0a88f5b005040808f248588`.
- Rollback catalog: `PSE-V2-PHASE-B-B03-2026-09-22-1.0`, preserved with manifest SHA-256
  `fb420ec53ea1878743e3c3debd9082ecd57de867837a2080b2820d94259cc35a`.
- Real active API: 48/48 detail parity, 10/10 Batch 4 calculator parity, authentication boundary 401, and saved MWC
  scenario `#11` persisted.
- Real active browser: MWC rendered `PHP17.03` and changed to `PHP18.42` at 3.5% distribution growth; ACEN rendered
  `PHP3.51` and changed to `PHP3.83` at 1.2x P/B; the footer reported exactly 48 companies.
- Post-activation regression: 340 backend tests pass; frontend production build passes with the existing chunk-size
  warning.

**Activation status:** ✔ locally active, live verified, and user-confirmed on 2026-09-23. No deployment, push,
recovery, Batch 5, or Phase C work occurred.
