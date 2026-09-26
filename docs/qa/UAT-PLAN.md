# FinSight UAT plan

## PSE/US valuation workspace parity

### TC-PSE-01 — Market switch and route

1. Sign in and open `/valuation/AAPL`.
2. Select PSE and confirm navigation to `/pse/AP`.
3. Select US and confirm navigation back to `/valuation/AAPL`.

Expected: both pages use the same workspace structure and the selected market is visually active.  
Result: [x] Pass [ ] Fail — AAPL → PH opened `/pse/AP`; PH → US returned to `/valuation/AAPL`.

### TC-PSE-02 — Seven-day calendar and sections

1. Open `/pse/AP`.
2. Select an earlier calendar date, then return to latest.
3. Open each valuation section.

Expected: seven newest-first dates, viewed-state progress, and five keyboard/clickable sections behave like US.  
Result: [x] Pass [ ] Fail — earlier/latest dates, viewed count, and five valuation tabs rendered on the live AP page.

### TC-PSE-03 — AP intrinsic calculator

1. Open AP and select Base.
2. Change one assumption and observe the selected value change.
3. Reset and confirm the published base returns.

Expected: only Base changes during the edit; locked evidence stays unchanged; reset reproduces the catalog.  
Result: [x] Pass [ ] Fail — 3.5%→4.0% growth changed AP base from PHP29.15 to PHP33.45; Reset restored PHP29.15.

### TC-PSE-04 — Market-relative calculator

1. Open BDO and adjust the P/E multiple.
2. Open AREIT and adjust the required yield.

Expected: BDO changes by EPS × multiple; AREIT changes by annualized DPS ÷ yield; both remain labeled market-relative.  
Result: [x] Pass [ ] Fail — BDO 10×→11× changed PHP162.80→PHP179.08; AREIT 7%→6% changed PHP32.00→PHP37.33.

### TC-PSE-05 — Save and portfolio

1. Add a PH company to the portfolio.
2. Save a PSE scenario.
3. Open Portfolio and Saved scenarios.

Expected: the PH card shows its catalog base/status and links back to `/pse/:ticker`; the saved scenario retains ticker,
selected case, assumptions, value, and optional manual comparison.  
Result: [x] Pass [ ] Fail — PH BDO holding persisted and linked to `/pse/BDO`; saved scenario #3 rendered at PHP179.08 and linked back.

### TC-PSE-06 — Market-aware search

1. On a PSE valuation, open the global search and choose a PH ticker.
2. On a US valuation, repeat with a US ticker.

Expected: search lists and routes companies from the active market only.  
Result: [x] Pass [ ] Fail — PH search returned BDO and routed to `/pse/BDO`; US search remained the US catalog after switching back.

## PSE V2 Phase B Batch 1

### TC-PSE-B01-01 — Cumulative staged catalog and search

1. Sign in to the isolated staged workspace.
2. Open `/pse/AP` and confirm the footer reports 18 companies.
3. Search for BPI and MREIT and open each result.

Expected: the candidate contains the unchanged pilot plus the frozen ten; new companies route through the existing PSE
workspace without changing the active catalog.  
Result: [x] Pass [ ] Fail — staged footer reported 18 companies; search routed to `/pse/BPI` and `/pse/MREIT`; the
normal local API continued to serve the active eight-company 1.1 catalog.

### TC-PSE-B01-02 — Bank residual-income calculator

1. Open BPI Base.
2. Confirm the published base value and residual-income assumption controls.
3. Change cost of equity from 12.052% to 13%.

Expected: the base case changes through the residual-income engine while reported book value remains locked.  
Result: [x] Pass [ ] Fail — BPI rendered PHP98.44 and changed to PHP88.37; the page displayed current ROE, terminal
ROE, cost of equity, payout ratio, and terminal growth.

### TC-PSE-B01-03 — REIT sustainable-distributions calculator

1. Open MREIT Base.
2. Confirm the published base value and distribution assumption controls.
3. Change cost of equity from 11% to 12%.

Expected: the base case changes through the sustainable-distributions engine while reviewed DPU remains locked.  
Result: [x] Pass [ ] Fail — MREIT rendered PHP12.08 and changed to PHP10.81; the page displayed distribution growth,
cost of equity, and terminal growth.

### TC-PSE-B01-04 — Stored/API parity and persistence

1. Read the staged list and all 18 details through authenticated HTTP.
2. Reproduce all ten Batch 1 calculator defaults.
3. Save one edited BPI scenario and test unauthenticated access.

Expected: 18/18 raw stored-versus-served parity, 10/10 calculator parity, a persisted saved scenario, and 401 without
authentication.  
Result: [x] Pass [ ] Fail — all parity checks passed; BPI scenario `#4` persisted; unauthenticated list access returned
401.

### TC-PSE-B01-05 — Local activation and rollback boundary

1. Activate the confirmed cumulative catalog through the guarded activation script.
2. Read the normal local API and open BPI and MREIT through `localhost:4000`.
3. Confirm the previous eight-company catalog still exists unchanged.

Expected: the normal app serves exactly 18 companies from the confirmed manifest, both new calculator routes work, and
the previous catalog remains available for rollback.  
Result: [x] Pass [ ] Fail — active API returned exact 18/18 detail and 10/10 calculator parity; active BPI rendered
PHP98.44→PHP88.37 at 13% cost of equity; active search opened MREIT and rendered PHP12.08→PHP10.81 at 12%; the previous
1.1 catalog remained intact.

## PSE V2 Phase B Batch 2

### TC-PSE-B02-01 — Cumulative staged catalog and active preservation

1. Sign in to the isolated Batch 2 workspace.
2. Confirm the staged footer reports 28 companies.
3. Confirm the normal local app still serves the active 18-company Batch 1 catalog.

Expected: the candidate contains the unchanged active 18 plus the frozen ten; no active pointer or artifact changes.  
Result: [x] Pass [ ] Fail — staged footer/API reported 28; candidate twins were identical; active pointer and manifest
hashes remained unchanged.

### TC-PSE-B02-02 — Issuer-bound FCFF calculator

1. Search for URC and open Base.
2. Confirm the published FCFF range and assumption controls.
3. Change explicit growth from 4% to 5%.

Expected: URC recalculates from its own cash, debt, claims, and shares; only the selected case changes.  
Result: [x] Pass [ ] Fail — URC rendered PHP21.56 and changed to PHP25.11; the issuer-bound capital-bridge tests passed.

### TC-PSE-B02-03 — FCFF-blocked market-relative fallback

1. Search for DNL and confirm the market-relative label and FCFF limitation.
2. Change the Base P/E multiple from 10x to 11x.

Expected: DNL remains market-relative-only and changes from EPS × multiple without exposing intrinsic scenarios.  
Result: [x] Pass [ ] Fail — DNL rendered PHP3.60 and changed to PHP3.96 while retaining the market-relative label.

### TC-PSE-B02-04 — Stored/API parity and persistence

1. Read all 28 staged details through authenticated HTTP.
2. Reproduce all ten Batch 2 calculator defaults.
3. Save one edited URC scenario and test unauthenticated access.

Expected: 28/28 stored-versus-served parity, 10/10 calculator parity, persisted scenario, and 401 without auth.  
Result: [x] Pass [ ] Fail — all parity checks passed; URC scenario `#6` persisted; unauthenticated list access returned
401.

### TC-PSE-B02-05 — Local activation and rollback boundary

1. Activate the confirmed cumulative catalog through the guarded activation script.
2. Read the normal local API and open URC and DNL through `localhost:4000`.
3. Confirm the previous 18-company catalog remains unchanged.

Expected: the normal app serves exactly 28 companies from the confirmed manifest, both Batch 2 output types work, and
the previous catalog remains available for rollback.  
Result: [x] Pass [ ] Fail — active API returned exact 28/28 detail and 10/10 calculator parity; active URC rendered
PHP21.56→PHP25.11 at 5% growth; active search opened DNL with the market-relative label and PHP3.60 base; the Batch 1
catalog remained intact.

## PSE V2 Phase B Batch 3

### TC-PSE-B03-01 — Cumulative staged catalog and active preservation

1. Sign in to the isolated Batch 3 workspace.
2. Confirm the staged footer reports 38 companies.
3. Confirm the normal local app still serves the active 28-company Batch 2 catalog.

Expected: the candidate contains the unchanged active 28 plus the frozen ten; no active pointer or artifact changes.  
Result: [x] Pass [ ] Fail — staged footer/API reported 38; candidate twins were identical; active pointer and Batch 2
manifest hashes remained unchanged.

### TC-PSE-B03-02 — Property RNAV calculator

1. Open RLC Base and confirm the intrinsic RNAV label and published range.
2. Change fair-value uplift realization from 50% to 60%.

Expected: RLC recalculates from locked parent equity, property values, claims, and shares; only Base changes.  
Result: [x] Pass [ ] Fail — RLC rendered PHP61.82 and changed to PHP66.87.

### TC-PSE-B03-03 — Sub-one P/B fallback

1. Open AEV and confirm the market-relative label and unresolved SOTP limitation.
2. Change the Base P/B multiple from 0.6x to 0.7x.

Expected: AEV remains market-relative-only and the calculator permits a multiple below 1.0.  
Result: [x] Pass [ ] Fail — AEV rendered PHP31.39 and changed to PHP36.62.

### TC-PSE-B03-04 — Stored/API parity and persistence

1. Read all 38 staged details through authenticated HTTP.
2. Reproduce all ten Batch 3 calculator defaults.
3. Save one edited SM scenario and test unauthenticated access.

Expected: 38/38 stored-versus-served parity, 10/10 calculator parity, persisted scenario, and 401 without auth.  
Result: [x] Pass [ ] Fail — all parity checks passed; SM scenario `#8` persisted; unauthenticated list access returned
401.

