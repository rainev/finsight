# Controlled Universe Reset Batch 27 Initial Result

Date: 2026-08-31  
Status: **user-confirmed on 2026-08-31**

## Outcome

- Pass: **6/10** — TER, TXN, LRCX, MU, IT, ADSK
- Conditional: **4/10** — KLAC, ADBE, COHR, FLEX
- Withheld: **0/10**
- Numeric: **10/10**

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| TER | Pass | $29.81 | $48.46 | $97.32 | Low | Complete test/robotics cash history, debt absence, NCI, and shares |
| TXN | Pass | $12.70 | $55.44 | $124.01 | Low | Fab-capex cycle is fully visible and ranged through five-year cash history |
| KLAC | Conditional | $23.87 | $45.28 | $73.55 | Low | $5.970B purchase commitment needs explicit 3/5/8-year timing assumptions |
| LRCX | Pass | $34.75 | $74.68 | $121.47 | Low | Productive-assets capex, unrestricted cash, debt/leases, and split shares reconcile |
| MU | Pass | $29.18 | $80.97 | $153.49 | Low | Memory-cycle history includes the loss year; full unpaid capex is deducted |
| IT | Pass | $150.06 | $269.07 | $480.66 | Low | Recurring information-services cash and corrected capex lineage reconcile |
| ADSK | Pass | $95.45 | $192.97 | $296.63 | Low | Subscription cash, investments, debt, SBC, and shares are bounded |
| ADBE | Conditional | $245.54 | $421.40 | $612.37 | Low | $1.560B acquisition and acquired cash conversion remain material |
| COHR | Conditional | $0.00 | $16.79 | $41.71 | Low | Current post-capex cash is negative after acquisitions and conversion dilution |
| FLEX | Conditional | $12.75 | $29.83 | $55.83 | Low | $1.134B acquisition, financing, maturities, and EMS working capital remain material |

These are baseline decision ranges, not predictions or recommendations. COHR's $0 bear is an
explicit limited-liability floor: the private raw bear is -$0.7822 per share. No missing value was
replaced with zero.

## Controlling sources

| Ticker | Accession | Filed | Report period |
| --- | --- | --- | --- |
| TER | 0001193125-26-327715 | 2026-07-31 | 2026-06-28 |
| TXN | 0000097476-26-000152 | 2026-07-24 | 2026-06-30 |
| KLAC | 0000319201-26-000027 | 2026-08-06 | 2026-06-30 |
| LRCX | 0000707549-26-000037 | 2026-08-07 | 2026-06-28 |
| MU | 0000723125-26-000015 | 2026-06-25 | 2026-05-28 |
| IT | 0000749251-26-000245 | 2026-08-04 | 2026-06-30 |
| ADSK | 0000769397-26-000044 | 2026-05-29 | 2026-04-30 |
| ADBE | 0000796343-26-000112 | 2026-06-15 | 2026-05-29 |
| COHR | 0000820318-26-000020 | 2026-08-14 | 2026-06-30 |
| FLEX | 0000866374-26-000030 | 2026-07-31 | 2026-06-26 |

LRCX, ADBE, COHR, and FLEX packets/packages were reused from validated difficult-106 evidence; six
were captured once. Cache-only replay later reused all ten with zero fetches/reparsing. Structural
top-level diagnostic dates were never used for selection.

Narrow lineage repairs used `InterestAndDebtExpense` for TXN, `PaymentsForCapitalImprovements` for
IT, and current `InterestExpenseOperating` for COHR. KLAC/LRCX post-split share denominators were
bound to current structural facts.

## Load-bearing treatments

- KLAC's commitment grew from $2.420B to $5.970B. Bear/base/bull assume equal annual payments over
  3/5/8 years ($1.990B/$1.194B/$746.25M annually). Exact discounted reserves are
  $4.905596B/$4.644244B/$4.288429B. A permanent margin haircut is not used.
- MU deducts the full $6.914B current PP&E payable once. Its $5.722B debt/capital-lease total already
  includes the $2.670B finance-lease subset.
