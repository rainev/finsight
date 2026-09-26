---
name: pse-v2-corpus-blockers-are-authoritative
description: Existing PSE filing corpora are source-rich but their specialist-input review blockers must control V2 publication.
metadata: { type: gotcha }
---
The Phase A PSE corpora can contain thousands of page-linked fact candidates while still being correctly marked
`calculation_status: blocked`. Do not treat document volume, parser confidence, or a legacy consolidated-company value
as permission to publish a specialist V2 valuation. AP may remain provisional on its explicitly labeled legacy FCFF
proxy; SCC, ACR, PERC, BDO, AREIT, ALI, and AC stay null until the route-specific missing/review fields close.

**Why:** A specialist route needs economic objects that generic statements do not establish: reserve/segment values,
bank capital and common book equity, sustainable REIT distributions, or attributable SOTP components and parent claims.

**How to detect / apply:** Read each issuer's corpus `validation.json` and `requirements.json` before building the
artifact. Any failed required-input check produces `not_available` + `blocked`, with the exact reasons carried into the
public artifact. Never replace a missing critical field with zero.