### TC-PSE-B03-05 — Local activation and rollback boundary

1. Activate the confirmed cumulative catalog through the guarded activation script.
2. Read the normal local API and open RLC and AEV through `localhost:4000`.
3. Confirm the previous 28-company catalog remains unchanged.

Expected: the normal app serves exactly 38 companies, both Batch 3 output types work, and Batch 2 remains available for
rollback.  
Result: [x] Pass [ ] Fail — active API returned exact 38/38 detail and 10/10 calculator parity; active RLC rendered
PHP61.82→PHP66.87 and AEV rendered PHP31.39→PHP36.62; the Batch 2 manifest remained unchanged.

## PSE V2 Phase B Batch 4

### TC-PSE-B04-01 — Cumulative staged catalog and active preservation

1. Sign in to the isolated Batch 4 workspace.
2. Confirm the staged footer reports 48 companies.
3. Confirm the normal local app still serves the active 38-company Batch 3 catalog.

Expected: the candidate contains the unchanged active 38 plus the frozen ten; no active pointer or artifact changes.  
Result: [x] Pass [ ] Fail — staged footer/API reported 48; candidate twins were identical; active pointer and Batch 3
manifest hashes remained unchanged.

### TC-PSE-B04-02 — Finite-life concession distribution calculator

1. Open MWC Base and confirm the intrinsic label, published range, and absence of terminal-growth control.
2. Change distribution growth from 2.5% to 3.5%.

Expected: MWC recalculates only through the locked January 2047 expiry and assigns zero terminal value.  
Result: [x] Pass [ ] Fail — MWC rendered PHP17.03 and changed to PHP18.42; the model and calculator finite-life tests
confirmed zero terminal value.

### TC-PSE-B04-03 — Renewable-project fallback

1. Open ACEN and confirm the market-relative label and unresolved project-SOTP limitation.
2. Change the Base P/B multiple from 1.1x to 1.2x.

Expected: ACEN remains market-relative-only and changes from book value × multiple without intrinsic scenarios.  
Result: [x] Pass [ ] Fail — ACEN rendered PHP3.51 and changed to PHP3.83.

### TC-PSE-B04-04 — Stored/API parity and persistence

1. Read all 48 staged details through authenticated HTTP.
2. Reproduce all ten Batch 4 calculator defaults.
3. Save one edited MWC scenario and test unauthenticated access.

Expected: 48/48 stored-versus-served parity, 10/10 calculator parity, persisted scenario, and 401 without auth.  
Result: [x] Pass [ ] Fail — all parity checks passed; MWC scenario `#10` persisted; unauthenticated list access returned
401.

### TC-PSE-B04-05 — Local activation and rollback boundary

1. Activate the confirmed cumulative catalog through the guarded activation script.
2. Read the normal local API and open MWC and ACEN through `localhost:4000`.
3. Confirm the previous 38-company catalog remains unchanged.

Expected: the normal app serves exactly 48 companies, both Batch 4 output types work, and Batch 3 remains available for
rollback.  
Result: [x] Pass [ ] Fail — active API returned exact 48/48 detail and 10/10 calculator parity; active MWC rendered
PHP17.03→PHP18.42 and ACEN rendered PHP3.51→PHP3.83; the Batch 3 manifest remained unchanged.

## PSE V2 Phase B Batch 5

### TC-PSE-B05-01 — Cumulative staged catalog and active preservation

Expected: exactly 58 staged companies and the active 48-company Batch 4 catalog unchanged.  
Result: [x] Pass [ ] Fail — deterministic twins and active hashes matched.

### TC-PSE-B05-02 — Residual-income calculator

1. Open PNB Base and change cost of equity from 12.052% to 11%.

Expected: only Base recalculates from the locked book-value anchor.  
Result: [x] Pass [ ] Fail — PNB rendered PHP113.31 and changed to PHP129.27.

### TC-PSE-B05-03 — Fee-platform fallback

1. Open PSE and change Base P/E from 12x to 13x.

Expected: PSE remains market-relative-only and changes without intrinsic scenarios.  
Result: [x] Pass [ ] Fail — PSE rendered PHP169.32 and changed to PHP183.43.

### TC-PSE-B05-04 — Stored/API parity and persistence

Expected: 58/58 detail parity, 10/10 calculator parity, saved scenario, and unauthenticated 401.  
Result: [x] Pass [ ] Fail — all checks passed and PNB scenario `#12` persisted.

### TC-PSE-B05-05 — Local activation and rollback boundary

Expected: the normal app serves exactly 58 companies, both Batch 5 output types work, and Batch 4 remains available for
rollback.  
Result: [x] Pass [ ] Fail — active API returned 58/58 detail and 10/10 calculator parity; active PNB and PSE rendered
correctly; Batch 4 remained unchanged.

## PSE V2 Phase B Batch 6

### TC-PSE-B06-01 — Cumulative staged catalog and active preservation

Result: [x] Pass [ ] Fail — exact 68-company candidate, deterministic twins, and unchanged active Batch 5 hashes.

### TC-PSE-B06-02 — Market-relative telecom flow

Result: [x] Pass [ ] Fail — TEL rendered PHP1277.80; real API changed it to PHP1405.58 at 11x P/E and saved scenario #14.

### TC-PSE-B06-03 — Stored/API parity

Result: [x] Pass [ ] Fail — 68/68 detail parity, 10/10 calculator parity, and unauthenticated 401.

### TC-PSE-B06-04 — Local activation and rollback

Result: [x] Pass [ ] Fail — active API serves 68/68 records, TEL renders in the normal UI, and Batch 5 remains intact.

## PSE V2 Phase B Batch 7

### TC-PSE-B07-01 — Cumulative staged catalog and active preservation

Result: [x] Pass [ ] Fail — exact 78-company candidate, deterministic twins, verified artifact hashes, and unchanged active Batch 6 hashes.

### TC-PSE-B07-02 — Transportation screen and calculator flow

Result: [x] Pass [ ] Fail — ICT rendered PHP527.51, changed to PHP562.68 at 16x P/E, and the UI reported 78 companies.

### TC-PSE-B07-03 — Source-bound special cases

Result: [x] Pass [ ] Fail — ICT exposes its dated USD-to-PHP normalization and ATI exposes its stale-period warning.

### TC-PSE-B07-04 — Stored/API parity

Result: [x] Pass [ ] Fail — 78/78 detail parity, 10/10 calculator parity, unauthenticated 401, and ICT scenario `#16` persisted.

### TC-PSE-B07-05 — Activation boundary

Result: [x] Pass [ ] Fail — active API and UI serve the confirmed 78-company Batch 7 catalog; Batch 6 remains unchanged for rollback, and the user confirmed local activation on 2026-09-23.

## PSE V2 Phase B Batch 8

### TC-PSE-B08-01 — Cumulative staged catalog and active preservation

Result: [x] Pass [ ] Fail — exact 88-company candidate, deterministic twins, verified artifact hashes, and unchanged active Batch 7 hashes.

### TC-PSE-B08-02 — Resource screen and calculator flow

Result: [x] Pass [ ] Fail — OGP rendered PHP31.40, changed to PHP34.54 at 11x P/E, and the UI reported 88 companies.

### TC-PSE-B08-03 — Route and currency coverage

Result: [x] Pass [ ] Fail — OGP exposed PHP-normalized USD earnings; PCOR, PXP, and NIKL rendered representative downstream, upstream, and mining screens.

### TC-PSE-B08-04 — Stored/API parity

Result: [x] Pass [ ] Fail — 88/88 detail parity, 10/10 calculator parity, unauthenticated 401, and OGP scenario `#18` persisted.

### TC-PSE-B08-05 — Activation boundary

Result: [x] Pass [ ] Fail — active API and UI serve the confirmed 88-company Batch 8 catalog; Batch 7 remains unchanged for rollback, and the user confirmed local activation on 2026-09-23.

## PSE V2 Phase B Batch 9

### TC-PSE-B09-01 — Cumulative staged catalog and active preservation

Result: [x] Pass [ ] Fail — exact 98-company candidate, deterministic twins, verified artifact hashes, and unchanged active Batch 8 hashes.

### TC-PSE-B09-02 — Staples screen and calculator flow

Result: [x] Pass [ ] Fail — FB rendered PHP50.40, changed to PHP55.44 at 11x P/E, and the UI reported 98 companies.

### TC-PSE-B09-03 — Currency, filing, and fiscal-period coverage

Result: [x] Pass [ ] Fail — DELM exposed its PHP-normalized USD revenue screen, ANI exposed the delayed-filing warning, and CAT showed the 2026-03-31 period.

### TC-PSE-B09-04 — Stored/API parity

Result: [x] Pass [ ] Fail — 98/98 detail parity, 10/10 calculator parity, unauthenticated 401, and FB scenario `#20` persisted.

### TC-PSE-B09-05 — Activation boundary

Result: [x] Pass [ ] Fail — active API and UI serve the confirmed 98-company Batch 9 catalog; Batch 8 remains unchanged for rollback, and the user confirmed local activation on 2026-09-23.

## PSE V2 Phase B Batch 10

### TC-PSE-B10-01 — Cumulative staged catalog and active preservation

Result: [x] Pass [ ] Fail — exact 108-company candidate, deterministic twins, verified artifact hashes, and unchanged active Batch 9 hashes.

### TC-PSE-B10-02 — Resort screen and calculator flow

Result: [x] Pass [ ] Fail — BEL rendered PHP2.39, changed to PHP2.79 at 0.7x P/B, and the UI reported 108 companies.

### TC-PSE-B10-03 — Restructuring, zero-revenue, and suspension coverage

Result: [x] Pass [ ] Fail — PHR exposed the proposed asset-transfer warning, ACE exposed the zero-revenue warning, and MJC exposed its suspension and stale-audit warning.

