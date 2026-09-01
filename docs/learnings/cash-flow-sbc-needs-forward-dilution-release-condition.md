---
name: cash-flow SBC needs a forward dilution release condition
description: OCF-based FCFF retains noncash stock-compensation add-backs, so material recurring SBC needs an explicit dilution or buyback treatment.
metadata: { type: gotcha }
---
An operating-cash-flow FCFF model normally includes the noncash add-back for stock-based
compensation. A current diluted-share denominator does not by itself model future grants, net share
issuance, or cash buybacks used to offset dilution. When recurring SBC is material to owner cash,
retain the reported OCF fact but classify the result Conditional until forward net dilution or an
equivalent buyback burden is normalized.

**Why:** Batch 30 initially labeled MPWR Pass even though H1 stock compensation was `$94.282M`
against `$585.537M` of TTM owner cash. PLTR's H1 stock compensation was `$466.801M`. Subtracting SBC
as if it were a cash expense would falsify reported cash flow, while ignoring its forward ownership
cost would overstate completeness.

**How to detect / apply:** source the exact current SBC fact, compare it with owner cash, reconcile
weighted diluted and current outstanding shares, and inspect repurchases. Keep SBC inside reported
OCF; separately record whether the valuation models forward net issuance or buyback cash. If it
does not and the amount is material, use Conditional Low with a named release condition rather
than inventing a future dilution rate. See also [[share-facts-must-preserve-share-units]].
