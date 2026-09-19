# FinSight whole-universe production backlog

Only work that does not belong on the approved 500/500 critical path is parked here. Full-universe coverage, specialist model lanes, price comparison, and backtesting are scheduled roadmap work, not deferred aspirations.

## Deferred until the critical path is verified

- **B1 · General documentation cleanup.** Large folder reorganization does not change valuation behavior. Revisit after the reliability pipeline and canonical universe are stable.
- **B2 · Retiring old generated frontend modules.** The active U.S. valuation page reads the API. Remove unused generated modules only after the API/UI contract is finalized and imports are rechecked.
- **B3 · Production deployment.** Feature-branch implementation and local/staging verification do not authorize merging or deploying. Unblocks after all roadmap gates, branch review, and explicit user approval.
- **B4 · Paid institutional market-data integration.** The first governed current-price comparison should use an approved public source. Paid data remains unnecessary unless public-source quality fails the release gate.

## Log-new-tangent rule

If a defect is discovered while executing a phase and it does not block that phase's consumer-visible behavior, record it here with the exact evidence, why it is deferred, and what would move it back to the roadmap. Do not interrupt the current phase for unrelated cleanup.

## Deferred — quality caveats to revisit (not blockers, but carry review flags)

- **B5 · Conservative fallbacks undervalue growth names.** Residual-income / DDM fallbacks (HD $155, MCD $121, WMT $42)
  are systematically conservative for low-payout / high-growth companies. Fine as `review_required` floors; revisit if
  they're surfaced as headline values.
- **B6 · Candidate archetype cohort contamination.** `specialty_chemicals` mixes industrial chem + household/personal
  care; `internet_digital_services` is META/GOOGL-heavy (n=5); `transportation` mixes rail/airline; `retail` mixes
  discount/franchise. Split + recalibrate before promoting to `pass`.
- **B7 · `sales_to_capital` and dividend-growth are governed policy, not per-issuer.** Documented; refine with
  per-issuer evidence before final publish.
- **B8 · Preserve contradiction-trigger evidence in structural rejection reports.** HPE is safely rejected when its
  displayed preferred-stock zero conflicts with same-filing preferred-instrument evidence, but the corrected report
  row currently has `evidence: null`. Retain the triggering companion fact, context, period, and accession directly in
  future rejection artifacts before relying on those artifacts for analyst-facing audit trails.
- **B9 · Reject clearly liability-like preferred-equity review noise.** The corrected DE candidate remains safely
  review-grade and withheld, but its documentation and `LiabilitiesAbstract` parent identify a liability rather than
  genuine preferred-equity ambiguity. Add a deterministic economic-class rejection after broader regression coverage.

- **B10 · Historical BP4 bounded-review baseline (superseded by Phase 1).**
  *Why retained:* the pre-Phase-1 replay had 104 legacy private artifacts, zero bounded candidates, and five requested
  current private artifacts absent. This is historical evidence of the fail-closed baseline, not a current publication
  rule or reliability threshold.
  *Revisit when:* the Phase 1 policy is replayed on current source-linked artifacts; do not treat the old 1% spread
  criterion as a live acceptance rule.

- **B11 · Recover stale bridge-shadow writer locks automatically.**
  *Why deferred:* an abrupt process termination can leave `.bridge-policy-shadow.lock`; this fails safely and requires
  an operator to verify no writer is active before removing the lock. It does not risk serving writes or overwrite
  immutable output.
  *Reconsider when:* the replay CLI becomes scheduled or routinely concurrent and needs PID-aware stale-lock recovery.

- **B12 · Retire or rewrite the older Batch 01 all-or-nothing implementation plan.**
  *Why deferred:* `docs/superpowers/plans/2026-08-14-batch-01-ten-company-valuation.md`
  remains useful implementation research, but its branch assumptions and requirement that all
  ten pass before any promotion conflict with the user-approved controlled reset. The active
  roadmap and controlled-reset rules govern; the old file must not silently drive promotion.
  *Reconsider when:* Batch 01 is reported and the historical plan can be annotated or archived
  without losing useful design evidence.

- **B13 · Canonical 500-universe proof.**
  **Resolved 2026-08-24 by explicit user authorization.** Exhaustive local/Git review found no
  original historical 500-row artifact, so the workflow stopped before selection. The user then
  authorized a replacement S&P 500 issuer universe effective 2026-08-14. A pinned public table,
  official S&P cutoff-change evidence, and captured SEC mapping reconcile 503 securities to 500
  CIKs; the canonical manifest and all Batches 02–50 are frozen and independently challenged.

