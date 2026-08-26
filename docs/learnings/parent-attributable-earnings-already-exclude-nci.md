---
name: parent-attributable-earnings-already-exclude-nci
description: Do not subtract NCI again when the selected continuing-income fact is already attributable to the parent.
metadata: { type: gotcha }
---
An issuer's `IncomeLossFromContinuingOperations` presentation may already be the amount attributable to the parent, even when separate NCI presentation facts appear nearby. Confirm the statement label and context before subtracting NCI. If the selected earnings line is already parent-attributable, retain the NCI facts only as reconciliation diagnostics.

**Why:** In the APTV Batch 08 recovery, subtracting the $3M/$6M NCI presentation from the already parent-attributable $427M/$125M continuing-income facts understated every scenario.

**How to detect / apply:** Reconcile consolidated continuing income, redeemable/nonredeemable NCI, and the parent-attributable line from the same filing and period. Record `nci_subtracted_again: false` when the selected fact is already attributable to the parent. See also [[mixed-finance-business-needs-honest-equity-baseline]].
