# WG16 remaining NCI, acquisition and litigation overlaps

Verified and user-confirmed 2026-09-12. This is a bounded working-group
result, not release approval. WG16 did not activate production, schedule work,
merge, push, deploy, start family adapters or process companies outside Batches
01–44.

## Retained mechanism

BSX, DGX and EW all prove current NCI, acquisition-liability and legal-reserve
surfaces, but only DGX has a complete source-bound valuation candidate.

The reusable rules keep ordinary and redeemable NCI carrying balances separate
from NCI earnings, OCI, contributions and distributions. Acquisition aggregates,
Level-3 duplicates, typed components and current portions reconcile to one
carrying claim. Paid cash, measurement changes, possible-loss maxima and other
acquisition consideration remain diagnostics. Legal accruals are either deducted
once or retained as operating liabilities under the issuer's approved cash-flow
scope; no insurance recovery is inferred.

## Company results

| Company | Classification | Previous low / base / high | Current low / base / high |
|---|---|---|---|
| DGX | Source-bound representative; $303M ordinary NCI + $80M redeemable NCI + $100M acquisition liability; $174M malpractice and $17M legal reserves remain operating | 60.392900977119275 / 146.04096163084048 / 288.50140798514724 | 53.97122682607165 / 139.2569970055438 / 278.9208215655317 |
| BSX | Current $242M NCI, $257M acquisition liability and $282M legal accrual reconcile; post-period restructuring schedule remains separate | 12.073451734533077 / 26.917579129891784 / 49.3426337522577 | No candidate; implementation gap |
| EW | $106.9M NCI, $9.9M aggregate contingent carrying value with $7.5M current subset, and $56.9M legal reserve reconcile; unaccrued tail remains unbounded | 22.7162955873064 / 42.40480316156332 / 58.04798250543981 | No candidate; source/economic review |

DGX changes are -6.421674151047625 / -6.783964625296676 /
-9.580586419615543 per share (-10.633160598595136% /
-4.645247846590495% / -3.320810975074606%). Moving the same $483M
claim from the legacy preferred slot into $383M NCI plus a $100M signed
acquisition adjustment is value-neutral. The change comes from current
source-derived cash conversion and one current 112.37336M share denominator
rather than the older scenario-specific cash/share inputs.

BSX and EW have no official current valuation change because no candidate was
issued. A mechanical BSX calculation that simply removes its untimed
restructuring reserve is not an acceptable successor. EW's $132.5M acquisition
maximum and the former $70M arithmetic midpoint are no longer treated as current
scenario liabilities, but its unbounded patent, milestone, appeal and tax tail
still prevents a successor valuation.

## Source classification

### BSX

- Controlling 10-Q: accession `0000885725-26-000053`, period `2026-06-30`,
  filed `2026-08-03`; structural SHA-256
  `de76e924cb5d09779171cd0ab5ae0d4a29ea2932166e40bebcea8314573022c3`;
  source-manifest SHA-256
  `95d96bff75ab58407dc328931bca35a4a57b4b1dbfa0c98b662efada7abd8f5a`.
- Current NCI is $242M. NCI earnings and OCI reconcile the roll-forward and
  remain duration diagnostics.
- Current contingent consideration is $257M: the aggregate and Level-3 views
  match, while $76M and $181M typed components sum to the same total. The $596M
  maximum and $82M/$78M cash presentations are not added.
- Current legal accrual is $282M. The $76M litigation expense flow, reversed
  historical award and covenant exclusion limits are not additional claims.
- Post-period restructuring cash is disclosed as $600M–$700M without a timed
  schedule. It cannot remain in a generic equity-claim slot or be discarded.

### DGX

- Controlling 10-Q: accession `0001022079-26-000070`, period `2026-06-30`,
  filed `2026-07-23`; structural SHA-256
  `b57ae8b2132584bc31951d81d1681d4930266a5f6bb48f3563845a845b2af32c`;
  source-manifest SHA-256
  `30eca0eba5c1117ddd2345aa7c82fa04058ebf59910f3f4a68d221d72bde81cf`.
- Ordinary NCI is $303M and redeemable NCI is $80M. The matching $80M fair-
  value view is an alias, not another claim. Earnings, contributions,
  distributions and dividends remain duration diagnostics.
- Current contingent consideration is $100M in matching aggregate and Level-3
  presentations. $3M/$4M measurement changes and $38M acquisition cash are not
  additional contingent liabilities.
- The $174M malpractice reserve and separate $17M litigation reserve remain
  recorded operating liabilities; the approved cash conversion already bears
  them, so the equity bridge adjustment is zero.
