# WG18 ordinary NCI with acquisition carrying claims

Verified 2026-09-12 and user-confirmed 2026-09-13. This is a bounded working-group
result, not release approval. WG18 did not activate production, schedule work,
merge, push, deploy, start family adapters or process companies outside Batches
01–44.

## Retained mechanism and outcome

GLW, MDT and PFE all prove the shared current mechanism: an ordinary
noncontrolling-interest carrying balance plus a separately reported acquisition
carrying liability. Each company now has a source-bound successor candidate on
one frozen implementation and policy snapshot.

The implementation binds current carrying balances separately from NCI
earnings and owner flows, current/noncurrent subsets, Level-3 duplicates,
acquisition cash, measurement changes, operating legal/environmental reserves,
preferred par-only disclosures and post-period transactions. No transaction
maximum, paid cash flow or operating reserve is added to the equity bridge.

## Company results

Ranges below are exact low / base / high values. Candidate changes are relative
to the frozen historical recipe; official serving change remains zero because
nothing was activated.

| Company | Previous range | Source-bound candidate | Exact candidate change |
|---|---:|---:|---:|
| GLW | 3.350978640724463 / 15.157336392596388 / 31.59951088000838 | 3.3832508772483743 / 15.282530866244509 / 31.817188337275947 | +0.032272236523911424 / +0.1251944736481203 / +0.21767745726756615 |
| MDT | 30.522535700217027 / 55.40862094808861 / 79.209828771173 | 30.870846235865745 / 55.739197524880744 / 79.36607325501032 | +0.34831053564871794 / +0.3305765767921329 / +0.1562444838373267 |
| PFE | 5.935452072306099 / 14.768112979685727 / 34.60589590237525 | 5.516414408100449 / 14.95295334390251 / 33.83719063801446 | -0.4190376642056499 / +0.18484036421678418 / -0.7687052643607899 |

The claim migration by itself changes GLW and PFE by exactly zero because their
legacy mixed claim totals already equal the source-bound component sums. For
MDT, removing the duplicate $200M operating-reserve deduction changes the
claim-only replay by
`+0.15526744817949023 / +0.1557544338059813 / +0.1562444838373267`.
The remaining candidate movement comes from recomputing current source shares,
cash conversion and bridge inputs under the approved shared normalizer, not
from claim arithmetic.

## Source classification

### GLW — representative single noncurrent claim

- Controlling 10-Q: accession `0000024741-26-000255`, period `2026-06-30`,
  filed `2026-07-29`; raw HTML SHA-256
  `5ce0dc355e9ec6c0d9131ad9e698e8a2bd9951426ee3ce8f51d9b7d0c8980ac1`;
  current-parser structural SHA-256
  `88a254a808124275f5fc12506cbdeaf07f355f2dff533526e221408a79405ee4`.
- Ordinary NCI is $567M. Current H1 $87M and Q2 $50M NCI earnings are flows,
  and the $567M equity-member row is a duplicate presentation.
- Noncurrent contingent consideration is $156M. No current portion or current
  acquisition-payment fact is evidenced; absence is not converted to zero.
- The $85M environmental accrual stays in operating liabilities. NVIDIA warrant
  proceeds/dilution and other event evidence remain separate.
- Current debt is $668M. The same-context noncurrent debt row is $7.756B at
  `decimals=-6` and $7.8B at `decimals=-8`; declared-precision reconciliation
  selects the precise row, producing $8.424B total debt once.
- Current Q2 revenue, operating cash, capex and interest are reconstructed from
  structural YTD/comparative facts because companyfacts stops at Q1 for those
  fields. Total capex uses reported `PaymentsForCapitalImprovements`.

### MDT — difficult typed-location and operating-reserve case

- Controlling 10-K: accession `0001628280-26-044354`, period `2026-04-24`,
  filed `2026-06-18`; raw HTML SHA-256
  `7ce6d9c32d2964b14d6851b85b1f91c373a8bde2c1412aa394c91f12a212bade`;
  current-parser structural SHA-256
  `2961cd681afb1faddffee523fa175a47b7df6366ccabd6736c2c66f40ae65b9b`.
- Ordinary NCI is $609M. $37M of NCI earnings and MiniMed ownership movements
  are duration flows, not added balances.
- The acquisition carrying liability is $163M. Typed balance-sheet locations
  split it into $32M current and $131M noncurrent; Level-3 components split it
  into $141M revenue milestones and $22M product-development milestones. Each
  view reconciles independently to one $163M claim.
- $406M of acquisition cash and the negative $5M measurement change are flows,
  not claims. The $200M loss-contingency accrual is an operating liability and
  receives no second equity-bridge deduction.
- The $28.131B reported debt carrying total is used once. A $1 par-only
  preferred disclosure is accepted only because the same current filing reports
  zero preferred shares issued and common components reconcile exactly to
  parent equity.