- COHR's current cash FCFF is -$864.893M. The bear state carries the exact gap from normalized
  positive cash to the current negative state, producing the raw negative equity result and public
  zero floor. Temporary/preferred equity is source-proven zero after conversion; 12.419M conversion
  shares are already within diluted shares.
- ADBE and FLEX keep acquisitions inside consolidated operations while explicitly capping
  reliability for acquired conversion and integration.

## Independent challenge

Two disjoint reviewers were used:

- `gpt-5.6-luna` High: identity, cutoff, histories, units, bridge coverage, share splits, aliases,
  and public safety.
- `gpt-5.6-luna` xhigh: model choice, classification, commitments, unpaid capex, negative cash,
  DCF arithmetic, sensitivities, and calculator behavior.

Three Important findings were repaired: KLAC commitment cash timing, MU unpaid-capex treatment, and
COHR current-negative-cash bear treatment. A fourth recheck corrected KLAC's initially perpetual
cash haircut into the exact present-value equivalent of finite annual payments. Final disposition:
**0 Critical / 0 Important**. The generic calculator-control display remains a minor shared backlog
item (Production Backlog B25); default results still match exactly. Challenge receipt SHA-256:
`25a96c261dfe10c7010af5b7c864cd405fd87e58a696f33165b0fd894e37204a`.

## Determinism and verification

- Source capture/replay A/B hash (`capture_batch_02_sources._tree_hash`):
  `58e84f6bec67cf9d537e22951612a31136002916c8b9e6ca29c8449efb3e3ec1`
- Initial structural capture hash (same contract):
  `ca81678ddaa6ae880310edcbfcc0c0a23557f37edfca1f7f4934d009579e24fa`
- Structural replay A/B: all ten reused, byte-identical, hash
  `3d21712fa5e173a0c5cda0611b89e62d105a1601186ba19f047d8796930f9562`
- Final candidate H/I: 21/21 corresponding files byte-identical; report SHA-256
  `8038e1d32a17646f60ddb285ade310296cf34ab7e6b350047dabca6a9d65bc5e`
- Candidate tree (`run_batch_07_history._tree`):
  `bcae9112ee1883ee5700a9a8d29aa4bf2f18aef383d21ff27b88a2da4beff466`
- Focused Batch 27 tests: **10 passed**
- Complete backend suite: **1,645 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated cumulative catalog: **270** issuers — 104 available / 157 conditional / 9 unavailable;
  artifact tree `e43a30e9b97f6b969468dd940a1771bca551ceccbc1f0d69b1275bdb272b0db5`
- Real API: 270 list/detail/calculator GET and default parity checks; 261 numeric POST 200, 9
  unavailable POST 400, zero private leaks
- API receipt SHA-256:
  `713f2caafcae240c9d3051217c2290618c781ea02a4036cac950cb89be882ed8`
- Catalog manifest SHA-256:
  `9e0e58820abb2474fd257698e80f7d584390d70e54f9a4852762ecd077f38394`
- Pre-confirmation watchlist remains 162 (153 Conditional / 9 Withheld), SHA-256
  `46e368ddfca3362758475b90498e39dc6cbe45808f001d7a1d91ddc86affe67e`
- Withheld history remains 19, SHA-256
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`
- Tracked serving artifacts remain unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-08-31. KLAC, ADBE, COHR, and FLEX entered the Recovery Learning
Watchlist as direct Conditional entries; COHR retains equity-at-risk status. The confirmed
watchlist is **166 companies** — 157 Conditional and 9 Withheld. The still-Withheld register is
unchanged because Batch 27 has zero withheld companies. No recovery is needed. Batch 28, serving
promotion, merge, push, and deployment remain outside scope.

Confirmed watchlist SHA-256:
`a69685b0cecee22058f27c3e356494c2f177401d25dbe75f03cd2013b733dc04`. The unchanged
withheld-register SHA-256 remains
`28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`.
