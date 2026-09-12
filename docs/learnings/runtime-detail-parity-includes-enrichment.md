---
name: runtime-detail-parity-includes-enrichment
description: Compare staged valuation artifacts with the API only after adding the catalog and freshness fields that the runtime intentionally owns.
metadata: { type: gotcha }
---

The U.S. valuation detail endpoint adds `catalog_version` and `freshness` after loading and sanitizing the staged
artifact. A verifier that compares the raw staged JSON directly with the HTTP response will therefore report every
detail as different even when the valuation content is exact.

**Why:** Those fields describe the active runtime snapshot and refresh state, so they correctly belong to the serving
layer rather than the immutable issuer artifact. Ignoring this boundary produced 0/450 byte-parity even though the only
differences were the two expected runtime fields.

**How to detect / apply:** A manifest-controlled catalog artifact is already public and canonical. First assert that a
sanitizer replay is byte/field-idempotent; then build the expected response from the **raw stored artifact** and add the
manifest's `catalog_version` and ticker-specific `refresh_status` (or historical-snapshot default). Never sanitize the
expected artifact only inside the parity verifier: that can reproduce and conceal the same runtime mutation. Still
verify list parity, all detail status codes, calculator default parity, private-key absence and forbidden serving imports
separately.