### PFE — current/noncurrent Level-3 duplicate case

- Controlling 10-Q: accession `0000078003-26-000095`, period `2026-06-28`,
  filed `2026-08-04`; raw HTML SHA-256
  `e7eedee8103786bd6d60b555741a427c8242a972bd5d1458d4e4ca25d02ce141`;
  current-parser structural SHA-256
  `c5f7d0a127729dbf59aa878ac00c5fd8d0310dfc5c38a2336eceb436d5f4b26b`.
- Ordinary NCI is $302M. $10M quarterly and $19M year-to-date NCI earnings are
  flows, not balance-sheet claims.
- Contingent consideration is $96M current plus $2.163B noncurrent, or $2.259B
  once. Matching Level-3 rows corroborate rather than add. $255M quarterly and
  $550M year-to-date remeasurement facts are flows.
- Metsera cash already paid, CVR maxima, legal settlements, restructuring,
  pension and tax matters remain outside the current claim. Debt is separately
  bound at $63.194B and preferred equity at zero.

## Verification evidence

- Frozen current source index:
  `output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json`;
  file SHA-256 `0d38ec5d8b427528d8412809db98d6f0ec994c8a2c1c388d7a236acfa45356a8`.
  It records current parser definition SHA-256
  `22e48483c36e5cf0cc694b901716085abfd8ec700805322dc3c0ae183ad8f3f0`
  for all three reparsed hashed filings.
- Direct cached-source report:
  `output/us-refresh-runtime/source-validation/a79c57afce22eee30933f9532e989e1d250a636a334e4aaace4c373df06498bb/report.json`,
  SHA-256 `a79c57afce22eee30933f9532e989e1d250a636a334e4aaace4c373df06498bb`.
  Outcome: three current source-bound candidates on implementation SHA-256
  `19e7f6f985e317d112fe4dd938a3dd1a80158bc15628e8c62f0ae9ec46dbd2c3`
  and policy SHA-256
  `178d3bd912c5fbe5e1a54f43fd85dd71088303094927f8fd20600aa139879e29`.
- Frozen two-worker group:
  `output/us-refresh-group-verification/1cf60684f8a77f5fadb93f997a84f375a50ca7883ac423da58b192bea6c31966/report.json`,
  file SHA-256 `0584a924f2e7654eba911b37c34e63da1d92f1fce4062dfeb0b076348bf889c6`.
  Worker 1 handled GLW/PFE and worker 2 handled MDT; deterministic reduction
  reproduced all three candidates exactly.
- Focused cross-module regression: 175 passed. It covers WG18 source rules,
  typed members, duplicate drift, declared-precision debt, par-only preferred
  evidence, earlier acquisition/litigation/NCI rules, bridge, normalization,
  compilation/bindings and the two-worker path.
- Each company passed isolated real FastAPI/database catalog activation,
  request reload, stale-CAS rejection and rollback. Evidence and SHA-256:
  - GLW: `output/us-refresh-operational-uat-20260912T101948Z-1f03a8ec/uat-report.json`,
    `b249d928630aa7da5ad3ba474eaa33c34357bc660b5a3e253fe4cdfccbff72bd`.
  - MDT: `output/us-refresh-operational-uat-20260912T102023Z-90787f12/uat-report.json`,
    `19d513addb02a4dbff1332dd840d636e3198ace130246c9cfca07f57171bdb41`.
  - PFE: `output/us-refresh-operational-uat-20260912T102047Z-ff3bdd5b/uat-report.json`,
    `0084c3135625604296622504b0e563cfeb86d2a4fecf634b946cecaa4da18355`.
  All three retained 440 registry entries and 419 private recipes and explicitly
  report `production_runtime_touched=false`.
- Current work register: 440 companies, 419 recipes, 272 compiled contracts,
  147 implementation gaps, 192 financial reviews, 164 source gaps, three
  current-policy source-bound results and zero successive-period proofs.
  Readiness correctly exits 2 at 272/419.
- No frontend behavior changed, so the redesigned browser was not mechanically
  rerun. `git diff --check` is required before this gate is presented.

Three Luna reviewers were assigned bounded, non-overlapping GLW, MDT and PFE
source audits at high/xhigh effort. The primary agent rechecked their material
facts, reparsed the exact cached filing bytes with the current parser, integrated
the rules and independently exercised the group and API gates.

## Remaining blockers

- No WG18 company has a successive-period proof yet. This remains a final
  release requirement, not a reason to discard the current source-bound result.
- The current source index is large and its one-time scan took 378.60 seconds;
  downstream indexed runs were bounded and did not rescan it.
- These are isolated successor candidates. Production remains on the prior
  catalog until the broader release gate and explicit approval.
- The complete pipeline remains unfinished: 147 implementation gaps, 192
  financial reviews and 164 source gaps remain elsewhere in the 440-company
  register.
