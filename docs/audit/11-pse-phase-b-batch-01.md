# Audit 11 — PSE V2 Phase B Batch 1

**Implementation status:** Batch results were implemented, live verified, and user-confirmed on 2026-09-22. The user
separately authorized local activation; the cumulative 18-company catalog is now active locally and live verified.
Local activation was user-confirmed on 2026-09-22. The previous eight-company catalog remains preserved for rollback.

## Frozen scope

- Banks: `BPI, MBT, SECB, CBC, EW`
- REITs: `RCR, MREIT, CREIT, FILRT, DDMPR`
- No issuer was added, removed, substituted, recovered, activated, pushed, or deployed.

## Model routes

- Banks use the existing residual-income engine with one shared, versioned scenario policy.
- REITs use the existing sustainable-distributions engine with shared stable-growth or recovery-income policies.
- NAV and market multiples remain separate checks; neither is silently blended into intrinsic value.
- All ten results are provisional and Low reliability pending a real filing refresh and deeper regulatory/NAV challenge.

## Batch 1 values per share

| Ticker | Model | Bear | Base | Bull | Status |
|---|---|---:|---:|---:|---|
| BPI | Residual income | 70.16205523563028 | 98.43829776101308 | 134.84108831292946 | Provisional intrinsic · Low |
| MBT | Residual income | 57.435760517614284 | 78.86001130928499 | 106.13405613916176 | Provisional intrinsic · Low |
| SECB | Residual income | 96.67900231915135 | 128.63627934493672 | 168.42878225191245 | Provisional intrinsic · Low |
| CBC | Residual income | 56.03571554890494 | 82.56741775285494 | 113.178652983914 | Provisional intrinsic · Low |
| EW | Residual income | 21.225182139891476 | 29.020471302913112 | 38.90783842628291 | Provisional intrinsic · Low |
| RCR | Sustainable distributions | 3.413087907610259 | 5.146705882352937 | 7.245650674738483 | Provisional intrinsic · Low |
| MREIT | Sustainable distributions | 8.012215866189337 | 12.08187999999999 | 17.009147982260032 | Provisional intrinsic · Low |
| CREIT | Sustainable distributions | 1.623375926065798 | 2.447941176470587 | 3.4462677764102914 | Provisional intrinsic · Low |
| FILRT | Sustainable distributions | 1.5896455998936205 | 2.4824806305258953 | 3.4525776016411047 | Provisional intrinsic · Low |
| DDMPR | Sustainable distributions | 0.6267623010269364 | 0.978787518643988 | 1.361275420271948 | Provisional intrinsic · Low |

## Evidence and verification

- Source readiness: official FY2025 annual and 2Q2026 interim paths were identified for all ten issuers.
- Rights boundary: the candidate stores deterministic reviewed fact receipts and official source links, not unrestricted
  copies of remote filings. Full redistribution/commercial-use clearance remains unresolved.
- Real persistence: 10 securities, 10 reviewed receipts, 40 reported facts, 150 versioned assumptions, and 10 valuation
  runs in Postgres; all 10 receipt objects were verified in MinIO. A replay left the counts unchanged.
- Candidate twins: independently generated candidates were byte-identical. Candidate manifest SHA-256:
  `74bff339ea0f5e1925cf598640f1b83ce85790f541d8da55f5fb66b5b59c85a5`.
- Pre-activation preservation check: the active pointer SHA-256 remained
  `03d7356003ccc46c6f0221d9b1dc1a279a41113b7c88953bbe3032732e401ff1`; active manifest SHA-256 remained
  `4223479fea8b1ef471a87a77249d249d440d89fb65beea55f1e34aa7c55f364f`.
- Real staged API: 18/18 detail responses exactly matched stored artifacts; all 10 Batch 1 calculator defaults reproduced
  the catalog; unauthenticated list access returned 401; a BPI scenario persisted as saved scenario `#4`.
- Real staged UI: PH search routed to BPI and MREIT; BPI rendered `PHP98.44` base and changed to `PHP88.37` when cost
  of equity changed from 12.052% to 13%; MREIT rendered `PHP12.08` base and changed to `PHP10.81` at 12% cost of equity.
- Automated verification: 38 focused PSE tests and 308 full backend tests passed. The frontend production build passed
  with the existing chunk-size warning.

## Gate

**Verified and user-confirmed on 2026-09-22.** Confirmation accepts this staged Batch 1 result and bookkeeping only. It
did not authorize deployment, push, recovery, or Batch 2. Local activation was separately authorized afterward.

## Local activation

- Active catalog: `PSE-V2-PHASE-B-B01-2026-09-22-1.0`, exactly 18 issuers.
- Active pointer SHA-256: `004072021832c8697bc40bffb75169c0737b589bcde222eacea3b74c1b59fae8`.
- Rollback catalog: `PSE-V2-PILOT-2026-09-21-1.1`, preserved unchanged.
- Real active API: 18/18 detail parity, 10/10 calculator parity, authentication boundary 401, and saved BPI scenario
  `#5` persisted.
- Real active browser: BPI rendered PHP98.44 and responded PHP88.37 at 13% cost of equity; search returned MREIT,
  which rendered PHP12.08 and responded PHP10.81 at 12% cost of equity.
- Regression: 309 backend tests pass; frontend production build passes with the existing chunk-size warning.

**Activation status:** ✔ locally active, live verified, and user-confirmed on 2026-09-22. No deployment, push, recovery,
or Batch 2 work has occurred.
