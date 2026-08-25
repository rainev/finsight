---
name: sec-issuer-identity-is-not-exact-display-name
description: Verify SEC issuer identity with CIK and ticker while retaining display-name variants; exact name equality creates false mismatches.
metadata: { type: gotcha }
---
In the real Batch 01 packets, all ten CIK/ticker pairs match the frozen manifest, but only AAPL,
CRM, and DELL use the exact manifest display name in both SEC source identities. Other valid
packets contain SEC legal-name variants, capitalization differences, punctuation, or a non-
breaking space.

**Why:** Treating issuer name as an exact identity key would reject valid SEC packets or tempt
an unsafe silent name rewrite. CIK is the durable issuer identifier and ticker is the batch
cross-check; names are provenance-preserved aliases that still need human-readable review.

**How to detect / apply:** Require exact normalized CIK and manifest ticker. Preserve the
manifest display name plus both SEC source names in the private packet. Flag a materially
different name for review, but do not require byte-for-byte display-name equality unless a
separate canonical-name policy has been approved.

