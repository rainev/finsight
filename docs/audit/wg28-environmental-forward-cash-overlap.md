# WG28 — environmental reserve/recovery forward-cash overlap

Narrow source-ledger/blocked-update gate verified and user-confirmed,
2026-09-16. Full environmental forward-cash reconciliation is not done yet.
WG27 narrow accounting/safety gate user-confirmed,
not a completed LHX refresh or release. LHX first; MCK preservation control.

## Reference/current delta/reuse

Reference: inspect current/annual source cash, reserves, recoveries/timing and
forecast overlap. No missing-payment zero, automatic net $175M claim, recovery
surplus cash, duplicate obligation, dropped preferred/environmental claim.

Verified current Note R: reported estimated liability $660M/$659M and recoverable
assets $485M/$483M at July 3/January 2, 2026. Recoveries are probable via future
government contract pricing; current/noncurrent portions are described without
amount/timing schedule. Sites/share of PRP costs also carry unresolved scope.
Recent annual companyfacts contain total cash-flow inputs but not matched
environmental payments/recoveries or current same-program annual history.
Historic pre-Aerojet values cannot substitute for that scope. Cached source
inventory and independent annual-evidence challenge completed; no network retrieval.
The liability is gross relative to the separate recovery asset, not independently
proven to be undiscounted or present value by the current source concept.

Reuse hashed narrative parser, scoped GAAP/issuer fact selection, existing history
and claim engines, frozen workers and source verifier. Do not reuse a cash-
insurance-receivable netting rule for future contract-pricing recoveries.

| ID | Severity | Verified gap | Acceptance |
|---|---|---|---|
| WG28.1 | P0 | Current gross/recovery facts need matched source/period/mechanism proof | Exact Note R and dimensional context identity |
| WG28.2 | P0 | Payment/timing/forecast overlap not captured | Versioned ledger with unknowns, no inferred zero or automatic reserve |
| WG28.3 | P0 | Preserve reported CF/legacy claims while rule incomplete | Unchanged exact history/recipe/API and named required blockers |
| WG28.4 | P0 | Runtime current gate | Real frozen two-worker, independent challenge and stable regression |

No full economic reserve until timing and source cash overlap are supported.
The related $175M book difference is only a diagnostic, not PV/current debt or
forecast cash. Changes $1M liability/$2M recovery do not prove settlements.
Preserve unresolved preferred basis, MCK, lease, portability, HCA/HON/hardening.

## Implemented narrow ledger and real source result

`FINSIGHT-ENVIRONMENTAL-FORWARD-SCOPE-WG28-1` keeps source balances separate
from forward cash claims. The existing LHX hash-bound narrative envelope adds
Note R contract-pricing recovery, undetermined PRP share and current/noncurrent
presentation terms; Note B preferred terms are unchanged in value. Source
metadata/version is explicit, no amount/date baked into economic rule tables.

- Current $660M/$485M source facts share current context, issuer CIK, USD,
  environmental axis/member and Loss Contingencies presentation. Comparative
  $659M/$483M belongs to January 2 in the same current filing, not a newly
  acquired annual filing. Different programs/contexts cannot be silently netted.
- Related $175M is explicitly a book difference, not PV, reserve deduction or
  surplus cash. Missing/conflicting/wrong-scope balances fail closed.
- Cash payments, recovery timing, payment schedule, forecast overlap, claim
  adjustment and PV remain unknown/None. Neither the $1M/$2M stock movement
  nor missing cash-concept tags supply payment cash. No new addback/deduction.
- Five reported annual total OCF observations remain inventory only, not a
  new normalization policy or an environmental payment allocation. The retained
  approved three-year baseline and all negative observations/inputs are unchanged.
  Selected payment-concept candidates are discovery cues, not source-binding
  evidence or proof that no payments occurred.
- Captured companyfacts environmental balances stop at older/pre-Aerojet scope
  for annual rows; more recent 2023 comparative/quarter rows are not current
  same-program annual cash history. No matching recent annual environmental
  payment/recovery scope or exact timed schedule captured in the inspected data.

Full LHX implementation remains `implementation_gap`, with partial environmental
ledger `related_balances_verified_forward_cash_review`, not a numeric successor.
Preferred economic basis and $660M legacy environmental deduction are preserved
pending full overlap reconciliation. MCK is control only; no shared legal rule
or new valuation introduced. All 419 historical recipes remain executable.

## Exact historical results

