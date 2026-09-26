# PSE Sector Valuation Pipeline V2

**Status:** Phase A and A.1 confirmed on 2026-09-21; Phase A.2 and Phase B Batch 1 results/activation confirmed on
2026-09-22. Phase B Batch 2 results and local activation were confirmed on 2026-09-22. Batch 3 results were implemented,
live verified, and user-confirmed on 2026-09-22. Local Batch 3 activation was separately authorized, live verified, and
user-confirmed on 2026-09-22. The cumulative 38-company Batch 3 catalog is active locally and not deployed; the
28-company Batch 2 catalog remains preserved for rollback. Batch 4 was implemented, live verified, and user-confirmed
as a staged 48-company candidate on 2026-09-22. Local Batch 4 activation was separately authorized, live verified, and
user-confirmed on 2026-09-23. The 48-company Batch 4 catalog is active locally and not deployed, and the 38-company
Batch 3 catalog remains preserved for rollback. Batch 5 was implemented, live verified, and user-confirmed as a staged
58-company candidate on 2026-09-23. Local activation was separately authorized, live verified, and user-confirmed on
2026-09-23. The 58-company Batch 5 catalog is active locally and not deployed; Batch 4 remains preserved for rollback.
Batch 6 was implemented, results-confirmed, locally activated, live verified, and user-confirmed on 2026-09-23. Batch 7
was implemented and results-confirmed, then separately authorized for local activation, live-verified, and
user-confirmed on 2026-09-23. The 78-company Batch 7 catalog is active locally and Batch 6 is preserved for rollback.  
Batch 8 was implemented and results-confirmed, then separately authorized for local activation, live-verified, and
user-confirmed on 2026-09-23. The 88-company Batch 8 catalog is active locally and Batch 7 is preserved for rollback.  
Batch 9 was implemented and results-confirmed, then separately authorized for local activation, live-verified, and
user-confirmed on 2026-09-23. The 98-company Batch 9 catalog is active locally and Batch 8 is preserved for rollback.  
Batch 10 was implemented and results-confirmed, then separately authorized for local activation, live-verified, and
user-confirmed on 2026-09-23. The 108-company Batch 10 catalog is active locally and Batch 9 is preserved for rollback.  
Batch 11 was implemented and live-verified as a staged 118-company candidate, results-confirmed, then separately authorized for local activation, live-verified, and user-confirmed on 2026-09-23. The 118-company Batch 11 catalog is active locally; Batch 10 remains preserved for rollback.  
Batch 12 was implemented and live-verified as a staged 128-company candidate, results-confirmed, then separately authorized for local activation, live-verified, and user-confirmed on 2026-09-23. The 128-company Batch 12 catalog is active locally; Batch 11 remains preserved for rollback.  
Batch 13 was implemented and live-verified as a staged 138-company candidate, results-confirmed, then separately authorized for local activation, live-verified, and user-confirmed on 2026-09-23. The 138-company Batch 13 catalog is active locally; Batch 12 remains preserved for rollback.  
Batch 14 was implemented and live-verified as a staged 148-company candidate, and its results were user-confirmed on 2026-09-23. Local activation was separately authorized, live-verified, and user-confirmed on 2026-09-23. The 148-company Batch 14 catalog is active locally; Batch 13 remains preserved for rollback.  
Batch 15 was implemented and live-verified as a staged 158-record candidate, and its results were user-confirmed on 2026-09-23. A separate local-activation request switched the active pointer to Batch 15; post-recovery API, browser, persistence, and regression verification passed and the user confirmed local activation on 2026-09-24. Batch 14 remains preserved for rollback.  
Batch 16 was implemented and live-verified as a staged 168-record candidate, and its results were user-confirmed on 2026-09-25. Separate local activation was then authorized, live-verified, and user-confirmed on 2026-09-25; the 168-record Batch 16 catalog is active locally. Batch 15 remains preserved for rollback.  
Batch 17 was implemented and live-verified as a staged 178-record candidate, and its results were user-confirmed on 2026-09-25. Separate local activation was then authorized, live-verified, and user-confirmed on 2026-09-25; the 178-record Batch 17 catalog is active locally. Batch 16 remains preserved for rollback.  
Batch 18 was implemented and live-verified as a staged 188-record candidate, and its results were user-confirmed on 2026-09-25. Separate local activation was then authorized, live-verified, and user-confirmed on 2026-09-25; the 188-record Batch 18 catalog is active locally. Batch 17 remains preserved for rollback.  
Batch 19 was implemented and live-verified as a staged 198-record candidate on 2026-09-25; its results were user-confirmed the same day. Separate local activation was then authorized, live-verified, and user-confirmed; the 198-record Batch 19 catalog is active locally. Batch 18 remains preserved for rollback.  
Batch 20 was implemented and live-verified as a staged 208-record candidate on 2026-09-25; its results were user-confirmed the same day. Separate local activation was then authorized, live-verified, and user-confirmed; the 208-record Batch 20 catalog is active locally. Batch 19 remains preserved for rollback.  
Batch 21 was implemented and live-verified as a staged 218-record candidate on 2026-09-25; its results were user-confirmed the same day. Separate local activation was then authorized, live-verified and user-confirmed; the 218-record Batch 21 catalog is locally active, with Batch 20 preserved for rollback.  
Batch 22 was frozen to `CSB, ORE, ECVC, GREEN, EGRN, ENEX, JAS, NI, WIN, PA` and implemented as a staged 228-record candidate on 2026-09-25. Its results were live-verified and user-confirmed; separate local activation was then authorized, live-verified and user-confirmed. The 228-record Batch 22 catalog is locally active, with Batch 21 preserved for rollback.  
Batch 23 was frozen to `BC, CA, LC, ATN, OPM, FJP, DIZ, IMP, FERRO, ABG` and implemented as a staged 238-record candidate on 2026-09-25. Its results were live-verified and user-confirmed; separate local activation was then authorized, live-verified and user-confirmed. The 238-record Batch 23 catalog is locally active, with Batch 22 preserved for rollback.  
Batch 24 was frozen to `AB, FPI, FAF, BH, GEO, UPM, MA, X, MFC, SLF` and implemented as a staged 248-record candidate on 2026-09-25. Its results were live-verified and user-confirmed; separate local activation was then authorized, live-verified and user-confirmed. The 248-record Batch 24 catalog is locally active, with Batch 23 preserved for rollback.  
Batch 25 was frozen to `FFI, FYN, MAH, MED, MG, ZHI, LTL, VLL, VREIT, ALLDY` and staged as an exact 258-record candidate on 2026-09-25. Three new results are Low-reliability market-relative screens; seven are blocked/null. Results were live-verified and user-confirmed; separate local activation was then authorized, live-verified and user-confirmed. The 258-record Batch 25 catalog is locally active, with Batch 24 preserved for rollback.  
Batch 26 was frozen to `DHI, HOME, MM, STR, VLC, UNH, PNX, ROX, INFRA, I` and staged as an exact 268-record candidate on 2026-09-25. MM has one historical Low-reliability market-relative screen; nine new outcomes are blocked/null. Results were live-verified and user-confirmed; separate local activation was then authorized, live-verified and user-confirmed. The 268-record Batch 26 catalog is locally active, with Batch 25 preserved for rollback.  
Batch 27 was frozen to `AR, BMM, CYBR, MGH, MJIC, PNC, PORT, SOC, T, TUBIG` and staged as an exact 278-record candidate on 2026-09-25. All ten new outcomes are blocked/null; no new numerical valuation is claimed. Staged verification passed and the user confirmed the results. Separate local activation was then authorized, live-verified and user-confirmed; the 278-record Batch 27 catalog is locally active, with Batch 26 preserved for rollback.  
Batch 28 was explicitly frozen as the four remaining in-scope ordinary-common issuers `AAA, EG, NXGEN, PTT` on 2026-09-26. Its exact 282-record candidate was staged, live-verified and results-confirmed; NXGEN has one Low-reliability market-relative screen and three new records are blocked/null. Separate local activation was then authorized, live-verified and user-confirmed; the 282-record Batch 28 catalog is locally active, with Batch 27 preserved for rollback.  
**Frozen pilot:** `AC, ACR, ALI, AP, AREIT, BDO, PERC, SCC`  
**Valuation date:** 2026-09-21

This plan supersedes the model-blending direction in `docs/pse-valuation-engine-plan.md` for V2. The legacy PSE
workbench remains available until the staged V2 catalog is verified and explicitly confirmed.

## V1 contract

- Four intrinsic engines only: FCFF, residual income, sustainable distributions, and SOTP.
- Comparables are a separately labeled market-relative check, never an automatic blend.
- Ordinary common equity only.
- Missing critical evidence blocks the affected valuation; it is never replaced with zero.
- Availability (`intrinsic_valuation`, `market_relative_only`, `not_available`) is separate from review state
  (`approved`, `provisional`, `blocked`).
- Postgres stores reviewed facts, adjustments, assumptions, and runs; MinIO stores original documents.
- Immutable catalog artifacts are staged and hash-bound. Activation is a separate confirmation.

## Phase A — reviewed pilot (NOW)

1. Verify the local source set and content hashes.
2. Build the common evidence schema and four pure engines.
3. Route the eight issuers by business economics.
4. Produce bear/base/bull artifacts without forcing unsupported values.
5. Generate deterministic twin catalogs.
6. Serve the staged catalog through authenticated list/detail endpoints.
7. Render the staged `/pse-v2` page while leaving `/pse` unchanged.
8. Run focused tests, full regression, frontend build, and live API/UI verification.

**Exit:** exact 8/8 stored/API parity; all critical facts are source-linked; blocked artifacts are null with reasons;
twins are byte-identical; the real staged page renders; the user confirmed this staged Phase A result on 2026-09-21.

### Phase A verification evidence

- Staged catalog: `1 provisional intrinsic / 0 market-relative / 7 not available`; no approved artifacts.
- AP exact bear/base/bull: `PHP 13.070828684544006 / 29.154683615845205 / 53.07395689365769`.
- Evidence store: 8 securities, 48 hash-verified documents in Postgres and MinIO, 5 reviewed AP facts, 1 dated macro
  assumption, and 8 valuation runs; replay leaves all counts unchanged.
- Deterministic generation: independent catalog twins are byte-identical and tampering fails closed.
- Tests/build: 20 focused PSE V2 tests and 290 full backend tests pass; frontend production build passes with the
  existing large-chunk warning.
- Real API: authenticated list count 8, all 8 details return 200 and exactly match stored artifacts, unauthenticated
  access returns 401.
- Real UI: staged `/pse-v2` renders AP's provisional scenarios and BDO's blocked/null reasons; active `/pse` remains
  the legacy four-company page.

**Gate status:** ✔ verified and user-confirmed. This confirmation covered Phase A bookkeeping only. Phase A.2 later
authorized local catalog/UI activation; deployment, recovery, and Phase B remain unauthorized. Commercial-use terms
remain the external Gate 0 blocker for automated acquisition.

## Phase A.1 — practical market-relative fallbacks **NOW**

| ID | What | Source gap | Severity | Verify |
|---|---|---|---|---|
| MR-01 | Convert the seven specialist-blocked issuers to provisional `market_relative_only` ranges using source-linked EPS/DPS and versioned policy bands. | Audit 09 | P0 | Seven artifacts have finite low/base/high relative estimates while intrinsic scenarios remain null. |
| MR-02 | Expose the base relative estimate in the authenticated list API without changing AP intrinsic behavior. | Audit 09 | P1 | Stored-versus-served parity for all eight details and summaries. |
| MR-03 | Render a distinct market-relative screen in `/pse-v2`, preserving limitations and source evidence. | Audit 09 | P1 | Browser-check AP intrinsic plus one P/E, one yield, and the former blocked state semantics. |

**Definition of done:** deterministic staged catalog, focused/full tests, production build, exact 8/8 API parity, real
browser verification, no active pointer, and user confirmation. Policy bands remain provisional and are not presented
as empirically validated peer sets.

### Phase A.1 verification evidence

- Staged catalog `PSE-V2-PILOT-2026-09-21-1.1`: `1 intrinsic / 7 market-relative / 0 unavailable`; all eight remain
  provisional and no artifact is approved.
- Market-relative low/base/high values:
  - AC `PHP 518.16 / 647.70 / 777.24`
  - ACR `PHP 1.071 / 1.26 / 1.449`
  - ALI `PHP 32.40 / 40.50 / 48.60`
  - AREIT `PHP 28.00 / 32.00 / 37.333333333333336`
  - BDO `PHP 130.24 / 162.80 / 195.36`
  - PERC `PHP 4.675 / 5.50 / 6.325`
  - SCC `PHP 23.4855 / 27.63 / 31.7745`
- Evidence store: 8 securities, 50 hash-verified documents, 12 source-linked facts, 22 versioned assumptions, 16
  valuation runs, and 50 MinIO objects; replay leaves all counts unchanged.
- Tests/build: 22 focused PSE V2 tests and 292 full backend tests pass; frontend production build passes with the
  existing large-chunk warning.
- Real API: exact 8/8 stored/detail parity, all eight list summaries finite, and unauthenticated access returns 401.
- Real UI: AP intrinsic, BDO P/E fallback, and AREIT distribution-yield fallback render with distinct labels,
  warnings, source evidence, and specialist-model limitations; active `/pse` remains unchanged.

**Gate status:** ✔ verified and user-confirmed. This confirmation covered the staged Phase A.1 fallback catalog and its
bookkeeping only. Phase A.2 later authorized local catalog/UI activation; deployment, specialist-model recovery, and
Phase B remain unauthorized.

## Phase A.2 — seamless PSE/US workspace parity **NOW**

