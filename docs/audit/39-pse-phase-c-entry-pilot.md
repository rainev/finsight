# Audit 39 — PSE V2 supervised approval and refresh pilot

**Status:** Staged findings user-confirmed on 2026-09-26. Scope is exactly `AP, BPI, RLC, RCR` against the user-approved Phase C entry test. No artifact, publication state, active pointer, database record, automation, or price feed was changed. This confirms the audit findings, **not** an issuer approval or a completed valuation refresh.

## Reference and current flow

The V2 plan allows controlled refresh automation only after each major template has an approved issuer and the pilot survives a real filing refresh. It also requires reviewed source access/rights, dated macro observations, immutable staging, and attribution for material changes. The [active Batch 28 catalog](../plans/PSE-SECTOR-VALUATION-PIPELINE-V2.md) has 282 records, including 34 intrinsic, 205 market-relative and 43 unavailable, but **zero approved**. The four selected intrinsic outputs are all `provisional`. Their served values and status were read back from the authenticated local API on 2026-09-26; the active manifest and pointer hashes remain `8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7` and `50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92`.

The existing reusable FCFF, residual-income, SOTP and distribution engines already reproduce these four bases. This pilot needs reviewed facts and accounting judgment, not another engine or scheduler. The path a user sees is source reference → reviewed receipt/assumption → engine → immutable artifact → authenticated API/UI. AP's eight public source entries have null URLs/page references; BPI and RCR each expose only one PSE-summary link even where issuer reports substantiate model inputs. RLC exposes the issuer annual-report PDF and p. 270, but the material ownership bridge is not represented in its RNAV inputs.

## Mechanical reconciliation, not economic approval

Independent `Decimal` replay from the published inputs and model formulas produced the following PHP/share bases; the live API returned the artifact values shown. This proves arithmetic reproducibility **only**.

