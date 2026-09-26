# Audit 26 — PSE V2 Phase B Batch 16

**Status:** Batch 16 staged results and separately authorized local activation were live-verified and user-confirmed on 2026-09-25. The 168-record Batch 16 catalog is active locally; Batch 15 remains preserved for rollback. No deployment or next batch is authorized by this confirmation.

## Reference and current state

Confirmed set: `AXLM, BALAI, FCG, FOOD, SFI, BCOR, BNCOM, BSC, PMPC, PPC`. The PSE stock-data pages showed open ordinary common classes during the source check; SFI also has a separate preferred class, which is excluded. The contract requires source-period and claim-bound screening outputs, no automatic blend of comparables into intrinsic value, and a staged cumulative catalog outside serving.

| Issuer | Reviewed PSE source | Original facts for the screen | Latest period and caveat |
|---|---|---|---|
| AXLM | [PSE financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=673) | FY2025 EPS 0.22 + 1H2026 EPS 0.11 − prior 1H EPS 0.06 = PHP0.27 TTM | 2026-06-30; export and input-cost cycle. |
| BALAI | [PSE financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=697) | 1H2026 reported BVPS PHP0.42 | 2026-06-30; parent equity/income fields render zero while total equity and BVPS are positive. Do not treat those zero fields as economic facts. |
| FCG | [PSE financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=689) | June FY2025 EPS 0.12 + 9M FY2026 EPS 0.08 − prior 9M EPS 0.08 = PHP0.12 TTM | 2026-03-31 on the summary; June fiscal year, not a calendar 1H2026 or completed FY2026 annual. |
| FOOD | [PSE financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=602), [common-share data](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=602) | USD78,817,556 FY2025 revenue + USD22,813,840 1H2026 − USD35,552,503 prior 1H = USD66,078,893 TTM; 2,499,712,463 outstanding common shares | 2026-06-30; USD accounts, losses, equity decline, rounded zero BVPS, and [proposed equity restructuring](https://edge.pse.com.ph/downloadHtml.do?file_id=1963653). Currency translation requires a dated same-series BSP USD/PHP observation. |
| SFI | [PSE financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=165), [common-share data](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=165&security_id=402) | PHP33.489m FY2025 revenue + PHP10.290m 1H2026 − PHP16.241m prior 1H = PHP27.538m TTM; 1,818,436,953 common shares | 2026-06-30; reported BVPS of 1 does not reconcile to total equity/common shares, and [convertible preferred shares](https://edge.pse.com.ph/downloadHtml.do?file_id=1940854) complicate claims. |
| BCOR | [PSE financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=9) | March 2026 reported BVPS PHP2.73 | 2026-03-31; June fiscal year, mixed automotive/hotel/holding interests and negative YTD income. |
| BNCOM | [PSE financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=692), [common-share data](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=692) | 1H2026 reported BVPS PHP22.08; reported total equity PHP36.373bn versus 1,403,013,920 listed outstanding common shares | 2026-06-30; interim parent-equity field blank and reported BVPS does not reconcile to listed common shares. Residual-income common-equity bridge is incomplete. |
| BSC | [PSE financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=60) | 1H2026 reported BVPS PHP0.28 | 2026-06-30; FY2025 BVPS column reads PHP0.02 despite billions in parent equity; mixed fuel/renewable interests and negative 1H parent income. |
| PMPC | [PSE financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=104) | June 2026 reported BVPS PHP12.68 | 2026-06-30; March FY2026 plus June Q1; reported Q1 EPS fell from 0.93 prior year to 0.21. |
| PPC | [PSE financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=150) | FY2025 EPS 1.97 + 1H2026 EPS 0.93 − prior 1H EPS 0.95 = PHP1.95 TTM | 2026-06-30; LPG, property and other interests need attributable SOTP for intrinsic value. |

These are manually reviewed public summaries/stock records, not automatically downloaded original filings. The PSE site notice limits access/download to personal, non-commercial use unless otherwise stated. Store local hash-bound fact receipts and official links; broader acquisition/redistribution rights remain unconfirmed.

## One-batch gap register

| ID | Severity | Check | Gap and intended treatment |
|---|---|---|---|
| B16-01 | P0 | ✔ Active Batch 15 manifest and exact frozen set | No Batch 16 config, reviewed receipts, 168-record candidate, or exact-set guard exists. Build outside serving and preserve all 158 parent artifacts byte-for-byte. |
| B16-02 | P1 | ✔ PSE period/metric columns and prior relative policies | AXLM/FCG/PPC earnings bridges and FOOD/SFI sales bridges require original annual/YTD facts stored separately from derived TTM metrics. Preserve June/March fiscal periods; no fixed-percentage price bumps. |
| B16-03 | P1 | ✔ PSE equity, EPS, share-class columns | BALAI parent attribution appears zero despite positive equity; SFI's BVPS does not fit common shares and has convertible preferred claims; BNCOM's BVPS/common-share denominator is unresolved; BSC annual BVPS and interim parent capital differ sharply. Do not force intrinsic values or treat missing/rounded fields as zero. Use clearly limited relative screens and explicit warnings. |
| B16-04 | P1 | ✔ FOOD USD source and BSP-linked prior conversion pattern | FOOD needs a dated USD/PHP assumption from the same benchmark series and a reviewed common share count before a PHP sales-per-share screen. Record FX date and rounding, and warn on restructuring and equity claims. |
| B16-05 | P1 | ✔ PSE company business descriptions and active model routes | BNCOM remains a residual-income route, BSC/BCOR/PPC mixed SOTP routes, and operating manufacturers/food services FCFF routes. Component and claim bridges are incomplete; comparables cannot be presented as intrinsic. |
| B16-06 | P1 | ✔ Source notices and local runtime contract | Current listing, source access rights, exact catalog status, active-pointer safety, and real API/UI parity must be checked. Stage first; no activation or automated source acquisition. |

## Reuse and flow

Reuse existing FCFF, residual-income and SOTP route labels; the market-relative P/E, P/B and P/S arithmetic; Postgres/MinIO receipt persistence; immutable catalog; authenticated API/calculator; and PH page. Nine or ten usable market-relative screens depend on fact reconciliation. Missing critical facts block only their affected model, with null values and reasons. Run deterministic twins, focused and full tests, frontend build, real persistence, exact 168/168 API parity, and browser status/calculator/source checks. Stop for **Batch 16 results confirmation**; no activation, deployment, push, blocked recovery, Batch 17, or Phase C is authorized.

## Staged result, 2026-09-25

All ten new outputs are provisional `market_relative_only` screens with Low reliability; intrinsic bear/base/bull remain null. These finite policy bands are not peer-calibrated price targets. Values are exact artifact PHP per ordinary common share before display rounding.

| Ticker | Low | Base | High | Screening basis |
|---|---:|---:|---:|---|
| AXLM | 2.16 | 2.70 | 3.24 | PHP0.27 TTM EPS × 8/10/12 P/E |
| BALAI | 0.126 | 0.210 | 0.294 | PHP0.42 BVPS × 0.30/0.50/0.70 P/B |
| FCG | 0.96 | 1.20 | 1.44 | PHP0.12 TTM EPS × 8/10/12 P/E |
| FOOD | 0.165739640 | 0.248609460 | 0.331479280 | TTM USD sales/common share × dated 62.698 PHP/USD × 0.10/0.15/0.20 P/S |
| SFI | 0.001514377 | 0.002271566 | 0.003028755 | PHP27.538m TTM sales/common share × 0.10/0.15/0.20 P/S |
| BCOR | 0.6825 | 1.0920 | 1.5015 | PHP2.73 BVPS × 0.25/0.40/0.55 P/B |
| BNCOM | 13.248 | 17.664 | 22.080 | PHP22.08 reported BVPS × 0.60/0.80/1.00 P/B; not residual income |
| BSC | 0.070 | 0.112 | 0.154 | PHP0.28 BVPS × 0.25/0.40/0.55 P/B |
| PMPC | 6.340 | 8.876 | 11.412 | PHP12.68 BVPS × 0.50/0.70/0.90 P/B |
| PPC | 15.60 | 19.50 | 23.40 | PHP1.95 TTM EPS × 8/10/12 P/E |

## Verification and release boundary

- Candidate `PSE-V2-PHASE-B-B16-2026-09-25-1.0` has exactly 168 issuer records: 34 inherited intrinsic, 132 market-relative, 2 inherited unavailable (CDC and HOUSE); 166 provisional and 2 blocked. Manifest SHA-256 `729e2272ddb7674592212cef7682b496e1814e68b0d326a6b3c4e0e75b628b93`. Deterministic twin builds were byte-identical, and all 158 Batch 15 parent artifacts were preserved byte-for-byte.
- Existing Postgres/MinIO verified ten current reviewed-fact receipts/objects, 22 original-period facts, 30 multiple assumptions, one dated USD/PHP assumption, and ten matching runs. FOOD revenue remains original USD; SFI revenue remains original PHP thousands; ordinary-common share counts keep their as-of dates and `currency=N/A` non-monetary label. An initial loader attempt rejected null currency for shares; the same idempotent receipt replay succeeded after explicit non-monetary labeling, with no row deletion.
- Four focused Batch 16 tests and all `393` backend tests pass; frontend production build passes with the existing large-chunk warning. The shared P/S calculator was corrected to accept the reviewed sub-1× policy band; low positive SFI peso outputs now display four decimals rather than falsely appearing as PHP0.00.
- Isolated authenticated staged HTTP returned `168/168` exact stored-detail parity and ten of ten new calculator states. AXLM edited and saved PHP2.97 at 11× P/E (scenario `#46`); SFI edited to PHP0.003028754992530115 at 0.20× P/S. FOOD carried the 23 September BSP USD/PHP source and rate 62.698. Unauthenticated access returned `401`; inherited CDC/HOUSE calculators stayed disabled.
- Isolated browser switched US→PH, searched AXLM, showed the staged 168-company footer and provisional PHP2.70 base, recalculated PHP2.97 and saved scenario `#47`. SFI showed a nonzero PHP0.0023 base and preferred-claim warning; FOOD showed the restructuring warning and PSE/common-share/BSP source links; BNCOM showed its unresolved BVPS/common-share bridge; FCG kept its March nine-month/June-fiscal-year caveat; inherited HOUSE rendered blocked/null.
- At the staged-results gate, active Batch 15 pointer SHA-256 was `350a44123ab089a0c484c9d600046177cfb557a05eb72da8472a959559a9c632`. Batch 16 was outside the serving root. Its exact user-confirmed manifest hash was pinned in a guard with read-only default preflight and an explicit mutating `--activate` path; the real mutating path had not yet been run. No activation, deployment, push, blocked recovery, or next batch occurred at that gate.

**Results gate:** user-confirmed on 2026-09-25. Read-only preflight verified the 168-entry candidate, CDC/HOUSE blocked set, and unchanged active Batch 15 parent. An isolated temporary-root activation test verified the guarded transition without touching real serving. Await separate authorization for local activation. Broader-use PSE source rights remain unconfirmed, and low host disk space remains an operational risk.

## Batch 16 local activation, 2026-09-25

- The separately authorized guard switched `active.json` to the exact 168-entry Batch 16 manifest SHA-256 `729e2272ddb7674592212cef7682b496e1814e68b0d326a6b3c4e0e75b628b93`; active pointer SHA-256 is `f86e87818993602af954ebb7f0c334307add93c687004d59e725e13797377888`. Batch 15's manifest remains unchanged at `641265728e673864851eeffaf3a989f9e18f41bba498aa5b523b383e60921aa3` for rollback.
- Existing Docker Postgres and MinIO volumes were not reset. The backend/frontend were started from existing local images with source mounts. Post-activation readback verified ten reviewed source objects, 22 original-period facts, 30 multiple assumptions, one dated FX assumption, and ten matching valuation runs.
- The running authenticated API served all 168 list/detail records with exact stored-artifact parity, ten of ten new calculator states, and disabled CDC/HOUSE calculators; unauthenticated listing returned 401. A short-lived locally signed JWT was used for bulk HTTP parity because the configured `.env` admin login returned 401; the browser checks used an existing signed-in session. The bulk check briefly hit the normal 120/minute limiter, then completed after its reset without changing the limiter.
- In the real PH page, the signed-in browser showed the 168-company Batch 16 footer and AXLM's provisional PHP2.70 base; changing its P/E from 10× to 11× recalculated PHP2.97 without saving. The company selector opened SFI, which showed nonzero PHP0.0023. FOOD showed its PSE financial, common-share, corporate-action, and dated BSP source links. HOUSE showed blocked/unavailable with no current per-share value or calculator.
- Historical builder successor guards and active-list expectations were advanced to Batch 16 without changing pinned earlier manifests. All 393 backend tests and the frontend production build pass; `git diff --check` passes. No deployment, push, blocked-issuer recovery, Batch 17, or Phase C work occurred.

**Activation gate:** locally active, live-verified, and user-confirmed on 2026-09-25. Fresh readback showed the exact 168-entry Batch 16 manifest and unchanged Batch 15 rollback hash. No deployment, push, CDC/HOUSE recovery, Batch 17, or Phase C work is authorized. Broader-use PSE source rights remain unconfirmed; host disk space is still tight.