- **B14 · Batch 01 SEC acquisition lacks a monitored contact.**
  **Resolved 2026-08-20.** The user supplied a monitored contact, the capture completed 10/10,
  and a cached rerun reproduced the same immutable packets without serving changes. Retained as
  history because future fresh acquisition still requires an explicit monitored contact; never
  invent one or bypass this provenance gate.

- **B15 · Representative browser UAT for controlled Batch 01.**
  *Why deferred:* the worktree has no installed frontend runtime (`vite: command not found`) and
  the U.S. valuation route is authentication-protected. No UI code changed in this phase, and a
  faked login would not be real consumer evidence. The real staged FastAPI path is verified.
  *Reconsider when:* frontend dependencies and a local authenticated test user/database are
  available; then exercise the 10-item selector and withheld detail state in the browser.

- **B16 · NEE specialist FPL/NEER sum-of-parts.**
  *Why deferred:* direct Q2 extraction fixed the period defect, but the approved consolidated
  FCFE fallback produces nonpositive bear/base common cash flow once commercial paper and parent/
  NCI allocation are complete. A dividend-only value would conceal the mixed-business problem.
  *Reconsider when:* source-linked FPL regulated equity/rate-base economics, Energy Resources
  project cash flow, parent claims, and segment financing can be reconciled into a provisional
  specialist SOTP and independently challenged.

- **B17 · Batch 02 real localhost HTTP acceptance.**
  **Resolved 2026-08-24 after explicit user approval.** Uvicorn served the exact staged ten on
  `127.0.0.1:8765`; list count was 10, all 10 details returned HTTP 200 with exact range/state/
  reliability parity, no private fields leaked, zero Arelle modules loaded in the serving import,
  and the process shut down cleanly.

- **B18 · Reconstruct the exact difficult-corpus official-package denominator.**
  **Denominator resolved by FOD5.** The retained period-aware report proves exactly 106 candidates. Combined with Batch 01/02 and the withheld subset, the de-duplicated manifest has 121 unique issuers and 133 cohort memberships.

- **B19 · Capture unified official-evidence packets for the remaining difficult 101.**
  **Resolved after the user supplied a monitored SEC contact.** All 106 source packets and 205 unique controller/annual packages were frozen, the initial 11 XBRL-ZIP package failures were repaired safely, and the complete evidence/consumer/API replay passed twice without serving changes.

- **B20 · Obtain promotable specialist source payloads.**
  *Why blocked:* FR Y-9C bulk access returned HTTP 403, FERC CID/payload/allocation is unresolved, and the SEC-filed Realty Income supplement is link-verified but not frozen locally with a complete AFFO reconciliation.
  *Unblocks when:* immutable official payloads, parent identity/allocation, cutoff, units, and reconciliations pass the specialist contracts.

- **B21 · Supply approved private U.S. EOD and peer records.**
  *Why blocked:* the worktree contains no private vendor EOD dataset, peer cohort, or provider
  client/credentials. The launch-first implementation can validate and consume provider-neutral
  private records, but it must not fabricate prices or silently substitute an unapproved source.
  *Unblocks when:* approved records include canonical security/listing, USD currency,
  split-adjusted close, price date, provider, and payload hash under the private contract.

- **B22 · Batch 04 promotion resolved; merge, push, and deployment remain separate.**
  *Current state:* the user explicitly confirmed and promoted the exact Batch 04 history-backed
  candidate on 2026-08-26. Ten default backend serving artifacts and the real API are verified.
  *Why still blocked:* promotion did not authorize merge, push, staging deployment, production
  deployment, Batch 05/06 retry, or Batch 07 processing. Main pushes auto-deploy staging.
  *Unblocks when:* the user separately authorizes the specific outward-facing or next-batch action.

- **B23 · Real Postgres U.S. saved-run migration and persistence acceptance.**
  *Why blocked:* this machine has no Docker command or reachable local Postgres. Nullable U.S.
  columns, migration SQL, `save_us`, API scoping, safe payload tests, and the browser save response
  pass, but no real row was inserted/read back.
  *Unblocks when:* a staging/local database is available; run migrations, save a custom U.S. result,
  read it through `/api/valuations`, verify user scoping and fields, then delete the test row.

