# WG26 — remaining redeemable-ownership claim stack

Narrow carrying/alias source gate verified and user-confirmed,
checked 2026-09-15. Full claim-stack implementation remains incomplete.
WG25 narrow source-ledger/blocked-update result
user-confirmed, not completed lease reconciliation or pipeline release.
Batches 01–44 only; preserve all dirty/untracked work and history.

## Reference and current gap

Reference: bind issuer outside-ownership carrying once, reconcile aliases by
economic scope, keep redemption/conversion/warrants, ordinary/redeemable NCI,
legal/environmental accruals/recoveries and post-payment events separate.

Verified current source: LHX preferred redeemable subsidiary carrying $968M
duplicates a temporary-equity carrying presentation; $1.422B redemption value
is distinct. Current conversion and warrant derivative liabilities $130M/$186M
and environmental $660M/$485M recoverable assets are separate. Legacy $1.628B
mixed deduction is not an executable full current source rule.

MCK has $376M ordinary NCI, $2.563B common redeemable carrying and a dimensional
redeemable-equity-member alias. These may share only the carrying/alias mechanism;
its opioid $5.660B June accrual and reported $496M July payment remain separate.
Independent review initially excluded MCK from LHX's full preferred/redemption
mechanism. Primary agrees with that exclusion, but actual code/source review
confirmed both can share the narrower non-additive carrying/alias primitive.
MCK is included only at that boundary; no conversion/redemption policy is shared
and neither whole stack is cleared by one ownership mapping.

## Reuse and bounded plan

Reuse ReportedNciScopeRule/current source validator and existing bridge, claim
dispatcher, source index, frozen workers and pure calculation_recipe evaluator.
Extend semantic alias mappings only if current source proves the target and
declared dimensional/member/presentation scope. No amount/date in rule tables.

| ID | Severity | Verified delta | Acceptance |
|---|---|---|---|
| WG26.1 | P0 | Preferred and common redeemable aliases need explicit target/scope rather than additive sums | Real current source, duplicate collapse and unrelated dimension rejection |
| WG26.2 | P0 | Full source stacks remain separate from narrow ownership proof | No derivative/reserve/payment dropped, exact retained recipe comparison |
| WG26.3 | P0 | Runtime current gate needs fresh proof | Frozen two-worker, independent challenge, regression and isolated API |

Prove LHX representative preferred/temporary carrying and MCK difficult dimensional
alias only if genuinely eligible. Preserve mandatory full-stack blockers rather
than marking companies complete/unavailable. No scheduling, activation, Git
release, deployment, later-group execution or family adapters.

## Implemented and verified narrow source behavior

Extended the existing ReportedNciScopeRule, not a new valuation engine. Versioned
alias target/member/presentation mappings derive amounts and dates from source.
Required new carrying components need current instant USD/CIK/namespace and
balance-sheet liability presentation; negative components cannot offset other
claims. Explicit dimensional aliases require the declared axis/member, resolved
issuer namespace and approved presentation parent. Aliases reconcile to their
named carrying component, not to a target valuation. Duplicates collapse;
redemption diagnostics are separate from aliases and never enter the sum.

The existing source-verification command now records a partial ownership proof
when a mapping intentionally does not clear full implementation scope. The main
row remains implementation_gap; no calculator recipe, price, availability or
serving catalog is changed. Frozen workers therefore exercise the actual source
mapping without pretending a missing full-stack implementation is complete.

### Source evidence

LHX 10-Q `0000202058-26-000058`, period `2026-07-03`, filed `2026-07-30`:
structural SHA-256 `5cabfcb598e53ed46a96294c0a285547e833e5a52aa949abe6fba75a4e7056f3`;
raw HTML SHA-256 `ac631a84b954633b8ae89a8a35ac9bb054dfeb13b4ac2483cf3f48856bdadf02`.
Note B Strategic Investment in Subsidiary, Note I Debt and Credit Arrangements,
Note R Environmental Matters corroborate the actual economic scopes.

- Current preferred redeemable carrying $968M equals temporary-parent equity
  carrying $968M, same current context, as duplicate presentations of one claim.
- $1.422B redemption amount is not a second claim or the amount to read from the
  carrying fact's terse label. Current carrying reflects initial host $1.070B,
  deferred-tax reduction $89M, transaction costs $27M and accretion $14M. Those
  are accounting movements, not invented cash settlements.
- The instrument has mutually exclusive liquidation, QIPO conversion and later
  redemption outcomes; it was not currently redeemable. No invented conversion
  dilution is added alongside a cash/ownership claim.
- Current conversion/warrant derivative liabilities $130M/$186M are bifurcated
  and separately recognized; initial April 17 facts are not current duplicates.
  They require an explicit subsidiary-to-parent economic valuation rule, not
  absorption into the $968M carrying alias. Preferred is anti-dilutive and the
  warrants not currently exercisable; no current as-converted shares invented.
- Environmental liability $660M and recoverable assets $485M share the same
  program/context. Recovery is through future government contract pricing, not
  surplus cash. No automatic net $175M reserve or removal of cash-flow burden is
  approved without timing/forecast overlap. No environmental cash-payment fact
  was captured in this filing.
- Debt $10.999B equals $9.184B noncurrent + $1.815B current, also $10.776B fixed
  debt + $267M leases/other - $44M discounts/costs. Those are alternate views of
  one aggregate, not additive claims. $112M repayments (including $100M specific
  debentures) and $973M preferred net proceeds already affect ending cash/debt.

MCK 10-Q `0000927653-26-000234`, period `2026-06-30`, filed `2026-08-05`:
structural SHA-256 `86ba2d2b34b9acbdbb369fc35f903292eafa6a62a25a7513f930e4798a224afc`;
raw HTML SHA-256 `ae1dbb2b5240d1316869e75771565769fb61963e9dcf343d2bd1decc34bee502`.