### TC-PSE-B10-04 — Stored/API parity

Result: [x] Pass [ ] Fail — 108/108 detail parity, 10/10 calculator parity, unauthenticated 401, and BEL scenario `#22` persisted.

### TC-PSE-B10-05 — Activation boundary

Result: [x] Pass [ ] Fail — active API and UI serve the confirmed 108-company Batch 10 catalog; Batch 9 remains unchanged for rollback, and the user confirmed local activation on 2026-09-23.

## PSE V2 Phase B Batch 11

### TC-PSE-B11-01 — Cumulative staged catalog and active preservation

Result: [x] Pass [ ] Fail — exactly 118 staged artifacts, deterministic twins, verified hashes, and unchanged active Batch 10 pointer and manifest.

### TC-PSE-B11-02 — Holding-company screen and calculator

Result: [x] Pass [ ] Fail — final SMC rendered market-relative/provisional PHP35.24, changed to PHP44.05 at 0.5x P/B, saved scenario `#27`, and the page reported 118 companies.

### TC-PSE-B11-03 — Ownership and intrinsic limitations

Result: [x] Pass [ ] Fail — browser showed TFHI's SMC overlap and LPZ's FPH/ABS overlap warnings; their screens were not presented as intrinsic or additive.

### TC-PSE-B11-04 — Stored/API parity and persistence

Result: [x] Pass [ ] Fail — 118/118 detail parity, 10/10 calculator parity, unauthenticated 401; ten receipts, facts, runs, and objects plus thirty assumptions verified.

### TC-PSE-B11-05 — Confirmation and activation boundary

Result: [x] Pass [ ] Fail — at the staged-results gate, the user confirmed Batch 11 on 2026-09-23; the exact hash was pinned and Batch 10 remained active until the separately authorized activation in TC-PSE-B11-06.

### TC-PSE-B11-06 — Locally active API, UI, and rollback

Result: [x] Pass [ ] Fail — after separate authorization, active Batch 11 serves exactly 118 records with 118/118 detail and 10/10 calculator parity. The live UI switched US→PH, searched SMC, changed PHP35.24 to PHP44.05 at 0.5x, saved scenario `#29`, and showed TFHI's SMC overlap warning. Batch 10 remains byte-unchanged for rollback; 373 backend tests and the frontend build pass. The user confirmed local activation on 2026-09-23.

## PSE V2 Phase B Batch 12

### TC-PSE-B12-01 — Exact staged catalog and active preservation

Result: [x] Pass [ ] Fail — exactly 128 staged artifacts, deterministic twins, verified hashes, and unchanged active Batch 11 pointer and manifest.

### TC-PSE-B12-02 — Property screen and calculator

Result: [x] Pass [ ] Fail — staged CPG showed market-relative/provisional PHP0.97, changed to PHP1.08 at 0.50x P/B, saved scenario `#31`, and the page reported 128 companies.

### TC-PSE-B12-03 — Merger block and source lineage

Result: [x] Pass [ ] Fail — CDC rendered a blocked/unavailable page with no value or calculator, explained the post-report merger, and linked both its financial summary and merger disclosure; API POST returned 400.

### TC-PSE-B12-04 — Ownership and common-claim warning

Result: [x] Pass [ ] Fail — DD showed its PHP7.78 relative screen and a visible warning that DD and DDMPR per-share screens overlap and must not be added.

### TC-PSE-B12-05 — Stored/API parity and persistence

Result: [x] Pass [ ] Fail — 128/128 detail parity, 10/10 calculator states, unauthenticated 401; ten current receipts, facts, runs and objects plus twenty-seven assumptions verified.

### TC-PSE-B12-06 — Results-confirmation boundary

Result: [x] Pass [ ] Fail — at the staged-results gate, the user confirmed Batch 12 on 2026-09-23; the exact hash was pinned and Batch 11 remained active until the separately authorized activation in TC-PSE-B12-07.

### TC-PSE-B12-07 — Locally active API, UI, and rollback

Result: [x] Pass [ ] Fail — after separate authorization, active Batch 12 serves exactly 128 records with 128/128 detail and 10/10 calculator-state parity. The live UI switched US→PH, searched CPG, changed PHP0.97 to PHP1.08 at 0.50x, saved scenario `#33`, showed CDC's blocked/null state with source links and DD's overlap warning. Batch 11 remains unchanged for rollback; 377 backend tests and the frontend build pass. The user confirmed local activation on 2026-09-23.

## PSE V2 Phase B Batch 13

### TC-PSE-B13-01 — Exact staged catalog and active preservation

Result: [x] Pass [ ] Fail — exactly 138 staged artifacts, deterministic twins, verified manifest/artifact hashes, and unchanged active Batch 12 pointer and manifest.

### TC-PSE-B13-02 — USD conversion, sources, and calculator

Result: [x] Pass [ ] Fail — TECH showed a provisional relative PHP9.72 baseline, preferred-share warning, and PSE/BSP links; a 0.60x multiple showed PHP11.66 and saved scenario `#35`. The dated 62.698 PHP/USD observation is distinct from the original USD fact.

### TC-PSE-B13-03 — Non-December fiscal period

Result: [x] Pass [ ] Fail — VMC rendered its 2026-05-31 period, PHP1.82 base, and explicit August-fiscal-year warning.

### TC-PSE-B13-04 — Post-report change and currency display

Result: [x] Pass [ ] Fail — LFM showed the July direct-distribution caveat; after removing display-only binary float noise, its PHP10.255 base rendered as PHP10.26 without changing the artifact.

### TC-PSE-B13-05 — Inherited unavailable state

Result: [x] Pass [ ] Fail — CDC remained blocked/null in the 138-company staged catalog, with no calculator.

### TC-PSE-B13-06 — Stored/API parity and persistence

Result: [x] Pass [ ] Fail — 138/138 detail parity, 10/10 new calculator parity, unauthenticated 401; ten current receipts, original-currency facts, runs and objects plus thirty-one assumptions verified.

### TC-PSE-B13-07 — Results-confirmation boundary

Result: [x] Pass [ ] Fail — at the staged-results gate, the user confirmed Batch 13 on 2026-09-23; the exact hash was pinned and Batch 12 remained active until the separately authorized activation in TC-PSE-B13-08.

### TC-PSE-B13-08 — Locally active API, UI, and rollback

Result: [x] Pass [ ] Fail — after separate authorization, active Batch 13 serves exactly 138 records with 138/138 detail and 10/10 new calculator parity. The live UI switched US→PH, searched TECH, changed PHP9.72 to PHP11.66 at 0.60x, saved scenario `#37`, retained PSE/BSP/preferred sources, showed VMC's May period and LFM's PHP10.26, and kept CDC blocked. Batch 12 remains unchanged for rollback; 381 backend tests and the frontend build pass. The user confirmed local activation on 2026-09-23.

## PSE V2 Phase B Batch 14 — locally active

### TC-PSE-B14-01 — Exact candidate and release boundary

Result: [x] Pass [ ] Fail — 148 exact staged records and deterministic twins; all 138 Batch 13 artifacts byte-preserved, active pointer unchanged, and Batch 14 activation locked pending separate approval.

### TC-PSE-B14-02 — Fiscal-period EPS and book-value screens

Result: [x] Pass [ ] Fail — STI March 2026, CEU February 2026, FEU May 2026, and the other seven June 2026 source periods preserved. Eight TTM EPS bridges, one annual EPS, and one interim BVPS were stored as 26 original-period facts; derived values stayed outside reported-fact rows.

### TC-PSE-B14-03 — Browser market switch, search, and calculator

Result: [x] Pass [ ] Fail — isolated local browser switched US→PH, searched STI, showed staged 148-company footer and provisional market-relative PHP2.20 baseline, then changed to PHP2.42 at 11× P/E. API saved STI scenario `#38`.

### TC-PSE-B14-04 — Specialist limitations and inherited block

Result: [x] Pass [ ] Fail — MEDIC showed its P/B screen and delayed-audit caveat/source links, KEEPR showed the COSCO non-additive warning, and CDC remained blocked/null with no calculator. MEDIC's slider endpoint rendered cleanly as `1.05` after the display-only fix.

### TC-PSE-B14-05 — API, persistence, tests, and build

Result: [x] Pass [ ] Fail — real authenticated staged API returned 148/148 artifact parity and 10/10 new calculator states, unauthenticated 401; local Postgres/MinIO verified ten receipts/objects, 26 facts, 30 assumptions and ten runs; 385 backend tests and the frontend production build passed.

### TC-PSE-B14-06 — Results-confirmation gate

Result: [x] Pass [ ] Fail — user confirmed staged Batch 14 results on 2026-09-23; the exact manifest hash was pinned and read-only preflight passed. Batch 13 remains active. Do not activate, deploy, push, recover CDC, or begin Batch 15/Phase C without separate authorization.

### TC-PSE-B14-07 — Locally active API, UI, and rollback

Result: [x] Pass [ ] Fail — after separate authorization, active Batch 14 served 148/148 stored-detail parity and 10/10 calculator states, with unauthenticated 401. Live browser switched US→PH, searched STI, changed PHP2.20 to PHP2.42 at 11× P/E, and saved scenario `#40`; MEDIC and KEEPR warnings and CDC blocked/null remained visible. Batch 13's manifest remained unchanged for rollback. Postgres/MinIO checks, all 385 backend tests, and the frontend build passed. User confirmed this local activation on 2026-09-23.

## PSE V2 Phase B Batch 15 — locally active

### TC-PSE-B15-01 — Exact staged catalog and active preservation

Result: [x] Pass [ ] Fail — exactly 158 staged records and byte-identical deterministic twins, 148 inherited Batch 14 artifacts unchanged, active pointer unchanged, and Batch 15 activation locked pending separate approval.

