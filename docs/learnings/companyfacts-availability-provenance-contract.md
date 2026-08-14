---
name: companyfacts-availability-provenance-contract
description: Ordinary current CompanyFacts records may omit extended provenance; replacement aggregates and annual-carried records may not.
metadata: { type: gotcha }
---
The evidence-aware bridge reconciler must treat a production, current ordinary account with a nonempty `source_accession` as source-backed even when `source_kind` or `evidence_class` is null. The CompanyFacts normalizer intentionally preserves those optional metadata fields instead of inventing provenance. Requiring all three fields caused every required account in the real Microsoft fixture to block despite the legacy bridge being complete.

The optional independently supplied `total_interest_bearing_debt` aggregate is different: because it can replace five detailed debt fields, it requires nonempty `source_kind`, `evidence_class`, and exact `covered_fields` in addition to current production authority and accession.

An annual-carried record is also different. `fallback_level="annual_carried_forward"` and `freshness="carried_forward"` are a bidirectional pair, and eligibility requires production authority, reported state, a finite nonnegative value, `source_kind="companyfacts"`, `evidence_class="reported"`, an accession, and integer age from 0 through 365 days. The XBRL producer must emit authority and evidence class explicitly; recovery must not invent either when metadata is absent.

**Why:** Provenance requirements must match the upstream producer contract. Tightening them downstream without first enriching the source does not improve evidence quality; it converts valid reported facts into false gaps.

**How to detect / apply:** Run a real normalizer result through `FieldAvailability.from_dict()` and `reconcile_bridge()`. A legacy-complete issuer such as MSFT must remain complete with the same cash, debt, and bridge adjustment. Keep optional ordinary current metadata optional. For replacement aggregates and annual-carried facts, reconstruct eligibility from the complete authoritative metadata and reject missing, conflicting, future, over-age, shadow, or forged records.
