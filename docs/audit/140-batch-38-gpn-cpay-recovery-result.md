# Batch 38 GPN/CPAY Recovery Result

Date: 2026-09-07
Status: verified recovery result; user confirmation recorded.

## Exact result

The single authorized recovery attempt covered exactly GPN and CPAY. The full Batch 38 denominator remains ten.

| Ticker | Initial | Recovery | Low | Base | High | Reliability |
| --- | --- | --- | ---: | ---: | ---: | --- |
| GPN | Withheld | Withheld | — | — | — | — |
| CPAY | Withheld | Conditional | $40.12 | $65.42 | $90.95 | Low |

Recovered Batch 38 counts are Pass **0/10**, Conditional **9/10**, Withheld **1/10**, numeric **9/10**.

## GPN decision

The reported post-Worldpay H1 cash-FCFF anchor annualizes to $554.447M. Against $1.6979B available corporate cash,
$22.418326B debt/finance leases, $858.943M NCI claims, and reported diluted shares, all three raw residuals remain
negative: approximately −$67.15/−$54.67/−$39.25 per share.

A favorable stress that incorrectly allows all $5.409B balance-sheet cash and removes NCI claims still produces
approximately −$50.49/−$37.84/−$21.98. A second private diagnostic annualizes Q2 operating income plus D&A less
estimated half-H1 capex and produces −$3.42/$82.51/$139.50. It is not published because quarterly capex is estimated,
working-capital and settlement/customer-funding cash are omitted, and software/reinvestment is not separately reported.
GPN therefore remains withheld rather than presenting that proxy as a source-bounded valuation.

The settlement-line borrowing of $1.136764B is recorded as a matched exclusion alongside excluded settlement/customer
cash. Including that borrowing without its matched cash only lowers value. Recovery requires a full comparable
post-close cash-flow period with recurring corporate cash, integration costs, software/capex, and settlement funding
reconciled.

## CPAY recovery

CPAY is recovered through a five-year parent/common-equity residual-income fallback. This route keeps customer deposits,
restricted cash, securitized receivables, and their funding inside equity economics and never treats them as free cash.

- Reported common earnings: FY2023 $981.890M, FY2024 $1.003746B, FY2025 $1.068346B.
- TTM common earnings: $1.068346B + $592.558M − $527.401M = $1.133503B.
- Parent common equity: $3.541884B; latest shares: 65,659,599.
- Governed ROE: 10%/14%/18%; payout: 20%/30%/40%; cost of equity: 11%/9.5%/8.5%.
- Terminal ROE: 8.5%/10.5%/11.5%; terminal growth: 1%/2%/2.5%.
- The bear share denominator adds the full 328,213 July performance units; base/bull do not assume vesting.

The pooled H1 AP/accrued/customer-deposit cash-flow line is also reconciled privately: $711.251M AP movement,
−$38.174M accrued movement, and $797.220M customer-deposit movement total $1.470297B. The $100.046M difference from
the reported $1.570343B pooled line matches the separately recorded $100M FTC charge within $46,000. The charge is
already in earnings and is not deducted twice.

The pending Maintenance sale's expected approximately $800M proceeds and $460–515M gain are excluded until closing.
This remains Conditional Low because customer-funding behavior, credit losses, leverage, the disposal, and legal outcomes
can move actual value beyond the range.

## Verification

- Recovery candidates: `output/batch-38-recovery-run-a-20260907` and
  `output/batch-38-recovery-run-b-20260907`; all 21 files are byte-identical.
- Recovery report SHA-256: `4183001c790ed7896759b7cbae0edd9676136b4ffa28ada25daebbfb9d541a71`.
- Luna xhigh challenged GPN's strict and Q2-proxy routes; Luna high independently built and challenged CPAY's
  customer-funds and parent-equity routes. Sol reconciled both against the frozen sources and formula replay.
  Their final run-B checks found no remaining Critical, Important, or Minor finding.
- Focused recovery/history/calculator tests: **22 passed**.
- Complete backend regression: **1,642 passed, 3 skipped, 1 warning** (219.89 seconds). The warning is the existing
  Python `crypt` deprecation in passlib.
- Frontend production build: passed, 1,694 modules. No UI behavior changed in this recovery.
- Isolated catalog: 380 companies — 116 available / 252 conditional / 12 unavailable; 368 review-required / 12 withheld.
- Catalog tree SHA-256: `cf4d18c9852494e13c75190c5660c380f96e6e99779d99756ad68820fb8c71af`.
- Catalog manifest SHA-256: `937572c31fb7772ff9b6315488aae14a105ddcc7ff3a2cf11bbc5f0f10858afa`.
- Real API: 380 list entries, 380 detail/calculator GETs, 380 expected calculator outcomes, exact list/detail parity,
  zero private leaks, and zero forbidden serving imports.
- API receipt SHA-256: `c3969571ba870de10c0742c4b238664e1221e180c8b224cc15081718e7a97e1a`.
- Exact API/import receipt SHA-256: `194a7965fb285307f406d134ddf0e7a907ea2752dbb88c0451653a6d50cd9df2`.

## Confirmation boundary

No tracked serving artifact, merge, push, deployment, or Batch 39 work was performed. The learning watchlist now has
264 entries (252 Conditional / 12 Withheld), and the cumulative withheld register now has 22 entries. CPAY is bookmarked
as recovered Conditional; GPN is bookmarked as withheld after recovery and is the only new cumulative withheld entry.
Watchlist SHA-256: `d006122224ce57ca4ee3cf73ff866d8d2507d8186690e1c81bd81f982968948e`.
Withheld-register SHA-256: `3f5f1ade1e95013dccce0036bbb566c3b781cd03bdb3b0e9d08431cd3fb68d2a`.
