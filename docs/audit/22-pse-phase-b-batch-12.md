# Audit 22 — PSE V2 Phase B Batch 12

**Status:** frozen property-company batch implemented, staged, results-confirmed, separately activated locally, live-verified, and user-confirmed on 2026-09-23. Batch 11 is preserved for rollback.

## Reference and current state

- Confirmed set: `CPG, ROCK, SHNG, DD, ALLHC, CDC, ARA, PHES, RLT, BRN` — ordinary listed common equity only. The active Batch 11 catalog contains exactly 118 issuers and none of these ten.
- The existing property route uses attributable property RNAV/SOTP when carrying value, independent fair value, tax leakage, ownership, preferred claims, and shares are reconciled. Market-relative P/B is a separately labeled screening fallback. The ten PSE summary pages below show FY2025 annual and 2026 interim financials, but do not alone complete property-level RNAV or a current common-equity bridge.
- The existing calculator's blocked-artifact path is not fully wired: it attempts to read a market-relative baseline even for `not_available`; the PSE page loads detail and calculator together. A genuinely blocked Batch 12 record must render a null/unavailable page, not an error.

| Issuer | PSE financial-summary page | Reviewed interim BVPS (PHP) | Period |
|---|---|---:|---|
| CPG | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=189) | 2.16 | 2026-06-30 |
| ROCK | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=635) | 8.17 | 2026-06-30 |
| SHNG | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=218) | 11.60 | 2026-06-30 |
| DD | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=651) | 19.44 | 2026-06-30 |
| ALLHC | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=26) | 2.40 | 2026-06-30 |
| CDC | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=39) | 1.97, **pre-merger** | 2026-06-30 |
| ARA | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=38) | 1.17 | 2026-06-30 |
| PHES | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=138) | 1.01 | 2026-06-30 |
| RLT | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=40) | 0.72 | 2026-06-30 |
| BRN | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=13) | 2.79 | 2026-06-30 |

## Gaps against the frozen-batch contract

