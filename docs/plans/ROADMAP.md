# FinSight controlled 500-company reset roadmap

Date adopted: 2026-08-20

Common valuation date: 2026-08-14

References:

- user-supplied `FinSight Controlled 500-Company Reset Plan`
- `/Users/carlosconda/Downloads/PLAN.md`, `FinSight Free Official-Data Completion Plan`, confirmed 2026-08-24

This roadmap supersedes the earlier phase ordering and the older all-ten-or-nothing Batch 01
promotion rule. It is a logical reset: existing infrastructure, code, tests, evidence, and
valuations are preserved, but old valuations are comparison evidence only.

## Definition of done

Processing completion and publishable numeric completion are reported separately. The full
reset is complete only when exactly 500 unique issuers have explicit outcomes, all frozen
inputs replay deterministically twice, the full backend/API/browser acceptance path passes,
and the user confirms release. A company is publishable with a finite coherent low/base/high
baseline, an economically suitable governed model, a High/Medium/Low reliability label, and a safe
public artifact. Reported facts and estimated assumptions must remain distinguishable; material
assumption-driven results are conditional, capped at Low, and added to the Recovery Learning
Watchlist. No hidden fact is fabricated merely to reach 500/500.

## Protected starting point

- Work only in `.worktrees/whole-universe-greenlight` and preserve every pre-existing dirty
  change and untracked artifact.
- Starting branch/commit: `codex/period-aware-valuation-policy` at `27c2cda`.
- Starting backend suite: 996 passed, 3 skipped.
- Starting serving hash: `34b380fe6678af826fbd63cb53b3fd737a596631e86bbb93346ad04e10c1e00a`.
- Starting serving outcomes: 88 finite review-required, 118 withheld, 206 total.
- Starting Batch 01 comparison: 5/10 finite and 5/10 withheld; 0/10 raw reliability records.
- Generated source packets, private evidence, and replay output remain untracked and
  non-serving. No serving artifact changes before a complete batch report and user approval.

## Phase CR0 — reset adoption and baseline protection

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| CR0.1 | Record branch, commit, dirty state, tests, serving hash, and outcomes | CR-01 | P0 | Direct Git/filesystem reads and full backend suite | ✔ FIRSTHAND VERIFIED |
| CR0.2 | Audit Batch 01 against the controlled-reset reference | CR-01–CR-09 | P0 | `docs/audit/09-controlled-reset-batch-01.md` cross-check | ✔ FIRSTHAND VERIFIED |
| CR0.3 | Reconcile roadmap and backlog without erasing prior evidence | CR-01, CR-07 | P0 | Re-read roadmap/backlog and `git diff --check` | ✔ FIRSTHAND VERIFIED |

Gate: protected starting state is reproducible and the current implementation gaps are
explicit. **Passed; proceed under the user's instruction to implement Batch 01.**

## Phase CR1 — immutable Batch 01 and model governance

Batch 01 remains exactly: AAPL, MSFT, CRM, ANET, WDC, DELL, JPM, BAC, NEE, O.

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| CR1.1 | Add one immutable manifest with identities, CIKs, regime, accounting standard, date, and lane hypotheses | CR-02 | P0 | Exact-membership, uniqueness, immutability, and invalid-lookup tests | ✔ FIRSTHAND VERIFIED — 2 focused tests |
| CR1.2 | Add private economic-profile and model-decision schemas | CR-03 | P0 | Contract tests for required economics, candidates, rejected alternatives, accessions, maturity, and cap | ✔ FIRSTHAND VERIFIED — 4 focused tests |
| CR1.3 | Add initial accession-linked records for all ten; treat configured routes only as hypotheses until source-packet validation | CR-08 | P0 | Per-company record validation plus adversarial wrong-model review | ✔ FIRSTHAND VERIFIED — 10/10 load as Withhold hypotheses |

Gate: every member has one validated private profile and decision record; no model is accepted
merely because SIC or an old artifact selected it. **Passed:** all ten records load through the
real private contract, retain an accession, and remain `hypothesis` / `Withhold` pending CR2.

## Phase CR2 — immutable point-in-time source packets

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| CR2.1 | Capture submissions and Companyfacts for exactly ten issuers in a non-serving tree | CR-04 | P0 | Identity/date/hash tests; serving hash unchanged | ✔ FIRSTHAND VERIFIED — 10/10 real packets |
| CR2.2 | Select only filings public by 2026-08-14 and preserve accession, filed date, period, unit, and currency | CR-04 | P0 | Packet ledger and future-filing rejection tests | ✔ FIRSTHAND VERIFIED — payload hashes and cutoff ledgers pass |
| CR2.3 | Invoke offline Arelle only for unresolved filing structure; keep it out of generation and FastAPI imports | CR-04, CR-06 | P0 | Offline parser receipt and serving-process import check | ✔ FIRSTHAND VERIFIED — 5/5 parsed, zero failures |
| CR2.4 | Record accepted, rejected, missing, and conflicting evidence separately | CR-04 | P0 | Packet-schema tests and representative manual trace | ✔ FIRSTHAND VERIFIED — 1 accepted, 10 rejected, 8 unresolved |

Gate: 10/10 identities have verified immutable packets or one explicit invalid/source blocker;
the serving hash is unchanged. **Passed:** all ten raw packets pass identity, payload-hash,
cutoff, and cache checks; five required filing packages parsed offline; the two structural runs
produced the same 22 files and tree hash; no rejected or unresolved decision was promoted.

## Phase CR3 — Batch 01 lanes and valuations

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| CR3.1 | Reconstruct current TTM flows and latest trustworthy balance snapshots without annual-flow copying or missing-as-zero | CR-05 | P0 | Quarterly/YTD, 365/366, zero-vs-missing, unit/period/currency tests | ✔ FIRSTHAND VERIFIED — point-in-time selectors and real packet replay |
| CR3.2 | Resolve lane-specific gaps exposed by the ten companies, building only the smallest reusable lane increments | CR-08 | P0 | Formula benchmarks, limiting cases, hand calculations, and real filing traces | ✔ MECHANICS VERIFIED — missing issuer inputs explicitly block model selection |
| CR3.3 | Produce one explicit numeric, withheld, or invalid outcome per company with low/base/high and reliability when eligible | CR-05 | P0 | Exactly 10 outcomes; finite ordered ranges; maturity cap and blocker tests | ✔ FIRSTHAND VERIFIED — 0 numeric, 10 withheld, 0 invalid |
| CR3.4 | Independently challenge arithmetic, assumptions, wrong-model risk, dilution/debt/cash monotonicity, and terminal constraints | CR-08 | P0 | Calculation traces and adversarial review receipt | ✔ SOL HIGH SUBSTITUTE REVIEW — Luna unavailable |

Gate: all ten remain in the denominator, every outcome is explicit, and each numeric result is
mechanically correct and economically routed. Numeric coverage may be below 10/10 only with
exact blockers; it may not be raised by fabrication or substitution. **Passed honestly:** all
ten outcomes are withheld with exact evidence/model blockers; legacy diagnostic values are not
counted as controlled-reset results.

