# WG17 ordinary and redeemable NCI with contingent consideration

Verified and user-confirmed 2026-09-12. This is a bounded working-group
result, not release approval. WG17 did not activate production, schedule work,
merge, push, deploy, start family adapters or process companies outside Batches
01–44.

## Retained mechanism and release outcome

DVA and CRL prove the shared ordinary-NCI, redeemable-NCI and acquisition-claim
mechanism. Both remain source/economic review; no new valuation candidate was
issued. ZBH was inspected but excluded because its filing proves ordinary NCI,
not redeemable NCI, and its China-distributor and tax tails remain unbounded.

The source rules reconcile current carrying balances separately from fair-value
aliases, redemption ranges, earnings, owner flows, paid cash, acquisition cash,
operating liabilities and post-period events. A clean mechanical replay is not
accepted when an acquisition obligation already sits inside debt or when a
separate current liability has unresolved operating-cash overlap.

## Company results

| Company | Classification | Existing low / base / high | WG17 result |
|---|---|---|---|
| DVA | Representative source mechanism; $283.118M ordinary NCI + $1.561416B redeemable NCI; acquisition obligation already included in debt | 112.79957208119313 / 255.50456616152965 / 421.6587798603326 | No candidate; source/economic review |
| CRL | Difficult retained case; $6.354M ordinary NCI + $42.537M redeemable NCI + $45M contingent consideration + separate $105M deferred consideration | 21.24746874359052 / 69.79517035219583 / 134.8738002012298 | No candidate; source/economic review |
| ZBH | Excluded from WG17: $8.7M ordinary NCI but no current redeemable NCI; acquisition/legal claims belong to another mechanism | 36.93181676761808 / 77.98514761336149 / 123.17264994856492 | No candidate; implementation gap preserved |

Exact official valuation changes are zero for all three because no successor was
issued or activated. Two private diagnostics explain why a mechanical rewrite
would be unsafe:

- DVA, removing the duplicate $39.463M deduction while retaining the obligation
  inside aggregate debt, mechanically gives
  `113.38441706311262 / 256.10578801472445 / 422.2773221800818`, or
  `+0.5848449819194883 / +0.6012218531948008 / +0.6185423197492241`.
  This is not a candidate because the later $200M Elara transaction lacks a
  cash/debt/share/operating rollforward.
- CRL, treating the separate $105M K.F. Cambodia deferred consideration as an
  additional debt-like claim, mechanically gives
  `19.081895175962753 / 67.61278241407521 / 132.67433474255708`, or
  `-2.165573567627767 / -2.1823879381206126 / -2.1994654586727336`.
  This is not a candidate because cash-flow overlap and the unbounded securities
  and derivative tail remain unresolved.

## Source classification

### DVA

- Controlling 10-Q: accession `0000927066-26-000108`, period `2026-06-30`,
  filed `2026-08-04`; structural SHA-256
  `c48eb46965b58c8a3a7438d34a44332c139180574010031ac0bfdcf4db87ac2b`;
  source-manifest SHA-256
  `183a86fac257aff757501d4fef28e1bc385b69fbeaa4c49a835220a52404ff39`.
- Ordinary NCI is $283.118M and redeemable NCI is $1.561416B. Matching
  fair-value and temporary-equity presentations are aliases; the $225M NCI
  sensitivity is not a carrying claim. Earnings, distributions, acquisitions,
  redemptions and contributions remain duration diagnostics.
- The $39.463M `AcquisitionObligationsAndOtherNotesPayable` carrying value and
  fair-value alias are presented in the debt-instrument table. The filed
  $10.781013B aggregate debt already contains this component, so no second
  acquisition adjustment is permitted.
- $38.54M of acquisition cash is a flow. The $200M Elara equity-method
  investment occurred after the balance-sheet date and requires a complete
  post-event rollforward.
- Preferred value and issued preferred shares are explicitly zero.

### CRL

- Controlling 10-Q: accession `0001100682-26-000118`, period `2026-06-27`,
  filed `2026-08-05`; structural SHA-256
  `efd6c000c0187ff9e03d34274278d907c3d9afb17fc862c54451c228dc024990`;
  source-manifest SHA-256
  `319144a3fcfcf6fb595af2160ede5095c5f9d238c2c33112b1a9fac5f62e19e6`.
- Ordinary NCI is $6.354M and redeemable NCI is $42.537M. The $42.5M current
  redemption value and $47M–$54M range are diagnostics, not exact carrying-
  balance aliases. Earnings, OCI, dividends and accretion are flows.
- Current and noncurrent contingent consideration are $22.5M each. Aggregate,
  Level-3, rollforward and fair-value views reconcile to $45M once.
