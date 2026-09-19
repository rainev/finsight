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

WG32's Core put term appears in two interim filings (five-year cadence,75% of
initial-fair-value floor) and is omitted from later annual/current narrative.
Omission alone is not source-proven amendment or revocation. Retain the dated
term with current-validity review; do not silently remove the floor or infer a
current exercise date/claim amount from the omission.
