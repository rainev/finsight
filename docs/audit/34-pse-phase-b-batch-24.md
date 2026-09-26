# Audit 34 — PSE V2 Phase B Batch 24

**Status:** Frozen Batch 24 results were user-confirmed, then separately authorized for local activation on 2026-09-25. The 248-record Batch 24 catalog is locally active, live-verified and user-confirmed; Batch 23 remains preserved for rollback. No deployment, push, blocked recovery or Batch 25 work occurred.

## Frozen scope and source boundary

Confirmed set: `AB, FPI, FAF, BH, GEO, UPM, MA, X, MFC, SLF`. All ten were absent from active Batch 23. Dated PSE stock-data snapshots showed `Open` ordinary common; recheck on refresh rather than treating a company page as perpetual listing proof. Reviewed FY2025 and 1H2026 PSE summary paths are identifiable. The pipeline stores hash-bound **reviewed fact receipts**, not downloaded original filing/page payloads. Original publication dates and page numbers were not fully established. PSE materials display a personal/non-commercial notice; wider acquisition and redistribution rights remain unconfirmed. No current market price or upside is published.

| Ticker | PSE financial summary | Reviewed equity/claim boundary |
|---|---|---|
| AB | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=19) | Parent equity **negative PHP390,230,168** while total equity and reported BVPS are positive; common residual cannot be inferred from total book. Blocked/null. |
| FPI | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=220) | PHP261,653,330 parent equity / 1,838,943,246 outstanding common shares. Printed PHP0.22 BVPS does not reconcile to this parent/share bridge. |
| FAF | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=81) | Parent equity **negative PHP684,615,700** despite PHP20.009m positive total equity. Blocked/null. |
| BH | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=62) | PHP87,100,779 parent equity / 499,987 outstanding common shares, not 20,000 listed shares. Printed PHP199 BVPS follows total equity; trading is exceptionally thin. |
| GEO | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=198) | Parent equity only PHP325,798 / 3.5bn shares and zero revenue; printed BVPS rounds to zero. A microscopic positive book number would be economically misleading. Blocked/null. |
| UPM | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=168) | Parent equity **negative PHP336,437,679**, with a [proposed 40bn-share debt conversion](https://edge.pse.com.ph/downloadHtml.do?file_id=1861941). Current and pro-forma common claims unresolved. Blocked/null. |
| MA | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=119) | PHP3,360,556,712 parent equity / 311,504,146,443 pooled A+B outstanding common shares; printed PHP0.01 BVPS approximately reconciles only when both classes are included. |
| X | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=656) | Parent equity **negative PHP213,213,964**, persistent losses and a [recovery plan](https://edge.pse.com.ph/downloadHtml.do?file_id=1966030) needing common-capital reconciliation. Blocked/null. |
| MFC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=120) | Equity reported as C$52,324 **millions** with parent attribution blank. Approved dated CAD/PHP and insurer common claims are missing. Blocked/null. |
| SLF | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=78) | Equity reported as C$25,765 **millions** with parent attribution blank. Approved dated CAD/PHP and insurer common claims are missing. Blocked/null. |

## Exact staged outputs

Three new records are `market_relative_only` and `provisional`, Low reliability, in PHP per ordinary common share. Intrinsic bear/base/bull remain null. Seven new records are `not_available`/`blocked`, with null values and disabled calculators. The finite 0.25/0.40/0.55× P/B band is a reused screening sensitivity, **not** a peer-calibrated target or completed intrinsic model.

| Ticker | Low | Base | High | Result |
|---|---:|---:|---:|---|
| AB | — | — | — | Blocked: negative parent-common bridge |
| FPI | 0.035571154 | 0.056913846 | 0.078256538 | Parent book; BVPS discrepancy |
| FAF | — | — | — | Blocked: negative parent equity |
| BH | 43.551521840 | 69.682434943 | 95.813348047 | Parent book; thin trading and minority caveat |
| GEO | — | — | — | Blocked: near-exhausted equity, zero revenue |
| UPM | — | — | — | Blocked: negative equity, pending dilution |
| MA | 0.002697040 | 0.004315264 | 0.005933488 | Pooled A+B common book |
| X | — | — | — | Blocked: negative equity/recovery plan |
| MFC | — | — | — | Blocked: CAD/PHP and insurer claims |
| SLF | — | — | — | Blocked: CAD/PHP and insurer claims |

## Staged verification and historical release boundary

