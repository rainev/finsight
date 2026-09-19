# WG39 — pharmaceutical current bridge and royalty-cash overlap

2026-09-19 qualification: the [cross-cutting evidence audit](wg-truth-and-launch-handoff-20260919.md)
found that GILD/INCY refresh normalization reintroduced current TTM observations
excluded by their retained Batch14 rules. The numerical receipts below remain
reproducible historical evidence, but candidate substitution requires targeted
normalization review. The royalty repayment equality is a reconciliation, not
standalone proof excluding every other liability movement. User approval remains
recorded; these newly identified issues must be disclosed before publication.

Started 2026-09-18 after WG38's narrow result was user-confirmed. Cached evidence
only, Batches 01–44. This is a verified candidate gate, not production activation
or pipeline release.

## Acceptance status

| Item | Result |
|---|---|
| GILD cash/debt/NCI/preferred bridge | VERIFIED CANDIDATE; CONFIRMATION PENDING |
| GILD Immunomedics royalty/debt/cash overlap | VERIFIED CANDIDATE; CONFIRMATION PENDING |
| INCY cash/securities/debt/NCI/preferred bridge | VERIFIED CANDIDATE; CONFIRMATION PENDING |
| INCY claim, Vega cash and structural TTM reconciliation | VERIFIED CANDIDATE; CONFIRMATION PENDING |
| Frozen two-worker determinism | VERIFIED; CONFIRMATION PENDING |
| Independent challenge, focused/broad regression | VERIFIED; CONFIRMATION PENDING |
| Real isolated API/calculator activation, reload and rollback | VERIFIED; CONFIRMATION PENDING |

## Reusable rule

`FINSIGHT-PHARMA-BRIDGE-WG39-1` binds one period-aligned bridge without filing
amounts or dates in policy:

- cash and current/noncurrent cash-like securities;
- complete current/noncurrent debt and finance-lease scope;
- ordinary NCI or source-proven absence;
- preferred value/absence;
- acquisition claims kept outside debt unless the debt note proves overlap;
- dated post-period cash projected exactly once; and
- strategic equity investments excluded from cash-like securities.

Every fact is reselected from the controlling hashed structural filing. Unknown
nonzero debt, investment or ownership rows fail closed.

## GILD result

Controlling filing `0000882095-26-000031`, period `2026-06-30`, filed
`2026-08-06`; raw structural SHA256
`0edaddfd2564ae8bf3c19d0103afe8f345de614fcd2b0a076d000232b72c4983`.

Current bridge:

| Component | Amount |
|---|---:|
| Cash | $3.179B |
| Current / noncurrent marketable securities | $0 / $0 |
| Current / noncurrent debt | $2.414B / $23.832B |
| Total debt | $26.246B |
| Reported NCI / valuation NCI | $(84)M / $0 |
| Preferred | $0 |
| WG38 acquisition claim | $337M |

`$2.414B + $23.832B = $26.246B`; the total is counted once. The negative NCI
is retained in evidence but never credited to common equity.

Immunomedics royalty reconciliation:

- debt-note royalty component: $1.077B;
- rounded carrying disclosure: $1.1B;
- fair-value diagnostic: $700M;
- senior debt/term loans: $25.168B; and
- $25.168B + $1.077B = $26.245B, reconciling to $26.246B within reported
  precision.

The royalty principal is proven inside financing cash: prior royalty component
$1.110B less current $1.077B = $33M; matured March note $2.750B less zero =
$2.750B; `33M + 2.750B = 2.783B` reported debt repayments. The prior rows remain
in `royalty_cash_reconciliation_sources`; current `FieldAvailability` lineage
correctly remains limited to the current snapshot. The $1.1B carrying and $700M
fair value are not extra claims. The $288M MYR payment remains separate.

The historical recipe already used $26.246B total debt. WG39 source-binds that
choice and prevents future double counting; the valuation change comes from
reclassifying scenario claims, refreshing cash conversion, and locking current
shares—not from changing total debt.

| Range | Historical | WG39 candidate | Exact change |
|---|---:|---:|---:|
| Low | 47.814576621348 | 50.84725647933317 | +3.0326798579851655 |
| Base | 84.83355650735321 | 90.53884458037521 | +5.705288073022004 |
| High | 142.23827451110367 | 155.4654607530073 | +13.227186241903638 |

Reliability remains **Low**. The gross-interest adjustment remains an accrual
proxy; cash interest paid is not separately proven.

## INCY result

Controlling filing `0000879169-26-000056`, period `2026-06-30`, filed
`2026-07-28`; raw structural SHA256
`0d7dd2588cbcae3870b3c7585dc7df826a07ab3205c6c3c1a617c44d29cbb4f4`.

Current bridge:

