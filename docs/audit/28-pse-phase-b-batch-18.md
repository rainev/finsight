# Audit 28 — PSE V2 Phase B Batch 18

**Status:** Batch 18 staged results and separately authorized local activation were live-verified and user-confirmed on 2026-09-25. The 188-record Batch 18 catalog is active locally; Batch 17 remains preserved for rollback. No deployment or next batch is authorized by this confirmation.

## Frozen scope and source boundary

Confirmed set: `PBC, PTC, V, BKR, APC, IPM, SGI, CTS, REG, ECP`. None overlapped active Batch 17. Recent PSE stock-data pages showed ordinary common lines with `Open` status at their latest observed dates; these are snapshots, not a guarantee against later suspension. No price is published in the artifacts. PSE website materials carry a personal/non-commercial access notice; broader acquisition and redistribution rights remain unconfirmed. The pipeline stores locally generated, hash-bound reviewed-fact receipts and official links, not unrestricted copies of PSE pages.

| Issuer | Reviewed PSE financial summary | Source-bounded screening input and caveat |
|---|---|---|
| PBC | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=208) | 1H2026 reported BVPS PHP44.74; residual income still needs capital and ROE review. |
| PTC | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=144) | 1H2026 reported BVPS PHP23.22; parent equity/income fields display zero despite positive total equity. Treat zero fields as unavailable, not economic zero. |
| V | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=65) | 1H2026 reported BVPS PHP2.47; investment components need attributable SOTP. |
| BKR | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=66) | 1H2026 reported BVPS PHP0.96; EPS and reported income conflict, and its [MARC interest](https://edge.pse.com.ph/companyInformation/form.do?cmpy_id=66) is non-additive. |
| APC | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=177) | 1H2026 rounded BVPS PHP0.02; zero reported gross revenue and losses make this only a tiny, Low-reliability book screen. |
| IPM | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=4) | PHP848,022,273 parent equity / 690,000,000 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=4) = PHP1.229017787/share; reported PHP1.80 BVPS follows total equity and is not substituted. |
| SGI | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=160) | 1H2026 reported BVPS PHP7.16; electronics/property components need SOTP. |
| CTS | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=693) | 1H2026 reported BVPS PHP0.29; EPS rounds to zero, so no invented P/E precision. |
| REG | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=153) | PHP2,451,235 thousand parent equity × 1,000 / 682,065,632 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=153) = PHP3.593840365/share; reported PHP4.00 BVPS follows total equity. |
| ECP | [FY2025 and 1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=70) | PHP247,185,590 parent equity / 150,000,000 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=70&security_id=126) = PHP1.647903933/share; reported PHP1.89 BVPS follows total equity. |

## One-batch gap register and treatment

| ID | Severity | Firsthand gap | Treatment |
|---|---|---|---|
| B18-01 | P0 | Confirmed ten absent from active Batch 17 | Exact-set config and 188-record candidate outside serving; preserve all 178 parent artifacts byte-for-byte. |
| B18-02 | P1 | PTC zero parent fields and BKR/APC/CTS unusable EPS or operating income | Keep reported facts separate from missing values; use finite, explicit P/B screens only and label them Low reliability. |
| B18-03 | P1 | IPM, REG and ECP reported BVPS includes minority equity | Preserve original total BVPS, parent equity, currency units and dated ordinary shares; derive a parent-common per-share screen rather than using total equity. |
| B18-04 | P1 | Bank capital, mixed holdings and operating FCFF incomplete | Keep residual-income, SOTP and FCFF as primary routes with null intrinsic scenarios; never auto-blend relative screens into intrinsic value. |
| B18-05 | P1 | Release boundary | Verify Postgres/MinIO, deterministic twins, tests/build, staged API/UI and active-pointer safety; stop for results confirmation. |

## Exact staged outputs

All ten new outputs are `market_relative_only`, `provisional`, Low reliability, in PHP per ordinary common share. Intrinsic bear/base/bull are null. These finite policy bands are screening sensitivities, not peer-calibrated price targets.

| Ticker | Low | Base | High | Basis |
|---|---:|---:|---:|---|
| PBC | 26.844 | 35.792 | 44.740 | PHP44.74 reported BVPS × 0.60/0.80/1.00 P/B |
| PTC | 13.932 | 18.576 | 23.220 | PHP23.22 reported BVPS × 0.60/0.80/1.00 P/B |
| V | 0.6175 | 0.9880 | 1.3585 | PHP2.47 reported BVPS × 0.25/0.40/0.55 P/B |
| BKR | 0.240 | 0.384 | 0.528 | PHP0.96 reported BVPS × 0.25/0.40/0.55 P/B |
| APC | 0.005 | 0.008 | 0.011 | PHP0.02 rounded reported BVPS × 0.25/0.40/0.55 P/B |
| IPM | 0.307254447 | 0.491607115 | 0.675959783 | PHP1.229017787 derived parent BVPS × 0.25/0.40/0.55 P/B |
| SGI | 1.790 | 2.864 | 3.938 | PHP7.16 reported BVPS × 0.25/0.40/0.55 P/B |
| CTS | 0.0725 | 0.1160 | 0.1595 | PHP0.29 reported BVPS × 0.25/0.40/0.55 P/B |
| REG | 0.898460091 | 1.437536146 | 1.976612201 | PHP3.593840365 derived parent BVPS × 0.25/0.40/0.55 P/B |
| ECP | 0.494371180 | 0.823951967 | 1.153532753 | PHP1.647903933 derived parent BVPS × 0.30/0.50/0.70 P/B |

