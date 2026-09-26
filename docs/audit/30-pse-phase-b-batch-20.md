# Audit 30 — PSE V2 Phase B Batch 20

**Status:** Frozen Batch 20 results and separately authorized local activation were live-verified and user-confirmed on 2026-09-25. The 208-company Batch 20 catalog is active locally. Batch 19 remains preserved for rollback. No deployment, push, blocked recovery, or next batch occurred.

## Frozen scope and source boundary

Confirmed set: `MACAY, DMW, HTI, REDC, TOP, XG, HI, MBC, LOTO, PRC`. All ten were absent from active Batch 19. PSE common-stock pages showed `Open`/`Common` at their latest observed September 2026 dates; these are snapshots, not a perpetual listing guarantee. The PSE financial-summary pages show FY2025 and 1H2026 periods for each issuer. The pipeline stores locally generated, hash-bound reviewed-fact receipts and official links, not original PSE pages. Source publication dates and original filing page numbers remain unestablished. The PSE site displays a personal/non-commercial materials notice; broader acquisition and redistribution rights remain unconfirmed. No current market price or upside claim is published.

| Ticker | Official financial summary | Source-bounded parent-common distinction |
|---|---|---|
| MACAY | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=145) | PHP3,836,027,384 parent equity / 1,292,755,794 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=145&security_id=221); reported PHP4.83 BVPS follows much larger total equity. |
| DMW | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=671) | PHP36,292,091,230 parent equity / 3,395,864,100 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=671); development and leasing assets still need appraisal. |
| HTI | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=690) | PHP3,891,545,520 parent equity / 2,500,000,000 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=690); printed PHP1.67 BVPS follows total equity. |
| REDC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=702) | PHP2,521,175,284 parent equity / 650,000,002 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=702&security_id=702); printed PHP4.21 BVPS follows total equity. |
| TOP | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=706) | PHP3,210,994,963 parent equity / 10,742,193,000 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=706) = PHP0.298914287, not printed PHP0.38 BVPS; PSE stock page leaves ISIN blank. |
| XG | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=705) | PHP669,333,909 parent equity / 1,490,000,003 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=705); printed PHP0.51 BVPS follows total equity. FY2025 parent loss conflicts with positive displayed EPS, so EPS is not used. |
| HI | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=82) | PHP37,149,440,595 parent equity / 1,469,302,230 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=82&security_id=203), not PHP60.02bn total equity, printed PHP40.85 BVPS, or only 776.8m listed shares. |
| MBC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=117) | PHP1,930,472,627 parent equity / 402,682,990 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=117&security_id=382); parent equity exceeds total equity, so printed BVPS is not substituted. |
| LOTO | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=605) | PHP1,138,164,143 parent equity / 895,330,946 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=605); printed PHP1.39 BVPS does not match this dated denominator. |
| PRC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=141) | PHP4,610,601,173 parent equity / 546,706,156 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=141); printed PHP9.06 BVPS does not match this dated denominator and FY2025/1H2026 parent income is negative. |

## Exact staged outputs

All ten new outputs are `market_relative_only`, `provisional`, Low reliability, in PHP per ordinary common share. Intrinsic bear/base/bull remain null. These finite reused policy bands are screening sensitivities, not peer-calibrated price targets or specialist intrinsic values. `operating_book` uses 0.30/0.50/0.70×, `property_book` 0.30/0.45/0.60×, and `asset_book` 0.25/0.40/0.55× parent book per share.

| Ticker | Low | Base | High | Policy |
|---|---:|---:|---:|---|
| MACAY | 0.890197685 | 1.483662808 | 2.077127932 | Operating book |
| DMW | 3.206143429 | 4.809215143 | 6.412286857 | Property book |
| HTI | 0.466985462 | 0.700478194 | 0.933970925 | Property book |
| REDC | 0.969682799 | 1.551492478 | 2.133302157 | Asset book |
| TOP | 0.089674286 | 0.149457144 | 0.209240001 | Operating book |
| XG | 0.112304347 | 0.179686955 | 0.247069563 | Asset book |
| HI | 6.320932453 | 10.113491925 | 13.906051396 | Asset book |
| MBC | 1.438207728 | 2.397012880 | 3.355818032 | Operating book |
| LOTO | 0.381366515 | 0.635610859 | 0.889855202 | Operating book |
| PRC | 2.530025200 | 3.795037801 | 5.060050401 | Property book |

## Verification and release boundary

