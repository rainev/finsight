---
name: customer-held-cash-needs-an-operating-reserve
description: Marketplace cash is not automatically excess cash when customer and merchant balances are embedded in it.
metadata: { type: gotcha }
---
For marketplace and travel issuers, reported cash can include money collected for customers or suppliers. Do not add all cash to enterprise value while leaving the matching merchant liability inside operating working capital. Build a source-linked excess-cash range from the filing's customer accounts, restricted traveler cash, deferred merchant bookings, prepaid bookings, and merchant payables; deduct the operating reserve once and keep the issuer Conditional when the supplier-versus-margin split is not reported.

**Why:** Adding customer-held cash as a nonoperating asset overstates equity, while also subtracting the matching operating liability as a bridge claim double-counts the same obligation.

**How to detect / apply:** Search the controlling filing for customer accounts, restricted cash, deferred merchant bookings, prepaid bookings, and merchant payables before setting excess cash. Record the cash range and state explicitly which operating liabilities were not subtracted again. See also [[operating-liabilities-are-not-equity-bridge-claims]].

DASH demonstrates a governed full/half/zero customer-contract cash reserve:
the reported liability sets the amount, while the fractions remain scenario
policy rather than reported debt. ICE demonstrates an exact decomposition:
issuer cash + restricted cash + matched clearing-member margin funds reconciles
to cash-flow cash, and the matching member liability is not added to debt.
