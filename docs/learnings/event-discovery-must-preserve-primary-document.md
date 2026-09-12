---
name: event-discovery-must-preserve-primary-document
description: SEC event inventory must retain the primary filename for body capture, not only the URL.
metadata: { type: gotcha }
---
Live September 2026 captures exposed `primary_filing_body_unavailable_or_unsafe` even though SEC submissions supplied a valid primary document. `_event_records` retained its URL but dropped the filename consumed by `_event_with_index`.

**Why:** direct event-download tests constructed `primaryDocument` themselves and missed the actual discovery-to-download handoff.

**How to detect / apply:** preserve `primary_document` and test the complete submissions-record conversion before download. The primary filing must have its own captured source hash. Exhibit capture or a directory listing is not equivalent to review of the economic event; unfamiliar events still require an approved rule.