## Phase CR4 — strict-policy deterministic verification and Batch 01 report

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| CR4.1 | Regenerate twice from frozen inputs in separate non-serving directories | CR-05, CR-06 | P0 | Byte-identical artifact and report hashes | ✔ FIRSTHAND VERIFIED — structural and valuation trees identical |
| CR4.2 | Verify public safety and staged FastAPI list/detail agreement for all ten | CR-06 | P0 | Real local API responses; no private evidence; Arelle absent | ✔ FIRSTHAND VERIFIED — list + 10/10 detail HTTP 200 |
| CR4.3 | Run focused, lane, and complete backend suites plus representative browser flow when available | CR-06 | P0 | Exact commands/output and browser evidence or explicit UI limitation | ✔ BACKEND 1040 PASSED; browser explicitly deferred in B15 |
| CR4.4 | Record reusable learnings, regressions, policy versions, earlier-company impact, and old-vs-new changes | CR-05 | P0 | Learning index, tests, replay list, and change report | ✔ FIRSTHAND VERIFIED — prior 106-candidate replay deterministic |
| CR4.5 | Produce the complete Batch 01 report and stop for user confirmation | CR-05–CR-08 | P0 | Required 10-company table, counts, blockers, hashes, and cumulative 10/500 | ✔ VERIFIED — USER CONFIRMATION NEEDED |

Gate: report the batch as **verified — user confirmation needed**. Stop here. Do not promote,
start Batch 02, construct substitute universe members, merge, or deploy. **Reached:** this is the
strict-policy stop gate. The user's subsequent practical-policy implementation request keeps
Batch 01 open and supersedes this as the current work gate; it does not approve promotion.

## Phase PB0 — practical-policy adoption and blocker audit

Reference: `docs/audit/11-practical-bounded-uncertainty-policy.md`.

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| PB0.1 | Preserve the strict 0/10 result as the comparison baseline | PB-09 | P0 | Re-read strict artifacts, hashes, and serving tree | ✔ FIRSTHAND VERIFIED |
| PB0.2 | Classify every Batch 01 blocker as bounded, unbounded, model-development, or extraction | PB-01–PB-10 | P0 | Source-packet/private-trace/code audit plus independent lenses | ✔ FIRSTHAND VERIFIED — final economic challenge passed |
| PB0.3 | Confirm only public competitor practices are reused | PB-02 | P1 | AlphaSpread/GuruFocus public methodology pages; no proprietary formulas | ✔ FIRSTHAND VERIFIED |

Gate: the strict result remains immutable comparison evidence and every proposed relaxation has
a named source/range path or remains withheld. **Passed into shared implementation; model
judgment still gates each company.**

## Phase PB1 — shared practical bounded-uncertainty contract

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| PB1.1 | Add governed bounded-model decision/range records without weakening hard safety blockers | PB-01, PB-02 | P0 | Boundary, nonfinite, nonpositive, identity/source/conflict, and missing-vs-zero tests | ✔ VERIFIED |
| PB1.2 | Add private and public-safe practical-policy reason codes | PB-03 | P0 | Exact allowlist, round-trip, and public-scrubbing tests | ✔ VERIFIED — exact eight-code contract |
| PB1.3 | Wire consolidated/R&D/capex/cycle/bank/utility/AFFO uncertainty into ordered low/base/high and Low caps | PB-04, PB-06–PB-08 | P0 | Formula, monotonicity, hand-calculation, and limiting-case tests | ✔ VERIFIED — unbounded routes still withhold |
| PB1.4 | Add practical bridge ranges for finite non-operating claims without zero substitution | PB-05 | P0 | Real AAPL/ANET traces, aggregate coverage, range arithmetic, and conflict tests | ✔ VERIFIED — joint endpoints included |

Gate: shared policy can publish only finite ordered ranges from source-linked bounded assumptions,
always caps material provisional uncertainty at Low, and still withholds every hard safety case.
**Passed.**

## Phase PB2 — practical Batch 01 company routes

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| PB2.1 | Apply consolidated operating fallbacks and R&D/capex/SBC/growth sensitivities to AAPL, MSFT, CRM, and ANET | PB-04, PB-05 | P0 | Real packets, old-vs-new arithmetic, direction tests | ✔ VERIFIED — four numeric Low |
| PB2.2 | Apply provisional common-equity/regulatory-capital residual-income ranges to JPM and BAC | PB-06 | P0 | Source-aligned equity/earnings, hand RI, capital sensitivity | ✔ VERIFIED — corrected common-equity mechanics |
| PB2.3 | Apply mixed-utility consolidated FCFE fallback to NEE and AFFO/NAV fallback to O | PB-07, PB-08 | P0 | Source-linked cash flow/AFFO/NOI ranges and monotonicity | ✔ VERIFIED HONESTLY — O numeric AFFO DCF; NEE withheld on latest-period extraction gap |
| PB2.4 | Keep WDC and DELL withheld unless finite source-backed cycle/finance separation is proven | PB-02, PB-10 | P0 | Explicit unbounded blockers; no invented range | ✔ VERIFIED — both withheld |

Gate: exactly ten outcomes, no substitutions, and every newly numeric result has source-linked
finite low/base/high, Low cap, reason codes, and a suitable model.
**Passed: 7 numeric Low / 3 withheld / 0 invalid.**

## Phase PB3 — independent challenge and regression replay

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| PB3.1 | Compare strict and practical outputs company by company | PB-09 | P0 | Exact 10-row change report and arithmetic traces | ✔ VERIFIED — audit 12 |
| PB3.2 | Independently challenge every newly numeric result and resolve Important/Critical findings | PB-10 | P0 | Source/date, formula, sensitivity, model suitability, boundedness review | ✔ SOL HIGH SUBSTITUTE PASS — no Important/Critical open |
| PB3.3 | Replay all earlier companies affected by shared rules | PB-04–PB-08 | P0 | Frozen-corpus replay, unsafe-promotion count, serving hash | ✔ VERIFIED — 106 candidates, zero unsafe promotions |

## Phase PB4 — deterministic real-consumer verification and stop gate

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| PB4.1 | Regenerate strict/practical Batch 01 twice | P0 | Byte-identical artifacts and reports | ✔ VERIFIED — both policies deterministic |
| PB4.2 | Run focused and complete backend suites | P0 | Exact commands and output | ✔ VERIFIED — 220 focused; 1068 full |
| PB4.3 | Start the real staged API and verify list/detail for all ten; prove Arelle isolation | P0 | HTTP 200 agreement, public safety, import receipt | ✔ VERIFIED — list + 10/10 details; zero Arelle imports |
| PB4.4 | Present exact comparison and stop for user confirmation | P0 | Complete report with counts, values, caps, fallbacks, blockers | ✔ VERIFIED — USER CONFIRMATION NEEDED |

Gate: **verified — user confirmation needed**. Nothing is promoted; Batch 02, main, merge, and
deployment remain out of scope. **Reached; stop here.**

## Phase RR0 — three-company recovery evidence gate

Reference: user-approved NEE, DELL, and WDC recovery plan. The existing seven practical Batch 01
results remain staged and all serving artifacts stay protected.

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| RR0.1 | Freeze the recovery baseline and exact three-company denominator | P0 | Git/source/output/serving hashes and 7/3 report re-read | ✔ VERIFIED |
| RR0.2 | Capture NEE Q2 and DELL annual filing packages by exact eligible accession | P0 | CIK/accession/form/date/package hashes; no future source | ✔ VERIFIED — NEE annual added only when TTM capex required it |
| RR0.3 | Capture one Seagate submissions/Companyfacts packet for the WDC cycle benchmark | P0 | Identity/cutoff/hash and annual paired-metric coverage | ✔ VERIFIED — ten paired states |

Gate: do not build a model until its exact current evidence and required historical range are
source-verifiable. Failed evidence leaves that issuer withheld without consuming later model work.
**Passed; source trees B/C are byte-identical.**

