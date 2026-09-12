---
name: sec-event-exhibits-can-hide-behind-business-filenames
description: SEC event capture must not assume exhibit filenames contain 99, exhibit, or release.
metadata: { type: gotcha }
---
An SEC 8-K can label an attachment as Exhibit 99.1 while giving the actual file a business-oriented name. Coinbase's
July 30, 2026 earnings exhibit was named `q226earningsdeck_sec.htm`, so Batch 40's filename-token filter skipped it even
though the primary 8-K linked it explicitly.

**Why:** A captured primary 8-K plus an incomplete attachment inventory can make event review look complete while
omitting the document that contains the operating metrics and management context.

**How to detect / apply:** Reconcile every relevant local HTML link in the primary filing against the captured inventory,
and recognize earnings/deck filenames in addition to generic `99`, `exhibit`, and `release` tokens. For load-bearing
event review, prefer the filing's exhibit metadata over filename conventions and fail closed when a referenced exhibit is
missing.
