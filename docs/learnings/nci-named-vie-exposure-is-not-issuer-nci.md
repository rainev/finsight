---
name: nci-named-vie-exposure-is-not-issuer-nci
description: A noncontrolling-interest XBRL name can describe an unconsolidated investment exposure rather than an issuer ownership claim.
metadata: { type: gotcha }
---
Do not map `NoncontrollingInterestInVariableInterestEntity` into the common-
equity bridge from its name alone. Agilent reports the fact under the
not-primary-beneficiary VIE disclosure with no balance-sheet role; the amount is
the carrying exposure of investments and loans, not consolidated NCI.

**Why:** An unchecked name-based mapping would deduct the same investment as an
outside-owner claim and could also add it through investments, understating
common value twice.

**How to detect / apply:** Require current accession/period identity, complete
package provenance, statement role, presentation ancestry, primary-beneficiary
status, a containing investment balance, and the absence of conflicting
ordinary NCI. Keep the exposure as a private diagnostic and exclude it from both
issuer NCI and additive cash-like investments unless a separate source rule
proves otherwise.
