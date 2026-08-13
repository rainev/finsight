---
name: companyfacts-availability-provenance-contract
description: Ordinary FinSight CompanyFacts availability records require an accession, but source_kind and evidence_class may legitimately be absent.
metadata: { type: gotcha }
---
The evidence-aware bridge reconciler must treat a production, current ordinary account with a nonempty `source_accession` as source-backed even when `source_kind` or `evidence_class` is null. The CompanyFacts normalizer intentionally preserves those optional metadata fields instead of inventing provenance. Requiring all three fields caused every required account in the real Microsoft fixture to block despite the legacy bridge being complete.

The optional independently supplied `total_interest_bearing_debt` aggregate is different: because it can replace five detailed debt fields, it requires nonempty `source_kind`, `evidence_class`, and exact `covered_fields` in addition to current production authority and accession.

**Why:** Provenance requirements must match the upstream producer contract. Tightening them downstream without first enriching the source does not improve evidence quality; it converts valid reported facts into false gaps.

**How to detect / apply:** Run a real normalizer result through `FieldAvailability.from_dict()` and `reconcile_bridge()`. A legacy-complete issuer such as MSFT must remain complete with the same cash, debt, and bridge adjustment. Keep optional ordinary metadata optional; apply stronger metadata only to replacement aggregates whose authority depends on it.