- K.F. Cambodia deferred consideration is a separate current $105M recorded
  liability. Its effect inside operating cash is not isolated, so its additional
  bridge treatment remains review-only.
- $11.4M paid contingent cash and $467.254M acquisition cash are not added to
  current carrying claims. Disposal receivables and future support maxima remain
  separate asset/event diagnostics.
- The securities class action and two derivative actions have no finite loss
  range, damages reserve, settlement amount, D&O insurance ceiling or recognized
  insurance receivable. Preferred value and issued shares are zero.

### ZBH

- Controlling 10-Q: accession `0001193125-26-335044`, period `2026-06-30`,
  filed `2026-08-05`; structural SHA-256
  `58f7a1427bca8d895badb97f50791ad54d3231b48f13a6ba4f5c490f69706046`;
  source-manifest SHA-256
  `cc10f888eebc1f978ecf4ebfe7543dae9a8e7c5f5c1258466c749422c2ac1d93`.
- Current ordinary NCI is $8.7M. No current redeemable-NCI or temporary-equity
  carrying balance exists, so ZBH does not fit WG17.
- The $244.6M aggregate recurring Level-3 contingent liability, $137.9M legal
  reserve, acquisition components, $720M maximum and $69.2M paid cash remain
  for a different mixed-claim rule.
- China-distributor loss beyond accrual and material tax-audit exposure cannot
  be estimated. No insurance recovery is disclosed.

## Verification evidence

- Frozen source index:
  `output/us-refresh-runtime/source-indexes/3f708765d48cd7c5e24782deae53fc6b4714a3a51c9b7372e2c3e485bfc33ee4.json`,
  file SHA-256 `b696cb36ef36d4e9d7adb021c69d33f3ca94673310eb9c053611c800f4c46a5f`.
- Direct cached-source report:
  `output/us-refresh-runtime/source-validation/fe8bc7f5f6391313bdfa8d48b9f00e84939f5ae9911273bc1573451ad688bf1e/report.json`,
  SHA-256 `fe8bc7f5f6391313bdfa8d48b9f00e84939f5ae9911273bc1573451ad688bf1e`.
  Outcome: DVA and CRL source/economic review; ZBH implementation gap.
- Frozen two-worker group:
  `output/us-refresh-group-verification/fdb10eeb8552f38a1bf9ed6d74d5a226ba05d88759ab7aea76f9fabb9e84b884/report.json`,
  SHA-256 `d6062a505aecfc472a4fc2596f9de47c07f187693a3d31255b592a64eb41c5dc`.
  It reproduced two source/economic reviews and one implementation gap on
  implementation SHA-256
  `9716ec1c11b0d933b247b7cb6721cf75a938197dca719965032954d686056c48`
  and policy SHA-256
  `1be99ee886c5abc88d927b89096346ff752c3fbaa2e5a329f479a808bc3f030d`.
- Focused cross-module regression: 172 passed in 89.17 seconds. It covers WG17
  NCI/contingent rules plus earlier overlap, mixed-claim, acquisition,
  litigation, NCI, preferred, bridge, normalization, compilation/bindings and
  two-worker paths.
- Isolated blocked-group API evidence:
  `output/us-refresh-runtime/blocked-group-api-evidence.json`, SHA-256
  `6807d526d06f5d84529099be432ddff55f84fbeae9cbf0085473d50ab212e1ad`.
  A real FastAPI worker authenticated against the isolated UAT database and
  served exact frozen detail and default-calculator parity for DVA, CRL and ZBH.
  All 440 companies remained present and no candidate catalog was activated.
- Current work register: 440 companies, 419 recipes, 269 compiled contracts,
  150 implementation gaps, zero current-version source-bound results in this
  latest three-company report and zero successive-period proofs. Readiness
  correctly exits 2 at 269/419.
- `git diff --check` passed. No frontend behavior changed, so the browser was
  not mechanically rerun.

Three Luna reviewers independently inspected DVA and CRL at xhigh effort and
ZBH at high effort. The primary agent rechecked their source facts, rejected the
initial false DVA candidate after proving the debt overlap, implemented the
fail-closed current rules and exercised the real API preservation path.

## Remaining blockers

- DVA requires a post-Elara cash/debt/share/operating rollforward. Its $39.463M
  acquisition obligation remains inside aggregate debt and must never be
  deducted twice.
- CRL requires resolution of the $105M deferred-consideration cash-flow overlap
  and finite evidence for the securities/derivative claim and insurance scope.
- ZBH needs a separate ordinary-NCI/acquisition/litigation rule; it is not a
  redeemable-NCI case. China-distributor and tax exposure remain unbounded.
- No company has successive-period proof under the current release candidate.
