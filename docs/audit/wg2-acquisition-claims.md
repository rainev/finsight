# WG2 acquisition and contingent-payment claim result

Verified 2026-09-09; user confirmation pending. Scope is Batches 01–44 only.
Production, scheduling, merge, push and deployment were untouched.

| Company | Current claim result | Full refresh result | Reason |
|---|---:|---|---|
| CTSH | $25M source-bound | Source-bound candidate | Matching current aggregate and Level-3 views are one liability; acquisition-date maximum is not added. |
| VRT | $222.5M source-bound | Source-bound candidate | Issuer current total equals aggregate and Level-3 derivative views; $206.1M/$12.1M slices and the $62M noncash change are not added. |
| VRTX | $79.6M source-bound | Review | The claim is distinct from the pending $10B Crinetics transaction and later financing; current financing-flow normalization remains incomplete. |
| LLY | $2.518B June claim source-bound | Review | $814M current + $1.704B noncurrent Level-3 components; the separate July $2B cash event is not machine-bound and transaction maxima/prices are excluded. |
| REGN | $67.2M duration accrual retained diagnostically | Review | The H1 noncash disclosure is not an instant balance; overlap with accrued liabilities, $99.9M investing cash and OCF remains unresolved. |

Frozen group:
`output/us-refresh-group-verification/9cf4cebb528b7543796dd6718c5f8a96d2818e43fa2dc4bb1bbf6cad1f73ff69/report.json`
(report SHA-256 `be483a269c7e39bd35b47eea8a87cadc5c8909eb7941b4f29f723f4ec6f243d8`,
implementation `a0d0dd1a53bc949ef49451dca28e280405e4ff0f791eca7205f04b0c6fb8c39b`,
policy `36c57f2d53e4209d75bd65527f36f7d49b947aeb15c06f41a3ee9e441141f097`).

Exact public-candidate changes:

- CTSH: `47.55004760434793 / 78.25181585482817 / 109.15870682135167`
  to `47.0516194323946 / 75.66345322748494 / 103.08156677066385`.
- VRT: `22.52775016549566 / 89.3468249295978 / 167.22306274092608`
  to `22.469992316948076 / 89.06426945554773 / 163.49926241373018`.

The carrying claims are reclassified from the legacy preferred slot to one
negative nonoperating adjustment, so that move has no net value effect. Candidate
changes come from locking one current reported share denominator in all scenarios.
CTSH additionally reconstructs current revenue, OCF, capex and interest from exact
annual + current YTD − comparative YTD filing evidence.

Real API evidence:
`output/us-refresh-operational-uat-20260909-wg2-vrt/uat-report.json` served VRT
baseline → candidate → rollback exactly, reloaded without restart, rejected a
stale compare-and-swap, preserved 440 entries/419 recipes and reports
`production_runtime_touched:false`.
