---
name: earnings-release-supersession-is-field-specific
description: An earnings release can supersede named financial fields without refreshing claims and schedules it does not report.
metadata: { type: gotcha }
---
SNDK's August release updates revenue, cash flow, cash, investments, debt and
shares, but does not separately update the April tax indemnity or commitment
schedules.

**Why:** Treating the release as a complete new filing silently carries or erases
unreported claims while presenting one date for every input.

**How to detect / apply:** Store superseded and retained field lists with source
hashes. Each retained claim keeps its original date/freshness or remains review;
once a later regular filing is eligible, it replaces the release route.
