---
name: canonical-source-identity-uses-normalized-evidence
description: Preserve fetched bytes, but derive a reproducible canonical dataset from pinned inputs and normalized economic events rather than mutable page scaffolding.
metadata: { type: gotcha }
---
An authoritative corroborating webpage can return different bytes even when the underlying event
is unchanged. Keep every raw response and hash for audit, but make canonical dataset identity
depend on a pinned membership input plus a small, schema-validated semantic event record. For the
2026-08-14 reset universe, the normalized S&P event is announcement date, effective date, index,
addition, and deletion; transient HTML does not alter the universe hash.

**Why:** Hashing live presentation HTML directly into canonical identity made two truthful source
captures appear nondeterministic even though both proved the same AVB/RDDT event.

**How to detect / apply:** If fresh captures have unequal raw hashes, compare the parsed semantic
record and canonical output. Preserve both raw variants, reject any semantic disagreement, and
require independent A/B canonical equality before freezing. See
[[batch-boundaries-are-economic-not-leftovers]].
