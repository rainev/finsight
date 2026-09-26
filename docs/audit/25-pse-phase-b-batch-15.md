# Audit 25 — PSE V2 Phase B Batch 15

**Status:** Batch 15 staged results were user-confirmed on 2026-09-23. The separately authorized local activation was live-verified and user-confirmed on 2026-09-24. Batch 14 is preserved for rollback. HOUSE remains blocked/delisted.

## Reference and current state

The confirmed set is `ALCO, ALHI, APVI, CEI, ELI, GERI, HOUSE, KPPI, PRMX, SLI`. Reuse the Batch 12 source-bounded property policy and immutable-catalog contract rather than creating another intrinsic engine. Property-level RNAV/SOTP remains the intrinsic route; a reported-book P/B result is a separately labeled, Low-reliability market-relative screen.

| Ticker | Firsthand PSE financial-summary source | Latest reviewed reported BVPS, PHP/share | Period and source caveat |
|---|---|---:|---|
| ALCO | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=172) | 1.21 | 2026-03-31 on summary; [later June 17-Q](https://edge.pse.com.ph/downloadHtml.do?file_id=1958227) requires period reconciliation; multiple preferred classes. |
| ALHI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=612) | 11.48 | 2026-06-30; large movement from FY2025 BVPS 8.69 and preferred capital claims require review. |
| APVI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=678) | 11.62 | 2026-06-30; [JGS-related property](https://edge.pse.com.ph/companyInformation/form.do?cmpy_id=678), so parent/subsidiary screens are non-additive. |
| CEI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=186) | 0.15 | 2026-06-30; [property and healthcare mix](https://edge.pse.com.ph/companyInformation/form.do?cmpy_id=186) needs component review. |
| ELI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=190) | 2.02 | 2026-06-30; [MEG-related](https://edge.pse.com.ph/companyInformation/form.do?cmpy_id=190), non-additive with parent. |
| GERI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=193) | 3.98 | 2026-06-30; [MEG-related](https://edge.pse.com.ph/companyInformation/form.do?cmpy_id=193), non-additive with parent. |
| HOUSE | [PSE historical summary](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=626) | 10.23 | Only 2025-06-30 interim source; [PSE delisted common shares effective 2025-10-31](https://edge.pse.com.ph/downloadHtml.do?file_id=1827603). Not eligible for a current listed-common valuation. |
| KPPI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=672) | 4.26 | 2026-06-30; [single Cebu office-property portfolio](https://edge.pse.com.ph/companyInformation/form.do?cmpy_id=672) needs rental/NAV review. |
| PRMX | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=214) | 0.86 | 2026-06-30; parent-equity basis differs between annual/interim columns, and project cash flows need review. |
| SLI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=41) | 4.00 | 2026-06-30; reported issued/treasury share bridge needs review before intrinsic per-share value. |

The PSE pages are manually reviewed source summaries, not original filing copies. Their notice limits access/download to personal, non-commercial use unless otherwise stated. Preserve a local, hash-bound reviewed-fact receipt and official link; do not automatically acquire or redistribute remote pages.

## One-batch gap register