- Current $5.642B debt reconciles to $10M current plus $5.632B noncurrent debt.
  The complete filing scope and balance-sheet witnesses support no separate
  commercial paper, finance lease or marketable-security balance.

### EW

- Controlling 10-Q: accession `0001099800-26-000043`, period `2026-06-30`,
  filed `2026-08-04`; structural SHA-256
  `58e51c247ece28daac527bfbf97aedb04ccc39ed43dd42eade774d660e623e87`;
  source-manifest SHA-256
  `be53d58e79c1467b5e1581040a8f6c30cb78e3965f7a900c2e145dffd271b2c9`.
- Current NCI is $106.9M. Negative NCI earnings, comprehensive income and the
  $112.4M equity movement are flows, not additive balances.
- The current aggregate Level-3 contingent carrying value is $9.9M, with a
  $7.5M current portion. The $132.5M Autus maximum and separate acquisition
  equity presentations remain diagnostics.
- The $56.9M litigation reserve is not added to the broader $72.4M litigation-
  and-insurance aggregate, and no recognized insurance receivable is inferred.
- PASCAL, Valtech, appeal, securities and tax exposures outside recorded
  balances lack a finite source-supported range. The rule therefore fails
  closed with an explicit review reason.

## Verification evidence

- Frozen source index:
  `output/us-refresh-runtime/source-indexes/3f708765d48cd7c5e24782deae53fc6b4714a3a51c9b7372e2c3e485bfc33ee4.json`,
  file SHA-256 `b696cb36ef36d4e9d7adb021c69d33f3ca94673310eb9c053611c800f4c46a5f`.
- Direct cached-source report:
  `output/us-refresh-runtime/source-validation/4b586343ca6a0b77910d5e2a8cf9f7b296cd56639d6542e34af6d63610faaeea/report.json`,
  SHA-256 `4b586343ca6a0b77910d5e2a8cf9f7b296cd56639d6542e34af6d63610faaeea`.
  Outcome: DGX source-bound, BSX implementation gap, EW source/economic review.
- Frozen two-worker group:
  `output/us-refresh-group-verification/57fbccd5d710025ed884792d45a53ab82662728fb60ac7b7c29a04a25cd5d453/report.json`,
  SHA-256 `e687b0ca74dd80ec2f123aca1757af8f3b861abdaf49b47d5ed51313333783f5`.
  It reproduced the same three outcomes on implementation SHA-256
  `61d18588b15c90c9d3c16672419b202c3ad6005adf1094b996b372e2863e9e11`
  and policy SHA-256
  `cf2d1a51cb7e47bda538cb09b0edaa715289727f89dbb2a2a89da226f53512fb`.
- Focused cross-module regression: 163 passed in 240.90 seconds. It covers the
  new overlap rules plus WG15 mixed claims, acquisition, litigation, NCI,
  preferred lifecycle, bridge scope, normalization, compilation/bindings and
  the two-worker flow.
- Isolated DGX API/database UAT:
  `output/us-refresh-operational-uat-20260912T081008Z-a3132f9d/uat-report.json`,
  SHA-256 `2bf8415a606c55e4b1f75473537a48a2d1ad1f3bb28bf367ef4f8c32259e5174`.
  A real FastAPI worker served predecessor → candidate → rollback, reloaded
  without restart, rejected stale CAS and retained 440 companies plus 419
  private recipes. Production was not touched.
- Current work register: 440 companies, 419 recipes, 267 compiled contracts,
  152 implementation gaps, one current-version source-bound result and zero
  successive-period proofs. Readiness correctly exits 2 at 267/419.
- `git diff --check` passed. No frontend behavior changed, so the browser was
  not mechanically rerun for this source/calculation-only group.

Three Luna reviewers independently inspected BSX and DGX at xhigh effort and EW
at high effort. The primary agent rechecked their source facts, corrected EW's
current portion/aggregate distinction, implemented the shared rules, ran the
real cached-source and API paths, and preserved both unresolved cases.

## Remaining blockers

- BSX needs a source-timed schedule or separately approved event treatment for
  the $600M–$700M post-period restructuring cash, plus a refreshed combined-
  company history check. Its current NCI/acquisition/legal selectors are proved,
  but the complete valuation contract is not.
- EW needs finite source evidence or resolution for the unaccrued PASCAL,
  Valtech, appeal, securities and tax exposure. Current recorded balances do not
  bound that tail.
- DGX has no successive-filing proof. Its current candidate remains diagnostic
  and unactivated until release approval.
- No company has successive-period proof under the current release candidate.