## Phases RR1–RR3 — sequential issuer recovery

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| RR1 | Recover NEE with direct Q2 extraction and provisional mixed-utility consolidated FCFE | P0 | Current-period reconciliation, formula/direction tests, real packet run | ✔ VERIFIED HONESTLY — period fixed; complete bear/base FCFE nonpositive, remains withheld |
| RR2 | Recover DELL with anti-double-counted captive-finance consolidated FCFE and DFS reconciliation | P0 | DFS cash/funding reconciliation, double-count tests, real annual/Q1 run | ✔ VERIFIED — numeric Low |
| RR3 | Recover WDC with paired WDC/Seagate normalized-cycle FCFF and EPV diagnostic | P0 | Comparable-state ledger, percentile/fade arithmetic, real filing run | ✔ VERIFIED — numeric Low |

Each route remains Provisional and capped at Low. A failed source, reconciliation, comparability,
share, claim, or nonpositive-value gate remains withheld; 3/3 is a target, never a quota.

## Phase RR4 — independent challenge and complete Batch 01 replay

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| RR4.1 | Independently challenge all newly numeric recovery results | P0 | Source/date/unit, formula, sensitivity, suitability, boundedness receipt | ✔ SOL HIGH SUBSTITUTE PASS — no Important/Critical open |
| RR4.2 | Regenerate strict/practical Batch 01 twice and compare exact trees | P0 | Byte-identical A/B outputs; exactly ten outcomes | ✔ VERIFIED — 9 numeric / 1 withheld |
| RR4.3 | Run focused/full suites, affected-corpus replay, and real staged API | P0 | Tests, zero unsafe promotions, list/detail parity, zero Arelle imports | ✔ VERIFIED — 1078 full; API 10/10 |

## Phase RR5 — Batch 01 learning graduation and stop gate

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| RR5.1 | Record proven source, routing, model, and transparency learnings from all ten | P0 | One durable learning per non-obvious reusable rule plus regression pointer | ✔ VERIFIED — five durable recovery learnings |
| RR5.2 | Add proven controls to the Batch 02+ preflight without validating immature lanes | P0 | Preflight tests and explicit Provisional/Low maturity caps | ✔ VERIFIED — four deterministic preflight actions; lanes remain Provisional |
| RR5.3 | Present one final Batch 01 comparison and stop for approval | P0 | Exact 10-row report, evidence hashes, blockers, no serving writes | ✔ VERIFIED — USER CONFIRMATION NEEDED |

Gate: **verified — user confirmation needed**. The seven prior results and any recovered results
remain unserved until explicit approval. Do not start Batch 02, merge, or deploy.

## Phase CR5 — after Batch 01 approval: per-company promotion

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| CR5.1 | Promote only individually passing Batch 01 artifacts after explicit approval | P0 | Guarded exact-file replacement and before/after hash ledger | Blocked on user approval |
| CR5.2 | Re-run serving API acceptance and confirm non-batch artifacts are unchanged | P0 | List/detail equality and non-batch hash reconciliation | Blocked on CR5.1 |

## Phase U — VERIFIED: freeze the authorized 500 and Batches 02–50

The original historical 500-row artifact could not be recovered, so the required stop was
reached. The user then explicitly authorized an S&P 500 issuer universe effective 2026-08-14 as
the replacement denominator. Freeze exactly 500 issuer CIKs and 49 remaining immutable ten-
company manifests before processing Batch 02.

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| U0.1 | Add Batch 01 companies still withheld after one recovery to the cumulative reset register | P0 | Exact ticker/CIK/model/blocker and one-attempt contract tests | ✔ VERIFIED — NEE first entry |
| U0.2 | Freeze exactly 500 replacement issuer identities effective 2026-08-14 | P0 | Pinned source, exact count, CIK/share-class/cutoff reconciliation, A/B canonical equality | ✔ VERIFIED — public reconstruction, 503 securities / 500 CIKs |
| U0.3 | Freeze and hash Batches 02–50 before processing Batch 02 | P0 | 490 remaining unique CIKs, 49×10 partition, truthful lane/boundary constraints | ✔ VERIFIED — exact cover, deterministic root `fd499771…` |
| U0.4 | Maintain the Recovery Learning Watchlist for every withheld or material conditional issuer through Batch 50 | P0 | Machine contract, exact withheld coverage, learning themes and revisit triggers | ✔ VERIFIED — 7 current entries |

Gate: **verified — user confirmation needed.** Batch 02 is frozen as OMC, VZ, T, TTWO, NFLX,
CHTR, CMCSA, TMUS, META, and WBD, but none has been processed. Await the explicit signal
`Process frozen Batch 02.` No serving write, promotion, Batch 03 work, merge, or deployment.

## Phase B02 — initial pass verified; user confirmation needed

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B02.1 | Capture exact SEC packets and controlling structural filings for all ten | P0 | CIK/ticker/cutoff/hash reconciliation; protected-root hashes | ✔ VERIFIED — 10/10 packets and 10/10 Arelle parses |
| B02.2 | Apply strict and practical policy with explicit source/model decisions | P0 | Exact denominator; finite ordered ranges or named hard blockers | ✔ VERIFIED — strict 0/10; practical 4 numeric Low / 6 withheld |
| B02.3 | Independently challenge every numeric and withheld decision | P0 | Source/arithmetic/model/sensitivity/public audit | ✔ VERIFIED — final Luna-High PASS, no Critical/Important finding |
| B02.4 | Regenerate twice, run regression/full suite, and preserve serving roots | P0 | Byte equality, full backend, prior public contract, tree hashes | ✔ VERIFIED — `fdb0a830…`, 1103 passed, no serving writes |
| B02.5 | Exercise real local FastAPI list/detail for all ten | P0 | Uvicorn process; list count 10; 10 detail parity; zero private leaks/Arelle | ✔ VERIFIED — list 200/10; details 10/10 200; exact parity; zero leaks/Arelle |
| B02.6 | Present all initial results and stop before recovery | P0 | Exact 10-row report; no register update or Batch 03 | ✔ VERIFIED — user confirmation needed before separate recovery signal |

Gate: **verified initial pass.** Source, valuation, challenge, determinism, tests, real localhost
HTTP, and serving safety passed. Recovery was subsequently authorized and completed in B02-R;
no serving promotion, Batch 03 work, merge, or deployment.

## Phase B02-R — one-attempt recovery verified; user confirmation needed

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B02-R1 | Research the smallest public-method/source-backed workaround for all six | P0 | Official methodology and issuer filing cross-check | ✔ VERIFIED — public concepts only; no proprietary formulas |
| B02-R2 | Attempt each withheld issuer once without forcing a quota | P0 | Exact six receipts with model, source, blocker, and trigger | ✔ VERIFIED — 6/6 attempted; 0 recovered; 6 withheld |
| B02-R3 | Independently challenge economic decisions and provenance | P0 | Luna-High source/model/receipt audit | ✔ VERIFIED — period defect fixed; final PASS |
| B02-R4 | Regenerate twice, run full suite, and verify real API | P0 | Byte equality, backend suite, list/detail parity/privacy | ✔ VERIFIED — `6a46fe37…`, 1107 passed, API 10/10 |
| B02-R5 | Append every still-withheld issuer to the cumulative register | P0 | One attempt each; sorted unique ticker/CIK entries | ✔ VERIFIED — register now 7 total (NEE + six Batch 02) |

