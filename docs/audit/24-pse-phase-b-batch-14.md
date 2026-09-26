# Audit 24 — PSE V2 Phase B Batch 14

**Status:** exact ten-company Batch 14 results and separate local activation were both live-verified and user-confirmed on 2026-09-23. Batch 13 remains preserved for rollback.

## Reference and current state

- Confirmed set: `STI, CEU, FEU, IPO, MEDIC, EURO, MRSGI, UPSON, FRUIT, KEEPR` — ordinary listed common equity only. The active Batch 14 catalog contains exactly 148 issuers, including these ten; the prior 138-issuer Batch 13 catalog is retained unchanged for rollback.
- Intrinsic FCFF or attributable SOTP requires enrollment/store or distribution economics, reinvestment, ownership, minority and capital-claim bridges. The PSE financial summaries below give source-bounded reported per-share figures but not enough for those intrinsic models. Reuse the existing market-relative engine separately, with Low reliability and null intrinsic values.

| Issuer | PSE financial-summary page | Reviewed source basis | Latest cited period |
|---|---|---|---|
| STI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=222) | FY2025 EPS 0.22 + 9M FY2026 EPS 0.16 − prior 9M EPS 0.16 = PHP 0.22 TTM | 2026-03-31; June year-end |
| CEU | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=223) | FY2025 EPS 1.53 + 9M FY2026 EPS 1.20 − prior 9M EPS 1.24 = PHP 1.49 TTM | 2026-02-28; May year-end |
| FEU | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=25) | FY2026 basic EPS PHP 80.43 | 2026-05-31; May year-end |
| IPO | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=85) | FY2025 EPS 0.90 + 1H2026 EPS 0.42 − prior 1H EPS 0.39 = PHP 0.93 TTM | 2026-06-30 |
| MEDIC | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=687) | 1H2026 reported book value per share PHP 0.85 | 2026-06-30 |
| EURO | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=219) | FY2025 EPS 0.10 + 1H2026 EPS 0.05 − prior 1H EPS 0.04 = PHP 0.11 TTM | 2026-06-30 |
| MRSGI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=659) | FY2025 EPS 0.21 + 1H2026 EPS 0.07 − prior 1H EPS 0.04 = PHP 0.24 TTM | 2026-06-30 |
| UPSON | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=700) | FY2025 EPS 0.13 + 1H2026 EPS 0.08 − prior 1H EPS 0.06 = PHP 0.15 TTM | 2026-06-30 |
| FRUIT | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=676) | FY2025 EPS 0.05 + 1H2026 EPS 0.03 − prior 1H EPS 0.03 = PHP 0.05 TTM | 2026-06-30 |
| KEEPR | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=2) | FY2025 EPS 0.25 + 1H2026 EPS 0.12 − prior 1H EPS 0.11 = PHP 0.26 TTM | 2026-06-30 |

## Gaps against the frozen-batch contract

