# Audit 31 — PSE V2 Phase B Batch 21

**Status:** Frozen Batch 21 results were user-confirmed, then separately authorized for local activation on 2026-09-25. The 218-record Batch 21 catalog is locally active, live-verified, and user-confirmed; Batch 20 remains preserved for rollback. No deployment, push, blocked recovery, or next batch occurred.

## Frozen scope and reviewed sources

Confirmed set: `IDC, JOH, KEP, LPC, DWC, OM, MHC, PHA, SPM, SRDC`. All ten were absent from active Batch 20. PSE stock-data pages showed `Open`/`Common` at their latest observed September 2026 dates; these are snapshots, not a perpetual listing guarantee. The PSE financial-summary pages show FY2025 and 1H2026 for nine issuers; SPM's latest visible interim is **March 2026**, not June. The pipeline stores locally generated, hash-bound reviewed-fact receipts and official links, not original PSE pages. Original filing publication dates and page numbers were not established. The PSE site displays a personal/non-commercial materials notice; broader acquisition and redistribution rights remain unconfirmed. No current market price or upside claim is published.

| Ticker | Official PSE financial summary | Reviewed equity/share distinction |
|---|---|---|
| IDC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=660) | PHP1,992,603,887 parent equity / 724,004,114 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=660); reported PHP2.75 BVPS reconciles approximately. |
| JOH | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=261) | PHP2,935,659,508 parent equity / 281,500,000 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=261), excluding about PHP1.045bn of non-parent equity. |
| KEP | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=88) | PHP518,803,222 parent equity / 293,828,900 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=88), not the 296.6m listed count. |
| LPC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=698) | Parent-equity field is blank. PHP501,136,587 total equity / 25,000,000,000 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=698) is a labeled total-book proxy; printed PHP0.02 BVPS is rounded. |
| DWC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=647) | PHP5,558,266,499 parent equity / 854,000,000 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=647); FY2025 and 1H2026 parent results were losses. |
| OM | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=207) | PHP578,026,502 parent equity / 1,050,461,673 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=207), not printed PHP0.57 BVPS following total equity. |
| MHC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=206) | PHP158,524,085 parent equity / 1,200,000,000 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=206); reported PHP0.34 BVPS follows PHP406.8m total equity with substantial minority claims. |
| PHA | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=148) | Source units are PHP thousands: PHP2,500,159 thousand parent equity / 5,708,359,504 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=148), not only 2.254bn listed shares. |
| SPM | [FY2025/1Q2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=156) | Parent-equity line is blank/zero and remains unavailable. PHP381,562,152 total equity / 133,074,040 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=156), not 163m listed shares, is a tentative total-book proxy. |
| SRDC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=479) | Parent-equity field shows zero despite PHP45,520,576 positive total equity. That zero is treated as unavailable attribution; total equity / 110,000,000 [outstanding common shares](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=479) is only a tentative book proxy. |

## Exact staged outputs

All ten new outputs are `market_relative_only`, `provisional`, Low reliability, in PHP per ordinary common share. Intrinsic bear/base/bull remain null. The finite 0.30/0.45/0.60× property-book and 0.25/0.40/0.55× layered-book bands are screening sensitivities, **not** peer-calibrated targets or appraised NAV/SOTP. LPC, SPM and SRDC use labeled total-book proxies because parent attribution is unavailable; the other seven use parent equity.

| Ticker | Low | Base | High | Basis |
|---|---:|---:|---:|---|
| IDC | 0.825659902 | 1.238489854 | 1.651319805 | Parent; property book |
| JOH | 2.607157645 | 4.171452232 | 5.735746818 | Parent; layered book |
| KEP | 0.529699313 | 0.794548970 | 1.059398627 | Parent; property book |
| LPC | 0.006013639 | 0.009020459 | 0.012027278 | Total proxy; property book |
| DWC | 1.952552634 | 2.928828951 | 3.905105269 | Parent; property book |
| OM | 0.137564872 | 0.220103795 | 0.302642718 | Parent; layered book |
| MHC | 0.033025851 | 0.052841362 | 0.072656872 | Parent; layered book |
| PHA | 0.109495513 | 0.175192820 | 0.240890128 | Parent; PHP-thousands conversion |
| SPM | 0.716823041 | 1.146916865 | 1.577010690 | Total proxy; March interim |
| SRDC | 0.124147025 | 0.186220538 | 0.248294051 | Total proxy; parent fields unavailable |

## Staged verification and historical release boundary

