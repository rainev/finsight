---
name: companyfacts-cross-accession-restatements-are-not-duplicates
description: Companyfacts may retain amended or later-filed values for one fiscal year; fail on unequal duplicates within one accession, then choose deterministically across accessions.
metadata: { type: gotcha }
---
The real JPM packet contains different `NetIncomeLoss` observations associated with the same
fiscal year across different SEC accessions. A first selector version treated the cross-
accession difference as a duplicate conflict and blocked the entire bank route.

**Why:** Companyfacts preserves amendments, comparative disclosures, and later-filed versions.
Those are distinct provenance records, not unordered duplicates. The point-in-time selector
must still fail if the same concept, period, and accession carries unequal values, but it may
choose the latest cutoff-eligible filing across different accessions.

**How to detect / apply:** De-duplicate by `(concept, period_end, accession)` and reject unequal
values within that key. For a fiscal-year series, select deterministically by period end,
filed date, and accession after applying the valuation-date gate. Never collapse or average
cross-accession values.

