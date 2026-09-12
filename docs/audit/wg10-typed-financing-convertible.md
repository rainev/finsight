# WG10 typed financing dimensions and convertible claims

Verified 2026-09-09; user confirmation pending. This is a partial working-group
result, not release approval. Production, scheduling, merge, push, deployment
and the family-adapter phase were untouched.

## Parser and policy changes

Structural facts now preserve typed dimension evidence as
`axis / typed-domain / canonical-member-value` while retaining the old
`axis / typed` dimensions marker. Old cached artifacts remain readable. Parser
definition hashes change, new immutable parses receive new cache/index identities,
and source selection prefers a current-parser, fully dated structural record over
an older equally identified parse.

The versioned KDP policy uses typed semantics, not context ids or amounts. It
also binds preferred equity as a claim rather than conversion dilution, and
source-selects the pro-forma revenue and integration range from the current
filing. MCHP's versioned convertible policy fails closed until its narrative-only
conversion date/range is machine-bound.

## Company results

| Company | Result | Previous low / base / high | Current low / base / high |
|---|---|---|---|
| KDP | Source-bound difficult case | 0 / 7.484190074942197 / 44.5292634704103 | 0 / 5.686990692870578 / 22.368865967695047 |
| MCHP | Source/economic review | 3.0508679571950985 / 17.758157215797535 / 46.424128171930924 | No candidate |

KDP's non-debt claims become $10.716B / $10.559B / $10.234B including $4.196B
NCI. The special portion contains the preferred carrying/liquidation claim,
$898M mandatory redemption, $320M typed structured financing, $402M deferred
consideration and $400M/$325M/$0 integration stress. The $1.779B accounts-payable
supplier-finance portion remains operating. $16.615B paid acquisition cash and
$314M inventory step-up are not deducted again.

The candidate movement also reflects current cash-conversion margins and the
current 1,365,126,038-share denominator. The high case falls materially because
the refreshed history produces a 14.39% high cash margin rather than the prior
19.94%; this is not caused solely by the additional $1.620B claims.

MCHP retains its existing dividend-PV/conversion-dilution valuation privately,
but its future conversion date/rates remain unexecutable from current structured
evidence. No liquidation preference was added and no existing claim was dropped.

## Verification evidence

- Real offline KDP reparse:
  `output/wg10-kdp-typed-structural-20260909/KDP/structural-filing.json`, SHA-256
  `9094f4c491ecc0962987196ff086f0cf061bce8ab55f9fba6f6fd93449811ccc`.
  It reports c-475 as `us-gaap:AccountsPayableCurrent` and c-477 as
  `ns_765b64f84f:StructuredPayablesCurrent` in `typed_dimensions`.
- Source index:
  `output/us-refresh-runtime/source-indexes/3f708765d48cd7c5e24782deae53fc6b4714a3a51c9b7372e2c3e485bfc33ee4.json`,
  1,041 packet directories, 982 structural files and 2,023 entries; no network.
- Frozen two-worker group:
  `output/us-refresh-group-verification/d18829f116ac4ee15a8acdf2b8574e113550152339dfbb10232086bcd1df567b/report.json`.
  File SHA-256 `f8f152265e809e376fd1f30e35aee4c8eb1af8cd41b0165c0fb05c698c4eaddf`;
  implementation `735a38d739f5213c39e72b7da49d3532bfa929df4099069f111d59f317496a4d`;
  policy `0559fed3c3ae7979bbc169836b797c9578e16c3b2ec6ebb0eebde12fea153612`.
  Result: one cached source-bound candidate and one exact source/economic review.
  Preparation 0.70s, source processing 1.47s, calculation 3.35s and public
  verification 0.001s.
- Source-specific evidence:
  `output/us-refresh-runtime/source-validation/e4d5e7a34f138a89c0a459524f16360399d12c8189a7a893826370d512b254c6/report.json`.
- Focused regression: 289 passed. The final typed/claims/bridge subset passed 141
  tests.
- KDP isolated real API/database UAT:
  `output/us-refresh-operational-uat-20260909-wg10-kdp/uat-report.json`. A real
  FastAPI worker served predecessor, candidate and rollback values, reloaded
  without restart, rejected stale CAS and preserved 440 registry rows plus 419
  private recipes.
- Work-register JSON reproduced SHA-256
  `65cc303635fae1696912c51d26efb17b9f095b0081e22fdd2c8b3434bede1ce5`.
  Current status: 258 compiled contracts, 161 implementation gaps, 1 current-
  policy source-bound result, 70 unclassified flags and 0 successive-period
  proofs. The real stage command remains blocked at 258/419 and no production
  pointer exists.

## Remaining blockers

MCHP needs deterministic extraction of its mandatory conversion date and
conversion-rate range from current hashed filing narrative before the existing
dividend-PV and conversion-share formula can run automatically. BMY remains a
separate CVR plus timed-license-payment mechanism and was not forced into the
convertible rule.
