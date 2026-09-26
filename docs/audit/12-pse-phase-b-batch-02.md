# Audit 12 — PSE V2 Phase B Batch 2

**Implementation status:** Batch 2 results were implemented, live verified, and user-confirmed on 2026-09-22. The user
separately authorized local activation; the cumulative 28-company catalog is now active locally and live verified.
Local activation was user-confirmed on 2026-09-22. The previous 18-company Batch 1 catalog remains preserved for rollback.

## Frozen scope

- Consumer and operating companies: `URC, CNPF, MONDE, JFC, DNL`
- Retail companies: `PGOLD, RRHI, WLCON, SEVN, SSI`
- No issuer was added, removed, substituted, activated, pushed, or deployed.

## Routes and source boundary

- `URC, CNPF, MONDE, JFC, PGOLD, RRHI, WLCON, SEVN` use the existing FCFF engine with issuer-bound cash, debt,
  lease, claim, and share bridges.
- `DNL` and `SSI` remain `market_relative_only` because their current source packages do not support stable,
  reconciled FCFF and lease-adjusted capital bridges.
- Intrinsic inputs use a three-year median of reported operating cash flow less reported capital expenditures.
- All ten results are provisional and Low reliability; policy bands are not represented as empirical peer studies.
- Candidate evidence contains deterministic reviewed fact receipts and official links, not unrestricted remote filing
  copies. Full redistribution/commercial-use clearance remains unresolved.

## Batch 2 values per share

| Ticker | Output | Bear/Low | Base | Bull/High | Status |
|---|---|---:|---:|---:|---|
| URC | FCFF | 11.263629431374948 | 21.556249836915885 | 40.80625504271362 | Provisional intrinsic · Low |
| CNPF | FCFF | 11.340301965607832 | 18.54319014508341 | 32.014554043536336 | Provisional intrinsic · Low |
| MONDE | FCFF | 4.398554862122852 | 6.454718620301496 | 10.300305214324085 | Provisional intrinsic · Low |
| JFC | FCFF | 68.92564111693721 | 157.42876710686852 | 322.95373246150155 | Provisional intrinsic · Low |
| DNL | P/E fallback | 2.88 | 3.5999999999999996 | 4.32 | Provisional market-relative · Low |
| PGOLD | FCFF | 19.15065088924349 | 33.51729421683522 | 60.24565100521666 | Provisional intrinsic · Low |
| RRHI | FCFF | 12.716058412981202 | 42.24903793403655 | 97.19353649666994 | Provisional intrinsic · Low |
| WLCON | FCFF | 4.752872410833716 | 7.808708650465419 | 13.493925401331442 | Provisional intrinsic · Low |
| SEVN | FCFF | 36.052491412463084 | 54.12015904970705 | 87.73406982416627 | Provisional intrinsic · Low |
| SSI | P/E fallback | 2.4000000000000004 | 3.2 | 4.0 | Provisional market-relative · Low |

## Evidence and verification

- Real persistence: 10 securities, 10 reviewed receipts, 79 reported facts, 134 versioned assumptions, and 10
  valuation runs in Postgres; all 10 receipt objects were verified in MinIO. Replay left counts unchanged.
- Candidate twins are byte-identical. Manifest SHA-256:
  `f1a1405a3a9d8c8bdc8b620b1a1c9a34dc4a38320d3ef403c8c99c9f3d418741`.
- Pre-activation preservation check: active pointer SHA-256 remained
  `004072021832c8697bc40bffb75169c0737b589bcde222eacea3b74c1b59fae8`; active 18-company manifest SHA-256 remains
  `74bff339ea0f5e1925cf598640f1b83ce85790f541d8da55f5fb66b5b59c85a5`.
- Real staged API: 28/28 details matched stored artifacts; all 10 Batch 2 calculator defaults reproduced the catalog;
  unauthenticated list access returned 401; edited URC scenario `#6` persisted.
- Real staged UI: search opened URC and DNL; URC rendered PHP21.56 and changed to PHP25.11 when growth changed from
  4% to 5%; DNL rendered PHP3.60 and changed to PHP3.96 when the multiple changed from 10x to 11x.
- Calculator repair: non-AP FCFF issuers now use their own artifact-bound capital bridges instead of AP's seed facts.
- Verification: 26 focused model/calculator tests and 318 full backend tests passed. The frontend production build
  passed with the existing chunk-size warning.

## Gate

**Verified and user-confirmed on 2026-09-22.** Confirmation accepts this staged Batch 2 result and bookkeeping only. It
did not authorize deployment, push, recovery, Batch 3, or Phase C. Local activation was separately authorized afterward.

## Local activation

- Active catalog: `PSE-V2-PHASE-B-B02-2026-09-22-1.0`, exactly 28 issuers.
- Active pointer SHA-256: `c9821d8980125f61597d9662ff83f0b7c7e878420ec73beed62792467a7389d6`.
- Rollback catalog: `PSE-V2-PHASE-B-B01-2026-09-22-1.0`, preserved unchanged.
- Real active API: 28/28 detail parity, 10/10 calculator parity, authentication boundary 401, and saved URC scenario
  `#7` persisted.
- Real active browser: URC rendered PHP21.56 and responded PHP25.11 at 5% growth; search opened DNL with the correct
  market-relative label and PHP3.60 base.
- Regression: 319 backend tests pass; frontend production build passes with the existing chunk-size warning.

**Activation status:** ✔ locally active, live verified, and user-confirmed on 2026-09-22. No deployment, push, recovery,
Batch 3, or Phase C work has occurred.
