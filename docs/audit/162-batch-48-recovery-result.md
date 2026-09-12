# Batch 48 WY/EQR Recovery Result

Date: 2026-09-11
Status: user-confirmed; recovery and bookkeeping complete.

## Outcome

The single authorized recovery attempt covered exactly **WY and EQR**.

- Recovered to Conditional: **1/2 — WY**
- Still Withheld: **1/2 — EQR**
- Final Batch 48 candidate: **0 Pass / 9 Conditional / 1 Withheld**, numeric **9/10**

## WY — recovered to Conditional Low

WY now has a conservative **synthetic total-payout baseline, not a dividend promise or timberland NAV**:

- **Bear: $5.51** — annualized H1 Adjusted FAD of $265M, 721.787M diluted shares, and the low end (75%) of the
  company's stated 75-80% total cash-return framework. That framework may use repurchases or supplemental dividends,
  so this is an owner-cash proxy rather than a promised dividend.
- **Base: $8.40** — the current $0.84 annual base dividend; H1 coverage is not demonstrated and remains a warning.
- **Bull: $11.80** — the five-year median total dividend of $1.18 per share, which includes historical supplemental
  distributions and is therefore explicitly upside rather than a promised dividend.

All three use a zero-growth 10% Gordon owner-distribution discount. The model never publishes the initial negative
enterprise residual, substitutes a $0 floor, invents timberland NAV, or adds unreported supplemental distributions.
The distribution input is locked in the public calculator; a higher cost of equity lowers value.

## EQR — remains Withheld

The attempt exhausted both cutoff-safe routes:

- A standalone EQR diagnostic can be calculated from annualized H1 Normalized FFO and recurring capital at about
  **$46.43 / $49.64 / $53.31**, but it remains private because guidance was withdrawn and the standalone economic object
  was expected to disappear three days later.
- The July 31 filing provides a 2.793 exchange ratio and preliminary combined GAAP pro formas, but not combined AFFO,
  final closing shares, debt/cash, purchase accounting or integration costs. These preliminary figures are diagnostic,
  not a publishable Vivmark valuation.

No post-August-14 closing facts or successor/VMRK identity were used. EQR remains `Withheld`, its range is null and its
calculator is unavailable.

## Independent challenge and verification

Three Luna High reviewers separately challenged WY's source lineage/model/calculator and EQR's merger boundary. Sol
replayed the arithmetic and enforced the canonical public contract. No unresolved Critical or Important model finding
remains; the public Low reliability label on EQR is the serving contract's safety ceiling and is subordinate to its
explicit Withheld state and null confidence.

- Final candidates: `output/batch-48-recovery-run-g-20260911` and
  `output/batch-48-recovery-run-h-20260911`; all private/public/report files are byte-identical.
- Recovery report SHA-256: `eaeddfec14283b54b8981eaa483986e1d6e44dc9449e6abff2691d36ebdc3a6b`.
- Recovery candidate-tree SHA-256: `1cb9e5fe45c5f2a9c096dd7affe6bb6c9d6b77f57f72026f4480e168b9a9d5e4`.
- Focused Batch 48 history/recovery/calculator tests: **20 passed**.
- Final complete backend suite: **2,347 passed / 3 skipped / 0 failed**.
- Frontend production build: passed (`1,694` modules transformed).
- Immutable recovery catalog `US-RESET-2026-08-14-B01-B48-RECOVERY-1.0` was built twice with byte equality:
  **480 companies = 116 Pass / 339 Conditional / 25 Withheld**, numeric **455/480**. Manifest SHA-256:
  `24a773cda6e53bfcc6e036c1687927da8a696274d20a193d10a37f1344ca27df`; artifact-tree SHA-256:
  `dc8bdc0002b2bf8ce160544b078ceb62720036d3f59ef7d65c3b09d43cb2a059`.
- Real isolated API: **480/480** list/detail exact catalog parity, **480/480** calculator-default parity, zero private
  leaks and zero forbidden serving imports. Official receipt SHA-256:
  `25f229d93a53803988bb3dd422ba548fc1db090ee5a73d75eb5bc7cf48993178`; calculator receipt SHA-256:
  `3b77ee71eccb70a1897ed0c63907c1baa78fba6b02d5367c09d0bc5b4aaf6cc6`.

## Boundary

Before confirmation, serving artifacts, the Recovery Learning Watchlist and cumulative withheld register remained
unchanged. The user's confirmation authorized only the Batch 48 watchlist and withheld-register bookkeeping below.

The user confirmed the recovery result. The 480-company universe is now **116 Pass / 339 Conditional / 25 Withheld**,
with **455/480 numeric**. All ten Batch 48 issuers were added once to the Recovery Learning Watchlist, which now contains
**364 companies: 339 Conditional / 25 Withheld** and has SHA-256
`e43f9c37f58b5e5821ef899dad13d1ca6dfdddfbcd5731b66641ceda3e774856`. EQR was added once to the cumulative
post-recovery withheld history, which now contains **35 companies** and has SHA-256
`ff14e5d7d68932d08046911c763bac21bca972546f2a0d9acce9c96c6be990cc`.

Serving promotion, Batch 49, merge, push and deployment remain outside this confirmation.
