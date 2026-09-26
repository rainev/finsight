# Audit 33 — PSE V2 Phase B Batch 23

**Status:** Frozen Batch 23 results were user-confirmed, then separately authorized for local activation on 2026-09-25. The 238-record Batch 23 catalog is locally active, live-verified, and user-confirmed; Batch 22 remains preserved for rollback. No deployment, push, blocked recovery or Batch 24 work occurred.

## Frozen scope and source judgment

Confirmed set: `BC, CA, LC, ATN, OPM, FJP, DIZ, IMP, FERRO, ABG`. Each was absent from active Batch 22. Available dated PSE stock pages showed `Open` ordinary common at review time; that is not a perpetual listing guarantee. The pipeline stores hash-bound **reviewed fact receipts**, not downloaded original filing/page payloads. Source publication dates and filing page numbers were not fully established. The PSE site displays a personal/non-commercial notice; wider acquisition and redistribution rights remain unconfirmed. No market price or upside is published.

| Ticker | PSE financial summary | Reviewed accounting boundary |
|---|---|---|
| BC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=108) | Parent equity PHP10,982,048 thousand and A+B common shares reconcile near printed BVPS, but [convertible preferred shares](https://edge.pse.com.ph/downloadHtml.do?file_id=1942132) remain an unresolved common claim. Blocked/null. |
| CA | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=213) | Parent equity PHP313,390,546 / 27,466,449 reported combined common shares; [equal A/B dividend](https://edge.pse.com.ph/downloadHtml.do?file_id=1878408) and PHP11.41 BVPS support the denominator. Do not add a separate older B-page count again. |
| LC | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=98) | Parent equity PHP7,634,806 thousand / 66,375,758,097 pooled A+B common shares; reported PHP0.12 BVPS approximately reconciles. |
| ATN | [FY2026/June 2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=56) | March 31 fiscal year. Parent equity PHP2,568,247,205 / 6,825,055,429 pooled A+B common shares; reported PHP0.37 BVPS approximately reconciles. |
| OPM | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=43) | Parent equity is **USD84,487,332**, with 192,063,300,000 A+B common shares. No approved dated USD/PHP observation or independently underwritten reserve bridge was available; PHP valuation remains blocked/null. |
| FJP | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=225) | [A/B rights disclosure](https://edge.pse.com.ph/downloadHtml.do?file_id=1939673) says the common shares have equal rights. Parent equity PHP2,089,516,655 / 481,827,653 pooled shares is the explicit screen; printed PHP5.71 BVPS does **not** reconcile to that denominator. |
| DIZ | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=68) | Parent equity PHP25,892,569 / 79,087,487 outstanding common shares; no reported 1H2026 revenue or reserve appraisal. |
| IMP | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=201) | Parent equity PHP989,306,677 / 652,500,000 outstanding common shares, not 100m listed shares. Reported revenue is minimal. |
| FERRO | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=643) | Parent equity PHP157,514,702 / 341,824,002 current outstanding shares. A [property-for-share proposal](https://edge.pse.com.ph/downloadHtml.do?file_id=1636679) could materially alter this denominator; no pro-forma value is implied. |
| ABG | [FY2025/1H2026](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=176) | Parent-equity field is blank; PHP246,342,895 total equity / 300m shares is a labeled low-reliability proxy. Proposed future assets and current trading levels are not valued. |

## Exact staged outputs

Eight new records are `market_relative_only` and `provisional`, Low reliability, in PHP per ordinary common share. Intrinsic bear/base/bull remain null. Two new records, BC and OPM, are `not_available`/`blocked`: all valuation values and calculators are null/disabled. The finite operating 0.30/0.50/0.70× and layered asset 0.25/0.40/0.55× P/B bands are reused screening sensitivities, **not** peer-calibrated targets, completed SOTPs or DCFs.

| Ticker | Low | Base | High | Result |
|---|---:|---:|---:|---|
| BC | — | — | — | Blocked: convertible preferred common claim |
| CA | 3.422982119 | 5.704970198 | 7.986958278 | Combined-common operating book |
| LC | 0.028756003 | 0.046009605 | 0.063263207 | PHP-thousands, pooled A+B resource book |
| ATN | 0.094074225 | 0.150518760 | 0.206963295 | March-year, pooled A+B asset book |
| OPM | — | — | — | Blocked: USD-to-PHP and reserve bridge |
| FJP | 1.084161858 | 1.734658974 | 2.385156089 | Equal-rights A+B parent book, BVPS discrepancy |
| DIZ | 0.081847869 | 0.130956590 | 0.180065311 | Parent resource book |
| IMP | 0.379044704 | 0.606471526 | 0.833898348 | Parent asset book |
| FERRO | 0.115201610 | 0.184322577 | 0.253443543 | Current-share holding book; material dilution caveat |
| ABG | 0.205285746 | 0.328457193 | 0.451628641 | Total-book proxy; prospective assets excluded |

## Staged verification and historical release boundary

- Candidate `PSE-V2-PHASE-B-B23-2026-09-25-1.0` contains exactly 238 entries: 34 inherited intrinsic, 197 market-relative and 7 unavailable; 231 provisional and 7 blocked (BC, OPM, CDC, HOUSE, IS, PAX, PRIM). Manifest SHA-256 `84f33618d2cf063028ec0bac58e5742e1dbd0f51a595ed7f625a4d26ccbfe631`. All 228 Batch 22 parent artifacts are copied byte-identically.
- Independent `Decimal` tests reproduced the eight source-bounded PHP equity/share bridges and each finite low/base/high sensitivity. Null blocked values and disabled calculators passed focused tests. Deterministic twin builds matched. Four focused Batch 23 tests, all 422 backend tests and frontend production build passed (with existing non-blocking warnings).
- Existing Postgres/MinIO readback verified ten reviewed receipt objects, 35 original-period/source-class facts, ten separately labeled reviewed common denominators, 24 finite multiple assumptions and ten staged runs. Receipt hashes are **not** original filing-content hashes.
- Real staged authenticated HTTP returned exact 238/238 stored-detail parity, eight of ten enabled new calculators, BC/OPM and all five inherited blocked calculators disabled, CA edited to PHP6.845964238041838 at 0.60× P/B, and unauthenticated listing returned 401.
- Signed-in staged browser at `http://127.0.0.1:4003/pse/CA` showed the 238-company footer, seven-day calendar, PHP5.70 default and PHP6.85 edited base; three source links rendered. Search opened FJP and displayed its equal-rights warning; LC's PHP-thousands warning, ATN's March fiscal year, new BC/OPM blocked/null, and inherited PRIM blocked/null with no calculators passed. Current-build screenshots are under `output/pse-valuation-candidates/phase-b-batch-23-candidate-a/ui-*-staged.png`. The temporary browser test account was removed; readback found none remaining.
- At the staged gate, fresh authenticated active HTTP still returned Batch 22/228 and BC 404. Batch 23 was absent from active serving.
- At the staged gate, the active Batch 22 pointer SHA-256 was `8355c4838a6ff48ebdcb06d582570b391e9f29af6d2bcb29ce3a81ef3411f193`; its manifest SHA-256 was `f173bcc9b8854563f5bce9655c2f7c88e08187e9447ae115c1b012e5bb6c9f26`.

**Results gate:** user-confirmed on 2026-09-25. The exact 238-entry manifest SHA-256 `84f33618d2cf063028ec0bac58e5742e1dbd0f51a595ed7f625a4d26ccbfe631` is pinned in `scripts/activate_pse_v2_phase_b_batch_23.py`. Its default read-only preflight checked the frozen issuer and seven-name blocked sets, status counts, 228 byte-identical inherited artifacts, ten receipt hashes and the unchanged active Batch 22 pointer. An isolated temporary-root activation rehearsal passed without touching real serving; the expected future active-pointer hash is pinned. Fresh authenticated active HTTP still returned Batch 22/228 and BC 404. Five focused Batch 23 tests, all 423 backend tests, and the frontend production build passed. The active pointer remains SHA-256 `8355c4838a6ff48ebdcb06d582570b391e9f29af6d2bcb29ce3a81ef3411f193`.

The staged results and pre-activation checks above describe the historical state before separately authorized local activation.

## Batch 23 local activation — 2026-09-25

- The pinned activation guard passed; `--activate` switched the local active pointer to the exact 238-entry Batch 23 catalog. Active pointer SHA-256 is `5ad7fb97f37a443d025f09841bee2643222f201d1fbd6af527e8bf4c40ccd8c4`; Batch 23 manifest SHA-256 remains `84f33618d2cf063028ec0bac58e5742e1dbd0f51a595ed7f625a4d26ccbfe631`. Batch 22 rollback manifest SHA-256 remains `f173bcc9b8854563f5bce9655c2f7c88e08187e9447ae115c1b012e5bb6c9f26`.
- The real authenticated active API returned 238/238 stored-detail parity, eight enabled new calculators, BC/OPM and five inherited disabled calculators, CA's edited PHP6.845964238041838 base at 0.60× P/B, and unauthenticated 401. Active Postgres/MinIO readback found ten receipts/objects, 35 facts, ten reviewed class denominators, 24 multiple assumptions and ten runs.
- Signed-in active PH browser at `http://localhost:4000/pse/CA` showed 238 companies, CA's calendar and calculator edit, three source links, global search to FJP, FJP's equal-rights warning, LC's PHP-thousands warning, ATN's March fiscal year, new BC/OPM blocked/null and inherited PRIM blocked/null without calculators. Current-build screenshots are under `output/pse-valuation-candidates/phase-b-batch-23-candidate-a/ui-*-active.png`. The temporary browser test account was removed; readback found none remaining.
- Historical Batch builders and tests were updated to recognize the pinned Batch 23 successor while retaining exact earlier catalog hashes. All 124 focused Phase B/API tests and all 423 backend tests passed; the frontend production build passed with its existing large-chunk warning. No deployment, push, blocked recovery or Batch 24 work occurred.

**Activation gate:** user-confirmed on 2026-09-25. Final read-only preflight found Batch 23 active/238 and the Batch 22 rollback intact; the active pointer, Batch 23 manifest, and Batch 22 manifest hashes remained exactly as pinned above. Fresh authenticated local HTTP returned Batch 23/238, CA 200/market-relative-only, and BC and OPM 200/not-available. Original-filing content lineage, commercial-use source rights, approved USD/PHP and specialist intrinsic inputs remain unresolved. No deployment, push, blocked recovery, Batch 24 or Phase C work is implied.
