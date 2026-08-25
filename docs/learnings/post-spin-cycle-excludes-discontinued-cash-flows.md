---
name: post-spin-cycle-excludes-discontinued-cash-flows
description: A post-spin cycle model must remove discontinued-business cash-flow components and balance peer weights explicitly.
metadata: { type: gotcha }
---
WDC's recast revenue and EBIT were continuing-only, but comparative consolidated D&A and capex
still included discontinued Flash amounts disclosed separately in Note 4. **Why:** mixing those
cash flows understates continuing reinvestment and corrupts the cycle. Pooling three WDC states
with ten peer states also silently gives the peer 77% weight. **How to detect / apply:** subtract
filed discontinued D&A/capex, reset history at the business change, preserve paired annual states,
and allocate issuer weights deliberately before calculating cycle quantiles.
