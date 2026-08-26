---
name: reused-sec-packets-preserve-fetch-metadata
description: Reused SEC packet metadata must be unwrapped and carried forward exactly or deterministic replay silently weakens provenance.
metadata: { type: gotcha }
---
An immutable packet's `submissions.meta.json` and `companyfacts.meta.json` wrap the original client
metadata inside `fetch_metadata`. Passing the entire wrapper back to the packet builder makes it look
like metadata is unavailable and changes the manifest even though the source JSON is byte-identical.

**Why:** Batch 10's first replay preserved the financial facts but replaced recorded network-fetch
timestamps and source hashes with `unavailable_from_client`, so the evidence tree was not
deterministic.

**How to detect / apply:** on cache reuse, pass `meta["fetch_metadata"]` to the packet builder, while
retaining the wrapper's payload hash separately. Compare complete packet trees, not only submissions
and Companyfacts payload hashes. A correct replay preserves both provenance and bytes. See
[[canonical-source-identity-uses-normalized-evidence]].
