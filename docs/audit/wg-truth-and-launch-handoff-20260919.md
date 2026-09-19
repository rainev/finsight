# WG evidence audit and launch handoff

Date: 2026-09-19. Audit only; no valuations, runtime policies, serving pointers or deployment changed. The user superseded sequential WG continuation with this audit, followed by a separately requested 500-company publication sweep. Existing human approvals are accepted; concrete defects still require resolution.

## Scope and evidence standard

This is a cross-cutting audit of reusable conclusions and the reliability of WG reporting. It is not a re-underwriting of 500 companies, a fresh live API test, or a certification of every historical WG. Direct code/receipt inspection covers current refresh reporting, normalization, pharma claims/bridge, BIIB blocking, plus selected earlier claim, commitment, ownership, margin and operational reports. Earlier reported tests remain historical evidence unless rerun. No claim is established solely by a generated report or its hash: hashes establish byte identity, not financial truth or source authenticity.

## Launch assessment

The staged manifest at `output/batch-50-api-runtime-a/catalogs/US-RESET-2026-08-14-B01-B50-INITIAL-1.0/manifest.json` currently declares 500 entries: 116 available, 358 conditional, 26 unavailable (474 numeric). The inspected `output/universe-500-p0-label-repair-20260912/availability-parity-receipt.json` records 500 served rows and zero stored/served availability mismatches on September 12. These are existing release-candidate evidence, not a fresh 500-company sweep.

The repository serving pointer `backend/app/data/us_valuation_catalogs/active.json` names the 100-company catalog. This is a local repository fact; remote deployed state was not inspected.

A launch of dated, transparent baseline estimates need not wait for fully autonomous refresh or eliminate every Low rating, wide band, or review flag. Final launch readiness is still conditional on the next scoped publication/runtime sweep. Automation blockers do not automatically disqualify an approved historical estimate. Conversely, confirmed double counting, wrong entity/date/scope or a lost approved adjustment cannot be excused by a Low label or prior approval.

## Reusable lessons retained

| Lesson | Evidence inspected | Future application and limit |
|---|---|---|
| Reconcile totals and components once | `refresh_pharma_bridge.py`; WG39 GILD receipt; `refresh_acquisition_claims.py` | Current debt may already be inside a total. Require scope and reconciliation; never infer it from a tag name. |
| Keep ceilings, carrying values and paid cash distinct | `refresh_pharma_claims.py`; WG38–40 source receipts | CVR maxima are contingent exposure. Carrying value is an accounting proxy, not necessarily economic fair value. Paid cash is not another outstanding liability. |
| Establish ownership of cash | WG8 evidence; customer-funds rule; INCY bridge | Customer/restricted funds and strategic holdings are not automatically surplus cash. Classification needs source support. |
| Separate operating reserves from financing claims | WG7/WG34–35 evidence and current scope modules | Avoid deducting a reserve already represented in forecast cash. Historical payments alone do not establish forward runoff. |
| Keep NCI, preferred, conversion and parent earnings consistent | WG12 and WG33 evidence; reported-NCI/preferred rules | Approved carrying proxies may be retained with disclosure. Do not deduct a cash claim and conversion dilution together, or subtract NCI again from parent earnings. |
| Timed commitments need timing and overlap | WG4 evidence; `refresh_commitment_claims.py` | A purchase maximum or new-only lease schedule is not complete current debt. An exact current carrying claim need not invent a payment schedule. |
| Preserve governed assumptions and exclusions | WG24 evidence; governed-margin code; Batch14 history | Approved margins and history exclusions must survive migration unless an explicit economic change is justified. Keep negative history. |
| Match event dates and operating scope | WG37/HON and WG40/BIIB ledgers | A price, cash payment, partial revenue or pro forma earnings table does not establish combined FCFF. Useful partial evidence may leave a review exception. |
| Structural filings can repair Companyfacts lag | `refresh_financials.py`; INCY source receipt | Align FY + current YTD − comparative YTD, including financing basis. Do not use stale periods or fill absent flows with zero. |
| Calculator/API/reload tests demonstrate software behavior | WG39 UAT receipts and verifier code | Preserve exact model parity and version checks. They do not establish economic calibration, future-quarter support, or deployed behavior. |

## Corrections and concrete gaps

All findings below are verified by direct code/receipt inspection unless explicitly qualified.

