# WG7 operating reserves and benefit-liability overlap

Verified and user-confirmed 2026-09-09. This is a partial working-group
result, not release approval. Production, scheduling, merge, push, deployment
and the family-adapter phase were untouched.

## Reusable rule

The versioned `FINSIGHT-OPERATING-CLAIM-1` contract separates ownership claims,
benefit funded-status liabilities, restructuring/environmental reserves,
recognized recoveries, cash payments, noncash OCF movements, compensation
liabilities and acquisition consideration. It contains no amount, filing date or
accession. Current issuer, accession, period, unit, context, namespace,
dimensions and presentation scope are validated at runtime.

Ending balances are never added to charges, current portions, payments or
noncash movements. Aggregate benefit facts must reconcile to disjoint components.
Operating stresses remain scenario overlays and are not relabeled debt or present
values. Missing timing and same-scope recovery support remain explicit review.

## Company results

| Company | Mechanism result | Full result | Previous low / base / high | Current low / base / high |
|---|---|---|---|---|
| MPC | $6.643B NCI separate; $1.656B gross pension/environmental stress in bear only; $4M recovery not netted | Source-bound difficult candidate | 114.70110782714586 / 260.6138117576469 / 420.161792576826 | 100.98881790732223 / 301.20243208445146 / 459.7235121981297 |
| BALL | $251M pension/retiree-medical claim and $20M NCI reconcile; flows and operating liabilities excluded | Claim source-bound; full calculation review | 4.782217303771855 / 21.26908781162332 / 40.347306289310076 | No candidate: current cash-FCFF scenario is non-positive |
| AVY | $19.4M restructuring, $9.4M environmental and $2.2M acquisition balances separated from $26M/$1.2M payments and noncash movements | Economic/source review | 46.46777035487608 / 113.022742883164 / 184.81468988181297 | No candidate: forward-cash overlap and zero-NCI scope are unresolved |

MPC's ownership/stress reclassification itself preserves the historical claim
arithmetic: the bear still deducts $6.643B plus $1.656B and base/bull still deduct
$6.643B. The candidate movement comes from current history-normalized cash FCFF
and the current 280,824,763-share denominator. Cash FCFF changes from
$8.870737695B / $10.504303217B / $12.026474637B to
$8.322687679B / $11.641169106B / $12.993097193B.

## Verification evidence

- Frozen two-worker group:
  `output/us-refresh-group-verification/0422da0c4e440b9af32f1a640d1b3edc2d1dac9330d7f611d8c224c507f91640/report.json`.
  File SHA-256 `7b8321e3f959228fe63a91568a45e0eea156046cf21fb742568334f81230d7d9`;
  implementation `3fc8af3d85db41be256a85989d97ed523eb93a26d8ea78e5a036715822b02a0a`;
  policy `ce8d3b9636cc69e7ec902da4644a6d64363f034fcd8074523b50e3661013a2e6`.
- Group result: one cached source-bound candidate and two exact reviews.
  Preparation 0.70s, source processing 2.51s, calculation 7.14s and public
  verification 0.001s.
- Source-specific command:
  `output/us-refresh-runtime/source-validation/d656b5ea86a1a22f7044cb3a442d061638e9aab06575c3adc6f542d46e91567e/report.json`.
- Focused regression: 137 passed. The narrower operating-claim/bridge/binding
  suite passed 76 tests.
- MPC isolated real API/database UAT:
  `output/us-refresh-operational-uat-20260909-wg7-mpc/uat-report.json`. A real
  FastAPI worker served predecessor, candidate and rollback values; reloaded the
  candidate without restart; rejected stale CAS; and retained 440 registry rows
  and 419 private recipes. `production_runtime_touched` is false.
- The deterministic work register reproduced SHA-256
  `976aca8d0f8b4f8eecaf96be84a3d34e3ecbc278e84ec093979f204ae28f2f21`.
  After removing a keyword false-positive, the final unclassified count is 74:
  three WG7 companies moved to explicit mechanisms and RVTY's existing retained
  restructuring text is now represented as an operating-reserve classification.
- Current status: 253 compiled contracts, 166 implementation gaps, 1 current-
  policy source-bound result and 0 successive-period proofs. The real stage
  command exits 2 at 253/419; no production active pointer exists.

## Remaining blockers

AVY needs a source-supported forward-cash treatment that resolves its ending
restructuring/environmental reserves and current acquisition consideration
without repeating charges or paid cash, plus evidence-backed zero-NCI scope
because the filing has no direct NCI fact. BALL's claim scope is complete, but its
current normalized cash-FCFF scenario is non-positive and must be solved as a
financial-normalization issue, not bypassed in claim logic. MPC still lacks
timing for a finite PV reserve and same-scope support for netting the $4M recovery;
the current policy therefore keeps the gross amount as a bear stress only.
