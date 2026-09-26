---
name: us-website-publishes-confirmed-batches-01-10
description: The FinSight website U.S. universe is the confirmed Batches 01–10 catalog, never the loose 206-artifact folder.
metadata: { type: feedback }
---
The public FinSight website must serve the immutable catalog
`US-RESET-2026-08-14-B01-B10-1.0`: exactly 100 companies from confirmed Universe Reset
Batches 01–10. It must not enumerate `backend/app/data/us_valuations/`, whose 206 loose
artifacts belong to an older publication surface.

**Why:** The user explicitly corrected the website denominator. Directory enumeration can silently
publish companies that were not part of the ten reviewed batches and can mix incompatible valuation
methodologies.

**How to detect / apply:** `GET /api/us-valuations` must report `count: 100`,
`included_batches: [1..10]`, and catalog version `US-RESET-2026-08-14-B01-B10-1.0`.
The response must not include a later loose artifact such as NVDA. Serve only manifest-bound files
whose hashes validate through the active catalog pointer.