| ID | Severity | Check | Gap and intended treatment |
|---|---|---|---|
| B15-01 | P0 | ✔ Active manifest and frozen list | No Batch 15 config, exact-set guard, source receipts, or 158-entry candidate exists. Build beside the active serving root and byte-preserve all 148 Batch 14 artifacts. |
| B15-02 | P0 | ✔ [PSE delisting notice](https://edge.pse.com.ph/downloadHtml.do?file_id=1827603) versus historical HOUSE summary | HOUSE was delisted before the valuation date. Keep it in the exact confirmed set as `not_available`/`blocked`, with null values and explicit reason; do not replace the issuer or use stale BVPS as a current price screen. |
| B15-03 | P1 | ✔ PSE financial summaries and Batch 12 property model | Nine issuers have positive, source-period-bound reported BVPS, but no completed property-level RNAV, lease/project cash flows, minority, tax, debt, or common-claim bridge. Reuse the separately labeled provisional P/B screen; intrinsic scenarios stay null. |
| B15-04 | P1 | ✔ ALCO/ALHI filings and PSE summary periods | ALCO's summary ends March while a June filing appears separately; ALHI's interim BVPS moves materially. Preserve actual source period and expose warnings; do not silently relabel ALCO's March fact as June or interpret ALHI's change as recurring operating value. |
| B15-05 | P1 | ✔ PSE company information | ELI/GERI overlap MEG, APVI overlaps JGS, and ALCO/ALHI have preferred capital claims. Their per-share screens are not additive to parent screens; common-equity intrinsic bridges remain unresolved. |
| B15-06 | P1 | ✔ PSE source notices | Broader-use rights, original publication dates and source pages are not established by the summary interface. Store reviewed local receipts and links only; production or automated acquisition remains outside this batch. |

## Reuse and gated flow

Reuse Batch 12's market-relative P/B policy, PSE artifact contract, deterministic cumulative builder, Postgres/MinIO receipt persistence, authenticated API, calculator, and PH workspace. Process original-period facts as reported; do not replace absent values with zero. Verify deterministic twins, exact 158-set and 148 parent preservation, real persistence, 158/158 API/detail parity, nine usable calculators plus HOUSE disabled, backend regression, frontend build, and browser states. Stop for the user's **Batch 15 results confirmation**; no activation, deployment, push, HOUSE recovery, substitution, Batch 16, or Phase C is authorized.

## Staged result, 2026-09-23

The nine numeric rows below are provisional `market_relative_only` P/B screens with Low reliability and null intrinsic bear/base/bull values. The 0.30×/0.45×/0.60× band is carried from Batch 12, not an independently calibrated peer study or property appraisal. Values are exact artifact PHP per share before UI two-decimal display rounding.

| Ticker | Low | Base | High | Availability |
|---|---:|---:|---:|---|
| ALCO | 0.363 | 0.5445 | 0.726 | Market-relative only; March source period |
| ALHI | 3.444 | 5.166 | 6.888 | Market-relative only; book movement/preferred warning |
| APVI | 3.486 | 5.229 | 6.972 | Market-relative only; JGS overlap |
| CEI | 0.045 | 0.0675 | 0.090 | Market-relative only; property/healthcare mix |
| ELI | 0.606 | 0.909 | 1.212 | Market-relative only; MEG overlap |
| GERI | 1.194 | 1.791 | 2.388 | Market-relative only; MEG overlap |
| HOUSE | null | null | null | Blocked; common shares delisted 2025-10-31 |
| KPPI | 1.278 | 1.917 | 2.556 | Market-relative only; concentrated office property |
| PRMX | 0.258 | 0.387 | 0.516 | Market-relative only; equity-basis warning |
| SLI | 1.200 | 1.800 | 2.400 | Market-relative only; treasury-share warning |

## Verification and release boundary

- Candidate `PSE-V2-PHASE-B-B15-2026-09-23-1.0` has exactly 158 records: 34 intrinsic, 122 market-relative, 2 unavailable; 156 provisional and 2 blocked (inherited CDC and new HOUSE). Manifest SHA-256 `641265728e673864851eeffaf3a989f9e18f41bba498aa5b523b383e60921aa3`. Deterministic twins were byte-identical; all 148 inherited Batch 14 artifacts were byte-preserved.
- Postgres/MinIO checked ten current reviewed-fact receipts and objects, ten original-period BVPS facts, 27 versioned multiple assumptions for the nine screenable issuers, and ten matching runs. `HOUSE` is explicitly stored as `delisted` with its historical 2025-06-30 fact; ALCO's reported March period is not relabeled as June.
- Four focused Batch 15 tests and all 389 backend tests pass. The frontend production build passes with its existing large-chunk warning.
- Isolated authenticated staged HTTP returned `158/158` exact stored-detail parity, nine usable new calculators and HOUSE disabled, unauthenticated `401`, inherited CDC disabled. KPPI edited from PHP1.917 to PHP2.13 at 0.50× P/B (saved scenario `#42`); a HOUSE calculator POST returned `400`.
- Isolated browser switched US→PH, searched KPPI, showed the 158-company staged catalog, changed its displayed base PHP1.92→2.13 and saved scenario `#43`. HOUSE rendered blocked/null with the PSE delisting notice and no calculator. ALCO showed the March-versus-June/preferred caveat; ELI showed its MEG non-additive warning.
- Active Batch 14 pointer SHA-256 remains `aa71518fbc10d3637058490f5031a5d30f74e5df9a30e0023560ec209421b2a4`. Batch 15 is absent from the serving root. Its activation guard pins the confirmed Batch 15 manifest hash; the default command is read-only preflight, and the mutating `--activate` path has not been run against real serving. No activation, deployment, push, substitution, HOUSE recovery, or next batch occurred.

**Results-confirmation gate:** user-confirmed on 2026-09-23. Read-only preflight verified all 158 artifacts, the exact two blocked records, and the unchanged active Batch 14 parent. An isolated temporary serving root exercised the activation routine without changing the real active pointer. The next gate is separate authorization for **local activation**. My earlier proposal incorrectly treated HOUSE's persistent PSE company page as evidence of a current listing; the later exchange delisting notice controls eligibility. Broader-use PSE source rights remain unconfirmed, so this is local reviewed-source work, not an automated or production data feed.

## Local activation — initial runtime blocker (resolved)

- The separately authorized `scripts/activate_pse_v2_phase_b_batch_15.py --activate` switched only local `active.json` to `PSE-V2-PHASE-B-B15-2026-09-23-1.0`. Readback validates all 158 artifacts against the confirmed manifest `641265728e673864851eeffaf3a989f9e18f41bba498aa5b523b383e60921aa3`; active pointer SHA-256 is `350a44123ab089a0c484c9d600046177cfb557a05eb72da8472a959559a9c632`. The Batch 14 manifest remains unchanged at `3afe1ac6f26b5e8751a714cf15776cc8e05a00304735d4b8b77b3c2922e54d38` for rollback.
- Historical candidate-builder successor guards and active-list assertions now recognize Batch 15, without changing pinned parent hashes or valuation artifacts. Full backend regression passes `389` tests; frontend production build passes with its existing large-chunk warning.
- **Not live-verified after activation:** local Postgres `127.0.0.1:5442` and MinIO `127.0.0.1:9100` were not listening. The persistence verifier failed with `psycopg_pool.PoolTimeout` after connection refusals. Docker Desktop's engine/status requests timed out, its normal restart failed to stop existing processes, and opening its error dialog through computer use timed out. No reset, data-volume deletion, API parity run, or browser check was attempted as a substitute.
- On the user's separate verification request, a fresh readback again validated all 158 active artifacts byte-for-byte against the confirmed candidate and the unchanged Batch 14 rollback manifest. Both local service ports remained closed and `docker desktop status` again failed to return engine status. The active API, browser, and current persistence checks therefore remain unverified; this repeated attempt is not marked as a UAT pass.

**Gate at that point (later resolved):** restore the existing Docker Desktop engine and Postgres/MinIO without resetting volumes, then rerun persistence verification, active authenticated `158/158` API/detail and ten calculator checks, browser UAT (KPPI edit/save, HOUSE blocked/source, ALCO period, ELI overlap), and final pointer/rollback readback. Only then request the user's Batch 15 **local-activation confirmation**. No deployment, push, HOUSE recovery, Batch 16, or Phase C work is implied.

### Infrastructure recovery after the verification blocker

- Docker Desktop's backend log identified `no space left on device` while writing its VM `init.log`. The VM was stopped. Host disk space later showed 9.9 GiB available, but Docker remained stuck in its error state.
- Under the user's explicit request to restore Docker without resetting volumes, the normal stop failed. The exact stuck Docker Desktop GUI/backend processes were validated and stopped; no VM disk or named volume was deleted, reset, or replaced. `docker desktop start` then returned `Status running` on readback.
- The original `valuation-db-1` and `valuation-minio-1` containers returned healthy on ports 5442 and 9100. Named volumes `valuation_pgdata` and `valuation_miniodata` remain present. The Batch 15 persistence verifier passed again with ten current receipts/objects, ten original-period facts, 27 assumptions, ten runs, HOUSE `delisted`, and ALCO's March source period intact.
- **At that point still open (later resolved below):** the active authenticated 158/158 API/detail, calculator, and browser UAT checks had not yet been rerun after infrastructure recovery. Host disk remained 98% used, about 9.9 GiB free; no unrelated files were removed to make space.

## Post-recovery active runtime verification, 2026-09-24

- Docker Desktop remained `running`; the original local Postgres and MinIO containers were healthy. The Batch 15 persistence verifier passed against existing data: ten reviewed receipts and MinIO objects, ten original-period facts, 27 assumptions, ten current runs, HOUSE `delisted` with 2025-06-30 historical period, and ALCO's 2026-03-31 period.
- Isolated local FastAPI ran against the real `active.json` pointer. Authenticated HTTP returned `158/158` exact stored-detail parity, all ten new calculator states (nine usable, HOUSE disabled), inherited CDC disabled, unauthenticated `401`, and HOUSE calculator POST `400`. KPPI edited to PHP2.13 at 0.50× P/B and saved scenario `#44` through HTTP.
- The actual local browser switched US→PH, searched KPPI, displayed the active 158-record catalog, recalculated PHP1.92→PHP2.13 and saved scenario `#45`. HOUSE rendered blocked/null without a calculator and linked its PSE delisting notice; ALCO showed its March source-period/preferred-claim caveat; ELI showed the MEG non-additive warning; inherited CDC stayed blocked/null.
- Read-only final catalog verification validated all 158 active artifacts and showed the served 169 files byte-identical to the user-confirmed Batch 15 candidate. The Batch 14 rollback manifest remains unchanged at SHA-256 `3afe1ac6f26b5e8751a714cf15776cc8e05a00304735d4b8b77b3c2922e54d38`. All `389` backend tests and the frontend production build passed on the current checkout; the existing `crypt` deprecation and large-chunk warnings remain informational.

**Activation confirmation gate:** passed locally and user-confirmed on 2026-09-24. Fresh readback still showed the 158-entry Batch 15 active manifest `641265728e673864851eeffaf3a989f9e18f41bba498aa5b523b383e60921aa3` and unchanged Batch 14 rollback manifest `3afe1ac6f26b5e8751a714cf15776cc8e05a00304735d4b8b77b3c2922e54d38`. No deployment, push, HOUSE recovery, Batch 16, or Phase C work was performed. Broader-use PSE source rights remain unconfirmed, and host disk pressure remains an operational risk.
