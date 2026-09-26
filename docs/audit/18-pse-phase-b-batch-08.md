# Audit 18 — PSE V2 Phase B Batch 8

**Status:** implemented, staged-results confirmed, locally activated, live-verified, and user-confirmed on 2026-09-23. Batch 7 is preserved for rollback.

## Reference

- Confirmed set: `NIKL, PX, APX, FNI, AT, MARC, OGP, PCOR, PXP, OV`.
- Producing mines target reserve-based NAV/life-of-mine DCF; downstream refining targets normalized FCFF; upstream exploration targets risked reserve/option NAV.
- Where those specialist bridges are incomplete, publish transparent market-relative estimates without relabeling them intrinsic.

## Ours before Batch 8

- Active catalog: confirmed 78-company Batch 7.
- Existing market-relative engine supports P/E and P/B; no new engine or UI is required.

## Gaps

| ID | Gap | Severity | Evidence |
|---|---|---|---|
| B08-01 | No reviewed source config or route exists for the frozen ten. | P0 | ✔ No Batch 8 module/config existed. |
| B08-02 | OGP reports in USD and requires explicit dated PHP normalization. | P0 | ✔ PSE report and BSP 2026-09-22 reference rate. |
| B08-03 | PX and PXP have negative 1H2026 earnings; AT's recent turnaround is too abrupt for a simple earnings multiple. | P0 | ✔ Current PSE financial summaries. |
| B08-04 | Reserve schedules, mine lives, costs, commodity decks, closure claims, and resource probabilities remain incomplete. | P0 | ✔ Specialist route requirements. |
| B08-05 | No cumulative 88-company candidate or live verification evidence exists. | P0 | ✔ Latest builder targets Batch 7. |

The build closes only this frozen batch and stops before activation.

## Batch 8 values per share

| Ticker | Screen | Low | Base | High |
|---|---|---:|---:|---:|
| NIKL | P/E | 3.540 | 4.720 | 5.900 |
| PX | P/B | 4.560 | 5.700 | 6.840 |
| APX | P/E | 10.440 | 13.920 | 17.400 |
| FNI | P/E | 2.400 | 3.200 | 4.000 |
| AT | P/B | 8.838 | 11.784 | 14.730 |
| MARC | P/E | 1.150 | 1.610 | 2.070 |
| OGP | P/E on PHP-normalized TTM EPS | 25.1196 | 31.3995 | 37.6794 |
| PCOR | P/B | 2.208 | 2.944 | 3.680 |
| PXP | P/B | 0.648 | 0.864 | 1.080 |
| OV | P/B | 0.0077503991 | 0.0103338654 | 0.0129173318 |

All ten are provisional market-relative outputs with Low reliability. They are not substitutes for reserve-based NAV, life-of-mine DCF, or normalized downstream FCFF.

## Evidence and verification

- Cumulative candidate: 88 artifacts — 34 intrinsic, 54 market-relative, 0 unavailable; all provisional.
- Persistence: 10 securities, 10 receipts, 10 screening facts, 30 assumptions, 10 runs, and 10 verified MinIO objects.
- Deterministic twins are byte-identical; manifest SHA-256 is `0236bc52a4408f3e175c814ff9140cf82fa198454b84fbbe0044f8cc4c557a78`.
- Every manifest artifact hash and every internal artifact hash verifies.
- Real staged API: 88/88 detail parity, 10/10 calculator parity, unauthenticated 401, and OGP scenario `#18` persisted.
- Real staged UI rendered OGP at PHP31.40 and changed it to PHP34.54 at 11x P/E; PCOR, PXP, and NIKL rendered PHP2.94, PHP0.86, and PHP4.72; footer reported 88 companies.
- Verification: 361 backend tests passed; frontend production build passed with the existing chunk-size warning.
- At the staged-results gate, active Batch 7 remained unchanged: pointer SHA-256 `62caa7cce3ef7987681a7995c17aebec0db998db1f08e96dcd97b31b952cef7b`; manifest SHA-256 `7b3419c52934f9a15d378f8918027697fd9737f2fc449d7f897fa5dcda9f6f91`.
- At the staged-results gate, Batch 8 was absent from the serving root and its activation script remained locked pending results confirmation.

## Gate

**Verified and user-confirmed on 2026-09-23.** This confirmation accepts the staged Batch 8 results only and does not authorize activation, deployment, push, Batch 9, or Phase C.

## Local activation

- Active catalog: `PSE-V2-PHASE-B-B08-2026-09-23-1.0`, exactly 88 issuers.
- Active pointer SHA-256: `cddaa00e782f5236d328985bd798815d010ee1e05ec6302d54c1733cd8a5ad2a`.
- Active manifest SHA-256: `0236bc52a4408f3e175c814ff9140cf82fa198454b84fbbe0044f8cc4c557a78`.
- Batch 7 rollback manifest remains `7b3419c52934f9a15d378f8918027697fd9737f2fc449d7f897fa5dcda9f6f91`.
- Active API: 88/88 detail parity, 10/10 calculator parity, unauthenticated 401, and OGP scenario `#19` persisted.
- Active UI rendered OGP at PHP31.40, changed it to PHP34.54 at 11x P/E, rendered PCOR at PHP2.94, and showed the 88-company footer.
- Persistence remained 10 securities, 10 receipts, 10 facts, 30 assumptions, 10 runs, and 10 verified objects.
- Post-activation regression: 361 backend tests and the frontend production build pass; the existing chunk-size warning remains informational.

**Activation status:** ✔ locally active, live-verified, and user-confirmed on 2026-09-23. No deployment, push, Batch 9, or Phase C work occurred.
