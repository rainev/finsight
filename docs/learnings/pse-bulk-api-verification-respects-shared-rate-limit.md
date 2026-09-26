---
name: pse-bulk-api-verification-respects-shared-rate-limit
description: A full PSE catalog HTTP parity scan can exhaust the local 120-per-minute per-IP limiter and temporarily affect the signed-in PH page.
metadata: { type: gotcha }
---
During Batch 16 local activation, a 168-detail HTTP parity scan reached `429` after roughly 120 requests. The signed-in PH browser session shared the local IP rate-limit key: its next calculator request failed and a fresh page briefly showed `0 companies` until the window reset and the list refetched. The catalog itself remained healthy, and the browser later showed all 168 companies.

During Batch 20 local activation, two post-scan browser attempts rendered the correct 208-entry detail/footer but an empty PH search dropdown; one attempt logged HTTP 200 and 208 items from the PSE list endpoint (and 200/100 from the US list). A later clean browser run loaded both lists and navigated search to REDC. This confirms an intermittent search-hydration symptom, but **does not establish that rate limiting caused both attempts**.

During Batch 24 staging, a 248-detail parity scan completed successfully with retry waits, but the immediately following browser run reached FAF while shared-IP requests were still returning `429`. Its heading wait timed out; staged backend logs showed `429` for FAF detail, calculator, history and list, not a catalog or model failure. Do not run the bulk API verifier and the signed-in browser check back-to-back in the same limiter window. Wait for reset and rerun the browser alone.

The next Batch 24 browser attempt was run alone but rapidly visited eight issuer pages; React's repeated list/detail/history requests again exhausted the same window by X. Keep the browser acceptance path to representative states, or pace navigation across windows. Let the full API parity check cover every issuer's exact detail and calculator status; a single rapid browser tour of all 248 records is not how a person uses the page.

**Why:** The general API limiter is Postgres-backed and defaults to client-IP keys, so parallel verification requests from the same local client affect the normal UI even when authentication differs.

**How to detect / apply:** For future active-catalog checks, respect `Retry-After` or pace requests below 120 per minute; do not disable the limiter or interpret a transient `429`/zero-company footer as catalog corruption. After reset, recheck the live list, calculator, search navigation, and active pointer before recording a pass. If search stays empty despite 200 responses with populated `items`, inspect the browser's list-promise/auth hydration path separately; an HTTP 200 alone is not proof that the dropdown populated.
