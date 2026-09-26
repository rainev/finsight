# Audit 17 — PSE V2 Phase B Batch 7

**Status:** implemented, staged-results confirmed, locally activated, live-verified, and user-confirmed on 2026-09-23. Batch 6 is preserved for rollback.

## Reference

- Confirmed set: `ICT, CEB, PAL, MAC, ATI, TUGS, C, LSC, MWIDE, EEI`.
- Ports target concession-life DCF/SOTP; airlines target fleet NAV and lease-adjusted economics; shipping targets fleet NAV/FCFF; contractors target normalized FCFF or builder/concession SOTP.
- Where those specialist bridges are incomplete, publish transparent market-relative estimates without relabeling them intrinsic.

## Ours before Batch 7

- Active catalog: confirmed 68-company Batch 6.
- Existing market-relative engine supports P/E, P/B, and P/S; no new engine or UI is required.

## Gaps

| ID | Gap | Severity | Evidence |
|---|---|---|---|
| B07-01 | No reviewed source config or route exists for the frozen ten. | P0 | ✔ No Batch 7 module/config existed. |
| B07-02 | ICT reports in USD and requires an explicit dated PHP normalization. | P0 | ✔ PSE report and BSP 2026-09-22 reference rate. |
| B07-03 | CEB/PAL current earnings are negative; LSC is loss-making with near-zero 1H2026 equity. | P0 | ✔ Current PSE financial summaries. |
| B07-04 | ATI's latest PSE summary available in the review is stale. | P1 | ✔ Latest page period is 2025-09-30. |
| B07-05 | No cumulative 78-company candidate or live verification evidence exists. | P0 | ✔ Latest builder targets Batch 6. |

The build closes only this frozen batch and stops before activation.

## Batch 7 values per share

| Ticker | Screen | Low | Base | High |
|---|---|---:|---:|---:|
| ICT | P/E on PHP-normalized TTM EPS | 422.00928 | 527.51160 | 633.01392 |
| CEB | P/B | 18.156 | 24.208 | 30.260 |
| PAL | P/B | 1.062 | 1.416 | 1.770 |
| MAC | P/E | 5.120 | 6.400 | 7.680 |
| ATI | P/E | 22.560 | 28.200 | 33.840 |
| TUGS | P/E | 0.900 | 1.200 | 1.500 |
| C | P/B | 0.585 | 0.780 | 0.975 |
| LSC | P/S | 0.3006159619 | 0.4509239429 | 0.6012319239 |
| MWIDE | P/B | 2.766 | 3.688 | 4.610 |
| EEI | P/B | 3.036 | 4.048 | 5.060 |

All ten are provisional market-relative outputs with Low reliability. ATI carries a separate stale-period warning.

## Evidence and verification

- Cumulative candidate: 78 artifacts — 34 intrinsic, 44 market-relative, 0 unavailable; all provisional.
- Persistence: 10 securities, 10 receipts, 10 screening facts, 30 assumptions, 10 runs, and 10 verified MinIO objects.
- Deterministic twins are byte-identical; manifest SHA-256 is `7b3419c52934f9a15d378f8918027697fd9737f2fc449d7f897fa5dcda9f6f91`.
- Every manifest artifact hash and every internal artifact hash verifies.
- Real staged API: 78/78 detail parity, 10/10 calculator parity, unauthenticated 401, and ICT scenario `#16` persisted.
- Real staged UI rendered ICT at PHP527.51, changed to PHP562.68 at 16x P/E, reported 78 companies, and exposed ATI's stale-period warning.
- Verification: 357 backend tests passed; frontend production build passed with the existing chunk-size warning.
- At the staged-results gate, active Batch 6 remained unchanged: pointer SHA-256 `458520a940cc85411c5b1980d01d8063fc8b97cc863ff1b1626dc64f3fb1f96a`; manifest SHA-256 `848f8205e4da2b2fd6568385c1287e4efc890f0ce889595f0163abfea3ade37a`.
- At the staged-results gate, Batch 7 was absent from the serving root and its activation script remained locked pending results confirmation.

## Gate

**Verified and user-confirmed on 2026-09-23.** This confirmation accepts the staged Batch 7 results only and does not authorize activation, deployment, push, Batch 8, or Phase C.

## Local activation

- Active catalog: `PSE-V2-PHASE-B-B07-2026-09-23-1.0`, exactly 78 issuers.
- Active pointer SHA-256: `62caa7cce3ef7987681a7995c17aebec0db998db1f08e96dcd97b31b952cef7b`.
- Active manifest SHA-256: `7b3419c52934f9a15d378f8918027697fd9737f2fc449d7f897fa5dcda9f6f91`.
- Batch 6 rollback manifest remains `848f8205e4da2b2fd6568385c1287e4efc890f0ce889595f0163abfea3ade37a`.
- Active API: 78/78 detail parity, 10/10 calculator parity, unauthenticated 401, and ICT scenario `#17` persisted.
- Active UI rendered ICT at PHP527.51, changed it to PHP562.68 at 16x P/E, showed the 78-company footer, and exposed ATI's stale-period warning.
- Persistence remained 10 securities, 10 receipts, 10 facts, 30 assumptions, 10 runs, and 10 verified objects.
- Post-activation regression: 357 backend tests and the frontend production build pass; the existing chunk-size warning remains informational.

**Activation status:** ✔ locally active, live-verified, and user-confirmed on 2026-09-23. No deployment, push, Batch 8, or Phase C work occurred.