- **B24 · Normalize `filed_date` into inherited structural flow rows.**
  *Why deferred:* Batch 12 recovery retains the controlling accession and receipt-level filed date,
  so `filed: null` on selected structural rows is a display/provenance-shape issue rather than a
  valuation or cutoff failure. Changing the shared Batch 07 helper would alter many historical
  private traces during a value-recovery phase.
  *Unblocks when:* a cross-batch provenance-schema migration can regenerate and compare every
  affected private artifact without changing public values.

- **B25 · Make calculator controls display each artifact's actual base assumptions.**
  *Why deferred:* cumulative default POSTs reproduce every published range, but the shared
  calculator view still displays generic cash-conversion, growth, discount-rate, and terminal-growth
  defaults. Correcting this safely changes the public contract across all confirmed historical
  catalogs, not only Batch 27.
  *Unblocks when:* a dedicated cross-batch migration can map each operating/equity model's exact
  base assumptions into calculator controls, rebuild every catalog, and reverify saved-run and API
  compatibility without changing confirmed values.

- **WG22-R1 · Complete the ordinary-NCI group's independent financial challenge.**
  *Resolved 2026-09-15:* after initial capacity failures, Luna High completed
  the bounded challenge with no material defect. Primary rechecked actual
  sources, reproduced the same frozen report and passed 48 focused checks.
  Evidence: `docs/audit/wg22-independent-review.md`. User confirmation remains
  separate; this did not authorize production or the next group.

- **WG22-R2 · Fail closed on future share-only preferred/temporary issuance.**
  *Why deferred:* ETN's current complete package has no preferred/temporary
  facts in any unit, so the current common-only proof is valid. The USD-focused
  common-equity guard does not explicitly require a share-only instrument screen.
  *Unblocks when:* before final release, add and test a reusable guard against
  new preferred/temporary share disclosures without inferred carrying amounts.
  This is future-structure hardening, not a current ETN valuation defect.

- **WG23-JBL · Full current finance-lease carrying scope and overlap.**
  *Why blocked:* the current $51M disclosure is future payments for new leases
  only, with broad buckets and separate guarantee/uncommenced exclusions. It
  cannot substitute for a full current carrying amount or exact PV schedule.
  *Unblocks when:* current carrying scope, payment timing and debt/cash-flow
  overlap are source-bound. Preserve historical deduction; no missing-tag zero.
- **WG23-INTC · Explicit governed foundry cash-margin normalization.**
  *Narrow migration verified in WG24; user confirmation pending:* retained 3%/7%/12%
  assumptions are separate from reported cash/history and reproduce the old
  range exactly. Five source-backed annual periods/four negative observations
  remain. Full issuer refresh is still blocked, never made unavailable.
- **WG24-INTC · Reinvestment and economic-validity scope.**
  *Why blocked:* current PP&E payments in financing activities, finance-lease
  principal and extended-term PP&E purchases are separate from investing
  capex. Cash-equivalent/AFS overlap, restricted equity investments, escrowed-
  share derivatives/warrants, incentive/working-capital cash and transformation/
  Altera deconsolidation also need source-backed validity decisions.
  *Unblocks when:* reconcile cash, total reinvestment, financing debt, claims,
  dilution and operating scope without inferred zeros or duplicate deductions;
  satisfy the versioned explicit economic-review gate. Do not adjust margins
  automatically or promote a margin-only replay to a numeric successor.
- **WG23-LHX/MCK · Separate excluded current claim stacks.**
  *Why separate:* LHX preferred redemption/conversion/warrants/environmental
  economics and MCK ordinary/redeemable/opioid post-payment economics are not
  the ordinary-NCI-only rule. LHX also reports $130M conversion-feature and
  $186M warrant liabilities, not approved as additional deductions here.
  *Unblocks when:* their complete source-backed claim/overlap/lifecycle rules
  are addressed in bounded groups. Exclusion does not remove required companies.

- **WG24-H1 · Guard future direct governed-validity callers.**
  *Why deferred:* the current production caller enforces complete/finite cash
  history and supplies the current source interval. The low-level helper still
  permits omitted interval data. Mandatory economic review remains fail-closed.
  *Before reuse by another caller:* require the same upstream validated input
  contract or make those arguments mandatory; do not treat the helper alone as
  a complete refresh approval. Independent review found no current result defect.

