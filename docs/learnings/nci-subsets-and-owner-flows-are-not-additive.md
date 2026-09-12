---
name: nci-subsets-and-owner-flows-are-not-additive
description: A VIE NCI member and NCI owner flows must not be added to the current total NCI balance.
metadata: { type: gotcha }
---
A current undimensioned NCI balance can already include a consolidated-VIE
member. APD reports $2.7126B total NCI and a $1.8316B VIE-primary-beneficiary
subset; adding them would double count ownership. Investments by NCI,
distributions, purchases/redemptions, earnings and OCI are period flows and do
not become additional balance-sheet claims.

**Why:** XBRL presents totals, dimensional subsets and equity roll-forward flows
near one another. A keyword-driven sum can turn one current claim into several.

**How to detect / apply:** Prefer the current undimensioned balance, reconcile it
to the NCI equity member and total-minus-parent equity, retain dimensional VIE
rows only as subsets, and keep every duration flow in a separate roll-forward
ledger. In parent-equity models, do not deduct the reconciled NCI again.
