# WG34 — HCA professional-liability reserve and forward-cash overlap

WG34 narrow gate user-confirmed 2026-09-17. WG33 narrow governed-ownership gate user-confirmed, not a
completed MCK/HCA refresh or pipeline release. Cached evidence only; HCA first,
MCK preservation control. No acquisition, tuning, adapters or release actions.

## Reference, audit and bounded rule

| ID | Severity | Verified delta | Acceptance | Status |
|---|---|---|---|---|
| WG34.1 | P0 | Reserve/asset presentations are nonadditive | Exact source scope, current/comparative and difficult reconciliation | USER-CONFIRMED |
| WG34.2 | P0 | Paid claims/reinsurance/OCF overlap incomplete | No inferred payment/recovery or duplicate cash/reserve adjustment | USER-CONFIRMED |
| WG34.3 | P0 | Legacy scenario reserve sensitivity needs honest labels | Preserve 100/50/0 noncurrent sensitivity value-neutrally | USER-CONFIRMED |
| WG34.4 | P0 | Runtime/history preservation | Frozen workers, independent challenge, regression, isolated API | USER-CONFIRMED |

## Current source ledger and financial meaning

Current HCA 10-Q accession `0001193125-26-321077`, report 2026-06-30,
filed 2026-07-28. Structural SHA-256
`87ec53ce464da6e43f13646a5d44c9cf7de4bc1795175d7f2c2bed3297f19fec`;
raw HTML `54906eacf9bb8118621afc3d9a6c0afa52199dae87171482535ca8ff986dbe6b`.

- balance-sheet ProfessionalLiabilityRisks1464M current/1466M year-end comparison;
  line visually appears after long-term debt, but structural parent is only broad
  LiabilitiesAndStockholdersEquityAbstract—not explicit current/noncurrent scope;
- insurance-subsidiary reserve104M plus retained self-insured reserve1892M =
  total narrative reserves1996M;
- expected next-12-month net claims573M, retained subset532M, exact timing None;
- 1996−1464=532M matches retained expected payments arithmetically, but is **not
  a tagged current reserve** and cannot be promoted as reported reconciliation;
- insurance portfolio519M = current117M + noncurrent402M; held for statutory
  equity/claims and not surplus cash or automatic recovery offset;
- reinsurance contracts exist, but no separately recognized recovery receivable
  amount; generic receivables cannot substitute;
- coverage120M/occurrence and retention15M/occurrence are contract limits, not
  aggregate liabilities or claim adjustments;
- ordinary NCI3433M reconciles independently; NCI earnings/distributions are
  flows, not additional stocks.

Five annual Companyfacts OCF observations are available (2021–2025), but no
annual HCA raw10-K package is cached. Current Q comparative supplies year-end
balances. Annual reserve narrative/payment history is therefore unavailable;
do not describe it as unreported/zero or claim successive annual package proof.

## Governed narrow result

`FINSIGHT-PROFESSIONAL-LIABILITY-FORWARD-SCOPE-WG34-1` keeps premiums/ordinary
claims in reported cash history and preserves the existing noncurrent line
sensitivity while overlap remains incomplete. It does **not** remove the reserve:

- bear: NCI3433M +100%×1464M sensitivity;
- base: NCI3433M +50%×1464M sensitivity;
- bull: NCI3433M +0% sensitivity.

Semantic fields become preferred0/NCI3433M/signed reserve stress, but each old
scenario value is exactly unchanged. Full1996M reserve, expected573/532M flows,
insurance assets, reinsurance and coverage maxima are not added/netted. Actual
paid claims and recovery history remain None. `numeric_successor_issued=false`.

| Company | Retained low / base / high | Exact changes | Reliability |
|---|---:|---:|---|
| HCA | 113.67603706327972 / 341.89411295994046 / 666.5180777852703 | 0 / 0 / 0 | Low |
| MCK control | 477.99247723179093 / 849.8325771275278 / 1262.3562145555925 | 0 / 0 / 0 | Low |

Both main rows remain implementation_gap; no numeric/unavailable successor.
Focused HCA source suite **15 passed in6.35s**. Independent Luna High challenge
found that an initial three-observation minimum was weaker than the five-year
inventory; primary changed the governed requirement to exactly five and added a
four-observation fail-closed test. Final independent **15 passed in3.86s**, no
remaining material issue. See [independent review](wg34-independent-review.md).

Frozen report
`output/us-refresh-group-verification/9af94a0e3bbe151a9fcb3b390424f22fa07c7e4c4f747d02bde9c7af05b97a6e/report.json`,
file SHA-256 `1a14bddcb62f276274c9f08a52fb49788b7ac055d17e07bb88f633660c57c3b2`;
implementation `e0c2f01dbae3a5b827139e832edaf6a2b603bfa06c8c0ad00b423d728b7106ca`,
policy `f0a41020bb6a3d399c3470dea4901764426409912d671727c2d488cd74cbdb0d`.
Repeated bytes are identical; HCA/MCK remain implementation_gap. Isolated real
440-company PostgreSQL API/default-calculator parity passes for HCA, MCK, LHX,
INTC, JBL and HON; receipt SHA-256
`c27b6b40dfe3fe1a4d71a93518d3789f55a05a0b66d4bd973b063f55105b8eaf`.
No public model/UI/save behavior changed, so browser/save/activation/rollback
were not repeated or claimed. Final broad: **781 passed**, one existing Passlib
crypt deprecation warning, **247.87 seconds**. HEAD remains `4fa0a64`; no
production, schedule, merge, push or deployment.

Rebuilt register: 440 companies,419 recipes,282 compiled instructions,137 coding
gaps,196 financial flags,168 source flags,435 needing current-version recheck,
21 prior unavailable and zero successive-period certifications. Categories
overlap and are not a completion percentage. All MCK, LHX, lease, portability,
HON and hardening work remain required.

## Following group, not started

WG35 should capture and reconcile HCA annual professional-liability evidence from
annual packages `0001193125-26-044769` and `0000950170-25-020134`, latest first,
only with explicit network/contact-egress authorization. It should seek reserve
rollforwards, paid claims, recognized recoveries, premiums and forward timing;
Companyfacts observations are not substitutes for raw annual narrative evidence.
Every existing blocker remains required. No later group started here.
