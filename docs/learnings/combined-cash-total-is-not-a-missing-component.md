---
name: combined-cash-total-is-not-a-missing-component
description: A reported cash-plus-short-investments total can support the bridge without inventing a component split.
metadata: { type: gotcha }
---
HSIC reports `CashCashEquivalentsAndShortTermInvestments` as one current $157M
balance but does not separately tag cash and marketable-security components.
Treating the individual fields as missing blocks an otherwise complete bridge;
placing the combined total into both fields double-counts the same assets.

**Why:** The valuation needs the combined cash-like total, not an invented
allocation. Component absence is not zero in general, but a complete combined
scope can prove that the total should enter once and that no additional
separately reported cash-like balance should be added.

**How to detect / apply:** Require the current undimensioned combined fact,
complete filing-package provenance, and an exhaustive search for separately
reported cash, short-term investment, marketable-security and noncurrent
cash-like facts. Fail closed if any nonzero separate fact conflicts. Otherwise
bind the combined amount once and mark the component fields as covered by that
same reconciled scope.