### TC-PSE-B15-02 — Property screen and calculator

Result: [x] Pass [ ] Fail — staged KPPI showed market-relative/provisional PHP1.917 exact base (PHP1.92 rendered), changed to PHP2.13 at 0.50× P/B, saved browser scenario `#43`, and the page reported 158 catalog records.

### TC-PSE-B15-03 — Delisted security stays null

Result: [x] Pass [ ] Fail — HOUSE showed blocked/unavailable with no value or calculator, explained the PSE's 2025-10-31 common-share delisting, and linked its historical financial summary and delisting notice. Calculator POST returned `400`; Postgres records `listing_status=delisted` and the 2025-06-30 fact as historical.

### TC-PSE-B15-04 — Period and parent/claim caveats

Result: [x] Pass [ ] Fail — ALCO rendered its 2026-03-31 source period and March-versus-June/preferred-share caveat; ELI showed the MEG parent/subsidiary non-additive warning. Intrinsic scenarios remained null for all nine numeric screens.

### TC-PSE-B15-05 — API, persistence, tests, and build

Result: [x] Pass [ ] Fail — authenticated staged API returned 158/158 stored-detail parity and ten new calculator states; unauthenticated 401 and inherited CDC disabled. Postgres/MinIO verified ten receipts/objects, ten original-period facts, 27 assumptions and ten runs; 389 backend tests and frontend production build passed.

### TC-PSE-B15-06 — Results-confirmation boundary

Result: [x] Pass [ ] Fail — user confirmed staged Batch 15 results on 2026-09-23; the exact manifest hash was pinned and read-only preflight passed. Batch 14 remains active. Do not activate, deploy, push, replace/recover HOUSE, or begin Batch 16/Phase C without separate authorization.

### TC-PSE-B15-07 — Locally active API, UI, and rollback

Result: [x] Pass [ ] Fail — after infrastructure recovery, active Batch 15 served 158/158 exact stored-detail parity and ten new calculator states, with unauthenticated 401, HOUSE calculator POST 400, and CDC disabled. Live browser switched US→PH, searched KPPI, changed PHP1.92→2.13 at 0.50× P/B and saved scenario `#45`; HOUSE blocked/null with the delisting source, ALCO's March-period caveat, ELI's MEG-overlap warning, and CDC blocked/null remained visible. Postgres/MinIO records and objects passed readback. All 158 active artifacts match the confirmed candidate; Batch 14 rollback is byte-preserved. All 389 backend tests and the frontend build passed. The user confirmed this local activation on 2026-09-24.

## PSE V2 Phase B Batch 16 — locally active and user-confirmed

### TC-PSE-B16-01 — Exact staged catalog and active preservation

Result: [x] Pass [ ] Fail — exactly 168 staged records, byte-identical deterministic twins, all 158 active Batch 15 artifacts preserved, active pointer unchanged, and real Batch 16 activation requires separate authorization.

### TC-PSE-B16-02 — Operating screen, browser edit and save

Result: [x] Pass [ ] Fail — isolated browser switched US→PH, searched AXLM, showed provisional market-relative PHP2.70 base and staged 168-company footer, edited to PHP2.97 at 11× P/E and saved scenario `#47`.

### TC-PSE-B16-03 — Small P/S screen, preferred claims and FX lineage

Result: [x] Pass [ ] Fail — SFI displayed a nonzero PHP0.0023 base (not PHP0.00), accepted an API 0.20× P/S edit, and showed the convertible-preferred/book-value warning. FOOD showed the USD-to-PHP sales screen, September restructuring caveat, and PSE common-share plus dated BSP FX source links.

### TC-PSE-B16-04 — Bank and fiscal-period caveats

Result: [x] Pass [ ] Fail — BNCOM rendered provisional P/B rather than unsupported residual income and exposed the reported BVPS/common-share mismatch; FCG retained its March 2026 nine-month/June fiscal-year label. Inherited HOUSE stayed blocked/null.

### TC-PSE-B16-05 — API, persistence, tests and build

Result: [x] Pass [ ] Fail — authenticated staged API returned 168/168 exact stored-detail parity and ten new calculator states; unauthenticated 401 and inherited CDC/HOUSE disabled. Postgres/MinIO verified ten receipts/objects, 22 original-period facts, 30 multiples, one dated FX observation and ten runs. All 393 backend tests and the frontend production build passed.

### TC-PSE-B16-06 — Results-confirmation boundary

Result: [x] Pass [ ] Fail — user confirmed staged Batch 16 results on 2026-09-25. Exact manifest hash was pinned, read-only preflight and isolated temporary-root activation test passed, and Batch 15 remained active at that gate. Separate authorization was required for the later local activation; no deployment, push, blocked recovery, Batch 17, or Phase C was implied.

### TC-PSE-B16-07 — Locally active API, PH page, persistence, and rollback

Result: [x] Pass [ ] Fail — separately authorized local activation set the exact 168-entry Batch 16 manifest active. Live authenticated API returned 168/168 exact stored-detail parity and ten of ten new calculator states; CDC/HOUSE remained disabled and unauthenticated listing returned 401. Signed-in PH page showed the 168-company footer, AXLM PHP2.70→2.97 calculator edit, SFI PHP0.0023, FOOD PSE/BSP source links, and HOUSE blocked/null. Postgres/MinIO source, fact, assumption, and run readback passed; Batch 15's manifest is unchanged for rollback. All 393 backend tests and the frontend production build passed. The user confirmed local activation on 2026-09-25; no deployment, push, recovery, Batch 17, or Phase C is authorized.

## PSE V2 Phase B Batch 17 — locally active and user-confirmed

### TC-PSE-B17-01 — Exact staged catalog and parent preservation

Result: [x] Pass [ ] Fail — at the staged-results gate, exactly 178 records, byte-identical deterministic twins, all 168 Batch 16 parent artifacts preserved, active pointer unchanged, and real Batch 17 activation required separate authorization.

### TC-PSE-B17-02 — Real relative-screen calculator and save

Result: [x] Pass [ ] Fail — signed-in staged PH browser showed the 178-company footer and SGP provisional PHP19.31 base, edited to PHP22.07 at 0.80× P/B and saved scenario `#48`. TFC showed PHP37.50 base with 2026-05-31 financial period; staged HTTP edited it to PHP41.25 at 11× P/E without saving.

### TC-PSE-B17-03 — Material caveats, sources and blocked state

Result: [x] Pass [ ] Fail — PREIT showed PHP0.76 relative screen, lease/permit warning and official legal source link; LBC showed PHP7.00 P/S plus listed-versus-outstanding share warning; MRC showed parent-equity and placement-share caveats. Inherited HOUSE remained blocked/null. US→PH navigation returned to AP's inherited intrinsic page.

### TC-PSE-B17-04 — API, persistence, regression and serving boundary

Result: [x] Pass [ ] Fail — isolated staged HTTP returned 178/178 exact stored-detail parity, ten new calculator states, CDC/HOUSE disabled and unauthenticated 401. Postgres/MinIO readback verified ten receipts/objects, 15 original-period facts, 30 multiples and ten runs, with idempotent receipt replay. All 397 backend tests and the frontend production build passed. The normal active PH page still showed Batch 16 with 168 companies.

### TC-PSE-B17-05 — Results-confirmation boundary

Result: [x] Pass [ ] Fail — user confirmed staged Batch 17 results on 2026-09-25. Exact manifest hash was pinned, read-only preflight and isolated temporary-root activation test passed, and Batch 16 remained active at that gate. Separate authorization was required for the later local activation; no deployment, push, blocked recovery, Batch 18, or Phase C was implied.

### TC-PSE-B17-06 — Locally active API, PH page, persistence, and rollback

Result: [x] Pass [ ] Fail — separately authorized local activation set the exact 178-entry Batch 17 manifest active. Live authenticated API returned 178/178 exact stored-detail parity and ten new calculator states; CDC/HOUSE remained disabled and unauthenticated listing returned 401. Signed-in PH page switched US→PH, showed the 178-company footer, searched SGP, recalculated PHP19.31→22.07 at 0.80× P/B and saved scenario `#49`. Postgres/MinIO source, fact, assumption and run readback passed. Batch 16's manifest is unchanged for rollback; all 397 backend tests and the frontend build pass. A later full browser navigation returned to login, so fresh-reload session persistence was not verified. The user confirmed local activation on 2026-09-25; no deployment, push, recovery, Batch 18, or Phase C is authorized.

## PSE V2 Phase B Batch 18 — locally active and user-confirmed

### TC-PSE-B18-01 — Exact staged catalog and active preservation

Result: [x] Pass [ ] Fail — at the staged-results gate, exactly 188 records, byte-identical deterministic twins, all 178 Batch 17 parent artifacts preserved, active pointer unchanged, and real Batch 18 activation required separate authorization.

### TC-PSE-B18-02 — Relative-screen calculator, small value and save

Result: [x] Pass [ ] Fail — signed-in staged PH browser showed 188 companies and PBC provisional PHP35.79 base, edited to PHP40.27 at 0.90× P/B and saved scenario `#50`. APC displayed positive PHP0.0080 rather than PHP0.00 with its no-revenue limitation; isolated HTTP edited ECP to PHP0.98874236 at 0.60× P/B.

### TC-PSE-B18-03 — Parent-attribution, bank caveat and blocked state

Result: [x] Pass [ ] Fail — PTC exposed the zero-parent-field caveat without treating zero as fact. IPM showed parent equity per common share about PHP1.229, not reported PHP1.80 total BVPS. REG and ECP parent-basis arithmetic and warnings passed focused/API checks. Inherited HOUSE remained blocked/null. US→PH navigation returned to AP's inherited intrinsic page.

