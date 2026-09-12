# WG8 customer funds, settlement balances and guarantees

Verified and user-confirmed 2026-09-09. This is a partial working-group
result, not release approval. Production, scheduling, merge, push, deployment
and the family-adapter phase were untouched.

## Retained mechanism and exclusions

The versioned `FINSIGHT-CUSTOMER-FUNDS-1` contract identifies cash ownership
before valuation. It validates issuer, accession, period, unit, context,
namespace, dimensions, statement placement and exact reconciliation without
filing amounts, dates or accessions in policy.

DASH and ICE were retained. KDP is acquisition capital structure and supplier
financing; MSCI is recognized acquisition consideration plus a pending event.
They were classified from their filings and remain required implementation work,
not failed or unavailable customer-funds cases.

## Company results

| Company | Classification | Result | Previous low / base / high | Current low / base / high |
|---|---|---|---|---|
| DASH | Customer-cash reserve, temporary equity, separate litigation | Source-bound representative | 78.1881151915972 / 136.0538646510765 / 190.99640464875785 | 79.22183438822366 / 135.13288096791305 / 185.30051084937546 |
| ICE | Matched clearing-member funds and settlement balances | Source-bound difficult case | 38.95027916345947 / 85.92002066234853 / 134.26299655765646 | 45.774824210822295 / 94.66147010833012 / 144.49188449437167 |
| KDP | Acquisition, preferred/NCI and structured financing | Classified implementation gap | 0 / 7.484190074942197 / 44.5292634704103 | No candidate |
| MSCI | Recognized and pending acquisition consideration | Classified implementation gap | 130.0741537164008 / 265.46018394493495 / 404.37721726992066 | No candidate |

DASH's customer-cash range remains $5.662B / $5.939B / $6.216B. The valuation
movement comes from replacing scenario-varying shares with the current
440,833,000 denominator and deducting the separately reported $406M litigation
reserve; its combined outside-owner/legal claim is now $417M. The contract
liability is an approved scenario reserve, not reported debt.

ICE's $101M outside-owner claim is unchanged economically and merely moves from
the legacy preferred slot to $69M NCI plus $32M redeemable NCI. Its valuation
movement comes from current history-normalized cash FCFF and the current
563,394,487-share denominator. No clearing-member funds enter issuer cash.

KDP's exact remaining source items include $4.196B NCI, $4.418B temporary equity,
$898M mandatory redemption, $320M financing-like structured payables and $402M
deferred acquisition consideration. MSCI has $33.9M recognized contingent
consideration, $9.5M already paid and a pending $120M First Street cash
sensitivity. These are next-group inputs, not WG8 valuation changes.

## Verification evidence

- Frozen two-worker group:
  `output/us-refresh-group-verification/7c900cc775d7c241f6b02d85c812bb15337a7a1059bd1779d5d0c1f2a53a2ef8/report.json`.
  File SHA-256 `21a838c003885d55a42a675777ba18dc66ab9946dd77957c40d90b20cb49cb86`;
  implementation `05cf5cb142e592473f597973310b916d8d180f5fd23a8c0d2ce427a917997db5`;
  policy `f4274a4dd2477e3bfe73b8c5850ad8c7bfa2d57048ed827612e27c3ad8c7120a`.
- Group result: two cached source-bound candidates. Preparation 1.31s, source
  processing 4.05s, calculation 18.77s and public verification 0.004s.
- Source-specific evidence:
  `output/us-refresh-runtime/source-validation/bccdf3c34f4078f5e36507460fccbb60fba582816c39ca809528c8794c3337b3/report.json`.
- Focused regression: 169 passed. The final customer-funds/claim/bridge/binding
  subset passed 115 tests.
- DASH isolated UAT:
  `output/us-refresh-operational-uat-20260909-wg8-dash-final/uat-report.json`.
  ICE isolated UAT:
  `output/us-refresh-operational-uat-20260909-wg8-ice-final/uat-report.json`.
  Both used a real FastAPI worker and isolated catalog/database, served exact
  predecessor/candidate/rollback values, reloaded without restart, rejected stale
  CAS and preserved 440 registry rows plus 419 private recipes.
- Work-register JSON reproduced SHA-256
  `7f48668dd53b707b2569eff824597bc05995adcb59be2346101213d06c7dda0b`.
  The final unclassified count is 71, down from 74: DASH/ICE became executable
  typed mechanisms; KDP/MSCI became filing-supported classifications; FISV
  correctly returned to unclassified after removing a false legal classification
  based only on the word “settlement.”
- Current status: 255 compiled contracts, 164 implementation gaps, 2 current-
  policy source-bound results and 0 successive-period proofs. The real stage
  command remains blocked at 255/419 and no production pointer exists.

## Remaining blockers

KDP needs disjoint source rules for mandatory redemption, the financing-like
portion of supplier payables, deferred JDE consideration, NCI, temporary equity
and integration-cost scenarios. MSCI needs its $33.9M current contingent-
consideration liability added once while keeping $9.5M paid cash and pending
First Street consideration separate. DASH remains Low/Conditional because
acquisition integration, dilution and marketplace working-capital uncertainty
remain; ICE retains pending MarketAxess event context outside current value.
