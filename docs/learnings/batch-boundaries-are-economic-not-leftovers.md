---
name: batch-boundaries-are-economic-not-leftovers
description: A deterministic exact-cover partition is insufficient unless boundary roles preserve issuer identity and have predeclared economic meaning.
metadata: { type: gotcha }
---
Future reset batches may use deterministic cohort packing, but the two boundary members cannot be
arbitrary leftovers. Preserve every issuer's actual sector lane, name the economic reason for each
boundary, and use `partition_family_id` only as a workload/preflight grouping—not as final
valuation routing. Final source-backed routing may change after filings are read without swapping
the frozen company.

**Why:** The first 49-batch partition was numerically perfect yet placed unrelated companies into
false core lanes. It would have passed count and hash tests while undermining the purpose of the
boundary challenge.

**How to detect / apply:** Assert exact cover and determinism, then separately assert zero
overwritten lane IDs, a nonempty approved reason on every boundary, no boundary reason on core
members, and an economic review of every cross-sector exception. Reject result-driven selection.
See [[canonical-source-identity-uses-normalized-evidence]].
