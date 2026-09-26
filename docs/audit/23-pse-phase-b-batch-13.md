# Audit 23 — PSE V2 Phase B Batch 13

**Status:** frozen manufacturing and industrial-supply batch implemented, staged, results-confirmed, separately activated locally, live-verified, and user-confirmed on 2026-09-23. Batch 12 is preserved for rollback.

## Reference and current state

- Confirmed set: `IMI, TECH, ION, CIC, MVC, CROWN, STN, LFM, VMC, SBS` — ordinary listed common equity only. The active Batch 12 catalog contains exactly 128 issuers and none of these ten.
- FCFF remains the intrinsic route for operating manufacturers and distributors; ION and TECH also require holding-company attribution. PSE financial summaries identify periods, units, book value per share, and basic earnings, but do not supply an independently reviewed cash-flow forecast, reinvestment, claims, and common-share bridge for an intrinsic valuation.
- The prior Batch 9 cyclical operating P/B band and the existing lower recovery P/B band can be reused as *screening assumptions*, not peer-calibrated multiples or intrinsic values.

| Issuer | PSE financial-summary page | Reviewed interim BVPS | Period |
|---|---|---:|---|
| IMI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=622) | USD 0.12 | 2026-06-30 |
| TECH | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=630) | USD 0.31 | 2026-06-30 |
| ION | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=203) | USD 0.08 | 2026-06-30 |
| CIC | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=648) | PHP 14.10 | 2026-06-30 |
| MVC | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=100) | PHP 6.83 | 2026-06-30 |
| CROWN | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=657) | PHP 3.98 | 2026-06-30 |
| STN | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=164) | PHP 0.90 | 2026-06-30 |
| LFM | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=227) | PHP 14.65 | 2026-06-30 |
| VMC | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=123) | PHP 2.60 | 2026-05-31 (August year-end) |
| SBS | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=658) | PHP 3.11 | 2026-06-30 |

## Gaps against the frozen-batch contract

