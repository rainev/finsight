# WG6 unclassified ownership claims versus operating reserves

Verified and user-confirmed 2026-09-09. This is a partial working-group
result, not release approval. Production, scheduling, merge, push and deployment
were untouched.

## Shared rule

A legacy non-debt-claim slot does not establish one economic mechanism. Current
reported NCI and redeemable NCI are outside-owner claims and enter the enterprise-
to-common bridge once. Pension, postemployment, restructuring and environmental
reserves remain separate operating or finite-payment questions until their cash-
flow overlap and payment scope are proven. A negative NCI balance is retained as
a diagnostic; it is not inverted into an asset for common shareholders.

The rule is versioned and contains no filing amount, accession or date. It binds
the selected current filing by issuer, period, unit, context, namespace and exact
component scope, and fails closed if an excluded nonpositive NCI component becomes
a positive outside-owner claim.

## Company results

| Company | Source classification | Result | Previous low / base / high | Current low / base / high |
|---|---|---|---|---|
| NUE | $1.157B direct NCI; $7.099B complete debt | Source-bound representative | 10.145541923817701 / 121.8011652366488 / 338.78105649606704 | 10.297725052674966 / 121.8011652366488 / 333.699340648626 |
| STLD | $143.259M redeemable NCI; $(199.720)M negative nonredeemable NCI diagnostic | Source-bound difficult case | 0.5751620187990207 / 49.46559171931485 / 208.35899065262876 | 4.9612460718897475 / 61.6698137139049 / 184.85358688797865 |
| AVY | $19.4M restructuring reserve; $9.4M environmental accrual; $2.2M acquisition consideration | Implementation gap: operating-cash overlap not complete | 46.46777035487608 / 113.022742883164 / 184.81468988181297 | No candidate |
| BALL | $20M NCI plus $176M pension and $75M postemployment; separate $25M environmental accrual | Implementation gap: mixed ownership/operating scope | 4.782217303771855 / 21.26908781162332 / 40.347306289310076 | No candidate |
| MPC | $6.643B NCI; $1.288B pension/postretirement and $368M environmental reserve in bear case | Implementation gap: reserve timing and OCF overlap | 114.70110782714586 / 260.6138117576469 / 420.161792576826 | No candidate |

For NUE, moving the same $1.157B from the legacy preferred slot to NCI is
economically neutral. Its low/high changes come from replacing scenario-varying
share denominators with the current reported 226,875,676 shares; the base is
unchanged. For STLD, the same $143.259M claim reclassification is neutral. Its
larger movement comes from current history-normalized cash FCFF and the current
143,887,088-share denominator; no negative NCI asset was added.

## Verification evidence

- Frozen two-worker group:
  `output/us-refresh-group-verification/f87b3f1adce5ee910a4f75dd63c8ed44bca293deab23c279e34ce3412a02b8bf/report.json`.
  Report SHA-256 `847fed92b114e7b5b9ddbdbfa72484190416071eaa27132e4f2097df734c08c1`;
  implementation `f933fddd4480d314054eac540d3d464111439bd82934bfb10a17de509fab3a7a`;
  policy `1b02b7ca244bebc7f20ab14a7cb1b1e332fe78641f9fa8fd46f646e322d1c508`.
- Group result: two cached source-bound candidates and three exact implementation
  gaps. Preparation 0.70s, source processing 1.29s, calculation 4.28s and public
  verification 0.002s.
- Focused regression: 118 passed. NCI/bridge/financial subset: 62 passed. The
  source-specific two-company command returned two cached source-bound results.
- NUE isolated UAT:
  `output/us-refresh-operational-uat-20260909-wg6-nue-b/uat-report.json`.
  STLD isolated UAT:
  `output/us-refresh-operational-uat-20260909-wg6-stld/uat-report.json`.
  Both exercised a real FastAPI worker, isolated catalog/database activation,
  worker reload, stale-CAS rejection and rollback while preserving 440 registry
  entries and 419 private recipes.
- The UAT harness was corrected to compare the complete scenario range rather
  than demanding an artificial base-value change. NUE then proved the valid
  unchanged-base case.
- Current work register: 250 compiled contracts, 169 implementation gaps, 2
  current-policy source-bound results, 78 unclassified flags and 0 successive-
  period proofs. These states are not a completion percentage.
- The real stage command exits 2 at the 250/419 migration gate. No production
  active pointer exists.

## Remaining blockers

AVY needs a single source-backed decision on whether the ending restructuring,
environmental and acquisition balances overlap operating cash flow or require a
separate timed claim. BALL needs disjoint NCI, pension/postemployment and
environmental treatment. MPC needs payment timing and OCF-overlap support before
its bear-only $1.656B operating-reserve stress can become a reusable rule. None
was set to zero, made unavailable or counted complete.