- **WG25-S1 · INTC/JBL complete current finance-lease carrying and debt overlap.**
  *Why blocked:* controlling cached quarters do not bind full carrying balances,
  liability rollforwards or lease inclusion in debt. INTC noncash capital total/
  inclusion is not a proved ending financing liability; JBL new-only payments
  and combined exclusions are not current carrying debt or a principal split.
  *Unblocks when:* capture/source-bind the missing current scope or an evidenced
  complete rollforward. Do not invent closing balances/timing, drop old claims,
  deduct cash/principal twice or convert missing evidence to zero/unavailable.
- **WG25-O1 · Verify arbitrary external output-root snapshot portability.**
  *Observed:* a temporary external diagnostic output-root run failed with its
  snapshot source-index file missing. Canonical project-root frozen workers pass
  the exact economic-check regression; no integrity checks were removed.
  *Unblocks when:* independently reproduce and repair the output-root/materialized
  snapshot boundary, then run real external-root workers/replay. Portable output
  roots are not yet verified; this remains operational release work.

- **WG26-S1 · Complete LHX/MCK economic claim stacks.**
  *Why required:* carrying/alias source proofs do not establish instrument fair
  value, conversion basis, derivative parent scope, environmental forward-cash/
  recovery overlap or MCK legal/acquisition/post-payment attribution. All old
  deductions/cash history are preserved; no numeric successor approved.
  *Unblocks when:* reusable separately source-supported economic rules and
  exact current full-stack replay/calculator verification are complete.
- **WG26-H1 · Screen unexpected future temporary-parent equity.**
  *Observed in independent in-memory challenge:* a new positive MCK temporary-
  parent carrying fact without NCI markers is outside the known narrow mapping
  and currently ignored. Actual current MCK has no such fact; main model gap
  prevents numeric use. Before reusing the mapping as a full executable claim
  rule, reject/source-classify unexpected temporary-equity balances rather than
  treating a known-component partial proof as complete coverage. Required future
  hardening, not waived current publication acceptance.

- **WG27-S1 · Source-supported LHX preferred economic value.**
  *Verified 2026-09-16:* accounting allocation/host/derivatives/program/proceeds
  reconcile, but QIPO capitalization/price, segment value/milestone outcome and
  parent economic basis are missing. Accounting total $1.284B is not an intrinsic
  claim; full cash settlement cannot add bifurcated host/features or dilution.
  *Unblocks when:* an explicit supported economic recipe bounds the contract's
  exclusive outcomes and source scope, alongside environmental forward-cash
  treatment. No book-value-as-intrinsic, invented IPO values or paid-cash double count.
- **WG27-H1 · Retain indexed structural-byte contract for new callers.**
  *Current workflow verified:* input source index rehashes structural/package
  bytes before source ledger, narrative re-extraction checks original bytes.
  Standalone dictionaries are not independently hash-authenticated by the pure
  helper. Before adding a direct caller, require the same validated/frozen source
  contract; do not reuse a ledger as proof of arbitrary input provenance.
- **WG28-S1 · Annual environmental cash/recovery evidence and forward overlap.**
  *Updated by WG29 2026-09-16:* current related liability/recovery balances and
  two authorized complete annual packages now captured and parsed. Missing payment
  tags and stock changes do not prove zero cash. Contract-pricing recoveries
  are not surplus cash; $175M book difference is not a PV claim.
  *Unblocks when:* source-supported same-program cash, recovery/timing and
  forecast OCF/revenue overlap are quantified and independently reviewed.
  Captured annuals `0000202058-26-000015` and `0000202058-25-000023` add balances/
  conditional-discounting/capitalization policy, but not the required cash schedule.
  Capture alone does not close the economic gap. Preserve existing deduction
  and preferred basis until an approved supported economic treatment replaces it.
- **WG30-S1 · MCK complete post-period cash/claim and ownership economics.**
  *Verified 2026-09-16:* same-program July payment and conditional paired cash/
  liability arithmetic source-bound, not actual closing balances. Other cash/debt/
  legal movements and restricted escrow must reconcile; $243M equity/debt
  securities are not newly approved cash-like assets. Ordinary/redeemable NCI
  carrying/alias proof does not bound Apollo conversion or PRISM/Core put rights.
  Remaining settlement payments/forecast cash overlap and nonsettling exposure
  remain required. *Unblocks when:* a source-supported full economic bridge and
  approved instrument/cash assumptions preserve all prior burdens without
  invented timing, duplication, adding proceeds twice or declining claim alone.
