# Audit 19 — PSE V2 Phase B Batch 9

**Status:** implemented, staged-results confirmed, locally activated, live-verified, and user-confirmed on 2026-09-23. Batch 8 is preserved for rollback.

## Reference

- Confirmed set: `FB, EMI, GSMI, RFM, MAXS, PIZZA, DELM, VITA, ANI, CAT`.
- Diversified staples target FCFF/SOTP; mature brands target normalized FCFF or distributions; restaurants target store-cohort FCFF; stressed and cyclical agriculture uses explicit fallback screens.
- Where those specialist bridges are incomplete, publish transparent market-relative estimates without relabeling them intrinsic.

## Ours before Batch 9

- Active catalog: confirmed 88-company Batch 8.
- Existing market-relative engine supports P/E, P/B, and P/S; no new engine or UI is required.

## Gaps

| ID | Gap | Severity | Evidence |
|---|---|---|---|
| B09-01 | No reviewed source config or route exists for the frozen ten. | P0 | ✔ No Batch 9 module/config existed. |
| B09-02 | DELM reports in USD, has negative parent equity, and requires explicit PHP normalization. | P0 | ✔ PSE report, common-share record, and BSP rate. |
| B09-03 | ANI's FY2025 annual filing remains delayed and cannot be silently treated as complete. | P0 | ✔ PSE filing note. |
| B09-04 | CAT uses a June fiscal year and requires non-calendar period handling. | P1 | ✔ Current PSE financial summary. |
| B09-05 | No cumulative 98-company candidate or live verification evidence exists. | P0 | ✔ Latest builder targets Batch 8. |

The build closes only this frozen batch and stops before activation.

## Batch 9 values per share

| Ticker | Screen | Low | Base | High |
|---|---|---:|---:|---:|
| FB | P/E | 40.320 | 50.400 | 60.480 |
| EMI | P/B | 10.560 | 14.080 | 17.600 |
| GSMI | P/E | 246.160 | 307.700 | 369.240 |
| RFM | P/E | 3.920 | 4.900 | 5.880 |
| MAXS | P/E | 2.700 | 3.600 | 4.500 |
| PIZZA | P/E | 4.100 | 5.330 | 6.560 |
| DELM | P/S on PHP-normalized FY2025 revenue/share | 2.5503088506 | 3.8254632760 | 5.1006177013 |
| VITA | P/B | 0.330 | 0.462 | 0.594 |
| ANI | P/B | 0.984 | 1.640 | 2.296 |
| CAT | P/B | 9.320 | 13.048 | 16.776 |

All ten are provisional market-relative outputs with Low reliability. DELM and ANI carry separate source-status warnings.

## Evidence and verification

- Cumulative candidate: 98 artifacts — 34 intrinsic, 64 market-relative, 0 unavailable; all provisional.
- Persistence: 10 securities, 10 receipts, 10 screening facts, 30 assumptions, 10 runs, and 10 verified MinIO objects.
- Deterministic twins are byte-identical; manifest SHA-256 is `194f099d96c4218341fb4d40e6a7849a9e2e9e8ccc306fe36c4b3ba4f01457c0`.
- Every manifest artifact hash and every internal artifact hash verifies.
- Real staged API: 98/98 detail parity, 10/10 calculator parity, unauthenticated 401, and FB scenario `#20` persisted.
- Real staged UI rendered FB at PHP50.40 and changed it to PHP55.44 at 11x P/E; DELM and ANI warnings rendered; CAT showed the 2026-03-31 period; footer reported 98 companies.
- Verification: 365 backend tests passed; frontend production build passed with the existing chunk-size warning.
- At the staged-results gate, active Batch 8 remained unchanged: pointer SHA-256 `cddaa00e782f5236d328985bd798815d010ee1e05ec6302d54c1733cd8a5ad2a`; manifest SHA-256 `0236bc52a4408f3e175c814ff9140cf82fa198454b84fbbe0044f8cc4c557a78`.
- At the staged-results gate, Batch 9 was absent from the serving root and its activation script remained locked pending results confirmation.

## Gate

**Verified and user-confirmed on 2026-09-23.** This confirmation accepts the staged Batch 9 results only and does not authorize activation, deployment, push, Batch 10, or Phase C.

## Local activation

- Active catalog: `PSE-V2-PHASE-B-B09-2026-09-23-1.0`, exactly 98 issuers.
- Active pointer SHA-256: `439d44cfec381664393e8b8f064d2ffece3dd0f58f95cb6e80b40c7bc3f64907`.
- Active manifest SHA-256: `194f099d96c4218341fb4d40e6a7849a9e2e9e8ccc306fe36c4b3ba4f01457c0`.
- Batch 8 rollback manifest remains `0236bc52a4408f3e175c814ff9140cf82fa198454b84fbbe0044f8cc4c557a78`.
- Active API: 98/98 detail parity, 10/10 calculator parity, unauthenticated 401, and FB scenario `#21` persisted.
- The verifier was streamlined to stay below the normal 120-request/minute ceiling without reducing 98/98 detail or 10/10 calculator coverage.
- Active UI rendered FB at PHP50.40, changed it to PHP55.44 at 11x P/E, showed the 98-company footer, and exposed the ANI and DELM warnings.
- Persistence remained 10 securities, 10 receipts, 10 facts, 30 assumptions, 10 runs, and 10 verified objects.
- Post-activation regression: 365 backend tests and the frontend production build pass; the existing chunk-size warning remains informational.

**Activation status:** ✔ locally active, live-verified, and user-confirmed on 2026-09-23. No deployment, push, Batch 10, or Phase C work occurred.