| ID | What | Source gap | Severity | Verify |
|---|---|---|---|---|
| UI-01 | Make `/pse/:ticker` the V2 workspace and keep `/pse-v2` as a compatibility redirect. | Audit 10 | P0 | US→PSE→US switch preserves the active market and valid route. |
| UI-02 | Add PSE calculator view/post/save endpoints for AP intrinsic and seven market-relative policies. | Audit 10 | P0 | Defaults reproduce catalog values; edits change only the selected case; saved row persists. |
| UI-03 | Reuse the US identity, seven-day calendar, swipe sections, assumptions controls, source view, and footer. | Audit 10 | P1 | Browser UAT across AP, BDO, and AREIT. |
| UI-04 | Make header search, valuation dock, portfolio cards, and saved scenarios market-aware. | Audit 10 | P1 | PH search, add-to-portfolio, save, and return-to-company flows pass live. |

**Definition of done:** focused/full tests and build pass; PSE calculator defaults reproduce all eight staged baselines;
real API, persistence, market switch, calendar, calculator, save, portfolio, and search flows pass; no deployment or
Phase B work occurs; user confirmation remains required.

### Phase A.2 verification evidence

- Active local route: `/pse/:ticker`; `/pse` redirects to AP and `/pse-v2` remains a compatibility redirect.
- Active catalog pointer: `PSE-V2-PILOT-2026-09-21-1.1`; no deployment or push performed.
- Calculator API: AP defaults reproduce all three FCFF cases; BDO 10×→11× changes base `PHP162.80→179.08`; AREIT
  7%→6% yield changes base `PHP32.00→37.333333333333336`; invalid overrides fail closed.
- Persistence: BDO PH holding and edited scenario save/readback succeeded on the non-admin verification account.
- Real UI: US↔PH market switch, PH header search, seven-day calendar, five swipe sections, AP reset, BDO/AREIT edits,
  portfolio link, and saved-scenario return link passed TC-PSE-01 through TC-PSE-06.
- Automated verification: 30 focused PSE V2 tests and 300 full backend tests pass; frontend production build passes
  with the existing large-chunk warning.

**Gate status:** ✔ verified and user-confirmed on 2026-09-22. Confirmation covers the locally active Phase A.2 catalog,
workspace, calculator, search, portfolio, save, and history behavior. No deployment, push, specialist-model recovery,
or Phase B work has been performed.

## Phase B — frozen subsector batches of ten

### Batch 1 — banks and REITs **NOW**

**Frozen set:** `BPI, MBT, SECB, CBC, EW, RCR, MREIT, CREIT, FILRT, DDMPR`

- Five banks use residual income with justified book-value economics.
- Five REITs use sustainable distributions with reported book value retained as a separate check.
- The candidate is cumulative: the unchanged active eight plus the frozen ten, for exactly 18 artifacts.
- Candidate generation stays outside the serving catalog root so history and list/detail endpoints cannot expose it
  before activation.
- Original remote filings are not redistributed. Deterministic reviewed fact receipts bind the staged inputs and
  official links while source-rights clearance remains unresolved.

### Batch 1 verification evidence

- Batch output: `10 provisional intrinsic / 0 market-relative / 0 unavailable`; all ten are Low reliability.
- Exact values and per-issuer evidence are recorded in `docs/audit/11-pse-phase-b-batch-01.md`.
- Persistence: 10 securities, 10 reviewed receipts, 40 facts, 150 assumptions, 10 valuation runs, and 10 verified MinIO
  objects; replay leaves counts unchanged.
- Deterministic twins are byte-identical; cumulative manifest SHA-256 is
  `74bff339ea0f5e1925cf598640f1b83ce85790f541d8da55f5fb66b5b59c85a5`.
- Real staged API: exact 18/18 detail parity and 10/10 calculator parity; authentication and saved-scenario persistence
  pass.
- Real staged UI: search, BPI residual-income controls, and MREIT sustainable-distribution controls pass
  TC-PSE-B01-01 through TC-PSE-B01-04.
- Automated verification: 38 focused PSE tests and 308 full backend tests pass; frontend production build passes with
  the existing chunk-size warning.
- Pre-activation preservation check: local serving remained `PSE-V2-PILOT-2026-09-21-1.1` with exactly eight issuers
  until the later, separately authorized activation.

**Gate status:** ✔ Batch 1 results were verified and user-confirmed on 2026-09-22. The user separately authorized local
activation. Local activation was verified and user-confirmed on 2026-09-22. No deployment, push, recovery, or Batch 2
work is authorized.

### Batch 1 local activation evidence

- `active.json` and `staged.json` now select `PSE-V2-PHASE-B-B01-2026-09-22-1.0`; its manifest hash remains
  `74bff339ea0f5e1925cf598640f1b83ce85790f541d8da55f5fb66b5b59c85a5`.
- The previous `PSE-V2-PILOT-2026-09-21-1.1` directory and manifest remain unchanged for rollback.
- Real active API: 18/18 stored-versus-served detail parity, 10/10 Batch 1 calculator parity, unauthenticated access 401,
  and edited BPI scenario `#5` persisted.
- Real active UI: `localhost:4000/pse/BPI` rendered PHP98.44 and changed to PHP88.37 at 13% cost of equity; active
  search returned MREIT and `/pse/MREIT` rendered PHP12.08, changing to PHP10.81 at 12% cost of equity.
- Post-activation verification: 309 full backend tests pass; frontend production build passes with the existing
  chunk-size warning.

### Batch 2 — consumer and retail operating companies **NOW**

**Frozen set:** `URC, CNPF, MONDE, JFC, DNL, PGOLD, RRHI, WLCON, SEVN, SSI`

- Eight issuers use the shared FCFF engine with issuer-bound capital bridges and a three-year median owner-cash proxy.
- DNL and SSI use transparent P/E fallbacks because their specialist FCFF bridges remain unresolved.
- The candidate is cumulative: the unchanged active 18 plus the frozen ten, for exactly 28 artifacts.
- Candidate generation and the staged pointer remain outside the serving root; no activation occurred.

### Batch 2 verification evidence

- Batch output: `8 provisional intrinsic / 2 market-relative / 0 unavailable`; all ten are Low reliability.
- Exact values and per-issuer evidence are recorded in `docs/audit/12-pse-phase-b-batch-02.md`.
- Persistence: 10 securities, 10 reviewed receipts, 79 facts, 134 assumptions, 10 valuation runs, and 10 verified MinIO
  objects; replay leaves counts unchanged.
- Deterministic twins are byte-identical; cumulative manifest SHA-256 is
  `f1a1405a3a9d8c8bdc8b620b1a1c9a34dc4a38320d3ef403c8c99c9f3d418741`.
- Real staged API: exact 28/28 detail parity and 10/10 Batch 2 calculator parity; authentication and save persistence
  pass.
- Real staged UI: URC FCFF and DNL market-relative flows pass alongside exact 28-company search/list behavior.
- Calculator safeguard: non-AP FCFF issuers now recalculate from their own artifact-bound bridges.
- Automated verification: 26 focused model/calculator tests and 318 full backend tests pass; frontend production build
  passes with the existing chunk-size warning.
- Pre-activation preservation check: local serving remained the confirmed 18-company Batch 1 catalog until the later,
  separately authorized activation.

**Gate status:** ✔ Batch 2 results were verified and user-confirmed on 2026-09-22. The user separately authorized local
activation. Local activation was verified and user-confirmed on 2026-09-22. No deployment, push, recovery, Batch 3,
or Phase C work is authorized.

### Batch 2 local activation evidence

- `active.json` and `staged.json` now select `PSE-V2-PHASE-B-B02-2026-09-22-1.0`; active pointer SHA-256 is
  `c9821d8980125f61597d9662ff83f0b7c7e878420ec73beed62792467a7389d6`.
- The confirmed manifest remains `f1a1405a3a9d8c8bdc8b620b1a1c9a34dc4a38320d3ef403c8c99c9f3d418741`.
- The previous `PSE-V2-PHASE-B-B01-2026-09-22-1.0` catalog remains unchanged for rollback.
- Real active API: 28/28 detail parity, 10/10 Batch 2 calculator parity, unauthenticated access 401, and edited URC
  scenario `#7` persisted.
- Real active UI: `localhost:4000/pse/URC` rendered PHP21.56 and changed to PHP25.11 at 5% growth; active search opened
  DNL with the correct market-relative label and PHP3.60 base.
- Post-activation verification: 319 backend tests pass; frontend production build passes with the existing chunk-size
  warning.

### Batch 3 — holding companies and property developers **STAGED**

**Frozen set:** `SM, AEV, JGS, GTCAP, DMC, SMPH, RLC, MEG, FLI, CLI`

- `SMPH, RLC, FLI` use provisional property RNAV through the existing SOTP/NAV engine.
- The other seven issuers use finite P/B-to-reported-NAV fallbacks while complete component or property bridges remain
  unresolved; they are not mislabeled intrinsic.
- The candidate is cumulative: the unchanged active 28 plus the frozen ten, for exactly 38 artifacts.
- Candidate generation and the staged pointer remain outside the serving root; no activation occurred.

### Batch 3 verification evidence

- Batch output: `3 provisional intrinsic / 7 market-relative / 0 unavailable`; all ten are Low reliability.
- Exact values and per-issuer evidence are recorded in `docs/audit/13-pse-phase-b-batch-03.md`.
- Persistence: 10 securities, 10 reviewed receipts, 32 facts, 39 assumptions, 10 valuation runs, and 10 verified MinIO
  objects.
- Deterministic twins are byte-identical; cumulative manifest SHA-256 is
  `fb420ec53ea1878743e3c3debd9082ecd57de867837a2080b2820d94259cc35a`.
- Real staged API: exact 38/38 detail parity and 10/10 Batch 3 calculator parity; authentication and save persistence
  pass.
- Real staged UI: RLC intrinsic RNAV and AEV sub-one P/B fallback both render and recalculate correctly.
- Automated verification: 328 backend tests pass; frontend production build passes with the existing chunk-size warning.
- Active preservation: the 28-company Batch 2 active pointer and manifest hashes remain unchanged.

**Gate status:** ✔ Batch 3 results and local activation were separately verified and user-confirmed on 2026-09-22. No
deployment, push, recovery, Batch 4, or Phase C work is authorized.

### Batch 3 local activation evidence

- `active.json` and `staged.json` now select `PSE-V2-PHASE-B-B03-2026-09-22-1.0`; active pointer SHA-256 is
  `2c39244d615d31432e6996714a768192475e9b95949079593ba18060c083bf7b`.
- The confirmed manifest remains `fb420ec53ea1878743e3c3debd9082ecd57de867837a2080b2820d94259cc35a`.
- The previous `PSE-V2-PHASE-B-B02-2026-09-22-1.0` catalog remains unchanged for rollback.
- Real active API: 38/38 detail parity, 10/10 Batch 3 calculator parity, unauthenticated access 401, and edited SM
  scenario `#9` persisted.
- Real active UI: RLC rendered `PHP61.82→PHP66.87` at 60% uplift realization; AEV rendered
  `PHP31.39→PHP36.62` at 0.7x P/B; the footer reported 38 companies.
- Post-activation verification: 329 backend tests pass; frontend production build passes with the existing chunk-size
  warning.

### Batch 4 — electricity, energy, power, and water **STAGED**

**Frozen set:** `MER, FGEN, ACEN, MWC, SPC, CREC, ALTER, ASLAG, SPNEC, MYNLD`

- `MER, MWC, MYNLD` use finite-life common-distribution valuations ending at documented franchise/concession expiry.
- `SPC` uses a continuing common-distribution valuation based on reviewed 2025 regular payouts.
- `FGEN, ACEN, CREC, ALTER, ASLAG, SPNEC` use finite P/B screens while their project/asset FCFF or SOTP bridges remain
  incomplete; those outputs are not labeled intrinsic.
- The candidate is cumulative: the unchanged active 38 plus the frozen ten, for exactly 48 artifacts.
- Candidate generation and the staged pointer remain outside the serving root; no activation occurred.

### Batch 4 verification evidence

- Batch output: `4 provisional intrinsic / 6 market-relative / 0 unavailable`; all ten are Low reliability.
- Exact values and per-issuer evidence are recorded in `docs/audit/14-pse-phase-b-batch-04.md`.
- Persistence: 10 securities, 16 reviewed receipts, 28 facts, 45 assumptions, 10 valuation runs, and 16 verified MinIO
  objects.
- Deterministic twins are byte-identical; cumulative manifest SHA-256 is
  `29673524d381211947d1518cc31720320fcbbe60d0a88f5b005040808f248588`.
- Real staged API: exact 48/48 detail parity and 10/10 Batch 4 calculator parity; authentication and save persistence
  pass.
- Real staged UI: MWC finite-life distributions and ACEN P/B fallback both render and recalculate correctly.
- Automated verification: 339 backend tests pass; frontend production build passes with the existing chunk-size warning.
- Active preservation: the 38-company Batch 3 active pointer and manifest hashes remain unchanged.

**Gate status:** ✔ Batch 4 results and local activation were separately verified and user-confirmed by 2026-09-23. No
deployment, push, recovery, Batch 5, or Phase C work is authorized.

### Batch 4 local activation evidence

- `active.json` and `staged.json` now select `PSE-V2-PHASE-B-B04-2026-09-22-1.0`; active pointer SHA-256 is
  `8deab067ac2cdb80a618f1c389ba397c472d76855c2340820d6551ebf6ee5d88`.
- The confirmed manifest remains `29673524d381211947d1518cc31720320fcbbe60d0a88f5b005040808f248588`.
- The previous `PSE-V2-PHASE-B-B03-2026-09-22-1.0` catalog remains unchanged for rollback.
- Real active API: 48/48 detail parity, 10/10 Batch 4 calculator parity, unauthenticated access 401, and edited MWC
  scenario `#11` persisted.
- Real active UI: MWC rendered `PHP17.03→PHP18.42` at 3.5% distribution growth; ACEN rendered
  `PHP3.51→PHP3.83` at 1.2x P/B; the footer reported 48 companies.
