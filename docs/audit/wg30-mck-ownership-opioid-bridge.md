# WG30 — MCK ownership and opioid-settlement bridge

Narrow scoped-payment/conditional paired-diagnostic and blocked-update gate
verified 2026-09-16, user confirmation needed; not completed MCK refresh.
WG29 narrow annual-source/blocked-update gate user-confirmed,
not completed LHX reconciliation or pipeline release. MCK only plus LHX control.
No new network acquisition or release action.

## Audit/reference and bounded specification

Reference: actual cached current NCI/redeemable claims, opioid accrual/payment,
cash/cutoff and unrelated acquisition/instrument economics reconciled without
inferred amounts, flow-as-stock, duplicates or double deductions.
Reuse WG26 carrying/alias proof, scoped source selection, deterministic narrative
layer, pure engine/calculator, frozen two-worker flow and isolated API.

| ID | Severity | Verified delta | Acceptance |
|---|---|---|---|
| WG30.1 | P0 | July settlement amount exists but needs scoped reusable cash/liability rule | Source term/fact agree, payment-only asset/liability movement paired |
| WG30.2 | P0 | Post-payment cash is not full post-period state | Explicit unknown other movements; no actual-closing-cash claim |
| WG30.3 | P0 | NCI/preferred/put rights and securities separate | Preserve WG26 carrying proof and all unresolved economic burdens |
| WG30.4 | P0 | Current runtime gate | Real frozen workers, independent challenge, regression and isolated API |

Current MCK 10-Q accession `0000927653-26-000234`, end 2026-06-30,
filed 2026-08-05. Cash $5.164B, related opioid accrual $5.660B ($602M current,
$5.058B noncurrent). Q1 government/state/tribe payments explicitly zero;
July payment $496M explicitly reported. This zero is narrow source evidence,
not a default for missing other-program payments. $243M equity/debt securities
and $92M restricted cash are not new available cash or opioid payments.

Payment-only cash $4.668B and liability $5.164B are conditional arithmetic,
not complete post-July balance observations. Existing recipe cash/securities
$4.911B preserves $243M legacy inclusion; no new liquidity classification approved.
Ordinary/redeemable NCI $376M/$2.563B carrying/alias proof already exists.
Apollo preferred and PRISM/Core Ventures put rights remain separate economics.

## Implemented source-backed narrow rule

`FINSIGHT-SETTLEMENT-PAYMENT-BRIDGE-WG30-1` reuses the hash-bound narrative
parser and WG26 carrying/alias proof. Tagged current opioid accrual aggregate
and current/noncurrent parts reconcile in one case/context; total is not added
to its parts. Cash is the undimensioned USD asset, not restricted cash or
securities. Actual Q1 government/state/tribe zero and July payment bind to their
distinct narrative/tagged periods with exact document/text locators.
SRT litigation axis and issuer member namespaces are independently resolved;
subsequent payment requires the additional GAAP subsequent-event member.
Historical tribal $196M total terms on the same payment concept, $7.9B aggregate
settlement maximum, paid hospital/payor escrow and owner flows are not new cash
payments or balance claims. Narrative payment month is not an invented payment
day or future schedule. All amounts/dates come from incoming hashed evidence.

The paired movement is explicitly conditional dollar-for-dollar accrued-claim
arithmetic, not a reported actual-closing-liability rollforward. Both actual
post-period cash and liability remain None; other movements, financing and
program scope remain unresolved. No PV, claim adjustment or numeric successor.
Current ownership proof does not approve Apollo conversion or PRISM/Core put
rights, and legacy $243M securities inclusion is not new cash-like approval.
Canadian/private nonsettling possible exposure remains unquantifiable, not zero.

## Calculation and runtime receipts

| Company | Retained low / base / high | Exact official changes | Reliability |
|---|---:|---:|---|
| MCK | 477.99247723179093 / 849.8325771275278 / 1262.3562145555925 | 0 / 0 / 0 | Low |
| LHX preservation control | 69.08352051394239 / 152.4724672181145 / 263.63410016487416 | 0 / 0 / 0 | Low |

No unavailable conversion or dropped historic adjustments. LHX preferred/
environmental, MCK complete stack, INTC/JBL leases/cash, portability, HCA/HON and
hardening remain required. Cached filing cutoff is 2026-08-14, not latest live
SEC discovery as of the verification date.