## Verification and release boundary

- Candidate `PSE-V2-PHASE-B-B18-2026-09-25-1.0` has exactly 188 records: 34 inherited intrinsic, 152 market-relative, 2 inherited unavailable (CDC/HOUSE); 186 provisional and 2 blocked. Manifest SHA-256 `bef1cca0c41bf093c146068a688b1b35829886f281089bd6f0674142439626d1`. Deterministic twin builds matched byte-for-byte; all 178 Batch 17 artifacts were preserved.
- Existing Postgres/MinIO readback verified ten current reviewed receipts/objects, 16 original-period facts, 30 versioned multiple assumptions and ten matching runs. A receipt replay produced the same counts. Original REG parent equity remained PHP thousands; ordinary-share counts retained their as-of dates and `currency=N/A` label.
- Four focused Batch 18 tests and all 401 backend tests passed at the staged-results gate. Frontend production build passed with the existing large-chunk warning. At that gate, the serving pointer remained Batch 17 with SHA-256 `baea93d879687860442a50512fc6a4253b2a4a6d355df972cf59d17d5e5b5aa2`; Batch 18 was absent from the serving root. The exact confirmed manifest hash was pinned in a guard with read-only default preflight and an explicit mutating `--activate` path; the real mutating path had not yet been run.
- Isolated staged authenticated HTTP served 188/188 exact stored-detail parity and ten of ten new calculator states. ECP edited to PHP0.98874236 at 0.60× P/B without saving. CDC/HOUSE calculators stayed disabled; unauthenticated listing returned 401. A short-lived local test-signed JWT was used for bulk parity; the browser used an existing signed-in session. The normal 120/minute API limiter was respected with a reset wait.
- Isolated signed-in browser showed PBC's provisional PHP35.79 base, 188-company footer and PHP40.27 edit at 0.90× P/B, then saved scenario `#50`. PTC displayed the zero-parent-field caveat; APC displayed nonzero PHP0.0080 and its no-revenue warning; IPM showed its PHP1.229 parent-common input rather than PHP1.80 total BVPS. Inherited HOUSE remained blocked/null. US→PH navigation returned to AP's inherited intrinsic screen.
- At the staged-results gate, the active `http://localhost:4000/pse/SGP` page still showed Batch 17 and 178 companies. No catalog activation, deployment, push, blocked recovery, or next batch occurred at that gate.

**Results gate:** user-confirmed on 2026-09-25. Read-only preflight verified the 188-entry candidate, CDC/HOUSE blocked set, and unchanged active Batch 17 parent. An isolated temporary-root activation test verified the guarded transition without touching real serving. Separate local-activation authorization followed, as recorded below. Commercial-use PSE source rights remain unconfirmed, and host disk space remains tight.

## Batch 18 local activation, 2026-09-25

- The separately authorized guard switched `active.json` to the exact 188-entry Batch 18 manifest SHA-256 `bef1cca0c41bf093c146068a688b1b35829886f281089bd6f0674142439626d1`; active pointer SHA-256 is `ad0bd9eed2daa8a7e5c1f2288ead9f8355029dd1002722bdd358eb8971b4deb0`. Batch 17's manifest remains unchanged at `63790df2c3df426b0b5c2e6e0ec8ca3c25c204717eee71a0b3a665f95f1efb92` for rollback.
- Historical builder successor guards and active-list tests were advanced to Batch 18 without changing pinned earlier manifests. All 401 backend tests and the frontend production build pass.
- The running authenticated local API served 188/188 exact stored-detail parity, ten of ten new calculator states, disabled CDC/HOUSE calculators, and unauthenticated listing 401. ECP edited to PHP0.98874236 at 0.60× P/B without saving. The bulk verifier respected the normal rate limit. Existing Postgres/MinIO readback reconfirmed ten receipts/objects, 16 original-period facts, 30 multiple assumptions and ten matching runs; no data volumes were reset.
- The signed-in real page showed the active 188-company footer, recalculated PBC's provisional PHP35.79 base to PHP40.27 at 0.90× P/B and saved scenario `#51`. PTC retained its zero-parent-field warning; HOUSE remained blocked/null without a calculator. US→PH navigation returned to AP's inherited intrinsic screen.
- No deployment, push, blocked-issuer recovery, Batch 19, or Phase C work occurred. Broader-use PSE source rights remain unconfirmed.

**Activation gate:** locally active, live-verified, and user-confirmed on 2026-09-25. Fresh readback showed the exact 188-entry Batch 18 manifest and unchanged Batch 17 rollback hash. No deployment, push, CDC/HOUSE recovery, Batch 19, or Phase C work is authorized. Broader-use PSE source rights remain unconfirmed; host disk space remains tight.