- Candidate `PSE-V2-PHASE-B-B21-2026-09-25-1.0` contains exactly 218 entries: 34 inherited intrinsic, 179 market-relative and 5 inherited unavailable; 213 provisional and 5 blocked (CDC, HOUSE, IS, PAX, PRIM). Manifest SHA-256 `eddf03189b851c60a4c8166de1cf8d57ad37ea7b0510791b152ae3e939a992a3`. Deterministic twin builds matched byte-for-byte and preserved all 208 Batch 20 artifacts.
- Local Postgres/MinIO readback verified ten current reviewed receipts/objects, 30 original-period facts, 30 versioned multiple assumptions and ten staged runs. Receipts hash reviewed fact records, not original filings. PHA retained PHP-thousands units; SPM retained its March 2026 period.
- Independent `Decimal` arithmetic reproduced the ten per-share bases and low/base/high outputs. Three focused Batch 21 tests and all 412 backend tests passed; frontend production build passed with its existing large-chunk warning.
- Isolated staged authenticated HTTP served exact 218/218 stored-detail parity and ten of ten enabled new calculators; inherited CDC/HOUSE/IS/PAX/PRIM remained disabled, LPC edited to PHP0.01002273174 at 0.50× P/B, and unauthenticated listing returned 401.
- Signed-in staged browser at `http://127.0.0.1:4002/pse/LPC` showed the 218-company footer, seven-day calendar and PHP0.0090 default, then edited to about PHP0.01; source links rendered. Calendar navigation, search to PHA, PHA's PHP-thousands warning, SPM's March financial period, SRDC's total-proxy warning and inherited PRIM blocked/null with no calculator passed. Current staged screenshots are under `output/pse-valuation-candidates/phase-b-batch-21-candidate-a/ui-*-staged.png`. The temporary browser test account was removed; readback found none remaining.
- The normal local authenticated API still serves Batch 20 with 208 records and IDC 404. Its `active.json` SHA-256 remains `cac24ffdb3f4a795ee3c204bd48c096d31491b1874a7e34580c156eaa5a1e20f`. No Batch 21 catalog was copied to the serving root.
- **UI precision caveat:** The shared PSE page switches from four to two displayed decimals at PHP0.01. For LPC, exact low/base/high differ, but a high near PHP0.012 can display as PHP0.01, similar to an edited base near PHP0.010. Exact catalog/API numbers above remain intact; a small-value display improvement is deferred rather than changing the active Batch 20 UI during this staging gate.

**Results gate:** user-confirmed on 2026-09-25. The exact 218-entry manifest hash is pinned in `scripts/activate_pse_v2_phase_b_batch_21.py`. Its default read-only preflight verified the issuer and blocked sets, availability/publication counts, all 208 inherited artifacts, ten receipt hashes, and the unchanged active Batch 20 parent. An isolated temporary-root activation rehearsal passed without touching real serving. A fresh authenticated local API check still returned active Batch 20/208 and IDC 404. Four focused Batch 21 tests and all 413 backend tests passed; the frontend production build passed with its existing large-chunk warning. The active pointer remains SHA-256 `cac24ffdb3f4a795ee3c204bd48c096d31491b1874a7e34580c156eaa5a1e20f`.

The staged results and pre-activation checks above describe the historical state before the separately authorized local activation.

## Batch 21 local activation — 2026-09-25

- The pinned activation guard passed; `--activate` switched the local active pointer to the exact 218-entry Batch 21 catalog. Active pointer SHA-256 is `7d20dc192b2859f109f8400158592e7ce6cd33c4f19e3ccdf718f3dffac0fe0c`; Batch 21 manifest SHA-256 remains `eddf03189b851c60a4c8166de1cf8d57ad37ea7b0510791b152ae3e939a992a3`. Batch 20 rollback manifest SHA-256 remains `50227c8db032133bf191da95ba4f8b9de94b717dc423fa8b027607a9b061ea23`.
- The real authenticated active API returned 218/218 stored-detail parity, ten enabled new calculators, five inherited disabled calculators, LPC's edited PHP0.01002273174 base at 0.50× P/B and unauthenticated 401. Active Postgres/MinIO readback found ten receipts/objects, 30 facts, 30 assumptions and ten runs.
- Signed-in active PH browser showed 218 companies, LPC's calendar and calculator edit, global search to PHA, PHA's PHP-thousands warning, SPM's March period, SRDC's total-proxy warning and inherited PRIM blocked/null without a calculator. Current-build screenshots are under `output/pse-valuation-candidates/phase-b-batch-21-candidate-a/ui-*-active.png`.
- The live 218-record list initially timed out after 30 seconds because it revalidated the full catalog for every entry. The router now validates the catalog once per request while still hash-checking artifacts; an authenticated list returned 200 in 0.186 seconds. PH/US search requests were isolated so one failed market request does not erase the other's results. The final active browser flow passed; residual intermittent search behavior remains a monitor item.
- 114 focused Phase B tests and all 413 backend tests passed; the frontend production build passed with its existing large-chunk warning. The LPC small-value display-precision caveat remains disclosed. No deployment, push, blocked recovery or Batch 22 work occurred.

**Activation gate:** user-confirmed on 2026-09-25. Final read-only preflight found Batch 21 active/218 and the Batch 20 rollback intact; the active pointer, Batch 21 manifest, and Batch 20 manifest hashes remained exactly as pinned above. Fresh authenticated local HTTP returned Batch 21/218, IDC 200/market-relative-only and inherited PRIM 200/not-available. Wider PSE source-use rights, original-filing content lineage, specialist intrinsic underwrites, and LPC display precision remain unresolved. No deployment, push, blocked recovery, Batch 22 or Phase C work is implied.