| ID | Severity | Check | Gap and intended treatment |
|---|---|---|---|
| B14-01 | P0 | ✔ Active manifest and local config inventory | No Batch 14 config, fact receipts, 148-company candidate, or exact-set guard exists. Build beside the serving root and preserve Batch 13. |
| B14-02 | P1 | ✔ PSE summaries and model requirements | Cash-flow, capex, enrollment/store economics, leases, minorities, and common claims are not reconciled for intrinsic FCFF/SOTP. Keep intrinsic scenarios null and label numeric outputs as provisional market-relative screens. |
| B14-03 | P1 | ✔ PSE annual/YTD period columns | STI and CEU use non-December fiscal years; FEU's May 2026 annual is newer than its February interim. Preserve source periods and store original EPS components separately from calculated TTM EPS. |
| B14-04 | P1 | ✔ [MEDIC filing history](https://edge.pse.com.ph/downloadHtml.do?file_id=1914083) and current summary | MEDIC's FY2025 audited filing was delayed; the summary now shows 2025 figures, but its low/rounded earnings make a P/E screen fragile. Use reported interim BVPS only as a Low-reliability P/B screen with an explicit filing-review warning. |
| B14-05 | P1 | ✔ [KEEPR company information](https://edge.pse.com.ph/companyInformation/form.do?cmpy_id=2) and current summary | KEEPR's equity overlaps COSCO, already in the catalog; standalone per-share screens are non-additive. The summary omits parent-equity attribution, so an intrinsic parent bridge is not complete. |
| B14-06 | P1 | ✔ PSE summary-page notices | The summary pages are not original filing copies and do not establish publication date/source page or broader commercial-use rights. Store reviewed-fact receipts and links; no automated acquisition or redistribution of remote pages. |

## Reuse and flow

Reuse `market_relative_range`, the existing P/E and P/B calculator controls, Postgres/MinIO fact-receipt persistence, immutable catalog builder, authenticated API, and PSE page. The target flow is official source → original-period reported facts → documented TTM normalization or stock metric → separately labeled provisional screen → staged 148-entry catalog → real API → actual PSE page. No new intrinsic model, price feed, autonomous extraction, or peer study is introduced.

## Staged result, 2026-09-23

All ten are provisional `market_relative_only` screens with Low reliability; intrinsic bear/base/bull remain null. These are not peer-calibrated price targets. The values below are exact artifact values in PHP per share, before the UI's two-decimal rounding.

| Ticker | Low | Base | High | Basis |
|---|---:|---:|---:|---|
| STI | 1.76 | 2.20 | 2.64 | TTM EPS × 8/10/12 P/E |
| CEU | 11.92 | 14.90 | 17.88 | TTM EPS × 8/10/12 P/E |
| FEU | 643.44 | 804.30 | 965.16 | FY2026 EPS × 8/10/12 P/E |
| IPO | 7.44 | 9.30 | 11.16 | TTM EPS × 8/10/12 P/E |
| MEDIC | 0.255 | 0.425 | 0.595 | 1H2026 BVPS × 0.30/0.50/0.70 P/B |
| EURO | 0.88 | 1.10 | 1.32 | TTM EPS × 8/10/12 P/E |
| MRSGI | 1.92 | 2.40 | 2.88 | TTM EPS × 8/10/12 P/E |
| UPSON | 1.20 | 1.50 | 1.80 | TTM EPS × 8/10/12 P/E |
| FRUIT | 0.40 | 0.50 | 0.60 | TTM EPS × 8/10/12 P/E |
| KEEPR | 2.08 | 2.60 | 3.12 | TTM EPS × 8/10/12 P/E |

## Verification and boundary

- Candidate `PSE-V2-PHASE-B-B14-2026-09-23-1.0`: 148 exact issuer records, 34 intrinsic, 113 market-relative, 1 unavailable; 147 provisional and 1 blocked. SHA-256 of manifest: `3afe1ac6f26b5e8751a714cf15776cc8e05a00304735d4b8b77b3c2922e54d38`. Deterministic twin catalogs matched byte-for-byte; all 138 inherited artifacts were byte-preserved.
- Postgres/MinIO: ten current reviewed-fact receipts/objects, 26 original-period PHP per-share facts, 30 multiple assumptions, and ten matching valuation runs. Derived TTM EPS is a normalization, not a reported fact. Source receipts are local summaries with links, not copies of PSE pages or filings; publication date and source-page references remain unavailable in the reviewed summary interface.
- Tests/build: four focused Batch 14 tests and all 385 backend tests pass. Frontend production build passes with the existing large-chunk warning (and was rerun after the MEDIC slider-label precision fix).
- Isolated authenticated staged HTTP on `127.0.0.1:4021`: 148/148 stored-detail parity, ten of ten new calculators, STI edited and saved at PHP 2.42 for 11× P/E (scenario `#38`), unauthenticated 401, inherited CDC calculator disabled.
- Isolated real browser at `127.0.0.1:4020`: US→PH market switch, 148-company staged footer, STI search and calculator edit (PHP 2.20→2.42), MEDIC P/B and delayed-audit caveat/source links, KEEPR/COSCO non-additive warning, and CDC blocked/null state with no calculator observed. MEDIC slider endpoint now displays `1.05` rather than binary-float noise.
- Active Batch 13 pointer SHA-256 remains `2f68c065064a9f0cd8c0c067ee6af69c7aff7bd935cfa5879153f0cb5af34170`; Batch 14 is absent from serving root. The activation guard pins the confirmed Batch 14 manifest hash; its default command is read-only preflight, and the mutating `--activate` path has not been run. No activation, deployment, push, CDC recovery, or next batch was performed.

**Results-confirmation gate:** user-confirmed on 2026-09-23. Read-only preflight verified all 148 artifacts and the unchanged active Batch 13 parent; an isolated temporary serving root exercised the activation routine without changing the real active pointer. The next gate is separate authorization for **local activation**. Broader-use PSE data rights remain unconfirmed, so this is local reviewed-source work, not an automated or production data feed.

## Local activation, 2026-09-23

- After the separate user authorization, `scripts/activate_pse_v2_phase_b_batch_14.py --activate` copied only the confirmed candidate into the local serving root and switched `active.json` to `PSE-V2-PHASE-B-B14-2026-09-23-1.0`. The active pointer SHA-256 is `aa71518fbc10d3637058490f5031a5d30f74e5df9a30e0023560ec209421b2a4`; the manifest still hashes to `3afe1ac6f26b5e8751a714cf15776cc8e05a00304735d4b8b77b3c2922e54d38`. Batch 13's manifest hash remains `beea44ae0f261aedf5c0d832253c45714ffebc50f7b59868b4a39b881740cc3c` for rollback.
- Real authenticated active API on the isolated local server returned `148/148` stored-detail parity, all ten Batch 14 calculator states, unauthenticated `401`, STI edited/saved at PHP 2.42 (`#39` via API), and CDC calculator disabled. Postgres/MinIO still verified ten current receipts/objects, 26 original-period facts, 30 assumptions, and ten matching runs.
- Real browser on the isolated local frontend switched US→PH, searched STI, showed the 148-company active footer and PHP 2.20 baseline, recalculated PHP 2.42 at 11× P/E and saved scenario `#40`. MEDIC retained its P/B/delayed-filing warning, KEEPR retained its COSCO non-additive warning, and CDC rendered blocked/null without a calculator.
- The first full regression after activation exposed 32 stale active-successor/active-count test expectations, not changed valuation outputs. Historical builder successor guards and active-list assertions were advanced without altering pinned parent hashes. The full backend suite then passed `385` tests; the frontend production build passed with its existing large-chunk warning.

**Activation-confirmation gate:** user-confirmed on 2026-09-23 after a fresh readback showed the 148-entry Batch 14 active pointer and the unchanged Batch 13 rollback manifest. No deployment, push, CDC recovery, Batch 15, or Phase C work is implied. Broader-use PSE source rights remain unconfirmed.