- Candidate `PSE-V2-PHASE-B-B20-2026-09-25-1.0` contains exactly 208 entries: 34 inherited intrinsic, 169 market-relative and 5 inherited unavailable; 203 provisional and 5 blocked (CDC, HOUSE, IS, PAX, PRIM). Manifest SHA-256 `50227c8db032133bf191da95ba4f8b9de94b717dc423fa8b027607a9b061ea23`. Deterministic twin builds matched byte-for-byte and preserved all 198 Batch 19 artifacts.
- Local Postgres/MinIO readback verified ten current reviewed receipts/objects, 30 original-period facts, 30 versioned multiple assumptions and ten staged runs. Receipts hash the reviewed fact records, not the original filings.
- Independent `Decimal` arithmetic reproduced the ten parent-common per-share bases and low/base/high outputs. Three focused Batch 20 tests and all 408 backend tests passed; frontend production build passed with its existing large-chunk warning.
- Isolated staged authenticated HTTP served exact 208/208 stored-detail parity and ten of ten enabled new calculators; inherited CDC/HOUSE/IS/PAX/PRIM remained disabled, TOP edited to PHP0.179348572 at 0.60× P/B, and unauthenticated listing returned 401.
- Signed-in staged browser at `http://127.0.0.1:4002/pse/TOP` showed the 208-company footer, seven-day calendar and PHP0.15 default, then edited to PHP0.18; source links rendered. Calendar navigation, search to REDC, HI's parent-equity warning, and inherited PRIM blocked/null with no calculator passed. Current staged screenshots are under `output/pse-valuation-candidates/phase-b-batch-20-candidate-a/ui-*-staged.png`. The temporary browser test account was removed; readback found none remaining.
- The normal local authenticated API still serves Batch 19 with 198 records and TOP 404. Its `active.json` SHA-256 remains `f4002d7a63c89938df3380f0d64da00742b6717b9ea65a1716d72810735e214e`. No Batch 20 catalog was copied to the serving root.

**Results gate:** user-confirmed on 2026-09-25. The exact 208-entry manifest hash is pinned in `scripts/activate_pse_v2_phase_b_batch_20.py`. Its default read-only preflight verified the confirmed issuer and blocked sets, availability/publication counts, 198 inherited artifacts, ten new receipt hashes, and the unchanged active Batch 19 parent. An isolated temporary-root activation rehearsal passed without touching real serving. A fresh authenticated local API check still returned active Batch 19/198 and TOP 404. Four focused Batch 20 tests and all 409 backend tests passed; the frontend production build passed with its existing large-chunk warning. The real active pointer remains SHA-256 `f4002d7a63c89938df3380f0d64da00742b6717b9ea65a1716d72810735e214e`.

**At the results gate:** separate user authorization was required for local activation; it followed as recorded below. Wider PSE source-use rights, original-filing content lineage and specialist intrinsic underwrites remain unresolved.

## Batch 20 local activation, 2026-09-25

- The separately authorized guard copied only the exact confirmed candidate into the local serving root and switched `active.json` to `PSE-V2-PHASE-B-B20-2026-09-25-1.0`. Active pointer SHA-256 is `cac24ffdb3f4a795ee3c204bd48c096d31491b1874a7e34580c156eaa5a1e20f`; active manifest SHA-256 remains `50227c8db032133bf191da95ba4f8b9de94b717dc423fa8b027607a9b061ea23`. The Batch 19 rollback manifest remains `2eb66b33f1dc545d6ae5584040db43234699911cc643ece3f98b5b3613c31b2f`.
- Historical batch-builder successor allowlists and active-count tests were advanced to Batch 20 without changing older catalog bytes. All 107 focused Phase B batch tests and all 409 backend tests passed; the frontend production build passed with the existing large-chunk warning.
- The running authenticated localhost:4001 API returned `active` with exact 208/208 stored-detail parity, ten enabled Batch 20 calculator states, inherited CDC/HOUSE/IS/PAX/PRIM disabled, TOP edited base PHP0.179348572289 at 0.60× P/B, and unauthenticated listing 401. Postgres/MinIO readback reconfirmed ten receipts/objects, 30 original facts, 30 multiple assumptions and ten runs.
- The signed-in localhost:4000 PH page showed the 208-company footer and TOP's provisional market-relative PHP0.15 base, changed to PHP0.18 at 0.60× P/B. The seven-day calendar changed from September 25 to 24 and back; global PH search opened REDC on the clean verification run. HI's Cross-checks showed the parent-equity versus reported-BVPS distinction, and inherited PRIM stayed blocked/null without a calculator. Current-build screenshots are under `output/pse-valuation-candidates/phase-b-batch-20-candidate-a/ui-*-active.png`.
- Two earlier post-scan browser attempts had an empty PH search dropdown; one received populated 200 responses from both list endpoints. A later clean browser run passed. This intermittent hydration symptom is recorded in the PSE learning and production backlog; its cause is not established and it did not change the catalog integrity result. Temporary verification accounts were removed; final database readback found zero. No volume reset, public deployment, or promotion occurred.

**Activation gate:** locally active, live-verified, and user-confirmed on 2026-09-25. Final read-only checks found the active pointer still at SHA-256 `cac24ffdb3f4a795ee3c204bd48c096d31491b1874a7e34580c156eaa5a1e20f`, the exact 208-entry manifest unchanged, and the Batch 19 rollback manifest unchanged. The live authenticated API returned Batch 20/208, TOP detail 200, and PRIM detail 200 with `not_available`. The intermittent search-hydration symptom remains logged for follow-up; this confirmation does not resolve it. No deployment, push, blocked recovery, Batch 21 or Phase C is authorized. Commercial-use PSE source rights, original-filing content lineage and specialist intrinsic inputs remain unresolved.
