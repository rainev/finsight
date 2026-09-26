# Audit 29 — PSE V2 Phase B Batch 19

**Status:** Frozen Batch 19 results and separately authorized local activation were live-verified and user-confirmed on 2026-09-25. The 198-company Batch 19 catalog is active locally. Batch 18 remains preserved for rollback. No deployment, push, blocked recovery, or next batch occurred.

## Frozen scope and reviewed sources

Confirmed set: `TBGI, IS, PHC, LODE, CPM, APL, ABA, PAX, LMG, PRIM`. Each has a PSE common-stock page and latest financial-summary page; these are dated snapshots, not a perpetual listing guarantee. The catalog stores locally generated, hash-bound reviewed-fact receipts and official links, not original PSE page copies. Source publication dates and original filing page numbers remain unestablished. The PSE site displays a personal/non-commercial materials notice; broader acquisition and redistribution rights remain unconfirmed. No market price or current-upside claim is published.

| Ticker | PSE summary | Important source distinction |
|---|---|---|
| TBGI | [June 2026 report](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=269) | PHP597,119,987 parent equity / 3,795,622,000 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=269); EPS rounds to zero. |
| IS | [July 2026 report](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=204) | Non-December fiscal period; negative PHP109,791,383 total equity and losses. |
| PHC | [June 2026 report](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=97) | PHP1,454,602,858 parent equity / 996,391,254 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=97), not only 60m listed shares. |
| LODE | [June 2026 report](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=37) | Printed PHP0.80 BVPS conflicts with PHP225,367,129 total equity / 3bn [common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=37) = about PHP0.0751. The latter is a disclosed tentative total-book proxy, not parent-attributable intrinsic value. |
| CPM | [June 2026 report](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=621) | Parent equity PHP1,899,700,351 / 2,820,330,450 [shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=621); whole-peso printed BVPS is coarse. |
| APL | [June 2026 report](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=638) | Parent equity PHP3,597,252,668 / 292,686,349,297 [shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=638); zero gross revenue FY2025/1H2026. |
| ABA | [June 2026 report](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=174) | Parent equity PHP6,171,918,015 / 4,504,527,420 [outstanding shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=174), not total equity or only listed shares. |
| PAX | [June 2026 report](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=194) | Printed PHP5.97 BVPS does not reconcile to PHP1,265,232 thousand parent equity / 1,148,534,866 [common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=194). |
| LMG | [June 2026 report](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=205) | Parent equity PHP338,438,443 / 1,935,441,760 [shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=205); zero gross revenue FY2025/1H2026. |
| PRIM | [June 2026 report](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=30) | Total BVPS cannot be assigned to ordinary common while [Series A convertible preferred retirement/conversion](https://edge.pse.com.ph/downloadHtml.do?file_id=1945403) remains unresolved. |

## Staged outputs

The seven numeric rows are **market-relative P/B screens only**, provisional and Low reliability. They reuse finite existing operating (0.30/0.50/0.70×) or layered/asset (0.25/0.40/0.55×) review bands; they are neither peer-calibrated targets nor intrinsic values. Intrinsic bear/base/bull stay null for all ten. Values are PHP per ordinary common share, rounded to nine decimals in artifacts.

| Ticker | Low | Base | High | Status |
|---|---:|---:|---:|---|
| TBGI | 0.047195426 | 0.078659043 | 0.110122660 | Market-relative only |
| IS | — | — | — | Blocked: negative equity and financing residual |
| PHC | 0.364967791 | 0.583948465 | 0.802929139 | Market-relative only |
| LODE | 0.018780594 | 0.030048951 | 0.041317307 | Market-relative only; total-book proxy |
| CPM | 0.168393419 | 0.269429471 | 0.370465522 | Market-relative only |
| APL | 0.003072617 | 0.004916188 | 0.006759758 | Market-relative only; speculative asset book |
| ABA | 0.342539707 | 0.548063532 | 0.753587356 | Market-relative only |
| PAX | — | — | — | Blocked: parent equity/share and BVPS bridge unresolved |
| LMG | 0.052459100 | 0.087431833 | 0.122404567 | Market-relative only; no reported sales |
| PRIM | — | — | — | Blocked: convertible preferred/common dilution unresolved |

## Verification and release gate

- Candidate `PSE-V2-PHASE-B-B19-2026-09-25-1.0` contains exactly 198 entries: 34 inherited intrinsic, 159 market-relative and 5 unavailable; 193 provisional and 5 blocked (CDC, HOUSE, IS, PAX, PRIM). Manifest SHA-256 `2eb66b33f1dc545d6ae5584040db43234699911cc643ece3f98b5b3613c31b2f`. Deterministic twin builds are byte-identical and preserve all 188 Batch 18 artifacts byte-for-byte.
- Original-period Postgres facts, versioned assumptions, staged runs, and MinIO receipt-object readback passed: ten securities, ten receipts/objects, 30 facts, 21 multiple assumptions, ten runs. These receipts are not original filing hashes.
- Independent `Decimal` checks reproduced each new low/base/high value from equity units and dated outstanding shares. Three focused tests and all 404 backend tests passed; frontend production build passed with its existing large-chunk warning.
- Isolated authenticated staged HTTP returned exact 198/198 stored-detail parity, seven enabled and three disabled new calculator states, CDC/HOUSE still disabled, TBGI edited base PHP0.094390851 at 0.60× P/B, and unauthenticated 401.
- Signed-in temporary browser at `http://127.0.0.1:4002/pse/TBGI` rendered the 198-company staged footer, seven-day calendar and PHP0.08 default, then edited to PHP0.09 on screen. LODE's Cross-checks showed the PHP0.80/PHP0.0751 discrepancy. IS, PAX and PRIM each rendered their reason with no calculator. Screenshots are in `output/pse-valuation-candidates/phase-b-batch-19-candidate-a/ui-*-staged.png`. Only the uniquely created temporary test account was removed after each run; a final query found none remaining.
- The active local API still returned Batch 18 with 188 issuers; `active.json` SHA-256 stayed `ad0bd9eed2daa8a7e5c1f2288ead9f8355029dd1002722bdd358eb8971b4deb0`. No Batch 19 artifact was copied under the active serving root.

**Results gate:** user-confirmed on 2026-09-25. The exact 198-entry manifest hash is pinned in `scripts/activate_pse_v2_phase_b_batch_19.py`. Its default read-only preflight verified the confirmed issuer and blocked sets, 188 inherited artifacts, ten new receipt hashes, and the unchanged active Batch 18 parent. An isolated temporary-root activation rehearsal passed without touching real serving. A fresh authenticated local API check still returned active Batch 18 with 188 records and a 404 for TBGI. Four focused Batch 19 tests and all 405 backend tests passed; the frontend production build passed with its existing large-chunk warning. The real active pointer remains SHA-256 `ad0bd9eed2daa8a7e5c1f2288ead9f8355029dd1002722bdd358eb8971b4deb0`.

**At the results gate:** separate user authorization was required for local activation; it followed as recorded below. Wider PSE source-use rights, original-filing content lineage and specialist intrinsic underwrites remain unresolved.

## Batch 19 local activation, 2026-09-25

- The separately authorized guard copied only the exact confirmed candidate into the local serving root and switched `active.json` to `PSE-V2-PHASE-B-B19-2026-09-25-1.0`. Active pointer SHA-256 is `f4002d7a63c89938df3380f0d64da00742b6717b9ea65a1716d72810735e214e`; active manifest SHA-256 remains `2eb66b33f1dc545d6ae5584040db43234699911cc643ece3f98b5b3613c31b2f`. The Batch 18 rollback manifest remains `bef1cca0c41bf093c146068a688b1b35829886f281089bd6f0674142439626d1`.
- Historical batch-builder successor allowlists and active-count test expectations were advanced to Batch 19 without changing pinned older manifests. All 103 focused Phase B batch tests and all 405 backend tests passed; the frontend production build passed with the existing large-chunk warning.
- The running authenticated localhost:4001 API returned `active` with exact 198/198 stored-detail parity, seven enabled and three disabled Batch 19 calculator states, inherited CDC/HOUSE disabled, TBGI edited base PHP0.094390851407 at 0.60× P/B, and unauthenticated listing 401. Postgres/MinIO readback reconfirmed ten receipt objects, 30 original-period facts, 21 multiple assumptions and ten runs, including three blocked runs.
- The signed-in localhost:4000 PH page showed the 198-company footer and TBGI's provisional market-relative PHP0.08 base, changed to PHP0.09 at 0.60× P/B. The seven-day calendar changed from September 25 to 24 and back; global PH search opened ABA. LODE's Cross-checks displayed the printed PHP0.80 versus calculated PHP0.0751 book-value distinction. IS, PAX and PRIM each showed a blocked/null page without a calculator. Current-build screenshots are under `output/pse-valuation-candidates/phase-b-batch-19-candidate-a/ui-*-active.png`.
- Only temporary, uniquely named browser-verification accounts were removed; a final database readback found zero remaining. No source volumes were reset, no public deployment or promotion was performed, and no Batch 20/Phase C work began.

**Activation gate:** locally active, live-verified, and user-confirmed on 2026-09-25. Final read-only checks found the active pointer still at SHA-256 `f4002d7a63c89938df3380f0d64da00742b6717b9ea65a1716d72810735e214e`, the exact 198-entry manifest unchanged, and the Batch 18 rollback manifest unchanged. The live authenticated API returned Batch 19/198, TBGI detail 200, and PRIM detail 200 with `not_available`. No deployment, push, blocked recovery, Batch 20, or Phase C is authorized by this confirmation. Commercial-use PSE source rights, original-filing content lineage and specialist intrinsic inputs remain unresolved.
