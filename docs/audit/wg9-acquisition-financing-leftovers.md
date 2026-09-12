# WG9 acquisition and financing claim leftovers

Verified and user-confirmed 2026-09-09. This is a partial working-group
result, not release approval. Production, scheduling, merge, push, deployment
and the family-adapter phase were untouched.

## Reusable rule

The versioned `FINSIGHT-ACQUISITION-FINANCING-CLAIMS-1` contract separates
recognized acquisition liabilities, paid cash, pending prices, unquantified
contingent payments, NCI, temporary/preferred equity, mandatory redemption,
supplier-finance locations, restricted cash, integration stress and operating
inventory adjustments. Policies contain no filing amounts, dates or accessions.

Recognized totals must reconcile to their current/noncurrent components. Paid
cash is diagnostic and never deducted again. Pending transaction prices remain
event sensitivities. Typed financing components cannot be classified by matching
their amount to a prior recipe.

## Company results

| Company | Result | Previous low / base / high | Current low / base / high |
|---|---|---|---|
| MSCI | Source-bound representative | 130.0741537164008 / 265.46018394493495 / 404.37721726992066 | 143.74078494536505 / 283.1653477111849 / 423.27512674579384 |
| KDP | Source/economic review | 0 / 7.484190074942197 / 44.5292634704103 | No candidate |

MSCI now deducts $153.9M / $93.9M / $33.9M across bear/base/bull: the $33.9M
recognized liability in every scenario plus the retained full/half/zero pending
First Street sensitivity. Its cash FCFF changes from
$1.709323871B / $1.722078861B / $1.730224437B to
$1.807523218B / $1.814227525B / $1.824419981B, and the denominator becomes the
current 72,832,000 shares. The source correction lowers value relative to the
same refreshed cash inputs, while the current cash normalization raises the net
candidate versus the historical baseline.

KDP's filing proves the component values but not two load-bearing semantics. The
supplier-finance location axis is retained only as `typed`, so $320M financing
cannot be distinguished mechanically from $1.779B accounts payable. The existing
temporary preferred is not bound until claim-versus-conversion treatment is
approved. The contract therefore returns review rather than fitting amounts.

## Verification evidence

- Frozen two-worker group:
  `output/us-refresh-group-verification/0a674d97e2218b78e3885fd85fabed40608bc2bc30a68fdfb65ed746d324efa6/report.json`.
  File SHA-256 `c6042970a5b5db47708b37623814e9000f239b381303852e8282c138393f644f`;
  implementation `fedfdaf87efe7c8b9e0f35251e3e7c46a51f3db348ff2b43e07c3ee46f8a20ec`;
  policy `5f79b16c5936260c7d94ae6a2fdab468529d1307d5e353623c00b02987acb090`.
  Result: one cached source-bound candidate and one exact source/economic review.
  Preparation 0.69s, source processing 1.74s, calculation 2.46s and public
  verification 0.001s.
- Source-specific evidence:
  `output/us-refresh-runtime/source-validation/46c811617d1b08ae95d0066557bdf79f73bda2442004a9efaeca1fdcf39bbea5/report.json`.
- Focused regression: 205 passed. The final claim/bridge/binding subset passed 72
  tests.
- MSCI isolated real API/database UAT:
  `output/us-refresh-operational-uat-20260909-wg9-msci/uat-report.json`. A real
  FastAPI worker served predecessor, candidate and rollback values, reloaded
  without restart, rejected stale CAS and preserved 440 registry rows plus 419
  private recipes.
- Work-register JSON reproduced SHA-256
  `2e2137aae32606e9dba16ee92dc0f36fceb15fb9434fea470cbcf10e29b27f82`.
  Current status: 257 compiled contracts, 162 implementation gaps, 1 current-
  policy source-bound result, 71 unclassified flags and 0 successive-period
  proofs. The real stage command remains blocked at 257/419 and no production
  pointer exists.

## Remaining blockers

KDP needs structural preservation of typed member values for supplier-finance
location and an explicit claim-versus-conversion rule for its convertible
preferred. BMY still needs its $607M current CVR separated from $950M timed fixed
licensing payments. APA remains in NCI/operating-reserve and pending-event work.
