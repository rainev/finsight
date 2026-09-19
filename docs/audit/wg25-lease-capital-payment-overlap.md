# WG25 — finance-lease and capital-payment overlap

Narrow source ledger/blocked-update gate verified and user-confirmed,
checked 2026-09-15. Complete lease/debt reconciliation remains blocked.
WG24 narrow migration/blocked-update result
user-confirmed, not an INTC numeric valuation. Scope Batches 01–44 only.

## Reference, current gap and reuse

Reference: user-approved WG25 requires carrying balances, principal cash,
investing capital payments, new-only schedules, uncommenced leases and overlap
kept separate. No inferred dates, amounts, absent-tag zeros or duplicate debt.

Current verified code: WG24 preserves Intel's $1.423B financing capital-payment
line as a review diagnostic; WG23 preserves Jabil's $51M new-only payment table
as review. Neither currently proves full lease debt. Reuse existing current
filing identity/period validation, deterministic narrative extraction, commitment
selector, claim dispatcher, frozen workers and exact recipe evaluator.

Verified source read: Intel cash-flow statement and MD&A explicitly describe
financing payments for capital expenditures with extended terms, separate from
finance-lease principal. Jabil Note 4 explicitly covers NEW leases only; its
guarantee and uncommenced exclusions cover the combined lease disclosures, not
necessarily finance-only. No full current lease carrying fact was found in the
controlling structural packets. Both independent reviews confirmed this source
gap; absence does not
prove zero, aggregate-debt inclusion or economic absence.

## Bounded specification and gates

1. Bind hashed narrative scope to the same current filing as the structural
   packet: Intel extended-term financing cash, Jabil new-only schedule and its
   separate guarantee/uncommenced exclusions. Use exact versioned extraction
   contracts, not arbitrary keyword classification or amount matching.
2. Introduce a reusable lease/capital-payment source ledger. Distinguish current
   carrying claims from duration flows and payment maxima; require unit/entity/
   namespace/role/presentation and period agreement. Do not promote future cash
   totals or noncash disclosures to current balances. Duration contexts alone
   do not settle the noncash amount's economic stock-versus-flow/ending coverage.
3. Require complete current carrying and debt-overlap proof before numeric
   treatment. Missing balances/overlap remain named review stops. No new floor,
   margin, cash adjustment, capex deduction or debt deduction is invented.
4. Prove representative Jabil schedule and difficult Intel financing cash;
   real cached filing receipts, frozen two-worker flow, independent financial
   challenge, regression and isolated API preservation.

### Gaps

| ID | Severity | Verified delta | Acceptance |
|---|---|---|---|
| WG25.1 | P0 | Cash financing and future lease tables do not prove current carrying debt | Source-backed typed ledger and explicit missing-scope stops |
| WG25.2 | P0 | Narrative economic scope not executable for these two current packets | Hash-bound deterministic scope terms; altered/stale sources fail closed |
| WG25.3 | P0 | No current numeric successor can be justified without full carrying/overlap | Exact unchanged history/calculator parity; no unavailable conversion |

Preserve Intel governed margins/history/floor and separate cash/AFS and special-
situation review; preserve LHX/MCK/HCA/HON required blockers. No production,
schedule, merge/push/deploy or family adapters. Economic evidence gaps remain
required work even if the classification/exception implementation is verified.

## Source-supported result, not numeric refresh completion

Both companies genuinely share the **current carrying claim versus cash-payment/
future-schedule distinction**. Their financing mechanisms are not forced into
one deduction: Intel extended-payment-term cash and Jabil new-only lease
commitments retain separate versioned source variants in the shared ledger.

INTC controlling cached 10-Q: accession `0000050863-26-000157`, period
`2026-06-27`, filed `2026-07-24`. Structural raw SHA-256
`20d1bd5f814320a61d0bffdae86433b6a340eb1501fb7f7b18e37eaca890f201`;
primary HTML SHA-256
`23bf9b8f45c8a4412245f9919fcbf124d0aa1af3bd949af671a4cce68fc2acda`.

- Current six-month cash: investing PP&E $6.192B; extended-term financing PP&E
  payments $1.423B; finance-lease principal $832M. All use aligned
  `2025-12-28..2026-06-27` USD issuer cash-flow contexts with their respective
  investing/financing presentation parents. These are **YTD disclosures**, not
  replacement TTM valuation inputs; retained TTM capex remains $12.105B.
