# Audit 15 — PSE V2 Phase B Batch 5

**Status:** implemented, live verified, and user-confirmed as a staged candidate on 2026-09-23. The user separately
authorized local activation; the cumulative 58-company catalog is now active locally, live verified, and
user-confirmed. The 48-company Batch 4 catalog is preserved for rollback.

## Reference

- Confirmed set: `PNB, RCB, UBP, AUB, PBB, PSB, COL, PSE, NRCP, MFIN`.
- Banks and balance-sheet financials use residual income/P/B economics; fee-based financial platforms may use
  residual income or distributions where source-supported.
- Comparables remain separately labeled market-relative outputs.

## Ours before Batch 5

- The active catalog is the confirmed 48-company Batch 4 catalog.
- The residual-income engine, calculator, receipt, persistence, API, and UI paths already work for five Batch 1 banks.
- No Batch 5 config, reviewed artifacts, cumulative 58-company builder, or live verification evidence exists.

## Reuse check

- Reuse the existing residual-income and market-relative engines and the Batch 1 bank policy pattern.
- Add no new model, service, scheduler, or Batch-specific UI.

## Gaps

| ID | Gap | Severity | Evidence |
|---|---|---|---|
| B05-01 | The exact frozen ten have no reviewed FY2025 fact config or route classification. | P0 | ✔ No Batch 5 module/config exists. |
| B05-02 | Fee-based and insurance/lending names require a separate versioned residual-income policy rather than ticker code. | P1 | ✔ Batch 1 contains only a shared bank policy. |
| B05-03 | MFIN's FY2025 profit conflicts with a material 2026 first-half loss, so FY2025 intrinsic normalization is not decision-safe. | P1 | ✔ PSE FY2025 and 1H2026 reports disagree directionally. |
| B05-04 | No cumulative 58-company candidate pins and preserves the confirmed active 48-company parent. | P0 | ✔ Latest builder targets Batch 4. |
| B05-05 | No Batch 5 persistence, deterministic, API, calculator, or live UI evidence exists. | P0 | ✔ No Batch 5 scripts/tests exist. |

All findings are firsthand against the current workspace and official PSE financial summaries. The build closes only
this frozen batch and stops before activation.

## Resolution

- B05-01/B05-02: closed with one config-driven residual-income route using shared bank and other-financial policies.
- B05-03: closed by retaining MFIN as market-relative-only with the 2026 first-half loss exposed.
- B05-04/B05-05: closed with the cumulative builder and live verification evidence below.

## Batch 5 values per share

| Ticker | Output | Bear/Low | Base | Bull/High | Status |
|---|---|---:|---:|---:|---|
| PNB | Residual income | 83.55680919032517 | 113.31431277036152 | 150.77187807429993 | Provisional intrinsic · Low |
| RCB | Residual income | 28.871354936801264 | 38.399769751853746 | 50.310540755551 | Provisional intrinsic · Low |
| UBP | Residual income | 27.07968544733096 | 35.9930399661488 | 47.213057829695884 | Provisional intrinsic · Low |
| AUB | Residual income | 40.11543948927631 | 59.09562494355668 | 80.86950239234363 | Provisional intrinsic · Low |
| PBB | Residual income | 12.235716438571206 | 16.289360191746706 | 21.310293741210664 | Provisional intrinsic · Low |
| PSB | Residual income | 50.92987411861971 | 67.76197512861248 | 88.72933293404036 | Provisional intrinsic · Low |
| COL | Residual income | 0.30699023381987184 | 0.4753124046455236 | 0.7055261955048878 | Provisional intrinsic · Low |
| PSE | P/E fallback | 141.10 | 169.32 | 197.54 | Provisional market-relative · Low |
| NRCP | Residual income | 1.814508339488318 | 2.5989260514658543 | 3.6361875869534224 | Provisional intrinsic · Low |
| MFIN | P/B fallback | 1.296 | 1.7280000000000002 | 2.16 | Provisional market-relative · Low |

## Evidence and verification

- Batch output: `8 provisional intrinsic / 2 market-relative / 0 unavailable`; all ten are Low reliability.
- Real persistence: 10 securities, 10 reviewed receipts, 46 reported facts, 174 versioned assumptions, and 10
  valuation runs in Postgres; all 10 receipt objects were verified in MinIO.
- Candidate twins are byte-identical. Cumulative manifest SHA-256:
  `b6dc2ae35ad13e0ee2f40c11e0b7190441da651acf914e90fea3334302ece95b`.
- Cumulative candidate: 58 artifacts — 42 intrinsic, 26 market-relative, 0 unavailable; all 58 provisional.
- Real staged API: 58/58 details matched stored artifacts; all 10 Batch 5 calculator defaults reproduced the catalog;
  unauthenticated list access returned 401; edited PNB scenario `#12` persisted.
- Real staged UI: PNB rendered `PHP113.31` and changed to `PHP129.27` when cost of equity changed to 11%; PSE rendered
  `PHP169.32` and changed to `PHP183.43` when P/E changed from 12x to 13x; footer reported 58 companies.
- Verification: 348 backend tests passed; frontend production build passed with the existing chunk-size warning.
- Active preservation: active pointer SHA-256 remains
  `8deab067ac2cdb80a618f1c389ba397c472d76855c2340820d6551ebf6ee5d88`; active Batch 4 manifest SHA-256 remains
  `29673524d381211947d1518cc31720320fcbbe60d0a88f5b005040808f248588`.

## Gate

**Verified and user-confirmed on 2026-09-23.** Confirmation accepts the staged Batch 5 result and bookkeeping only. It
did not authorize deployment, push, recovery, Batch 6, or Phase C. Local activation was separately authorized.

## Local activation

- Active catalog: `PSE-V2-PHASE-B-B05-2026-09-23-1.0`, exactly 58 issuers.
- Active pointer SHA-256: `ff29ce15140054d26b4a6e8db57af9152dd74cdabbb0dbe4240434151f3e791b`.
- Active manifest SHA-256: `b6dc2ae35ad13e0ee2f40c11e0b7190441da651acf914e90fea3334302ece95b`.
- Rollback catalog: `PSE-V2-PHASE-B-B04-2026-09-22-1.0`, preserved with manifest SHA-256
  `29673524d381211947d1518cc31720320fcbbe60d0a88f5b005040808f248588`.
- Real active API: 58/58 detail parity, 10/10 Batch 5 calculator parity, unauthenticated access 401, and saved PNB
  scenario `#13` persisted.
- Real active browser: PNB rendered `PHP113.31` and PSE rendered `PHP169.32→PHP183.43` at 13x P/E; footer reported 58
  companies.
- Post-activation regression: 349 backend tests pass; frontend production build passes with the existing chunk-size
  warning.

**Activation status:** ✔ locally active, live verified, and user-confirmed on 2026-09-23. No deployment, push,
recovery, Batch 6, or Phase C work occurred.