### TC-PSE-B18-04 — API, persistence, tests and build

Result: [x] Pass [ ] Fail — isolated staged HTTP returned 188/188 exact stored-detail parity, ten new calculator states, CDC/HOUSE disabled and unauthenticated 401. Postgres/MinIO verified ten receipts/objects, 16 original-period facts, 30 multiples and ten runs; idempotent replay retained counts. All 401 backend tests and frontend build passed; normal active PH page still showed Batch 17 with 178 companies.

### TC-PSE-B18-05 — Results-confirmation boundary

Result: [x] Pass [ ] Fail — user confirmed staged Batch 18 results on 2026-09-25. Exact manifest hash was pinned, read-only preflight and isolated temporary-root activation test passed, and Batch 17 remained active at that gate. Separate authorization was required for the later local activation; no deployment, push, blocked recovery, Batch 19, or Phase C was implied.

### TC-PSE-B18-06 — Locally active API, PH page, persistence, and rollback

Result: [x] Pass [ ] Fail — separately authorized local activation set the exact 188-entry Batch 18 manifest active. Live authenticated API returned 188/188 exact stored-detail parity and ten new calculator states; CDC/HOUSE remained disabled and unauthenticated listing returned 401. Signed-in PH page showed the 188-company footer, recalculated PBC PHP35.79→40.27 at 0.90× P/B and saved scenario `#51`; PTC's zero-parent-field warning and HOUSE blocked/null remained visible, and US→PH navigation returned to inherited AP. Postgres/MinIO source, fact, assumption and run readback passed. Batch 17's manifest is unchanged for rollback; all 401 backend tests and frontend build pass. The user confirmed local activation on 2026-09-25; no deployment, push, recovery, Batch 19, or Phase C is authorized.

## PSE V2 Phase B Batch 19 — active locally and user-confirmed

### TC-PSE-B19-01 — Exact candidate and active boundary

Result: [x] Pass [ ] Fail — frozen ten plus 188 inherited entries yielded an exact 198-record staged catalog. Deterministic twins matched byte-for-byte, all parent artifacts were preserved, and the active Batch 18 pointer/hash and 188-record API remained unchanged.

### TC-PSE-B19-02 — Reviewed equity/share arithmetic and unavailable states

Result: [x] Pass [ ] Fail — seven Low-reliability market-relative screens independently reconcile to scoped reported equity and dated ordinary-common shares. IS, PAX and PRIM expose null values and distinct reasons; inherited CDC/HOUSE remain blocked. LODE retains the reported PHP0.80 BVPS but uses an explicitly labeled PHP0.0751 total-book proxy.

### TC-PSE-B19-03 — Staged browser, calendar, calculator and blockers

Result: [x] Pass [ ] Fail — signed-in staged PH browser showed the seven-day calendar, 198-company footer and TBGI PHP0.08 base; 0.60× P/B changed the displayed value to PHP0.09. LODE's Cross-checks displayed the source discrepancy. IS/PAX/PRIM each showed a blocked/null page with no calculator; full-page screenshots were captured under the Batch 19 candidate root. Temporary test accounts were removed.

### TC-PSE-B19-04 — API, persistence, regression and build

Result: [x] Pass [ ] Fail — isolated staged authenticated API returned 198/198 stored-detail parity and ten new calculator states; unauthenticated listing returned 401. Local Postgres/MinIO readback matched ten receipts/objects, 30 original-period facts, 21 multiple assumptions and ten runs. All 404 backend tests and the frontend production build passed.

### TC-PSE-B19-05 — Results-confirmation boundary

Result: [x] Pass [ ] Fail — user confirmed staged Batch 19 results on 2026-09-25. The exact 198-entry manifest hash was pinned in a read-only-by-default activation guard. Preflight checked the exact issuer/blocked sets, parent artifact preservation and unchanged Batch 18 active pointer. Isolated temporary-root activation passed without touching real serving; fresh active HTTP still returned Batch 18/188 and TBGI 404. Four focused and all 405 backend tests plus frontend build passed. Separate local-activation authorization is still required; no deployment, push, blocked recovery, Batch 20 or Phase C is implied.

### TC-PSE-B19-06 — Local activation, live API/UI and rollback

Result: [x] Pass [ ] Fail — after separate authorization, the exact confirmed 198-record Batch 19 manifest became locally active. Live authenticated API returned 198/198 stored-detail parity, seven enabled and three disabled new calculators, inherited CDC/HOUSE disabled, TBGI 0.60× edit, and unauthenticated 401. Signed-in PH browser showed 198 companies, changed calendar dates, searched/opened ABA, edited TBGI PHP0.08→0.09, showed LODE's book-value warning, and kept IS/PAX/PRIM blocked/null. Postgres/MinIO readback passed; 103 focused Phase B tests, all 405 backend tests, and frontend build passed. Batch 18's rollback manifest is unchanged and temporary test accounts were removed. The user confirmed local activation on 2026-09-25; a final read-only API check still returned Batch 19/198, TBGI 200 and PRIM 200/not_available. No deployment, push, recovery, Batch 20, or Phase C is implied.

## PSE V2 Phase B Batch 20 — active locally and user-confirmed

### TC-PSE-B20-01 — Exact staged catalog and active preservation

Result: [x] Pass [ ] Fail — frozen ten plus 198 inherited entries produced exact 208-record deterministic twins, with all parent artifacts byte-identical. Batch 20 remains outside serving; Batch 19 active pointer and 198-record API are unchanged.

### TC-PSE-B20-02 — Parent-common arithmetic and limitations

Result: [x] Pass [ ] Fail — ten Low-reliability P/B screens independently reconcile to June 2026 parent equity and dated outstanding common shares. Printed BVPS, minority claims, TOP's blank ISIN, XG's EPS conflict, and PRC's losses remain visible as limitations. Intrinsic scenarios are null for all ten.

### TC-PSE-B20-03 — Staged PH browser, calendar, search, calculator and block

Result: [x] Pass [ ] Fail — signed-in staged browser showed 208 companies, TOP provisional PHP0.15 base and PHP0.18 after a 0.60× P/B edit, navigated the seven-day calendar, opened REDC from search, displayed HI's parent-equity warning, and kept inherited PRIM blocked/null without a calculator. Current-build screenshots are under the Batch 20 candidate root; the temporary test account was removed.

### TC-PSE-B20-04 — API, persistence, regression and build

Result: [x] Pass [ ] Fail — isolated staged HTTP returned 208/208 exact stored-detail parity, ten enabled new calculators, five inherited blocked calculators and unauthenticated 401. Postgres/MinIO readback matched ten receipts/objects, 30 reported facts, 30 assumptions and ten runs. Three focused Batch 20 tests, all 408 backend tests and frontend build passed.

### TC-PSE-B20-05 — Results-confirmation boundary

Result: [x] Pass [ ] Fail — user confirmed staged Batch 20 results on 2026-09-25. The exact 208-entry manifest hash was pinned in a read-only-by-default activation guard. Preflight checked the exact issuer/blocked sets, availability counts, parent artifact preservation, receipt hashes and unchanged Batch 19 active pointer. Isolated temporary-root activation passed without touching real serving; fresh active HTTP still returned Batch 19/198 and TOP 404. Four focused and all 409 backend tests plus frontend build passed. Separate local-activation authorization is still required; no deployment, push, blocked recovery, Batch 21 or Phase C is implied.

### TC-PSE-B20-06 — Local activation, live API/UI and rollback

Result: [x] Pass [ ] Fail — after separate authorization, the exact confirmed 208-record Batch 20 manifest became locally active. Live authenticated API returned 208/208 stored-detail parity, ten enabled new calculators, five inherited disabled calculators, TOP 0.60× edit and unauthenticated 401. Signed-in PH browser showed 208 companies, changed calendar dates, searched/opened REDC, edited TOP PHP0.15→0.18, showed HI's parent-equity warning and kept PRIM blocked/null. Postgres/MinIO readback passed; 107 focused Phase B tests, all 409 backend tests and frontend build passed. Batch 19's rollback manifest is unchanged and temporary test accounts were removed. Two earlier post-scan browser attempts had an empty search dropdown; a clean rerun passed, and the intermittent symptom remains logged. The user confirmed local activation on 2026-09-25; a final read-only API check still returned Batch 20/208, TOP 200 and PRIM 200/not_available. No deployment, push, recovery, Batch 21 or Phase C is implied.

## PSE V2 Phase B Batch 21 — locally active, live-verified and user-confirmed

### TC-PSE-B21-01 — Exact staged catalog and active preservation

Result: [x] Pass [ ] Fail — at the staged gate, frozen ten plus 208 inherited entries produced exact 218-record deterministic twins, with every parent artifact byte-identical. Batch 20 active pointer and 208-record API were unchanged then; subsequent local activation is recorded in TC-PSE-B21-06.

### TC-PSE-B21-02 — Equity scope, units and period

Result: [x] Pass [ ] Fail — seven parent-equity screens and three explicitly labeled total-book proxies independently reconcile to sourced equity and dated outstanding common shares. PHA retained PHP-thousands units and SPM retained its March 2026 interim. Blank/zero parent fields were never stored as economic zero; intrinsic scenarios remain null for all ten.

### TC-PSE-B21-03 — Staged PH browser and inherited block

Result: [x] Pass [ ] Fail — signed-in staged browser showed 218 companies, LPC provisional PHP0.0090 base and about PHP0.01 after a 0.50× P/B edit, navigated the seven-day calendar, opened PHA from search, displayed PHA's thousand-unit warning, SPM's March period, SRDC's unavailable-parent warning and inherited PRIM blocked/null without a calculator. Current-build screenshots were captured and the temporary test account removed. The separate small-value display-precision limitation is recorded in Audit 31/backlog.

