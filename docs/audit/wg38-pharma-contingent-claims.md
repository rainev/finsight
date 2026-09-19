# WG38 — pharmaceutical contingent consideration, CVR maxima and paid cash

Started 2026-09-18 after WG37's narrow result was user-confirmed. Cached evidence
only. This is a source/classification implementation gate, not a completed company
refresh or pipeline release.

## Acceptance status

| Item | Result |
|---|---|
| Shared recognized-liability / ceiling / paid-cash rule | VERIFIED; CONFIRMATION PENDING |
| BIIB difficult legal-overlap case | VERIFIED BLOCKER; CONFIRMATION PENDING |
| GILD carrying liability and maximum/CVR separation | VERIFIED; royalty/cash overlap still blocked |
| INCY carrying liability and post-period cash separation | VERIFIED; current bridge still blocked |
| Frozen two-worker determinism | VERIFIED; CONFIRMATION PENDING |
| Focused/broad regression, independent challenge and isolated API | VERIFIED; CONFIRMATION PENDING |

## Rule implemented

`FINSIGHT-PHARMA-ACQUISITION-CLAIM-WG38-1` uses one reusable economic
framework with distinct ledgers for:

1. recognized current carrying liabilities;
2. aggregate, Level-3, current/noncurrent and typed-location duplicates;
3. contractual milestone maxima and CVR ceilings;
4. acquisition or contingent-consideration cash already paid;
5. litigation, royalty and collaboration obligations; and
6. completed post-period acquisition events.

The rule contains no filing amounts or dates. Identity, accession, cutoff,
period, unit, namespace, member scope and reported precision are validated from
the frozen structural facts. A contractual maximum never becomes a current
liability merely because it appears in XBRL. Cash is adjusted only through a
separate bridge field and never added to the claim.

## Exact company results

### BIIB — retained financial review

- Current noncurrent contingent-consideration carrying total: **$273.5M**.
- Same total under Level 3: **$273.5M**; Level 1/2 are zero.
- Narrower existing balance **$269.4M** plus Apellis purchase addition **$4.1M**
  reconciles to the total and is not additive.
- Genentech judgment **$124.3M** is a separate appealed legal amount, not a
  current balance-sheet carrying liability or paid cash.
- Result: `review_required` for
  `separate_legal_judgment_carrying_scope_unresolved`; no numeric successor.

Historical low/base/high remains
`30.820572961480448 / 122.45052291592471 / 272.12004639095767`.
Exact official valuation change: `0 / 0 / 0`.

### GILD — acquisition subclaim reconciled, full refresh blocked

- MYR business-combination carrying liability: **$60M**, with matching
  aggregate/Level-3 views.
- Ouro asset-acquisition carrying liability: **$277M**.
- Typed current/noncurrent location rows **$143M + $133M = $276M** reconcile to
  the $277M total within their reported million-dollar precision; they are not
  added again.
- Reconciled recognized acquisition subclaim: **$337M**.
- Excluded from the claim: Arcellx CVR ceiling **$300M**, Tubulis maximum
  **$1.9B**, Ouro maximum **$500M**, MYR settlements **$288M**, and acquisition
  cash including **$1.6B** Ouro and **$11.318B** H1 business-acquisition cash.
- Immunomedics future-royalty obligation is separately reported at **$1.1B
  carrying value / $700M fair value**. Its current/noncurrent split and forecast
  cash overlap are unresolved, so WG38 now fails closed at the pharma selector
  with `immunomedics_future_royalty_scope_and_cash_overlap_unresolved`. The
  broader cash, commercial-paper and lease bridge also remains required.

Historical low/base/high remains
`47.814576621348 / 84.83355650735321 / 142.23827451110367`.
Exact official valuation change: `0 / 0 / 0`.

### INCY — acquisition claim and cash adjustment source-bound, full refresh blocked

- Current contingent liability **$38.811M** plus noncurrent **$63.189M** equals
  the **$102M** recurring Level-3/estimated-fair-value aggregate; all are one
  claim.