- **WG31-S1 · MCK executed instrument terms and current component economics.**
  *Verified 2026-09-16:* current aggregate RNI rollforward and approximate Apollo
  preferred event/net financing separation supported; current package/index has
  only the controlling Q. Apollo subscription/purchase and governing MSS LLC
  agreement, conversion/redemption formula/coupon/seniority, PRISM put terms,
  Core exact exercise windows/pricing and current per-instrument carrying schedule
  are not captured. WG32 adds repeated Core75% initial-value floor and525M
  arithmetic lower bound, but no first date/formula/current component. Issuer Monte Carlo
  description is not reproducible without inputs, nor independent intrinsic value.
  *Unblocks when:* actual eligible executed terms and component evidence or an
  individually reviewed, source-supported economic treatment bounds outcomes.
  Public availability is not established; no network acquisition authorized in
  WG31. Do not substitute June12 term-loan filing for preferred/put contracts,
  invent subsidiary value, use13% as parent dilution or add proceeds twice.
- **WG31-P1 · Measure broad regression preparation cost before optimizing.**
  Final739-check suite817.40s; earlier718-check suite244.71s is not same frozen
  code/input/test set, so no attribution or speedup claim. Benchmark identical
  frozen inputs with per-phase timing before changing cache/recheck policy;
  preserve integrity, source hashing, test coverage and two-worker limits.
  Deferred as separate efficiency work, not a reason to weaken WG31 verification.
- **WG33-S1 · MCK legal/cash and instrument-specific completion.**
  *Verified 2026-09-16:* ownership carrying proxy2939M approved once and legacy
  claim semantics value-neutral. *Still required:* actual post-July legal/cash/
  funding/allocation state, forecast cash overlap, cash/securities classification,
  executed instrument outcomes/current components. Conditional legal5164M remains
  continuity-only and cannot publish a numeric successor. Preserve all source
  diagnostics/nonadditivity and Low reliability until separately resolved.
- **WG34-S1 · HCA professional-liability forward-cash completion.**
  *Verified 2026-09-16:* current line1464M, narrative total1996M, dedicated
  insurance investments519M, next-12-month573M/retained532M and ordinary
  NCI3433M are separate; legacy100/50/0 reserve sensitivity remains value-neutral.
  *WG35 update 2026-09-17:* two annual raw packages now bind gross/current/
  noncurrent/net reserves,47/80M recognized reinsurance and 2023–2025 paid-claim/
  provision rollforwards. Historical recurring payments stay in OCF. *Still
  required:* current-Q current reserve/reinsurance split, professional-liability
  premiums, exact multi-year runoff or equivalent forward-OCF reconciliation,
  and complete preferred/common bridge. Do not promote the532M
  arithmetic equality, add restricted assets to cash, infer recovery or remove/
  deduct the reserve without resolving its cash overlap.
- **WG36-S1 · HON continuing-company event reconciliation.**
  Actual June27 close precedes June29 Aerospace distribution; shares are already
  split-adjusted. Parent and HONA carve-out evidence need intercompany eliminations,
  distributed/retained assets, cash, debt and NCI, and continuing cost/FCFF scope.
  July17 Johnson Matthey funding, paid cash and acquired economics remain unbound.
  Trademark payments require receipts/tax/forecast overlap; Quantinuum is separate.
  A new HON value needs the full bridge. Cached submissions identify June29 8-K
  `0000773840-26-000084` and July23 8-K `0000773840-26-000120` as potential
  next sources; acquisition requires separate user authorization. Preserve the
  historical range without presenting it as refreshed post-event intrinsic value.
- **WG37-S1 · HON current post-close balance and enterprise cash scope.**
  *Verified 2026-09-18:* March pro forma bridge, continuing earnings history,
  Q2 adjusted cash, FY guidance, transaction financing and contract schedules are
  source-bound separately. *Still required:* one current post-close HON cash,
  debt, NCI and share bridge; Johnson Matthey funding/allocation/acquired FCFF;
  PSS/WWS proceeds and operating removal; intercompany settlement amounts;
  trademark receipts/tax/forecast overlap; enterprise-compatible cash conversion.
  Unavailable from cutoff-safe captured sources. A later eligible post-close
  filing is the release condition; do not combine March/June/July surfaces.