### TC-PSE-B21-04 — API, persistence, regression and build

Result: [x] Pass [ ] Fail — isolated staged HTTP returned 218/218 exact stored-detail parity, ten enabled new calculators, five inherited blocked calculators and unauthenticated 401. Postgres/MinIO readback matched ten receipts/objects, 30 reported facts, 30 assumptions and ten runs. Three focused Batch 21 tests, all 412 backend tests and frontend build passed.

### TC-PSE-B21-05 — Results-confirmation boundary

Result: [x] Pass [ ] Fail — user confirmed staged Batch 21 results on 2026-09-25. The exact 218-entry manifest hash was pinned in a read-only-by-default activation guard. Preflight checked issuer/status counts, parent artifact preservation, receipt hashes and unchanged Batch 20 active pointer. Isolated temporary-root activation passed without touching real serving; fresh active HTTP still returned Batch 20/208 and IDC 404. Four focused and all 413 backend tests plus frontend build passed. The small-value display caveat remains logged; separate local-activation authorization is still required. No deployment, push, blocked recovery, Batch 22 or Phase C is implied.

### TC-PSE-B21-06 — Local activation, live API/UI and rollback

Result: [x] Pass [ ] Fail — after separate user authorization, the pinned Batch 21 manifest became locally active with 218 records; Batch 20 rollback manifest stayed unchanged. Real authenticated API returned 218/218 stored-detail parity, ten enabled new calculators, five inherited disabled calculators, LPC's 0.50× P/B edited base PHP0.01002273174 and unauthenticated 401. Signed-in active PH browser showed the 218-company list, LPC calendar/calculator, search to PHA, PHA unit warning, SPM March period, SRDC total-book warning and PRIM blocked/null. Active Postgres/MinIO readback passed. The list-path catalog-validation timeout was fixed and measured at 0.186 seconds; 114 focused Phase B tests, all 413 backend tests and frontend build passed. The user confirmed local activation on 2026-09-25; final read-only preflight and fresh authenticated API still returned Batch 21/218, IDC market-relative-only and PRIM not-available, with the Batch 20 rollback hash intact. The LPC small-value display caveat remains. No deployment, push, recovery, Batch 22 or Phase C is implied.

## PSE V2 Phase B Batch 22 — locally active, live-verified and user-confirmed

### TC-PSE-B22-01 — Frozen set and deterministic catalog

Result: [x] Pass [ ] Fail — at the staged gate, the exact confirmed ten plus 218 inherited entries produced byte-identical 228-record twin candidates. Every Batch 21 parent artifact was preserved. The candidate has 34 intrinsic, 189 market-relative and five unavailable records; Batch 21 was still active and CSB absent from serving then. Subsequent local activation is recorded in TC-PSE-B22-05.

### TC-PSE-B22-02 — Source scope and accounting bridges

Result: [x] Pass [ ] Fail — the ten reviewed equity/share bridges reconciled independently from dated PSE summary and common-share records. CSB, ECVC and JAS use explicitly labeled total-book proxies because parent attribution is zero, inconsistent or blank; the other seven use parent equity. Intrinsic scenarios remain null, with explicit blockers and Low reliability. Ten receipt objects, 30 scoped facts, 30 assumptions and ten staged runs read back from Postgres/MinIO.

### TC-PSE-B22-03 — Staged HTTP and signed-in page

Result: [x] Pass [ ] Fail — staged authenticated API returned 228/228 stored-detail parity, ten enabled new calculators, five inherited disabled calculators, CSB's 1.00× edit at PHP8.432332154257614 and unauthenticated 401. Signed-in staged browser showed 228 companies, CSB's calculator and calendar, source links, search to ORE, ORE's loss warning, ENEX's June period, ECVC's parent-field warning and inherited PRIM blocked/null. Current-build screenshots were captured and the temporary account removed. All 417 backend tests and frontend production build passed.

### TC-PSE-B22-04 — Results and activation boundary

Result: [x] Pass [ ] Fail — the user confirmed the staged Batch 22 results on 2026-09-25. The exact 228-entry manifest was pinned in a read-only-by-default activation guard. Preflight checked the frozen issuer/status sets, parent artifact preservation, receipt hashes and unchanged Batch 21 active pointer. Isolated temporary-root activation passed without touching real serving; fresh authenticated active HTTP still returned Batch 21/218 and CSB 404. Five focused Batch 22 tests, all 418 backend tests and frontend build passed. Separate local-activation authorization is still required; no deployment, push, blocked recovery, Batch 23 or Phase C is implied.

### TC-PSE-B22-05 — Local activation, live API/UI and rollback

Result: [x] Pass [ ] Fail — after separate user authorization, the pinned Batch 22 manifest became locally active with 228 records; Batch 21 rollback manifest remained unchanged. Real authenticated API returned 228/228 stored-detail parity, ten enabled new calculators, five inherited disabled calculators, CSB's edited PHP8.432332154257614 base at 1.00× P/B and unauthenticated 401. Signed-in active PH browser showed the 228-company list, CSB calendar/calculator, source links, search to ORE, ORE loss warning, ENEX June period, ECVC parent-field warning and PRIM blocked/null. Active Postgres/MinIO readback passed; 119 focused Phase B/API tests, full backend regression and frontend build passed. Temporary test accounts were removed. The user confirmed local activation on 2026-09-25; final read-only preflight and fresh authenticated API still returned Batch 22/228, CSB market-relative-only and PRIM not-available, with the Batch 21 rollback hash intact. No deployment, push, blocked recovery, Batch 23 or Phase C is implied.

## PSE V2 Phase B Batch 23 — locally active, live-verified and user-confirmed

### TC-PSE-B23-01 — Frozen set, class bridges and null gates

Result: [x] Pass [ ] Fail — at the staged gate, the exact confirmed ten plus 228 inherited entries produced byte-identical 238-record twins, with every Batch 22 artifact unchanged. Eight new PHP/common screens use reviewed class denominators; BC and OPM expose blocked/null values and disabled calculators because preferred claims or USD conversion are unresolved. The cumulative catalog has 34 intrinsic, 197 market-relative and seven unavailable records. Subsequent local activation is recorded in TC-PSE-B23-05.

### TC-PSE-B23-02 — Source facts and persistence

Result: [x] Pass [ ] Fail — independent `Decimal` replay matched eight low/base/high P/B sensitivities; class-sum and declassification checks caught wrong denominators. Existing Postgres/MinIO readback matched ten current receipt objects, 35 dated source facts, ten separately labeled denominator assumptions, 24 multiple assumptions and ten staged runs. USD units for OPM and PHP-thousands units for BC/LC remained distinct. Four focused Batch 23 tests, all 422 backend tests and frontend build passed.

### TC-PSE-B23-03 — Real staged API and signed-in PH browser

Result: [x] Pass [ ] Fail — staged authenticated API returned 238/238 exact stored-detail parity, eight enabled new calculators, BC/OPM plus five inherited disabled calculators, CA's 0.60× edited base PHP6.845964238041838 and unauthenticated 401. Signed-in staged browser showed 238 companies, CA calculator/calendar/source links, searched to FJP, displayed FJP rights and LC unit warnings, ATN March fiscal year, and BC/OPM/PRIM blocked/null without calculators. Current-build screenshots were captured and the temporary account removed.

### TC-PSE-B23-04 — Results and active boundary

Result: [x] Pass [ ] Fail — the user confirmed staged Batch 23 results on 2026-09-25. The exact 238-entry manifest was pinned in a read-only-by-default activation guard. Preflight checked the issuer/blocked sets, status counts, parent artifact preservation, receipt hashes and unchanged Batch 22 pointer. Isolated temporary-root activation passed without touching real serving; fresh authenticated active HTTP still returned Batch 22/228 and BC 404. Five focused Batch 23 tests, all 423 backend tests and frontend build passed. Separate local-activation authorization is still required; no deployment, push, blocked recovery, Batch 24 or Phase C is implied.

### TC-PSE-B23-05 — Local activation, live API/UI and rollback

Result: [x] Pass [ ] Fail — after separate user authorization, the pinned Batch 23 manifest became locally active with 238 records; Batch 22 rollback manifest remained unchanged. Real authenticated API returned 238/238 stored-detail parity, eight enabled new calculators, BC/OPM plus five inherited disabled calculators, CA's 0.60× edited base PHP6.845964238041838 and unauthenticated 401. Signed-in active PH browser showed the 238-company list, CA calendar/calculator and source links, search to FJP, FJP rights and LC unit warnings, ATN March fiscal year and BC/OPM/PRIM blocked/null. Active Postgres/MinIO readback passed; 124 focused Phase B/API tests, all 423 backend tests and frontend build passed. Temporary test accounts were removed. The user confirmed local activation on 2026-09-25; final read-only preflight and fresh authenticated API still returned Batch 23/238, CA market-relative-only, BC/OPM not-available, with the Batch 22 rollback hash intact. No deployment, push, blocked recovery, Batch 24 or Phase C is implied.

## PSE V2 Phase B Batch 24 — locally active, live-verified and user-confirmed

### TC-PSE-B24-01 — Frozen set, exact catalog and active boundary

Result: [x] Pass [ ] Fail — at the staged gate, the exact confirmed ten plus 238 inherited entries produced byte-identical 248-record twins, with every Batch 23 artifact unchanged. The candidate has 34 intrinsic, 200 market-relative and 14 unavailable records. Batch 23 was active and Batch 24 outside serving then. Subsequent local activation is recorded in TC-PSE-B24-05.

### TC-PSE-B24-02 — Source facts, currencies and claims