| ID | Severity | Check | Gap and intended treatment |
|---|---|---|---|
| B13-01 | P0 | ✔ Active manifest and config inventory | No exact Batch 13 fact config, receipts, 138-company candidate, or frozen-set guard exists. Build outside the serving root and preserve Batch 12. |
| B13-02 | P1 | ✔ PSE summary pages and FCFF engine inputs | Operating cash flows, capex, debt/lease/preferred/minority claims, and explicit forecasts are not reconciled. Keep intrinsic scenarios null; publish only separately labeled Low-reliability market-relative screens. |
| B13-03 | P1 | ✔ [BSP dated exchange-rate observation](https://www.bsp.gov.ph/Statistics/sdds/sdds.aspx) | IMI, TECH, and ION report USD BVPS while the catalog reports PHP. Preserve the rounded original USD values and normalize with the 23 September 2026 BSP observation of PHP 62.698 per USD. Warn that rounded USD cents magnify per-share uncertainty. |
| B13-04 | P1 | ✔ [TECH share classes](https://edge.pse.com.ph/downloadHtml.do?file_id=1903522) and PSE summaries | TECH has listed preferred classes; ION/STN have significant minority interests. A P/B screen is not a completed common-claim bridge. |
| B13-05 | P1 | ✔ [VMC financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=123) and [LFM disclosure](https://edge.pse.com.ph/downloadHtml.do?file_id=1931896) | VMC has an August fiscal year and a May interim period; LFM took over flour distribution after its June report. Preserve these dates and warn against treating the screen as refreshed operating economics. |
| B13-06 | P1 | ✔ PSE summary-page notices | Summary pages are not original filing copies and do not establish publication date/source page or broader commercial-use rights. Store reviewed-fact receipts and source links without automated acquisition or redistribution of remote pages. |

## Reuse and flow

Reuse the existing `market_relative_range`, Postgres/MinIO fact-receipt persistence, immutable catalog builder, authenticated API, calculator, and PSE page. The target flow is official PSE/BSP source → reviewed versioned fact and normalization → deterministic artifact → staged 138-entry catalog → real API → actual PSE page. No new intrinsic model, trading feed, automated PSE acquisition, or peer study is being introduced.

## Batch 13 results per share

All figures are PHP per share and **market-relative P/B screens**, not intrinsic FCFF/SOTP values. The bands are analyst screening assumptions rather than peer-calibrated multiples. Their numerical precision is calculation precision, not a claim that the rounded source BVPS is equally precise.

| Ticker | P/B band | Low | Base | High |
|---|---|---:|---:|---:|
| IMI | 0.30/0.50/0.70 | 2.257128 | 3.761880 | 5.266632 |
| TECH | 0.30/0.50/0.70 | 5.830914 | 9.718190 | 13.605466 |
| ION | 0.30/0.50/0.70 | 1.504752 | 2.507920 | 3.511088 |
| CIC | 0.50/0.70/0.90 | 7.050000 | 9.870000 | 12.690000 |
| MVC | 0.50/0.70/0.90 | 3.415000 | 4.781000 | 6.147000 |
| CROWN | 0.50/0.70/0.90 | 1.990000 | 2.786000 | 3.582000 |
| STN | 0.50/0.70/0.90 | 0.450000 | 0.630000 | 0.810000 |
| LFM | 0.50/0.70/0.90 | 7.325000 | 10.255000 | 13.185000 |
| VMC | 0.50/0.70/0.90 | 1.300000 | 1.820000 | 2.340000 |
| SBS | 0.50/0.70/0.90 | 1.555000 | 2.177000 | 2.799000 |

All ten are provisional and Low reliability, with null intrinsic scenarios. TECH's preferred classes, ION/STN minority claims, VMC's August fiscal year, LFM's July distribution change, and SBS's potential option dilution remain explicit limitations. No dated market-price comparison or current upside is asserted.

## Evidence and verification

- Cumulative staged candidate: exactly 138 artifacts — 34 intrinsic, 103 market-relative, 1 not available (the previously blocked CDC); 137 provisional and 1 blocked. The 128 active-parent artifacts were copied byte-for-byte.
- Persistence: 10 current securities/hashed reviewed-fact receipts/original-currency reported facts/valuation runs, 31 assumptions including one shared dated BSP FX observation, and 10 verified MinIO receipt objects. Three reported facts remain USD; VMC retains its 2026-05-31 period. Receipts are not redistributed filing copies.
- Deterministic twin builds are byte-identical. Manifest SHA-256 `beea44ae0f261aedf5c0d832253c45714ffebc50f7b59868b4a39b881740cc3c`; pointer and all artifact/internal hashes validate.
- Real authenticated staged API: 138/138 stored-detail parity and 10/10 new calculator parity. TECH baseline PHP9.71819, edited 0.60x result PHP11.661828, saved scenario `#34`; inherited CDC calculator remains disabled; unauthenticated list returns 401.
- Real staged browser: US→PH navigation and TECH search showed the 138-company footer, provisional relative label, PHP9.72 base, preferred-share warning, and PSE/preferred/BSP source links. Editing to 0.60x showed PHP11.66 and saved scenario `#35`. VMC rendered PHP1.82 with its May 2026 period and August-year-end warning. LFM rendered its post-report distribution warning; a display-only floating-point rounding error was corrected, and its mathematically PHP10.255 base now displays PHP10.26. The inherited CDC block still rendered null with a reason.
- Full backend regression: 381 passed; one pre-existing `crypt` deprecation warning. Frontend production build passed with the existing large-chunk warning.
- Active Batch 12 pointer SHA-256 remains `b86c8fd0fb732be6ec0ef8bacf27b6c60a72f6b719f4f5c653271b6f6b48a4e7`; its manifest remains `91f49f05119c301ee91bdb87053cec8d5eff201af183cf730819b7cdb273327a`. Batch 13 is absent from the serving root. The activation guard now pins the exact confirmed candidate hash, but activation has not been run.

## Gate

**Staged-results gate, verified and user-confirmed on 2026-09-23.** That confirmation accepted the results only; local activation was separately authorized afterward, as recorded below. No deployment, push, CDC recovery, Batch 14, or Phase C work was authorized at this gate. Source acquisition remains manual and broader-use rights remain unconfirmed.

## Local activation

- The user separately authorized local Batch 13 activation on 2026-09-23. `active.json` and `staged.json` now select `PSE-V2-PHASE-B-B13-2026-09-23-1.0`, exactly 138 issuers. Active pointer SHA-256: `2f68c065064a9f0cd8c0c067ee6af69c7aff7bd935cfa5879153f0cb5af34170`; manifest SHA-256 remains `beea44ae0f261aedf5c0d832253c45714ffebc50f7b59868b4a39b881740cc3c`.
- The active catalog's 149 files are byte-identical to the confirmed candidate. Batch 12 rollback manifest remains unchanged at `91f49f05119c301ee91bdb87053cec8d5eff201af183cf730819b7cdb273327a`.
- Real active API with its normal rate limit: 138/138 stored-detail parity, 10/10 new calculator states, unauthenticated 401, inherited CDC disabled, and TECH's 0.60x scenario persisted as `#36` (PHP9.71819 baseline, PHP11.661828 edited).
- Real active UI: US→PH navigation and search selected TECH; the page showed 138 companies, its PHP9.72 relative screen changed to PHP11.66 at 0.60x, and scenario `#37` saved. PSE, preferred-share, and BSP source links remained visible. LFM displayed PHP10.26; VMC showed its May 2026 period; CDC remained blocked/null without a calculator.
- Persistence remained ten current receipts/facts/runs/objects (three original USD facts) and thirty-one assumptions. Frontend production build passed. After advancing historical builder successor guards and active-list tests without changing their pinned parent hashes, **381 backend tests passed**. Existing `crypt` deprecation and large-chunk warnings remain informational.

**Activation status:** locally active, live-verified, and user-confirmed on 2026-09-23. No deployment, push, CDC recovery, Batch 14, or Phase C work occurred. Broader-use source rights remain unconfirmed.