- Post-activation verification: 340 backend tests pass; frontend production build passes with the existing chunk-size
  warning.

### Batch 5 — banks and other financial institutions **STAGED**

**Frozen set:** `PNB, RCB, UBP, AUB, PBB, PSB, COL, PSE, NRCP, MFIN`

- Eight issuers use residual income through shared bank or other-financial policies.
- PSE uses a P/E fallback because the reported parent-equity/BVPS/share bridge does not reconcile after the PDS
  transaction; MFIN uses P/B because its 2026 first-half loss conflicts with FY2025 profitability.
- The candidate is cumulative: the unchanged active 48 plus the frozen ten, for exactly 58 artifacts.
- Candidate generation and the staged pointer remain outside the serving root; no activation occurred.

### Batch 5 verification evidence

- Batch output: `8 provisional intrinsic / 2 market-relative / 0 unavailable`; all ten are Low reliability.
- Exact values and evidence are recorded in `docs/audit/15-pse-phase-b-batch-05.md`.
- Persistence: 10 securities, 10 receipts, 46 facts, 174 assumptions, 10 runs, and 10 verified MinIO objects.
- Deterministic twins are byte-identical; cumulative manifest SHA-256 is
  `b6dc2ae35ad13e0ee2f40c11e0b7190441da651acf914e90fea3334302ece95b`.
- Real staged API: exact 58/58 detail parity and 10/10 Batch 5 calculator parity; authentication and save persistence
  pass.
- Real staged UI: PNB residual income and PSE P/E fallback both render and recalculate correctly.
- Automated verification: 348 backend tests pass; frontend production build passes with the existing chunk-size warning.
- Active preservation: the 48-company Batch 4 active pointer and manifest hashes remain unchanged.

**Gate status:** ✔ Batch 5 results and local activation were separately verified and user-confirmed on 2026-09-23. No
deployment, push, recovery, Batch 6, or Phase C work is authorized.

### Batch 5 local activation evidence

- `active.json` and `staged.json` select `PSE-V2-PHASE-B-B05-2026-09-23-1.0`; active pointer SHA-256 is
  `ff29ce15140054d26b4a6e8db57af9152dd74cdabbb0dbe4240434151f3e791b`.
- The confirmed manifest remains `b6dc2ae35ad13e0ee2f40c11e0b7190441da651acf914e90fea3334302ece95b`.
- The previous Batch 4 catalog remains unchanged for rollback.
- Real active API: 58/58 detail parity, 10/10 calculator parity, 401 unauthenticated, and PNB scenario `#13` persisted.
- Real active UI: PNB rendered PHP113.31 and PSE rendered PHP169.32→PHP183.43 at 13x P/E; footer reported 58.
- Post-activation verification: 349 backend tests pass; frontend production build passes.

### Batch 6 — connectivity, media, and digital platforms **STAGED**

**Frozen set:** `TEL, GLO, CNVRG, DITO, NOW, GMA7, ABS, MB, DFNN, PLUS`

- All ten publish finite market-relative screens while specialist FCFF, SOTP, NAV, or distribution bridges remain incomplete.
- Negative-equity issuers use revenue screens instead of invalid P/B or P/E outputs.
- The cumulative candidate contains the unchanged active 58 plus the frozen ten, exactly 68 artifacts.

### Batch 6 verification evidence

- Batch output: `0 intrinsic / 10 market-relative / 0 unavailable`; all provisional and Low reliability.
- Exact values are in `docs/audit/16-pse-phase-b-batch-06.md`.
- Persistence: 10 securities, 10 receipts, 10 facts, 30 assumptions, 10 runs, and 10 verified objects.
- Manifest SHA-256: `848f8205e4da2b2fd6568385c1287e4efc890f0ce889595f0163abfea3ade37a`.
- Real staged API: 68/68 detail parity and 10/10 calculator parity; UI rendered TEL correctly.
- Automated verification: 353 backend tests and frontend production build pass.
- Active 58-company Batch 5 catalog remains unchanged.

**Gate status:** ✔ Batch 6 results and local activation were separately verified and user-confirmed on 2026-09-23. No deployment, push, Batch 7, or Phase C work is authorized.

### Batch 6 local activation evidence

- Active pointer SHA-256: `458520a940cc85411c5b1980d01d8063fc8b97cc863ff1b1626dc64f3fb1f96a`.
- Active API: 68/68 detail and 10/10 calculator parity; TEL scenario `#15` persisted.
- Active UI rendered TEL and the 68-company footer; Batch 5 remains preserved.
- Post-activation verification: 353 backend tests and frontend production build pass.

### Batch 7 — transportation, logistics, and infrastructure **STAGED**

**Frozen set:** `ICT, CEB, PAL, MAC, ATI, TUGS, C, LSC, MWIDE, EEI`

- Ports target concession-life DCF/SOTP; airlines target fleet NAV and lease-adjusted economics; shipping targets fleet NAV/FCFF; contractors target normalized FCFF or builder/concession SOTP.
- All ten publish finite market-relative screens while those specialist intrinsic bridges remain incomplete.
- ICT's USD earnings metric is explicitly converted to PHP using the dated 2026-09-22 BSP reference rate.
- ATI remains valued as a Low-reliability screen but carries a visible stale-period warning.
- The cumulative candidate contains the unchanged active 68 plus the frozen ten, exactly 78 artifacts.

### Batch 7 verification evidence

- Batch output: `0 intrinsic / 10 market-relative / 0 unavailable`; all provisional and Low reliability.
- Exact values are in `docs/audit/17-pse-phase-b-batch-07.md`.
- Persistence: 10 securities, 10 receipts, 10 facts, 30 assumptions, 10 runs, and 10 verified objects.
- Manifest SHA-256: `7b3419c52934f9a15d378f8918027697fd9737f2fc449d7f897fa5dcda9f6f91`.
- Real staged API: 78/78 detail parity and 10/10 calculator parity; UI rendered and recalculated ICT correctly and exposed ATI's stale warning.
- Automated verification: 357 backend tests and frontend production build pass.
- Active 68-company Batch 6 pointer and manifest remain unchanged; Batch 7 is absent from the serving root.

**Gate status:** ✔ Batch 7 results and local activation were separately verified and user-confirmed on 2026-09-23. No deployment, push, Batch 8, or Phase C work is authorized.

### Batch 7 local activation evidence

- `active.json` and `staged.json` select `PSE-V2-PHASE-B-B07-2026-09-23-1.0`; active pointer SHA-256 is
  `62caa7cce3ef7987681a7995c17aebec0db998db1f08e96dcd97b31b952cef7b`.
- The confirmed manifest remains `7b3419c52934f9a15d378f8918027697fd9737f2fc449d7f897fa5dcda9f6f91`.
- The previous Batch 6 catalog remains unchanged for rollback.
- Real active API: 78/78 detail parity, 10/10 calculator parity, 401 unauthenticated, and ICT scenario `#17` persisted.
- Real active UI: ICT rendered PHP527.51 and changed to PHP562.68 at 16x P/E; ATI's stale warning rendered; footer reported 78.
- Post-activation verification: 357 backend tests and frontend production build pass.

### Batch 8 — mining and oil **STAGED**

**Frozen set:** `NIKL, PX, APX, FNI, AT, MARC, OGP, PCOR, PXP, OV`

- Producing mines target reserve-based NAV/life-of-mine DCF; downstream refining targets normalized FCFF; upstream exploration targets risked reserve/option NAV.
- All ten publish finite market-relative screens while those specialist reserve and capital-claim bridges remain incomplete.
- OGP's USD earnings metric is explicitly converted to PHP using the dated 2026-09-22 BSP reference rate.
- The cumulative candidate contains the unchanged active 78 plus the frozen ten, exactly 88 artifacts.

### Batch 8 verification evidence

- Batch output: `0 intrinsic / 10 market-relative / 0 unavailable`; all provisional and Low reliability.
- Exact values are in `docs/audit/18-pse-phase-b-batch-08.md`.
- Persistence: 10 securities, 10 receipts, 10 facts, 30 assumptions, 10 runs, and 10 verified objects.
- Manifest SHA-256: `0236bc52a4408f3e175c814ff9140cf82fa198454b84fbbe0044f8cc4c557a78`.
- Real staged API: 88/88 detail parity and 10/10 calculator parity; UI rendered and recalculated OGP and rendered representative mining, downstream, and upstream routes.
- Automated verification: 361 backend tests and frontend production build pass.
- Active 78-company Batch 7 pointer and manifest remain unchanged; Batch 8 is absent from the serving root.

**Gate status:** ✔ Batch 8 results and local activation were separately verified and user-confirmed on 2026-09-23. No deployment, push, Batch 9, or Phase C work is authorized.

### Batch 8 local activation evidence

- `active.json` and `staged.json` select `PSE-V2-PHASE-B-B08-2026-09-23-1.0`; active pointer SHA-256 is
  `cddaa00e782f5236d328985bd798815d010ee1e05ec6302d54c1733cd8a5ad2a`.
- The confirmed manifest remains `0236bc52a4408f3e175c814ff9140cf82fa198454b84fbbe0044f8cc4c557a78`.
- The previous Batch 7 catalog remains unchanged for rollback.
- Real active API: 88/88 detail parity, 10/10 calculator parity, 401 unauthenticated, and OGP scenario `#19` persisted.
- Real active UI: OGP rendered PHP31.40 and changed to PHP34.54 at 11x P/E; PCOR rendered PHP2.94; footer reported 88.
- Post-activation verification: 361 backend tests and frontend production build pass.

### Batch 9 — food, beverage, restaurants, and agriculture **STAGED**

**Frozen set:** `FB, EMI, GSMI, RFM, MAXS, PIZZA, DELM, VITA, ANI, CAT`

- Diversified staples target FCFF/SOTP; mature brands target normalized FCFF or distributions; restaurants target store-cohort FCFF; stressed and cyclical agriculture uses explicit fallback screens.
- All ten publish finite market-relative screens while those specialist cash-flow and segment bridges remain incomplete.
- DELM's USD revenue metric is explicitly converted to PHP using the dated 2026-09-22 BSP reference rate.
- ANI's delayed FY2025 annual filing and CAT's non-calendar fiscal year remain explicit in the public output.
- The cumulative candidate contains the unchanged active 88 plus the frozen ten, exactly 98 artifacts.

### Batch 9 verification evidence

- Batch output: `0 intrinsic / 10 market-relative / 0 unavailable`; all provisional and Low reliability.
- Exact values are in `docs/audit/19-pse-phase-b-batch-09.md`.
- Persistence: 10 securities, 10 receipts, 10 facts, 30 assumptions, 10 runs, and 10 verified objects.
- Manifest SHA-256: `194f099d96c4218341fb4d40e6a7849a9e2e9e8ccc306fe36c4b3ba4f01457c0`.
- Real staged API: 98/98 detail parity and 10/10 calculator parity; UI rendered and recalculated FB and exposed DELM/ANI/CAT source-period behavior.
- Automated verification: 365 backend tests and frontend production build pass.
- Active 88-company Batch 8 pointer and manifest remain unchanged; Batch 9 is absent from the serving root.

**Gate status:** ✔ Batch 9 results and local activation were separately verified and user-confirmed on 2026-09-23. No deployment, push, Batch 10, or Phase C work is authorized.

### Batch 9 local activation evidence

- `active.json` and `staged.json` select `PSE-V2-PHASE-B-B09-2026-09-23-1.0`; active pointer SHA-256 is
  `439d44cfec381664393e8b8f064d2ffece3dd0f58f95cb6e80b40c7bc3f64907`.
- The confirmed manifest remains `194f099d96c4218341fb4d40e6a7849a9e2e9e8ccc306fe36c4b3ba4f01457c0`.
- The previous Batch 8 catalog remains unchanged for rollback.
- Real active API: 98/98 detail parity, 10/10 calculator parity, 401 unauthenticated, and FB scenario `#21` persisted.
- Real active UI: FB rendered PHP50.40 and changed to PHP55.44 at 11x P/E; ANI and DELM warnings rendered; footer reported 98.
- Post-activation verification: 365 backend tests and frontend production build pass.

### Batch 10 — gaming, resorts, and hospitality **STAGED**

**Frozen set:** `BLOOM, BEL, WEB, SUN, PHR, WPI, ACE, BHI, GPH, MJC`

- Integrated resorts target property-level SOTP/FCFF; gaming platforms target regulatory-scenario FCFF; hotels target RNAV; distressed and suspended issuers retain explicit warnings.
- All ten publish finite market-relative screens while those specialist operating, property, restructuring, and capital-claim bridges remain incomplete.
- PHR's proposed asset transfer, ACE's zero revenue, and MJC's suspension and stale audit remain explicit in the public output.
- The cumulative candidate contains the unchanged active 98 plus the frozen ten, exactly 108 artifacts.

### Batch 10 verification evidence

- Batch output: `0 intrinsic / 10 market-relative / 0 unavailable`; all provisional and Low reliability.
- Exact values are in `docs/audit/20-pse-phase-b-batch-10.md`.
- Persistence: 10 securities, 10 receipts, 10 facts, 30 assumptions, 10 runs, and 10 verified objects.
- Manifest SHA-256: `d835ccf5a75b9728a76e7a01f89a7fcc1054e06cf7564070f3f9c1973dbd5018`.
- Real staged API: 108/108 detail parity and 10/10 calculator parity; UI rendered and recalculated BEL and exposed PHR/ACE/MJC limitations.
- Automated verification: 369 backend tests and frontend production build pass.
- Active 98-company Batch 9 pointer and manifest remain unchanged; Batch 10 is absent from the serving root.

**Gate status:** ✔ Batch 10 results and local activation were separately verified and user-confirmed on 2026-09-23. No deployment, push, Batch 11, or Phase C work is authorized.

### Batch 10 local activation evidence

