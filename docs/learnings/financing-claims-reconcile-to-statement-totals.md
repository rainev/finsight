---
name: financing-claims-reconcile-to-statement-totals
description: A debt-like tag's name does not prove scope; reconcile current, noncurrent, leases, and special financing obligations to the filed total.
metadata: { type: gotcha }
---
Batch 02 initially treated `LongTermDebtAndCapitalLeaseObligations` as total debt for VZ and T,
but the filed balance sheets separately presented current debt. TMUS also reports tower obligations
outside its disclosed debt-and-finance-lease subtotal; the tower note calls them long-term financial
obligations that accrue interest.

The opposite trap appeared in Batch 06: YUM's `LongTermDebtAndCapitalLeaseObligations` was the
filed aggregate total, so adding `LongTermDebtCurrent` again overstated claims by $2.823 billion.
The tag name alone could not distinguish that aggregate from the noncurrent-only cases.

Batch 35 repeated the first form for WMB: `$28.121B` of
`LongTermDebtAndCapitalLeaseObligations` was the noncurrent face-statement line, while `$2.197B`
of current maturities and `$475M` of commercial paper were separately reported. The complete claim
was `$30.793B`, not `$28.121B`.

Batch 43 repeated it for MOS: the `$4.7677B` `LongTermDebtAndCapitalLeaseObligations` fact was
explicitly labeled "Long-term debt, less current maturities." The complete cutoff bridge therefore
also required `$66.7M` current maturities and `$1.0213B` short-term borrowings, for `$5.8557B` total.

**Why:** A plausible aggregate tag can still cover only the noncurrent line, while a separately
named obligation can still be financing. Either error overstates common equity.

**How to detect / apply:** Reconcile every selected claim to the face balance sheet and debt note:
current + noncurrent + finance leases + other explicitly financial obligations. Confirm aggregates
include their components exactly once by replaying the filed subtotal; never add a current component
to a proven aggregate total. Retain operating leases as operating when their expense and
cash payments remain in cash flow. See [[operating-liabilities-are-not-equity-bridge-claims]] and
[[telecom-spectrum-cash-is-reinvestment]].
