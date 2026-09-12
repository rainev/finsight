---
name: claim-evidence-must-enter-before-bridge-resolution
description: A verified claim checked only after bridge resolution cannot clear the missing field that already stopped the valuation.
metadata: { type: gotcha }
---
A reported-NCI rule was originally validated only after `normalized_bridge`
returned. For issuers where NCI was absent from the generic CompanyFacts path,
the bridge failed first, so the valid structural evidence was unreachable.

Convert validated current claim scope into a governed `FieldAvailability`
record and merge it before normalization resolves the bridge. Revalidate the
resolved amount afterward. This ordering preserves fail-closed source checks
while allowing the evidence to affect the decision it is meant to support.

Canonical policy JSON sorts input keys, so declaration order cannot enforce
this gate. The binding layer must explicitly evaluate `special_claim` selectors
before normalized bridge selectors; otherwise an economic review can be hidden
behind an earlier generic bridge error.