- `active.json` and `staged.json` select `PSE-V2-PHASE-B-B10-2026-09-23-1.0`; active pointer SHA-256 is
  `08b448c02edaf2e4f93bb1f307b8f9bad85bc90279cfbbb685d35387fe74f2a6`.
- The confirmed manifest remains `d835ccf5a75b9728a76e7a01f89a7fcc1054e06cf7564070f3f9c1973dbd5018`.
- The previous Batch 9 catalog remains unchanged for rollback.
- Real active API: 108/108 detail parity, 10/10 calculator parity, 401 unauthenticated, and BEL scenario `#23` persisted.
- Real active UI: BEL rendered PHP2.39 and changed to PHP2.79 at 0.7x P/B; PHR and MJC warnings rendered; footer reported 108.
- Post-activation verification: 369 backend tests and frontend production build pass.

### Batch 11 — diversified and layered holding companies **ACTIVE LOCALLY**

**Frozen set:** `SMC, LTG, AGI, COSCO, FDC, FPH, ANS, LPZ, APO, TFHI`

- Attributable SOTP remains the intrinsic route. Incomplete component values, ownership, parent-only claims, and minority interests keep all ten at provisional, Low-reliability, market-relative P/B screens.
- Layered holdings use a 0.25/0.40/0.55 P/B band; other diversified holdings use 0.45/0.60/0.75. These are analyst screening bands, not peer studies or completed intrinsic valuations.
- Parent/subsidiary overlaps are disclosed; the per-share values are not additive. Exact figures and official PSE source links are in `docs/audit/21-pse-phase-b-batch-11.md`.

### Batch 11 verification evidence

- Exact cumulative 118-company staged catalog: 34 intrinsic / 84 market-relative / 0 unavailable; all provisional.
- Ten current source receipts, ten facts, thirty assumptions, ten runs, and ten MinIO objects verified. Superseded local draft receipts remain as immutable history.
- Deterministic twins match; final manifest SHA-256 `82481331464c9910fc80c79215ef9c0ead4d709238bd2f2d3c0f3f101f684974`.
- Real staged API: 118/118 detail parity, 10/10 calculator parity, unauthenticated 401. Real browser rendered SMC, TFHI, and LPZ with status and overlap caveats; SMC changed from PHP35.24 to PHP44.05 at 0.5x and saved.
- Full backend regression: 373 tests passed. Frontend production build passed. Existing dependency deprecation and chunk-size warnings remain.
- Active Batch 10 pointer and manifest hashes are unchanged; Batch 11 is absent from the serving root. The activation guard pins the confirmed Batch 11 hash, but has not been run.
- PSE summary-page terms restrict access/download to personal, non-commercial use unless otherwise stated. Commercial automation or redistribution rights are unconfirmed and must be reviewed before broader use.

**Staged-results gate:** live-verified and results-confirmed by the user on 2026-09-23; local activation was separately authorized afterward, as recorded below. No deployment, push, Batch 12, or Phase C work is authorized.

### Batch 11 local activation evidence

- The separately authorized local activation made `PSE-V2-PHASE-B-B11-2026-09-23-1.0` active with exactly 118 issuers; active pointer SHA-256 `795bd88681e26e70565743058887f1fa19ac8ac09a49b43c6f0900032c36c227`.
- The active 129-file catalog is byte-identical to the confirmed candidate; Batch 10's manifest remains unchanged for rollback.
- Real active API: 118/118 stored-detail parity, 10/10 calculator parity, unauthenticated 401, SMC scenario `#28` persisted.
- Real active UI: US→PH navigation and search selected SMC; its PHP35.24 screen became PHP44.05 at 0.5x, saved scenario `#29`, and displayed 118 companies. TFHI rendered its PHP175.03 screen and SMC overlap warning.
- Persistence verified ten current source receipts/facts/runs/objects and thirty assumptions; frontend production build and all 373 backend tests pass. Historical batch-builder successor guards and the active-list test were advanced to Batch 11 without changing pinned parent hashes.

**Activation status:** locally active, live-verified, and user-confirmed on 2026-09-23. No deployment, push, Batch 12, or Phase C work is authorized. Broader-use source rights remain unconfirmed.

### Batch 12 — property developers and landlords **STAGED**

**Frozen set:** `CPG, ROCK, SHNG, DD, ALLHC, CDC, ARA, PHES, RLT, BRN`

- Reviewed source paths and gaps are recorded in `docs/audit/22-pse-phase-b-batch-12.md`.
- Keep property RNAV/SOTP as the intrinsic route; until property values and common-equity claims reconcile, publish only separately labeled provisional P/B screens. CDC's post-report merger invalidates its per-share denominator, so keep CDC blocked and null until a reviewed post-merger bridge exists.
- Reuse the Batch 3 diversified-property P/B band and Batch 11 layered-holding P/B band; do not add a model or peer study. Carry source dates, units, ownership overlaps, preferred-claim warnings, and source-rights limitations explicitly.
- Build a deterministic 128-entry candidate outside the serving root. Verify source receipts and persistence, twin builds, exact artifact hashes, the real authenticated staged API and PSE page (including CDC unavailable), full backend regression, and frontend production build.
- Stop for the user's Batch 12 **results confirmation**. Do not activate, deploy, push, recover a blocked issuer, or start Batch 13/Phase C without separate authorization.

### Batch 12 verification evidence

- The exact cumulative 128-company candidate is staged outside the serving root: 34 intrinsic, 93 market-relative, 1 not available (CDC); 127 provisional and 1 blocked. The active 118-company Batch 11 remains byte-unchanged.
- Nine source-bounded P/B screens reuse reviewed property or layered-holding bands; CDC remains null after its post-report merger. Exact values, PSE links, and caveats are in `docs/audit/22-pse-phase-b-batch-12.md`.
- Ten current source receipts, ten facts, twenty-seven assumptions, ten runs, and ten MinIO objects verified. Deterministic twins match; manifest SHA-256 `91f49f05119c301ee91bdb87053cec8d5eff201af183cf730819b7cdb273327a`.
- Real staged API: 128/128 detail parity, 10/10 calculator status parity, CDC disabled/POST 400, unauthenticated 401. Real browser rendered CPG's PHP0.97 screen and PHP1.08 edited sensitivity, CDC's blocked/null page and merger sources, and DD's overlap warning.
- Full backend regression: 377 tests passed; frontend production build passed. Existing dependency deprecation and chunk-size warnings remain.
- Batch 11 active pointer and manifest hashes remain unchanged; Batch 12 is absent from serving root. The activation guard pins the confirmed Batch 12 hash, but has not been run.

**Staged-results gate:** live-verified and results-confirmed by the user on 2026-09-23; local activation was separately authorized afterward, as recorded below. No deployment, push, CDC recovery, Batch 13, or Phase C work is authorized.

### Batch 12 local activation evidence

- The separately authorized local activation made `PSE-V2-PHASE-B-B12-2026-09-23-1.0` active with exactly 128 issuers; active pointer SHA-256 `b86c8fd0fb732be6ec0ef8bacf27b6c60a72f6b719f4f5c653271b6f6b48a4e7`.
- The active 139-file catalog is byte-identical to the confirmed candidate; Batch 11's manifest remains unchanged for rollback.
- Real active API: 128/128 stored-detail parity, 10/10 calculator states, CDC POST 400, unauthenticated 401, CPG scenario `#32` persisted under the normal rate limit.
- Real active UI: US→PH navigation and search selected CPG; its PHP0.97 screen became PHP1.08 at 0.50x, saved scenario `#33`, and displayed 128 companies. CDC remained blocked/null with merger sources, and DD showed its DDMPR overlap warning.
- Persistence verified ten current source receipts/facts/runs/objects and twenty-seven assumptions; frontend production build and all 377 backend tests pass. Historical batch-builder successor guards and the active-list test were advanced to Batch 12 without changing pinned parent hashes.

**Activation status:** locally active, live-verified, and user-confirmed on 2026-09-23. No deployment, push, CDC recovery, Batch 13, or Phase C work is authorized. Broader-use source rights remain unconfirmed.

### Batch 13 — manufacturers and industrial suppliers **STAGED**

**Frozen set:** `IMI, TECH, ION, CIC, MVC, CROWN, STN, LFM, VMC, SBS`

- Reviewed source paths, periods, currency conversion, and gaps are recorded in `docs/audit/23-pse-phase-b-batch-13.md`.
- FCFF or attributable SOTP remains the intrinsic route. Until cash-flow, reinvestment, and common-claim bridges reconcile, publish only separately labeled provisional P/B screening ranges using two reviewed shared bands. Preserve USD source units and the dated BSP conversion for IMI, TECH, and ION; preserve VMC's non-December year and LFM's post-report distribution change.
- Build a deterministic 138-entry candidate outside the serving root. Verify receipt hashes and Postgres/MinIO persistence, twin builds, exact artifact hashes, the real authenticated staged API and PSE page, full backend regression, and frontend production build.
- Stop for the user's Batch 13 **results confirmation**. Do not activate, deploy, push, recover any blocked issuer, or start Batch 14/Phase C without separate authorization.

### Batch 13 verification evidence

- The exact cumulative 138-company candidate is staged outside the serving root: 34 intrinsic, 103 market-relative, 1 not available (inherited CDC); 137 provisional and 1 blocked. Active Batch 12 remains byte-unchanged.
- Ten reviewed original-currency PSE facts produce ten Low-reliability market-relative P/B screens; the three USD facts use the dated BSP PHP62.698/USD observation. Exact values, source links, and caveats are in `docs/audit/23-pse-phase-b-batch-13.md`.
- Ten current receipts, ten facts (three USD), thirty-one assumptions, ten runs, and ten MinIO objects verified. Deterministic twins match; manifest SHA-256 `beea44ae0f261aedf5c0d832253c45714ffebc50f7b59868b4a39b881740cc3c`.
- Real staged API: 138/138 detail parity, 10/10 new calculator parity, inherited CDC disabled, unauthenticated 401. Real browser rendered TECH's PHP9.72 baseline/PHP11.66 edited screen, BSP and preferred-share links, VMC's May period, LFM's post-report warning and corrected PHP10.26 display, and CDC's block.
- Full backend regression: 381 tests passed; frontend production build passed. Existing dependency deprecation and chunk-size warnings remain.
- Batch 12 active pointer and manifest hashes remain unchanged; Batch 13 is absent from serving root. The activation guard pins the confirmed Batch 13 hash, but has not been run.

**Staged-results gate:** live-verified and results-confirmed by the user on 2026-09-23; local activation was separately authorized afterward, as recorded below. No deployment, push, CDC recovery, Batch 14, or Phase C work is authorized.

### Batch 13 local activation evidence

- The separately authorized local activation made `PSE-V2-PHASE-B-B13-2026-09-23-1.0` active with exactly 138 issuers; active pointer SHA-256 `2f68c065064a9f0cd8c0c067ee6af69c7aff7bd935cfa5879153f0cb5af34170`.
- The active 149-file catalog is byte-identical to the confirmed candidate; Batch 12's manifest remains unchanged for rollback.
- Real active API: 138/138 stored-detail parity, 10/10 new calculator states, inherited CDC disabled, unauthenticated 401, TECH scenario `#36` persisted under the normal rate limit.
- Real active UI: US→PH navigation and search selected TECH; its PHP9.72 screen became PHP11.66 at 0.60x, saved scenario `#37`, and displayed 138 companies. PSE/BSP/preferred sources, VMC's May period, LFM's corrected PHP10.26 display, and CDC's blocked state rendered.
- Persistence verified ten current original-currency source receipts/facts/runs/objects (three USD facts) and thirty-one assumptions; frontend production build and all 381 backend tests pass. Historical batch-builder successor guards and active-list tests were advanced to Batch 13 without changing pinned parent hashes.

**Activation status:** locally active, live-verified, and user-confirmed on 2026-09-23. No deployment, push, CDC recovery, Batch 14, or Phase C work is authorized. Broader-use source rights remain unconfirmed.

### Batch 14 — education, healthcare, and consumer-facing operators **LOCALLY ACTIVE**

**Frozen set:** `STI, CEU, FEU, IPO, MEDIC, EURO, MRSGI, UPSON, FRUIT, KEEPR`

- Source paths, fiscal periods, original EPS components, ownership, and gaps are recorded in `docs/audit/24-pse-phase-b-batch-14.md`.
- FCFF or attributable SOTP remains the intrinsic route. Until those cash-flow and common-claim bridges reconcile, use separately labeled provisional P/E screens for the nine issuers with positive source-bounded normalized EPS and a conservative P/B screen for MEDIC. No peer study or new model is implied.
- Build a deterministic 148-entry candidate outside the serving root. Verify 26 original reported facts (eight three-part TTM bridges, one FY EPS, one interim BVPS), receipt hashes and Postgres/MinIO persistence, twin builds, artifact hashes, the real authenticated staged API and PSE page, full backend regression, and frontend production build.
- Stop for the user's Batch 14 **results confirmation**. Do not activate, deploy, push, recover CDC, or start Batch 15/Phase C without separate authorization.

### Batch 14 staged verification evidence

- Exact staged catalog `PSE-V2-PHASE-B-B14-2026-09-23-1.0` contains 148 records: 34 intrinsic, 113 market-relative and 1 unavailable; 147 provisional and inherited CDC blocked. Manifest hash `3afe1ac6f26b5e8751a714cf15776cc8e05a00304735d4b8b77b3c2922e54d38`. Ten exact low/base/high screens and source links are in Audit 24.
- Deterministic twins matched byte-for-byte, 138 parent artifacts were preserved, and Batch 13 remains active with unchanged pointer hash `2f68c065064a9f0cd8c0c067ee6af69c7aff7bd935cfa5879153f0cb5af34170`. Batch 14 activation remains locked.
- Existing Postgres/MinIO hold ten source receipts/objects, 26 original-period facts, 30 assumptions, and ten current runs. All 385 backend tests pass; frontend production build passes with its pre-existing large-chunk warning.
- Isolated staged API served 148/148 matching details and ten of ten new calculators; unauthenticated access returned 401, an edited STI case saved at PHP 2.42, and CDC remained disabled. Browser verified US→PH search/navigation, STI edit, MEDIC and KEEPR warnings/source links, and CDC blocked/null. No deployment, push, recovery, or activation occurred.

