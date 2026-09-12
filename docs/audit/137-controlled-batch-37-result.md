# Controlled Universe Reset Batch 37 Result

Date: 2026-09-06
Status: **user-confirmed on 2026-09-06**

## Outcome

The exact frozen denominator is preserved: **Pass 0 / Conditional 10 / Withheld 0 / Numeric 10**.
All ten ranges are finite, ordered, and Low reliability. No company is skipped or replaced.

| Ticker | Outcome | Low | Base | High | Main reason |
| --- | --- | ---: | ---: | ---: | --- |
| IVZ | Conditional Low | $16.00 | $26.04 | $34.96 | Asset-manager fee/AUM cycle, preferred claim, NCI, and impairment normalization. |
| ERIE | Conditional Low | $38.22 | $63.54 | $91.02 | Reciprocal-insurance management-fee structure and Class A/B economics. |
| ACGL | Conditional Low | $48.09 | $79.85 | $113.22 | P&C/reinsurance catastrophe, reserve, investment, preferred, and capital cycles. |
| FDS | Conditional Low | $163.83 | $277.51 | $436.25 | Subscription cash conversion, recurring reinvestment, debt, and fiscal-period alignment. |
| OKE | Conditional Low | $2.06 | $53.79 | $156.32 | Pipeline/resource cycle, leverage, acquisition reinvestment, projects, and ATM capacity. |
| MCO | Conditional Low | $119.63 | $215.96 | $360.37 | Ratings/data cycle, subscription cash, restructuring, debt, and sale effects. |
| BRK.B | Conditional Low | $271.31 | $424.89 | $613.47 | Holding-company/insurance mix, market gains, NCI, acquisitions, and class conversion. |
| MET | Conditional Low | $26.82 | $43.83 | $61.42 | Life-insurance reserves, investments, capital, redeemable NCI, and preferred claims. |
| TROW | Conditional Low | $39.68 | $64.86 | $91.36 | Asset-manager market/flow cycle and sponsored-portfolio/redeemable-NCI boundaries. |
| NDAQ | Conditional Low | $16.43 | $27.55 | $38.77 | Exchange/data integration, debt, transaction volumes, and nonrecurring disposal effects. |

## Load-bearing treatments

- IVZ uses only three current comparable annual common-earnings periods. Raw TTM common earnings
  remain `−$309.2M`; a reported `$1.7949B` 2025 indefinite-lived intangible impairment is added back
  at a governed 21% tax effect, producing `$1.108771B` normalized TTM. July preliminary AUM of
  `$2.4471T` is fee-scale evidence, never issuer cash.
- ERIE uses parent residual income and exact `$1.656098B` H1 management-fee proceeds at the reported
  25% rate. Reciprocal policyholder premiums, reserves, and float are not parent cash. The share
  denominator is the reported `52.29944M` diluted Class A-equivalent amount.
- FDS and MCO use operating FCFF despite their Financials metadata because their economics are
  subscription/data operating businesses with source-linked OCF, capex, interest, cash, investments,
  and debt. MCO uses consistent `InterestPaidNet`; current plus noncurrent debt reconciles exactly to
  the single aggregate before deduction.
- BRK.B uses parent-attributable earnings and `2.140710161B` Class B-equivalent shares from current
  Class A shares multiplied by the reported 1,500:1 conversion plus Class B shares. Insurance float
  and subsidiary funding remain inside equity economics and are not EV-bridged.
- MET rejects the zero par-value preferred tag. The `$2.905B` current economic claim is carried from
  year-end liquidation preference only after unchanged current/prior series shares and `$76M` H1
  preferred dividends prove that the stack persists.
- OKE deducts `$30.773B` noncurrent debt, `$750M` current debt, and `$1.499B` short borrowings once;
  NCI plus redeemable NCI totals `$144M`. The reported `$353M` H1 acquisition cash becomes a
  full/half/zero bear/base/bull reinvestment burden. A `$60M` equity-method impairment stays noncash.
  The `$1B` ATM prospectus reports capacity but no completed sale, so neither proceeds nor dilution
  is invented.
