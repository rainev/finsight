---
name: xbrl-context-entity-outranks-wrapper-identity
description: Preserve and validate the XBRL context entity instead of inheriting a wrapper artifact CIK.
metadata: { type: gotcha }
---
A structural fact's entity identifier and scheme must come from its XBRL context. A surrounding FinSight artifact, source-manifest directory, or requested CIK can disagree; copying that wrapper identity onto the fact would conceal a wrong-issuer promotion.

**Why:** The hermetic structural fixture carries entity `0000000000` while the wrapper artifact uses `0000000001`. The parser correctly exposed the mismatch only after context identity became first-class.

**How to detect / apply:** Retain `context.entityIdentifier` on every structural candidate and require an exact normalized match to the public-parent CIK before selection. Preserve the mismatching source identity in rejected evidence. See [[sec-issuer-identity-is-not-exact-display-name]].