Gate: **verified — user confirmation needed.** Final Batch 02 remains 4 numeric Low / 6
withheld. The six holdouts have consumed one automatic recovery and are registered. No serving
promotion, Batch 03, merge, or deployment.

## Phase FOD1 — NOW: generalized official filing ingestion

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| FOD1.1 | Add point-in-time private evidence request/candidate/decision contracts | OE1-02–OE1-04 | P0 | Round-trip, cutoff, failure, rejected-candidate, and silent-missing tests | ✔ VERIFIED — contracts + identity/cutoff invariants |
| FOD1.2 | Add manifest-driven controlling + latest-annual selection and material-gap trigger | OE1-01 | P0 | Arbitrary issuer manifest, cutoff/amendment, annual/controller identity tests | ✔ VERIFIED — canonical selector and source cross-check |
| FOD1.3 | Capture governed relevant attachments and immutable parsed-output cache | OE1-05–OE1-06 | P1 | Package hash/role and parse-once deterministic tests | ✔ VERIFIED — generation-bound cache and lock |
| FOD1.4 | Replay Batch 01/02 and known empty-Companyfacts controls through the generalized runner | OE1-07 | P0 | Exact denominator, explicit outcomes, A/B hashes, protected roots | ◐ PARTIAL — Batch 01/02 byte-identical; difficult corpus source tree unavailable, moved to FOD5 |

Gate: **verified partial.** Batch 01/02 requests are explicit and byte-identical, four filing-only facts were recovered, and protected roots are unchanged. FOD2 may proceed because semantic work does not require the absent corpus; the difficult-corpus/uncached-package portion remains an explicit FOD5 acceptance blocker.

## Phase FOD2 — NOW: governed semantics, tables, DQC, and restatements

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| FOD2.1 | Unify field governance for standard/custom concepts, scopes, aggregates, exclusions, and economic meaning | OE2-01–OE2-02 | P0 | Custom-tag/consolidation/aggregate/double-count fixtures | ✔ VERIFIED — exact registry + decision gate |
| FOD2.2 | Replace ticker-specific table parsing with dated deterministic table evidence and complete-search receipts | OE2-03–OE2-04 | P0 | Current/comparative, multi-number, duplicate, ambiguous, and not-disclosed fixtures | ✔ VERIFIED — strict observations; primary-only no-matches unresolved |
| FOD2.3 | Add offline taxonomy-matched DQC diagnostics and semantic restatement ledger | OE2-05–OE2-06 | P0 | DQC cannot create values; pre/post-amendment cutoff replay | ✔ VERIFIED — rule stats + classified value-change ledger |
| FOD2.4 | Normalize evidence outcomes and exercise every rejection/zero edge case | OE2-07–OE2-08 | P0 | Exact outcome matrix with no silent zero | ✔ VERIFIED — 315 focused tests |

Gate: **verified.** Semantic fixtures and real Batch 01/02 artifacts fail closed, byte-identical, and preserve cutoff identity. DQC is execution-proven and diagnostic-only. Package-complete `not_disclosed` remains unavailable until FOD3 provides governed attachment/source inventories.

## Phase FOD3 — NOW: free official specialist packets

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| FOD3.1 | Add immutable specialist packet/receipt and CIK–RSSD–LEI/entity-bridge contracts | OE3-01–OE3-02 | P0 | Identity, ownership, consolidation, cutoff, hash, and rejection fixtures | ✔ VERIFIED — parent crosswalk + strict contracts |
| FOD3.2 | Add FR Y-9C parent packets with FFIEC subsidiary corroboration | OE3-03 | P0 | JPM/BAC capital/equity packet or exact official-source blocker | ✔ BLOCKER VERIFIED — identities pass; current bulk endpoint HTTP 403 |
| FOD3.3 | Add FERC utility packets and parent/allocation proof | OE3-04 | P0 | NEE/FPL packet or exact official-source blocker | ✔ BLOCKER VERIFIED — CID/payload/allocation unresolved |
| FOD3.4 | Add SEC-filed REIT Exhibit 99 packet and issuer-defined reconciliation | OE3-05 | P0 | Realty Income FFO/AFFO packet or exact official-source blocker | ✔ BLOCKER VERIFIED — exact source link; immutable payload absent; residual unresolved |
| FOD3.5 | Make every specialist input cutoff-safe before adapters consume it | OE3-06–OE3-07 | P0 | Later-filed and subsidiary-to-parent rejection plus representative real packet run | ✔ VERIFIED — cutoff/lineage/order regressions |

Gate: **verified with blockers.** All four representative paths have verified identities/source links or exact payload/allocation blockers. No specialist packet is promotable and none affects valuation.

## Phase FOD4 — NOW: evidence-order valuation integration

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| FOD4.1 | Enforce official-source exhaustion and project complete decisions into production availability | OE4-01–OE4-03 | P0 | Precedence/conflict/range/model-suitability tests | ✔ VERIFIED — declared tiers + typed projections |
| FOD4.2 | Preserve exact private trace while maintaining public schema/privacy and parser isolation | OE4-04, OE4-06 | P0 | Shape snapshots, sanitizer, list/detail parity, import assertion | ✔ VERIFIED — real API 20/20, zero leaks/imports |
| FOD4.3 | Preserve specialist model identity in downstream public generation | OE4-05 | P1 | Bank/utility/REIT model-policy contract tests | ✔ VERIFIED — four model families preserved |

Gate: **verified.** Staged list/detail shape and values reconcile exactly, 225 private decisions produce zero leaks, and serving imports no Arelle/regulator/supplement parser code. Specialist data remains shadow-only because no packet is promotable.

## Phase FOD5 — NOW: full replay and rollout evidence

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| FOD5.1 | Freeze the exact combined replay manifest and reconcile the difficult-corpus denominator | OE5-01 | P0 | Unique issuer/request ledger with included/excluded reasons | ✔ VERIFIED — 121 unique / 133 memberships |
| FOD5.2 | Emit complete rescue, restatement, DQC, outcome, cause, safety, and hash metrics | OE5-02–OE5-03 | P0 | Metric reconciliation and zero unsafe promotions | ✔ VERIFIED — 225 outcomes; zero unsafe |
| FOD5.3 | Regenerate twice, run focused/full suites, and verify staged localhost API | OE5-04–OE5-05 | P0 | Byte equality, protected hashes, test output, HTTP list/detail/privacy/import evidence | ✔ VERIFIED — 1,175 pass; 20/20 API |
| FOD5.4 | Present evidence and keep serving/promotion/Batch 03 frozen for user confirmation | OE5-06 | P0 | Zero serving changes and explicit user done-gate | BLOCKED — specialist payloads + user gate |

Gate: **general SEC evidence verified; specialist/user gate open.** Batch 01, Batch 02, and all 106 difficult issuers pass outcome, exhaustion, consumer, determinism, safety, full-suite, and real API checks. Promotable specialist packets remain unavailable, and user confirmation is still required before any serving write or Batch 03.

## Phase B02-RX — NOW: user-authorized revised-extraction retry

