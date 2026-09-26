# Audit 41 — AP calculation candidate and RLC owner-bridge candidate

**Status:** Staged findings user-confirmed on 2026-09-26; calculations not approved or served. This workpaper answers the user-authorized AP FCFF rebuild and RLC property-by-owner reconciliation as far as the reviewed filings permit. It is **not** a Phase C refresh approval. The machine-readable [candidate workpaper](evidence/pse-phase-c-ap-rlc-candidate-workpaper.json) sits outside the valuation catalogs and is not a public artifact.

## AP — candidate calculation with explicit proxy ledger

The [FY2025 AP annual report](https://pdswordpressbucket.s3.ap-southeast-1.amazonaws.com/wp-content/uploads/2026/04/Disclosure-No.-1254-2026-Annual-Report-SEC-Form-17-A.pdf) and [1H2026 Form 17-Q](https://pdswordpressbucket.s3.ap-southeast-1.amazonaws.com/wp-content/uploads/2026/08/Disclosure-No.-2960-2026-Quarterly-Report-SEC-Form-17-Q.pdf) support a trailing-period cash bridge (PHP millions). The FY2025 file is available locally and hash-checked in [Audit 40](40-pse-ap-refresh-rlc-ownership-bridge.md); the 2026 original PDF is online-reviewed only, **not byte-hashed**. The 2026 17-Q's cash-flow statement and Note 8 distinguish operating cash, investing distributions, the nonrecurring CGHI preferred-share redemption, and new financing claims.

| Cash bridge | FY2025 | 1H2025 | 1H2026 | TTM 30 Jun 2026 |
|---|---:|---:|---:|---:|
| Operating cash flow | 51,722.480 | 21,889.383 | 20,674.210 | 50,507.307 |
| PPE + intangible cash additions | 28,501.353 | 9,260.562 | 10,282.498 | 29,523.289 |
| Cash after these additions | 23,221.127 | 12,628.821 | 10,391.712 | 20,984.018 |
| Financing-classified cash interest paid | 17,491.517 | 9,061.746 | 9,978.697 | 18,408.468 |

Formula: `TTM = FY2025 + 1H2026 − 1H2025`. **Illustrative** operating FCFF, *excluding equity-method investees*, is `cash after additions + cash interest × (1 − 25% tax-shield assumption)`: **PHP34,790.369m TTM** and **PHP36,339.765m FY2025**. The base starting FCFF below is their arithmetic midpoint **PHP35,565.067m**; bear uses TTM and bull FY2025. The 25% rate is a [general domestic-corporation rate](https://bir-cdn.bir.gov.ph/BIR/pdf/RR%207-2025.pdf), **not a verified AP blended marginal interest shield**. Actual project incentives, maintenance/growth capex, working-capital reversals and lease-interest classification may change it. Cash dividends from equity-method investees are **PHP11,528.280m TTM** and are *excluded* from this core FCFF; the **PHP29,480m CGHI redemption is nonrecurring and also excluded**. [Source: AP 1H2026 17-Q, PDF pp. 16 and 27–28.](https://pdswordpressbucket.s3.ap-southeast-1.amazonaws.com/wp-content/uploads/2026/08/Disclosure-No.-2960-2026-Quarterly-Report-SEC-Form-17-Q.pdf)

For a **calculation-only** equity bridge, the existing five-year reinvestment-aware [FCFF engine](../../backend/app/pse_valuation/models/fcff.py) uses the unchanged bear/base/bull operating, WACC and terminal policy from [pipeline.py](../../backend/app/pse_valuation/pipeline.py). It adds 30 June 2026 cash **PHP62,658.309m** and equity-method investments at their **PHP138,809.675m book-value proxy**, subtracts borrowings **plus leases PHP325,625.209m**, **PHP14,103.045m book NCI proxy**, and approximately **PHP3,900m outstanding CGHI contingent consideration**, then divides by **7,205.854307m shares**. The June 2026 [macro snapshot](../../backend/app/pse_valuation/config/macro_snapshot.json) has not been newly reviewed. Book investments and book NCI are **not fair values**. [Source: AP 1H2026 17-Q, PDF pp. 2, 11–12, 27–28, 41.](https://pdswordpressbucket.s3.ap-southeast-1.amazonaws.com/wp-content/uploads/2026/08/Disclosure-No.-2960-2026-Quarterly-Report-SEC-Form-17-Q.pdf)

| AP calculation-only scenario | Bear | Base | Bull |
|---|---:|---:|---:|
| Starting FCFF, PHPm | 34,790.369 | 35,565.067 | 36,339.765 |
| Enterprise value, PHPm | 332,133.852 | 447,969.512 | 622,507.686 |
| Common-equity value, PHPm | 189,973.582 | 305,809.242 | 480,347.416 |
| **Indicative PHP/share, not publishable** | **26.364** | **42.439** | **66.661** |

The candidate base is **45.6% above** the active AP base of PHP29.1547/share. Its PHPm common-equity bridge is:

| Change from active base | PHPm effect |
|---|---:|
| Core enterprise value, revised cash inputs | −30,669.865 |
| Cash and borrowings update, net | +5,649.403 |
| Add equity-method investment *book proxy* separately | +138,809.675 |
| Deduct book NCI and contingent claim proxies | −18,003.045 |
| **Net common-equity change** | **+95,786.168** |

The larger share count reduces the resulting per-share figure by another PHP0.0124 versus using the old count. This is the required **>20% change attribution**, not evidence that PHP42.439 is the right price. The central judgment is whether the JV book proxy and consolidated cash stream are economically disjoint and fairly valued. Neither that, the NCI economic claim, the tax shield, nor the normalized forecast is independently approved. Therefore the *publication candidate* remains **null**; these three numbers are an internal sensitivity only.

## RLC — owner and accounting-basis reconciliation

The [group FY2025 17-A](https://robinsonsland.com/sites/default/files/2026-04/RLC_SEC%2017-A_December%2031%202025.pdf) discloses investment-property carrying/fair values of **PHP143,427.865m / PHP447,175.302m** (uplift **PHP303,747.436m**, printed p. 270). The [parent-only 2025 statements in the issuer's definitive 20-IS](https://robinsonsland.com/sites/default/files/2026-04/Robinsons%20Land%20Corporation_%20SEC%20Form%2020-IS%20%28Definitive%20Information%20Statement%29%20Clean%20%28redacted%29_compressed.pdf) disclose parent investment-property carrying **PHP115,836.052m** and fair value **PHP319,521.030m** (uplift **PHP203,684.978m**, printed pp. 39–40). Subtracting these parent figures from the group totals gives a **diagnostic residual**: carrying **PHP27,591.813m**, fair value **PHP127,654.272m**, uplift **PHP100,062.459m**. This arithmetic residual is **not yet an identified subsidiary/property allocation**, because consolidated transfers and eliminations have not been mapped.

| Owner or scope at 31 Dec 2025 | Ownership | Disclosed property basis | What is still missing |
|---|---:|---|---|
| RLC parent direct | 100% | Standalone carrying PHP115,836.052m; appraised FV PHP319,521.030m | Confirmation that the exact parent property slice survives group consolidation unchanged |
| [RCR](https://rlcommercialreit.com.ph/sites/default/files/2026-03/RCR%20SEC%2017A%20122025_to%20file.pdf) | 60.51% | Standalone investment properties already carried at FV **PHP161,470.010m** | Asset-level *group-basis* carrying and FV after RLC/RCR eliminations |
| BRFLC; AAI; GDI | 70%; 51%; 51% | Ownership documented in [RLC's issuer subsidiary table](https://robinsonsland.com/sites/default/files/2026-04/Robinsons%20Land%20Corporation_%20SEC%20Form%2020-IS%20%28Definitive%20Information%20Statement%29%20Clean%20%28redacted%29_compressed.pdf) | Their property carrying/FV and any intercompany effects |
| Other consolidated subsidiaries | Mostly 100% | Included in group totals | Entity/property schedule |

The [RCR property-performance schedule](https://rlcommercialreit.com.ph/sites/default/files/2026-03/RL%20Commercial%20REIT%2C%20Inc._20-IS%20%28Definitive%20Information%20Statement%29_1.pdf) identifies individual RCR offices and malls with valuation amounts, but not each one's RLC-*consolidated* carrying base. Moreover, the [2025 nine-mall swap disclosure](https://rlcommercialreit.com.ph/sites/default/files/2025-07/RCR%20-%20SEC%20Form%2020-DIS.pdf) says the underlying **land was retained by RLC**, while buildings went to RCR; the [RLC parent cash-flow note](https://robinsonsland.com/sites/default/files/2026-04/Robinsons%20Land%20Corporation_%20SEC%20Form%2020-IS%20%28Preliminary%20Information%20Statement%29%20%20%28redacted%29%20%281%29.pdf) reports a **PHP30,675m subsidiary investment increase** against **PHP7,606m investment-property and PHP187m PPE book decreases** for that common-control swap. Those are transfer/accounting amounts, **not** the missing post-elimination group appraisal bridge. RCR's PHP161,470.010m standalone FV even exceeds the PHP127,654.272m group-less-parent *diagnostic residual* by PHP33,815.739m; that mismatch is why multiplying the whole uplift by 60.51% would be false precision.

At the active 50%-realization/20%-leakage base policy, **parent-only uplift** would add PHP81,473.991m to reported parent equity, giving a **PHP257,005.931m / PHP53.486/share partial subtotal**. This is **not a corrected RLC valuation, a lower bound, or a publishable price**: the parent slice's consolidation treatment is not yet certified, and the subsidiary uplift/claims are unallocated. The *full attributable uplift and publication candidate values remain null*. The active RLC provisional PHP61.8157/share is unchanged.

## Verification and gate

The AP TTM cash bridge and RLC parent/group residual were independently replayed with decimal arithmetic. The AP base FCFF was independently replayed from the engine's explicit five-year cash flows and reinvestment-aware terminal formula, matching **PHP42.4389987/share**; the RLC parent-only partial subtotal was separately replayed through the existing SOTP aggregator. The [candidate JSON](evidence/pse-phase-c-ap-rlc-candidate-workpaper.json) was syntax- and formula-checked against these source facts and has SHA-256 `3348138b35f99657055d0cd4c9706b906f2a22a09251d06411d7e931c836ca2a`. No independent analyst has approved the proxy valuation judgments. The 2026 AP and RLC/RCR online source PDFs were not captured and byte-hashed for immutable publication. The app was not running for API/UI verification; no public artifact was produced, so no live-serving claim is made.

**Decision:** Keep both active provisional valuations untouched. AP has an internal calculation sensitivity that needs source capture, accounting normalization and claim review; RLC has a stronger parent/subsidiary accounting bridge, but no full attributable RNAV. Do not approve either issuer or initiate Phase C automation from this workpaper. Stop at user review before any further source coordination or catalog change.

**Confirmation gate:** The user confirmed these staged workpaper findings on 2026-09-26. Read-only checks at confirmation found the candidate JSON SHA-256 still `3348138b35f99657055d0cd4c9706b906f2a22a09251d06411d7e931c836ca2a`, active-pointer SHA-256 still `50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92`, and Batch 28 manifest SHA-256 still `8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7`. This confirmation accepts the analysis only: AP's PHP42.439 base remains a calculation sensitivity, RLC's PHP53.486 remains a partial subtotal, and both publication candidates remain null. No issuer approval, activation, automation, deployment or next-stage source coordination follows from it.
