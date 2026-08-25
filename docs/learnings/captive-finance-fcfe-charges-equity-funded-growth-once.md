---
name: captive-finance-fcfe-charges-equity-funded-growth-once
description: Captive-finance adjusted FCF becomes owner cash flow only after charging once for the equity-funded share of finance-asset growth.
metadata: { type: gotcha }
---
Dell's adjusted FCF removes financing-receivable and operating-lease-equipment effects, while its
7:1 DFS debt-to-equity approximation identifies the common-equity funding requirement. **Why:**
subtracting DFS debt again double counts funding; ignoring asset growth overstates owner cash.
**How to detect / apply:** use `adjusted FCF - finance asset growth / (1 + D/E)`, discount at cost
of equity, and never apply a later cash/debt bridge. Reconcile structured plus allocated core debt
to the disclosed target.
