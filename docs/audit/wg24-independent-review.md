# WG24 independent financial and implementation challenge

Completed 2026-09-15 by read-only `gpt-5.6-luna` reviewers with **high** reasoning:
`wg24_intc_economics` and `wg24_rule_inventory`. Disjoint assignments were
Intel source/economic validity and inventory of genuinely matching retained
rules. The economics reviewer additionally challenged the completed code and
the final two defensive changes. No production, retrieval, parameter tuning,
FSLR implementation or new engine work was delegated.

## Material findings and primary verification

- Approved 3%/7%/12% cash margins are hypothetical post-total-reinvestment
  assumptions, not reported sustainable cash or historical statistics. Five
  complete annual cash/tax periods retain all four negative years. Primary
  real-source proof reproduces revenue $57.032B, gross-interest proxy $1.150B,
  investing-capex FCFF diagnostic $3.7395B and the exact original range/floor.
- Preserve gross interest per source period: FY2021 `InterestExpense`, newer
  annual/current periods `InterestExpenseNonoperating`. Primary corrected the
  alias rule and verified the complete resulting source series and old parity.
  No net-interest or cash-interest substitution was made.
- $1.423B financing PP&E payments, $832M finance-lease principal and $626M
  extended-term PP&E cannot be silently ignored, blindly treated as extra capex
  or deducted together with corresponding debt. Primary checked current hashed
  cash-flow source and retains full-refresh review, not an invented adjustment.
- The retained cash/AFS combination has unresolved cash-equivalent overlap;
  marketable equity has separate liquidity restrictions. Current ordinary NCI
  is not the escrowed-share derivative claim. Incentives, customer cash,
  transformation and deconsolidation require separate scope/review. These are
  blockers, not defects resolved by migrating the margin field.
- FSLR is the sole plausible optional inventory match (0.5%/3%/10% margins).
  Primary checked its actual Batch 30 generator/private evidence. Its tax-credit,
  unpaid-capex and legal conditions require different validity work; it was not
  added. No numeric/source acceptance is claimed for any inventory candidate.

## Final implementation challenge

No material defect found in the implemented assumption registry, normalization,
binding or public explanation. Exact policy identity/version/margins/issuer
checks fail closed. Governed margins remain a `finsight_assumption` field while
reported/history cash remains separate. Live binding rejects the mandatory
economic-review stop before a bridge error can hide it; no successor is issued.

Final defensive-delta review independently passed **14 tests in 1.32 seconds**:
financing payments match the source-derived current YTD start; reported zero
on one financing line does not certify total reinvestment; the actual source
locator calls the diagnostic investing-classified capex, not total capex.
Primary passed 28 source/protected-blocker checks in 2.35 seconds and reran
current frozen source/calculation commands. Exact receipts are in
[WG24 audit](wg24-governed-cash-margin-normalization.md).

Low-level `governed_source_validity` assumes upstream complete/finite annual
and reported data; its optional interval argument must not be omitted by any
new caller. Current production `cash_history` supplies it and enforces the
upstream conditions; mandatory economic review also remains closed. This is
future-interface defensive hardening, not waived current financial validation.

This verifies a **narrow migration and blocked-update behavior**, not an INTC
numeric refresh, live acquisition, resolved bridge or rollout. User confirmation
of WG24's bounded migration/blocked-update result was received 2026-09-15;
this is not a completed INTC valuation or rollout approval.