**Results gate:** user-confirmed on 2026-09-23. The confirmed manifest hash is pinned in the activation guard. Its default preflight verified all 148 artifacts and the unchanged Batch 13 active parent; an isolated temporary-root activation test passed without touching real serving. Await separate local-activation authorization. Commercial-use source rights are not established.

### Batch 14 local activation evidence

- Separately authorized local activation set `active.json` to the exact 148-entry Batch 14 manifest `3afe1ac6f26b5e8751a714cf15776cc8e05a00304735d4b8b77b3c2922e54d38`. Active pointer SHA-256 is `aa71518fbc10d3637058490f5031a5d30f74e5df9a30e0023560ec209421b2a4`; Batch 13's unchanged manifest remains available for rollback.
- Active authenticated API returned 148/148 stored-detail parity, ten of ten new calculator states, unauthenticated 401, edited STI PHP 2.42, and CDC disabled. Postgres/MinIO verified ten receipts/objects, 26 original-period facts, 30 assumptions and ten runs.
- Actual local browser switched US→PH, searched STI, showed the active 148-company footer, edited PHP 2.20→2.42 at 11× and saved scenario `#40`; MEDIC, KEEPR and CDC retained their required warning/blocked states.
- Historical replay guards and active-list assertions were advanced to the new active successor while preserving pinned parent hashes. All 385 backend tests and the frontend production build pass; only the pre-existing `crypt` deprecation and large-chunk warnings remain.

**Activation gate:** locally active, live-verified, and user-confirmed on 2026-09-23. A fresh readback still showed the confirmed 148-entry manifest and unchanged Batch 13 rollback hash. No deployment, push, CDC recovery, Batch 15, or Phase C was authorized. Commercial-use source rights remain unconfirmed.

### Batch 15 — property developers and owners **LOCALLY ACTIVE**

**Frozen set:** `ALCO, ALHI, APVI, CEI, ELI, GERI, HOUSE, KPPI, PRMX, SLI` (confirmed by the user on 2026-09-23).

- Review the exact source/period and ownership gaps in [Audit 25](../audit/25-pse-phase-b-batch-15.md). HOUSE was delisted before this valuation date, so its exact-set record must be blocked/null; do not substitute another issuer.
- For the other nine, reuse a single versioned, provisional P/B-to-reported-BVPS property screen, separate from unresolved property-level RNAV/SOTP. Preserve ALCO's March source period and relevant preferred, parent/subsidiary and accounting warnings.
- Build a deterministic 158-entry candidate outside serving. Persist ten reviewed receipts, ten original-period facts, nine sets of multiple assumptions, and ten runs in existing Postgres/MinIO; verify twin builds, all 148 inherited artifacts, exact status contract and active-pointer safety.
- Exercise the real authenticated staged API and PH page, run the focused/full backend tests and frontend production build. Stop for Batch 15 **results confirmation**. No local activation, deployment, push, HOUSE recovery, Batch 16, or Phase C is authorized.

### Batch 15 staged verification evidence

- Exact staged catalog `PSE-V2-PHASE-B-B15-2026-09-23-1.0` contains 158 records: 34 intrinsic, 122 market-relative, 2 unavailable; 156 provisional and 2 blocked. Manifest SHA-256 `641265728e673864851eeffaf3a989f9e18f41bba498aa5b523b383e60921aa3`. All 148 Batch 14 parent artifacts were byte-preserved, and deterministic twin builds matched.
- Nine provisional P/B screens and one null HOUSE block are itemized in Audit 25. HOUSE common shares were delisted 2025-10-31; its historical BVPS is retained only as a reported fact, with no current value or calculator.
- Local Postgres/MinIO verified ten reviewed receipts/objects, ten original-period facts, 27 assumptions, and ten current runs; HOUSE is marked delisted and ALCO's March 2026 period remains intact. All 389 backend tests and the frontend production build pass.
- Real staged authenticated API served 158/158 matching details and ten new calculator states, with unauthenticated 401; KPPI edited/saved at PHP2.13 and HOUSE/CDC stayed disabled. Real browser verified US→PH, KPPI edit/save, HOUSE blocked/null/source link, ALCO period caveat, and ELI/MEG overlap warning.
- Active Batch 14 pointer remains unchanged at SHA-256 `aa71518fbc10d3637058490f5031a5d30f74e5df9a30e0023560ec209421b2a4`; Batch 15 is outside serving and activation remains locked.

**Results gate:** user-confirmed on 2026-09-23. The exact manifest hash is pinned in the activation guard. Read-only preflight verified all 158 records, CDC/HOUSE blocks, and unchanged active Batch 14; an isolated temporary-root activation test passed without touching real serving. Await separate local-activation authorization. Commercial-use PSE source rights are not established.

### Batch 15 local activation — resolved runtime gate

- Separately authorized local pointer switch made the 158-record Batch 15 manifest active with confirmed hash `641265728e673864851eeffaf3a989f9e18f41bba498aa5b523b383e60921aa3`. Active pointer SHA-256 `350a44123ab089a0c484c9d600046177cfb557a05eb72da8472a959559a9c632`; Batch 14 rollback manifest remains unchanged.
- Historical builder successor guards and active-list tests were updated without changing pinned parent hashes. All 389 backend tests and the frontend production build pass.
- Live active API/UI and current persistence verification remain **unverified**: Postgres/MinIO local ports are closed, Docker Desktop's engine is unresponsive, and the persistence verifier timed out on refused connections. A normal Docker Desktop restart failed; no volume reset was performed.

**Earlier activation gate (resolved 2026-09-24):** the local services needed restoration before active 158/158 API, calculator, browser, and persistence checks could be completed. No deployment, push, HOUSE recovery, Batch 16, or Phase C was authorized.

**Infrastructure update:** Docker Desktop was restored without resetting volumes; the original Postgres and MinIO containers were healthy, and the Batch 15 persistence verifier passed on existing records/objects. Active API and browser checks were completed afterward, as recorded below. The host disk was 98% used at recovery.

### Batch 15 active runtime verification after infrastructure recovery

- The active authenticated API returned 158/158 exact stored-detail parity, ten new calculator states, unauthenticated 401, KPPI PHP2.13 edit/save, and HOUSE/CDC disabled; HOUSE calculator POST returned 400. Existing Postgres/MinIO records and objects passed readback.
- Real browser switched US→PH, searched KPPI, changed PHP1.92→2.13 and saved scenario `#45`; HOUSE blocked/null and PSE delisting source, ALCO period warning, ELI/MEG overlap, and CDC blocked/null were observed.
- The active catalog's 169 files match the confirmed candidate byte-for-byte; Batch 14's rollback manifest is unchanged. All 389 backend tests and the frontend production build pass.

**Activation gate:** live-verified and user-confirmed on 2026-09-24. Fresh readback showed the confirmed 158-entry Batch 15 manifest and unchanged Batch 14 rollback hash. No deployment, push, HOUSE recovery, Batch 16, or Phase C is authorized. Commercial-use source rights remain unconfirmed; low host disk space is still an operational risk.

### Batch 16 — food, operating, banking and mixed-business templates **ACTIVE LOCALLY**

**Frozen set:** `AXLM, BALAI, FCG, FOOD, SFI, BCOR, BNCOM, BSC, PMPC, PPC` (confirmed by the user on 2026-09-25).

- Review the exact source-period, claim, currency and route gaps in [Audit 26](../audit/26-pse-phase-b-batch-16.md). All ten have PSE-identified open common-share classes; SFI preferred shares are excluded.
- Reuse versioned finite P/E, P/B and P/S screening policies where source-bounded. The approved intrinsic route is kept separate and null until each FCFF, residual-income or SOTP claim bridge is supported. Carry an explicit dated USD/PHP observation for FOOD and retain original-currency facts.
- Build a deterministic 168-record candidate outside serving. Persist source receipts, original-period facts, assumptions and runs in existing Postgres/MinIO. Verify all 158 inherited artifacts, exact issuer/status contract, deterministic twins and active-pointer safety.
- Exercise the real staged authenticated API/calculator and PH page, then run focused/full backend tests and the frontend build. Stop for Batch 16 **results confirmation**; do not activate, deploy, push, recover blocked issuers, or start Batch 17/Phase C.

### Batch 16 staged verification evidence

- Exact staged catalog `PSE-V2-PHASE-B-B16-2026-09-25-1.0` contains 168 records: 34 intrinsic, 132 market-relative, 2 unavailable; 166 provisional and inherited CDC/HOUSE blocked. Manifest SHA-256 `729e2272ddb7674592212cef7682b496e1814e68b0d326a6b3c4e0e75b628b93`. Ten exact low/base/high screens and source periods are in Audit 26.
- At the staged-results gate, deterministic twins matched byte-for-byte and all 158 Batch 15 parent artifacts were unchanged. Active Batch 15 pointer SHA-256 was `350a44123ab089a0c484c9d600046177cfb557a05eb72da8472a959559a9c632`; Batch 16 was outside serving and activation was locked pending separate authorization.
- Existing Postgres/MinIO verified ten receipts/objects, 22 original-period facts, 30 multiple assumptions, one dated BSP USD/PHP assumption, and ten runs. The SFI/FOOD share-count facts use a non-monetary currency label rather than inventing a currency or replacing absent facts with zero.
- All 393 backend tests and the frontend build pass. The P/S calculator now supports the reviewed sub-one multiples and the PH page shows small positive SFI values with four decimal places.
- Isolated staged authenticated API served 168/168 exact stored-detail parity and all ten new calculators; AXLM edited/saved PHP2.97, SFI edited to a positive PHP0.003028754992530115, FOOD displayed the dated BSP FX source, and CDC/HOUSE stayed disabled. Browser verified US→PH search, AXLM edit/save, SFI nonzero value/preferred warning, FOOD PSE/BSP/restructuring sources, BNCOM common-capital warning, FCG fiscal period and HOUSE blocked/null.

**Results gate:** staged Batch 16 results user-confirmed on 2026-09-25. The exact manifest hash was pinned in the activation guard; default read-only preflight verified all 168 artifacts, CDC/HOUSE blocks, and unchanged active Batch 15. An isolated temporary-root activation test passed without touching real serving. Separate local-activation authorization followed, as recorded below. Commercial-use PSE source rights remain unconfirmed.

### Batch 16 local activation evidence

- The separately authorized guard switched the active pointer to the exact 168-entry Batch 16 manifest `729e2272ddb7674592212cef7682b496e1814e68b0d326a6b3c4e0e75b628b93`. Active pointer SHA-256 `f86e87818993602af954ebb7f0c334307add93c687004d59e725e13797377888`; Batch 15's rollback manifest remains unchanged.
- Live authenticated local API served 168/168 stored-detail parity and ten of ten new calculator states, while CDC/HOUSE stayed disabled and unauthenticated listing returned 401. Current Postgres/MinIO facts, runs, and source objects passed readback. The local API's normal 120/minute rate limit was respected during the bulk check.
- Signed-in browser showed the active 168-company footer, AXLM PHP2.70→2.97 calculator edit, SFI PHP0.0023, FOOD PSE/BSP source links, and HOUSE blocked/null. All 393 backend tests and the frontend production build pass.

**Activation gate:** live-verified and user-confirmed on 2026-09-25. Fresh readback still showed the exact 168-entry Batch 16 manifest and unchanged Batch 15 rollback hash. No deployment, push, CDC/HOUSE recovery, Batch 17, or Phase C work is authorized. Commercial-use PSE source rights remain unconfirmed.

### Batch 17 — infrastructure, real-asset and logistics screens **ACTIVE LOCALLY**

**Frozen set:** `SGP, VVT, PREIT, SHLPH, CHP, PHN, RCI, TFC, LBC, MRC` (confirmed by the user on 2026-09-25).

- Review source periods, ordinary-common identity, parent attribution, legal/lease claims and units in [Audit 27](../audit/27-pse-phase-b-batch-17.md). All ten were absent from the active 168-record catalog; PSE stock-data snapshots showed open ordinary common lines at their latest observed dates.
- Reuse FCFF, SOTP and sustainable-distribution intrinsic routes, but publish only separate finite P/B, P/E or P/S screens while their cash flows, ownership and capital bridges remain unresolved. TFC's August fiscal year and LBC's outstanding-versus-listed share counts receive explicit review; PREIT's lease proceedings do not imply an approved payout forecast.
- Build a deterministic 178-record candidate outside serving, persist manually reviewed fact receipts/assumptions/runs in existing Postgres/MinIO, verify all 168 inherited artifacts, exact status contract and active-pointer safety, then exercise staged API/UI and full regression. Stop for Batch 17 **results confirmation**; no local activation, deployment, push, blocked recovery or Batch 18/Phase C work is authorized.

### Batch 17 staged verification evidence