| Component | Amount |
|---|---:|
| Unrestricted cash | $3.982375B |
| Current AFS debt securities | $553.365M |
| Strategic noncurrent equity investments excluded from cash | $104.387M |
| Current / noncurrent finance leases | $4.259M / $28.420M |
| Revolving-credit borrowing | $0 |
| NCI / preferred | $0 / $0 |
| ARIAD/Takeda acquisition claim | $102M |
| Completed Vega cash adjustment | $(1.25)B |
| Vega contingent ceiling excluded | $750M |

The current AFS line and duplicate aggregate agree at $553.365M; its maturity
schedule $205.695M + $347.670M also reconciles. The $104.387M strategic equity
investment hierarchy is excluded from cash, not converted to zero. Finance-
lease debt is $32.679M. Assets $7.872647B equal liabilities $1.528220B plus
parent equity $6.344427B with no nonzero outside ownership claim, proving NCI
zero.

Companyfacts lagged the controlling Q2 filing. Structural current/comparative
YTD plus the annual fact reconstruct TTM flows. Interest is exactly FY2025
$2.428M + H1 2026 $1.151M − H1 2025 $1.254M = **$2.325M**; missing current
Companyfacts is never treated as zero.

Period-end cash and securities total $4.535740B; after the completed July Vega
payment, valuation cash is $3.285740B. The bridge checker projects the same dated
cash adjustment before comparing model and source, preventing a false mismatch.

| Range | Historical | WG39 candidate | Exact change |
|---|---:|---:|---:|
| Low | 39.53829408784563 | 49.655920876512866 | +10.117626788667238 |
| Base | 76.77527520525082 | 96.2418217177929 | +19.46654651254208 |
| High | 142.64357455245997 | 150.63899303483984 | +7.9954184823798755 |

Reliability remains **Low**. The historical bear/base Vega-maximum deductions
are removed; current structural cash history and locked current shares are also
recalculated independently.

## Verification

Frozen two-worker report:
`output/us-refresh-group-verification/da0b9d353851a341ea9d88171952c1587d7cb0391f4725a83afea5a011ba6808/report.json`.
It produced two `cached_source_bound` candidates and repeated byte-identically;
file SHA256 `94b0a675031f1a2100b2cba142b599a7bdb0d31b6e76a5b1a7aa7427bf0d0d59`.
Policy SHA256 `3d4a9bbd99b655d243f3f62f55b13a71a3b285d600b1b8f54f8612f7ab630632`.

Direct source-validation report:
`output/us-refresh-runtime/source-validation/d0b03fd4ebf477718558789dc4d5ca30dd7444d2a8992b110f9c770c3577e9a7/report.json`,
SHA256 equal to its directory/report identifier.

- Primary focused suite: **138 passed**, one existing Passlib `crypt` warning.
- Independent Luna High challenge: **197 passed** and final mechanical PASS after
  primary corrected the reviewer's interest trace to the actual $2.325M TTM.
- Broad refresh/Batch-14 suite: **803 passed**, one existing warning, 272.10s.

Real isolated operational UAT:

- GILD report `output/us-refresh-operational-uat-wg39-gild-final2-20260918/uat-report.json`,
  SHA256 `b1ce6c7bc6610d8be880ad0c0a70323b7c058ca84c3f6e1490a4e29872a0261d`.
- INCY report `output/us-refresh-operational-uat-wg39-incy-final-20260918/uat-report.json`,
  SHA256 `c84dd1558571d85896d7733140e33467aec3fd79eacccdfec38640ef9c35fa9c`.

Each used the real FastAPI process and existing isolated PostgreSQL UAT database,
served the candidate through detail and default calculator with exact parity,
activated atomically, reloaded the worker, preserved a pinned reader, rejected a
stale CAS activation, and rolled back exactly to the historical range. Production
runtime was not touched. No UI/save behavior changed, so browser and saved-run
checks were not repeated.

## Counts and boundary

Current generated register: 440 companies, 419 recipes, 285 compiled, 134 coding
gaps, 197 financial flags, 169 source flags, 438 needing recheck, 21 prior
unavailable, **2 current-version source-bound candidates**, and zero successive-
period proofs. Flags overlap and 369 accumulated source reports remain
non-composable release evidence.

Both candidates are Low/review-required and remain unactivated. Cached source
binding does not prove full-universe release readiness or live future acquisition.
BIIB and all HON, HCA, MCK, LHX, lease, portability and hardening requirements
remain. No network, paid source, parameter tuning, family adapter, production
activation, scheduling, merge, push or deployment occurred.

## Following group, not started

The next bounded pharmaceutical special situation is BIIB's appealed Genentech
judgment and post-Apellis operating-cash comparability. Its legal carrying scope
and partial-period acquisition history must be solved separately; neither GILD
nor INCY's rule can be forced onto it.
