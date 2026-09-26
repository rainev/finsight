# Audit 27 — PSE V2 Phase B Batch 17

**Status:** Batch 17 staged results and separately authorized local activation were live-verified and user-confirmed on 2026-09-25. The 178-record Batch 17 catalog is active locally; Batch 16 remains preserved for rollback. No deployment or next batch is authorized by this confirmation.

## Frozen scope and reviewed source boundary

Confirmed set: `SGP, VVT, PREIT, SHLPH, CHP, PHN, RCI, TFC, LBC, MRC`. None overlapped active Batch 16. PSE stock-data pages showed ordinary common lines with `Open` status at their latest observed dates, ranging from 2026-09-07 to 2026-09-24. These snapshots are not a guarantee against later trading halts; no market quote is published in the artifacts. PSE website materials carry a personal/non-commercial access notice; broader acquisition and redistribution rights remain unconfirmed. The pipeline stores locally generated, hash-bound reviewed-fact receipts and official source links, not unrestricted copies of PSE pages.

| Issuer | PSE financial summary | Reviewed screening fact | Principal limitation |
|---|---|---|---|
| SGP | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=166) | 1H2026 reported BVPS PHP27.59 | Grid holding structure and large minority claims need SOTP. |
| VVT | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=79) | 1H2026 reported BVPS PHP21.81 | Power and water components need attributable valuation. |
| PREIT | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=699) | 1H2026 reported BVPS PHP1.90 | Large FY2025 loss plus [SIPCOR lease/permit proceedings](https://edge.pse.com.ph/downloadHtml.do?file_id=1960555) preclude an approved distribution model. |
| SHLPH | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=663) | 1H2026 reported BVPS PHP19.58 | 1H parent loss; fuel inventory, margins and leases need normalization. |
| CHP | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=662) | 1H2026 reported BVPS PHP0.95 | Losses, cement-cycle cash flows and parent-group overlap. |
| PHN | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=107) | 1H2026 reported BVPS PHP28.06 | Mixed education/materials/property holdings and minorities. |
| RCI | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=54) | 1H2026 reported BVPS PHP9.18 | Land values and 2025 gains cannot be extrapolated. |
| TFC | [August FY2025 and May 2026 nine months](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=8) | PHP3.52 annual EPS + 2.81 current 9M − 2.58 prior 9M = PHP3.75 aligned TTM EPS | August fiscal year; earnings screen is not property NAV. |
| LBC | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=236) | PHP14,025,956,097 annual revenue + 7,220,274,354 current 1H − 6,978,435,899 prior 1H, divided by 1,425,865,471 outstanding common shares = PHP10.0064100311 TTM sales/share | [Stock page](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=236&security_id=469) lists only 40,899,000 shares despite 1,425,865,471 outstanding; use outstanding for the screen and leave full economic-rights reconciliation open. |
| MRC | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=131) | 1H2026 reported BVPS PHP1.17 | Parent equity, total equity, BVPS and listed/outstanding shares do not reconcile; parent income is blank. |

## One-batch gap register and treatment

| ID | Severity | Firsthand gap | Treatment |
|---|---|---|---|
| B17-01 | P0 | Confirmed ten absent from active Batch 16 | Exact-set config and 178-record candidate outside serving; preserve all 168 parent artifacts byte-for-byte. |
| B17-02 | P1 | Mixed reporting periods and units | Keep original PHP/per-share/peso facts, align TFC's August fiscal-year EPS and LBC's annual/YTD revenue with the outstanding-common denominator. |
| B17-03 | P1 | Component economics and common claims not fully sourced | Keep FCFF, distributions and SOTP as primary routes, but publish only separately labeled Low-reliability P/B, P/E or P/S screens. No intrinsic scenarios or automatic blends. |
| B17-04 | P1 | PREIT lease case, LBC/MRC share-count gaps, CHP/PHN attribution | Carry visible warnings and official links; do not treat a positive relative screen as resolved intrinsic value. |
| B17-05 | P1 | Release boundary | Verify real Postgres/MinIO, deterministic twins, tests/build, staged API/UI and active-pointer safety; stop for results confirmation. |

## Exact staged outputs

All ten new outputs are `market_relative_only`, `provisional`, Low reliability, in PHP per ordinary common share. Intrinsic bear/base/bull are null. These finite policy bands are screening sensitivities, not peer-calibrated price targets.

| Ticker | Low | Base | High | Basis |
|---|---:|---:|---:|---|
| SGP | 13.795 | 19.313 | 24.831 | PHP27.59 BVPS × 0.50/0.70/0.90 P/B |
| VVT | 10.905 | 15.267 | 19.629 | PHP21.81 BVPS × 0.50/0.70/0.90 P/B |
| PREIT | 0.475 | 0.760 | 1.045 | PHP1.90 BVPS × 0.25/0.40/0.55 P/B |
| SHLPH | 5.874 | 9.790 | 13.706 | PHP19.58 BVPS × 0.30/0.50/0.70 P/B |
| CHP | 0.285 | 0.475 | 0.665 | PHP0.95 BVPS × 0.30/0.50/0.70 P/B |
| PHN | 7.015 | 11.224 | 15.433 | PHP28.06 BVPS × 0.25/0.40/0.55 P/B |
| RCI | 2.295 | 3.672 | 5.049 | PHP9.18 BVPS × 0.25/0.40/0.55 P/B |
| TFC | 30.000 | 37.500 | 45.000 | PHP3.75 aligned TTM EPS × 8/10/12 P/E |
| LBC | 5.003205016 | 7.004487022 | 9.005769028 | PHP10.0064100311 TTM sales/share × 0.50/0.70/0.90 P/S |
| MRC | 0.2925 | 0.4680 | 0.6435 | PHP1.17 reported BVPS × 0.25/0.40/0.55 P/B |

