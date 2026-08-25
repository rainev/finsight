---
name: telecom-spectrum-cash-is-reinvestment
description: Telecom cash FCFF must deduct source-linked spectrum-license purchases in addition to PP&E capital spending.
metadata: { type: gotcha }
---
`Operating cash flow - PP&E capex + after-tax interest` overstates telecom enterprise cash FCFF
when spectrum licenses are purchased in investing cash flow. VZ and TMUS tag those payments as
`PaymentsToAcquireIntangibleAssets`; AT&T's current filing dimensionally tags license cash within
business-acquisition payments.

**Why:** Spectrum is a recurring economic requirement for a wireless network even though it is an
intangible asset rather than PP&E. Omitting it materially raised the first Batch 02 candidate.

**How to detect / apply:** Search the controlling filing and annual history for spectrum/license
cash, retain accession/period/unit lineage, subtract it from current and comparable annual cash
states, and use a current source-backed floor when an annual tag is absent. Test that one extra
dollar of spectrum cash lowers cash FCFF by one dollar. See
[[financing-claims-reconcile-to-statement-totals]].