This is a separately authorized retry after the official-evidence pipeline revision. It does not
reset the one automatic recovery attempt recorded in Phase B02-R.

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B02-RX1 | Re-audit the six prior release conditions against FOD5 governed evidence and consumer replay | P0 | Audit 30 exact field/blocker matrix | ✔ FIRSTHAND AUDITED |
| B02-RX2 | Build an immutable six-company revision-retry receipt without changing public artifacts | P0 | Exact input hashes, evidence deltas, release-condition decisions | ✔ VERIFIED — 0/6 release conditions cleared |
| B02-RX3 | Reproduce twice and run focused/full backend suites | P0 | Byte-identical tree hashes and pytest evidence | ✔ VERIFIED — `b201d335…`; 1,181 passed |
| B02-RX4 | Exercise the real staged Batch 02 API and prove list/detail/privacy/import safety | P0 | Uvicorn list + ten details + leak/import assertions | ✔ VERIFIED — list 10; detail 10/10; zero leaks/imports |
| B02-RX5 | Record the separate revision retry, update durable learning/audit evidence, and stop | P0 | Register schema, Audit 31, learning index, no Batch 03 | ✔ VERIFIED — separate retry count retained |

Gate: **verified — user confirmation needed.** Final Batch 02 remains 4 numeric Low / 6 withheld.
The six remain registered after one automatic attempt plus one explicit pipeline-revision retry.
No serving write, promotion, Batch 03 work, merge, or deployment.

## Phase B02-CE — NOW: conditional estimates with explicit warnings

Reference: Audit 32 and the user's authorization to value judgmental future-event states without
calling them reported facts or ordinary source-bounded intrinsic values.

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B02-CE1 | Add a public-safe conditional-estimate model identity and Low-only policy | P0 | Sanitizer/model/reliability contract tests | ✔ VERIFIED — conditional output identity; fail-closed scrubbing |
| B02-CE2 | Implement exact private scenario arithmetic for OMC, TTWO, CHTR, CMCSA, META, WBD | P0 | Formula replay, sources, missing-vs-zero, sensitivity tests | ✔ VERIFIED — 6/6 finite/nonnegative ranges |
| B02-CE3 | Stage all ten with six conditional values and concise warnings | P0 | Public/private parity, zero private leaks, no register/serving mutation | ✔ VERIFIED — 10/10 staged numeric; register/serving unchanged |
| B02-CE4 | Independently challenge every value and resolve Critical/Important findings | P0 | Source/model/arithmetic/direction/event-state review | ✔ LUNA HIGH PASS — all Critical/Important resolved |
| B02-CE5 | Regenerate twice, run focused/full tests, and exercise real API | P0 | Byte equality, pytest, list/detail/privacy/import evidence | ✔ VERIFIED — `1f27b04d…`; 1,189 passed; API 10/10 |
| B02-CE6 | Record durable learning and present exact comparison for confirmation | P0 | Learning index + Audit 33; stop before Batch 03 | ✔ VERIFIED — user confirmation pending |

Gate: **technically verified — user confirmation needed.** Conditional policy displays 10/10
numeric Batch 02 outcomes, all six new estimates Low. Source-bounded policy/register remain
unchanged. No serving write, register removal, promotion, Batch 03, merge, or deployment.

## Phases B03–B50 — controlled batch loop

For each batch: freeze -> source packets -> normalize -> hard safety gate -> economic profile ->
source-bounded or conditional baseline model -> valuation -> independent challenge -> deterministic real
consumer verification -> learning/regressions -> earlier-company replays -> report -> user
approval -> per-company promotion. Default behavior is to stop after every report unless the
user grants explicit standing-proceed.

The governing objective is decision support, not market prediction. Ordinary uncertainty widens
the range and lowers reliability; it does not cause withholding after the hard safety gate. See
Audit 37.

### Phase B03 — NOW: controlled initial pass

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B03.1 | Freeze and validate the exact ten-company Batch 03 contract | P0 | Manifest hash, exact identities, uniqueness, partition parity | ✔ FIRSTHAND AUDITED |
| B03.2 | Capture/reuse cutoff-safe SEC packets and controlling structural filings | P0 | Ten identities, dates, payload/package hashes, protected roots | ✔ VERIFIED — 10/10 packets; 10/10 parses |
| B03.3 | Apply strict and practical source-bounded valuation policy | P0 | Exact denominator; finite ordered ranges or explicit hard blockers | ✔ VERIFIED — 3 numeric Low / 7 withheld |
| B03.4 | Independently challenge every numeric and withheld decision | P0 | Source/model/arithmetic/sensitivity/event/claims review | ✔ LUNA HIGH PASS — all Critical/Important resolved |
| B03.5 | Reproduce twice, run focused/full suites, and verify real API | P0 | Byte equality, pytest, list/detail/privacy/import evidence | ✔ VERIFIED — `53892cba…`; 1,198 passed; API 10/10 |
| B03.6 | Present initial results and stop before recovery or watchlist mutation | P0 | Exact 10-row report; no Batch 04/serving/merge/deploy | ✔ VERIFIED — user confirmation pending |

Gate: **technically verified — user confirmation needed.** Initial Batch 03 is 3 numeric Low / 7
withheld. Conditional estimates, recovery, Recovery Learning Watchlist changes, Batch 04, serving
writes, promotion, merge, and deployment remain outside this initial pass.

### Phase LF1 — NOW: shared launch-first contract and safety boundary

Reference: user-supplied `FinSight Launch-First Valuation Plan` and Audits 38–40. The user's
implementation request is the Batch 03 recovery signal. It does not authorize Batch 04, serving
promotion, merge, push, or deployment.

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| LF1.1 | Add one validated `BaselineValuation`/availability/fallback-attempt contract and table-driven decision policy | LF-R1, LF-R3 | P0 | Contract, ordering, hard-failure, relative/conditional labeling tests | ✔ VERIFIED — ordered ladder and hard-failure contracts |
| LF1.2 | Extend the public allowlist to v1.2 while accepting v1.1 for one cycle | LF-A1, LF-A4 | P0 | Legacy/current round-trip, raw-price injection, withheld scrubbing tests | ✔ VERIFIED — 194 focused; live API 10/10 |
| LF1.3 | Add private EOD record validation and derived-gap semantics without a vendor client in serving imports | LF-A3, LF-A6, LF-A7 | P0 | Listing/currency/date/split/hash rejection and price non-disclosure tests | ✔ VERIFIED — data absence remains explicit |

Gate: **passed firsthand.** The shared contract fails closed on hard safety, preserves v1.1 fields,
and exposes only derived comparison fields. Absence of approved EOD records is an explicit
`comparison unavailable`, not fabricated data. Evidence: Audit 41.

### Phase LF2 — Batch 03 launch-first recovery

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| LF2.1 | Apply normalized/standalone/conditional baselines to LYV, ECHO, GOOGL, APP, FOXA, TKO, and PSKY | LF-R2 | P0 | Real frozen packets, reported/assumed ledger, formula and direction tests | ✔ VERIFIED — 5 new Conditional Low; ECHO/PSKY unavailable |
| LF2.2 | Keep genuine identity/share/conflict/nonfinite failures unavailable and label event-dependent states conditional | LF-R2, LF-R5 | P0 | Adversarial economic-object and zero-floor tests | ✔ VERIFIED — final independent PASS |
| LF2.3 | Regenerate Batch 03 twice and replay Batches 01–03 through the new contract without serving writes | LF-R3 | P0 | Exact denominators, A/B hashes, before/after coverage, protected-root hashes | ✔ VERIFIED — 30 unique / 27 numeric; byte-identical |

Gate: **passed firsthand.** Every Batch 03 company has a finite coherent range or a named hard
failure. Numeric coverage is a target, never a quota. Evidence: Audit 42.