- Reported noncash supplemental PP&E $3.148B includes $626M extended-term
  disclosure. Context duration alone does not establish economic purchase-flow
  versus ending unpaid-balance scope. Neither supplies a complete current
  financing liability or its debt overlap, and the inclusion is not added again.
- Balance-sheet debt carrying components $1.988B + $48.549B = $50.537B. This is
  not certified complete lease debt; full current lease carrying and financing-
  payable rollforward remain unbound. PP&E/finance-lease ROU assets cannot be
  substituted for a liability. Cash/AFS, derivatives/warrants, incentives,
  transformation and all WG24 special-situation conditions remain required work.

JBL controlling cached 10-Q: accession `0001628280-26-046138`, period
`2026-05-31`, filed `2026-06-30`. Structural raw SHA-256
`ae1fb9a2bb15f1ecf2d7912706ea15b85743f52c1b400cfef5db3deccf4f367d`;
primary HTML SHA-256
`97f71940301823dfd05a3b17e12cf34d3f8172f8e7e324e7af2fe42ec461883b`.

- Note 4 $51M NEW-only finance payments reconcile $8M + $37M + $6M + reported
  zero after year five. They remain future commitments, not current debt/PV.
- $80M residual guarantees and $181M signed/uncommenced payments are exclusions
  from the combined operating/finance lease disclosure. No finance-only split,
  recognized guarantee liability, maximum carrying claim or extra deduction is
  inferred. Guarantees are described as not probable and excluded from lease
  measurement, not as economic absence in every program.
- Balance-sheet debt carrying components $499M + $2.879B = $3.378B. Actual Note 6
  senior-note carrying rows sum to $3.378B; several principal amounts differ.
  The ledger therefore does not call these par/face amounts or prove full lease
  inclusion. Investing PP&E cash $382M is YTD `2025-09-01..2026-05-31`.
  Broad other-debt repayments $1.884B cannot substitute for a finance-principal
  split. Operating lease liabilities $98M/$416M and the combined $2.899B PP&E/
  finance ROU asset do not fill missing finance-lease carrying balances.
- Exact schedule dates/interest are required only if deriving PV or annual cash
  payments. A complete current carrying claim with proven debt overlap would
  not need invented annual timing. Current filing does not bind that claim.

### Exact historical valuation comparison

No numeric successor or unavailable conversion. All old economic adjustments
remain in executable history; carrying/schedule classification does not justify
silently removing the legacy lease deduction.

| Company | Retained low / base / high | Exact official changes | Reliability | Outcome |
|---|---:|---:|---|---|
| INTC | 0.0 / 3.001327108470505 / 16.50488639459598 | 0.0 / 0.0 / 0.0 | Low | Source/economic review, no current carrying/overlap proof |
| JBL | 19.535888894649034 / 104.26190555010285 / 220.1997056672033 | 0.0 / 0.0 / 0.0 | Low | Source/economic review, new-only schedule cannot fill current liability |

LHX preferred/redeemable/environmental stack, MCK ordinary/redeemable/opioid
post-payment stack, HCA professional-liability overlap and HON separation/
acquisition rollforward remain unchanged required work. All six isolated API
detail/default-calculator ranges remain exactly equal to the frozen catalog.

## Verification and corrections

Shared policy `FINSIGHT-LEASE-CAPITAL-SCOPE-WG25-1`; narrative extraction
`FINSIGHT-NARRATIVE-EVIDENCE-WG25-1`. Exact document/manifest/text/excerpt hashes,
section/character locators and filing dates are retained privately. Altered or
superseded narrative sources fail re-extraction; facts require identity, USD,
instant/duration context, finite/nonnegative values and approved presentation.
Distinct duration windows fail closed rather than dropping a quarter. Debt
carrying sources require liability presentation as well as balance-sheet role.
No source amount or filing date is embedded in economic rule tables.

- Real source ledger and historical replay:
  `output/us-refresh-runtime/wg25-lease-capital-source-proof.json`, SHA-256
  `5ef4b3a018027928ba39f7f180833abae3a476be15af9ce2e19b4f8f0f29ad97`.
- Current direct report:
  `output/us-refresh-runtime/source-validation/03c9d57a97c5a8b6f9bf911dc31036e76be10807636ead1a368d4539372773a4/report.json`.
