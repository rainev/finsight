# Audit 20 — PSE V2 Phase B Batch 10

**Status:** implemented, staged-results confirmed, locally activated, live-verified, and user-confirmed on 2026-09-23. Batch 9 is preserved for rollback.

## Reference

- Confirmed set: `BLOOM, BEL, WEB, SUN, PHR, WPI, ACE, BHI, GPH, MJC`.
- Integrated resorts target property-level SOTP/FCFF; gaming platforms target regulatory-scenario FCFF; hotels target RNAV; distressed and suspended issuers retain explicit warnings.
- Where those specialist bridges are incomplete, publish transparent market-relative estimates without relabeling them intrinsic.

## Ours before Batch 10

- Active catalog: confirmed 98-company Batch 9.
- Existing market-relative engine supports P/B and P/S; no new engine or UI is required.

## Gaps

| ID | Gap | Severity | Evidence |
|---|---|---|---|
| B10-01 | No reviewed source config or route exists for the frozen ten. | P0 | ✔ No Batch 10 module/config existed. |
| B10-02 | SUN, PHR, and WEB have negative equity and cannot use ordinary P/B or P/E screens. | P0 | ✔ Current PSE summaries. |
| B10-03 | PHR proposes transferring substantially all consolidated operating assets and liabilities. | P0 | ✔ September 2026 disclosure. |
| B10-04 | MJC is suspended and its FY2025 audit remains pending. | P0 | ✔ Current PSE stock data and disclosure. |
| B10-05 | No cumulative 108-company candidate or live verification evidence exists. | P0 | ✔ Latest builder targets Batch 9. |

The build closes only this frozen batch and stops before activation.

## Batch 10 values per share

| Ticker | Screen | Low | Base | High |
|---|---|---:|---:|---:|
| BLOOM | P/B | 2.220 | 3.330 | 4.440 |
| BEL | P/B | 1.596 | 2.394 | 3.192 |
| WEB | P/S | 0.5485484921 | 1.0970969842 | 1.6456454763 |
| SUN | P/S | 0.0000456677 | 0.0000913354 | 0.0001370032 |
| PHR | P/S | 0.0016390374 | 0.0032780747 | 0.0049171121 |
| WPI | P/B | 0.551 | 1.102 | 1.653 |
| ACE | P/B | 0.696 | 1.160 | 1.624 |
| BHI | P/B | 0.021 | 0.035 | 0.049 |
| GPH | P/B | 3.345 | 5.575 | 7.805 |
| MJC | P/B | 0.576 | 0.960 | 1.344 |

All ten are provisional market-relative outputs with Low reliability. SUN, PHR, ACE, and MJC carry separate limitations.

## Evidence and verification

- Cumulative candidate: 108 artifacts — 34 intrinsic, 74 market-relative, 0 unavailable; all provisional.
- Persistence: 10 securities, 10 receipts, 10 screening facts, 30 assumptions, 10 runs, and 10 verified MinIO objects.
- Deterministic twins are byte-identical; manifest SHA-256 is `d835ccf5a75b9728a76e7a01f89a7fcc1054e06cf7564070f3f9c1973dbd5018`.
- Every manifest artifact hash and every internal artifact hash verifies.
- Real staged API: 108/108 detail parity, 10/10 calculator parity, unauthenticated 401, and BEL scenario `#22` persisted.
- Real staged UI rendered BEL at PHP2.39 and changed it to PHP2.79 at 0.7x P/B; PHR, ACE, and MJC warnings rendered; footer reported 108 companies.
- Verification: 369 backend tests passed; frontend production build passed with the existing chunk-size warning.
- At the staged-results gate, active Batch 9 remained unchanged: pointer SHA-256 `439d44cfec381664393e8b8f064d2ffece3dd0f58f95cb6e80b40c7bc3f64907`; manifest SHA-256 `194f099d96c4218341fb4d40e6a7849a9e2e9e8ccc306fe36c4b3ba4f01457c0`.
- At the staged-results gate, Batch 10 was absent from the serving root and its activation script remained locked pending results confirmation.

## Gate

**Verified and user-confirmed on 2026-09-23.** This confirmation accepts the staged Batch 10 results only and does not authorize activation, deployment, push, Batch 11, or Phase C.

## Local activation

- Active catalog: `PSE-V2-PHASE-B-B10-2026-09-23-1.0`, exactly 108 issuers.
- Active pointer SHA-256: `08b448c02edaf2e4f93bb1f307b8f9bad85bc90279cfbbb685d35387fe74f2a6`.
- Active manifest SHA-256: `d835ccf5a75b9728a76e7a01f89a7fcc1054e06cf7564070f3f9c1973dbd5018`.
- Batch 9 rollback manifest remains `194f099d96c4218341fb4d40e6a7849a9e2e9e8ccc306fe36c4b3ba4f01457c0`.
- Active API: 108/108 detail parity, 10/10 calculator parity, unauthenticated 401, and BEL scenario `#23` persisted.
- The verifier observes the normal fixed-window rate limit between the detail and calculator sweeps; no limiter bypass is used.
- Active UI rendered BEL at PHP2.39, changed it to PHP2.79 at 0.7x P/B, showed the 108-company footer, and exposed the PHR and MJC warnings.
- Persistence remained 10 securities, 10 receipts, 10 facts, 30 assumptions, 10 runs, and 10 verified objects.
- Post-activation regression: 369 backend tests and the frontend production build pass; the existing chunk-size warning remains informational.

**Activation status:** ✔ locally active, live-verified, and user-confirmed on 2026-09-23. No deployment, push, Batch 11, or Phase C work occurred.
