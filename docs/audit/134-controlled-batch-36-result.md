# Controlled Universe Reset Batch 36 Result

Date: 2026-09-05
Status: **user-confirmed on 2026-09-05**

## Outcome

The exact frozen denominator is preserved: **Pass 0 / Conditional 9 / Withheld 1 / Numeric 9**.
All nine numeric results are Low reliability and use cutoff-safe reported history plus explicit
bear/base/bull assumptions. VLO is withheld because the Port Arthur third-party and regulatory
claim cannot presently be bounded without guessing; its intended public model remains refining
FCFF rather than mislabeling withholding as a model.

| Ticker | Outcome | Low | Base | High | Main reason |
| --- | --- | ---: | ---: | ---: | --- |
| FISV | Conditional Low | $30.51 | $79.60 | $146.24 | Payments FCFF separates settlement cash and bounds captive-finance reinvestment. |
| AMP | Conditional Low | $56.19 | $87.27 | $122.20 | Mixed wealth/insurance capital and claim cycles. |
| C | Conditional Low | $69.93 | $110.90 | $145.28 | Bank capital plus Banamex/Poland scope changes. |
| HIG | Conditional Low | $50.36 | $83.62 | $118.58 | Insurance catastrophe, reserve and investment cycles. |
| GS | Conditional Low | $250.06 | $410.30 | $574.66 | Broker-dealer cycle and cutoff debt/preferred-stock changes. |
| MS | Conditional Low | $48.24 | $79.49 | $112.04 | Wealth/trading cycle, compensation and capital. |
| CB | Conditional Low | $134.03 | $227.14 | $320.80 | P&C cycles and bounded preferred-claim absence. |
| ALL | Conditional Low | $88.52 | $146.99 | $208.43 | P&C cycles and new Oklahoma litigation warning. |
| COF | Conditional Low | $107.68 | $172.12 | $226.72 | Post-Discover combined TTM only; Brex accounting remains provisional. |
| VLO | Withheld | — | — | — | Port Arthur claims are unestimable and FY2025 capex lineage needs recovery evidence. |

## Load-bearing treatments

- FISV is treated as an operating payments processor, not a bank. Only `$627M` unrestricted cash
  enters the bridge. Equal `$17.561B` settlement assets and obligations are excluded, and a
  `$300M/$150M/$0` financing-asset reinvestment burden is applied across bear/base/bull.
- The eight financial issuers use parent/common-equity residual income. Deposits, policy reserves,
  client assets, securities financing and investment portfolios remain inside equity economics;
  none are incorrectly EV-bridged and NCI is not deducted twice.
- COF uses the `$5.407B` economic preferred claim rather than its zero par-value tag. Pre-Discover
  history is retained privately as a rejected diagnostic, not spliced into the combined-company
  baseline.
- GS adds the July `$2.5B` Series AA issuance and removes the completed `$0.75B` Series U redemption
  once. Equal net proceeds and claims leave common book equity unchanged; `$135.125M` of net annual
  preferred dividends reduces forward common earnings. Its separate July `$10B` note issuance
  adds `$567.775M` annual gross interest, scenario-adjusted for tax and proceeds income without
  incorrectly EV-bridging broker-dealer funding.
- VLO preserves `$11.349B` complete debt/finance leases, `$180M` restricted cash exclusion, and the
  custom `$798M/$1.066B` current/prior H1 capex facts. These do not cure the unbounded Port Arthur
  claim, so no number is emitted and missing values are never replaced by zero.

## Challenge and repairs

Independent source/model review identified and resolved the Important candidate defects:

1. VLO's fire and debt facts were initially attributed only to a buyback 8-K. The final receipt
   separately screens the controlling 10-Q that actually proves those facts.
2. The first public VLO artifact mislabeled `conditional_estimate` as its model. Final successors
   identify `fcff_dcf` as the intended model while availability and calculator remain withheld.
3. FISV's July leadership change and GS's `$10B` cutoff debt issuance were added to the complete
   event ledger; the GS coupon drag now flows through all three scenarios.
4. FISV's governed captive-finance range now traces the reported `$566M` originations, `$678M`
   collections, and `$188M` settlement-anticipation net collection and proves non-overlap with OCF.
5. CB's `NetIncomeLoss` is already parent-attributable. The final model proves consolidated profit
   less NCI equals the selected parent line and does not subtract NCI a second time.
6. FISV's public bridge review now displays its actual `$30.51/$79.60/$146.24` uncertainty range;
   CB's governed preferred midpoint is labeled estimated rather than reported.

The arithmetic challenge also prevented high recent AMP/HIG/GS/MS/CB returns from becoming a
forecast floor: recent history remains recorded, while conservative through-cycle ROE policy caps
the forward cases. Final review has no open Critical or Important finding.

## Determinism and real verification

- Final runs H/I: byte-identical; report SHA-256
  `7b624d466e631b2381f4ffeb456fe926f61073cfa746bc6c2d8749bc4f95cd24`.
- Source/event receipts: 10/10 event screens, five accepted and five rejected; event summary SHA-256
  `5664952a03c624756b13b9b8ddecfa7e91245ddd99aafc26f71e6e06a3974e1d`.
- Focused Batch 36/Batch 35/calculator verification: **30 passed**.
- Complete backend suite: **1,610 passed, 3 skipped, 1 warning**.
- Frontend production build: **1,694 modules**, passed.
- Isolated cumulative catalog: **360** — 116 available / 233 conditional / 11 unavailable;
  artifact tree `0fc3c8f29f85b206cb6b230dd983840cd97bfdf526279c5d3956560719eb5ed6`.
- Real API: **360 list, 360 detail, 360 calculator/default parity; zero private leaks**.
- Exact list/detail parity: true / **360 of 360**; forbidden serving imports: **0**.
- API receipts SHA-256:
  `eeb2c4fedc9e8be7dd49c23ba5947d0c2535d48c098db4d246e27e5286d2991d` and
  `74a6bfd63e456a09a144f0984c87ec123dafa651ece7b67a0e4c5df299cf6902`.
- Catalog manifest SHA-256:
  `24eb0660970e2490c5527fcd4123a0e99c97f9fe81894a95754df5bbbd602d63`.

## Confirmation boundary

The user confirmed this exact initial result with `y` on 2026-09-05. Tracked serving artifacts,
Recovery Learning Watchlist, withheld register, merge, push, deployment, recovery, and Batch 37
remain untouched. The next step is one VLO recovery attempt; any still-withheld outcome is then
recorded through the separate bookkeeping gate.