- Exact staged catalog `PSE-V2-PHASE-B-B17-2026-09-25-1.0` contains 178 records: 34 intrinsic, 142 market-relative, 2 unavailable; 176 provisional and inherited CDC/HOUSE blocked. Manifest SHA-256 `63790df2c3df426b0b5c2e6e0ec8ca3c25c204717eee71a0b3a665f95f1efb92`. Ten exact PHP low/base/high screens are in Audit 27.
- At the staged-results gate, deterministic twins matched byte-for-byte and all 168 Batch 16 artifacts were unchanged. Active Batch 16 pointer SHA-256 was `f86e87818993602af954ebb7f0c334307add93c687004d59e725e13797377888`; Batch 17 was outside serving. The exact confirmed hash was pinned in a guarded preflight before separate activation.
- Existing Postgres/MinIO verified ten reviewed receipts/objects, 15 original-period facts, 30 multiple assumptions and ten runs; replay and separate-process readback preserved counts. All 397 backend tests and the frontend production build pass.
- Isolated staged HTTP returned 178/178 stored-detail parity and ten new calculator states; TFC edited to PHP41.25, CDC/HOUSE disabled and unauthenticated listing 401. Signed-in browser verified SGP edit/save (`#48`), PREIT legal warning/source, TFC May-period label, LBC and MRC share caveats, HOUSE blocked/null and US→PH navigation. The normal active browser still showed Batch 16 and 168 companies.

**Results gate:** staged Batch 17 results user-confirmed on 2026-09-25. The exact manifest hash was pinned in the activation guard; default read-only preflight verified all 178 artifacts, CDC/HOUSE blocks, and unchanged active Batch 16. An isolated temporary-root activation test passed without touching real serving. Separate local-activation authorization followed, as recorded below. Commercial-use PSE source rights remain unconfirmed.

### Batch 17 local activation evidence

- The separately authorized guard switched the active pointer to the exact 178-entry Batch 17 manifest `63790df2c3df426b0b5c2e6e0ec8ca3c25c204717eee71a0b3a665f95f1efb92`. Active pointer SHA-256 `baea93d879687860442a50512fc6a4253b2a4a6d355df972cf59d17d5e5b5aa2`; Batch 16's rollback manifest remains unchanged.
- Live authenticated local API served 178/178 stored-detail parity and ten of ten new calculator states, while CDC/HOUSE stayed disabled and unauthenticated listing returned 401. Current Postgres/MinIO facts, runs and source receipts passed readback. All 397 backend tests and the frontend production build pass.
- Signed-in local browser switched US→PH, searched SGP in the 178-company catalog, edited PHP19.31→22.07 at 0.80× P/B and saved scenario `#49`. The session was restored with a local test-only verifier login; a later full navigation returned to login, so fresh-reload persistence was not verified.

**Activation gate:** live-verified and user-confirmed on 2026-09-25. Fresh readback still showed the exact 178-entry Batch 17 manifest and unchanged Batch 16 rollback hash. No deployment, push, CDC/HOUSE recovery, Batch 18, or Phase C work is authorized. Commercial-use PSE source rights remain unconfirmed.

### Batch 18 — banks, investment holdings and related services **ACTIVE LOCALLY**

**Frozen set:** `PBC, PTC, V, BKR, APC, IPM, SGI, CTS, REG, ECP` (confirmed by the user on 2026-09-25).

- Review exact source, ordinary-common identity, units, attribution and operating gaps in [Audit 28](../audit/28-pse-phase-b-batch-18.md). Recent PSE stock-data snapshots showed open common lines, but current status must be revalidated at future refreshes.
- Reuse residual-income, SOTP and FCFF routes, but publish only separate finite P/B screens until capital, component and cash-flow bridges are supported. IPM, REG and ECP use derived parent-common BVPS from reported parent equity and ordinary shares rather than reported total BVPS. PTC's zero parent fields are unavailable, not economic zero.
- Build a deterministic 188-record candidate outside serving; persist manually reviewed receipts, original facts, assumptions and runs in existing Postgres/MinIO. Verify all 178 inherited artifacts, exact status contract, deterministic twins, active-pointer safety, real staged API/UI and full regression. Stop for Batch 18 **results confirmation**; no local activation, deployment, push, blocked recovery or Batch 19/Phase C work is authorized.

### Batch 18 staged verification evidence

- Exact staged catalog `PSE-V2-PHASE-B-B18-2026-09-25-1.0` contains 188 records: 34 intrinsic, 152 market-relative, 2 unavailable; 186 provisional and inherited CDC/HOUSE blocked. Manifest SHA-256 `bef1cca0c41bf093c146068a688b1b35829886f281089bd6f0674142439626d1`. Ten exact PHP low/base/high screens are in Audit 28.
- At the staged-results gate, deterministic twins matched byte-for-byte and all 178 Batch 17 artifacts were unchanged. Active Batch 17 pointer SHA-256 was `baea93d879687860442a50512fc6a4253b2a4a6d355df972cf59d17d5e5b5aa2`; Batch 18 was outside serving. The exact confirmed hash was pinned in a guarded preflight before separate activation.
- Existing Postgres/MinIO verified ten reviewed receipts/objects, 16 original-period facts, 30 multiple assumptions and ten runs; replay and separate-process readback preserved counts. All 401 backend tests and the frontend production build pass.
- Isolated staged HTTP returned 188/188 stored-detail parity and ten new calculator states; ECP edited to PHP0.98874236, CDC/HOUSE disabled and unauthenticated listing 401. Signed-in browser verified PBC edit/save (`#50`), PTC zero-field warning, APC nonzero small value and no-revenue caveat, IPM parent-common basis, HOUSE blocked/null and US→PH navigation. The normal active browser still showed Batch 17 and 178 companies.

**Results gate:** staged Batch 18 results user-confirmed on 2026-09-25. The exact manifest hash was pinned in the activation guard; default read-only preflight verified all 188 artifacts, CDC/HOUSE blocks, and unchanged active Batch 17. An isolated temporary-root activation test passed without touching real serving. Separate local-activation authorization followed, as recorded below. Commercial-use PSE source rights remain unconfirmed.

### Batch 18 local activation evidence

- The separately authorized guard switched the active pointer to the exact 188-entry Batch 18 manifest `bef1cca0c41bf093c146068a688b1b35829886f281089bd6f0674142439626d1`. Active pointer SHA-256 `ad0bd9eed2daa8a7e5c1f2288ead9f8355029dd1002722bdd358eb8971b4deb0`; Batch 17's rollback manifest remains unchanged.
- Live authenticated local API served 188/188 stored-detail parity and ten of ten new calculator states, while CDC/HOUSE stayed disabled and unauthenticated listing returned 401. Current Postgres/MinIO facts, runs and source receipts passed readback. All 401 backend tests and the frontend production build pass.
- Signed-in local browser showed the active 188-company footer, edited PBC PHP35.79→40.27 at 0.90× P/B and saved scenario `#51`; PTC's zero-field caveat and HOUSE blocked/null remained visible. US→PH navigation returned to inherited AP.

**Activation gate:** live-verified and user-confirmed on 2026-09-25. Fresh readback still showed the exact 188-entry Batch 18 manifest and unchanged Batch 17 rollback hash. No deployment, push, CDC/HOUSE recovery, Batch 19, or Phase C work is authorized. Commercial-use PSE source rights remain unconfirmed.

### Batch 19 — communications, asset holdings and services **ACTIVE LOCALLY, USER-CONFIRMED**

**Frozen set:** `TBGI, IS, PHC, LODE, CPM, APL, ABA, PAX, LMG, PRIM` (confirmed by the user on 2026-09-25).

- Exact facts, source links, status reasons and PHP values are in [Audit 29](../audit/29-pse-phase-b-batch-19.md). Seven issuers have only finite Low-reliability P/B screens; IS, PAX and PRIM are blocked/null. No new intrinsic underwriting or price comparison is implied.
- At the staged-results gate, the candidate was outside the serving catalog root. It carried all 188 inherited artifacts unchanged and ten reviewed new receipts/artifacts. Batch 18 remained locally served; separate activation was not yet authorized at that gate.

### Batch 19 staged verification evidence

- Exact candidate `PSE-V2-PHASE-B-B19-2026-09-25-1.0`: 198 records, 34 intrinsic, 159 market-relative, 5 unavailable; 193 provisional and 5 blocked. Manifest SHA-256 `2eb66b33f1dc545d6ae5584040db43234699911cc643ece3f98b5b3613c31b2f`. Deterministic twins and parent artifact preservation passed.
- Local Postgres/MinIO readback verified ten reviewed receipts/objects, 30 original-period facts, 21 multiple assumptions and ten staged runs. Three focused tests and all 404 backend tests passed; frontend production build passed with the existing large-chunk warning.
- Isolated staged HTTP returned 198/198 stored-detail parity, seven enabled and three blocked new calculators, inherited CDC/HOUSE blocked, TBGI edit at 0.60× P/B, and unauthenticated 401. Signed-in staged browser showed TBGI, LODE's book-value warning and the IS/PAX/PRIM null states. The footer now uses the detail artifact's authoritative catalog count. Temporary browser test accounts were removed.
- The normal local API still serves active Batch 18 with 188 records. Its active pointer SHA-256 remains `ad0bd9eed2daa8a7e5c1f2288ead9f8355029dd1002722bdd358eb8971b4deb0`.

**Results gate:** user-confirmed on 2026-09-25. The exact 198-entry manifest hash `2eb66b33f1dc545d6ae5584040db43234699911cc643ece3f98b5b3613c31b2f` was pinned in a read-only-by-default activation guard. Preflight and isolated temporary-root activation rehearsal passed while real serving stayed on Batch 18/188; active TBGI returned 404. Four focused Batch 19 tests, all 405 backend tests and the frontend build passed. Separate local-activation authorization followed, as recorded below. Commercial-use PSE source rights, original-filing content lineage and specialist intrinsic inputs remain unresolved; source receipt hashes are not filing hashes.

### Batch 19 local activation evidence

- A separately authorized guard set the real local active pointer to the exact 198-entry Batch 19 manifest `2eb66b33f1dc545d6ae5584040db43234699911cc643ece3f98b5b3613c31b2f`. Active pointer SHA-256 is `f4002d7a63c89938df3380f0d64da00742b6717b9ea65a1716d72810735e214e`; Batch 18's rollback manifest remains `bef1cca0c41bf093c146068a688b1b35829886f281089bd6f0674142439626d1`.
- Live authenticated local API served 198/198 exact stored-detail parity and ten new calculator states; CDC/HOUSE remained disabled and unauthenticated listing returned 401. Postgres/MinIO readback matched ten receipts/objects, 30 original facts, 21 assumptions and ten runs. Historical builder successor guards and active-list tests were updated without changing old manifests; 103 focused Phase B tests, all 405 backend tests and frontend build passed.
- Signed-in local PH browser displayed the 198-company footer, interacted with the seven-day calendar, searched/opened ABA, changed TBGI PHP0.08→0.09 at 0.60× P/B, displayed LODE's book-value discrepancy, and showed IS/PAX/PRIM blocked/null with no calculator. Temporary test accounts were removed.

**Activation gate:** locally active, live-verified, and user-confirmed on 2026-09-25. Final read-only checks still found the exact 198-entry Batch 19 manifest, active pointer SHA-256 `f4002d7a63c89938df3380f0d64da00742b6717b9ea65a1716d72810735e214e`, unchanged Batch 18 rollback hash, and live authenticated Batch 19/198 API with TBGI available and PRIM blocked. No deployment, push, CDC/HOUSE/IS/PAX/PRIM recovery, Batch 20, or Phase C work is authorized. Commercial-use PSE source rights remain unconfirmed.

### Batch 20 — property, energy, operating services and holdings **ACTIVE LOCALLY, USER-CONFIRMED**

**Frozen set:** `MACAY, DMW, HTI, REDC, TOP, XG, HI, MBC, LOTO, PRC` (confirmed by the user on 2026-09-25).

- Exact sources, parent-equity/common-share bridges, warnings and PHP values are in [Audit 30](../audit/30-pse-phase-b-batch-20.md). All ten new outputs are provisional, Low-reliability market-relative P/B screens; intrinsic scenarios stay null. Inherited CDC/HOUSE/IS/PAX/PRIM remain blocked.
- At the staged-results gate, candidate `PSE-V2-PHASE-B-B20-2026-09-25-1.0` was outside serving and contained exact 198 inherited artifacts plus ten reviewed new receipts/artifacts. Batch 19 was still active; separate activation had not yet been authorized.

### Batch 20 staged verification evidence

- The exact 208-entry candidate has 34 intrinsic, 169 market-relative and 5 unavailable records; 203 provisional and 5 blocked. Manifest SHA-256 `50227c8db032133bf191da95ba4f8b9de94b717dc423fa8b027607a9b061ea23`. Deterministic twins and parent artifact preservation passed.
- Existing Postgres/MinIO readback verified ten reviewed receipts/objects, 30 original-period facts, 30 multiple assumptions and ten staged runs. Three focused Batch 20 tests, all 408 backend tests and the frontend production build passed.
- Isolated staged HTTP returned 208/208 stored-detail parity, ten new enabled calculators, five inherited disabled calculators, TOP edit at 0.60× P/B, and unauthenticated 401. Signed-in staged browser showed TOP calculator/calendar/source links, REDC search navigation, HI's parent-equity warning and inherited PRIM blocked/null. The temporary browser test account was removed.
- A fresh local active API check still served Batch 19/198 and TOP 404; active pointer SHA-256 remained `f4002d7a63c89938df3380f0d64da00742b6717b9ea65a1716d72810735e214e`.

**Results gate:** user-confirmed on 2026-09-25. The exact 208-entry manifest hash `50227c8db032133bf191da95ba4f8b9de94b717dc423fa8b027607a9b061ea23` was pinned in a read-only-by-default activation guard. Preflight and isolated temporary-root activation rehearsal passed while real serving stayed on Batch 19/198; active TOP returned 404. Four focused Batch 20 tests, all 409 backend tests and the frontend build passed. Separate local-activation authorization followed, as recorded below. Commercial-use PSE source rights, original-filing content lineage and specialist intrinsic inputs remain unresolved; source receipt hashes are not filing hashes.

### Batch 20 local activation evidence