### Phase LF3 — calculator, persistence, and retail flow

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| LF3.1 | Add safe GET/POST U.S. calculator endpoints with locked facts, model-specific limits, manual price/reset semantics, and default/base parity | LF-A2 | P0 | Endpoint, override, monotonicity, invalid-input, reset, API parity tests | ✔ VERIFIED — 30/30 real API parity |
| LF3.2 | Extend persistence for explicit U.S. custom runs without storing or returning automatic vendor prices | LF-A5, LF-U6 | P1 | Migration/service/user-scope/save-only-when-requested tests | ◐ IMPLEMENTED / LIVE DB UNVERIFIED — B23 |
| LF3.3 | Implement retail availability, Base Case, Bear/Base/Bull, confidence/reasons, edit/reset, comparison, and user-vs-baseline UI | LF-U1–LF-U5 | P0 | Frontend build plus authenticated browser-to-API flow | ✔ VERIFIED — operating/conditional/hard/bank/REIT browser flows |

Gate: **passed with one explicit environment limitation.** The real staged UI/API agree, default
calculator reproduces the artifact, directions are correct, and raw vendor/peer prices never cross
the boundary. Live Postgres persistence is parked in B23. Evidence: Audit 43.

### Phase LF4 — staged evidence and confirmation stop

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| LF4.1 | Run focused/full suites and real cached Batches 01–03 replay | LF-R1–LF-U7 | P0 | Counts, arithmetic, deterministic hashes, safety scan | ✔ VERIFIED — 1,232 full; deterministic 30-company replay |
| LF4.2 | Exercise staged FastAPI list/detail/calculator and browser flows across operating, bank, REIT, conditional, relative-only-if-data-present, and hard-failure cases | LF-A2, LF-U7 | P0 | Real HTTP responses and browser evidence | ✔ VERIFIED — relative-only remains data-blocked B21 |
| LF4.3 | Present before/after coverage, verified/partial/blocked/deferred claims, and stop for user confirmation | all | P0 | Evidence ledger and protected serving hashes | ✔ VERIFIED — USER CONFIRMED 2026-08-25 |

Gate: **passed — user confirmed 2026-08-25.** LF1–LF4 are approved as staged behavior. Batch 04,
serving promotion, merge, push, and deployment remain separate actions requiring explicit user
authorization. Evidence: Audit 44 and the `launch-first-confirmation-scope` learning.

### Phase B04 — NOW: launch-first controlled batch

The user explicitly authorized Batch 04 on 2026-08-25. Serving promotion, merge, push, and
deployment remain unauthorized.

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B04.1 | Freeze and validate the exact ten-company contract and close Batch 03 watchlist bookkeeping | P0 | Manifest hash, exact identities, 14-entry watchlist contract | ✔ VERIFIED |
| B04.2 | Capture/reuse ten cutoff-safe SEC packets and controlling structural filings | P0 | Identity/date/payload/package hashes and protected roots | ✔ VERIFIED — 10/10 packets; 10/10 parses |
| B04.3 | Apply the shared launch-first fallback ladder and v1.2 baseline contract | P0 | Exact denominator; coherent range or genuine hard failure | ✔ VERIFIED — 10/10 Conditional Low |
| B04.4 | Independently challenge source, model, arithmetic, assumptions, and availability labels | P0 | Luna-High review; resolve all Critical/Important | ✔ LUNA HIGH PASS — all findings resolved |
| B04.5 | Regenerate twice, run full backend/frontend checks, and exercise real API/calculator | P0 | Byte equality, tests/build, 10 list/detail/calculator parity | ✔ VERIFIED — `55523501…`; 1,239 backend; frontend/API pass |
| B04.6 | Report Batch 04 and stop before Batch 05 or rollout actions | P0 | Exact 10-row result; no serving/promotion/merge/push/deploy | ✔ USER CONFIRMED — watchlist recorded |

Gate: **passed — user confirmed by authorizing Batch 05.** Batch 04 is 10/10 Conditional Low.
Serving mutation, promotion, merge, push, and deployment remain outside scope.

### Phase B05 — launch-first controlled batch

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B05.1 | Freeze and validate the exact ten-company contract | P0 | Manifest hash and exact identities | ✔ VERIFIED |
| B05.2 | Capture/reuse ten cutoff-safe SEC packets and structural filings | P0 | Identity/date/package hashes and protected roots | ✔ VERIFIED — 10/10 |
| B05.3 | Produce honest conditional baselines, including homebuilder equity-earnings routes | P0 | Ordered finite ranges, source lineage, model identity | ✔ VERIFIED — 10/10 Conditional Low |
| B05.4 | Independently challenge source, model, arithmetic, calculator semantics, and reliability | P0 | Luna-XHigh; resolve all Critical/Important | ✔ PASS |
| B05.5 | Regenerate twice and verify backend, frontend, and real API/calculator | P0 | Byte equality, full suites, 10/10 HTTP parity | ✔ VERIFIED — `4a27f86b…`; 1,247 backend; frontend/API pass |
| B05.6 | Report, confirm, and bookmark conditional issuers | P0 | Exact result and 34-entry watchlist | ✔ USER CONFIRMED 2026-08-25 |

Gate: **passed — user confirmed 2026-08-25.** Batch 05 is 10/10 Conditional Low; all ten are
bookmarked for the post-Batch-50 learning review. Batch 06 and all rollout actions require a new
user signal.

### Phase B06 — NOW: launch-first controlled batch

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B06.1 | Freeze and validate the exact ten-company contract | P0 | Manifest hash and exact identities | ✔ VERIFIED |
| B06.2 | Capture/reuse ten cutoff-safe SEC packets and structural filings | P0 | Identity/date/package hashes and protected roots | ✔ VERIFIED — 10/10 |
| B06.3 | Produce honest conditional baselines with period and lease safeguards | P0 | Ordered finite ranges, source lineage, model identity | ✔ VERIFIED — 10/10 Conditional Low |
| B06.4 | Independently challenge source, model, arithmetic, debt scope, and calculator semantics | P0 | Luna-XHigh; resolve all Critical/Important | ✔ PASS |
| B06.5 | Regenerate twice and verify backend, frontend, and real API/calculator | P0 | Byte equality, full suites, 10/10 HTTP parity | ✔ VERIFIED — `fd618685…`; 1,255 backend; frontend/API pass |
| B06.6 | Report, confirm, and bookmark conditional issuers | P0 | Exact result and 44-entry watchlist | ✔ USER CONFIRMED 2026-08-26 |

Gate: **passed — user confirmed 2026-08-26.** Batch 06 is 10/10 Conditional Low; all ten are
bookmarked for the post-Batch-50 learning review. Batch 07 and all rollout actions require a new
user signal.

### Standing outcome-reporting contract for Batch 07 onward

Every controlled batch must attempt the source-bounded normal route first and report three exact,
mutually exclusive counts: **Pass / Conditional / Withheld**. Conditional is reserved for a named,
material provisional dependency; it is not the default launch-first result. The three counts must
sum to ten, and cumulative reporting must show the same categories across all processed issuers.