- H1 contingent cash paid **$9.565M** is not an extra liability.
- Completed Vega post-period cash **$1.25B** is a separate negative cash bridge
  adjustment exactly once.
- Vega contingent maximum **$750M** is an unrecognized ceiling, not a June 30
  liability. Collaboration and licensing maxima remain outside the claim.
- Full refresh remains blocked by unresolved commercial paper, debt,
  securities and NCI bridge fields.

Historical low/base/high remains
`39.53829408784563 / 76.77527520525082 / 142.64357455245997`.
Exact official valuation change: `0 / 0 / 0`.

## Verification evidence

Controlling accessions and structural hashes:

| Company | Accession | Structural SHA256 |
|---|---|---|
| BIIB | `0000875045-26-000075` | `0192005db66f4df7762a6707586217e55e0b6fcc7c6b0b76fc9939df6ab4cdf7` |
| GILD | `0000882095-26-000031` | `0edaddfd2564ae8bf3c19d0103afe8f345de614fcd2b0a076d000232b72c4983` |
| INCY | `0000879169-26-000056` | `0d7dd2588cbcae3870b3c7585dc7df826a07ab3205c6c3c1a617c44d29cbb4f4` |

Frozen two-worker report:
`output/us-refresh-group-verification/681d1199a1c283efdc39097be5ae036c5e637853335f04d1dd1c2dab8c99121d/report.json`.
It deterministically reproduced `source_or_economic_review: 3`; repeated report
file SHA256 `23176297b6a1dd86789544b4783d92b87627a1fcceb4a3f23d22ddc10dffdc96`.
Policy SHA256 `93684eb3e45d6df6f0584d454b77af3e4baea543f49d39330b9aa138084efc80`.

Focused regression: **40 passed**. Broad refresh/Batch-14 regression:
**795 passed**, one existing Passlib `crypt` deprecation warning, 265.53s.
Isolated real API evidence:
`output/us-refresh-runtime/wg38-blocked-preservation-api-evidence.json`, SHA256
`2d19ebd0d66498638a942f24dcaf8ca9c54374a6e7ca9d3e4d14985d58c4c089`.
The API served all 440 baseline records and exact detail/calculator parity for
BIIB, GILD, INCY and the retained HON/HCA/MCK/LHX/INTC/JBL blockers. No
candidate was activated and production was not touched. Browser/save checks
were not repeated because no public model, UI or persistence behavior changed.

The independent Luna High review confirmed the three filings support one
role-based framework, not one identical CVR formula. It independently confirmed
the $273.5M BIIB blocked claim, $337M GILD acquisition subclaim plus unresolved
$1.1B/$700M royalty scope, and $102M INCY claim plus -$1.25B cash adjustment.
It found two fail-closed defects: unsupported nonzero dimensions were ignored and
GILD's royalty scope did not block. Both are corrected and directly tested;
final reviewer readback passed **10 checks with 2 deselected** and found no
remaining material WG38 defect. See [independent review](wg38-independent-review.md).

## Counts and boundary

Compilation moved from **282 to 285 instructions** and coding gaps from **137 to
134**. Current generated register: 440 companies, 419 recipes, 285 compiled,
134 coding gaps, 199 financial flags, 171 source flags, 437 needing recheck, 21
prior unavailable, zero current-version full numeric source-bound and zero
successive-period proofs. Flag counts overlap and the accumulated source reports
are not composable release evidence.

All HON, HCA, MCK, LHX, lease, portability and hardening requirements remain.
Batches 01–44 only. No network acquisition, paid source, parameter tuning,
family adapter, production activation, scheduling, merge, push or deployment.

## Following group, not started

The highest-reuse next bounded problem is the pharmaceutical current bridge and
royalty-cash overlap exposed by GILD and INCY. It must prove cash/securities,
commercial paper/debt/leases, NCI/absence and royalty operating overlap from
current sources without converting missing bridge components to zero.