| ID | Priority | Finding | Required treatment |
|---|---|---|---|
| T01 | P1, candidate promotion | WG39 GILD/INCY refresh loses the original current-TTM exclusion. `batch_14_history.py::_history_profile` excludes TTM for both; `refresh_financials.py::cash_history` builds the profile including TTM. Both current receipts contain a June2026 `operating_ttm` observation. | Reassess normalization before substituting these candidate values in the 500 catalog. Preserve the user's approved baselines pending targeted resolution; do not automatically reject the companies. |
| T02 | P1, automation | GILD rule explicitly names `SeniorUnsecuredNotesDueInMarch2026Member` and requires that note reduction plus royalty-balance reduction equal aggregate repayments. | Captured arithmetic is evidence of compatibility, not a unique proof of royalty cash: interest accretion/other movements require consideration. Classify as a dated reconciliation, not general future-quarter automation. |
| T03 | P1, reporting | Current-version status compares global registry/policy/implementation hashes (`refresh_work_register.py::_choose_source_rows`). A code change can stale unrelated prior successes. | “2 current candidates” is a verification-freshness count, not total working companies or launchable companies. “Needs recheck” is not a count of broken valuations. Prior claim that more receipts alone caused the increase is unsupported. |
| T04 | P1, automation | `assess_biib_scope` always returns review with predefined reasons; selected facts do not automatically clear them. | Retain as a safety/evidence ledger. Do not call it a self-updating economic resolver. Missing scoped facts are not proof that no accrual exists. |
| T05 | P1, assurance | Tests, reviewer PASS, local raw-file hashes and canonical reports can all agree while a modeling assumption is lost (T01). | Check independent economic reference and intended exclusions; treat generated artifacts as auditable evidence, never unquestionable authority. |
| T06 | P1, source robustness | Pharma bridge selectors use finite concept lists and specific named members; these do not prove rejection of every unfamiliar financing/ownership structure. | Limit the future-support claim to tested reporting structures. Require successive real filings before automatic publication. |
| T07 | P2, planning | Estimates of 20–30 more WGs were not derived from a validated work/dependency schedule. | Withdraw that estimate as a completion forecast. Prioritize reusable mechanisms and explicit exceptions, not WG count. |
| T08 | Release handoff | 440-company automation registry and 500-company staged catalog are different scopes. | Select one explicit 500-company release manifest for the next sweep; identify any WG replacements individually. Do not silently rebase or promote receipts. |

T01 reproduction from existing receipts (not new valuations):

`output/us-refresh-runtime/source-validation/3a947cdb8dbf5bdc23c52a45a224b6c6bb3462f4f70e4bb54a5499ba8071efd0/{GILD,INCY}.json`

- GILD includes TTM cash margin 0.45069360166135186; resulting base margin 0.36677284916397124. The original excludes TTM for acquisition/IPR&D comparability.
- INCY includes TTM cash margin 0.3302898239324592; resulting base margin 0.22717674597457158. The original excludes TTM for the CMS/OPZELURA resolution.
- This proves a normalization migration difference, not that either historical rule is eternally optimal. No value recalculation or policy repair was performed in this audit.

Other corrected narrative claims: the historical GILD recipe already uses $26.246B debt; no historical current-debt double-count repair was demonstrated. INCY TTM interest is $2.325M, not $2.448M. RayThera amounts must not inherit TJ Bio dimensional identity. BIIB preferred bindings already referenced the normalized bridge; the added explicit zero proof strengthens source validation, but the earlier assertion that bindings directly hard-coded $335.65M was not supported.

## Current recorded counts and their meaning

Inspected register: 440 companies, 419 historical recipes, 285 compiled instructions, 134 implementation gaps, 197 financial flags, 169 source flags, 437 needing version recheck, 21 prior unavailable, 2 current-version source-bound results, zero successive-period proofs. Counts overlap. The two numeric results are mechanically reproduced candidates whose normalization is now qualified by T01. No runtime receipt was rewritten to erase its historical result.

## Next-prompt publication sweep contract

1. Use the explicit 500-company staged manifest; preserve existing human-approved estimates by default.
2. Classify results as publishable baseline, publishable with disclosure, targeted correction, or unavailable for a concrete reason. Low reliability or broad ranges alone are not failure criteria.
3. Compare any WG replacement against the approved baseline and preserved assumptions. Include T01, BIIB debt/legal scope and existing HON/HCA/MCK/LHX/lease concerns as targeted checks; do not claim this audit resolved them.
4. Verify the selected release's identity, dates, finite ordered ranges, formula/calculator parity, private-data boundary and current consumer flow once. Keep remote deployment as a separate action.
5. Report exact exceptions and value changes. Do not require every automation gap or optional backtest to close before baseline launch.

That sweep is deferred to the next user prompt. No WG41, batch work, publication, external acquisition or runtime mutation was performed here.