| Company | Retained low / base / high | Official changes | Reliability |
|---|---:|---:|---|
| LHX | 69.08352051394239 / 152.4724672181145 / 263.63410016487416 | 0.0 / 0.0 / 0.0 | Low |
| MCK control | 477.99247723179093 / 849.8325771275278 / 1262.3562145555925 | 0.0 / 0.0 / 0.0 | Low |

No unavailable conversion, source-derived payment zero, $175M PV, recovery cash
benefit or dropped reserve. Eligible cached evidence cutoff remains `2026-08-14`,
not latest live discovery as of verification 2026-09-16. No retrieval was performed.

## Runtime evidence

- Direct current source report:
  `output/us-refresh-runtime/source-validation/6fe99115fe75da8f96dd04590925dfd33b30c1d13ded64b9b9c0f01d997e4868/report.json`.
- Frozen two-worker report:
  `output/us-refresh-group-verification/94cfbe75ed48ff9cc15ed4b9bdde0407832d14b1e0bc368ee614e4c6bfc19e24/report.json`,
  file SHA-256 `f00eed4df68833a37f5d40b3e2b5b3727f28f5f081cd90171324df6f33347244`.
  Both main implementation gaps remain; LHX current environmental ledger actually
  executes inside frozen worker. Repeated current report is byte-identical.
- Narrative input `output/us-refresh-runtime/narrative-evidence/LHX.json`, file
  SHA-256 `794e03657f162b11187f68864e3d854eeb8aa9b2ef59762e99a5c2f3e8dfeda1`.
- Focused source/environment/preferred checks: **30 passed in 6.07 seconds**.
  Original frozen test failed because tuple policy fields became JSON lists;
  canonical JSON identity comparison fixed serialization without weakening
  identity/version validation. Failure is not counted as economic verification.
- Stable current full regression: **670 passed**, one existing Passlib `crypt`
  deprecation warning, in **219.45 seconds**. Command:
  `PYTHONPATH=backend:. pytest -q backend/tests/test_refresh_*.py backend/tests/test_calculation_recipe.py backend/tests/test_batch_28_history.py backend/tests/test_batch_26_history.py backend/tests/test_batch_21_history.py backend/tests/test_batch_14_history.py`.
- Real isolated PostgreSQL-backed login/list/detail/default-calculator parity:
  `output/us-refresh-runtime/wg28-blocked-preservation-api-evidence.json`, file
  SHA-256 `631ff18abe83dfb0cb2838dd7ad3d3cbce23029b136386255d74388fcebd2cf2`.
  440 baseline companies; exact six-name parity LHX/MCK/INTC/JBL/HCA/HON. No UI/
  save or official model interaction change, so browser/save/activation/reload/
  rollback not repeated or claimed; required final release gates remain open.

Current implementation SHA-256
`573c4a76e84e9f9b0e370656c04c1abb76be9551aa6a7789a81e99d9cd2454b0`;
policy SHA-256 `7dde7266929169a713d125325a3c91d36495e459da7ce4f6709175ea25e44a7c`.
Independent read-only Luna High source/economic challenge completed, with 12
focused checks passing and no required current code correction. Primary rechecked
material source/period, cache inventory and economic findings firsthand. See
[independent review](wg28-independent-review.md). No passing-test-only claim of
economic completeness.

## Required evidence and next bounded step

Recent annual raw HTML/XBRL packages are **not captured**, not proven unreported.
The submissions manifest lists annual accession `0000202058-26-000015`, filed
2026-02-12, document `hrs-20260102.htm`, and `0000202058-25-000023`, filed
2025-02-14, document `hrs-20250103.htm`. Repo-wide cache inventory found neither
package/document; indexed structural copies are the current 10-Q only.
Companyfacts and the current filing's January comparative do not replace them.

Next useful work is bounded acquisition of those annual public SEC packages,
latest first, followed by Note R payment/recovery/scope and OCF/revenue overlap
reconciliation. This requires explicit network acquisition authorization under
finsight-efficiency; no download was performed or later group started here.
Do not promise the annuals disclose enough to close the economic gap.

## Current register, 2026-09-16

440 companies; 419 historical executable recipes; 282 compiled instructions;
137 implementation gaps; 196 financial-review flags; 168 source-gap flags;
436 requiring current-version rechecking. Flags overlap, not completion counts.
Zero current full numeric source-bound or successive-period certifications in
the rebuilt register. Prior partial successes cannot be added into release
readiness. No new numeric candidate in WG28; all prior named gaps remain required.
