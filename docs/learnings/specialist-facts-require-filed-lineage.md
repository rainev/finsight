---
name: specialist-facts-require-filed-lineage
description: Specialist equity-model inputs must be selected by filing availability and retain the selected fact's own accession, form, unit, and currency.
metadata: { type: gotcha }
---
The specialist equity routes historically selected Companyfacts by period `end <= valuation_date`
and then attached `classification.source_accessions[0]` to the result. Period end does not prove
that a fact was public by the valuation date, and the first classification accession may not be
the accession that supplied the selected value.

**Why:** Point-in-time valuation and auditability fail if a later-filed fact can enter an earlier
valuation or if the public/private source statement points to a different filing than the value.

**How to detect / apply:** For every selected specialist fact, require and validate `filed`,
`end`, `accn`, `form`, unit, and currency. Gate on `filed <= valuation_date`, preserve the exact
selected fact's lineage, and reject conflicts rather than relying on list order. Regression-test
the selected accession and a fact whose period ends before but is filed after the valuation date.

The parser must receive the valuation cutoff separately; setting `valuation_date=filed_date` makes every source self-eligible and silently reintroduces look-ahead. Same-period candidates are ordered by period end, filed date, amendment precedence, and accession—not by numeric value or input order.