- Current MCK structural SHA-256
  `86ba2d2b34b9acbdbb369fc35f903292eafa6a62a25a7513f930e4798a224afc`;
  raw HTML `ae1dbb2b5240d1316869e75771565769fb61963e9dcf343d2bd1decc34bee502`.
- Narrative receipt `output/us-refresh-runtime/narrative-evidence/MCK.json`,
  file SHA-256 `bb273b8dcb8e3791441709c19067fcfc1337c36c2165eb4413b0558d1420e821`.
- Frozen two-worker report
  `output/us-refresh-group-verification/5101efea85afd341b552681328d4d794b3e2fbd5c93792f4ce4bc6a58468d5dd/report.json`,
  file SHA-256 `cdcdba8ec6d09e67f65bd4deb0785233f4f2e0ffa71120e127e782c7c77981cd`.
  MCK payment ledger and LHX annual ledger execute inside actual workers;
  both main rows stay implementation_gap. Repeated report bytes identical.
- Implementation SHA-256 `ce5cb789a0cfc72b4c8456dee9485be4b4c69a8a208421c3eeea1980beb5e0da`;
  policy SHA-256 `d2435fb5b3cdb1dc052cd701fc0c6d703411ae22aa19dceca23d479d3e465441`.
- Final corrected focused source/scope/engine tests: **54 passed in 18.17s**. Three independent
  engine tests demonstrate equal payment movement preserves each scenario,
  keeping all other claims/shares fixed; synthetic inverse move is not new
  reported balances. Initial tests mistakenly read the evaluator wrapper's
  field as value_per_share instead of value; corrected tests pass. Interrupted
  broad 180-check run is not acceptance; stable broad rerun pending.
- Real isolated PostgreSQL-backed login/list/detail/default calculator parity
  for MCK/LHX/INTC/JBL/HCA/HON, 440 issuers; receipt
  `output/us-refresh-runtime/wg30-blocked-preservation-api-evidence.json`, file
  SHA-256 `7cba107478a2c95a6deba33d7da9b5bbece3fd967af0c8350837ce1bcf3d7456`.
  No user-facing/save/model interaction changed; browser/database-save/activation/
  reload/rollback not repeated or claimed. Final-release acceptance remains open.

Independent source/economic challenge found nearby quarter-date acceptance gap;
primary verified and corrected it using independent reported-quarter EPS periods.
Final independent **24 passed in 4.82s**, no required material correction; explicit
payment-allocation/funding blockers preserved. See [review](wg30-independent-review.md).
Interrupted broad 669-check pre-correction run is not final acceptance.
Final stable current broad regression: **718 passed**, one existing Passlib crypt
deprecation warning, **244.71 seconds**. Command:
`PYTHONPATH=backend:. pytest -q backend/tests/test_refresh_*.py backend/tests/test_calculation_recipe.py backend/tests/test_batch_28_history.py backend/tests/test_batch_26_history.py backend/tests/test_batch_21_history.py backend/tests/test_batch_14_history.py`.
Final frozen repeat and six-company API checks after correction pass. Diff
whitespace check and py_compile pass; HEAD remains
`4fa0a64e7b7a684a87c5732a03fde1680c88d622`. No network, Git mutation, production
activation, scheduling, deployment or new family adapter. Narrow WG30 evidence
verified, user confirmation needed; no economic company-refresh/release completion.

Current rebuilt register 2026-09-16: 440 companies, 419 historical executable
recipes, 282 compiled instructions, 137 implementation gaps, 196 financial
flags, 168 source flags, 436 needs-recheck, zero current full numeric/successive
certifications. Flags overlap; not a completion percentage. No new numeric
company refresh in WG30. Historical/source partial successes not composable.

## Following working group, not started

WG31: MCK subsidiary preferred and redeemable put-right economic scope, using
captured Note 5/related source and WG26/30 evidence. Separate Apollo convertible
preferred from PRISM/Core put rights and ordinary NCI; do not equate parent
preferred zero with absence of subsidiary obligations, or apply subsidiary
ownership percentages to parent shares. Require source-bounded exclusive claim
versus conversion economics and retain gross/net proceeds already in cash.
MCK payment-allocation/funding, full cash/debt/cash-like assets, remaining legal
timing/forecast overlap and all other named gaps stay required. Cached-only;
no later-group work started or new acquisition authorization implied.
