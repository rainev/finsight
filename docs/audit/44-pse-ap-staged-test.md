# Audit 44 — AP supervised staged test

**Status:** Isolated AP test staged and verified for arithmetic, catalog integrity, and authenticated read API. **Not approved, not active, not calculator-parity clean, and not deployed.** RLC was excluded and remains pending a consolidation-level property bridge. The test used the three proxy choices user-confirmed in [Audit 43](43-pse-ap-proxy-recommendations.md); it did not alter those choices or any existing serving artifact.

## Staged result — calculation only

The existing five-year reinvestment-aware FCFF engine ran on the confirmed [proxy receipt](evidence/pse-ap-proxy-recommendations-2026-09-26.json), with [AP's original 1H2026 filing](https://pdswordpressbucket.s3.ap-southeast-1.amazonaws.com/wp-content/uploads/2026/08/Disclosure-No.-2960-2026-Quarterly-Report-SEC-Form-17-Q.pdf) and the local FY2025 original byte-checked against their pinned SHA-256 hashes. The source periods are FY2025 plus 1H2026 less 1H2025 (TTM to June 2026), not a current market-price estimate.

| Scenario | Enterprise value, PHPm | AP common equity, PHPm | AP value/share |
|---|---:|---:|---:|
| Bear | 332,133.852 | 182,204.052 | **PHP25.286** |
| Base | 447,969.512 | 298,039.712 | **PHP41.361** |
| Bull | 622,507.686 | 472,577.886 | **PHP65.582** |

The derived numeric range is **PHP25.286–65.582/share**; the base is the calculation headline **only inside this test**. It is **41.9% above** the still-active AP base of PHP29.155/share. The difference is largely the separate **PHP138,809.675m equity-method investment book proxy** (PHP19.263/share before other changes), with refreshed cash/debt/shares, operating cash inputs, a **25% assumed interest tax shield**, and a **PHP21,872.575m zero-growth cash-distribution minority proxy**. The existing June macro/WACC and ROIC/terminal cases were retained. This attribution explains the jump but **does not validate those economic proxies**. No dated price was supplied; there is no current-upside claim.

## Isolated catalog and test evidence

The output is a **one-issuer, non-serving** [staged catalog](evidence/pse-ap-staged-test-2026-09-26/PSE-V2-AP-SUPERVISED-2026-09-26-1.0/manifest.json) with exact issuer set `{AP}`, one `intrinsic_valuation` and one `provisional` status; there are zero `approved` entries. The [AP artifact](evidence/pse-ap-staged-test-2026-09-26/PSE-V2-AP-SUPERVISED-2026-09-26-1.0/artifacts/AP.json) has source references, all three scenario labels, the full capital bridge, warnings, an input hash and an internal artifact hash. It is outside `backend/app/data/pse_valuation_catalogs/`.

| Check | Observed result |
|---|---|
| Source pins | AP 1H2026 SHA-256 `0ea6d0d9fed540408f05c2ea8e6fb0c12fb691ee240aaf431e1f5fd3f6c24b80` and local FY2025 SHA-256 `f1985fdc43ca7e8111d7915c9c3300ef2ca676922b43619b5659f8aface6f60b` verified before output. A deliberately wrong 2026 source failed closed with `AP 1H2026 filing bytes differ from the reviewed original`. |
| Deterministic twins | Two independent builds and the staged output had identical pointer SHA-256 `34ef7f604ae3e9d927b52b140ca154e43e7bc5c3fca64c3566964c1fcc8c5f88`, manifest SHA-256 `1988b45dd71f3edc3dbddeb382f17506bce8ce150721964a37b293d15b920436`, and AP file SHA-256 `b002be6d1cc26df44e6ba574d65bb7a9af0b316634524962a24e9a8dcdf01fa0`. Internal artifact hash `62f095a445f2c7f3e010b1d1fc82e0f0925afba2bef1c91fb63b4c890a04e7f2` verified. |
| Independent calculation | Decimal replay of all three scenarios agreed with stored per-share values within `1e-8`; the base replay was PHP41.36077402036424. |
| Focused regression | **25 passed**, one existing `passlib`/`crypt` deprecation warning, across PSE model, contract and API tests. No production-code change was made. |
| Authenticated isolated HTTP route | Without a bearer token: **401**. With a test token and the isolated staged pointer: `GET /api/pse-valuations` returned **1/1 AP**, `catalog_status=staged`, base **PHP41.36077402036423**; `GET /api/pse-valuations/AP` matched the stored artifact; `GET /api/pse-valuations/RLC` returned **404**. This was an in-process FastAPI test, not a live app-server/UI run. |
| Unchanged active route | A separate authenticated in-process read against the default pointer still returned **282/282 active**, AP base **PHP29.154683615845205** and RLC base **PHP61.81569315623288**. The isolated stage did not replace serving data. |

**Real-flow gap — calculator parity:** The existing AP interactive calculator assumes **one** starting FCFF input for every scenario, but this confirmed staged test uses **PHP34,790.369m / 35,565.066875m / 36,339.76475m** for bear/base/bull. With *no user overrides*, the isolated calculator returned **PHP26.312 / 41.361 / 63.741**, versus the catalog's **PHP25.286 / 41.361 / 65.582**. Base matches; bear is **PHP1.026 higher** and bull **PHP1.842 lower**. This is an actual route-level discrepancy, not a failed arithmetic check. The artifact explicitly warns about it. **Do not attach this catalog to the visible PSE flow.** The simpler next design choice is one reviewed starting FCFF shared across all scenarios, leaving scenario growth/ROIC/WACC/terminal assumptions to vary; alternatively the calculator would need explicit scenario-specific FCFF support. Neither change was made here.

## Remaining decision boundary

The stage is useful for comparing AP cases, but source rights for durable filing storage/public display, analyst normalization of FCFF, fair value of the JV stakes and minority claim, other capital claims, and a fresh approved macro/discount case remain open. The observed **41.9%** change also requires economic attribution before any approval; the table above is a preliminary attribution only. The active 282-entry Batch 28 pointer SHA-256 remains `50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92`, and its manifest remains `8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7`. RLC stays at its earlier provisional result with no revised attributable RNAV. **Stop for the user's review of these staged results; no approval, activation, scheduler or next issuer is implied.**