- Frozen two-worker report:
  `output/us-refresh-group-verification/67087b79ffa54356f027136954d363c0cc9f97ff4e28dd3650c6ac30d821a63b/report.json`,
  SHA-256 `fb8ff567f4d8ee3537b9a7dbe39939affd98552b4b3427869238ccfbfd109309`.
  Implementation `345bb86f8823edafde9516205b79c8495386b258dc7cc7f25c6bee12ca1394a9`;
  policy `46c59a0bc121e199e0793eaa68b3d061c848b4bce3832d2a9e457b182e1c5eec`.
  Both named carrying/overlap reviews are verified by reading the actual reasons,
  not merely the status count. No acquisition or activation.
- Focused checks: **38 passed in 21.72 seconds**, including a real frozen
  two-worker subprocess regression that asserts economic-review reasons rather
  than a mechanically failed lookup. Final current-version broad regression:
  **626 passed**, one existing Passlib `crypt` deprecation warning, in
  **271.37 seconds**. Command:
  `PYTHONPATH=backend:. pytest -q backend/tests/test_refresh_*.py backend/tests/test_calculation_recipe.py backend/tests/test_batch_28_history.py backend/tests/test_batch_26_history.py backend/tests/test_batch_21_history.py backend/tests/test_batch_14_history.py`.
- Isolated PostgreSQL-backed API login/list/detail/calculator GET/POST:
  `output/us-refresh-runtime/wg25-blocked-preservation-api-evidence.json`, SHA-256
  `bdfe076745acd865bb54f29aa30c0cd1f3842f4652ce31d7045da4edf6251c46`.
  440 companies; exact INTC/JBL/LHX/MCK/HCA/HON parity. No public UI/save behavior
  changed or numeric candidate existed, so browser/save/activation/reload/rollback
  were not repeated or claimed. They remain final release acceptance requirements.

Primary corrections:

1. Initial frozen workers returned wrong-root lookup errors, not economic
   validation. Source root is now explicitly handed off from acquisition/
   verification into the source ledger, instead of derived from frozen code
   location. Current actual group reaches the intended financial review reasons.
   The faulty report `b063f1cf...` remains historical failed evidence, superseded.
2. Initial noncash flow wording was overly strong. The reported total/inclusion
   and unresolved economic ending scope replace inference from duration shape.
3. Independent review identified ambiguous "face debt" wording; current fields
   explicitly say balance-sheet debt carrying values. Guarantee disclosure is
   not declared a recognized liability or inferred contract maximum.
4. Multiple duration windows now fail closed, and liability-parent guards were
   strengthened. Both final independent Luna High delta challenges passed;
   primary verified all material findings. See
   [independent challenge](wg25-independent-review.md).

An external temporary output-root test failed before completion with a missing
snapshot source-index file. The approved project diagnostic root passes; arbitrary
output-root portability is **not verified**, and is recorded as operational
backlog rather than silently claimed. No integrity guard was disabled.

Register remains 440 companies, 419 recipes, 282 compiled, 137 implementation
gaps, 196 financial reviews, 168 source gaps, 438 needs_recheck, zero current-
snapshot numeric source-bound and zero successive-period proofs. This group
improves source classification/exception implementation, not numeric completion.
All counts overlap and receipts from different versions are not release-ready
summed successes. Production and Git HEAD remain unchanged.

"Current" here means the controlling cached evidence eligible at the retained
recipe cutoff `2026-08-14`, not a claim of latest live SEC discovery as of the
verification date. No new retrieval or event-exhibit coverage was established.

Final checks: repeated final group manifest/report remained byte-identical;
source proof/direct/group fingerprints match the final current implementation
and policy. Source index SHA-256 stays
`0d38ec5d8b427528d8412809db98d6f0ec994c8a2c1c388d7a236acfa45356a8`.
Module compilation and `git diff --check` pass; HEAD is `4fa0a64`.
Older 623/624-check runs predate final corrections and are not substituted for
the current 626-check gate. No measured speedup is claimed: concurrent reviews/
regressions make the timing samples unsuitable for like-for-like comparison.

## Following group, after narrow-result confirmation only

WG26 — remaining redeemable-ownership claim stack: inspect LHX first; inspect
MCK only if its actual source supports a genuinely shared carrying/alias rule.
Keep preferred redemption/conversion/warrants, ordinary/redeemable NCI, legal/
environmental accruals and recoveries, and post-payment events separate. Preserve
INTC/JBL required carrying/overlap gaps and HCA/HON blockers. Do not force a
shared deduction or begin family adapters. WG25 authorizes no later group.