Result: [x] Pass [ ] Fail — independently checked PHP parent/common bridges support finite Low-reliability screens only for FPI, BH and MA. AB, FAF, GEO, UPM, X, MFC and SLF remain blocked/null with disabled calculators. The reviewed receipts preserve negative PHP parent equity and C$-millions reports without silently converting them to PHP. Existing Postgres/MinIO readback matched ten current receipts, 31 source facts, ten reviewed share denominators, nine multiples and ten staged runs. Four focused Batch 24 tests, all 427 backend tests and frontend build passed.

### TC-PSE-B24-03 — Real staged API and signed-in PH browser

Result: [x] Pass [ ] Fail — final staged authenticated API returned 248/248 exact stored-detail parity, three enabled new calculators, all 14 blocked/disabled calculators, BH's 0.50× edited base PHP87.10304367913565 and unauthenticated 401. Signed-in staged browser passed the 248-company BH calculator/calendar/source flow, searched to MA, showed its pooled A+B warning, rendered FPI, and kept representative AB/MFC plus inherited BC blocked/null without calculators. Two rapid browser attempts hit the shared 120-per-minute limiter after a bulk scan or many fast page transitions; backend logs showed `429`, and the shorter isolated run passed. Screenshots were captured and temporary accounts removed.

### TC-PSE-B24-04 — Results and activation boundary

Result: [x] Pass [ ] Fail — the user confirmed staged Batch 24 results on 2026-09-25. The exact 248-entry manifest was pinned in a read-only-by-default activation guard. Preflight checked issuer/blocked sets, status counts, parent artifact preservation, receipt hashes and unchanged Batch 23 pointer. Isolated temporary-root activation passed without touching real serving; fresh authenticated active HTTP still returned Batch 23/238 and AB 404. Five focused Batch 24 tests, all 428 backend tests and frontend build passed. Separate local-activation authorization is still required; no deployment, push, blocked recovery, Batch 25 or Phase C is implied.

### TC-PSE-B24-05 — Local activation, live API/UI and rollback

Result: [x] Pass [ ] Fail — after separate user authorization, the pinned Batch 24 manifest became locally active with 248 records; Batch 23 rollback manifest remained unchanged. Real authenticated API returned 248/248 stored-detail parity, three enabled new calculators, all 14 blocked/disabled calculators, BH's 0.50× edited base PHP87.10304367913565 and unauthenticated 401. Signed-in active PH browser showed the 248-company list, BH calendar/calculator and source links, searched MA with its pooled A+B warning, rendered FPI, and kept representative AB/MFC plus inherited BC blocked/null. Active Postgres/MinIO readback passed; 129 focused Phase B/API tests, all 428 backend tests and frontend build passed. Temporary test accounts were removed. The user confirmed local activation on 2026-09-25; final read-only preflight and fresh authenticated API still returned Batch 24/248, BH market-relative-only and MFC not-available, with the Batch 23 rollback hash intact. No deployment, push, blocked recovery, Batch 25 or Phase C is implied.

## PSE V2 Phase B Batch 25 — locally active, live-verified and user-confirmed

### TC-PSE-B25-01 — Frozen set, exact catalog and active boundary

Result: [x] Pass [ ] Fail — the confirmed ten plus 248 inherited entries produced byte-identical 258-record twins. Candidate has 34 intrinsic, 203 market-relative and 21 unavailable; all Batch 24 parent artifacts were unchanged. Final manifest SHA-256 `ae8f1e0b0fc13eab2f39ea5a6f7c2d419cb425ef792c845f8f9f89f1005a308c`. The active pointer stayed on Batch 24/248 and active LTL returned 404.

### TC-PSE-B25-02 — Source facts, claims and null gates

Result: [x] Pass [ ] Fail — independently replayed exact PHP equity/share bridges and finite P/B sensitivities for FFI, MED and MG. FYN's 33,426,498 preferred shares are a nonzero unresolved claim; MAH's parent equity is negative; ZHI's common residual is near zero; LTL's missing facts remain null; VLL/VREIT/ALLDY use stale summaries and suspended stock snapshots. All seven blocked records expose null results and disabled calculators. Existing Postgres/MinIO readback matched ten receipt objects, 28 facts, five supported denominators, nine multiple assumptions and ten runs. Four focused Batch 25 tests and all 432 backend tests passed.

### TC-PSE-B25-03 — Real staged API and signed-in PH browser

Result: [x] Pass [ ] Fail — separate staged authenticated HTTP returned 258/258 exact stored-detail parity, three enabled new calculators, 21 blocked/disabled calculators, MED's edited PHP0.005846717056099208 base at 0.50× P/B and unauthenticated 401. Signed-in staged browser switched US→PH, searched the 258-company list to FFI, interacted with its seven-day calendar, edited its multiple from 0.40× to 0.50× (displayed base PHP2.33), opened its PSE source links, and showed MED's sub-cent display/Edit (PHP0.0058 at 0.50×). Representative FYN, MAH, LTL, VLL, VREIT and ALLDY pages rendered blocked/null. The frontend production build passed with its existing chunk-size warning. An initial staged-only CORS origin mismatch was corrected; isolated browser checks then passed. The temporary local browser-test account was removed. Results confirmation, activation and deployment remain separate gates.

### TC-PSE-B25-04 — Confirmed results and separate activation boundary

Result: [x] Pass [ ] Fail — the user confirmed staged Batch 25 results on 2026-09-25. The exact 258-entry manifest hash was pinned in a read-only-by-default activation guard. Preflight checked the confirmed ten, 21 blocked tickers, status counts, ten receipts, 248 inherited artifacts and unchanged Batch 24 pointer. Isolated temporary-root activation passed while real serving remained unchanged. Fresh authenticated active HTTP returned Batch 24/248 and LTL 404; separate staged HTTP returned Batch 25/258, LTL not-available and FFI market-relative-only. Six focused tests, all 434 backend tests and frontend production build passed. Separate local-activation authorization is still required; no deployment, push, blocked recovery, Batch 26 or Phase C is implied.

### TC-PSE-B25-05 — Local activation, live API/UI and rollback

Result: [x] Pass [ ] Fail — after separate user authorization, the pinned Batch 25 manifest became locally active with 258 records; Batch 24 rollback manifest remained unchanged. Real authenticated API returned 258/258 stored-detail parity, three enabled new calculators, 21 blocked/disabled calculators, MED's 0.50× edited base PHP0.005846717056099208 and unauthenticated 401. Signed-in active PH browser showed the 258-company catalog, FFI calendar, source links and 0.50× edit to displayed PHP2.33, searched/opened MED and displayed its PHP0.0047→0.0058 sub-cent edit, and kept LTL, VREIT and inherited BC blocked/null. Active Postgres/MinIO readback passed; historical builder guards and active-list assertions were advanced to pinned Batch 25 hashes, and the older Batch 24 activation guard now refuses a rollback over Batch 25. All 434 backend tests and the frontend build passed. The user confirmed local activation on 2026-09-25; final read-only preflight and fresh authenticated API still returned Batch 25/258, FFI market-relative-only and LTL/VREIT not-available, with the Batch 24 rollback hash intact. No deployment, push, blocked recovery, Batch 26 or Phase C is implied.

## PSE V2 Phase B Batch 26 — locally active, live-verified and user-confirmed

### TC-PSE-B26-01 — Frozen set, exact catalog and active boundary

Result: [x] Pass [ ] Fail — the confirmed ten plus 258 inherited entries produced byte-identical 268-record twins. Candidate has 34 intrinsic, 204 market-relative and 30 unavailable; all Batch 25 artifacts were unchanged. Final manifest SHA-256 `d1d929b164286168f77d6e0e9d9dbbe93f7af4f73610cc47ec20b88606ebf60a`. Active pointer stayed on Batch 25/258 and active MM returned 404.

### TC-PSE-B26-02 — Source periods, claims and null gates

Result: [x] Pass [ ] Fail — independently replayed the dated PHP parent equity/share bridge and 0.25×/0.40×/0.55× historical P/B sensitivities for MM. DHI's pending merger, UNH/VLC/INFRA's unresolved common-share bridges, PNX's stale preferred/debt claims, I's negative parent equity and HOME/STR/ROX's older periods remain null. All ten checked common-stock snapshots were suspended; no current quote/upside is published. Existing Postgres/MinIO readback matched ten receipt objects, 30 reported facts, five supported denominators, three multiple assumptions and ten runs. Four focused Batch 26 tests and all 438 backend tests passed.

### TC-PSE-B26-03 — Real staged API and signed-in PH browser

Result: [x] Pass [ ] Fail — separate staged authenticated HTTP returned 268/268 exact stored-detail parity, one enabled new MM calculator, all 30 blocked/disabled calculators, MM's edited PHP0.19770744050054204 base at 0.50× P/B and unauthenticated 401. Signed-in staged browser switched US→PH, searched the 268-company catalog to MM, used its seven-day calendar, edited the MM multiple to displayed PHP0.20, read the historical/suspended method text and opened its PSE source references. DHI/UNH/HOME blockers and inherited LTL blocked/null rendered. Frontend build passed with its existing large-chunk warning; the temporary test account was removed. Results confirmation, activation and deployment remain separate gates.

### TC-PSE-B26-04 — Confirmed results and separate activation boundary

Result: [x] Pass [ ] Fail — the user confirmed staged Batch 26 results on 2026-09-25. The exact 268-entry manifest hash was pinned in a read-only-by-default activation guard. Preflight checked the confirmed ten, 30 blocked tickers, status counts, ten receipts, 258 inherited artifacts and unchanged Batch 25 pointer. Isolated temporary-root activation passed while real serving stayed on Batch 25. Fresh authenticated active HTTP returned Batch 25/258 and MM 404; separate staged HTTP returned Batch 26/268, MM market-relative-only and DHI not-available. Six focused tests, all 440 backend tests and frontend production build passed. Separate local-activation authorization is still required; no deployment, push, blocked recovery, Batch 27 or Phase C is implied.

