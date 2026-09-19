---
name: preferred-par-zero-is-not-claim-absence
description: A zero preferred-stock par-value line does not prove that the economic preferred claim is zero.
metadata: { type: gotcha }
---
A balance sheet may show preferred stock at zero after rounding its small par value while placing the
much larger issuance premium in capital surplus. Do not interpret that zero as preferred-claim
absence when dividends, outstanding series, or regulatory capital evidence contradict it.

**Why:** PNC's Batch 35 filing showed a zero rounded preferred line but separately reported `$5.879B`
of preferred stock plus related surplus in its Basel III capital table. Treating the par-value line as
absence would overstate common book equity by roughly that amount.

**How to detect / apply:** Before accepting a zero preferred claim, reconcile preferred shares,
dividends, acquisition issuances, capital surplus, and regulatory-capital tables. Bind any narrative
or table value to the filing URL, accession, table locator, document hash, and package hash. Subtract
the economic preferred claim once from total equity; using common-attributable earnings after
preferred dividends is a separate earnings-attribution step, not a duplicate stock-claim deduction.

WG22's independent ETN review also identified a future-disclosure guard: a scan
restricted to USD carrying facts can miss a new share-only preferred/temporary
issuance. The current ETN package has no such facts in any unit, so its complete
common-only source proof remains valid. Before treating a future structure as
supported, screen the instrument/share evidence and fail closed on an unbound
new claim rather than interpreting the missing dollar amount as zero.
