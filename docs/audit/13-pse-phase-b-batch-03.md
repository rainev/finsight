# Audit 13 — PSE V2 Phase B Batch 3

**Implementation status:** Batch 3 was implemented, live verified, and user-confirmed as a staged candidate on
2026-09-22. The user separately authorized local activation; the cumulative 38-company catalog is now active locally,
live verified, and user-confirmed. The 28-company Batch 2 catalog is preserved for rollback.

## Frozen scope

`SM, AEV, JGS, GTCAP, DMC, SMPH, RLC, MEG, FLI, CLI`

No issuer was added, removed, substituted, activated, pushed, deployed, or carried into another batch.

## Routes and source boundary

- `SMPH, RLC, FLI` use provisional property RNAV through the existing SOTP/NAV engine. The bridge starts with reported
  parent equity and adds a scenario-adjusted, after-tax investment-property fair-value uplift.
- `SM, AEV, JGS, GTCAP, DMC, MEG, CLI` use transparent P/B-to-reported-NAV fallbacks while complete component SOTP or
  property RNAV bridges remain unresolved.
- All ten remain provisional and Low reliability. Market-relative outputs keep intrinsic scenarios null and retain
  explicit intrinsic blockers.
- Candidate evidence contains deterministic reviewed fact receipts and official source links, not redistributed
  filing payloads.

## Batch 3 values per share

| Ticker | Output | Bear/Low | Base | Bull/High | Status |
|---|---|---:|---:|---:|---|
| SM | P/B fallback | 515.07 | 629.53 | 743.99 | Provisional market-relative · Low |
| AEV | P/B fallback | 23.5395 | 31.386 | 39.2325 | Provisional market-relative · Low |
| JGS | P/B fallback | 16.7895 | 22.386 | 27.9825 | Provisional market-relative · Low |
| GTCAP | P/B fallback | 609.4305 | 812.574 | 1015.7175 | Provisional market-relative · Low |
| DMC | P/B fallback | 9.07 | 11.3375 | 13.605 | Provisional market-relative · Low |
| SMPH | Property RNAV | 30.51643446938899 | 41.68760898486752 | 54.13548915925787 | Provisional intrinsic · Low |
| RLC | Property RNAV | 50.753333811152906 | 61.81569315623288 | 74.14232214075057 | Provisional intrinsic · Low |
| MEG | P/B fallback | 2.469 | 3.7035000000000005 | 4.938 | Provisional market-relative · Low |
| FLI | Property RNAV | 5.4664039229961165 | 6.527948871181909 | 7.710813242017505 | Provisional intrinsic · Low |
| CLI | P/B fallback | 2.092 | 2.8765000000000005 | 3.661 | Provisional market-relative · Low |

## Evidence and verification

- Real persistence: 10 securities, 10 reviewed receipts, 32 reported facts, 39 versioned assumptions, and 10 valuation
  runs in Postgres; all 10 receipt objects were verified in MinIO.
- Candidate twins are byte-identical. Cumulative manifest SHA-256:
  `fb420ec53ea1878743e3c3debd9082ecd57de867837a2080b2820d94259cc35a`.
- Cumulative candidate: 38 artifacts — 22 intrinsic, 16 market-relative, 0 unavailable; all 38 provisional.
- Real staged API: 38/38 details matched stored artifacts; all 10 Batch 3 calculator defaults reproduced the catalog;
  unauthenticated list access returned 401; edited SM scenario `#8` persisted.
- Real staged UI: RLC rendered `PHP61.82` and changed to `PHP66.87` when uplift realization changed from 50% to 60%;
  AEV rendered `PHP31.39` and changed to `PHP36.62` when P/B changed from 0.6x to 0.7x.
- Calculator repair: P/B screens now permit legitimate multiples below 1.0 while prior P/E bounds remain unchanged.
- Catalog safeguard: list metadata must now match each artifact's model, availability, and publication state.
- Verification: 328 backend tests passed; the frontend production build passed with the existing chunk-size warning.
- Active preservation: active pointer SHA-256 remains
  `c9821d8980125f61597d9662ff83f0b7c7e878420ec73beed62792467a7389d6`; active Batch 2 manifest SHA-256 remains
  `f1a1405a3a9d8c8bdc8b620b1a1c9a34dc4a38320d3ef403c8c99c9f3d418741`.

## Gate

**Verified and user-confirmed on 2026-09-22.** Confirmation accepts the staged Batch 3 result and bookkeeping only. It
did not authorize deployment, push, recovery, Batch 4, or Phase C. Local activation was separately authorized.

## Local activation

- Active catalog: `PSE-V2-PHASE-B-B03-2026-09-22-1.0`, exactly 38 issuers.
- Active pointer SHA-256: `2c39244d615d31432e6996714a768192475e9b95949079593ba18060c083bf7b`.
- Active manifest SHA-256: `fb420ec53ea1878743e3c3debd9082ecd57de867837a2080b2820d94259cc35a`.
- Rollback catalog: `PSE-V2-PHASE-B-B02-2026-09-22-1.0`, preserved with manifest SHA-256
  `f1a1405a3a9d8c8bdc8b620b1a1c9a34dc4a38320d3ef403c8c99c9f3d418741`.
- Real active API: 38/38 detail parity, 10/10 Batch 3 calculator parity, authentication boundary 401, and saved SM
  scenario `#9` persisted.
- Real active browser: RLC rendered `PHP61.82` and changed to `PHP66.87` at 60% uplift realization; AEV rendered
  `PHP31.39` and changed to `PHP36.62` at 0.7x P/B; the footer reported exactly 38 companies.
- Post-activation regression: 329 backend tests pass; frontend production build passes with the existing chunk-size
  warning.

**Activation status:** ✔ locally active, live verified, and user-confirmed on 2026-09-22. No deployment, push,
recovery, Batch 4, or Phase C work occurred.