### TC-PSE-B26-05 — Local activation, live API/UI and rollback

Result: [x] Pass [ ] Fail — after separate user authorization, the pinned Batch 26 manifest became locally active with 268 records; Batch 25 rollback manifest remained unchanged. Real authenticated API returned 268/268 stored-detail parity, one enabled new MM calculator, all 30 blocked/disabled calculators, MM's 0.50× edited base PHP0.19770744050054204 and unauthenticated 401. Signed-in active PH browser showed the 268-company catalog, MM calendar/source links/historical method text and 0.50× edit to displayed PHP0.20, searched/opened DHI with its merger blocker, and kept UNH plus inherited LTL blocked/null. Active Postgres/MinIO readback passed; historical builder guards and active-list assertions advanced to pinned Batch 26 hashes, while older Batch 24/25 activation guards now refuse rollback over Batch 26. All 440 backend tests and the frontend build passed. The user confirmed local activation on 2026-09-25; final read-only preflight and fresh authenticated API still returned Batch 26/268, MM market-relative-only and DHI/LTL not-available, with the Batch 25 rollback hash intact. No deployment, push, blocked recovery, Batch 27 or Phase C is implied.

## PSE V2 Phase B Batch 27 — locally active, live-verified and user-confirmed

### TC-PSE-B27-01 — Frozen set, source receipts and null gates

Result: [x] Pass [ ] Fail — the exact confirmed ten have reviewed PSE financial-summary and common-stock paths, preserved original currency/unit labels and individually documented blockers. PNC's absent period/equity/BVPS are null, not zero; AR's printed `PES0` label and inconsistent share counts are preserved as evidence. All ten are `not_available`/`blocked` with null low/base/high and no current price or calculator. Original filing bytes and commercial-use rights are not claimed.

### TC-PSE-B27-02 — Deterministic catalog, persistence and active boundary

Result: [x] Pass [ ] Fail — deterministic twins produced the exact 278-entry candidate, with 268 inherited artifacts byte-identical to active Batch 26. Manifest SHA-256 `9799ff5e8f536d914d1addaa37b10946b402f06c6ec6fe8aca8e570454b44f85`. Postgres/MinIO readback found ten receipt objects, 28 facts, three reviewed denominators, zero multiple assumptions and ten runs. Active pointer hash stayed `ebc67e971ec52323e56ce2b3e909dbf71d4f0400c237f3746ea0d80a5667f371`; active HTTP still returned Batch 26/268 and PNC/AR 404.

### TC-PSE-B27-03 — Real staged API and signed-in PH browser

Result: [x] Pass [ ] Fail — separate staged authenticated HTTP returned 278/278 stored-detail parity, all 40 blocked calculators disabled, PNC filing period null, inherited MM historical base PHP0.158165952 and unauthenticated 401. Signed-in browser switched US→PH, searched the 278-company list to PNC, showed its unavailable state and three source links, clicked the seven-day calendar to change the preview date, and rendered CYBR/SOC/TUBIG blocked reasons. Generic blocked source-copy was corrected for PNC; the temporary test user and five sessions were removed. Four focused tests, all 444 backend tests and frontend production build passed. Results confirmation and activation remain separate gates.

### TC-PSE-B27-04 — Confirmed results and separate activation boundary

Result: [x] Pass [ ] Fail — the user confirmed staged Batch 27 results on 2026-09-25. The exact 278-entry manifest hash was pinned in a read-only-by-default activation guard. Preflight checked the confirmed ten, 40 blocked tickers, status counts, ten receipts, 268 inherited artifacts and unchanged Batch 26 pointer. Isolated temporary-root activation passed while real serving stayed on Batch 26. Fresh authenticated active HTTP returned Batch 26/268 and PNC/AR 404. Six focused tests, all 446 backend tests and frontend production build passed. Separate local-activation authorization is still required; no deployment, push, blocked recovery, Batch 28 or Phase C is implied.

### TC-PSE-B27-05 — Local activation, live API/UI and rollback

Result: [x] Pass [ ] Fail — after separate user authorization, the pinned Batch 27 manifest became locally active with 278 records; the Batch 26 rollback manifest remained unchanged and all 289 served files matched the staged candidate byte-for-byte. Real authenticated API returned 278/278 stored-detail parity, zero enabled new calculators, all 40 blocked calculators disabled, PNC filing period null, inherited MM historical base PHP0.158165952 and unauthenticated 401. Signed-in active PH browser showed the 278-company search, PNC/AR blockers, PNC source links and working seven-day calendar, plus the inherited MM 0.40×→0.50× edit to displayed PHP0.20. Active Postgres/MinIO readback passed; historical builder guards and active-list assertions advanced to pinned Batch 27 hashes, while Batch 24–26 activation preflights refuse a backward switch. All 446 backend tests and frontend build passed. The temporary test account and its four sessions were removed. The user confirmed local activation on 2026-09-25; final read-only preflight and authenticated API still returned Batch 27/278, PNC null/unavailable and MM market-relative-only, with the Batch 26 rollback hash intact. No deployment, push, blocked recovery, Batch 28 or Phase C is implied.

## PSE V2 Phase B Batch 28 — locally active, live-verified and user-confirmed

### TC-PSE-B28-01 — Frozen four, dated sources and numerical/null boundaries

Result: [x] Pass [ ] Fail — the user-confirmed ordinary-common set is exactly `AAA, EG, NXGEN, PTT`. Live PSE financial-summary pages matched the reviewed periods, original currency/unit labels and equity values; stock pages supported the dated share/status lines. Independent `Decimal` replay of NXGEN's PHP669,333,909 parent equity / 1,490,000,003 common shares at 0.25×/0.40×/0.55× reproduced PHP0.112304347/PHP0.179686955/PHP0.247069563. NXGEN is Low-reliability `market_relative_only`/`provisional`, with no licensed price/upside or intrinsic claim. AAA, EG and PTT are `not_available`/`blocked` with null scenarios and disabled calculators. Receipt hashes do not claim original filing bytes or cleared commercial-use rights.

### TC-PSE-B28-02 — Deterministic catalog, persistence and active boundary

Result: [x] Pass [ ] Fail — deterministic twins produced the exact 282-entry candidate, with all 278 Batch 27 artifacts byte-identical. Manifest SHA-256 `8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7`; counts are 34 intrinsic, 205 market-relative, 43 unavailable, 239 provisional and 43 blocked. Postgres/MinIO readback matched four receipts/objects, 12 reported facts, two reviewed denominators, three multiple assumptions and four runs. Active pointer SHA-256 stayed `c1edb4294e00c8e986e5336b2f3b1a226e08b3dd8a074bc1169e4f3ec8218e08`; fresh active HTTP still returned Batch 27/278 and AAA/NXGEN 404.

### TC-PSE-B28-03 — Real staged API and signed-in PH browser

Result: [x] Pass [ ] Fail — separate staged authenticated HTTP returned 282/282 stored-detail parity, one of four new calculators enabled, all 43 blocked calculators disabled, NXGEN's 0.50× edited base PHP0.22460869384306975, and unauthenticated 401. Signed-in browser switched US→PH, searched the 282-company catalog to NXGEN, displayed its market-relative label, PHP0.11/PHP0.18/PHP0.25 low/base/high and non-intrinsic explanation, edited 0.40×→0.50× to displayed PHP0.22, opened PSE source links and changed the seven-day calendar date. AAA, EG and PTT showed distinct blocked/null explanations. The temporary user and five sessions were removed. Four focused tests, all 450 backend tests and frontend build passed. Results confirmation and activation remain separate gates.

### TC-PSE-B28-04 — Confirmed results and separate activation boundary

Result: [x] Pass [ ] Fail — the user confirmed staged Batch 28 results on 2026-09-26. The exact 282-entry manifest hash was pinned in a read-only-by-default activation guard. Preflight checked the confirmed four, 43 blocked tickers, NXGEN's exact low/base/high market-relative screen, status counts, four receipts, 278 inherited artifacts and unchanged Batch 27 pointer. Isolated temporary-root activation passed while real serving stayed on Batch 27. Fresh authenticated active HTTP returned Batch 27/278 and AAA/NXGEN 404. Six focused tests, all 452 backend tests and frontend production build passed. Separate local-activation authorization is still required; no deployment, push, blocked recovery, additional batch or Phase C is implied.

### TC-PSE-B28-05 — Local activation, live API/UI and rollback

Result: [x] Pass [ ] Fail — after separate user authorization, the pinned Batch 28 manifest became locally active with 282 records; the Batch 27 rollback manifest remained unchanged and all 287 served files matched the staged candidate byte-for-byte. Real authenticated API returned 282/282 stored-detail parity, one enabled new NXGEN calculator, all 43 blocked calculators disabled, NXGEN's 0.50× edited base PHP0.22460869384306975 and unauthenticated 401. Signed-in active PH browser showed the 282-company search, NXGEN's separate market-relative label, PSE source links and working seven-day calendar, plus the 0.40×→0.50× edit to displayed PHP0.22; AAA, EG and PTT rendered distinct blocked/null reasons. Active Postgres/MinIO readback passed; historical builder guards and active-list assertions advanced to the pinned Batch 28 hashes, while Batch 24–27 activation preflights refuse a backward switch. All 452 backend tests and frontend build passed. The temporary test account and its five sessions were removed. The user confirmed local activation on 2026-09-26; final read-only preflight and authenticated API still returned Batch 28/282, NXGEN market-relative-only and AAA null/unavailable, with the Batch 27 rollback hash intact. No deployment, push, blocked recovery, additional batch or Phase C is implied.

## Reporting protocol

Record case ID, role, URL, exact actions, observed result versus expected result, timestamp, and screenshot when a visual
delta matters. Mark Pass only after driving the current local build through the real API and database.
