# Batch 31 Oracle Recovery Result

Date: 2026-09-02
Status: **user-confirmed on 2026-09-02**

## Outcome

Oracle received its one authorized recovery attempt and remains **Withheld**.

- Attempted: **1/1 — ORCL**
- Recovered to Conditional: **0/1**
- Still Withheld: **1/1 — ORCL**
- Final Batch 31: **Pass 2 / Conditional 7 / Withheld 1 / Numeric 9**

## What was tried

The initial ordinary fixed-cash model was replaced by a ten-year cloud-infrastructure stress replay
using the controlling FY2026 10-K, accession `0001193125-26-277521`:

- revenue `$67.357B`, OCF `$31.977B`, capex `$55.663B`, and construction in progress `$39.973B`;
- `$638B` RPO with 12% / 34% / 34% / 20% reported recognition timing;
- `$260B` of uncommenced data-center leases, beginning fiscal 2027–2029 over 15–19 years;
- `$13.309B` of data-center-power obligations with exact fiscal 2027–2031 buckets;
- a subsequent additional `$19B` five-year infrastructure commitment beginning fiscal 2027;
- `$137.242B` debt/finance leases, `$4.954B` preferred equity, `$548M` NCI, and `$31.894B` cash/securities;
- corrected preferred-conversion dilution of 24.99M–31.24M common shares.

The replay grows reported revenue at history-derived rates, fades the current 82.64% capex/revenue
ratio toward historical floors, explicitly charges new lease cohorts and the first five power-
obligation buckets, deducts post-year-ten lease residuals, and bridges debt, preferred equity, and
NCI once. RPO is never treated as cash.

All modeled growth, margin, capex-fade, lease-cohort, WACC, and terminal inputs are privately labeled
as historically derived or FinSight assumptions. The filing-reported aggregates, windows, terms,
and claims remain separately identified as reported facts.

## Diagnostic replay

| Scenario | Enterprise value | Common equity | Raw value/share | Preferred-conversion alternative |
| --- | ---: | ---: | ---: | ---: |
| Bear | `−$309.198B` | `−$420.048B` | `−$144.15` | `−$140.94` |
| Base | `$93.298B` | `−$17.552B` | `−$6.06` | `−$4.31` |
| Bull | `$622.987B` | `$512.137B` | `$177.80` | `$177.97` |

The central replay is deliberately optimistic: it excludes the `$7.533B` after-year-five purchase-
obligation bucket and the subsequent `$19B` commitment because their annual timing is not fully
reported. Adding both lowers base from `−$6.06` to approximately `−$11.93` per share. The base is
also negative under the corrected preferred-conversion alternative.

Because the practical base remains nonpositive, publishing a normal positive range would require
inventing better infrastructure cash conversion or more favorable capex/lease economics. The
recovery therefore fails closed with `MODEL_UNSUPPORTED`, `NONFINITE_OR_NONPOSITIVE_VALUE`, and
`CAPEX_CASH_CONVERSION_SENSITIVITY`.

## Independent challenge

Two `gpt-5.6-luna` reviewers challenged the exact recovery:

- High reasoning: source accessions, filing terms, lease/purchase/debt/preferred schedules, overlap,
  evidence labels, public metadata, and private/public safety.
- xhigh reasoning: independent ten-year arithmetic, sensitivity directions, optimistic omissions,
  preferred claim-versus-conversion treatment, and the final release decision.

The source reviewer required explicit FinSight/optimistic labels for lease cohorts and modeled
economics plus corrected withheld metadata. Those findings were repaired. Final disposition:
**0 Critical / 0 Important / 0 material Minor**.

## Determinism and real-consumer verification

- Final recovery candidates F/G: 21/21 files byte-identical
- Recovery report SHA-256:
  `6cfbc8b8a36f27f72924516ebb4793288fa792964ea511ab8ffa2b6981662a51`
- Recovery candidate tree SHA-256:
  `bf6c1c5793857a0fc793b9d9975681aa257efa07076c181e403312732b42ba59`
- Focused recovery tests: **5 passed**
- Complete backend suite: **1,546 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated recovery catalog: **310 issuers** — 113 available / 187 conditional / 10 unavailable;
  artifact tree `fdc111e713ed34c9896271f655b28292efdc76939cbad6606273c4ae0d68a90e`
- Real API: 310 list, 310 detail GET, 310 calculator GET/default parity; 300 numeric POST 200,
  10 unavailable POST 400, zero private leaks
- Exact detail/catalog parity: 310/310; forbidden serving imports: 0
- Calculator/API receipt SHA-256:
  `020737c4ed8787cb0100e2328ec4a938a59c0df86dd2f4e1ec2ba23e4a147091`
- Detail/import receipt SHA-256:
  `8af0dad82c8def907dc9574602cbce7a5014eced47a0436055ae7cdfa07f0daf`
- Catalog manifest SHA-256:
  `db0973e2d814aeaeddd9b792eba7c7332c6650f56945743c201641f064de91c6`
- Pre-confirmation watchlist remains **196** — 187 Conditional / 9 Withheld, SHA-256
  `28e81df86c67da7ef79c4c4e9b1fe26f74167879bacca393dd08e1a90ff9a254`
- Append-only withheld history remains **19**, SHA-256
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`
- Tracked serving roots remain unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-09-02. ORCL entered the Recovery Learning Watchlist with
`withheld_after_recovery` status and the cumulative withheld register with exactly one consumed
automatic recovery attempt. The confirmed watchlist now contains **197 companies** — 187
Conditional and 10 Withheld. The append-only automatic-withheld history now contains **20 entries**.

Confirmed watchlist SHA-256:
`44535d4d8a71ab1c183de9ba156b548df280bb25a5c23bb23e7b13dd87404759`. Confirmed withheld-
register SHA-256:
`7530586e01fdf65a61eea35feeca4b47337bc19134caeb4a87e4e8a87a016fce`.

ORCL receives no second automatic recovery during the 50-batch reset. Batch 32, serving promotion,
merge, push, and deployment remain outside scope.