| Route | Issuer | Independent replay | Active artifact/API | Source check |
|---|---|---:|---:|---|
| FCFF DCF | AP | 29.154683615845210 | 29.154683615845205 | FY2025 seed/proxy and five-year reinvestment-aware formula; [2026 2Q 17-Q](https://pdswordpressbucket.s3.ap-southeast-1.amazonaws.com/wp-content/uploads/2026/08/Disclosure-No.-2960-2026-Quarterly-Report-SEC-Form-17-Q.pdf) is a newer, separate filing. |
| Residual income | BPI | 98.438297761013089 | 98.43829776101308 | [FY2025 PSE summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=234) and [issuer 2025 17-A](https://www.bpi.com.ph/content/dam/bpi/documents/english/about-bpi/disclosures/sec-filings/sec-form-17-a-archive/2025%20BPI%20SEC%20Form%2017A.pdf). |
| Property SOTP/RNAV | RLC | 61.815693156232875 | 61.81569315623288 | [Issuer FY2025 17-A, investment-property note](https://robinsonsland.com/sites/default/files/2026-04/RLC_SEC%2017-A_December%2031%202025.pdf) and [PSE summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=195). |
| Sustainable distributions | RCR | 5.146705882352941 | 5.146705882352937 | [Issuer 4Q2025 fund-management report](https://rlcommercialreit.com.ph/sites/default/files/2026-02/2025_4Q%20RCR%20FM.pdf) and [PSE summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=684). |

### AP — supervised filing-refresh rehearsal

✔ A genuinely newer original [SEC Form 17-Q for 1H2026](https://pdswordpressbucket.s3.ap-southeast-1.amazonaws.com/wp-content/uploads/2026/08/Disclosure-No.-2960-2026-Quarterly-Report-SEC-Form-17-Q.pdf), dated 14 August 2026, was located and its relevant cash-flow lines checked against the PSE [1H2026 financial summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=609). The filing reports 1H2026 operating cash flow PHP20,674.210m, PPE additions PHP9,799.559m and intangible additions PHP482.939m. The simple **diagnostic** cash remainder after these additions is PHP10,391.712m, versus PHP12,628.821m for 1H2025 (−17.7%). This is **not FCFF**: interest is classified in financing, and taxes, associate cash flows, minority claims and project timing require a separate bridge. The 2026 filing reports 7,205,854,307 common shares, versus the model's FY2025 seed denominator of 7,203,750,741 (+0.0292%). The PSE summary reports 1H2026 parent equity PHP206.536bn versus total equity PHP220.639bn.

✔ The active model still starts from an analyst-normalized PHP38,000m FCFF proxy and FY2025 cash/debt/shares in [pipeline.py](../../backend/app/pse_valuation/pipeline.py) and [financials_data.json](../../backend/app/seed/financials_data.json); its consolidated FCFF-to-common bridge does not supply an attributable minority-value deduction. The new filing was **not** turned into a reviewed forecast, updated macro/capital bridge, byte-hashed new source record or staged refreshed artifact. All eight pilot artifact hashes in Batch 1 still match Batch 28. Thus this is a **partial source refresh rehearsal, not the plan's completed real pilot valuation refresh**.

### BPI — source-true book and return, pending approval judgments

✔ The [2025 issuer 17-A](https://www.bpi.com.ph/content/dam/bpi/documents/english/about-bpi/disclosures/sec-filings/sec-form-17-a-archive/2025%20BPI%20SEC%20Form%2017A.pdf) supports PHP476,553m year-end parent equity, PHP430,469m prior-year parent equity, PHP66,615m FY2025 income attributable to parent, and 5,283,794,223 FY2025 year-end common shares. The model's endpoint-average ROE is exactly `66,615 / ((476,553 + 430,469) / 2) = 14.6887%`. The issuer's separate daily-average-equity ROE disclosure is about **14.54%**; this is a method difference, not a calculation failure. The [PSE stock page](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=234) shows 5,296,362,773 outstanding as of 25 September 2026 (+0.2379%), while the model infers a FY2025 denominator from rounded PHP90.19 book value per share. Its 12.052% base cost of equity and regulatory-capital/asset-quality case still need reviewer judgment.

### RLC — property uplift needs attributable ownership

✔ The [issuer FY2025 annual-report note](https://robinsonsland.com/sites/default/files/2026-04/RLC_SEC%2017-A_December%2031%202025.pdf) reports PHP143.428bn investment-property carrying value and PHP447.175bn **Level 3** fair value, an uplift of PHP303.747bn. The model's base policy realizes 50% after 20% leakage: PHP121.499bn, or **40.9% of its PHP297.031bn modeled common-equity base**. [RLC's issuer release](https://robinsonsland.com/stories/robinsons-land-delivers-solid-2025-performance-double-digit-growth-revenue-ebitda-and-ebit) says RLC owned 60.51% of listed RCR at FY2025 end. Yet [phase_b_batch_03.py](../../backend/app/pse_valuation/phase_b_batch_03.py) applies **100% ownership** to the consolidated property fair-value uplift added to parent equity. The source check establishes an attribution risk, not an exact overstatement: the uplift must be separated by underlying asset/owner before a corrected common value can be quantified. RLC and RCR are overlapping listed interests, not additive valuations.

### RCR — distribution amount confirmed, share base changed

✔ The [issuer 4Q2025 fund-management report](https://rlcommercialreit.com.ph/sites/default/files/2026-02/2025_4Q%20RCR%20FM.pdf) reports quarterly dividends PHP0.1047 + 0.1049 + 0.1060 + 0.1112 = **PHP0.4268/share**, the model input. It also shows 19,548,803,008 shares by 4Q2025. The [2Q2026 PSE dividend notice](https://edge.pse.com.ph/downloadHtml.do?file_id=1955573) and [current PSE stock page](https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id=684) show PHP0.1117/share for 2Q2026 and 20,836,365,310 outstanding shares (+6.5864%). The model's 2.5% ongoing growth and 11% cost of equity are policy judgments, and the public artifact links only the PSE financial-summary receipt—not the fund-management report that supports PHP0.4268. A post-infusion, per-share distributable-income and ownership check is needed before approval.

## Gap register — this one supervised batch

`✔` means directly checked against the current artifact/code, live API, or linked primary source. `⚠` is not established and is not treated as an approval fact. P0 blocks the Phase C entry test or an issuer approval; P1 is a material review gap; P2 is a smaller source/display precision issue.

| ID | Severity | Verification | Concrete delta from approval/refresh target |
|---|---|---|---|
| C-01 | P0 | ✔ | AP has a newer filing, but no complete reviewed 1H2026 FCFF, attributable minority/capital bridge, approved assumptions, source hash and refreshed immutable artifact. The pilot has **not survived a real valuation refresh**. |
| C-02 | P0 | ✔ | RLC's RNAV applies the entire group property uplift at ownership 1.0 despite a partly owned RCR; attributable property-by-property uplift is not reconciled. |
| C-03 | P0 | ✔ | All 282 catalog records, including the four reviewed, remain `provisional` or `blocked`: **zero reviewer-approved issuers**. The major-template approval requirement is unmet. |
| C-04 | P1 | ✔ | BPI's endpoint-average ROE differs from its reported daily-average ROE; FY2025 versus September 2026 share denominators and bank capital/asset quality need sign-off before a current common-equity approval. |
| C-05 | P1 | ✔ | RCR's FY2025 distribution source is correct, but the 2026 share base is 6.6% larger, sustaining the per-share payout needs review, and the distribution source is absent from the public artifact's source list. |
| C-06 | P1 | ✔ | The shared [macro snapshot](../../backend/app/pse_valuation/config/macro_snapshot.json) is dated 23 June 2026 and marked `reviewed_for_pilot`, not a current reviewer-approved September benchmark. A carry-forward decision must be explicit. |
| C-07 | P0 for automation | ✔ local record / ⚠ external right | Existing audits record no confirmed commercial-use, automated-acquisition, storage or public-display permission for the PSE source set. This is a **missing recorded rights clearance**, not a legal conclusion about what PSE permits. No automated acquisition or licensed-price refresh should be inferred. |
| C-08 | P2 | ✔ | AP's public sources lack usable URLs/page references; BPI/RCR's public source list does not expose the primary issuer reports used in this review. The reader cannot fully traverse claim → source from the current detail screen. |

## Staged decision

**Do not promote any of these four to `approved` in this pilot.** Their published numerical outputs remain mechanically reproducible but provisional. The AP 1H2026 source review is useful, yet is **not** a refreshed valuation; the Phase C entry condition remains unmet. No active/staged catalog, model input, Postgres/MinIO object, approval record, scheduler or deployment was changed by this audit. Source PDFs were read online for facts; extraction/visual inspection of every relevant original page was not completed, so no original-file byte/content hash is claimed for the new AP filing. Human accounting judgment and rights confirmation remain necessary before an approval or automation request.

**Next decision for the user:** whether to authorize a separately scoped, supervised AP full refresh and RLC attribution reconciliation, while BPI/RCR return/capital and distribution/share bases receive reviewer sign-off. Stop again at a findings/approval gate; no automatic publication or Phase C scheduler.

**Confirmation gate:** The user confirmed these staged findings on 2026-09-26. Final read-only checks still found Batch 28/282 active, with manifest SHA-256 `8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7` and active-pointer SHA-256 `50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92`. This confirmation authorizes no approval-state change, refresh implementation, source-rights assumption, deployment, or Phase C automation.