## Verification and release boundary

- Candidate `PSE-V2-PHASE-B-B17-2026-09-25-1.0` has exactly 178 records: 34 inherited intrinsic, 142 market-relative, 2 inherited unavailable (CDC/HOUSE); 176 provisional and 2 blocked. Manifest SHA-256 `63790df2c3df426b0b5c2e6e0ec8ca3c25c204717eee71a0b3a665f95f1efb92`. Deterministic twin builds matched byte-for-byte; all 168 Batch 16 artifacts were preserved.
- Existing Postgres/MinIO readback verified ten current reviewed receipts/objects, 15 original-period facts, 30 versioned multiple assumptions and ten matching runs. A receipt replay produced the same counts. Loader and verifier require separate processes because closing the shared psycopg pool is final in-process; the separate-process readback passed.
- Four focused Batch 17 tests and all 397 backend tests passed at the staged-results gate. Frontend production build passed with the existing large-chunk warning. At that gate, the serving pointer remained Batch 16 with SHA-256 `f86e87818993602af954ebb7f0c334307add93c687004d59e725e13797377888`; Batch 17 was absent from the serving root. The exact user-confirmed manifest hash was pinned in a guard with read-only default preflight and an explicit mutating `--activate` path; the real mutating path had not yet been run.
- Isolated staged authenticated HTTP served 178/178 exact stored-detail parity and ten of ten new calculator states. TFC edited to PHP41.25 at 11× P/E without saving. CDC/HOUSE calculators stayed disabled; unauthenticated listing returned 401. A short-lived local test-signed JWT was used for the bulk read-only parity check; the browser used an existing signed-in session. The normal 120/minute API limiter was respected with a reset wait.
- Isolated signed-in browser showed SGP's provisional PHP19.31 base, 178-company footer and PHP22.07 edit at 0.80× P/B, then saved scenario `#48`. PREIT showed a provisional PHP0.76 P/B screen with the lease/permit warning and official proceedings link. TFC retained its 2026-05-31 financial period and PHP37.50 base. LBC showed PHP7.00 P/S and the listed-versus-outstanding share caveat. MRC showed its unresolved attribution/share warning. Inherited HOUSE remained blocked/null. US→PH navigation returned to AP's inherited intrinsic screen.
- At the staged-results gate, the active `http://localhost:4000/pse/AXLM` page still showed Batch 16 and 168 companies. No catalog activation, deployment, push, blocked recovery, or next batch occurred at that gate.

**Results gate:** user-confirmed on 2026-09-25. Read-only preflight verified the 178-entry candidate, CDC/HOUSE blocked set, and unchanged active Batch 16 parent. An isolated temporary-root activation test verified the guarded transition without touching real serving. Separate local-activation authorization followed, as recorded below. Commercial-use PSE source rights remain unconfirmed, and host disk space remains tight.

## Batch 17 local activation, 2026-09-25

- The separately authorized guard switched `active.json` to the exact 178-entry Batch 17 manifest SHA-256 `63790df2c3df426b0b5c2e6e0ec8ca3c25c204717eee71a0b3a665f95f1efb92`; active pointer SHA-256 is `baea93d879687860442a50512fc6a4253b2a4a6d355df972cf59d17d5e5b5aa2`. Batch 16's manifest remains unchanged at `729e2272ddb7674592212cef7682b496e1814e68b0d326a6b3c4e0e75b628b93` for rollback.
- Historical builder successor guards and active-list tests were advanced to Batch 17 without changing pinned earlier manifests. All 397 backend tests and the frontend production build pass.
- The running authenticated local API served 178/178 exact stored-detail parity, ten of ten new calculator states, disabled CDC/HOUSE calculators, and unauthenticated listing 401. TFC edited to PHP41.25 at 11× P/E without saving. The local bulk verifier respected the normal rate limit. Existing Postgres/MinIO readback reconfirmed ten receipts/objects, 15 original-period facts, 30 multiple assumptions and ten matching runs; no data volumes were reset.
- The signed-in real page switched US→PH, showed the active 178-company footer, found SGP via the company selector, recalculated its provisional PHP19.31 base to PHP22.07 at 0.80× P/B, and saved scenario `#49`. The browser tab began at login; a local test-only verifier account was used. A later full browser navigation returned to login, so fresh-reload session persistence was not established in this check; the in-app navigation and active API checks passed.
- No deployment, push, blocked-issuer recovery, Batch 18, or Phase C work occurred. Broader-use PSE source rights remain unconfirmed.

**Activation gate:** locally active, live-verified, and user-confirmed on 2026-09-25. Fresh readback showed the exact 178-entry Batch 17 manifest and unchanged Batch 16 rollback hash. No deployment, push, CDC/HOUSE recovery, Batch 18, or Phase C work is authorized. Broader-use PSE source rights remain unconfirmed; host disk space remains tight.