| ID | Severity | Check | Gap and intended treatment |
|---|---|---|---|
| B12-01 | P0 | ✔ Active manifest and local config inventory | No Batch 12 config, receipts, 128-company candidate, or frozen-set guard exists. Build beside the serving root and preserve Batch 11. |
| B12-02 | P0 | ✔ [CDC merger disclosure](https://edge.pse.com.ph/downloadHtml.do?file_id=1934958) and PSE summary | CDC's July 2026 merger changed its common-share denominator after the 30 June per-share report. Without a reviewed post-merger common-equity bridge, expose a blocked null result, not a current per-share screen. |
| B12-03 | P0 | ✔ Calculator and PSE page code | A blocked PSE record currently makes the calculator endpoint fail and the page show a generic error. Return a disabled calculator view and render explicit blocking reasons and source links. |
| B12-04 | P1 | ✔ Financial-summary pages and existing Batch 3 RNAV requirements | Property fair-value uplifts, claims, and shares are not source-reconciled for an intrinsic RNAV. Use a labeled, Low-reliability P/B screen for the other nine; keep intrinsic values null. Reuse the Batch 3 diversified-property and Batch 11 layered-holding screening bands, not new engines. |
| B12-05 | P1 | ✔ [DD company information](https://edge.pse.com.ph/companyInformation/form.do?cmpy_id=651), [ALLHC information](https://edge.pse.com.ph/companyInformation/form.do?cmpy_id=26), and [BRN information](https://edge.pse.com.ph/companyInformation/form.do?cmpy_id=13) | DD overlaps the listed DDMPR stake, ALLHC is held by ALI, and BRN has non-property interests and preferred claims. Show non-additivity and capital-claim warnings. |
| B12-06 | P1 | ✔ PSE summary-page notices | The pages are not original filing copies and do not establish publication date/source page or commercial-use rights. Store reviewed-fact receipts and links, leave publication date null, and do not automate acquisition or redistribute the remote pages. |

## Reuse and flow

Reuse the existing `market_relative_range`, blocked-artifact contract, Postgres/MinIO receipts, immutable catalog builder, authenticated API, and PSE page. The target flow is official source → reviewed versioned fact and adjustment → deterministic artifact → staged 128-entry catalog → real API → actual PSE page. Nine relative screens and one blocked result are the source-bounded initial routes, subject to testing; no PSE data API, price feed, peer study, or numerical RNAV is being invented.

## Batch 12 results per share

All figures are PHP per share. These are Low-reliability, **market-relative P/B screens**, not intrinsic RNAV/SOTP. The two bands are reused analyst screening assumptions, not calibrated peer multiples. CDC is null because its pre-merger per-share denominator does not describe the current common equity.

| Ticker | P/B band | Low | Base | High | Status |
|---|---|---:|---:|---:|---|
| CPG | 0.30/0.45/0.60 | 0.6480 | 0.9720 | 1.2960 | Provisional relative |
| ROCK | 0.30/0.45/0.60 | 2.4510 | 3.6765 | 4.9020 | Provisional relative |
| SHNG | 0.30/0.45/0.60 | 3.4800 | 5.2200 | 6.9600 | Provisional relative |
| DD | 0.25/0.40/0.55 | 4.8600 | 7.7760 | 10.6920 | Provisional relative |
| ALLHC | 0.30/0.45/0.60 | 0.7200 | 1.0800 | 1.4400 | Provisional relative |
| CDC | None accepted | — | — | — | Blocked / unavailable |
| ARA | 0.30/0.45/0.60 | 0.3510 | 0.5265 | 0.7020 | Provisional relative |
| PHES | 0.30/0.45/0.60 | 0.3030 | 0.4545 | 0.6060 | Provisional relative |
| RLT | 0.30/0.45/0.60 | 0.2160 | 0.3240 | 0.4320 | Provisional relative |
| BRN | 0.25/0.40/0.55 | 0.6975 | 1.1160 | 1.5345 | Provisional relative |

DD/DDMPR and ALLHC/ALI values overlap and must not be added. BRN's preferred-share claims and mixed interests remain unresolved. RLT's loss-making FY2025 limits the relevance of an earnings approach. No dated market price or current upside is asserted.

## Evidence and verification

- Cumulative candidate: exactly 128 artifacts — 34 intrinsic, 93 market-relative, 1 not available; 127 provisional and 1 blocked. The prior 118 artifacts were copied byte-for-byte from active Batch 11.
- Persistence: 10 current securities/hashed reviewed-fact receipts/reported facts/valuation runs, 27 screening assumptions (none adopted for blocked CDC), and 10 verified MinIO receipt objects. These are receipts, not redistributed PSE filing copies.
- Deterministic twin builds are byte-identical. Manifest SHA-256 `91f49f05119c301ee91bdb87053cec8d5eff201af183cf730819b7cdb273327a`; pointer and all artifact/internal hashes validate.
- Real authenticated staged API: 128/128 stored-detail parity; 10/10 calculator states. CDC detail exposes null values and explicit reasons; its calculator is disabled and POST returns 400. CPG baseline PHP0.972, edited 0.50x result PHP1.08, saved scenario `#30`; unauthenticated list returns 401.
- Real staged browser: US→PH navigation and CPG search showed the 128-company footer, provisional relative label and PHP0.97 base. Editing 0.45x to 0.50x showed PHP1.08 and saved scenario `#31`. CDC rendered `Blocked · unavailable`, no numerical value or calculator, the merger reason, seven-day calendar, and links to both the financial summary and merger disclosure. DD rendered PHP7.78 and the DDMPR overlap warning.
- Full backend regression: 377 passed; one pre-existing `crypt` deprecation warning. Frontend production build passed with the existing large-chunk warning.
- Active Batch 11 pointer SHA-256 remains `795bd88681e26e70565743058887f1fa19ac8ac09a49b43c6f0900032c36c227`; its manifest remains `82481331464c9910fc80c79215ef9c0ead4d709238bd2f2d3c0f3f101f684974`. Batch 12 is absent from the serving root. The activation guard now pins the exact confirmed candidate hash, but activation has not been run.

## Gate

**Staged-results gate, verified and user-confirmed on 2026-09-23.** That confirmation accepted the results only; local activation was separately authorized afterward, as recorded below. No deployment, push, CDC recovery, Batch 13, or Phase C work was authorized at this gate. Source acquisition remains manual and broader-use rights remain unconfirmed.

## Local activation

- The user separately authorized local Batch 12 activation on 2026-09-23. `active.json` and `staged.json` now select `PSE-V2-PHASE-B-B12-2026-09-23-1.0`, exactly 128 issuers. Active pointer SHA-256: `b86c8fd0fb732be6ec0ef8bacf27b6c60a72f6b719f4f5c653271b6f6b48a4e7`; manifest SHA-256 remains `91f49f05119c301ee91bdb87053cec8d5eff201af183cf730819b7cdb273327a`.
- The active catalog's 139 files are byte-identical to the confirmed candidate. Batch 11 rollback manifest remains unchanged at `82481331464c9910fc80c79215ef9c0ead4d709238bd2f2d3c0f3f101f684974`.
- Real active API with its normal rate limit: 128/128 stored-detail parity, 10/10 calculator states, unauthenticated 401, CDC disabled with POST 400, and CPG's 0.50x scenario persisted as `#32` (PHP0.972 baseline, PHP1.08 edited).
- Real active UI: US→PH navigation and search selected CPG; the page showed 128 companies, its PHP0.97 relative screen changed to PHP1.08 at 0.50x, and scenario `#33` saved. CDC rendered `Blocked · unavailable`, no numeric value or calculator, the merger reason, and both source links. DD rendered PHP7.78 and the DDMPR overlap warning.
- Persistence remained 10 current receipts/facts/runs/objects and 27 assumptions. Frontend production build passed. The full backend suite initially had one historical Batch 11 active-version assertion; after advancing it and older builder successor guards without changing their pinned parent hashes, **377 backend tests passed**. The existing `crypt` deprecation and large-chunk warnings remain informational.

**Activation status:** locally active, live-verified, and user-confirmed on 2026-09-23. No deployment, push, CDC recovery, Batch 13, or Phase C work occurred. Broader-use source rights remain unconfirmed.