- A separately authorized guard set the real local active pointer to the exact 208-entry Batch 20 manifest `50227c8db032133bf191da95ba4f8b9de94b717dc423fa8b027607a9b061ea23`. Active pointer SHA-256 is `cac24ffdb3f4a795ee3c204bd48c096d31491b1874a7e34580c156eaa5a1e20f`; Batch 19's rollback manifest remains `2eb66b33f1dc545d6ae5584040db43234699911cc643ece3f98b5b3613c31b2f`.
- Live authenticated local API served 208/208 exact stored-detail parity and ten new enabled calculator states; five inherited unavailable calculators stayed disabled and unauthenticated listing returned 401. Postgres/MinIO readback matched ten receipts/objects, 30 facts, 30 assumptions and ten runs. Historical successor guards and active-list tests were advanced without changing older manifests; 107 focused Phase B tests, all 409 backend tests and frontend build passed.
- Signed-in local PH browser displayed the 208-company footer, interacted with the calendar, searched/opened REDC, changed TOP PHP0.15→0.18 at 0.60× P/B, displayed HI's parent-equity warning and kept PRIM blocked/null. Two earlier post-scan attempts showed an empty search dropdown despite a healthy catalog; the clean run passed and the intermittent symptom is in the PSE learning/backlog. Temporary test accounts were removed.

**Activation gate:** locally active, live-verified, and user-confirmed on 2026-09-25. Final read-only checks still found the exact 208-entry Batch 20 manifest, active pointer SHA-256 `cac24ffdb3f4a795ee3c204bd48c096d31491b1874a7e34580c156eaa5a1e20f`, unchanged Batch 19 rollback hash, and live authenticated Batch 20/208 API with TOP available and PRIM blocked. The intermittent PH search-hydration symptom remains logged for follow-up. No deployment, push, blocked recovery, Batch 21 or Phase C work is authorized. Commercial-use PSE source rights remain unconfirmed.

### Batch 21 — property and holding-company screens **LOCALLY ACTIVE, USER-CONFIRMED**

**Frozen set:** `IDC, JOH, KEP, LPC, DWC, OM, MHC, PHA, SPM, SRDC` (confirmed by the user on 2026-09-25).

- Exact sources, scoped equity/common-share bridges, warnings and PHP values are in [Audit 31](../audit/31-pse-phase-b-batch-21.md). Ten new outputs are provisional, Low-reliability market-relative P/B screens; intrinsic scenarios stay null. LPC, SPM and SRDC use explicitly labeled total-book proxies where parent attribution is unavailable. Inherited CDC/HOUSE/IS/PAX/PRIM remain blocked.
- Candidate `PSE-V2-PHASE-B-B21-2026-09-25-1.0` contains exact 208 inherited artifacts plus ten reviewed new receipts/artifacts. It remained outside serving at the staged-results gate; subsequent separately authorized local activation is recorded below. No deployment, push, blocked recovery, next batch or Phase C was authorized.

### Batch 21 staged verification evidence

- The exact 218-entry candidate has 34 intrinsic, 179 market-relative and 5 unavailable records; 213 provisional and 5 blocked. Manifest SHA-256 `eddf03189b851c60a4c8166de1cf8d57ad37ea7b0510791b152ae3e939a992a3`. Deterministic twins and parent artifact preservation passed.
- Existing Postgres/MinIO readback verified ten reviewed receipts/objects, 30 original-period facts, 30 multiple assumptions and ten staged runs. PHA's PHP-thousands units and SPM's March 2026 interim survived readback. Three focused Batch 21 tests, all 412 backend tests and the frontend production build passed.
- Isolated staged HTTP returned 218/218 stored-detail parity, ten new enabled calculators, five inherited disabled calculators, LPC edit at 0.50× P/B, and unauthenticated 401. Signed-in staged browser showed LPC small-value calculator/calendar/source links, PHA search and unit warning, SPM's March period, SRDC total proxy and inherited PRIM blocked/null. The temporary browser test account was removed.
- The shared PH UI currently shows only two decimals once a value reaches PHP0.01, so close small-value estimates may display alike even while catalog/API values remain distinct. The issue is parked in the backlog rather than changing active Batch 20 UI during this staging gate.
- A fresh local active API check still served Batch 20/208 and IDC 404; active pointer SHA-256 remained `cac24ffdb3f4a795ee3c204bd48c096d31491b1874a7e34580c156eaa5a1e20f`.

**Results gate:** user-confirmed on 2026-09-25. The exact 218-entry manifest hash `eddf03189b851c60a4c8166de1cf8d57ad37ea7b0510791b152ae3e939a992a3` is pinned in a read-only-by-default activation guard. Preflight and isolated temporary-root activation rehearsal passed while real serving stayed on Batch 20/208; active IDC returned 404. Four focused Batch 21 tests, all 413 backend tests and the frontend build passed. Await separate local-activation authorization. The LPC display-precision caveat, commercial-use PSE source rights, original-filing content lineage and specialist intrinsic inputs remain unresolved; source receipt hashes are not filing hashes.

**Local activation gate:** separately authorized, live-verified and user-confirmed on 2026-09-25. The pinned 218-entry manifest is active locally; pointer SHA-256 `7d20dc192b2859f109f8400158592e7ce6cd33c4f19e3ccdf718f3dffac0fe0c`, Batch 21 manifest SHA-256 `eddf03189b851c60a4c8166de1cf8d57ad37ea7b0510791b152ae3e939a992a3`, and preserved Batch 20 rollback manifest SHA-256 `50227c8db032133bf191da95ba4f8b9de94b717dc423fa8b027607a9b061ea23`. Real active HTTP returned 218/218 stored-detail parity, ten enabled new calculators and five inherited blocked; signed-in PH UI exercised the calendar, calculator, search and warning states. Active persistence readback, 114 focused Phase B tests, 413 backend tests and frontend build passed. A quadratic catalog-list validation timeout was fixed without relaxing artifact hash checks; measured active list response was 0.186 seconds. Final read-only preflight and authenticated local API again confirmed active Batch 21/218, IDC market-relative-only and PRIM not-available. Do not infer deployment, push, blocked recovery, Batch 22 or Phase C. LPC precision and source-rights caveats remain.

### Batch 22 — bank, resource, holding and operating screens **LOCALLY ACTIVE, USER-CONFIRMED**

**Frozen set:** `CSB, ORE, ECVC, GREEN, EGRN, ENEX, JAS, NI, WIN, PA` (confirmed by the user on 2026-09-25).

- Exact PSE source paths, scoped equity/common-share bridges, limitations and PHP values are in [Audit 32](../audit/32-pse-phase-b-batch-22.md). The ten new outputs are provisional Low-reliability market-relative P/B screens, not intrinsic values. CSB, ECVC and JAS use explicitly labeled total-equity proxies; inherited CDC/HOUSE/IS/PAX/PRIM remain blocked.
- Candidate `PSE-V2-PHASE-B-B22-2026-09-25-1.0` contains 228 entries (34 intrinsic, 189 relative, five unavailable), with all 218 inherited artifacts byte-identical. Manifest SHA-256 `f173bcc9b8854563f5bce9655c2f7c88e08187e9447ae115c1b012e5bb6c9f26`.
- Postgres/MinIO readback, deterministic twins, independent calculation reconciliation, 228/228 staged authenticated API detail parity, ten enabled new calculators, inherited blocked behavior, signed-in staged PSE page, all 417 backend tests and frontend build passed. The real active API still returned Batch 21/218 and CSB 404.
- At the staged-results gate, the results were user-confirmed on 2026-09-25. The exact 228-entry manifest hash was pinned in a read-only-by-default activation guard. Preflight and isolated temporary-root activation rehearsal passed while real serving stayed on Batch 21/218; active CSB returned 404. Five focused Batch 22 tests, all 418 backend tests and frontend build passed. Separate local activation was subsequently authorized and verified below. Commercial-use PSE source rights and original-filing content lineage remain unresolved.

**Local activation gate:** separately authorized, live-verified and user-confirmed on 2026-09-25. The pinned 228-entry manifest is active locally; pointer SHA-256 `8355c4838a6ff48ebdcb06d582570b391e9f29af6d2bcb29ce3a81ef3411f193`, Batch 22 manifest SHA-256 `f173bcc9b8854563f5bce9655c2f7c88e08187e9447ae115c1b012e5bb6c9f26`, and preserved Batch 21 rollback manifest SHA-256 `eddf03189b851c60a4c8166de1cf8d57ad37ea7b0510791b152ae3e939a992a3`. Real active HTTP returned 228/228 stored-detail parity, ten enabled new calculators and five inherited blocked; signed-in PH UI exercised the calendar, calculator, search and warning states. Active persistence readback, 119 focused Phase B/API tests, full backend regression and frontend build passed. Final read-only preflight and authenticated local API again confirmed active Batch 22/228, CSB market-relative-only and PRIM not-available. Do not infer deployment, push, blocked recovery, Batch 23 or Phase C. Source-rights and specialist-intrinsic caveats remain.

### Batch 23 — class-aware mining, industrial and holding screens **LOCALLY ACTIVE, USER-CONFIRMED**

**Frozen set:** `BC, CA, LC, ATN, OPM, FJP, DIZ, IMP, FERRO, ABG` (confirmed by the user on 2026-09-25).

- [Audit 33](../audit/33-pse-phase-b-batch-23.md) contains the official source paths, class-equity bridges, exact PHP sensitivities and two explicit null blockers. Eight new records are provisional Low-reliability market-relative P/B screens; BC and OPM are blocked/null for unresolved convertible preferred claims and an unavailable approved USD/PHP conversion, respectively. No intrinsic values are implied.
- Candidate `PSE-V2-PHASE-B-B23-2026-09-25-1.0` contains 238 entries (34 intrinsic, 197 relative, seven unavailable), with all 228 inherited artifacts byte-identical. Manifest SHA-256 `84f33618d2cf063028ec0bac58e5742e1dbd0f51a595ed7f625a4d26ccbfe631`.
- At the staged gate, ten reviewed receipts, 35 original-period facts, ten reviewed class denominators, 24 finite multiple assumptions and ten staged runs read back from Postgres/MinIO. Deterministic twins, independent calculations, 238/238 staged API detail parity, eight enabled new calculators, seven disabled blocked calculators, signed-in staged PSE page, all 422 backend tests and frontend build passed. The real active API still served Batch 22/228 and BC 404 then.
- At the staged-results gate, results were user-confirmed on 2026-09-25. The exact 238-entry manifest hash was pinned in a read-only-by-default activation guard. Preflight and isolated temporary-root activation rehearsal passed while real serving stayed on Batch 22/228; active BC returned 404. Five focused Batch 23 tests, all 423 backend tests and frontend build passed. Separate local activation was subsequently authorized and verified below. Commercial-use PSE source rights, original-filing content lineage, approved USD/PHP and specialist intrinsic inputs remain unresolved.

**Local activation gate:** separately authorized, live-verified and user-confirmed on 2026-09-25. The pinned 238-entry manifest is active locally; pointer SHA-256 `5ad7fb97f37a443d025f09841bee2643222f201d1fbd6af527e8bf4c40ccd8c4`, Batch 23 manifest SHA-256 `84f33618d2cf063028ec0bac58e5742e1dbd0f51a595ed7f625a4d26ccbfe631`, and preserved Batch 22 rollback manifest SHA-256 `f173bcc9b8854563f5bce9655c2f7c88e08187e9447ae115c1b012e5bb6c9f26`. Real active HTTP returned 238/238 stored-detail parity, eight enabled new calculators and seven blocked/disabled; signed-in PH UI exercised the calendar, calculator, search, class warnings and blocked states. Active persistence readback, 124 focused Phase B/API tests, all 423 backend tests and frontend build passed. Final read-only preflight and authenticated local API again confirmed active Batch 23/238, CA market-relative-only and BC/OPM not-available. Do not infer deployment, push, blocked recovery, Batch 24 or Phase C. Source-rights, USD/PHP and specialist-intrinsic caveats remain.

### Batch 24 — source-claim and CAD-currency screens **LOCALLY ACTIVE, USER-CONFIRMED**

**Frozen set:** `AB, FPI, FAF, BH, GEO, UPM, MA, X, MFC, SLF` (confirmed by the user on 2026-09-25).

- [Audit 34](../audit/34-pse-phase-b-batch-24.md) contains official source paths, exact PHP sensitivities and seven explicit null blockers. Three new outputs are provisional Low-reliability market-relative P/B screens; the other seven are blocked/null for negative or near-exhausted equity, material dilution, or missing approved CAD/PHP and insurer-capital inputs. No intrinsic values are implied.
- Candidate `PSE-V2-PHASE-B-B24-2026-09-25-1.0` contains 248 entries (34 intrinsic, 200 relative, 14 unavailable), with all 238 inherited artifacts byte-identical. Final manifest SHA-256 `89b78a2fa1597a5b4d8cfd1e606f567554be18c222d7c782bc02a5879fc27ef0`.
- At the staged gate, Postgres/MinIO readback, deterministic twins, independent calculations, 248/248 exact staged API parity against the corrected final manifest, three enabled new calculators, 14 disabled blocked calculators, 427 backend tests and frontend build passed. The shortened signed-in staged PSE page passed representative calculator, search, calendar, source and blocked-state checks. Rapid browser navigation after a bulk API scan hit the shared limiter twice; the later isolated browser run passed, and the rate-limit learning was updated.
- At the staged-results gate, results were user-confirmed on 2026-09-25. The exact 248-entry manifest hash was pinned in a read-only-by-default activation guard. Preflight and isolated temporary-root activation rehearsal passed while real serving stayed on Batch 23/238; active AB returned 404. Five focused Batch 24 tests, all 428 backend tests and frontend build passed. Separate local activation was subsequently authorized and verified below. Commercial-use source rights, original-filing content lineage, approved CAD/PHP and specialist inputs remain unresolved.

