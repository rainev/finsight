---
name: pse-list-validates-catalog-once
description: The active PSE list timed out because it revalidated every catalog artifact once per issuer; reuse the validated catalog within one request.
metadata: { type: gotcha }
---
During Batch 21 local activation, the signed-in detail page rendered but PH search remained at `0 · PSE V2`. A direct authenticated `GET /api/pse-valuations` timed out after 30 seconds. The list handler loaded the catalog once, then called `_load_artifact` for each of 218 entries; that helper loaded the pointer again, and `load_pointer` hash-validates **every** artifact. The request therefore repeated full-catalog validation for every item. Passing in the already loaded catalog kept the same per-artifact hash checks and response contract; the live list then returned 218 records in about 0.19 seconds, and a clean browser run searched to PHA.

**Why:** A correct but repeated integrity check can turn a growing catalog into a quadratic request. A detail endpoint can stay healthy while the global search is empty because its list response is still pending. This is distinct from a `429` rate-limit response; see [[pse-bulk-api-verification-respects-shared-rate-limit]].

**How to detect / apply:** Time the real authenticated list endpoint when search is empty, and inspect whether it reloads the catalog inside its item loop. Validate the catalog once per request, continue verifying each requested artifact, and assert in a focused test that the list invokes the catalog loader once. Recheck live search, exact stored-versus-served parity, and the active pointer after the change.