### Phase B07 — history-backed controlled batch

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B07.1 | Freeze and validate the exact ten-company contract | P0 | Manifest hash and exact identities | ✔ VERIFIED |
| B07.2 | Capture/reuse ten cutoff-safe SEC packets and structural filings | P0 | Identity/date/package hashes and protected roots | ✔ VERIFIED — 10/10 |
| B07.3 | Apply three-to-five-year company history and produce exact Pass/Conditional/Withheld outcomes | P0 | Source-linked history, ordered ranges, completed bridges | ✔ VERIFIED — Pass 4 / Conditional 6 / Withheld 0 |
| B07.4 | Challenge customer funds, debt/NCI, casino commitments, regulatory credits, and provenance | P0 | Independent XHigh review; resolve all Critical/Important | ✔ PASS |
| B07.5 | Regenerate twice and verify backend, frontend, and real API/calculator | P0 | Byte equality, full suites, 10/10 HTTP parity | ✔ VERIFIED — 1,285 backend; frontend/API pass |
| B07.6 | Present Batch 07, confirm, and bookmark Conditional issuers | P0 | Exact report and confirmation gate | ✔ USER CONFIRMED 2026-08-26 |

Gate: **passed — user confirmed 2026-08-26.** The result is Pass 4 / Conditional 6 / Withheld 0.
The six Conditional issuers are bookmarked. Serving artifacts remain unchanged. Batch 08,
promotion, merge, push, and deployment require separate authorization.

### Phase B08 — history-backed controlled batch

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B08.1 | Freeze and validate the exact ten-company contract | P0 | Manifest hash and exact identities | ✔ VERIFIED |
| B08.2 | Capture/reuse ten cutoff-safe SEC packets and structural filings | P0 | Identity/date/package hashes and protected roots | ✔ VERIFIED — 10/10 |
| B08.3 | Apply history and specialist fallbacks with exact Pass/Conditional/Withheld outcomes | P0 | Source-linked history, ordered ranges, fail-closed object identity | ✔ VERIFIED — Pass 2 / Conditional 6 / Withheld 2 |
| B08.4 | Challenge acquisitions, captive finance, customer funds, commitments, software capex, and share/claim scope | P0 | Luna XHigh; resolve all Critical/Important | ✔ PASS |
| B08.5 | Regenerate twice and verify backend, frontend, and real API/calculator | P0 | Byte equality, full suites, 10/10 HTTP parity | ✔ VERIFIED — 1,292 backend; frontend/API pass |
| B08.6 | Present Batch 08, confirm, and bookmark Conditional issuers | P0 | Exact report and confirmation gate | ✔ USER CONFIRMED 2026-08-26 |

Gate: **passed — user confirmed 2026-08-26.** The six Conditional issuers are bookmarked. NCLH
and APTV remain outside the post-recovery register/watchlist until their one recovery attempt.
Serving artifacts remain unchanged. Recovery, Batch 09, promotion, merge, push, and deployment
require separate authorization.

### Phase B08-R — one-attempt withheld recovery

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B08-R.1 | Audit APTV post-spin and NCLH cruise funding alternatives | P0 | Exact continuing earnings, debt, commitments, shares, and source lineage | ✔ VERIFIED |
| B08-R.2 | Recover APTV without pre-spin history and challenge NCLH funding | P0 | Conditional equity earnings / explicit hard stop | ✔ VERIFIED — APTV recovered; NCLH withheld |
| B08-R.3 | Recalculate, deterministic replay, full suite, and real API | P0 | Luna XHigh; byte equality; 10/10 API parity | ✔ PASS |
| B08-R.4 | Record final watchlist and cumulative withheld register | P0 | Exact counts/hashes and one-attempt invariant | ✔ VERIFIED |

Gate: **passed.** Final Batch 08 is Pass 2 / Conditional 7 / Withheld 1. APTV and NCLH are
bookmarked; NCLH is in the cumulative withheld register. Batch 09 and all rollout actions require
a separate user signal.

### Phase B09 — history-backed controlled batch

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B09.1 | Freeze and validate the exact ten-company contract | P0 | Manifest hash, class identity, exact denominator | ✔ VERIFIED |
| B09.2 | Capture/reuse ten cutoff-safe SEC packets and structural filings | P0 | Identity/date/package hashes and protected roots | ✔ VERIFIED — 10/10 |
| B09.3 | Apply history and explicit current bridge fallbacks | P0 | 3–5 years, KO structural TTM, ordered outcomes | ✔ VERIFIED — Pass 2 / Conditional 7 / Withheld 1 |
| B09.4 | Challenge class shares, securities, debt/lease scope, negative history, and current bridge completeness | P0 | Luna XHigh; resolve all Critical/Important | ✔ PASS |
| B09.5 | Regenerate twice and verify backend, frontend, and real API/calculator | P0 | Byte equality, full suites, 10/10 HTTP parity | ✔ VERIFIED — 1,302 backend; frontend/API pass |
| B09.6 | Present Batch 09, confirm, and bookmark Conditional issuers | P0 | Exact report and confirmation gate | ✔ USER CONFIRMED 2026-08-26 |

Gate: **passed — user confirmed 2026-08-26.** The seven Conditional issuers are bookmarked. CLX
received its one authorized recovery attempt in Phase B09-R below. Serving artifacts remain
unchanged. Batch 10, promotion, merge, push, and deployment require separate authorization.

### Phase B09-R — one-attempt CLX recovery

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B09-R.1 | Recover the linked CLX financial-statements IXBRL document | P0 | Official ZIP/member hashes; 1,675 parsed facts | ✔ VERIFIED |
| B09-R.2 | Build and independently challenge a conservative post-acquisition range | P0 | Commercial paper/debt/lease bridge; event cash treatment | ✔ PASS — Conditional Low |
| B09-R.3 | Replay twice, run full backend suite, and exercise real API | P0 | Byte equality; 1,305 tests; 10/10 HTTP parity | ✔ VERIFIED |
| B09-R.4 | Add CLX to the Recovery Learning Watchlist | P0 | Exact watchlist/register counts | ✔ VERIFIED |

Gate: **passed — user confirmed 2026-08-26.** Final Batch 09 is Pass 2 / Conditional 8 / Withheld 0.
CLX is bookmarked as Conditional, not added to the cumulative withheld register. Batch 10 remains
outside scope.

### Phase B10 — history-backed Consumer Staples batch

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B10.1 | Freeze and validate the exact ten-company contract | P0 | Manifest identity/hash and exact denominator | ✔ VERIFIED |
| B10.2 | Capture/reuse ten cutoff-safe SEC packets and structural filings | P0 | Identity/date/package hashes and protected roots | ✔ VERIFIED — 10/10 |
| B10.3 | Build history-backed Pass/Conditional/Withheld baselines | P0 | Exact bridges, 3–5 years, ordered values | ✔ VERIFIED — Pass 6 / Conditional 3 / Withheld 1 |
| B10.4 | Challenge transactions, class shares, debt/lease scope, NCI, and supplier finance | P0 | Luna XHigh; resolve all Critical/Important | ✔ PASS |
| B10.5 | Replay twice and verify backend, frontend, and real API/calculator | P0 | Byte equality, full suites, 10/10 HTTP parity | ✔ VERIFIED |
| B10.6 | Present Batch 10 and stop for confirmation | P0 | Exact report and confirmation gate | ✔ USER CONFIRMED 2026-08-26 |

Gate: **passed — user confirmed 2026-08-26.** Batch 10 is Pass 6 / Conditional 3 / Withheld 1.
The three Conditional issuers are bookmarked. KMB requires its separately authorized recovery
attempt. Serving artifacts remain unchanged. Recovery, Batch 11, promotion, merge, push, and
deployment require separate authorization.

