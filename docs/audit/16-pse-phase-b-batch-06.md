# Audit 16 — PSE V2 Phase B Batch 6

**Status:** implemented, staged-results confirmed, locally activated, live verified, and user-confirmed on 2026-09-23. Batch 5 is preserved for rollback.

## Reference

- Confirmed set: `TEL, GLO, CNVRG, DITO, NOW, GMA7, ABS, MB, DFNN, PLUS`.
- Telecom and profitable digital/media names target FCFF or distributions; holding/restructuring names target SOTP/NAV.
- When those specialist bridges are incomplete, publish transparent market-relative estimates without relabeling them intrinsic.

## Ours before Batch 6

- Active catalog: confirmed 58-company Batch 5.
- Existing relative engine supports P/E, P/B, and other positive per-share metrics; no new engine or UI is required.

## Gaps

| ID | Gap | Severity | Evidence |
|---|---|---|---|
| B06-01 | No reviewed source config or route for the frozen ten. | P0 | ✔ No Batch 6 module/config exists. |
| B06-02 | DITO, ABS, and DFNN have negative equity or earnings and cannot use ordinary P/B or P/E screens. | P0 | ✔ Current PSE financial summaries. |
| B06-03 | NOW's FY2025 annual filing status and ABS's 2026 recapitalization require current-period review. | P1 | ✔ PSE disclosures. |
| B06-04 | No cumulative 68-company candidate or live verification evidence exists. | P0 | ✔ Latest builder targets Batch 5. |

The build closes only this frozen batch and stops before activation.

## Batch 6 values per share

| Ticker | Screen | Low | Base | High |
|---|---|---:|---:|---:|
| TEL | P/E | 1022.24 | 1277.80 | 1533.36 |
| GLO | P/E | 1209.68 | 1512.10 | 1814.52 |
| CNVRG | P/B | 10.464 | 13.952 | 17.44 |
| DITO | P/S | 0.4779815250715499 | 0.7647704401144799 | 1.0515593551574098 |
| NOW | P/B | 0.75 | 1.00 | 1.25 |
| GMA7 | P/E | 2.70 | 3.60 | 4.50 |
| ABS | P/S, post-recapitalization shares | 1.869628660796162 | 3.1160477679936034 | 4.362466875191045 |
| MB | P/B | 0.40 | 0.60 | 0.80 |
| DFNN | P/S | 0.282100833 | 0.4231512495 | 0.564201666 |
| PLUS | P/E | 16.86 | 22.48 | 28.10 |

All ten are provisional market-relative outputs with Low reliability.

## Evidence and verification

- Cumulative candidate: 68 artifacts — 34 intrinsic, 34 market-relative, 0 unavailable; all provisional.
- Persistence: 10 securities, 10 receipts, 10 screening facts, 30 assumptions, 10 runs, and 10 verified MinIO objects.
- Deterministic twins are byte-identical; manifest SHA-256 is `848f8205e4da2b2fd6568385c1287e4efc890f0ce889595f0163abfea3ade37a`.
- Real staged API: 68/68 detail parity, 10/10 calculator parity, unauthenticated 401, and TEL scenario `#14` persisted.
- Real staged UI rendered TEL with the correct market-relative label and PHP1277.80 base. A later slider request hit the
  normal rate limiter after the full verification sweep; the same edit passed through real HTTP.
- Verification: 353 backend tests passed; frontend production build passed with the existing chunk warning.
- Active 58-company Batch 5 catalog remains unchanged.

## Gate

**Verified and user-confirmed on 2026-09-23.** Confirmation accepts staged Batch 6 only and does not authorize
deployment, push, recovery, Batch 7, or Phase C. Local activation was separately authorized.

## Local activation

- Active catalog: `PSE-V2-PHASE-B-B06-2026-09-23-1.0`, exactly 68 issuers.
- Active pointer SHA-256: `458520a940cc85411c5b1980d01d8063fc8b97cc863ff1b1626dc64f3fb1f96a`.
- Active manifest: `848f8205e4da2b2fd6568385c1287e4efc890f0ce889595f0163abfea3ade37a`.
- Batch 5 rollback manifest remains `b6dc2ae35ad13e0ee2f40c11e0b7190441da651acf914e90fea3334302ece95b`.
- Active API: 68/68 detail parity, 10/10 calculator parity, 401 unauthenticated, and TEL scenario `#15` persisted.
- Active UI rendered TEL with PHP1277.80 and the 68-company catalog footer.
- Post-activation regression: 353 backend tests and frontend production build pass.

**Activation status:** ✔ locally active, live verified, and user-confirmed on 2026-09-23. No deployment, push, Batch 7, or Phase C work occurred.
