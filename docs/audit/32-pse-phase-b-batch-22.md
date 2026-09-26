# Audit 32 — PSE V2 Phase B Batch 22

**Status:** Frozen Batch 22 results were user-confirmed, then separately authorized for local activation on 2026-09-25. The 228-record Batch 22 catalog is locally active, live-verified, and user-confirmed; Batch 21 remains preserved for rollback. No deployment, push, blocked-issuer recovery or Batch 23 work occurred.

## Scope and source boundary

Confirmed set: `CSB, ORE, ECVC, GREEN, EGRN, ENEX, JAS, NI, WIN, PA`. All ten were absent from the active Batch 21 manifest. Reviewed PSE stock-data snapshots showed `Open` ordinary common at their dated observations; this is not a permanent listing guarantee. Each has an identifiable FY2025 and 1H2026 PSE financial-summary path. The pipeline stores hash-bound **reviewed fact receipts**, not downloaded original filings or webpage payloads. Original filing publication dates and page references were not established; PSE materials display a personal/non-commercial notice and broader rights remain unconfirmed. No current price or upside is published.

| Ticker | PSE financial summary | Stock data as of | Equity screen and key caution |
|---|---|---|---|
| CSB | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=228) | [Sep 24](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=228) | PHP1,466,087,430 total equity / 173,865,000 outstanding shares; parent field zero, so total book is a labeled proxy. |
| ORE | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=616) | [Sep 23](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=616&security_id=541) | PHP7,055,062,031 parent equity / 2,878,500,005 outstanding shares; book is not a reserve appraisal. |
| ECVC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=46) | [Sep 10](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=46&security_id=346) | PHP1,289,748,726 total equity / 6,630,000,000 outstanding shares; parent fields conflict and the listed count is far smaller. |
| GREEN | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=132) | [Sep 17](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=132) | PHP1,750,986,715 parent equity / 4,150,778,574 outstanding shares; printed BVPS does not reconcile to that bridge. |
| EGRN | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=191) | [Sep 25](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=191) | PHP3,567,426,561 parent equity / 25,000,000,000 outstanding shares; interim retained-earnings presentation needs follow-up. |
| ENEX | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=653) | [Sep 22](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=653) | PHP23,548,036 parent equity / 250,000,001 outstanding shares; no reported revenue or underwritten commercial reserves. |
| JAS | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=134) | [Sep 24](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=134) | PHP180,650,832 total equity / 250,059,097 outstanding shares; parent attribution unavailable, so a labeled total-book proxy. |
| NI | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=103) | [Sep 21](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=103) | PHP239,459,312 parent equity / 1,010,000,000 outstanding shares; zero revenue and no proven reserve value. |
| WIN | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=90) | [Sep 21](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=90) | PHP1,382,842,122 parent equity / 3,276,035,637 outstanding shares; falling interim sales and losses are not normalized cash flow. |
| PA | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=109) | [Sep 24](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=109) | PHP102,193,148 parent equity / 325,000,000 outstanding shares; no reported revenue. |

## Exact staged outputs

All ten new outputs are `market_relative_only`, `provisional`, Low reliability, in PHP per ordinary common share. Intrinsic bear/base/bull remain null. The finite bank 0.60/0.80/1.00×, layered-asset 0.25/0.40/0.55× and operating-book 0.30/0.50/0.70× bands are reused screening sensitivities, **not** peer-calibrated targets or completed intrinsic models. CSB, ECVC and JAS use explicitly labeled total-book proxies; the other seven use parent equity.

| Ticker | Low | Base | High | Basis |
|---|---:|---:|---:|---|
| CSB | 5.059399293 | 6.745865723 | 8.432332154 | Total proxy; bank book |
| ORE | 0.612737712 | 0.980380340 | 1.348022967 | Parent; resource book |
| ECVC | 0.048633059 | 0.077812894 | 0.106992730 | Total proxy; resource book |
| GREEN | 0.105461342 | 0.168738147 | 0.232014952 | Parent; layered book |
| EGRN | 0.035674266 | 0.057078825 | 0.078483384 | Parent; layered book |
| ENEX | 0.023548036 | 0.037676857 | 0.051805679 | Parent; energy book |
| JAS | 0.216729766 | 0.361216277 | 0.505702788 | Total proxy; operating book |
| NI | 0.059272107 | 0.094835371 | 0.130398635 | Parent; resource book |
| WIN | 0.126632516 | 0.211054194 | 0.295475872 | Parent; operating book |
| PA | 0.078610114 | 0.125776182 | 0.172942250 | Parent; layered book |

## Staged verification and historical release boundary