**Local activation gate:** separately authorized, live-verified and user-confirmed on 2026-09-25. The pinned 248-entry manifest is active locally; pointer SHA-256 `f3afe66297cf939e595bbcfc12ae7fb2c6b2ee19ca4851e0dbd2485a1dc67e53`, Batch 24 manifest SHA-256 `89b78a2fa1597a5b4d8cfd1e606f567554be18c222d7c782bc02a5879fc27ef0`, and preserved Batch 23 rollback manifest SHA-256 `84f33618d2cf063028ec0bac58e5742e1dbd0f51a595ed7f625a4d26ccbfe631`. Real active HTTP returned 248/248 stored-detail parity, three enabled new calculators and 14 blocked/disabled; signed-in PH UI exercised the calendar, calculator, search, class warning and blocked states. Active persistence readback, 129 focused Phase B/API tests, all 428 backend tests and frontend build passed. Final read-only preflight and authenticated local API again confirmed active Batch 24/248, BH market-relative-only and MFC not-available, with Batch 23 rollback unchanged. Do not infer deployment, push, blocked recovery, Batch 25 or Phase C. Source-rights, CAD/PHP and specialist-input caveats remain.

### Batch 25 — fund, small-cap and suspended-common screens **LOCALLY ACTIVE, USER-CONFIRMED**

**Frozen set:** `FFI, FYN, MAH, MED, MG, ZHI, LTL, VLL, VREIT, ALLDY` (confirmed by the user on 2026-09-25).

- [Audit 35](../audit/35-pse-phase-b-batch-25.md) records the official source paths, exact PHP low/base/high market-relative results, seven null blockers and source-rights caveats. FFI, MED and MG have finite Low-reliability book screens; no new intrinsic valuations are claimed. FYN's preferred claim, MAH's negative parent equity, ZHI's near-zero equity, LTL's absent reviewed facts and the stale/suspended VLL/VREIT/ALLDY cases remain blocked.
- Candidate `PSE-V2-PHASE-B-B25-2026-09-25-1.0` has 258 records (34 inherited intrinsic, 203 market-relative, 21 unavailable); all 248 parent artifacts are byte-identical. Manifest SHA-256 `ae8f1e0b0fc13eab2f39ea5a6f7c2d419cb425ef792c845f8f9f89f1005a308c`.
- Deterministic twins, independent `Decimal` calculations, Postgres/MinIO readback, exact 258/258 staged authenticated API parity, representative signed-in PH browser flow, 432 backend tests and frontend build passed. Active Batch 24/248 still served, with LTL 404 outside the staged server.

**Results gate:** user-confirmed on 2026-09-25. The exact 258-entry manifest hash `ae8f1e0b0fc13eab2f39ea5a6f7c2d419cb425ef792c845f8f9f89f1005a308c` is pinned in a read-only-by-default activation guard. Preflight and isolated temporary-root activation rehearsal passed while real serving stayed on Batch 24/248; active LTL returned 404 and staged LTL remained blocked/null. Six focused tests, all 434 backend tests and frontend build passed. Await separate local-activation authorization. Do not infer recovery, push, merge, deployment, Batch 26 or Phase C. Original-filing content lineage, commercial-use PSE source rights and specialist intrinsic inputs remain unresolved.

**Local activation gate:** separately authorized, live-verified and user-confirmed on 2026-09-25. The pinned 258-entry manifest is active locally; pointer SHA-256 `c476841f32dcaeef1995477f566ddfc0ce0c6ea6fddcaf490342c519b2c9338e`, Batch 25 manifest SHA-256 `ae8f1e0b0fc13eab2f39ea5a6f7c2d419cb425ef792c845f8f9f89f1005a308c`, and preserved Batch 24 rollback manifest SHA-256 `89b78a2fa1597a5b4d8cfd1e606f567554be18c222d7c782bc02a5879fc27ef0`. Real active HTTP returned 258/258 stored-detail parity, three enabled new calculators and 21 blocked/disabled; signed-in PH UI exercised the calendar, calculator, search, sources and blocked states. Active persistence readback, all 434 backend tests and frontend build passed. Historical builder guards and active-list assertions followed the exact successor without changing prior manifest hashes. Final read-only preflight and authenticated local API again confirmed Batch 25/258, FFI market-relative-only and LTL/VREIT not-available, with Batch 24 rollback unchanged. Do not infer deployment, push, blocked recovery, Batch 26 or Phase C. Source-rights and specialist-input caveats remain.

### Batch 26 — suspended common-share and claim screens **LOCALLY ACTIVE, USER-CONFIRMED**

**Frozen set:** `DHI, HOME, MM, STR, VLC, UNH, PNX, ROX, INFRA, I` (confirmed by the user on 2026-09-25).

- [Audit 36](../audit/36-pse-phase-b-batch-26.md) records official PSE source paths, the exact MM PHP low/base/high historical market-relative sensitivity, nine null blockers and source-rights caveats. No new intrinsic value is claimed. Current source periods and common claims are not silently inferred for suspended names.
- Candidate `PSE-V2-PHASE-B-B26-2026-09-25-1.0` has 268 records (34 inherited intrinsic, 204 market-relative, 30 unavailable), with all 258 inherited artifacts byte-identical. Manifest SHA-256 `d1d929b164286168f77d6e0e9d9dbbe93f7af4f73610cc47ec20b88606ebf60a`.
- Deterministic twins, independent `Decimal` calculation, Postgres/MinIO readback, exact 268/268 staged authenticated API parity, a signed-in PH browser flow, 438 backend tests and frontend build passed. The active local API still served Batch 25/258 and MM 404.

**Results gate:** user-confirmed on 2026-09-25. The exact 268-entry manifest hash `d1d929b164286168f77d6e0e9d9dbbe93f7af4f73610cc47ec20b88606ebf60a` is pinned in a read-only-by-default activation guard. Preflight and isolated temporary-root activation rehearsal passed while real serving stayed on Batch 25/258; active MM returned 404 and staged MM remained historical market-relative-only. Six focused tests, all 440 backend tests and frontend build passed. Await separate local-activation authorization. Do not infer recovery, push, merge, deployment, Batch 27 or Phase C. Original-filing content lineage, commercial-use PSE source rights and specialist intrinsic inputs remain unresolved.

**Local activation gate:** separately authorized, live-verified and user-confirmed on 2026-09-25. The pinned 268-entry manifest is active locally; pointer SHA-256 `ebc67e971ec52323e56ce2b3e909dbf71d4f0400c237f3746ea0d80a5667f371`, Batch 26 manifest SHA-256 `d1d929b164286168f77d6e0e9d9dbbe93f7af4f73610cc47ec20b88606ebf60a`, and preserved Batch 25 rollback manifest SHA-256 `ae8f1e0b0fc13eab2f39ea5a6f7c2d419cb425ef792c845f8f9f89f1005a308c`. Real active HTTP returned 268/268 stored-detail parity, one enabled new MM calculator and 30 blocked/disabled; signed-in PH UI exercised the calendar, calculator, search, sources and blocked states. Active persistence readback, all 440 backend tests and frontend build passed. Historical builder guards and active-list assertions followed the exact successor without changing prior manifest hashes. Final read-only preflight and authenticated local API again confirmed Batch 26/268, MM market-relative-only and DHI/LTL not-available, with Batch 25 rollback unchanged. Do not infer deployment, push, blocked recovery, Batch 27 or Phase C. Source-rights and specialist-input caveats remain.

### Batch 27 — suspended common claims and incomplete reporting **LOCALLY ACTIVE, USER-CONFIRMED**

**Frozen set:** `AR, BMM, CYBR, MGH, MJIC, PNC, PORT, SOC, T, TUBIG` (confirmed by the user on 2026-09-25).

- [Audit 37](../audit/37-pse-phase-b-batch-27.md) records the official PSE source paths, dated and original-unit fact receipts, and individual reasons all ten outcomes remain blocked/null. No new finite intrinsic or market-relative estimate is claimed.
- Candidate `PSE-V2-PHASE-B-B27-2026-09-25-1.0` has 278 records (34 inherited intrinsic, 204 inherited market-relative, 40 unavailable); all 268 Batch 26 artifacts remain byte-identical. Manifest SHA-256 `9799ff5e8f536d914d1addaa37b10946b402f06c6ec6fe8aca8e570454b44f85`.
- Deterministic twins, Postgres/MinIO readback, exact 278/278 staged authenticated API parity, signed-in PH browser checks, 444 backend tests and frontend build passed. The active local API still served Batch 26/268 and returned 404 for PNC/AR.

**Results gate:** user-confirmed on 2026-09-25. The exact 278-entry manifest SHA-256 `9799ff5e8f536d914d1addaa37b10946b402f06c6ec6fe8aca8e570454b44f85` is pinned in a read-only-by-default activation guard. Preflight and isolated temporary-root activation rehearsal passed while real serving stayed on Batch 26/268; active PNC/AR returned 404 and staged PNC/AR remained blocked/null. Six focused tests, all 446 backend tests and frontend build passed. Await separate local-activation authorization. Do not infer recovery, push, merge, deployment, Batch 28 or Phase C. Original-filing content lineage, commercial-use PSE source rights and specialist intrinsic inputs remain unresolved.

**Local activation gate:** separately authorized, live-verified and user-confirmed on 2026-09-25. The pinned 278-entry manifest is active locally; pointer SHA-256 `c1edb4294e00c8e986e5336b2f3b1a226e08b3dd8a074bc1169e4f3ec8218e08` and Batch 26 rollback manifest SHA-256 `d1d929b164286168f77d6e0e9d9dbbe93f7af4f73610cc47ec20b88606ebf60a` remain intact. Real authenticated active HTTP returned 278/278 stored-detail parity, all ten new calculators disabled and all 40 blocked calculators disabled. Signed-in PH UI exercised US→PH, 278-company search, PNC/AR blockers, PNC source links/calendar and inherited MM's 0.50× edit to displayed PHP0.20. Active persistence readback, all 446 backend tests and frontend build passed. Historical builder guards and active-list assertions followed the exact successor; Batch 24–26 preflights refuse a backward activation. Fresh read-only preflight and authenticated local API again confirmed Batch 27/278, PNC null/unavailable and MM market-relative-only with the Batch 26 rollback hash intact. No deployment, push, blocked recovery, Batch 28 or Phase C is implied. Source-rights and specialist-input caveats remain.

### Batch 28 — final four ordinary-common additions **LOCALLY ACTIVE, USER-CONFIRMED**

**Frozen set:** `AAA, EG, NXGEN, PTT` (the user-approved exception to ten-name batches on 2026-09-26).

- [Audit 38](../audit/38-pse-phase-b-batch-28.md) records official PSE source paths and original-unit receipts. NXGEN has a separate Low-reliability market-relative PHP0.112304347 / PHP0.179686955 / PHP0.247069563 low/base/high P/B screen using parent, not total, equity. AAA, EG and PTT remain null/blocked; no new intrinsic value is claimed.
- Candidate `PSE-V2-PHASE-B-B28-2026-09-26-1.0` has 282 records (34 inherited intrinsic, 205 market-relative, 43 unavailable); all 278 Batch 27 artifacts remain byte-identical. Manifest SHA-256 `8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7`.
- Deterministic twins, independent `Decimal` replay, Postgres/MinIO readback, exact 282/282 staged authenticated API parity, signed-in PH browser checks, 450 backend tests and frontend build passed. The active local API still served Batch 27/278 and returned 404 for AAA/NXGEN.

**Results gate:** user-confirmed on 2026-09-26. The exact 282-entry manifest SHA-256 `8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7` is pinned in a read-only-by-default activation guard. Preflight and isolated temporary-root activation rehearsal passed while real serving stayed on Batch 27/278; active AAA/NXGEN returned 404 and staged NXGEN remained market-relative-only. Six focused tests, all 452 backend tests and frontend build passed. Await separate local-activation authorization. Do not infer blocked recovery, push, merge, deployment, another batch or Phase C. Original-filing content lineage, commercial-use PSE source rights and specialist intrinsic inputs remain unresolved.

**Local activation gate:** separately authorized, live-verified and user-confirmed on 2026-09-26. The pinned 282-entry manifest is active locally; pointer SHA-256 `50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92` and Batch 27 rollback manifest SHA-256 `9799ff5e8f536d914d1addaa37b10946b402f06c6ec6fe8aca8e570454b44f85` remain intact. All 287 served files are byte-identical to the staged candidate. Real authenticated active HTTP returned 282/282 stored-detail parity, one of four new calculators enabled and all 43 blocked calculators disabled. Signed-in PH UI exercised US→PH, the 282-company search, NXGEN market-relative values/calculator/source links/calendar, and AAA/EG/PTT blocked states. Active Postgres/MinIO readback, all 452 backend tests and frontend build passed. Historical builder guards and active-list assertions followed the exact successor; Batch 24–27 preflights refuse a backward activation. Fresh read-only preflight and authenticated local API again confirmed Batch 28/282, NXGEN market-relative-only and AAA null/unavailable, with the Batch 27 rollback hash intact. No deployment, push, blocked recovery, another batch or Phase C is implied. Source-rights and specialist-input caveats remain.

## Later gates

- **Remaining Phase B:** Batch 28 is a separately frozen four-company exception because the reviewed PSE directory has no further in-scope unmodeled ordinary-common names in that snapshot. Any further additions require a new source-verified listing or a separately approved scope change. No automatic recovery, activation or next-batch work.
- **Phase C:** one scheduler for changed filings, approved macro observations, and licensed prices only after the
  pilot survives a real filing refresh. The [supervised AP/BPI/RLC/RCR entry findings](../audit/39-pse-phase-c-entry-pilot.md) were user-confirmed on 2026-09-26; zero approved issuers and no completed pilot valuation refresh mean this gate remains closed. No automation or promotion is implied.
- **Deferred:** backtesting, full-exchange numerical coverage, additional models, agents, microservices, Airflow,
  vector databases, Monte Carlo, machine-learned routing, and live trading feeds.