### Phase B10-R — one-attempt KMB recovery

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B10-R.1 | Reconcile the completed IFP sale and pending Kenvue state | P0 | Current filing/event facts and non-overlapping bridge | ✔ VERIFIED |
| B10-R.2 | Build and challenge a post-IFP/pre-Kenvue current-state baseline | P0 | Continuing EBIT/D&A/capex proxy; Luna XHigh | ✔ PASS — Conditional Low |
| B10-R.3 | Replay twice, run full backend suite, and exercise real API | P0 | Byte equality; 1,313 tests; 10/10 HTTP parity | ✔ VERIFIED |
| B10-R.4 | Add KMB to the Recovery Learning Watchlist | P0 | Exact watchlist/register counts | ✔ VERIFIED |

Gate: **passed — user confirmed 2026-08-26.** Final Batch 10 is Pass 6 / Conditional 4 /
Withheld 0. KMB is bookmarked as Conditional and is not added to the cumulative withheld register.
Batch 11 remains outside scope.

### Phase B04-PR — verified Pass repairs

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B04-PR.1 | Repair TJX revenue and ROST interest provenance | P0 | Exact FY + current YTD − prior YTD replay | ✔ VERIFIED |
| B04-PR.2 | Close MCD/HD preferred/NCI bridge treatment | P0 | Controlling filing structure and zero reserve | ✔ VERIFIED |
| B04-PR.3 | Reclassify, challenge, replay, and exercise real API | P0 | Pass 4 / Conditional 6 / Withheld 0; deterministic/API proof | ✔ PASS |

Gate: **passed under the user's explicit repair approval.** MCD, TJX, HD, and ROST are source-bounded
Pass results and were removed from the Recovery Learning Watchlist. Batch 05 reclassification and
Batch 07 remain outside scope.

### Phase B05-HR — history-backed Pass repairs

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B05-HR.1 | Confirm core historical-data layer and wire Batch 05 | P0 | Source-linked private profiles and safe public metadata | ✔ VERIFIED |
| B05-HR.2 | Reclassify WSM/CASY/AZO/ORLY using five-year history | P0 | Pass 4 / Conditional 6 / Withheld 0 | ✔ VERIFIED |
| B05-HR.3 | Challenge, deterministic replay, full suites, and real API | P0 | Independent challenge; byte equality; 10/10 API parity | ✔ PASS |

Gate: **passed under the user's Batch 05 repair authorization.** Four source-bounded Pass results
were removed from the Recovery Learning Watchlist. Batch 06 reclassification and Batch 07 remain
outside scope.

### Phase B06-HR — history-backed Pass repairs

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| B06-HR.1 | Wire unique-period company history into Batch 06 | P0 | Private profiles, safe public metadata, BBY/CMG special paths | ✔ VERIFIED |
| B06-HR.2 | Reclassify seven ordinary history-backed issuers | P0 | Pass 7 / Conditional 3 / Withheld 0 | ✔ VERIFIED |
| B06-HR.3 | Challenge, deterministic replay, full suites, and real API | P0 | Independent challenge; byte equality; 10/10 API parity | ✔ PASS |

Gate: **passed under the user's Batch 06 repair authorization.** Seven source-bounded Pass results
were removed from the Recovery Learning Watchlist. Batch 07 remains outside scope until the user's
explicit start signal.

### Phase H01 — company-history valuation layer

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| H01.1 | Add shared three-to-five-year source-linked history profiles for operating, bank, utility, and REIT lanes | P0 | Focused/full tests and private lineage inspection | ✔ VERIFIED |
| H01.2 | Expose only safe history metadata and keep raw observations private | P0 | Sanitizer tests, leakage scan, real staged API | ✔ VERIFIED |
| H01.3 | Shadow only Batch 04 under the user's narrowed scope | P0 | Two byte-identical runs; exact Pass/Conditional/Withheld counts | ✔ VERIFIED |
| H01.4 | Independently challenge the final source/model candidate | P0 | Luna source and economic review | ⚠ REVIEWERS UNAVAILABLE — no findings returned |
| H01.5 | Exercise the visual browser flow | P1 | Real U.S. list/detail assumption display | ⚠ BROWSER CONTROL UNAVAILABLE |
| H01.6 | Promote the exact user-confirmed Batch 04 candidate with rollback evidence | P0 | Byte parity, full suite/build, real default-serving API | ✔ USER-CONFIRMED AND VERIFIED |

Shadow gate history: the Batch 04 shadow was **verified with stated review limitations** at
4 Pass / 6 Conditional / 0 Withheld; all 10 remained Low under unchanged scenario-width rules.
At that checkpoint Batches 05/06 were not replayed and no serving promotion had occurred.

Promotion update: **the user explicitly confirmed and promoted the exact Batch 04 history-backed
candidate on 2026-08-26.** The default backend serving directory now contains all ten artifacts;
real list/detail/calculator API verification passed. Browser review, merge, push, deployment,
Batches 05/06, and Batch 07 remain separate gates.

### Phase C10 — versioned catalog cutover through Batch 10

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| C10.1 | Preserve the exact pre-promotion 206-company catalog as an immutable tracked archive | P0 | Commit/tree identity, 206 byte comparisons, manifest hash, isolated rollback | ✔ VERIFIED |
| C10.2 | Assemble the exact final Batch 01–10 public artifacts into one versioned catalog | P0 | Two builds, 100 source comparisons, unique ticker/CIK and 45/51/4 counts | ✔ VERIFIED |
| C10.3 | Serve only the active manifest and support one-batch-at-a-time immutable successors | P0 | Hash-drift/extra-file tests, metadata API, atomic activation | ✔ VERIFIED |
| C10.4 | Present numeric Pass/Conditional results identically and unavailable results as a dash | P0 | Production build plus real PG/KMB/NEE browser flow | ✔ VERIFIED |
| C10.5 | Exercise all public boundaries and preserve rollback | P0 | 1,321 backend tests; 100/100 HTTP detail/calculator; browser console clean | ✔ VERIFIED |

Gate: **passed — user confirmed 2026-08-27.** The active local catalog contains exactly
100 Batch 01–10 companies: 45 available, 51 internally conditional but presented normally, and
four unavailable. The old 206 are archived and the former mixed loose directory is retired.
Evidence: Audit 63. Merge, push, deployment, and Batch 11 remain outside scope.

### Phase C11 — valuation UX and calculator correction

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| C11.1 | Remove user-facing Confidence and empty Relative cross-check surfaces while preserving audit data | P0 | 100-artifact reconciliation, production build, browser absence checks | ✔ VERIFIED |
| C11.2 | Display rate assumptions as two-decimal percentages without changing model precision | P0 | JPM field-value inspection and calculator API trace | ✔ VERIFIED |
| C11.3 | Make edited assumptions update headline/model values and clarify market price/save behavior | P0 | JPM $190.14→$308.62, manual comparison, save, and reset browser flow | ✔ VERIFIED |
| C11.4 | Consolidate valuation navigation and preserve old route compatibility | P0 | One nav item; `/valuation` and `/us-valuations` redirects | ✔ VERIFIED |

Gate: **verified locally — user confirmation needed.** Evidence: Audit 64. Reliability remains in
the artifact/API for governance but is no longer a headline UI verdict. Merge, push, and deployment
remain outside scope.

## Final 500-company gate

Confirm exactly 500 unique processed issuers and no denominator loss; replay all frozen inputs
twice; run the complete backend/API/browser acceptance path and point-in-time backtest; assess
reliability-label discrimination; reconcile all serving hashes; separately report processing
completion and publishable numeric completion; obtain explicit user confirmation before any
merge or production release.
