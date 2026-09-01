# Controlled Universe Reset Batch 24 Initial Result

Status: **firsthand verified and user-confirmed on 2026-08-31**. Exactly the ten frozen Batch 24
issuers were processed at the 2026-08-14 valuation date. Confirmation added the six Conditional
issuers to the Recovery Learning Watchlist. No recovery, withheld-history mutation, tracked serving
promotion, Batch 25, merge, push, or deployment was performed.

## Outcome

- Pass: **4/10** — BLDR, TT, XYL, ALLE
- Conditional: **6/10** — NOC, TDG, GNRC, HII, UBER, ETN
- Withheld: **0/10**
- Numeric: **10/10**
- Reliability: **10 Low / 0 Medium / 0 High**
- Cumulative through 240 issuers: **90 Pass / 141 Conditional / 9 Withheld**
- Cumulative numeric coverage: **231/240**

| Ticker | Outcome | Low | Base | High | Simple reason |
| --- | --- | ---: | ---: | ---: | --- |
| NOC | Conditional | $88.04 | $212.13 | $410.17 | B-21/program cash, capacity investment, and environmental claim tail |
| TDG | Conditional | $0.00 | $285.06 | $729.50 | Acquisitions, roughly $33B debt, redeemable NCI, and high leverage |
| BLDR | Pass | $21.78 | $72.41 | $181.62 | Five-year housing-cycle cash history and complete current bridge |
| TT | Pass | $98.98 | $200.69 | $347.79 | Five-year climate-systems cash history; acquisition/warranty evidence is bounded |
| GNRC | Conditional | $25.43 | $63.46 | $127.39 | Volatile standby-power cycle, acquisition, tariffs, impairment, and warranties |
| HII | Conditional | $0.00 | $137.69 | $270.42 | Negative current post-capex cash and long-cycle shipbuilding program timing |
| XYL | Pass | $21.79 | $46.83 | $85.61 | Five-year water-infrastructure history and complete debt/NCI bridge |
| UBER | Conditional | $4.70 | $48.22 | $108.25 | Restricted funds, marketplace balances, acquisitions, investments, claims, and NCI |
| ETN | Conditional | $42.44 | $104.59 | $193.49 | $11.079B acquisition, new debt, supplier finance, restructuring, and integration |
| ALLE | Pass | $62.13 | $113.45 | $182.54 | Five-year security-products history and complete debt/investment/share bridge |

TDG and HII have private negative raw bear residuals and public $0 limited-liability floors. Those
zeros are scenario outputs, not missing-value substitutions.

## Controlling sources

| Ticker | Accession | Form | Filed | Report period |
| --- | --- | --- | --- | --- |
| NOC | `0001133421-26-000034` | 10-Q | 2026-07-21 | 2026-06-30 |
| TDG | `0001260221-26-000053` | 10-Q | 2026-08-04 | 2026-06-27 |
| BLDR | `0001193125-26-325451` | 10-Q | 2026-07-30 | 2026-06-30 |
| TT | `0001628280-26-051117` | 10-Q | 2026-07-30 | 2026-06-30 |
| GNRC | `0001437749-26-025669` | 10-Q | 2026-08-04 | 2026-06-30 |
| HII | `0001501585-26-000047` | 10-Q | 2026-07-30 | 2026-06-30 |
| XYL | `0001524472-26-000110` | 10-Q | 2026-07-28 | 2026-06-30 |
| UBER | `0001543151-26-000032` | 10-Q | 2026-08-05 | 2026-06-30 |
| ETN | `0001551182-26-000030` | 10-Q | 2026-07-31 | 2026-06-30 |
| ALLE | `0001579241-26-000028` | 10-Q | 2026-07-23 | 2026-06-30 |

Malformed structural top-level period dates were retained only as diagnostics; filing selection
uses the source receipt and fact-level periods.

## Challenge and corrections

One `gpt-5.6-luna` High reviewer inventoried source/model risks and independently challenged the
exact private candidate. Two Important issues were found and repaired:

1. Uber's $10.120B AFS securities aggregate included $9.486B restricted investments. Available
   cash/securities was corrected to `$4.870B + ($10.120B - $9.486B) = $5.504B`, lowering the range.
2. TDG initially mixed a negative annual net-interest concept with positive current/prior expense
   concepts. The final candidate uses only `InterestPaidNet`: `$1.481B + $1.210B - $908M = $1.783B`
   TTM.

The reviewer rechecked final runs E/F and found **0 remaining Critical / 0 Important**. TT and ALLE
retain explicit minor aggregate-cash scope caveats; neither has contradictory evidence or a
quantified unavailable-cash amount. Final challenge receipt SHA-256:
`d77da6f265c491260870582e5abd8a0272da31e377008b7f5130c77c19725fca`.

## Verification evidence

- Frozen manifest SHA-256:
  `5e91acf91a147facfa50ed3fc2691eab4e7e3a3d10a7dc37477a4b4d7cb95dc2`.
- SEC packets: **3 reused / 7 fetched**; tree SHA-256:
  `447fa14301daac828a8ffc34ff89705e6b66a16f68df4535777e5034d312036a`.
- Structural parsing: 10/10; tree SHA-256:
  `f0251fdb94e4ddc7231c300c98e0114d9c6f149daca4a02fefc3eb89b73c945d`.
- Final E/F byte equality; report SHA-256:
  `53bd17c5f6d8bec6db7b44ca81e4393b85a511b3931b2462cbcf9d65c146e414`.
- Generated-private tree SHA-256:
  `8b2381a5f27c05317061bf50fabe1b9fbe5f1fd43e6e4a19a63081483cc62360`.
- Staged-public tree SHA-256:
  `3c5dfb5f133782575e5662dc80fe02884ecb3eea2f5d67a641262db32cac3172`.
- Focused Batch 24 tests: **8 passed**.
- Complete final backend suite: **1,468 passed, 3 skipped, 1 warning**.
- Frontend production build: **1,694 modules**, passed after final corrections.
- `git diff --check`: repeated at the final gate.

## Real consumer path

- Isolated cumulative catalog: exactly **240** artifacts, Batches 01–24.
- Availability: **90 available / 141 conditional / 9 unavailable**.
- Publication: **231 review-required / 9 withheld**.
- Artifact-tree SHA-256:
  `979ad6d7e97cb25e9de3b6a00d53dcf319ef062d5ca49df946b96c0ea1a2624f`.
- Manifest SHA-256:
  `c305cc877f9064a85b3cc95d6efec5585972e91aed02a41a977e06fe0aa62bab`.
- Real localhost FastAPI: list 240; detail 240/240; calculator GET/default parity 240/240;
  231 numeric POST 200; 9 unavailable POST 400; final Batch 24 parity 10/10; private leaks 0.
- API receipt SHA-256:
  `cea60703b174a6345bff6b5489ffc0bb0eb4c2f1f12565f9ffe230c4e005a7f0`.
- Arelle remained outside serving; the isolated server was stopped.

## Protected state and confirmation gate

- Tracked catalog tree:
  `38efe664dc981e9d2383ece43b66e9ae326b4b9a7cc2443f2463498432ef66a8`.
- Frontend public-data tree:
  `353a14bc672002e88d248811f98d23d4c1fb47cf28e526d969f463f256260274`.
- Generated research tree:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Recovery Learning Watchlist is **150** (141 Conditional / 9 Withheld), SHA-256
  `8f800a534b2123e6911a0b97c546dc4cfc7c4b4d243367c51070e971103e7357`.
- Automatic-withheld history remains **19**, SHA-256
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`.

The user replied `y` on 2026-08-31. NOC, TDG, GNRC, HII, UBER, and ETN were added as direct
Conditional entries with `recovery_outcome=not_applicable`; BLDR, TT, XYL, and ALLE remain outside
the watchlist as Pass issuers. Because Withheld is 0/10, no automatic recovery is needed. Batch 25
was not started; the next valid signal is `Start Universe Reset Batch 25`.
