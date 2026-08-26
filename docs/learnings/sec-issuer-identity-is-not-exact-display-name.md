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

**How to detect / apply:** Require exact normalized CIK and an explicit manifest-to-SEC ticker
mapping. Preserve the manifest display name plus both SEC source names in the private packet.
Share-class punctuation can differ without changing the security: Batch 09 freezes Brown–Forman
Class B as `BF.B`, while SEC submissions use `BF-B`. Record that alias with the same CIK and class;
never silently rename or substitute the issuer. Flag materially different names/classes for review,
but do not require byte-for-byte display-name equality unless a canonical-name policy is approved.