- $376M ordinary NCI is a separate balance. $2.563B common redeemable carrying
  equals its current redeemable-equity-member dimensional alias. Aggregate
  reported outside ownership $2.939B does not conflate preferred instrument terms.
- No static LHX-style temporary-parent carrying or redemption-value fact is
  present. MCK $374M redemption adjustment and $293M/$81M temporary accretion
  are duration adjustments, not carrying balances. The reported $418M NCI/EPS
  duration diagnostic is not an ownership stock or a pure cash payment.
- Apollo convertible preferred, PRISM/Core Ventures put rights and ordinary
  interests retain separate economics. No full LHX conversion rule applies.
- Opioid accrual $5.660B = $602M current + $5.058B noncurrent; July $496M payment
  is a source-captured subsequent-event cash amount, not a same-period claim.
  Legal/acquisition/cash overlap and the complete post-period recipe remain
  required separate rules; no payment is deducted twice.

All current source references are controlling cached evidence eligible at
`2026-08-14`, not latest live SEC discovery as of the verification date.

### Exact classification replay, not new valuation

| Company | Retained low / base / high | Exact official changes | Reliability | Full refresh |
|---|---:|---:|---|---|
| LHX | 69.08352051394239 / 152.4724672181145 / 263.63410016487416 | 0.0 / 0.0 / 0.0 | Low | implementation_gap |
| MCK | 477.99247723179093 / 849.8325771275278 / 1262.3562145555925 | 0.0 / 0.0 / 0.0 | Low | implementation_gap |

Reclassifying LHX's legacy $1.628B into ownership $968M and remaining legacy
$660M is bit-exact value-neutral. Reclassifying MCK's legacy $8.103B into
ownership $2.939B and remaining $5.164B is also bit-exact. Those remaining
deductions are labeled legacy continuity, not certified current reserve/claims.
The old cash rollforward and ALL old economic adjustments remain. No $316M
derivative repair, $485M recovery benefit or new economic valuation is silently
applied. No numeric successor or unavailable conversion.

## Runtime evidence

- Narrow real-source proof/replay: `output/us-refresh-runtime/wg26-redeemable-ownership-source-proof.json`, file SHA-256 `0ea2d147d92e5317ea143d1ecd2cbb970d75a46a28b3d9456d550b315114f411`.
- Current direct report: `output/us-refresh-runtime/source-validation/1130c7af2063bdffc7eb405f5d3f89a6f9f0666be532c828be7450f63e101b9f/report.json`.
- Frozen two-worker report: `output/us-refresh-group-verification/908efdfe8c59f0c76d57ac6199ff278e1bfd66abb903ce071538bd34c09cffb4/report.json`.
  File SHA-256 `008ad5637cf1749763e0365c1ceceaa5990d96befa79ab2a6794303204431089`;
  implementation `3a17eb2d7205e53cf924a201beeabc071e12679dcb5e9709f3a9ffd13e32fd53`;
  policy `a59c891c786d3e74862e9c3a4daaba4f6893458b317be73d8caa5a9e88fc8a49`.
  Both main rows stay implementation_gap; both partial proofs are source_bound
  with numeric_successor_issued=false. Actual source data is processed inside
  each frozen worker, not replaced by compilation counts.
- Real isolated PostgreSQL-backed API login/list/detail/default-calculator
  parity: `output/us-refresh-runtime/wg26-blocked-preservation-api-evidence.json`.
  File SHA-256 `631ff18abe83dfb0cb2838dd7ad3d3cbce23029b136386255d74388fcebd2cf2`.
  LHX/MCK/INTC/JBL/HCA/HON exact historical ranges remain. No public UI/save or
  official calculator interaction changed, so browser/save/activation/reload/
  rollback were not repeated or claimed; final release still requires them.
- Current focused source/scope checks: 43 passed in 281.57 seconds, including
  actual frozen source workers. Final current-version full regression: **640
  passed**, one existing Passlib `crypt` deprecation warning, in **392.87 seconds**.
  Command: `PYTHONPATH=backend:. pytest -q backend/tests/test_refresh_*.py backend/tests/test_calculation_recipe.py backend/tests/test_batch_28_history.py backend/tests/test_batch_26_history.py backend/tests/test_batch_21_history.py backend/tests/test_batch_14_history.py`.
  Final independent defensive review: **14 passed in 6.88 seconds**, no current
  bounded-scope flaw. See [independent challenge](wg26-independent-review.md). Prior
  41/42-check runs predate the last negative-component guard and are not the
  final current-version acceptance evidence.

Required full-stack work: LHX economic preferred/derivative basis and environmental
forecast/recovery overlap; MCK ordinary/redeemable attribution and mixed legal/
acquisition/post-payment rules. INTC/JBL carrying/debt/cash gaps, WG25-O1 output-
location portability and HCA/HON blockers remain required. Do not count either
company as complete or add historical source successes into current readiness.

Current register: 440 companies, 419 historical recipes, 282 compiled contracts,
137 coding gaps, 196 financial reviews, 168 source gaps, 436 needs_recheck,
zero current-snapshot numeric source-bound and zero successive-period proofs.
Full regression also exercises INTC/JBL's current real frozen guard test; their
fresh review receipts reduce needs_recheck without producing valuations. Counts
overlap; no completion percentage or speedup is claimed.

Following group only after narrow-result confirmation: WG27 — subsidiary
preferred/derivative economic bridge scope — LHX first. Reconcile host carrying,
redemption outcomes, separate derivatives, program investment assets/proceeds,
cash already reflected, and locked current shares together; do not invent IPO
price/dilution, double-count cash/dilution or drop environmental/mixed claims.
No later-group work occurs under WG26 authority.