- Candidate `PSE-V2-PHASE-B-B24-2026-09-25-1.0` contains exactly 248 entries: 34 inherited intrinsic, 200 market-relative and 14 unavailable; 234 provisional and 14 blocked. Manifest SHA-256 `89b78a2fa1597a5b4d8cfd1e606f567554be18c222d7c782bc02a5879fc27ef0`. All 238 Batch 23 parent artifacts are copied byte-identically.
- Independent `Decimal` tests reproduced the three positive PHP parent/common bridges and each finite low/base/high sensitivity. Null blocked values, wrong class denominators, missing CAD/PHP and disabled calculators passed focused tests. Deterministic twin builds matched. Four focused Batch 24 tests, all 427 backend tests and frontend production build passed (with existing non-blocking warnings).
- Existing Postgres/MinIO readback verified ten reviewed receipt objects, 31 dated source facts, ten separately labeled reviewed denominators, nine finite multiple assumptions and ten staged runs. Receipt hashes are **not** original filing-content hashes.
- Real staged authenticated HTTP returned exact 248/248 stored-detail parity **against the corrected final manifest**, three of ten enabled new calculators, seven new plus seven inherited disabled calculators, BH edited to PHP87.10304367913565 at 0.50× P/B, and unauthenticated listing returned 401.
- Signed-in staged browser at `http://127.0.0.1:4004/pse/BH` showed the 248-company footer, seven-day calendar, PHP69.68 default and PHP87.10 edited base; source links rendered. Search opened MA and displayed its pooled A+B warning; FPI rendered a separate market-relative screen; representative AB/MFC and inherited BC blocked/null states had no calculator. Current-build screenshots are under `output/pse-valuation-candidates/phase-b-batch-24-candidate-a/ui-*-staged.png`. The temporary browser test accounts were removed; readback found none remaining. Seven new and seven inherited blocked calculators were separately checked through authenticated HTTP.
- At the staged gate, active Batch 23 pointer SHA-256 was `5ad7fb97f37a443d025f09841bee2643222f201d1fbd6af527e8bf4c40ccd8c4`; its manifest SHA-256 was `84f33618d2cf063028ec0bac58e5742e1dbd0f51a595ed7f625a4d26ccbfe631`.

**Results gate:** user-confirmed on 2026-09-25. The exact 248-entry manifest SHA-256 `89b78a2fa1597a5b4d8cfd1e606f567554be18c222d7c782bc02a5879fc27ef0` is pinned in `scripts/activate_pse_v2_phase_b_batch_24.py`. Its default read-only preflight checked the frozen issuer and 14-name blocked sets, status counts, 238 byte-identical inherited artifacts, ten receipt hashes and the unchanged active Batch 23 pointer. An isolated temporary-root activation rehearsal passed without touching real serving; the expected future active-pointer hash is pinned. Fresh authenticated active HTTP still returned Batch 23/238 and AB 404. Five focused Batch 24 tests, all 428 backend tests and the frontend production build passed. The active pointer remains SHA-256 `5ad7fb97f37a443d025f09841bee2643222f201d1fbd6af527e8bf4c40ccd8c4`.

The staged results and pre-activation checks above describe the historical state before separately authorized local activation.

## Batch 24 local activation — 2026-09-25

- The pinned activation guard passed; `--activate` switched the local active pointer to the exact 248-entry Batch 24 catalog. Active pointer SHA-256 is `f3afe66297cf939e595bbcfc12ae7fb2c6b2ee19ca4851e0dbd2485a1dc67e53`; Batch 24 manifest SHA-256 remains `89b78a2fa1597a5b4d8cfd1e606f567554be18c222d7c782bc02a5879fc27ef0`. Batch 23 rollback manifest SHA-256 remains `84f33618d2cf063028ec0bac58e5742e1dbd0f51a595ed7f625a4d26ccbfe631`.
- The real authenticated active API returned 248/248 stored-detail parity, three enabled new calculators, seven new plus seven inherited disabled calculators, BH's edited PHP87.10304367913565 base at 0.50× P/B, and unauthenticated 401. Active Postgres/MinIO readback found ten receipts/objects, 31 facts, ten reviewed share denominators, nine multiple assumptions and ten runs.
- Signed-in active PH browser at `http://localhost:4000/pse/BH` showed 248 companies, BH's calendar and calculator edit, source links, global search to MA, MA's A+B common warning, FPI's separate market-relative screen, representative AB/MFC blocked/null and inherited BC blocked/null without calculators. Current-build screenshots are under `output/pse-valuation-candidates/phase-b-batch-24-candidate-a/ui-*-active.png`. The temporary browser test account was removed; readback found none remaining.
- Historical Batch builders and tests were updated to recognize the pinned Batch 24 successor while retaining exact earlier catalog hashes. All 129 focused Phase B/API tests and all 428 backend tests passed; the frontend production build passed with its existing large-chunk warning. No deployment, push, blocked recovery or Batch 25 work occurred.

**Activation gate:** locally active, live-verified and separately user-confirmed on 2026-09-25. Final read-only preflight found the exact Batch 24/248 manifest active, with active pointer SHA-256 `f3afe66297cf939e595bbcfc12ae7fb2c6b2ee19ca4851e0dbd2485a1dc67e53` and unchanged Batch 23 rollback manifest SHA-256 `84f33618d2cf063028ec0bac58e5742e1dbd0f51a595ed7f625a4d26ccbfe631`. Fresh authenticated active HTTP returned Batch 24/248, BH `market_relative_only` and MFC `not_available`. No deployment, push, blocked recovery, Batch 25 or Phase C work is implied. Original-filing content lineage, commercial-use source rights, approved CAD/PHP and specialist insurer/resource inputs remain unresolved.
