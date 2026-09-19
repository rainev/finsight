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

WG17 exposed the reverse classification trap for DVA. Its `$39.463M`
`AcquisitionObligationsAndOtherNotesPayable` row is a component of the filed debt-instrument table
and is already included in the `$10.781013B` aggregate debt carrying value. Moving the row from a
legacy mixed claim bucket into a separate acquisition-adjustment field would deduct it twice. Keep
the amount inside aggregate debt, retain its fair-value row as corroboration, and treat the later
$200M Elara investment cash as a separate post-period event requiring a full rollforward.

WG18 exposed a precision variant for GLW. The same current context reports
noncurrent debt/capital leases at $7.756B with `decimals=-6` and $7.8B with
`decimals=-8`. These are compatible precise and rounded presentations, not two
claims and not necessarily a source conflict. Select the most precise row only
when the accession, period, context, dimensions and declared rounding interval
prove compatibility; otherwise fail closed. Adding $668M current debt yields
the filed $8.424B debt bridge once.

WG23 exposed another scope trap in JBL: $51M of `FinanceLeaseLiabilityPaymentsDue`
was a table of future payments under NEW fiscal-year leases only, not the full
current finance-lease carrying value. The broad 1–3/3–5-year buckets did not
supply exact annual timing, and guarantees/uncommenced leases were separately
excluded. Never promote a partial undiscounted payment total into debt or
preferred equity merely because the prior recipe deducted the same amount.
Retain the legacy result in history and require current carrying scope, timing
and debt overlap before issuing a successor.

WG25 confirmed JBL Note 4's residual-guarantee and signed/uncommenced-payment
exclusions apply to the combined operating/finance lease disclosure. Do not
assign those totals solely to finance leases, or infer a recognized current
guarantee liability from an excluded maximum. Exact timing is required only
if estimating a PV from future payments; a source-proven complete current
carrying claim with reconciled debt overlap would not need invented annual
payment dates. Current new-only payments cannot supply that carrying claim.

WG39 exposed the aggregate form again for GILD. `LongTermDebt` of $26.246B
already equals $2.414B current plus $23.832B noncurrent debt and already contains
the $1.077B Immunomedics future-royalty component. Adding current debt or the
rounded $1.1B royalty carrying disclosure again double-counts claims. The debt
note also reconciles $25.168B senior debt plus the $1.077B royalty component to
the total within reported precision. The H1 $2.783B financing repayment equals
the $2.750B matured note plus the $33M decline in the royalty component. The
September 19 audit qualifies the former claim that this equality alone proved
royalty cash classification: interest accretion, other movements and payment
scope must also reconcile. Retain the equality as corroboration, not unique cash
identification. The historical GILD recipe already used the correct debt total.

**Why:** A plausible aggregate tag can still cover only the noncurrent line, while a separately
named obligation can still be financing. Either error overstates common equity.

**How to detect / apply:** Reconcile every selected claim to the face balance sheet and debt note:
current + noncurrent + finance leases + other explicitly financial obligations. Confirm aggregates
include their components exactly once by replaying the filed subtotal; never add a current component
or a separately labelled acquisition obligation to a proven aggregate total. Retain operating leases as operating when their expense and
cash payments remain in cash flow. See [[operating-liabilities-are-not-equity-bridge-claims]] and
[[telecom-spectrum-cash-is-reinvestment]].