- NDAQ removes the `$89M` business-sale gain after a governed 21% tax effect and the separate `$88M`
  net-of-tax discontinued-operation adjustment once. Its `$1.5B` revolver is undrawn capacity, not
  debt proceeds.

## Independent challenge

Two `gpt-5.6-luna` reviewers ran under the FinSight Efficiency workflow:

- High reasoning verified source identity, exact periods/units, event documents, parent attribution,
  preferred/NCI/class-share treatment, debt bridges, and private/public separation.
- xhigh reasoning replayed all thirty scenarios, challenged FCFF versus residual-income routing,
  checked sensitivities/calculators, and tested the classifications.

The challenge corrected OKE's debt overlap, added its acquisition/lease/ATM treatment, replaced
MCO's net-interest alias with cash-interest lineage, added NDAQ's discontinued adjustment, persisted
MET's preferred-dividend evidence, and proved BRK.B parent earnings without double-subtracting NCI.
The apparent MCO investment omission was independently withdrawn after confirming that `$1.467B`
cash plus `$29M` investments equals the `$1.496B` used in every scenario. Final disposition:
**0 Critical / 0 Important / 0 Minor**.

## Determinism and verification

- Final runs E/F: byte-identical; report SHA-256
  `3de35a110166d4270126398117675cfae698081b64f2e283b7f47ac5427254ea`.
- Final run tree SHA-256:
  `27a3320e81b440847a5cb128d13ab3e756970dbbf3272357cababe995ee7d013`.
- Structural capture: **10 attempted / 10 parsed / 0 failed**; summary SHA-256
  `e4829a9b074e10e61d650ac64145d9e96dcc50a5db646cefe310630ffa862da5`.
- Event ledger: **10 screened — 3 accepted / 7 rejected**; summary SHA-256
  `f3de3778b4550eb16764621b84b90f6feb36082304d3512e330760c07f74f6e1`.
- Focused Batch 37/Batch 36/calculator verification: **22 passed**.
- Complete backend suite: **1,626 passed, 3 skipped, 1 warning**.
- Frontend production build: **1,694 modules**, passed.
- Isolated cumulative catalog: **370** — 116 available / 243 conditional / 11 unavailable;
  artifact tree `39d43452805ada42dd319ea075ba2a9a227440b702bac7b96e3e11a64134d1b8`.
- Real API: **370 list, 370 detail, 370 calculator/default parity; zero private leaks**.
- Exact list/detail parity: true / **370 of 370**; forbidden serving imports: **0**.
- API receipts SHA-256:
  `717274d2189b0608da401adc5730fd81e6330f48beababef7c2989a8654ebc89` and
  `38695412efeca93c4da6e62268e5db826eebe73ac97c7ec95aa8167967aa840c`.
- Catalog manifest SHA-256:
  `484533ce5a2c83c9ce8bc7bafed366f38dc4d1485be420c7d286a30dcd4ca8d3`.

## Confirmation and bookkeeping

The user confirmed this exact initial result with `y` on 2026-09-06. No company is Withheld, so no
withheld-company recovery attempt is needed. All ten Conditional companies are now recorded on the
Recovery Learning Watchlist.

- Watchlist: **254 companies** — 243 Conditional and 11 Withheld; SHA-256
  `a476c3503379e52326b3fb393ae9189d83fddf1764c015f5013c3b94b6141f34`.
- Cumulative withheld register: unchanged at **21 entries**; SHA-256
  `22fb28e93e84996d6b2fe1bd836d0cee3df746f3536aec26b57dfc1215751bb6`.
- Post-bookkeeping watchlist/withheld/Batch 37 verification: **15 passed**.

Tracked serving artifacts, recovery, merge, push, deployment, and Batch 38 remain untouched.