- Candidate `PSE-V2-PHASE-B-B22-2026-09-25-1.0` contains exactly 228 entries: 34 inherited intrinsic, 189 market-relative and 5 inherited unavailable; 223 provisional and 5 blocked (CDC, HOUSE, IS, PAX, PRIM). Manifest SHA-256 `f173bcc9b8854563f5bce9655c2f7c88e08187e9447ae115c1b012e5bb6c9f26`.
- Independent `Decimal` test arithmetic reproduced every reviewed equity/share bridge and low/base/high sensitivity. Deterministic twin builds matched; all 218 Batch 21 parent artifacts were byte-identical in the candidate. Four focused Batch 22 tests and all 417 backend tests passed; frontend production build passed with its existing large-chunk warning.
- Existing Postgres/MinIO readback verified ten current reviewed receipts/objects, 30 period-and-unit-scoped facts, 30 multiple assumptions, and ten staged runs. Receipts hash reviewed fact records, not original PSE filing content.
- Real staged authenticated HTTP returned exact 228/228 stored-detail parity, ten of ten enabled new calculators, five inherited disabled calculators, CSB edited to PHP8.432332154257614 at 1.00× P/B, and unauthenticated listing returned 401.
- Signed-in staged browser at `http://127.0.0.1:4002/pse/CSB` showed the 228-company footer, seven-day calendar, PHP6.75 default and PHP8.43 edited base; source links rendered. Calendar navigation, search to ORE, ORE's loss warning, ENEX's 1H2026 period, ECVC's parent-field warning and inherited PRIM blocked/null with no calculator passed. Current staged screenshots are under `output/pse-valuation-candidates/phase-b-batch-22-candidate-a/ui-*-staged.png`. The temporary browser test account was removed; readback found none remaining.
- At the staged gate, the real active local authenticated API still served Batch 21 with 218 records and CSB 404. Batch 22 was absent from active serving.
- At the staged gate, the active Batch 21 pointer SHA-256 was `7d20dc192b2859f109f8400158592e7ce6cd33c4f19e3ccdf718f3dffac0fe0c`; its manifest SHA-256 was `eddf03189b851c60a4c8166de1cf8d57ad37ea7b0510791b152ae3e939a992a3`.

**Results gate:** user-confirmed on 2026-09-25. The exact 228-entry manifest SHA-256 `f173bcc9b8854563f5bce9655c2f7c88e08187e9447ae115c1b012e5bb6c9f26` is pinned in `scripts/activate_pse_v2_phase_b_batch_22.py`. Its default read-only preflight checked the frozen issuer and blocked sets, status counts, 218 byte-identical inherited artifacts, ten receipt hashes, and the unchanged active Batch 21 pointer. An isolated temporary-root activation rehearsal passed without touching real serving; the expected future active-pointer hash is pinned. Fresh authenticated active HTTP still returned Batch 21/218 and CSB 404. Five focused Batch 22 tests, all 418 backend tests, and the frontend production build passed. The active pointer remains SHA-256 `7d20dc192b2859f109f8400158592e7ce6cd33c4f19e3ccdf718f3dffac0fe0c`.

The staged results and pre-activation checks above describe the historical state before separately authorized local activation.

## Batch 22 local activation — 2026-09-25

- The pinned activation guard passed; `--activate` switched the local active pointer to the exact 228-entry Batch 22 catalog. Active pointer SHA-256 is `8355c4838a6ff48ebdcb06d582570b391e9f29af6d2bcb29ce3a81ef3411f193`; Batch 22 manifest SHA-256 remains `f173bcc9b8854563f5bce9655c2f7c88e08187e9447ae115c1b012e5bb6c9f26`. Batch 21 rollback manifest SHA-256 remains `eddf03189b851c60a4c8166de1cf8d57ad37ea7b0510791b152ae3e939a992a3`.
- The real authenticated active API returned 228/228 stored-detail parity, ten enabled new calculators, five inherited disabled calculators, CSB's edited PHP8.432332154257614 base at 1.00× P/B, and unauthenticated 401. Active Postgres/MinIO readback found ten receipts/objects, 30 facts, 30 assumptions and ten runs.
- Signed-in active PH browser at `http://localhost:4000/pse/CSB` showed 228 companies, CSB's calendar and calculator edit, source links, global search to ORE, ORE's loss warning, ENEX's June period, ECVC's parent-field warning and inherited PRIM blocked/null without a calculator. Current-build screenshots are under `output/pse-valuation-candidates/phase-b-batch-22-candidate-a/ui-*-active.png`. The temporary browser test account was removed; readback found none remaining.
- Historical Batch builders and tests were updated to recognize the pinned Batch 22 successor while retaining exact earlier catalog hashes. All 119 focused Phase B/API tests and the full backend regression passed; the frontend production build passed with its existing large-chunk warning. No deployment, push, blocked recovery or Batch 23 work occurred.

**Activation gate:** user-confirmed on 2026-09-25. Final read-only preflight found Batch 22 active/228 and the Batch 21 rollback intact; the active pointer, Batch 22 manifest, and Batch 21 manifest hashes remained exactly as pinned above. Fresh authenticated local HTTP returned Batch 22/228, CSB 200/market-relative-only and inherited PRIM 200/not-available. Commercial-use source rights, original-filing content lineage, and specialist intrinsic underwrites remain unresolved. No deployment, push, blocked recovery, Batch 23 or Phase C work is implied.
